import plotly.express as px
import pandas as pd

def cpu_chart(metrics):

    df = pd.DataFrame(metrics)

    fig = px.line(
        df,
        x="timestamp",
        y="cpu",
        color="service",
        title="CPU Usage per Service"
    )

    return fig


def memory_chart(metrics):

    df = pd.DataFrame(metrics)

    fig = px.line(
        df,
        x="timestamp",
        y="memory",
        color="service",
        title="Memory Usage"
    )

    return fig


def incident_severity_chart(incidents):

    df = pd.DataFrame(incidents)

    fig = px.histogram(
        df,
        x="severity",
        color="service",
        title="Incident Severity"
    )

    return fig