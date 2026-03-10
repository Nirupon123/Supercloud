import time

from clickhouse_client import fetch_recent_logs
from detector_client import send_to_detector
from config import POLL_INTERVAL

STARTUP_DELAY = 5  # seconds to wait before the first poll


def run():

    print(f"Telemetry service started. First poll in {STARTUP_DELAY}s, then every {POLL_INTERVAL}s.")
    time.sleep(STARTUP_DELAY)

    poll_count = 0

    while True:

        poll_count += 1
        logs = fetch_recent_logs()
        log_count = len(logs.get("logs", []))

        print(f"\n[Poll #{poll_count}] Fetched {log_count} incident log(s) from ClickHouse.")

        if log_count == 0:
            print("No matching logs in the last window. Skipping detector call.")
        else:
            payload = {"logs": logs}
            print("Sending to detector...")
            send_to_detector(payload)

        print(f"Sleeping {POLL_INTERVAL}s until next poll...")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    run()