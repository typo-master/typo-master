"""
Pytest configuration and fixtures for TypoAgent tests.
"""

import sys

# Clear any cached app modules before setting up mocks
# This ensures tests get fresh imports
for mod in list(sys.modules.keys()):
    if mod.startswith('app'):
        del sys.modules[mod]

import pytest
import pytest_asyncio
import asyncio
import tempfile
import os
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock

# Module-level mocks - set up BEFORE any app imports
# Create mock runtime
_mock_agent_runtime = MagicMock()
_mock_agent_runtime.initialize = AsyncMock(return_value=None)
_mock_agent_runtime.shutdown = AsyncMock(return_value=None)
_mock_agent_runtime.chat = AsyncMock(return_value={
    "success": True,
    "reply": "Test reply",
    "mode": "skill",
})

# Skill execution with security check for dangerous commands
async def _mock_execute_skill(skill_name, params, **kwargs):
    """Mock skill execution with security validation."""
    # Block dangerous system commands
    if skill_name == "system_command" or skill_name == "dangerous_skill":
        command = params.get("command", "")
        if any(dangerous in command.lower() for dangerous in ["rm -rf", "rm -fr", "del /f", "format"]):
            return {
                "success": False,
                "error": "Permission denied: dangerous command blocked",
            }
    return {
        "success": True,
        "result": {"test": "data"},
    }

_mock_agent_runtime.execute_skill = AsyncMock(side_effect=_mock_execute_skill)
_mock_agent_runtime.run_workflow = AsyncMock(return_value={
    "success": True,
    "result": {"workflow": "completed"},
})
_mock_agent_runtime.get_capabilities = AsyncMock(return_value={
    "skills": [],
    "mcp_servers": [],
})
_mock_agent_runtime.list_skills = AsyncMock(return_value=[])
_mock_agent_runtime.upsert_skill = AsyncMock(return_value={"success": True})
_mock_agent_runtime.delete_skill = AsyncMock(return_value={"success": True})
_mock_agent_runtime.list_mcp_servers = AsyncMock(return_value={"servers": []})
_mock_agent_runtime.list_mcp_catalog = AsyncMock(return_value={"catalog": []})
_mock_agent_runtime.install_mcp_from_catalog = AsyncMock(return_value={"success": True})
_mock_agent_runtime.upsert_mcp_server = AsyncMock(return_value={"success": True})
_mock_agent_runtime.delete_mcp_server = AsyncMock(return_value={"success": True})
_mock_agent_runtime.probe_mcp_server = AsyncMock(return_value={"success": True})
_mock_agent_runtime.execute_mcp_tool = AsyncMock(return_value={"success": True})
_mock_agent_runtime.execute_sql = AsyncMock(side_effect=lambda database, query, **kwargs: {
    "success": True,
    "result": [],
} if "DROP" not in query.upper() and "DELETE" not in query.upper() else {
    "success": False,
    "error": "Write operations not allowed in read_only mode",
})
_mock_agent_runtime.get_permissions = Mock(return_value={})
_mock_agent_runtime.update_permissions = Mock(return_value={"success": True})


# Create proper exception classes that can be caught
class MockConversationNotFoundError(KeyError):
    pass


class MockWorkflowTaskNotFoundError(KeyError):
    pass


