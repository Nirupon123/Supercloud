import json

try:
    import clickhouse_connect

    client = clickhouse_connect.get_client(
        host="localhost",
        port=8123
    )
except Exception as e:
    client = None
    connection_error = str(e)


def parse_log_body(body):
    """
    Try to parse structured JSON logs.
    If not JSON, return raw message.
    """
    try:
        return json.loads(body)
    except Exception:
        return {"message": body}


def get_recent_logs_json(limit=10):

    if client is None:
        return {"error": connection_error}

    try:
        query = f"""
        SELECT DISTINCT
            toDateTime(timestamp/1000000000) as ts,
            body
        FROM signoz_logs.logs_v2
        WHERE body NOT LIKE '%GET %'
          AND body NOT LIKE '%POST %'
        ORDER BY ts DESC
        LIMIT {limit}
        """

        result = client.query(query)

        logs = []

        for row in result.result_rows:

            parsed = parse_log_body(row[1])

            logs.append({
                "timestamp": str(row[0]),
                **parsed
            })

        return {"logs": logs}

    except Exception as e:
        return {"error": str(e)}


def get_log_volume_json():

    if client is None:
        return {"error": connection_error}

    try:
        query = """
        SELECT
            toStartOfMinute(toDateTime(timestamp/1000000000)) as minute,
            count() as log_count
        FROM signoz_logs.logs_v2
        WHERE body NOT LIKE '%GET %'
          AND body NOT LIKE '%POST %'
        GROUP BY minute
        ORDER BY minute DESC
        LIMIT 10
        """

        result = client.query(query)

        data = []

        for row in result.result_rows:
            data.append({
                "minute": str(row[0]),
                "log_count": row[1]
            })

        return {"log_volume": data}

    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":

    print("\n=== Recent Logs JSON ===")
    logs_json = get_recent_logs_json()
    print(json.dumps(logs_json, indent=2))

    print("\n=== Log Volume JSON ===")
    volume_json = get_log_volume_json()
    print(json.dumps(volume_json, indent=2))