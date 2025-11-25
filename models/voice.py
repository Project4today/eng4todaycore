from pydantic import BaseModel

class VoiceResponse(BaseModel):
    """A model representing a single available Polly voice."""
    id: str
    name: str
    gender: str
    language_code: str
    language_name: str
