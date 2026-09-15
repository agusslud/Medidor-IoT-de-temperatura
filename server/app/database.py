import sqlite3
from pathlib import Path

from .schemas import TelemetryIn


def connect(database_path: str) -> sqlite3.Connection:
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    # FastAPI executes synchronous handlers in a worker thread; SQLite's default
    # thread affinity would reject that connection after lifespan initialization.
    connection = sqlite3.connect(database_path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection


def initialize(connection: sqlite3.Connection) -> None:
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS telemetry (
          id INTEGER PRIMARY KEY, received_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          device_id TEXT NOT NULL, temperature REAL, raw_temperature REAL,
          offset_applied REAL NOT NULL, power_source TEXT NOT NULL,
          sensor_status TEXT NOT NULL, buffered_records INTEGER NOT NULL DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_telemetry_device_received
          ON telemetry(device_id, received_at DESC);
        CREATE TABLE IF NOT EXISTS alerts (
          id INTEGER PRIMARY KEY, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          device_id TEXT NOT NULL, alert_type TEXT NOT NULL, resolved_at TEXT
        );
        CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT NOT NULL);
    """)
    connection.commit()


def save_telemetry(connection: sqlite3.Connection, item: TelemetryIn) -> int:
    cursor = connection.execute(
        """INSERT INTO telemetry (device_id, temperature, raw_temperature, offset_applied,
        power_source, sensor_status, buffered_records) VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (item.device_id, item.temperature, item.raw_temperature, item.offset_applied,
         item.power_source, item.sensor_status, item.buffered_records),
    )
    connection.commit()
    return int(cursor.lastrowid)


def history(connection: sqlite3.Connection, device_id: str, limit: int) -> list[sqlite3.Row]:
    return connection.execute(
        "SELECT * FROM telemetry WHERE device_id = ? ORDER BY received_at DESC LIMIT ?",
        (device_id, limit),
    ).fetchall()


def set_config(connection: sqlite3.Connection, key: str, value: str) -> None:
    connection.execute(
        "INSERT INTO config(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    connection.commit()
