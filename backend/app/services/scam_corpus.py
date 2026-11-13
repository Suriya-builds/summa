"""Synthetic training corpus for the scam text model.

Every message here is generated from templates written for this project. No real
SMS is included. Templates are split into a training group and a held-out group so
the reported score reflects messages worded differently from anything in training.
"""
from __future__ import annotations

import random

BANKS = ["HDFC Bank", "SBI", "ICICI Bank", "Axis Bank", "Kotak Bank", "PNB", "Canara Bank", "Bank of Baroda",
         "Yes Bank", "IDFC First Bank", "Union Bank", "IndusInd Bank"]
BRANDS = ["Amazon", "Flipkart", "Paytm", "PhonePe", "Google Pay", "Jio", "Airtel", "Netflix", "Swiggy", "Zomato",
          "Myntra", "IRCTC", "India Post", "BlueDart", "Delhivery", "FedEx", "DHL"]
SHORT = ["bit.ly", "tinyurl.com", "cutt.ly", "rb.gy", "is.gd", "t.ly", "shorturl.at"]
FAKE_DOMAINS = ["{b}-kyc.in", "{b}-secure.co", "{b}bank-update.com", "{b}-verify.xyz", "kyc-{b}.online",
                "{b}-rewards.top", "secure-{b}.site", "{b}-netbanking.info", "{b}help.live", "my{b}-alert.club"]
MERCHANTS = ["SWIGGY", "ZOMATO", "AMAZON", "FLIPKART", "UBER", "BIGBASKET", "MYNTRA", "IRCTC", "NETFLIX", "DMART",
             "RELIANCE FRESH", "APOLLO PHARMACY", "BOOKMYSHOW", "ZEPTO", "RAPIDO", "JIO RECHARGE"]
PEOPLE = ["RAJU KUMAR", "PRIYA S", "ANITA SHARMA", "KARTHIK R", "MOHAMMED IMRAN", "SNEHA REDDY"]


