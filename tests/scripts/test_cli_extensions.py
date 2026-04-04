# tests/scripts/test_cli_extensions.py
import pytest
from unittest.mock import Mock, patch
import argparse

from src.scripts.web3_typo_hunter_cli import parse_args


class TestCLIExtensions:
    """CLI 扩展测试"""

    def test_translate_subcommand(self):
        """测试 translate 子命令"""
        with patch('sys.argv', ['cli', 'translate', '--token', 'test_token', '--repo', 'owner/repo', '--target-lang', 'zh']):
            args = parse_args()
            assert args.command == 'translate'
            assert args.token == 'test_token'
            assert args.repo == 'owner/repo'
            assert args.target_lang == 'zh'

    def test_translate_default_target_lang(self):
        """测试 translate 默认目标语言"""
        with patch('sys.argv', ['cli', 'translate', '--token', 'test_token', '--repo', 'owner/repo']):
            args = parse_args()
            assert args.target_lang == 'zh'  # 默认值

    def test_find_issues_subcommand(self):
        """测试 find-issues 子命令"""
        with patch('sys.argv', ['cli', 'find-issues', '--token', 'test_token', '--repo', 'owner/repo', '--limit', '20']):
            args = parse_args()
            assert args.command == 'find-issues'
            assert args.token == 'test_token'
            assert args.repo == 'owner/repo'
            assert args.limit == 20

    def test_find_contributions_subcommand(self):
        """测试 find-contributions 子命令"""
        with patch('sys.argv', ['cli', 'find-contributions', '--token', 'test_token', '--repos', 'owner/repo1', 'owner/repo2']):
            args = parse_args()
            assert args.command == 'find-contributions'
            assert args.token == 'test_token'
            assert args.repos == ['owner/repo1', 'owner/repo2']
