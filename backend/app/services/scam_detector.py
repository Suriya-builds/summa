"""Scam and phishing risk scoring for SMS text.

Two parts are combined:
  * signal rules - each one fires for a concrete, explainable reason
  * a text classifier (TF-IDF + logistic regression) trained on a synthetic corpus

The rules carry the verdict; the classifier can raise a score but can never, by
itself, push a message to "dangerous". That keeps a model mistake from hiding a
real bank alert.
"""
from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field

DANGEROUS_AT = 0.70
SUSPICIOUS_AT = 0.40
ML_WEIGHT = 0.65  # the most the classifier alone can contribute; below DANGEROUS_AT on purpose

OFFICIAL_DOMAINS = {
    "hdfcbank.com", "hdfcbank.net", "sbi.co.in", "onlinesbi.sbi", "onlinesbi.com", "sbicard.com", "icicibank.com",
    "axisbank.com", "kotak.com", "yesbank.in", "idfcfirstbank.com", "pnbindia.in", "bankofbaroda.in",
    "canarabank.com", "unionbankofindia.co.in", "indusind.com", "federalbank.co.in", "paytm.com", "phonepe.com",
    "google.com", "amazon.in", "amazon.com", "flipkart.com", "npci.org.in", "upi.org.in", "rbi.org.in",
    "irctc.co.in", "airtel.in", "jio.com", "myvi.in", "swiggy.com", "zomato.com", "myntra.com", "uber.com",
    "olacabs.com", "netflix.com", "indiapost.gov.in", "incometax.gov.in", "uidai.gov.in", "bluedart.com",
    "delhivery.com", "zerodha.com", "groww.in", "cred.club", "licindia.in",
}
OFFICIAL_SUFFIXES = (".gov.in", ".nic.in", ".bank.in", ".sbi")
SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "cutt.ly", "rb.gy", "is.gd", "ow.ly", "shorturl.at", "tiny.cc",
    "rebrand.ly", "lnkd.in", "t.ly", "s.id", "wa.me", "t.me", "tiny.one", "shorter.me",
}
BRAND_TOKENS = [
    "hdfc", "sbi", "icici", "axis", "kotak", "pnb", "canara", "idfc", "yesbank", "indusind", "paytm", "phonepe",
    "gpay", "googlepay", "npci", "upi", "kyc", "bank", "rbi", "uidai", "aadhaar", "aadhar", "pan", "incometax",
    "amazon", "flipkart", "jio", "airtel", "netflix", "irctc", "fastag", "indiapost", "bluedart", "delhivery",
    "fedex", "dhl", "sim", "electricity", "netbanking", "reward", "refund", "secure", "verify", "login", "update",
]
_TLDS = (
    "com|in|co|net|org|xyz|top|info|online|site|link|ly|me|app|live|club|shop|cc|io|gl|page|dev|biz|icu|"
    "buzz|click|work|vip|store|tech|fun|gd|at|id|one|sbi|bank"
)
URL_RE = re.compile(
    rf"(?:https?://|www\.)[^\s<>()]+"
    rf"|(?<![@\w.])(?:[a-z0-9][a-z0-9-]*\.)+(?:{_TLDS})(?:\.[a-z]{{2,3}})?(?![a-z0-9])(?:/[^\s<>()]*)?"
    # any other "name.tld/path" is a link too, whatever the top-level domain
    r"|(?<![@\w.])(?:[a-z0-9][a-z0-9-]*\.)+[a-z]{2,8}/[^\s<>()]+",
    re.I,
)
MOBILE = r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{9}(?!\d)"
_NEGATION = re.compile(r"(?:do not|don'?t|dont|never|not|no one should|nobody should|will never)\W+(?:\w+\W+){0,3}$", re.I)
_LEET = str.maketrans({"0": "o", "1": "l", "3": "e", "4": "a", "5": "s", "@": "a", "$": "s", "!": "i"})
_LEET_WORDS = {
    "account", "accolnt", "blocked", "bank", "verify", "update", "click", "link", "reward", "customer", "your",
    "suspended", "password", "login", "kyc", "wallet", "refund", "claim",
}


