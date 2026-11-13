"""Request dependencies: the current user and rate limiting."""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_db
from .models import AuthSession, User, utcnow
from .security import hash_token, rate_limiter

COOKIE_NAME = "summa_session"


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Please log in.")
    session = db.execute(select(AuthSession).where(AuthSession.token_hash == hash_token(token))).scalar_one_or_none()
    if session is None or session.expires_at < utcnow():
        raise HTTPException(status_code=401, detail="Your session has expired. Please log in again.")
    user = db.get(User, session.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Please log in.")
    return user


def limit(key: str, max_hits: int, window_seconds: int, message: str = "Too many requests. Please wait and try again.") -> None:
    if not rate_limiter.allow(key, max_hits, window_seconds):
        raise HTTPException(status_code=429, detail=message)
