# Home Credit LAP Voice Agent — Automated Test Cases & Execution Report

This document records the automated test suite executed against the Home Credit Loan Against Property (LAP) Voice Agent.

- **Test Suite Engine**: `pytest 9.1.1` on Python 3.14.0
- **Total Executed Tests**: **98**
- **Passed**: **98**
- **Failed**: **0**
- **Status**: **ALL TESTS VERIFIED & PASSED**

---

## 1. Positive Qualification Scenarios

| Test Case ID & Method | Customer Utterance(s) | Expected State Transition | Expected Agent Response Category | Expected Outcome | Actual Result |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-POS-01**<br>`test_standard_seven_fields_happy_path` | 1. "Yes, speaking."<br>2. "Yes, I would like to explore."<br>3. "Residential apartment."<br>4. "Sole owner."<br>5. "Yes, original documents ready."<br>6. "I need 40 lakhs."<br>7. "Salaried with bank deposit."<br>8. "90 lakhs market value."<br>9. "10 years tenure." | `GREETING` -> `OFFER_PRESENTATION` -> `CHECKLIST_QUESTIONING` (Q1 through Q7 sequential) -> `QUALIFIED_HANDOFF` | Congratulates customer, confirms preliminary eligibility, states senior loan expert will call back to discuss interest rates. | `qualified_handoff` | **PASS** |
| **TC-POS-02**<br>`test_eligible_commercial_property_joint_ownership` | Commercial office space, Joint ownership with partner, 50L loan, Self-employed with bank income, 1Cr value, 5y tenure. | `CHECKLIST_QUESTIONING` -> `QUALIFIED_HANDOFF` | Validates commercial + joint co-ownership as eligible. Handoff to human expert. | `qualified_handoff` | **PASS** |
| **TC-POS-03**<br>`test_eligible_industrial_property` | "I want to pledge my factory in Pune." | Advances Q1 -> Q2 | Industrial property recognized as eligible collateral. Prompts for ownership status. | `in_progress` | **PASS** |
| **TC-POS-04**<br>`test_self_employed_bank_income` | "I run my own business and all payments come through bank transfer." | Advances Q5 -> Q6 | Self-employed verified with bank income mode. Prompts for property market value. | `in_progress` | **PASS** |
| **TC-POS-05**<br>`test_boundary_exact_75_lakhs` | "I need exactly 75 lakhs." | Evaluates Q4 boundary <= ₹75,00,000 | Accepts ₹75,00,000 as eligible upper boundary without entering negotiation. Prompts for occupation. | `in_progress` | **PASS** |
| **TC-POS-06**<br>`test_boundary_exact_3_years_tenure` | "3 years." | Evaluates Q7 boundary >= 3 years | Validates 3 years as eligible minimum tenure boundary. Reaches post-qualification handoff. | `qualified_handoff` | **PASS** |
| **TC-POS-07**<br>`test_boundary_exact_15_years_tenure` | "15 years." | Evaluates Q7 boundary <= 15 years | Validates 15 years as eligible maximum tenure boundary. Reaches post-qualification handoff. | `qualified_handoff` | **PASS** |
| **TC-POS-08**<br>`test_multiple_checklist_answers_in_one_sentence` | "I have a residential flat which is solely in my name, I have all original papers, and I need 30 lakhs." | Extracts Q1, Q2, Q3, Q4 simultaneously in memory | Skips Q1-Q4 questions; proceeds directly to earliest unanswered: Q5 (Occupation & Income). | `in_progress` | **PASS** |
| **TC-POS-09**<br>`test_volunteers_market_value_before_asked` | "I have a flat worth 85 lakhs." (Volunteered at Q1) | Stores Q1 (Residential) and Q6 (85 Lakhs) in memory | Asks Q2, Q3, Q4, Q5; skips Q6; jumps straight to Q7 (Tenure). Never asks market value again. | `in_progress` | **PASS** |
| **TC-POS-10**<br>`test_volunteers_income_mode_and_loan_amount_out_of_order` | "It is a house, and I earn my salary in bank account and need 20 lakhs." | Stores Q1 (Residential), Q5 (Salaried/Bank), Q4 (20L) | Skips Q1; proceeds to earliest unanswered: Q2 (Ownership status). | `in_progress` | **PASS** |
| **TC-POS-11**<br>`test_customer_interrupts_with_interest_rate_then_resumes` | "What is your interest rate?" | Context retained in `CHECKLIST_QUESTIONING` | Explains senior loan expert will customize exact interest rate; immediately re-prompts earliest unanswered checklist field. | `in_progress` | **PASS** |
| **TC-POS-12**<br>`test_correction_to_another_eligible_value` | "Actually not a flat, it is a commercial shop." | Updates Q1 from Residential to Commercial | Updates memory; re-evaluates eligibility; continues to next unanswered field. | `in_progress` | **PASS** |

