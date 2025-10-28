# app/api/routes/depth_stats.py

from fastapi import APIRouter, HTTPException
from app.services.memory_services_mongodb import mongo_memory_service as memory_service

router = APIRouter()

@router.get("/depth_stats/{user_id}/{session_id}")
async def get_depth_statistics(user_id: str, session_id: str):
    """Get depth score statistics and word count progress for a session"""
    try:
        from app.questions.questions import QUESTION_BANK
        
        memories = await memory_service.get_user_memories(user_id, session_id)
        
        if not memories:
            raise HTTPException(status_code=404, detail="No memories found")
        
        total_memories = 0
        total_depth = 0
        total_words = 0
        depth_distribution = {
            "Minimal": 0,
            "Basic": 0,
            "Moderate": 0,
            "Rich": 0,
            "Exceptional": 0
        }
        category_depths = {}
        
        for category, mems in memories.items():
            category_total_depth = 0
            category_total_words = 0
            category_count = 0
            
            for mem in mems:
                if mem.get("response") and len(mem.get("response", "").strip()) > 5:
                    depth_score = mem.get("depth_score", 0)
                    depth_level = mem.get("depth_level", "Minimal")
                    word_count = len(mem.get("response", "").split())
                    
                    total_memories += 1
                    total_depth += depth_score
                    total_words += word_count
                    depth_distribution[depth_level] += 1
                    
                    category_total_depth += depth_score
                    category_total_words += word_count
                    category_count += 1
            
            if category_count > 0:
                core_questions_count = len(QUESTION_BANK.get(category, {}).get("questions", []))
                target_words = core_questions_count * 600
                
                word_progress = round((category_total_words / target_words * 100), 1) if target_words > 0 else 0
                
                category_depths[category] = {
                    "average_depth": round(category_total_depth / category_count, 1),
                    "memory_count": category_count,
                    "total_words": category_total_words,
                    "target_words": target_words,
                    "word_progress_percentage": word_progress,
                    "status": "complete" if word_progress >= 100 else "in_progress"
                }
        
        avg_depth = round(total_depth / total_memories, 1) if total_memories > 0 else 0
        
        # Calculate total target (59 core questions × 600 words = 35,400 words MINIMUM)
        total_target_words = 35400
        word_progress_percentage = round((total_words / total_target_words * 100), 1)
        
        # Quality rating
        if avg_depth >= 70:
            quality_rating = "Exceptional"
        elif avg_depth >= 50:
            quality_rating = "Excellent"
        elif avg_depth >= 35:
            quality_rating = "Good"
        else:
            quality_rating = "Developing"
        
        # Story completion status
        if word_progress_percentage >= 100:
            story_status = "complete"
            status_message = f"Congratulations! You've reached the target. Your story has {total_words:,} words."
        elif word_progress_percentage >= 75:
            story_status = "nearly_complete"
            status_message = f"Almost there! {total_target_words - total_words:,} words remaining."
        elif word_progress_percentage >= 50:
            story_status = "halfway"
            status_message = f"Great progress! You're halfway through."
        else:
            story_status = "in_progress"
            status_message = f"Keep going! {total_target_words - total_words:,} words remaining."
        
        return {
            "user_id": user_id,
            "session_id": session_id,
            "total_memories": total_memories,
            "average_depth_score": avg_depth,
            "quality_rating": quality_rating,
            "depth_distribution": depth_distribution,
            "category_depths": category_depths,
            "word_count_progress": {
                "current_words": total_words,
                "target_words": total_target_words,
                "progress_percentage": word_progress_percentage,
                "remaining_words": max(0, total_target_words - total_words),
                "status": story_status,
                "message": status_message
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
