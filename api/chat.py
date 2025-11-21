import json
from typing import List
import uuid
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from google.api_core import exceptions as google_exceptions
from fastapi import APIRouter, HTTPException, status, Depends, Response

from db.session import get_db_pool
from models.chat import (
    ChatMessage,
    MessageRequest,
    StartChatSessionRequest,
    StartChatSessionResponse,
    ChatSessionResponse,
    UserSessionInfo,
)
from models.persona import Persona
from core.config import GEMINI_MODEL_VERSION, MAX_CONVERSATION_TOKENS, DEFAULT_POLLY_VOICE_ID
from services.aws import get_or_create_audio_url, generate_audio_filename, get_presigned_url

router = APIRouter()

def construct_system_prompt_from_persona(persona: Persona) -> str:
    """Constructs a detailed system prompt string from a Persona object."""
    if not persona:
        return None
    
    p = dict(persona)
    prompt_parts = [
        "# YOUR ROLE AND GOAL",
        f"- Role: You are {p.get('role_name', 'an AI assistant')}.",
        f"- Goal: {p.get('goal', 'To assist the user.')}",
        f"- Expertise: {p.get('expertise', 'Not specified.')}",
        "",
        "# CORE CHARACTERISTICS",
        f"- Personality: {p.get('personality', 'Standard AI personality.')}",
        f"- Tone of Voice: {p.get('tone_of_voice', 'Normal.')}",
        "",
        "# CONTEXT",
        f"- Setting: {p.get('setting', 'A digital chat interface.')}",
        f"- Situation: {p.get('situation', 'A standard conversation.')}",
        "",
        "# RULES",
        f"- MUST DO: {p.get('must_do_rules', 'Follow user instructions.')}",
        f"- MUST NOT DO: {p.get('must_not_do_rules', 'Do not disclose you are an AI unless asked.')}",
        "",
        "# RESPONSE STRUCTURE",
        f"- Length: {p.get('response_length', 'As needed.')}",
        f"- Format: {p.get('response_format', 'Standard text.')}",
        "",
        "# STARTING INSTRUCTION",
        f"- {p.get('starting_instruction', 'Start the conversation naturally.')}"
    ]
    return "\n".join(prompt_parts)


