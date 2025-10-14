#app/services/memory_services.py

import json, os, uuid, datetime, re
from typing import Dict, List


class MemoryService:
    def __init__(self):
        self.file_path = "memory.json"
        self.memory_map: Dict[str, Dict[str, List[dict]]] = {}  # user_id -> {category -> memories}
        self.user_phase: Dict[str, str] = {}  # current life phase
        self._load_memory()

    # ─── Load & Save ─────────────────────────────────────────────────────────
    def _load_memory(self):
        """Load existing memory file safely."""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r") as f:
                    data = json.load(f)
                    self.memory_map = data.get("memory_map", {})
                    self.user_phase = data.get("user_phase", {})
            except json.JSONDecodeError:
                self.memory_map, self.user_phase = {}, {}

    def _save_memory(self):
        """Persist current memory state."""
        with open(self.file_path, "w") as f:
            json.dump({
                "memory_map": self.memory_map,
                "user_phase": self.user_phase
            }, f, indent=2)

    # ─── Phase Handling ─────────────────────────────────────────────────────
    def get_phase(self, user_id: str) -> str:
        """Return user's current phase, default to childhood."""
        return self.user_phase.get(user_id, "childhood")

    def set_phase(self, user_id: str, phase: str):
        """Set user's current life phase."""
        self.user_phase[user_id] = phase
        self._save_memory()

    # ─── generate snippet ───────────────────────────────────────────────────
    def _generate_snippet(self, response: str, max_length: int = 120) -> str:
        """
        Extracts the first sentence or short preview from user's story.
        """
        if not response:
            return ""
        # Split by sentence-ending punctuation
        sentence = re.split(r'(?<=[.!?]) +', response.strip())[0]
        snippet = sentence.strip()
        if len(snippet) > max_length:
            snippet = snippet[:max_length].rsplit(" ", 1)[0] + "..."
        return snippet

    # ─── Memory Management ────────────────────────────────────────────────────
    def add_memory(self, user_id: str, category: str, question: str, response: str,
                   photos: List[str] = None, audio_clips: List[str] = None,
                   contributors: List[str] = None):
        photos = photos or []
        audio_clips = audio_clips or []
        contributors = contributors or []

        snippet = self._generate_snippet(response)

        memory_entry = {
            "id": str(uuid.uuid4()),
            "question": question,
            "response": response,
            "snippet": snippet,
            "photos": photos,
            "audio_clips": audio_clips,
            "contributors": contributors,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }

        if user_id not in self.memory_map:
            self.memory_map[user_id] = {}
        if category not in self.memory_map[user_id]:
            self.memory_map[user_id][category] = []

        self.memory_map[user_id][category].append(memory_entry)
        self._save_memory()

    def get_user_memories(self, user_id: str):
        """Return all categories & memories for a user."""
        return self.memory_map.get(user_id, {})

    def get_category_memories(self, user_id: str, category: str):
        """Return all memories for a specific category."""
        user_data = self.memory_map.get(user_id, {})
        return user_data.get(category, [])

    def clear_user(self, user_id: str):
        """Reset all memory and phase for a user."""
        self.memory_map[user_id] = {}
        self.user_phase[user_id] = "childhood"
        self._save_memory()

    def get_formatted_history(self, user_id: str) -> str:
        """
        Returns all memories for a user as formatted text.
        Combines all categories sequentially.
        """
        user_data = self.memory_map.get(user_id, {})
        formatted_lines = []
        for category, memories in user_data.items():
            formatted_lines.append(f"--- {category.upper()} ---")
            for mem in memories:
                formatted_lines.append(f"Q: {mem['question']}")
                formatted_lines.append(f"A: {mem['response']}\n")
        return "\n".join(formatted_lines)

    # ─── Helpers for LLM ─────────────────────────────────────────────────────
    def get_history(self, user_id: str):
        """Return a chronological conversation-like history."""
        user_data = self.memory_map.get(user_id, {})
        history = []
        for category, memories in user_data.items():
            for mem in memories:
                if mem["question"]:
                    history.append({"role": "Assistant", "content": mem["question"]})
                if mem["response"]:
                    history.append({"role": "User", "content": mem["response"]})
        return history

    def add_message(self, user_id: str, role: str, content: str):
        """Store assistant messages only; user messages are paired elsewhere."""
        category = self.get_phase(user_id)
        if role == "Assistant":
            self.add_memory(user_id, category, content, "")



# Singleton instance
memory_service = MemoryService()


# from typing import Dict, List
# import json, os

# class MemoryService:
#     def __init__(self):
#         self.memory: Dict[str, List[dict]] = {}
#         self.user_phase: Dict[str, str] = {}
#         self.file_path = "memory.json"
#         self._load_memory()

#     def _load_memory(self):
#         if os.path.exists(self.file_path):
#             with open(self.file_path, "r") as f:
#                 data = json.load(f)
#                 self.memory = data.get("memory", {})
#                 self.user_phase = data.get("user_phase", {})

#     def _save_memory(self):
#         with open(self.file_path, "w") as f:
#             json.dump({"memory": self.memory, "user_phase": self.user_phase}, f, indent=2)

#     def get_history(self, user_id: str):
#         return self.memory.get(user_id, [])

#     def add_message(self, user_id: str, role: str, content: str):
#         if user_id not in self.memory:
#             self.memory[user_id] = []
#         self.memory[user_id].append({"role": role, "content": content})
#         self._save_memory()

#     def get_phase(self, user_id: str):
#         return self.user_phase.get(user_id, "childhood")

#     def set_phase(self, user_id: str, phase: str):
#         self.user_phase[user_id] = phase
#         self._save_memory()

#     def clear(self, user_id: str):
#         self.memory[user_id] = []
#         self.user_phase[user_id] = "childhood"
#         self._save_memory()

#     def get_formatted_history(self, user_id: str):
#         history = self.get_history(user_id)
#         return "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in history])


# # ✅ Shared instance for global use
# memory_service = MemoryService()

