from __future__ import annotations

import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import MerchantRule, Transaction, User
from ..schemas import TransactionCreate, TransactionPatch
from ..services import analytics, categorizer, pipeline
from ..services.categories import valid_for
from ..services.sms_parser import counterparty_key
from ..services.timeutil import is_month_key, month_bounds

router = APIRouter(prefix="/api/transactions", tags=["transactions"])

SORTS = {
    "date_desc": Transaction.occurred_at.desc(),
    "date_asc": Transaction.occurred_at.asc(),
    "amount_desc": Transaction.amount_paise.desc(),
    "amount_asc": Transaction.amount_paise.asc(),
}


def _filtered(user_id: int, month, category, direction, q, min_amount, max_amount):
    query = select(Transaction).where(Transaction.user_id == user_id)
    if month:
        if not is_month_key(month):
            raise HTTPException(status_code=422, detail="month must look like 2026-11.")
        start, end = month_bounds(month)
        query = query.where(Transaction.occurred_at >= start, Transaction.occurred_at < end)
    if category:
        query = query.where(Transaction.category == category)
    if direction:
        if direction not in ("debit", "credit"):
            raise HTTPException(status_code=422, detail="direction must be debit or credit.")
        query = query.where(Transaction.direction == direction)
    if q:
        needle = q.strip().lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(func.lower(Transaction.counterparty).like(f"%{needle}%", escape="\\"))
    if min_amount is not None:
        query = query.where(Transaction.amount_paise >= int(round(min_amount * 100)))
    if max_amount is not None:
        query = query.where(Transaction.amount_paise <= int(round(max_amount * 100)))
    return query


def _own(db: Session, user: User, txn_id: int) -> Transaction:
    txn = db.execute(select(Transaction).where(Transaction.id == txn_id, Transaction.user_id == user.id)).scalar_one_or_none()
    if txn is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    return txn


@router.get("")
def list_transactions(
    month: str | None = None,
    category: str | None = None,
    direction: str | None = None,
    q: str | None = Query(None, max_length=80),
    min_amount: float | None = Query(None, ge=0),
    max_amount: float | None = Query(None, ge=0),
    sort: str = "date_desc",
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if sort not in SORTS:
        raise HTTPException(status_code=422, detail=f"sort must be one of {', '.join(SORTS)}.")
    base = _filtered(user.id, month, category, direction, q, min_amount, max_amount)
    sub = base.subquery()
    total, debit_sum, credit_sum = db.execute(
        select(
            func.count(),
            func.coalesce(func.sum(sub.c.amount_paise).filter(sub.c.direction == "debit"), 0),
            func.coalesce(func.sum(sub.c.amount_paise).filter(sub.c.direction == "credit"), 0),
        ).select_from(sub)
    ).one()
    rows = db.execute(base.order_by(SORTS[sort], Transaction.id.desc()).offset((page - 1) * page_size).limit(page_size)).scalars()
    return {
        "items": [analytics.txn_dict(t) for t in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_debit": analytics.rupees(debit_sum),
        "total_credit": analytics.rupees(credit_sum),
    }


@router.get("/export.csv")
def export_csv(month: str | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    rows = db.execute(_filtered(user.id, month, None, None, None, None, None).order_by(Transaction.occurred_at)).scalars()

    def safe(value) -> str:
        # Prefix cells a spreadsheet would treat as a formula.
        text = "" if value is None else str(value)
        return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["date", "direction", "amount", "counterparty", "category", "channel", "account", "reference", "note"])
    for t in rows:
        writer.writerow([
            t.occurred_at.isoformat(timespec="minutes"), t.direction, f"{t.amount_paise / 100:.2f}", safe(t.counterparty),
            analytics.label(t.category), t.channel, t.account_tail or "", safe(t.reference), safe(t.note),
        ])
    filename = f"summa-transactions-{month or 'all'}.csv"
    return Response(buffer.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.post("", status_code=201)
def create_transaction(body: TransactionCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """Add a transaction by hand, for example a cash payment that produced no SMS."""
    try:
        occurred = datetime.fromisoformat(body.date)
    except ValueError:
        raise HTTPException(status_code=422, detail="date must be YYYY-MM-DD or YYYY-MM-DDTHH:MM.") from None
    occurred = occurred.replace(tzinfo=None)
    if len(body.date) <= 10:
        occurred = occurred.replace(hour=12)
    if not (2000 <= occurred.year <= 2100):
        raise HTTPException(status_code=422, detail="date is out of range.")
    allowed = valid_for(body.direction)
    if body.category:
        if body.category not in allowed:
            raise HTTPException(status_code=422, detail="That category does not apply to this kind of transaction.")
        category, source, confidence = body.category, "user", 1.0
    else:
        result = categorizer.categorise(body.counterparty, body.direction, "", pipeline.user_rules(db, user.id))
        category, source, confidence = result.category, result.source, result.confidence
    name = body.counterparty.strip()
    txn = Transaction(
        user_id=user.id, occurred_at=occurred, amount_paise=int(round(body.amount * 100)), direction=body.direction,
        counterparty=name, counterparty_key=counterparty_key(name), channel="manual", category=category,
        category_source=source, category_confidence=confidence, note=(body.note or None),
    )
    db.add(txn)
    db.commit()
    return {"transaction": analytics.txn_dict(txn)}


@router.patch("/{txn_id}")
def update_transaction(txn_id: int, body: TransactionPatch, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    txn = _own(db, user, txn_id)
    updated_others = 0
    if body.counterparty is not None:
        txn.counterparty = body.counterparty.strip()
        txn.counterparty_key = counterparty_key(txn.counterparty)
    if body.note is not None:
        txn.note = body.note.strip() or None
    if body.category is not None and body.category != txn.category:
        if body.category not in valid_for(txn.direction):
            raise HTTPException(status_code=422, detail="That category does not apply to this kind of transaction.")
        txn.category, txn.category_source, txn.category_confidence = body.category, "user", 1.0
        if body.apply_to_merchant and txn.direction == "debit" and txn.counterparty_key != "unknown":
            rule = db.execute(select(MerchantRule).where(
                MerchantRule.user_id == user.id, MerchantRule.counterparty_key == txn.counterparty_key)).scalar_one_or_none()
            if rule is None:
                db.add(MerchantRule(user_id=user.id, counterparty_key=txn.counterparty_key, category=body.category))
            else:
                rule.category = body.category
            others = db.execute(select(Transaction).where(
                Transaction.user_id == user.id, Transaction.counterparty_key == txn.counterparty_key,
                Transaction.direction == "debit", Transaction.id != txn.id)).scalars()
            for other in others:
                if other.category != body.category:
                    other.category, other.category_source, other.category_confidence = body.category, "user", 1.0
                    updated_others += 1
    db.commit()
    return {"transaction": analytics.txn_dict(txn), "also_updated": updated_others}


@router.delete("/{txn_id}")
def delete_transaction(txn_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    db.delete(_own(db, user, txn_id))
    db.commit()
    return {"ok": True}
