
from fastapi import APIRouter, UploadFile, Form, HTTPException
from app.services.llm_services import LLMService
from app.services.transcription_services import transcribe_audio
from app.services.memory_services_mongodb import mongo_memory_service as memory_service
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

        # Get or detect initial phase
        category = await memory_service.get_phase(user_id, session_id)
        if category is None:
            # First interaction - detect phase from user input
            category = memory_service.detect_initial_phase(text)
            if category == "ASK_USER":
                # Ask user to choose their preferred phase
                return {
                    "response": "That sounds wonderful! Which part of your life would you like to share about?\n\n"
                                "1. Childhood (early years, family, school)\n"
                                "2. Teenage years (high school, friendships)\n"
                                "3. Early adulthood (university, first jobs)\n"
                                "4. Career & work life\n"
                                "5. Relationships & family\n"
                                "6. Hobbies & adventures (travel, interests)\n"
                                "7. Later life & reflections\n\n"
                                "You can simply tell me the number or name of the phase.",
                    "awaiting_phase_selection": True,
                    "current_category": None
                }
            await memory_service.set_phase(user_id, session_id, category)
        
        user_data = await memory_service.get_user_memories(user_id, session_id)
        
        # Handle phase selection from user
        phase_map = {
            "1": "childhood", "childhood": "childhood",
            "2": "teenage years", "teenage": "teenage years", "teen": "teenage years",
            "3": "early adulthood", "early adult": "early adulthood", "adulthood": "early adulthood",
            "4": "career work", "career": "career work", "work": "career work",
            "5": "relationships & family", "relationship": "relationships & family", "family": "relationships & family",
            "6": "hobbies & adventures", "hobbies": "hobbies & adventures", "hobby": "hobbies & adventures", "adventure": "hobbies & adventures",
            "7": "later life & reflections", "later life": "later life & reflections", "reflection": "later life & reflections"
        }
        
        text_lower = text.lower().strip()
        
        # Check if user is EXPLICITLY requesting phase change
        explicit_phase_keywords = ["go with", "shift to", "move to", "talk about", "explore", "let's discuss", 
                                   "want to share", "tell about", "switch to", "change to", "start with", "want to shear {phase_map} memory"]
        is_explicit_phase_request = any(keyword in text_lower for keyword in explicit_phase_keywords)
        
        # Only detect phase change if it's an explicit request
        detected_phase = None
        if is_explicit_phase_request:
            for key, phase in phase_map.items():
                if key in text_lower:
                    detected_phase = phase
                    break
        
        if detected_phase and detected_phase != category:
            # User explicitly wants to switch phase
            category = detected_phase
            await memory_service.set_phase(user_id, session_id, category)
            
            # Get first question from new phase
            core_questions = QUESTION_BANK.get(category, {}).get("questions", [])
            if core_questions:
                first_question = core_questions[0]
                await memory_service.add_memory(
                    user_id=user_id,
                    session_id=session_id,
                    category=category,
                    question=first_question,
                    response=""
                )
                return {
                    "response": f"Wonderful! Let's explore your {category.replace('_', ' ')}. {first_question}",
                    "current_category": category,
                    "phase_selected": True
                }
            else:
                return {
                    "response": f"Wonderful! Let's explore your {category.replace('_', ' ')}. What would you like to share first?",
                    "current_category": category,
                    "phase_selected": True
                }
        
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
        if has_unanswered and text.lower().strip() in ["hi", "hello", "hey", "back", "continue", "previous"]:
            return {
                "response": f"Welcome back! Your last question was: \"{last_question}\" but you didn't answer this. Please answer this question.",
                "current_category": category,
                "is_reminder": True
            }

        await memory_service.add_memory(
            user_id=user_id,
            session_id=session_id,
            category=category,
            question=last_question or "Free Talk",     
            response=text,
        )
        
        followup = await llm.generate_followup(user_id, session_id, text)
        
        # Check if phase is complete
        if followup == "PHASE_COMPLETE":
            # Calculate progress for all phases
            all_phases = list(QUESTION_BANK.keys())
            phase_progress = {}
            
            for phase in all_phases:
                phase_data = user_data.get(phase, [])
                total_questions = len(QUESTION_BANK[phase]["questions"])
                answered = len([m for m in phase_data if m.get("response", "").strip() and len(m.get("response", "").split()) > 5])
                progress = (answered / total_questions * 100) if total_questions > 0 else 0
                phase_progress[phase] = {"progress": progress, "answered": answered, "total": total_questions}
            
            # Find phases with least progress (excluding current)
            incomplete_phases = [(p, data) for p, data in phase_progress.items() 
                               if p != category and data["progress"] < 100]
            incomplete_phases.sort(key=lambda x: x[1]["progress"])
            
            if incomplete_phases:
                # Suggest incomplete phases naturally
                suggestions = incomplete_phases[:3]
                phase_names = [p.replace('_', ' ') for p, _ in suggestions]
                
                # Create natural suggestion text
                if len(phase_names) == 1:
                    suggestion_text = phase_names[0]
                elif len(phase_names) == 2:
                    suggestion_text = f"{phase_names[0]} or {phase_names[1]}"
                else:
                    suggestion_text = f"{', '.join(phase_names[:-1])}, or {phase_names[-1]}"
                
                return {
                    "response": f"Thank you for sharing those wonderful memories about your {category.replace('_', ' ')}. "
                               f"If you'd like, we could explore your {suggestion_text} next. "
                               f"Which would you prefer?",
                    "current_category": category,
                    "phase_complete": True,
                    "suggested_phases": [p for p, _ in suggestions],
                    "progress": phase_progress
                }
            else:
                # All phases complete!
                return {
                    "response": "What a wonderful journey through your life story! You've shared so many beautiful memories. "
                               "Is there anything else you'd like to add or any phase you'd like to revisit?",
                    "current_category": category,
                    "all_phases_complete": True
                }
        
        # Save the AI's question to memory (so next time we know what was asked)
        await memory_service.add_memory(
            user_id=user_id,
            session_id=session_id,
            category=category,
            question=followup,
            response=""
        )
        
        # Get updated category after followup (in case it changed)
        updated_category = await memory_service.get_phase(user_id, session_id)
        
        response_data = {
            "response": followup,
            "current_category": updated_category,
            "memory_saved": True
        }
        
        return response_data

    except Exception as e:
        logger.exception("Interview processing failed.")
        raise HTTPException(status_code=500, detail=str(e))
