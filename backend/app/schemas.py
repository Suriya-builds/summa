"""Request bodies. Responses are plain dictionaries built by the services."""
from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator

_EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,185}\.[A-Za-z]{2,24}$")


class SignupIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: str = Field(max_length=254)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        value = value.strip().lower()
        if not _EMAIL.match(value):
            raise ValueError("Enter a valid email address.")
        return value

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Enter your name.")
        return value


class LoginIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return value.strip().lower()


class ImportTextIn(BaseModel):
    text: str = Field(min_length=1)
    use_ai: bool = False


class TransactionPatch(BaseModel):
    category: str | None = Field(default=None, max_length=24)
    note: str | None = Field(default=None, max_length=200)
    counterparty: str | None = Field(default=None, min_length=1, max_length=120)
    apply_to_merchant: bool = True


class TransactionCreate(BaseModel):
    date: str = Field(description="YYYY-MM-DD or YYYY-MM-DDTHH:MM")
    amount: float = Field(gt=0, le=100_000_000)
    direction: str = Field(pattern="^(debit|credit)$")
    counterparty: str = Field(min_length=1, max_length=120)
    category: str | None = Field(default=None, max_length=24)
    note: str | None = Field(default=None, max_length=200)


class BudgetsIn(BaseModel):
    limits: dict[str, float]


class ScamCheckIn(BaseModel):
    text: str = Field(min_length=5, max_length=4000)
    sender: str = Field(default="", max_length=64)
    explain: bool = False


class AskIn(BaseModel):
    question: str = Field(min_length=2, max_length=1000)


class NarrativeIn(BaseModel):
    month: str | None = None
