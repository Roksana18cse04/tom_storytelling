#app/main.py

from fastapi import FastAPI 
from app.api.routes import interview, history, memory_map

app= FastAPI()

app.include_router(interview.router,prefix="/ai", tags=["Interview mode"])
app.include_router(memory_map.router, prefix="/ai", tags= ["Memory map"])
app.include_router(history.router,prefix="/ai", tags=["History"])