import clickhouse_connect
from config import CLICKHOUSE_HOST, CLICKHOUSE_PORT
from datetime import datetime, timezone

# Lazy client — created on first use so startup is never blocked
_client = None


def _get_client():
    global _client
    if _client is None:
        print(f"[clickhouse] Connecting to {CLICKHOUSE_HOST}:{CLICKHOUSE_PORT}...")
        _client = clickhouse_connect.get_client(
            host=CLICKHOUSE_HOST,
            port=CLICKHOUSE_PORT
        )
        print("[clickhouse] Connected.")
    return _client


# Keywords that indicate a real issue worth inspecting.
ISSUE_KEYWORDS = [
    "error", "err:", "warn", "fail", "spike", "crash",
    "leak", "timeout", "latency", "exception", "critical",
    "down", "unavailable", "refused", "unreachable",
    "AIOps-TEST", "OOMKilled", "panic",
]

# Cursor — tracks the newest timestamp we have already processed.
# Initialised to now() so historical logs are completely ignored.
# Only logs that arrive AFTER this process started are processed.
_last_seen_ts: datetime = datetime.now(timezone.utc)


def _keyword_filter() -> str:
    """Build a SQL OR clause matching any issue keyword (case-insensitive)."""
    clauses = [f"lowerUTF8(body) LIKE '%{kw.lower()}%'" for kw in ISSUE_KEYWORDS]
    return "(" + "\n       OR ".join(clauses) + ")"


def fetch_recent_logs(limit=20):
    """
    Return only logs that are NEWER than the last time we polled.
    Each incident log is processed exactly once — no re-sends.
    """
    global _last_seen_ts

    client = _get_client()
    keyword_filter = _keyword_filter()

    # Format cursor as ClickHouse-compatible datetime string
    cursor_str = _last_seen_ts.strftime("%Y-%m-%d %H:%M:%S")

    query = f"""
    SELECT
        toDateTime(timestamp/1000000000) as ts,
        body,
        severity_text
    FROM signoz_logs.logs_v2
    WHERE {keyword_filter}
      AND body NOT LIKE '%GET %'
      AND body NOT LIKE '%POST %'
      AND toDateTime(timestamp/1000000000) > toDateTime('{cursor_str}')
    ORDER BY ts ASC
    LIMIT {limit}
    """

    result = client.query(query)

    logs = []
    newest_ts = _last_seen_ts

    for row in result.result_rows:
        ts: datetime = row[0]
        if not ts.tzinfo:
            ts = ts.replace(tzinfo=timezone.utc)
        logs.append({
            "timestamp": str(ts),
            "message":   row[1],
            "severity":  row[2] if row[2] else "UNKNOWN",
        })
        if ts > newest_ts:
            newest_ts = ts

    # Advance the cursor so next poll only sees genuinely new logs
    if logs:
        _last_seen_ts = newest_ts
        print(f"[cursor] Advanced to {_last_seen_ts} — {len(logs)} new log(s) forwarded.")

    return {"logs": logs}