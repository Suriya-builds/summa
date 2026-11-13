from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import BudgetsIn
from ..services import budgets
from .analytics import resolve_month

router = APIRouter(prefix="/api/budgets", tags=["budgets"])


@router.get("")
def get_budgets(month: str | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return budgets.status(db, user.id, resolve_month(db, user, month))


@router.get("/suggestions")
def get_suggestions(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return budgets.suggestions(db, user.id)


@router.put("")
def put_budgets(body: BudgetsIn, month: str | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    for category, amount in body.limits.items():
        if category not in budgets.BUDGETABLE:
            raise HTTPException(status_code=422, detail=f"'{category}' cannot have a budget.")
        if amount < 0 or amount > 10_000_000:
            raise HTTPException(status_code=422, detail="Budget amounts must be between 0 and 1,00,00,000.")
    budgets.save_limits(db, user.id, body.limits)
    return budgets.status(db, user.id, resolve_month(db, user, month))
