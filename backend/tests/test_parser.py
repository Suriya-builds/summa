from datetime import datetime

import pytest

from app.services.sms_parser import parse_transaction

R = datetime(2026, 10, 3, 14, 30)

POSITIVE = [
    ("Sent Rs.250.00 From HDFC Bank A/C *1234 To SWIGGY On 03/10/26 Ref 427612345678 Not You? Call 18002586161/SMS BLOCK UPI to 7308080808", "debit", 250.00, "SWIGGY"),
    ("Rs 1500.00 debited from a/c **1234 on 03-10-26 to VPA raju.k@okaxis(UPI Ref No 427612345678). Not you? Call 18002586161", "debit", 1500.00, "raju.k@okaxis"),
    ("Dear UPI user A/C X1234 debited by 120.0 on date 03Oct26 trf to ZOMATO Refno 427612345678. If not u? call 1800111109. -SBI", "debit", 120.00, "ZOMATO"),
    ("Dear SBI User, your A/c X1234-credited by Rs.5000 on 01Oct26 transfer from RAMESH KUMAR Ref No 427612345678 -SBI", "credit", 5000.00, "RAMESH KUMAR"),
    ("ICICI Bank Acct XX123 debited for Rs 349.00 on 03-Oct-26; NETFLIX credited. UPI:427612345678. Call 18002662 for dispute.", "debit", 349.00, "NETFLIX"),
    ("INR 499.00 debited\nA/c no. XX1234\n03-10-26, 14:22:10\nUPI/P2M/427612345678/AMAZON PAY\nNot you? SMS BLOCKUPI Cust ID to 919951860002\nAxis Bank", "debit", 499.00, "AMAZON PAY"),
    ("Received Rs.2000.00 in your Kotak Bank AC X1234 from priya@okhdfcbank on 02-10-26.UPI Ref:427612345678.", "credit", 2000.00, "priya@okhdfcbank"),
    ("Alert: You've spent Rs.1,299.00 on your HDFC Bank Credit Card xx1234 at MYNTRA on 2026-10-03:18:22:10. Avl Lmt: Rs.48,701.00.", "debit", 1299.00, "MYNTRA"),
    ("INR 2,499.00 spent on ICICI Bank Card XX1234 on 03-Oct-26 at AMAZON. Avl Lmt: INR 1,20,000.00. To dispute, call 18002662", "debit", 2499.00, "AMAZON"),
    ("Rs.2000 withdrawn from A/c XX1234 at ATM on 03-10-26. Avl Bal Rs.12,345.67. Not you? Call 18002586161", "debit", 2000.00, "ATM Cash Withdrawal"),
    ("Your a/c XX1234 is credited with INR 35,000.00 on 01-10-26 by NEFT from ACME TECH PVT LTD (Ref no N274260012345). Avl bal INR 41,220.50", "credit", 35000.00, "ACME TECH PVT LTD"),
    ("Your SB A/c **1234 Debited for Rs:150.00 on 03-10-2026 14:05:11 by Mob Bk ref no 427612345678 Avl Bal Rs:8,220.10 -Canara Bank", "debit", 150.00, None),
    ("Rs 1300.00 debited from a/c **4821 on 04-10-26 to VPA 9845012345@ybl(UPI Ref No 473256846712). Not you?", "debit", 1300.00, "9845012345@ybl"),
]

NEGATIVE = [
    "123456 is your OTP for txn of INR 500.00 at AMAZON on card XX1234. Valid for 10 mins. Do not share with anyone.",
    "Your a/c XX1234 will be debited Rs 4999 for Annual Plan. To cancel click bit.ly/x9Kd2",
    "Flat 50% off! Get Rs 500 cashback credited on your first order. Use code NEW50. T&C",
    "raju@ybl has requested money Rs 4,999 from you. Enter UPI PIN to approve the collect request.",
    "Your HDFC Bank Credit Card xx1234 statement is generated. Total due Rs.12,300. Min due Rs.615. Due date 20-10-26",
    "Payment of Rs.299 received for your Jio number 9876543210. Thank you.",
    "Txn of Rs 899.00 at ZARA on card XX1234 declined due to insufficient funds.",
    "Hi, are we meeting at 5? I paid 200 for tea",
]


@pytest.mark.parametrize("body,direction,amount,counterparty", POSITIVE)
def test_parses_bank_formats(body, direction, amount, counterparty):
    t = parse_transaction(body, R)
    assert t is not None
    assert t.direction == direction
    assert t.amount_paise == round(amount * 100)
    if counterparty:
        assert t.counterparty == counterparty


@pytest.mark.parametrize("body", NEGATIVE)
def test_ignores_non_transactions(body):
    assert parse_transaction(body, R) is None


def test_balance_not_taken_as_amount():
    t = parse_transaction("Rs.2000 withdrawn from A/c XX1234 at ATM on 03-10-26. Avl Bal Rs.12,345.67.", R)
    assert t.amount_paise == 200000
    assert t.balance_paise == 1234567


def test_date_and_time_extracted():
    t = parse_transaction(POSITIVE[7][0], R)
    assert t.occurred_at == datetime(2026, 10, 3, 18, 22, 10)


def test_future_date_falls_back_to_received_time():
    t = parse_transaction("Sent Rs.50.00 From HDFC Bank A/C *1234 To SWIGGY On 03/12/26 Ref 427612345678", R)
    assert t.occurred_at == R
