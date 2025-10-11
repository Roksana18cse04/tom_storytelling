#app/main.py

from fastapi import FastAPI 
from app.api.routes import interview, history

app= FastAPI()

app.include_router(interview.router,prefix="/ai", tags=["Interview mode"])
app.include_router(history.router,prefix="/ai", tags=["History"])