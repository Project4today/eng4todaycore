from typing import List, Optional
from datetime import datetime
import uuid
from pydantic import BaseModel, Field

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
    history: List[ChatMessage]

class UserSessionInfo(BaseModel):
    session_id: uuid.UUID
    updated_at: datetime
    title: Optional[str] = None
