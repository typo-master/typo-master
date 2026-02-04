"""
Unit Tests for TypoAgent

This module provides comprehensive unit tests for the TypoAgent system.
"""

import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Import modules to test
from src.agent_framework.base_agent import BaseAgent, AgentConfig, AgentState, AgentMetrics
from src.agent_framework.message import Message, MessageType
from src.agent_framework.state import StateStore, StateSnapshot
from src.agent_framework.config import ConfigManager, AppConfig
from src.agent_framework.tool_system import ToolCategory, ToolMetadata, ToolParameter
from src.tools.file_tools import read_file, write_file
from src.tools.spell_tools import SpellChecker


class TestBaseAgent(unittest.TestCase):
    """Tests for BaseAgent class"""
    
    def test_agent_config_creation(self):
        """Test AgentConfig creation with defaults"""
        config = AgentConfig(name="TestAgent")
        self.assertEqual(config.name, "TestAgent")
        self.assertEqual(config.version, "1.0.0")
        self.assertEqual(config.max_retries, 3)
        self.assertEqual(config.timeout, 300.0)
    
    def test_agent_config_custom(self):
        """Test AgentConfig with custom values"""
        config = AgentConfig(
            name="CustomAgent",
            version="2.0.0",
            max_retries=5,
            timeout=600.0,
            custom_config={"key": "value"}
        )
        self.assertEqual(config.name, "CustomAgent")
        self.assertEqual(config.version, "2.0.0")
        self.assertEqual(config.max_retries, 5)
        self.assertEqual(config.custom_config["key"], "value")
    
    def test_agent_state_enum(self):
        """Test AgentState enum values"""
        self.assertEqual(AgentState.INITIALIZING.value, "initializing")
        self.assertEqual(AgentState.RUNNING.value, "running")
        self.assertEqual(AgentState.STOPPED.value, "stopped")
    
    def test_agent_metrics_defaults(self):
        """Test AgentMetrics default values"""
        metrics = AgentMetrics()
        self.assertEqual(metrics.total_tasks, 0)
        self.assertEqual(metrics.successful_tasks, 0)
        self.assertEqual(metrics.failed_tasks, 0)
        self.assertEqual(metrics.error_rate, 0.0)


class TestMessage(unittest.TestCase):
    """Tests for Message class"""
    
    def test_message_creation(self):
        """Test Message creation"""
        message = Message(
            type=MessageType.REQUEST,
            sender="agent1",
            receiver="agent2",
            content={"key": "value"}
        )
        self.assertEqual(message.type, MessageType.REQUEST)
        self.assertEqual(message.sender, "agent1")
        self.assertEqual(message.receiver, "agent2")
        self.assertEqual(message.content["key"], "value")
        self.assertIsNotNone(message.message_id)
        self.assertIsNotNone(message.timestamp)
    
    def test_message_to_dict(self):
        """Test Message serialization to dictionary"""
        message = Message(
            type=MessageType.RESPONSE,
            sender="agent1",
            receiver="agent2",
            content={"result": "success"}
        )
        msg_dict = message.to_dict()
        self.assertEqual(msg_dict["type"], "response")
        self.assertEqual(msg_dict["sender"], "agent1")
        self.assertEqual(msg_dict["content"]["result"], "success")
    
    def test_message_to_json(self):
        """Test Message serialization to JSON"""
        message = Message(
            type=MessageType.EVENT,
            sender="agent1",
            content={"event": "test"}
        )
        json_str = message.to_json()
        self.assertIn("event", json_str)
        self.assertIn("test", json_str)
    
    def test_message_types(self):
        """Test all message types"""
        for msg_type in MessageType:
            message = Message(type=msg_type, sender="test")
            self.assertEqual(message.type, msg_type)


