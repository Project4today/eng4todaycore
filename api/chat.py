import json
import uuid

import google.generativeai as genai
from fastapi import APIRouter, HTTPException, status, Depends, Response
from google.api_core import exceptions as google_exceptions
from google.generativeai.types import GenerationConfig

from core.config import GEMINI_MODEL_VERSION, MAX_CONVERSATION_TOKENS, DEFAULT_POLLY_VOICE_ID
from db.session import get_db_pool
from models.chat import (
    ChatMessage,
    MessageRequest,
    StartChatSessionRequest,
    StartChatSessionResponse,
    ChatSessionResponse,
)
from models.persona import Persona
from services.aws import get_or_create_audio_url, generate_audio_filename, get_presigned_url

router = APIRouter()

def construct_system_prompt_from_persona(persona: Persona) -> str:
    """Constructs a detailed system prompt for the AI to act as an expert voice director."""
    if not persona:
        return None
    
    p = dict(persona)
    
    # Advanced instructions using a robust delimiter-based format.
    ssml_instructions = """
### SSML Generation Mandate
You are an expert SSML generator for Amazon Polly's Neural Engine. Your goal is "Human-Like Naturalness", avoiding robotic artifacts at all costs.

### I. STRICT RULES (To avoid "Fake" sounding audio)
1.  **NO PITCH:** Do not use the `pitch` attribute in `<prosody>`. It sounds artificial on Neural voices.
2.  **NO LONG FAST SEGMENTS:** Never apply `rate="fast"` (or >100%) to sentences longer than 7 words. Fast speech must be "bursts" only.
3.  **NO UNSUPPORTED TAGS:** Do not use `<emphasis>`, `whispered` effect, or `vocal-tract-length`.

### II. ADVANCED HUMANIZATION STRATEGIES
1.  **The "Anti-Robot" Fast Rule (Urgency):** Use `<prosody rate="fast">` only for short interjections (e.g., "Hurry!").
2.  **Fixing "Flat" Low Tones (Intimacy & Depth):** Use `<amazon:effect name="drc">` to add richness. Use `...` in your text to signal a natural drop in intonation.
3.  **Punctuation over Tags (Natural Breathing):** Rely on commas and periods for natural pauses. Use `<break strength="medium"/>` only for deliberate, longer pauses.

### III. FINAL INSTRUCTION
Your response MUST be in two parts, separated by a unique delimiter.

[DISPLAY_TEXT]
(Your clean, plain text response for the UI goes here. This part should not contain any SSML tags.)

[SSML_TEXT]
(Your full SSML response, enclosed in `<speak>` tags, goes here. This part contains all the performance tags.)

**EXAMPLE:**
[DISPLAY_TEXT]
Oh no! I forgot the keys. Wait... let me check my bag.

[SSML_TEXT]
<speak><amazon:effect name="drc"><prosody rate="fast">Oh no!</prosody> I forgot the keys. <break strength="medium"/> Wait... <prosody rate="105%">let me check my bag.</prosody></amazon:effect></speak>
"""

    prompt_parts = [
        "# YOUR ROLE AND GOAL",
        f"- Role: You are {p.get('role_name', 'an AI assistant')}.",
        f"- Goal: {p.get('goal', 'To assist the user.')}",
        "",
        "# CORE CHARACTERISTICS",
        f"- Personality: {p.get('personality', 'Standard AI personality.')}",
        "",
        "# RESPONSE FORMAT AND SSML RULES",
        ssml_instructions.strip(),
    ]
    
    return "\n".join(prompt_parts)


@router.post("/start", response_model=StartChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def start_chat_session(request: StartChatSessionRequest, db_pool=Depends(get_db_pool)):
    if not db_pool:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection is not available.")
    
    async with db_pool.acquire() as connection:
        try:
            result = await connection.fetchrow(
                "INSERT INTO chat_sessions (user_id, persona_id, bot_version) VALUES ($1, $2, $3) RETURNING *",
                request.user_id, request.persona_id, request.bot_version
            )
            if result:
                return StartChatSessionResponse(
                    session_id=str(result['session_id']), 
                    persona_id=result['persona_id'],
                    bot_version=result['bot_version'],
                    history=[]
                )
            else:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create chat session.")
        except Exception as e:
            print(f"Error creating chat session: {e}")
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
                text_for_audio = msg.ssml or msg.content
                filename = generate_audio_filename(text_for_audio, session_voice_id)
                msg.audio_url = get_presigned_url(filename)
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
            if request.bot_version is not None:
                await connection.execute("UPDATE chat_sessions SET bot_version = $1 WHERE session_id = $2", request.bot_version, session_id)

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
                ai_response_raw = response_obj.text

                display_text = ai_response_raw
                ssml_text = None
                text_for_audio = display_text
                text_type_for_audio = 'text'

                # --- NEW: Robust parsing using delimiters ---
                if "[SSML_TEXT]" in ai_response_raw:
                    parts = ai_response_raw.split("[SSML_TEXT]", 1)
                    display_text_part = parts[0].replace("[DISPLAY_TEXT]", "").strip()
                    ssml_text_part = parts[1].strip()

                    if display_text_part and ssml_text_part:
                        display_text = display_text_part
                        ssml_text = ssml_text_part
                        text_for_audio = ssml_text
                        text_type_for_audio = 'ssml'
                        print("--- AI Response Analysis ---")
                        print(f"Raw AI Response: {ai_response_raw}")
                        print("SSML PARSED SUCCESSFULLY using delimiter.")
                        print("--------------------------")
                    else:
                        print(f"WARNING: AI used delimiter but parts were empty. Falling back. Raw: {ai_response_raw}")
                else:
                    print(f"WARNING: AI did not use delimiter. Falling back. Raw: {ai_response_raw}")

                audio_url = await get_or_create_audio_url(text_for_audio, session_voice_id, text_type_for_audio)
                
                history.append(ChatMessage(role="model", content=display_text, ssml=ssml_text, audio_url=audio_url))

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
