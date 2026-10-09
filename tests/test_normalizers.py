"""Unit tests for Indian financial normalizers and criterion parsers."""

import pytest
from src.normalizers import (
    parse_inr_amount, parse_tenure_years, parse_property_type,
    parse_ownership_status, parse_original_documents,
    parse_occupation_and_income_mode
)
from src.models import PropertyType, OwnershipStatus, DocumentStatus, Occupation, IncomeMode


class TestInrAmountNormalizer:
    @pytest.mark.parametrize("text,expected", [
        ("75,00,000", 7500000),
        ("7500000", 7500000),
        ("₹75,00,000", 7500000),
        ("75 lakhs", 7500000),
        ("75 lakh", 7500000),
        ("75 lac", 7500000),
        ("75 lacs", 7500000),
        ("75L", 7500000),
        ("30 lakhs", 3000000),
        ("50 lakhs", 5000000),
        ("1 crore", 10000000),
        ("1.5 crore", 15000000),
        ("2 cr", 20000000),
        ("thirty lakhs", 3000000),
        ("seventy-five lakhs", 7500000),
        ("one crore", 10000000),
        ("75 लाख", 7500000),
        ("Rs. 45,00,000", 4500000),
        ("", None),
        ("invalid text", None),
    ])
    def test_parse_inr_amount(self, text, expected):
        assert parse_inr_amount(text) == expected


class TestTenureNormalizer:
    @pytest.mark.parametrize("text,expected", [
        ("3 years", 3),
        ("5 yrs", 5),
        ("15 years", 15),
        ("10 yr", 10),
        ("5 saal", 5),
        ("five years", 5),
        ("ten years", 10),
        ("fifteen", 15),
        ("60 months", 5),
        ("36 months", 3),
        ("180 months", 15),
        ("2", 2),
        ("16", 16),
        ("", None),
    ])
    def test_parse_tenure_years(self, text, expected):
        assert parse_tenure_years(text) == expected


class TestPropertyTypeNormalizer:
    def test_residential(self):
        pt, amb = parse_property_type("I have a 3BHK flat in Pune")
        assert pt == PropertyType.RESIDENTIAL
        assert not amb

    def test_commercial(self):
        pt, amb = parse_property_type("It is a commercial office space")
        assert pt == PropertyType.COMMERCIAL
        assert not amb

    def test_industrial(self):
        pt, amb = parse_property_type("We have a factory in MIDC")
        assert pt == PropertyType.INDUSTRIAL
        assert not amb

    def test_agricultural(self):
        pt, amb = parse_property_type("It is agricultural farmland")
        assert pt == PropertyType.AGRICULTURAL
        assert not amb

    def test_multiple_ambiguous(self):
        pt, amb = parse_property_type("I have both a flat and a shop")
        assert amb


class TestOwnershipStatusNormalizer:
    def test_sole_ownership(self):
        own, amb = parse_ownership_status("I am the sole owner")
        assert own == OwnershipStatus.SOLE
        assert not amb

    def test_joint_ownership(self):
        own, amb = parse_ownership_status("It is jointly owned with my wife")
        assert own == OwnershipStatus.JOINT
        assert not amb


class TestOriginalDocumentsNormalizer:
    def test_originals_available(self):
        doc, amb = parse_original_documents("Yes, all original papers are with me")
        assert doc == DocumentStatus.AVAILABLE
        assert not amb

    def test_originals_unavailable(self):
        doc, amb = parse_original_documents("No, the original papers are missing")
        assert doc == DocumentStatus.UNAVAILABLE
        assert not amb

    def test_photocopies_ambiguous(self):
        doc, amb = parse_original_documents("I only have photocopies and xerox right now")
        assert amb


class TestOccupationAndIncomeModeNormalizer:
    def test_salaried_bank(self):
        occ, inc, amb = parse_occupation_and_income_mode("I am salaried and receive salary in bank account")
        assert occ == Occupation.SALARIED
        assert inc == IncomeMode.BANK
        assert not amb

    def test_self_employed_bank(self):
        occ, inc, amb = parse_occupation_and_income_mode("I run my own business and take money through bank transfer")
        assert occ == Occupation.SELF_EMPLOYED
        assert inc == IncomeMode.BANK
        assert not amb

    def test_cash_income(self):
        occ, inc, amb = parse_occupation_and_income_mode("I have a shop and get all cash in hand")
        assert occ == Occupation.SELF_EMPLOYED
        assert inc == IncomeMode.CASH
        assert not amb

    def test_mixed_income_ambiguous(self):
        occ, inc, amb = parse_occupation_and_income_mode("I get partly cash and partly in bank")
        assert inc == IncomeMode.MIXED_AMBIGUOUS
        assert amb
