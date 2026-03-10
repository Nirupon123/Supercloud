import gradio as gr
import pandas as pd

from api import (
    get_incidents, get_metrics, get_rca, run_remediation,
    check_opa_policy, get_pipeline_status, poll_pipeline_events
)
from charts import (
    incident_severity_chart, incident_timeline_chart,
    cpu_chart, memory_chart
)
from logs import get_logs
from dependency import generate_dependency_graph


# ── Helpers ──────────────────────────────────────────────────────────────────

def load_incidents():
    data = get_incidents()
    df   = pd.DataFrame(data) if data and "error" not in data[0] else pd.DataFrame()
    sev  = incident_severity_chart(data)
    tl   = incident_timeline_chart(data)
    return df, sev, tl


def load_metrics():
    metrics = get_metrics()
    return cpu_chart(metrics), memory_chart(metrics)


def load_pipeline_status():
    statuses = get_pipeline_status()
    rows = [[svc, status] for svc, status in statuses.items()]
    return pd.DataFrame(rows, columns=["Service", "Status"])


def refresh_pipeline_events():
    return poll_pipeline_events(last_n=30)


def run_manual_rca(incident_json: dict):
    return get_rca(incident_json)


def run_manual_fix(incident_id: str, issue_type: str, container: str):
    return run_remediation(incident_id, issue_type, container)


def run_opa_check(issue_type: str, environment: str, confidence: float):
    return check_opa_policy(issue_type, environment, confidence)


def query_logs(service: str):
    df = get_logs(service)
    return df


# ── Gradio UI ─────────────────────────────────────────────────────────────────

