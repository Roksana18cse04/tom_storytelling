# app/services/memory_services_mongodb.py

import uuid, datetime, re
from typing import Dict, List
from app.questions.questions import QUESTION_BANK
from app.core.database import memories_collection, user_phases_collection


class MongoMemoryService:
    
    def _generate_snippet(self, response: str, max_length: int = 120) -> str:
        if not response:
            return ""
        sentence = re.split(r'(?<=[.!?]) +', response.strip())[0]
        snippet = sentence.strip()
        if len(snippet) > max_length:
            snippet = snippet[:max_length].rsplit(" ", 1)[0] + "..."
        return snippet

    # ─── Phase Handling ───────────────────────────
    async def get_phase(self, user_id: str, session_id: str) -> str:
        doc = await user_phases_collection.find_one({"user_id": user_id, "session_id": session_id})
        return doc["current_phase"] if doc else None

    async def set_phase(self, user_id: str, session_id: str, phase: str):
        await user_phases_collection.update_one(
            {"user_id": user_id, "session_id": session_id},
            {"$set": {"current_phase": phase, "updated_at": datetime.datetime.now().isoformat()}},
            upsert=True
        )

    def detect_initial_phase(self, text: str) -> str:
        """Detect appropriate starting phase from user's first input."""
        text_lower = text.lower()
        
        stage_map = {
            "childhood": ["childhood", "child", "kid", "young", "elementary", "primary school", "grew up"],
            "teenage years": ["teenage", "teen", "adolescent", "high school", "secondary school", "teenager"],
            "early adulthood": ["early adult", "young adult", "university", "college", "first job", "twenties"],
            "career work": ["career", "work", "job", "professional", "office", "business", "employed"],
            "relationships & family": ["married", "wedding", "spouse", "partner", "children", "parent", "family life"],
            "hobbies & adventures": ["travel", "hobby", "adventure", "trip", "vacation", "journey", "visited", "tour"],
            "home & community": ["moved", "neighborhood", "community", "hometown", "lived in"],
            "challenges & growth": ["difficult", "struggle", "overcome", "challenge", "hardship"],
            "later life & reflections": ["retired", "retirement", "grandchildren", "looking back", "reflection"]
        }
        
        for phase, keywords in stage_map.items():
            if any(kw in text_lower for kw in keywords):
                return phase
        
        vague_intents = ["share", "tell", "talk about", "memory", "story", "life"]
        if any(intent in text_lower for intent in vague_intents) and len(text.split()) < 10:
            return "ASK_USER"
        
        age_match = re.search(r'\b(\d{1,2})\s*(?:years?|yrs?)\s*old\b', text_lower)
        if age_match:
            age = int(age_match.group(1))
            if age <= 12: return "childhood"
            if age <= 19: return "teenage years"
            if age <= 30: return "early adulthood"
            if age <= 50: return "career work"
            return "later life & reflections"
        
        return "ASK_USER"

    # ─── Memory Management ────────────────────────
    async def add_memory(self, user_id: str, session_id: str, category: str,
                   question: str, response: str, photos=None, audio_clips=None, contributors=None, photo_caption=None):
        photos = photos or []
        audio_clips = audio_clips or []
        contributors = contributors or []

        snippet = self._generate_snippet(response)
        
        # Calculate depth score
        from app.services.depth_scorer import depth_scorer
        depth_data = depth_scorer.calculate_depth_score(response) if response else None
        
        entry = {
            "_id": str(uuid.uuid4()),
            "user_id": user_id,
            "session_id": session_id,
            "category": category,
            "question": question,
            "response": response,
            "snippet": snippet,
            "depth_score": depth_data["total_score"] if depth_data else 0,
            "depth_level": depth_data["depth_level"] if depth_data else "Minimal",
            "depth_breakdown": depth_data["breakdown"] if depth_data else None,
            "photos": photos,
            "photo_caption": photo_caption,
            "audio_clips": audio_clips,
            "contributors": contributors,
            "timestamp": datetime.datetime.now().isoformat()
        }

        await memories_collection.insert_one(entry)
        return entry["_id"]

    async def get_user_sessions(self, user_id: str):
        """Return all session IDs for a user."""
        sessions = await memories_collection.distinct("session_id", {"user_id": user_id})
        return sessions

    async def get_user_memories(self, user_id: str, session_id: str):
        """Get all memories grouped by category."""
        memories = await memories_collection.find({"user_id": user_id, "session_id": session_id}).to_list(None)
        
        # Group by category
        grouped = {}
        for mem in memories:
            category = mem.get("category", "uncategorized")
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(mem)
        
        return grouped

    async def get_category_memories(self, user_id: str, session_id: str, category: str):
        memories = await memories_collection.find({
            "user_id": user_id,
            "session_id": session_id,
            "category": category
        }).to_list(None)
        return memories

    async def clear_session(self, user_id: str, session_id: str):
        await memories_collection.delete_many({"user_id": user_id, "session_id": session_id})
        await user_phases_collection.delete_one({"user_id": user_id, "session_id": session_id})

    async def get_formatted_history(self, user_id: str, session_id: str) -> dict:
        session_data = await self.get_user_memories(user_id, session_id)
        formatted_lines = []
        last_question = None
        all_memories = []
        
        for category, memories in session_data.items():
            formatted_lines.append(f"--- {category.upper()} ---")
            for mem in memories:
                formatted_lines.append(f"Q: {mem['question']}")
                formatted_lines.append(f"A: {mem['response']}\n")
                all_memories.append(mem)
        
        # Find last unanswered question (iterate from end)
        for mem in reversed(all_memories):
            if mem.get('question') and not mem.get('response', '').strip():
                last_question = mem['question']
                break
        
        return {
            "formatted_history": "\n".join(formatted_lines),
            "last_question": last_question
        }

    # ─── Progress Tracking ────────────────────────
    async def get_progress(self, user_id: str, session_id: str) -> Dict[str, float]:
        """Calculate completion percentage for each category."""
        session_data = await self.get_user_memories(user_id, session_id)
        progress = {}
        DEFAULT_TARGET = 5
        
        for category in QUESTION_BANK.keys():
            answered = len([m for m in session_data.get(category, []) if m["response"].strip()])
            total_questions = len(QUESTION_BANK[category]["questions"]) if category in QUESTION_BANK else DEFAULT_TARGET
            progress[category] = round((answered / total_questions) * 100, 1) if total_questions > 0 else 0.0
        
        return progress

    async def get_overall_progress(self, user_id: str, session_id: str) -> float:
        """Calculate overall completion percentage."""
        progress = await self.get_progress(user_id, session_id)
        return round(sum(progress.values()) / len(progress), 1) if progress else 0.0

    async def add_message(self, user_id: str, session_id: str, role: str, content: str):
        """Add assistant message to memory."""
        category = await self.get_phase(user_id, session_id)
        if role == "Assistant" and category:
            await self.add_memory(user_id, session_id, category, content, "")


# Singleton instance
mongo_memory_service = MongoMemoryService()
