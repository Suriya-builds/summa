from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import COOKIE_NAME, get_current_user
from ..models import Budget, ChatMessage, MerchantRule, Message, Transaction, User
from ..services import categorizer, llm, scam_detector
from ..services.categories import DISCRETIONARY, EXPENSE_CATEGORIES, INCOME_CATEGORIES, NON_SPEND_CATEGORIES

router = APIRouter(prefix="/api", tags=["account"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/meta")
def meta() -> dict:
    """Static reference data and honest model cards for the two local classifiers."""
    scam_detector.text_model.get()
    categorizer.merchant_model.get()
    return {
        "categories": {
            "expense": [{"id": k, "label": v, "counts_as_spend": k not in NON_SPEND_CATEGORIES,
                         "discretionary": k in DISCRETIONARY} for k, v in EXPENSE_CATEGORIES.items()],
            "income": [{"id": k, "label": v} for k, v in INCOME_CATEGORIES.items()],
        },
        "llm": llm.status(),
        "models": {"scam_text": scam_detector.text_model.metrics, "merchant_category": categorizer.merchant_model.metrics},
        "scam_thresholds": {"suspicious": scam_detector.SUSPICIOUS_AT, "dangerous": scam_detector.DANGEROUS_AT},
    }


@router.get("/account/overview")
def overview(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    def count(model) -> int:
        return db.execute(select(func.count()).select_from(model).where(model.user_id == user.id)).scalar_one()

    first, last = db.execute(
        select(func.min(Transaction.occurred_at), func.max(Transaction.occurred_at)).where(Transaction.user_id == user.id)
    ).one()
    return {
        "messages": count(Message), "transactions": count(Transaction), "budgets": count(Budget),
        "merchant_rules": count(MerchantRule), "chat_messages": count(ChatMessage),
        "first_transaction": first.date().isoformat() if first else None,
        "last_transaction": last.date().isoformat() if last else None,
    }


@router.delete("/account/data")
def delete_data(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """Remove everything imported or created by the user, keeping the login."""
    for model in (Transaction, Message, Budget, MerchantRule, ChatMessage):
        db.execute(delete(model).where(model.user_id == user.id))
    db.commit()
    return {"ok": True}


@router.delete("/account")
def delete_account(response: Response, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    for model in (Transaction, Message, Budget, MerchantRule, ChatMessage):
        db.execute(delete(model).where(model.user_id == user.id))
    db.delete(db.get(User, user.id))
    db.commit()
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}
