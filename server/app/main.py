from contextlib import asynccontextmanager, closing
from datetime import UTC
from typing import Annotated, Literal

from fastapi import Body, FastAPI, HTTPException, Query, Response, status
from pydantic import AwareDatetime

from .contract_v2 import Event, Heartbeat, HeartbeatReply, HistoryPage, Summary
from .database import connect, history, initialize, save_telemetry, set_config
from .schemas import OffsetConfigIn, TelemetryIn
from .settings import settings
from .storage_v2 import initialize_v2, record_history, save_record


@asynccontextmanager
async def lifespan(app: FastAPI):
    with closing(connect(settings.database_path)) as connection:
        initialize(connection)
        initialize_v2(connection)
    yield


app = FastAPI(title="Farmacia Cold Chain Monitor", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v2/records", status_code=status.HTTP_201_CREATED)
def create_record_v2(
    item: Annotated[Summary | Event, Body(discriminator="type")], response: Response,
) -> dict[str, object]:
    result, record_id = save_record(settings.database_path, item)
    if result == "conflict":
        raise HTTPException(status_code=409, detail="record identity already has different content")
    if result == "duplicate":
        response.status_code = status.HTTP_200_OK
    return {"result": result, "id": record_id}


@app.post("/api/v2/heartbeat", response_model=HeartbeatReply)
def heartbeat_v2(item: Heartbeat) -> HeartbeatReply:
    # A running system clock alone does not prove NTP synchronization.
    return HeartbeatReply(server_time=None, time_quality="unknown")


@app.get("/api/v2/records", response_model=HistoryPage)
def history_v2(
    device_id: Annotated[str, Query(min_length=1, max_length=80)],
    record_type: Literal["temperature_summary", "event"] | None = None,
    time_basis: Literal["observed", "received"] = "observed",
    start: AwareDatetime | None = None, end: AwareDatetime | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> HistoryPage:
    start = start.astimezone(UTC) if start else None
    end = end.astimezone(UTC) if end else None
    if start is not None and end is not None and start > end:
        raise HTTPException(status_code=422, detail="start must not be after end")
    return record_history(settings.database_path, device_id, record_type,
                          time_basis, start, end, limit, offset)


@app.post("/api/telemetry", status_code=status.HTTP_201_CREATED)
def create_telemetry(item: TelemetryIn) -> dict[str, object]:
    if item.sensor_status == "OK" and item.temperature is None:
        raise HTTPException(status_code=422, detail="temperature is required when sensor is OK")
    with closing(connect(settings.database_path)) as database:
        record_id = save_telemetry(database, item)
    return {"id": record_id, "accepted": True}


@app.get("/api/temperature/history")
def temperature_history(device_id: str, limit: int = 500) -> list[dict[str, object]]:
    if not 1 <= limit <= 10_000:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 10000")
    with closing(connect(settings.database_path)) as database:
        return [dict(row) for row in history(database, device_id, limit)]


@app.post("/api/config/offset")
def set_offset(item: OffsetConfigIn) -> dict[str, object]:
    with closing(connect(settings.database_path)) as database:
        set_config(database, f"offset:{item.device_id}", str(item.offset_c))
    # The ESP32 will fetch this setting through an authenticated config endpoint
    # introduced once device credentials have been selected.
    return {"device_id": item.device_id, "offset_c": item.offset_c}
