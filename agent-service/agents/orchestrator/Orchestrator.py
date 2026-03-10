from xmlrpc import server

import httpx
from uuid6 import uuid7
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional, cast
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS


class IncidentState(Enum):
    MONITORING = "monitoring"
    ANOMALY_DETECTED = "anomaly_detected"
    RCA_IN_PROGRESS = "rca_in_progress"
    REMEDIATION_IN_PROGRESS = "remediation_in_progress"
    RESOLVED = "resolved"
    FAILED = "failed"


class Orchestrator:

    def __init__(
        self,
        incident_logger=None,
        config: Optional[Dict[str, Any]] = None,
        websocket_manager=None
    ):
        self.logger = incident_logger
        self.config = self._default_config()
        if config:
            self.config.update(config)

        self.detector_service_url = self.config.get("detector_service_url")
        self.rca_service_url = self.config.get("rca_service_url")
        self.fixer_service_url = self.config.get("fixer_service_url")
        self.websocket_manager = websocket_manager


        self.influx_client = InfluxDBClient(
        url=self.config.get("influx_url"),
        token=self.config.get("influx_token"),
        org=self.config.get("influx_org"))

        self.influx_write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)

        self.active_incidents: Dict[str, Dict[str, Any]] = {}

    def _default_config(self) -> Dict[str, Any]:
        return {
            "enable_auto_remediation": True,
            "detector_service_url": "http://detector:8001",
            "rca_service_url": "http://rca_brain:8002",
            "fixer_service_url": "http://fixer:8003",
            "email_enabled": True,
            "email_sender": "niruponpal2003@gmail.com",
            "email_password": os.getenv("EMAIL_APP_PASSWORD", ""),
            "email_receiver": "niruponpal@gmail.com",

            
             "influx_url": "http://influxdb:8086",
            "influx_token": os.getenv("INFLUX_TOKEN", ""),
            "influx_org": "supercloud",
            "influx_bucket": "incidents",


        }

    async def process_telemetry(self, telemetry_payload: Dict[str, Any]) -> Dict[str, Any]:

        detection_result = await self._run_detection(telemetry_payload)
        print("DETECTION RESULT:", detection_result)

        action = detection_result.get("action")

        # Detector returns 'trigger_rca' when it finds real incidents
        if action == "trigger_rca":
            await self._handle_incident(detection_result, telemetry_payload)
        else:
            print(f"[Orchestrator] No incident — detector action: {action}")

        return {
            "status": "processed",
            "action": action,
            "parameters": detection_result.get("parameters", {})
        }

    async def _run_detection(self, telemetry_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.detector_service_url}/detect",
                    json=telemetry_data,
                    timeout=10
                )
                response.raise_for_status()
                return response.json()

        except Exception as e:
            print(f"[Orchestrator] Detector service error: {e}")
            return {"action": "error", "error": str(e)}

    async def _handle_incident(
        self,
        detection_result: Dict[str, Any],
        telemetry_data: Dict[str, Any]
    ):

        # UUID7
        incident_id = str(uuid7())

        print(f"\n[Orchestrator] INCIDENT DETECTED: {incident_id}\n")

        incident_record = {
            "incident_id": incident_id,
            "state": IncidentState.ANOMALY_DETECTED.value,
            "detection_time": datetime.now(timezone.utc).isoformat(),
            "detection_result": detection_result,
            "telemetry_snapshot": telemetry_data,
            "timeline": []
        }

        self.active_incidents[incident_id] = incident_record

        # detector action is already 'trigger_rca' — go straight to RCA
        await self._run_rca_pipeline(incident_id)

    async def _run_rca_pipeline(self, incident_id: str):

        incident = self.active_incidents[incident_id]
        incident["state"] = IncidentState.RCA_IN_PROGRESS.value

        # Pull the filtered logs the detector already triaged as incident-worthy
        params = cast(Dict[str, Any], incident.get("detection_result", {}).get("parameters", {}))
        logs_for_rca = params.get("logs_for_rca", [])
        reason      = params.get("reason", "")

        rca_state = {
            "incident_id": incident_id,
            "severity":    params.get("severity", "unknown"),
            "anomaly_score": 0.0,
            # Send only the pre-filtered incident logs — not the full raw snapshot
            "logs": logs_for_rca,
            "reason": reason,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.rca_service_url}/analyze",
                    json=rca_state,
                    timeout=20
                )
                response.raise_for_status()
                rca_result = response.json()

            print(f"[Orchestrator RCA RESULT] {incident_id}:\n", rca_result)

            incident["rca_result"] = rca_result

            if self.config.get("enable_auto_remediation"):
                await self._run_remediation(incident_id)
            else:
                incident["state"] = IncidentState.RESOLVED.value
                await self._log_incident(incident_id)

        except Exception as e:
            print(f"[Orchestrator] RCA service error:\n{e}")
            incident["state"] = IncidentState.FAILED.value
            await self._log_incident(incident_id)

    async def _alert_only(self, incident_id: str):
        await self._log_incident(incident_id)

    async def _log_incident(self, incident_id: str):

        incident = self.active_incidents.get(incident_id)
        if not incident:
            return

        print(f"[Orchestrator] Logging incident {incident_id}")

  
        try:
            severity = incident.get("detection_result", {}).get("parameters", {}).get("severity", "UNKNOWN")
            anomaly_score = incident.get("detection_result", {}).get("parameters", {}).get("anomaly_score", 0)

            metrics = incident.get("telemetry_snapshot", {}).get("metrics", {})

            point = (
                Point("supercloud_incidents")
                .tag("incident_id", incident_id)
                .tag("severity", severity)
                .field("anomaly_score", float(anomaly_score))
                .field("cpu_percent", float(metrics.get("cpu", {}).get("cpu_percent", 0)))
                .field("memory_percent", float(metrics.get("memory", {}).get("used_percent", 0)))
                .field("disk_percent", float(metrics.get("disk", {}).get("used_percent", 0)))
                .time(datetime.now(timezone.utc).isoformat(), WritePrecision.NS)
            )

            self.influx_write_api.write(
                bucket=self.config.get("influx_bucket"),
                org=self.config.get("influx_org"),
                record=point
            )

            print("[Orchestrator] Incident written to InfluxDB")

        except Exception as e:
            print("[Orchestrator] Influx write failed:", e)


        # send email
        await self._send_incident_email(incident)

    async def _send_incident_email(self, incident: Dict[str, Any]):

        if not self.config.get("email_enabled", False):
            print("Email disabled")
            return

        sender = self.config.get("email_sender")
        password = self.config.get("email_password")
        receiver = self.config.get("email_receiver")

        if not password:
            print("EMAIL PASSWORD EMPTY")
            return

        try:
            severity = incident.get("detection_result", {}).get("parameters", {}).get("severity", "UNKNOWN")
            anomaly_score = incident.get("detection_result", {}).get("parameters", {}).get("anomaly_score", 0)

            metrics = incident.get("telemetry_snapshot", {}).get("metrics", {})
            logs = incident.get("telemetry_snapshot", {}).get("logs", {})
            rca = incident.get("rca_result", {})

            severity_color = {
            "CRITICAL": "#dc3545",
            "HIGH": "#fd7e14",
            "MEDIUM": "#ffc107",
            "LOW": "#28a745"
            }.get(severity.upper(), "#6c757d")

            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[SuperCloud Alert] {severity} Incident {incident['incident_id']}"
            msg["From"] = sender
            msg["To"] = receiver

            html_content = f"""
        <html>
        <head>
          <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #f4f6f9;
                margin: 0;
                padding: 0;
            }}
            .container {{
                max-width: 800px;
                margin: 20px auto;
                background: #ffffff;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.08);
                padding: 30px;
            }}
            .header {{
                border-bottom: 2px solid #eee;
                padding-bottom: 15px;
                margin-bottom: 20px;
            }}
            .severity {{
                display: inline-block;
                padding: 6px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: bold;
                color: white;
                background-color: {severity_color};
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
            }}
            table th, table td {{
                border: 1px solid #eee;
                padding: 8px;
                text-align: left;
                font-size: 13px;
            }}
            table th {{
                background-color: #f8f9fa;
            }}
            .section {{
                margin-top: 25px;
            }}
            .footer {{
                margin-top: 30px;
                font-size: 12px;
                color: #888;
                text-align: center;
                border-top: 1px solid #eee;
                padding-top: 15px;
            }}
          </style>
        </head>
        <body>
          <div class="container">

            <div class="header">
              <h2> SuperCloud Incident Report</h2>
              <p><span class="severity">{severity}</span></p>
            </div>

            <div class="section">
              <h3> Incident Summary</h3>
              <table>
                <tr><th>Incident ID</th><td>{incident['incident_id']}</td></tr>
                <tr><th>Status</th><td>{incident['state']}</td></tr>
                <tr><th>Detected At</th><td>{incident['detection_time']}</td></tr>
                <tr><th>Anomaly Score</th><td>{anomaly_score}</td></tr>
              </table>
            </div>

            <div class="section">
              <h3> System Metrics Snapshot</h3>
              <table>
                <tr><th>CPU Usage</th><td>{metrics.get("cpu", {}).get("cpu_percent", "N/A")} %</td></tr>
                <tr><th>Memory Usage</th><td>{metrics.get("memory", {}).get("used_percent", "N/A")} %</td></tr>
                <tr><th>Disk Usage</th><td>{metrics.get("disk", {}).get("used_percent", "N/A")} %</td></tr>
                <tr><th>Network RX</th><td>{metrics.get("network", {}).get("rx_bytes_per_sec", "N/A")}</td></tr>
                <tr><th>Network TX</th><td>{metrics.get("network", {}).get("tx_bytes_per_sec", "N/A")}</td></tr>
              </table>
            </div>

            <div class="section">
              <h3> Log Trigger</h3>
              <table>
                <tr><th>Service</th><td>{logs.get("service", "N/A")}</td></tr>
                <tr><th>Log Level</th><td>{logs.get("level", "N/A")}</td></tr>
                <tr><th>Message</th><td>{logs.get("message", "N/A")}</td></tr>
              </table>
            </div>

            <div class="section">
        <h3> Root Cause Analysis</h3>
        <table>
            <tr><th>Issue Type</th><td>{rca.get("parameters", {}).get("issue_type", "N/A")}</td></tr>
            <tr><th>Confidence</th><td>{rca.get("parameters", {}).get("confidence", "N/A")}</td></tr>
            <tr><th>Environment</th><td>{rca.get("parameters", {}).get("target", {}).get("environment", "N/A")}</td></tr>
            <tr><th>Container</th><td>{rca.get("parameters", {}).get("target", {}).get("container_name", "N/A")}</td></tr>
            <tr><th>Service</th><td>{rca.get("parameters", {}).get("target", {}).get("service_name", "N/A")}</td></tr>
        </table>
        </div>

            <div class="section">
              <h3> Recommended Developer Actions</h3>
              <ul>
                <li>Review logs around detection timestamp.</li>
                <li>Check service dependencies.</li>
                <li>Inspect recent deployments.</li>
                <li>Monitor CPU / memory patterns.</li>
              </ul>
            </div>

            <div class="footer">
              SuperCloud AIOps Monitoring System<br>
              Automated Detection • RCA • Intelligent Response
            </div>

          </div>
        </body>
        </html>
        """

            msg.attach(MIMEText(html_content, "html"))

            with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as server:
                server.starttls()
                server.login(sender, password)
                server.sendmail(sender, receiver, msg.as_string())

            print("[Orchestrator] Email sent successfully")

        except Exception as e:
            print("[Orchestrator] Email failed:", e)



    async def _run_remediation(self, incident_id: str):

        incident = self.active_incidents[incident_id]
        incident["state"] = IncidentState.REMEDIATION_IN_PROGRESS.value

        rca_result = incident.get("rca_result", {})
        params = rca_result.get("parameters", {})

        fix_payload = {
            "incident_id": incident_id,
            "issue_type": params.get("issue_type"),
            "target": params.get("target", {})
        }

        print(f"[Orchestrator] Triggering Fixer for incident {incident_id}")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.fixer_service_url}/fix",
                    json=fix_payload,
                    timeout=20
                )

                response.raise_for_status()
                fix_result = response.json()

            print(f"[Orchestrator] Fixer result:", fix_result)

            incident["fix_result"] = fix_result

            if fix_result.get("status") == "success":
                incident["state"] = IncidentState.RESOLVED.value
            else:
                incident["state"] = IncidentState.FAILED.value

        except Exception as e:
            print("[Orchestrator] Fixer service error:", e)
            incident["state"] = IncidentState.FAILED.value

        await self._log_incident(incident_id)



