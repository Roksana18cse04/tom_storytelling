#app.api.routes.history.py


from app.services.memory_services import MemoryService
from fastapi import APIRouter, Form


memory= MemoryService()
router= APIRouter()

@router.get("/history")
async def history(user_id: str):
    return memory.get_history(user_id)