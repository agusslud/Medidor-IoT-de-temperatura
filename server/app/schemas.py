from enum import StrEnum

from pydantic import BaseModel, Field


class SensorStatus(StrEnum):
    OK = "OK"
    FAULT = "FAULT"


class PowerSource(StrEnum):
    MAIN_POWER = "MAIN_POWER"
    BATTERY = "BATTERY"
    UNKNOWN = "UNKNOWN"


class TelemetryIn(BaseModel):
    device_id: str = Field(min_length=1, max_length=80)
    temperature: float | None = Field(default=None, ge=-100, le=100)
    raw_temperature: float | None = Field(default=None, ge=-100, le=100)
    offset_applied: float = Field(ge=-10, le=10)
    sensor_status: SensorStatus
    power_source: PowerSource = PowerSource.UNKNOWN
    buffered_records: int = Field(default=0, ge=0, le=100_000)


class OffsetConfigIn(BaseModel):
    device_id: str = Field(min_length=1, max_length=80)
    offset_c: float = Field(ge=-10, le=10)
