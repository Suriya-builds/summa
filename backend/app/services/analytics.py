"""Spending analytics. Every number shown in the app or given to the assistant is computed here.

Definitions used throughout:
  income   = all credits
  spend    = all debits except the "investments" category
  invested = debits in the "investments" category
  saved    = income - spend   (so money invested counts as saved)
"""
from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Message, Transaction
from .categories import NON_SPEND_CATEGORIES, label
from .timeutil import days_in_month, month_bounds, month_key, now_ist, previous_month


def rupees(paise: int | float | None) -> float:
    return round((paise or 0) / 100.0, 2)


def inr(amount: float) -> str:
    """Format rupees with Indian digit grouping: 1234567 -> ₹12,34,567."""
    whole = int(round(abs(amount)))
    digits = str(whole)
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        digits = ",".join(groups + [tail])
    return ("-" if amount < 0 else "") + "₹" + digits


def txn_dict(t: Transaction) -> dict:
    return {
        "id": t.id,
        "date": t.occurred_at.isoformat(timespec="minutes"),
        "amount": rupees(t.amount_paise),
        "direction": t.direction,
        "counterparty": t.counterparty,
        "category": t.category,
        "category_label": label(t.category),
        "category_source": t.category_source,
        "category_confidence": round(t.category_confidence or 0.0, 2),
        "channel": t.channel,
        "account_tail": t.account_tail,
        "balance": rupees(t.balance_paise) if t.balance_paise is not None else None,
        "reference": t.reference,
        "note": t.note,
        "message_id": t.message_id,
    }


def is_spend(t: Transaction) -> bool:
    return t.direction == "debit" and t.category not in NON_SPEND_CATEGORIES


def available_months(db: Session, user_id: int) -> list[str]:
    rows = db.execute(select(Transaction.occurred_at).where(Transaction.user_id == user_id)).scalars()
    return sorted({month_key(dt) for dt in rows}, reverse=True)


def default_month(db: Session, user_id: int) -> str | None:
    latest = db.execute(select(func.max(Transaction.occurred_at)).where(Transaction.user_id == user_id)).scalar()
    return month_key(latest) if latest else None


def load(db: Session, user_id: int, start: datetime | None = None, end: datetime | None = None) -> list[Transaction]:
    query = select(Transaction).where(Transaction.user_id == user_id)
    if start is not None:
        query = query.where(Transaction.occurred_at >= start)
    if end is not None:
        query = query.where(Transaction.occurred_at < end)
    return list(db.execute(query.order_by(Transaction.occurred_at)).scalars())


def load_month(db: Session, user_id: int, month: str) -> list[Transaction]:
    start, end = month_bounds(month)
    return load(db, user_id, start, end)


def _totals(txns: list[Transaction]) -> dict:
    income = sum(t.amount_paise for t in txns if t.direction == "credit")
    spend = sum(t.amount_paise for t in txns if is_spend(t))
    invested = sum(t.amount_paise for t in txns if t.direction == "debit" and t.category in NON_SPEND_CATEGORIES)
    return {"income": income, "spend": spend, "invested": invested}


def _pct_change(current: float, previous: float) -> float | None:
    if previous <= 0:
        return None
    return round((current - previous) / previous * 100.0, 1)


def month_progress(month: str, today: datetime | None = None) -> dict:
    """How far through the month we are. Past months are complete; future ones have not started."""
    today = today or now_ist()
    total = days_in_month(month)
    current = month_key(today)
    if month == current:
        elapsed = today.day
    elif month < current:
        elapsed = total
    else:
        elapsed = 0
    return {"days_total": total, "days_elapsed": elapsed, "is_current": month == current, "is_complete": elapsed == total}


