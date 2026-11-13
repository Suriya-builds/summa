from __future__ import annotations

import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..deps import COOKIE_NAME, client_ip, get_current_user, limit
from ..models import AuthSession, User, utcnow
from ..schemas import LoginIn, SignupIn
from ..security import hash_password, hash_token, new_session_token, verify_password
from ..services import budgets, pipeline, sample_data

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Hashing a throwaway password on unknown emails keeps response time the same for both cases.
_DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


def user_dict(user: User) -> dict:
    return {"id": user.id, "name": user.name, "email": user.email, "is_demo": user.is_demo}


def start_session(db: Session, user: User, response: Response) -> None:
    token = new_session_token()
    db.add(AuthSession(user_id=user.id, token_hash=hash_token(token),
                       expires_at=utcnow() + timedelta(days=settings.session_days)))
    db.commit()
    response.set_cookie(
        COOKIE_NAME, token, max_age=settings.session_days * 86400, httponly=True, samesite="strict",
        secure=settings.cookie_secure, path="/",
    )


@router.post("/signup", status_code=201)
def signup(body: SignupIn, request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    limit(f"signup:{client_ip(request)}", 10, 3600)
    if db.execute(select(User.id).where(User.email == body.email)).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists. Try logging in.")
    user = User(email=body.email, name=body.name, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    start_session(db, user, response)
    return {"user": user_dict(user)}


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    limit(f"login:{client_ip(request)}", 20, 300, "Too many login attempts. Wait a few minutes and try again.")
    limit(f"login:{body.email}", 8, 300, "Too many login attempts. Wait a few minutes and try again.")
    user = db.execute(select(User).where(User.email == body.email)).scalar_one_or_none()
    valid = verify_password(body.password, user.password_hash if user else _DUMMY_HASH)
    if user is None or not valid or user.is_demo:
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    db.execute(delete(AuthSession).where(AuthSession.expires_at < utcnow()))
    start_session(db, user, response)
    return {"user": user_dict(user)}


@router.post("/demo", status_code=201)
def demo(request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    """Create a throwaway account and run a synthetic inbox through the real import pipeline."""
    limit(f"demo:{client_ip(request)}", 20, 3600)
    cutoff = utcnow() - timedelta(hours=24)
    for stale in db.execute(select(User).where(User.is_demo.is_(True), User.created_at < cutoff)).scalars():
        db.delete(stale)
    user = User(
        email=f"demo-{secrets.token_hex(6)}@demo.summa.invalid",
        name="Demo User",
        password_hash=hash_password(secrets.token_urlsafe(24)),
        is_demo=True,
    )
    db.add(user)
    db.commit()
    result = pipeline.import_messages(db, user, sample_data.generate_inbox())
    suggested = budgets.suggestions(db, user.id)
    budgets.save_limits(db, user.id, {item["category"]: item["suggested"] for item in suggested["items"]})
    start_session(db, user, response)
    return {"user": user_dict(user), "import": result.as_dict()}


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    token = request.cookies.get(COOKIE_NAME)
    if token:
        session = db.execute(select(AuthSession).where(AuthSession.token_hash == hash_token(token))).scalar_one_or_none()
        if session is not None:
            db.delete(session)
            db.commit()
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me")
def me(request: Request, db: Session = Depends(get_db)) -> dict:
    """The signed-in user, or null. Returns 200 either way so a logged-out page load is not an error."""
    try:
        return {"user": user_dict(get_current_user(request, db))}
    except HTTPException:
        return {"user": None}
