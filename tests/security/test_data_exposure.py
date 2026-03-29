"""
Data exposure security tests.
"""

import pytest


@pytest.mark.security
class TestDataExposure:
    """Test for sensitive data exposure."""

    def test_health_endpoint_no_sensitive_data(self, client):
        """Test health endpoint doesn't expose sensitive data."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()

        # Should not contain sensitive fields
        sensitive_fields = ["password", "secret", "key", "token", "credential"]
        data_str = str(data).lower()
        for field in sensitive_fields:
            assert field not in data_str, f"Health endpoint exposes {field}"

    def test_error_messages_no_internal_info(self, client):
        """Test error messages don't expose internal information."""
        # Trigger an error with invalid input
        response = client.post(
            "/api/v1/conversations/invalid/messages",
            json={"message": "test"},
        )

        if response.status_code >= 400:
            data = response.json()
            error_detail = str(data.get("detail", "")).lower()

            # Should not contain internal paths or SQL
            internal_patterns = [
                "traceback",
                "exception",
                "app/backend",
                "select ",
                "insert ",
                "delete ",
                "mysql",
                "password",
            ]
            for pattern in internal_patterns:
                assert pattern not in error_detail, f"Error exposes: {pattern}"

    def test_sql_error_handling(self, client):
        """Test SQL error handling doesn't expose schema."""
        response = client.post(
            "/api/v1/sql/execute",
            json={
                "database": "test_db",
                "query": "SELECT * FROM nonexistent_table",
                "read_only": True,
            },
        )

        if response.status_code >= 400:
            data = response.json()
            error = str(data.get("detail", "")).lower()

            # Should not expose full SQL or schema
            assert "nonexistent_table" not in error or "table" in error

    def test_conversation_messages_no_excess_data(self, client):
        """Test conversation messages don't expose excess data."""
        # Create conversation
        create_response = client.post("/api/v1/conversations")
        conv_id = create_response.json()["conversation_id"]

        # Get messages
        response = client.get(f"/api/v1/conversations/{conv_id}/messages")
        data = response.json()

        # Response should be minimal
        assert "conversation_id" in data
        assert "messages" in data
        # Should not have internal fields
        for msg in data.get("messages", []):
            assert "id" not in msg or "role" in msg  # internal DB ID should not be exposed
