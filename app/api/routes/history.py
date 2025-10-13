#app.api.routes.history.py


from fastapi import APIRouter, HTTPException
from app.services.memory_services import MemoryService

router = APIRouter(prefix="/api/history", tags=["History"])
memory = MemoryService()  # uses persistent version (memory.json)

# 🟢 Get chat history for a user
@router.get("/{user_id}")
async def get_history(user_id: str):
    history = memory.get_history(user_id)
    if not history:
        raise HTTPException(status_code=404, detail="No history found for this user.")
    return {"user_id": user_id, "history": history}

# 🟡 Get formatted history as plain text
@router.get("/{user_id}/formatted")
async def get_formatted_history(user_id: str):
    formatted = memory.get_formatted_history(user_id)
    if not formatted:
        raise HTTPException(status_code=404, detail="No history found for this user.")
    return {"user_id": user_id, "formatted_history": formatted}

# 🔵 Add a message manually (optional endpoint)
@router.post("/{user_id}/add")
async def add_message(user_id: str, role: str, content: str):
    memory.add_message(user_id, role, content)
    return {"message": "Message added successfully", "user_id": user_id}

# 🔴 Clear chat history
@router.delete("/{user_id}/clear")
async def clear_history(user_id: str):
    memory.clear(user_id)
    return {"message": f"History cleared for user {user_id}"}

# ⚪ Get user’s current phase
@router.get("/{user_id}/phase")
async def get_phase(user_id: str):
    phase = memory.get_phase(user_id)
    return {"user_id": user_id, "phase": phase}

# 🟠 Update user’s current phase
@router.put("/{user_id}/phase")
async def update_phase(user_id: str, phase: str):
    memory.set_phase(user_id, phase)
    return {"message": f"Phase updated to '{phase}' for user {user_id}"}
