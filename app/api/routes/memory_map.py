#app.api.routes.memory_map.py
# app/api/routes/memory_map.py

from fastapi import APIRouter, HTTPException
from typing import Optional
from app.services.memory_services_mongodb import mongo_memory_service as memory_service

router = APIRouter()


# Specific routes FIRST (to avoid path conflicts)
@router.get("/progress/{user_id}/{session_id}")
async def get_progress(user_id: str, session_id: str):
    """
    Get completion progress for all categories and overall percentage.
    """
    progress = await memory_service.get_progress(user_id, session_id)
    overall = await memory_service.get_overall_progress(user_id, session_id)
    gaps = []
    richest = []
    
    return {
        "user_id": user_id,
        "session_id": session_id,
        "overall_progress": overall,
        "category_progress": progress,
        "gaps": gaps,
        "richest_categories": [{
            "category": cat,
            "progress": prog
        } for cat, prog in richest]
    }


# @router.get("/related/{user_id}/{session_id}/{memory_id}")
# async def get_related_memories(user_id: str, session_id: str, memory_id: str):
#     """
#     Find memories related to a specific memory based on common keywords.
#     """
#     related = []  # TODO: Implement in MongoDB service
#     return {
#         "user_id": user_id,
#         "session_id": session_id,
#         "memory_id": memory_id,
#         "related_memories": related
#     }


# @router.get("/threads/{user_id}/{session_id}")
# async def get_story_threads(user_id: str, session_id: str):
#     """
#     Detect recurring themes, people, or places across different life stages.
#     """
#     threads = []  # TODO: Implement in MongoDB service
#     return {
#         "user_id": user_id,
#         "session_id": session_id,
#         "story_threads": threads
#     }



# Generic routes AFTER
@router.get("/{user_id}")
async def get_user_memory_map(user_id: str):
    """
    Return all sessions and their categories for a user.
    """
    user_sessions = await memory_service.get_user_sessions(user_id)
    if not user_sessions:
        raise HTTPException(status_code=404, detail="No memories found for this user.")

    memory_map = {}
    for session_id in user_sessions:
        session_data = await memory_service.get_user_memories(user_id, session_id)
        # Convert ObjectId to string and add display field
        for category, memories in session_data.items():
            for mem in memories:
                mem["_id"] = str(mem["_id"])
                mem["memory_id"] = str(mem["_id"])
                mem["is_photo"] = bool(mem.get("photos"))
                mem["question_display"] = mem.get("display_text") or mem.get("question")
        memory_map[session_id] = session_data

    return {"user_id": user_id, "sessions": memory_map}


@router.get("/{user_id}/{session_id}")
async def get_session_memory(user_id: str, session_id: str):
    """
    Return all categories and memories for a specific session of a user.
    """
    session_data = await memory_service.get_user_memories(user_id, session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail=f"No memories found for session '{session_id}'")

    # Convert ObjectId to string and add display field
    for category, memories in session_data.items():
        for mem in memories:
            mem["_id"] = str(mem["_id"])
            mem["memory_id"] = str(mem["_id"])
            mem["is_photo"] = bool(mem.get("photos"))
            # Use display_text if available, otherwise use question
            mem["question_display"] = mem.get("display_text") or mem.get("question")

    # Find last question/message from current phase
    from app.services.memory_services_mongodb import mongo_memory_service
    from datetime import datetime
    current_phase = await mongo_memory_service.get_phase(user_id, session_id)
    
    last_question = None
    if current_phase and current_phase in session_data:
        phase_memories = session_data[current_phase]
        
        # Sort by timestamp - handle both datetime objects and strings
        def get_sort_key(mem):
            ts = mem.get('timestamp', '')
            if isinstance(ts, datetime):
                return ts.isoformat()
            return ts or ''
        
        phase_memories.sort(key=get_sort_key, reverse=True)
        
        # Get the last memory entry (most recent) from current phase
        if phase_memories:
            last_mem = phase_memories[0]
            question = last_mem.get('question', '')
            response = last_mem.get('response', '').strip()
            
            # Check for phase complete messages
            if question in ['PHASE_COMPLETE_MESSAGE', 'ALL_PHASES_COMPLETE_MESSAGE']:
                last_question = response  # The message itself
            # For any question (answered or unanswered), use display_text if available
            elif question:
                last_question = last_mem.get('display_text') or question

    return {
        "user_id": user_id,
        "session_id": session_id,
        "categories": session_data,
        "last_question": last_question,
        "current_category": current_phase
    }


@router.get("/{user_id}/{session_id}/{category}")
async def get_category_memories(user_id: str, session_id: str, category: str):
    """
    Return all memories in a specific category for a specific session of a user.
    """
    # Convert to lowercase for case-insensitive matching
    category = category.lower()
    category_data = await memory_service.get_category_memories(user_id, session_id, category)
    if not category_data:
        raise HTTPException(
            status_code=404,
            detail=f"No memories found in category '{category}' for session '{session_id}'"
        )

    # Convert ObjectId to string and add display field
    for mem in category_data:
        mem["_id"] = str(mem["_id"])
        mem["memory_id"] = str(mem["_id"])
        mem["is_photo"] = bool(mem.get("photos"))
        # Use display_text if available, otherwise use question
        mem["question_display"] = mem.get("display_text") or mem.get("question")

    return {
        "user_id": user_id,
        "session_id": session_id,
        "category": category,
        "memories": category_data
    }
