# #app/services/narrative_story
# from app.services.memory_services import memory_service
# from app.services.llm_services import client

# class NarrativeEngine:
#     """
#     Converts all Q&A histories into a continuous, emotionally coherent story.
#     """

#     def __init__(self):
#         self.model = "gpt-4o-mini"

#     async def generate_full_story(self, user_id: str) -> str:
#         """Generate a complete narrative story for the user from all phases."""
#         user_memories = memory_service.get_user_memories(user_id)
#         if not user_memories:
#             return "No memories found for this user."

#         # Combine all Q&A histories in chronological order
#         qa_text = ""
#         for phase, memories in user_memories.items():
#             if memories:
#                 qa_text += f"--- {phase.upper()} ---\n"
#                 for m in memories:
#                     qa_text += f"Q: {m['question']}\nA: {m['response']}\n"
#                 qa_text += "\n"

#         prompt = f"""
#         You are an empathetic biographer writing a life story.
#         Convert the following Q&A format into a flowing, natural story.
#         Keep the tone authentic, reflective, and emotionally coherent.

#         Q&A:
#         {qa_text}

#         Write in first person, as if the user is narrating their life story.
#         Make smooth transitions between phases.
#         """

#         response = client.chat.completions.create(
#             model=self.model,
#             messages=[
#                 {"role": "system", "content": "You are a compassionate storyteller."},
#                 {"role": "user", "content": prompt},
#             ],
#             temperature=0.7,
#         )

#         story_text = response.choices[0].message.content.strip()
#         return story_text


# # Singleton instance
# narrative_engine = NarrativeEngine()

from app.services.memory_services import memory_service
from app.services.llm_services import client


class NarrativeEngine:
    """
    Converts session-level Q&A histories into a coherent, emotionally engaging story.
    """

    def __init__(self):
        self.model = "gpt-4o-mini"

    async def generate_session_story(self, user_id: str, session_id: str) -> str:
        """Generate a story for a specific session of a user."""
        # Fetch memories for this user & session
        session_data = memory_service.get_user_memories(user_id, session_id)
        if not session_data or not isinstance(session_data, dict):
            return "No memories found for this session."

        # Get current phase (e.g., childhood, teenage, adulthood)
        phase = memory_service.get_phase(user_id, session_id).capitalize()

        # Construct chronological Q&A text
        qa_text = f"--- {phase.upper()} (Session: {session_id}) ---\n"
        for category, memories in session_data.items():
            qa_text += f"\n[{category.upper()}]\n"
            for m in memories:
                question = m.get("question", "No question")
                response = m.get("response", "No response")
                qa_text += f"Q: {question}\nA: {response}\n"

        if not qa_text.strip():
            return "No memories found for this session."

        prompt = f"""
        You are an empathetic biographer writing a reflective life story chapter.
        Convert the following Q&A format into a natural, emotionally rich narrative.
        Maintain authenticity, depth, and coherence.

        Q&A:
        {qa_text}

        Write in first person, as if the user is narrating their own story
        during the '{phase}' phase of life.
        """

        # ✅ FIX: Must await AsyncOpenAI calls
        response = await client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a compassionate storyteller."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )

        story_text = response.choices[0].message.content.strip()
        return story_text


# Singleton
narrative_engine = NarrativeEngine()
