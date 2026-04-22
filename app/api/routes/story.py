# app/api/routes/story.py

from fastapi import APIRouter, HTTPException, Query
from app.services.narrative_engine import narrative_engine
from app.core.database import story_collection
from app.services.story_cache import get_or_generate_chapter, get_or_generate_full_story
import datetime

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

    chapter, from_cache, _source_fingerprint = await get_or_generate_chapter(
        user_id=user_id,
        session_id=session_id,
        category=category,
        style=style,
    )

    if chapter.startswith("No ") or chapter.startswith("Error"):
        raise HTTPException(status_code=404, detail=chapter)

    # Fetch the stored doc to return _id consistently.
    stored = await story_collection.find_one(
        {
            "user_id": user_id,
            "session_id": session_id,
            "category": category,
            "style": style,
        }
    )

    return {
        "_id": str(stored["_id"]) if stored and stored.get("_id") else None,
        "user_id": user_id,
        "session_id": session_id,
        "category": category,
        "style": style,
        "chapter": chapter,
        "from_cache": from_cache
    }


@router.get("/full/{user_id}/{session_id}")
async def generate_full_story(
    user_id: str,
    session_id: str,
    style: str = Query("conversational", description="Style: conversational, literary, formal, reflective, light_hearted or concise")
):
    """Generate complete life story as single continuous narrative with smooth transitions."""
    story_text, from_cache, _source_fingerprint = await get_or_generate_full_story(
        user_id=user_id,
        session_id=session_id,
        style=style,
    )

    # Preserve previous error semantics
    if story_text.startswith("No ") or story_text.startswith("Error"):
        raise HTTPException(status_code=404, detail=story_text)

    stored = await story_collection.find_one(
        {
            "user_id": user_id,
            "session_id": session_id,
            "category": "__full__",
            "style": style,
        }
    )

    return {
        "_id": str(stored["_id"]) if stored and stored.get("_id") else None,
        "user_id": user_id,
        "session_id": session_id,
        "style": style,
        "story": story_text,
        "from_cache": from_cache,
    }


@router.get("/{user_id}")
async def compile_story(user_id: str, session_id: str = Query(..., description="The session ID to generate story for")):
    """Compile a narrative story for a specific session (legacy endpoint)."""
    story = await narrative_engine.generate_session_story(user_id, session_id)
    if not story or story.startswith("Error"):
        raise HTTPException(status_code=404, detail="No memories found for this user/session.")
    return {"story": story}
          