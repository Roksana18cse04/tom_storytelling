# app/api/routes/photo_story.py

import os
import shutil
import uuid
import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.services.photo_service import photo_service
from app.services.memory_services import memory_service
from typing import Optional
import logging

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

        # Save the uploaded image permanently
        # Use a unique filename to avoid conflicts
        filename = f"{uuid.uuid4()}_{image.filename}"
        file_path = os.path.join(IMAGE_DIR, filename)
        with open(file_path, "wb") as f:
            shutil.copyfileobj(image.file, f)

        # Analyze photo using LLM to get a storytelling question
        question = await photo_service.analyze_image(user_id, file_path)

        # Generate memory ID before saving
        memory_id = str(uuid.uuid4())

        # Save question + image to memory under the session
        # We need to manually create the entry to get the ID
        snippet = memory_service._generate_snippet("")
        entry = {
            "id": memory_id,
            "question": question,
            "response": "",
            "snippet": snippet,
            "photos": [file_path],
            "photo_caption": None,
            "audio_clips": [],
            "contributors": [],
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        memory_service.memory_map.setdefault(user_id, {}).setdefault(session_id, {}).setdefault("photo_story", []).append(entry)
        memory_service._save_memory()

        return {
            "user_id": user_id,
            "session_id": session_id,
            "memory_id": memory_id,  # ← Return this!
            "question": question,
            "image_path": file_path
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing photo: {str(e)}")


@router.post("/photo_answer")
async def photo_answer(
    user_id: str = Form(...),
    session_id: str = Form(...),
    memory_id: str = Form(...),
    answer: str = Form(...)
):
    """
    User answers the photo question. AI generates a caption and updates the memory.
    """
    try:
        # Get the memory with the photo
        session_data = memory_service.get_user_memories(user_id, session_id)
        photo_memories = session_data.get("photo_story", [])
        
        target_memory = None
        for mem in photo_memories:
            if mem["id"] == memory_id:
                target_memory = mem
                break
        
        if not target_memory:
            raise HTTPException(status_code=404, detail="Photo memory not found")
        
        # Generate caption from user's answer
        caption = await photo_service.generate_caption(answer, target_memory.get("photos", [None])[0])
        
        # Update the memory with answer and caption
        target_memory["response"] = answer
        target_memory["snippet"] = memory_service._generate_snippet(answer)
        target_memory["photo_caption"] = caption
        memory_service._save_memory()
        
        return {
            "user_id": user_id,
            "session_id": session_id,
            "memory_id": memory_id,
            "answer": answer,
            "caption": caption,
            "message": "Photo story saved with caption"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving photo answer: {str(e)}")
