import json
from typing import List
import uuid
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from fastapi import APIRouter, HTTPException, status, Depends

from db.session import get_db_pool
from models.chat import (
    ChatMessage,
    MessageRequest,
    StartChatSessionRequest,
    StartChatSessionResponse,
    ChatSessionResponse,
    UserSessionInfo,
)
from core.config import GEMINI_MODEL_VERSION, MAX_CONVERSATION_TOKENS

router = APIRouter()

@router.post("/start", response_model=StartChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def start_chat_session(request: StartChatSessionRequest = Depends(), db_pool=Depends(get_db_pool)):
    if not db_pool:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection is not available.")
    
    async with db_pool.acquire() as connection:
        try:
            result = await connection.fetchrow(
                "INSERT INTO chat_sessions (user_id, system_prompt, history) VALUES ($1, $2, '[]'::jsonb) RETURNING session_id, session_name, system_prompt, history",
                request.user_id, request.system_prompt
            )
            if result:
                return StartChatSessionResponse(
                    session_id=str(result['session_id']), 
                    session_name=result['session_name'], 
                    system_prompt=result['system_prompt'], 
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
        try:
            result = await connection.fetchrow("SELECT session_id, session_name, system_prompt, history FROM chat_sessions WHERE session_id = $1", session_id)
            if result:
                history_data = result['history']
                if isinstance(history_data, str):
                    history_data = json.loads(history_data)
                return ChatSessionResponse(
                    session_id=str(result['session_id']), 
                    session_name=result['session_name'], 
                    system_prompt=result['system_prompt'], 
                    history=history_data
                )
            else:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Chat session with ID '{session_id}' not found.")
        except Exception as e:
            print(f"Error retrieving chat session: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

@router.post("/{session_id}/message", response_model=ChatSessionResponse, status_code=status.HTTP_200_OK)
async def handle_chat_message(session_id: uuid.UUID, request: MessageRequest, db_pool=Depends(get_db_pool)):
    if not db_pool:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection is not available.")
    async with db_pool.acquire() as connection:
        async with connection.transaction():
            session_record = await connection.fetchrow("SELECT history, session_name, system_prompt FROM chat_sessions WHERE session_id = $1", session_id)
            if not session_record:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Chat session with ID '{session_id}' not found.")
            
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

            final_system_instruction = system_instruction_override if system_instruction_override is not None else session_record.get('system_prompt')
            
            model = genai.GenerativeModel(GEMINI_MODEL_VERSION, system_instruction=final_system_instruction)
            
            gemini_history = [{"role": msg.role, "parts": [msg.content]} for msg in history]
            
            while True:
                total_tokens = await model.count_tokens_async(gemini_history)
                if total_tokens.total_tokens <= MAX_CONVERSATION_TOKENS:
                    break
                
                print(f"Token count {total_tokens.total_tokens} exceeds limit. Truncating history...")
                if len(gemini_history) > 2:
                    gemini_history = gemini_history[2:]
                else:
                    break
            
            history = [ChatMessage(role=msg["role"], content=msg["parts"][0]) for msg in gemini_history]
            
            try:
                chat = model.start_chat(history=[m for m in gemini_history[:-1]])
                response = await chat.send_message_async(
                    content=gemini_history[-1]['parts'],
                    generation_config=generation_config_override
                )
                history.append(ChatMessage(role="model", content=response.text))
            except Exception as e:
                print(f"Error communicating with Gemini API: {e}")
                raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Failed to get response from AI model.")
            
            updated_history_json = [msg.dict() for msg in history]
            
            new_session_name = None
            if is_first_message:
                new_session_name = request.message[:99]
                await connection.execute(
                    "UPDATE chat_sessions SET history = $1, session_name = $2 WHERE session_id = $3",
                    updated_history_json, new_session_name, session_id
                )
            else:
                await connection.execute(
                    "UPDATE chat_sessions SET history = $1 WHERE session_id = $2",
                    updated_history_json, session_id
                )
            
            final_session_name = new_session_name if new_session_name is not None else session_record['session_name']
            
            return ChatSessionResponse(
                session_id=str(session_id), 
                session_name=final_session_name, 
                system_prompt=final_system_instruction, 
                history=history
            )

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
