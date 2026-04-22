# Tom Storytelling - Project Review & Route Documentation

## Project Overview
**Tom Storytelling** is an AI-powered life story platform that helps users capture, organize, and compile their life memories into beautiful narrative form through conversational AI interviews.

### Tech Stack
- **Backend**: FastAPI (Python)
- **Database**: MongoDB (with Motor async driver)
- **LLM**: OpenAI API
- **Storage**: AWS S3 (for photos)
- **Audio**: Transcription services
- **Server**: Uvicorn

---

## System Architecture

### Core Modules
```
app/
├── main.py                    # FastAPI app initialization & middleware
├── api/
│   ├── routes/               # 6 main route modules
│   │   ├── interview.py      # AI interview conversations
│   │   ├── photo_story.py    # Photo-based storytelling
│   │   ├── story.py          # Narrative generation
│   │   ├── memory_map.py     # Memory navigation
│   │   ├── history.py        # Session history
│   │   └── depth_stats.py    # Analytics & depth metrics
├── services/
│   ├── llm_services.py       # OpenAI LLM interactions
│   ├── memory_services_mongodb.py # Memory CRUD & phase management
│   ├── photo_service.py      # Image analysis & S3 upload
│   ├── narrative_engine.py   # Story generation
│   ├── transcription_services.py # Audio-to-text
│   └── other services...
├── core/
│   ├── config.py             # Configuration management
│   ├── database.py           # MongoDB connections
└── questions/
    └── questions.py          # Question bank for 9 life phases
```

---

## Life Phases (9 Total)
1. **Childhood** - Early years, family, school
2. **Teenage Years** - Independence, friendships, identity  
3. **Early Adulthood** - University, first jobs, leaving home
4. **Career & Work** - Professional life, achievements (8 questions)
5. **Relationships & Family** - Partners, children, traditions (8 questions)
6. **Hobbies & Adventures** - Travel, interests, joy (6 questions)
7. **Home & Community** - Neighborhood, hometown, relocation
8. **Challenges & Growth** - Difficulties, struggles, overcoming
9. **Later Life & Reflections** - Legacy, wisdom, advice (7 questions)

---

## API Routes (6 Main Modules)

### 📌 Route Prefixes in main.py
```python
/ai                      → interview + photo_story + history
/ai/memory              → memory_map
/ai/story               → story
/ai/depth               → depth_stats
```

---

## 1. INTERVIEW ROUTES (`/ai`)
**Purpose**: AI-powered conversational interviewing with smart phase detection

### POST `/ai/` - Start/Continue Interview
**Input**:
- `user_id` (required) - Unique user identifier
- `session_id` (required) - Session identifier
- `text` (optional) - User's text input
- `audio` (optional) - Audio file for transcription

**Process**:
1. If audio provided → transcribe to text
2. Detect life phase from user's input
3. Handle explicit phase changes (keywords + intent detection)
4. Auto-advance phases when question threshold met
5. Remember unanswered questions
6. Return next AI question

**Response**:
```json
{
  "response": "AI's follow-up question or message",
  "current_category": "early adulthood",
  "memory_saved": true,
  "answered_in_phase": 5,
  "awaiting_phase_selection": false,
  "phase_selected": false,
  "is_reminder": false
}
```

**Smart Features**:
- ✅ Phase selection with keywords (e.g., "let's explore childhood")
- ✅ Unanswered question reminders
- ✅ Context-aware phase detection
- ✅ Returns numbered phase selection menu if initial phase unclear
- ✅ Audio transcription support

**Key Logic**:
- Explicit intent phrases: "want to share", "let's explore", "move to"
- Phase detection only triggers with intent + memory keyword
- Falls back to phase selection menu if ambiguous

---

## 2. PHOTO STORY ROUTES (`/ai`)
**Purpose**: Photo-based memory capture with AI analysis

