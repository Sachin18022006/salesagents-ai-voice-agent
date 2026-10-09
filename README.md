# Home Credit Loan Against Property (LAP) — AI Voice Agent

[![Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)
[![Tests Passing](https://img.shields.io/badge/tests-98%2F98%20passing-brightgreen.svg)]()
[![Platform: Retell AI & Bolna](https://img.shields.io/badge/voice--platform-Retell%20AI%20%7C%20Bolna-orange.svg)]()

Production-ready conversational AI voice agent engineered for **Home Credit** to qualify existing valued customers for a pre-approved **Loan Against Property (LAP)** offer of up to **₹75,00,000 (75 Lakhs)**.

Built to exact hiring assignment specifications for the **SalesAgents AI Intern — Prompt Engineer** role.

---

## 1. Project Directory Structure

```text
salesagents-ai-voice-agent/
├── README.md                          # Master project documentation & execution guide
├── .env.example                       # Template environment configuration (no secrets)
├── .gitignore                         # Strict exclusion of cache, secrets, and environment files
├── docs/
│   ├── requirements-checklist.md      # Full requirement-to-implementation-to-test mapping
│   ├── system-prompt.md               # Complete, ready-to-paste production system prompt
│   ├── conversation-flows.md          # State machine architecture & Mermaid flow diagrams
│   ├── test-cases.md                  # Comprehensive test scenarios & verification report
│   ├── sample-transcripts.md          # Clearly labeled simulated multi-turn transcripts
│   └── submission-checklist.md       # Final submission audit, decisions & recording guide
├── src/
│   ├── __init__.py                    # Package initialization
│   ├── models.py                      # Pydantic data models, enums & state definitions
│   ├── normalizers.py                 # Indian currency, tenure, property & document parsers
│   ├── extractor.py                   # Out-of-order multi-fact extractor & intent classifier
│   ├── state_machine.py               # Deterministic conversation state machine & gates
│   ├── prompt_builder.py              # Prompt renderer supporting all 11 runtime variables
│   ├── simulator.py                   # Interactive terminal CLI & batch dialogue simulator
│   ├── retell_client.py               # Retell AI REST API client & agent payload exporter
│   └── web_server.py                  # FastAPI REST server, Retell webhook & web simulator UI
└── tests/
    ├── __init__.py
    ├── test_normalizers.py            # Unit tests for financial & criteria normalization
    ├── test_extractor.py              # Tests for out-of-order multi-fact extraction
    ├── test_state_machine.py          # 1:1 tests for all positive, disqualification & routing flows
    └── test_prompt_builder.py         # Tests for all 11 runtime prompt variables
```

---

## 2. Key Architecture & Features

### A. All 11 Mandatory Runtime Variables Supported
1. `{{company_name}}` — Home Credit
2. `{{customer_name}}` — Customer full name
3. `{{agent_name}}` — AI assistant identity (e.g., Priya)
4. `{{agent_gender}}` — Strictly adheres to gendered grammar (especially in Hindi: "bol rahi hoon" vs "bol raha hoon")
5. `{{current_date}}` — Runtime date context
6. `{{current_day}}` — Runtime day context
7. `{{current_time}}` — Runtime time context (drives greeting salutation)
8. `{{additional_context_from_rag}}` — Verified RAG product knowledge
9. `{{language_to_speak}}` — Configured language (English or Hindi)
10. `{{conversation_history}}` — Formatted multi-turn chat memory
11. `{{customer_utterance}}` — Customer's latest speech turn

### B. 7-Point Mandatory Eligibility Checklist
Preserves the required sequence while implementing the **Critical Memory Rule**:
- **Q1 Property Type**: Residential, Commercial, Industrial are **Eligible**; Agricultural is **Immediately Disqualified**.
- **Q2 Ownership Status**: Sole or Joint ownership are both **Eligible**.
- **Q3 Original Documents**: Original documents available is **Eligible**; Unavailable is **Immediately Disqualified**; Photocopies/scans trigger immediate clarification.
- **Q4 Requested Loan Amount**: Up to ₹75,00,000. If > ₹75 Lakhs, negotiates cap; customer agreement proceeds, refusal disqualifies.
- **Q5 Occupation & Income Mode**: Salaried / Self-Employed with **Bank** income is **Eligible**; **Cash** income is **Immediately Disqualified**.
- **Q6 Property Market Value**: Estimates captured and normalized without inventing unsupported LTV formulas.
- **Q7 Requested Tenure**: 3 to 15 years (inclusive) is **Eligible**; out-of-range values negotiate; refusal disqualifies.

### C. Out-of-Order Memory & Information Extraction
When customers volunteer multiple facts in one sentence (e.g., *"I need 30 lakhs against my 80-lakh flat, and salary is in bank"*), the extraction engine records all facts into structured state immediately and skips asking those questions later.

### D. Priority Routing & Strict Gates
- **High-Priority Loan Transfer**: Mentions of existing loans or reducing EMI immediately transfer the customer to a Loan Transfer specialist (`loan_transfer_referral`), bypassing the fresh-loan checklist.
- **Strict Handoff Gate**: Qualification (`qualified_handoff`) occurs **only** when all 7 fields are captured, verified valid, and all eligibility criteria pass.
- **Terminal State Isolation**: Once a call reaches a terminal outcome (disqualified, transfer, refusal, busy), subsequent turns cannot accidentally re-open qualification.

---

## 3. Quick Start & Execution

### Prerequisites
- Python 3.10+ (Tested on Python 3.14)
- (Optional) Retell AI account for live voice testing

### Installation
```bash
# Clone or navigate to the project directory
cd salesagents-ai-voice-agent

# Install dependencies
pip install -r requirements.txt # or: pip install pytest fastapi uvicorn pydantic requests python-dotenv
```

### Running Automated Tests
```bash
# Run the complete test suite (98 tests)
python -m pytest -v
```

### Running the Interactive CLI Simulator
Test conversations interactively in your terminal with colored logs and real-time state tracking:
```bash
python -m src.simulator
```

### Running the Local Web UI Simulator & API Server
```bash
python -m uvicorn src.web_server:app --reload --port 8000
```
Open [http://localhost:8000](http://localhost:8000) in your browser to interact with the voice qualification agent.

---

## 4. Voice Platform Integration (Retell AI & Bolna)

### Live Retell AI Deployment Links
- **Agent Name**: `Home Credit LAP - Priya`
- **Agent ID**: `agent_5753219f81a13cac53ddfb266c`
- **LLM Engine ID**: `llm_7e15ff1dd281c9c3863c8a85972b`
- **Voice Persona**: `11labs-Monika` (Indian English Female / ElevenLabs)
- **Live Call Link**: [https://beta.retellai.com/call/call_a85dcd5bcdeb845186c5f3f9681](https://beta.retellai.com/call/call_a85dcd5bcdeb845186c5f3f9681)
- **Agent Dashboard**: [https://beta.retellai.com/dashboard/agents/agent_5753219f81a13cac53ddfb266c](https://beta.retellai.com/dashboard/agents/agent_5753219f81a13cac53ddfb266c)

Detailed step-by-step instructions are provided in [docs/submission-checklist.md](file:///C:/Users/sachi/.gemini/antigravity-ide/scratch/salesagents-ai-voice-agent/docs/submission-checklist.md).
