# app/api/routes/photo_story.py

import os
import shutil
import uuid
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.services.photo_service import photo_service
from app.services.memory_services import memory_service
from typing import Optional

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

        # Save question + image to memory under the session
        memory_service.add_memory(
            user_id=user_id,
            session_id=session_id,
            category="photo_story",
            question=question,
            response="",  # response will be filled when user answers
            photos=[file_path],  # save image path
        )

        return {
            "user_id": user_id,
            "session_id": session_id,
            "question": question,
            "image_path": file_path
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing photo: {str(e)}")
