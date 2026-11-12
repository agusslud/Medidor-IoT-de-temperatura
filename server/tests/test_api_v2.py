import sqlite3
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app


def sample(boot=None):
    return {"schema_version": 2, "type": "temperature_summary", "device_id": "sim-1",
            "boot_id": str(boot or uuid4()), "sequence": 1, "uptime_ms": 600000,
            "observed_at": None, "time_quality": "unknown", "temperature_last_c": 4.2,
            "temperature_min_c": 3.8, "temperature_max_c": 4.7, "valid_samples": 10,
            "sensor_status": "OK", "power_source": "UNKNOWN"}


def test_v2_persistence_duplicate_conflict_and_restart(database_path):
    item = sample()
    with TestClient(app) as client:
        first = client.post("/api/v2/records", json=item)
        duplicate = client.post("/api/v2/records", json=item)
        assert (first.status_code, duplicate.status_code) == (201, 200)
        assert duplicate.json() == {"result": "duplicate", "id": first.json()["id"]}
        assert client.post("/api/v2/records", json={**item, "temperature_last_c": 4.3}).status_code == 409
        assert client.post("/api/v2/records", json={**item, "time_quality": "synchronized"}).status_code == 422
        event = {key: item[key] for key in ("schema_version", "device_id", "boot_id", "uptime_ms",
                                            "observed_at", "time_quality")}
        event.update(type="event", sequence=2, event_type="sensor_fault", power_source="BATTERY")
        assert client.post("/api/v2/records", json=event).status_code == 201
        heartbeat = {key: item[key] for key in ("schema_version", "device_id", "boot_id", "uptime_ms",
                                                "sensor_status", "power_source")}
        heartbeat.update(type="heartbeat", buffered_records=0)
        reply = client.post("/api/v2/heartbeat", json=heartbeat)
        assert reply.json() == {"server_time": None, "time_quality": "unknown"}
    with TestClient(app) as client:
        assert client.post("/api/v2/records", json=item).json()["result"] == "duplicate"
    with sqlite3.connect(database_path) as database:
        rows = database.execute("SELECT record_type, received_at, payload FROM telemetry_v2").fetchall()
    assert len(rows) == 2
    assert all(row[1].endswith("Z") for row in rows)
    assert '"observed_at":null' in rows[0][2]


def test_concurrent_duplicate_acknowledgements():
    item = sample()
    with TestClient(app) as client, ThreadPoolExecutor(max_workers=6) as executor:
        responses = list(executor.map(lambda _: client.post("/api/v2/records", json=item), range(12)))
    assert sorted(response.status_code for response in responses) == [200] * 11 + [201]
    assert len({response.json()["id"] for response in responses}) == 1


@pytest.mark.parametrize("record_type", [None, "unknown", "heartbeat"])
def test_invalid_record_type(record_type, database_path):
    item = sample()
    if record_type is None:
        del item["type"]
    else:
        item["type"] = record_type
    with TestClient(app) as client:
        assert client.post("/api/v2/records", json=item).status_code == 422
    with sqlite3.connect(database_path) as database:
        assert database.execute("SELECT count(*) FROM telemetry_v2").fetchone()[0] == 0
