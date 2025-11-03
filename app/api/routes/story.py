# app/api/routes/story.py

from fastapi import APIRouter, HTTPException, Query
from app.services.narrative_engine import narrative_engine

router = APIRouter()

@router.get("/chapter/{user_id}/{session_id}/{category}")
async def generate_chapter(
    user_id: str, 
    session_id: str, 
    category: str,
    style: str = Query("conversational", description="Style: conversational, literary, formal, reflective, light_hearted or concise")
):
    """Generate a narrative chapter for a specific category."""
    category = category.lower()
    chapter = await narrative_engine.generate_chapter(user_id, session_id, category, style)
    if chapter.startswith("No ") or chapter.startswith("Error"):
        raise HTTPException(status_code=404, detail=chapter)
    return {
        "user_id": user_id,
        "session_id": session_id,
        "category": category,
        "style": style,
        "chapter": chapter
    }


@router.get("/full/{user_id}/{session_id}")
async def generate_full_story(
    user_id: str,
    session_id: str,
    style: str = Query("conversational", description="Style: conversational, literary, formal, reflective, light_hearted or concise")
):
    """Generate complete life story with all chapters."""
    result = await narrative_engine.generate_full_story(user_id, session_id, style)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/{user_id}")
async def compile_story(user_id: str, session_id: str = Query(..., description="The session ID to generate story for")):
    """Compile a narrative story for a specific session (legacy endpoint)."""
    story = await narrative_engine.generate_session_story(user_id, session_id)
    if not story or story.startswith("Error"):
        raise HTTPException(status_code=404, detail="No memories found for this user/session.")
    return {"story": story}
          