@dataclass
class Signal:
    code: str
    weight: float
    reason: str


@dataclass
class ScamVerdict:
    score: float
    level: str  # safe | suspicious | dangerous
    reasons: list[dict] = field(default_factory=list)
    rule_score: float = 0.0
    ml_probability: float | None = None
    advice: str = ""

    def as_dict(self) -> dict:
        return {
            "score": round(self.score, 3),
            "level": self.level,
            "reasons": self.reasons,
            "rule_score": round(self.rule_score, 3),
            "ml_probability": None if self.ml_probability is None else round(self.ml_probability, 3),
            "advice": self.advice,
        }


def _domain(url: str) -> str:
    host = re.sub(r"^(?:https?://)?(?:www\.)?", "", url.strip().lower())
    host = re.split(r"[/?#:]", host, maxsplit=1)[0]
    return host.strip(".")


def _is_official(domain: str) -> bool:
    if domain in OFFICIAL_DOMAINS or domain.endswith(OFFICIAL_SUFFIXES):
        return True
    return any(domain.endswith("." + official) for official in OFFICIAL_DOMAINS)


def extract_links(text: str) -> list[str]:
    links: list[str] = []
    for m in URL_RE.finditer(text):
        url = m.group(0).rstrip(".,;:!?)")
        # "Rs.250.00" and similar never have a letters-only top-level part; skip pure numbers.
        if re.fullmatch(r"[\d.,]+", url):
            continue
        links.append(url)
    return links


def _not_negated(text: str, match: re.Match) -> bool:
    return not _NEGATION.search(text[max(0, match.start() - 40) : match.start()])


def _first(pattern: str, text: str, check_negation: bool = False) -> re.Match | None:
    for m in re.finditer(pattern, text, re.I | re.S):
        if not check_negation or _not_negated(text, m):
            return m
    return None


