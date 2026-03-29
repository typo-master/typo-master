"""
Unit tests for MySQLStorage.
"""

import sys
# Remove any mocks from sys.modules before importing
for mod in list(sys.modules.keys()):
    if mod.startswith('app.backend.storage'):
        del sys.modules[mod]

import pytest
from unittest.mock import MagicMock, patch, mock_open
from datetime import datetime

from app.backend.storage import MySQLStorage, ConversationNotFoundError, WorkflowTaskNotFoundError


@pytest.fixture(autouse=True)
def cleanup_storage_module():
    """Ensure storage module is clean before each test."""
    # Clear any cached storage module
    for mod in list(sys.modules.keys()):
        if mod.startswith('app.backend.storage'):
            del sys.modules[mod]
    # Re-import the real module
    import app.backend.storage
    yield


@pytest.mark.unit
class TestMySQLStorage:
    """Test MySQLStorage class."""

    @pytest.fixture
    def storage(self):
        """Create MySQLStorage instance with test config."""
        return MySQLStorage(
            host="localhost",
            port=3306,
            user="test",
            password="test",
            database="test_db",
        )

    @pytest.fixture
    def mock_connection(self):
        """Mock database connection with proper context manager support."""
        cursor = MagicMock()
        # Configure cursor as a context manager
        cursor.__enter__ = MagicMock(return_value=cursor)
        cursor.__exit__ = MagicMock(return_value=False)

        conn = MagicMock()
        # Configure conn.cursor() to return a context manager (the cursor itself)
        conn.cursor = MagicMock(return_value=cursor)
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)

        return conn, cursor

    def test_init_with_valid_database(self):
        """Test initialization with valid database name."""
        storage = MySQLStorage(
            host="localhost",
            port=3306,
            user="test",
            password="test",
            database="valid_db_name",
        )
        assert storage.database == "valid_db_name"

    def test_init_with_invalid_database(self):
        """Test initialization with invalid database name."""
        with pytest.raises(ValueError):
            MySQLStorage(
                host="localhost",
                port=3306,
                user="test",
                password="test",
                database="invalid-db-name!",
            )

    @patch("app.backend.storage.pymysql.connect")
    def test_create_conversation(self, mock_connect, storage, mock_connection):
        """Test creating a conversation."""
        conn, cursor = mock_connection
        mock_connect.return_value = conn

        storage.create_conversation("conv-123", "2024-01-01T00:00:00")

        cursor.execute.assert_called_once()
        conn.commit.assert_called_once()
        conn.close.assert_called_once()

    @patch("app.backend.storage.pymysql.connect")
    def test_get_conversation_messages(self, mock_connect, storage, mock_connection):
        """Test getting conversation messages."""
        conn, cursor = mock_connection
        mock_connect.return_value = conn

        # First query: conversation exists
        cursor.fetchone.return_value = {"conversation_id": "conv-123"}
        # Second query: messages
        cursor.fetchall.return_value = [
            {"role": "user", "content": "Hello", "created_at": datetime.now()},
        ]

        messages = storage.get_conversation_messages("conv-123")

        assert messages is not None
        assert len(messages) == 1
        assert messages[0]["role"] == "user"

    @patch("app.backend.storage.pymysql.connect")
    def test_get_conversation_messages_not_found(self, mock_connect, storage, mock_connection):
        """Test getting messages for non-existent conversation."""
        conn, cursor = mock_connection
        mock_connect.return_value = conn
        cursor.fetchone.return_value = None

        messages = storage.get_conversation_messages("nonexistent")

        assert messages is None

    @patch("app.backend.storage.pymysql.connect")
    def test_append_message(self, mock_connect, storage, mock_connection):
        """Test appending a message."""
        conn, cursor = mock_connection
        mock_connect.return_value = conn

        storage.append_message("conv-123", "user", "Hello", "2024-01-01T00:00:00")

        cursor.execute.assert_called_once()
        conn.commit.assert_called_once()

    @patch("app.backend.storage.pymysql.connect")
    def test_create_workflow_task(self, mock_connect, storage, mock_connection):
        """Test creating a workflow task."""
        conn, cursor = mock_connection
        mock_connect.return_value = conn

        storage.create_workflow_task(
            task_id="task-123",
            status="queued",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )

        cursor.execute.assert_called_once()
        conn.commit.assert_called_once()

    @patch("app.backend.storage.pymysql.connect")
    def test_update_workflow_task(self, mock_connect, storage, mock_connection):
        """Test updating a workflow task."""
        conn, cursor = mock_connection
        mock_connect.return_value = conn
        cursor.rowcount = 1

        storage.update_workflow_task(
            task_id="task-123",
            status="running",
            updated_at="2024-01-01T00:00:00",
        )

        cursor.execute.assert_called_once()
        conn.commit.assert_called_once()

    @patch("app.backend.storage.pymysql.connect")
    def test_update_workflow_task_not_found(self, mock_connect, storage, mock_connection):
        """Test updating non-existent task."""
        conn, cursor = mock_connection
        mock_connect.return_value = conn
        cursor.rowcount = 0

        with pytest.raises(WorkflowTaskNotFoundError):
            storage.update_workflow_task(
                task_id="nonexistent",
                status="running",
                updated_at="2024-01-01T00:00:00",
            )

    @patch("app.backend.storage.pymysql.connect")
    def test_get_workflow_task(self, mock_connect, storage, mock_connection):
        """Test getting a workflow task."""
        conn, cursor = mock_connection
        mock_connect.return_value = conn
        cursor.fetchone.return_value = {
            "task_id": "task-123",
            "status": "queued",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "result_json": '{"success": true}',
            "error_text": None,
        }

        task = storage.get_workflow_task("task-123")

        assert task is not None
        assert task["task_id"] == "task-123"
        assert task["status"] == "queued"
        assert task["result"]["success"] is True

    @patch("app.backend.storage.pymysql.connect")
    def test_get_workflow_task_not_found(self, mock_connect, storage, mock_connection):
        """Test getting non-existent task."""
        conn, cursor = mock_connection
        mock_connect.return_value = conn
        cursor.fetchone.return_value = None

        task = storage.get_workflow_task("nonexistent")

        assert task is None

    def test_iso_to_mysql_datetime(self, storage):
        """Test ISO datetime conversion."""
        from datetime import datetime

        result = MySQLStorage._iso_to_mysql_datetime("2024-01-15T10:30:00+00:00")
        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_mysql_datetime_to_iso(self, storage):
        """Test MySQL datetime to ISO conversion."""
        from datetime import datetime

        now = datetime.utcnow()
        result = MySQLStorage._mysql_datetime_to_iso(now)
        assert isinstance(result, str)
        assert "2024" in result or "2025" in result or "2026" in result

    def test_dump_json(self, storage):
        """Test JSON dumping."""
        assert MySQLStorage._dump_json(None) is None
        assert MySQLStorage._dump_json({"key": "value"}) == '{"key": "value"}'

    def test_load_json(self, storage):
        """Test JSON loading."""
        assert MySQLStorage._load_json(None) is None
        assert MySQLStorage._load_json('{"key": "value"}') == {"key": "value"}
        assert MySQLStorage._load_json("plain string") == {"raw": "plain string"}