# Added by Souherdya - Websocket for UI Updates
# -----------------------------------------------------------------------------


from fastapi import WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
from datetime import datetime, timezone
from collections import deque
import asyncio

class WebSocketManager:
    def __init__(self, buffer_size: int = 5000):
        self.active_connections: List[WebSocket] = []
        self.event_buffer = deque(maxlen=buffer_size)
        self.lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self.lock:
            self.active_connections.append(websocket)
            # Replay buffered events to new client while holding the lock
            for event in list(self.event_buffer):
                try:
                    await websocket.send_json(event)
                except Exception as e:
                    print(f"[WS] Replay send failed, dropping connection: {e}")
                    self.active_connections.remove(websocket)
                    return

    async def disconnect(self, websocket: WebSocket):
        async with self.lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)

    async def emit(self, data: Dict[str, Any]):
        """
        Broadcast a single log event
        """
        # Store for replay
        self.event_buffer.append(data)

        await self._broadcast(data)

    async def _broadcast(self, message: Dict[str, Any]):
        dead_connections = []

        async with self.lock:
            for ws in self.active_connections:
                try:
                    await ws.send_json(message)
                except Exception:
                    dead_connections.append(ws)

            # Cleanup dead sockets
            for ws in dead_connections:
                self.active_connections.remove(ws)