def _token(rng: random.Random, n: int = 6) -> str:
    return "".join(rng.choice("abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(n))


def _fill(rng: random.Random, template: str) -> str:
    bank = rng.choice(BANKS)
    brand = rng.choice(BRANDS)
    slug = rng.choice([bank, brand]).split()[0].lower()
    values = {
        "bank": bank,
        "brand": brand,
        "short": f"{rng.choice(SHORT)}/{_token(rng)}",
        "fake": rng.choice(FAKE_DOMAINS).format(b=slug) + rng.choice(["", "/login", "/verify", "/update", f"/{_token(rng, 4)}"]),
        "phone": str(rng.randint(6000000000, 9999999999)),
        "amt": f"{rng.choice([199, 499, 999, 1499, 2500, 4999, 9999, 25000, 49999]):,}",
        "bigamt": f"{rng.choice([25, 50, 75]) },00,000",
        "small": f"{rng.randint(20, 3500)}.{rng.choice(['00', '50', '00'])}",
        "tail": str(rng.randint(1000, 9999)),
        "otp": str(rng.randint(100000, 999999)),
        "ref": str(rng.randint(400000000000, 499999999999)),
        "merchant": rng.choice(MERCHANTS),
        "person": rng.choice(PEOPLE),
        "date": f"{rng.randint(1, 28):02d}-{rng.randint(1, 12):02d}-26",
        "hours": str(rng.choice([2, 12, 24, 48])),
        "bal": f"{rng.randint(500, 90000):,}.{rng.randint(10, 99)}",
        "pct": str(rng.choice([10, 20, 30, 40, 50, 60, 70])),
        "code": rng.choice(["NEW50", "SAVE20", "FEST30", "WELCOME", "FLAT100"]),
    }
    text = template.format(**values)
    if rng.random() < 0.15:
        text = text.upper() if rng.random() < 0.4 else text.replace("Dear", "Dear ")
    return text


SCAM_TRAIN = [
    "Dear Customer, your {bank} account will be blocked today. Update your KYC immediately at {fake}",
    "{bank} ALERT: Your a/c XX{tail} has been suspended due to incomplete KYC. Verify now {short}",
    "Your {bank} netbanking will be deactivated within {hours} hours. Update PAN card details here {fake}",
    "Dear user your {bank} debit card is blocked. Call customer care {phone} to reactivate immediately",
    "Congratulations! You have won Rs {bigamt} in KBC lucky draw. To claim call {phone} or WhatsApp now",
    "You have won a {brand} gift voucher worth Rs {amt}. Claim your reward now: {short}",
    "Dear consumer, your electricity power will be disconnected tonight at 9.30 pm because your previous month bill was not updated. Call electricity officer {phone}",
    "Your {brand} parcel is on hold due to incomplete address. Pay Rs 25 re-delivery fee at {short} within {hours} hrs",
    "Earn Rs {amt} daily working from home. Part time job, no investment. WhatsApp {phone} to start today",
    "Hi, I am HR from {brand}. We offer part-time job, like YouTube videos and earn Rs {amt} per day. Join Telegram {short}",
    "You received Rs {amt} from {person}. Enter your UPI PIN to receive the money in your account. {short}",
    "{bank}: Rs {amt} refund is pending. Click the link and enter UPI PIN to claim your refund {fake}",
    "Your a/c XX{tail} will be debited Rs {amt} for annual subscription. If not done by you click {short} to cancel",
    "Dear customer, share the OTP sent to your mobile to complete your {bank} KYC verification. Call {phone}",
    "Income tax refund of Rs {amt} approved. Submit your bank details to receive the amount: {fake}",
    "Pre-approved instant personal loan of Rs {bigamt} without documents. No CIBIL check. Apply {short}",
    "Your SIM card will be blocked in {hours} hours. Complete e-KYC by calling {phone} immediately",
    "Dear {bank} customer, your reward points worth Rs {amt} will expire today. Redeem now at {fake}",
    "Guaranteed 100% profit daily. Double your money in 7 days. Join our WhatsApp group for stock tips {short}",
    "URGENT: Unusual login to your {bank} account. Verify your identity now or the account will be frozen {fake}",
    "Customs has held your package. Pay clearance charge Rs {amt} at {short} to avoid return",
    "Install the {bank} support app to fix your blocked account: {fake}/support.apk",
    "Your {brand} account is locked. Download AnyDesk and call our executive {phone} for verification",
    "Dear Sir, your PAN is not linked with {bank} a/c. Account will be closed. Update here {short}",
    "Final notice: your {bank} credit card will be blocked. Share card number and CVV on call {phone} to continue service",
    "Lucky winner! Your mobile number has won Rs {bigamt} lottery. Send your name and bank details to WhatsApp {phone}",
    "Work from home data entry job. Salary Rs {amt} weekly. Registration fee Rs 499 only. Contact {phone}",
    "Get crypto profit daily. Invest Rs {amt} and earn double in 24 hours. Risk-free returns. {short}",
    "{bank} Alert: Rs {amt} debited from your a/c. Not you? Stop the transaction now at {fake}",
    "Your FASTag KYC has expired and will be deactivated. Update immediately {short}",
    "Aadhaar update required. Your bank account will be on hold. Link Aadhaar now at {fake}",
    "Dear customer, your gas connection will be disconnected today. Pay pending bill by contacting {phone}",
    "{person} has requested Rs {amt}. Approve the collect request and enter PIN to get cashback of Rs {amt}",
    "Hello, this is {bank} customer care. Your a/c is under review. Send OTP {otp} to this number to avoid blocking",
    "Y0ur {bank} acc0unt is b1ocked. C1ick here to ver1fy: {short}",
    "Cashback of Rs {amt} credited! Claim it before it expires: {short}. Enter your UPI PIN to accept",
]
SCAM_HELD_OUT = [
    "Attention {bank} user, KYC not updated. Service will stop in {hours} hrs. Complete it here: {fake}",
    "We tried delivering your {brand} order. Confirm address and pay Rs 30 at {short}",
    "Your electricity bill is unpaid. Supply will be cut off at 10 pm tonight. Contact lineman on {phone}",
    "Selected for online job! Review hotels and earn Rs {amt} per day. Message {phone} on WhatsApp",
    "To get Rs {amt} in your bank, type your UPI PIN on the next screen. Offer from {brand}: {short}",
    "{bank}: your debit card has been deactivated. Tell the OTP to our agent on {phone} to activate",
    "You are the lucky draw winner of Rs {bigamt}. Claim your prize by paying processing fee. WhatsApp {phone}",
    "Instant loan approved Rs {bigamt}. No paperwork. Disbursal in 5 minutes: {short}",
    "Assured returns of 40% every week on our trading platform. Join Telegram channel {short}",
    "Your {bank} account is temporarily locked. Install QuickSupport and share the code with our officer {phone}",
    "TAX DEPT: refund of Rs {amt} is waiting. Verify PAN and bank account to claim: {fake}",
    "Dear customer your {brand} wallet will be suspended. Complete re-KYC now {fake}",
]
LEGIT_TRAIN = [
    "Sent Rs.{small} From {bank} A/C *{tail} To {merchant} On {date} Ref {ref} Not You? Call 18002586161/SMS BLOCK UPI to 7308080808",
    "Rs {small} debited from a/c **{tail} on {date} to VPA merchant@okaxis(UPI Ref No {ref}). Not you? Call 18002586161",
    "Dear UPI user A/C X{tail} debited by {small} on date {date} trf to {merchant} Refno {ref}. If not u? call 1800111109. -SBI",
    "Dear SBI User, your A/c X{tail}-credited by Rs.{small} on {date} transfer from {person} Ref No {ref} -SBI",
    "{bank} Acct XX{tail} debited for Rs {small} on {date}; {merchant} credited. UPI:{ref}. Call 18002662 for dispute.",
    "INR {small} debited A/c no. XX{tail} {date}, 14:22:10 UPI/P2M/{ref}/{merchant} Not you? SMS BLOCKUPI Cust ID to 919951860002 Axis Bank",
    "Received Rs.{small} in your {bank} AC X{tail} from {person} on {date}.UPI Ref:{ref}.",
    "Alert: You've spent Rs.{small} on your {bank} Credit Card xx{tail} at {merchant} on {date}. Avl Lmt: Rs.{bal}. Not you? Call 18002586161",
    "Rs.{amt} withdrawn from A/c XX{tail} at ATM on {date}. Avl Bal Rs.{bal}. Not you? Call 18002586161",
    "Your a/c XX{tail} is credited with INR {amt} on {date} by NEFT from ACME TECH PVT LTD (Ref no N{ref}). Avl bal INR {bal}",
    "{otp} is your OTP for txn of INR {small} at {merchant} on card XX{tail}. Valid for 10 mins. Do not share it with anyone. -{bank}",
    "{otp} is the OTP to log in to your {brand} account. Never share your OTP with anyone.",
    "Your OTP for {bank} NetBanking is {otp}. It is valid for 5 minutes. {bank} never asks for OTP over call.",
    "Flat {pct}% off on {brand}! Use code {code}. Shop now on the app. T&C apply.",
    "{brand}: Your order has been shipped and will arrive by {date}. Track it in the app.",
    "Your {brand} order was delivered today. Rate your experience in the app.",
    "Recharge of Rs {amt} for your {brand} number is successful. Validity 28 days. Thank you.",
    "Your {bank} Credit Card xx{tail} statement is generated. Total due Rs.{amt}. Due date {date}. Pay via NetBanking or the official app.",
    "Dear Customer, your SIP of Rs {amt} in Nifty 50 Index Fund has been processed on {date}. Units allotted.",
    "Your {brand} ride is arriving in 3 minutes. Driver: Ramesh, KA 01 AB 1234. OTP {otp}.",
    "Reminder: your electricity bill of Rs {amt} is due on {date}. Pay on the official app or at the nearest office.",
    "{bank}: Your FD of Rs {amt} matures on {date}. Visit your branch or use NetBanking for renewal.",
    "Thank you for banking with {bank}. Your cheque book request has been processed and will be dispatched soon.",
    "Refund of Rs.{small} has been credited to your {bank} A/c XX{tail} on {date} from {merchant}. Avl bal: Rs.{bal}",
    "Your booking is confirmed. PNR 4521783345, Train 12658, {date}, Coach S4. Happy journey. -IRCTC",
    "{brand} sale starts tomorrow! Up to {pct}% off on electronics and fashion. Wishlist now.",
    "Your appointment with Dr Sharma is confirmed for {date} at 5:30 PM. Apollo Clinic.",
    "Hi! Your {brand} order of Rs {small} is confirmed and will be delivered in 30 minutes.",
    "Dear Student, the semester exam fee of Rs {amt} is due on {date}. Pay at the college portal.",
    "Money Transfer:Rs {small} from {bank} A/c **{tail} on {date} to {person} UPI: {ref} Not you? Call 18002586161",
    "Your a/c XX{tail} has been credited with interest of Rs {small} on {date}. Avl Bal Rs {bal} -{bank}",
    "{bank}: Never share your OTP, CVV or PIN with anyone. Bank staff will never ask for them.",
    "Your monthly data pack expires on {date}. Recharge on the {brand} app to continue enjoying services.",
    "Sent Rs.{small} from {bank} AC X{tail} to merchant@paytm on {date}.UPI Ref {ref}. Not you, https://kotak.com/KBANKT/Fraud",
]
LEGIT_HELD_OUT = [
    "INR {small} spent on {bank} Card XX{tail} on {date} at {merchant}. Avl Lmt: INR {bal}. To dispute call 18002662",
    "Your SB A/c **{tail} Debited for Rs:{small} on {date} by Mob Bk ref no {ref} Avl Bal Rs:{bal} -Canara Bank",
    "Use {otp} as your verification code for {brand}. This code expires in 10 minutes. Do not share it.",
    "{brand} weekend deal: extra {pct}% off with code {code}. Order on the app. T&C apply.",
    "Dear Customer, Acct XX{tail} is credited with Rs {amt} on {date} from ACME TECH PVT LTD. UPI:{ref}-{bank}.",
    "Your {brand} postpaid bill of Rs {amt} is generated. Due date {date}. Pay on the official app.",
    "Hi, your package from {brand} is out for delivery today. Our agent will call before arriving.",
    "Dear Customer, Rs.{small} has been debited from account {tail} to VPA store@ybl {merchant} on {date}. Your UPI transaction reference number is {ref}. -Axis",
    "Standing instruction for Rs {amt} towards your mutual fund SIP was executed successfully on {date}.",
    "{bank} wishes you a happy Diwali. Stay alert: we never ask for PIN or OTP on call.",
    "Your train 12658 is running late by 20 minutes. Expected arrival 18:45. -IRCTC",
    "Gym membership renewed. Next billing date {date}. Thank you for choosing Cult Fit.",
]


def build(seed: int, scam_templates: list[str], legit_templates: list[str], per_template: int) -> tuple[list[str], list[int]]:
    rng = random.Random(seed)
    texts: list[str] = []
    labels: list[int] = []
    for template in scam_templates:
        for _ in range(per_template):
            texts.append(_fill(rng, template))
            labels.append(1)
    for template in legit_templates:
        for _ in range(per_template):
            texts.append(_fill(rng, template))
            labels.append(0)
    order = list(range(len(texts)))
    rng.shuffle(order)
    return [texts[i] for i in order], [labels[i] for i in order]


def training_set() -> tuple[list[str], list[int]]:
    return build(21, SCAM_TRAIN, LEGIT_TRAIN, per_template=30)


def held_out_set() -> tuple[list[str], list[int]]:
    return build(22, SCAM_HELD_OUT, LEGIT_HELD_OUT, per_template=15)
