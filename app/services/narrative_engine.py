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

    def generate_session_story(self, user_id: str, session_id: str) -> str:
        """Generate a story for a specific session of a user."""
        try:
            session_data = memory_service.get_user_memories(user_id, session_id)
            if not session_data:
                return "No memories found for this session."

            phase = memory_service.get_phase(user_id, session_id).capitalize()
            
            qa_text = f"--- {phase.upper()} (Session: {session_id}) ---\n"
            for category, memories in session_data.items():
                qa_text += f"\n[{category.upper()}]\n"
                for m in memories:
                    question = m.get("question", "No question")
                    response = m.get("response", "No response")
                    qa_text += f"Q: {question}\nA: {response}\n"

            return f"Story for {phase} phase:\n\n{qa_text}"
            
        except Exception as e:
            return f"Error: {str(e)}"


# Singleton
narrative_engine = NarrativeEngine()
