from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response

from app.api.routes import router
from app.api.pc_control import router as pc_router
from app.config import MIRA_NAME


app = FastAPI(title=MIRA_NAME, version="7.4.1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"]
)
app.include_router(router)
app.include_router(pc_router)


@app.get("/", response_class=HTMLResponse)
def home():
    html = (Path(__file__).parent / "web" / "index.html").read_text(encoding="utf-8")
    # Version query prevents an old browser/service-worker cached PC-control script
    # from silently bypassing the live PC command path.
    return html.replace("</body>", '<script src="/voice.js?v=pc3"></script><script src="/document.js?v=pc3"></script><script src="/pc-control.js?v=pc3"></script></body>')


@app.get("/voice.js")
def voice_script():
    return Response(
        content=(Path(__file__).parent / "web" / "voice.js").read_text(encoding="utf-8"),
        media_type="application/javascript",
    )


@app.get("/document.js")
def document_script():
    return Response(
        content=(Path(__file__).parent / "web" / "document.js").read_text(encoding="utf-8"),
        media_type="application/javascript",
    )


@app.get("/pc-control.js")
def pc_control_script():
    return Response(
        content=(Path(__file__).parent / "web" / "pc-control.js").read_text(encoding="utf-8"),
        media_type="application/javascript",
        headers={"Cache-Control": "no-store"},
    )
