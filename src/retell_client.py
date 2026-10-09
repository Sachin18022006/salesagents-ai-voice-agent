"""Retell AI platform integration client and deployment manager."""

import os
import json
from typing import Dict, Any, Optional
import requests
from dotenv import load_dotenv
from src.prompt_builder import get_base_system_prompt_template, render_system_prompt
from src.models import RuntimeVariables

load_dotenv()

RETELL_BASE_URL = "https://api.retellai.com"


class RetellClient:
    """Client for interacting with Retell AI platform APIs."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("RETELL_API_KEY")

    def _headers(self) -> Dict[str, str]:
        if not self.api_key:
            raise ValueError("Retell API Key is required. Set RETELL_API_KEY in environment or .env file.")
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def create_retell_llm(self, prompt: str, begin_message: str, model: str = "gpt-4o") -> Dict[str, Any]:
        """Creates a Retell LLM response engine."""
        url = f"{RETELL_BASE_URL}/create-retell-llm"
        payload = {
            "general_prompt": prompt,
            "begin_message": begin_message,
            "model": model
        }
        res = requests.post(url, headers=self._headers(), json=payload, timeout=20)
        res.raise_for_status()
        return res.json()

    def create_agent(self, llm_id: str, agent_name: str, voice_id: str = "11labs-Adrian") -> Dict[str, Any]:
        """Creates an agent connected to the LLM response engine."""
        url = f"{RETELL_BASE_URL}/create-agent"
        payload = {
            "agent_name": agent_name,
            "voice_id": voice_id,
            "response_engine": {
                "type": "retell-llm",
                "llm_id": llm_id
            },
            "responsiveness": 0.9,
            "interruption_sensitivity": 0.8,
            "enable_backchannel": True,
            "ambient_sound": "office"
        }
        res = requests.post(url, headers=self._headers(), json=payload, timeout=20)
        res.raise_for_status()
        return res.json()

    def create_web_call(self, agent_id: str) -> Dict[str, Any]:
        """Creates an interactive web call session and returns public shareable call identifiers."""
        url = f"{RETELL_BASE_URL}/v2/create-web-call"
        payload = {"agent_id": agent_id}
        res = requests.post(url, headers=self._headers(), json=payload, timeout=15)
        res.raise_for_status()
        data = res.json()
        call_id = data.get("call_id")
        data["public_call_url"] = f"https://beta.retellai.com/call/{call_id}"
        return data

    def deploy_full_agent(self, variables: Optional[RuntimeVariables] = None) -> Dict[str, Any]:
        """Deploys LLM, creates agent, and generates an initial web call session."""
        vars = variables or RuntimeVariables()
        prompt = get_base_system_prompt_template()
        begin_msg = (
            f"Hello, good morning, am I speaking with {vars.customer_name}? "
            f"I'm {vars.agent_name} calling from {vars.company_name}."
        )

        print("[1/3] Creating Retell LLM response engine...")
        llm_data = self.create_retell_llm(prompt=prompt, begin_message=begin_msg)
        llm_id = llm_data["llm_id"]
        print(f"       -> LLM created with ID: {llm_id}")

        print("[2/3] Creating Retell Voice Agent...")
        agent_data = self.create_agent(
            llm_id=llm_id,
            agent_name=f"Home Credit LAP - {vars.agent_name}",
            voice_id="11labs-Adrian" if vars.agent_gender.lower() == "male" else "11labs-Priya-Indian"
        )
        agent_id = agent_data["agent_id"]
        print(f"       -> Agent created with ID: {agent_id}")

        print("[3/3] Generating initial Web Call session...")
        call_data = self.create_web_call(agent_id=agent_id)
        print(f"       -> Call ID: {call_data.get('call_id')}")
        print(f"       -> Public Call Link: {call_data.get('public_call_url')}")

        return {
            "status": "success",
            "agent_id": agent_id,
            "llm_id": llm_id,
            "call_id": call_data.get("call_id"),
            "public_call_url": call_data.get("public_call_url"),
            "access_token": call_data.get("access_token")
        }


if __name__ == "__main__":
    client = RetellClient()
    if client.api_key:
        result = client.deploy_full_agent()
        print("\nDEPOLYMENT RESULT:")
        print(json.dumps(result, indent=2))
    else:
        print("[NOTICE] RETELL_API_KEY is not set.")
        print("Please set your Retell API key in .env or run with your key.")
