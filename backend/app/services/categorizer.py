"""Assign a category to a transaction.

Order of precedence:
  1. a rule the user created by correcting a transaction
  2. a keyword dictionary of well-known Indian merchants
  3. a character n-gram classifier trained on merchant-name patterns, which
     handles names no dictionary lists ("SRI BALAJI MEDICALS", "Annapoorna Mess")
"""
from __future__ import annotations

import random
import re
import threading
from dataclasses import dataclass

from .sms_parser import counterparty_key

# (regex on the normalised counterparty, category). First match wins.
KEYWORD_RULES: list[tuple[str, str]] = [
    (r"swiggy instamart|instamart|blinkit|zepto|bigbasket|big basket|dmart|d mart|jiomart|reliance fresh|reliance smart|"
     r"more supermarket|spencers|nature s basket|licious|country delight|milkbasket|dunzo|grofers|ratnadeep|nilgiris", "groceries"),
    (r"swiggy|zomato|dominos|domino s|pizza hut|mcdonald|kfc|burger king|subway|starbucks|cafe coffee day|ccd|chaayos|"
     r"haldiram|faasos|eatfit|box8|behrouz|barbeque nation|wow momo|a2b|adyar ananda|saravana bhavan|sangeetha|"
     r"eatsure|magicpin|dineout|biryani|chai point|third wave|blue tokai|baskin|naturals ice", "food_dining"),
    (r"uber|ola\b|olacabs|rapido|namma yatri|blusmart|metro|dmrc|bmrc|cmrl|bmtc|best bus|ksrtc|tnstc|msrtc|"
     r"indian oil|iocl|hpcl|hp petrol|bharat petroleum|bpcl|shell|nayara|fastag|netc|parking|yulu|bounce|vogo|"
     r"petrol|fuel|filling station", "transport"),
    (r"irctc|makemytrip|mmt\b|goibibo|cleartrip|ixigo|easemytrip|yatra|redbus|abhibus|indigo|air india|vistara|"
     r"spicejet|akasa|oyo|airbnb|treebo|fabhotel|booking com|agoda", "travel"),
    (r"amazon|flipkart|myntra|ajio|meesho|nykaa|snapdeal|tata cliq|tatacliq|croma|reliance digital|vijay sales|"
     r"decathlon|ikea|pepperfry|lenskart|firstcry|shopsy|zara|h m\b|westside|pantaloons|max fashion|trends|lifestyle|"
     r"shoppers stop|bata|titan|tanishq|apple store|samsung|boat lifestyle|mi store|poorvika|sangeetha mobiles", "shopping"),
    (r"netflix|hotstar|jiohotstar|prime video|primevideo|spotify|gaana|jiosaavn|wynk|youtube|sonyliv|zee5|"
     r"bookmyshow|pvr|inox|cinepolis|playstation|steam|xbox|google play|apple com bill|itunes|audible|kindle|"
     r"dream11|mpl\b|district app|paytm insider", "entertainment"),
    (r"airtel|jio\b|reliance jio|vodafone|vi prepaid|\bvi\b|bsnl|act fibernet|actcorp|hathway|tata play|tatasky|dish tv|"
     r"sun direct|electricity|bescom|tneb|tangedco|msedcl|bses|tata power|adani electricity|torrent power|cesc|"
     r"kseb|apspdcl|tsspdcl|mahanagar gas|indraprastha gas|indane|hp gas|bharat gas|water board|bwssb|"
     r"recharge|broadband|billdesk|bbps|bharat billpay|postpaid|prepaid|dth", "bills"),
    (r"\brent\b|nobroker|no broker|nestaway|stanza living|zolo|colive|\bpg\b|hostel|housing society|maintenance|"
     r"landlord|cred rent|magicbricks|apartment", "rent"),
    (r"apollo|pharmeasy|netmeds|1mg|tata 1mg|medplus|practo|pharmacy|medical|medicals|hospital|clinic|diagnostic|"
     r"dr lal|thyrocare|healthians|dental|fortis|manipal|narayana health|max healthcare|aster|wellness forever", "health"),
    (r"cult fit|cultfit|curefit|gym|fitness|salon|urban company|urbanclap|spa\b|parlour|barber|naturals salon|"
     r"lakme|looks salon|yoga|anytime fitness|gold s gym", "personal"),
    (r"udemy|coursera|unacademy|byju|vedantu|physics wallah|pw live|upgrad|simplilearn|scaler|geeksforgeeks|"
     r"leetcode|coding ninjas|college|university|school|institute|academy|tuition|exam fee|nptel|"
     r"examination|stationery|xerox|book", "education"),
    (r"zerodha|groww|upstox|kite\b|coin by|kuvera|paytm money|et money|indmoney|angel one|5paisa|smallcase|"
     r"mutual fund|\bsip\b|nps\b|ppf\b|bse star|nse clearing|iccl|cams\b|kfintech|\bamc\b|nextbillion|"
     r"hdfc securities|icici direct|sbi mf|lic\b|insurance premium", "investments"),
    (r"atm cash|cash withdrawal", "cash"),
    (r"annual fee|late fee|finance charge|gst on|service charge|sms charge|amc charge|penalty|interest charged|"
     r"processing fee|convenience fee|forex markup", "fees"),
]
_COMPILED = [(re.compile(rf"(?:^|\b)(?:{pattern})", re.I), category) for pattern, category in KEYWORD_RULES]

