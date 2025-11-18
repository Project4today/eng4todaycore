from typing import Optional
from datetime import datetime
from pydantic import BaseModel

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
