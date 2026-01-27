#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件 - 存储项目的各种全局配置参数
"""

import os
from typing import List, Dict, Any

# 项目基础路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 结果存储路径
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")

# 仓库存储路径
REPOS_DIR = os.path.join(PROJECT_ROOT, "data/repos")

# GitHub API 设置
GITHUB_API_BASE_URL = "https://api.github.com"
GITHUB_API_HEADERS = {
    "Accept": "application/vnd.github.v3+json"
}

# Web3术语白名单 - 避免误报
WEB3_TERMS: List[str] = [
    "ethereum", "solidity", "blockchain", "defi", "nft", "dao", "web3", "dapp", "dapps", 
    "metamask", "wallet", "wallets", "token", "tokens", "protocol", "mainnet", "testnet",
    "erc20", "erc721", "erc1155", "evm", "gas", "gwei", "wei", "eth", "bnb", "sol",
    "smart contract", "truffle", "hardhat", "ganache", "openzeppelin", "chainlink",
    "uniswap", "aave", "compound", "staking", "yield", "farming", "mining", "miner", "miners",
    "consensus", "block", "blocks", "tx", "txs", "transaction", "transactions",
    "ledger", "merkle", "ipfs", "filecoin", "arweave", "decentralized", "centralized",
    "public key", "private key", "signature", "hash", "hashing", "cryptography",
]

# Web3相关主题
WEB3_TOPICS: List[str] = [
    "blockchain", "web3", "ethereum", "solidity", "smart-contract", 
    "defi", "nft", "dao", "cryptocurrency", "token"
]

# 支持的文件扩展名
SUPPORTED_EXTENSIONS: List[str] = [
    '.md', '.txt', '.js', '.ts', '.jsx', '.tsx', '.sol', 
    '.py', '.html', '.css', '.json', '.yml', '.yaml'
]

# 默认查询参数
DEFAULT_SEARCH_PARAMS = {
    "days": 30,
    "min_stars": 100,
    "limit": 50
}

# PR模板
PR_TEMPLATE = """
## 修复拼写错误

这个PR修复了文档和代码注释中的一些拼写错误，提高了代码的可读性。

### 修复内容
{fixed_files}

没有功能上的改动，只是文本修正。

祝项目越来越好！
"""

# 确保目录存在
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(REPOS_DIR, exist_ok=True) 