### POST `/ai/photo_question` - Upload Photo & Get Question
**Input**:
- `user_id` (required)
- `image` (required) - Image file
- `session_id` (optional) - If not provided, creates new session

**Process**:
1. Save image temporarily
2. Upload to AWS S3
3. AI analyzes photo content
4. Generate contextual storytelling question
5. Save to MongoDB with S3 URL
6. Delete local temp file

**Response**:
```json
{
  "user_id": "user_34",
  "session_id": "session_uuid",
  "memory_id": "mongodb_id",
  "question": "What's the story behind this moment...",
  "image_path": "s3_url_to_image"
}
```

### POST `/ai/photo_answer` - Answer Photo Question
**Input**:
- `user_id` (required)
- `session_id` (required)
- `memory_id` (required) - Memory ID from photo_question response
- `text` or `audio` (required) - User's answer

**Process**:
1. Transcribe audio if provided
2. Locate photo memory in MongoDB
3. Generate up to 4 follow-up questions (structured):
   - Q1: Who/What was involved?
   - Q2: When/Where did this happen?
   - Q3: Sensory details?
   - Q4: Emotional impact/Significance?
4. Update memory with response
5. Track answer count for completion

**Response**:
```json
{
  "memory_id": "mongodb_id",
  "answer_count": 2,  // How many answer rounds completed
  "next_question": "Follow-up question or completion message",
  "category_detected": "childhood",
  "updated_category": false
}
```

**Key Feature**: MAX_PHOTO_FOLLOWUPS = 4 (structured deep-dive questions)

---

## 3. STORY ROUTES (`/ai/story`)
**Purpose**: Generate narrative stories from collected memories

### GET `/ai/story/chapter/{user_id}/{session_id}/{category}`
Generate narrative chapter for a specific life phase

**Query Parameters**:
- `style` (optional, default: "conversational")
  - Options: conversational, literary, formal, reflective, light_hearted, concise

**Response**:
```json
{
  "_id": "story_mongodb_id",
  "user_id": "user_id",
  "session_id": "session_id",
  "category": "childhood",
  "style": "conversational",
  "chapter": "Full narrative text...",
  "from_cache": false  // Whether from cache or freshly generated
}
```

**Features**:
- ✅ Caching mechanism (get_or_generate_chapter)
- ✅ Multiple narrative styles
- ✅ Fingerprinting to detect memory changes

### GET `/ai/story/full/{user_id}/{session_id}`
Generate complete life story as single continuous narrative

**Query Parameters**:
- `style` (optional, default: "conversational")

**Response**:
```json
{
  "_id": "story_mongodb_id",
  "user_id": "user_id",
  "session_id": "session_id",
  "style": "conversational",
  "story": "Complete life narrative with smooth transitions...",
  "from_cache": false
}
```

**Key Features**:
- ✅ Smooth transitions between life phases
- ✅ Hallucination prevention (only uses provided info)
- ✅ Photo captions naturally woven in
- ✅ Caching for performance

### GET `/ai/story/{user_id}` (Legacy Endpoint)
Legacy endpoint for story compilation

**Query Parameters**:
- `session_id` (required)

---

## 4. MEMORY MAP ROUTES (`/ai/memory`)
**Purpose**: Navigate memory structure and track progress

### GET `/ai/memory/progress/{user_id}/{session_id}`
Get completion progress across all life phases

**Response**:
```json
{
  "user_id": "user_id",
  "session_id": "session_id",
  "overall_progress": 45.5,  // Percentage (0-100)
  "category_progress": {
    "childhood": 80,
    "teenage years": 60,
    "early adulthood": 40,
    ...
  },
  "gaps": [],
  "richest_categories": [
    { "category": "childhood", "progress": 80 },
    { "category": "career work", "progress": 75 }
  ]
}
```

### GET `/ai/memory/{user_id}`
Get all sessions for a user with memory structure

