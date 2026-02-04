"""
Repository Typo Scanner - Advanced typo detection for repositories

This module provides advanced typo scanning functionality for repositories,
including file filtering, Web3 term filtering, and comprehensive reporting.
"""

import os
import re
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field

from ..agent_framework.tool_system import tool, ToolCategory, ToolResult
from ..agent_framework.logger import get_logger

logger = get_logger(__name__)


# Web3 terms that should not be flagged as typos
WEB3_TERMS = [
    "blockchain", "ethereum", "bitcoin", "crypto", "cryptocurrency",
    "web3", "defi", "nft", "dao", "smart", "contract", "solidity",
    "token", "airdrop", "metamask", "wallet", "gas", "hash", "nonce",
    "validator", "consensus", "fork", "merge", "staking", "yield",
    "liquidity", "pool", "swap", "bridge", "oracle", "gwei", "wei",
    "satoshi", "halving", "mining", "proof", "work", "stake",
    "uniswap", "aave", "compound", "maker", "curve", "balancer",
    "chainlink", "polygon", "arbitrum", "optimism", "avalanche",
    "solana", "polkadot", "cardano", "cosmos", "near", "flow",
    "tezos", "algorand", "stellar", "ripple", "dogecoin", "shiba",
    "binance", "coinbase", "kraken", "gemini", "ftx", "blockfi",
    "celsius", "nexo", "celcius", "blockfi", "ledger", "trezor",
    "cold", "hot", "private", "public", "key", "address",
    "transaction", "block", "blockchain", "decentralized", "distributed",
    "permissionless", "trustless", "immutable", "transparent", "audit",
    "verifiable", "provable", "zk", "zero", "knowledge", "snark",
    "stark", "rollup", "layer", "scaling", "sharding", "sidechain",
    "l1", "l2", "layer1", "layer2", "mainnet", "testnet", "devnet",
    "ganache", "hardhat", "truffle", "foundry", "brownie", "ape",
    "openzeppelin", "erc", "erc20", "erc721", "erc1155", "eip",
    "bip", "bip32", "bip39", "bip44", "mnemonic", "seed", "phrase",
    "hd", "hierarchical", "deterministic", "derivation", "path",
    "utxo", "unspent", "transaction", "output", "spend", "script",
    "sig", "signature", "ecdsa", "rsa", "ed25519", "secp256k1",
    "keccak", "sha256", "sha3", "ripemd", "hash", "merkle", "patricia",
    "trie", "state", "storage", "evm", "ethereum", "virtual", "machine",
    "opcode", "gaslimit", "gasprice", "block", "number", "timestamp",
    "difficulty", "gasused", "logs", "bloom", "receipt", "transaction",
    "index", "hash", "parent", "uncle", "ommer", "nonce", "miner",
    "extra", "data", "mix", "hash", "coinbase", "state", "root",
    "transactions", "receipts", "logs", "bloom", "difficulty", "total",
    "gas", "size", "uncles", "ommer", "transactions", "uncle", "ommer",
]


# Code patterns to exclude
CODE_PATTERNS = [
    r'import\s+\w+',  # Import statements
    r'from\s+\w+\s+import',  # From imports
    r'class\s+\w+',  # Class definitions
    r'def\s+\w+',  # Function definitions
    r'var\s+\w+',  # Variable declarations
    r'let\s+\w+',  # Let declarations
    r'const\s+\w+',  # Const declarations
    r'https?://',  # URLs
    r'www\.',  # URLs
    r'\.com',  # URLs
    r'\.org',  # URLs
    r'\.io',  # URLs
    r'\.dev',  # URLs
    r'\.app',  # URLs
]


@dataclass
class TypoResult:
    """Result of a typo detection"""
    file_path: str
    line_number: int
    typo: str
    correction: str
    context: str
    confidence: float


