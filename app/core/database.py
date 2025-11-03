# app/core/database.py

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

# MongoDB client
client = AsyncIOMotorClient(settings.mongo_url)
# Extract database name from connection string
db_name = settings.mongo_url.split("/")[-1].split("?")[0]
db = client[db_name]

# Collections
memories_collection = db["memories"]
user_phases_collection = db["user_phases"]
