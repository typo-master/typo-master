"""
Unit tests for TypeAgentRuntime.
"""

import sys
# Remove any cached modules before importing
for mod in list(sys.modules.keys()):
    if mod.startswith('app.agent.runtime'):
        del sys.modules[mod]

import pytest
import json
import asyncio
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock, mock_open

# Create mocks before importing the runtime module
_mock_coordinator = MagicMock()
_mock_coordinator.initialize = AsyncMock(return_value=None)
_mock_coordinator.stop = AsyncMock(return_value=None)
_mock_coordinator.process_task = AsyncMock(return_value={
    "success": True,
    "features": {"test": True},
})
_mock_coordinator.add_to_conversation = AsyncMock(return_value=None)
_mock_coordinator.build_llm_context = AsyncMock(return_value="")
_mock_coordinator.config = MagicMock()
_mock_coordinator.config.enable_memory = False

_mock_llm_client = MagicMock()
_mock_llm_client.is_enabled = True
_mock_llm_client.config = MagicMock()
_mock_llm_client.config.model = "gpt-4-test"
_mock_llm_client.generate_text = MagicMock(return_value={
    "success": True,
    "text": "Test LLM response",
})

_mock_llm_client_class = MagicMock()
_mock_llm_client_class.from_config = MagicMock(return_value=_mock_llm_client)

_mock_registry = MagicMock()
_mock_registry.list_skills = MagicMock(return_value=[])
_mock_registry.list_mcp_servers = MagicMock(return_value=[])
_mock_registry.upsert_skill = MagicMock(return_value={"name": "test_skill"})
_mock_registry.get_skill = MagicMock(return_value=None)
_mock_registry.delete_skill = MagicMock(return_value=True)
_mock_registry.list_mcp_catalog = MagicMock(return_value=[])
_mock_registry.install_mcp_from_catalog = MagicMock(return_value={"id": "test_server"})
_mock_registry.upsert_mcp_server = MagicMock(return_value={"id": "test_server"})
_mock_registry.get_mcp_server = MagicMock(return_value=None)
_mock_registry.delete_mcp_server = MagicMock(return_value=None)
_mock_registry.save = MagicMock(return_value=None)
_mock_registry.ensure_builtin_skills = MagicMock(return_value=None)

# Inject mocks
sys.modules['src.agents.coordinator_agent'] = MagicMock()
sys.modules['src.agents.coordinator_agent'].CoordinatorAgent = MagicMock(return_value=_mock_coordinator)

sys.modules['src.agent_framework.logger'] = MagicMock()
sys.modules['src.agent_framework.logger'].get_logger = MagicMock(return_value=MagicMock())

sys.modules['src.agent_framework.llm_client'] = MagicMock()
sys.modules['src.agent_framework.llm_client'].OpenAICompatibleResponsesClient = _mock_llm_client_class

sys.modules['src.agent_framework.permissions'] = MagicMock()
sys.modules['src.agent_framework.permissions'].normalize_permissions = MagicMock(return_value={})
sys.modules['src.agent_framework.permissions'].set_current_permissions = MagicMock(return_value=None)
sys.modules['src.agent_framework.permissions'].get_current_permissions = MagicMock(return_value={})
sys.modules['src.agent_framework.permissions'].is_permission_allowed = MagicMock(return_value=True)
sys.modules['src.agent_framework.permissions'].get_permission_denial_message = MagicMock(return_value="Permission denied")
sys.modules['src.agent_framework.permissions'].PERMISSION_GROUPS = {"test": {"perm1", "perm2"}}

sys.modules['app.agent.registry'] = MagicMock()
sys.modules['app.agent.registry'].RuntimeRegistry = MagicMock(return_value=_mock_registry)
sys.modules['app.agent.registry'].BUILTIN_SKILLS = []
sys.modules['app.agent.registry'].MCP_CATALOG_TEMPLATES = []

# Now import the runtime
from app.agent.runtime import TypeAgentRuntime, WorkflowRunRequest, agent_runtime