def summary(db: Session, user_id: int, month: str, today: datetime | None = None) -> dict:
    txns = load_month(db, user_id, month)
    prev_key = previous_month(month)
    prev_txns = load_month(db, user_id, prev_key)
    progress = month_progress(month, today)
    totals, prev_totals = _totals(txns), _totals(prev_txns)

    # For a month still in progress, compare against the same number of days of the previous month.
    cutoff = progress["days_elapsed"] if progress["is_current"] else None
    prev_same_period = [t for t in prev_txns if cutoff is None or t.occurred_at.day <= cutoff]
    prev_period_totals = _totals(prev_same_period)

    by_category: dict[str, dict] = defaultdict(lambda: {"amount": 0, "count": 0})
    for t in txns:
        if t.direction == "debit":
            by_category[t.category]["amount"] += t.amount_paise
            by_category[t.category]["count"] += 1
    prev_by_category: dict[str, int] = defaultdict(int)
    for t in prev_same_period:
        if t.direction == "debit":
            prev_by_category[t.category] += t.amount_paise
    total_debit = sum(v["amount"] for v in by_category.values()) or 1
    categories = [
        {
            "category": cat,
            "label": label(cat),
            "amount": rupees(v["amount"]),
            "count": v["count"],
            "share": round(v["amount"] / total_debit * 100.0, 1),
            "previous_amount": rupees(prev_by_category.get(cat, 0)),
            "change_pct": _pct_change(v["amount"], prev_by_category.get(cat, 0)),
            "counts_as_spend": cat not in NON_SPEND_CATEGORIES,
        }
        for cat, v in sorted(by_category.items(), key=lambda kv: -kv[1]["amount"])
    ]

    start, _ = month_bounds(month)
    last_day = progress["days_elapsed"] if progress["is_current"] else progress["days_total"]
    daily_spend: dict[int, int] = defaultdict(int)
    daily_income: dict[int, int] = defaultdict(int)
    for t in txns:
        if is_spend(t):
            daily_spend[t.occurred_at.day] += t.amount_paise
        elif t.direction == "credit":
            daily_income[t.occurred_at.day] += t.amount_paise
    daily = []
    running = 0
    for day in range(1, max(last_day, 0) + 1):
        running += daily_spend.get(day, 0)
        daily.append({
            "date": (start + timedelta(days=day - 1)).date().isoformat(),
            "spend": rupees(daily_spend.get(day, 0)),
            "income": rupees(daily_income.get(day, 0)),
            "cumulative_spend": rupees(running),
        })

    merchants: dict[str, dict] = {}
    for t in txns:
        if not is_spend(t):
            continue
        entry = merchants.setdefault(t.counterparty_key, {"counterparty": t.counterparty, "amount": 0, "count": 0, "category": t.category})
        entry["amount"] += t.amount_paise
        entry["count"] += 1
    top_merchants = [
        {**m, "amount": rupees(m["amount"]), "category_label": label(m["category"])}
        for m in sorted(merchants.values(), key=lambda m: -m["amount"])[:8]
    ]

    channels: dict[str, int] = defaultdict(int)
    for t in txns:
        if is_spend(t):
            channels[t.channel] += t.amount_paise

    spends = [t for t in txns if is_spend(t)]
    largest = max(spends, key=lambda t: t.amount_paise) if spends else None
    saved = totals["income"] - totals["spend"]
    return {
        "month": month,
        "has_data": bool(txns),
        "progress": progress,
        "income": rupees(totals["income"]),
        "spend": rupees(totals["spend"]),
        "invested": rupees(totals["invested"]),
        "saved": rupees(saved),
        "savings_rate": round(saved / totals["income"] * 100.0, 1) if totals["income"] > 0 else None,
        "transaction_count": len(txns),
        "average_daily_spend": rupees(totals["spend"] / max(1, last_day)) if txns else 0.0,
        "previous": {
            "month": prev_key,
            "income": rupees(prev_totals["income"]),
            "spend": rupees(prev_totals["spend"]),
            "same_period_spend": rupees(prev_period_totals["spend"]),
            "compared_days": cutoff,
        },
        "spend_change_pct": _pct_change(totals["spend"], prev_period_totals["spend"]),
        "by_category": categories,
        "daily": daily,
        "top_merchants": top_merchants,
        "by_channel": [{"channel": c, "amount": rupees(a)} for c, a in sorted(channels.items(), key=lambda kv: -kv[1])],
        "largest_expense": txn_dict(largest) if largest else None,
    }


def monthly_trend(db: Session, user_id: int, months: int = 6) -> list[dict]:
    txns = load(db, user_id)
    buckets: dict[str, list[Transaction]] = defaultdict(list)
    for t in txns:
        buckets[month_key(t.occurred_at)].append(t)
    out = []
    for key in sorted(buckets)[-months:]:
        totals = _totals(buckets[key])
        out.append({"month": key, "income": rupees(totals["income"]), "spend": rupees(totals["spend"]),
                    "invested": rupees(totals["invested"])})
    return out


