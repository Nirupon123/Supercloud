import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


def incident_severity_chart(incidents: list):
    if not incidents or "error" in (incidents[0] if incidents else {}):
        fig = go.Figure()
        fig.update_layout(title="No incidents yet")
        return fig

    df = pd.DataFrame(incidents)
    if "severity" not in df.columns:
        df["severity"] = "unknown"
    if "state" not in df.columns:
        df["state"] = "unknown"

    fig = px.histogram(
        df,
        x="severity",
        color="state",
        title="Incidents by Severity & State",
        color_discrete_map={
            "anomaly_detected":        "#ef4444",
            "rca_in_progress":         "#f97316",
            "remediation_in_progress": "#eab308",
            "resolved":                "#22c55e",
            "failed":                  "#6b7280",
        }
    )
    fig.update_layout(bargap=0.2)
    return fig


def incident_timeline_chart(incidents: list):
    if not incidents:
        fig = go.Figure()
        fig.update_layout(title="No incidents to plot")
        return fig

    df = pd.DataFrame(incidents)
    if "detection_time" not in df.columns:
        return go.Figure()

    df["detection_time"] = pd.to_datetime(df["detection_time"], errors="coerce")
    df = df.dropna(subset=["detection_time"])

    fig = px.scatter(
        df,
        x="detection_time",
        y="issue_type",
        color="state",
        hover_data=["incident_id", "severity", "first_message"],
        title="Incident Timeline",
        size_max=15,
    )
    return fig


def cpu_chart(metrics: list):
    if not metrics:
        fig = go.Figure()
        fig.update_layout(title="No metrics yet")
        return fig

    df = pd.DataFrame(metrics)
    if "cpu" not in df.columns or df["cpu"].sum() == 0:
        fig = go.Figure()
        fig.add_annotation(text="CPU metrics not available from log-based incidents",
                           xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(title="CPU Usage")
        return fig

    fig = px.line(df, x="detection_time", y="cpu", color="service", title="CPU Usage per Service")
    return fig


def memory_chart(metrics: list):
    if not metrics:
        fig = go.Figure()
        fig.update_layout(title="No metrics yet")
        return fig

    df = pd.DataFrame(metrics)
    if "memory" not in df.columns or df["memory"].sum() == 0:
        fig = go.Figure()
        fig.add_annotation(text="Memory metrics not available from log-based incidents",
                           xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(title="Memory Usage")
        return fig

    fig = px.line(df, x="detection_time", y="memory", color="service", title="Memory Usage per Service")
    return fig