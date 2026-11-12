import sqlite3

import pytest
from fastapi.testclient import TestClient
from test_api_v2 import sample

from app.main import app


def test_observed_history_and_filters(database_path):
    with TestClient(app) as client:
        for sequence, instant in enumerate(("2026-11-12T12:10:00Z", "2026-11-12T12:00:00Z", None)):
            item = sample()
            item.update(sequence=sequence, observed_at=instant,
                        time_quality="estimated" if instant else "unknown")
            assert client.post("/api/v2/records", json=item).status_code == 201
        other = sample()
        other.update(device_id="other", observed_at="2026-11-12T12:05:00Z",
                     time_quality="synchronized")
        client.post("/api/v2/records", json=other)
        params = {"device_id": "sim-1"}
        page = client.get("/api/v2/records", params=params).json()
        assert [row["record"]["sequence"] for row in page["items"]] == [0, 1]
        assert page["next_offset"] is None
        assert page["items"][0]["record"]["time_quality"] == "estimated"
        filtered = client.get("/api/v2/records", params={**params,
            "start": "2026-11-12T09:00:00-03:00", "end": "2026-11-12T12:10:00Z"}).json()
        assert [row["record"]["sequence"] for row in filtered["items"]] == [1]
        received = client.get("/api/v2/records", params={**params, "time_basis": "received"}).json()
        assert len(received["items"]) == 3
        assert any(row["record"]["observed_at"] is None for row in received["items"])
        event = {key: other[key] for key in ("device_id", "boot_id", "uptime_ms", "observed_at", "time_quality")}
        event.update(device_id="sim-1", type="event", sequence=5, event_type="sensor_fault")
        client.post("/api/v2/records", json=event)
        assert len(client.get("/api/v2/records", params={**params, "record_type": "event"}).json()["items"]) == 1
        assert len(client.get("/api/v2/records", params={**params, "record_type": "temperature_summary"}).json()["items"]) == 2
        assert client.get("/api/v2/records", params={"device_id": "absent"}).json() == {"items": [], "next_offset": None}
        with sqlite3.connect(database_path) as db:
            db.execute("UPDATE telemetry_v2 SET received_at='2026-11-12T14:00:00Z'")
        assert client.get("/api/v2/records", params={**params, "time_basis": "received",
            "end": "2026-11-12T14:00:00Z"}).json()["items"] == []


def test_stable_pages_with_equal_dates():
    with TestClient(app) as client:
        ids = []
        for _ in range(5):
            item = sample()
            item.update(observed_at="2026-11-12T12:00:00Z", time_quality="synchronized")
            ids.append(client.post("/api/v2/records", json=item).json()["id"])
        found = []
        offset = 0
        while offset is not None:
            page = client.get("/api/v2/records", params={"device_id": "sim-1",
                              "limit": 2, "offset": offset}).json()
            found.extend(row["id"] for row in page["items"])
            offset = page["next_offset"]
        assert found == ids[::-1]


@pytest.mark.parametrize("extra", [
    {"start": "2026-11-12T12:00:00"}, {"end": "bad"},
    {"start": "2026-11-13T00:00:00Z", "end": "2026-11-12T00:00:00Z"},
    {"limit": 0}, {"limit": 501}, {"offset": -1},
    {"record_type": "heartbeat"}, {"time_basis": "invalid"},
])
def test_invalid_history_parameters(extra):
    with TestClient(app) as client:
        assert client.get("/api/v2/records", params={"device_id": "sim-1", **extra}).status_code == 422


def test_device_required():
    with TestClient(app) as client:
        assert client.get("/api/v2/records").status_code == 422