def rule_signals(body: str, sender: str = "") -> list[Signal]:
    text = re.sub(r"\s+", " ", body.strip())
    lower = text.lower()
    signals: list[Signal] = []

    def add(code: str, weight: float, reason: str) -> None:
        if all(s.code != code for s in signals):
            signals.append(Signal(code, weight, reason))

    # --- links -------------------------------------------------------------
    for url in extract_links(text):
        domain = _domain(url)
        if not domain or _is_official(domain):
            continue
        if url.lower().split("?")[0].endswith(".apk"):
            add("apk_link", 0.80, "Asks you to install an app file (.apk) from outside the Play Store.")
        if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", domain):
            add("ip_link", 0.60, f"Link points to a raw IP address ({domain}) instead of a named website.")
        elif domain in SHORTENERS:
            add("shortened_link", 0.35, f"Uses a shortened link ({domain}) that hides where it really goes.")
        else:
            flat = re.sub(r"[^a-z0-9]", "", domain.rsplit(".", 1)[0])
            brand = next((b for b in BRAND_TOKENS if b in flat), None)
            if brand:
                add("lookalike_domain", 0.70,
                    f"The link '{domain}' uses the word '{brand}' but is not an official website.")
            else:
                add("unknown_link", 0.20, f"Contains a link to an unrecognised website ({domain}).")

    # --- requests for secrets ------------------------------------------------
    if _first(r"\b(share|enter|provide|send|tell|confirm|submit|give|type|forward)\b[^.!?]{0,45}"
              r"\b(otp|upi pin|m-?pin|pin|cvv|password|passcode|card (?:number|details)|net ?banking (?:id|password))\b",
              lower, check_negation=True):
        add("asks_secret", 0.75, "Asks for an OTP, PIN, CVV or password. A bank never asks for these.")
    if _first(r"\b(enter|use|type|put|approve)\b[^.!?]{0,40}\bpin\b[^.!?]{0,60}\b(receive|get|claim|accept|credit|cashback|refund)|"
              r"\b(receive|get|claim|accept)\b[^.!?]{0,70}\b(enter|type|approve|use)\b[^.!?]{0,30}\bpin\b|"
              r"\bpin\b[^.!?]{0,20}\bto (?:receive|get|claim|accept)", lower):
        add("pin_to_receive", 0.85, "Says you must enter your UPI PIN to receive money. A PIN is only ever needed to send money.")

    # --- threats and pressure -------------------------------------------------
    if _first(r"\b(account|a/c|acct|card|upi|wallet|sim|net ?banking|service|kyc|pan|fastag|connection|number)\b[^.!?]{0,45}"
              r"\b(?:will be|has been|have been|is|are|gets?|been|be|shall be|is temporarily|temporarily|is under)\s+"
              r"(?:\w+\s+)?(blocked|suspended|deactivated|frozen|closed|restricted|terminated|locked|expired|on hold|"
              r"disconnected|stopped|b1ocked)", lower):
        add("account_threat", 0.50, "Threatens that an account, card or service will be blocked or suspended.")
    if _first(r"\b(electricity|power|light|gas|water|bijli|supply)\b[^.!?]{0,70}\b(disconnect\w*|cut off|cut tonight|be cut)", lower):
        add("bill_threat", 0.70, "Threatens to disconnect electricity, gas or water unless you act now.")
    if _first(r"\bimmediately\b|\burgent\w*|\bwithin \d+ ?(?:hrs?|hours?|minutes|mins)\b|\btonight\b|\b(?:by|expires?) today\b|"
              r"\blast (?:chance|day|warning)\b|\bfinal (?:notice|reminder|warning)\b|\bact now\b|\basap\b|\bin \d+ ?(?:hrs?|hours?)\b",
              lower):
        add("urgency", 0.25, "Pushes you to act immediately, a common pressure tactic.")
    if _first(r"\be-?kyc\b|\bre-?kyc\b|\bkyc\b|\bpan\b[^.!?]{0,25}(?:updat|link|verif|not linked)|aadhaa?r[^.!?]{0,25}(?:updat|link|verif)", lower):
        add("kyc_update", 0.45, "Asks you to update KYC, PAN or Aadhaar details through a message.")

    # --- bait -----------------------------------------------------------------
    if _first(r"\b(?:you(?:'ve| have)?|u) (?:have )?won\b|\bwinner\b|\blottery\b|\blucky draw\b|\bkbc\b|\bjackpot\b|"
              r"congratulations[^.!?]{0,50}(?:won|selected|reward|gift|prize)|claim (?:your|ur) (?:reward|prize|gift)", lower):
        add("prize", 0.60, "Claims you won a prize, lottery or reward you never entered.")
    if _first(r"work from home|part[\s-]?time job|online job|data entry job|typing job|\b(?:earn|income|salary|make)\b[^.!?]{0,30}"
              r"(?:rs\.?|inr|₹)\s?[\d,]+[^.!?]{0,25}(?:daily|per day|/day|a day|weekly|per hour|per week|every day)|"
              r"like (?:youtube )?videos|review (?:hotels|products|restaurants)[^.!?]{0,20}earn|registration fee", lower):
        add("job_scam", 0.60, "Offers easy money for part-time or work-from-home tasks.")
    if _first(r"\b(?:instant|pre-?approved|personal)\b[^.!?]{0,20}\bloan\b[^.!?]{0,90}(?:no (?:documents?|cibil|paperwork|income)|"
              r"without (?:documents?|cibil|paperwork)|approved|disburs)|loan (?:is )?approved", lower):
        add("loan_scam", 0.45, "Promises an instant loan with no documents or credit check.")
    if _first(r"\b(?:guaranteed|assured|risk[\s-]?free|sure ?shot)\b[^.!?]{0,40}(?:returns?|profit|income)|double your money|"
              r"100% (?:profit|returns?)|\b\d{2,3}% (?:profit|returns?) (?:daily|weekly|every)|"
              r"(?:crypto|trading|stock tips?)[^.!?]{0,60}(?:profit|earn|double|join)|join (?:our )?(?:whatsapp|telegram) (?:group|channel)", lower):
        add("investment_scam", 0.60, "Promises guaranteed or unusually high investment returns.")
    if _first(r"\b(parcel|package|courier|shipment|consignment|order)\b[^.!?]{0,70}"
              r"(?:on hold|held|customs|address[^.!?]{0,15}(?:incomplete|incorrect|wrong|confirm)|re-?deliver\w*|"
              r"clearance|pay (?:rs|₹|inr))|"
              r"\bdeliver\w*\b[^.!?]{0,60}\b(?:confirm|update|verify)\b[^.!?]{0,15}\baddress|"
              r"\b(?:confirm|update|verify) (?:your )?address\b[^.!?]{0,40}\bpay\b", lower):
        add("parcel", 0.50, "Says a parcel is stuck and asks for a fee or address confirmation.")
    if _first(r"\b(refund|cashback|reward points?|tax refund)\b[^.!?]{0,70}\b(click|claim|link|verify|redeem|submit|expire)", lower):
        add("refund_bait", 0.45, "Dangles a refund, cashback or reward that you must claim through a link.")
    if _first(r"collect request|has requested (?:money|payment|rs|₹|inr)|requested (?:rs|₹|inr)|payment request", lower):
        add("collect_request", 0.50, "This is a request to pay. Approving it sends money out of your account.")
    if _first(r"will be (?:debited|deducted|charged).{0,120}?(?:click|cancel|stop|link|call)|"
              r"(?:debited|deducted)[^.!?]{0,60}not (?:done by )?you\??[^.!?]{0,30}(?:click|stop|https?://|www\.)", lower):
        add("fake_debit", 0.55, "Imitates a debit alert and tells you to click or call to cancel it.")

    # --- how they want to be contacted ----------------------------------------
    if _first(r"anydesk|teamviewer|quick ?support|rustdesk|airdroid|screen ?shar\w*|remote (?:access|app|control)", lower):
        add("remote_app", 0.85, "Asks you to install a screen-sharing or remote-control app.")
    if _first(rf"\b(call|contact|whatsapp|dial|reach|message|msg)\b[^0-9.!?]{{0,28}}{MOBILE}", lower):
        add("personal_number", 0.35, "Tells you to call or WhatsApp a personal mobile number, not an official helpline.")

    sender_digits = re.sub(r"\D", "", sender or "")
    if len(sender_digits) >= 10 and not re.search(r"[A-Za-z]", sender or ""):
        if re.search(r"\bbank\b|dear (?:customer|user|consumer|sir)|\bkyc\b|\ba/c\b|account|" + "|".join(BRAND_TOKENS[:12]), lower):
            add("sender_mismatch", 0.40,
                "Came from an ordinary mobile number while claiming to be a bank or company. "
                "Banks send from registered sender IDs.")

    # --- disguised spelling -----------------------------------------------------
    for token in re.findall(r"[A-Za-z0-9@$!]{4,}", text):
        if not re.search(r"[A-Za-z]", token) or not re.search(r"[0-9@$!]", token[1:-1] or ""):
            continue
        plain = token.lower().translate(_LEET)
        if plain != token.lower() and plain in _LEET_WORDS:
            add("obfuscation", 0.35, f"Uses disguised spelling ('{token}') to slip past filters.")
            break

    return signals


