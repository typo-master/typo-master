from datetime import datetime, timezone

import pytest

from app.backend.storage import MySQLStorage


def test_mysql_storage_default_connection_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MYSQL_HOST", raising=False)
    monkeypatch.delenv("MYSQL_PORT", raising=False)
    monkeypatch.delenv("MYSQL_USER", raising=False)
    monkeypatch.delenv("MYSQL_PASSWORD", raising=False)
    monkeypatch.delenv("MYSQL_DATABASE", raising=False)

    storage = MySQLStorage.from_env()

    assert storage.host == "127.0.0.1"
    assert storage.port == 3306
    assert storage.user == "root"
    assert storage.password == "nopasswd"
    assert storage.database == "typomaster"


def test_mysql_storage_database_identifier_validation() -> None:
    with pytest.raises(ValueError):
        MySQLStorage(
            host="127.0.0.1",
            port=3306,
            user="root",
            password="nopasswd",
            database="bad-name",
        )


def test_mysql_storage_iso_datetime_roundtrip() -> None:
    original = "2026-03-23T12:34:56+00:00"

    mysql_dt = MySQLStorage._iso_to_mysql_datetime(original)
    result = MySQLStorage._mysql_datetime_to_iso(mysql_dt)

    assert isinstance(mysql_dt, datetime)
    assert mysql_dt.tzinfo is None
    assert result == original


def test_mysql_storage_load_json_invalid_payload() -> None:
    payload = MySQLStorage._load_json("{not json")
    assert payload == {"raw": "{not json"}


def test_mysql_storage_load_json_datetime_passthrough() -> None:
    value = datetime(2026, 3, 23, 0, 0, 0, tzinfo=timezone.utc)
    payload = MySQLStorage._load_json(value)
    assert payload == {"value": value}
