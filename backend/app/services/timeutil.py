"""Time helpers. Every stored transaction time is naive Indian Standard Time."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}


def now_ist() -> datetime:
    return datetime.now(IST).replace(tzinfo=None, microsecond=0)


def from_epoch_ms(value: int | float) -> datetime:
    return datetime.fromtimestamp(float(value) / 1000.0, IST).replace(tzinfo=None, microsecond=0)


def _year(y: int) -> int:
    return y + 2000 if y < 100 else y


def _build(y: int, m: int, d: int, hh: int = 0, mm: int = 0, ss: int = 0) -> datetime | None:
    try:
        return datetime(_year(y), m, d, hh, mm, ss)
    except ValueError:
        return None


_ISO = re.compile(r"(?<!\d)(\d{4})-(\d{1,2})-(\d{1,2})(?:[ T:]+(\d{1,2}):(\d{2})(?::(\d{2}))?)?")
_DMY = re.compile(
    r"(?<![\d/-])(\d{1,2})[-/](\d{1,2})[-/](\d{4}|\d{2})(?![\d/-])"
    r"(?:[ ,T]+(?:at\s+)?(\d{1,2}):(\d{2})(?::(\d{2}))?(?:\s*([ap]m))?)?",
    re.I,
)
_DMONY = re.compile(
    r"(?<![\dA-Za-z])(\d{1,2})[-\s]?(jan|feb|mar|apr|may|jun|jul|aug|sept?|oct|nov|dec)[a-z]*[-\s,]{0,2}(\d{4}|\d{2})(?!\d)"
    r"(?:[ ,T]+(?:at\s+)?(\d{1,2}):(\d{2})(?::(\d{2}))?(?:\s*([ap]m))?)?",
    re.I,
)


def _clock(hh: str | None, mm: str | None, ss: str | None, ampm: str | None = None) -> tuple[int, int, int, bool]:
    if hh is None or mm is None:
        return 0, 0, 0, False
    hour = int(hh)
    if ampm:
        ampm = ampm.lower()
        if ampm == "pm" and hour < 12:
            hour += 12
        if ampm == "am" and hour == 12:
            hour = 0
    return hour, int(mm), int(ss or 0), True


def find_datetime(text: str) -> tuple[datetime | None, bool]:
    """Find the first date in free text. Returns (datetime, has_time).

    Numeric dates are read day-first, the convention in Indian bank messages.
    """
    candidates: list[tuple[int, datetime, bool]] = []
    for m in _ISO.finditer(text):
        hh, mm, ss, has_time = _clock(m.group(4), m.group(5), m.group(6))
        dt = _build(int(m.group(1)), int(m.group(2)), int(m.group(3)), hh, mm, ss)
        if dt:
            candidates.append((m.start(), dt, has_time))
    for m in _DMY.finditer(text):
        hh, mm, ss, has_time = _clock(m.group(4), m.group(5), m.group(6), m.group(7))
        dt = _build(int(m.group(3)), int(m.group(2)), int(m.group(1)), hh, mm, ss)
        if dt:
            candidates.append((m.start(), dt, has_time))
    for m in _DMONY.finditer(text):
        hh, mm, ss, has_time = _clock(m.group(4), m.group(5), m.group(6), m.group(7))
        dt = _build(int(m.group(3)), MONTHS[m.group(2).lower()[:3]], int(m.group(1)), hh, mm, ss)
        if dt:
            candidates.append((m.start(), dt, has_time))
    if not candidates:
        return None, False
    candidates.sort(key=lambda c: c[0])
    _, dt, has_time = candidates[0]
    if not (2000 <= dt.year <= 2100):
        return None, False
    return dt, has_time


def parse_loose(value: object) -> datetime | None:
    """Parse a date supplied in a file column or a line prefix."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return from_epoch_ms(value) if value > 10_000_000_000 else from_epoch_ms(value * 1000)
    text = str(value).strip()
    if not text:
        return None
    if re.fullmatch(r"\d{12,14}", text):
        return from_epoch_ms(int(text))
    if re.fullmatch(r"\d{9,11}", text):
        return from_epoch_ms(int(text) * 1000)
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if dt.tzinfo is not None:
            dt = dt.astimezone(IST).replace(tzinfo=None)
        return dt.replace(microsecond=0)
    except ValueError:
        pass
    dt, _ = find_datetime(text)
    return dt


def month_key(dt: datetime | date) -> str:
    return f"{dt.year:04d}-{dt.month:02d}"


def month_bounds(key: str) -> tuple[datetime, datetime]:
    """Start (inclusive) and end (exclusive) of a YYYY-MM month."""
    year, month = (int(p) for p in key.split("-"))
    start = datetime(year, month, 1)
    end = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)
    return start, end


def days_in_month(key: str) -> int:
    start, end = month_bounds(key)
    return (end - start).days


def previous_month(key: str) -> str:
    start, _ = month_bounds(key)
    return month_key(start - timedelta(days=1))


def is_month_key(key: str) -> bool:
    if not re.fullmatch(r"\d{4}-\d{2}", key or ""):
        return False
    return 1 <= int(key[5:]) <= 12 and 2000 <= int(key[:4]) <= 2100