def _noisy_or(weights: list[float]) -> float:
    remaining = 1.0
    for w in weights:
        remaining *= 1.0 - w
    return 1.0 - remaining


class _TextModel:
    def __init__(self) -> None:
        self._pipeline = None
        self._lock = threading.Lock()
        self.metrics: dict = {}

    def _train(self):
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import precision_recall_fscore_support
        from sklearn.pipeline import make_pipeline, make_union

        from . import scam_corpus

        x_train, y_train = scam_corpus.training_set()
        pipeline = make_pipeline(
            make_union(
                TfidfVectorizer(analyzer="word", ngram_range=(1, 2), sublinear_tf=True, min_df=2,
                                token_pattern=r"(?u)\b[A-Za-z][A-Za-z']+\b"),
                TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True, min_df=3),
            ),
            LogisticRegression(max_iter=500, C=4.0),
        )
        pipeline.fit(x_train, y_train)
        x_test, y_test = scam_corpus.held_out_set()
        predictions = pipeline.predict(x_test)
        precision, recall, f1, _ = precision_recall_fscore_support(y_test, predictions, average="binary", zero_division=0)
        self.metrics = {
            "model": "TF-IDF (word 1-2 grams + character 3-5 grams) + logistic regression",
            "training_examples": len(x_train),
            "held_out_examples": len(x_test),
            "held_out_precision": round(float(precision), 4),
            "held_out_recall": round(float(recall), 4),
            "held_out_f1": round(float(f1), 4),
            "note": "Trained and tested on synthetic messages written for this project. The held-out set uses "
                    "templates never seen in training. These figures do not measure accuracy on real-world scams.",
        }
        return pipeline

    def get(self):
        if self._pipeline is None:
            with self._lock:
                if self._pipeline is None:
                    self._pipeline = self._train()
        return self._pipeline

    def probabilities(self, texts: list[str]) -> list[float]:
        if not texts:
            return []
        pipeline = self.get()
        index = list(pipeline.classes_).index(1)
        return [float(row[index]) for row in pipeline.predict_proba(texts)]

    def probability(self, text: str) -> float:
        return self.probabilities([text])[0]


