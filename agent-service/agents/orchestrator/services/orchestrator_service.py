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

if __name__ == "__main__":
    uvicorn.run(
        "orchestrator_service:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )
