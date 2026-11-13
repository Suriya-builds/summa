"""Mask identifiers before any text leaves the machine for an LLM.

Kept: amounts, dates, merchant and payee names, the last four digits of an account.
Masked: long digit runs (account, card, reference and phone numbers), PAN, Aadhaar,
email addresses and one-time codes.
"""
from __future__ import annotations

import re

_PAN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
_AADHAAR = re.compile(r"(?<!\d)\d{4}[\s-]\d{4}[\s-]\d{4}(?!\d)")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[a-z]{2,}(?:\.[a-z]{2,})?\b", re.I)
_PHONE = re.compile(r"(?<![\d,.])(?:\+?91[\s-]?)?[6-9]\d{9}(?!\d)")
_LONG_DIGITS = re.compile(r"(?<![\d,.])[A-Za-z]{0,2}\d{9,}(?![\d,.])")
_OTP = re.compile(r"(?<!\d)\d{4,8}(?!\d)(?=[^.]{0,40}\b(?:otp|one[\s-]?time|verification code|passcode)\b)|"
                  r"(?<=\botp\b)([^.\d]{0,30})\d{4,8}(?!\d)", re.I)
_CURRENCY_BEFORE = re.compile(r"(?:rs\.?|inr|₹)\s*[:\-]?\s*$", re.I)


def _mask_unless_amount(pattern: re.Pattern, replacement: str, text: str) -> str:
    def swap(match: re.Match) -> str:
        if _CURRENCY_BEFORE.search(text[max(0, match.start() - 6) : match.start()]):
            return match.group(0)
        return replacement

    return pattern.sub(swap, text)


def redact_text(text: str) -> str:
    if not text:
        return text
    out = _PAN.sub("[PAN]", text)
    out = _AADHAAR.sub("[ID]", out)
    out = _EMAIL.sub("[email]", out)
    out = _mask_unless_amount(_PHONE, "[phone]", out)
    out = _mask_unless_amount(_LONG_DIGITS, "[number]", out)
    out = _OTP.sub(lambda m: (m.group(1) or "") + "[code]", out)
    return out


def redact_value(value):
    """Recursively redact strings inside JSON-like data."""
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        return [redact_value(v) for v in value]
    if isinstance(value, dict):
        return {k: redact_value(v) for k, v in value.items()}
    return value
