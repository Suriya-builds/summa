from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..deps import get_current_user, limit
from ..models import Message, User
from ..schemas import ImportTextIn
from ..services import llm, pipeline, sample_data, splitter

router = APIRouter(prefix="/api/messages", tags=["messages"])

KINDS = {"transaction", "scam", "otp", "promo", "other"}


def message_dict(m: Message) -> dict:
    return {
        "id": m.id,
        "sender": m.sender,
        "body": m.body,
        "received_at": m.received_at.isoformat(timespec="minutes"),
        "kind": m.kind,
        "scam_level": m.scam_level,
        "scam_score": round(m.scam_score, 3),
        "parse_source": m.parse_source,
    }


def _run_import(db: Session, user: User, raws: list[splitter.RawMessage], use_ai: bool) -> dict:
    if not raws:
        raise HTTPException(status_code=422, detail="No messages were found in what you provided.")
    if use_ai and not llm.is_enabled():
        raise HTTPException(status_code=400, detail="AI parsing needs an API key on the server. Import without it, or configure ANTHROPIC_API_KEY.")
    return pipeline.import_messages(db, user, raws, use_llm=use_ai).as_dict()


@router.post("/import")
def import_text(body: ImportTextIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    limit(f"import:{user.id}", 30, 300)
    if len(body.text.encode("utf-8")) > settings.max_import_bytes:
        raise HTTPException(status_code=413, detail=f"Pasted text is larger than {settings.max_import_bytes // 1024} KB. Split it into smaller parts.")
    return _run_import(db, user, splitter.parse_text(body.text), body.use_ai)


@router.post("/import-file")
async def import_file(
    file: UploadFile = File(...),
    use_ai: bool = Form(False),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    limit(f"import:{user.id}", 30, 300)
    data = await file.read(settings.max_import_bytes + 1)
    if len(data) > settings.max_import_bytes:
        raise HTTPException(status_code=413, detail=f"The file is larger than {settings.max_import_bytes // 1024} KB.")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=415, detail="The file is not UTF-8 text. Upload a .txt, .csv, .json or .xml export.") from None
    if "\x00" in text:
        raise HTTPException(status_code=415, detail="The file looks binary. Upload a .txt, .csv, .json or .xml export.")
    try:
        raws = splitter.parse_upload(file.filename or "", text)
    except splitter.ImportFormatError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _run_import(db, user, raws, use_ai)


@router.post("/sample")
def import_sample(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """Generate a synthetic inbox and import it through the normal pipeline."""
    limit(f"import:{user.id}", 30, 300)
    return pipeline.import_messages(db, user, sample_data.generate_inbox()).as_dict()


@router.get("")
def list_messages(
    kind: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if kind and kind not in KINDS:
        raise HTTPException(status_code=422, detail=f"kind must be one of {', '.join(sorted(KINDS))}.")
    base = select(Message).where(Message.user_id == user.id)
    if kind:
        base = base.where(Message.kind == kind)
    total = db.execute(select(func.count()).select_from(base.subquery())).scalar_one()
    rows = db.execute(base.order_by(Message.received_at.desc()).offset((page - 1) * page_size).limit(page_size)).scalars()
    counts = dict(db.execute(select(Message.kind, func.count()).where(Message.user_id == user.id).group_by(Message.kind)).all())
    return {"items": [message_dict(m) for m in rows], "total": total, "page": page, "page_size": page_size, "counts": counts}
