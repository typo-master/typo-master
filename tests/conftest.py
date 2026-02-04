"""
Pytest configuration and fixtures for TypoAgent tests.
"""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Pytest configuration
pytest_plugins = ['pytest_asyncio']


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp = tempfile.mkdtemp()
    yield temp
    import shutil
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def temp_file(temp_dir):
    """Create a temporary file for tests."""
    file_path = os.path.join(temp_dir, "test_file.txt")
    with open(file_path, 'w') as f:
        f.write("Test content")
    return file_path


@pytest.fixture
def temp_repo(temp_dir):
    """Create a temporary git repository for tests."""
    repo_path = os.path.join(temp_dir, "test_repo")
    os.makedirs(repo_path)
    
    # Initialize git repo
    os.system(f"cd {repo_path} && git init")
    
    # Create a test file
    test_file = os.path.join(repo_path, "README.md")
    with open(test_file, 'w') as f:
        f.write("# Test Repository\n\nThis is a test file.\n")
    
    # Add and commit
    os.system(f"cd {repo_path} && git add . && git commit -m 'Initial commit'")
    
    return repo_path


@pytest.fixture
def mock_github_token():
    """Mock GitHub token for tests."""
    return "mock_github_token_12345"


@pytest.fixture
def sample_typo_content():
    """Sample content with typos for testing."""
    return """
# Test Document

This is a document with some helloo words and teh typos.

The quick brown fox jumps over the lazy dog.

Web3 is greate for defi and nft projects.
"""


@pytest.fixture
def sample_clean_content():
    """Sample clean content without typos."""
    return """
# Clean Document

This is a clean document without any typos.

The quick brown fox jumps over the lazy dog.

Ethereum is a great blockchain for defi applications.
"""


@pytest.fixture
def agent_config():
    """Create a sample agent configuration."""
    from src.agent_framework.base_agent import AgentConfig
    return AgentConfig(
        name="TestAgent",
        version="1.0.0",
        description="A test agent",
        max_retries=3,
        timeout=300.0
    )


@pytest.fixture
def app_config():
    """Create a sample application configuration."""
    from src.agent_framework.config import AppConfig, SystemConfig, GitHubConfig
    return AppConfig(
        system=SystemConfig(log_level="DEBUG"),
        github=GitHubConfig(token="test_token"),
    )


@pytest.fixture
def spell_checker():
    """Create a spell checker instance."""
    from src.tools.spell_tools import SpellChecker
    return SpellChecker()


@pytest.fixture
def typo_scanner():
    """Create a typo scanner instance."""
    from src.tools.repo_typo_scanner import RepoTypoScanner
    return RepoTypoScanner()


# Markers for test categories
pytestmark = [
    pytest.mark.unit,
    pytest.mark.integration,
]


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add categories."""
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        else:
            item.add_marker(pytest.mark.unit)
