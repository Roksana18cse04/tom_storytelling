# Tom Storytelling - AI-Powered Life Story Platform

An intelligent storytelling platform that helps users capture, organize, and compile their life memories into beautiful narrative form through conversational AI interviews.

## Features

### 🎙️ AI Interview System
- Warm, British-style conversational interviewer
- Context-aware follow-up questions
- Support for both text and audio input
- Automatic life stage detection and categorization
- Progress tracking across 9 life phases

### 📸 Photo Memory Integration
- Upload photos with storytelling prompts
- AI-powered image analysis and caption generation
- Automatic life stage detection from photo context
- Photos embedded in narrative with custom placeholders

### 📖 Story Generation
- Multiple narrative styles (memoir, biography)
- Chapter-by-chapter or full story compilation
- Hallucination prevention - only uses provided information
- Photo captions naturally woven into narrative
- Custom image placeholders for frontend rendering

### 🗺️ Memory Map
- 7 life phase categories with progress tracking
- Auto-categorization of memories
- Snippet generation for quick preview
- Gap detection and suggestions

## Life Phases

1. **Childhood** (14 questions) - Early years, family, school
2. **Teenage Years** (9 questions) - Independence, friendships, identity
3. **Early Adulthood** (7 questions) - University, first jobs, leaving home
4. **Career & Work** (8 questions) - Professional life, achievements
5. **Relationships & Family** (8 questions) - Partners, children, traditions
6. **Hobbies & Adventures** (6 questions) - Travel, interests, joy
7. **Later Life & Reflections** (7 questions) - Legacy, wisdom, advice

## API Endpoints

### Interview Routes

#### POST `/interview`
Start or continue an AI interview session.

**Request:**
```
user_id: string (required)
session_id: string (required)
text: string (optional)
audio: file (optional)
```

**Response:**
```json
{
  "response": "AI's follow-up question",
  "current_category": "early adulthood",
  "memory_saved": true,
  "answered_in_phase": 5
}
```

**Features:**
- Detects life stage from user input
- Remembers unanswered questions
- Auto-advances to next phase when threshold met
- Welcomes returning users with context

---

### Photo Story Routes

#### POST `/photo_story/photo_question`
Upload a photo and receive a storytelling question.

**Request:**
```
user_id: string (required)
session_id: string (optional)
image: file (required)
```

**Response:**
```json
{
  "user_id": "user_34",
  "session_id": "session_34",
  "memory_id": "uuid",
  "question": "What's the story behind this moment...",
  "image_path": "path/to/image.jpg"
}
```

**Features:**
- AI analyzes photo content
- Generates contextual storytelling question
- Asks for life stage clarification
- Saves photo to current phase category

---

#### POST `/photo_story/photo_answer`
Answer the photo question (text or audio).

**Request:**
```
user_id: string (required)
session_id: string (required)
memory_id: string (required)
text: string (optional)
audio: file (optional)
```

**Response:**
```json
{
  "user_id": "user_34",
  "session_id": "session_34",
  "memory_id": "uuid",
  "answer": "This was from my university days...",
  "caption": "University days with my best friend",
  "category": "early adulthood",
  "moved_from": "career work"
}
```

**Features:**
- Supports text or audio input
- Generates AI caption from answer + photo
- Detects life stage from answer
- Auto-moves photo to correct category

---

### Story Generation Routes

#### GET `/story/chapter/{user_id}/{session_id}/{category}`
Generate a single chapter for a specific life phase.

**Query Parameters:**
- `style`: "memoir" (default) or "biography"

**Response:**
```json
{
  "user_id": "user_34",
  "session_id": "session_34",
  "category": "early adulthood",
  "style": "memoir",
  "chapter": "### Chapter: Early Adulthood\n\nI remember..."
}
```

**Use Case:** Preview individual chapters, phase-specific editing

---

#### GET `/story/full/{user_id}/{session_id}`
Generate complete life story with all chapters.

**Query Parameters:**
- `style`: "memoir" (default) or "biography"

**Response:**
```json
{
  "user_id": "user_34",
  "session_id": "session_34",
  "style": "memoir",
  "chapters": {
    "childhood": "Chapter text...",
    "early adulthood": "Chapter text...",
    "career work": "Chapter text..."
  },
  "total_chapters": 3
}
```

**Use Case:** Full story review, structured API response

---

#### GET `/story/{user_id}?session_id={session_id}`
Compile all chapters into single continuous text (legacy).

**Response:**
```json
{
  "story": "# Childhood\n\n...\n\n# Early Adulthood\n\n..."
}
```

**Use Case:** Final manuscript export, PDF generation

---

### History & Progress Routes

#### GET `/history/{user_id}/{session_id}`
Get formatted conversation history.

**Response:**
```json
{
  "user_id": "user_34",
  "session_id": "session_34",
  "formatted_history": "--- CHILDHOOD ---\nQ: ...\nA: ...\n"
}
```

---

