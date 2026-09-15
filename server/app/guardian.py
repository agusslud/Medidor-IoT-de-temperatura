"""Periodic heartbeat check, intended to be invoked by systemd every minute."""

from .database import connect, initialize
from .settings import settings


def main() -> None:
    connection = connect(settings.database_path)
    initialize(connection)
    # TODO: Find devices whose last telemetry exceeds heartbeat_timeout_seconds,
    # open/resolve SERVER_OFFLINE alerts idempotently, and notify via Telegram.
    connection.close()


if __name__ == "__main__":
    main()
