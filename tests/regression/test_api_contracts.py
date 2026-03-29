"""
API contract regression tests.
Ensure API responses maintain consistent structure.
"""

import pytest


@pytest.mark.regression
class TestHealthContract:
    """Test health endpoint contract."""

    def test_health_response_structure(self, client, load_baseline):
        """Test health response maintains expected structure."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

        data = response.json()

        # Check required fields
        required_fields = ["ok", "service", "timestamp"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Check field types
        assert isinstance(data["ok"], bool)
        assert isinstance(data["service"], str)
        assert isinstance(data["timestamp"], str)

        # Check service name consistency
        assert data["service"] == "typomaster-backend"


@pytest.mark.regression
class TestConversationsContract:
    """Test conversation endpoints contract."""

    def test_create_conversation_response_structure(self, client):
        """Test create conversation response structure."""
        response = client.post("/api/v1/conversations")
        assert response.status_code == 200

        data = response.json()

        # Check required fields
        required_fields = ["conversation_id", "created_at"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Check field types
        assert isinstance(data["conversation_id"], str)
        assert isinstance(data["created_at"], str)

        # Check UUID format
        assert len(data["conversation_id"]) == 36  # Standard UUID length

    def test_list_messages_response_structure(self, client):
        """Test list messages response structure."""
        # Create conversation first
        create_response = client.post("/api/v1/conversations")
        conv_id = create_response.json()["conversation_id"]

        response = client.get(f"/api/v1/conversations/{conv_id}/messages")
        assert response.status_code == 200

        data = response.json()

        # Check required fields
        required_fields = ["conversation_id", "messages"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        assert isinstance(data["messages"], list)

    def test_send_message_response_structure(self, client):
        """Test send message response structure."""
        # Create conversation first
        create_response = client.post("/api/v1/conversations")
        conv_id = create_response.json()["conversation_id"]

        response = client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"message": "Hello"},
        )

        if response.status_code == 200:
            data = response.json()

            # Check required fields
            required_fields = ["success", "mode", "reply", "conversation_id"]
            for field in required_fields:
                assert field in data, f"Missing required field: {field}"

            # Check field types
            assert isinstance(data["success"], bool)
            assert isinstance(data["mode"], str)
            assert isinstance(data["reply"], str)
            assert isinstance(data["conversation_id"], str)

            # Check mode values
            assert data["mode"] in ["skill", "direct", "fallback"]

    def test_404_response_structure(self, client):
        """Test 404 error response structure."""
        response = client.get("/api/v1/conversations/nonexistent/messages")
        assert response.status_code == 404

        data = response.json()

        # Check error structure
        assert "detail" in data
        assert isinstance(data["detail"], str)

    def test_422_response_structure(self, client):
        """Test 422 validation error response structure."""
        response = client.post(
            "/api/v1/conversations/test/messages",
            json={"message": ""},  # Empty message should fail validation
        )

        if response.status_code == 422:
            data = response.json()

            # Check error structure
            assert "detail" in data
            assert isinstance(data["detail"], list)


@pytest.mark.regression
class TestWorkflowsContract:
    """Test workflow endpoints contract."""

    def test_run_workflow_response_structure(self, client):
        """Test run workflow response structure."""
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

        # Check required fields
        required_fields = ["task_id", "status", "created_at", "updated_at"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Check field types
        assert isinstance(data["task_id"], str)
        assert isinstance(data["status"], str)
        assert isinstance(data["created_at"], str)
        assert isinstance(data["updated_at"], str)

        # Check status values
        assert data["status"] in ["queued", "running", "succeeded", "failed"]

    def test_get_workflow_response_structure(self, client):
        """Test get workflow response structure."""
        # Create workflow first
        create_response = client.post(
            "/api/v1/agent/workflows",
            json={
                "workflow": "single_project",
                "owner": "test",
                "repo": "test-repo",
            },
        )
        task_id = create_response.json()["task_id"]

        response = client.get(f"/api/v1/agent/workflows/{task_id}")
        assert response.status_code == 200

        data = response.json()

        # Check required fields
        required_fields = ["task_id", "status", "created_at", "updated_at"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Optional fields should be present but can be null
        assert "result" in data
        assert "error" in data

    def test_workflow_error_response_structure(self, client):
        """Test workflow error response structure."""
        response = client.post(
            "/api/v1/agent/workflows",
            json={
                "workflow": "single_project",
                # Missing required owner and repo
            },
        )
        assert response.status_code == 422

        data = response.json()
        assert "detail" in data


@pytest.mark.regression
class TestSkillsContract:
    """Test skills endpoints contract."""

    def test_list_skills_response_structure(self, client):
        """Test list skills response structure."""
        response = client.get("/api/v1/skills")
        assert response.status_code == 200

        data = response.json()

        # Check required fields
        assert "success" in data
        assert "skills" in data
        assert isinstance(data["success"], bool)
        assert isinstance(data["skills"], list)

    def test_execute_skill_response_structure(self, client):
        """Test execute skill response structure."""
        response = client.post(
            "/api/v1/skills/execute",
            json={
                "skill_name": "test-skill",
                "params": {},
                "conversation_id": "",
            },
        )

        if response.status_code == 200:
            data = response.json()

            # Check required fields
            required_fields = ["success", "skill_name", "mode", "message", "executed_at"]
            for field in required_fields:
                assert field in data, f"Missing required field: {field}"

            # Check field types
            assert isinstance(data["success"], bool)
            assert isinstance(data["skill_name"], str)
            assert isinstance(data["mode"], str)
            assert isinstance(data["message"], str)
            assert isinstance(data["executed_at"], str)


@pytest.mark.regression
class TestSQLContract:
    """Test SQL execute endpoint contract."""

    def test_sql_execute_response_structure(self, client):
        """Test SQL execute response structure."""
        response = client.post(
            "/api/v1/sql/execute",
            json={
                "database": "typomaster",
                "query": "SELECT 1 as test",
                "read_only": True,
            },
        )

        if response.status_code == 200:
            data = response.json()

            # Check required fields
            assert "success" in data
            assert isinstance(data["success"], bool)

            if data["success"]:
                assert "result" in data
            else:
                assert "error" in data
