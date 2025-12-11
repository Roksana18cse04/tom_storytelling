# app/api/routes/story.py

from fastapi import APIRouter, HTTPException, Query
from app.services.narrative_engine import narrative_engine
from app.core.database import story_collection
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
    
    # Check if story already exists in database
    existing_story = await story_collection.find_one({
        "user_id": user_id,
        "session_id": session_id,
        "category": category,
        "style": style
    })
    
    # If exists, return from database (cached)
    if existing_story:
        return {
            "_id": str(existing_story['_id']),
            "user_id": user_id,
            "session_id": session_id,
            "category": category,
            "style": style,
            "chapter": existing_story["chapter"],
            "from_cache": True
        }
    
    # Generate new story
    chapter = await narrative_engine.generate_chapter(user_id, session_id, category, style)
    if chapter.startswith("No ") or chapter.startswith("Error"):
        raise HTTPException(status_code=404, detail=chapter)
    
    # Save generated story to database and get inserted ID
    result = await story_collection.insert_one({
        "user_id": user_id,
        "session_id": session_id,
        "category": category,
        "chapter": chapter,
        "style": style,
        "timestamp": datetime.datetime.now().isoformat()
    })
    
    return {
        "_id": str(result.inserted_id),
        "user_id": user_id,
        "session_id": session_id,
        "category": category,
        "style": style,
        "chapter": chapter,
        "from_cache": False
    }


@router.get("/full/{user_id}/{session_id}")
async def generate_full_story(
    user_id: str,
    session_id: str,
    style: str = Query("conversational", description="Style: conversational, literary, formal, reflective, light_hearted or concise")
):
    """Generate complete life story as single continuous narrative with smooth transitions."""
    result = await narrative_engine.generate_full_story(user_id, session_id, style)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    # Combine chapters into single continuous story with AI-generated transitions
    chapters_dict = result["chapters"]
    if not chapters_dict:
        raise HTTPException(status_code=404, detail="No chapters found")
    
    # Create continuous story with smooth transitions
    continuous_story = await narrative_engine.combine_chapters_with_transitions(chapters_dict, style)
    
    return {
        "user_id": user_id,
        "session_id": session_id,
        "style": style,
        "story": continuous_story
    }


@router.get("/{user_id}")
async def compile_story(user_id: str, session_id: str = Query(..., description="The session ID to generate story for")):
    """Compile a narrative story for a specific session (legacy endpoint)."""
    story = await narrative_engine.generate_session_story(user_id, session_id)
    if not story or story.startswith("Error"):
        raise HTTPException(status_code=404, detail="No memories found for this user/session.")
    return {"story": story}
          