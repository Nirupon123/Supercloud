import os
import json
import subprocess
from typing import Dict, Any, List
from agents.base_agent import BaseAgent

base_dir = os.path.dirname(os.path.abspath(__file__))
# Shares the same rulebook.json as the RCA brain
rulebook_path = os.path.join(base_dir, "..", "rca_brain", "rulebook.json")

DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"


class FixerAgent(BaseAgent):

    def __init__(self, agent_id: str):
        super().__init__(agent_id, "fixer")

        with open(rulebook_path) as f:
            self.rulebook = json.load(f)

        print(f"[fixer] Loaded rulebook. DRY_RUN={DRY_RUN}")
        print(f"[fixer] Known issues: {list(self.rulebook['issues'].keys())}")


    async def get_action(self, payload: Dict[str, Any]) -> Dict[str, Any]:

        incident_id = payload.get("incident_id", "unknown")
        issue_type  = payload.get("issue_type")
        target      = payload.get("target", {})

        print(f"\n[fixer] Received fix request — incident={incident_id} issue={issue_type} target={target}")

        if not issue_type or issue_type == "none":
            return {
                "status":  "skipped",
                "reason":  "no issue_type provided",
                "actions_taken": []
            }

        issue_def = self.rulebook.get("issues", {}).get(issue_type)
        if not issue_def:
            return {
                "status":  "skipped",
                "reason":  f"issue_type '{issue_type}' not in rulebook",
                "actions_taken": []
            }

        steps = sorted(issue_def.get("steps", []), key=lambda s: s.get("priority", 99))
        actions_taken = []

        for step in steps:
            action_name    = step.get("action")
            action_def     = self.rulebook.get("actions", {}).get(action_name, {})
            cmd_template   = action_def.get("command_template", [])
            allowed_params = action_def.get("allowed_params", [])

            # Resolve template placeholders from target dict
            cmd = []
            for part in cmd_template:
                resolved = part
                for param in allowed_params:
                    if f"{{{param}}}" in part:
                        value = target.get(param, f"<{param}-unknown>")
                        resolved = resolved.replace(f"{{{param}}}", str(value))
                cmd.append(resolved)

            result_entry = {
                "action":   action_name,
                "command":  " ".join(cmd),
                "dry_run":  DRY_RUN,
                "exit_code": None,
                "output":   None,
            }

            if DRY_RUN:
                print(f"[fixer][DRY_RUN] Would execute: {' '.join(cmd)}")
                result_entry["exit_code"] = 0
                result_entry["output"]    = f"DRY_RUN — command not executed: {' '.join(cmd)}"
            else:
                try:
                    print(f"[fixer][LIVE] Executing: {' '.join(cmd)}")
                    proc = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=60
                    )
                    result_entry["exit_code"] = proc.returncode
                    result_entry["output"]    = (proc.stdout or proc.stderr or "").strip()
                    print(f"[fixer] exit={proc.returncode} output={result_entry['output'][:200]}")
                except Exception as e:
                    result_entry["exit_code"] = -1
                    result_entry["output"]    = f"Exception: {e}"
                    print(f"[fixer] Command failed: {e}")

            actions_taken.append(result_entry)

            # Stop on first failure if global policy says so
            global_policy = self.rulebook.get("global_policy", {})
            if global_policy.get("stop_execution_on_failure") and result_entry["exit_code"] != 0:
                print(f"[fixer] Stopping execution due to failure (stop_execution_on_failure=true)")
                break

        overall_status = "success" if all(a["exit_code"] == 0 for a in actions_taken) else "failed"

        print(f"[fixer] Done — status={overall_status} actions={len(actions_taken)}")

        return {
            "status":       overall_status,
            "incident_id":  incident_id,
            "issue_type":   issue_type,
            "actions_taken": actions_taken,
        }