**Response**:
```json
{
  "user_id": "user_id",
  "sessions": {
    "session_id_1": {
      "childhood": [
        {
          "_id": "memory_id",
          "memory_id": "memory_id",
          "question": "What was your earliest memory?",
          "response": "I remember...",
          "question_display": "Display text or question",
          "is_photo": false,
          "timestamp": "2024-01-15T10:30:00"
        }
      ],
      "teenage years": [...],
      ...
    },
    "session_id_2": {...}
  }
}
```

### GET `/ai/memory/{user_id}/{session_id}`
Get all memories for a specific session

**Response** (Same structure as above but for single session):
```json
{
  "user_id": "user_id",
  "session_id": "session_id",
  "current_phase": "early adulthood",
  "last_question": "Follow-up question or phase message",
  "is_last": false,
  "photo_complete": false,
  "categories": {
    "childhood": [... memories ...],
    "teenage years": [... memories ...],
    ...
  }
}
```

**Key Fields**:
- `is_photo`: Indicates photo-based memory
- `question_display`: User-friendly question (uses display_text if available)
- `last_question`: Most recent message across all categories
- `is_last`: Whether this is a phase completion message

---

## 5. HISTORY ROUTES (`/ai`)
**Purpose**: Session management and history access

### GET `/ai/{user_id}/sessions`
Get all sessions for a user

**Response**:
```json
{
  "user_id": "user_id",
  "sessions": ["session_id_1", "session_id_2", "session_id_3"]
}
```

### GET `/ai/{user_id}`
Get formatted history for a session

**Query Parameters**:
- `session_id` (required)

**Response**:
```json
{
  "user_id": "user_id",
  "session_id": "session_id",
  "formatted_history": "Markdown-formatted conversation history",
  "last_question": "Last question asked"
}
```

### DELETE `/ai/{user_id}`
Clear/delete a session

**Query Parameters**:
- `session_id` (required)

**Response**:
```json
{
  "message": "Session session_id cleared for user user_id"
}
```

---

## 6. DEPTH ANALYTICS ROUTES (`/ai/depth`)
**Purpose**: Track memory quality and story completion progress

### GET `/ai/depth/depth_stats/{user_id}/{session_id}`
Get comprehensive depth statistics and progress

**Response**:
```json
{
  "user_id": "user_id",
  "session_id": "session_id",
  "total_memories": 42,
  "average_depth_score": 62.3,
  "quality_rating": "Excellent",
  "depth_distribution": {
    "Minimal": 5,
    "Basic": 10,
    "Moderate": 15,
    "Rich": 10,
    "Exceptional": 2
  },
  "category_depths": {
    "childhood": {
      "average_depth": 65.4,
      "memory_count": 8,
      "total_words": 4200,
      "target_words": 8400,
      "word_progress_percentage": 50.0,
      "status": "in_progress"
    },
    ...
  },
  "word_count_progress": {
    "current_words": 22500,
    "target_words": 35400,
    "progress_percentage": 63.6,
    "remaining_words": 12900,
    "status": "in_progress",
    "message": "Keep going! 12,900 words remaining."
  }
}
```

**Depth Levels**:
- Minimal (0-20)
- Basic (21-40)
- Moderate (41-60)
- Rich (61-80)
- Exceptional (81-100)

**Quality Rating**:
- Exceptional: avg_depth ≥ 70
- Excellent: avg_depth ≥ 50
- Good: avg_depth ≥ 35
- Developing: avg_depth < 35

**Story Status**:
- complete: ≥ 100% of target words
- nearly_complete: 75-99%
- halfway: 50-74%
- in_progress: < 50%

---

## Data Models

### Memory Object
```json
{
  "_id": "ObjectId",
  "user_id": "string",
  "session_id": "string",
  "category": "string (life phase)",
  "question": "string",
  "response": "string",
  "display_text": "string (optional, used for UI display)",
  "photos": ["s3_url_1", "s3_url_2"],
  "depth_score": 0-100,
  "depth_level": "Minimal|Basic|Moderate|Rich|Exceptional",
  "snippet": "short preview text",
  "timestamp": "ISO datetime"
}
```

