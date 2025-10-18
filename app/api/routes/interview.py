
from fastapi import APIRouter, UploadFile, Form, HTTPException
from app.services.llm_services import LLMService
from app.services.transcription_services import transcribe_audio
from app.services.memory_services import memory_service
from app.questions.questions import QUESTION_BANK
from typing import Optional
import logging

router = APIRouter()
llm = LLMService()
logger = logging.getLogger(__name__)

# Default minimum questions for phases without defined question bank
DEFAULT_MIN_QUESTIONS = 5

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

        # Detect life stage from user's response
        detected_stage = llm._detect_life_stage(text)
        if detected_stage:
            memory_service.set_phase(user_id, session_id, detected_stage)
        
        category = memory_service.get_phase(user_id, session_id)
        user_data = memory_service.get_user_memories(user_id, session_id)
        
        # Check for unanswered question
        last_question = None
        has_unanswered = False
        if category in user_data and user_data[category]:
            for mem in reversed(user_data[category]):
                if mem["question"] and not mem["response"]:
                    last_question = mem["question"]
                    has_unanswered = True
                    user_data[category].remove(mem)
                    break
        
        # If returning user with unanswered question, remind them
        if has_unanswered and text.lower().strip() in ["hi", "hello", "hey"]:
            return {
                "response": f"Welcome back! Your last question was: \"{last_question}\" but you didn't answer this. Please answer this question.",
                "current_category": category,
                "is_reminder": True
            }

        memory_service.add_memory(
            user_id=user_id,
            session_id=session_id,
            category=category,
            question=last_question or "Free Talk",
            response=text,
        )

        # Check if current phase has enough responses
        answered_count = len([m for m in user_data.get(category, []) if m["response"].strip()])
        
        # Get threshold for current phase
        phase_threshold = len(QUESTION_BANK[category]["questions"]) if category in QUESTION_BANK else DEFAULT_MIN_QUESTIONS
        
        # Auto-advance to next phase if threshold met
        should_advance = False
        if answered_count >= phase_threshold:
            all_phases = list(QUESTION_BANK.keys())
            current_index = all_phases.index(category)
            if current_index + 1 < len(all_phases):
                next_phase = all_phases[current_index + 1]
                memory_service.set_phase(user_id, session_id, next_phase)
                should_advance = True
                category = next_phase
        
        followup = await llm.generate_followup(user_id, session_id, text)
        
        # Get updated category after followup (in case it changed)
        updated_category = memory_service.get_phase(user_id, session_id)
        
        response_data = {
            "response": followup,
            "current_category": updated_category,
            "memory_saved": True,
            "answered_in_phase": answered_count
        }
        
        # Add phase transition message if advanced
        if should_advance:
            phase_name = updated_category.replace("_", " ").title()
            response_data["phase_transition"] = True
            response_data["response"] = f"That's wonderful. We've covered quite a bit about that time in your life. Now, let's move on to {phase_name}. {followup}"
        
        return response_data

    except Exception as e:
        logger.exception("Interview processing failed.")
        raise HTTPException(status_code=500, detail=str(e))
