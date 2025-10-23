# app/core/database.py

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

# MongoDB client
client = AsyncIOMotorClient(settings.mongo_url)
db = client["TomWiffenDb"]

# Collections
memories_collection = db["memories"]
user_phases_collection = db["user_phases"]
