# Two-Step Closing Question Implementation

## Overview
Replaced the single closing question with a two-step flow to give users more control before moving to the next core question.

## Changes Made

### 1. llm_services.py

**Line 395 - Changed single question to CLOSING_Q1 marker:**
```python
# Before:
return "That's a wonderful memory. Is there anything more you'd like to share about this, or shall we move on?"

# After:
return "CLOSING_Q1"
```

**Lines 280-298 - Added detection logic:**
```python
# Check if user just answered CLOSING_Q1 → Return CLOSING_Q2
if last_question and "CLOSING_Q1" in last_question:
    return "CLOSING_Q2"

# Check if user just answered CLOSING_Q2 → Move to next core question
if last_question and "CLOSING_Q2" in last_question:
    if unanswered_core:
        return unanswered_core[0]  # Next core question
    else:
        return "PHASE_COMPLETE"
```

### 2. interview.py

**Lines 338-380 - Added CLOSING_Q1 and CLOSING_Q2 handling:**

**CLOSING_Q1 Flow:**
```python
if followup == "CLOSING_Q1":
    closing_q1_text = "Thanks for sharing your memories. Is there anything else you'd like to share about this part of your life?"
    # Save with empty response so it appears in last_question
    await memory_service.add_memory(
        user_id=user_id,
        session_id=session_id,
        category=category,
        question="CLOSING_Q1",
        response="",
        display_text=closing_q1_text
    )
    return {"response": closing_q1_text, ...}
```

**CLOSING_Q2 Flow:**
```python
if followup == "CLOSING_Q2":
    closing_q2_text = "Thank you. Are you happy to move on?"
    # Save temporarily with empty response
    await memory_service.add_memory(
        user_id=user_id,
        session_id=session_id,
        category=category,
        question="CLOSING_Q2",
        response="",
        display_text=closing_q2_text
    )
    return {"response": closing_q2_text, ...}
```

**CLOSING_Q2 Cleanup:**
```python
# When user answers CLOSING_Q2, delete it from memory
if last_question and "CLOSING_Q2" in last_question:
    await memories_collection.delete_one({
        "user_id": user_id,
        "session_id": session_id,
        "category": category,
        "question": "CLOSING_Q2"
    })
```

## Flow Diagram

```
Core Question + Follow-ups Complete
         ↓
    [CLOSING_Q1] "Thanks for sharing... Is there anything else?"
         ↓
    User answers (saved to memory in current phase)
         ↓
    [CLOSING_Q2] "Thank you. Are you happy to move on?"
         ↓
    User answers (NOT saved - just confirmation)
         ↓
    Delete CLOSING_Q2 entry
         ↓
    Next Core Question
```

## Memory Structure

### CLOSING_Q1 (Saved):
```json
{
  "category": "childhood",
  "question": "CLOSING_Q1",
  "response": "No, nothing more to add",
  "display_text": "Thanks for sharing your memories. Is there anything else you'd like to share about this part of your life?"
}
```

### CLOSING_Q2 (Temporary - Deleted after answer):
```json
{
  "category": "childhood",
  "question": "CLOSING_Q2",
  "response": "",
  "display_text": "Thank you. Are you happy to move on?"
}
```

## Frontend Integration

### `/ai/memory/{user_id}/{session_id}` Response:

**When CLOSING_Q1 is asked:**
```json
{
  "last_question": "Thanks for sharing your memories. Is there anything else you'd like to share about this part of your life?",
  "current_category": "childhood"
}
```

**When CLOSING_Q2 is asked:**
```json
{
  "last_question": "Thank you. Are you happy to move on?",
  "current_category": "childhood"
}
```

**After CLOSING_Q2 answered:**
```json
{
  "last_question": "What were your parents' names and occupations?",
  "current_category": "childhood"
}
```

## Key Features

1. ✅ **CLOSING_Q1 answer is saved** - User's final thoughts about the phase are preserved
2. ✅ **CLOSING_Q2 answer is NOT saved** - Just a confirmation, no memory content
3. ✅ **Both questions appear in last_question** - Frontend can display them properly
4. ✅ **Clean memory structure** - No clutter from confirmation questions
5. ✅ **Saved in current phase** - CLOSING_Q1 answer belongs to the phase being discussed

## Testing Scenarios

### Scenario 1: User adds more content at CLOSING_Q1
```
AI: "Thanks for sharing... Is there anything else?"
User: "Yes, I also remember playing with my dog"
→ System treats this as normal response, generates follow-ups
```

### Scenario 2: User says no at CLOSING_Q1
```
AI: "Thanks for sharing... Is there anything else?"
User: "No, nothing more"
→ Answer saved to memory
→ System asks CLOSING_Q2
```

### Scenario 3: User confirms at CLOSING_Q2
```
AI: "Thank you. Are you happy to move on?"
User: "Yes, please move on"
→ Answer NOT saved
→ CLOSING_Q2 entry deleted
→ Next core question asked
```

## Benefits

1. **Better UX** - Two clear steps instead of combined question
2. **Cleaner data** - Only meaningful content saved
3. **Frontend friendly** - Both questions visible in last_question
4. **Flexible** - User can add more at CLOSING_Q1 or move on
5. **Consistent** - Follows same pattern as other questions

## Notes

- CLOSING_Q1 and CLOSING_Q2 are **markers** that get replaced with actual text
- Memory map API already handles `display_text` field properly
- No changes needed to frontend - just displays `last_question` as before
- Works seamlessly with existing smart resume and phase selection features
