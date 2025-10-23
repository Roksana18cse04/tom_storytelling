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

        # Upload to Cloudinary and get URL
        cloudinary_url = photo_service.upload_to_cloudinary(temp_file_path, user_id)
        
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
            photos=[cloudinary_url]
        )

        return {
            "user_id": user_id,
            "session_id": session_id,
            "memory_id": memory_id,  # ← Return this!
            "question": question,
            "image_path": cloudinary_url
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
    User answers the photo question via text or audio. AI generates a caption and updates the memory.
    """
    try:
        # Handle audio transcription
        if audio:
            from app.services.transcription_services import transcribe_audio
            answer = await transcribe_audio(audio)
        elif text:
            answer = text
        else:
            raise HTTPException(status_code=400, detail="Either text or audio must be provided")
        
        # Get the memory with the photo from all categories
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
        
        # Detect life stage from user's answer
        detected_category = memory_service.detect_initial_phase(answer)
        if detected_category == "ASK_USER":
            detected_category = old_category  # Fallback to current category
        
        # Generate caption from user's answer (pass Cloudinary URL)
        photo_url = target_memory.get("photos", [None])[0]
        caption = await photo_service.generate_caption(answer, photo_url)
        
        # Update the memory in MongoDB
        from app.core.database import memories_collection
        await memories_collection.update_one(
            {"_id": memory_id},
            {"$set": {
                "response": answer,
                "snippet": memory_service._generate_snippet(answer),
                "photo_caption": caption,
                "category": detected_category
            }}
        )
        
        return {
            "user_id": user_id,
            "session_id": session_id,
            "memory_id": memory_id,
            "answer": answer,
            "caption": caption,
            "category": detected_category,
            "moved_from": old_category if detected_category != old_category else None,
            "message": "Photo story saved with caption"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving photo answer: {str(e)}")