text_model = _TextModel()

ADVICE = {
    "dangerous": "Do not click any link, call any number or share any code from this message. "
                 "If it mentions your bank, open the bank's own app or call the number printed on your card. "
                 "Report fraud at cybercrime.gov.in or call 1930.",
    "suspicious": "Treat this with caution. Check through the official app or website before acting, "
                  "and never share an OTP or PIN.",
    "safe": "Nothing in this message matches known scam patterns. Still, never share an OTP or PIN with anyone.",
}


MIN_MODEL_CHARS = 20


def score_message(body: str, sender: str = "", use_model: bool = True, ml_probability: float | None = None) -> ScamVerdict:
    """Score one message. Pass `ml_probability` when it was already computed in a batch."""
    signals = rule_signals(body, sender)
    rule_score = _noisy_or([s.weight for s in signals])
    reasons = [{"code": s.code, "weight": s.weight, "text": s.reason} for s in sorted(signals, key=lambda s: -s.weight)]

    ml_component = 0.0
    if ml_probability is None and use_model and len(body.strip()) >= MIN_MODEL_CHARS:
        ml_probability = text_model.probability(body)
    if ml_probability is not None:
        ml_component = ML_WEIGHT * max(0.0, (ml_probability - 0.5) / 0.5)
        if ml_probability >= 0.8:
            reasons.append({
                "code": "ml_text",
                "weight": round(ml_component, 3),
                "text": f"The wording resembles scam messages the text model was trained on "
                        f"(model score {ml_probability:.0%}).",
            })

    score = 1.0 - (1.0 - rule_score) * (1.0 - ml_component)
    level = "dangerous" if score >= DANGEROUS_AT else "suspicious" if score >= SUSPICIOUS_AT else "safe"
    return ScamVerdict(score=score, level=level, reasons=reasons, rule_score=rule_score,
                       ml_probability=ml_probability, advice=ADVICE[level])


def score_messages(items: list[tuple[str, str]]) -> list[ScamVerdict]:
    """Score many (body, sender) pairs with one model call."""
    eligible = [i for i, (body, _) in enumerate(items) if len(body.strip()) >= MIN_MODEL_CHARS]
    probabilities = dict(zip(eligible, text_model.probabilities([items[i][0] for i in eligible])))
    return [
        score_message(body, sender, use_model=False, ml_probability=probabilities.get(i))
        for i, (body, sender) in enumerate(items)
    ]
