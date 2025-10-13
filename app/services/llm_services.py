# #app.services.llm_services.py

# from openai import OpenAI 
# from app.services.memory_services import MemoryService
# from app.core.config import settings

# client= OpenAI(api_key= settings.openai_api_key)
# memory= MemoryService()


# SYSTEM_PROMPT="""
# You are an empathetic interviewer helping a user narrate their life story.

# Start from their early childhood, asking open-ended, reflective questions.
# After each user response, analyze their story and ask a relevant follow-up question
# that deepens emotional or narrative context.

# Never repeat questions. Keep tone warm, conversational, and human.
# """


# class LLMService:
#     def __init__(self):
#         self.model = "gpt-4o-mini"
    
#     def chat(self, user_id: str, user_input: str):
#         history= memory.get_history(user_id)


#         messages= [{"role": "system", "content": SYSTEM_PROMPT}] + history
#         messages.append({"role": "user", "content": user_input})

#         response = client.chat.completions.create(
#             model= self.model,
#             messages= messages,
#             temperature= 0.8,
#         )

#         reply = response.choices[0].message.content
#         memory.add_message(user_id, "user", user_input)
#         memory.add_message(user_id, "assistant", reply)

#         return reply


from openai import OpenAI
from app.services.memory_services import MemoryService
from app.core.config import settings
from app.questions.questions import QUESTION_BANK
import random

client = OpenAI(api_key=settings.openai_api_key)
memory = MemoryService()


class LLMService:
    def __init__(self):
        self.model = "gpt-4o-mini"

    def generate_followup(self, user_id: str, user_input: str) -> str:
        """Decide follow-up question based on context + memory."""
        current_phase = memory.get_phase(user_id)
        history = memory.get_formatted_history(user_id)
        available = [
            q for q in QUESTION_BANK[current_phase]["questions"]
            if q not in [m["content"] for m in memory.get_history(user_id) if m["role"] == "Assistant"]
        ]

        if not available:
            # move to next phase
            all_phases = list(QUESTION_BANK.keys())
            next_index = all_phases.index(current_phase) + 1
            if next_index >= len(all_phases):
                return "That’s a wonderful story. Thank you for sharing it!"
            next_phase = all_phases[next_index]
            memory.set_phase(user_id, next_phase)
            available = QUESTION_BANK[next_phase]["questions"]

        # Let LLM pick the most relevant question semantically
        prompt = f"""
        You are an empathetic interviewer continuing a life story conversation.
        User’s current phase: {current_phase}.
        Chat so far:
        {history}

        The user's last answer was: "{user_input}"

        Choose ONE question from this list that best fits naturally as a follow-up:
        {available}

        Respond ONLY with the question text (no explanation).
        """

        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a life story interviewer."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
        )

        followup = response.choices[0].message.content.strip()

        # Save context
        memory.set_phase(user_id, current_phase)
        memory.add_message(user_id, "Assistant", followup)

        return followup