# Statefule in-memory storage mock for regression tests
class MemoryStorageMock:
    """In-memory storage mock that maintains state for regression tests."""

    def __init__(self, *args, **kwargs):
        self._conversations = {}  # conv_id -> created_at
        self._messages = {}  # conv_id -> list of messages
        self._workflow_tasks = {}  # task_id -> task_data
        self.database = kwargs.get('database', 'test_db')

    @classmethod
    def from_env(cls):
        return cls()

    def initialize(self):
        # Clear all state on initialization
        self._conversations.clear()
        self._messages.clear()
        self._workflow_tasks.clear()

    def create_conversation(self, conversation_id: str, created_at: str) -> None:
        self._conversations[conversation_id] = created_at
        self._messages[conversation_id] = []

    def get_conversation_messages(self, conversation_id: str):
        if conversation_id not in self._conversations:
            return None
        return self._messages.get(conversation_id, [])

    def append_message(self, conversation_id: str, role: str, content: str, created_at: str) -> None:
        if conversation_id not in self._conversations:
            raise MockConversationNotFoundError(f"conversation not found: {conversation_id}")
        self._messages[conversation_id].append({
            "role": role,
            "content": content,
            "created_at": created_at,
        })

    def create_workflow_task(self, task_id: str, status: str, created_at: str, updated_at: str, result=None, error=None) -> None:
        self._workflow_tasks[task_id] = {
            "task_id": task_id,
            "status": status,
            "created_at": created_at,
            "updated_at": updated_at,
            "result": result,
            "error": error,
        }

    def update_workflow_task(self, task_id: str, status: str, updated_at: str, result=None, error=None) -> None:
        if task_id not in self._workflow_tasks:
            raise MockWorkflowTaskNotFoundError(f"task not found: {task_id}")
        self._workflow_tasks[task_id].update({
            "status": status,
            "updated_at": updated_at,
            "result": result,
            "error": error,
        })

    def get_workflow_task(self, task_id: str):
        task = self._workflow_tasks.get(task_id)
        if task is None:
            return None
        # Return a copy to prevent external mutation
        return dict(task)


# Create singleton instance
_memory_storage = MemoryStorageMock()

# Legacy mock storage instance for backward compatibility
_mock_storage_instance = MagicMock()
_mock_storage_instance.initialize.return_value = None
_mock_storage_instance.create_conversation.return_value = None
_mock_storage_instance.get_conversation_messages.return_value = []
_mock_storage_instance.append_message.return_value = None
_mock_storage_instance.create_workflow_task.return_value = None
_mock_storage_instance.update_workflow_task.return_value = None
_mock_storage_instance.get_workflow_task.return_value = {
    "task_id": "test-task-1",
    "status": "queued",
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00",
    "result": None,
    "error": None,
}

_mock_storage_class = MagicMock()
_mock_storage_class.from_env.return_value = _mock_storage_instance

# Create mock modules
_mock_runtime_module = MagicMock()
_mock_runtime_module.agent_runtime = _mock_agent_runtime
_mock_runtime_module.WorkflowRunRequest = MagicMock

_mock_storage_module = MagicMock()
_mock_storage_module.MySQLStorage = _mock_storage_class
_mock_storage_module.ConversationNotFoundError = MockConversationNotFoundError
_mock_storage_module.WorkflowTaskNotFoundError = MockWorkflowTaskNotFoundError

# Inject mocks into sys.modules BEFORE any imports
# Only mock the specific modules we need
sys.modules['app.agent.runtime'] = _mock_runtime_module

# NOTE: We do NOT mock app.backend.storage here because some tests need the real module.
# The storage mock is injected per-test or per-module as needed.

# Create a proper mock for mcp_sse_server
_mock_mcp_module = MagicMock()
_mock_mcp_module.create_mcp_router = MagicMock(return_value=MagicMock())
sys.modules['app.agent.mcp_sse_server'] = _mock_mcp_module

# Pytest configuration
pytest_plugins = ['pytest_asyncio']


@pytest.fixture(autouse=True)
def clear_module_cache():
    """Clear app module cache before each test to ensure fresh imports."""
    # Clear app modules (but keep the mock setup)
    for mod in list(sys.modules.keys()):
        if mod.startswith('app.backend') and mod != 'app.backend.storage':
            del sys.modules[mod]
        if mod.startswith('app.agent'):
            del sys.modules[mod]
    # Re-inject mocks after clearing
    sys.modules['app.agent.runtime'] = _mock_runtime_module
    sys.modules['app.agent.mcp_sse_server'] = _mock_mcp_module
    yield


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp = tempfile.mkdtemp()
    yield temp
    import shutil
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def temp_file(temp_dir):
    """Create a temporary file for tests."""
    file_path = os.path.join(temp_dir, "test_file.txt")
    with open(file_path, 'w') as f:
        f.write("Test content")
    return file_path


