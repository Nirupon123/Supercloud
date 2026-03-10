import os

CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "signoz-clickhouse")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", 8123))

# Now sends to orchestrator, which internally drives detector → rca_brain → fixer
ORCHESTRATOR_URL = os.getenv(
    "ORCHESTRATOR_URL",
    "http://orchestrator:8000/anomaly"
)

POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 10))