from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.database import engine, Base
from app.routes import applications, score, dashboard


app = FastAPI(
    title="AI Credit Approval System",
    version="1.0.0"
)

Base.metadata.create_all(bind=engine)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.include_router(applications.router)
app.include_router(score.router)
app.include_router(dashboard.router)


@app.get("/")
def root():
    return FileResponse(STATIC_DIR / "index.html")
