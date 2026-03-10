import requests

ORCHESTRATOR = "http://localhost:8000"
DETECTOR = "http://localhost:8001"
RCA = "http://localhost:8002"
FIXER = "http://localhost:8003"

def get_incidents():

    try:
        r = requests.get(f"{ORCHESTRATOR}/incidents")
        return r.json()
    except:
        return []

def get_metrics():

    try:
        r = requests.get(f"{ORCHESTRATOR}/metrics")
        return r.json()
    except:
        return []

def run_remediation(service):

    try:
        r = requests.post(f"{FIXER}/fix", json={"service": service})
        return r.json()
    except:
        return {"status": "failed"}

def get_rca(incident):

    try:
        r = requests.post(f"{RCA}/analyze", json=incident)
        return r.json()
    except:
        return {"rca": "unavailable"}