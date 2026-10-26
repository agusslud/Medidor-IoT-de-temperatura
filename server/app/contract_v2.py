"""Versioned experimental message models; not connected to the HTTP API."""

from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from .schemas import PowerSource, SensorStatus


class TimeQuality(StrEnum):
    SYNCHRONIZED = "synchronized"
    ESTIMATED = "estimated"
    UNKNOWN = "unknown"


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    schema_version: Literal[2] = 2
    device_id: str = Field(min_length=1, max_length=80)
    boot_id: UUID
    uptime_ms: int = Field(ge=0, le=2**64 - 1)


class TimedRecord(Message):
    sequence: int = Field(ge=0, le=2**64 - 1)
    observed_at: datetime | None
    time_quality: TimeQuality

    @model_validator(mode="after")
    def validate_time(self):
        if (self.observed_at is None) != (self.time_quality == TimeQuality.UNKNOWN):
            raise ValueError("unknown time requires null observed_at, and vice versa")
        if self.observed_at is not None and self.observed_at.utcoffset() != timedelta(0):
            raise ValueError("observed_at must be timezone-aware UTC")
        return self


class Summary(TimedRecord):
    type: Literal["temperature_summary"] = "temperature_summary"
    temperature_last_c: float | None
    temperature_min_c: float | None
    temperature_max_c: float | None
    valid_samples: int = Field(ge=0, le=10)
    sensor_status: SensorStatus
    power_source: PowerSource

    @model_validator(mode="after")
    def validate_samples(self):
        values = (self.temperature_last_c, self.temperature_min_c, self.temperature_max_c)
        if self.valid_samples == 0:
            if any(value is not None for value in values):
                raise ValueError("no valid samples requires null temperatures")
        elif any(value is None for value in values):
            raise ValueError("valid samples require all temperatures")
        elif not self.temperature_min_c <= self.temperature_last_c <= self.temperature_max_c:
            raise ValueError("expected min <= last <= max")
        return self


class Event(TimedRecord):
    type: Literal["event"] = "event"
    event_type: Literal[
        "sensor_fault", "sensor_recovered", "temperature_out_of_range",
        "temperature_in_range", "power_changed", "records_lost",
    ]
    temperature_c: float | None = None
    power_source: PowerSource = PowerSource.UNKNOWN
    lost_count: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_loss(self):
        if (self.event_type == "records_lost") != (self.lost_count is not None):
            raise ValueError("lost_count is required only for records_lost")
        return self


class Heartbeat(Message):
    type: Literal["heartbeat"] = "heartbeat"
    buffered_records: int = Field(ge=0)
    sensor_status: SensorStatus
    power_source: PowerSource


class HeartbeatReply(BaseModel):
    server_time: datetime | None
    time_quality: Literal["synchronized", "unknown"]

    @model_validator(mode="after")
    def validate_time(self):
        if (self.server_time is None) != (self.time_quality == "unknown"):
            raise ValueError("unknown server time requires null server_time")
        if self.server_time is not None and self.server_time.utcoffset() != timedelta(0):
            raise ValueError("server_time must be timezone-aware UTC")
        return self


WireMessage = Annotated[Summary | Event | Heartbeat, Field(discriminator="type")]
wire_adapter = TypeAdapter(WireMessage)


def estimate_time(record: TimedRecord, anchor_boot_id: UUID, anchor_uptime_ms: int,
                  anchor_time: datetime) -> datetime | None:
    """Estimate only from a trustworthy, same-boot UTC anchor; never fill gaps."""
    if (record.boot_id != anchor_boot_id or anchor_uptime_ms < record.uptime_ms
            or anchor_time.utcoffset() != timedelta(0)):
        return None
    return anchor_time.astimezone(UTC) - timedelta(milliseconds=anchor_uptime_ms - record.uptime_ms)
