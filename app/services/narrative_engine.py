from app.services.memory_services_mongodb import mongo_memory_service as memory_service
from openai import AsyncOpenAI
from app.core.config import settings

client = AsyncOpenAI(api_key=settings.openai_api_key)


class NarrativeEngine:
    """
    Converts session-level Q&A histories into a coherent, emotionally engaging story.
    """

    def __init__(self):
        # Use GPT-4o for better style differentiation
        self.model = "gpt-4o"
        
        # Style-specific models and temperatures (lower for authenticity)
        self.style_config = {
            "conversational": {"model": "gpt-4o", "temperature": 0.1},  # Almost deterministic
            "literary": {"model": "gpt-4o", "temperature": 0.2},        # Very low - only rearrange
            "formal": {"model": "gpt-4o", "temperature": 0.2},          # Very structured
            "reflective": {"model": "gpt-4o", "temperature": 0.4},      # Thoughtful but controlled
            "light_hearted": {"model": "gpt-4o", "temperature": 0.5},   # Playful but not wild
            "concise": {"model": "gpt-4o", "temperature": 0.3}          # Precise
        }
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
                    # Include photo with correct placeholder format
                    caption = m.get("photo_caption", "")
                    if m.get('photos'):
                        photo_path = m.get('photos', [None])[0]
                        if caption and caption.lower() != "null":
                            photo_info += f"[Image: {photo_path}]\n[Caption: \"{caption}\"]\n\n"
                        else:
                            photo_info += f"[Image: {photo_path}]\n[Caption: \"Null\"]\n\n"

            if not qa_text.strip() or not has_substantial_content:
                return f"No substantial content in {category}."

            chapter_title = category.replace("_", " ").title()
            photo_section = f"\n\nPhotos in this chapter:\n{photo_info}" if photo_info else ""
            
            # Get style-specific configuration
            style_cfg = self.style_config.get(style, self.style_config["conversational"])
            model = style_cfg["model"]
            temperature = style_cfg["temperature"]
            
            # Get style-specific prompt
            prompt = self._get_style_prompt(style, chapter_title, qa_text, photo_section)

            # Get style-specific system message
            system_message = self._get_system_message(style)
            
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
            )

            return response.choices[0].message.content.strip()
            
        except Exception as e:
            return f"Error: {str(e)}"

    def _get_system_message(self, style: str) -> str:
        """Get style-specific system message"""
        messages = {
            "conversational": "You are a biographer. ABSOLUTE RULE: Copy user's EXACT words. DO NOT add ANY descriptive words. BANNED: lush, dotted, scattered, nestled, surrounded, woven, vibrant, amid, narrow, winding, thatched. You may ONLY remove Q&A format and add: 'and', 'then', 'so'. If you add even ONE word user didn't say, you FAIL.",
            "literary": "You are a literary biographer. CRITICAL RULE: You may ONLY rearrange user's EXACT words. DO NOT add ANY new words except: 'and', 'then', 'but', 'as', 'when', 'where'. BANNED: nestled, dotted, scattered, lush, vibrant, symphony, tapestry, embrace. If you add ANY banned word or ANY adjective/verb user didn't say, you FAIL. Use ONLY user's words in better order.",
            "formal": "You are a professional biographer. CRITICAL: Present user's information factually with clear structure. Use third-person (The subject, He/She) or neutral tone. No embellishment. Preserve exact facts stated.",
            "reflective": "You are a thoughtful biographer. CRITICAL: Use user's own reflections and emotions. Add introspective pacing and time perspective shifts (e.g., 'Looking back...'), but never invent feelings or insights they didn't express. Use ONLY their words.",
            "light_hearted": "You are a warm storyteller. CRITICAL: Emphasize user's humor and joy using their own words. Keep playful tone but never exaggerate beyond their natural expression. Use ONLY what they said.",
            "concise": "You are a biographer creating brief narratives. CRITICAL: Use user's exact words in shortest form. Remove all unnecessary adjectives. Focus on key facts only. 50% shorter than original."
        }
        return messages.get(style, messages["conversational"])
    
    def _get_style_prompt(self, style: str, chapter_title: str, qa_text: str, photo_section: str) -> str:
        """Get style-specific prompt with examples"""
        
        # Core authenticity rules
        if style == "formal":
            core_rules = f"""
Chapter: {chapter_title}

Q&A:
{qa_text}{photo_section}

🔒 AUTHENTICITY RULES (CRITICAL - NEVER VIOLATE):

1. FACTUAL ACCURACY
   - ONLY use information EXPLICITLY stated in Q&A.
   - DO NOT invent details, emotions, or events.

2. FORMAL VOICE
   - CONVERT "I" to "The subject" or "He/She".
   - Remove conversational quirks.
   - Use objective, professional language.

3. PHOTO INTEGRATION (CRITICAL - MUST INCLUDE)
   - You MUST include ALL photo placeholders in the story
   - Format: [Image: path][Caption: "text"] or [Caption: "Null"]
   - Place them where contextually appropriate in the narrative
   - Keep the EXACT format - do not modify the placeholder syntax
"""
        else:
            core_rules = f"""
Chapter: {chapter_title}

Q&A:
{qa_text}{photo_section}

🔒 AUTHENTICITY RULES (CRITICAL - NEVER VIOLATE):

1. PRESERVE USER'S EXACT VOICE
   - Use their EXACT words, phrases, expressions
   - Keep their natural phrasing, humor, rhythm, quirks
   - Edit ONLY for readability (remove "um", "uh")
   - DO NOT enhance, embellish, or "improve" their language

2. ABSOLUTE FIDELITY TO FACTS
   - ONLY use information EXPLICITLY stated in Q&A
   - Add ONLY small connectors: "and", "then", "so"
   - NEVER add: details, emotions, interpretations, sensory info not mentioned
   - If user said "crisp air" → use "crisp air" (don't add "gentle breeze")

3. PHOTO INTEGRATION (CRITICAL - MUST INCLUDE)
   - You MUST include ALL photo placeholders in the story
   - Format: [Image: path][Caption: "text"] or [Caption: "Null"]
   - Place them where contextually appropriate in the narrative
   - Keep the EXACT format - do not modify the placeholder syntax
   - Don't describe photos beyond user's words
"""
        
        # Style-specific instructions with examples
        if style == "conversational":
            return core_rules + """
📝 STYLE: Conversational (Spoken Storytelling)

⚠️ CRITICAL: Keep it SIMPLE and NATURAL - like the user is talking to family!

🚫 BANNED WORDS (DO NOT USE):
- lush, dotted, scattered, nestled, woven, vibrant, amid, throughout, surrounded
- narrow, winding, thatched, embrace, tapestry, symphony, perfume, kissed
- painted, adorned, graced, vast, distant, soft, gentle, faint
- ANY adjective or verb user didn't explicitly say

✅ INSTRUCTIONS:
1. USE SHORT SENTENCES. (Avoid long run-on sentences with "and").
2. PREFER FULL STOPS (.) over connectors.
3. You can add: "and", "then", "so", "but" - BUT USE SPARINGLY!
4. EVERYTHING ELSE = user's EXACT words.

⚠️ CRITICAL: If user said "green fields" → write "green fields" (NOT "surrounded by green fields")

HOW TO WRITE:
- First-person, warm, personal tone
- Break long thoughts into smaller chunks.
- Use ONLY user's exact words - don't make them "prettier"

EXAMPLE 1:
User said: "I was born in a village. It had green fields. We lived in mud houses."

✅ CORRECT: "I was born in a village. It had green fields. We lived in mud houses."

❌ WRONG (Run-on): "I was born in a village and it had green fields and we lived in mud houses."

❌ WRONG (Flowery): "The village was surrounded by lush green fields..."

NOW WRITE - KEEP IT SIMPLE AND PUNCHY!
"""
        
        elif style == "literary":
            return core_rules + """
📝 STYLE: Literary (Creative Nonfiction)

⚠️ CRITICAL: Rich STRUCTURE, NOT invented content!

🚫 ZERO TOLERANCE - BANNED WORDS:
- nestled, embrace, tapestry, sentinels, symphony, perfume, kissed, dotted, scattered
- woven, painted, adorned, graced, vast, lush, vibrant, amid, throughout
- ANY adjective or verb user didn't explicitly say

⚠️ YOU CAN ONLY ADD: and, then, but, as, when, where, which, that
⚠️ EVERYTHING ELSE must be user's EXACT words

HOW TO WRITE:
- Rearrange user's EXACT words for better flow
- Vary sentence lengths (short + long)
- Use ONLY user's adjectives and verbs
- Add rhythm through sentence structure ONLY

WHAT YOU CAN DO:
✅ Rearrange: "I was born in 2001 in a village" → "In 2001, I was born in a village"
✅ Combine: User's separate sentences into flowing paragraphs
✅ Emphasize: User's own sensory words (if they said them)

WHAT YOU CANNOT DO:
❌ Add ANY adjectives user didn't use
❌ Add ANY verbs user didn't use ("dotted", "nestled", "graced")
❌ Add poetic phrases
❌ Replace user's simple words with fancy ones

EXAMPLE:
User said: "I was born in a village under Sreepur Upazila in 2001. It had green fields and small mud houses."

✅ CORRECT: "In 2001, I was born in a village under Sreepur Upazila. Green fields and small mud houses defined the landscape."

❌ WRONG: "Nestled under Sreepur Upazila, the village where I was born in 2001 was dotted with small mud houses amid lush green fields."
(Added: "nestled", "dotted", "amid", "lush" - NOT user's words!)

USE ONLY USER'S EXACT WORDS - just arrange them beautifully!
"""
        
        elif style == "formal":
            return core_rules + """
📝 STYLE: Formal (Biographical Record)

HOW TO WRITE:
- Third-person (The subject, He/She) OR neutral first-person
- Clear, structured, factual
- Minimal emotion
- No contractions (use "was not" not "wasn't")
- Precise word choice
- CHANGE PRONOUNS: "I" -> "The subject" or "He/She"

EXAMPLE TRANSFORMATION:
Q: Tell me about your siblings.
A: I have two siblings. My sister Ayesha is three years older, and my brother Rafi is two years younger.

✅ CORRECT OUTPUT:
"The subject has two siblings: Ayesha, three years senior, and Rafi, two years junior. Family structure consisted of three children with the subject positioned as the middle child."

❌ WRONG (too conversational):
"Yes, I have two siblings. My elder sister is Ayesha, who's three years older than me..."

NOW WRITE THE CHAPTER:
"""
        
        elif style == "reflective":
            return core_rules + """
📝 STYLE: Reflective (Thoughtful Introspection)

HOW TO WRITE:
- Gentle, contemplative tone
- Slower pacing
- Include introspective questions IF user expressed them
- Focus on meaning and emotional nuance
- Time perspective shifts ("Looking back...", "In retrospect...")
- You MAY add reflective framing words (e.g., "It seems...", "Looking back...") even if user didn't say them, but DO NOT invent the core feeling.

EXAMPLE TRANSFORMATION:
Q: What does that memory mean to you?
A: It reminds me of simpler times. I was carefree back then.

✅ CORRECT OUTPUT:
"Looking back, that memory carries me to simpler times—a period when I was carefree, unburdened by the complexities that would come later. I often wonder what it was about those days that felt so light."

❌ WRONG (invented reflection):
"That memory carries me back to simpler times. Perhaps it was the innocence of youth, or the way sunlight filtered through the trees, but those days held a magic I've spent a lifetime trying to recapture."
(Added: "innocence of youth", "sunlight through trees", "magic" - NOT stated!)

NOW WRITE THE CHAPTER:
"""
        
        elif style == "light_hearted":
            return core_rules + """
📝 STYLE: Light-hearted (Playful & Upbeat)

HOW TO WRITE:
- Playful, cheerful tone
- Emphasize humor and joy
- Lively verbs
- Mild exaggeration ONLY if user's tone suggests it
- Keep warmth and fun
- AVOID overly flowery metaphors unless user used them.

EXAMPLE TRANSFORMATION:
Q: What did you and your brother do?
A: We'd run out the moment it rained. My sister would yell at us to come back.

✅ CORRECT OUTPUT:
"The moment rain hit, we'd bolt—my sister yelling after us to come back, but we were already gone, splashing through every puddle we could find."

❌ WRONG (over-exaggerated):
"We were unstoppable rain warriors! The second those first drops fell, we'd bolt like lightning—my sister's protests fading into the distance as we conquered every muddy puddle like it was our sacred mission!"
(Too much exaggeration not in user's tone)

NOW WRITE THE CHAPTER:
"""
        
        elif style == "concise":
            return core_rules + """
📝 STYLE: Concise (Streamlined & Factual)

HOW TO WRITE:
- Short, direct sentences
- Minimal adjectives
- Chronological sequencing ("First... then...")
- 50% SHORTER than conversational
- Focus on key facts only

EXAMPLE TRANSFORMATION:
Q: Describe your childhood home.
A: We lived in a small house near the market. It had two bedrooms and a courtyard where we played. The walls were painted blue, and there was a mango tree in the yard.

✅ CORRECT OUTPUT:
"We lived in a small house near the market. Two bedrooms, one courtyard. Blue walls. A mango tree stood in the yard where we played."

❌ WRONG (too descriptive):
"We lived in a small house near the bustling market. It had two cozy bedrooms and a courtyard where we spent countless hours playing. The walls were painted a cheerful blue, and a magnificent mango tree stood in the yard."
(Added: "bustling", "cozy", "countless hours", "cheerful", "magnificent" - too much!)

NOW WRITE THE CHAPTER:
"""
        
        else:
            return core_rules + "\nNOW WRITE THE CHAPTER:\n"
    
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

    async def combine_chapters_with_transitions(self, chapters_dict: dict, style: str = "conversational") -> str:
        """Combine separate chapters into one continuous story with phase headers and smooth transitions."""
        if not chapters_dict:
            return "No story content available."
        
        # Prepare chapters text
        chapters_text = ""
        for category, content in chapters_dict.items():
            title = category.replace("_", " ").title()
            chapters_text += f"\n\n=== {title} ===\n{content}"
        
        # Get style configuration
        style_cfg = self.style_config.get(style, self.style_config["conversational"])
        model = style_cfg["model"]
        temperature = style_cfg["temperature"]
        
        # AI prompt to combine with transitions and phase headers
        prompt = f"""
🚨 MANDATORY FORMATTING RULES - FAILURE TO FOLLOW = REJECTION 🚨

You have separate life phase chapters. Combine them into ONE continuous flowing story with phase headers.

Style: {self.styles.get(style, self.styles['conversational'])}

🔴 ABSOLUTE REQUIREMENTS (NO EXCEPTIONS):

1. PHASE HEADERS: Start each phase with name as header ("Childhood:", "Teenage Years:", "Early Adulthood:")

2. PARAGRAPH LENGTH LIMIT: 
   ⚠️ MAXIMUM 3 LINES PER PARAGRAPH
   ⚠️ After 3 lines, you MUST start new paragraph
   ⚠️ Each distinct memory/idea = separate paragraph

3. SENTENCE LENGTH LIMIT:
   ⚠️ MAXIMUM 20 words per sentence
   ⚠️ If sentence has 3+ clauses, SPLIT into multiple sentences
   ⚠️ Mix: 50% short (5-10 words), 50% medium (11-20 words)

4. BANNED REPETITIVE WORDS (DO NOT REPEAT):
   🚫 "sunlight filtering/streaming" - use ONCE only
   🚫 "quiet hum" - use ONCE only  
   🚫 "smell of..." pattern - use ONCE only
   🚫 "faint scent/aroma" - use ONCE only
   🚫 If you used a sensory word, find DIFFERENT imagery next time

5. SPECIFIC TRANSITIONS (NOT GENERIC):
   ✅ Reference actual previous content: "The curiosity of childhood evolved into teenage self-discovery"
   ❌ Generic phrases: "As years passed", "Time moved on"

6. MANDATORY REFLECTION:
   ⚠️ EVERY phase MUST end with reflection paragraph about lessons learned

7. PRESERVE EXACT CONTENT:
   ⚠️ Keep ALL facts, details, photo placeholders [Image: path][Caption: "text"]
   ⚠️ Only rearrange and break into shorter paragraphs

8. SENTENCE FLOW (AVOID CHOPPY LISTS):
   ⚠️ Link related sentences with "and", "while", "as" instead of choppy periods
   ❌ WRONG: "I was in charge of my schedule, finances, and routines. Excitement and apprehension filled those early days."
   ✅ CORRECT: "I was in charge of my schedule, finances, and routines, and excitement and apprehension filled those early days."

9. PERSONAL REFLECTIONS:
   ⚠️ End each phase with personal, conversational reflection using "I", "who I am", "how I approach"
   ❌ WRONG: "These experiences continue to shape my journey."
   ✅ CORRECT: "These experiences continue to shape who I am and how I approach life today."

10. SENSORY UNIQUENESS PER PHASE:
    ⚠️ Each phase gets ONE unique sensory focus - do NOT repeat sensory types across phases
    ✅ Childhood: sounds (laughter, bells, voices)
    ✅ Teenage: visual (light, patterns, colors)
    ✅ Early Adulthood: smells (coffee, food, cleaning)
    🚫 Do NOT use same sensory type in multiple phases

🔥 ENFORCEMENT EXAMPLE:

❌ WRONG (Too long, repetitive):
"I was born in a small town in the late 1990s, a quiet place surrounded by narrow streets, familiar faces, and a strong sense of community. My early years were shaped by simple routines—playing outside with neighborhood friends, listening to elders' stories, and watching life move at a slower, more predictable pace."

✅ CORRECT (Short paragraphs, varied sentences):
"I was born in a small town in the late 1990s. It was quiet, with narrow streets and familiar faces.

My early years followed simple routines. I played outside with neighborhood friends. We listened to elders' stories and watched life move slowly.

Those experiences shaped my sense of community. The warmth created lasting bonds."

Chapters to combine:
{chapters_text}

🚨 WRITE NOW - FOLLOW ALL RULES EXACTLY:
"""
        
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": f"You are a professional biographer combining life chapters with clear phase headers and smooth transitions. Maintain {style} style."},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature
        )
        
        return response.choices[0].message.content.strip()

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
