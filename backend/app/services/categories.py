"""The fixed category list used across the app."""
from __future__ import annotations

EXPENSE_CATEGORIES: dict[str, str] = {
    "food_dining": "Food & Dining",
    "groceries": "Groceries",
    "transport": "Transport",
    "shopping": "Shopping",
    "bills": "Bills & Recharges",
    "rent": "Rent & Housing",
    "entertainment": "Entertainment",
    "health": "Health",
    "personal": "Personal Care & Fitness",
    "education": "Education",
    "travel": "Travel",
    "investments": "Investments",
    "transfers": "Transfers to People",
    "cash": "Cash Withdrawal",
    "fees": "Fees & Charges",
    "other": "Other",
}

INCOME_CATEGORIES: dict[str, str] = {
    "salary": "Salary & Allowance",
    "refund": "Refunds & Cashback",
    "interest": "Interest",
    "transfer_in": "Money Received",
    "other_income": "Other Income",
}

ALL_CATEGORIES: dict[str, str] = {**EXPENSE_CATEGORIES, **INCOME_CATEGORIES}

# Money moved into savings is not counted as spending.
NON_SPEND_CATEGORIES = {"investments"}

# Categories where trimming is realistic, used by the budget suggester.
DISCRETIONARY = {"food_dining", "shopping", "entertainment", "travel", "personal", "other"}


def label(category: str) -> str:
    return ALL_CATEGORIES.get(category, category.replace("_", " ").title())


def valid_for(direction: str) -> dict[str, str]:
    return INCOME_CATEGORIES if direction == "credit" else EXPENSE_CATEGORIES