with gr.Blocks(title="SuperCloud AIOps Console") as app:

    gr.Markdown("""
    # 🚀 SuperCloud AIOps Console
    **Pipeline:** `Telemetry → Orchestrator → Detector → RCA Brain (OPA) → Fixer`
    """)

    # ── Tab 1: Service Health (status bar) ───────────────────────────────────
    with gr.Tab("🟢 Service Health"):
        gr.Markdown("### Live status of all pipeline services")
        status_table = gr.Dataframe(
            headers=["Service", "Status"],
            interactive=False
        )
        with gr.Row():
            refresh_status_btn = gr.Button("Refresh Status", variant="primary")
        refresh_status_btn.click(load_pipeline_status, outputs=status_table)
        app.load(load_pipeline_status, outputs=status_table)   # load on open

    # ── Tab 2: Live Pipeline Stream ──────────────────────────────────────────
    with gr.Tab("⚡ Live Pipeline"):
        gr.Markdown("""
        ### Real-time pipeline events
        Shows events flowing through: **Detector → RCA Brain → OPA → Fixer**
        > Trigger an incident from your MERN app (`/api/leak` or `/api/slow`) then click **Refresh**.
        """)
        pipeline_output = gr.Textbox(
            label="Pipeline Events (most recent)",
            lines=30,
            max_lines=50,
            interactive=False,
        )
        refresh_pipeline_btn = gr.Button("🔄 Refresh Events", variant="primary")
        refresh_pipeline_btn.click(refresh_pipeline_events, outputs=pipeline_output)

    # ── Tab 3: Incident Command Center ───────────────────────────────────────
    with gr.Tab("🚨 Incidents"):
        gr.Markdown("### All incidents tracked by the Orchestrator")
        incident_table = gr.Dataframe(interactive=False)
        with gr.Row():
            sev_chart = gr.Plot(label="Severity Breakdown")
            tl_chart  = gr.Plot(label="Incident Timeline")
        refresh_inc_btn = gr.Button("🔄 Refresh Incidents", variant="primary")
        refresh_inc_btn.click(load_incidents, outputs=[incident_table, sev_chart, tl_chart])

    # ── Tab 4: Trigger Issue (manual frontend-driven incident) ───────────────
    with gr.Tab("🔧 Trigger Issue"):
        gr.Markdown("""
        ### Manually trigger an RCA + Fix cycle
        Paste a JSON payload representing the incident, or fill the quick form below.
        """)
        with gr.Row():
            with gr.Column():
                gr.Markdown("#### Manual RCA")
                rca_input  = gr.JSON(label="Incident Payload", value={
                    "incident_id":   "manual-001",
                    "severity":      "high",
                    "anomaly_score": 0.9,
                    "logs": [{"timestamp": "", "message": "AIOps-TEST: Triggering intentional memory leak...", "severity": "warn"}],
                    "reason": "Manual trigger from SuperCloud Console"
                })
                rca_btn    = gr.Button("🧠 Run RCA", variant="primary")
                rca_output = gr.JSON(label="RCA Result")
                rca_btn.click(run_manual_rca, inputs=rca_input, outputs=rca_output)

            with gr.Column():
                gr.Markdown("#### Manual Fixer")
                inc_id_in  = gr.Textbox(label="Incident ID",    value="manual-001")
                issue_in   = gr.Dropdown(
                    label="Issue Type",
                    choices=["memory_high", "cpu_high", "disk_high", "service_error_log", "log_issue", "kubernetes_pod_crash"],
                    value="memory_high"
                )
                container_in = gr.Textbox(label="Container Name", value="mern-backend")
                fix_btn      = gr.Button("🔨 Run Fixer", variant="secondary")
                fix_output   = gr.JSON(label="Fixer Result")
                fix_btn.click(run_manual_fix, inputs=[inc_id_in, issue_in, container_in], outputs=fix_output)

    # ── Tab 5: OPA Policy Guard ───────────────────────────────────────────────
    with gr.Tab("🔏 OPA Policy"):
        gr.Markdown("""
        ### Test the OPA Rulebook Guard
        Check whether a given issue/environment/confidence would be **allowed** through to the Fixer.
        """)
        with gr.Row():
            opa_issue = gr.Dropdown(
                label="Issue Type",
                choices=["memory_high", "cpu_high", "disk_high", "service_error_log", "log_issue", "kubernetes_pod_crash", "unknown_issue"],
                value="memory_high"
            )
            opa_env = gr.Dropdown(
                label="Environment",
                choices=["docker", "kubernetes", "systemd", "host", "invalid_env"],
                value="docker"
            )
            opa_conf = gr.Slider(label="Confidence", minimum=0.0, maximum=1.0, step=0.05, value=0.8)
        opa_btn    = gr.Button("✅ Check Policy", variant="primary")
        opa_result = gr.JSON(label="OPA Decision")
        opa_btn.click(run_opa_check, inputs=[opa_issue, opa_env, opa_conf], outputs=opa_result)

    # ── Tab 6: Logs Explorer ─────────────────────────────────────────────────
    with gr.Tab("📋 Logs Explorer"):
        gr.Markdown("### Incident logs from ClickHouse (keyword-filtered)")
        service_input = gr.Textbox(label="Service Name (optional, leave blank for all)", value="")
        query_btn     = gr.Button("Fetch Logs", variant="primary")
        logs_output   = gr.Dataframe(interactive=False)
        query_btn.click(query_logs, inputs=service_input, outputs=logs_output)

    # ── Tab 7: Dependency Map ─────────────────────────────────────────────────
    with gr.Tab("🗺️ Architecture"):
        gr.Markdown("### Pipeline Dependency Graph")
        graph = gr.Plot()
        load_graph_btn = gr.Button("Show Architecture", variant="secondary")
        load_graph_btn.click(generate_dependency_graph, outputs=graph)

    # ── Tab 8: Audit / Export ─────────────────────────────────────────────────
    with gr.Tab("📤 Audit Export"):
        gr.Markdown("### Download incident history as CSV")
        export_btn = gr.Button("📥 Download CSV", variant="secondary")
        file_out   = gr.File()

        def export_audit():
            data = get_incidents()
            df   = pd.DataFrame(data)
            path = "audit_history.csv"
            df.to_csv(path, index=False)
            return path

        export_btn.click(export_audit, outputs=file_out)


app.launch(
    server_port=7860,
    share=False,
    theme=gr.themes.Soft(),
    css=".gradio-container { max-width: 1400px !important; }"
)