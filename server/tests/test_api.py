from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_accepts_valid_telemetry(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.main.settings.database_path", str(tmp_path / "test.db"))
    with TestClient(app) as client:
        response = client.post("/api/telemetry", json={
            "device_id": "ESP32_FARMACIA_01", "temperature": 4.25,
            "raw_temperature": 4.05, "offset_applied": 0.2,
            "sensor_status": "OK", "power_source": "MAIN_POWER", "buffered_records": 0,
        })
    assert response.status_code == 201
    assert response.json()["accepted"] is True
