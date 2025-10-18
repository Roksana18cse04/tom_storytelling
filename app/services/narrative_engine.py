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

    async def generate_session_story(self, user_id: str, session_id: str) -> str:
        """Generate a story for a specific session of a user."""
        try:
            session_data = memory_service.get_user_memories(user_id, session_id)
            if not session_data:
                return "No memories found for this session."

            phase = memory_service.get_phase(user_id, session_id).capitalize()
            
            qa_text = ""
            for category, memories in session_data.items():
                for m in memories:
                    if m.get("response"):
                        qa_text += f"Q: {m.get('question', '')}\nA: {m.get('response', '')}\n\n"

            prompt = f"""
You are an empathetic biographer writing a beautiful life story.
Convert the following Q&A format into a flowing, natural narrative story.
Keep the tone authentic, warm, and emotionally engaging.

Life Phase: {phase}

Q&A:
{qa_text}

Write in first person, as if the person is narrating their own memory.
Make it read like a story, not an interview.
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


# Singleton
narrative_engine = NarrativeEngine()
