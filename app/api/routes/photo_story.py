# app/api/routes/photo_story.py

import os
import shutil
import uuid
import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.services.photo_service import photo_service
from app.services.memory_services_mongodb import mongo_memory_service as memory_service
from typing import Optional
import logging
from fastapi import UploadFile

logger = logging.getLogger(__name__)

router = APIRouter()
IMAGE_DIR = os.path.join(os.getcwd(), "user_images")
os.makedirs(IMAGE_DIR, exist_ok=True)


@router.post("/photo_question")
async def photo_question(
    user_id: str = Form(...),
    image: UploadFile = File(...),
    session_id: Optional[str]= Form(None)  # optional session_id
):
    """
    Accepts a user-uploaded photo, analyzes it, and returns a storytelling question.
    Saves the image and associates it with a session.
    """
    if not image:
        raise HTTPException(status_code=400, detail="No image file provided.")

    try:
        # Use provided session_id or generate a new one
        if not session_id:
            session_id = str(uuid.uuid4())

        # Save the uploaded image temporarily
        filename = f"{uuid.uuid4()}_{image.filename}"
        temp_file_path = os.path.join(IMAGE_DIR, filename)
        with open(temp_file_path, "wb") as f:
            shutil.copyfileobj(image.file, f)

        # Upload to S3 and get URL
        s3_url = photo_service.upload_to_s3(temp_file_path, user_id)
        
        # Analyze photo using LLM to get a storytelling question
        question = await photo_service.analyze_image(user_id, temp_file_path)
        
        # Delete temporary local file after upload
        try:
            os.remove(temp_file_path)
        except:
            pass

        # Get user's current phase/category
        category = await memory_service.get_phase(user_id, session_id)
        if not category:
            category = "early adulthood"  # Default if no phase set
        
        # Save to MongoDB and get the generated memory_id
        memory_id = await memory_service.add_memory(
            user_id=user_id,
            session_id=session_id,
            category=category,
            question=question,
            response="",
            photos=[s3_url]
        )

        return {
            "user_id": user_id,
            "session_id": session_id,
            "memory_id": memory_id,
            "question": question,
            "image_path": s3_url
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing photo: {str(e)}")


@router.post("/photo_answer")
async def photo_answer(
    user_id: str = Form(...),
    session_id: str = Form(...),
    memory_id: str = Form(...),
    text: Optional[str] = Form(None),
    audio: Optional[UploadFile] = File(None)
):
    """
    User answers the photo question. AI may generate follow-up questions (max 2).
    """
    MAX_PHOTO_FOLLOWUPS = 4  # Structured follow-ups: Who/What → When/Where → Sensory → Emotional/Significance
    
    try:
        # Handle audio transcription
        if audio:
            from app.services.transcription_services import transcribe_audio
            answer = await transcribe_audio(audio)
        elif text:
            answer = text
        else:
            raise HTTPException(status_code=400, detail="Either text or audio must be provided")
        
        # Get the memory with the photo
        session_data = await memory_service.get_user_memories(user_id, session_id)
        
        target_memory = None
        old_category = None
        for category, memories in session_data.items():
            for mem in memories:
                if mem["_id"] == memory_id:
                    target_memory = mem
                    old_category = category
                    break
            if target_memory:
                break
        
        if not target_memory:
            raise HTTPException(status_code=404, detail="Photo memory not found")
        
        photo_url = target_memory.get("photos", [None])[0]
        
        # Update memory with answer
        from app.core.database import memories_collection
        
        # Get current response to build conversation history
        current_response = target_memory.get("response", "")
        if current_response:
            updated_response = f"{current_response}\n\n{answer}"
        else:
            updated_response = answer
        
        await memories_collection.update_one(
            {"_id": memory_id},
            {"$set": {
                "response": updated_response,
                "snippet": memory_service._generate_snippet(updated_response)
            }}
        )

        user_data = await memory_service.get_user_memories(user_id, session_id)

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
        if has_unanswered and text.lower().strip() in ["back", "continue", "previous"]:
            return {
                "last message": f"Welcome back! Your last question was: \"{last_question}\" but you didn't answer this. Please answer this question.",
                "current_category": category,
                "is_reminder": True
            }
        
        # Count follow-ups
        conversation_history = []
        if target_memory.get("question"):
            conversation_history.append({
                "question": target_memory.get("question"),
                "answer": answer
            })
        
        followup_count = len(conversation_history) - 1
        needs_depth = photo_service._needs_depth_exploration(answer, conversation_history)
        
        if needs_depth and followup_count < MAX_PHOTO_FOLLOWUPS:
            followup = await photo_service.generate_photo_followup(photo_url, conversation_history, answer, followup_count + 1)
            
            if followup:
                # Detect category from current answer
                detected_category = memory_service.detect_initial_phase(updated_response)
                if detected_category == "ASK_USER":
                    detected_category = old_category
                
                await memories_collection.update_one(
                    {"_id": memory_id},
                    {"$set": {
                        "question": followup,
                        "category": detected_category
                    }}
                )
                
                return {
                    "user_id": user_id,
                    "session_id": session_id,
                    "memory_id": memory_id,
                    "response": followup,
                    "current_category": detected_category,
                    "followup_count": followup_count + 1,
                    "has_followup": True
                }
        
        # Finalize photo story
        detected_category = memory_service.detect_initial_phase(updated_response)
        if detected_category == "ASK_USER":
            detected_category = old_category
        
        caption = await photo_service.generate_caption(updated_response, photo_url)
        
        await memories_collection.update_one(
            {"_id": memory_id},
            {"$set": {
                "photo_caption": caption,
                "category": detected_category
            }}
        )
        
        return {
            "user_id": user_id,
            "session_id": session_id,
            "memory_id": memory_id,
            "answer": updated_response,
            "caption": caption,
            "category": detected_category,
            "moved_from": old_category if detected_category != old_category else None,
            "photo_complete": True,
            "message": "Photo story completed"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving photo answer: {str(e)}")
