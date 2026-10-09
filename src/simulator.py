"""Interactive and programmatic dialogue simulator for local testing and demonstration."""

import sys
from typing import List, Dict, Any, Tuple

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.models import ConversationSession, RuntimeVariables, CallOutcome, Stage
from src.state_machine import LAPVoiceStateMachine


class DialogueSimulator:
    """Simulates multi-turn conversations between agent and customer."""

    def __init__(self, variables: RuntimeVariables = None):
        self.variables = variables or RuntimeVariables()
        self.sm = LAPVoiceStateMachine(
            ConversationSession(session_id="sim-001", variables=self.variables)
        )
        self.transcript: List[Dict[str, str]] = []

    def start_call(self) -> str:
        greeting = self.sm.get_greeting_message()
        self.transcript.append({"speaker": "Agent", "text": greeting})
        return greeting

    def user_say(self, utterance: str) -> str:
        self.transcript.append({"speaker": "Customer", "text": utterance})
        agent_reply, _ = self.sm.process_turn(utterance)
        self.transcript.append({"speaker": "Agent", "text": agent_reply})
        return agent_reply

    def run_scripted_dialogue(self, customer_utterances: List[str]) -> Tuple[List[Dict[str, str]], ConversationSession]:
        """Runs a sequence of customer utterances through the state machine."""
        self.start_call()
        for u in customer_utterances:
            self.user_say(u)
            # Break early if session reached terminal outcome
            if self.sm.session.outcome != CallOutcome.IN_PROGRESS and self.sm.session.stage not in [Stage.LOAN_AMOUNT_NEGOTIATION, Stage.TENURE_NEGOTIATION]:
                break
        return self.transcript, self.sm.session

    def print_summary(self):
        s = self.sm.session
        print("\n" + "=" * 60)
        print("SIMULATION CONVERSATION SUMMARY")
        print("=" * 60)
        for turn in self.transcript:
            prefix = "[Agent] " if turn["speaker"] == "Agent" else "[Customer] "
            print(f"{prefix}{turn['speaker']}: {turn['text']}")
        print("-" * 60)
        print(f"Final Stage: {s.stage.value}")
        print(f"Final Call Outcome: {s.outcome.value}")
        if s.disqualification_reason:
            print(f"Disqualification Reason: {s.disqualification_reason}")
        if s.callback_preference:
            print(f"Callback Preference: {s.callback_preference}")
        print("\nCaptured Checklist Fields:")
        for name, field in s.checklist.model_dump().items():
            ans = field.get("is_answered")
            val = field.get("parsed_value")
            valid = field.get("is_valid")
            print(f"  * {name:28}: Answered={ans:<5} Valid={valid:<5} Value={val}")
        print("=" * 60 + "\n")


def interactive_cli():
    """Allows running interactive call simulation directly in terminal."""
    print("\n=======================================================")
    print(" Home Credit LAP Voice Agent - Interactive CLI Simulator ")
    print("=======================================================\n")
    sim = DialogueSimulator()
    greeting = sim.start_call()
    print(f"[Agent]: {greeting}\n")

    while True:
        try:
            user_input = input("[Customer]: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit"]:
                break
            reply = sim.user_say(user_input)
            print(f"\n[Agent]: {reply}\n")

            if sim.sm.session.outcome != CallOutcome.IN_PROGRESS and sim.sm.session.stage not in [Stage.LOAN_AMOUNT_NEGOTIATION, Stage.TENURE_NEGOTIATION]:
                print(f"[Call Terminated with Outcome: {sim.sm.session.outcome.value}]")
                break
        except (KeyboardInterrupt, EOFError):
            break

    sim.print_summary()


if __name__ == "__main__":
    interactive_cli()
