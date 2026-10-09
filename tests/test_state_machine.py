"""Comprehensive automated tests covering all positive, disqualification, routing, and boundary scenarios."""

import pytest
from src.state_machine import LAPVoiceStateMachine
from src.models import (
    Stage, CallOutcome, PropertyType, OwnershipStatus,
    DocumentStatus, Occupation, IncomeMode, RuntimeVariables, ConversationSession
)


def create_sm():
    vars = RuntimeVariables(
        company_name="Home Credit",
        customer_name="Rajesh Sharma",
        agent_name="Ananya",
        agent_gender="Female"
    )
    return LAPVoiceStateMachine(ConversationSession(session_id="test-1", variables=vars))


class TestPositiveQualificationFlows:
    def test_standard_seven_fields_happy_path(self):
        """All seven fields supplied in normal order; every criterion passes."""
        sm = create_sm()
        # Stage A
        resp, s = sm.process_turn("Yes, speaking.")
        assert s.stage == Stage.OFFER_PRESENTATION
        assert s.identity_verified

        # Stage B
        resp, s = sm.process_turn("Yes, I would like to explore the offer.")
        assert s.stage == Stage.CHECKLIST_QUESTIONING
        assert "residential" in resp.lower()

        # Q1: Property type (Residential)
        resp, s = sm.process_turn("It is a residential apartment.")
        assert s.checklist.property_type.parsed_value == PropertyType.RESIDENTIAL
        assert "solely owned" in resp.lower()

        # Q2: Ownership status (Sole)
        resp, s = sm.process_turn("I am the sole owner.")
        assert s.checklist.ownership_status.parsed_value == OwnershipStatus.SOLE
        assert "original property documents" in resp.lower()

        # Q3: Original documents (Available)
        resp, s = sm.process_turn("Yes, I have all original documents with me.")
        assert s.checklist.original_documents_available.parsed_value == DocumentStatus.AVAILABLE
        assert "how much loan amount" in resp.lower()

        # Q4: Requested loan amount (40 Lakhs)
        resp, s = sm.process_turn("I need 40 lakhs.")
        assert s.checklist.requested_loan_amount.parsed_value == 4000000
        assert "occupation" in resp.lower()

        # Q5: Occupation and income mode (Salaried, Bank)
        resp, s = sm.process_turn("I am salaried and get salary directly in my bank account.")
        assert s.checklist.occupation_and_income_mode.parsed_value["occupation"] == Occupation.SALARIED
        assert s.checklist.occupation_and_income_mode.parsed_value["income_mode"] == IncomeMode.BANK
        assert "market value" in resp.lower()

        # Q6: Property market value (90 Lakhs)
        resp, s = sm.process_turn("The estimated market value is 90 lakhs.")
        assert s.checklist.property_market_value.parsed_value == 9000000
        assert "tenure" in resp.lower()

        # Q7: Requested tenure (10 years)
        resp, s = sm.process_turn("I would like a 10 years tenure.")
        assert s.checklist.requested_tenure_years.parsed_value == 10

        # Post-qualification handoff check
        assert s.stage == Stage.QUALIFIED_HANDOFF
        assert s.outcome == CallOutcome.QUALIFIED_HANDOFF
        assert "congratulations" in resp.lower()
        assert "senior loan expert" in resp.lower()

    def test_eligible_commercial_property_joint_ownership(self):
        """Eligible commercial property with joint ownership."""
        sm = create_sm()
        sm.process_turn("Speaking")
        sm.process_turn("Yes, interested")
        sm.process_turn("It is a commercial office space")
        sm.process_turn("Jointly owned with my partner")
        sm.process_turn("Yes, original docs are available")
        sm.process_turn("50 lakhs")
        sm.process_turn("Self-employed with bank income")
        sm.process_turn("1 crore")
        resp, s = sm.process_turn("5 years")

        assert s.checklist.property_type.parsed_value == PropertyType.COMMERCIAL
        assert s.checklist.ownership_status.parsed_value == OwnershipStatus.JOINT
        assert s.outcome == CallOutcome.QUALIFIED_HANDOFF

    def test_eligible_industrial_property(self):
        """Eligible industrial property."""
        sm = create_sm()
        sm.process_turn("Yes this is Rajesh")
        sm.process_turn("Sure, tell me")
        resp, s = sm.process_turn("I want to pledge my factory in Pune")
        assert s.checklist.property_type.parsed_value == PropertyType.INDUSTRIAL
        assert s.checklist.property_type.is_valid

    def test_self_employed_bank_income(self):
        """Self-employed customer receiving income through a bank."""
        sm = create_sm()
        sm.process_turn("Speaking")
        sm.process_turn("Yes")
        sm.process_turn("Residential flat")
        sm.process_turn("Sole owner")
        sm.process_turn("Original documents available")
        sm.process_turn("25 lakhs")
        resp, s = sm.process_turn("I run my own business and all payments come through bank transfer")
        assert s.checklist.occupation_and_income_mode.parsed_value["occupation"] == Occupation.SELF_EMPLOYED
        assert s.checklist.occupation_and_income_mode.parsed_value["income_mode"] == IncomeMode.BANK
        assert s.checklist.occupation_and_income_mode.is_valid

    def test_boundary_exact_75_lakhs(self):
        """Exactly ₹75,00,000 requested."""
        sm = create_sm()
        sm.process_turn("Speaking")
        sm.process_turn("Yes")
        sm.process_turn("House")
        sm.process_turn("Sole")
        sm.process_turn("Yes")
        resp, s = sm.process_turn("I need exactly 75 lakhs")
        assert s.checklist.requested_loan_amount.parsed_value == 7500000
        assert s.checklist.requested_loan_amount.is_valid
        assert s.stage == Stage.CHECKLIST_QUESTIONING

    def test_boundary_exact_3_years_tenure(self):
        """Exactly 3-year tenure (lower boundary)."""
        sm = create_sm()
        sm.process_turn("Speaking")
        sm.process_turn("Yes")
        sm.process_turn("House")
        sm.process_turn("Sole")
        sm.process_turn("Yes")
        sm.process_turn("30 lakhs")
        sm.process_turn("Salaried bank")
        sm.process_turn("70 lakhs")
        resp, s = sm.process_turn("3 years")
        assert s.checklist.requested_tenure_years.parsed_value == 3
        assert s.outcome == CallOutcome.QUALIFIED_HANDOFF

    def test_boundary_exact_15_years_tenure(self):
        """Exactly 15-year tenure (upper boundary)."""
        sm = create_sm()
        sm.process_turn("Speaking")
        sm.process_turn("Yes")
        sm.process_turn("House")
        sm.process_turn("Sole")
        sm.process_turn("Yes")
        sm.process_turn("30 lakhs")
        sm.process_turn("Salaried bank")
        sm.process_turn("70 lakhs")
        resp, s = sm.process_turn("15 years")
        assert s.checklist.requested_tenure_years.parsed_value == 15
        assert s.outcome == CallOutcome.QUALIFIED_HANDOFF

    def test_multiple_checklist_answers_in_one_sentence(self):
        """Customer volunteers multiple answers in one sentence."""
        sm = create_sm()
        sm.process_turn("Speaking")
        sm.process_turn("Yes")
        resp, s = sm.process_turn("I have a residential flat which is solely in my name, I have all original papers, and I need 30 lakhs.")
        c = s.checklist
        assert c.property_type.parsed_value == PropertyType.RESIDENTIAL
        assert c.ownership_status.parsed_value == OwnershipStatus.SOLE
        assert c.original_documents_available.parsed_value == DocumentStatus.AVAILABLE
        assert c.requested_loan_amount.parsed_value == 3000000
        assert "occupation" in resp.lower()

    def test_volunteers_market_value_before_asked(self):
        """Customer volunteers market value before agent asks."""
        sm = create_sm()
        sm.process_turn("Speaking")
        sm.process_turn("Yes")
        sm.process_turn("I have a flat worth 85 lakhs")
        assert sm.session.checklist.property_type.parsed_value == PropertyType.RESIDENTIAL
        assert sm.session.checklist.property_market_value.parsed_value == 8500000
        sm.process_turn("Sole owner")
        sm.process_turn("Originals available")
        sm.process_turn("25 lakhs")
        resp, s = sm.process_turn("Salaried with bank deposit")
        assert "tenure" in resp.lower()

    def test_volunteers_income_mode_and_loan_amount_out_of_order(self):
        """Customer volunteers income mode and loan amount out of order."""
        sm = create_sm()
        sm.process_turn("Speaking")
        sm.process_turn("Yes")
        # In Q1 (Property type), customer answers: "It is a house, and I earn my salary in bank account and need 20 lakhs"
        resp, s = sm.process_turn("It is a house, and I earn my salary in bank account and need 20 lakhs")
        c = s.checklist
        assert c.property_type.parsed_value == PropertyType.RESIDENTIAL
        assert c.occupation_and_income_mode.parsed_value["income_mode"] == IncomeMode.BANK
        assert c.requested_loan_amount.parsed_value == 2000000
        # Next asked field must be ownership_status (the earliest unanswered)
        assert "solely owned" in resp.lower()

    def test_customer_interrupts_with_interest_rate_then_resumes(self):
        """Customer interrupts asking for interest rate, agent answers without hallucinating and continues."""
        sm = create_sm()
        sm.process_turn("Speaking")
        sm.process_turn("Yes")
        resp, s = sm.process_turn("What is your interest rate?")
        assert "senior loan expert" in resp.lower()
        assert "property" in resp.lower()

    def test_correction_to_another_eligible_value(self):
        """Customer corrects a previously captured value to another eligible value."""
        sm = create_sm()
        sm.process_turn("Speaking")
        sm.process_turn("Yes")
        sm.process_turn("Residential flat")
        assert sm.session.checklist.property_type.parsed_value == PropertyType.RESIDENTIAL

        # Correction
        resp, s = sm.process_turn("Actually not a flat, it is a commercial shop")
        assert s.checklist.property_type.parsed_value == PropertyType.COMMERCIAL
        assert s.checklist.property_type.is_valid


