# #app/services/llm_services.py

# from openai import OpenAI
# from app.services.memory_services import memory_service
# from app.core.config import settings
# from app.questions.questions import QUESTION_BANK

# client = OpenAI(api_key=settings.openai_api_key)


# class LLMService:
#     def __init__(self):
#         self.model = "gpt-4o-mini"

#     def generate_followup(self, user_id: str, user_input: str) -> str:
#         """Generate a relevant follow-up question based on user input and memory."""
#         current_phase = memory_service.get_phase(user_id)
#         history_text = memory_service.get_formatted_history(user_id)

#         # Collect available questions
#         all_used_questions = [
#             mem["question"]
#             for cat in memory_service.get_user_memories(user_id).values()
#             for mem in cat if mem["question"]
#         ]
#         available_questions = [
#             q for q in QUESTION_BANK[current_phase]["questions"]
#             if q not in all_used_questions
#         ]

#         # If phase is exhausted → move to next one
#         if not available_questions:
#             all_phases = list(QUESTION_BANK.keys())
#             next_index = all_phases.index(current_phase) + 1
#             if next_index >= len(all_phases):
#                 return "That’s a wonderful story. Thank you for sharing it!"
#             next_phase = all_phases[next_index]
#             memory_service.set_phase(user_id, next_phase)
#             available_questions = QUESTION_BANK[next_phase]["questions"]

#         # LLM prompt
#         prompt = f"""
#         You are an empathetic interviewer continuing a life story conversation.
#         Current phase: {current_phase}.
#         Conversation so far:
#         {history_text}

#         The user's latest response was: "{user_input}"

#         Choose ONE question from this list that best follows up naturally:
#         {available_questions}

#         Respond ONLY with the chosen question text.
#         """

#         response = client.chat.completions.create(
#             model=self.model,
#             messages=[
#                 {"role": "system", "content": "You are a compassionate interviewer."},
#                 {"role": "user", "content": prompt},
#             ],
#             temperature=0.5,
#         )

#         followup = response.choices[0].message.content.strip()

#         # Save assistant message to memory
#         memory_service.add_message(user_id, "Assistant", followup)

#         return followup
# app/services/llm_services.py

from openai import AsyncOpenAI
from app.services.memory_services import memory_service
from app.core.config import settings
from app.questions.questions import QUESTION_BANK
import re

client = AsyncOpenAI(api_key=settings.openai_api_key)


class LLMService:
    def __init__(self):
        self.model = "gpt-4o-mini"
        self.context_cache = {}  # Store user context (names, ages, interests)

    def _is_vague_response(self, text: str) -> bool:
        """Detect if response is too short or vague."""
        words = text.split()
        return len(words) < 5 or text.lower() in ["yes", "no", "maybe", "ok", "hi", "hello"]

    def _extract_context(self, user_id: str, session_id: str, text: str):
        """Extract and cache important context like names, ages, places."""
        key = f"{user_id}_{session_id}"
        if key not in self.context_cache:
            self.context_cache[key] = {"names": set(), "places": set(), "interests": set()}
        
        # Simple extraction (can be enhanced)
        words = text.split()
        for i, word in enumerate(words):
            if word.lower() in ["brother", "sister", "mother", "father", "friend"] and i + 1 < len(words):
                self.context_cache[key]["names"].add(words[i + 1])

    def _detect_life_stage(self, text: str) -> str:
        """Detect which life stage user is talking about from their response."""
        text_lower = text.lower()
        
        # Keywords for each life stage
        stage_keywords = {
            "childhood": ["childhood", "child", "kid", "young", "elementary", "primary school", "grew up"],
            "teenage years": ["teenage", "teen", "adolescent", "high school", "secondary school", "teenager"],
            "early adulthood": ["early adult", "young adult", "university", "college", "first job", "twenties"],
            "career work": ["career", "work", "job", "professional", "office", "business", "employed"],
            "relationships & family": ["married", "wedding", "spouse", "partner", "children", "parent", "family life"],
            "hobbies & adventures": ["travel", "hobby", "adventure", "trip", "vacation", "journey", "visited", "tour"],
            "home & community": ["moved", "neighborhood", "community", "hometown", "lived in"],
            "challenges & growth": ["difficult", "struggle", "overcome", "challenge", "hardship"],
            "later life & reflections": ["retired", "retirement", "grandchildren", "looking back", "reflection"]
        }
        
        # Check for explicit mentions
        if "adulthood" in text_lower or "adult" in text_lower:
            if "early" in text_lower or "young" in text_lower:
                return "early adulthood"
            return "early adulthood"  # Default adult category
        
        # Check keywords
        for stage, keywords in stage_keywords.items():
            if any(kw in text_lower for kw in keywords):
                return stage
        
        return None  # No stage detected

    def _get_british_system_prompt(self) -> str:
        """British interviewer personality."""
        return """You are a warm, thoughtful British interviewer helping someone record their life story.
        
Your tone is:
        - Gentle and encouraging, never over-enthusiastic
        - Respectful and curious, like a trusted companion
        - Natural and conversational, not formal or casual
        - Empathetic - you reflect back emotions when appropriate
        
You ask open-ended questions that invite detail. If someone gives a brief answer, you gently nudge them to elaborate.
You use British phrasing naturally (e.g., "That sounds special", "What do you remember about...").
You never rush - you give space for reflection."""

    async def generate_followup(self, user_id: str, session_id: str, user_input: str) -> str:
        """
        Generate a context-aware follow-up question with British interviewer personality.
        """
        current_phase = memory_service.get_phase(user_id, session_id)
        
        # Detect if user is talking about a different life stage
        detected_stage = self._detect_life_stage(user_input)
        if detected_stage and detected_stage != current_phase:
            # Switch to the detected stage
            memory_service.set_phase(user_id, session_id, detected_stage)
            current_phase = detected_stage
        
        history_text = memory_service.get_formatted_history(user_id, session_id)
        sample_questions = QUESTION_BANK.get(current_phase, {}).get("questions", [])
        
        # Extract context from user input
        self._extract_context(user_id, session_id, user_input)
        
        # Check if response is vague
        is_vague = self._is_vague_response(user_input)
        
        if is_vague:
            prompt = f"""
            The user gave a brief response: "{user_input}"
            
            Current conversation phase: {current_phase}
            Recent conversation:
            {history_text[-500:] if len(history_text) > 500 else history_text}
            
            Generate a gentle follow-up that encourages them to share more detail.
            Examples: "That sounds special. Who was with you that day?" or "What emotions do you remember feeling?"
            
            Respond with ONE warm, specific follow-up question only.
            """
        else:
            prompt = f"""
            Current life story phase: {current_phase}
            
            Conversation so far:
            {history_text}
            
            User's latest response: "{user_input}"
            
            Sample questions for this phase:
            {sample_questions[:5]}
            
            Based on what they've shared, generate ONE natural follow-up question that:
            - Builds on their response
            - Invites deeper reflection or moves the story forward
            - Feels like a caring friend asking, not an interrogation
            
            Respond with the question only.
            """

        response = await client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self._get_british_system_prompt()},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )

        followup = response.choices[0].message.content.strip()
        memory_service.add_message(user_id, session_id, "Assistant", followup)
        return followup


# Singleton
llm_service = LLMService()
