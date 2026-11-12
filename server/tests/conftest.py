import pytest

from app.settings import settings


@pytest.fixture(autouse=True)
def database_path(tmp_path, monkeypatch):
    path = tmp_path / "test.db"
    monkeypatch.setattr(settings, "database_path", str(path))
    return path
