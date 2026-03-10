import os

from fastapi import FastAPI, HTTPException
from typing import Dict, Any
import uvicorn
from agents.orchestrator.Orchestrator import Orchestrator
from fastapi import WebSocket, WebSocketDisconnect
from agents.orchestrator.Orchestrator import WebSocketManager
from pydantic import BaseModel
import json
import asyncio
import json

app = FastAPI(title="Orchestrator Service")

config = {
    "enable_auto_remediation": True, #change to True to enable auto remediation
    "detector_service_url": "http://detector:8001",
    "rca_service_url": "http://rca_brain:8002",
    "fixer_service_url": "http://fixer:8003",
    "email_enabled": True,
    "email_sender": "niruponpal2003@gmail.com",
    "email_password": os.getenv("EMAIL_APP_PASSWORD", ""),
    "email_receiver": "niruponpal@gmail.com"
}


orchestrator = Orchestrator(config=config)

@app.get("/")
async def health():
    return {
        "status": "ok",
        "service": "orchestrator",
        "config": config
    }

@app.post("/anomaly")
async def receive_anomaly(payload: Dict[str, Any]):
    """
    Receives anomaly payload from detector service
    """

    try:
        print("RECEIVED:", payload)
        result = await orchestrator.process_telemetry(payload)
        

        return {
                "status": "accepted",
                "orchestrator_response": result,
                
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

    

ws_manager = WebSocketManager(buffer_size=5000)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await asyncio.sleep(60)  # keep alive
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)


from pydantic import BaseModel
from datetime import datetime

class EventIn(BaseModel):
    type: str
    data: Dict[str, Any]

@app.post("/internal/event")
async def receive_event(event: EventIn):
    print(f"RECEIVED EVENT: {event}")

    await ws_manager.emit(
        event.model_dump(mode="json")  
    )

    return {"status": "ok"}

@app.get("/status")
async def status():
    return orchestrator.get_status()


@app.get("/incidents")
async def list_incidents():
    """
    Return all active incidents tracked by the orchestrator.
    Used by the SuperCloud Console frontend.
    """
    incidents = orchestrator.active_incidents
    result = []
    for incident_id, inc in incidents.items():
        params = inc.get("detection_result", {}).get("parameters", {})
        logs_for_rca = params.get("logs_for_rca", [])
        first_log = logs_for_rca[0] if logs_for_rca else {}
        result.append({
            "incident_id":    incident_id,
            "state":          inc.get("state"),
            "detection_time": inc.get("detection_time"),
            "severity":       params.get("severity", "unknown"),
            "reason":         params.get("reason", ""),
            "log_count":      len(logs_for_rca),
            "first_message":  first_log.get("message", ""),
            "issue_type":     inc.get("rca_result", {}).get("parameters", {}).get("issue_type", "pending"),
            "rca_allowed":    inc.get("rca_result", {}).get("action") == "rca_complete",
        })
    # Most recent first
    result.sort(key=lambda x: x["detection_time"], reverse=True)
    return result


@app.get("/metrics")
async def get_metrics():
    """
    Return a simple per-incident metrics summary.
    """
    incidents = orchestrator.active_incidents
    metrics = []
    for incident_id, inc in incidents.items():
        metrics.append({
            "incident_id":    incident_id,
            "state":          inc.get("state"),
            "detection_time": inc.get("detection_time"),
            "service":        "mern-backend",
            "severity":       inc.get("detection_result", {}).get("parameters", {}).get("severity", "unknown"),
            "cpu":            0,
            "memory":         0,
        })
    return metrics

if __name__ == "__main__":
    uvicorn.run(
        "orchestrator_service:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )
