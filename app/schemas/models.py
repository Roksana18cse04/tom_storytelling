# app/schemas/models.py
from pydantic import BaseModel
from typing import Optional

class InterviewRequest(BaseModel):
    user_id: str
    text: Optional[str] = None

class StoryRequest(BaseModel):
    session_id: str

