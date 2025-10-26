from app.services.memory_services_mongodb import mongo_memory_service as memory_service
from openai import AsyncOpenAI
from app.core.config import settings

client = AsyncOpenAI(api_key=settings.openai_api_key)


class NarrativeEngine:
    """
    Converts session-level Q&A histories into a coherent, emotionally engaging story.
    """

    def __init__(self):
        self.model = "gpt-4o-mini"
        # self.styles = {
        #     "memoir": "conversational, first-person, warm and personal",
        #     "biography": "polished, third-person, formal and structured"
        # }
        self.styles = {
            "conversational": "sounds like spoken storytelling — relaxed, warm, and personal",
            "literary": "rich, descriptive, and expressive — reads like creative nonfiction or a memoir; focuses on atmosphere and imagery",
            "formal": "clear, structured, and factual — presents information with minimal emotion",
            "reflective": "gentle and thoughtful — focuses on meaning, emotion, and insight",
            "light_hearted": "playful and upbeat — highlights humour, mischief, and joyful moments",
            "concise": "streamlined and factual — focuses on clarity and chronology over description"
}

    async def generate_chapter(self, user_id: str, session_id: str, category: str, style: str = "conversational") -> str:
        """Generate a narrative chapter for a specific category with strict authenticity."""
        try:
            memories = await memory_service.get_category_memories(user_id, session_id, category)
            if not memories:
                return f"No memories found for {category}."

            qa_text = ""
            photo_info = ""
            has_substantial_content = False
            
            for m in memories:
                response = m.get("response", "").strip()
                if response:
                    qa_text += f"Q: {m.get('question', '')}\nA: {response}\n\n"
                    if len(response.split()) > 5:
                        has_substantial_content = True
                    # Only include photo if caption is not "Null"
                    caption = m.get("photo_caption", "")
                    if m.get('photos'):
                        photo_path = m.get('photos', [None])[0]
                        if caption and caption.lower() != "null":
                            photo_info += f"[Photo Caption: {caption}]\n[Photo Path: {photo_path}]\n"
                        else:
                            photo_info += f"[Photo Caption: Null]\n[Photo Path: {photo_path}]\n"

            if not qa_text.strip() or not has_substantial_content:
                return f"No substantial content in {category}."

            style_desc = self.styles.get(style, self.styles["conversational"])
            chapter_title = category.replace("_", " ").title()
            photo_section = f"\n\nPhotos in this chapter:\n{photo_info}" if photo_info else ""
            
            # Style-specific instructions
            style_instructions = {
                "conversational": "Use friendly, informal tone with first-person voice. Keep sentences short and natural. Include emotional asides like 'I remember thinking...' Sound like the user is talking directly to family.",
                "literary": "Use rich, descriptive language with varied sentence lengths. Focus on sensory details and atmosphere. Create emotionally immersive scenes with figurative expressions.",
                "formal": "Use clear, structured language. Present information factually with minimal emotion. Use complete sentences, avoid contractions, maintain precise word choice.",
                "reflective": "Use gentle, thoughtful tone with slower pacing. Include introspective questions like 'I often wonder...' Focus on emotional nuance and meaning over time.",
                "light_hearted": "Use playful, upbeat tone highlighting humor and joy. Include lively verbs and cheerful anecdotes. May use mild exaggeration for color.",
                "concise": "Use short sentences with minimal adjectives. Focus on direct sequencing ('First... then...'). Prioritize clarity and chronology over description."
            }
            
            prompt = f"""
You are a compassionate biographer helping preserve authentic life stories.

Task: Convert the following Q&A into a flowing narrative chapter.

Chapter: {chapter_title}
Style: {style_desc}

Q&A:
{qa_text}{photo_section}

CRITICAL AUTHENTICITY RULES - FOLLOW STRICTLY:

1. PRESERVE USER'S EXACT VOICE
   - Use their EXACT words, phrases, and expressions wherever possible
   - Keep their natural phrasing, humor, rhythm, and quirks
   - Edit ONLY for readability (remove filler words like "um", "uh")
   - DO NOT enhance, embellish, or "improve" their language

2. ABSOLUTE FIDELITY TO FACTS
   - ONLY use information EXPLICITLY stated in the Q&A
   - You may add ONLY small connectors like "and", "then", "so" for flow
   - NEVER add:
     * Details not mentioned (sounds, sights, thoughts, feelings)
     * Interpretations or assumptions
     * Concluding reflections not stated by user
     * Sensory details beyond what user described
   - If user said "crisp air" - use "crisp air", don't add "gentle breeze"
   - If user said "breathless" - use "breathless", don't add "hearts pounding"

3. STYLE APPLICATION
   {style_instructions.get(style, style_instructions['conversational'])}
   - Apply style through STRUCTURE and FLOW, not by adding content

4. PHOTO INTEGRATION
   - If caption is "Null": Format as [Image: path][Caption: \"Null\"]
   - If caption exists: Format as [Image: path][Caption: \"actual caption\"]
   - Place photo reference where it fits contextually
   - DO NOT describe the photo beyond what user said

5. LENGTH AND COMPLETENESS
   - If user gave short answer, write SHORT chapter
   - DO NOT pad with invented reflections or conclusions
   - End naturally where user's story ends

GOAL: Transform Q&A format into narrative while keeping EVERY word authentic.

DO: Remove "Q:" and "A:", add small connectors, improve flow
DON'T: Add ANY details, thoughts, feelings, or descriptions not explicitly stated
"""

            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a compassionate biographer who honors authenticity above all. You preserve the user's natural voice while shaping their words into coherent narrative form."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.6,
            )

            return response.choices[0].message.content.strip()
            
        except Exception as e:
            return f"Error: {str(e)}"

    async def generate_full_story(self, user_id: str, session_id: str, style: str = "conversational") -> dict:
        """Generate complete life story with all chapters."""
        try:
            session_data = await memory_service.get_user_memories(user_id, session_id)
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