---

## 2. Immediate Disqualification Scenarios

| Test Case ID & Method | Customer Utterance(s) | Expected State Transition | Expected Agent Response Category | Expected Outcome | Actual Result |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-DISQ-01**<br>`test_agricultural_property_immediate_disqualification` | "It is agricultural farmland." | `CHECKLIST_QUESTIONING` -> `DISQUALIFIED` | Politely explains agricultural land is ineligible for this LAP offer; ceases questioning; ends call. | `disqualified_agricultural` | **PASS** |
| **TC-DISQ-02**<br>`test_original_documents_unavailable` | "No, original documents are not available, they are missing." | `CHECKLIST_QUESTIONING` -> `DISQUALIFIED` | Explains physical original documents are mandatory; stops questioning; ends call politely. | `disqualified_no_documents` | **PASS** |
| **TC-DISQ-03**<br>`test_cash_income_immediate_disqualification` | "I have a shop and get all income in cash in hand." | `CHECKLIST_QUESTIONING` -> `DISQUALIFIED` | Explains verifiable bank income is mandatory; stops questioning; ends call politely. | `disqualified_cash_income` | **PASS** |
| **TC-DISQ-04**<br>`test_loan_above_75_lakhs_declined_revision` | 1. "I need 1.5 crore."<br>2. "No, 75 lakhs is too less, I cannot reduce." | `CHECKLIST_QUESTIONING` -> `LOAN_AMOUNT_NEGOTIATION` -> `DISQUALIFIED` | Explains ₹75L cap. When customer declines reduction, explains policy limit and ends call politely. | `disqualified_excess_amount` | **PASS** |
| **TC-DISQ-05**<br>`test_loan_above_75_lakhs_agreed_to_maximum` | 1. "I need 1 crore."<br>2. "Okay fine, I will proceed with 75 lakhs." | `CHECKLIST_QUESTIONING` -> `LOAN_AMOUNT_NEGOTIATION` -> `CHECKLIST_QUESTIONING` | Explains ₹75L cap. When customer agrees, records ₹75,00,000 and resumes next unanswered field. | `in_progress` | **PASS** |
| **TC-DISQ-06**<br>`test_tenure_below_3_years_declined_revision` | 1. "I only want 1 year tenure."<br>2. "No, I cannot do 3 years." | `CHECKLIST_QUESTIONING` -> `TENURE_NEGOTIATION` -> `DISQUALIFIED` | Explains 3-15 years permitted range. When declined, ends call politely without qualification. | `disqualified_invalid_tenure` | **PASS** |
| **TC-DISQ-07**<br>`test_tenure_above_15_years_declined_revision` | 1. "I want 20 years."<br>2. "No, I strictly want 20 years." | `CHECKLIST_QUESTIONING` -> `TENURE_NEGOTIATION` -> `DISQUALIFIED` | Explains permitted range up to 15 years. When declined, ends call politely without qualification. | `disqualified_invalid_tenure` | **PASS** |
| **TC-DISQ-08**<br>`test_correction_from_eligible_to_disqualifying` | 1. "Residential flat."<br>2. "Actually sorry, it is agricultural land in my village." | `CHECKLIST_QUESTIONING` -> `DISQUALIFIED` | Overwrites property type with Agricultural and triggers immediate disqualification protocol. | `disqualified_agricultural` | **PASS** |
| **TC-DISQ-09**<br>`test_multiple_disqualifying_facts_in_one_utterance` | "It is agricultural land and I get cash income." | `CHECKLIST_QUESTIONING` -> `DISQUALIFIED` | Catches agricultural/cash violation immediately; terminates call; never qualifies. | `disqualified_agricultural` | **PASS** |

---

## 3. High-Priority Routing & Call Control Scenarios

