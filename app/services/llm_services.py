#app/services/llm_services.py

from openai import OpenAI
from app.services.memory_services import memory_service
from app.core.config import settings
from app.questions.questions import QUESTION_BANK

client = OpenAI(api_key=settings.openai_api_key)


class LLMService:
    def __init__(self):
        self.model = "gpt-4o-mini"

    def generate_followup(self, user_id: str, user_input: str) -> str:
        """Generate a relevant follow-up question based on user input and memory."""
        current_phase = memory_service.get_phase(user_id)
        history_text = memory_service.get_formatted_history(user_id)

        # Collect available questions
        all_used_questions = [
            mem["question"]
            for cat in memory_service.get_user_memories(user_id).values()
            for mem in cat if mem["question"]
        ]
        available_questions = [
            q for q in QUESTION_BANK[current_phase]["questions"]
            if q not in all_used_questions
        ]

        # If phase is exhausted → move to next one
        if not available_questions:
            all_phases = list(QUESTION_BANK.keys())
            next_index = all_phases.index(current_phase) + 1
            if next_index >= len(all_phases):
                return "That’s a wonderful story. Thank you for sharing it!"
            next_phase = all_phases[next_index]
            memory_service.set_phase(user_id, next_phase)
            available_questions = QUESTION_BANK[next_phase]["questions"]

        # LLM prompt
        prompt = f"""
        You are an empathetic interviewer continuing a life story conversation.
        Current phase: {current_phase}.
        Conversation so far:
        {history_text}

        The user's latest response was: "{user_input}"

        Choose ONE question from this list that best follows up naturally:
        {available_questions}

        Respond ONLY with the chosen question text.
        """

        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a compassionate interviewer."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
        )

        followup = response.choices[0].message.content.strip()

        # Save assistant message to memory
        memory_service.add_message(user_id, "Assistant", followup)

        return followup
