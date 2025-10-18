# Alternative POST approach (for reference only)
from fastapi import APIRouter, HTTPException
from app.services.narrative_engine import narrative_engine
from app.schemas.models import StoryRequest

router = APIRouter()

@router.post("/{user_id}")
async def compile_story(user_id: str, request: StoryRequest):
    """Compile a narrative story for a specific session of a given user."""
    story = await narrative_engine.generate_session_story(user_id, request.session_id)
    if not story:
        raise HTTPException(status_code=404, detail="No memories found for this user/session.")
    return {"story": story}