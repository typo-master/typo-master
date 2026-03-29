"""
Critical workflow regression tests.
Ensure critical user workflows continue to work.
"""

import pytest
import time


@pytest.mark.regression
@pytest.mark.critical
class TestConversationWorkflow:
    """Test conversation workflow regression."""

    def test_create_conversation_workflow(self, client):
        """Test complete conversation creation workflow."""
        # Step 1: Create conversation
        response = client.post("/api/v1/conversations")
        assert response.status_code == 200

        data = response.json()
        conv_id = data["conversation_id"]
        assert conv_id
        assert data["created_at"]

        # Step 2: Verify conversation exists (no messages yet)
        response = client.get(f"/api/v1/conversations/{conv_id}/messages")
        assert response.status_code == 200

        data = response.json()
        assert data["conversation_id"] == conv_id
        assert data["messages"] == []

    def test_send_and_receive_message_workflow(self, client):
        """Test sending and receiving messages workflow."""
        # Step 1: Create conversation
        create_response = client.post("/api/v1/conversations")
        conv_id = create_response.json()["conversation_id"]

        # Step 2: Send message
        response = client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"message": "Hello, Typo Master!"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["reply"]
        assert data["conversation_id"] == conv_id

        # Step 3: Verify message history
        response = client.get(f"/api/v1/conversations/{conv_id}/messages")
        assert response.status_code == 200

        data = response.json()
        assert len(data["messages"]) >= 2  # User message + assistant response

        # Verify message structure
        for msg in data["messages"]:
            assert "role" in msg
            assert "content" in msg
            assert "created_at" in msg
            assert msg["role"] in ["user", "assistant"]

    def test_conversation_persistence_workflow(self, client):
        """Test conversation persistence across requests."""
        # Step 1: Create conversation
        create_response = client.post("/api/v1/conversations")
        conv_id = create_response.json()["conversation_id"]

        # Step 2: Send multiple messages
        messages = ["Message 1", "Message 2", "Message 3"]
        for msg in messages:
            response = client.post(
                f"/api/v1/conversations/{conv_id}/messages",
                json={"message": msg},
            )
            assert response.status_code == 200

        # Step 3: Verify all messages persisted
        response = client.get(f"/api/v1/conversations/{conv_id}/messages")
        assert response.status_code == 200

        data = response.json()
        assert len(data["messages"]) >= len(messages)


@pytest.mark.regression
@pytest.mark.critical
class TestWorkflowTaskLifecycle:
    """Test workflow task lifecycle regression."""

    def test_single_project_workflow_lifecycle(self, client):
        """Test single project workflow lifecycle."""
        # Step 1: Create workflow task
        response = client.post(
            "/api/v1/agent/workflows",
            json={
                "workflow": "single_project",
                "owner": "test-owner",
                "repo": "test-repo",
                "create_pr": False,
            },
        )
        assert response.status_code == 200

        data = response.json()
        task_id = data["task_id"]
        assert task_id
        assert data["status"] == "queued"
        assert data["created_at"]
        assert data["updated_at"]

        # Step 2: Query task status
        response = client.get(f"/api/v1/agent/workflows/{task_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["task_id"] == task_id
        assert data["status"] in ["queued", "running", "succeeded", "failed"]

    def test_workflow_task_query_regression(self, client):
        """Test workflow task query returns consistent data."""
        # Create multiple tasks
        task_ids = []
        for i in range(3):
            response = client.post(
                "/api/v1/agent/workflows",
                json={
                    "workflow": "single_project",
                    "owner": "test",
                    "repo": f"repo-{i}",
                },
            )
            assert response.status_code == 200
            task_ids.append(response.json()["task_id"])

        # Query each task and verify consistent structure
        for task_id in task_ids:
            response = client.get(f"/api/v1/agent/workflows/{task_id}")
            assert response.status_code == 200

            data = response.json()
            assert "task_id" in data
            assert "status" in data
            assert "created_at" in data
            assert "updated_at" in data
            assert "result" in data
            assert "error" in data


@pytest.mark.regression
class TestSkillsWorkflow:
    """Test skills workflow regression."""

    def test_list_skills_workflow(self, client):
        """Test listing skills workflow."""
        response = client.get("/api/v1/skills")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert isinstance(data["skills"], list)

    def test_skill_execution_workflow(self, client):
        """Test skill execution workflow."""
        response = client.post(
            "/api/v1/skills/execute",
            json={
                "skill_name": "list_directory",
                "params": {"path": "."},
                "conversation_id": "",
            },
        )

        # Should either succeed or return a controlled error
        assert response.status_code in [200, 400, 404]

        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            assert "skill_name" in data
            assert "message" in data


@pytest.mark.regression
class TestCapabilitiesWorkflow:
    """Test capabilities workflow regression."""

    def test_get_capabilities_workflow(self, client):
        """Test getting capabilities workflow."""
        response = client.get("/api/v1/capabilities")
        assert response.status_code == 200

        data = response.json()

        # Verify expected structure
        assert isinstance(data, dict)

        # Check for MCP SSE info (should be present)
        assert "mcp_sse" in data

        mcp_sse = data["mcp_sse"]
        assert "enabled" in mcp_sse
        assert "endpoint" in mcp_sse
        assert "messages_endpoint" in mcp_sse