@pytest.fixture
def temp_repo(temp_dir):
    """Create a temporary git repository for tests."""
    repo_path = os.path.join(temp_dir, "test_repo")
    os.makedirs(repo_path)

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo_path, capture_output=True)

    # Create a test file
    test_file = os.path.join(repo_path, "README.md")
    with open(test_file, 'w') as f:
        f.write("# Test Repository\n\nThis is a test file.\n")

    # Add and commit
    subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"],
                   cwd=repo_path, capture_output=True)

    return repo_path


@pytest.fixture
def mock_github_token():
    """Mock GitHub token for tests."""
    return "mock_github_token_12345"


@pytest.fixture
def sample_typo_content():
    """Sample content with typos for testing."""
    return """
# Test Document

This is a document with some helloo words and teh typos.

The quick brown fox jumps over the lazy dog.

Web3 is greate for defi and nft projects.
"""


@pytest.fixture
def sample_clean_content():
    """Sample clean content without typos."""
    return """
# Clean Document

This is a clean document without any typos.

The quick brown fox jumps over the lazy dog.

Ethereum is a great blockchain for defi applications.
"""


@pytest.fixture
def client():
    """Create a test client for FastAPI app with mocked dependencies."""
    from fastapi.testclient import TestClient

    # Reset memory storage state before each test
    _memory_storage.initialize()

    # Use MemoryStorageMock for regression tests (stateful)
    _mock_storage_module.MySQLStorage = lambda *args, **kwargs: _memory_storage
    _mock_storage_module.MySQLStorage.from_env = lambda: _memory_storage

    # Inject storage mock BEFORE importing main
    sys.modules['app.backend.storage'] = _mock_storage_module

    # Clear any cached app modules to ensure fresh import
    for mod in list(sys.modules.keys()):
        if mod.startswith('app.backend') and mod != 'app.backend.storage':
            del sys.modules[mod]

    # Import main - it will use our module-level mocks
    from app.backend import main as main_module

    # Create test client
    test_client = TestClient(main_module.app)

    yield test_client
    test_client.close()

    # Clean up: remove the mock so other tests can import the real module
    for mod in list(sys.modules.keys()):
        if mod.startswith('app.backend'):
            del sys.modules[mod]


@pytest.fixture
def mock_storage():
    """Return the module-level mock storage instance."""
    return _mock_storage_instance


@pytest.fixture
def mock_agent_runtime():
    """Return the module-level mock agent runtime."""
    return _mock_agent_runtime


@pytest.fixture
def storage():
    """Create a MemoryStorage mock instance for schema regression tests."""
    # Use a fresh instance for each test
    fresh_mock = MemoryStorageMock()
    fresh_mock.initialize()
    return fresh_mock


@pytest.fixture
def spell_checker():
    """Create a spell checker instance."""
    try:
        from src.tools.spell_tools import SpellChecker
        return SpellChecker()
    except ImportError:
        return None


@pytest.fixture
def typo_scanner():
    """Create a typo scanner instance."""
    try:
        from src.tools.repo_typo_scanner import RepoTypoScanner
        return RepoTypoScanner()
    except ImportError:
        return None


# Markers for test categories
def pytest_collection_modifyitems(config, items):
    """Modify test collection to add categories."""
    for item in items:
        # Auto-mark based on path
        path = str(item.fspath)
        if "tests/unit" in path:
            item.add_marker(pytest.mark.unit)
        elif "tests/regression" in path:
            item.add_marker(pytest.mark.regression)
        elif "tests/security" in path:
            item.add_marker(pytest.mark.security)
        elif "tests/integration" in path or "test_integration" in path:
            item.add_marker(pytest.mark.integration)

        # Critical tests are in regression test_api_contracts or test_critical_workflows
        if "test_api_contracts" in path or "test_critical_workflows" in path:
            item.add_marker(pytest.mark.critical)
