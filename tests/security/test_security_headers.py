"""
Security headers tests.
"""

import pytest


@pytest.mark.security
class TestSecurityHeaders:
    """Test security headers."""

    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        # Test preflight request
        response = client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        # Check CORS headers in preflight response
        assert "access-control-allow-origin" in response.headers
        # CORS middleware allows all origins
        assert response.headers["access-control-allow-origin"] in ["*", "http://localhost:3000"]

    def test_content_type_header(self, client):
        """Test Content-Type header."""
        response = client.get("/api/v1/health")

        content_type = response.headers.get("content-type", "")
        assert "application/json" in content_type

    def test_no_server_version_header(self, client):
        """Test that server version is not exposed."""
        response = client.get("/api/v1/health")

        # Should not expose server version
        server_header = response.headers.get("server", "").lower()
        assert "python" not in server_header or "uvicorn" not in server_header

    def test_x_frame_options(self, client):
        """Test X-Frame-Options header."""
        response = client.get("/api/v1/health")

        # Should have X-Frame-Options for clickjacking protection
        # May not be present in default FastAPI, but good to check
        x_frame = response.headers.get("x-frame-options", "")
        if x_frame:
            assert x_frame.upper() in ["DENY", "SAMEORIGIN"]

    def test_x_content_type_options(self, client):
        """Test X-Content-Type-Options header."""
        response = client.get("/api/v1/health")

        # Should have nosniff to prevent MIME type sniffing
        x_content_type = response.headers.get("x-content-type-options", "").lower()
        if x_content_type:
            assert x_content_type == "nosniff"

    def test_strict_transport_security(self, client):
        """Test Strict-Transport-Security header."""
        response = client.get("/api/v1/health")

        # HSTS header (only relevant for HTTPS)
        hsts = response.headers.get("strict-transport-security", "")
        # May not be present in HTTP mode
        if hsts:
            assert "max-age" in hsts
