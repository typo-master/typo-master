"""
Mock utilities for unit tests.
"""

from unittest.mock import MagicMock, patch
import pytest


def create_mock_storage():
    """Create a mock MySQLStorage."""
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


def create_mock_agent_runtime():
    """Create a mock agent_runtime."""
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
    runtime.get_capabilities.return_value = {
        "skills": [],
        "mcp_servers": [],
    }
    runtime.list_skills.return_value = []
    runtime.get_permissions.return_value = {}
    runtime.update_permissions.return_value = {"success": True}
    return runtime


@pytest.fixture
def mock_storage():
    """Mock storage fixture."""
    return create_mock_storage()


@pytest.fixture
def mock_agent_runtime():
    """Mock agent runtime fixture."""
    return create_mock_agent_runtime()
