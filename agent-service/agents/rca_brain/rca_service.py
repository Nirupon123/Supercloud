from fastapi import FastAPI, HTTPException
from typing import Dict, Any
import uvicorn

from .rca import  RCABrainAgent

app = FastAPI()
rca_agent = RCABrainAgent(agent_id="rca-service-001")


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "rca_brain"}


@app.post("/analyze")
async def analyze(telemetry_payload: Dict[str, Any]):
    """
    Receives full incident telemetry payload from orchestrator
    and performs LLM-based RCA.
    """
    try:
        result = await rca_agent.get_action(telemetry_payload)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(
        "rca_service:app",
        host="0.0.0.0",
        port=8002,
        reload=True
    )
