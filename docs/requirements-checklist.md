# Home Credit LAP Voice Agent — Requirements Checklist & Traceability Matrix

## 1. Reference Materials & Audit Status

| Source | Reference Identifier | Access Status | Audit Notes |
| :--- | :--- | :--- | :--- |
| **Assignment PDF** | `SalesAgents AI Hiring Assignment - AI_voice_agent_prep.pdf` | **Fully Verified & Authoritative** | Read in full. Contains 5 pages specifying the Home Credit LAP use case, call stages, 7 eligibility checklist points, business boundaries, 11 runtime prompt variables, and submission rules. |
| **Notion Reference** | `https://dour-blade-da4.notion.site/...` | **Access Limitation Documented** | Direct HTTP retrieval returned an empty client-side JavaScript shell. Automated browser automation encountered environment-level Playwright driver initialization restrictions on this system. As instructed by the assignment directive, this limitation is honestly disclosed, the uploaded PDF serves as the authoritative source, and no artificial requirements have been fabricated. |

---

## 2. Requirements-to-Implementation-to-Test Mapping Matrix

### A. General Use Case & Agent Persona
| ID | Requirement Specification | Implementation Location | Verification Test | Status |
| :--- | :--- | :--- | :--- | :--- |
| **REQ-GEN-01** | AI Voice Agent for **Home Credit** contacting existing valued customers | `src/models.py`, `src/prompt_builder.py` | `test_runtime_variables_interpolation` | **PASS** |
| **REQ-GEN-02** | Introduce Loan Against Property (LAP) offer up to ₹75,00,000 (75 Lakhs) | `src/state_machine.py`, `docs/system-prompt.md` | `test_standard_seven_fields_happy_path` | **PASS** |
| **REQ-GEN-03** | Advisory, transparent tone; preliminary qualification, not final approval guarantee | `src/state_machine.py`, `docs/system-prompt.md` | `test_standard_seven_fields_happy_path` | **PASS** |
| **REQ-GEN-04** | Transition qualified leads to senior human loan expert for finalization | `src/state_machine.py:Stage.QUALIFIED_HANDOFF` | `test_standard_seven_fields_happy_path` | **PASS** |

---

### B. Prompt Runtime Variables (11 Mandatory Variables)
| ID | Runtime Variable | Template Syntax | Implementation File | Verification Test | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **VAR-01** | `company_name` | `{{company_name}}` | `src/models.py`, `src/prompt_builder.py` | `test_runtime_variables_interpolation` | **PASS** |
| **VAR-02** | `customer_name` | `{{customer_name}}` | `src/models.py`, `src/prompt_builder.py` | `test_runtime_variables_interpolation` | **PASS** |
| **VAR-03** | `agent_name` | `{{agent_name}}` | `src/models.py`, `src/prompt_builder.py` | `test_runtime_variables_interpolation` | **PASS** |
| **VAR-04** | `agent_gender` | `{{agent_gender}}` | `src/models.py`, `src/prompt_builder.py` | `test_runtime_variables_interpolation` | **PASS** |
| **VAR-05** | `current_date` | `{{current_date}}` | `src/models.py`, `src/prompt_builder.py` | `test_runtime_variables_interpolation` | **PASS** |
| **VAR-06** | `current_day` | `{{current_day}}` | `src/models.py`, `src/prompt_builder.py` | `test_runtime_variables_interpolation` | **PASS** |
| **VAR-07** | `current_time` | `{{current_time}}` | `src/models.py`, `src/prompt_builder.py` | `test_runtime_variables_interpolation` | **PASS** |
| **VAR-08** | `additional_context_from_rag` | `{{additional_context_from_rag}}` | `src/models.py`, `src/prompt_builder.py` | `test_runtime_variables_interpolation` | **PASS** |
| **VAR-09** | `language_to_speak` | `{{language_to_speak}}` | `src/models.py`, `src/prompt_builder.py` | `test_runtime_variables_interpolation` | **PASS** |
| **VAR-10** | `conversation_history` | `{{conversation_history}}` | `src/models.py`, `src/prompt_builder.py` | `test_runtime_variables_interpolation` | **PASS** |
| **VAR-11** | `customer_utterance` | `{{customer_utterance}}` | `src/models.py`, `src/prompt_builder.py` | `test_runtime_variables_interpolation` | **PASS** |

---

