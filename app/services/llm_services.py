#app.services.llm_services.py

from openai import OpenAI 
from app.services.memory_services import MemoryService
from app.core.config import settings

client= OpenAI(api_key= settings.openai_api_key)
memory= MemoryService()


SYSTEM_PROMPT="""
You are an empathetic interviewer helping a user narrate their life story.

Start from their early childhood, asking open-ended, reflective questions.
After each user response, analyze their story and ask a relevant follow-up question
that deepens emotional or narrative context.

Never repeat questions. Keep tone warm, conversational, and human.
"""


class LLMService:
    def __init__(self):
        self.model = "gpt-4o-mini"
    
    def chat(self, user_id: str, user_input: str):
        history= memory.get_history(user_id)


        messages= [{"role": "system", "content": SYSTEM_PROMPT}] + history
        messages.append({"role": "user", "content": user_input})

        response = client.chat.completions.create(
            model= self.model,
            messages= messages,
            temperature= 0.8,
        )

        reply = response.choices[0].message.content
        memory.add_message(user_id, "user", user_input)
        memory.add_message(user_id, "assistant", reply)

        return reply