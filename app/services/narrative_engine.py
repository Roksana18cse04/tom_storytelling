from app.services.memory_services import memory_service
from openai import AsyncOpenAI
from app.core.config import settings

client = AsyncOpenAI(api_key=settings.openai_api_key)


class NarrativeEngine:
    """
    Converts session-level Q&A histories into a coherent, emotionally engaging story.
    """

    def __init__(self):
        self.model = "gpt-4o-mini"
        self.styles = {
            "memoir": "conversational, first-person, warm and personal",
            "biography": "polished, third-person, formal and structured"
        }

    async def generate_chapter(self, user_id: str, session_id: str, category: str, style: str = "memoir") -> str:
        """Generate a narrative chapter for a specific category."""
        try:
            memories = memory_service.get_category_memories(user_id, session_id, category)
            if not memories:
                return f"No memories found for {category}."

            qa_text = ""
            photo_info = ""
            for m in memories:
                if m.get("response", "").strip():
                    qa_text += f"Q: {m.get('question', '')}\nA: {m.get('response', '')}\n\n"
                    if m.get("photo_caption"):
                        photo_info += f"[Photo Caption: {m.get('photo_caption')}]\n"

            if not qa_text.strip():
                return f"No answered questions in {category}."

            style_desc = self.styles.get(style, self.styles["memoir"])
            chapter_title = category.replace("_", " ").title()

            photo_section = f"\n\nPhotos in this chapter:\n{photo_info}" if photo_info else ""
            
            prompt = f"""
You are a compassionate biographer writing a beautiful life story.

Task: Convert the following Q&A into a flowing narrative chapter.

Chapter: {chapter_title}
Style: {style_desc}

Q&A:
{qa_text}{photo_section}

CRITICAL Instructions:
- ONLY use information explicitly provided in the Q&A above
- DO NOT add fictional details, dates, places, names, or events
- DO NOT make assumptions or create stories beyond what the user shared
- If information is minimal, write a SHORT chapter based ONLY on what's provided
- If there are photo captions, naturally reference them in the story and include the caption as: [Photo: "caption text"]
- Write in first person ("I was born...")
- Remove filler words but keep the person's authentic voice
- Connect memories naturally with transitions
- Make it read like a story, not an interview
- Keep it warm and emotionally engaging
"""

            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a compassionate storyteller who transforms conversations into beautiful narratives."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
            )

            return response.choices[0].message.content.strip()
            
        except Exception as e:
            return f"Error: {str(e)}"

    async def generate_full_story(self, user_id: str, session_id: str, style: str = "memoir") -> dict:
        """Generate complete life story with all chapters."""
        try:
            session_data = memory_service.get_user_memories(user_id, session_id)
            if not session_data:
                return {"error": "No memories found for this session."}

            chapters = {}
            for category in session_data.keys():
                chapter = await self.generate_chapter(user_id, session_id, category, style)
                if not chapter.startswith("No ") and not chapter.startswith("Error"):
                    chapters[category] = chapter

            return {
                "user_id": user_id,
                "session_id": session_id,
                "style": style,
                "chapters": chapters,
                "total_chapters": len(chapters)
            }
            
        except Exception as e:
            return {"error": str(e)}

    async def generate_session_story(self, user_id: str, session_id: str) -> str:
        """Generate a story for a specific session (legacy method)."""
        result = await self.generate_full_story(user_id, session_id)
        if "error" in result:
            return result["error"]
        
        # Combine all chapters
        story = ""
        for category, chapter in result["chapters"].items():
            title = category.replace("_", " ").title()
            story += f"\n\n# {title}\n\n{chapter}"
        
        return story.strip()


# Singleton
narrative_engine = NarrativeEngine()
