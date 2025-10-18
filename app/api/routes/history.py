from fastapi import APIRouter, HTTPException, Query
from app.services.memory_services import memory_service

router = APIRouter()

@router.get("/{user_id}/sessions")
async def get_user_sessions(user_id: str):
    sessions = memory_service.get_user_sessions(user_id)
    return {"user_id": user_id, "sessions": sessions}

@router.get("/{user_id}")
async def get_formatted_history(user_id: str, session_id: str = Query(...)):
    formatted = memory_service.get_formatted_history(user_id, session_id)
    if not formatted:
        raise HTTPException(status_code=404, detail="No history found.")
    return {"user_id": user_id, "session_id": session_id, "formatted_history": formatted}

@router.delete("/{user_id}")
async def clear_session(user_id: str, session_id: str = Query(...)):
    memory_service.clear_session(user_id, session_id)
    return {"message": f"Session {session_id} cleared for user {user_id}"}