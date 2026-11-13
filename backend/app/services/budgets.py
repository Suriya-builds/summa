"""Monthly budgets: suggestions from history, progress and month-end projection."""
from __future__ import annotations

import math
import statistics
from collections import defaultdict
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Budget
from . import analytics
from .categories import DISCRETIONARY, EXPENSE_CATEGORIES, NON_SPEND_CATEGORIES, label
from .timeutil import month_key, now_ist

BUDGETABLE = [c for c in EXPENSE_CATEGORIES if c not in NON_SPEND_CATEGORIES]
TRIM = 0.10  # suggested cut on discretionary categories


def get_limits(db: Session, user_id: int) -> dict[str, int]:
    rows = db.execute(select(Budget.category, Budget.monthly_limit_paise).where(Budget.user_id == user_id))
    return {category: limit for category, limit in rows}


def save_limits(db: Session, user_id: int, limits: dict[str, float]) -> None:
    """Replace the user's budgets. A limit of zero removes the budget for that category."""
    existing = {b.category: b for b in db.execute(select(Budget).where(Budget.user_id == user_id)).scalars()}
    for category, amount in limits.items():
        paise = int(round(amount * 100))
        current = existing.get(category)
        if paise <= 0:
            if current is not None:
                db.delete(current)
        elif current is None:
            db.add(Budget(user_id=user_id, category=category, monthly_limit_paise=paise))
        else:
            current.monthly_limit_paise = paise
    db.commit()


def status(db: Session, user_id: int, month: str, today: datetime | None = None) -> dict:
    limits = get_limits(db, user_id)
    progress = analytics.month_progress(month, today)
    recurring_items = analytics.recurring(db, user_id, today)["items"]
    recurring_keys = {i["counterparty_key"] for i in recurring_items}

    # Fixed payments (rent, subscriptions) happen once a month, so only the rest is extrapolated.
    spent: dict[str, int] = defaultdict(int)
    fixed: dict[str, int] = defaultdict(int)
    paid_keys: set[str] = set()
    for t in analytics.load_month(db, user_id, month):
        if analytics.is_spend(t):
            spent[t.category] += t.amount_paise
            if t.counterparty_key in recurring_keys:
                fixed[t.category] += t.amount_paise
                paid_keys.add(t.counterparty_key)
    still_due: dict[str, int] = defaultdict(int)
    if progress["is_current"]:
        for item in recurring_items:
            if item["counterparty_key"] not in paid_keys and item["category"] not in NON_SPEND_CATEGORIES \
                    and item["next_expected"][:7] == month:
                still_due[item["category"]] += int(round(item["amount"] * 100))

    items = []
    for category in BUDGETABLE:
        limit, used = limits.get(category, 0), spent.get(category, 0)
        if limit == 0 and used == 0:
            continue
        if progress["is_current"] and progress["days_elapsed"] > 0:
            variable = used - fixed.get(category, 0)
            projected = fixed.get(category, 0) + still_due.get(category, 0) \
                + variable / progress["days_elapsed"] * progress["days_total"]
        else:
            projected = float(used)
        if limit <= 0:
            state = "unbudgeted"
        elif used > limit:
            state = "over"
        elif projected > limit * 1.02:
            state = "warning"
        else:
            state = "ok"
        items.append({
            "category": category,
            "label": label(category),
            "limit": analytics.rupees(limit),
            "spent": analytics.rupees(used),
            "remaining": analytics.rupees(limit - used) if limit > 0 else None,
            "percent": round(used / limit * 100.0, 1) if limit > 0 else None,
            "projected": analytics.rupees(projected),
            "status": state,
        })
    items.sort(key=lambda i: (-i["limit"], -i["spent"]))
    total_limit = sum(limits.get(c, 0) for c in BUDGETABLE)
    budgeted_spend = sum(spent.get(c, 0) for c in BUDGETABLE if limits.get(c, 0) > 0)
    total_spend = sum(spent.values())
    days_left = progress["days_total"] - progress["days_elapsed"]
    remaining = total_limit - budgeted_spend
    return {
        "month": month,
        "progress": progress,
        "has_budget": total_limit > 0,
        "total_limit": analytics.rupees(total_limit),
        "total_spent": analytics.rupees(total_spend),
        "budgeted_spent": analytics.rupees(budgeted_spend),
        "total_remaining": analytics.rupees(remaining),
        "daily_allowance": analytics.rupees(remaining / days_left) if total_limit > 0 and days_left > 0 and remaining > 0 else None,
        "items": items,
    }