### Story Object
```json
{
  "_id": "ObjectId",
  "user_id": "string",
  "session_id": "string",
  "category": "string or '__full__'",
  "style": "conversational|literary|formal|reflective|light_hearted|concise",
  "chapter": "string (narrative text)",
  "source_fingerprint": "hash for change detection",
  "created_at": "ISO datetime",
  "updated_at": "ISO datetime"
}
```

---

## Key Features & Logic

### 1. Smart Phase Detection
- Uses keyword matching from phase_map dictionary
- Requires explicit intent + memory keyword combo
- Falls back to numbered menu if unclear
- Remembers last phase and resumes from there

### 2. Question Bank System
- 9 life phases with customized question counts
- Auto-detection when thresholds are met
- Unanswered question tracking
- Reminder system for incomplete questions

### 3. Photo Deep-Dive
- 4-level structured questioning
- Contextual analysis using OpenAI vision
- S3 storage with cleanup
- Auto-categorization based on user phase

### 4. Story Generation
- Multiple narrative styles
- Caching mechanism (MongoDB-based)
- Hallucination prevention
- Photo integration with custom placeholders
- Smooth transitions between chapters

### 5. Progress Tracking
- Depth scoring (0-100 scale)
- Word count targets (35,400 minimum for full story)
- Category-level progress
- Quality ratings
- Gap detection

### 6. Session Management
- Multi-session support per user
- Phase persistence
- Formatted history export
- Session deletion capability

---

## Database Collections
1. **memories** - Core memory storage with all metadata
2. **stories** - Generated narratives with caching
3. **sessions** - Session metadata and phase info
4. **users** - User profile data (if applicable)

---

## Environment Variables Required
- `OPENAI_API_KEY` - For LLM
- `MONGODB_URI` - Database connection
- `AWS_ACCESS_KEY_ID` - S3 access
- `AWS_SECRET_ACCESS_KEY` - S3 secret
- `S3_BUCKET_NAME` - S3 bucket name

---

## Potential Improvements & Observations

### 🔴 Issues to Address
1. **Duplicate Route Registration** - `/ai/depth` registered twice in main.py (line 41-42)
2. **Error Handling** - Some endpoints could have better error messages
3. **Validation** - Could add more strict request validation
4. **Rate Limiting** - No rate limiting implemented

### 🟡 Optimization Opportunities
1. **Caching Strategy** - Consider Redis for faster cache hits
2. **Batch Processing** - Photo uploads could support batch processing
3. **Async Operations** - All database calls are async-ready but some services could be optimized
4. **Photo Cleanup** - Add scheduled cleanup for failed uploads
5. **Progress Calculations** - Cache progress data to avoid recalculation

### 🟢 Good Practices
1. ✅ Async/await throughout
2. ✅ CORS enabled for frontend integration
3. ✅ MongoDB async driver (Motor)
4. ✅ Memory caching for generated stories
5. ✅ Photo S3 integration with cleanup
6. ✅ Comprehensive depth scoring system
7. ✅ Multi-session support

---

## Testing Recommendations
1. Test phase detection with ambiguous inputs
2. Validate photo upload with various formats
3. Test story generation with minimal memories
4. Verify depth score calculations
5. Test session switching and data isolation
6. Test concurrent user sessions

---

## Deployment Checklist
- [ ] Configure `.env` with all required keys
- [ ] Set up MongoDB Atlas or local MongoDB
- [ ] Configure AWS S3 bucket and credentials
- [ ] Set up OpenAI API key
- [ ] Run database migrations (if any)
- [ ] Test all endpoints with sample data
- [ ] Enable HTTPS for production
- [ ] Set up logging and monitoring
- [ ] Configure CORS properly for frontend domain

