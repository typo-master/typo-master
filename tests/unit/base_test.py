"""
Base test class for unit tests.
"""

import pytest
from unittest.mock import MagicMock


class BaseUnitTest:
    """Base class for unit tests."""

    @pytest.fixture(autouse=True)
    def setup_mocks(self, mock_mysql_storage, mock_agent_runtime):
        """Setup mocks for all tests."""
        self.storage = mock_mysql_storage
        self.agent_runtime = mock_agent_runtime

    def assert_success(self, result: dict):
        """Assert that a result indicates success."""
        assert result.get("success", False) is True

    def assert_failure(self, result: dict):
        """Assert that a result indicates failure."""
        assert result.get("success", False) is False

    def create_mock_response(self, success: bool = True, **kwargs) -> dict:
        """Create a mock response dict."""
        response = {"success": success}
        response.update(kwargs)
        return response
