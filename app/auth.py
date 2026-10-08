from app.clock import utcnow
import hashlib
import hmac
import os
import secrets
import json
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from app.database import get_db
from app.models import LoginSession, RateLimit

router = APIRouter(prefix="/auth", tags=["Access"])


def configured_users():
    """Optional individually named accounts. Fail closed on invalid configuration."""
    raw = os.getenv('APP_USERS_JSON', '')
    if not raw:
        return {}
    try:
        users = json.loads(raw)
        if not isinstance(users, dict) or not users:
            raise ValueError()
        for username, entry in users.items():
            if not isinstance(username, str) or not isinstance(entry, dict) or entry.get('role') not in ('admin', 'analyst'):
                raise ValueError()
            if not isinstance(entry.get('password_hash'), str):
                raise ValueError()
        return users
    except (ValueError, TypeError):
        raise HTTPException(503, 'La configuración de usuarios requiere atención del administrador.') from None


def verify_hash(password, stored):
    try:
        algorithm, rounds, salt, expected = stored.split('$')
        if algorithm != 'pbkdf2_sha256' or not 600000 <= int(rounds) <= 2000000:
            return False
        actual = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), int(rounds)).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False

def limit(db, key, maximum, seconds=60):
    now = utcnow()
    if db.get(RateLimit, key) is None:
        db.add(RateLimit(key=key, count=0, reset_at=now + timedelta(seconds=seconds)))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
    db.execute(update(RateLimit).where(RateLimit.key == key, RateLimit.reset_at <= now)
               .values(count=0, reset_at=now + timedelta(seconds=seconds)))
    result = db.execute(update(RateLimit).where(RateLimit.key == key, RateLimit.count < maximum)
                        .values(count=RateLimit.count + 1))
    db.commit()
    if result.rowcount != 1:
        raise HTTPException(429, "Demasiadas solicitudes. Intenta de nuevo más tarde.", headers={"Retry-After": str(seconds)})

def require_user(request: Request, db=Depends(get_db)):
    token = request.cookies.get("credit_session", "")
    session = db.get(LoginSession, hashlib.sha256(token.encode()).hexdigest())
    if not session or session.expires_at <= utcnow():
        raise HTTPException(401, "Inicia sesión para acceder a los expedientes.")
    individual = configured_users()
    if individual:
        entry = individual.get(session.actor)
        if not entry:
            raise HTTPException(401, 'La cuenta ya no está activa.')
        session.role = entry['role']
    elif session.actor not in ('admin', 'analyst') or not os.getenv('APP_PASSWORD'):
        raise HTTPException(401, 'La cuenta ya no está activa.')
    elif session.actor == 'analyst' and not os.getenv('ANALYST_PASSWORD'):
        raise HTTPException(401, 'La cuenta ya no está activa.')
    if request.method not in ("GET", "HEAD", "OPTIONS") and request.headers.get("X-Credit-Request") != "1":
        raise HTTPException(403, "Cabecera de seguridad requerida.")
    return session

class LoginInput(BaseModel):
    username: str = Field(max_length=80)
    password: str = Field(max_length=256)

@router.post("/login")
def login(data: LoginInput, request: Request, response: Response, db=Depends(get_db)):
    limit(db, "login:" + (request.client.host if request.client else "unknown"), 10, 300)
    individual = configured_users()
    if individual:
        entry = individual.get(data.username, {})
        role = entry.get('role', '')
        valid = verify_hash(data.password, entry.get('password_hash', ''))
    else:
        users = {"admin": ("APP_PASSWORD", "admin"), "analyst": ("ANALYST_PASSWORD", "analyst")}
        env, role = users.get(data.username, ("", ""))
        expected = os.getenv(env, "") if env else ""
        valid = len(expected) >= 12 and hmac.compare_digest(data.password.encode(), expected.encode())
    if not individual and not os.getenv("APP_PASSWORD"):
        raise HTTPException(503, "Configura APP_PASSWORD en el servidor para habilitar el espacio privado.")
    if not valid:
        raise HTTPException(401, "Usuario o contraseña incorrectos.")
    token = secrets.token_urlsafe(32)
    db.add(LoginSession(token_hash=hashlib.sha256(token.encode()).hexdigest(), actor=data.username,
                        role=role, expires_at=utcnow() + timedelta(hours=8)))
    db.commit()
    response.set_cookie("credit_session", token, httponly=True, secure=bool(os.getenv("RENDER")) or os.getenv("COOKIE_SECURE") == "true", samesite="strict", max_age=28800)
    return {"username": data.username, "role": role}

@router.get("/me")
def me(user=Depends(require_user)):
    return {"username": user.actor, "role": user.role}

@router.post("/logout")
def logout(response: Response, user=Depends(require_user), db=Depends(get_db)):
    db.delete(user)
    db.commit()
    response.delete_cookie("credit_session")
    return {"ok": True}
