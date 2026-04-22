# Narratus Implementation Plan
## Review & Enhancement Strategy for Current Narrative Engine

---

## 📊 CURRENT vs NARRATUS - COMPARISON

### Current State
✅ **What's Working:**
- 6 narrative styles implemented
- Style-specific temperatures configured
- Voice preservation safeguards present
- Banned words/phrases lists exist
- Photo integration support
- Authenticity rules emphasized

❌ **What's Missing:**
- No explicit content classification (Contextual/Formative/Emotional Anchor)
- No narrative weighting rules
- No required chapter structure template
- No timeline integrity checks
- No emotional anchor pattern enforcement
- Opening/ending rules are vague
- No quality check self-verification
- Voice preservation could be stronger

---

## 🎯 REQUIRED CHANGES

### **CHANGE 1: Add Content Classification Layer**
**Location:** `narrative_engine.py` → Add new method before chapter generation

**What to add:**
```python
def _classify_content(self, qa_text: str) -> dict:
    """
    Pre-process Q&A to classify each answer as:
    - Contextual: dates, locations, facts
    - Formative: experiences that shaped behavior/identity
    - Emotional Anchor: strong emotion, impact, loss, joy
    """
```

**Implementation:**
- Sends Q&A to GPT with classification prompt
- Returns structured dict with classifications
- Used to weight narrative sections differently

**Where:** Line 45-50 area (before `generate_chapter`)

---

### **CHANGE 2: Implement Narrative Weighting Rules**
**Location:** `_get_style_prompt()` method

**Current problem:**
- All Q&A treated equally
- No prioritization of formative/emotional content

**What to add:**
```
NARRATIVE WEIGHTING RULES:

Contextual Content → Compress to cover detail only
Formative Content → Expand modestly with reflection  
Emotional Anchors → MUST BE ELEVATED:
  1. Introduced with framing sentence
  2. Use user's exact words (or close paraphrase)
  3. Follow with ONE reflective sentence
  
IF Emotional Anchor without reflection → INVALID
```

**Where:** Add to ALL style prompts (especially in `_get_style_prompt()`)

---

### **CHANGE 3: Enforce Required Chapter Structure**
**Location:** `_get_style_prompt()` → Add explicit structure instructions

**Current:** 
- No explicit structure template
- Styles generate freely

**What to add:**
```
REQUIRED CHAPTER STRUCTURE:

1. OPENING (Meaning-Led)
   - NO logistics or scene setup
   - Establish emotional tone/theme/significance
   - Example: "This period taught me what resilience truly means."

2. CONTEXT & SETUP (Compressed)
   - Timeframe, circumstances, background
   - Keep minimal

3. CORE EXPERIENCES (Formative Focus)
   - Key relationships, events, decisions
   - Prioritize experiences that shaped narrator

4. EMOTIONAL ANCHORS (Elevated)
   - Moments of strong emotion/lasting impact
   - Use the pattern from CHANGE 2

5. CLOSING REFLECTION (Mandatory)
   - Answer: "What did this chapter give/change/reveal?"
   - Integrative, not anecdotal
   - Links back to opening theme
```

**Where:** Add to ALL style prompts

---

### **CHANGE 4: Add Timeline Integrity Check**
**Location:** `_get_style_prompt()` → Add validation rules

**Current problem:**
- No timeline constraint enforcement
- Could mix events out of scope

**What to add:**
```
TIMELINE INTEGRITY RULE:

This chapter = ONE life topic or period.

ALLOWED:
- Events within chapter scope
- Later reflections WITH explicit framing:
  "Years later..." / "Looking back now..."

DISALLOWED:
- Events outside scope without temporal framing
```

**Where:** Add to ALL style prompts

---

### **CHANGE 5: Enforce Emotional Anchor Output Pattern**
**Location:** `_get_style_prompt()` → Add exact pattern

**Current problem:**
- Emotional moments sometimes buried or underplayed

