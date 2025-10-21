import json, os, uuid, datetime, re
from typing import Dict, List, Tuple
from app.questions.questions import QUESTION_BANK

class MemoryService:
    def __init__(self):
        self.file_path = "memory.json"
        self.memory_map: Dict[str, Dict[str, Dict[str, List[dict]]]] = {}  # user_id → session_id → category → memories
        self.user_phase: Dict[str, Dict[str, str]] = {}  # user_id → session_id → phase
        self._load_memory()

    # ─── Load & Save ──────────────────────────────
    def _load_memory(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r") as f:
                    data = json.load(f)
                    self.memory_map = data.get("memory_map", {})
                    self.user_phase = data.get("user_phase", {})
            except json.JSONDecodeError:
                self.memory_map, self.user_phase = {}, {}

    def _save_memory(self):
        with open(self.file_path, "w") as f:
            json.dump({
                "memory_map": self.memory_map,
                "user_phase": self.user_phase
            }, f, indent=2)

    # ─── Phase Handling ───────────────────────────
    def get_phase(self, user_id: str, session_id: str) -> str:
        if user_id not in self.user_phase:
            self.user_phase[user_id] = {}
        if session_id not in self.user_phase[user_id]:
            self.user_phase[user_id][session_id] = None  # No default phase
        return self.user_phase[user_id][session_id]

    def set_phase(self, user_id: str, session_id: str, phase: str):
        self.user_phase.setdefault(user_id, {})[session_id] = phase
        self._save_memory()

    def detect_initial_phase(self, text: str) -> str:
        """Detect appropriate starting phase from user's first input."""
        text_lower = text.lower()
        
        # Life stage keywords (check FIRST before vague intent check)
        stage_map = {
            "childhood": ["child", "kid", "young", "elementary", "primary school", "grew up", "born"],
            "teenage years": ["teenage", "teen", "high school", "secondary", "adolescent"],
            "early adulthood": ["university", "college", "first job", "twenties", "young adult", "early adult"],
            "career work": ["career", "work", "job", "professional", "employed", "business"],
            "relationships & family": ["married", "wedding", "spouse", "children", "parent"],
            "hobbies & adventures": ["travel", "trip", "journey", "vacation", "adventure", "hobby", "visited"],
            "later life & reflections": ["retired", "retirement", "grandchildren", "looking back"]
        }
        
        for phase, keywords in stage_map.items():
            if any(kw in text_lower for kw in keywords):
                return phase
        
        # Check if user wants to be asked about phase preference (only if no stage detected)
        vague_intents = ["share", "tell", "talk about", "memory", "story", "life"]
        if any(intent in text_lower for intent in vague_intents) and len(text.split()) < 10:
            return "ASK_USER"
        
        # Age detection
        age_match = re.search(r'\b(\d{1,2})\s*(?:years?|yrs?)\s*old\b', text_lower)
        if age_match:
            age = int(age_match.group(1))
            if age <= 12: return "childhood"
            if age <= 19: return "teenage years"
            if age <= 30: return "early adulthood"
            if age <= 50: return "career work"
            return "later life & reflections"
        
        return "ASK_USER"  # Ask user if nothing detected

    # ─── Helper ───────────────────────────────────
    def _generate_snippet(self, response: str, max_length: int = 120) -> str:
        if not response:
            return ""
        sentence = re.split(r'(?<=[.!?]) +', response.strip())[0]
        snippet = sentence.strip()
        if len(snippet) > max_length:
            snippet = snippet[:max_length].rsplit(" ", 1)[0] + "..."
        return snippet

    # ─── Memory Management ────────────────────────
    def add_memory(self, user_id: str, session_id: str, category: str,
                   question: str, response: str, photos=None, audio_clips=None, contributors=None, photo_caption=None):
        photos = photos or []
        audio_clips = audio_clips or []
        contributors = contributors or []

        snippet = self._generate_snippet(response)
        entry = {
            "id": str(uuid.uuid4()),
            "question": question,
            "response": response,
            "snippet": snippet,
            "photos": photos,
            "photo_caption": photo_caption,
            "audio_clips": audio_clips,
            "contributors": contributors,
            "timestamp": datetime.datetime.now().isoformat()
        }

        self.memory_map.setdefault(user_id, {}).setdefault(session_id, {}).setdefault(category, []).append(entry)
        self._save_memory()

    def get_user_sessions(self, user_id: str):
        """Return all session IDs for a user."""
        return list(self.memory_map.get(user_id, {}).keys())

    def get_user_memories(self, user_id: str, session_id: str):
        return self.memory_map.get(user_id, {}).get(session_id, {})

    def get_category_memories(self, user_id: str, session_id: str, category: str):
        return self.memory_map.get(user_id, {}).get(session_id, {}).get(category, [])

    def clear_session(self, user_id: str, session_id: str):
        if user_id in self.memory_map and session_id in self.memory_map[user_id]:
            del self.memory_map[user_id][session_id]
        if user_id in self.user_phase and session_id in self.user_phase[user_id]:
            del self.user_phase[user_id][session_id]
        self._save_memory()

    def get_formatted_history(self, user_id: str, session_id: str) -> str:
        session_data = self.memory_map.get(user_id, {}).get(session_id, {})
        formatted_lines = []
        for category, memories in session_data.items():
            formatted_lines.append(f"--- {category.upper()} ---")
            for mem in memories:
                formatted_lines.append(f"Q: {mem['question']}")
                formatted_lines.append(f"A: {mem['response']}\n")
        return "\n".join(formatted_lines)

    def add_message(self, user_id: str, session_id: str, role: str, content: str):
        category = self.get_phase(user_id, session_id)
        if role == "Assistant":
            self.add_memory(user_id, session_id, category, content, "")

    # ─── Progress Tracking ────────────────────────
    def get_progress(self, user_id: str, session_id: str) -> Dict[str, float]:
        """Calculate completion percentage for each category."""
        session_data = self.memory_map.get(user_id, {}).get(session_id, {})
        progress = {}
        DEFAULT_TARGET = 5  # Fallback for undefined phases
        
        for category in QUESTION_BANK.keys():
            answered = len([m for m in session_data.get(category, []) if m["response"].strip()])
            total_questions = len(QUESTION_BANK[category]["questions"]) if category in QUESTION_BANK else DEFAULT_TARGET
            progress[category] = round((answered / total_questions) * 100, 1) if total_questions > 0 else 0.0
        
        return progress

    def get_overall_progress(self, user_id: str, session_id: str) -> float:
        """Calculate overall completion percentage."""
        progress = self.get_progress(user_id, session_id)
        return round(sum(progress.values()) / len(progress), 1) if progress else 0.0

    def detect_gaps(self, user_id: str, session_id: str) -> List[Dict[str, any]]:
        """Identify categories with low completion and suggest focus areas."""
        progress = self.get_progress(user_id, session_id)
        gaps = []
        
        for category, percentage in progress.items():
            if percentage < 20:
                gaps.append({
                    "category": category,
                    "progress": percentage,
                    "suggestion": f"You've added very little about {category.replace('_', ' ')}. Would you like to explore that time?"
                })
            elif percentage < 50:
                gaps.append({
                    "category": category,
                    "progress": percentage,
                    "suggestion": f"You've started sharing about {category.replace('_', ' ')}, but there's more to explore."
                })
        
        return sorted(gaps, key=lambda x: x["progress"])

    def get_richest_categories(self, user_id: str, session_id: str, top_n: int = 3) -> List[Tuple[str, float]]:
        """Return categories with most content."""
        progress = self.get_progress(user_id, session_id)
        return sorted(progress.items(), key=lambda x: x[1], reverse=True)[:top_n]

    # ─── Memory Connector ─────────────────────────────────────
    def extract_keywords(self, text: str) -> set:
        """Extract important keywords from text (names, places, events)."""
        if not text:
            return set()
        # Simple keyword extraction (can be enhanced with NLP)
        words = re.findall(r'\b[A-Z][a-z]+\b', text)  # Capitalized words
        common_words = {'I', 'The', 'A', 'An', 'My', 'We', 'He', 'She', 'They', 'It', 'That', 'This'}
        return set(w for w in words if w not in common_words)

    def find_related_memories(self, user_id: str, session_id: str, memory_id: str) -> List[Dict]:
        """Find memories related to a specific memory based on keywords."""
        session_data = self.memory_map.get(user_id, {}).get(session_id, {})
        target_memory = None
        target_category = None
        
        # Find the target memory
        for category, memories in session_data.items():
            for mem in memories:
                if mem["id"] == memory_id:
                    target_memory = mem
                    target_category = category
                    break
        
        if not target_memory:
            return []
        
        # Extract keywords from target memory
        keywords = self.extract_keywords(target_memory["response"])
        if not keywords:
            return []
        
        # Find related memories
        related = []
        for category, memories in session_data.items():
            if category == target_category:
                continue  # Skip same category
            for mem in memories:
                mem_keywords = self.extract_keywords(mem["response"])
                overlap = keywords & mem_keywords
                if overlap:
                    related.append({
                        "memory_id": mem["id"],
                        "category": category,
                        "snippet": mem["snippet"],
                        "common_keywords": list(overlap),
                        "timestamp": mem["timestamp"]
                    })
        
        return related[:5]  # Top 5 related memories

    def detect_story_threads(self, user_id: str, session_id: str) -> List[Dict]:
        """Detect recurring themes/people across categories."""
        session_data = self.memory_map.get(user_id, {}).get(session_id, {})
        keyword_map = {}  # keyword -> [(category, memory_id, snippet)]
        
        for category, memories in session_data.items():
            for mem in memories:
                if not mem["response"].strip():
                    continue
                keywords = self.extract_keywords(mem["response"])
                for kw in keywords:
                    if kw not in keyword_map:
                        keyword_map[kw] = []
                    keyword_map[kw].append({
                        "category": category,
                        "memory_id": mem["id"],
                        "snippet": mem["snippet"][:80]
                    })
        
        # Find keywords appearing in multiple categories
        threads = []
        for keyword, occurrences in keyword_map.items():
            categories = set(occ["category"] for occ in occurrences)
            if len(categories) >= 2:  # Appears in 2+ categories
                threads.append({
                    "keyword": keyword,
                    "categories": list(categories),
                    "occurrences": occurrences,
                    "count": len(occurrences)
                })
        
        return sorted(threads, key=lambda x: x["count"], reverse=True)[:10]


memory_service = MemoryService()
