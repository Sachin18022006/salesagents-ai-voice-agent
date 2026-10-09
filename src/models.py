"""Data models and enums for Home Credit LAP Voice Agent."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Stage(str, Enum):
    """Conversation lifecycle stages."""
    GREETING_AND_IDENTIFICATION = "GREETING_AND_IDENTIFICATION"
    OFFER_PRESENTATION = "OFFER_PRESENTATION"
    CHECKLIST_QUESTIONING = "CHECKLIST_QUESTIONING"
    LOAN_AMOUNT_NEGOTIATION = "LOAN_AMOUNT_NEGOTIATION"
    TENURE_NEGOTIATION = "TENURE_NEGOTIATION"
    DISQUALIFIED = "DISQUALIFIED"
    LOAN_TRANSFER_REFERRAL = "LOAN_TRANSFER_REFERRAL"
    QUALIFIED_HANDOFF = "QUALIFIED_HANDOFF"
    BUSY_CALLBACK = "BUSY_CALLBACK"
    REFUSAL_OR_TERMINATION = "REFUSAL_OR_TERMINATION"


class PropertyType(str, Enum):
    RESIDENTIAL = "Residential"
    COMMERCIAL = "Commercial"
    INDUSTRIAL = "Industrial"
    AGRICULTURAL = "Agricultural"
    UNKNOWN = "Unknown"


class OwnershipStatus(str, Enum):
    SOLE = "Sole"
    JOINT = "Joint"
    UNKNOWN = "Unknown"


class DocumentStatus(str, Enum):
    AVAILABLE = "Available"
    UNAVAILABLE = "Unavailable"
    AMBIGUOUS = "Ambiguous"
    UNKNOWN = "Unknown"


class Occupation(str, Enum):
    SALARIED = "Salaried"
    SELF_EMPLOYED = "Self-Employed"
    UNKNOWN = "Unknown"


class IncomeMode(str, Enum):
    BANK = "Bank"
    CASH = "Cash"
    MIXED_AMBIGUOUS = "Mixed/Ambiguous"
    UNKNOWN = "Unknown"


class CallOutcome(str, Enum):
    IN_PROGRESS = "in_progress"
    QUALIFIED_HANDOFF = "qualified_handoff"
    DISQUALIFIED_AGRICULTURAL = "disqualified_agricultural"
    DISQUALIFIED_NO_DOCUMENTS = "disqualified_no_documents"
    DISQUALIFIED_CASH_INCOME = "disqualified_cash_income"
    DISQUALIFIED_EXCESS_AMOUNT = "disqualified_excess_amount"
    DISQUALIFIED_INVALID_TENURE = "disqualified_invalid_tenure"
    LOAN_TRANSFER_REFERRAL = "loan_transfer_referral"
    BUSY_CALLBACK_SCHEDULED = "busy_callback_scheduled"
    CUSTOMER_REFUSED = "customer_refused"
    UNVERIFIED_IDENTITY_TERMINATED = "unverified_identity_terminated"


class FieldCapture(BaseModel):
    """Represents the capture and validation state for a single checklist field."""
    raw_value: Optional[str] = None
    parsed_value: Optional[Any] = None
    is_answered: bool = False
    is_valid: bool = False
    needs_clarification: bool = False
    clarification_reason: Optional[str] = None


class ChecklistState(BaseModel):
    """The 7 mandatory checklist data points."""
    property_type: FieldCapture = Field(default_factory=FieldCapture)
    ownership_status: FieldCapture = Field(default_factory=FieldCapture)
    original_documents_available: FieldCapture = Field(default_factory=FieldCapture)
    requested_loan_amount: FieldCapture = Field(default_factory=FieldCapture)
    occupation_and_income_mode: FieldCapture = Field(default_factory=FieldCapture)
    property_market_value: FieldCapture = Field(default_factory=FieldCapture)
    requested_tenure_years: FieldCapture = Field(default_factory=FieldCapture)

    def is_field_answered(self, field_name: str) -> bool:
        field = getattr(self, field_name, None)
        return field.is_answered if field else False

    def is_all_answered(self) -> bool:
        fields = [
            self.property_type,
            self.ownership_status,
            self.original_documents_available,
            self.requested_loan_amount,
            self.occupation_and_income_mode,
            self.property_market_value,
            self.requested_tenure_years,
        ]
        return all(f.is_answered and f.is_valid for f in fields)

    def get_earliest_unanswered_field(self) -> Optional[str]:
        sequence = [
            "property_type",
            "ownership_status",
            "original_documents_available",
            "requested_loan_amount",
            "occupation_and_income_mode",
            "property_market_value",
            "requested_tenure_years",
        ]
        for field_name in sequence:
            field = getattr(self, field_name)
            if not field.is_answered or field.needs_clarification:
                return field_name
        return None


class RuntimeVariables(BaseModel):
    """All 11 mandatory assignment runtime variables."""
    company_name: str = "Home Credit"
    customer_name: str = "Rajesh Sharma"
    agent_name: str = "Priya"
    agent_gender: str = "Female"  # "Female" or "Male"
    current_date: str = "2026-10-09"
    current_day: str = "Friday"
    current_time: str = "11:30 AM IST"
    additional_context_from_rag: str = (
        "Home Credit Loan Against Property (LAP) offers attractive rates, "
        "flexible tenure up to 15 years, transparent processing, and dedicated expert support."
    )
    language_to_speak: str = "English"  # "English" or "Hindi"
    conversation_history: List[Dict[str, str]] = Field(default_factory=list)
    customer_utterance: str = ""


class ConversationSession(BaseModel):
    """Session state encompassing the entire call lifecycle."""
    session_id: str
    stage: Stage = Stage.GREETING_AND_IDENTIFICATION
    identity_verified: bool = False
    customer_speaking: bool = False
    wrong_person: bool = False
    is_busy: bool = False
    callback_preference: Optional[str] = None
    refused: bool = False
    is_transfer_request: bool = False
    checklist: ChecklistState = Field(default_factory=ChecklistState)
    outcome: CallOutcome = CallOutcome.IN_PROGRESS
    disqualification_reason: Optional[str] = None
    negotiating_amount: bool = False
    negotiating_tenure: bool = False
    provisional_excess_amount: Optional[int] = None
    provisional_invalid_tenure: Optional[int] = None
    history: List[Dict[str, str]] = Field(default_factory=list)
    variables: RuntimeVariables = Field(default_factory=RuntimeVariables)
