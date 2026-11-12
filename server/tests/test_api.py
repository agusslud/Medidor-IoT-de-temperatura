from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_accepts_valid_telemetry() -> None:
    with TestClient(app) as client:
        response = client.post("/api/telemetry", json={
            "device_id": "ESP32_FARMACIA_01", "temperature": 4.25,
            "raw_temperature": 4.05, "offset_applied": 0.2,
            "sensor_status": "OK", "power_source": "MAIN_POWER", "buffered_records": 0,
        })
    assert response.status_code == 201
    assert response.json()["accepted"] is True



def test_concurrent_legacy_requests():
    payload = {"device_id": "concurrent", "temperature": 4.0, "raw_temperature": 4.0,
               "offset_applied": 0, "sensor_status": "OK", "power_source": "MAIN_POWER"}
    with TestClient(app) as client, ThreadPoolExecutor(max_workers=6) as executor:
        responses = list(executor.map(
            lambda _: client.post("/api/telemetry", json=payload), range(12),
        ))
        assert all(response.status_code == 201 for response in responses)
        assert len({response.json()["id"] for response in responses}) == 12
        history = client.get("/api/temperature/history", params={"device_id": "concurrent"})
        assert history.status_code == 200
        assert len(history.json()) == 12
        offset = client.post("/api/config/offset", json={"device_id": "concurrent", "offset_c": 0.2})
        assert offset.status_code == 200
        assert offset.json() == {"device_id": "concurrent", "offset_c": 0.2}
