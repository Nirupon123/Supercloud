from agents.base_agent import BaseAgent
from typing import Dict, Any, List
from groq import Groq
import os
import json


class DetectorAgent(BaseAgent):

    def __init__(self, agent_id: str):
        super().__init__(agent_id, "detector")
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))


    async def get_action(self, telemetry_payload: Dict[str, Any]) -> Dict[str, Any]:

        logs = telemetry_payload.get("logs", {}).get("logs", [])

        if not logs:
            return self.no_action_response()

        triage_result = self.llm_log_triage(logs)

        rca_logs     = triage_result["rca_logs"]      # full log objects
        ignored_logs = triage_result["ignored_logs"]

        if not rca_logs:
            return {
                "action": "no_issue",
                "parameters": {
                    "ignored_logs": ignored_logs
                }
            }

        return {
            "action": "trigger_rca",
            "parameters": {
                "logs_for_rca": rca_logs,    # only the truly problematic ones
                "ignored_logs": ignored_logs,
                "reason": "Detector Agent detected potential incidents"
            }
        }


    def llm_log_triage(self, logs: List[Dict[str, Any]]):

        # Build indexed entries so the LLM can reference back by index
        log_entries = [
            {
                "index":    i,
                "message":  log["message"],
                "severity": log.get("severity", "UNKNOWN"),
            }
            for i, log in enumerate(logs)
        ]

        prompt = f"""You are an AIOps incident triage agent. Your ONLY job is to identify
logs that indicate a REAL system incident requiring root cause analysis.

Be STRICT. Only flag logs that clearly describe a system failure or degradation.

Logs (JSON):
{json.dumps(log_entries, indent=2)}

RELEVANT for RCA — flag these:
- High latency / slow responses (e.g. "latency: 2000ms", "response time exceeded threshold")
- Memory leaks or OOM (e.g. "memory leak", "OOMKilled", "heap exhausted")
- Service / pod crashes or restarts (e.g. "CrashLoopBackOff", "container exited with code 1")
- Network spikes or connection failures (e.g. "connection refused", "timeout", "unreachable", "packet loss")
- Database or dependency failures (e.g. "DB connection failed", "redis unavailable", "downstream 503")
- Error rate spikes (e.g. "error rate 45%", "500 errors spiking")
- Disk / resource exhaustion (e.g. "disk full", "CPU at 99%", "no space left on device")

NOT RELEVANT — ignore these completely:
- Cache HIT / Cache SET / Cache MISS (routine cache activity, NOT an error)
- "Fetched N products" or similar fetch completion messages
- Normal GET / POST request logs
- Application startup, info, or debug messages
- AIOps simulation test messages that describe TEST setup, not a real degradation

Return ONLY valid JSON — no markdown, no code fences, no explanation outside the JSON:
{{
  "results": [
    {{
      "index": <original index integer>,
      "relevant_for_rca": true or false,
      "reason": "one-sentence explanation"
    }}
  ]
}}"""

        response = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a strict AIOps triage agent. Return only valid JSON with no markdown."},
                {"role": "user",   "content": prompt}
            ],
            temperature=0,
            max_completion_tokens=1024,
            top_p=1,
            stream=False
        )

        result_text = response.choices[0].message.content.strip()

        # Strip markdown code fences if model wraps the JSON
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]

        try:
            result_json = json.loads(result_text)
        except Exception as e:
            print(f"[detector] JSON parse error: {e}. Sending no logs to RCA.")
            return {"rca_logs": [], "ignored_logs": [log["message"] for log in logs]}

        rca_logs     = []
        ignored_logs = []

        for r in result_json.get("results", []):
            idx = r.get("index")
            if idx is None or idx >= len(logs):
                continue
            full_log = logs[idx]   # preserves: timestamp, message, severity
            if r.get("relevant_for_rca"):
                rca_logs.append({
                    "timestamp": full_log.get("timestamp"),
                    "message":   full_log.get("message"),
                    "severity":  full_log.get("severity", "UNKNOWN"),
                    "reason":    r.get("reason", ""),
                })
            else:
                ignored_logs.append(full_log.get("message"))

        return {
            "rca_logs":    rca_logs,
            "ignored_logs": ignored_logs,
        }


    def no_action_response(self):
        return {
            "action": "collect_more_logs",
            "parameters": {
                "interval": "30s"
            }
        }