SUBSCRIPTION_CATEGORIES = {"entertainment", "personal", "education"}
BILL_CATEGORIES = {"bills", "health"}


def _recurring_kind(category: str) -> str:
    if category in SUBSCRIPTION_CATEGORIES:
        return "subscription"
    if category in BILL_CATEGORIES:
        return "bill"
    return "commitment"


def recurring(db: Session, user_id: int, today: datetime | None = None) -> dict:
    """Payments to the same counterparty that repeat about monthly at a steady amount."""
    today = today or now_ist()
    groups: dict[str, list[Transaction]] = defaultdict(list)
    for t in load(db, user_id):
        if t.direction == "debit" and t.counterparty_key not in ("unknown", "atm cash withdrawal"):
            groups[t.counterparty_key].append(t)

    items = []
    for txns in groups.values():
        if len(txns) < 2:
            continue
        amounts = [t.amount_paise for t in txns]
        median_amount = statistics.median(amounts)
        if any(abs(a - median_amount) > 0.15 * median_amount for a in amounts):
            continue
        gaps = [(b.occurred_at - a.occurred_at).days for a, b in zip(txns, txns[1:])]
        if not gaps or any(g < 25 or g > 35 for g in gaps):
            continue
        last = txns[-1]
        next_expected = last.occurred_at + timedelta(days=round(statistics.median(gaps)))
        items.append({
            "counterparty": last.counterparty,
            "counterparty_key": last.counterparty_key,
            "category": last.category,
            "category_label": label(last.category),
            "amount": rupees(median_amount),
            "occurrences": len(txns),
            "last_date": last.occurred_at.date().isoformat(),
            "next_expected": next_expected.date().isoformat(),
            "overdue": next_expected.date() < today.date() - timedelta(days=5),
            "kind": _recurring_kind(last.category),
            "transaction_ids": [t.id for t in txns],
        })
    items.sort(key=lambda i: -i["amount"])
    subs = [i for i in items if i["kind"] in ("subscription", "bill")]
    return {
        "items": items,
        "monthly_total": round(sum(i["amount"] for i in items), 2),
        "subscription_total": round(sum(i["amount"] for i in subs), 2),
        "subscription_count": len(subs),
    }


ANOMALY_MIN_PAISE = 100_000  # ignore anything under ₹1,000
ANOMALY_SKIP = {"rent", "investments", "cash"}


def _upper_fence(values: list[int]) -> float:
    """Tukey outer fence: Q3 + 3 x IQR."""
    q1, _, q3 = statistics.quantiles(values, n=4, method="inclusive")
    return q3 + 3.0 * (q3 - q1)


def anomalies(db: Session, user_id: int, month: str | None = None) -> list[dict]:
    """Debits far above what is normal for that merchant, or for their category.

    A payment is compared with earlier payments to the same merchant when there are at least
    four. Otherwise it is compared with the category, and must clear the outer fence of the
    category's amounts. Recurring payments, rent, investments and cash are never flagged.
    """
    txns = [t for t in load(db, user_id) if t.direction == "debit"]
    regular = {i["counterparty_key"] for i in recurring(db, user_id)["items"]}
    by_category: dict[str, list[int]] = defaultdict(list)
    by_merchant: dict[str, list[int]] = defaultdict(list)
    for t in txns:
        by_category[t.category].append(t.amount_paise)
        by_merchant[t.counterparty_key].append(t.amount_paise)
    everyday = [t.amount_paise for t in txns if t.category not in ANOMALY_SKIP and t.counterparty_key not in regular]

    flagged = []
    for t in txns:
        if month and month_key(t.occurred_at) != month:
            continue
        if t.amount_paise < ANOMALY_MIN_PAISE or t.category in ANOMALY_SKIP or t.counterparty_key in regular:
            continue
        merchant_history = by_merchant[t.counterparty_key]
        category_history = by_category[t.category]
        if len(merchant_history) >= 5 and t.counterparty_key != "unknown":
            baseline, scope = statistics.median(merchant_history), f"payment to {t.counterparty.title()}"
            unusual = t.amount_paise > 3.0 * baseline
        elif len(category_history) >= 5:
            baseline, scope = statistics.median(category_history), f"{label(t.category)} payment"
            unusual = t.amount_paise > max(3.0 * baseline, _upper_fence(category_history))
        elif len(everyday) >= 20:
            baseline, scope = statistics.median(everyday), "payment"
            unusual = t.amount_paise >= 500_000 and t.amount_paise > _upper_fence(everyday)
        else:
            continue
        if baseline > 0 and unusual:
            ratio = t.amount_paise / baseline
            flagged.append({
                **txn_dict(t),
                "typical_amount": rupees(baseline),
                "ratio": round(ratio, 1),
                "reason": f"{ratio:.1f}x your typical {scope} of {inr(rupees(baseline))}",
            })
    flagged.sort(key=lambda f: -f["amount"])
    return flagged


