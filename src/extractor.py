"""Multi-field information extractor and conversational intent analyzer."""

import re
from typing import Dict, Any, Tuple, Optional
from src.models import (
    PropertyType, OwnershipStatus, DocumentStatus,
    Occupation, IncomeMode, FieldCapture
)
from src.normalizers import (
    parse_inr_amount, parse_tenure_years, parse_property_type,
    parse_ownership_status, parse_original_documents,
    parse_occupation_and_income_mode
)


def detect_loan_transfer_intent(text: str) -> bool:
    """Detect if customer is inquiring about transferring an existing loan, reducing EMI, or refinancing."""
    if not text:
        return False
    cleaned = text.lower()
    signals = [
        "existing loan",
        "already have a loan",
        "already took a loan",
        "loan chal raha hai",
        "already running",
        "shift my loan",
        "transfer my loan",
        "balance transfer",
        "refinance",
        "takeover",
        "top up on existing",
        "pichla loan transfer",
    ]
    if any(sig in cleaned for sig in signals):
        return True

    # Regex for EMI reduction: "reduce my current emi", "lower current emi", "cut emi"
    if re.search(r"(?:reduce|lower|cut|decrease)\s*(?:my|our|the)?\s*(?:current)?\s*emi", cleaned):
        return True

    return False


def detect_busy_intent(text: str) -> Tuple[bool, str]:
    """Detect if customer is busy, driving, or in a meeting and extract callback preference if provided."""
    if not text:
        return False, ""
    cleaned = text.lower()
    busy_signals = [
        "busy", "driving", "meeting", "can't talk", "cannot talk",
        "call back later", "call me later", "call after", "call tomorrow",
        "drive kar raha", "baad me call karo", "phir baat karte hai",
    ]
    is_busy = any(sig in cleaned for sig in busy_signals)
    callback_pref = ""
    if is_busy:
        # Extract callback time if present (e.g. "tomorrow at 5pm", "after 2 hours")
        time_match = re.search(r"(?:call|talk)\s*(?:me\s*)?(?:back\s*)?(?:later\s*)?(?:at|in|after|around)?\s*(tomorrow[0-9a-zA-Z\s:apm]*|[0-9a-zA-Z\s:apm]+)", cleaned)
        if time_match:
            candidate = time_match.group(1).strip()
            # Clean up trailing words
            callback_pref = candidate
        if not callback_pref and "tomorrow" in cleaned:
            callback_pref = "tomorrow"
    return is_busy, callback_pref


def detect_refusal_intent(text: str) -> bool:
    """Detect if customer refuses the offer or asks not to be contacted."""
    if not text:
        return False
    cleaned = text.lower()
    refusal_signals = [
        "not interested", "don't call me", "do not call", "stop calling",
        "remove my number", "nahi chahiye", "no loan", "interest nahi hai",
        "don't contact", "nahi lena", "never call", "please don't call"
    ]
    return any(sig in cleaned for sig in refusal_signals)


def detect_identity_verification(text: str, customer_name: str) -> Tuple[bool, bool]:
    """Detect whether identity is confirmed or if someone else picked up."""
    if not text:
        return False, False
    cleaned = text.lower()
    name_tokens = customer_name.lower().split()

    wrong_person_signals = [
        "wrong number", "wrong person", "not rajesh", "he is not available",
        "she is not available", "i am his", "i am her", "father speaking",
        "brother speaking", "wife speaking", "son speaking", "nahi hai",
        "galat number", "who are you looking for", "he stepped out"
    ]
    if any(sig in cleaned for sig in wrong_person_signals):
        return False, True

    confirmed_signals = [
        "yes", "speaking", "yes speaking", "this is", "myself", "haan",
        "haan bol raha hoon", "haan bol rahi hoon", "yes this is", "boliye"
    ]
    if any(sig in cleaned for sig in confirmed_signals) or any(tok in cleaned for tok in name_tokens):
        return True, False

    return False, False


def extract_amounts(cleaned: str, current_target_field: Optional[str], extracted: Dict[str, FieldCapture]):
    """Extract and disambiguate loan amount vs property market value."""
    text_lower = cleaned.lower()

    # Match clauses for loan amount vs property value
    loan_clauses = re.findall(r"(?:need|want|looking for|borrow|loan of|require)\s*(?:about|around|approx)?\s*(?:₹|rs\.?)?\s*([0-9a-zA-Z\s,]+?)(?=(?:and\s+my|and\s+property|and\s+the|property|worth|\.|$))", text_lower)
    property_clauses = re.findall(r"(?:property|house|flat|worth|value|market value|market rate|valuation|cost)\s*(?:is|of|about|around|approx)?\s*(?:₹|rs\.?)?\s*([0-9a-zA-Z\s,]+?)(?=(?:and\s+i|and\s+my|and\s+need|need|borrow|\.|$))", text_lower)

    if loan_clauses:
        amt = parse_inr_amount(loan_clauses[0])
        if amt:
            is_valid = (amt <= 75_00_000)
            extracted["requested_loan_amount"] = FieldCapture(
                raw_value=loan_clauses[0].strip(),
                parsed_value=amt,
                is_answered=True,
                is_valid=is_valid,
                needs_clarification=not is_valid,
                clarification_reason=f"Requested amount ₹{amt:,} exceeds the maximum ₹75,00,000 cap." if not is_valid else None
            )

    if property_clauses:
        val = parse_inr_amount(property_clauses[0])
        if val:
            extracted["property_market_value"] = FieldCapture(
                raw_value=property_clauses[0].strip(),
                parsed_value=val,
                is_answered=True,
                is_valid=True,
                needs_clarification=False
            )

    # If neither pattern matched but an amount exists, rely on current target field
    if "requested_loan_amount" not in extracted and "property_market_value" not in extracted:
        amt = parse_inr_amount(text_lower)
        if amt:
            if current_target_field == "requested_loan_amount":
                is_valid = (amt <= 75_00_000)
                extracted["requested_loan_amount"] = FieldCapture(
                    raw_value=cleaned,
                    parsed_value=amt,
                    is_answered=True,
                    is_valid=is_valid,
                    needs_clarification=not is_valid,
                    clarification_reason=f"Requested amount ₹{amt:,} exceeds ₹75,00,000 cap." if not is_valid else None
                )
            elif current_target_field == "property_market_value":
                extracted["property_market_value"] = FieldCapture(
                    raw_value=cleaned,
                    parsed_value=amt,
                    is_answered=True,
                    is_valid=True,
                    needs_clarification=False
                )


