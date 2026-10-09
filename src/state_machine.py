"""Deterministic conversation state machine for Home Credit LAP Voice Agent."""

from typing import Tuple, Optional
import re
from src.models import (
    Stage, CallOutcome, ConversationSession, PropertyType,
    DocumentStatus, IncomeMode, RuntimeVariables
)
from src.extractor import (
    detect_loan_transfer_intent, detect_busy_intent,
    detect_refusal_intent, detect_identity_verification,
    extract_checklist_facts
)
from src.normalizers import parse_inr_amount, parse_tenure_years


class LAPVoiceStateMachine:
    """Manages conversational state, validation gates, transitions, and response generation."""

    def __init__(self, session: Optional[ConversationSession] = None):
        if session is None:
            import uuid
            self.session = ConversationSession(
                session_id=str(uuid.uuid4()),
                variables=RuntimeVariables()
            )
        else:
            self.session = session

    def get_greeting_message(self) -> str:
        """Initial outbound greeting spoken by the agent."""
        vars = self.session.variables
        salutation = "good day"
        if "AM" in vars.current_time.upper():
            salutation = "good morning"
        elif "PM" in vars.current_time.upper():
            salutation = "good afternoon"

        if vars.language_to_speak.lower() == "hindi":
            gender_suffix = "bol rahi hoon" if vars.agent_gender.lower() == "female" else "bol raha hoon"
            return (
                f"Namaste, kya meri baat {vars.customer_name} ji se ho rahi hai? "
                f"Main {vars.company_name} se {vars.agent_name} {gender_suffix}."
            )
        else:
            return (
                f"Hello, {salutation}, am I speaking with {vars.customer_name}? "
                f"I'm {vars.agent_name} calling from {vars.company_name}."
            )

    def process_turn(self, utterance: str) -> Tuple[str, ConversationSession]:
        """Process customer utterance, update session state, apply business logic, and generate spoken response."""
        self.session.variables.customer_utterance = utterance
        self.session.history.append({"speaker": "customer", "text": utterance})

        # 0. Global Check: Loan Transfer Intent takes priority at any point
        if detect_loan_transfer_intent(utterance):
            self.session.is_transfer_request = True
            self.session.stage = Stage.LOAN_TRANSFER_REFERRAL
            self.session.outcome = CallOutcome.LOAN_TRANSFER_REFERRAL
            response = self._get_transfer_response()
            self.session.history.append({"speaker": "agent", "text": response})
            return response, self.session

        # 1. Global Check: Busy / Callback request
        is_busy, callback_pref = detect_busy_intent(utterance)
        if is_busy and self.session.stage in [Stage.GREETING_AND_IDENTIFICATION, Stage.OFFER_PRESENTATION, Stage.CHECKLIST_QUESTIONING]:
            self.session.is_busy = True
            self.session.callback_preference = callback_pref or "later"
            self.session.stage = Stage.BUSY_CALLBACK
            self.session.outcome = CallOutcome.BUSY_CALLBACK_SCHEDULED
            response = self._get_busy_response()
            self.session.history.append({"speaker": "agent", "text": response})
            return response, self.session

        # 2. Global Check: Refusal
        if detect_refusal_intent(utterance) and not self.session.negotiating_amount and not self.session.negotiating_tenure:
            self.session.refused = True
            self.session.stage = Stage.REFUSAL_OR_TERMINATION
            self.session.outcome = CallOutcome.CUSTOMER_REFUSED
            response = self._get_refusal_response()
            self.session.history.append({"speaker": "agent", "text": response})
            return response, self.session

        # 3. Stage-specific state processing
        if self.session.stage == Stage.GREETING_AND_IDENTIFICATION:
            return self._handle_greeting_stage(utterance)

        elif self.session.stage == Stage.OFFER_PRESENTATION:
            return self._handle_offer_stage(utterance)

        elif self.session.stage == Stage.LOAN_AMOUNT_NEGOTIATION:
            return self._handle_amount_negotiation(utterance)

        elif self.session.stage == Stage.TENURE_NEGOTIATION:
            return self._handle_tenure_negotiation(utterance)

        elif self.session.stage == Stage.CHECKLIST_QUESTIONING:
            return self._handle_checklist_stage(utterance)

        elif self.session.outcome in [
            CallOutcome.QUALIFIED_HANDOFF,
            CallOutcome.DISQUALIFIED_AGRICULTURAL,
            CallOutcome.DISQUALIFIED_NO_DOCUMENTS,
            CallOutcome.DISQUALIFIED_CASH_INCOME,
            CallOutcome.DISQUALIFIED_EXCESS_AMOUNT,
            CallOutcome.DISQUALIFIED_INVALID_TENURE,
            CallOutcome.LOAN_TRANSFER_REFERRAL,
            CallOutcome.BUSY_CALLBACK_SCHEDULED,
            CallOutcome.CUSTOMER_REFUSED,
            CallOutcome.UNVERIFIED_IDENTITY_TERMINATED
        ]:
            response = "Thank you. Our call has concluded. Have a wonderful day."
            return response, self.session

        return "I beg your pardon, could you please repeat that?", self.session

    def _handle_greeting_stage(self, utterance: str) -> Tuple[str, ConversationSession]:
        confirmed, wrong_person = detect_identity_verification(utterance, self.session.variables.customer_name)
        if wrong_person:
            self.session.wrong_person = True
            self.session.stage = Stage.REFUSAL_OR_TERMINATION
            self.session.outcome = CallOutcome.UNVERIFIED_IDENTITY_TERMINATED
            resp = (
                f"I apologize for the disturbance. I was attempting to reach {self.session.variables.customer_name}. "
                "Thank you and have a good day."
            )
            self.session.history.append({"speaker": "agent", "text": resp})
            return resp, self.session

        if confirmed:
            self.session.identity_verified = True
            self.session.customer_speaking = True
            self.session.stage = Stage.OFFER_PRESENTATION
            resp = self._get_offer_presentation_text()
            self.session.history.append({"speaker": "agent", "text": resp})
            return resp, self.session

        resp = (
            f"I am calling for {self.session.variables.customer_name} from {self.session.variables.company_name}. "
            "May I confirm if I am speaking with them?"
        )
        self.session.history.append({"speaker": "agent", "text": resp})
        return resp, self.session

    def _handle_offer_stage(self, utterance: str) -> Tuple[str, ConversationSession]:
        cleaned = utterance.lower()
        if any(k in cleaned for k in ["not interested", "nahi chahiye", "don't want", "no thanks"]):
            self.session.refused = True
            self.session.stage = Stage.REFUSAL_OR_TERMINATION
            self.session.outcome = CallOutcome.CUSTOMER_REFUSED
            resp = f"No problem at all, {self.session.variables.customer_name}. Thank you for your time with {self.session.variables.company_name}. Have a wonderful day!"
            self.session.history.append({"speaker": "agent", "text": resp})
            return resp, self.session

        self.session.stage = Stage.CHECKLIST_QUESTIONING

        target_field = self.session.checklist.get_earliest_unanswered_field()
        extracted = extract_checklist_facts(utterance, target_field)
        self._update_checklist_state(extracted)

        disq_resp = self._check_disqualifications()
        if disq_resp:
            self.session.history.append({"speaker": "agent", "text": disq_resp})
            return disq_resp, self.session

        return self._ask_next_question()

    def _handle_checklist_stage(self, utterance: str) -> Tuple[str, ConversationSession]:
        target_field = self.session.checklist.get_earliest_unanswered_field()

        # Handle user inquiring about interest rates or fees
        if any(k in utterance.lower() for k in ["interest rate", "roi", "rate of interest", "percentage", "charges", "fees"]):
            rate_reply = (
                "Regarding interest rates, our senior loan expert will share the exact customized rate based on your property valuation and financial profile. "
            )
            extracted = extract_checklist_facts(utterance, target_field)
            self._update_checklist_state(extracted)
            disq_resp = self._check_disqualifications()
            if disq_resp:
                self.session.history.append({"speaker": "agent", "text": disq_resp})
                return disq_resp, self.session

            next_q = self._get_question_prompt(self.session.checklist.get_earliest_unanswered_field())
            full_resp = rate_reply + next_q
            self.session.history.append({"speaker": "agent", "text": full_resp})
            return full_resp, self.session

        # Extract facts (both target and volunteered)
        extracted = extract_checklist_facts(utterance, target_field)
        self._update_checklist_state(extracted)

        # Disqualification checks
        disq_resp = self._check_disqualifications()
        if disq_resp:
            self.session.history.append({"speaker": "agent", "text": disq_resp})
            return disq_resp, self.session

        # Check if loan amount requires negotiation (> 75L)
        amt_field = self.session.checklist.requested_loan_amount
        if amt_field.is_answered and not amt_field.is_valid and amt_field.parsed_value and amt_field.parsed_value > 75_00_000:
            self.session.negotiating_amount = True
            self.session.provisional_excess_amount = amt_field.parsed_value
            self.session.stage = Stage.LOAN_AMOUNT_NEGOTIATION
            resp = (
                f"You requested ₹{amt_field.parsed_value:,}. However, our special Loan Against Property offer has a maximum limit of ₹75,00,000 (75 Lakhs). "
                "Would you be open to proceeding with the maximum allowed amount of ₹75,00,000 or a lower amount?"
            )
            self.session.history.append({"speaker": "agent", "text": resp})
            return resp, self.session

        # Check if tenure requires negotiation (<3 or >15)
        tenure_field = self.session.checklist.requested_tenure_years
        if tenure_field.is_answered and not tenure_field.is_valid and tenure_field.parsed_value is not None:
            if tenure_field.parsed_value < 3 or tenure_field.parsed_value > 15:
                self.session.negotiating_tenure = True
                self.session.provisional_invalid_tenure = tenure_field.parsed_value
                self.session.stage = Stage.TENURE_NEGOTIATION
                resp = (
                    f"You requested a tenure of {tenure_field.parsed_value} years. Our permitted repayment tenure must be between 3 and 15 years. "
                    "Would you like to select a tenure within this 3 to 15 year range?"
                )
                self.session.history.append({"speaker": "agent", "text": resp})
                return resp, self.session

        # Check if ambiguity requires clarification
        if target_field:
            curr_f = getattr(self.session.checklist, target_field)
            if curr_f.needs_clarification:
                clarification_resp = self._get_clarification_prompt(target_field, curr_f.clarification_reason)
                self.session.history.append({"speaker": "agent", "text": clarification_resp})
                return clarification_resp, self.session

        # If silence or unintelligible
        if not extracted and target_field:
            repeat_resp = f"I didn't quite catch that. {self._get_question_prompt(target_field)}"
            self.session.history.append({"speaker": "agent", "text": repeat_resp})
            return repeat_resp, self.session

        return self._ask_next_question()

    def _handle_amount_negotiation(self, utterance: str) -> Tuple[str, ConversationSession]:
        cleaned = utterance.lower()

        # Check DECLINE first
        decline_signals = ["no", "cannot", "can't", "nahi", "too less", "too small", "won't work", "not enough", "decline", "only want"]
        if any(re.search(rf"\b{re.escape(k)}\b", cleaned) for k in decline_signals):
            self.session.stage = Stage.DISQUALIFIED
            self.session.outcome = CallOutcome.DISQUALIFIED_EXCESS_AMOUNT
            self.session.disqualification_reason = "Customer declined the maximum cap of ₹75,00,000."
            resp = (
                "I understand. Since ₹75,00,000 is our maximum limit for this pre-approved offer, "
                "we will not be able to proceed with your application at this time. "
                "Thank you for speaking with Home Credit, and have a good day."
            )
            self.session.history.append({"speaker": "agent", "text": resp})
            return resp, self.session

        # Customer agrees to revised amount <= 75L
        new_amt = parse_inr_amount(utterance)
        if new_amt is not None and new_amt <= 75_00_000:
            self.session.checklist.requested_loan_amount.parsed_value = new_amt
            self.session.checklist.requested_loan_amount.is_answered = True
            self.session.checklist.requested_loan_amount.is_valid = True
            self.session.checklist.requested_loan_amount.needs_clarification = False
            self.session.negotiating_amount = False
            self.session.stage = Stage.CHECKLIST_QUESTIONING
            ack = f"Understood, I have updated your requested amount to ₹{new_amt:,}. "
            next_q = self._get_question_prompt(self.session.checklist.get_earliest_unanswered_field())
            resp = ack + next_q
            self.session.history.append({"speaker": "agent", "text": resp})
            return resp, self.session

        if any(k in cleaned for k in ["yes", "proceed", "okay", "fine", "75 lakh", "agree", "theek hai"]):
            self.session.checklist.requested_loan_amount.parsed_value = 75_00_000
            self.session.checklist.requested_loan_amount.is_answered = True
            self.session.checklist.requested_loan_amount.is_valid = True
            self.session.checklist.requested_loan_amount.needs_clarification = False
            self.session.negotiating_amount = False
            self.session.stage = Stage.CHECKLIST_QUESTIONING
            ack = "Thank you. I have recorded your loan request for ₹75,00,000. "
            next_q = self._get_question_prompt(self.session.checklist.get_earliest_unanswered_field())
            resp = ack + next_q
            self.session.history.append({"speaker": "agent", "text": resp})
            return resp, self.session

        resp = "Our maximum eligible amount is ₹75,00,000. Would you like to proceed with ₹75,00,000 or lower?"
        self.session.history.append({"speaker": "agent", "text": resp})
        return resp, self.session

    def _handle_tenure_negotiation(self, utterance: str) -> Tuple[str, ConversationSession]:
        cleaned = utterance.lower()

        # Check DECLINE first
        decline_signals = ["no", "cannot", "can't", "nahi", "strictly", "don't want", "decline", "not possible"]
        if any(re.search(rf"\b{re.escape(k)}\b", cleaned) for k in decline_signals):
            self.session.stage = Stage.DISQUALIFIED
            self.session.outcome = CallOutcome.DISQUALIFIED_INVALID_TENURE
            self.session.disqualification_reason = "Customer declined tenure in the allowed 3-15 years range."
            resp = (
                "I understand. Since our repayment tenure is strictly between 3 and 15 years, "
                "we cannot proceed with your request under this offer. "
                "Thank you for your time with Home Credit, and have a pleasant day."
            )
            self.session.history.append({"speaker": "agent", "text": resp})
            return resp, self.session

        new_tenure = parse_tenure_years(utterance)
        if new_tenure is not None and 3 <= new_tenure <= 15:
            self.session.checklist.requested_tenure_years.parsed_value = new_tenure
            self.session.checklist.requested_tenure_years.is_answered = True
            self.session.checklist.requested_tenure_years.is_valid = True
            self.session.checklist.requested_tenure_years.needs_clarification = False
            self.session.negotiating_tenure = False
            self.session.stage = Stage.CHECKLIST_QUESTIONING
            return self._ask_next_question()

        resp = "Our repayment tenure must be between 3 and 15 years. Could you confirm a tenure within this range that works for you?"
        self.session.history.append({"speaker": "agent", "text": resp})
        return resp, self.session

    def _update_checklist_state(self, extracted: dict):
        for field_name, field_cap in extracted.items():
            setattr(self.session.checklist, field_name, field_cap)

    def _check_disqualifications(self) -> Optional[str]:
        # Priority 1: Agricultural property
        pt = self.session.checklist.property_type
        if pt.is_answered and pt.parsed_value == PropertyType.AGRICULTURAL:
            self.session.stage = Stage.DISQUALIFIED
            self.session.outcome = CallOutcome.DISQUALIFIED_AGRICULTURAL
            self.session.disqualification_reason = "Agricultural property is not eligible for this offer."
            return (
                "I understand. Currently, under this specific Loan Against Property offer, "
                "we only accept residential, commercial, or industrial properties. "
                "Unfortunately, agricultural land is not eligible. "
                "Thank you for your time, and we look forward to assisting you with other products in the future."
            )

        # Priority 2: Original documents unavailable
        docs = self.session.checklist.original_documents_available
        if docs.is_answered and docs.parsed_value == DocumentStatus.UNAVAILABLE:
            self.session.stage = Stage.DISQUALIFIED
            self.session.outcome = CallOutcome.DISQUALIFIED_NO_DOCUMENTS
            self.session.disqualification_reason = "Original property documents are unavailable."
            return (
                "Thank you for clarifying. Having original property documents ready for verification is a mandatory requirement. "
                "As the originals are unavailable, we will not be able to proceed with this offer today. "
                "Thank you for speaking with Home Credit."
            )

        # Priority 3: Cash income
        occ = self.session.checklist.occupation_and_income_mode
        if occ.parsed_value and isinstance(occ.parsed_value, dict):
            if occ.parsed_value.get("income_mode") == IncomeMode.CASH:
                self.session.stage = Stage.DISQUALIFIED
                self.session.outcome = CallOutcome.DISQUALIFIED_CASH_INCOME
                self.session.disqualification_reason = "Income received in cash is not eligible."
                return (
                    "Thank you for sharing that. Under our credit guidelines, verifiable income credited into a bank account is mandatory. "
                    "Since your income is received in cash, we cannot proceed with this specific loan offer at this time. "
                    "Thank you for your time, and have a good day."
                )

        return None

    def _ask_next_question(self) -> Tuple[str, ConversationSession]:
        if self._evaluate_handoff_gate():
            self.session.stage = Stage.QUALIFIED_HANDOFF
            self.session.outcome = CallOutcome.QUALIFIED_HANDOFF
            resp = (
                f"Congratulations, {self.session.variables.customer_name}! "
                f"Based on your details, you meet our preliminary eligibility criteria for the Loan Against Property offer. "
                f"A senior loan expert from {self.session.variables.company_name} will contact you shortly to review the exact interest rates and complete your application. "
                "Thank you for your time, and have a wonderful day!"
            )
            self.session.history.append({"speaker": "agent", "text": resp})
            return resp, self.session

        next_field = self.session.checklist.get_earliest_unanswered_field()
        if next_field:
            resp = self._get_question_prompt(next_field)
            self.session.history.append({"speaker": "agent", "text": resp})
            return resp, self.session

        resp = "Thank you. Let me check the details."
        return resp, self.session

    def _evaluate_handoff_gate(self) -> bool:
        if not self.session.identity_verified:
            return False
        if self.session.is_transfer_request:
            return False
        if self.session.refused:
            return False
        if self.session.stage == Stage.DISQUALIFIED or self.session.outcome != CallOutcome.IN_PROGRESS:
            return False

        c = self.session.checklist
        fields = [
            c.property_type,
            c.ownership_status,
            c.original_documents_available,
            c.requested_loan_amount,
            c.occupation_and_income_mode,
            c.property_market_value,
            c.requested_tenure_years,
        ]
        all_passed = all(f.is_answered and f.is_valid and not f.needs_clarification for f in fields)
        return all_passed

    def _get_question_prompt(self, field_name: str) -> str:
        prompts = {
            "property_type": "Could you please tell me what type of property you would like to offer as collateral—is it residential (such as a house or flat), commercial (shop or office), or industrial (factory)?",
            "ownership_status": "Understood. Is this property solely owned in your name, or is it jointly owned with family members or partners?",
            "original_documents_available": "Great. Are the original property documents readily available with you for verification?",
            "requested_loan_amount": "How much loan amount are you looking to borrow against this property?",
            "occupation_and_income_mode": "Could you share your current occupation—are you salaried or self-employed—and do you receive your primary income through a bank account or in cash?",
            "property_market_value": "What is the estimated current market value of this property?",
            "requested_tenure_years": "How many years of repayment tenure would you prefer, between 3 and 15 years?",
        }
        return prompts.get(field_name, "Could you provide further details?")

    def _get_clarification_prompt(self, field_name: str, reason: Optional[str]) -> str:
        if field_name == "property_type":
            return "You mentioned multiple property types. Could you clarify which specific property you wish to pledge as collateral for this loan?"
        elif field_name == "original_documents_available":
            return "Just to clarify, original physical documents are required for verification. Do you have the original documents, or only photocopies/scans?"
        elif field_name == "occupation_and_income_mode":
            return "Could you clarify whether your income is credited directly through a bank account, or received in cash?"
        return reason or "Could you please clarify that detail?"

    def _get_offer_presentation_text(self) -> str:
        vars = self.session.variables
        return (
            f"Thank you for confirming, {vars.customer_name}. As a valued customer of {vars.company_name}, "
            "we are pleased to inform you about a special pre-approved Loan Against Property offer of up to ₹75,00,000 (75 Lakhs). "
            "This is a preliminary qualification check, and a senior loan expert will assist you with full details if you qualify. "
            "Would you like to explore this offer today?"
        )

    def _get_transfer_response(self) -> str:
        return (
            "I understand you are looking to transfer your existing loan or reduce your current EMI. "
            f"Our specialized Loan Transfer team will best assist you. I am referring your details to our senior loan transfer specialist, "
            f"who will contact you shortly. Thank you for your time with {self.session.variables.company_name}, and have a great day!"
        )

    def _get_busy_response(self) -> str:
        return (
            f"I completely understand you're busy right now. I have noted your callback preference for {self.session.callback_preference}. "
            f"We will connect back with you then. Thank you and have a wonderful day!"
        )

    def _get_refusal_response(self) -> str:
        return (
            f"I understand, {self.session.variables.customer_name}. We have noted your preference and will not disturb you further. "
            f"Thank you for your time with {self.session.variables.company_name}. Have a good day."
        )