class TestDisqualificationFlows:
    def test_agricultural_property_immediate_disqualification(self):
        """Agricultural property triggers immediate disqualification and stops questioning."""
        sm = create_sm()
        sm.process_turn("Speaking")
        sm.process_turn("Yes")
        resp, s = sm.process_turn("It is agricultural farmland")

        assert s.stage == Stage.DISQUALIFIED
        assert s.outcome == CallOutcome.DISQUALIFIED_AGRICULTURAL
        assert "agricultural" in resp.lower()
        assert "solely owned" not in resp.lower()

    def test_original_documents_unavailable(self):
        """Original documents unavailable triggers immediate disqualification."""
        sm = create_sm()
        sm.process_turn("Speaking")
        sm.process_turn("Yes")
        sm.process_turn("Residential flat")
        sm.process_turn("Sole owner")
        resp, s = sm.process_turn("No, original documents are not available, they are missing")

        assert s.stage == Stage.DISQUALIFIED
        assert s.outcome == CallOutcome.DISQUALIFIED_NO_DOCUMENTS
        assert "original" in resp.lower()

    def test_cash_income_immediate_disqualification(self):
        """Income received in cash triggers immediate disqualification."""
        sm = create_sm()
        sm.process_turn("Speaking")
        sm.process_turn("Yes")
        sm.process_turn("House")
        sm.process_turn("Sole")
        sm.process_turn("Yes")
        sm.process_turn("20 lakhs")
        resp, s = sm.process_turn("I have a shop and get all income in cash in hand")

        assert s.stage == Stage.DISQUALIFIED
        assert s.outcome == CallOutcome.DISQUALIFIED_CASH_INCOME
        assert "cash" in resp.lower()

    def test_loan_above_75_lakhs_declined_revision(self):
        """Loan above ₹75,00,000 followed by refusal to reduce it."""
        sm = create_sm()
        sm.process_turn("Speaking")
        sm.process_turn("Yes")
        sm.process_turn("House")
        sm.process_turn("Sole")
        sm.process_turn("Yes")
        resp, s = sm.process_turn("I need 1.5 crore")
        assert s.stage == Stage.LOAN_AMOUNT_NEGOTIATION
        assert "75,00,000" in resp

        resp, s = sm.process_turn("No, 75 lakhs is too less, I cannot reduce")
        assert s.stage == Stage.DISQUALIFIED
        assert s.outcome == CallOutcome.DISQUALIFIED_EXCESS_AMOUNT

    def test_loan_above_75_lakhs_agreed_to_maximum(self):
        """Loan above ₹75,00,000 followed by agreement to maximum cap."""
        sm = create_sm()
        sm.process_turn("Speaking")
        sm.process_turn("Yes")
        sm.process_turn("House")
        sm.process_turn("Sole")
        sm.process_turn("Yes")
        resp, s = sm.process_turn("I need 1 crore")
        assert s.stage == Stage.LOAN_AMOUNT_NEGOTIATION

        resp, s = sm.process_turn("Okay fine, I will proceed with 75 lakhs")
        assert s.stage == Stage.CHECKLIST_QUESTIONING
        assert s.checklist.requested_loan_amount.parsed_value == 7500000
        assert s.checklist.requested_loan_amount.is_valid
        assert "occupation" in resp.lower()

    def test_tenure_below_3_years_declined_revision(self):
        """Tenure below 3 years followed by refusal to revise."""
        sm = create_sm()
        sm.process_turn("Speaking")
        sm.process_turn("Yes")
        sm.process_turn("House")
        sm.process_turn("Sole")
        sm.process_turn("Yes")
        sm.process_turn("20 lakhs")
        sm.process_turn("Salaried bank")
        sm.process_turn("50 lakhs")
        resp, s = sm.process_turn("I only want 1 year tenure")
        assert s.stage == Stage.TENURE_NEGOTIATION
        assert "3 and 15 years" in resp

        resp, s = sm.process_turn("No, I cannot do 3 years")
        assert s.stage == Stage.DISQUALIFIED
        assert s.outcome == CallOutcome.DISQUALIFIED_INVALID_TENURE

    def test_tenure_above_15_years_declined_revision(self):
        """Tenure above 15 years followed by refusal to revise."""
        sm = create_sm()
        sm.process_turn("Speaking")
        sm.process_turn("Yes")
        sm.process_turn("House")
        sm.process_turn("Sole")
        sm.process_turn("Yes")
        sm.process_turn("20 lakhs")
        sm.process_turn("Salaried bank")
        sm.process_turn("50 lakhs")
        resp, s = sm.process_turn("I want 20 years")
        assert s.stage == Stage.TENURE_NEGOTIATION

        resp, s = sm.process_turn("No, I strictly want 20 years")
        assert s.stage == Stage.DISQUALIFIED
        assert s.outcome == CallOutcome.DISQUALIFIED_INVALID_TENURE

    def test_correction_from_eligible_to_disqualifying(self):
        """Correction that changes an eligible answer into a disqualifying answer."""
        sm = create_sm()
        sm.process_turn("Speaking")
        sm.process_turn("Yes")
        sm.process_turn("Residential flat")
        assert sm.session.checklist.property_type.is_valid

        resp, s = sm.process_turn("Actually sorry, it is agricultural land in my village")
        assert s.stage == Stage.DISQUALIFIED
        assert s.outcome == CallOutcome.DISQUALIFIED_AGRICULTURAL

    def test_multiple_disqualifying_facts_in_one_utterance(self):
        """Multiple disqualifying facts volunteered in one utterance (e.g. agricultural + cash)."""
        sm = create_sm()
        sm.process_turn("Speaking")
        sm.process_turn("Yes")
        resp, s = sm.process_turn("It is agricultural land and I get cash income")
        assert s.stage == Stage.DISQUALIFIED
        assert s.outcome in [CallOutcome.DISQUALIFIED_AGRICULTURAL, CallOutcome.DISQUALIFIED_CASH_INCOME]
        assert s.outcome != CallOutcome.QUALIFIED_HANDOFF