@router.post("/start", response_model=StartChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def start_chat_session(request: StartChatSessionRequest, db_pool=Depends(get_db_pool)):
    if not db_pool:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection is not available.")
    
    async with db_pool.acquire() as connection:
        try:
            # We no longer save bot_version at the start, it's session-based
            result = await connection.fetchrow(
                "INSERT INTO chat_sessions (user_id, persona_id) VALUES ($1, $2) RETURNING session_id, persona_id",
                request.user_id, request.persona_id
            )
            if result:
                return StartChatSessionResponse(
                    session_id=str(result['session_id']), 
                    persona_id=result['persona_id'],
                    history=[]
                )
            else:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create chat session.")
        except Exception as e:
            print(f"Error creating chat session: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

@router.get("/users/{user_id}/sessions", response_model=List[UserSessionInfo], status_code=status.HTTP_200_OK)
async def get_user_sessions(user_id: int, db_pool=Depends(get_db_pool)):
    if not db_pool:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection is not available.")
    async with db_pool.acquire() as connection:
        try:
            query = """
            SELECT session_id, updated_at, session_name AS title
            FROM chat_sessions
            WHERE user_id = $1 AND session_name IS NOT NULL
            ORDER BY updated_at DESC;
            """
            records = await connection.fetch(query, user_id)
            return [UserSessionInfo(session_id=r['session_id'], updated_at=r['updated_at'], title=r['title']) for r in records]
        except Exception as e:
            print(f"Error retrieving user sessions: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

@router.get("/{session_id}", response_model=ChatSessionResponse, status_code=status.HTTP_200_OK)
async def get_chat_history(session_id: uuid.UUID, db_pool=Depends(get_db_pool)):
    if not db_pool:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection is not available.")
    async with db_pool.acquire() as connection:
        session_record = await connection.fetchrow("SELECT * FROM chat_sessions WHERE session_id = $1", session_id)
        if not session_record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Chat session with ID '{session_id}' not found.")

        session_voice_id = DEFAULT_POLLY_VOICE_ID
        persona_id = session_record.get('persona_id')
        if persona_id:
            persona_record = await connection.fetchrow("SELECT voice_id FROM personas WHERE prompt_id = $1", persona_id)
            if persona_record and persona_record.get('voice_id'):
                session_voice_id = persona_record.get('voice_id')

        history_data = session_record['history']
        if isinstance(history_data, str):
            history_data = json.loads(history_data)
        
        enriched_history = []
        for msg_data in history_data:
            msg = ChatMessage.parse_obj(msg_data)
            if msg.role == "model":
                filename = generate_audio_filename(msg.content, session_voice_id)
                msg.audio_url = get_presigned_url(filename) # Generate fresh URL on-the-fly
            enriched_history.append(msg)

        return ChatSessionResponse(
            session_id=str(session_record['session_id']), 
            session_name=session_record['session_name'], 
            persona_id=session_record['persona_id'], 
            bot_version=session_record.get('bot_version') or GEMINI_MODEL_VERSION,
            history=enriched_history
        )

@router.post("/{session_id}/message", response_model=ChatSessionResponse, status_code=status.HTTP_200_OK)
async def handle_chat_message(session_id: uuid.UUID, request: MessageRequest, response: Response, db_pool=Depends(get_db_pool)):
    if not db_pool:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection is not available.")
    async with db_pool.acquire() as connection:
        async with connection.transaction():
            if request.persona_id is not None:
                await connection.execute("UPDATE chat_sessions SET persona_id = $1 WHERE session_id = $2", request.persona_id, session_id)

            session_record = await connection.fetchrow("SELECT * FROM chat_sessions WHERE session_id = $1", session_id)
            if not session_record:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Chat session with ID '{session_id}' not found.")
            
            session_voice_id = DEFAULT_POLLY_VOICE_ID
            default_system_prompt = None
            persona_id = session_record.get('persona_id')
            if persona_id:
                persona_record = await connection.fetchrow("SELECT * FROM personas WHERE prompt_id = $1", persona_id)
                if persona_record:
                    default_system_prompt = construct_system_prompt_from_persona(persona_record)
                    if persona_record.get('voice_id'):
                        session_voice_id = persona_record.get('voice_id')

            history_data = session_record['history']
            if isinstance(history_data, str):
                history_data = json.loads(history_data)
            
            is_first_message = not history_data
            history = [ChatMessage.parse_obj(msg) for msg in history_data]
            history.append(ChatMessage(role="user", content=request.message))
            
            system_instruction_override = None
            generation_config_override = None
            if request.config:
                config_dict = request.config.dict(exclude_unset=True)
                if "system_instruction" in config_dict:
                    system_instruction_override = config_dict.pop("system_instruction")
                generation_config_override = GenerationConfig(**config_dict)

            final_system_instruction = system_instruction_override if system_instruction_override is not None else default_system_prompt
            final_bot_version = session_record.get('bot_version') or GEMINI_MODEL_VERSION
            
            try:
                model = genai.GenerativeModel(final_bot_version, system_instruction=final_system_instruction)
                
                while True:
                    gemini_history_for_count = [{"role": msg.role, "parts": [msg.content]} for msg in history]
                    total_tokens = await model.count_tokens_async(gemini_history_for_count)
                    if total_tokens.total_tokens <= MAX_CONVERSATION_TOKENS: break
                    if len(history) > 2: history = history[2:]
                    else: break
                
                gemini_history = [{"role": msg.role, "parts": [msg.content]} for msg in history]

                chat = model.start_chat(history=[m for m in gemini_history[:-1]])
                response_obj = await chat.send_message_async(
                    content=gemini_history[-1]['parts'],
                    generation_config=generation_config_override
                )
                ai_text_response = response_obj.text

                audio_url = await get_or_create_audio_url(ai_text_response, session_voice_id)
                
                history.append(ChatMessage(role="model", content=ai_text_response, audio_url=audio_url))

            except google_exceptions.NotFound as e:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid bot_version: The model '{final_bot_version}' was not found.")
            except Exception as e:
                print(f"Error communicating with Gemini API: {e}")
                raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Failed to get response from AI model.")
            
            updated_history_json = [msg.dict() for msg in history]
            
            if is_first_message:
                new_session_name = request.message[:99]
                await connection.execute("UPDATE chat_sessions SET history = $1, session_name = $2 WHERE session_id = $3", updated_history_json, new_session_name, session_id)
            else:
                await connection.execute("UPDATE chat_sessions SET history = $1 WHERE session_id = $2", updated_history_json, session_id)
            
            final_session_name = new_session_name if is_first_message else session_record['session_name']
            
            response.headers["X-Bot-Version"] = final_bot_version

            return ChatSessionResponse(
                session_id=str(session_id), 
                session_name=final_session_name, 
                persona_id=persona_id,
                bot_version=final_bot_version,
                history=history
            )
