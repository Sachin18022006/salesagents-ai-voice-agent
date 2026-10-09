"""Normalizers and parsers for Indian financial formats, tenures, and checklist criteria."""

import re
from typing import Optional, Tuple
from src.models import PropertyType, OwnershipStatus, DocumentStatus, Occupation, IncomeMode


WORD_TO_NUMBER = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "fifteen": 15, "twenty": 20, "twenty-five": 25, "thirty": 30,
    "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "seventy-five": 75, "eighty": 80, "ninety": 90, "hundred": 100,
    # Hindi romanized numbers
    "ek": 1, "do": 2, "teen": 3, "char": 4, "paanch": 5,
    "chhe": 6, "saat": 7, "aath": 8, "nau": 9, "dus": 10,
    "pandrah": 15, "bees": 20, "pachees": 25, "tees": 30,
    "chalis": 40, "pachas": 50, "saath": 60, "sattar": 70,
    "pachattar": 75, "assi": 80, "nabbe": 90, "sau": 100,
}


def parse_inr_amount(text: str) -> Optional[int]:
    """Parse Indian Rupee amounts from text representations."""
    if not text:
        return None
    cleaned = text.lower().strip()
    cleaned = cleaned.replace("₹", "").replace("rs.", "").replace("rs", "").replace("inr", "").strip()

    # Match numeric crore: e.g. "1.5 crore", "1 crore", "2 cr"
    cr_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:crore|crores|cr|करोड़)", cleaned)
    if cr_match:
        val = float(cr_match.group(1))
        return int(round(val * 10_000_000))

    # Match numeric lakh: e.g. "75 lakhs", "75 lakh", "75 lac", "75 lacs", "75l", "75 लाख"
    lakh_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:lakhs?|lacs?|l|लाख)", cleaned)
    if lakh_match:
        val = float(lakh_match.group(1))
        return int(round(val * 100_000))

    # Match words + crore: e.g. "one crore", "two crores"
    word_cr_match = re.search(r"([a-z\-]+)\s*(?:crore|crores|cr)", cleaned)
    if word_cr_match:
        word = word_cr_match.group(1)
        if word in WORD_TO_NUMBER:
            return WORD_TO_NUMBER[word] * 10_000_000

    # Match words + lakh: e.g. "seventy-five lakhs", "thirty lakh", "tees lakh"
    word_lakh_match = re.search(r"([a-z\-]+)\s*(?:lakhs?|lacs?)", cleaned)
    if word_lakh_match:
        word = word_lakh_match.group(1)
        if word in WORD_TO_NUMBER:
            return WORD_TO_NUMBER[word] * 100_000

    # Match exact numbers with commas or plain digits (e.g., "75,00,000", "75,00,001", or "7500000")
    num_match = re.search(r"(\d[\d,]+)", cleaned)
    if num_match:
        digits_only = num_match.group(1).replace(",", "")
        try:
            return int(digits_only)
        except ValueError:
            return None

    return None


def parse_tenure_years(text: str) -> Optional[int]:
    """Parse repayment tenure in years."""
    if not text:
        return None
    cleaned = text.lower().strip()

    month_match = re.search(r"(\d+)\s*(?:months?|mahine|maheene)", cleaned)
    if month_match:
        months = int(month_match.group(1))
        return int(round(months / 12))

    year_match = re.search(r"(\d+)\s*(?:years?|yrs?|yr|saal|sal)?", cleaned)
    if year_match:
        return int(year_match.group(1))

    for word, num in WORD_TO_NUMBER.items():
        if word in cleaned:
            return num

    return None


def _has_positive_mention(text: str, keywords: list) -> bool:
    """Check if any keyword is present and NOT negated by 'not', 'no', 'nahi', etc."""
    for kw in keywords:
        match = re.search(rf"\b{re.escape(kw)}\b", text)
        if match:
            # Check preceding 20 chars for negation
            preceding = text[max(0, match.start() - 20):match.start()]
            if re.search(r"\b(?:not|no|nahi|instead of)\s+(?:a\s*)?$", preceding.strip()):
                continue
            return True
    return False


def parse_property_type(text: str) -> Tuple[PropertyType, bool]:
    """Parse property type. Returns (PropertyType, is_ambiguous)."""
    if not text:
        return PropertyType.UNKNOWN, False
    cleaned = text.lower()

    # Check agricultural first (immediate disqualifier)
    agri_keywords = ["agricultural", "farmland", "farm land", "farm", "kheti", "krishi", "agriculture", "field", "orchard"]
    if _has_positive_mention(cleaned, agri_keywords):
        return PropertyType.AGRICULTURAL, False

    res_keywords = ["residential", "house", "flat", "flats", "apartment", "makaan", "ghar", "villa", "home", "bungalow"]
    com_keywords = ["commercial", "shop", "office", "dukaan", "showroom", "store", "business space"]
    ind_keywords = ["industrial", "factory", "karkhana", "plant", "manufacturing unit", "warehouse", "godown"]

    is_res = _has_positive_mention(cleaned, res_keywords)
    is_com = _has_positive_mention(cleaned, com_keywords)
    is_ind = _has_positive_mention(cleaned, ind_keywords)

    count = sum([is_res, is_com, is_ind])
    if count > 1:
        return PropertyType.UNKNOWN, True

    if is_res:
        return PropertyType.RESIDENTIAL, False
    if is_com:
        return PropertyType.COMMERCIAL, False
    if is_ind:
        return PropertyType.INDUSTRIAL, False

    return PropertyType.UNKNOWN, False