#### GET `/memory_map/progress/{user_id}/{session_id}`
Get progress tracking for all phases.

**Response:**
```json
{
  "user_id": "user_34",
  "session_id": "session_34",
  "progress": {
    "childhood": 35.7,
    "early adulthood": 71.4,
    "career work": 12.5
  },
  "overall_progress": 39.9
}
```

**Calculation:**
- Phase progress = (answered questions / total questions) × 100
- Overall progress = average of all phase progress

---

## Story Generation Features

### Narrative Styles

**Memoir (Default):**
- Conversational, first-person
- Warm and personal tone
- Example: "I remember the day I was admitted to university..."

**Biography:**
- Polished, third-person
- Formal and structured
- Example: "She was admitted to university in 2015..."

### Photo Integration

Photos are embedded in stories with custom placeholders:

```
[Image: C:\Users\...\photo.jpg]
[Caption: "University days with my best friend: beauty, brains, and kindness."]
```

**Frontend Implementation:**
- Parse `[Image: ...]` to extract image path
- Parse `[Caption: ...]` to extract caption text
- Render as `<img src="path" alt="caption" />`

### Hallucination Prevention

The AI is strictly instructed to:
- ✅ ONLY use information explicitly provided by user
- ❌ NOT add fictional details, dates, places, or events
- ✅ Write SHORT chapters if information is minimal
- ❌ NOT make assumptions beyond user's words

### Chapter Generation Logic

Chapters are generated only if:
1. Category has answered questions
2. Responses have substantial content (>5 words)
3. Not just empty or placeholder responses

---

## Data Storage

### Memory Structure

```json
{
  "memory_map": {
    "user_id": {
      "session_id": {
        "category": [
          {
            "id": "uuid",
            "question": "Question text",
            "response": "User's answer",
            "snippet": "Short preview...",
            "photos": ["path/to/photo.jpg"],
            "photo_caption": "AI-generated caption",
            "audio_clips": [],
            "contributors": [],
            "timestamp": "ISO-8601"
          }
        ]
      }
    }
  },
  "user_phase": {
    "user_id": {
      "session_id": "current_category"
    }
  }
}
```

### File Storage

- **Memory data:** `memory.json`
- **User images:** `user_images/` directory
- **Story output:** Generated on-demand (not persisted)

---

## Setup & Installation

### Prerequisites

- Python 3.11+
- OpenAI API key
- FastAPI
- Uvicorn

### Installation

```bash
# Clone repository
git clone <repository-url>
cd tom_storytelling

# Install dependencies
pip install -r requirements.txt

# Set environment variables
# Create .env file with:
OPENAI_API_KEY=your_api_key_here

# Run server
uvicorn app.main:app --reload
```

### Configuration

Edit `app/core/config.py` to customize:
- OpenAI model (default: gpt-4o-mini and gpt-4o)
- Temperature settings
- File paths

---

## Workflow Example

### Complete User Journey

**1. Start Interview**
```bash
POST /interview
{
  "user_id": "user_34",
  "session_id": "session_34",
  "text": "I want to share my early adulthood memories"
}
```

**2. AI Detects Phase & Asks Question**
```json
{
  "response": "What specific memories stand out from that time?",
  "current_category": "early adulthood"
}
```

**3. User Answers Questions**
```bash
POST /interview
{
  "user_id": "user_34",
  "session_id": "session_34",
  "text": "I was admitted to university. I was so excited..."
}
```

**4. Upload Photo**
```bash
POST /photo_story/photo_question
{
  "user_id": "user_34",
  "session_id": "session_34",
  "image": <university_photo.jpg>
}
```

**5. Answer Photo Question**
```bash
POST /photo_story/photo_answer
{
  "user_id": "user_34",
  "session_id": "session_34",
  "memory_id": "uuid",
  "text": "This is from my early adult phase, university life with my best friend..."
}
```

**6. Check Progress**
```bash
GET /memory_map/progress/user_34/session_34
```

**7. Generate Story**
```bash
GET /story/full/user_34/session_34?style=memoir
```

---

## Key Design Decisions

### Why Separate Photo Category Detection?

Photos are initially saved to the user's current phase, but the answer is analyzed to detect the actual life stage. This allows:
- Flexible photo uploads at any time
- Accurate categorization based on content
- User control over placement

### Why Multiple Story Endpoints?

- `/chapter/` - For previewing individual phases
- `/full/` - For structured API responses (recommended)
- `/{user_id}` - For legacy support and simple text export

### Why Custom Image Placeholders?

Instead of Markdown or HTML:
- Frontend flexibility in rendering
- Easy parsing and replacement
- Support for various output formats (PDF, HTML, etc.)

---

## Tech Stack

- **Backend:** FastAPI (Python)
- **AI:** OpenAI GPT-4o-mini (vision + text)
- **Storage:** JSON file-based (scalable to database)
- **Audio:** Whisper API for transcription
- **Image Processing:** Base64 encoding for vision API
---

## Support

For issues or questions, please contact [your contact info]
