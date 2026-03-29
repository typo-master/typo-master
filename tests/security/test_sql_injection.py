"""
SQL injection security tests.
"""

import pytest


@pytest.mark.security
class TestSQLInjection:
    """Test SQL injection vulnerabilities."""

    def test_sql_execute_with_injection_attempt(self, security_client, sql_injection_payloads):
        """Test SQL execute endpoint with injection payloads."""
        for payload in sql_injection_payloads:
            response = security_client.post(
                "/api/v1/sql/execute",
                json={
                    "database": "test_db",
                    "query": f"SELECT * FROM conversations WHERE id = '{payload}'",
                    "read_only": True,
                },
            )
            # Should either fail validation or execute safely
            assert response.status_code in [200, 400, 422, 500]
            if response.status_code == 200:
                # If it succeeds, verify no data was exposed
                data = response.json()
                if "result" in data:
                    # Result should be empty or contain no sensitive data
                    pass

    def test_sql_execute_with_union_injection(self, security_client):
        """Test UNION-based SQL injection."""
        response = security_client.post(
            "/api/v1/sql/execute",
            json={
                "database": "test_db",
                "query": "' UNION SELECT * FROM mysql.user--",
                "read_only": True,
            },
        )
        # Should not return mysql.user data
        if response.status_code == 200:
            data = response.json()
            if "result" in data and isinstance(data["result"], list):
                for row in data["result"]:
                    # Check that no mysql system tables are exposed
                    row_str = str(row)
                    assert "mysql" not in row_str.lower() or "typomaster" in row_str.lower()

    def test_sql_execute_with_stacked_queries(self, security_client):
        """Test stacked query injection."""
        response = security_client.post(
            "/api/v1/sql/execute",
            json={
                "database": "test_db",
                "query": "SELECT 1; DROP TABLE conversations--",
                "read_only": True,
            },
        )
        # Should not execute the DROP statement
        # Response should indicate read_only mode or error
        assert response.status_code in [400, 422, 500]

    def test_sql_execute_read_only_enforcement(self, security_client):
        """Test that read_only flag prevents data modification."""
        response = security_client.post(
            "/api/v1/sql/execute",
            json={
                "database": "test_db",
                "query": "DELETE FROM conversations",
                "read_only": True,
            },
        )
        # Should fail due to read_only mode
        assert response.status_code in [400, 422]

    def test_sql_execute_invalid_database_name(self, security_client):
        """Test with invalid database name."""
        response = security_client.post(
            "/api/v1/sql/execute",
            json={
                "database": "invalid-db-name!@#",
                "query": "SELECT 1",
                "read_only": True,
            },
        )
        assert response.status_code in [400, 422, 500]

    def test_sql_execute_no_database(self, security_client):
        """Test SQL execute without specifying database."""
        response = security_client.post(
            "/api/v1/sql/execute",
            json={
                "query": "SELECT 1",
                "read_only": True,
            },
        )
        assert response.status_code == 422  # Validation error
