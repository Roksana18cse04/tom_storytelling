import json, os, uuid, datetime, re
from typing import Dict, List

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
            self.user_phase[user_id][session_id] = "childhood"
            self._save_memory()
        return self.user_phase[user_id][session_id]

    def set_phase(self, user_id: str, session_id: str, phase: str):
        self.user_phase.setdefault(user_id, {})[session_id] = phase
        self._save_memory()

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
                   question: str, response: str, photos=None, audio_clips=None, contributors=None):
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


memory_service = MemoryService()
