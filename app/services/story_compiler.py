# app/services/story_compiler.py

import json, os
from datetime import datetime
from app.services.memory_services import memory_service
from app.services.narrative_engine import narrative_engine

class StoryCompiler:
    """
    Compiles all narrative chapters (childhood → later life) into one coherent life storybook.
    """

    def __init__(self):
        self.story_file = "story_map.json"

    def compile_full_story(self, user_id: str, session_id: str) -> dict:
        """Generate and save a complete storybook for a given user session."""
        session_memories = memory_service.get_user_memories(user_id, session_id)
        if not session_memories:
            return {"error": "No memories found for this user session."}

        story_text = narrative_engine.generate_session_story(user_id, session_id)
        story_data = {
            "user_id": user_id,
            "session_id": session_id,
            "title": f"The Story of {user_id} - Session {session_id}",
            "created_at": datetime.utcnow().isoformat(),
            "story": story_text
        }

        self._save_story(story_data)
        return story_data

    def _save_story(self, story_data: dict):
        """Persist all generated stories in a single JSON file."""
        if os.path.exists(self.story_file):
            with open(self.story_file, "r") as f:
                existing = json.load(f)
        else:
            existing = {}

        key = f"{story_data['user_id']}_{story_data['session_id']}"
        existing[key] = story_data

        with open(self.story_file, "w") as f:
            json.dump(existing, f, indent=2)


# Singleton instance
story_compiler = StoryCompiler()
