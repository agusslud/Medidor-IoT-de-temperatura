"""SQLite storage for v2 records, independent of the legacy telemetry table."""

import json
import sqlite3
from contextlib import closing

from .contract_v2 import Event, Summary
from .database import connect


def initialize_v2(connection: sqlite3.Connection) -> None:
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS telemetry_v2 (
          id INTEGER PRIMARY KEY,
          device_id TEXT NOT NULL,
          boot_id TEXT NOT NULL,
          sequence TEXT NOT NULL,
          record_type TEXT NOT NULL,
          received_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
          payload TEXT NOT NULL,
          UNIQUE(device_id, boot_id, sequence)
        );
        CREATE INDEX IF NOT EXISTS idx_v2_device_received
          ON telemetry_v2(device_id, received_at);
    """)
    connection.commit()


def save_record(database_path: str, record: Summary | Event) -> tuple[str, int]:
    # Per-request connections avoid sharing transactions between concurrent requests.
    payload = json.dumps(record.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    key = (record.device_id, str(record.boot_id), str(record.sequence))
    with closing(connect(database_path)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        existing = connection.execute(
            "SELECT id, payload FROM telemetry_v2 WHERE device_id=? AND boot_id=? AND sequence=?",
            key,
        ).fetchone()
        if existing:
            result = "duplicate" if existing["payload"] == payload else "conflict"
            return result, existing["id"]
        cursor = connection.execute(
            "INSERT INTO telemetry_v2(device_id, boot_id, sequence, record_type, payload) "
            "VALUES (?, ?, ?, ?, ?)", (*key, record.type, payload),
        )
        return "stored", int(cursor.lastrowid)