class TestStateStore(unittest.TestCase):
    """Tests for StateStore class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.state_store = StateStore(storage_path=self.temp_dir)
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_state_save_and_load(self):
        """Test saving and loading state"""
        snapshot = StateSnapshot(
            state_id="test_state",
            agent_id="test_agent",
            timestamp=1234567890.0,
            state_data={"key": "value"}
        )
        
        file_path = self.state_store.save(snapshot)
        self.assertTrue(os.path.exists(file_path))
        
        loaded = self.state_store.load(file_path)
        self.assertEqual(loaded.state_id, "test_state")
        self.assertEqual(loaded.state_data["key"], "value")
    
    def test_state_verification(self):
        """Test state checksum verification"""
        snapshot = StateSnapshot(
            state_id="test_state",
            agent_id="test_agent",
            timestamp=1234567890.0,
            state_data={"data": "test"}
        )
        
        self.assertTrue(snapshot.verify())
        
        # Modify state data
        snapshot.state_data["modified"] = True
        self.assertFalse(snapshot.verify())


class TestConfigManager(unittest.TestCase):
    """Tests for ConfigManager class"""
    
    def test_config_manager_defaults(self):
        """Test ConfigManager with no config file"""
        manager = ConfigManager()
        config = manager.load()
        self.assertIsInstance(config, AppConfig)
        self.assertEqual(config.system.log_level, "INFO")
    
    def test_config_get_set(self):
        """Test configuration get and set"""
        manager = ConfigManager()
        manager.load()
        
        # Test get with default
        value = manager.get("nonexistent.key", "default")
        self.assertEqual(value, "default")
        
        # Test get existing
        value = manager.get("system.log_level")
        self.assertEqual(value, "INFO")
    
    def test_config_validation(self):
        """Test configuration validation"""
        manager = ConfigManager()
        manager.load()
        self.assertTrue(manager.validate())
    
    def test_env_override(self):
        """Test environment variable override"""
        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
            manager = ConfigManager()
            config = manager.load()
            self.assertEqual(config.system.log_level, "DEBUG")


class TestToolSystem(unittest.TestCase):
    """Tests for Tool System"""
    
    def test_tool_category(self):
        """Test ToolCategory enum"""
        self.assertEqual(ToolCategory.GITHUB.value, "github")
        self.assertEqual(ToolCategory.GIT.value, "git")
        self.assertEqual(ToolCategory.SPELL_CHECK.value, "spell_check")
    
    def test_tool_metadata(self):
        """Test ToolMetadata creation"""
        metadata = ToolMetadata(
            name="test_tool",
            description="A test tool",
            category=ToolCategory.GITHUB,
            parameters=[
                ToolParameter(name="param1", type="string", description="Test param")
            ]
        )
        self.assertEqual(metadata.name, "test_tool")
        self.assertEqual(len(metadata.parameters), 1)
    
    def test_tool_parameter(self):
        """Test ToolParameter creation"""
        param = ToolParameter(
            name="test_param",
            type="string",
            description="A test parameter",
            required=True,
            default="default_value"
        )
        self.assertEqual(param.name, "test_param")
        self.assertEqual(param.default, "default_value")


class TestFileTools(unittest.TestCase):
    """Tests for File Tools"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, "test.txt")
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_write_file(self):
        """Test writing a file"""
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            write_file(self.test_file, "Hello, World!")
        )
        self.assertIn("Written to", result)
        self.assertTrue(os.path.exists(self.test_file))
    
    def test_read_file(self):
        """Test reading a file"""
        # First write the file
        with open(self.test_file, 'w') as f:
            f.write("Test content")
        
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            read_file(self.test_file)
        )
        self.assertEqual(result, "Test content")
    
    def test_write_file_creates_directory(self):
        """Test that write_file creates directories"""
        nested_path = os.path.join(self.temp_dir, "nested", "deep", "file.txt")
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            write_file(nested_path, "Content")
        )
        self.assertTrue(os.path.exists(nested_path))


class TestSpellChecker(unittest.TestCase):
    """Tests for SpellChecker class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.checker = SpellChecker()
    
    def test_web3_terms_filtering(self):
        """Test that Web3 terms are not flagged"""
        # These should not be flagged as typos
        self.assertTrue(self.checker.is_web3_term("ethereum"))
        self.assertTrue(self.checker.is_web3_term("blockchain"))
        self.assertTrue(self.checker.is_web3_term("defi"))
    
    def test_non_web3_terms(self):
        """Test that non-Web3 terms are recognized"""
        self.assertFalse(self.checker.is_web3_term("helloo"))
        self.assertFalse(self.checker.is_web3_term("teh"))
    
    def test_spell_checker_initialization(self):
        """Test SpellChecker initialization"""
        self.assertIsNotNone(self.checker.web3_terms)
        self.assertIn("ethereum", self.checker.web3_terms)


class TestRepoTypoScanner(unittest.TestCase):
    """Tests for RepoTypoScanner"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test files
        self.md_file = os.path.join(self.temp_dir, "test.md")
        with open(self.md_file, 'w') as f:
            f.write("# Test Document\n\nThis is a test file with some helloo words.\n")
        
        self.py_file = os.path.join(self.temp_dir, "test.py")
        with open(self.py_file, 'w') as f:
            f.write("# Test Python file\nprint('Hello, World!')\n")
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_should_scan_file_md(self):
        """Test file scanning decision for .md files"""
        from src.tools.repo_typo_scanner import RepoTypoScanner
        scanner = RepoTypoScanner()
        self.assertTrue(scanner.should_scan_file(self.md_file))
    
    def test_should_scan_file_py(self):
        """Test file scanning decision for .py files"""
        from src.tools.repo_typo_scanner import RepoTypoScanner
        scanner = RepoTypoScanner()
        self.assertTrue(scanner.should_scan_file(self.py_file))
    
    def test_should_skip_git_dir(self):
        """Test that git directories are skipped"""
        from src.tools.repo_typo_scanner import RepoTypoScanner
        scanner = RepoTypoScanner()
        git_file = os.path.join(self.temp_dir, ".git", "config")
        self.assertFalse(scanner.should_scan_file(git_file))


