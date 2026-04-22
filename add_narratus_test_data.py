"""
Script to add sample memories for testing Narratus framework
"""
import asyncio
from app.services.memory_services_mongodb import mongo_memory_service as memory_service

async def add_test_memories():
    user_id = "narratus_demo"
    session_id = "demo_session_001"
    
    # Set phase to childhood
    await memory_service.set_phase(user_id, session_id, "childhood")
    
    # Add contextual memory (should be compressed)
    await memory_service.add_memory(
        user_id=user_id,
        session_id=session_id,
        category="childhood",
        question="Where and when were you born?",
        response="I was born in 1995 in a small village called Mirkadim under Sreepur Upazila in Gazipur district. My family lived in a modest house near the local school.",
        display_text="Where and when were you born?"
    )
    
    # Add formative memory (should be expanded)
    await memory_service.add_memory(
        user_id=user_id,
        session_id=session_id,
        category="childhood",
        question="Tell me about your early school experiences.",
        response="School was where I learned to be independent. My parents couldn't always help with homework, so I figured things out myself. That taught me to be resourceful. I also made my first real friends there - we'd play cricket after class every single day. Those friendships shaped how I value loyalty and teamwork even now.",
        display_text="Tell me about your early school experiences."
    )
    
    # Add emotional anchor (should be elevated)
    await memory_service.add_memory(
        user_id=user_id,
        session_id=session_id,
        category="childhood",
        question="What's a childhood moment that deeply affected you?",
        response="When I was 10 years old, my grandfather passed away. He used to tell me stories every night before bed. The night he died, I couldn't sleep because there was no story. I didn't understand death then, but I felt this huge emptiness. Looking back, that loss taught me that the people we love stay with us through the memories and lessons they leave behind. His stories are still with me.",
        display_text="What's a childhood moment that deeply affected you?"
    )
    
    # Add more contextual
    await memory_service.add_memory(
        user_id=user_id,
        session_id=session_id,
        category="childhood",
        question="What did your parents do for a living?",
        response="My father was a school teacher and my mother was a homemaker. We weren't wealthy, but we had everything we needed. My father's salary was modest, around 8,000 taka per month back then.",
        display_text="What did your parents do for a living?"
    )
    
    # Add formative with reflection
    await memory_service.add_memory(
        user_id=user_id,
        session_id=session_id,
        category="childhood",
        question="What values did your family instill in you?",
        response="My parents always emphasized education and honesty. They'd say, 'We can't give you wealth, but we can give you education.' That stuck with me. Even when money was tight, my education was never compromised. I learned that knowledge is the one thing no one can take from you. That belief pushed me to study hard and never take learning for granted.",
        display_text="What values did your family instill in you?"
    )
    
    print(f"✅ Added 5 test memories for user: {user_id}, session: {session_id}")
    print(f"Categories: Contextual (2), Formative (2), Emotional Anchor (1)")
    print(f"\nNow you can test story generation:")
    print(f"GET /ai/story/chapter/{user_id}/{session_id}/childhood?style=conversational")

if __name__ == "__main__":
    asyncio.run(add_test_memories())
