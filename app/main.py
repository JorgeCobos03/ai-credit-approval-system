import os
import time
import uuid
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from app.database import engine, Base
from app import models
from app.auth import router as auth_router
from app.routes import applications, score, dashboard
from app.request_limits import BodyLimitMiddleware

logger = logging.getLogger("creditos")

@asynccontextmanager
async def lifespan(app):
    # Additive schema: preserves the original applications table and records.
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title="CreditOS · Credit Operations", version="2.0.0", lifespan=lifespan)
app.add_middleware(BodyLimitMiddleware)
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
for router in (auth_router, applications.router, score.router, dashboard.router):
    app.include_router(router)

@app.middleware("http")
async def security(request, call_next):
    request_id = str(uuid.uuid4())
    start = time.monotonic()
    length = request.headers.get("content-length", "")
    if length and (not length.isdigit() or int(length) > 9 * 1024 * 1024):
        return JSONResponse({"detail": "La solicitud supera el límite de 9 MB."}, status_code=413)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    if not request.url.path.startswith(("/docs", "/redoc")):
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    response.headers["Cache-Control"] = "no-store" if not request.url.path.startswith("/static/") else "no-cache"
    logger.info("request id=%s method=%s status=%s duration_ms=%d", request_id, request.method, response.status_code, (time.monotonic()-start)*1000)
    return response

@app.get("/")
def root():
    return FileResponse(STATIC_DIR / "index.html")

@app.get("/health")
def health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(503, "Database unavailable") from None
    return {"status": "ok", "version": "2.0.0"}

@app.get("/config")
def config():
    return {"login_configured": bool(os.getenv("APP_PASSWORD") or os.getenv("APP_USERS_JSON")),
            "ai_configured": bool(os.getenv("OPENAI_API_KEY")), "version": "2.0.0"}
