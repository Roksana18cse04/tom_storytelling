
from fastapi import APIRouter, UploadFile, Form, HTTPException
from app.services.llm_services import LLMService
from app.services.transcription_services import transcribe_audio
from app.services.memory_services import memory_service
from typing import Optional
import logging

router = APIRouter()
llm = LLMService()
logger = logging.getLogger(__name__)

@router.post("/")
async def interview(
    user_id: str = Form(...),
    session_id: str = Form(...),
    text: Optional[str] = Form(None),
    audio: Optional[UploadFile] = None,
):
    try:
        if audio:
            text = await transcribe_audio(audio)
        if not text:
            raise HTTPException(status_code=400, detail="Either text or audio must be provided.")

        category = memory_service.get_phase(user_id, session_id)
        user_data = memory_service.get_user_memories(user_id, session_id)
        last_question = None
        if category in user_data and user_data[category]:
            for mem in reversed(user_data[category]):
                if mem["question"] and not mem["response"]:
                    last_question = mem["question"]
                    user_data[category].remove(mem)
                    break

        memory_service.add_memory(
            user_id=user_id,
            session_id=session_id,
            category=category,
            question=last_question or "Free Talk",
            response=text,
        )

        followup = await llm.generate_followup(user_id, session_id, text)
        return {"response": followup}

    except Exception as e:
        logger.exception("Interview processing failed.")
        raise HTTPException(status_code=500, detail=str(e))
