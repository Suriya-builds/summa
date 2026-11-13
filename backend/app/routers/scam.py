from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user, limit
from ..models import Message, User
from ..schemas import ScamCheckIn
from ..services import analytics, assistant, llm, pipeline, scam_detector

router = APIRouter(prefix="/api/scam", tags=["scam"])


def alert_dict(m: Message) -> dict:
    return {
        "id": m.id,
        "sender": m.sender,
        "body": m.body,
        "received_at": m.received_at.isoformat(timespec="minutes"),
        "score": round(m.scam_score, 3),
        "level": m.scam_level,
        "reasons": m.scam_reasons or [],
        "advice": scam_detector.ADVICE.get(m.scam_level, ""),
        "dismissed": m.dismissed,
    }


@router.get("/alerts")
def alerts(include_dismissed: bool = False, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    query = select(Message).where(Message.user_id == user.id, Message.scam_level != "safe")
    if not include_dismissed:
        query = query.where(Message.dismissed.is_(False))
    rows = db.execute(query.order_by(Message.scam_score.desc(), Message.received_at.desc()).limit(200)).scalars()
    scanned = db.query(Message).filter(Message.user_id == user.id).count()
    return {"counts": analytics.scam_counts(db, user.id), "scanned": scanned, "items": [alert_dict(m) for m in rows]}


@router.post("/check")
def check(body: ScamCheckIn, user: User = Depends(get_current_user)) -> dict:
    """Score any message the user pastes. Nothing is stored."""
    limit(f"scamcheck:{user.id}", 60, 300)
    verdict = scam_detector.score_message(body.text, body.sender).as_dict()
    verdict["links"] = scam_detector.extract_links(body.text)[:10]
    verdict["ai_explanation"] = None
    verdict["ai_error"] = None
    if body.explain:
        limit(f"llm:{user.id}", 20, 300, "You are asking the AI too quickly. Wait a minute and try again.")
        try:
            verdict["ai_explanation"] = assistant.explain_scam(body.text, verdict)
        except (llm.LLMUnavailable, assistant.AssistantError) as exc:
            verdict["ai_error"] = str(exc)
    return verdict


@router.post("/alerts/{message_id}/dismiss")
def dismiss(message_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """The user says this message is genuine. If it is a bank alert, record its transaction."""
    message = db.execute(select(Message).where(Message.id == message_id, Message.user_id == user.id)).scalar_one_or_none()
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found.")
    message.dismissed = True
    txn = pipeline.reparse_as_transaction(db, user, message)
    if txn is None and message.kind == "scam":
        message.kind = "other"
    db.commit()
    return {"ok": True, "transaction": analytics.txn_dict(txn) if txn else None}


@router.post("/alerts/{message_id}/restore")
def restore(message_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    message = db.execute(select(Message).where(Message.id == message_id, Message.user_id == user.id)).scalar_one_or_none()
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found.")
    message.dismissed = False
    if message.kind == "other":
        message.kind = "scam"
    db.commit()
    return {"ok": True}
