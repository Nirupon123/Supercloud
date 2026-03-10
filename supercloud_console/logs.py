import pandas as pd

try:
    import clickhouse_connect

    client = clickhouse_connect.get_client(
        host="localhost",
        port=8123
    )
except:
    client = None


def get_logs(service):

    if client is None:
        return pd.DataFrame({
            "Timestamp": ["No ClickHouse connection"],
            "Body": ["Logs unavailable"]
        })

    query = f"""
    SELECT Timestamp, Body
    FROM signoz_logs.logs
    WHERE ServiceName='{service}'
    ORDER BY Timestamp DESC
    LIMIT 100
    """

    return client.query_df(query)