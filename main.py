import os
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncpg
from fastapi import FastAPI, HTTPException, status, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from google.api_core import exceptions as google_exceptions
import uuid
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Constants ---
MAX_CONVERSATION_TOKENS = 20000

# --- API Key and Model Configuration ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL_VERSION = os.getenv("GEMINI_MODEL_VERSION", "gemini-1.5-pro")

if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
    raise ValueError("GEMINI_API_KEY environment variable not set or is still a placeholder. Please update your .env file.")

genai.configure(api_key=GEMINI_API_KEY)

# --- Database Connection ---
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL or "user:password" in DATABASE_URL:
     raise ValueError("DATABASE_URL environment variable not set or is still a placeholder. Please update your .env file.")
_db_pool: Optional[asyncpg.Pool] = None

async def _init_connection(connection):
    await connection.set_type_codec('jsonb', encoder=json.dumps, decoder=json.loads, schema='pg_catalog')

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _db_pool
    print("Application startup: connecting to database...")
    try:
        _db_pool = await asyncpg.create_pool(DATABASE_URL, init=_init_connection)
        print(f"Successfully connected to the database and configured to use '{GEMINI_MODEL_VERSION}'.")
    except Exception as e:
        print(f"FATAL: Failed to connect to the database: {e}")
        _db_pool = None
    yield
    if _db_pool:
        print("Application shutdown: closing database connection pool...")
        await _db_pool.close()
        print("Database connection pool closed.")

app = FastAPI(
    title="AI Chatbox API",
    description="Backend API for an AI Chatbox application with session management.",
    version="1.0.0",
    lifespan=lifespan
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models ---

class ChatMessage(BaseModel):
    role: str
    content: str

class GenerationConfigModel(BaseModel):
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    candidate_count: Optional[int] = None
    max_output_tokens: Optional[int] = None
    system_instruction: Optional[str] = None
    bot_version: Optional[str] = None

class MessageRequest(BaseModel):
    message: str = Field(..., min_length=1)
    config: Optional[GenerationConfigModel] = None

class StartChatSessionRequest(BaseModel):
    user_id: Optional[int] = None
    system_prompt: Optional[str] = None

class StartChatSessionResponse(BaseModel):
    session_id: str
    session_name: Optional[str] = None
    system_prompt: Optional[str] = None
    history: List[ChatMessage] = Field(default_factory=list)

class ChatSessionResponse(BaseModel):
    session_id: str
    session_name: Optional[str] = None
    system_prompt: Optional[str] = None
    bot_version: Optional[str] = None
    history: List[ChatMessage]

class UserSessionInfo(BaseModel):
    session_id: uuid.UUID
    updated_at: datetime
    title: Optional[str] = None

class Persona(BaseModel):
    prompt_id: Optional[int] = None
    role_name: str
    avatar_url: Optional[str] = None
    default_language: Optional[str] = 'English'
    goal: str
    personality: str
    tone_of_voice: Optional[str] = None
    expertise: Optional[str] = None
    setting: str
    situation: Optional[str] = None
    must_do_rules: Optional[str] = None
    must_not_do_rules: Optional[str] = None
    response_length: Optional[str] = None
    response_format: Optional[str] = None
    starting_instruction: Optional[str] = None
    additional_notes: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        orm_mode = True

# --- Persona CRUD Endpoints ---

@app.post("/api/personas", response_model=Persona, status_code=status.HTTP_201_CREATED)
async def create_persona(persona: Persona):
    if not _db_pool:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection is not available.")
    async with _db_pool.acquire() as connection:
        try:
            data = persona.dict(exclude={'prompt_id', 'created_at'})
            columns = ", ".join(data.keys())
            placeholders = ", ".join([f"${i+1}" for i in range(len(data))])
            query = f"INSERT INTO personas ({columns}) VALUES ({placeholders}) RETURNING *"
            record = await connection.fetchrow(query, *data.values())
            return record
        except asyncpg.exceptions.UniqueViolationError:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Persona with role_name '{persona.role_name}' already exists.")
        except Exception as e:
            print(f"Error creating persona: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

@app.get("/api/personas", response_model=List[Persona])
async def get_all_personas():
    if not _db_pool:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection is not available.")
    async with _db_pool.acquire() as connection:
        records = await connection.fetch("SELECT * FROM personas ORDER BY role_name")
        return records

@app.put("/api/personas/{prompt_id}", response_model=Persona)
async def update_persona(prompt_id: int, persona: Persona):
    if not _db_pool:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection is not available.")
    async with _db_pool.acquire() as connection:
        data = persona.dict(exclude={'prompt_id', 'created_at'}, exclude_unset=True)
        set_clauses = ", ".join([f"{key} = ${i+2}" for i, key in enumerate(data.keys())])
        query = f"UPDATE personas SET {set_clauses} WHERE prompt_id = $1 RETURNING *"
        record = await connection.fetchrow(query, prompt_id, *data.values())
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Persona with prompt_id {prompt_id} not found.")
        return record

@app.delete("/api/personas/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_persona(prompt_id: int):
    if not _db_pool:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection is not available.")
    async with _db_pool.acquire() as connection:
        result = await connection.execute("DELETE FROM personas WHERE prompt_id = $1", prompt_id)
        if result == "DELETE 0":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Persona with prompt_id {prompt_id} not found.")
        return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Chat Session Endpoints ---

@app.post("/api/chat/start", response_model=StartChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def start_chat_session(request: StartChatSessionRequest = StartChatSessionRequest()):
    if not _db_pool:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection is not available.")
    
    async with _db_pool.acquire() as connection:
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

@app.get("/api/users/{user_id}/sessions", response_model=List[UserSessionInfo], status_code=status.HTTP_200_OK)
async def get_user_sessions(user_id: int):
    if not _db_pool:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection is not available.")

    async with _db_pool.acquire() as connection:
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

@app.get("/api/chat/{session_id}", response_model=ChatSessionResponse, status_code=status.HTTP_200_OK)
async def get_chat_history(session_id: uuid.UUID):
    if not _db_pool:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection is not available.")
    async with _db_pool.acquire() as connection:
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

@app.post("/api/chat/{session_id}/message", response_model=ChatSessionResponse, status_code=status.HTTP_200_OK)
async def handle_chat_message(session_id: uuid.UUID, request: MessageRequest):
    if not _db_pool:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection is not available.")
    async with _db_pool.acquire() as connection:
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
            bot_version_override = None

            if request.config:
                config_dict = request.config.dict(exclude_unset=True)
                if "system_instruction" in config_dict:
                    system_instruction_override = config_dict.pop("system_instruction")
                if "bot_version" in config_dict:
                    bot_version_override = config_dict.pop("bot_version")
                generation_config_override = GenerationConfig(**config_dict)

            final_system_instruction = system_instruction_override if system_instruction_override is not None else session_record.get('system_prompt')
            final_bot_version = bot_version_override or GEMINI_MODEL_VERSION
            
            try:
                model = genai.GenerativeModel(final_bot_version, system_instruction=final_system_instruction)
                
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
                
                chat = model.start_chat(history=[m for m in gemini_history[:-1]])
                response = await chat.send_message_async(
                    content=gemini_history[-1]['parts'],
                    generation_config=generation_config_override
                )
                history.append(ChatMessage(role="model", content=response.text))

            except google_exceptions.NotFound as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid bot_version: The model '{final_bot_version}' was not found. Please check the model name."
                )
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
                bot_version=final_bot_version,
                history=history
            )
