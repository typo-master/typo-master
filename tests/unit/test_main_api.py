"""
Unit tests for FastAPI main endpoints.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime


@pytest.mark.unit
class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check(self, client):
        """Test basic health check."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["service"] == "typomaster-backend"
        assert "timestamp" in data


@pytest.mark.unit
class TestConversationsEndpoint:
    """Test conversation endpoints."""

    def test_create_conversation(self, client):
        """Test creating a conversation."""
        response = client.post("/api/v1/conversations")
        assert response.status_code == 200
        data = response.json()
        assert "conversation_id" in data
        assert "created_at" in data
        # Verify conversation was created (can be retrieved)
        conv_id = data["conversation_id"]
        response2 = client.get(f"/api/v1/conversations/{conv_id}/messages")
        assert response2.status_code == 200
        assert response2.json()["conversation_id"] == conv_id

    def test_get_messages(self, client):
        """Test getting conversation messages."""
        # Create conversation first
        create_response = client.post("/api/v1/conversations")
        conv_id = create_response.json()["conversation_id"]

        response = client.get(f"/api/v1/conversations/{conv_id}/messages")
        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"] == conv_id
        assert "messages" in data
        assert data["messages"] == []  # Empty for new conversation

    def test_get_messages_not_found(self, client):
        """Test getting messages for non-existent conversation."""
        response = client.get("/api/v1/conversations/nonexistent/messages")
        assert response.status_code == 404

    def test_send_message(self, client):
        """Test sending a message."""
        # Create conversation first
        create_response = client.post("/api/v1/conversations")
        conv_id = create_response.json()["conversation_id"]

        response = client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"message": "Hello"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "reply" in data

    def test_send_message_empty(self, client):
        """Test sending empty message."""
        response = client.post(
            "/api/v1/conversations/test-conv-123/messages",
            json={"message": ""},
        )
        assert response.status_code == 422  # Validation error


@pytest.mark.unit
class TestWorkflowsEndpoint:
    """Test workflow endpoints."""

    def test_run_workflow(self, client, mock_storage):
        """Test running a workflow."""
        response = client.post(
            "/api/v1/agent/workflows",
            json={
                "workflow": "single_project",
                "owner": "test",
                "repo": "test-repo",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "queued"

    def test_run_workflow_missing_params(self, client):
        """Test workflow without required params."""
        response = client.post(
            "/api/v1/agent/workflows",
            json={"workflow": "single_project"},  # Missing owner/repo
        )
        # API returns 422 when params are missing (validation error)
        assert response.status_code == 422

    def test_get_workflow_task(self, client):
        """Test getting workflow task."""
        # Create a workflow task first
        response = client.post(
            "/api/v1/agent/workflows",
            json={
                "workflow": "single_project",
                "owner": "test",
                "repo": "test-repo",
            },
        )
        assert response.status_code == 200
        task_id = response.json()["task_id"]

        # Get the task
        response = client.get(f"/api/v1/agent/workflows/{task_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task_id
        # Status can be any valid state (queued, running, succeeded, failed)
        assert data["status"] in ["queued", "running", "succeeded", "failed"]

    def test_get_workflow_task_not_found(self, client, mock_storage):
        """Test getting non-existent task."""
        mock_storage.get_workflow_task.return_value = None

        response = client.get("/api/v1/agent/workflows/nonexistent")
        assert response.status_code == 404


@pytest.mark.unit
class TestCapabilitiesEndpoint:
    """Test capabilities endpoint."""

    def test_get_capabilities(self, client, mock_agent_runtime):
        """Test getting capabilities."""
        mock_agent_runtime.get_capabilities.return_value = {
            "skills": [],
            "mcp_servers": [],
        }

        response = client.get("/api/v1/capabilities")
        assert response.status_code == 200
        data = response.json()
        assert "mcp_sse" in data


@pytest.mark.unit
class TestSkillsEndpoint:
    """Test skills endpoints."""

    def test_list_skills(self, client, mock_agent_runtime):
        """Test listing skills."""
        mock_agent_runtime.list_skills.return_value = []

        response = client.get("/api/v1/skills")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "skills" in data

    def test_execute_skill(self, client, mock_agent_runtime):
        """Test executing a skill."""
        mock_agent_runtime.execute_skill.return_value = {
            "success": True,
            "result": {"test": "data"},
        }

        response = client.post(
            "/api/v1/skills/execute",
            json={"skill_name": "test-skill", "params": {}, "conversation_id": ""},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


@pytest.mark.unit
class TestPermissionsEndpoint:
    """Test permissions endpoints."""

    def test_get_permissions(self, client, mock_agent_runtime):
        """Test getting permissions."""
        mock_agent_runtime.get_permissions.return_value = {}

        response = client.get("/api/v1/permissions")
        assert response.status_code == 200

    def test_update_permissions(self, client, mock_agent_runtime):
        """Test updating permissions."""
        mock_agent_runtime.update_permissions.return_value = {"success": True}

        response = client.put(
            "/api/v1/permissions",
            json={"permissions": {"test": True}},
        )
        assert response.status_code == 200