**What to add:**
```
EMOTIONAL ANCHOR OUTPUT PATTERN (REQUIRED):

[Context sentence establishing the moment]
[User's emotional statement - preserved or lightly edited]
[Reflection sentence linking to lasting meaning/impact]

EXAMPLE:
"When my father passed, I was only sixteen. 
It was sudden and I didn't know how to process it. 
But that loss forced me to grow up quickly, 
and I learned that day what real responsibility meant."
```

**Where:** Add to ALL style prompts

---

### **CHANGE 6: Strengthen Opening Rule (Meaning-Led)**
**Location:** `_get_style_prompt()` → Expand opening instructions

**Current problem:**
- Opening sometimes generic or descriptive
- Should establish MEANING first

**What to add:**
```
OPENING RULE (NON-NEGOTIABLE):

❌ WRONG: "I was born in 1995 in a small village near Dhaka."
✅ CORRECT: "This period of my life taught me the value of family bonds."

Opening MUST:
1. Establish emotional tone or theme
2. Signal what this chapter is ABOUT (thematically)
3. Come before ANY logistics or scene-setting
4. Be grounded in the user's reflections/feelings
```

**Where:** Add to ALL style prompts

---

### **CHANGE 7: Strengthen Ending Rule (Reflective & Integrative)**
**Location:** `_get_style_prompt()` → Expand ending instructions

**Current problem:**
- Some chapters end on anecdote or description
- Should end with synthesis

**What to add:**
```
ENDING RULE (FAIL IF MISSING):

Final paragraph MUST answer:
"What did this chapter of life give, change, or reveal?"

Requirements:
1. Synthesize key insights/learnings
2. Link to identity/values/growth
3. Connect back to opening theme if possible
4. NOT on logistics, description, or final anecdote
5. Reflective and integrative in tone

EXAMPLE:
"Looking back, those years shaped how I approach challenges now. 
I learned that setbacks are not endpoints, but redirections. 
That's a lesson I carry with me still."
```

**Where:** Add to ALL style prompts

---

### **CHANGE 8: Strengthen Voice Preservation Safeguards**
**Location:** `_get_system_message()` → Expand all style messages

**Current problem:**
- Voice preservation instructions exist but could be tougher
- Need explicit "Acceptance Test"

**What to add:**
```
VOICE PRESERVATION SAFEGUARDS (ALL STYLES):

DO NOT:
- Add motivations user didn't express
- Dramatise or embellish
- Add sensory detail unless stated
- Create emotional arcs user didn't indicate
- Invent character development

Acceptance Test:
The user should recognise the chapter as their story, 
just better shaped. If anything feels foreign or "written by AI," 
it violates this rule.

FAIL CONDITIONS:
- Added motivation: "He worked hard to prove himself" (if user didn't say)
- Added sensory: "The humid air clung to her skin" (if user didn't mention humidity)
- Invented arc: Chapter suggests growth user didn't claim
```

**Where:** Add to ALL style system messages

---

### **CHANGE 9: Add Quality Check Self-Verification**
**Location:** Add new method `_verify_chapter_quality()`

**Current problem:**
- No validation before returning chapter
- Bad chapters can slip through

**What to add:**
```python
async def _verify_chapter_quality(self, chapter: str, style: str) -> tuple[bool, str]:
    """
    Self-verify chapter against quality checklist.
    Returns (passed: bool, reason: str)
    
    Checks:
    1. ✓ Emotional anchors are elevated, not buried
    2. ✓ Contextual material is compressed
    3. ✓ Formative experiences receive more space
    4. ✓ Timeline integrity maintained
    5. ✓ Opening is meaning-led
    6. ✓ Ending is reflective and integrative
    7. ✓ Voice remains recognisably user's
    8. ✓ No banned words/phrases for style
    
    If fails, request revision from GPT.
    """
```

**Where:** Add new method after `generate_chapter()`

