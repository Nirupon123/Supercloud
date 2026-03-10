from fastapi import FastAPI, HTTPException
from typing import Dict, Any
import uvicorn

from .detector import DetectorAgent

app = FastAPI()

detector = DetectorAgent(agent_id="detector-service-001")


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "detector"}


@app.post("/detect")
async def detect(telemetry_payload: Dict[str, Any]):
    try:
        print("Received telemetry payload:", telemetry_payload)
        return await detector.get_action(telemetry_payload)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(
        "detector_service:app", host="0.0.0.0", port=8001, reload=True)
