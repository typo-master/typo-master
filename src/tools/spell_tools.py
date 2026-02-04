"""
Spell Check Tools - Typo Detection and Correction

This module provides tools for spell checking and typo detection.
"""

import re
from typing import Any, Dict, List, Optional, Tuple
import pycorrector

from ..agent_framework.tool_system import tool, ToolCategory
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


class SpellChecker:
    """Spell checker with Web3 term filtering"""
    
    def __init__(self):
        """Initialize spell checker"""
        self.web3_terms = set(term.lower() for term in WEB3_TERMS)
    
    def check_text(self, text: str) -> List[Tuple[str, str]]:
        """
        Check text for spelling errors
        
        Args:
            text: Text to check
            
        Returns:
            List of (typo, correction) tuples
        """
        errors, details = pycorrector.correct(text)
        
        # Filter out Web3 terms
        filtered_errors = []
        for typo, correction in details:
            # Check if it's a Web3 term
            if typo.lower() in self.web3_terms:
                continue
            
            # Check if correction is a Web3 term
            if correction.lower() in self.web3_terms:
                continue
            
            # Additional filters
            if self._should_skip(typo, correction):
                continue
            
            filtered_errors.append((typo, correction))
        
        return filtered_errors
    
    def _should_skip(self, typo: str, correction: str) -> bool:
        """
        Check if a typo should be skipped
        
        Args:
            typo: Original text
            correction: Suggested correction
            
        Returns:
            True if should skip
        """
        # Skip very short words
        if len(typo) <= 3:
            return True
        
        # Skip if it looks like code
        if re.match(r'^[_a-zA-Z][_a-zA-Z0-9]*$', typo):
            # Check if it's in a common code context
            code_patterns = [
                r'\bdef\s+\w+',  # Function definition
                r'\bclass\s+\w+',  # Class definition
                r'\bconst\s+\w+',  # Constant
                r'\blet\s+\w+',  # Variable
                r'\bvar\s+\w+',  # Variable
                r'\bfunction\s+\w+',  # Function
                r'\bimport\s+\w+',  # Import
                r'\bfrom\s+\w+',  # From import
            ]
            for pattern in code_patterns:
                if re.search(pattern, typo):
                    return True
        
        # Skip URLs
        if '://' in typo or typo.startswith(('http', 'https', 'ftp')):
            return True
        
        # Skip file paths
        if '/' in typo or '\\' in typo:
            return True
        
        # Skip if it's an acronym
        if typo.isupper() and len(typo) <= 5:
            return True
        
        return False
    
    def get_corrections(self, text: str) -> Dict[str, str]:
        """
        Get suggested corrections for text
        
        Args:
            text: Text to check
            
        Returns:
            Dictionary of {typo: correction}
        """
        errors = self.check_text(text)
        return {typo: correction for typo, correction in errors}


# Tool functions

@tool(
    name="check_spelling",
    description="Check text for spelling errors",
    category=ToolCategory.SPELL_CHECK,
    examples=[
        {
            "input": {"text": "This is a test with some typos"},
            "output": [{"typo": "typo", "correction": "type"}]
        }
    ]
)
async def check_spelling(
    text: str,
) -> List[Dict[str, str]]:
    """
    Check text for spelling errors
    
    Args:
        text: Text to check
        
    Returns:
        List of {typo, correction} dictionaries
    """
    checker = SpellChecker()
    errors = checker.check_text(text)
    
    return [
        {"typo": typo, "correction": correction}
        for typo, correction in errors
    ]


@tool(
    name="correct_spelling",
    description="Correct spelling errors in text",
    category=ToolCategory.SPELL_CHECK,
    examples=[
        {
            "input": {"text": "This is a test with some typos"},
            "output": "This is a test with some types"
        }
    ]
)
async def correct_spelling(
    text: str,
) -> str:
    """
    Correct spelling errors in text
    
    Args:
        text: Text to correct
        
    Returns:
        Corrected text
    """
    checker = SpellChecker()
    errors = checker.check_text(text)
    
    corrected = text
    for typo, correction in errors:
        # Replace only the first occurrence to avoid over-correction
        corrected = corrected.replace(typo, correction, 1)
    
    return corrected


@tool(
    name="get_spelling_suggestions",
    description="Get spelling suggestions for a word",
    category=ToolCategory.SPELL_CHECK,
    examples=[
        {
            "input": {"word": "typo"},
            "output": ["type", "typo", "top"]
        }
    ]
)
async def get_spelling_suggestions(
    word: str,
    max_suggestions: int = 5,
) -> List[str]:
    """
    Get spelling suggestions for a word
    
    Args:
        word: Word to get suggestions for
        max_suggestions: Maximum number of suggestions
        
    Returns:
        List of suggestions
    """
    # Use pycorrector to get suggestions
    checker = SpellChecker()
    
    # Create a sentence with the word
    test_text = f"This is a {word}"
    errors = checker.check_text(test_text)
    
    suggestions = []
    for typo, correction in errors:
        if typo == word:
            suggestions.append(correction)
    
    # Also add the original word
    if word not in suggestions:
        suggestions.append(word)
    
    return suggestions[:max_suggestions]


@tool(
    name="is_web3_term",
    description="Check if a word is a Web3 term",
    category=ToolCategory.SPELL_CHECK,
    examples=[
        {
            "input": {"word": "blockchain"},
            "output": True
        }
    ]
)
async def is_web3_term(
    word: str,
) -> bool:
    """
    Check if a word is a Web3 term
    
    Args:
        word: Word to check
        
    Returns:
        True if it's a Web3 term
    """
    checker = SpellChecker()
    return word.lower() in checker.web3_terms


@tool(
    name="check_file_spelling",
    description="Check spelling in a file",
    category=ToolCategory.SPELL_CHECK,
    examples=[
        {
            "input": {"file_path": "/path/to/file.md"},
            "output": [{"file": "file.md", "errors": [...]}]
        }
    ]
)
async def check_file_spelling(
    file_path: str,
) -> Dict[str, Any]:
    """
    Check spelling in a file
    
    Args:
        file_path: Path to file
        
    Returns:
        Dictionary with file name and errors
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        checker = SpellChecker()
        errors = checker.check_text(content)
        
        return {
            "file": file_path,
            "errors": [
                {"typo": typo, "correction": correction}
                for typo, correction in errors
            ],
            "error_count": len(errors),
        }
    
    except Exception as e:
        logger.error(f"Error checking file spelling: {e}")
        return {
            "file": file_path,
            "errors": [],
            "error_count": 0,
            "error": str(e),
        }
