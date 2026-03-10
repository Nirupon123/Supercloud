import requests
from config import ORCHESTRATOR_URL


def send_to_detector(log_payload):
    """
    Send telemetry log payload to the Orchestrator entry-point.
    The orchestrator drives: detector → rca_brain (OPA guard) → fixer.
    """
    try:
        response = requests.post(ORCHESTRATOR_URL, json=log_payload, timeout=30)
        print("\nOrchestrator Response:")
        print(response.json())

    except Exception as e:
        print("Orchestrator request failed:", e)