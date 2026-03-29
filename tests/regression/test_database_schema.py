"""
Database schema regression tests.
"""

import pytest


@pytest.mark.regression
class TestDatabaseSchema:
    """Test database schema stability."""

    def test_conversations_table_schema(self, storage):
        """Test conversations table schema."""
        # Try to create a conversation (validates schema)
        from datetime import datetime

        conv_id = "test-conv-123"
        created_at = datetime.utcnow().isoformat()

        storage.create_conversation(conv_id, created_at)

        # Verify it was created by trying to get messages
        messages = storage.get_conversation_messages(conv_id)
        assert messages is not None
        assert messages == []

    def test_messages_table_schema(self, storage):
        """Test conversation_messages table schema."""
        from datetime import datetime

        # Create conversation
        conv_id = "test-conv-messages"
        created_at = datetime.utcnow().isoformat()
        storage.create_conversation(conv_id, created_at)

        # Append message
        msg_at = datetime.utcnow().isoformat()
        storage.append_message(conv_id, "user", "Test message", msg_at)

        # Retrieve messages
        messages = storage.get_conversation_messages(conv_id)
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Test message"

    def test_workflow_tasks_table_schema(self, storage):
        """Test workflow_tasks table schema."""
        from datetime import datetime

        task_id = "test-task-123"
        created_at = datetime.utcnow().isoformat()

        storage.create_workflow_task(
            task_id=task_id,
            status="queued",
            created_at=created_at,
            updated_at=created_at,
        )

        # Retrieve task
        task = storage.get_workflow_task(task_id)
        assert task is not None
        assert task["task_id"] == task_id
        assert task["status"] == "queued"

    def test_workflow_task_update_schema(self, storage):
        """Test workflow task update schema."""
        from datetime import datetime

        # Create task
        task_id = "test-task-update"
        created_at = datetime.utcnow().isoformat()
        storage.create_workflow_task(
            task_id=task_id,
            status="queued",
            created_at=created_at,
            updated_at=created_at,
        )

        # Update task
        updated_at = datetime.utcnow().isoformat()
        storage.update_workflow_task(
            task_id=task_id,
            status="running",
            updated_at=updated_at,
            result={"progress": 50},
        )

        # Verify update
        task = storage.get_workflow_task(task_id)
        assert task["status"] == "running"
        assert task["result"]["progress"] == 50


@pytest.mark.regression
class TestDataTypeCompatibility:
    """Test data type compatibility."""

    def test_datetime_handling(self, storage):
        """Test datetime handling."""
        from datetime import datetime

        # Various datetime formats
        datetimes = [
            "2024-01-15T10:30:00",
            "2024-01-15T10:30:00+00:00",
            "2024-01-15T10:30:00Z",
        ]

        for dt_str in datetimes:
            conv_id = f"test-dt-{hash(dt_str) % 10000}"
            storage.create_conversation(conv_id, dt_str)

            messages = storage.get_conversation_messages(conv_id)
            assert messages is not None

    def test_unicode_handling(self, storage):
        """Test unicode content handling."""
        from datetime import datetime

        conv_id = "test-unicode"
        created_at = datetime.utcnow().isoformat()
        storage.create_conversation(conv_id, created_at)

        # Unicode content
        unicode_content = [
            "Hello World! 你好世界! 🌍",
            "日本語テスト",
            "Кириллица",
            "عربي",
            "🎉🎊🎁",
        ]

        for content in unicode_content:
            msg_at = datetime.utcnow().isoformat()
            storage.append_message(conv_id, "user", content, msg_at)

        messages = storage.get_conversation_messages(conv_id)
        assert len(messages) == len(unicode_content)

    def test_json_field_handling(self, storage):
        """Test JSON field handling in workflow tasks."""
        from datetime import datetime

        task_id = "test-json"
        created_at = datetime.utcnow().isoformat()

        # Various JSON structures
        results = [
            {"simple": "value"},
            {"nested": {"key": "value"}},
            {"array": [1, 2, 3]},
            {"mixed": {"array": [1, 2, {"nested": "value"}]}},
            None,
        ]

        for i, result in enumerate(results):
            tid = f"{task_id}-{i}"
            storage.create_workflow_task(
                task_id=tid,
                status="succeeded",
                created_at=created_at,
                updated_at=created_at,
                result=result,
            )

            task = storage.get_workflow_task(tid)
            if result is None:
                assert task["result"] is None
            else:
                assert task["result"] is not None
