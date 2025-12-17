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
from bson import ObjectId

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
        if not session_id:
            session_id = str(uuid.uuid4())

        clean_filename = image.filename.rstrip('.')
        filename = f"{uuid.uuid4()}_{clean_filename}"
        temp_file_path = os.path.join(IMAGE_DIR, filename)
        with open(temp_file_path, "wb") as f:
            shutil.copyfileobj(image.file, f)

        s3_url = photo_service.upload_to_s3(temp_file_path, user_id)
        
        question = await photo_service.analyze_image(user_id, temp_file_path)
        
        try:
            os.remove(temp_file_path)
        except:
            pass

        # Get user's current phase/category (can be None for photo uploads)
        category = await memory_service.get_phase(user_id, session_id)
        if not category:
            category = "uncategorized"  # Temporary category until user answers
        
        # Save to MongoDB and get the generated memory_id
        memory_id = await memory_service.add_memory(
            user_id=user_id,
            session_id=session_id,
            category=category,
            question=question,
            response="",
            photos=[s3_url],
            display_text=question  # Add display_text for last_question
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
    User answers the photo question. AI may generate follow-up questions (max 4).
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
        
        # Convert memory_id to ObjectId
        try:
            obj_id = ObjectId(memory_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid memory_id format")
        
        target_memory = None
        old_category = None
        for category, memories in session_data.items():
            for mem in memories:
                if mem["_id"] == obj_id:
                    target_memory = mem
                    old_category = category
                    break
            if target_memory:
                break
        
        if not target_memory:
            raise HTTPException(status_code=404, detail="Photo memory not found")
        
        photo_url = target_memory.get("photos", [None])[0]
        if photo_url:
            photo_url = photo_url.rstrip('.')  # Clean trailing dots from URL
        
        # Update memory with answer
        from app.core.database import memories_collection
        
        # Get current response to build conversation history
        current_response = target_memory.get("response", "")
        if current_response:
            updated_response = f"{current_response}\n\n{answer}"
        else:
            updated_response = answer
        
        await memories_collection.update_one(
            {"_id": obj_id},
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
        
        # Fetch fresh memory to get updated followup_count from database
        fresh_memory = await memories_collection.find_one({"_id": obj_id})
        current_followup_count = fresh_memory.get("followup_count", 0) if fresh_memory else 0
        existing_caption = fresh_memory.get("photo_caption", "") if fresh_memory else ""
        
        # Generate caption if it doesn't exist or is "Null" (retry logic)
        # Only attempt on first answer for meaningful caption
        if current_followup_count == 0:
            if not existing_caption or existing_caption.strip().lower() in ["null", ""]:
                caption = await photo_service.generate_caption(answer, photo_url)
                await memories_collection.update_one(
                    {"_id": obj_id},
                    {"$set": {
                        "photo_caption": caption,
                        "followup_count": 0
                    }}
                )
            else:
                # Valid caption already exists, just set followup_count
                await memories_collection.update_one(
                    {"_id": obj_id},
                    {"$set": {"followup_count": 0}}
                )
        
        # Build conversation history
        conversation_history = []
        if target_memory.get("question"):
            conversation_history.append({
                "question": target_memory.get("question"),
                "answer": updated_response
            })
        

        if current_followup_count < MAX_PHOTO_FOLLOWUPS:
            followup = await photo_service.generate_photo_followup(photo_url, conversation_history, answer, current_followup_count + 1)
            
            if followup:
                # Detect category from current answer
                detected_category = memory_service.detect_initial_phase(updated_response)
                if detected_category == "ASK_USER":
                    detected_category = old_category
                
                # Increment followup count
                new_followup_count = current_followup_count + 1
                
                # Check if this is the 4th (final) followup
                if new_followup_count >= MAX_PHOTO_FOLLOWUPS:
                    # Mark as complete after 4th followup
                    await memories_collection.update_one(
                        {"_id": obj_id},
                        {"$set": {
                            "question": followup,
                            "display_text": followup,
                            "category": detected_category,
                            "followup_count": new_followup_count,
                            "photo_complete": True
                        }}
                    )
                else:
                    # Not final followup yet
                    await memories_collection.update_one(
                        {"_id": obj_id},
                        {"$set": {
                            "question": followup,
                            "display_text": followup,
                            "category": detected_category,
                            "followup_count": new_followup_count
                        }}
                    )
                
                # Update user phase so current_category appears in memory map
                await memory_service.set_phase(user_id, session_id, detected_category)
                
                return {
                    "user_id": user_id,
                    "session_id": session_id,
                    "memory_id": memory_id,
                    "response": followup,
                    "current_category": detected_category,
                    "followup_count": new_followup_count,
                    "has_followup": True,
                    "photo_complete": new_followup_count >= MAX_PHOTO_FOLLOWUPS
                }
        
        # Finalize photo story
        detected_category = memory_service.detect_initial_phase(updated_response)
        if detected_category == "ASK_USER":
            detected_category = old_category
        
        # Fetch fresh caption from database (generated after first answer)
        fresh_memory = await memories_collection.find_one({"_id": obj_id})
        existing_caption = fresh_memory.get("photo_caption", "") if fresh_memory else ""
        
        await memories_collection.update_one(
            {"_id": obj_id},
            {"$set": {
                "category": detected_category,
                "photo_complete": True
            }}
        )
        
        return {
            "user_id": user_id,
            "session_id": session_id,
            "memory_id": memory_id,
            "answer": updated_response,
            "caption": existing_caption,
            "category": detected_category,
            "moved_from": old_category if detected_category != old_category else None,
            "photo_complete": True,
            "message": "Photo story completed"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving photo answer: {str(e)}")