class TestGitCommit(unittest.TestCase):
    """Tests for Git Commit tools"""
    
    def test_git_commit_with_author_tool_exists(self):
        """Test that git_commit_with_author tool is defined"""
        from src.tools.git_commit import git_commit_with_author
        self.assertIsNotNone(git_commit_with_author)
        self.assertEqual(git_commit_with_author.__name__, "git_commit_with_author")
    
    def test_git_commit_amend_tool_exists(self):
        """Test that git_commit_amend tool is defined"""
        from src.tools.git_commit import git_commit_amend
        self.assertIsNotNone(git_commit_amend)
    
    def test_git_get_commit_info_tool_exists(self):
        """Test that git_get_commit_info tool is defined"""
        from src.tools.git_commit import git_get_commit_info
        self.assertIsNotNone(git_get_commit_info)


class TestGitHubPullRequest(unittest.TestCase):
    """Tests for GitHub Pull Request tools"""
    
    def test_create_pr_with_labels_tool_exists(self):
        """Test that create_pr_with_labels tool is defined"""
        from src.tools.github_pull_request import create_pr_with_labels
        self.assertIsNotNone(create_pr_with_labels)
    
    def test_get_pr_details_tool_exists(self):
        """Test that get_pr_details tool is defined"""
        from src.tools.github_pull_request import get_pr_details
        self.assertIsNotNone(get_pr_details)
    
    def test_merge_pull_request_tool_exists(self):
        """Test that merge_pull_request tool is defined"""
        from src.tools.github_pull_request import merge_pull_request
        self.assertIsNotNone(merge_pull_request)


class TestGitHubRepoClone(unittest.TestCase):
    """Tests for GitHub Repository Clone tools"""
    
    def test_clone_github_repo_tool_exists(self):
        """Test that clone_github_repo tool is defined"""
        from src.tools.github_repo_clone import clone_github_repo
        self.assertIsNotNone(clone_github_repo)
    
    def test_get_repo_info_tool_exists(self):
        """Test that get_repo_info tool is defined"""
        from src.tools.github_repo_clone import get_repo_info
        self.assertIsNotNone(get_repo_info)
    
    def test_batch_clone_repos_tool_exists(self):
        """Test that batch_clone_repos tool is defined"""
        from src.tools.github_repo_clone import batch_clone_repos
        self.assertIsNotNone(batch_clone_repos)


class TestIntegration(unittest.TestCase):
    """Integration tests"""
    
    def test_agent_message_flow(self):
        """Test complete agent message flow"""
        # Create agents
        config = AgentConfig(name="TestAgent")
        
        # Create message
        request = Message(
            type=MessageType.REQUEST,
            sender="test",
            receiver="target",
            content={"action": "test"}
        )
        
        # Convert to dict and back
        msg_dict = request.to_dict()
        self.assertEqual(msg_dict["content"]["action"], "test")
    
    def test_config_with_all_sections(self):
        """Test configuration with all sections"""
        from src.agent_framework.config import SystemConfig, GitHubConfig, SpellConfig, PRConfig
        
        system = SystemConfig(log_level="DEBUG")
        github = GitHubConfig(token="test_token")
        spell = SpellConfig(min_confidence=0.8)
        pr = PRConfig(auto_create=True)
        
        app_config = AppConfig(
            system=system,
            github=github,
            spell=spell,
            pr=pr
        )
        
        self.assertEqual(app_config.system.log_level, "DEBUG")
        self.assertEqual(app_config.github.token, "test_token")
        self.assertEqual(app_config.spell.min_confidence, 0.8)
        self.assertTrue(app_config.pr.auto_create)


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestBaseAgent))
    suite.addTests(loader.loadTestsFromTestCase(TestMessage))
    suite.addTests(loader.loadTestsFromTestCase(TestStateStore))
    suite.addTests(loader.loadTestsFromTestCase(TestConfigManager))
    suite.addTests(loader.loadTestsFromTestCase(TestToolSystem))
    suite.addTests(loader.loadTestsFromTestCase(TestFileTools))
    suite.addTests(loader.loadTestsFromTestCase(TestSpellChecker))
    suite.addTests(loader.loadTestsFromTestCase(TestRepoTypoScanner))
    suite.addTests(loader.loadTestsFromTestCase(TestGitCommit))
    suite.addTests(loader.loadTestsFromTestCase(TestGitHubPullRequest))
    suite.addTests(loader.loadTestsFromTestCase(TestGitHubRepoClone))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite)


if __name__ == "__main__":
    run_tests()
