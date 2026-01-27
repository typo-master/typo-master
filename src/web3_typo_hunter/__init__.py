#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web3 Typo Hunter模块
这个模块用于发现Web3项目中的拼写错误，并自动提交PR修复
"""

# 为方便导入，从子模块导入重要的类和函数
from src.web3_typo_hunter.controller import Web3TypoHunterController
from src.web3_typo_hunter.discovery.repo_finder import RepoFinder
from src.web3_typo_hunter.discovery.repo_manager import RepoManager
from src.web3_typo_hunter.scanner.typo_scanner import TypoScanner
from src.web3_typo_hunter.scanner.typo_fixer import TypoFixer
from src.web3_typo_hunter.processor.pr_creator import PRCreator
from src.web3_typo_hunter.processor.report_generator import ReportGenerator

__version__ = "0.1.0"
