#app.services.memory_services.py

from typing import Dict, List 

class MemoryService:
    
    def __init__(self):
        self.memory: Dict[str, List[dict]] ={}
    

    def get_history(self, user_id:str) -> List[dict]:
        return self.memory.get(user_id, [])
    
    def add_message(self, user_id:str, role:str, content:str):
        if user_id not in self.memory:
            self.memory[user_id] =[]
        self.memory[user_id].append({"role":role, "content": content})
    
    def clear(self, user_id: str):
        self.memory[user_id] = []
