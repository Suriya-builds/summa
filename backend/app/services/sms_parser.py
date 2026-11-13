"""Rule engine that extracts a transaction from an Indian bank, card or UPI SMS.

The engine is deliberately conservative: a message that only talks about money
(an offer, a bill reminder, a collect request, a failed payment) is not a transaction.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from .timeutil import find_datetime, now_ist

_NUM = r"([0-9][0-9,]*(?:\.\d{1,2})?)"
_CUR = r"(?:rs\.?|inr|₹)"
AMOUNT_RE = re.compile(rf"{_CUR}\s*[:\-]?\s*{_NUM}", re.I)
# SBI writes "debited by 120.0" with no currency marker.
BARE_AMOUNT_RE = re.compile(rf"\b(?:debited|credited)\s+(?:by|for|with)\s+{_NUM}", re.I)
BALANCE_RE = re.compile(
    rf"(?:avl\.?|avail(?:able)?\.?|avbl\.?|clear|closing|a/c|net)?\s*\bbal(?:ance)?\b\.?\s*(?:is|of|:|-)?\s*(?:{_CUR})?\s*:?\s*{_NUM}",
    re.I,
)
_BALANCE_CONTEXT = re.compile(r"(?:bal(?:ance)?|lmt|limit|outstanding|due)\W{0,6}(?:is|of)?\W{0,4}$", re.I)

OTP_RE = re.compile(r"\botp\b|one[\s-]?time\s+pass|verification code|\bcvv\b", re.I)
PROMO_RE = re.compile(
    r"%\s*off|use code|\bt&c\b|\btnc\b|\boffers?\b|\bsale\b|shop now|download (?:the )?app|cashback up ?to|"
    r"get (?:flat|upto|up to|rs|₹|extra)|pre-?approved|limited period|voucher|coupon|\bwin\b|book now|apply now|"
    r"order now|buy now|hurry|deal of",
    re.I,
)
# Messages that mention money but record no completed movement on the user's account.
NON_TXN_RE = re.compile(
    r"will be (?:debited|deducted|credited|charged|auto[- ]?debited)|to be (?:debited|deducted)|"
    r"\b(?:is|are|was) due\b|due (?:on|date|by)|payment due|overdue|outstanding|minimum (?:amount )?due|"
    r"has requested|requested money|collect request|payment request|request(?:ed)? (?:of|for) (?:rs|inr|₹)|"
    r"declined|failed|unsuccessful|not (?:been )?(?:processed|completed)|could not be|"
    r"(?:payment|amount|premium) of .{0,40}(?:has been |was |is )?received|received (?:your|a) payment|"
    r"we have received|thank you for (?:your )?pay|bill (?:is )?generated|statement (?:is )?(?:generated|ready)|"
    r"e-?mandate|autopay (?:is )?(?:scheduled|set)|registered for|"
    r"enter (?:your )?(?:upi )?pin|click (?:here|the link|on)|to (?:receive|claim|avoid)",
    re.I,
)
ACCOUNT_ANCHOR_RE = re.compile(
    r"(?:a/c|\bac\b|acct|account|card|wallet)\D{0,14}?(?:[xX*]+\s?-?\d{2,6}|\.{2,}\d{3,6}|ending\s+(?:with\s+|in\s+)?\d{3,6}|\b\d{3,6}\b)|"
    r"\bupi\b|\bvpa\b|\bavl\.?\s*(?:bal|lmt)|\bneft\b|\bimps\b|\brtgs\b|\batm\b",
    re.I,
)
ACCOUNT_TAIL_RE = re.compile(
    r"(?:a/c|\bac\b|acct|account|card)\s*(?:no\.?|number|ending(?:\s+with|\s+in)?)?\s*[:\-]?\s*"
    r"(?:[xX*]+\s?-?|\.{2,})?(\d{3,6})(?!\d)",
    re.I,
)
REFERENCE_RE = re.compile(
    r"(?:\bref(?:erence)?\.?\s*(?:no\.?|number|id)?(?:\s+is)?|\brefno|\brrn|\butr|\btxn\s*(?:id|no\.?|ref)|\bupi)\s*[:#\-/]*\s*"
    r"(?:P2[AMP]/)?([A-Za-z]{0,2}\d{6,18})\b",
    re.I,
)

DEBIT_WORDS = r"debited|spent|paid|sent|withdrawn|withdrawal|purchase|deducted|money transfer|transferred|charged"
CREDIT_WORDS = r"credited|received|deposited|refunded|refund|reversed|cashback of"
DIRECTION_RE = re.compile(rf"\b(?:(?P<debit>{DEBIT_WORDS})|(?P<credit>{CREDIT_WORDS}))\b", re.I)

VPA = r"[A-Za-z0-9][A-Za-z0-9.\-_]{1,48}@[A-Za-z][A-Za-z0-9]{1,20}"
_STOP = (
    r"(?=\s+(?:on|ref|refno|upi|avl|avail|bal|not|via|using|for|is|has|thru|through|with|if|call|sms|dated|dt|"
    r"txn|info|credited|debited|at|from|to|by|and|was|your|total|bank)\b|\s*[.;,(|]|\s+-|\s*$)"
)
_NAME = r"([A-Za-z0-9][A-Za-z0-9&'._*/\- ]{1,58}?)"
_SKIP_START = re.compile(
    r"^(?:a/c|ac|acct|account|your|ur|the|this|my|be|block|report|dispute|know|avoid|rs|inr|neft|imps|rtgs|upi|"
    r"transfer|check|view|us|bank|card|credit card|debit card|wallet|you|any|stop|\d{5,})\b",
    re.I,
)
_BANK_ONLY = re.compile(
    r"^(?:(?:hdfc|sbi|icici|axis|kotak|yes|idfc(?: first)?|pnb|canara|union|federal|indusind|bob|boi)\s*(?:bank)?"
    r"(?:\s*(?:a/c|ac|acct|account|card).*)?)$",
    re.I,
)


@dataclass
class ParsedTransaction:
    amount_paise: int
    direction: str
    counterparty: str
    occurred_at: datetime
    channel: str = "other"
    account_tail: str | None = None
    balance_paise: int | None = None
    reference: str | None = None


def to_paise(text: str) -> int | None:
    try:
        value = float(text.replace(",", ""))
    except ValueError:
        return None
    if value <= 0 or value > 100_000_000:  # above ten crore is not a retail SMS amount
        return None
    return int(round(value * 100))


def normalise(body: str) -> str:
    """Collapse whitespace, keeping line breaks as ' | ' because some banks use them as separators."""
    text = body.replace(" ", " ").strip()
    text = re.sub(r"\s*\n+\s*", " | ", text)
    return re.sub(r"[ \t]+", " ", text)


def counterparty_key(name: str) -> str:
    key = re.sub(r"[^a-z0-9@]+", " ", name.lower()).strip()
    return re.sub(r"\s+", " ", key)[:120] or "unknown"


def _tidy_name(name: str) -> str:
    name = re.sub(r"\s+", " ", name).strip(" .,;:-*/|'\"")
    name = re.sub(r"^(?:vpa|m/s|mr|mrs|ms)\.?\s+", "", name, flags=re.I)
    return name[:120]


def _find_amount(text: str) -> tuple[int, int] | None:
    """Return (paise, position) of the transaction amount, skipping balances and limits."""
    for m in AMOUNT_RE.finditer(text):
        if _BALANCE_CONTEXT.search(text[max(0, m.start() - 24) : m.start()]):
            continue
        paise = to_paise(m.group(1))
        if paise:
            return paise, m.start()
    m = BARE_AMOUNT_RE.search(text)
    if m:
        paise = to_paise(m.group(1))
        if paise:
            return paise, m.start()
    return None


def _find_balance(text: str) -> int | None:
    for m in BALANCE_RE.finditer(text):
        return to_paise(m.group(1))
    return None


def _candidates(text: str, lead: str) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    for m in re.finditer(rf"\b(?:{lead})\s+(?:VPA\s+)?({VPA})", text, re.I):
        out.append((m.start(), m.group(1)))
    for m in re.finditer(rf"\b(?:{lead})\s*:?\s+(?:VPA\s+)?{_NAME}{_STOP}", text, re.I):
        out.append((m.start(), m.group(1)))
    out.sort(key=lambda item: item[0])
    return out


def _find_counterparty(text: str, direction: str, lower: str) -> str:
    # Axis style: UPI/P2M/427612345678/AMAZON PAY
    m = re.search(r"\bUPI/(?:P2[AMP]/)?\d{6,}/([^|/]{2,60}?)(?=\s*(?:\||/|$)|\s+not you)", text, re.I)
    if m:
        return _tidy_name(m.group(1))
    # ICICI style: "...debited for Rs 349.00 on 03-Oct-26; NETFLIX credited."
    m = re.search(rf";\s*{_NAME}\s+(?:credited|debited)\b", text, re.I)
    if m and not _SKIP_START.match(m.group(1)):
        return _tidy_name(m.group(1))
    if re.search(r"\batm\b|cash withdraw|withdrawn", lower):
        return "ATM Cash Withdrawal"
    lead = (
        r"trf to|transfer(?:red)? to|paid to|sent to|payment to|towards|to|at"
        if direction == "debit"
        else r"transfer from|received from|from|by"
    )
    for _, raw in _candidates(text, lead):
        name = _tidy_name(raw)
        if "@" in name and len(name) >= 5:
            return name  # a UPI ID is always a counterparty, even when it starts with a phone number
        if len(name) < 2 or _SKIP_START.match(name) or _BANK_ONLY.match(name):
            continue
        if re.fullmatch(r"[\d\s./-]+", name):
            continue
        return name
    m = re.search(rf"\bInfo\s*[:\-]\s*(?:UPI[-/])?{_NAME}{_STOP}", text, re.I)
    if m:
        return _tidy_name(m.group(1))
    return "Unknown"


def _channel(lower: str, counterparty: str) -> str:
    if re.search(r"\batm\b|cash withdraw|withdrawn", lower):
        return "atm"
    if re.search(r"\bupi\b|\bvpa\b", lower) or "@" in counterparty:
        return "upi"
    if re.search(r"credit card|debit card|\bcard\b", lower):
        return "card"
    if re.search(r"\bneft\b|\bimps\b|\brtgs\b|net ?banking", lower):
        return "netbanking"
    if "wallet" in lower:
        return "wallet"
    return "other"


def _resolve_time(text: str, received_at: datetime | None) -> datetime:
    found, has_time = find_datetime(text)
    reference = received_at or now_ist()
    if found is None:
        return reference
    # A date well after the message arrived is a validity or due date, not the transaction date.
    if received_at is not None and found > received_at + timedelta(days=2):
        return received_at
    if received_at is None and found > reference + timedelta(days=2):
        return reference
    if has_time:
        return found
    if received_at is not None and found.date() == received_at.date():
        return received_at
    return found.replace(hour=12)


def looks_promotional(body: str) -> bool:
    return bool(PROMO_RE.search(body))


def looks_like_otp(body: str) -> bool:
    return bool(OTP_RE.search(body))


def parse_transaction(body: str, received_at: datetime | None = None) -> ParsedTransaction | None:
    text = normalise(body)
    lower = text.lower()
    if len(text) < 15 or OTP_RE.search(lower) or NON_TXN_RE.search(lower):
        return None
    if not ACCOUNT_ANCHOR_RE.search(text):
        return None
    if PROMO_RE.search(lower) and not ACCOUNT_TAIL_RE.search(text):
        return None

    direction_match = DIRECTION_RE.search(text)
    if not direction_match:
        return None
    direction = "debit" if direction_match.group("debit") else "credit"

    amount = _find_amount(text)
    if not amount:
        return None
    amount_paise, _ = amount

    counterparty = _find_counterparty(text, direction, lower)
    tail = ACCOUNT_TAIL_RE.search(text)
    ref = REFERENCE_RE.search(text)
    return ParsedTransaction(
        amount_paise=amount_paise,
        direction=direction,
        counterparty=counterparty,
        occurred_at=_resolve_time(text, received_at),
        channel=_channel(lower, counterparty),
        account_tail=tail.group(1)[-4:] if tail else None,
        balance_paise=_find_balance(text),
        reference=ref.group(1) if ref else None,
    )