def suggestions(db: Session, user_id: int, today: datetime | None = None) -> dict:
    """Suggest a limit per category from the last complete months (up to three)."""
    today = today or now_ist()
    current = month_key(today)
    months = analytics.available_months(db, user_id)
    complete = [m for m in months if m < current][:3]
    basis = complete or months[:1]
    if not basis:
        return {"basis_months": [], "basis_is_partial": False, "excluded_one_offs": [], "items": [],
                "total_suggested": 0.0, "total_average": 0.0, "monthly_saving": 0.0, "average_income": 0.0,
                "left_after_budget": 0.0, "exceeds_income": False}

    # One-off large purchases would inflate a monthly budget, so they are left out of the basis.
    one_offs = {a["id"]: a for a in analytics.anomalies(db, user_id)}
    excluded: list[dict] = []
    per_month: dict[str, dict[str, int]] = {m: defaultdict(int) for m in basis}
    income: list[int] = []
    for m in basis:
        txns = analytics.load_month(db, user_id, m)
        income.append(sum(t.amount_paise for t in txns if t.direction == "credit"))
        for t in txns:
            if not analytics.is_spend(t):
                continue
            if t.id in one_offs:
                excluded.append({"counterparty": t.counterparty, "amount": analytics.rupees(t.amount_paise),
                                 "date": t.occurred_at.date().isoformat()})
                continue
            per_month[m][t.category] += t.amount_paise

    fixed_by_category: dict[str, int] = defaultdict(int)
    for item in analytics.recurring(db, user_id, today)["items"]:
        fixed_by_category[item["category"]] += int(round(item["amount"] * 100))

    items = []
    for category in BUDGETABLE:
        values = [per_month[m].get(category, 0) for m in basis]
        if not any(values):
            continue
        typical = statistics.median(values) if len(values) >= 3 else sum(values) / len(values)
        if typical <= 0:
            continue
        committed = fixed_by_category.get(category, 0)
        if category in DISCRETIONARY:
            suggested = max(100, math.floor(typical * (1 - TRIM) / 10_000) * 100)
            why = f"About {int(TRIM * 100)}% under your recent average, since this is flexible spending."
        else:
            suggested = math.ceil(typical / 10_000) * 100
            why = "Set at your recent average, since this is hard to cut."
        if committed and suggested * 100 < committed:
            suggested = math.ceil(committed / 10_000) * 100
            why = "Covers the recurring payments you already have in this category."
        items.append({
            "category": category,
            "label": label(category),
            "average": analytics.rupees(typical),
            "suggested": float(suggested),
            "saving": round(max(0.0, analytics.rupees(typical) - suggested), 2),
            "reason": why,
        })
    items.sort(key=lambda i: -i["suggested"])
    average_income = analytics.rupees(sum(income) / len(income)) if income else 0.0
    total_suggested = sum(i["suggested"] for i in items)
    return {
        "basis_months": basis,
        "basis_is_partial": not complete,
        "excluded_one_offs": excluded,
        "items": items,
        "total_suggested": round(total_suggested, 2),
        "total_average": round(sum(i["average"] for i in items), 2),
        "monthly_saving": round(sum(i["saving"] for i in items), 2),
        "average_income": average_income,
        "left_after_budget": round(average_income - total_suggested, 2),
        "exceeds_income": average_income > 0 and total_suggested > average_income,
    }
