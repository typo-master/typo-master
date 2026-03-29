"""
Unit testing utilities and fixtures.
"""

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_mysql_storage():
    """Mock MySQLStorage for unit tests."""
    storage = MagicMock()
    storage.create_conversation.return_value = None
    storage.get_conversation_messages.return_value = []
    storage.append_message.return_value = None
    storage.create_workflow_task.return_value = None
    storage.update_workflow_task.return_value = None
    storage.get_workflow_task.return_value = {
        "task_id": "test-task-1",
        "status": "queued",
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00",
        "result": None,
        "error": None,
    }
    return storage


@pytest.fixture
def mock_agent_runtime():
    """Mock agent_runtime for unit tests."""
    runtime = MagicMock()
    runtime.chat.return_value = {
        "success": True,
        "reply": "Test reply",
        "mode": "skill",
    }
    runtime.execute_skill.return_value = {
        "success": True,
        "result": {"test": "data"},
    }
    runtime.run_workflow.return_value = {
        "success": True,
        "result": {"workflow": "completed"},
    }
    return runtime
