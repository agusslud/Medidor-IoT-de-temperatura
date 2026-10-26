from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.contract_simulation import CircularQueue, SimulatedReceiver
from app.contract_v2 import Event, Heartbeat, HeartbeatReply, Summary, estimate_time, wire_adapter


def summary(boot_id, sequence=0, **changes):
    fields = {"device_id": "sensor-1", "boot_id": boot_id, "sequence": sequence,
              "uptime_ms": 600000, "observed_at": None, "time_quality": "unknown",
              "temperature_last_c": 4.0, "temperature_min_c": 3.0, "temperature_max_c": 5.0,
              "valid_samples": 10, "sensor_status": "OK", "power_source": "UNKNOWN"}
    fields.update(changes)
    return Summary(**fields)


def event(boot_id, sequence, **changes):
    fields = {"device_id": "sensor-1", "boot_id": boot_id, "sequence": sequence,
              "uptime_ms": 600000, "observed_at": None, "time_quality": "unknown",
              "event_type": "sensor_fault"}
    fields.update(changes)
    return Event(**fields)


def test_messages_and_validation():
    boot = uuid4()
    value = summary(boot)
    assert wire_adapter.validate_json(value.model_dump_json()) == value
    assert wire_adapter.validate_json(event(boot, 1).model_dump_json()).event_type == "sensor_fault"
    heartbeat = Heartbeat(device_id="sensor-1", boot_id=boot, uptime_ms=3, buffered_records=2,
                          sensor_status="FAULT", power_source="BATTERY")
    assert wire_adapter.validate_json(heartbeat.model_dump_json()) == heartbeat
    assert HeartbeatReply(server_time=None, time_quality="unknown").server_time is None
    empty = summary(boot, valid_samples=0, temperature_last_c=None,
                    temperature_min_c=None, temperature_max_c=None, sensor_status="FAULT")
    assert empty.valid_samples == 0
    with pytest.raises(ValidationError):
        summary(boot, valid_samples=0)
    with pytest.raises(ValidationError):
        summary(boot, time_quality="synchronized")
    with pytest.raises(ValidationError):
        summary(boot, observed_at=datetime(2026, 1, 1), time_quality="synchronized")
    with pytest.raises(ValidationError):
        summary(boot, temperature_min_c=6)
    with pytest.raises(ValidationError):
        summary(boot, temperature_last_c=float("nan"))


def test_time_quality_and_reconstruction():
    boot = uuid4()
    anchor = datetime(2026, 1, 1, 12, tzinfo=UTC)
    synced = summary(boot, observed_at=anchor, time_quality="synchronized")
    estimated = summary(boot, observed_at=anchor, time_quality="estimated")
    assert synced.time_quality != estimated.time_quality
    assert estimate_time(summary(boot, uptime_ms=0), boot, 600000, anchor).minute == 50
    assert estimate_time(summary(boot), uuid4(), 600000, anchor) is None
    assert estimate_time(summary(boot), boot, 1, anchor) is None
    assert estimate_time(summary(boot), boot, 600000, datetime(2026, 1, 1)) is None


def test_queue_overflow_and_loss_notice():
    boot = uuid4()
    queue = CircularQueue()
    for sequence in range(161):
        queue.append(summary(boot, sequence))
    assert len(queue.records) == 144
    assert queue.records[0].sequence == 17
    assert queue.lost_count == 17
    receiver = SimulatedReceiver()
    queue.send_one(receiver)
    queue.report_loss(event(boot, 161, event_type="records_lost", lost_count=17))
    assert queue.records[-1].lost_count == 17
    for sequence in range(162, 180):
        queue.append(event(boot, sequence))
    assert sum(isinstance(item, Summary) for item in queue.records) == 143
    assert queue.lost_count == 20


def test_retry_conflict_and_restart():
    boot = uuid4()
    queue = CircularQueue(4)
    receiver = SimulatedReceiver()
    queue.append(summary(boot))
    assert queue.send_one(receiver, ack_received=False) == "ack_lost"
    assert len(queue.records) == 1
    assert queue.send_one(receiver) == "duplicate"
    assert not queue.records
    queue.append(summary(boot, temperature_last_c=4.5))
    assert queue.send_one(receiver) == "conflict"
    assert len(queue.records) == 1
    assert receiver.receive(summary(uuid4())) == "stored"
    assert len(receiver.records) == 2