_COMPANY = re.compile(
    r"\b(pvt|private|ltd|limited|llp|inc|corp|technologies|technology|solutions|systems|services|consult|"
    r"software|infotech|labs|enterprises|industries|global|india)\b",
    re.I,
)
_SALARY = re.compile(r"\b(salary|sal cr|payroll|stipend|wages|sal for)\b", re.I)
_REFUND = re.compile(r"\b(refund|refunded|reversal|reversed|cashback|chargeback)\b", re.I)
_INTEREST = re.compile(r"\b(interest|int\.?\s*pd|int\.?\s*cr|int paid|dividend)\b", re.I)

# ---------------------------------------------------------------------------
# Training data for the merchant-name classifier. Synthetic by construction:
# shop-type words carry the signal, the name tokens are filler.
# ---------------------------------------------------------------------------
TYPE_WORDS: dict[str, list[str]] = {
    "food_dining": ["restaurant", "cafe", "hotel", "biryani", "tiffin", "tiffin centre", "tea stall", "bakery", "sweets",
                    "juice", "mess", "dhaba", "foods", "kitchen", "pizza", "canteen", "fast food", "caterers",
                    "chats", "bhavan", "coffee", "tea", "snacks", "food court", "bar and restaurant", "dosa", "momos",
                    "rolls", "ice cream", "eatery", "darshini", "military hotel", "juice centre", "chinese"],
    "groceries": ["supermarket", "kirana", "provision store", "provisions", "general store", "vegetables", "fruits",
                  "dairy", "milk", "mart", "departmental store", "grocery", "super market", "fresh", "rice traders",
                  "oil mill", "flour mill", "veg shop", "fruit stall", "milk booth", "kirana store", "hypermarket",
                  "daily needs", "organic store", "chicken centre", "meat shop", "fish stall", "eggs"],
    "transport": ["petrol pump", "fuels", "filling station", "auto", "cabs", "taxi", "parking", "service station",
                  "fuel station", "petroleum", "travels cab", "bike rental", "tyres", "auto garage", "car wash",
                  "motors service", "two wheeler service", "puncture", "toll plaza", "bus pass", "auto consultants"],
    "health": ["medicals", "pharmacy", "clinic", "hospital", "diagnostics", "dental", "labs", "opticals", "medical store",
               "nursing home", "eye care", "scan centre", "chemist", "druggist", "physiotherapy", "ayurveda",
               "homeo clinic", "polyclinic", "medical hall", "path lab", "dental care", "skin clinic"],
    "shopping": ["textiles", "garments", "fashions", "electronics", "mobiles", "footwear", "jewellers", "silks",
                 "gifts", "furniture", "readymades", "boutique", "sarees", "collections", "fancy store", "emporium",
                 "watch house", "home appliances", "hardware", "paints", "toys", "bags", "opticians store", "mens wear",
                 "kids wear", "cosmetics", "shoe mart", "mobile accessories", "computers", "handlooms"],
    "education": ["school", "college", "university", "academy", "coaching", "institute", "book stall", "stationery",
                  "tuition", "xerox", "book house", "publications", "coaching centre", "study centre", "public school",
                  "engineering college", "library", "book depot", "training institute", "polytechnic", "classes"],
    "entertainment": ["cinemas", "theatre", "multiplex", "gaming", "bowling", "amusement", "game zone", "talkies",
                      "fun city", "water park", "escape room", "snooker", "arcade", "pub", "lounge", "karaoke",
                      "play arena", "turf", "movies", "events"],
    "bills": ["electricity board", "broadband", "recharge", "telecom", "gas agency", "water board", "cable", "dth",
              "internet services", "cable network", "fibernet", "mobile recharge", "gas service", "power corporation",
              "municipal corporation", "property tax", "water supply", "communications"],
    "travel": ["travels", "tours", "lodge", "residency", "resort", "airlines", "tours and travels", "holidays",
               "inn", "guest house", "homestay", "bus services", "tourism", "travel agency", "comforts", "suites"],
    "rent": ["pg", "hostel", "properties", "housing", "apartments", "mens hostel", "ladies hostel", "realty",
             "paying guest", "residences", "co living", "flat owners association", "rentals", "ladies pg", "boys pg"],
    "personal": ["salon", "beauty parlour", "gym", "fitness", "spa", "hair studio", "unisex salon", "fitness centre",
                 "yoga centre", "mens parlour", "beauty care", "tattoo", "laundry", "dry cleaners", "tailors",
                 "hair cut", "saloon", "grooming"],
}
NAME_TOKENS = [
    "sri", "sree", "shri", "lakshmi", "balaji", "ganesh", "murugan", "sai", "krishna", "annapoorna", "saravana",
    "new", "royal", "city", "national", "modern", "star", "golden", "green", "om", "jai", "maa", "durga",
    "venkateswara", "raj", "anand", "amman", "vinayaga", "kumar", "ram", "shiva", "meenakshi", "ayyappa", "guru",
    "nandhini", "kaveri", "ganga", "bharat", "hindustan", "classic", "sagar", "udupi", "malabar", "punjab",
    "delhi", "bombay", "kerala", "andhra", "madurai", "chettinad", "nellai", "kovai", "priya", "sangeetha",
    "vasantha", "thalappakatti", "aishwarya", "jaya", "vijaya", "mahalakshmi", "kamatchi", "abirami", "selvam",
    "pandian", "raja", "rani", "surya", "chandra", "sharma", "gupta", "agarwal", "jain", "patel", "shah",
]
HELD_OUT_NAME_TOKENS = [
    "ashoka", "tirumala", "supreme", "friends", "mahaveer", "kailash", "nataraja", "sowmya", "prakash", "victory",
    "lotus", "everest", "padma", "arun", "geetha", "ruchi", "vaibhav", "noor", "al ameen", "st marys",
]
FIRST_NAMES = [
    "ramesh", "suresh", "priya", "anita", "rahul", "rohit", "sneha", "pooja", "arjun", "karthik", "divya", "deepak",
    "vijay", "sanjay", "meena", "lakshmi", "arun", "vignesh", "harish", "nisha", "aditya", "neha", "amit", "kavya",
    "manoj", "swathi", "ganesh", "bala", "mohammed", "fathima", "joseph", "mary", "gurpreet", "simran", "ankit",
    "shreya", "varun", "tanvi", "naveen", "revathi", "ajay", "sunita", "yash", "isha", "pranav", "aishwarya",
]
LAST_NAMES = [
    "kumar", "sharma", "reddy", "iyer", "nair", "singh", "patel", "gupta", "das", "khan", "rao", "menon", "pillai",
    "verma", "joshi", "mehta", "shetty", "naidu", "chowdhury", "banerjee", "fernandes", "thomas", "kaur", "yadav",
    "mishra", "pandey", "raj", "krishnan", "subramanian", "murthy", "s", "k", "r", "m",
]
HELD_OUT_FIRST = ["tarun", "bhavana", "imran", "lavanya", "nikhil", "ritika", "sathish", "zoya"]
HELD_OUT_LAST = ["bhat", "saxena", "george", "ansari", "gowda", "kulkarni"]
UPI_HANDLES = ["okaxis", "okhdfcbank", "okicici", "oksbi", "ybl", "ibl", "axl", "paytm", "upi", "apl"]