| Test Case ID & Method | Customer Utterance(s) | Expected State Transition | Expected Agent Response Category | Expected Outcome | Actual Result |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-ROUTE-01**<br>`test_existing_property_loan_triggers_transfer` | "I already have an existing loan on this property." | Transition to `LOAN_TRANSFER_REFERRAL` | Recognizes existing loan. Informs customer senior loan transfer specialist will contact them. Ends call. | `loan_transfer_referral` | **PASS** |
| **TC-ROUTE-02**<br>`test_reduce_existing_emi_triggers_transfer` | "Can you help me reduce my current EMI on this house?" | Transition to `LOAN_TRANSFER_REFERRAL` | Recognizes balance transfer/refinance intent. Routes to loan transfer team. Ends call. | `loan_transfer_referral` | **PASS** |
| **TC-ROUTE-03**<br>`test_explicit_loan_transfer_midway_through_qualification` | "Actually, I want to transfer my existing loan from HDFC to reduce interest." (Midway at Q4) | Aborts `CHECKLIST_QUESTIONING` -> `LOAN_TRANSFER_REFERRAL` | Ceases fresh-loan questions immediately; confirms referral to loan transfer specialist; ends call. | `loan_transfer_referral` | **PASS** |
| **TC-ROUTE-04**<br>`test_busy_customer_requests_callback` | "I am driving right now, call me tomorrow at 4pm." | Transition to `BUSY_CALLBACK` | Acknowledges busy state, captures "tomorrow at 4pm" callback preference, ends call politely. | `busy_callback_scheduled` | **PASS** |
| **TC-ROUTE-05**<br>`test_customer_refuses_offer` | "I am not interested, do not call me." | Transition to `REFUSAL_OR_TERMINATION` | Respects refusal without pressuring, notes opt-out preference, ends call politely. | `customer_refused` | **PASS** |
| **TC-ROUTE-06**<br>`test_wrong_person_answers` | "Wrong number, Rajesh is not here." | Transition to `REFUSAL_OR_TERMINATION` | Does not disclose loan offer or details. Apologizes for disturbance and closes call. | `unverified_identity_terminated` | **PASS** |
| **TC-ROUTE-07**<br>`test_identity_unverified_loop` | "Who is this?" | Stays in `GREETING_AND_IDENTIFICATION` | Explains caller identity and re-confirms whether speaking with intended customer. | `in_progress` | **PASS** |
| **TC-ROUTE-08**<br>`test_vague_answer_triggers_clarification` | "I only have photocopies of the registry right now." | Flags `needs_clarification=True` on Documents | Clarifies that physical original documents are mandatory; asks if originals can be produced. | `in_progress` | **PASS** |
| **TC-ROUTE-09**<br>`test_silence_or_unintelligible_repeats_question` | "umm... hmm..." | Retains current target field | Politely states didn't catch that, and repeats the pending question. | `in_progress` | **PASS** |
| **TC-ROUTE-10**<br>`test_skipped_unanswered_field_is_revisited` | Customer asks about processing charges instead of answering Q1. | Retains Q1 as earliest unanswered | Answers product question without hallucination, then re-prompts Q1 (Property type). | `in_progress` | **PASS** |
| **TC-ROUTE-11**<br>`test_disqualified_customer_never_marked_qualified` | Customer disqualified for agriculture asks: "Wait, what about my 50 lakhs loan?" | Stays in `DISQUALIFIED` | Retains terminal state; rejects subsequent qualification attempts. | `disqualified_agricultural` | **PASS** |
| **TC-ROUTE-12**<br>`test_transfer_referral_never_marked_as_fresh_loan` | Customer requests transfer of existing loan. | Retains `LOAN_TRANSFER_REFERRAL` | Does not mark as fresh-loan qualification; remains transfer referral. | `loan_transfer_referral` | **PASS** |
| **TC-ROUTE-13**<br>`test_handoff_gate_blocks_if_field_missing` | Customer answers Q1, Q2, Q3, Q4, but Q5, Q6, Q7 remain unanswered. | `_evaluate_handoff_gate()` returns `False` | Handoff is strictly blocked until all 7 fields pass. | `in_progress` | **PASS** |

---

## 4. Parameterized Boundary Test Execution

### Loan Amount Boundary Matrix
| Input Amount | Normalized INR Value | Expected Validity | Test Status |
| :--- | :--- | :--- | :--- |
| `"74,99,999"` | 7,499,999 | **True** (Within <= 75 Lakhs) | **PASS** |
| `"75,00,000"` | 7,500,000 | **True** (Exact cap boundary) | **PASS** |
| `"75,00,001"` | 7,500,001 | **False** (Exceeds cap, triggers negotiation) | **PASS** |
| `"80,00,000"` | 8,00,000 | **False** (Exceeds cap, triggers negotiation) | **PASS** |

### Repayment Tenure Boundary Matrix
| Input Tenure | Normalized Years | Expected Validity | Test Status |
| :--- | :--- | :--- | :--- |
| `"2 years"` | 2 | **False** (Below minimum, triggers negotiation) | **PASS** |
| `"3 years"` | 3 | **True** (Exact minimum boundary) | **PASS** |
| `"10 years"` | 10 | **True** (Permitted range) | **PASS** |
| `"15 years"` | 15 | **True** (Exact maximum boundary) | **PASS** |
| `"16 years"` | 16 | **False** (Above maximum, triggers negotiation) | **PASS** |
