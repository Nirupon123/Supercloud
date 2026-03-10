import requests
import json
import websocket   # pip install websocket-client

ORCHESTRATOR = "http://localhost:8000"
DETECTOR     = "http://localhost:8001"
RCA          = "http://localhost:8002"
FIXER        = "http://localhost:8003"
OPA          = "http://localhost:8181"


# ── Incidents ────────────────────────────────────────────────────────────────
def get_incidents():
    try:
        r = requests.get(f"{ORCHESTRATOR}/incidents", timeout=5)
        return r.json()
    except Exception as e:
        return [{"error": str(e)}]


# ── Metrics ──────────────────────────────────────────────────────────────────
def get_metrics():
    try:
        r = requests.get(f"{ORCHESTRATOR}/metrics", timeout=5)
        return r.json()
    except Exception as e:
        return []


# ── RCA  (manual trigger from frontend) ──────────────────────────────────────
def get_rca(incident: dict):
    try:
        r = requests.post(f"{RCA}/analyze", json=incident, timeout=30)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


# ── Fixer (manual trigger from frontend) ─────────────────────────────────────
def run_remediation(incident_id: str, issue_type: str, container_name: str):
    payload = {
        "incident_id": incident_id,
        "issue_type":  issue_type,
        "target": {
            "environment":    "docker",
            "container_name": container_name,
        }
    }
    try:
        r = requests.post(f"{FIXER}/fix", json=payload, timeout=30)
        return r.json()
    except Exception as e:
        return {"status": "failed", "error": str(e)}


# ── OPA policy check (manual) ────────────────────────────────────────────────
def check_opa_policy(issue_type: str, environment: str, confidence: float):
    try:
        r = requests.post(
            f"{OPA}/v1/data/rca/allow",
            json={"input": {
                "issue_type":  issue_type,
                "environment": environment,
                "confidence":  confidence,
            }},
            timeout=5
        )
        result = r.json().get("result", False)
        return {"allowed": result, "issue_type": issue_type, "environment": environment, "confidence": confidence}
    except Exception as e:
        return {"error": str(e)}


# ── Orchestrator status ───────────────────────────────────────────────────────
def get_pipeline_status():
    services = {
        "orchestrator": f"{ORCHESTRATOR}/",
        "detector":     f"{DETECTOR}/health",
        "rca_brain":    f"{RCA}/health",
        "fixer":        f"{FIXER}/health",
        "opa":          f"{OPA}/health",
    }
    statuses = {}
    for name, url in services.items():
        try:
            r = requests.get(url, timeout=3)
            statuses[name] = "🟢 online" if r.status_code == 200 else f"🔴 {r.status_code}"
        except:
            statuses[name] = "🔴 offline"
    return statuses


# ── Live pipeline event stream (reads WS buffer via HTTP poll) ────────────────
def poll_pipeline_events(last_n: int = 20):
    """
    The orchestrator's WebSocket replays buffered events.
    We use a synchronous WS client to collect them quickly and return as text.
    """
    events = []
    try:
        ws = websocket.create_connection("ws://localhost:8000/ws", timeout=3)
        import time; deadline = time.time() + 2
        while time.time() < deadline:
            try:
                ws.settimeout(0.5)
                msg = ws.recv()
                events.append(json.loads(msg))
            except:
                break
        ws.close()
    except Exception as e:
        return f"WebSocket unavailable: {e}"

    if not events:
        return "No events yet — trigger an incident from the MERN app."

    lines = []
    for e in events[-last_n:]:
        t = e.get("data", {}).get("timestamp") or e.get("timestamp", "")
        etype = e.get("type", "event")
        data  = json.dumps(e.get("data", e), indent=2)
        lines.append(f"─── {etype} {t} ───\n{data}\n")
    return "\n".join(lines)