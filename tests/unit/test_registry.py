"""
Unit tests for RuntimeRegistry.
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.agent.registry import RuntimeRegistry, BUILTIN_SKILLS, MCP_CATALOG_TEMPLATES


@pytest.mark.unit
class TestRuntimeRegistry:
    """Test RuntimeRegistry class."""

    @pytest.fixture
    def temp_registry(self, tmp_path):
        """Create a temporary registry for testing."""
        registry_path = tmp_path / "test_registry.json"
        return RuntimeRegistry(str(registry_path))

    def test_init_creates_empty_registry(self, tmp_path):
        """Test initialization creates empty registry when file doesn't exist."""
        registry_path = tmp_path / "nonexistent_registry.json"
        registry = RuntimeRegistry(str(registry_path))
        # Check that at least builtin skills are loaded
        assert len(registry.skills) >= len(BUILTIN_SKILLS)
        assert registry.mcp_servers == {}

    def test_init_loads_existing_registry(self, tmp_path):
        """Test initialization loads existing registry file."""
        registry_path = tmp_path / "existing_registry.json"
        # Create existing registry file
        data = {
            "skills": {
                "test_skill": {
                    "name": "test_skill",
                    "description": "Test skill",
                    "category": "test",
                    "enabled": True,
                    "source": "custom",
                }
            },
            "mcp_servers": {}
        }
        registry_path.write_text(json.dumps(data))

        registry = RuntimeRegistry(str(registry_path))
        assert "test_skill" in registry.skills
        assert registry.skills["test_skill"]["description"] == "Test skill"

    def test_ensure_builtin_skills(self, tmp_path):
        """Test that builtin skills are loaded on init."""
        registry_path = tmp_path / "registry.json"
        registry = RuntimeRegistry(str(registry_path))

        # Check that builtin skills are loaded
        skill_names = [s["name"] for s in BUILTIN_SKILLS]
        for name in skill_names:
            assert name in registry.skills, f"Builtin skill {name} not found"
            assert registry.skills[name]["source"] == "builtin"

    def test_list_skills(self, temp_registry):
        """Test listing skills returns sorted list."""
        # Add some skills
        temp_registry.upsert_skill("z_skill", {"description": "Z skill"})
        temp_registry.upsert_skill("a_skill", {"description": "A skill"})
        temp_registry.upsert_skill("m_skill", {"description": "M skill"})

        skills = temp_registry.list_skills()
        names = [s["name"] for s in skills]
        assert names == sorted(names)

    def test_get_skill_exists(self, temp_registry):
        """Test getting an existing skill."""
        temp_registry.upsert_skill("test_skill", {
            "description": "Test description",
            "category": "test_category"
        })

        skill = temp_registry.get_skill("test_skill")
        assert skill is not None
        assert skill["name"] == "test_skill"
        assert skill["description"] == "Test description"
        assert skill["category"] == "test_category"

    def test_get_skill_not_exists(self, temp_registry):
        """Test getting a non-existent skill returns None."""
        skill = temp_registry.get_skill("nonexistent")
        assert skill is None

    def test_upsert_skill_new(self, temp_registry):
        """Test creating a new skill."""
        result = temp_registry.upsert_skill("new_skill", {
            "description": "New skill description",
            "category": "test"
        })

        assert result["name"] == "new_skill"
        assert result["description"] == "New skill description"
        assert result["category"] == "test"
        assert result["enabled"] is True
        assert result["source"] == "custom"

    def test_upsert_skill_update(self, temp_registry):
        """Test updating an existing skill."""
        # Create initial skill
        temp_registry.upsert_skill("update_skill", {
            "description": "Original description",
            "category": "original"
        })

        # Update it
        result = temp_registry.upsert_skill("update_skill", {
            "description": "Updated description",
            "category": "updated"
        })

        assert result["description"] == "Updated description"
        assert result["category"] == "updated"

    def test_upsert_skill_preserves_builtin_source(self, temp_registry):
        """Test that upserting builtin skill preserves source."""
        # Get a builtin skill
        builtin_name = BUILTIN_SKILLS[0]["name"]
        result = temp_registry.upsert_skill(builtin_name, {
            "description": "Modified description"
        })

        assert result["source"] == "builtin"
        assert result["installMethod"] == "catalog"

    def test_delete_skill_custom(self, temp_registry):
        """Test deleting a custom skill."""
        temp_registry.upsert_skill("delete_me", {"description": "To be deleted"})
        assert "delete_me" in temp_registry.skills

        result = temp_registry.delete_skill("delete_me")
        assert result is True
        assert "delete_me" not in temp_registry.skills

    def test_delete_skill_builtin_not_allowed(self, temp_registry):
        """Test that builtin skills cannot be deleted."""
        builtin_name = BUILTIN_SKILLS[0]["name"]
        result = temp_registry.delete_skill(builtin_name)
        assert result is False
        assert builtin_name in temp_registry.skills

    def test_delete_skill_not_exists(self, temp_registry):
        """Test deleting a non-existent skill returns False."""
        result = temp_registry.delete_skill("nonexistent")
        assert result is False

    def test_list_mcp_servers(self, temp_registry):
        """Test listing MCP servers."""
        temp_registry.upsert_mcp_server("server1", {
            "name": "Server 1",
            "transport": "stdio",
            "command": "cmd1"
        })
        temp_registry.upsert_mcp_server("server2", {
            "name": "Server 2",
            "transport": "sse",
            "url": "http://example.com"
        })

        servers = temp_registry.list_mcp_servers()
        ids = [s["id"] for s in servers]
        assert ids == sorted(ids)

    def test_get_mcp_server(self, temp_registry):
        """Test getting an MCP server."""
        temp_registry.upsert_mcp_server("test_server", {
            "name": "Test Server",
            "transport": "stdio",
            "command": "test_cmd",
            "args": ["arg1", "arg2"]
        })

        server = temp_registry.get_mcp_server("test_server")
        assert server is not None
        assert server["id"] == "test_server"
        assert server["name"] == "Test Server"
        assert server["transport"] == "stdio"

    def test_delete_mcp_server(self, temp_registry):
        """Test deleting an MCP server."""
        temp_registry.upsert_mcp_server("delete_server", {
            "name": "Delete Server",
            "transport": "stdio"
        })
        assert "delete_server" in temp_registry.mcp_servers

        result = temp_registry.delete_mcp_server("delete_server")
        assert result is True
        assert "delete_server" not in temp_registry.mcp_servers

    def test_delete_mcp_server_not_exists(self, temp_registry):
        """Test deleting a non-existent MCP server returns False."""
        result = temp_registry.delete_mcp_server("nonexistent")
        assert result is False

    def test_list_mcp_catalog_no_query(self, temp_registry):
        """Test listing MCP catalog without query."""
        catalog = temp_registry.list_mcp_catalog()
        assert len(catalog) == len(MCP_CATALOG_TEMPLATES)

    def test_list_mcp_catalog_with_query(self, temp_registry):
        """Test listing MCP catalog with search query."""
        catalog = temp_registry.list_mcp_catalog("github")
        assert len(catalog) > 0
        for item in catalog:
            haystack = f"{item.get('catalog_id', '')} {item.get('name', '')} {item.get('description', '')}"
            assert "github" in haystack.lower()

    def test_install_mcp_from_catalog(self, temp_registry):
        """Test installing MCP server from catalog."""
        catalog_id = MCP_CATALOG_TEMPLATES[0]["catalog_id"]
        result = temp_registry.install_mcp_from_catalog(catalog_id)

        assert result["id"] == catalog_id
        assert catalog_id in temp_registry.mcp_servers

    def test_install_mcp_from_catalog_not_found(self, temp_registry):
        """Test installing non-existent catalog item raises error."""
        with pytest.raises(ValueError, match="mcp catalog item not found"):
            temp_registry.install_mcp_from_catalog("nonexistent_catalog")

    def test_install_mcp_from_catalog_empty_id(self, temp_registry):
        """Test installing with empty catalog_id raises error."""
        with pytest.raises(ValueError, match="catalog_id is required"):
            temp_registry.install_mcp_from_catalog("")

    def test_normalize_skill_validation(self, temp_registry):
        """Test skill normalization with invalid input."""
        with pytest.raises(ValueError, match="skill name is required"):
            temp_registry._normalize_skill({})

    def test_normalize_mcp_server_validation(self, temp_registry):
        """Test MCP server normalization with invalid input."""
        with pytest.raises(ValueError, match="mcp server id is required"):
            temp_registry._normalize_mcp_server({})

        with pytest.raises(ValueError, match="unsupported mcp transport"):
            temp_registry._normalize_mcp_server({"id": "test", "transport": "invalid"})

    def test_normalize_mcp_server_args_string(self, temp_registry):
        """Test MCP server normalization with string args."""
        result = temp_registry._normalize_mcp_server({
            "id": "test",
            "transport": "stdio",
            "args": "single_arg"
        })
        assert result["args"] == ["single_arg"]

    def test_normalize_mcp_server_timeout_bounds(self, temp_registry):
        """Test MCP server timeout is bounded."""
        # Test minimum bound
        result = temp_registry._normalize_mcp_server({
            "id": "test",
            "transport": "stdio",
            "timeout": 1
        })
        assert result["timeout"] == 3

        # Test maximum bound
        result = temp_registry._normalize_mcp_server({
            "id": "test",
            "transport": "stdio",
            "timeout": 1000
        })
        assert result["timeout"] == 600

    def test_save_and_load_roundtrip(self, tmp_path):
        """Test save and load roundtrip preserves data."""
        registry_path = tmp_path / "roundtrip_registry.json"

        # Create and populate registry
        registry1 = RuntimeRegistry(str(registry_path))
        registry1.upsert_skill("test_skill", {"description": "Test"})
        registry1.upsert_mcp_server("test_server", {
            "name": "Test Server",
            "transport": "stdio"
        })
        registry1.save()

        # Load in new instance
        registry2 = RuntimeRegistry(str(registry_path))
        assert "test_skill" in registry2.skills
        assert "test_server" in registry2.mcp_servers

    def test_deepcopy_isolation(self, temp_registry):
        """Test that returned objects are copies, not references."""
        temp_registry.upsert_skill("isolated", {"description": "Original"})

        skill1 = temp_registry.get_skill("isolated")
        skill1["description"] = "Modified"

        skill2 = temp_registry.get_skill("isolated")
        assert skill2["description"] == "Original"

    def test_load_corrupted_file(self, tmp_path):
        """Test loading corrupted registry file."""
        registry_path = tmp_path / "corrupted_registry.json"
        registry_path.write_text("not valid json {[")

        # Should not raise, just log warning
        registry = RuntimeRegistry(str(registry_path))
        # Builtin skills are still loaded
        assert len(registry.skills) >= len(BUILTIN_SKILLS)
        assert registry.mcp_servers == {}
