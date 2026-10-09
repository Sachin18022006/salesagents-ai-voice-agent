"""Tests for prompt builder and runtime variable injection."""

import pytest
from src.prompt_builder import render_system_prompt, get_retell_ai_agent_config
from src.models import RuntimeVariables


def test_runtime_variables_interpolation():
    vars = RuntimeVariables(
        company_name="Home Credit India",
        customer_name="Sunil Verma",
        agent_name="Pooja",
        agent_gender="Female",
        current_date="2026-10-09",
        current_day="Friday",
        current_time="02:30 PM",
        additional_context_from_rag="Special festive interest concessions available on LAP.",
        language_to_speak="Hindi",
        conversation_history=[
            {"speaker": "agent", "text": "Namaste Sunil ji"},
            {"speaker": "customer", "text": "Haan boliye"}
        ],
        customer_utterance="Mera flat hai Pune me"
    )

    prompt = render_system_prompt(vars)

    assert "Home Credit India" in prompt
    assert "Sunil Verma" in prompt
    assert "Pooja" in prompt
    assert "Female" in prompt
    assert "2026-10-09" in prompt
    assert "Friday" in prompt
    assert "02:30 PM" in prompt
    assert "Special festive interest concessions" in prompt
    assert "Hindi" in prompt
    assert "Namaste Sunil ji" in prompt
    assert "Mera flat hai Pune me" in prompt


def test_retell_ai_config_generation():
    config = get_retell_ai_agent_config()
    assert "agent_name" in config
    assert "voice_id" in config
    assert "post_call_analysis_data" in config
    analysis_names = [f["name"] for f in config["post_call_analysis_data"]]
    assert "call_outcome" in analysis_names
    assert "property_type" in analysis_names
    assert "requested_loan_amount" in analysis_names
    assert "requested_tenure_years" in analysis_names
