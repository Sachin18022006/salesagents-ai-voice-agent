"""Tests for information extraction and intent classification."""

import pytest
from src.extractor import (
    detect_loan_transfer_intent, detect_busy_intent,
    detect_refusal_intent, detect_identity_verification,
    extract_checklist_facts
)
from src.models import PropertyType, OwnershipStatus, DocumentStatus, Occupation, IncomeMode


def test_detect_loan_transfer_variations():
    assert detect_loan_transfer_intent("I already have an existing loan on this property")
    assert detect_loan_transfer_intent("Can you help me reduce my current EMI?")
    assert detect_loan_transfer_intent("I want to shift my loan from another bank")
    assert detect_loan_transfer_intent("I already took a loan against this flat")
    assert not detect_loan_transfer_intent("I want a new loan against my flat")


def test_detect_busy_variations():
    is_busy, pref = detect_busy_intent("I am driving right now, call back tomorrow at 5pm")
    assert is_busy
    assert "tomorrow at 5pm" in pref or "tomorrow" in pref

    is_busy2, _ = detect_busy_intent("I am in a meeting, call back later")
    assert is_busy2


def test_detect_refusal_intent():
    assert detect_refusal_intent("I am not interested, please do not call me")
    assert detect_refusal_intent("Stop calling, remove my number")
    assert not detect_refusal_intent("Sure, tell me about the offer")


def test_detect_identity_verification():
    confirmed, wrong = detect_identity_verification("Yes speaking", "Rajesh Sharma")
    assert confirmed
    assert not wrong

    confirmed, wrong = detect_identity_verification("Wrong number, this is not Rajesh", "Rajesh Sharma")
    assert not confirmed
    assert wrong


def test_multi_fact_extraction():
    # Example utterance from specification:
    # "I need 30 lakhs, my property is worth 80 lakhs, and I get my salary directly into my bank account"
    text = "I need 30 lakhs, my property is worth 80 lakhs, and I get my salary directly into my bank account"
    facts = extract_checklist_facts(text)

    assert "requested_loan_amount" in facts
    assert facts["requested_loan_amount"].parsed_value == 3000000
    assert facts["requested_loan_amount"].is_valid is True

    assert "property_market_value" in facts
    assert facts["property_market_value"].parsed_value == 8000000

    assert "occupation_and_income_mode" in facts
    occ_info = facts["occupation_and_income_mode"].parsed_value
    assert occ_info["occupation"] == Occupation.SALARIED
    assert occ_info["income_mode"] == IncomeMode.BANK
