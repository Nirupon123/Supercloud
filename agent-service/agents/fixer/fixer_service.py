from fastapi import FastAPI, HTTPException
from typing import Dict, Any
import uvicorn
from agents.fixer.fixer import FixerAgent

app = FastAPI(title="Fixer Agent Service")

fixer = FixerAgent(agent_id="fixer-001")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "fixer"}


@app.post("/fix")
async def fix(payload: Dict[str, Any]):
    """
    Called by the Orchestrator after RCA brain completes.
    Payload: { incident_id, issue_type, target: {environment, container_name|deployment_name|...} }
    """
    try:
        result = await fixer.get_action(payload)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(
        "fixer_service:app",
        host="0.0.0.0",
        port=8003,
        reload=False
    )
