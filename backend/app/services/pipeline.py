"""Import pipeline: raw messages -> scam verdict -> transaction -> category -> database."""
from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import MerchantRule, Message, Transaction, User
from . import categorizer, scam_detector, sms_parser
from .splitter import RawMessage
from .timeutil import now_ist

_MONEY_HINT = re.compile(r"(?:rs\.?|inr|₹)\s*[:\-]?\s*\d|\b(?:debited|credited)\b", re.I)


@dataclass
class ImportResult:
    received: int = 0
    imported: int = 0
    duplicates: int = 0
    skipped_over_limit: int = 0
    transactions: int = 0
    scams: int = 0
    otps: int = 0
    promos: int = 0
    others: int = 0
    llm_parsed: int = 0
    llm_error: str | None = None
    first_date: str | None = None
    last_date: str | None = None
    unparsed_money_messages: int = 0
    kinds: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return asdict(self)


def fingerprint(raw: RawMessage) -> str:
    stamp = raw.received_at.isoformat() if raw.received_at else ""
    payload = f"{raw.sender.strip().lower()}|{re.sub(r'\\s+', ' ', raw.body.strip())}|{stamp}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def user_rules(db: Session, user_id: int) -> dict[str, str]:
    rows = db.execute(select(MerchantRule.counterparty_key, MerchantRule.category).where(MerchantRule.user_id == user_id))
    return {key: category for key, category in rows}


def build_transaction(
    user_id: int,
    parsed: sms_parser.ParsedTransaction,
    body: str,
    rules: dict[str, str],
    cache: dict[tuple[str, str], categorizer.CategoryResult] | None = None,
) -> Transaction:
    key = sms_parser.counterparty_key(parsed.counterparty)
    cache_key = (key, parsed.direction)
    result = cache.get(cache_key) if cache is not None and parsed.direction == "debit" else None
    if result is None:
        result = categorizer.categorise(parsed.counterparty, parsed.direction, body, rules)
        if cache is not None and parsed.direction == "debit":
            cache[cache_key] = result
    counterparty = parsed.counterparty
    if counterparty == "Unknown" and result.category == "interest":
        counterparty = "Bank Interest"
    return Transaction(
        user_id=user_id,
        occurred_at=parsed.occurred_at,
        amount_paise=parsed.amount_paise,
        direction=parsed.direction,
        counterparty=counterparty,
        counterparty_key=sms_parser.counterparty_key(counterparty),
        channel=parsed.channel,
        account_tail=parsed.account_tail,
        balance_paise=parsed.balance_paise,
        reference=parsed.reference,
        category=result.category,
        category_source=result.source,
        category_confidence=result.confidence,
    )


def _is_duplicate_reference(db: Session, user_id: int, parsed: sms_parser.ParsedTransaction, seen: set) -> bool:
    if not parsed.reference:
        return False
    key = (parsed.reference, parsed.amount_paise, parsed.direction)
    if key in seen:
        return True
    exists = db.execute(
        select(Transaction.id).where(
            Transaction.user_id == user_id,
            Transaction.reference == parsed.reference,
            Transaction.amount_paise == parsed.amount_paise,
            Transaction.direction == parsed.direction,
        ).limit(1)
    ).first()
    seen.add(key)
    return exists is not None


def import_messages(db: Session, user: User, raws: list[RawMessage], use_llm: bool = False) -> ImportResult:
    result = ImportResult(received=len(raws))
    if len(raws) > settings.max_import_messages:
        result.skipped_over_limit = len(raws) - settings.max_import_messages
        raws = raws[: settings.max_import_messages]

    existing = set(db.execute(select(Message.fingerprint).where(Message.user_id == user.id)).scalars())
    fresh: list[tuple[RawMessage, str]] = []
    for raw in raws:
        fp = fingerprint(raw)
        if fp in existing:
            result.duplicates += 1
            continue
        existing.add(fp)
        fresh.append((raw, fp))
    if not fresh:
        return result

    verdicts = scam_detector.score_messages([(raw.body, raw.sender) for raw, _ in fresh])
    rules = user_rules(db, user.id)
    cache: dict = {}
    seen_refs: set = set()
    now = now_ist()
    llm_candidates: list[Message] = []
    dates: list[datetime] = []

    for (raw, fp), verdict in zip(fresh, verdicts):
        parsed = None if verdict.level == "dangerous" else sms_parser.parse_transaction(raw.body, raw.received_at)
        if verdict.level == "dangerous":
            kind = "scam"
        elif parsed is not None:
            kind = "transaction"
        elif sms_parser.looks_like_otp(raw.body):
            kind = "otp"
        elif verdict.level == "suspicious":
            kind = "scam"
        elif sms_parser.looks_promotional(raw.body):
            kind = "promo"
        else:
            kind = "other"

        received_at = raw.received_at or (parsed.occurred_at if parsed else now)
        message = Message(
            user_id=user.id,
            sender=raw.sender,
            body=raw.body,
            received_at=received_at,
            kind=kind,
            scam_score=round(verdict.score, 4),
            scam_level=verdict.level,
            scam_reasons=verdict.reasons,
            parse_source="rules" if parsed else "none",
            fingerprint=fp,
        )
        db.add(message)
        result.imported += 1
        dates.append(received_at)

        if parsed is not None:
            if _is_duplicate_reference(db, user.id, parsed, seen_refs):
                message.kind = "other"
                message.parse_source = "none"
                result.duplicates += 1
                result.others += 1
                continue
            txn = build_transaction(user.id, parsed, raw.body, rules, cache)
            txn.message = message
            db.add(txn)
            result.transactions += 1
        elif kind == "scam":
            result.scams += 1
        elif kind == "otp":
            result.otps += 1
        elif kind == "promo":
            result.promos += 1
        else:
            result.others += 1
            if _MONEY_HINT.search(raw.body) and sms_parser.DIRECTION_RE.search(raw.body):
                result.unparsed_money_messages += 1
                llm_candidates.append(message)

    db.flush()

    if use_llm and llm_candidates:
        from . import llm_parser

        try:
            added = llm_parser.parse_with_llm(db, user, llm_candidates, rules)
            result.llm_parsed = added
            result.transactions += added
            result.others -= added
            result.unparsed_money_messages -= added
        except llm_parser.LLMUnavailable as exc:
            result.llm_error = str(exc)

    db.commit()
    if dates:
        result.first_date = min(dates).date().isoformat()
        result.last_date = max(dates).date().isoformat()
    result.kinds = {
        "transaction": result.transactions, "scam": result.scams, "otp": result.otps,
        "promo": result.promos, "other": result.others,
    }
    return result


def reparse_as_transaction(db: Session, user: User, message: Message) -> Transaction | None:
    """Used when the user says a flagged message is genuine."""
    parsed = sms_parser.parse_transaction(message.body, message.received_at)
    if parsed is None:
        return None
    already = db.execute(select(Transaction.id).where(Transaction.message_id == message.id)).first()
    if already or _is_duplicate_reference(db, user.id, parsed, set()):
        return None
    txn = build_transaction(user.id, parsed, message.body, user_rules(db, user.id))
    txn.message = message
    message.kind = "transaction"
    message.parse_source = "rules"
    db.add(txn)
    return txn