class TestRoutingAndCallControl:
    def test_existing_property_loan_triggers_transfer(self):
        """Existing property loan triggers loan transfer route immediately."""
        sm = create_sm()
        sm.process_turn("Speaking")
        resp, s = sm.process_turn("I already have an existing loan on this property")

        assert s.stage == Stage.LOAN_TRANSFER_REFERRAL
        assert s.outcome == CallOutcome.LOAN_TRANSFER_REFERRAL
        assert "loan transfer specialist" in resp.lower()

    def test_reduce_existing_emi_triggers_transfer(self):
        """Request to reduce existing EMI triggers loan transfer route."""
        sm = create_sm()
        sm.process_turn("Speaking")
        sm.process_turn("Yes")
        sm.process_turn("House")
        resp, s = sm.process_turn("Can you help me reduce my current EMI on this house?")

        assert s.stage == Stage.LOAN_TRANSFER_REFERRAL
        assert s.outcome == CallOutcome.LOAN_TRANSFER_REFERRAL

    def test_explicit_loan_transfer_midway_through_qualification(self):
        """Explicit loan transfer request midway through qualification stops fresh-loan checklist."""
        sm = create_sm()
        sm.process_turn("Speaking")
        sm.process_turn("Yes")
        sm.process_turn("Commercial shop")
        sm.process_turn("Sole owner")
        sm.process_turn("Originals available")
        # Midway at Q4:
        resp, s = sm.process_turn("Actually, I want to transfer my existing loan from HDFC to reduce interest")
        assert s.stage == Stage.LOAN_TRANSFER_REFERRAL
        assert s.outcome == CallOutcome.LOAN_TRANSFER_REFERRAL
        assert "loan transfer" in resp.lower()
        # Questioning must NOT continue
        assert "occupation" not in resp.lower()

    def test_busy_customer_requests_callback(self):
        """Busy customer requests a callback."""
        sm = create_sm()
        resp, s = sm.process_turn("I am driving right now, call me tomorrow at 4pm")

        assert s.stage == Stage.BUSY_CALLBACK
        assert s.outcome == CallOutcome.BUSY_CALLBACK_SCHEDULED
        assert s.callback_preference is not None

    def test_customer_refuses_offer(self):
        """Customer refuses the offer."""
        sm = create_sm()
        sm.process_turn("Speaking")
        resp, s = sm.process_turn("I am not interested, do not call me")

        assert s.stage == Stage.REFUSAL_OR_TERMINATION
        assert s.outcome == CallOutcome.CUSTOMER_REFUSED

    def test_wrong_person_answers(self):
        """Wrong person answers."""
        sm = create_sm()
        resp, s = sm.process_turn("Wrong number, Rajesh is not here")

        assert s.stage == Stage.REFUSAL_OR_TERMINATION
        assert s.outcome == CallOutcome.UNVERIFIED_IDENTITY_TERMINATED

    def test_identity_unverified_loop(self):
        """Identity cannot be verified after asking."""
        sm = create_sm()
        resp, s = sm.process_turn("Who is this?")
        assert not s.identity_verified
        assert s.stage == Stage.GREETING_AND_IDENTIFICATION
        assert "confirm" in resp.lower()

    def test_vague_answer_triggers_clarification(self):
        """Customer provides a vague answer (photocopies only) requiring clarification."""
        sm = create_sm()
        sm.process_turn("Speaking")
        sm.process_turn("Yes")
        sm.process_turn("House")
        sm.process_turn("Sole owner")
        resp, s = sm.process_turn("I only have photocopies of the registry right now")
        assert s.checklist.original_documents_available.needs_clarification
        assert "original physical documents" in resp.lower()

    def test_silence_or_unintelligible_repeats_question(self):
        """Customer is silent or speech recognition fails."""
        sm = create_sm()
        sm.process_turn("Speaking")
        sm.process_turn("Yes")
        resp, s = sm.process_turn("umm... hmm...")
        assert "didn't quite catch that" in resp.lower()
        assert "residential" in resp.lower()

    def test_skipped_unanswered_field_is_revisited(self):
        """A field that was skipped due to a question or diversion is revisited."""
        sm = create_sm()
        sm.process_turn("Speaking")
        sm.process_turn("Yes")
        # Customer asks about interest rates instead of answering Q1
        resp, s = sm.process_turn("What are your processing charges?")
        # Agent answers and revisits Q1
        assert "property" in resp.lower()
        assert sm.session.checklist.get_earliest_unanswered_field() == "property_type"

    def test_disqualified_customer_never_marked_qualified(self):
        """A disqualified customer is never accidentally marked qualified even with subsequent turns."""
        sm = create_sm()
        sm.process_turn("Speaking")
        sm.process_turn("Yes")
        sm.process_turn("It is agricultural land")
        assert sm.session.outcome == CallOutcome.DISQUALIFIED_AGRICULTURAL
        # Subsequent turn
        resp, s = sm.process_turn("Wait, what about my 50 lakhs loan?")
        assert s.outcome == CallOutcome.DISQUALIFIED_AGRICULTURAL
        assert s.outcome != CallOutcome.QUALIFIED_HANDOFF

    def test_transfer_referral_never_marked_as_fresh_loan(self):
        """A transfer referral is never marked as fresh-loan qualification."""
        sm = create_sm()
        sm.process_turn("Speaking")
        resp, s = sm.process_turn("I have an existing loan")
        assert s.outcome == CallOutcome.LOAN_TRANSFER_REFERRAL
        assert s.outcome != CallOutcome.QUALIFIED_HANDOFF

    def test_handoff_gate_blocks_if_field_missing(self):
        """Handoff is strictly blocked if any required field is missing."""
        sm = create_sm()
        sm.process_turn("Speaking")
        sm.process_turn("Yes")
        sm.process_turn("House")
        sm.process_turn("Sole")
        sm.process_turn("Yes")
        sm.process_turn("30 lakhs")
        assert not sm._evaluate_handoff_gate()
        assert sm.session.outcome == CallOutcome.IN_PROGRESS


