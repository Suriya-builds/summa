from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user, limit
from ..models import User
from ..schemas import NarrativeIn
from ..services import analytics, assistant, llm
from ..services.timeutil import is_month_key, month_key, now_ist

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def resolve_month(db: Session, user: User, month: str | None) -> str:
    if month:
        if not is_month_key(month):
            raise HTTPException(status_code=422, detail="month must look like 2026-11.")
        return month
    return analytics.default_month(db, user.id) or month_key(now_ist())


@router.get("/months")
def months(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return {"months": analytics.available_months(db, user.id), "default": analytics.default_month(db, user.id)}


@router.get("/summary")
def summary(month: str | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return analytics.summary(db, user.id, resolve_month(db, user, month))


@router.get("/trend")
def trend(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return {"months": analytics.monthly_trend(db, user.id)}


@router.get("/recurring")
def recurring(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return analytics.recurring(db, user.id)


@router.get("/anomalies")
def anomalies(month: str | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    if month and not is_month_key(month):
        raise HTTPException(status_code=422, detail="month must look like 2026-11.")
    return {"items": analytics.anomalies(db, user.id, month)}


@router.get("/insights")
def insights(month: str | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    resolved = resolve_month(db, user, month)
    return {"month": resolved, "items": analytics.insights(db, user.id, resolved), "ai_available": llm.is_enabled()}


@router.post("/insights/narrative")
def narrative(body: NarrativeIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """Rewrite the computed insights as a short paragraph. Needs an LLM key."""
    limit(f"llm:{user.id}", 20, 300, "You are asking the AI too quickly. Wait a minute and try again.")
    resolved = resolve_month(db, user, body.month)
    facts = analytics.insights(db, user.id, resolved)
    if not facts:
        raise HTTPException(status_code=422, detail="There is no data for this month yet.")
    try:
        text = assistant.narrate_insights(resolved, facts, analytics.summary(db, user.id, resolved))
    except llm.LLMUnavailable as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except assistant.AssistantError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    check = assistant.check_figures(text, facts + [analytics.summary(db, user.id, resolved)])
    return {"month": resolved, "narrative": text, "figure_check": check}
