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
from app.services.memory_services_mongodb import mongo_memory_service as memory_service
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

    async def _needs_depth_exploration(self, user_input: str) -> bool:
        """Check if response has enough detail or needs follow-up."""
        # Rich response indicators
        rich_indicators = ["remember", "felt", "looked", "sounded", "smelled", "because", "when", "where", "who"]
        has_detail = any(indicator in user_input.lower() for indicator in rich_indicators)
        word_count = len(user_input.split())
        
        # Needs depth if: short response OR lacks sensory/emotional detail
        return word_count < 20 or not has_detail

    async def _count_followups_for_core_question(self, category_memories: list, core_question: str) -> int:
        """Count how many follow-ups have been asked for a specific core question."""
        count = 0
        found_core = False
        
        for mem in category_memories:
            q = mem.get("question", "")
            if q == core_question:
                found_core = True
            elif found_core:
                # If we found the core question, count subsequent questions until next core
                if q in QUESTION_BANK.get(mem.get("category", ""), {}).get("questions", []):
                    break  # Hit next core question
                count += 1
        
        return count

    async def generate_followup(self, user_id: str, session_id: str, user_input: str) -> str:
        """
        Generate follow-up based on depth score to reach 35,000+ word target.
        Target: ~600 words per core question (59 questions × 600 = 35,400 words)
        """
        TARGET_WORDS_PER_QUESTION = 600  # To reach 35,000+ words total
        MAX_FOLLOWUPS_PER_CORE = 5  # Increased from 2 to get more depth
        
        current_phase = await memory_service.get_phase(user_id, session_id)
        
        # Get conversation history and core questions
        session_data = await memory_service.get_user_memories(user_id, session_id)
        category_memories = session_data.get(current_phase, [])
        core_questions = QUESTION_BANK.get(current_phase, {}).get("questions", [])
        
        # Find which core questions have been ANSWERED (not just asked)
        answered_core_questions = set()
        for mem in category_memories:
            q = mem.get("question")
            r = mem.get("response", "").strip()
            if q in core_questions and r:  # Has response
                answered_core_questions.add(q)
        
        unanswered_core = [q for q in core_questions if q not in answered_core_questions]
        
        # Get last memory
        last_memory = category_memories[-1] if category_memories else None
        last_question = last_memory.get("question") if last_memory else None
        last_response = last_memory.get("response", "").strip() if last_memory else ""
        
        # Find which core question we're currently exploring
        current_core_question = None
        for mem in reversed(category_memories):
            if mem.get("question") in core_questions:
                current_core_question = mem.get("question")
                break
        
        # Count follow-ups for current core question
        followup_count = 0
        if current_core_question:
            followup_count = await self._count_followups_for_core_question(category_memories, current_core_question)
        
        # Calculate total words collected for current core question
        total_words_for_core = 0
        if current_core_question:
            for mem in category_memories:
                if mem.get("question") == current_core_question or \
                   (followup_count > 0 and mem.get("response")):
                    total_words_for_core += len(mem.get("response", "").split())
        
        # Extract context
        self._extract_context(user_id, session_id, user_input)
        
        # Calculate depth score for current response
        from app.services.depth_scorer import depth_scorer
        depth_data = depth_scorer.calculate_depth_score(user_input)
        depth_score = depth_data["total_score"]
        
        # Decision logic based on depth score and word count
        is_core_question = last_question in core_questions if last_question else False
        just_answered_core = is_core_question and last_response
        
        # Determine if we need more follow-ups
        needs_more_followups = (
            total_words_for_core < TARGET_WORDS_PER_QUESTION and 
            followup_count < MAX_FOLLOWUPS_PER_CORE and
            (depth_score < 60 or total_words_for_core < 300)
        )
        
        # Debug logging
        print(f"DEBUG: current_core_question={current_core_question}")
        print(f"DEBUG: followup_count={followup_count}/{MAX_FOLLOWUPS_PER_CORE}")
        print(f"DEBUG: depth_score={depth_score}")
        print(f"DEBUG: total_words_for_core={total_words_for_core}/{TARGET_WORDS_PER_QUESTION}")
        print(f"DEBUG: needs_more_followups={needs_more_followups}")
        print(f"DEBUG: answered_core_questions={len(answered_core_questions)}/{len(core_questions)}")
        
        # Check if we should generate follow-up or move to next core
        if just_answered_core and needs_more_followups:
            # Generate dynamic follow-up to deepen current core question
            print(f"DEBUG: Generating follow-up {followup_count + 1}/{MAX_FOLLOWUPS_PER_CORE}")
            print(f"DEBUG: Target remaining words: {TARGET_WORDS_PER_QUESTION - total_words_for_core}")
            
            # Determine follow-up focus based on depth score
            if depth_score < 30:
                focus_area = "basic details - WHO, WHAT, WHERE, WHEN"
            elif depth_score < 50:
                focus_area = "sensory details - sights, sounds, smells, textures"
            elif depth_score < 70:
                focus_area = "emotional depth - feelings, reactions, significance"
            else:
                focus_area = "deeper reflection - meaning, impact, connections"
            
            prompt = f"""
You are a warm British interviewer helping capture a complete life story.

GOAL: We're aiming for approximately 600 words per core question to create a rich, detailed life story of 35,000+ words.

Core question asked: "{last_question}"
User's response so far: "{user_input}"
Current word count for this question: {total_words_for_core} / {TARGET_WORDS_PER_QUESTION} words
Depth score: {depth_score}/100 ({depth_data['depth_level']})
Follow-up number: {followup_count + 1} of {MAX_FOLLOWUPS_PER_CORE}

Current focus area: {focus_area}

Your task: Generate ONE follow-up question to help reach our word target while enriching the story.

Follow-up strategy based on depth score:
- Low depth (0-30): Ask for basic facts - "Who was with you? Where exactly was this? When did this happen?"
- Medium depth (30-50): Ask for sensory details - "What did you see/hear/smell? Can you describe the atmosphere?"
- Good depth (50-70): Ask for emotions - "How did that make you feel? What was going through your mind?"
- High depth (70+): Ask for reflection - "Looking back, what did that moment mean to you? How did it shape you?"

Examples:
- "Can you tell me more about who was there with you?"
- "What do you remember about how it looked - the colors, the light, the setting?"
- "What sounds or smells come back to you when you think of that moment?"
- "How did you feel in that moment? What emotions do you remember?"
- "Looking back now, what made that experience so significant?"

Generate ONE warm, specific follow-up question:
"""
        else:
            # Move to next core question or check phase completion
            print("DEBUG: Moving to next core question")
            if unanswered_core:
                next_core = unanswered_core[0]
                print(f"DEBUG: Next core question: {next_core}")
                return next_core
            else:
                # All core questions done - check for incomplete phases
                print("DEBUG: Phase complete, checking other phases")
                return "PHASE_COMPLETE"  # Signal to interview route
        
        response = await client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self._get_british_system_prompt()},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )

        followup = response.choices[0].message.content.strip()
        await memory_service.add_message(user_id, session_id, "Assistant", followup)
        return followup


# Singleton
llm_service = LLMService()
