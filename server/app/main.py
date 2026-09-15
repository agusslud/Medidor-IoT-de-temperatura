from contextlib import asynccontextmanager
import sqlite3

from fastapi import FastAPI, HTTPException, Request, status

from .database import connect, history, initialize, save_telemetry, set_config
from .schemas import OffsetConfigIn, TelemetryIn
from .settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    connection = connect(settings.database_path)
    initialize(connection)
    app.state.database = connection
    yield
    connection.close()


app = FastAPI(title="Farmacia Cold Chain Monitor", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/telemetry", status_code=status.HTTP_201_CREATED)
def create_telemetry(item: TelemetryIn, request: Request) -> dict[str, object]:
    if item.sensor_status == "OK" and item.temperature is None:
        raise HTTPException(status_code=422, detail="temperature is required when sensor is OK")
    database: sqlite3.Connection = request.app.state.database
    record_id = save_telemetry(database, item)
    return {"id": record_id, "accepted": True}


@app.get("/api/temperature/history")
def temperature_history(device_id: str, request: Request, limit: int = 500) -> list[dict[str, object]]:
    if not 1 <= limit <= 10_000:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 10000")
    database: sqlite3.Connection = request.app.state.database
    return [dict(row) for row in history(database, device_id, limit)]


@app.post("/api/config/offset")
def set_offset(item: OffsetConfigIn, request: Request) -> dict[str, object]:
    database: sqlite3.Connection = request.app.state.database
    set_config(database, f"offset:{item.device_id}", str(item.offset_c))
    # The ESP32 will fetch this setting through an authenticated config endpoint
    # introduced once device credentials have been selected.
    return {"device_id": item.device_id, "offset_c": item.offset_c}