class TestBoundaryParameters:
    @pytest.mark.parametrize("amt,expected_valid", [
        ("74,99,999", True),
        ("75,00,000", True),
        ("75,00,001", False),
        ("80,00,000", False),
    ])
    def test_loan_amount_boundaries(self, amt, expected_valid):
        sm = create_sm()
        sm.process_turn("Speaking")
        sm.process_turn("Yes")
        sm.process_turn("House")
        sm.process_turn("Sole")
        sm.process_turn("Yes")
        resp, s = sm.process_turn(f"I need {amt}")
        field = s.checklist.requested_loan_amount
        assert field.is_valid == expected_valid

    @pytest.mark.parametrize("tenure,expected_valid", [
        ("2 years", False),
        ("3 years", True),
        ("10 years", True),
        ("15 years", True),
        ("16 years", False),
    ])
    def test_tenure_boundaries(self, tenure, expected_valid):
        sm = create_sm()
        sm.process_turn("Speaking")
        sm.process_turn("Yes")
        sm.process_turn("House")
        sm.process_turn("Sole")
        sm.process_turn("Yes")
        sm.process_turn("20 lakhs")
        sm.process_turn("Salaried bank")
        sm.process_turn("50 lakhs")
        resp, s = sm.process_turn(f"I want {tenure}")
        field = s.checklist.requested_tenure_years
        assert field.is_valid == expected_valid
