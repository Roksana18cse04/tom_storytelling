# app/api/routes/interview.py
from fastapi import APIRouter, UploadFile, Form, HTTPException
from app.services.llm_services import LLMService
from app.services.transcription_services import transcribe_audio
from app.services.memory_services import MemoryService  # shared instance
from typing import Optional

router = APIRouter()
llm = LLMService()
memory_service= MemoryService()

@router.post("/")
async def interview(
    user_id: str = Form(...),
    text: Optional[str] = Form(None),
    audio: Optional[UploadFile] = None
):
    try:
        if audio:
            text = await transcribe_audio(audio)

        if not text:
            raise HTTPException(status_code=400, detail="Either text or audio must be provided")

        # Get LLM reply
        response = llm.chat(user_id, text)

        # Save both user and assistant messages to memory
        memory_service.add_message(user_id, "User", text)
        memory_service.add_message(user_id, "Assistant", response)

        return {"Transcribed audio": text if audio else None, "Reply": response}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
