import gradio as gr
import pandas as pd

from api import *
from charts import *
from logs import *
from dependency import *

def load_incidents():

    data = get_incidents()

    df = pd.DataFrame(data)

    chart = incident_severity_chart(data)

    return df, chart


def load_metrics():

    metrics = get_metrics()

    cpu = cpu_chart(metrics)
    mem = memory_chart(metrics)

    return cpu, mem


def rca_analysis(row):

    result = get_rca(row)

    return result


def remediate(service):

    return run_remediation(service)


def export_audit():

    data = get_incidents()

    df = pd.DataFrame(data)

    path = "audit_history.csv"

    df.to_csv(path, index=False)

    return path


def query_logs(service):

    df = get_logs(service)

    return df


def dependency_graph():

    return generate_dependency_graph()


with gr.Blocks(title="SuperCloud AIOps Console") as app:

    gr.Markdown("# SuperCloud AIOps Platform")

    with gr.Tab("Incident Command Center"):

        incident_table = gr.Dataframe()

        severity_chart = gr.Plot()

        refresh = gr.Button("Refresh Incidents")

        refresh.click(load_incidents, outputs=[incident_table, severity_chart])


    with gr.Tab("Service Health"):

        cpu_plot = gr.Plot()
        mem_plot = gr.Plot()

        refresh_metrics = gr.Button("Load Metrics")

        refresh_metrics.click(load_metrics, outputs=[cpu_plot, mem_plot])


    with gr.Tab("Root Cause Analysis"):

        incident_input = gr.JSON()

        analyze_btn = gr.Button("Run RCA")

        rca_output = gr.JSON()

        analyze_btn.click(rca_analysis, inputs=incident_input, outputs=rca_output)


    with gr.Tab("Remediation"):

        service = gr.Textbox(label="Service Name")

        run = gr.Button("Run Fix")

        result = gr.JSON()

        run.click(remediate, inputs=service, outputs=result)


    with gr.Tab("Logs Explorer"):

        service_logs = gr.Textbox(label="Service")

        query = gr.Button("Fetch Logs")

        logs_output = gr.Dataframe()

        query.click(query_logs, inputs=service_logs, outputs=logs_output)


    with gr.Tab("Dependency Map"):

        graph = gr.Plot()

        load_graph = gr.Button("Show Architecture")

        load_graph.click(dependency_graph, outputs=graph)


    with gr.Tab("Audit Dashboard"):

        export = gr.Button("Download Incident History")

        file = gr.File()

        export.click(export_audit, outputs=file)


app.launch(server_port=7860)