def parse_ownership_status(text: str) -> Tuple[OwnershipStatus, bool]:
    """Parse ownership status: Sole or Joint."""
    if not text:
        return OwnershipStatus.UNKNOWN, False
    cleaned = text.lower()

    joint_keywords = ["joint", "jointly", "wife", "husband", "father", "mother", "brother", "partner", "co-owner", "co-owned", "together", "family", "saath"]
    sole_keywords = ["sole", "single", "only me", "my own", "mine", "alone", "individual", "akela", "sirf mera", "myself", "purely mine"]

    is_joint = any(k in cleaned for k in joint_keywords)
    is_sole = any(k in cleaned for k in sole_keywords)

    if is_joint and not is_sole:
        return OwnershipStatus.JOINT, False
    if is_sole and not is_joint:
        return OwnershipStatus.SOLE, False
    if is_joint and is_sole:
        return OwnershipStatus.UNKNOWN, True

    return OwnershipStatus.UNKNOWN, False


def parse_original_documents(text: str, is_target_field: bool = False) -> Tuple[DocumentStatus, bool]:
    """Parse original document availability."""
    if not text:
        return DocumentStatus.UNKNOWN, False
    cleaned = text.lower()

    doc_keywords = [
        "document", "documents", "papers", "paper", "originals", "original",
        "title deed", "registry", "kagaz", "patta", "photocopy", "photocopies", "xerox", "soft copy"
    ]
    has_doc_mention = any(k in cleaned for k in doc_keywords)

    if not is_target_field and not has_doc_mention:
        return DocumentStatus.UNKNOWN, False

    # Check for soft-copies / photocopies / xerox / future promise -> AMBIGUOUS
    ambiguous_keywords = ["photocopy", "photocopies", "xerox", "scanned", "soft copy", "pdf", "will get later", "apply karunga", "not sure", "might have", "duplicate", "certified copy"]
    if any(k in cleaned for k in ambiguous_keywords):
        return DocumentStatus.AMBIGUOUS, True

    # Check for UNAVAILABLE
    unavailable_keywords = [
        "not available", "don't have", "do not have", "lost", "missing",
        "nahi hai", "bank me hai", "mortgaged with other bank", "unavailable",
        "cannot give", "don't hold", "with someone else"
    ]
    if any(k in cleaned for k in unavailable_keywords):
        return DocumentStatus.UNAVAILABLE, False

    if is_target_field and re.search(r"\b(?:no|nope|nah|nahi)\b", cleaned):
        return DocumentStatus.UNAVAILABLE, False

    # Check AVAILABLE
    available_keywords = [
        "available", "i have them", "ready", "with me", "original documents are there",
        "haan hai", "originals available", "ghar pe hai", "all original papers", "clear title"
    ]
    if any(k in cleaned for k in available_keywords):
        return DocumentStatus.AVAILABLE, False

    if is_target_field and re.search(r"\b(?:yes|yeah|yep|sure|haan|ha|ji)\b", cleaned):
        return DocumentStatus.AVAILABLE, False

    return DocumentStatus.UNKNOWN, False


def parse_occupation_and_income_mode(text: str) -> Tuple[Occupation, IncomeMode, bool]:
    """Parse occupation (Salaried/Self-Employed) and income receipt mode (Bank/Cash)."""
    if not text:
        return Occupation.UNKNOWN, IncomeMode.UNKNOWN, False
    cleaned = text.lower()

    # Occupation detection
    occ = Occupation.UNKNOWN
    if any(k in cleaned for k in ["salaried", "salary", "job", "employee", "service", "working in", "mnc", "naukri", "private sector", "govt"]):
        occ = Occupation.SALARIED
    elif any(k in cleaned for k in ["self employed", "self-employed", "business", "businessman", "shop", "shopkeeper", "trader", "freelance", "vyapar", "consultant", "proprietor", "firm"]):
        occ = Occupation.SELF_EMPLOYED

    # Income mode detection
    inc_mode = IncomeMode.UNKNOWN
    is_ambiguous = False

    has_cash = any(k in cleaned for k in ["cash", "rokad", "nagad", "in hand", "cash in hand"])
    has_bank = any(k in cleaned for k in ["bank", "account", "transfer", "neft", "rtgs", "online", "cheque", "direct deposit", "salary account"])

    if has_cash and has_bank:
        inc_mode = IncomeMode.MIXED_AMBIGUOUS
        is_ambiguous = True
    elif has_cash and not has_bank:
        inc_mode = IncomeMode.CASH
    elif has_bank and not has_cash:
        inc_mode = IncomeMode.BANK

    return occ, inc_mode, is_ambiguous
