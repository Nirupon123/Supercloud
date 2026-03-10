import networkx as nx
import matplotlib.pyplot as plt

def generate_dependency_graph():

    G = nx.DiGraph()

    edges = [
        ("Telemetry", "Orchestrator"),
        ("Orchestrator", "Detector"),
        ("Orchestrator", "RCA"),
        ("Orchestrator", "Fixer"),
        ("Detector", "InfluxDB"),
        ("RCA", "LLM")
    ]

    G.add_edges_from(edges)

    fig = plt.figure()

    nx.draw(G, with_labels=True, node_color="lightblue", node_size=2000)

    return fig