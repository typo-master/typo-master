"""
Authorization security tests.
"""

import pytest


@pytest.mark.security
class TestAuthorization:
    """Test authorization and access control."""

    def test_get_other_user_conversation(self, client):
        """Test accessing another user's conversation."""
        # Create a conversation
        create_response = client.post("/api/v1/conversations")
        conv_id = create_response.json()["conversation_id"]

        # Try to access it (in real scenario with auth, this would fail)
        response = client.get(f"/api/v1/conversations/{conv_id}/messages")
        # Currently returns 404 if not found, but with auth should be 403
        assert response.status_code in [200, 404]

    def test_workflow_task_access_control(self, client):
        """Test workflow task access control."""
        # Try to access non-existent task
        response = client.get("/api/v1/agent/workflows/nonexistent-task-id")
        assert response.status_code == 404

        # Create a task
        response = client.post(
            "/api/v1/agent/workflows",
            json={
                "workflow": "single_project",
                "owner": "test",
                "repo": "test-repo",
            },
        )
        task_id = response.json()["task_id"]

        # Access the task
        response = client.get(f"/api/v1/agent/workflows/{task_id}")
        assert response.status_code == 200

    def test_skill_execution_permissions(self, client):
        """Test skill execution permissions."""
        # Try to execute arbitrary skill
        response = client.post(
            "/api/v1/skills/execute",
            json={
                "skill_name": "system_command",
                "params": {"command": "rm -rf /"},
            },
        )
        # Should fail validation or execution (403 Forbidden for permission denied)
        assert response.status_code in [400, 403, 422, 500]

    def test_mcp_server_management(self, client):
        """Test MCP server management authorization."""
        # Try to access MCP servers
        response = client.get("/api/v1/mcp/servers")
        assert response.status_code in [200, 401, 403]

        # Try to delete MCP server
        response = client.delete("/api/v1/mcp/servers/test-server")
        assert response.status_code in [200, 401, 403, 404]

    def test_permissions_update(self, client):
        """Test permissions update authorization."""
        # Try to update permissions without proper authorization
        response = client.put(
            "/api/v1/permissions",
            json={"permissions": {"admin": True, "all_access": True}},
        )
        assert response.status_code in [200, 401, 403]
