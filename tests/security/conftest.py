"""
Security test fixtures.
"""

import sys
from unittest.mock import MagicMock, AsyncMock, Mock

# Clear module cache to ensure fresh imports
for mod in list(sys.modules.keys()):
    if mod.startswith('app'):
        del sys.modules[mod]

# Setup mocks before importing app
_mock_agent_runtime = MagicMock()
_mock_agent_runtime.initialize = AsyncMock(return_value=None)
_mock_agent_runtime.shutdown = AsyncMock(return_value=None)
_mock_agent_runtime.execute_sql = AsyncMock(side_effect=lambda database, query, **kwargs: {
    "success": True,
    "result": [],
} if "DROP" not in query.upper() and "DELETE" not in query.upper() else {
    "success": False,
    "error": "Write operations not allowed in read_only mode",
})
_mock_agent_runtime.chat = AsyncMock(return_value={
    "success": True,
    "reply": "Test reply",
    "mode": "skill",
})
_mock_agent_runtime.execute_skill = AsyncMock(side_effect=lambda skill_name, params, **kwargs: {
    "success": False,
    "error": "Permission denied: dangerous command blocked",
} if skill_name == "system_command" else {
    "success": True,
    "result": {"test": "data"},
})
_mock_agent_runtime.list_mcp_servers = AsyncMock(return_value={"servers": []})
_mock_agent_runtime.delete_mcp_server = AsyncMock(return_value={"success": True})
_mock_agent_runtime.get_permissions = Mock(return_value={})
_mock_agent_runtime.update_permissions = Mock(return_value={"success": True})

_mock_runtime_module = MagicMock()
_mock_runtime_module.agent_runtime = _mock_agent_runtime
_mock_runtime_module.WorkflowRunRequest = MagicMock

_mock_storage_module = MagicMock()
_mock_storage_module.MySQLStorage = MagicMock()
_mock_storage_module.MySQLStorage.from_env = MagicMock(return_value=MagicMock())
_mock_storage_module.ConversationNotFoundError = KeyError
_mock_storage_module.WorkflowTaskNotFoundError = KeyError

_mock_mcp_module = MagicMock()
_mock_mcp_module.create_mcp_router = MagicMock(return_value=MagicMock())

sys.modules['app.agent.runtime'] = _mock_runtime_module
sys.modules['app.backend.storage'] = _mock_storage_module
sys.modules['app.agent.mcp_sse_server'] = _mock_mcp_module

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def security_client():
    """Test client for security tests."""
    from app.backend.main import app
    return TestClient(app)


@pytest.fixture
def sql_injection_payloads():
    """Common SQL injection payloads."""
    return [
        "' OR '1'='1",
        "' OR '1'='1' --",
        "' OR '1'='1' /*",
        "'; DROP TABLE conversations; --",
        "1; DROP TABLE conversations--",
        "1; DELETE FROM conversations WHERE '1'='1",
        "' UNION SELECT * FROM conversations--",
        "' UNION SELECT null, username, password FROM users--",
        "1 AND 1=1",
        "1 AND 1=2",
        "1' AND 1=1--",
        "1' AND 1=2--",
    ]


@pytest.fixture
def xss_payloads():
    """Common XSS payloads."""
    return [
        "<script>alert('xss')</script>",
        "<img src=x onerror=alert('xss')>",
        "<body onload=alert('xss')>",
        "javascript:alert('xss')",
        "<svg onload=alert('xss')>",
        "<iframe src=javascript:alert('xss')>",
    ]


@pytest.fixture
def traversal_payloads():
    """Directory traversal payloads."""
    return [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\config\\sam",
        "....//....//....//etc/passwd",
        "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
    ]
