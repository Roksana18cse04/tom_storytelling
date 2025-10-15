#app.api.routes.memory_map.py
# app/api/routes/memory_map.py

from fastapi import APIRouter, HTTPException
from typing import Optional
from app.services.memory_services import memory_service

router = APIRouter()


@router.get("/{user_id}")
async def get_user_memory_map(user_id: str):
    """
    Return all sessions and their categories for a user.
    """
    user_sessions = memory_service.get_user_sessions(user_id)
    if not user_sessions:
        raise HTTPException(status_code=404, detail="No memories found for this user.")

    memory_map = {}
    for session_id in user_sessions:
        memory_map[session_id] = memory_service.get_user_memories(user_id, session_id)

    return {"user_id": user_id, "sessions": memory_map}


@router.get("/{user_id}/{session_id}")
async def get_session_memory(user_id: str, session_id: str):
    """
    Return all categories and memories for a specific session of a user.
    """
    session_data = memory_service.get_user_memories(user_id, session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail=f"No memories found for session '{session_id}'")

    return {"user_id": user_id, "session_id": session_id, "categories": session_data}


@router.get("/{user_id}/{session_id}/{category}")
async def get_category_memories(user_id: str, session_id: str, category: str):
    """
    Return all memories in a specific category for a specific session of a user.
    """
    category_data = memory_service.get_category_memories(user_id, session_id, category)
    if not category_data:
        raise HTTPException(
            status_code=404,
            detail=f"No memories found in category '{category}' for session '{session_id}'"
        )

    return {
        "user_id": user_id,
        "session_id": session_id,
        "category": category,
        "memories": category_data
    }