def _shop_names(rng: random.Random, tokens: list[str], per_type: int) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for category, words in TYPE_WORDS.items():
        for word in words:
            for _ in range(per_type):
                a, b = rng.choice(tokens), rng.choice(tokens)
                style = rng.random()
                if style < 0.45:
                    name = f"{a} {word}"
                elif style < 0.75:
                    name = f"{a} {b} {word}"
                elif style < 0.9:
                    name = f"{word} {a}"
                else:
                    name = f"{a}{word.replace(' ', '')}@{rng.choice(UPI_HANDLES)}"
                rows.append((name, category))
    return rows


def _person_names(rng: random.Random, firsts: list[str], lasts: list[str], count: int) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for _ in range(count):
        first, last = rng.choice(firsts), rng.choice(lasts)
        style = rng.random()
        if style < 0.4:
            name = f"{first} {last}"
        elif style < 0.55:
            name = first
        elif style < 0.75:
            name = f"{first}{last}{rng.randint(1, 99)}@{rng.choice(UPI_HANDLES)}"
        elif style < 0.9:
            name = f"{first}.{last}@{rng.choice(UPI_HANDLES)}"
        else:
            name = f"{rng.randint(6000000000, 9999999999)}@{rng.choice(UPI_HANDLES)}"
        rows.append((name, "transfers"))
    return rows