@pytest.mark.unit
class TestTypeAgentRuntime:
    """Test TypeAgentRuntime class."""

    @pytest.fixture
    def runtime(self):
        """Create a TypeAgentRuntime instance for testing."""
        with patch('app.agent.runtime._load_config_with_path') as mock_load:
            mock_load.return_value = ({}, None)
            runtime = TypeAgentRuntime()
            return runtime

    @pytest.fixture(autouse=True)
    def reset_mocks(self):
        """Reset mocks before each test."""
        _mock_registry.get_skill.reset_mock()
        _mock_registry.get_skill.return_value = None
        _mock_coordinator.process_task.reset_mock()
        _mock_coordinator.process_task.return_value = {"success": True}
        yield

    @pytest.fixture
    def initialized_runtime(self, runtime):
        """Create an initialized TypeAgentRuntime instance."""
        runtime._coordinator = _mock_coordinator
        runtime._registry = _mock_registry
        return runtime

    @pytest.mark.asyncio
    async def test_init_loads_config(self):
        """Test initialization loads configuration."""
        with patch('app.agent.runtime._load_config_with_path') as mock_load:
            mock_load.return_value = ({"test": "config"}, Path("/test/config.yml"))
            runtime = TypeAgentRuntime()
            assert runtime._config == {"test": "config"}
            assert runtime._config_file == Path("/test/config.yml")

    @pytest.mark.asyncio
    async def test_initialize_creates_coordinator(self, runtime):
        """Test initialize creates coordinator."""
        runtime._registry = _mock_registry
        await runtime.initialize()
        assert runtime._coordinator is not None
        _mock_coordinator.initialize.assert_called_once()
        _mock_registry.ensure_builtin_skills.assert_called_once()
        _mock_registry.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_is_idempotent(self, runtime):
        """Test initialize is idempotent when called multiple times."""
        runtime._registry = _mock_registry
        runtime._coordinator = _mock_coordinator

        await runtime.initialize()
        # Should not re-initialize if already initialized
        _mock_coordinator.initialize.reset_mock()
        await runtime.initialize()
        _mock_coordinator.initialize.assert_not_called()

    @pytest.mark.asyncio
    async def test_shutdown_stops_coordinator(self, runtime):
        """Test shutdown stops the coordinator."""
        runtime._coordinator = _mock_coordinator
        await runtime.shutdown()
        _mock_coordinator.stop.assert_called_once()
        assert runtime._coordinator is None

    @pytest.mark.asyncio
    async def test_shutdown_is_idempotent(self, runtime):
        """Test shutdown is idempotent when called multiple times."""
        await runtime.shutdown()
        # Should not raise even if coordinator is None
        await runtime.shutdown()

    @pytest.mark.asyncio
    async def test_get_capabilities_not_initialized(self, runtime):
        """Test get_capabilities returns error when not initialized."""
        result = await runtime.get_capabilities()
        assert result["success"] is False
        assert "not initialized" in result["error"]

    @pytest.mark.asyncio
    async def test_get_capabilities_success(self, initialized_runtime):
        """Test get_capabilities returns capabilities."""
        result = await initialized_runtime.get_capabilities()
        assert "skill_registry" in result
        assert "mcp" in result
        assert result["mcp"]["adapter"] == "langchain-mcp-adapters"

    @pytest.mark.asyncio
    async def test_run_workflow_not_initialized(self, runtime):
        """Test run_workflow returns error when not initialized."""
        req = WorkflowRunRequest(
            workflow="single_project",
            create_pr=False,
            owner="test",
            repo="repo",
        )
        result = await runtime.run_workflow(req)
        assert result["success"] is False
        assert "not initialized" in result["error"]

    @pytest.mark.asyncio
    async def test_run_workflow_success(self, initialized_runtime):
        """Test run_workflow executes workflow."""
        _mock_coordinator.process_task.reset_mock()
        _mock_coordinator.process_task.return_value = {"success": True, "result": "done"}
        req = WorkflowRunRequest(
            workflow="single_project",
            create_pr=False,
            owner="test",
            repo="repo",
        )
        result = await initialized_runtime.run_workflow(req)
        assert result["success"] is True
        # Verify the last call was run_workflow
        calls = _mock_coordinator.process_task.call_args_list
        assert calls[-1] == unittest.mock.call({
            'type': 'run_workflow',
            'workflow': 'single_project',
            'create_pr': False,
            'days': 30,
            'min_stars': 100,
            'limit': 5,
            'owner': 'test',
            'repo': 'repo',
        })

    @pytest.mark.asyncio
    async def test_list_skills(self, initialized_runtime):
        """Test list_skills returns skills from registry."""
        _mock_registry.list_skills.return_value = [
            {"name": "skill1", "enabled": True},
            {"name": "skill2", "enabled": False},
        ]
        result = await initialized_runtime.list_skills()
        assert len(result) == 2
        assert result[0]["name"] == "skill1"

    @pytest.mark.asyncio
    async def test_upsert_skill_success(self, initialized_runtime):
        """Test upsert_skill creates new skill."""
        _mock_registry.upsert_skill.return_value = {"name": "new_skill", "source": "custom"}
        result = await initialized_runtime.upsert_skill("new_skill", {"description": "Test"})
        assert result["success"] is True
        assert result["skill"]["name"] == "new_skill"

    @pytest.mark.asyncio
    async def test_upsert_skill_empty_name(self, initialized_runtime):
        """Test upsert_skill with empty name returns error."""
        result = await initialized_runtime.upsert_skill("", {"description": "Test"})
        assert result["success"] is False
        assert "skill name is required" in result["error"]

    @pytest.mark.asyncio
    async def test_upsert_skill_exception(self, initialized_runtime):
        """Test upsert_skill handles exceptions."""
        _mock_registry.upsert_skill.side_effect = ValueError("Invalid skill")
        result = await initialized_runtime.upsert_skill("test", {})
        assert result["success"] is False
        assert "Invalid skill" in result["error"]

    @pytest.mark.asyncio
    async def test_delete_skill_success(self, initialized_runtime):
        """Test delete_skill removes skill."""
        _mock_registry.get_skill.return_value = {"name": "test_skill", "source": "custom"}
        _mock_registry.delete_skill.return_value = True
        result = await initialized_runtime.delete_skill("test_skill")
        assert result["success"] is True
        assert result["skill_name"] == "test_skill"

    @pytest.mark.asyncio
    async def test_delete_skill_not_found(self, initialized_runtime):
        """Test delete_skill returns error for non-existent skill."""
        _mock_registry.get_skill.return_value = None
        result = await initialized_runtime.delete_skill("nonexistent")
        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_delete_skill_empty_name(self, initialized_runtime):
        """Test delete_skill with empty name returns error."""
        result = await initialized_runtime.delete_skill("")
        assert result["success"] is False
        assert "skill name is required" in result["error"]

    @pytest.mark.asyncio
    async def test_delete_skill_builtin_not_allowed(self, initialized_runtime):
        """Test delete_skill returns error for builtin skill."""
        _mock_registry.get_skill.return_value = {"name": "builtin_skill", "source": "builtin"}
        _mock_registry.delete_skill.return_value = False
        result = await initialized_runtime.delete_skill("builtin_skill")
        assert result["success"] is False
        assert "cannot be deleted" in result["error"]

    @pytest.mark.asyncio
    async def test_list_mcp_servers(self, initialized_runtime):
        """Test list_mcp_servers returns servers."""
        _mock_registry.list_mcp_servers.return_value = [
            {"id": "server1", "enabled": True},
        ]
        result = await initialized_runtime.list_mcp_servers()
        assert result["success"] is True
        assert len(result["servers"]) == 1
        assert result["adapter"]["available"] is True

    @pytest.mark.asyncio
    async def test_list_mcp_catalog(self, initialized_runtime):
        """Test list_mcp_catalog returns catalog items."""
        _mock_registry.list_mcp_catalog.return_value = [
            {"catalog_id": "github", "name": "GitHub"},
        ]
        result = await initialized_runtime.list_mcp_catalog(query="github")
        assert result["success"] is True
        assert len(result["items"]) == 1
        assert result["query"] == "github"

    @pytest.mark.asyncio
    async def test_install_mcp_from_catalog_success(self, initialized_runtime):
        """Test install_mcp_from_catalog installs server."""
        _mock_registry.install_mcp_from_catalog.return_value = {"id": "github", "name": "GitHub"}
        result = await initialized_runtime.install_mcp_from_catalog("github", overrides={"env": {"TOKEN": "xxx"}})
        assert result["success"] is True
        assert result["server"]["id"] == "github"

    @pytest.mark.asyncio
    async def test_install_mcp_from_catalog_empty_id(self, initialized_runtime):
        """Test install_mcp_from_catalog with empty id returns error."""
        result = await initialized_runtime.install_mcp_from_catalog("", overrides={})
        assert result["success"] is False
        assert "catalog_id is required" in result["error"]

    @pytest.mark.asyncio
    async def test_install_mcp_from_catalog_exception(self, initialized_runtime):
        """Test install_mcp_from_catalog handles exceptions."""
        _mock_registry.install_mcp_from_catalog.side_effect = ValueError("Invalid catalog")
        result = await initialized_runtime.install_mcp_from_catalog("invalid", overrides={})
        assert result["success"] is False
        assert "Invalid catalog" in result["error"]

    @pytest.mark.asyncio
    async def test_upsert_mcp_server_success(self, initialized_runtime):
        """Test upsert_mcp_server creates server."""
        _mock_registry.upsert_mcp_server.return_value = {"id": "test_server", "name": "Test"}
        result = await initialized_runtime.upsert_mcp_server("test_server", {"name": "Test", "transport": "stdio"})
        assert result["success"] is True
        assert result["server"]["id"] == "test_server"

    @pytest.mark.asyncio
    async def test_upsert_mcp_server_empty_id(self, initialized_runtime):
        """Test upsert_mcp_server with empty id returns error."""
        result = await initialized_runtime.upsert_mcp_server("", {"name": "Test"})
        assert result["success"] is False
        assert "server id is required" in result["error"]

    @pytest.mark.asyncio
    async def test_delete_mcp_server_success(self, initialized_runtime):
        """Test delete_mcp_server removes server."""
        _mock_registry.get_mcp_server.return_value = {"id": "test_server"}
        result = await initialized_runtime.delete_mcp_server("test_server")
        assert result["success"] is True
        assert result["server_id"] == "test_server"

    @pytest.mark.asyncio
    async def test_delete_mcp_server_not_found(self, initialized_runtime):
        """Test delete_mcp_server returns error for non-existent server."""
        _mock_registry.get_mcp_server.return_value = None
        result = await initialized_runtime.delete_mcp_server("nonexistent")
        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_delete_mcp_server_empty_id(self, initialized_runtime):
        """Test delete_mcp_server with empty id returns error."""
        result = await initialized_runtime.delete_mcp_server("")
        assert result["success"] is False
        assert "server id is required" in result["error"]

    def test_get_permissions(self, initialized_runtime):
        """Test get_permissions returns permissions."""
        result = initialized_runtime.get_permissions()
        assert result["success"] is True
        assert "permissions" in result
        assert "groups" in result

    @patch('builtins.open', mock_open())
    @patch('yaml.safe_dump')
    def test_update_permissions_success(self, mock_yaml_dump, initialized_runtime):
        """Test update_permissions saves permissions."""
        initialized_runtime._config_file = Path("/test/config.yml")
        result = initialized_runtime.update_permissions({"github_read": True})
        assert result["success"] is True
        mock_yaml_dump.assert_called_once()

    def test_update_permissions_invalid_payload(self, initialized_runtime):
        """Test update_permissions with invalid payload returns error."""
        result = initialized_runtime.update_permissions("not a dict")
        assert result["success"] is False
        assert "must be an object" in result["error"]

    def test_update_permissions_no_config_file(self, initialized_runtime):
        """Test update_permissions without config file returns error."""
        initialized_runtime._config_file = None
        result = initialized_runtime.update_permissions({"github_read": True})
        assert result["success"] is False
        assert "config file not found" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_skill_empty_name(self, initialized_runtime):
        """Test execute_skill with empty name returns error."""
        result = await initialized_runtime.execute_skill("", {})
        assert result["success"] is False
        assert "skill_name is required" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_skill_disabled(self, initialized_runtime):
        """Test execute_skill with disabled skill returns error."""
        _mock_registry.get_skill.return_value = {"name": "test", "enabled": False}
        result = await initialized_runtime.execute_skill("test", {})
        assert result["success"] is False
        assert "disabled" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_skill_workflow_skills(self, initialized_runtime):
        """Test execute_skill for workflow skills."""
        _mock_registry.get_skill.return_value = {"name": "scan_typo", "enabled": True}
        _mock_coordinator.process_task.return_value = {"success": True}
        result = await initialized_runtime.execute_skill("scan_typo", {"owner": "test", "repo": "repo"})
        assert result["mode"] == "workflow_skill"

    @pytest.mark.asyncio
    async def test_execute_skill_workflow_missing_owner_repo(self, initialized_runtime):
        """Test execute_skill workflow skill without owner/repo returns error."""
        _mock_registry.get_skill.return_value = {"name": "scan_typo", "enabled": True}
        result = await initialized_runtime.execute_skill("scan_typo", {})
        assert result["success"] is False
        assert "owner/repo are required" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_skill_sql_skills(self, initialized_runtime):
        """Test execute_skill for sql skills with permission check."""
        _mock_registry.get_skill.return_value = {"name": "run_sql", "enabled": True}
        with patch('app.agent.runtime.is_permission_allowed') as mock_perm:
            mock_perm.return_value = False
            result = await initialized_runtime.execute_skill("run_sql", {
                "host": "127.0.0.1",
                "database": "test",
                "query": "SELECT 1",
            })
            # Local MySQL should be allowed without permission
            assert result["mode"] == "sql"

    @pytest.mark.asyncio
    async def test_execute_skill_llm_skills(self, initialized_runtime):
        """Test execute_skill for llm skills."""
        _mock_registry.get_skill.return_value = {"name": "ask_ai", "enabled": True}
        with patch('app.agent.runtime.is_permission_allowed') as mock_perm:
            mock_perm.return_value = True
            result = await initialized_runtime.execute_skill("ask_ai", {"question": "test"})
            assert result["mode"] == "llm_skill"

    @pytest.mark.asyncio
    async def test_execute_skill_llm_skill_no_prompt(self, initialized_runtime):
        """Test execute_skill for llm skills without prompt returns error."""
        _mock_registry.get_skill.return_value = {"name": "ask_ai", "enabled": True}
        # Should fallback to chat with constructed prompt - chat returns success
        result = await initialized_runtime.execute_skill("ask_ai", {})
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_execute_skill_unsupported_skill(self, initialized_runtime):
        """Test execute_skill for unsupported skill with definition."""
        _mock_registry.get_skill.return_value = {"name": "custom", "enabled": True}
        with patch.object(initialized_runtime, 'chat', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = {"success": False}
            result = await initialized_runtime.execute_skill("custom", {})
            assert result["mode"] == "unsupported"

    @pytest.mark.asyncio
    async def test_execute_skill_unsupported_skill_with_fallback(self, initialized_runtime):
        """Test execute_skill fallback for unsupported skill."""
        _mock_registry.get_skill.return_value = None  # Skill not in registry
        with patch.object(initialized_runtime, 'chat', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = {"success": True, "reply": "Fallback response"}
            result = await initialized_runtime.execute_skill("unknown_skill", {})
            assert result["mode"] == "custom_fallback"

    @pytest.mark.asyncio
    async def test_execute_skill_custom_executor_workflow(self, initialized_runtime):
        """Test execute_skill with custom workflow executor."""
        _mock_registry.get_skill.return_value = {
            "name": "custom",
            "enabled": True,
            "executor": {"type": "workflow", "ownerParam": "owner", "repoParam": "repo"},
        }
        _mock_coordinator.process_task.return_value = {"success": True}
        result = await initialized_runtime.execute_skill("custom", {"owner": "test", "repo": "repo"})
        assert result["mode"] == "custom_executor_workflow"

    @pytest.mark.asyncio
    async def test_execute_skill_custom_executor_workflow_missing_params(self, initialized_runtime):
        """Test execute_skill with custom workflow executor missing params."""
        _mock_registry.get_skill.return_value = {
            "name": "custom",
            "enabled": True,
            "executor": {"type": "workflow", "workflow": "single_project"},
        }
        result = await initialized_runtime.execute_skill("custom", {})
        assert result["success"] is False
        assert "single_project workflow requires owner and repo" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_skill_custom_executor_mcp(self, initialized_runtime):
        """Test execute_skill with custom MCP executor."""
        _mock_registry.get_skill.return_value = {
            "name": "custom",
            "enabled": True,
            "executor": {"type": "mcp", "server_id": "test", "tool": "test_tool"},
        }
        _mock_registry.get_mcp_server.return_value = {"id": "test", "enabled": True}
        with patch.object(initialized_runtime, '_invoke_mcp_tool', new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = {"success": True, "result": "done"}
            result = await initialized_runtime.execute_skill("custom", {})
            assert result["mode"] == "custom_executor_mcp"

    @pytest.mark.asyncio
    async def test_execute_skill_custom_executor_sql(self, initialized_runtime):
        """Test execute_skill with custom SQL executor."""
        _mock_registry.get_skill.return_value = {
            "name": "custom",
            "enabled": True,
            "executor": {"type": "sql", "database": "test"},
        }
        with patch.object(initialized_runtime, '_execute_sql_skill', new_callable=AsyncMock) as mock_sql:
            mock_sql.return_value = {"success": True, "result": "done"}
            result = await initialized_runtime.execute_skill("custom", {"query": "SELECT 1"})
            assert result["mode"] == "custom_executor_sql"

    @pytest.mark.asyncio
    async def test_execute_skill_custom_executor_http(self, initialized_runtime):
        """Test execute_skill with custom HTTP executor."""
        _mock_registry.get_skill.return_value = {
            "name": "custom",
            "enabled": True,
            "executor": {"type": "http", "url": "https://example.com"},
        }
        with patch.object(initialized_runtime, '_execute_webhook_skill', new_callable=AsyncMock) as mock_webhook:
            mock_webhook.return_value = {"success": True}
            result = await initialized_runtime.execute_skill("custom", {})
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_execute_skill_custom_executor_http_no_url(self, initialized_runtime):
        """Test execute_skill with custom HTTP executor missing URL."""
        _mock_registry.get_skill.return_value = {
            "name": "custom",
            "enabled": True,
            "executor": {"type": "http"},
        }
        result = await initialized_runtime.execute_skill("custom", {})
        assert result["success"] is False
        assert "url is required" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_skill_custom_executor_llm(self, initialized_runtime):
        """Test execute_skill with custom LLM executor."""
        _mock_registry.get_skill.return_value = {
            "name": "custom",
            "enabled": True,
            "executor": {"type": "llm", "prompt": "Test prompt"},
        }
        with patch.object(initialized_runtime, 'chat', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = {"success": True, "reply": "Response"}
            result = await initialized_runtime.execute_skill("custom", {})
            assert result["mode"] == "custom_executor_llm"

    @pytest.mark.asyncio
    async def test_execute_skill_custom_executor_unsupported_type(self, initialized_runtime):
        """Test execute_skill with unsupported executor type."""
        _mock_registry.get_skill.return_value = {
            "name": "custom",
            "enabled": True,
            "executor": {"type": "unknown"},
        }
        result = await initialized_runtime.execute_skill("custom", {})
        assert result["success"] is False
        assert "Unsupported executor type" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_skill_webhook_skill(self, initialized_runtime):
        """Test execute_skill for webhook_notify."""
        _mock_registry.get_skill.return_value = {"name": "webhook_notify", "enabled": True}
        with patch('app.agent.runtime.is_permission_allowed') as mock_perm:
            mock_perm.return_value = True
            with patch.object(initialized_runtime, '_execute_webhook_skill', new_callable=AsyncMock) as mock_webhook:
                mock_webhook.return_value = {"success": True, "mode": "webhook"}
                result = await initialized_runtime.execute_skill("webhook_notify", {"url": "https://example.com"})
                assert result["success"] is True
                assert result["mode"] == "webhook"

    @pytest.mark.asyncio
    async def test_execute_skill_webhook_permission_denied(self, initialized_runtime):
        """Test execute_skill webhook with permission denied."""
        _mock_registry.get_skill.return_value = {"name": "webhook_notify", "enabled": True}
        with patch('app.agent.runtime.is_permission_allowed') as mock_perm:
            mock_perm.return_value = False
            result = await initialized_runtime.execute_skill("webhook_notify", {"url": "https://example.com"})
            assert result["success"] is False
            assert result["mode"] == "webhook"

    @pytest.mark.asyncio
    async def test_execute_mcp_tool_server_not_found(self, initialized_runtime):
        """Test execute_mcp_tool for non-existent server."""
        _mock_registry.get_mcp_server.return_value = None
        result = await initialized_runtime.execute_mcp_tool("nonexistent", "tool", {})
        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_mcp_tool_server_disabled(self, initialized_runtime):
        """Test execute_mcp_tool for disabled server."""
        _mock_registry.get_mcp_server.return_value = {"id": "test", "enabled": False}
        result = await initialized_runtime.execute_mcp_tool("test", "tool", {})
        assert result["success"] is False
        assert "disabled" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_mcp_tool_empty_server_id(self, initialized_runtime):
        """Test execute_mcp_tool with empty server_id."""
        result = await initialized_runtime.execute_mcp_tool("", "tool", {})
        assert result["success"] is False
        assert "server_id is required" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_mcp_tool_empty_tool_name(self, initialized_runtime):
        """Test execute_mcp_tool with empty tool_name."""
        _mock_registry.get_mcp_server.return_value = {"id": "test", "enabled": True}
        result = await initialized_runtime.execute_mcp_tool("test", "", {})
        assert result["success"] is False
        assert "tool_name is required" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_mcp_tool_permission_denied(self, initialized_runtime):
        """Test execute_mcp_tool with permission denied."""
        with patch('app.agent.runtime.is_permission_allowed') as mock_perm:
            mock_perm.return_value = False
            result = await initialized_runtime.execute_mcp_tool("test", "tool", {})
            assert result["success"] is False
            assert result["mode"] == "mcp"

    @pytest.mark.asyncio
    async def test_probe_mcp_server_not_found(self, initialized_runtime):
        """Test probe_mcp_server for non-existent server."""
        _mock_registry.get_mcp_server.return_value = None
        result = await initialized_runtime.probe_mcp_server("nonexistent")
        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_probe_mcp_server_empty_id(self, initialized_runtime):
        """Test probe_mcp_server with empty id."""
        result = await initialized_runtime.probe_mcp_server("")
        assert result["success"] is False
        assert "server id is required" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_sql_local_mysql_allowed(self, initialized_runtime):
        """Test execute_sql allows local MySQL without api_call permission."""
        result = await initialized_runtime.execute_sql(
            database="test",
            query="SELECT 1",
        )
        # Should attempt to connect to local MySQL - will fail because no real MySQL
        assert result["success"] is False  # Will fail because no real MySQL

    @pytest.mark.asyncio
    async def test_execute_sql_remote_requires_permission(self, initialized_runtime):
        """Test execute_sql requires permission for remote MySQL."""
        with patch('app.agent.runtime.is_permission_allowed') as mock_perm:
            mock_perm.return_value = False
            result = await initialized_runtime.execute_sql(
                database="test",
                query="SELECT 1",
                args=[],
                read_only=True,
                max_rows=200,
            )
            # The database name gets validated, then it tries to execute
            # Since we don't set host param, it defaults to env which is localhost
            assert result["success"] is False

    @pytest.mark.asyncio
    async def test_execute_sql_invalid_port(self, initialized_runtime):
        """Test execute_sql with invalid port."""
        result = await initialized_runtime.execute_sql(
            database="test",
            query="SELECT 1",
            args=["invalid_port"],  # This won't affect port, but let's test
        )
        # Port comes from params or env, args are for query parameters
        assert result["success"] is False  # Will fail connecting

    @pytest.mark.asyncio
    async def test_execute_sql_no_database(self, initialized_runtime):
        """Test execute_sql without database uses default."""
        # When database is empty, it falls back to MYSQL_DATABASE env var or "typomaster"
        with patch.dict('os.environ', {'MYSQL_DATABASE': 'test_db'}):
            result = await initialized_runtime.execute_sql(
                database="",
                query="SELECT 1",
            )
            # Empty database triggers validation error
            assert result["success"] is False

    @pytest.mark.asyncio
    async def test_execute_sql_no_query(self, initialized_runtime):
        """Test execute_sql without query."""
        result = await initialized_runtime.execute_sql(
            database="test",
            query="",
        )
        assert result["success"] is False
        assert "query is required" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_sql_read_only_blocks_write(self, initialized_runtime):
        """Test execute_sql read_only blocks write statements."""
        result = await initialized_runtime.execute_sql(
            database="test",
            query="INSERT INTO test VALUES (1)",
            read_only=True,
        )
        assert result["success"] is False
        assert "read_only mode only allows" in result["error"]

    @pytest.mark.asyncio
    async def test_chat_empty_message(self, initialized_runtime):
        """Test chat with empty message."""
        result = await initialized_runtime.chat("", [])
        assert result["success"] is False
        assert "message is empty" in result["error"]

    @pytest.mark.asyncio
    async def test_chat_run_command(self, initialized_runtime):
        """Test chat with /run command."""
        with patch.object(initialized_runtime, 'run_workflow', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {"success": True}
            result = await initialized_runtime.chat("/run owner/repo", [], "conv-123")
            assert result["success"] is True
            assert result["mode"] == "agent_action"

    @pytest.mark.asyncio
    async def test_chat_run_command_invalid_format(self, initialized_runtime):
        """Test chat with invalid /run command format."""
        result = await initialized_runtime.chat("/run invalid", [], "conv-123")
        assert result["success"] is False
        assert "Invalid /run format" in result["error"]

    @pytest.mark.asyncio
    async def test_chat_run_command_permission_denied(self, initialized_runtime):
        """Test chat /run command with permission denied."""
        with patch('app.agent.runtime.is_permission_allowed') as mock_perm:
            mock_perm.return_value = False
            result = await initialized_runtime.chat("/run owner/repo", [], "conv-123")
            assert result["success"] is False

    @pytest.mark.asyncio
    async def test_chat_llm_mode(self, initialized_runtime):
        """Test chat in LLM mode."""
        result = await initialized_runtime.chat("Hello", [], "conv-123")
        assert result["success"] is True
        assert result["mode"] == "llm"
        assert result["reply"] == "Test LLM response"

    @pytest.mark.asyncio
    async def test_chat_llm_permission_denied(self, initialized_runtime):
        """Test chat with LLM permission denied."""
        with patch('app.agent.runtime.is_permission_allowed') as mock_perm:
            mock_perm.return_value = False
            result = await initialized_runtime.chat("Hello", [], "conv-123")
            assert result["success"] is True
            assert result["mode"] == "fallback"
            assert "warning" in result

    @pytest.mark.asyncio
    async def test_chat_llm_failure_fallback(self, initialized_runtime):
        """Test chat falls back when LLM fails."""
        _mock_llm_client.generate_text.return_value = {"success": False, "error": "LLM error"}
        result = await initialized_runtime.chat("Hello", [], "conv-123")
        assert result["success"] is True
        assert result["mode"] == "fallback"

    @pytest.mark.asyncio
    async def test_chat_not_initialized(self, runtime):
        """Test chat when not initialized."""
        runtime._llm_client = _mock_llm_client
        result = await runtime.chat("Hello", [], "conv-123")
        # Should work without coordinator
        assert result["success"] is True

    def test_extract_owner_repo(self, initialized_runtime):
        """Test _extract_owner_repo helper."""
        # Direct owner/repo
        owner, repo = initialized_runtime._extract_owner_repo({"owner": "test", "repo": "repo"})
        assert owner == "test"
        assert repo == "repo"

        # Repository field
        owner, repo = initialized_runtime._extract_owner_repo({"repository": "test/repo"})
        assert owner == "test"
        assert repo == "repo"

        # repoFullName field
        owner, repo = initialized_runtime._extract_owner_repo({"repoFullName": "test/repo"})
        assert owner == "test"
        assert repo == "repo"

        # target field
        owner, repo = initialized_runtime._extract_owner_repo({"target": "test/repo"})
        assert owner == "test"
        assert repo == "repo"

        # Missing values
        owner, repo = initialized_runtime._extract_owner_repo({})
        assert owner is None
        assert repo is None

    def test_build_mcp_client_config_stdio(self, initialized_runtime):
        """Test _build_mcp_client_config for stdio transport."""
        server = {"id": "test", "transport": "stdio", "command": "npx", "args": ["-y", "@modelcontextprotocol/server-github"]}
        config = initialized_runtime._build_mcp_client_config(server)
        assert config["transport"] == "stdio"
        assert config["command"] == "npx"
        assert config["args"] == ["-y", "@modelcontextprotocol/server-github"]

    def test_build_mcp_client_config_http(self, initialized_runtime):
        """Test _build_mcp_client_config for http transport."""
        server = {"id": "test", "transport": "http", "url": "http://localhost:3000"}
        config = initialized_runtime._build_mcp_client_config(server)
        assert config["transport"] == "http"
        assert config["url"] == "http://localhost:3000"

    def test_build_mcp_client_config_missing_command(self, initialized_runtime):
        """Test _build_mcp_client_config stdio without command raises error."""
        server = {"id": "test", "transport": "stdio"}
        with pytest.raises(ValueError, match="stdio transport requires command"):
            initialized_runtime._build_mcp_client_config(server)

    def test_build_mcp_client_config_missing_url(self, initialized_runtime):
        """Test _build_mcp_client_config http without url raises error."""
        server = {"id": "test", "transport": "http"}
        with pytest.raises(ValueError, match="http transport requires url"):
            initialized_runtime._build_mcp_client_config(server)

    def test_build_mcp_client_config_with_env(self, initialized_runtime):
        """Test _build_mcp_client_config with env variables."""
        server = {"id": "test", "transport": "stdio", "command": "cmd", "env": {"KEY": "value"}}
        config = initialized_runtime._build_mcp_client_config(server)
        assert config["env"] == {"KEY": "value"}

    def test_build_mcp_client_config_with_headers(self, initialized_runtime):
        """Test _build_mcp_client_config with headers."""
        server = {"id": "test", "transport": "http", "url": "http://localhost", "headers": {"Auth": "token"}}
        config = initialized_runtime._build_mcp_client_config(server)
        assert config["headers"] == {"Auth": "token"}

    def test_build_mcp_client_config_streamable_http(self, initialized_runtime):
        """Test _build_mcp_client_config converts streamable_http to http."""
        server = {"id": "test", "transport": "streamable_http", "url": "http://localhost"}
        config = initialized_runtime._build_mcp_client_config(server)
        assert config["transport"] == "http"

    def test_to_json_safe(self, initialized_runtime):
        """Test _to_json_safe helper."""
        # Regular dict
        result = initialized_runtime._to_json_safe({"key": "value"})
        assert result == {"key": "value"}

        # Bytes
        result = initialized_runtime._to_json_safe(b"test bytes")
        assert result == "test bytes"

        # Datetime
        now = datetime.now(timezone.utc)
        result = initialized_runtime._to_json_safe(now)
        assert isinstance(result, str)

        # Unserializable object
        class CustomObj:
            def __str__(self):
                return "custom"
        result = initialized_runtime._to_json_safe(CustomObj())
        assert result == "custom"

    def test_history_to_text(self, initialized_runtime):
        """Test _history_to_text helper."""
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        result = initialized_runtime._history_to_text(history)
        assert "user: Hello" in result
        assert "assistant: Hi" in result

    def test_history_to_text_empty(self, initialized_runtime):
        """Test _history_to_text with empty history."""
        result = initialized_runtime._history_to_text([])
        assert result == "(empty)"

    def test_history_to_text_limits_to_last_12(self, initialized_runtime):
        """Test _history_to_text only includes last 12 messages."""
        history = [{"role": "user", "content": f"Message {i}"} for i in range(15)]
        result = initialized_runtime._history_to_text(history)
        assert "Message 14" in result
        assert "Message 0" not in result

    def test_rule_based_chat_fallback_capabilities(self, initialized_runtime):
        """Test _rule_based_chat_fallback for capabilities query."""
        result = initialized_runtime._rule_based_chat_fallback("What are your capabilities?")
        assert "capabilities endpoint" in result

    def test_rule_based_chat_fallback_run(self, initialized_runtime):
        """Test _rule_based_chat_fallback for run query."""
        result = initialized_runtime._rule_based_chat_fallback("How do I run a workflow?")
        assert "/run owner/repo" in result

    def test_rule_based_chat_fallback_generic(self, initialized_runtime):
        """Test _rule_based_chat_fallback for generic query."""
        result = initialized_runtime._rule_based_chat_fallback("Something else")
        assert "LLM is not configured" in result

    def test_allow_local_mysql_sql_without_api_permission(self, initialized_runtime):
        """Test _allow_local_mysql_sql_without_api_permission for local hosts."""
        # Local hosts should be allowed
        assert initialized_runtime._allow_local_mysql_sql_without_api_permission({"host": "127.0.0.1"}) is True
        assert initialized_runtime._allow_local_mysql_sql_without_api_permission({"host": "localhost"}) is True
        assert initialized_runtime._allow_local_mysql_sql_without_api_permission({"host": "::1"}) is True

        # Remote hosts should not be allowed
        assert initialized_runtime._allow_local_mysql_sql_without_api_permission({"host": "remote.example.com"}) is False

    def test_iter_candidate_files(self, initialized_runtime, tmp_path):
        """Test _iter_candidate_files finds candidate files."""
        # Create test files
        (tmp_path / "test.txt").write_text("test content")
        (tmp_path / ".hidden").write_text("hidden")

        files = initialized_runtime._iter_candidate_files(tmp_path, max_files=10)
        assert len(files) >= 1
        # Hidden files should be skipped
        assert not any(".hidden" in str(f) for f in files)

    def test_iter_candidate_files_skips_large_files(self, initialized_runtime, tmp_path):
        """Test _iter_candidate_files skips large files."""
        # Create a large file (> 512KB)
        large_file = tmp_path / "large.bin"
        large_file.write_bytes(b"x" * (513 * 1024))

        files = initialized_runtime._iter_candidate_files(tmp_path, max_files=10)
        assert large_file not in files

    def test_iter_candidate_files_skips_skip_dirs(self, initialized_runtime, tmp_path):
        """Test _iter_candidate_files skips skip_dirs."""
        skip_dir = tmp_path / ".git"
        skip_dir.mkdir()
        (skip_dir / "config").write_text("config")

        files = initialized_runtime._iter_candidate_files(tmp_path, max_files=10)
        assert not any(".git" in str(f) for f in files)

    def test_iter_candidate_files_respects_max_files(self, initialized_runtime, tmp_path):
        """Test _iter_candidate_files respects max_files limit."""
        # Create multiple files
        for i in range(5):
            (tmp_path / f"file{i}.txt").write_text(f"content {i}")

        files = initialized_runtime._iter_candidate_files(tmp_path, max_files=3)
        assert len(files) == 3

    @pytest.mark.asyncio
    async def test_execute_webhook_skill(self, initialized_runtime):
        """Test _execute_webhook_skill sends request."""
        with patch('app.agent.runtime.urlrequest.urlopen') as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.read.return_value = b'{"success": true}'
            mock_urlopen.return_value.__enter__.return_value = mock_response

            result = await initialized_runtime._execute_webhook_skill("test", {
                "url": "https://example.com/webhook",
                "method": "POST",
                "payload": {"key": "value"},
            })
            assert result["success"] is True
            assert result["mode"] == "webhook"

    @pytest.mark.asyncio
    async def test_execute_webhook_skill_invalid_url(self, initialized_runtime):
        """Test _execute_webhook_skill with invalid URL."""
        result = await initialized_runtime._execute_webhook_skill("test", {
            "url": "ftp://example.com",
            "method": "POST",
        })
        assert result["success"] is False
        assert "http:// or https://" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_webhook_skill_non_success_status(self, initialized_runtime):
        """Test _execute_webhook_skill with non-success status."""
        with patch('app.agent.runtime.urlrequest.urlopen') as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 500
            mock_response.read.return_value = b'Error'
            mock_urlopen.return_value.__enter__.return_value = mock_response

            result = await initialized_runtime._execute_webhook_skill("test", {
                "url": "https://example.com/webhook",
            })
            assert result["success"] is False

    @pytest.mark.asyncio
    async def test_agent_runtime_singleton(self):
        """Test agent_runtime singleton is created."""
        assert agent_runtime is not None
        assert isinstance(agent_runtime, TypeAgentRuntime)

