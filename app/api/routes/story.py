# app/api/routes/story.py

from fastapi import APIRouter, HTTPException, Query
from app.services.narrative_engine import narrative_engine

router = APIRouter()

@router.get("/{user_id}")
async def compile_story(user_id: str, session_id: str = Query(..., description="The session ID to generate story for")):
    """Compile a narrative story for a specific session of a given user."""
    story = await narrative_engine.generate_session_story(user_id, session_id)
    if not story:
        raise HTTPException(status_code=404, detail="No memories found for this user/session.")
    return {"story": story}
          