def build_training_set(seed: int = 7) -> tuple[list[str], list[str]]:
    rng = random.Random(seed)
    rows = _shop_names(rng, NAME_TOKENS, per_type=6) + _person_names(rng, FIRST_NAMES, LAST_NAMES, 900)
    rng.shuffle(rows)
    return [counterparty_key(n) for n, _ in rows], [c for _, c in rows]


def build_held_out_set(seed: int = 11) -> tuple[list[str], list[str]]:
    """Names built from tokens the model never saw, to estimate how it generalises."""
    rng = random.Random(seed)
    rows = _shop_names(rng, HELD_OUT_NAME_TOKENS, per_type=2) + _person_names(rng, HELD_OUT_FIRST, HELD_OUT_LAST, 200)
    return [counterparty_key(n) for n, _ in rows], [c for _, c in rows]


@dataclass
class CategoryResult:
    category: str
    source: str  # user | rule | ml
    confidence: float


class _MerchantModel:
    """Lazy singleton. Training takes about a second on CPU."""

    def __init__(self) -> None:
        self._pipeline = None
        self._lock = threading.Lock()
        self.metrics: dict = {}

    def _train(self):
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import make_pipeline

        x_train, y_train = build_training_set()
        pipeline = make_pipeline(
            TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True, min_df=2),
            LogisticRegression(max_iter=400, C=8.0),
        )
        pipeline.fit(x_train, y_train)
        x_test, y_test = build_held_out_set()
        accuracy = float((pipeline.predict(x_test) == y_test).mean()) if x_test else 0.0
        self.metrics = {
            "model": "TF-IDF character n-grams (2-5) + logistic regression",
            "training_examples": len(x_train),
            "held_out_examples": len(x_test),
            "held_out_accuracy": round(accuracy, 4),
            "note": "Synthetic merchant names. Held-out names use tokens absent from training; "
                    "the shop-type words are shared, so this measures generalisation to new names, not new shop types.",
        }
        return pipeline

    def get(self):
        if self._pipeline is None:
            with self._lock:
                if self._pipeline is None:
                    self._pipeline = self._train()
        return self._pipeline

    def predict(self, key: str) -> tuple[str, float]:
        pipeline = self.get()
        probabilities = pipeline.predict_proba([key])[0]
        best = int(probabilities.argmax())
        return str(pipeline.classes_[best]), float(probabilities[best])


merchant_model = _MerchantModel()

ML_CONFIDENCE_FLOOR = 0.45


def keyword_category(key: str) -> str | None:
    for pattern, category in _COMPILED:
        if pattern.search(key):
            return category
    return None


def categorise(
    counterparty: str,
    direction: str,
    body: str = "",
    user_rules: dict[str, str] | None = None,
) -> CategoryResult:
    key = counterparty_key(counterparty)
    if user_rules and key in user_rules:
        return CategoryResult(user_rules[key], "user", 1.0)

    if direction == "credit":
        if _REFUND.search(body) or keyword_category(key) not in (None, "investments", "rent"):
            return CategoryResult("refund", "rule", 0.9)
        if _INTEREST.search(body) or _INTEREST.search(counterparty):
            return CategoryResult("interest", "rule", 0.9)
        if _SALARY.search(body) or _SALARY.search(counterparty) or _COMPANY.search(counterparty):
            return CategoryResult("salary", "rule", 0.8)
        if key == "unknown":
            return CategoryResult("other_income", "rule", 0.3)
        return CategoryResult("transfer_in", "rule", 0.6)

    by_keyword = keyword_category(key)
    if by_keyword:
        return CategoryResult(by_keyword, "rule", 0.95)
    if key == "unknown":
        return CategoryResult("other", "rule", 0.2)
    category, confidence = merchant_model.predict(key)
    if confidence < ML_CONFIDENCE_FLOOR:
        return CategoryResult("other", "ml", round(confidence, 3))
    return CategoryResult(category, "ml", round(confidence, 3))