@dataclass
class ScanReport:
    """Report of a repository scan"""
    repo_path: str
    total_files: int = 0
    scanned_files: int = 0
    typos_found: int = 0
    results: List[TypoResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class RepoTypoScanner:
    """Repository typo scanner with advanced filtering"""
    
    def __init__(self, web3_terms: Optional[List[str]] = None):
        """
        Initialize typo scanner
        
        Args:
            web3_terms: List of Web3 terms to filter out
        """
        self.web3_terms = set(term.lower() for term in (web3_terms or WEB3_TERMS))
        self.code_patterns = [re.compile(pattern) for pattern in CODE_PATTERNS]
        
        # Supported file extensions
        self.supported_extensions = {
            '.md', '.txt', '.rst', '.adoc',  # Documentation
            '.py', '.js', '.ts', '.jsx', '.tsx',  # Code
            '.sol', '.rs', '.go', '.java', '.cpp',  # Smart contracts
        }
        
        # Directories to skip
        self.skip_dirs = {
            '.git', '.github', 'node_modules', '__pycache__',
            '.venv', 'venv', 'env', 'dist', 'build',
            '.idea', '.vscode', 'target', 'bin', 'obj',
        }
        
        # Maximum file size to scan (bytes)
        self.max_file_size = 100000
    
    def should_scan_file(self, file_path: str) -> bool:
        """
        Check if a file should be scanned
        
        Args:
            file_path: File path
            
        Returns:
            True if file should be scanned
        """
        path = Path(file_path)
        
        # Check extension
        if path.suffix.lower() not in self.supported_extensions:
            return False
        
        # Check size
        try:
            if path.stat().st_size > self.max_file_size:
                return False
        except OSError:
            return False
        
        # Check if in skip directory
        for part in path.parts:
            if part in self.skip_dirs:
                return False
        
        return True
    
    def is_web3_term(self, word: str) -> bool:
        """
        Check if a word is a Web3 term
        
        Args:
            word: Word to check
            
        Returns:
            True if word is a Web3 term
        """
        return word.lower() in self.web3_terms
    
    def is_code_pattern(self, text: str) -> bool:
        """
        Check if text matches code patterns
        
        Args:
            text: Text to check
            
        Returns:
            True if text matches code patterns
        """
        for pattern in self.code_patterns:
            if pattern.search(text):
                return True
        return False
    
    def scan_file(self, file_path: str) -> List[TypoResult]:
        """
        Scan a single file for typos
        
        Args:
            file_path: File path
            
        Returns:
            List of typo results
        """
        results = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                # Skip empty lines
                if not line.strip():
                    continue
                
                # Skip code patterns
                if self.is_code_pattern(line):
                    continue
                
                # Check for typos using pycorrector
                try:
                    import pycorrector
                    corrected, details = pycorrector.correct(line)
                    
                    for typo, correction in details:
                        # Filter Web3 terms
                        if self.is_web3_term(typo) or self.is_web3_term(correction):
                            continue
                        
                        # Add result
                        results.append(TypoResult(
                            file_path=file_path,
                            line_number=line_num,
                            typo=typo,
                            correction=correction,
                            context=line.strip(),
                            confidence=0.8,
                        ))
                except Exception as e:
                    logger.warning(f"Error checking line {line_num} in {file_path}: {e}")
        
        except Exception as e:
            logger.error(f"Error scanning file {file_path}: {e}")
        
        return results
    
    def scan_repository(
        self,
        repo_path: str,
        max_files: Optional[int] = None,
    ) -> ScanReport:
        """
        Scan a repository for typos
        
        Args:
            repo_path: Repository path
            max_files: Maximum number of files to scan
            
        Returns:
            Scan report
        """
        report = ScanReport(repo_path=repo_path)
        
        logger.info(f"Scanning repository: {repo_path}")
        
        # Find all files
        all_files = []
        for root, dirs, files in os.walk(repo_path):
            # Skip directories
            dirs[:] = [d for d in dirs if d not in self.skip_dirs]
            
            for file in files:
                file_path = os.path.join(root, file)
                if self.should_scan_file(file_path):
                    all_files.append(file_path)
        
        report.total_files = len(all_files)
        
        # Scan files
        scanned_count = 0
        for file_path in all_files:
            if max_files and scanned_count >= max_files:
                break
            
            try:
                results = self.scan_file(file_path)
                report.results.extend(results)
                report.scanned_files += 1
                
                if results:
                    report.typos_found += len(results)
                    logger.info(f"Found {len(results)} typos in {file_path}")
                
            except Exception as e:
                report.errors.append(f"{file_path}: {str(e)}")
            
            scanned_count += 1
        
        logger.info(f"Scan complete: {report.typos_found} typos found in {report.scanned_files} files")
        
        return report


# Tool functions

@tool(
    name="scan_local_repo",
    description="Scan a local repository for typos",
    category=ToolCategory.SPELL_CHECK,
    examples=[
        {
            "input": {"repo_directory": "./repos/solidity"},
            "output": "Scan report with typos found"
        }
    ]
)
async def scan_local_repo(
    repo_directory: str,
    max_files: Optional[int] = None,
) -> ToolResult:
    """
    Scan a local repository for typos
    
    Args:
        repo_directory: Repository directory path
        max_files: Maximum number of files to scan
        
    Returns:
        Tool execution result with scan report
    """
    try:
        scanner = RepoTypoScanner()
        report = scanner.scan_repository(repo_directory, max_files)
        
        # Convert report to dict
        report_dict = {
            "repo_path": report.repo_path,
            "total_files": report.total_files,
            "scanned_files": report.scanned_files,
            "typos_found": report.typos_found,
            "results": [
                {
                    "file_path": r.file_path,
                    "line_number": r.line_number,
                    "typo": r.typo,
                    "correction": r.correction,
                    "context": r.context,
                    "confidence": r.confidence,
                }
                for r in report.results
            ],
            "errors": report.errors,
        }
        
        return ToolResult(success=True, data=report_dict)
    except Exception as e:
        logger.error(f"Failed to scan repository: {e}")
        return ToolResult(success=False, error=str(e))


@tool(
    name="scan_single_file",
    description="Scan a single file for typos",
    category=ToolCategory.SPELL_CHECK,
    examples=[
        {
            "input": {"file_path": "./repos/solidity/README.md"},
            "output": "List of typos found"
        }
    ]
)
async def scan_single_file(
    file_path: str,
) -> ToolResult:
    """
    Scan a single file for typos
    
    Args:
        file_path: File path
        
    Returns:
        Tool execution result with typos
    """
    try:
        scanner = RepoTypoScanner()
        results = scanner.scan_file(file_path)
        
        results_dict = [
            {
                "file_path": r.file_path,
                "line_number": r.line_number,
                "typo": r.typo,
                "correction": r.correction,
                "context": r.context,
                "confidence": r.confidence,
            }
            for r in results
        ]
        
        return ToolResult(success=True, data={"results": results_dict})
    except Exception as e:
        logger.error(f"Failed to scan file: {e}")
        return ToolResult(success=False, error=str(e))


@tool(
    name="get_typo_summary",
    description="Get a summary of typos found in a repository",
    category=ToolCategory.SPELL_CHECK,
    examples=[
        {
            "input": {"repo_directory": "./repos/solidity"},
            "output": "Typo summary statistics"
        }
    ]
)
async def get_typo_summary(
    repo_directory: str,
) -> ToolResult:
    """
    Get a summary of typos found in a repository
    
    Args:
        repo_directory: Repository directory path
        
    Returns:
        Tool execution result with summary
    """
    try:
        scanner = RepoTypoScanner()
        report = scanner.scan_repository(repo_directory)
        
        # Calculate summary statistics
        typo_counts = {}
        for result in report.results:
            typo = result.typo
            typo_counts[typo] = typo_counts.get(typo, 0) + 1
        
        # Sort by frequency
        sorted_typos = sorted(typo_counts.items(), key=lambda x: x[1], reverse=True)
        
        summary = {
            "total_files": report.total_files,
            "scanned_files": report.scanned_files,
            "typos_found": report.typos_found,
            "unique_typos": len(typo_counts),
            "most_common_typos": sorted_typos[:10],
            "files_with_typos": len(set(r.file_path for r in report.results)),
        }
        
        return ToolResult(success=True, data=summary)
    except Exception as e:
        logger.error(f"Failed to get typo summary: {e}")
        return ToolResult(success=False, error=str(e))