def scam_counts(db: Session, user_id: int) -> dict:
    rows = db.execute(
        select(Message.scam_level, func.count()).where(
            Message.user_id == user_id, Message.scam_level != "safe", Message.dismissed.is_(False)
        ).group_by(Message.scam_level)
    ).all()
    counts = {level: count for level, count in rows}
    return {"dangerous": counts.get("dangerous", 0), "suspicious": counts.get("suspicious", 0)}


def insights(db: Session, user_id: int, month: str, today: datetime | None = None) -> list[dict]:
    """Plain facts about the month, most actionable first. Each carries the numbers it was built from."""
    from . import budgets  # local import: budgets depends on this module

    s = summary(db, user_id, month, today)
    if not s["has_data"]:
        return []
    out: list[dict] = []
    partial = s["progress"]["is_current"]
    so_far = " so far" if partial else ""
    compared = s["previous"]["compared_days"]
    period = f"the first {compared} days of last month" if compared else "the month before"

    status = budgets.status(db, user_id, month, today)
    at_risk = [b for b in status["items"] if b["status"] in ("over", "warning")]
    for b in sorted(at_risk, key=lambda b: -(b["projected"] - b["limit"]))[:2]:
        if b["status"] == "over":
            title = f"{b['label']} is {inr(b['spent'] - b['limit'])} over budget"
            detail = f"Spent {inr(b['spent'])} against a budget of {inr(b['limit'])}."
        else:
            title = f"{b['label']} is on pace to go over budget"
            detail = f"Spent {inr(b['spent'])} of {inr(b['limit'])}{so_far}; projected {inr(b['projected'])} by month end."
        out.append({"kind": "budget", "tone": "warn", "title": title, "detail": detail,
                    "data": {"category": b["category"], "limit": b["limit"], "spent": b["spent"], "projected": b["projected"]}})

    movers = [c for c in s["by_category"]
              if c["change_pct"] is not None and c["counts_as_spend"] and abs(c["amount"] - c["previous_amount"]) >= 500]
    risers = sorted([c for c in movers if c["change_pct"] >= 20], key=lambda c: -(c["amount"] - c["previous_amount"]))
    fallers = sorted([c for c in movers if c["change_pct"] <= -20], key=lambda c: c["amount"] - c["previous_amount"])
    for c in risers[:2]:
        out.append({
            "kind": "category_up", "tone": "warn",
            "title": f"{c['label']} is up {c['change_pct']:.0f}%",
            "detail": f"{inr(c['amount'])}{so_far}, against {inr(c['previous_amount'])} in {period}.",
            "data": {"category": c["category"], "amount": c["amount"], "previous_amount": c["previous_amount"],
                     "change_pct": c["change_pct"]},
        })
    for c in fallers[:1]:
        out.append({
            "kind": "category_down", "tone": "good",
            "title": f"{c['label']} is down {abs(c['change_pct']):.0f}%",
            "detail": f"{inr(c['amount'])}{so_far}, against {inr(c['previous_amount'])} in {period}.",
            "data": {"category": c["category"], "amount": c["amount"], "previous_amount": c["previous_amount"],
                     "change_pct": c["change_pct"]},
        })

    for a in anomalies(db, user_id, month)[:1]:
        reason = a["reason"]
        out.append({
            "kind": "anomaly", "tone": "warn",
            "title": f"Unusually large: {inr(a['amount'])} at {a['counterparty'].title()}",
            "detail": reason[:1].upper() + reason[1:] + ".",
            "data": {"transaction_id": a["id"], "amount": a["amount"], "typical_amount": a["typical_amount"],
                     "ratio": a["ratio"]},
        })

    if s["savings_rate"] is not None:
        rate = s["savings_rate"]
        tone = "good" if rate >= 20 else "warn" if rate < 5 else "info"
        if s["saved"] >= 0:
            title = f"You have kept {inr(s['saved'])}{so_far} ({rate:.0f}% of income)" if partial \
                else f"You saved {inr(s['saved'])} ({rate:.0f}% of income)"
        else:
            title = f"You spent {inr(abs(s['saved']))} more than you earned"
        detail = f"Income {inr(s['income'])}, spending {inr(s['spend'])}."
        if s["invested"]:
            detail += f" Another {inr(s['invested'])} went into investments, which counts as saved."
        if partial:
            detail += f" {s['progress']['days_total'] - s['progress']['days_elapsed']} days of the month remain."
        out.append({
            "kind": "savings_rate", "tone": tone, "title": title, "detail": detail,
            "data": {"income": s["income"], "spend": s["spend"], "saved": s["saved"], "savings_rate": rate,
                     "invested": s["invested"]},
        })

    rec = recurring(db, user_id, today)
    if rec["subscription_count"]:
        names = ", ".join(i["counterparty"].title() for i in rec["items"] if i["kind"] in ("subscription", "bill"))
        out.append({
            "kind": "subscriptions", "tone": "info",
            "title": f"{rec['subscription_count']} subscriptions and bills cost {inr(rec['subscription_total'])} a month",
            "detail": f"{names}. That is {inr(rec['subscription_total'] * 12)} a year.",
            "data": {"count": rec["subscription_count"], "monthly_total": rec["subscription_total"],
                     "yearly_total": round(rec["subscription_total"] * 12, 2)},
        })

    txns = [t for t in load_month(db, user_id, month) if is_spend(t)]
    small = [t for t in txns if t.amount_paise < 15_000]
    if len(small) >= 10:
        total_small = rupees(sum(t.amount_paise for t in small))
        out.append({
            "kind": "small_spends", "tone": "info",
            "title": f"{len(small)} small payments added up to {inr(total_small)}",
            "detail": "Each was under ₹150. Small UPI payments are easy to lose track of.",
            "data": {"count": len(small), "total": total_small, "threshold": 150},
        })

    weekend: dict[str, int] = defaultdict(int)
    weekday: dict[str, int] = defaultdict(int)
    regular = {i["counterparty_key"] for i in rec["items"]}
    for t in txns:
        if t.counterparty_key in regular:
            continue
        bucket = weekend if t.occurred_at.weekday() >= 5 else weekday
        bucket[t.occurred_at.date().isoformat()] += t.amount_paise
    if len(weekend) >= 2 and len(weekday) >= 4:
        weekend_avg = sum(weekend.values()) / len(weekend)
        weekday_avg = sum(weekday.values()) / len(weekday)
        if weekday_avg > 0 and weekend_avg / weekday_avg >= 1.4:
            out.append({
                "kind": "weekend", "tone": "info",
                "title": f"A weekend day costs {weekend_avg / weekday_avg:.1f}x a weekday",
                "detail": f"{inr(rupees(weekend_avg))} on an average weekend day against {inr(rupees(weekday_avg))} "
                          "on a weekday, leaving out recurring payments.",
                "data": {"weekend_daily": rupees(weekend_avg), "weekday_daily": rupees(weekday_avg),
                         "ratio": round(weekend_avg / weekday_avg, 1)},
            })

    scams = scam_counts(db, user_id)
    if scams["dangerous"] or scams["suspicious"]:
        total = scams["dangerous"] + scams["suspicious"]
        out.append({
            "kind": "scams", "tone": "warn" if scams["dangerous"] else "info",
            "title": f"{total} risky message{'s' if total != 1 else ''} found in your inbox",
            "detail": f"{scams['dangerous']} look dangerous and {scams['suspicious']} suspicious. Review them in Scam Shield.",
            "data": scams,
        })
    return out[:9]
