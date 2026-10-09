"""One-click deployment script to create Retell AI voice agent and generate live call link."""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

from src.retell_client import RetellClient
from src.models import RuntimeVariables


def main():
    api_key = os.getenv("RETELL_API_KEY")
    if len(sys.argv) > 1:
        api_key = sys.argv[1].strip()

    if not api_key:
        print("=" * 60)
        print("RETELL AI DEPLOYMENT")
        print("=" * 60)
        print("No RETELL_API_KEY detected in .env or arguments.")
        print("Usage:")
        print("  python deploy_retell.py <YOUR_RETELL_API_KEY>")
        print("or add it to your .env file:")
        print("  RETELL_API_KEY=key_xxxxxxxxxxxxxxxx")
        print("=" * 60)
        sys.exit(1)

    print("Deploying Home Credit LAP Voice Agent (Lead: Priya) to Retell AI...")
    client = RetellClient(api_key=api_key)
    try:
        vars = RuntimeVariables(agent_name="Priya", agent_gender="Female")
        result = client.deploy_full_agent(variables=vars)
        print("\n" + "=" * 60)
        print("DEPLOYMENT SUCCESSFUL!")
        print("=" * 60)
        print(f"Agent ID        : {result['agent_id']}")
        print(f"LLM ID          : {result['llm_id']}")
        print(f"Call ID         : {result['call_id']}")
        print(f"Public Call Link: {result['public_call_url']}")
        print("=" * 60)
    except Exception as e:
        print(f"\n[ERROR] Deployment failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
