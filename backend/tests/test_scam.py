import pytest

from app.services import scam_detector
from app.services.scam_detector import score_message

SCAMS = [
    "Dear Customer, your HDFC Bank account will be blocked today. Update your KYC immediately at hdfc-kyc-update.in/verify",
    "You received Rs 4,999 from PRIYA S. Enter your UPI PIN to receive the money in your account. bit.ly/Rcv4999",
    "Your SBI account is temporarily locked. Install QuickSupport and share the code with our officer 9731000456",
    "Dear consumer, your electricity power will be disconnected tonight at 9.30 pm. Call electricity officer 9123456780",
    "Congratulations! You have won Rs 25,00,000 in KBC lucky draw. To claim call 8800554321 or WhatsApp now",
]
SAFE = [
    "Sent Rs.250.00 From HDFC Bank A/C *1234 To SWIGGY On 03/10/26 Ref 427612345678 Not You? Call 18002586161",
    "123456 is your OTP for txn of INR 500.00 at AMAZON. Do not share it with anyone. -ICICI Bank",
    "HDFC Bank: Never share your OTP, CVV or PIN with anyone. Bank staff will never ask for them.",
    "Your booking is confirmed. PNR 4521783345, Train 12658, Coach S4. Happy journey. -IRCTC",
    "Sent Rs.80.00 from Kotak Bank AC X1234 to merchant@paytm on 03-10-26.UPI Ref 427612345678. Not you, https://kotak.com/KBANKT/Fraud",
]


@pytest.mark.parametrize("text", SCAMS)
def test_scams_flagged_dangerous(text):
    v = score_message(text)
    assert v.level == "dangerous", v.reasons
    assert v.reasons


@pytest.mark.parametrize("text", SAFE)
def test_genuine_messages_safe(text):
    assert score_message(text).level == "safe"


def test_negated_secret_request_is_not_a_signal():
    codes = [s.code for s in scam_detector.rule_signals("Never share your OTP or PIN with anyone.")]
    assert "asks_secret" not in codes


def test_official_domain_not_flagged_as_lookalike():
    codes = [s.code for s in scam_detector.rule_signals("Visit https://www.hdfcbank.com/personal for details")]
    assert "lookalike_domain" not in codes


def test_model_alone_cannot_reach_dangerous():
    assert scam_detector.ML_WEIGHT < scam_detector.DANGEROUS_AT


def test_held_out_metrics_reported():
    scam_detector.text_model.get()
    m = scam_detector.text_model.metrics
    assert m["held_out_examples"] > 0 and 0 <= m["held_out_f1"] <= 1
