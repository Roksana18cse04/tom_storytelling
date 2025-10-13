#app.api.routes.memory_map.py

from fastapi import APIRouter, HTTPException
from app.services.memory_services import memory_service

router = APIRouter(prefix="/api/memory-map", tags=["Memory Map"])

@router.get("/{user_id}")
async def get_memory_map(user_id: str):
    data = memory_service.get_user_memories(user_id)
    if not data:
        raise HTTPException(status_code=404, detail="No memories found for this user.")
    return {"user_id": user_id, "categories": data}

@router.get("/{user_id}/{category}")
async def get_category_memories(user_id: str, category: str):
    data = memory_service.get_category_memories(user_id, category)
    if not data:
        raise HTTPException(status_code=404, detail=f"No memories found in '{category}'")
    return {"user_id": user_id, "category": category, "memories": data}
