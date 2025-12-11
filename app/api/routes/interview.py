
from fastapi import APIRouter, UploadFile, Form, HTTPException
from app.services.llm_services import LLMService
from app.services.transcription_services import transcribe_audio
from app.services.memory_services_mongodb import mongo_memory_service as memory_service
from app.questions.questions import QUESTION_BANK
from typing import Optional
import logging
import random

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

        # Get current phase
        category = await memory_service.get_phase(user_id, session_id)
        user_data = await memory_service.get_user_memories(user_id, session_id)
        
        text_lower = text.lower().strip()
        
        # Handle phase selection from user
        phase_map = {
            "childhood": ["childhood", "child", "kid", "young", "elementary", "primary school", "grew up"],
            "teenage years": ["teenage", "teen", "adolescent", "high school", "secondary school", "teenager", "teenage years"],
            "early adulthood": ["early adult", "young adult", "university", "college", "first job", "twenties", "early adulthood"],
            "career work": ["career", "work", "job", "professional", "office", "business", "employed","career work"],
            "relationships & family": ["relationship", "relationships", "married", "wedding", "spouse", "partner", "children", "parent", "family life", "family","relationships family","relationships & family"],
            "hobbies & adventures": ["hobby", "hobbies", "adventure", "adventures", "travel", "trip", "vacation", "journey", "visited", "tour","hobbies adventures","hobbies & adventures"],
            "home & community": ["home", "community", "moved", "neighborhood", "hometown", "lived in","home & community","home community"],
            "challenges & growth": ["challenge", "challenges", "growth", "difficult", "struggle", "overcome", "hardship","challenges growth","challenges & growth"],
            "later life & reflections": ["later life", "reflection", "reflections", "retired", "retirement", "grandchildren", "looking back","later life reflections","later life & reflections"]
        }
        
        # Check if user is EXPLICITLY requesting phase change with clear intent
        # Must have both: intent phrase + phase keyword + "memory" word
        explicit_intent_phrases = [
            "want to share", "want to shear", "want to explore",
            "let's explore", "let's talk about",
            "i'd like to share", "move to"
        ]
        
        has_explicit_intent = any(phrase in text_lower for phrase in explicit_intent_phrases)
        has_memory_keyword = any(word in text_lower for word in ["memory", "memories", "story", "stories", "experience", "experiences"])
        
        # Detect which phase user wants (only if explicit intent)
        detected_phase = None
        if has_explicit_intent and has_memory_keyword:
            for phase_name, keywords in phase_map.items():
                if any(kw in text_lower for kw in keywords):
                    detected_phase = phase_name
                    break
        
        # If phase detected (including same category re-selection)
        if detected_phase:
            # User explicitly wants to switch phase
            category = detected_phase
            await memory_service.set_phase(user_id, session_id, category)
            
            # Reload user_data after phase change to get fresh data
            user_data = await memory_service.get_user_memories(user_id, session_id)
            
            # Smart Resume: Check if category has existing memories
            core_questions = QUESTION_BANK.get(category, {}).get("questions", [])
            category_memories = user_data.get(category, [])
            
            if not category_memories:
                # EMPTY → Start with 1st core question
                if core_questions:
                    first_question = core_questions[0]
                    display_text = f"Wonderful! Let's explore your {category.replace('_', ' ')}. {first_question}"
                    await memory_service.add_memory(
                        user_id=user_id,
                        session_id=session_id,
                        category=category,
                        question=first_question,
                        response="",
                        display_text=display_text
                    )
                    return {
                        "response": display_text,
                        "current_category": category,
                        "phase_selected": True
                    }
                else:
                    return {
                        "response": f"Wonderful! Let's explore your {category.replace('_', ' ')}. What would you like to share first?",
                        "current_category": category,
                        "phase_selected": True
                    }
            else:
                # HAS MEMORIES → Find last unanswered question
                last_unanswered = None
                for mem in reversed(category_memories):
                    if mem.get("question") and not mem.get("response", "").strip():
                        last_unanswered = mem.get("question")
                        break
                
                if last_unanswered:
                    # Found unanswered question → Welcome back message
                    display_text = f"Welcome back! Your last question was: \"{last_unanswered}\" but you didn't answer this. Please answer this question."
                    
                    # Update existing memory with display_text so memory map API can show it
                    from app.core.database import memories_collection
                    await memories_collection.update_one(
                        {
                            "user_id": user_id,
                            "session_id": session_id,
                            "category": category,
                            "question": last_unanswered
                        },
                        {"$set": {"display_text": display_text}}
                    )
                    
                    return {
                        "response": display_text,
                        "current_category": category,
                        "is_reminder": True
                    }
                else:
                    # All questions have responses → Start with 1st question
                    if core_questions:
                        first_question = core_questions[0]
                        display_text = f"Wonderful! Let's explore your {category.replace('_', ' ')}. {first_question}"
                        await memory_service.add_memory(
                            user_id=user_id,
                            session_id=session_id,
                            category=category,
                            question=first_question,
                            response="",
                            display_text=display_text
                        )
                        return {
                            "response": display_text,
                            "current_category": category,
                            "phase_selected": True
                        }
        
        # If no phase detected and category is None, use detect_initial_phase
        if category is None and detected_phase is None:
            category = memory_service.detect_initial_phase(text)
            if category == "ASK_USER":
                return {
                    "response": "That sounds wonderful! Which part of your life would you like to share about?\n\n"
                                "1. Childhood (early years, family, school)\n"
                                "2. Teenage years (high school, friendships)\n"
                                "3. Early adulthood (university, first jobs)\n"
                                "4. Career & work life\n"
                                "5. Relationships & family\n"
                                "6. Hobbies & adventures (travel, interests)\n"
                                "7. Home & Community\n"
                                "8. Challanges & Growth\n"
                                "9. Later life & reflections\n\n"
                                "You can simply tell me the number or name of the phase.",
                    "awaiting_phase_selection": True,
                    "current_category": None
                }
            await memory_service.set_phase(user_id, session_id, category)
        
        # Check if user said "yes" after phase complete message OR directly mentioned phase
        if text_lower in ["yes", "yeah", "sure", "ok", "okay"] or any(kw in text_lower for kw in ["childhood", "teenage", "early adult", "career", "relationship", "hobby", "home", "challenge", "later life", "1", "2", "3", "4", "5", "6", "7", "8", "9"]):
            # Check if last question was phase complete message
            if category in user_data and user_data[category]:
                for mem in reversed(user_data[category]):
                    if mem.get("question") in ["PHASE_COMPLETE_MESSAGE", "ALL_PHASES_COMPLETE_MESSAGE"]:
                        # Check if user directly mentioned phase name or number
                        phase_number_map = {
                            "1": "childhood",
                            "2": "teenage years",
                            "3": "early adulthood",
                            "4": "career work",
                            "5": "relationships & family",
                            "6": "hobbies & adventures",
                            "7": "home & community",
                            "8": "challenges & growth",
                            "9": "later life & reflections"
                        }
                        
                        selected_phase = None
                        
                        # Check for number
                        for num, phase in phase_number_map.items():
                            if num in text_lower:
                                selected_phase = phase
                                break
                        
                        # Check for phase name
                        if not selected_phase:
                            for phase_name, keywords in phase_map.items():
                                if any(kw in text_lower for kw in keywords):
                                    selected_phase = phase_name
                                    break
                        
                        # If phase selected, start that phase
                        if selected_phase:
                            await memory_service.set_phase(user_id, session_id, selected_phase)
                            core_questions = QUESTION_BANK.get(selected_phase, {}).get("questions", [])
                            if core_questions:
                                first_question = core_questions[0]
                                display_text = f"Wonderful! Let's explore your {selected_phase.replace('_', ' ')}. {first_question}"
                                await memory_service.add_memory(
                                    user_id=user_id,
                                    session_id=session_id,
                                    category=selected_phase,
                                    question=first_question,
                                    response="",
                                    display_text=display_text
                                )
                                return {
                                    "response": display_text,
                                    "current_category": selected_phase,
                                    "phase_selected": True
                                }
                        
                        # If just "yes" without phase, show menu
                        return {
                            "response": "Great! Which phase would you like to explore?\n\n"
                                        "1. Childhood (early years, family, school)\n"
                                        "2. Teenage years (high school, friendships)\n"
                                        "3. Early adulthood (university, first jobs)\n"
                                        "4. Career & work life\n"
                                        "5. Relationships & family\n"
                                        "6. Hobbies & adventures (travel, interests)\n"
                                        "7. Home & Community\n"
                                        "8. Challenges & Growth\n"
                                        "9. Later life & reflections\n\n"
                                        "Just tell me the number or name of the phase.",
                            "awaiting_phase_selection": True,
                            "current_category": category
                        }
                    break
        
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
        if has_unanswered and text.lower().strip() in ["hey", "back", "continue", "previous"]:
            return {
                "response": f"Welcome back! Your last question was: \"{last_question}\" but you didn't answer this. Please answer this question.",
                "current_category": category,
                "is_reminder": True
            }

        # Check if user wants to skip the question
        skip_keywords = ["","null"]
        if text_lower in skip_keywords or text.strip() == "":
            # User wants to skip - get next question without saving response
            core_questions = QUESTION_BANK.get(category, {}).get("questions", [])
            answered_questions = [m.get("question") for m in user_data.get(category, []) if m.get("response", "").strip()]
            
            # Find next unanswered question
            next_question = None
            for q in core_questions:
                if q not in answered_questions and q != last_question:
                    next_question = q
                    break
            
            if next_question:
                # Save the skipped question with empty response
                if last_question:
                    await memory_service.add_memory(
                        user_id=user_id,
                        session_id=session_id,
                        category=category,
                        question=last_question,
                        response="[Skipped]"
                    )
                
                # Save next question with skip message as display_text for GET route
                skip_display_text = f"No problem! Let's move on. {next_question}"
                await memory_service.add_memory(
                    user_id=user_id,
                    session_id=session_id,
                    category=category,
                    question=next_question,
                    response="",
                    display_text=skip_display_text
                )
                
                return {
                    "response": f"No problem! Let's move on. {next_question}",
                    "current_category": category,
                    "question_skipped": True,
                    "skipped_question": last_question
                }
            else:
                # No more questions - show add more prompt
                category_display = category.replace('_', ' ').title()
                add_more_text = (f"You've answered all of Narratus' questions for {category_display}, "
                                f"but please feel free to share anything important that we may have missed, "
                                f"or maybe some reflections on this time of your life. "
                                f"When you're finished, just click Submit.")
                
                await memory_service.add_memory(
                    user_id=user_id,
                    session_id=session_id,
                    category=category,
                    question="ADD_MORE_PROMPT",
                    response="",
                    display_text=add_more_text
                )
                
                return {
                    "response": add_more_text,
                    "current_category": category,
                    "phase_complete": True
                }

        # Calculate depth score before saving
        from app.services.depth_scorer import depth_scorer
        depth_data = depth_scorer.calculate_depth_score(text)
        
        await memory_service.add_memory(
            user_id=user_id,
            session_id=session_id,
            category=category,
            question=last_question or "Free Talk",     
            response=text,
        )
        
        followup = await llm.generate_followup(user_id, session_id, text)
        
        # Handle CLOSING_Q1: Save with empty response so it appears in last_question
        if followup == "CLOSING_Q1":
            closing_q1_text = "Thanks for sharing your memories. Is there anything else you'd like to share about this part of your life?"
            await memory_service.add_memory(
                user_id=user_id,
                session_id=session_id,
                category=category,
                question="CLOSING_Q1",
                response="",
                display_text=closing_q1_text
            )
            return {
                "response": closing_q1_text,
                "current_category": category,
                "memory_saved": True
            }
        
        # Handle CLOSING_Q2: Save temporarily with empty response
        if followup == "CLOSING_Q2":
            # First, update CLOSING_Q1 with user's answer (already saved in line 335)
            # Now save CLOSING_Q2 temporarily
            closing_q2_text = "Thank you. Are you happy to move on?"
            await memory_service.add_memory(
                user_id=user_id,
                session_id=session_id,
                category=category,
                question="CLOSING_Q2",
                response="",
                display_text=closing_q2_text
            )
            return {
                "response": closing_q2_text,
                "current_category": category,
                "memory_saved": True
            }
        
        # If user just answered CLOSING_Q2, delete it from memory (don't keep the answer)
        if last_question and "CLOSING_Q2" in last_question:
            from app.core.database import memories_collection
            await memories_collection.delete_one({
                "user_id": user_id,
                "session_id": session_id,
                "category": category,
                "question": "CLOSING_Q2"
            })
        
        # Check if phase is complete
        if followup == "PHASE_COMPLETE":
            # Show "Add More" prompt for completed phase
            category_display = category.replace('_', ' ').title()
            add_more_text = (f"You've answered all of Narratus' questions for {category_display}, "
                            f"but please feel free to share anything important that we may have missed, "
                            f"or maybe some reflections on this time of your life. "
                            f"When you're finished, just click Submit.")
            
            await memory_service.add_memory(
                user_id=user_id,
                session_id=session_id,
                category=category,
                question="ADD_MORE_PROMPT",
                response="",
                display_text=add_more_text
            )
            
            return {
                "response": add_more_text,
                "current_category": category,
                "phase_complete": True
            }
        
        # Check if followup is a core question and add transition for display
        core_questions = QUESTION_BANK.get(category, {}).get("questions", [])
        is_core_question = followup in core_questions
        
        # Generate random compliment for display
        compliments = ["Lovely.", "Wonderful.", "That's great.", "Thank you for sharing.", "How interesting.", "I appreciate that."]
        display_question = followup
        if is_core_question:
            compliment = random.choice(compliments)
            display_question = f"{compliment} {followup}"
        
        # Save the AI's question to memory with display_text
        await memory_service.add_memory(
            user_id=user_id,
            session_id=session_id,
            category=category,
            question=followup,
            response="",
            display_text=display_question
        )
        
        # Get updated category after followup (in case it changed)
        updated_category = await memory_service.get_phase(user_id, session_id)
        
        # Calculate progress towards word target
        updated_user_data = await memory_service.get_user_memories(user_id, session_id)
        category_memories = updated_user_data.get(updated_category, [])
        total_category_words = sum(len(m.get("response", "").split()) for m in category_memories if m.get("response"))
        core_questions_count = len(QUESTION_BANK.get(updated_category, {}).get("questions", []))
        target_category_words = core_questions_count * 600
        
        response_data = {
            "response": display_question,
            "current_category": updated_category,
            "memory_saved": True,
            "depth_score": depth_data["total_score"],
            "depth_level": depth_data["depth_level"],
            "word_count": len(text.split()),
            "category_word_progress": {
                "current": total_category_words,
                "target": target_category_words,
                "percentage": round((total_category_words / target_category_words * 100), 1) if target_category_words > 0 else 0
            }
        }
        
        return response_data

    except Exception as e:
        logger.exception("Interview processing failed.")
        raise HTTPException(status_code=500, detail=str(e))
