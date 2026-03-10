import os
import json
import re
import httpx
from typing import Dict, Any
from datetime import datetime, timezone
from dotenv import load_dotenv
from groq import AsyncGroq
from agents.base_agent import BaseAgent

load_dotenv()

base_dir = os.path.dirname(os.path.abspath(__file__))
rulebook_path = os.path.join(base_dir, "rulebook.json")

OPA_URL = os.getenv("OPA_URL", "http://opa:8181/v1/data/rca/allow")


class RCABrainAgent(BaseAgent):

    def __init__(self, agent_id: str):
        super().__init__(agent_id, "rca_brain")

        self.groq_api_key = os.getenv("GROQ_API_KEY")
        if not self.groq_api_key:
            raise ValueError("GROQ_API_KEY not found")

        self.client = AsyncGroq(api_key=self.groq_api_key)

        with open(rulebook_path) as f:
            self.rulebook = json.load(f)

        self.valid_issue_types = list(self.rulebook["issues"].keys())
        print(f"[rca_brain] Loaded rulebook. valid_issue_types={self.valid_issue_types}")
        print(f"[rca_brain] OPA endpoint: {OPA_URL}")


    async def get_action(self, telemetry_payload: Dict[str, Any]) -> Dict[str, Any]:

        incident_id   = telemetry_payload.get("incident_id", "unknown")
        severity      = telemetry_payload.get("severity", "low")
        anomaly_score = telemetry_payload.get("anomaly_score", 0.0)

        context = self.build_investigation_context(telemetry_payload)

        rca_result = await self.perform_llm_reasoning(
            context,
            incident_id,
            severity,
            anomaly_score,
            telemetry_payload
        )

        # Early exit for alert_only (LLM or validation said no)
        if rca_result.get("action") == "alert_only":
            return rca_result

        # ── OPA Guard ────────────────────────────────────────────────────────
        opa_decision = await self._validate_with_opa(rca_result)

        if not opa_decision["allowed"]:
            reason = opa_decision.get("deny_reason", "opa_denied")
            print(f"[rca_brain][OPA] DENIED — {reason}")
            return {
                "action": "alert_only",
                "reason": f"opa_denied: {reason}",
                "rca_details": rca_result
            }

        print(f"[rca_brain][OPA] ALLOWED — proceeding to fixer")
        # ─────────────────────────────────────────────────────────────────────

        return {
            "action":     "rca_complete",
            "parameters": rca_result
        }


    async def _validate_with_opa(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call OPA to validate the RCA result before allowing remediation.
        Returns { allowed: bool, deny_reason: str|None }
        """
        issue_type  = parsed.get("issue_type", "none")
        environment = parsed.get("target", {}).get("environment", "")
        confidence  = parsed.get("confidence", 0.0)

        opa_input = {
            "input": {
                "issue_type":  issue_type,
                "environment": environment,
                "confidence":  confidence
            }
        }

        print(f"[rca_brain][OPA] Checking policy: {opa_input['input']}")

        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.post(OPA_URL, json=opa_input)
                resp.raise_for_status()
                result = resp.json()

            allowed = result.get("result", False)

            # Also fetch deny_reason if denied
            deny_reason = None
            if not allowed:
                try:
                    deny_resp = await client.post(
                        OPA_URL.replace("/allow", "/deny_reason"),
                        json=opa_input,
                        timeout=5
                    )
                    deny_reason = deny_resp.json().get("result", "opa_denied")
                except Exception:
                    deny_reason = "opa_denied"

            return {"allowed": allowed, "deny_reason": deny_reason}

        except Exception as e:
            # OPA unavailable → fail OPEN (allow) with a warning
            print(f"[rca_brain][OPA] WARNING: OPA unreachable ({e}). Failing open.")
            return {"allowed": True, "deny_reason": None}


    def build_investigation_context(self, telemetry_payload: Dict[str, Any]) -> str:

        logs        = telemetry_payload.get("logs", [])
        reason      = telemetry_payload.get("reason", "")
        anomaly_type = telemetry_payload.get("anomaly_type", "unknown")

        if isinstance(logs, dict):
            logs = [logs]

        formatted_logs = "\n".join(
            f"  [{l.get('severity','?')}] {l.get('timestamp','')} — {l.get('message','')} "
            f"(detector reason: {l.get('reason', '')})"
            for l in logs
        ) if logs else "  (no logs)"

        valid_issues = "\n".join([f"- {i}" for i in self.valid_issue_types])

        return f"""
You are analyzing a production incident detected by the AIOps system.

DETECTOR REASON: {reason}

ANOMALY TYPE: {anomaly_type}

INCIDENT LOGS (pre-filtered — only real incidents):
{formatted_logs}

Valid issue_type options:
{valid_issues}

Choose ONLY from the above list.
If none apply, return:
  "issue_type": "none"
  "confidence": 0.0

Classify:
- issue_type
- severity (critical | high | medium | low)
- execution environment (kubernetes | docker | systemd | host)

Return ONLY valid JSON.
"""


    def validate_llm_output(self, parsed: Dict[str, Any]) -> Dict[str, Any] | None:

        issue_type = parsed.get("issue_type")

        if issue_type == "none":
            return {
                "action": "alert_only",
                "reason": "no_matching_rule"
            }

        if issue_type not in self.valid_issue_types:
            print(f"[rca_brain] Invalid issue_type from LLM: {issue_type}")
            return None

        actual_env = parsed.get("target", {}).get("environment", "")
        if not actual_env:
            print("[rca_brain] Missing environment in LLM output")
            return None

        actual_env = actual_env.strip().lower()
        parsed["target"]["environment"] = actual_env

        allowed_envs = ["docker", "kubernetes", "systemd", "host"]
        if actual_env not in allowed_envs:
            print(f"[rca_brain] Invalid environment: {actual_env}")
            return None

        if parsed.get("confidence", 0) < 0.4:
            return {
                "action": "alert_only",
                "reason": "low_confidence"
            }

        return parsed


    def enrich_target_fields(self, parsed: Dict[str, Any], telemetry_payload: Dict[str, Any]):

        target = parsed.get("target", {})
        env    = target.get("environment")

        # Try to extract service name from first log message
        logs = telemetry_payload.get("logs", [])
        if isinstance(logs, list) and logs:
            first_log = logs[0]
            service_name = first_log.get("service", "") or telemetry_payload.get("host", "mern-backend")
        else:
            service_name = telemetry_payload.get("host", "mern-backend")

        if env == "docker":
            target.setdefault("container_name", service_name)

        elif env == "kubernetes":
            target.setdefault("deployment_name", service_name)
            target.setdefault("namespace", "default")

        elif env in ("systemd", "host"):
            target.setdefault("service_name", service_name)

        parsed["target"] = target
        return parsed


    async def perform_llm_reasoning(
        self,
        context: str,
        incident_id: str,
        severity: str,
        anomaly_score: float,
        telemetry_payload: Dict[str, Any]
    ) -> Dict:

        prompt = f"""
You are an AI Root Cause Classification Engine.

{context}

Required schema:

{{
  "version": "2.0",
  "incident_id": "{incident_id}",
  "issue_type": "string",
  "confidence": 0.0,
  "severity": "{severity}",
  "target": {{
      "environment": "kubernetes | docker | systemd | host",
      "deployment_name": "",
      "pod_name": "",
      "container_name": "",
      "service_name": "",
      "namespace": ""
  }},
  "strategy_override": {{
      "replica_count": "",
      "force_restart": "",
      "skip_canary": false
  }},
  "metadata": {{
      "detected_at": "{datetime.now(timezone.utc).isoformat()}",
      "anomaly_score": {anomaly_score},
      "trigger_metric": {{}}
  }}
}}
"""

        try:
            response = await self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=1,
                max_completion_tokens=1024,
                top_p=1,
                stream=False
            )

            content = response.choices[0].message.content.strip()
            cleaned = re.sub(r"<think>[\s\S]*?</think>", "", content).strip()

            start = cleaned.find("{")
            end   = cleaned.rfind("}")

            if start == -1 or end == -1:
                raise ValueError("No JSON found in LLM response")

            parsed = json.loads(cleaned[start:end+1])

            validated = self.validate_llm_output(parsed)

            if not validated:
                return {
                    "action": "alert_only",
                    "reason": "validation_failed"
                }

            enriched = self.enrich_target_fields(validated, telemetry_payload)
            return enriched

        except Exception as e:
            print(f"[rca_brain] LLM reasoning error: {e}")
            return {
                "action": "alert_only",
                "reason": "rca_parse_failed"
            }