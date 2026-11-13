"""SQLAlchemy models. Money is stored as integer paise to avoid float drift."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    """Naive UTC timestamp. SQLite does not keep time zones, so all stored times are naive."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80))
    password_hash: Mapped[str] = mapped_column(String(255))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    sessions: Mapped[list[AuthSession]] = relationship(back_populates="user", cascade="all, delete-orphan")


class AuthSession(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime)

    user: Mapped[User] = relationship(back_populates="sessions")


class Message(Base):
    """One imported SMS. `kind` is transaction, scam, otp, promo or other."""

    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("user_id", "fingerprint", name="uq_message_fingerprint"),
        Index("ix_message_user_kind", "user_id", "kind"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    sender: Mapped[str] = mapped_column(String(64), default="")
    body: Mapped[str] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(DateTime)
    kind: Mapped[str] = mapped_column(String(16))
    scam_score: Mapped[float] = mapped_column(Float, default=0.0)
    scam_level: Mapped[str] = mapped_column(String(12), default="safe")
    scam_reasons: Mapped[list] = mapped_column(JSON, default=list)
    parse_source: Mapped[str] = mapped_column(String(8), default="none")
    dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    fingerprint: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (Index("ix_txn_user_time", "user_id", "occurred_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    message_id: Mapped[int | None] = mapped_column(ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime)
    amount_paise: Mapped[int] = mapped_column(Integer)
    direction: Mapped[str] = mapped_column(String(6))  # debit | credit
    counterparty: Mapped[str] = mapped_column(String(120), default="Unknown")
    counterparty_key: Mapped[str] = mapped_column(String(120), default="unknown", index=True)
    channel: Mapped[str] = mapped_column(String(12), default="other")
    account_tail: Mapped[str | None] = mapped_column(String(8), nullable=True)
    balance_paise: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reference: Mapped[str | None] = mapped_column(String(40), nullable=True)
    category: Mapped[str] = mapped_column(String(24), default="other")
    category_source: Mapped[str] = mapped_column(String(8), default="rule")
    category_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    note: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    message: Mapped[Message | None] = relationship()


class MerchantRule(Base):
    """A category the user chose for a merchant. Applied before any other categoriser."""

    __tablename__ = "merchant_rules"
    __table_args__ = (UniqueConstraint("user_id", "counterparty_key", name="uq_merchant_rule"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    counterparty_key: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(24))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Budget(Base):
    __tablename__ = "budgets"
    __table_args__ = (UniqueConstraint("user_id", "category", name="uq_budget_category"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(24))
    monthly_limit_paise: Mapped[int] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(10))  # user | assistant
    content: Mapped[str] = mapped_column(Text)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
