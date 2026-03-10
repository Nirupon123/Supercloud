import pandas as pd

try:
    import clickhouse_connect
    client = clickhouse_connect.get_client(host="localhost", port=8123)
except Exception as e:
    print(f"[logs] ClickHouse connection failed: {e}")
    client = None


ISSUE_KEYWORDS = [
    "error", "warn", "fail", "spike", "crash", "leak",
    "timeout", "latency", "exception", "critical",
    "AIOps-TEST", "OOMKilled",
]


def get_logs(service: str = "", limit: int = 100):
    if client is None:
        return pd.DataFrame({
            "timestamp": ["No ClickHouse connection"],
            "severity":  ["—"],
            "message":   ["ClickHouse unavailable — ensure SigNoz stack is running"]
        })

    conditions = []

    if service.strip():
        conditions.append(f"ServiceName = '{service.strip()}'")

    keyword_clauses = " OR ".join(
        [f"lowerUTF8(body) LIKE '%{kw.lower()}%'" for kw in ISSUE_KEYWORDS]
    )
    conditions.append(f"({keyword_clauses})")

    where = " AND ".join(conditions) if conditions else "1=1"

    query = f"""
    SELECT
        toDateTime(timestamp / 1000000000) AS timestamp,
        severity_text AS severity,
        body AS message
    FROM signoz_logs.logs_v2
    WHERE {where}
    ORDER BY timestamp DESC
    LIMIT {limit}
    """

    try:
        return client.query_df(query)
    except Exception as e:
        return pd.DataFrame({"error": [str(e)]})