#app/main.py

from fastapi import FastAPI 
from app.api.routes import interview, history, memory_map, story, photo_story
import os


app= FastAPI()


import psutil
import os

process = psutil.Process(os.getpid())

# Convert from bytes → GB
ram_usage_gb = process.memory_info().rss / (1024 ** 3)
total_ram_gb = psutil.virtual_memory().total / (1024 ** 3)

print(f"Total system RAM: {total_ram_gb:.2f} GB")
print(f"Used by this process: {ram_usage_gb:.2f} GB")







app.include_router(interview.router,prefix="/ai", tags=["Interview mode"])
app.include_router(memory_map.router, prefix="/ai/memory", tags= ["Memory map"])
app.include_router(story.router, prefix="/ai/story", tags=["Story builder"])
app.include_router(photo_story.router, prefix="/ai", tags=["Photo Story"])
app.include_router(history.router,prefix="/ai", tags=["History"])

