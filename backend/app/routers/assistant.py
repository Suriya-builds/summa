from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user, limit
from ..models import ChatMessage, User
from ..schemas import AskIn
from ..services import analytics, assistant, llm

router = APIRouter(prefix="/api/assistant", tags=["assistant"])

SUGGESTED = [
    "How much did I spend on food this month compared with last month?",
    "What are my subscriptions and what do they cost a year?",
    "What was my biggest expense last month?",
    "Am I on track with my budget this month?",
    "Which day of the week do I spend the most?",
    "Were there any scam messages in my inbox?",
]


def chat_dict(m: ChatMessage) -> dict:
    return {"id": m.id, "role": m.role, "content": m.content, "created_at": m.created_at.isoformat(timespec="seconds"), **(m.meta or {})}


@router.get("/status")
def status(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return {**llm.status(), "has_data": analytics.default_month(db, user.id) is not None, "suggested_questions": SUGGESTED}


@router.get("/history")
def history(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    rows = db.execute(select(ChatMessage).where(ChatMessage.user_id == user.id).order_by(ChatMessage.id.desc()).limit(60)).scalars()
    return {"items": [chat_dict(m) for m in reversed(list(rows))]}


@router.delete("/history")
def clear_history(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    db.execute(delete(ChatMessage).where(ChatMessage.user_id == user.id))
    db.commit()
    return {"ok": True}


@router.post("/ask")
def ask(body: AskIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    if not llm.is_enabled():
        raise HTTPException(status_code=503, detail="The AI assistant is not configured. Set ANTHROPIC_API_KEY on the server to enable it.")
    limit(f"llm:{user.id}", 20, 300, "You are asking the AI too quickly. Wait a minute and try again.")
    question = body.question.strip()
    previous = db.execute(select(ChatMessage).where(ChatMessage.user_id == user.id).order_by(ChatMessage.id.desc()).limit(6)).scalars()
    history_turns = [{"role": m.role, "content": m.content} for m in reversed(list(previous))]
    try:
        result = assistant.ask(db, user.id, question, history_turns)
    except llm.LLMUnavailable as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except assistant.AssistantError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    db.add(ChatMessage(user_id=user.id, role="user", content=question, meta={}))
    reply = ChatMessage(user_id=user.id, role="assistant", content=result["answer"], meta={
        "citations": result["citations"], "tools": result["tools"], "figure_check": result["figure_check"],
    })
    db.add(reply)
    db.commit()
    return chat_dict(reply)
