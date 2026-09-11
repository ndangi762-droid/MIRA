from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pathlib import Path
from app.api.routes import router

app = FastAPI(title="MIRA", version="2.0.0")
app.include_router(router)

@app.get("/", response_class=HTMLResponse)
def home():
    return (Path(__file__).parent / "web" / "index.html").read_text(encoding="utf-8")
