"""In-memory simulator only: no production storage, hardware or network."""

from collections import deque
from dataclasses import dataclass, field
from typing import Literal

from .contract_v2 import Event, Summary

Record = Summary | Event
Key = tuple[str, str, int]


def record_key(record: Record) -> Key:
    return (record.device_id, str(record.boot_id), record.sequence)


@dataclass
class SimulatedReceiver:
    records: dict[Key, Record] = field(default_factory=dict)

    def receive(self, record: Record) -> Literal["stored", "duplicate", "conflict"]:
        key = record_key(record)
        existing = self.records.get(key)
        if existing is not None:
            return "duplicate" if existing == record else "conflict"
        self.records[key] = record.model_copy(deep=True)
        return "stored"


class CircularQueue:
    def __init__(self, summary_capacity: int = 144, event_capacity: int = 16):
        if summary_capacity < 1 or event_capacity < 1:
            raise ValueError("capacities must be positive")
        self.summary_capacity = summary_capacity
        self.event_capacity = event_capacity
        self.records: deque[Record] = deque()
        self.lost_count = 0

    def append(self, record: Record) -> None:
        record_type = Summary if isinstance(record, Summary) else Event
        capacity = self.summary_capacity if record_type is Summary else self.event_capacity
        matching = [item for item in self.records if isinstance(item, record_type)]
        if len(matching) == capacity:
            self.records.remove(matching[0])
            self.lost_count += 1
        self.records.append(record.model_copy(deep=True))

    def send_one(self, receiver: SimulatedReceiver, *, ack_received: bool = True) -> str:
        if not self.records:
            return "empty"
        result = receiver.receive(self.records[0])
        if ack_received and result in ("stored", "duplicate"):
            self.records.popleft()
        return result if ack_received else "ack_lost"

    def report_loss(self, record: Event) -> None:
        """Queue a cumulative notice after space is available; count never resets."""
        if record.event_type != "records_lost" or record.lost_count != self.lost_count:
            raise ValueError("loss notice must match current cumulative loss")
        if sum(isinstance(item, Event) for item in self.records) == self.event_capacity:
            raise ValueError("loss notice requires an available slot")
        self.append(record)
