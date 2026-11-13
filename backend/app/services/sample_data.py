"""Generate a realistic synthetic SMS inbox.

The output is plain SMS text. It goes through exactly the same import pipeline
as a real inbox, so the demo exercises the parser, categoriser and scam detector
rather than loading prepared results.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta

from .splitter import RawMessage
from .timeutil import now_ist

HDFC_TAIL, SBI_TAIL, CARD_TAIL = "4821", "7730", "9005"
_MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _money(value: float, commas: bool = False) -> str:
    return f"{value:,.2f}" if commas else f"{value:.2f}"


class _Inbox:
    def __init__(self, rng: random.Random) -> None:
        self.rng = rng
        self.messages: list[RawMessage] = []
        self.hdfc_balance = 18_450.75
        self.card_limit = 120_000.00

    def _ref(self) -> str:
        return str(self.rng.randint(400_000_000_000, 499_999_999_999))

    def add(self, sender: str, when: datetime, body: str) -> None:
        self.messages.append(RawMessage(body=body, sender=sender, received_at=when))

    # --- HDFC savings account, UPI ------------------------------------------
    def hdfc_debit(self, when: datetime, amount: float, to: str) -> None:
        self.hdfc_balance -= amount
        if "@" in to:
            body = (f"Rs {_money(amount)} debited from a/c **{HDFC_TAIL} on {when:%d-%m-%y} to VPA {to}"
                    f"(UPI Ref No {self._ref()}). Not you? Call 18002586161")
        else:
            body = (f"Sent Rs.{_money(amount)} From HDFC Bank A/C *{HDFC_TAIL} To {to} On {when:%d/%m/%y} "
                    f"Ref {self._ref()} Not You? Call 18002586161/SMS BLOCK UPI to 7308080808")
        self.add("VM-HDFCBK", when, body)

    def hdfc_credit_neft(self, when: datetime, amount: float, sender_name: str) -> None:
        self.hdfc_balance += amount
        self.add("VM-HDFCBK", when,
                 f"Your a/c XX{HDFC_TAIL} is credited with INR {_money(amount, True)} on {when:%d-%m-%y} by NEFT from "
                 f"{sender_name} (Ref no N{self.rng.randint(10**11, 10**12 - 1)}). Avl bal INR {_money(self.hdfc_balance, True)}")

    def hdfc_credit_upi(self, when: datetime, amount: float, vpa: str) -> None:
        self.hdfc_balance += amount
        self.add("VM-HDFCBK", when,
                 f"Received Rs.{_money(amount)} in your HDFC Bank AC X{HDFC_TAIL} from {vpa} on {when:%d-%m-%y}."
                 f"UPI Ref:{self._ref()}.")

    def hdfc_atm(self, when: datetime, amount: float) -> None:
        self.hdfc_balance -= amount
        self.add("VM-HDFCBK", when,
                 f"Rs.{amount:.0f} withdrawn from A/c XX{HDFC_TAIL} at ATM on {when:%d-%m-%y}. "
                 f"Avl Bal Rs.{_money(self.hdfc_balance, True)}. Not you? Call 18002586161")

    def hdfc_refund(self, when: datetime, amount: float, merchant: str) -> None:
        self.hdfc_balance += amount
        self.add("VM-HDFCBK", when,
                 f"Refund of Rs.{_money(amount)} has been credited to your HDFC Bank A/c XX{HDFC_TAIL} on {when:%d-%m-%y} "
                 f"from {merchant}. Avl bal: Rs.{_money(self.hdfc_balance, True)}")

    def hdfc_interest(self, when: datetime, amount: float) -> None:
        self.hdfc_balance += amount
        self.add("VM-HDFCBK", when,
                 f"Your a/c XX{HDFC_TAIL} has been credited with interest of Rs {_money(amount)} on {when:%d-%m-%y}. "
                 f"Avl Bal Rs {_money(self.hdfc_balance, True)} -HDFC Bank")

    # --- SBI savings account, small UPI payments -----------------------------
    def sbi_debit(self, when: datetime, amount: float, to: str) -> None:
        date = f"{when.day:02d}{_MON[when.month - 1]}{when:%y}"
        self.add("AD-SBIUPI", when,
                 f"Dear UPI user A/C X{SBI_TAIL} debited by {amount:.1f} on date {date} trf to {to} "
                 f"Refno {self._ref()}. If not u? call 1800111109. -SBI")

    def sbi_credit(self, when: datetime, amount: float, name: str) -> None:
        date = f"{when.day:02d}{_MON[when.month - 1]}{when:%y}"
        self.add("AD-SBIUPI", when,
                 f"Dear SBI User, your A/c X{SBI_TAIL}-credited by Rs.{amount:.0f} on {date} transfer from {name} "
                 f"Ref No {self._ref()} -SBI")

    # --- ICICI credit card ---------------------------------------------------
    def card_spend(self, when: datetime, amount: float, merchant: str) -> None:
        self.card_limit -= amount
        date = f"{when.day:02d}-{_MON[when.month - 1]}-{when:%y}"
        self.add("JD-ICICIT", when,
                 f"INR {_money(amount, True)} spent on ICICI Bank Card XX{CARD_TAIL} on {date} at {merchant}. "
                 f"Avl Lmt: INR {_money(self.card_limit, True)}. To dispute, call 18002662/SMS BLOCK {CARD_TAIL} to 9215676766")


def _at(day: datetime, rng: random.Random, start_hour: int = 8, end_hour: int = 22) -> datetime:
    return day.replace(hour=rng.randint(start_hour, end_hour), minute=rng.randint(0, 59), second=rng.randint(0, 59))


def _pick_amount(rng: random.Random, low: int, high: int, step: int = 1) -> float:
    return float(rng.randrange(low, high + 1, step))


def generate_inbox(seed: int | None = None, now: datetime | None = None) -> list[RawMessage]:
    """About eleven weeks of messages ending at `now`: two full months and the current one."""
    rng = random.Random(seed)
    now = now or now_ist()
    first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start = (first_of_month - timedelta(days=45)).replace(day=1)
    inbox = _Inbox(rng)

    friends_vpa = ["karthik.r@okicici", "sneha.reddy@oksbi", "9845012345@ybl", "arjun.menon@okaxis"]
    friends_name = ["PRIYA S", "ROHIT VERMA", "ANITA SHARMA"]
    food_delivery = ["SWIGGY", "ZOMATO"]
    eateries = ["SRI GANESH TEA STALL", "ANNAPOORNA MESS", "CAMPUS CANTEEN", "UDUPI DARSHINI", "CHAI POINT"]
    grocers = ["ZEPTO", "BLINKIT", "BIGBASKET", "LOTUS SUPERMARKET", "NANDHINI MILK BOOTH"]
    rides = ["UBER INDIA", "RAPIDO", "NAMMA METRO BMRCL", "OLA CABS"]
    shops = ["AMAZON", "FLIPKART", "MYNTRA", "DECATHLON", "NYKAA"]

    day = start
    month_index = 0
    current_month = (now.year, now.month)
    big_purchase_done = False
    while day.date() <= now.date():
        is_current = (day.year, day.month) == current_month
        if day.day == 1 and day != start:
            month_index += 1
        weekday = day.weekday() < 5
        events: list[tuple[datetime, callable]] = []

        def schedule(when: datetime, fn, *args) -> None:
            if when <= now:
                events.append((when, lambda: fn(when, *args)))

        # --- fixed monthly items ---
        if day.day == 1:
            schedule(day.replace(hour=9, minute=12), inbox.hdfc_credit_neft, 45_000.0, "ACME TECH PVT LTD")
        if day.day == 3:
            schedule(day.replace(hour=10, minute=40), inbox.hdfc_debit, 11_500.0, "GREEN NEST PG")
        if day.day == 5:
            schedule(day.replace(hour=6, minute=5), inbox.hdfc_debit, 199.0, "NETFLIX")
        if day.day == 7:
            schedule(day.replace(hour=8, minute=30), inbox.hdfc_debit, 3_000.0, "GROWW")
        if day.day == 10:
            schedule(day.replace(hour=7, minute=45), inbox.hdfc_debit, 119.0, "SPOTIFY INDIA")
        if day.day == 12:
            schedule(day.replace(hour=11, minute=20), inbox.hdfc_debit, 349.0, "JIO PREPAID RECHARGE")
        if day.day == 15:
            schedule(day.replace(hour=19, minute=10), inbox.hdfc_debit, _pick_amount(rng, 780, 1150, 10), "BESCOM")
        if day.day == 18:
            schedule(day.replace(hour=6, minute=55), inbox.card_spend, 999.0, "CULT FIT")
        if day.day == 21:
            schedule(_at(day, rng, 10, 20), inbox.hdfc_atm, 2_000.0)

        # --- everyday spending ---
        delivery_chance = 0.62 if is_current else 0.36
        if rng.random() < delivery_chance:
            amount = _pick_amount(rng, 180, 520) * (1.25 if is_current else 1.0)
            schedule(_at(day, rng, 12, 22), inbox.hdfc_debit, round(amount), rng.choice(food_delivery))
        if rng.random() < (0.7 if weekday else 0.3):
            schedule(_at(day, rng, 8, 18), inbox.sbi_debit, _pick_amount(rng, 20, 140, 5), rng.choice(eateries))
        if rng.random() < 0.28:
            schedule(_at(day, rng, 9, 21), inbox.hdfc_debit, _pick_amount(rng, 150, 900, 10), rng.choice(grocers))
        if rng.random() < (0.5 if weekday else 0.25):
            schedule(_at(day, rng, 8, 22), inbox.sbi_debit, _pick_amount(rng, 40, 320, 5), rng.choice(rides))
        if day.day in (6, 16, 26):
            schedule(_at(day, rng, 8, 20), inbox.hdfc_debit, _pick_amount(rng, 500, 1200, 50), "HP PETROL PUMP KORAMANGALA")
        if rng.random() < 0.1:
            schedule(_at(day, rng, 10, 23), inbox.card_spend, _pick_amount(rng, 400, 3500, 50) - 1, rng.choice(shops))
        if day.day in (9, 23):
            schedule(_at(day, rng, 17, 22), inbox.card_spend, _pick_amount(rng, 300, 700, 10), "BOOKMYSHOW")
        if rng.random() < 0.04:
            schedule(_at(day, rng, 10, 20), inbox.sbi_debit, _pick_amount(rng, 150, 900, 5), "APOLLO PHARMACY")
        if day.day in (4, 13, 25):
            schedule(_at(day, rng, 10, 22), inbox.hdfc_debit, _pick_amount(rng, 200, 2000, 50), rng.choice(friends_vpa))
        if day.day in (8, 22):
            if rng.random() < 0.5:
                schedule(_at(day, rng, 10, 22), inbox.hdfc_credit_upi, _pick_amount(rng, 150, 1500, 50), rng.choice(friends_vpa))
            else:
                schedule(_at(day, rng, 10, 22), inbox.sbi_credit, _pick_amount(rng, 150, 1500, 50), rng.choice(friends_name))
        if day.day == 27 and rng.random() < 0.8:
            schedule(_at(day, rng, 9, 18), inbox.sbi_debit, _pick_amount(rng, 30, 180, 5), "CITY XEROX AND STATIONERY")

        # --- one-off items in the previous month ---
        if month_index == 1 and day.day == 19 and not big_purchase_done:
            schedule(day.replace(hour=16, minute=48), inbox.card_spend, 18_499.0, "CROMA ELECTRONICS")
            big_purchase_done = True
        if month_index == 1 and day.day == 24:
            schedule(day.replace(hour=13, minute=5), inbox.hdfc_refund, 1_299.0, "FLIPKART")
        if day.month in (3, 6, 9, 12) and day.day == 30:
            schedule(day.replace(hour=23, minute=10), inbox.hdfc_interest, 212.0)

        for _, run in sorted(events, key=lambda e: e[0]):
            run()
        day += timedelta(days=1)

    _add_noise(inbox, rng, start, now)
    inbox.messages.sort(key=lambda m: m.received_at or now)
    return inbox.messages


def _add_noise(inbox: _Inbox, rng: random.Random, start: datetime, now: datetime) -> None:
    """OTPs, promotions, service notices and scam attempts spread over the period."""
    span = max(1, int((now - start).total_seconds()))

    def moment() -> datetime:
        return (start + timedelta(seconds=rng.randint(0, span))).replace(microsecond=0)

    def code() -> str:
        return str(rng.randint(100000, 999999))

    for _ in range(7):
        inbox.add("VM-HDFCBK", moment(),
                  f"{code()} is your OTP for txn of INR {rng.randint(200, 3000)}.00 at {rng.choice(['AMAZON', 'FLIPKART', 'MYNTRA'])} "
                  f"on card XX{CARD_TAIL}. Valid for 10 mins. Do not share it with anyone. -ICICI Bank")
    for _ in range(3):
        inbox.add("JM-SWIGGY", moment(), f"{code()} is the OTP to log in to your Swiggy account. Never share your OTP with anyone.")
    promos = [
        ("AX-MYNTRA", "Flat 50% off on Myntra End of Reason Sale! Use code EORS50. Shop now on the app. T&C apply."),
        ("VK-ZOMATO", "Hungry? Get 60% off up to Rs 120 on your next order. Use code TREAT. Order now on Zomato. T&C apply."),
        ("JD-AMAZON", "Amazon Great Indian Festival starts tomorrow! Up to 70% off on electronics and fashion. Wishlist now."),
        ("BP-JIOINF", "Your monthly data pack expires soon. Recharge on the MyJio app to continue enjoying services."),
        ("AD-BMSHOW", "New releases this Friday! Book now on BookMyShow and get offers on your favourite snacks."),
        ("VM-CULTFT", "Your Cult Fit membership renews on the 18th. Thank you for staying active with us."),
        ("JK-FLPKRT", "Flipkart: Your order has been shipped and will arrive in 2 days. Track it in the app."),
        ("JD-ICICIT", f"Your ICICI Bank Credit Card XX{CARD_TAIL} statement is generated. Total due Rs.6,412.00. "
                      "Pay via NetBanking or the official app before the due date."),
        ("VM-HDFCBK", "HDFC Bank: Never share your OTP, CVV or PIN with anyone. Bank staff will never ask for them."),
        ("AX-IRCTCi", "Your booking is confirmed. PNR 4521783345, Train 12658, Coach S4. Happy journey. -IRCTC"),
    ]
    for sender, body in promos:
        inbox.add(sender, moment(), body)

    scams = [
        ("+919812045567", "Dear Customer, your HDFC Bank account will be blocked today. Update your KYC immediately at "
                          "hdfc-kyc-update.in/verify"),
        ("+917409981234", "Dear consumer, your electricity power will be disconnected tonight at 9.30 pm because your "
                          "previous month bill was not updated. Call electricity officer 9123456780"),
        ("VK-REWARD", "You received Rs 4,999 from PRIYA S. Enter your UPI PIN to receive the money in your account. "
                      "bit.ly/Rcv4999"),
        ("+918800554321", "Congratulations! You have won Rs 25,00,000 in KBC lucky draw. To claim call 8800554321 or "
                          "WhatsApp now"),
        ("+919900112233", "Hi, I am HR from Amazon. We offer part-time job, like YouTube videos and earn Rs 4,999 per day. "
                          "Join Telegram t.me/amzn_jobs"),
        ("BX-DLVRY", "Your India Post parcel is on hold due to incomplete address. Pay Rs 25 re-delivery fee at "
                     "cutt.ly/ipost25 within 12 hrs"),
        ("JK-ALERTS", f"Your a/c XX{HDFC_TAIL} will be debited Rs 4,999 for annual subscription. If not done by you click "
                      "rb.gy/stop4999 to cancel"),
        ("+919731000456", "Your SBI account is temporarily locked. Install QuickSupport and share the code with our "
                          "officer 9731000456"),
        ("VM-UPIREQ", "rahul.traders@ybl has requested Rs 2,500 from you. Approve the collect request in your UPI app."),
    ]
    for sender, body in scams:
        inbox.add(sender, moment(), body)
