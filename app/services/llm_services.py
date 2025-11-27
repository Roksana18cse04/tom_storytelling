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
        self.model = "gpt-4o"  # Upgraded for better reasoning
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

    async def _check_story_completeness(self, conversation_history: list, user_input: str, current_question: str) -> dict:
        """
        Use GPT-4o to intelligently check if memory is complete.
        Returns: {"is_complete": bool, "missing": list, "suggestion": str, "is_relevant": bool}
        """
        history_text = "\n".join([
            f"Q: {item['question']}\nA: {item.get('response', '')}" 
            for item in conversation_history[-5:]  # Last 5 exchanges
        ])
        
        prompt = f"""
Analyze this memory conversation and determine if the story feels complete.

Current question: "{current_question}"
Conversation:
{history_text}

Latest response: "{user_input}"

First, check if the latest response is RELEVANT to the current question:
- If user talks about something completely different (e.g., asked about toy but talks about birth), mark as irrelevant

Then check for:
1. Has EMOTION been shared? (feelings, reactions)
2. Has REFLECTION been shared? (meaning, significance)
3. Does the story have a clear ARC? (beginning → middle → end)
4. Are key details present? (who, what, where, when, why, how)

IMPORTANT for suggestion field:
- If incomplete, generate a NEW follow-up question that builds on their answer
- DO NOT repeat the current question: "{current_question}"
- Ask about specific details they mentioned (e.g., "You mentioned the neighborhood was close-knit—what was that like?")
- Focus on missing elements (emotion, reflection, sensory details, etc.)

Respond in JSON format:
{{
  "is_relevant": true/false,
  "is_complete": true/false,
  "has_emotion": true/false,
  "has_reflection": true/false,
  "has_story_arc": true/false,
  "missing_elements": ["list of missing elements"],
  "suggestion": "one NEW follow-up question based on their answer (NOT the core question), or gentle redirect if irrelevant, or empty string if complete"
}}
"""
        
        response = await client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert story analyst. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        import json
        try:
            return json.loads(response.choices[0].message.content)
        except:
            return {"is_complete": False, "suggestion": "Can you tell me more about that?"}

    async def generate_followup(self, user_id: str, session_id: str, user_input: str) -> str:
        """
        Intelligent follow-up generation using GPT-4o.
        Pattern: Core Question → Follow-ups → Completion Check → Next Question
        Target: ~600 words per core question (59 questions × 600 = 35,400 words)
        """
        TARGET_WORDS_PER_QUESTION = 600
        MAX_FOLLOWUPS_PER_CORE = 10  # Dynamic - stops when story is complete
        
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
        
        # Check if user just answered CLOSING_Q1 → Return CLOSING_Q2
        if last_question and "CLOSING_Q1" in last_question:
            print("DEBUG: User answered CLOSING_Q1, returning CLOSING_Q2")
            return "CLOSING_Q2"
        
        # Check if user just answered CLOSING_Q2 → Move to next core question
        if last_question and "CLOSING_Q2" in last_question:
            print("DEBUG: User answered CLOSING_Q2, moving to next core question")
            if unanswered_core:
                next_core = unanswered_core[0]
                print(f"DEBUG: Next core question: {next_core}")
                return next_core
            else:
                print("DEBUG: Phase complete")
                return "PHASE_COMPLETE"
        
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
        
        # Build conversation history for completion check
        conversation_history = []
        all_asked_questions = set()  # Track ALL questions asked (core + follow-ups)
        if current_core_question:
            for mem in category_memories:
                q = mem.get("question")
                if q:
                    all_asked_questions.add(q.lower().strip())
                if mem.get("question") == current_core_question or \
                   (mem.get("question") and mem.get("response")):
                    conversation_history.append({
                        "question": mem.get("question"),
                        "response": mem.get("response", "")
                    })
        
        # Check story completeness using GPT-4o
        completeness = await self._check_story_completeness(conversation_history, user_input, last_question or "")
        
        # Check if we're currently exploring a core question (not if last question was core)
        is_exploring_core = current_core_question is not None
        just_gave_response = user_input and len(user_input.strip()) > 0
        
        # Check if response is relevant to current question
        is_relevant = completeness.get("is_relevant", True)
        
        # If irrelevant, gently redirect to current question
        if not is_relevant and last_question:
            print(f"DEBUG: User gave irrelevant answer, redirecting to: {last_question}")
            redirect_prompt = f"""
The user was asked: "{last_question}"
But they answered with: "{user_input}"

Generate a warm, gentle redirect that:
1. Acknowledges what they shared ("That's interesting about...")
2. Gently brings them back to the original question
3. Uses British phrasing

Example: "That's lovely to hear about your birth in Dhaka. But I'm curious—could we go back to the toy or game you mentioned? What did it look like, and where did you play with it?"

Generate ONE gentle redirect:
"""
            
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_british_system_prompt()},
                    {"role": "user", "content": redirect_prompt}
                ],
                temperature=0.7
            )
            
            redirect = response.choices[0].message.content.strip()
            await memory_service.add_message(user_id, session_id, "Assistant", redirect)
            return redirect
        
        # Check if last question was a confirmation question
        is_confirmation_question = last_question and "anything more" in last_question.lower() and "move on" in last_question.lower()
        
        # If user answered confirmation question, detect their intent
        if is_confirmation_question:
            user_input_lower = user_input.lower().strip()
            word_count = len(user_input.split())
            
            # Check if user wants to move on (short responses with move-on keywords)
            user_wants_to_move_on = (
                any(word in user_input_lower for word in ["no", "move", "next", "skip"]) and
                word_count <= 10
            )
            
            # Check if user is sharing actual content (longer response)
            user_sharing_content = word_count > 10 or ("yes" in user_input_lower and word_count > 3)
            
            if user_wants_to_move_on:
                print("DEBUG: User wants to move on, going to next core question")
                if unanswered_core:
                    next_core = unanswered_core[0]
                    print(f"DEBUG: Next core question: {next_core}")
                    return next_core
                else:
                    print("DEBUG: Phase complete")
                    return "PHASE_COMPLETE"
            elif user_sharing_content:
                print(f"DEBUG: User sharing more content ({word_count} words), treating as normal response")
                pass
            else:
                print("DEBUG: User wants to continue but no content yet, generating follow-up")
                pass
        
        # Check if user just answered a core question (not a follow-up)
        last_question_was_core = last_question in core_questions if last_question else False
        
        # Determine if we need more follow-ups
        needs_more_followups = (
            not completeness.get("is_complete", False) and
            followup_count < MAX_FOLLOWUPS_PER_CORE and
            (total_words_for_core < TARGET_WORDS_PER_QUESTION or depth_score < 60)
        )
        
        # Debug logging
        print(f"DEBUG: last_question={last_question}")
        print(f"DEBUG: last_question_was_core={last_question_was_core}")
        print(f"DEBUG: current_core_question={current_core_question}")
        print(f"DEBUG: followup_count={followup_count}/{MAX_FOLLOWUPS_PER_CORE}")
        print(f"DEBUG: depth_score={depth_score}")
        print(f"DEBUG: total_words_for_core={total_words_for_core}/{TARGET_WORDS_PER_QUESTION}")
        print(f"DEBUG: needs_more_followups={needs_more_followups}")
        print(f"DEBUG: is_exploring_core={is_exploring_core}")
        print(f"DEBUG: just_gave_response={just_gave_response}")
        print(f"DEBUG: answered_core_questions={len(answered_core_questions)}/{len(core_questions)}")
        
        # If user just answered a core question, ALWAYS generate at least one follow-up
        if last_question_was_core and just_gave_response:
            print(f"DEBUG: User just answered core question, generating first follow-up")
            needs_more_followups = True  # Force follow-up generation
        
        # Check if we should generate follow-up or move to next core
        if is_exploring_core and just_gave_response and needs_more_followups:
            print(f"DEBUG: Generating follow-up {followup_count + 1}")
            print(f"DEBUG: Completeness check: {completeness}")
            
            # ALWAYS generate new follow-up (don't trust GPT-4o suggestion to avoid core question repetition)
            
            # Determine follow-up focus
            missing = completeness.get("missing_elements", [])
            if "emotion" in str(missing).lower():
                focus_area = "emotional depth - feelings, reactions, significance"
            elif "reflection" in str(missing).lower():
                focus_area = "deeper reflection - meaning, impact, life lessons"
            elif "story arc" in str(missing).lower():
                focus_area = "narrative flow - what happened next, how it ended"
            elif depth_score < 30:
                focus_area = "basic details - WHO, WHAT, WHERE, WHEN, WHY, HOW"
            elif depth_score < 50:
                focus_area = "sensory details - sights, sounds, smells, atmosphere"
            else:
                focus_area = "deeper context - relationships, significance, connections"
            
            # Get list of already asked questions to avoid repetition
            already_asked = "\n".join([f"- {q}" for q in all_asked_questions])
            
            prompt = f"""
You are a warm British interviewer capturing a complete life story.

Pattern: Core Question → Follow-ups → Completion Check → Next Question

CURRENT CORE QUESTION: "{current_core_question}"
User's latest response: "{user_input}"

Progress:
- Words collected: {total_words_for_core} / {TARGET_WORDS_PER_QUESTION}
- Depth score: {depth_score}/100 ({depth_data['depth_level']})
- Follow-up: {followup_count + 1}
- Story completeness: {completeness.get('is_complete', False)}
- Missing elements: {', '.join(completeness.get('missing_elements', []))}

Focus area: {focus_area}

IMPORTANT RULES:
1. Your follow-up MUST relate ONLY to the current core question above
2. DO NOT ask about new topics or other core questions
3. Build on what they just said about THIS specific topic
4. DO NOT repeat these already asked questions:
{already_asked}

Generate ONE contextual follow-up question that:
1. Directly relates to the CURRENT CORE QUESTION: "{current_core_question}"
2. Builds naturally on their latest response: "{user_input[:100]}..."
3. Addresses missing elements: {', '.join(completeness.get('missing_elements', ['details']))}
4. Uses warm, British phrasing
5. Encourages storytelling (not yes/no questions)

Examples based on focus (all related to current topic):
- Details: "Who else was there with you? Can you paint the scene for me?"
- Sensory: "What do you remember seeing, hearing, or smelling in that moment?"
- Emotion: "How did that make you feel? What was going through your mind?"
- Reflection: "Looking back, what did that experience mean to you?"
- Story arc: "What happened next? How did that moment unfold?"

Generate ONE warm, specific follow-up about "{current_core_question}":
"""
        else:
            # Story feels complete - ask confirmation before moving on
            # BUT only if we have collected reasonable amount of content
            MIN_WORDS_FOR_CONFIRMATION = 300  # At least 50% of target
            MIN_FOLLOWUPS_FOR_CONFIRMATION = 3  # At least 3 follow-ups asked
            
            if (completeness.get("is_complete") and 
                followup_count >= MIN_FOLLOWUPS_FOR_CONFIRMATION and
                total_words_for_core >= MIN_WORDS_FOR_CONFIRMATION):
                print("DEBUG: Story complete with sufficient content, asking CLOSING_Q1")
                return "CLOSING_Q1"
            
            # If story marked complete but insufficient content, continue with follow-ups
            if completeness.get("is_complete") and followup_count < MAX_FOLLOWUPS_PER_CORE:
                print(f"DEBUG: Story marked complete but only {total_words_for_core} words, forcing more follow-ups")
                needs_more_followups = True
                # Generate follow-up (reuse the logic from above)
                missing = completeness.get("missing_elements", [])
                if "emotion" in str(missing).lower():
                    focus_area = "emotional depth - feelings, reactions, significance"
                elif "reflection" in str(missing).lower():
                    focus_area = "deeper reflection - meaning, impact, life lessons"
                elif depth_score < 30:
                    focus_area = "basic details - WHO, WHAT, WHERE, WHEN, WHY, HOW"
                elif depth_score < 50:
                    focus_area = "sensory details - sights, sounds, smells, atmosphere"
                else:
                    focus_area = "deeper context - relationships, significance, connections"
                
                already_asked = "\n".join([f"- {q}" for q in all_asked_questions])
                
                prompt = f"""
You are a warm British interviewer capturing a complete life story.

CURRENT CORE QUESTION: "{current_core_question}"
User's latest response: "{user_input}"

Progress: Only {total_words_for_core}/{TARGET_WORDS_PER_QUESTION} words collected
Focus area: {focus_area}

IMPORTANT: We need more depth. DO NOT repeat these questions:
{already_asked}

Generate ONE warm follow-up that explores {focus_area}:
"""
                
                response = await client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self._get_british_system_prompt()},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7
                )
                
                followup = response.choices[0].message.content.strip()
                await memory_service.add_message(user_id, session_id, "Assistant", followup)
                return followup
            
            # Move to next core question
            print("DEBUG: Moving to next core question")
            if unanswered_core:
                next_core = unanswered_core[0]
                print(f"DEBUG: Next core question: {next_core}")
                # Return ONLY the core question without transition phrases
                # This ensures the question is saved correctly in database
                return next_core
            else:
                print("DEBUG: Phase complete - returning special marker")
                return "PHASE_COMPLETE"
        
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