def extract_checklist_facts(utterance: str, current_target_field: Optional[str] = None) -> Dict[str, FieldCapture]:
    """Extract any volunteered or explicitly answered checklist facts from customer utterance."""
    extracted: Dict[str, FieldCapture] = {}
    cleaned = utterance.strip()
    if not cleaned:
        return extracted

    # 1. Property Type
    pt, pt_amb = parse_property_type(cleaned)
    if pt != PropertyType.UNKNOWN:
        extracted["property_type"] = FieldCapture(
            raw_value=cleaned,
            parsed_value=pt,
            is_answered=True,
            is_valid=(pt != PropertyType.AGRICULTURAL),
            needs_clarification=pt_amb,
            clarification_reason="Customer mentioned multiple properties. Clarify which property is being offered as collateral." if pt_amb else None
        )
    elif pt_amb:
        extracted["property_type"] = FieldCapture(
            raw_value=cleaned,
            parsed_value=None,
            is_answered=False,
            is_valid=False,
            needs_clarification=True,
            clarification_reason="Customer mentioned multiple properties. Please clarify which specific property is collateral."
        )

    # 2. Ownership Status
    own, own_amb = parse_ownership_status(cleaned)
    if own != OwnershipStatus.UNKNOWN:
        extracted["ownership_status"] = FieldCapture(
            raw_value=cleaned,
            parsed_value=own,
            is_answered=True,
            is_valid=True,
            needs_clarification=own_amb,
            clarification_reason="Ownership details are ambiguous." if own_amb else None
        )

    # 3. Original Documents
    is_doc_target = (current_target_field == "original_documents_available")
    docs, docs_amb = parse_original_documents(cleaned, is_target_field=is_doc_target)
    if docs != DocumentStatus.UNKNOWN:
        extracted["original_documents_available"] = FieldCapture(
            raw_value=cleaned,
            parsed_value=docs,
            is_answered=(not docs_amb),
            is_valid=(docs == DocumentStatus.AVAILABLE),
            needs_clarification=docs_amb,
            clarification_reason="Customer mentioned photocopies, soft-copies, or obtaining them later. Must clarify if original physical documents are available." if docs_amb else None
        )

    # 4. Requested Loan Amount & Market Value
    extract_amounts(cleaned, current_target_field, extracted)

    # 5. Occupation & Income Mode
    occ, inc_mode, inc_amb = parse_occupation_and_income_mode(cleaned)
    if occ != Occupation.UNKNOWN or inc_mode != IncomeMode.UNKNOWN or inc_amb:
        # If income mode is CASH, it's immediately answered and INVALID (triggers immediate disqualification)
        is_answered = (inc_mode == IncomeMode.CASH) or (occ != Occupation.UNKNOWN and inc_mode != IncomeMode.UNKNOWN and not inc_amb)
        is_valid = (inc_mode == IncomeMode.BANK and not inc_amb)
        extracted["occupation_and_income_mode"] = FieldCapture(
            raw_value=cleaned,
            parsed_value={"occupation": occ, "income_mode": inc_mode},
            is_answered=is_answered,
            is_valid=is_valid,
            needs_clarification=inc_amb or (occ != Occupation.UNKNOWN and inc_mode == IncomeMode.UNKNOWN),
            clarification_reason="Income mode is cash or partly cash/ambiguous. Clarify how income is received." if (inc_amb or (occ != Occupation.UNKNOWN and inc_mode == IncomeMode.UNKNOWN)) else None
        )

    # 6. Requested Tenure
    if current_target_field == "requested_tenure_years" or any(k in cleaned.lower() for k in ["year", "yr", "tenure", "saal", "month"]):
        tenure = parse_tenure_years(cleaned)
        if tenure is not None:
            is_valid = (3 <= tenure <= 15)
            extracted["requested_tenure_years"] = FieldCapture(
                raw_value=cleaned,
                parsed_value=tenure,
                is_answered=True,
                is_valid=is_valid,
                needs_clarification=False,
                clarification_reason=f"Requested tenure {tenure} years is out of the 3 to 15 years allowable range." if not is_valid else None
            )

    return extracted