### C. Conversation Lifecycle & State Machine
| ID | Stage / Branch | Functional Logic | Implementation | Automated Test | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **FLOW-01** | Greeting & Identity | Confirm intended customer speaking before disclosing offer | `src/state_machine.py:_handle_greeting_stage` | `test_identity_unverified_loop` | **PASS** |
| **FLOW-02** | Third Party / Wrong Person | Do not reveal sensitive details; terminate politely | `src/state_machine.py:detect_identity_verification` | `test_wrong_person_answers` | **PASS** |
| **FLOW-03** | Busy / Driving / Meeting | Acknowledge situation, record callback time, close politely | `src/extractor.py:detect_busy_intent` | `test_busy_customer_requests_callback` | **PASS** |
| **FLOW-04** | Customer Refusal | Respect refusal, no pressure, terminate gracefully | `src/extractor.py:detect_refusal_intent` | `test_customer_refuses_offer` | **PASS** |
| **FLOW-05** | Present Offer | Explain loyalty offer up to ₹75 Lakhs | `src/state_machine.py:_get_offer_presentation_text` | `test_standard_seven_fields_happy_path` | **PASS** |
| **FLOW-06** | Loan Transfer Switch | If existing loan or EMI reduction requested, route immediately | `src/extractor.py:detect_loan_transfer_intent` | `test_existing_property_loan_triggers_transfer`, `test_reduce_existing_emi_triggers_transfer` | **PASS** |

---

### D. The 7-Point Eligibility Checklist
| ID | Checklist Field | Qualification Rule | Implementation | Automated Test | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **CHK-01** | `property_type` | Residential, Commercial, Industrial: Eligible.<br>Agricultural: Immediate Disqualification. | `src/normalizers.py:parse_property_type` | `test_residential`, `test_commercial`, `test_industrial`, `test_agricultural_property_immediate_disqualification` | **PASS** |
| **CHK-02** | `ownership_status` | Sole: Eligible.<br>Joint: Eligible. | `src/normalizers.py:parse_ownership_status` | `test_sole_ownership`, `test_joint_ownership` | **PASS** |
| **CHK-03** | `original_documents_available` | Original available: Eligible.<br>Unavailable: Immediate Disqualification.<br>Photocopy/scans: Clarify. | `src/normalizers.py:parse_original_documents` | `test_originals_available`, `test_original_documents_unavailable`, `test_photocopies_ambiguous` | **PASS** |
| **CHK-04** | `requested_loan_amount` | <= ₹75,00,000: Eligible.<br>> ₹75,00,000: Negotiate cap; disqualify if declined. | `src/normalizers.py:parse_inr_amount`, `src/state_machine.py:_handle_amount_negotiation` | `test_boundary_exact_75_lakhs`, `test_loan_above_75_lakhs_agreed_to_maximum`, `test_loan_above_75_lakhs_declined_revision` | **PASS** |
| **CHK-05** | `occupation_and_income_mode` | Salaried/Self-employed with Bank income: Eligible.<br>Cash income: Immediate Disqualification.<br>Mixed: Clarify. | `src/normalizers.py:parse_occupation_and_income_mode` | `test_salaried_bank`, `test_self_employed_bank_income`, `test_cash_income_immediate_disqualification`, `test_mixed_income_ambiguous` | **PASS** |
| **CHK-06** | `property_market_value` | Estimated INR value captured without inventing minimum LTV thresholds. | `src/extractor.py:extract_amounts` | `test_volunteers_market_value_before_asked` | **PASS** |
| **CHK-07** | `requested_tenure_years` | 3 to 15 years inclusive: Eligible.<br><3 or >15: Negotiate; disqualify if declined. | `src/normalizers.py:parse_tenure_years`, `src/state_machine.py:_handle_tenure_negotiation` | `test_boundary_exact_3_years_tenure`, `test_boundary_exact_15_years_tenure`, `test_tenure_below_3_years_declined_revision`, `test_tenure_above_15_years_declined_revision` | **PASS** |

---

### E. Memory, Out-of-Order Extraction & Strict Handoff Gates
| ID | Requirement | Logic & Behavior | Implementation | Automated Test | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **GATE-01** | Out-of-Order Volunteering | If customer volunteers future checklist answers, store them and do NOT ask again | `src/extractor.py:extract_checklist_facts`, `src/state_machine.py:_update_checklist_state` | `test_multiple_checklist_answers_in_one_sentence`, `test_volunteers_income_mode_and_loan_amount_out_of_order` | **PASS** |
| **GATE-02** | Strict Handoff Gates | Handoff occurs ONLY when all 7 fields answered and valid, fresh loan, identity verified | `src/state_machine.py:_evaluate_handoff_gate` | `test_handoff_gate_blocks_if_field_missing`, `test_standard_seven_fields_happy_path` | **PASS** |
| **GATE-03** | Terminal Isolation | Disqualified, transfer, or refused sessions can NEVER accidentally resume qualification | `src/state_machine.py:process_turn` | `test_disqualified_customer_never_marked_qualified`, `test_transfer_referral_never_marked_as_fresh_loan` | **PASS** |
| **GATE-04** | Non-Hallucination Guardrail | Never invent interest rates or processing fees; refer to senior expert | `src/state_machine.py:_handle_checklist_stage`, `docs/system-prompt.md` | `test_customer_interrupts_with_interest_rate_then_resumes` | **PASS** |

---

## 3. Test Execution Summary
- **Framework**: `pytest 9.1.1`
- **Total Test Cases Executed**: **98**
- **Passed**: **98 (100%)**
- **Failed**: **0**
- **Execution Time**: **0.17 seconds**
