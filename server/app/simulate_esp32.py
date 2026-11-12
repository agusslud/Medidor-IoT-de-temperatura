"""Send a sample v2 summary and retry it over HTTP; no hardware required."""

import argparse
import json
from urllib.request import Request, urlopen
from uuid import uuid4

from .contract_v2 import Summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    record = Summary(device_id="ESP32_SIMULADO", boot_id=uuid4(), sequence=0,
                     uptime_ms=600000, observed_at=None, time_quality="unknown",
                     temperature_last_c=4.2, temperature_min_c=3.8, temperature_max_c=4.7,
                     valid_samples=10, sensor_status="OK", power_source="UNKNOWN")
    payload = record.model_dump_json().encode()
    for attempt in ("primera entrega", "reintento"):
        request = Request(f"{args.url.rstrip('/')}/api/v2/records", data=payload,
                          headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(request, timeout=5.0) as response:
            print(f"{attempt}: HTTP {response.status} {json.load(response)}")


if __name__ == "__main__":
    main()
