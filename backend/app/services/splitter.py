"""Turn pasted text or an uploaded file into individual SMS records.

Supported inputs:
  * plain text  - one message per line, or blocks separated by blank lines
  * prefixed    - "SENDER | date | body" or "VM-HDFCBK: body"
  * CSV         - columns named body/text/message, sender/address, date/time
  * JSON        - a list of objects with the same keys
  * XML         - the format written by the Android app "SMS Backup & Restore"
"""
from __future__ import annotations

import csv
import io
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime

from .timeutil import parse_loose

BODY_KEYS = ("body", "text", "message", "sms", "content", "msg")
SENDER_KEYS = ("sender", "address", "from", "number", "sender_id", "senderid")
DATE_KEYS = ("date", "received_at", "received", "timestamp", "time", "datetime", "date_time", "date_sent")

# DLT sender headers look like "VM-HDFCBK" or "JD-SBIUPI-S"; anything else before a colon is body text.
_HEADER = r"[A-Za-z]{2}-[A-Za-z0-9]{3,9}(?:-[A-Za-z])?"
_PHONE = r"\+?\d{10,13}"
_SENDER_COLON = re.compile(rf"^\s*({_HEADER}|{_PHONE})\s*[:>]\s+(.+)$", re.S)
_PIPE = re.compile(r"^\s*([^|]{1,40})\|([^|]{0,40})\|(.+)$", re.S)
_BRACKET_DATE = re.compile(rf"^\s*\[([^\]]{{6,30}})\]\s*({_HEADER}|{_PHONE})?\s*[:\-]?\s*(.+)$", re.S)


class ImportFormatError(ValueError):
    """The upload could not be read as any supported format."""


@dataclass
class RawMessage:
    body: str
    sender: str = ""
    received_at: datetime | None = None


def _clean(text: str) -> str:
    return re.sub(r"[ \t\r\f\v]+", " ", text.replace(" ", " ")).strip()


def _parse_line(block: str) -> RawMessage | None:
    block = block.strip()
    if not block:
        return None
    m = _PIPE.match(block)
    if m:
        sender, date_text, body = (part.strip() for part in m.groups())
        when = parse_loose(date_text)
        if when is not None or not date_text:
            return RawMessage(body=_clean(body), sender=sender[:64], received_at=when)
    m = _BRACKET_DATE.match(block)
    if m:
        when = parse_loose(m.group(1))
        if when is not None:
            return RawMessage(body=_clean(m.group(3)), sender=(m.group(2) or "")[:64], received_at=when)
    m = _SENDER_COLON.match(block)
    if m:
        return RawMessage(body=_clean(m.group(2)), sender=m.group(1)[:64])
    return RawMessage(body=_clean(block))


def parse_text(text: str) -> list[RawMessage]:
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return []
    if re.search(r"\n\s*\n", text):
        blocks = re.split(r"\n\s*\n", text)
    else:
        blocks = text.split("\n")
    out: list[RawMessage] = []
    for block in blocks:
        msg = _parse_line(block)
        if msg and len(msg.body) >= 8:
            out.append(msg)
    return out


def _pick(row: dict, keys: tuple[str, ...]) -> object:
    lowered = {str(k).strip().lower(): v for k, v in row.items() if k is not None}
    for key in keys:
        if key in lowered and lowered[key] not in (None, ""):
            return lowered[key]
    return None


def _from_rows(rows: list[dict]) -> list[RawMessage]:
    out: list[RawMessage] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        body = _pick(row, BODY_KEYS)
        if not body or not str(body).strip():
            continue
        sender = _pick(row, SENDER_KEYS)
        out.append(
            RawMessage(
                body=_clean(str(body)),
                sender=str(sender).strip()[:64] if sender else "",
                received_at=parse_loose(_pick(row, DATE_KEYS)),
            )
        )
    return out


def parse_csv(text: str) -> list[RawMessage]:
    reader = csv.DictReader(io.StringIO(text))
    headers = [h.strip().lower() for h in (reader.fieldnames or []) if h]
    if not any(h in BODY_KEYS for h in headers):
        raise ImportFormatError(
            "The CSV needs a column named body, text or message. Found: " + (", ".join(headers) or "no header row")
        )
    return _from_rows(list(reader))


def parse_json(text: str) -> list[RawMessage]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ImportFormatError(f"The file is not valid JSON ({exc.msg}, line {exc.lineno}).") from exc
    if isinstance(data, dict):
        for key in ("messages", "sms", "smses", "data", "items"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
    if not isinstance(data, list):
        raise ImportFormatError("The JSON must be a list of messages.")
    return _from_rows(data)


def parse_xml(text: str) -> list[RawMessage]:
    if re.search(r"<!\s*(DOCTYPE|ENTITY)", text, re.I):
        raise ImportFormatError("XML files with a DOCTYPE or entity declarations are not accepted.")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise ImportFormatError(f"The file is not valid XML ({exc}).") from exc
    out: list[RawMessage] = []
    for node in root.iter("sms"):
        # type 1 = received, 2 = sent. Only received messages are bank alerts.
        if node.get("type") not in (None, "1"):
            continue
        body = node.get("body") or ""
        if not body.strip():
            continue
        out.append(
            RawMessage(
                body=_clean(body),
                sender=(node.get("address") or "").strip()[:64],
                received_at=parse_loose(node.get("date")),
            )
        )
    return out


def parse_upload(filename: str, text: str) -> list[RawMessage]:
    """Pick a parser from the file extension, falling back to the content."""
    name = (filename or "").lower()
    stripped = text.lstrip("﻿ \t\r\n")
    if name.endswith(".xml") or stripped.startswith("<"):
        return parse_xml(stripped)
    if name.endswith(".json") or stripped[:1] in ("[", "{"):
        return parse_json(stripped)
    if name.endswith(".csv"):
        return parse_csv(stripped)
    first_line = stripped.split("\n", 1)[0].lower()
    if "," in first_line and any(k in [h.strip().strip('"') for h in first_line.split(",")] for k in BODY_KEYS):
        return parse_csv(stripped)
    return parse_text(stripped)