---

### **CHANGE 10: Add Narratus System Prompt as Base**
**Location:** `_get_system_message()` → Add foundational base

**Current problem:**
- No unified "Narratus" foundation
- Each style starts from scratch

**What to add:**
```
BASE SYSTEM MESSAGE (for all styles):

You are Narratus, generating a finished memoir chapter 
from an interview transcript. Your task is to produce 
a shaped, reflective chapter that preserves the user's 
natural voice and factual accuracy.

CORE PRINCIPLES (NON-NEGOTIABLE):
1. Preserve user's voice and phrasing
2. Do not invent events, facts, motivations
3. Reflection must be derived from user's statements
4. Emotional truth > completeness
5. Shape and meaning > chronological exhaustiveness
6. Output must read like thoughtful memoir, not notes

[Then add style-specific variations]
```

**Where:** Create new method `_get_narratus_base_system()` and call in `_get_system_message()`

---

## 📋 IMPLEMENTATION SEQUENCE

### **Phase 1: Foundation (2 methods)**
1. ✅ Add `_classify_content()` method
2. ✅ Add `_verify_chapter_quality()` method

### **Phase 2: Prompt Enhancement (6 prompts)**
3. ✅ Update all 6 style prompts with:
   - Narratus base principles
   - Narrative weighting rules
   - Required chapter structure
   - Timeline integrity rules
   - Emotional anchor pattern
   - Opening rule (meaning-led)
   - Ending rule (reflective)
   - Voice preservation safeguards
   - Quality check instructions

### **Phase 3: System Message Strengthening (6 messages)**
4. ✅ Update all 6 system messages with:
   - Narratus role definition
   - Voice preservation safeguards
   - Fail conditions
   - Acceptance test

### **Phase 4: Integration (1 method)**
5. ✅ Update `generate_chapter()` to:
   - Call `_classify_content()` if enabled
   - Use enhanced prompts
   - Call `_verify_chapter_quality()` before return
   - Handle revision if needed

### **Phase 5: Testing**
6. ✅ Test with sample memoirs
7. ✅ Verify all 6 styles work correctly
8. ✅ Validate quality checks

---

## 🔧 FILES TO MODIFY

| File | Changes | Lines |
|------|---------|-------|
| `narrative_engine.py` | Add 2 methods + update `_get_system_message()` + update `_get_style_prompt()` + update `generate_chapter()` | 450-550 lines total change |

---

## ⚡ EFFORT ESTIMATE

| Task | Effort | Notes |
|------|--------|-------|
| Add classification method | 20 mins | Straightforward |
| Add verification method | 25 mins | Needs quality check logic |
| Update all 6 styles | 60 mins | Prompts need careful rewrite |
| Update system messages | 30 mins | Add Narratus base + safeguards |
| Integrate into generate_chapter | 15 mins | Flow control |
| Testing | 30 mins | Manual testing with samples |
| **TOTAL** | **~3 hours** | Can do all today |

---

## ✅ SUCCESS CRITERIA

After implementation, chapters should:

1. ✅ Start with meaning-led opening (not description)
2. ✅ Elevate emotional anchors with proper pattern
3. ✅ Compress contextual material
4. ✅ Expand formative experiences
5. ✅ Maintain timeline integrity
6. ✅ End with reflective synthesis
7. ✅ Preserve user's natural voice
8. ✅ Pass quality checks before delivery
9. ✅ Users recognize their story, just better shaped
10. ✅ No banned words/phrases sneak in

---

## 🎯 NEXT STEPS

**IF YOU APPROVE THIS PLAN:**
1. Say "Yes, implement it"
2. I will update `narrative_engine.py` with ALL changes
3. We test with sample data
4. Deploy

**IF YOU WANT MODIFICATIONS:**
1. Tell me which changes to adjust
2. I'll update the plan
3. Then implement

**Ready to proceed?** 🚀

