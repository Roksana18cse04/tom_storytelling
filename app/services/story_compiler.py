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

    def compile_full_story(self, user_id: str) -> dict:
        """Generate and save a complete storybook for a given user."""
        user_memories = memory_service.get_user_memories(user_id)
        if not user_memories:
            return {"error": "No memories found for this user."}

        story_map = {}
        compiled_story = []

        for phase in user_memories.keys():
            chapter_text = narrative_engine.generate_chapter(user_id, phase)
            story_map[phase] = chapter_text
            compiled_story.append(f"## {phase.title()}\n\n{chapter_text}\n")

        full_story_text = "\n---\n".join(compiled_story)
        story_data = {
            "user_id": user_id,
            "title": f"The Story of {user_id}",
            "created_at": datetime.utcnow().isoformat(),
            "chapters": story_map,
            "full_story": full_story_text
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

        existing[story_data["user_id"]] = story_data

        with open(self.story_file, "w") as f:
            json.dump(existing, f, indent=2)


# Singleton instance
story_compiler = StoryCompiler()
