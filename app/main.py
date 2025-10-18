#app/main.py

from fastapi import FastAPI 
from app.api.routes import interview, history, memory_map, story, photo_story

app= FastAPI()

app.include_router(interview.router,prefix="/ai", tags=["Interview mode"])
app.include_router(memory_map.router, prefix="/ai/memory", tags= ["Memory map"])
app.include_router(story.router, prefix="/ai/story", tags=["Story builder"])
app.include_router(photo_story.router, prefix="/ai", tags=["Photo Story"])
app.include_router(history.router,prefix="/ai", tags=["History"])