"""
Test cases for Spell Tools
"""

import pytest
from unittest.mock import Mock, AsyncMock

from src.tools import (
    check_spelling,
    correct_spelling,
    get_spelling_suggestions,
    is_web3_term,
    check_file_spelling,
)
from src.agent_framework.logger import get_logger

logger = get_logger(__name__)


class TestSpellTools:
    """Test cases for spell checking tools"""
    
    @pytest.mark.asyncio
    async def test_check_spelling(self):
        """Test checking spelling in text"""
        result = await check_spelling(text="This is a test with some typos")
        
        # Should return a result
        assert "success" in result
        assert "data" in result
        
        # Data should be a list
        if result.get("success"):
            assert isinstance(result["data"], list)
    
    @pytest.mark.asyncio
    async def test_correct_spelling(self):
        """Test correcting spelling in text"""
        result = await correct_spelling(text="This is a test with some typos")
        
        # Should return a result
        assert "success" in result
        assert "data" in result
    
    @pytest.mark.asyncio
    async def test_get_spelling_suggestions(self):
        """Test getting spelling suggestions"""
        result = await get_spelling_suggestions(word="typo")
        
        # Should return a result
        assert "success" in result
        assert "data" in result
        
        # Data should be a list
        if result.get("success"):
            assert isinstance(result["data"], list)
    
    @pytest.mark.asyncio
    async def test_is_web3_term(self):
        """Test checking if word is a Web3 term"""
        # Test known Web3 term
        result = await is_web3_term(word="blockchain")
        
        assert result["success"] == True
        assert result["data"] == True
        
        # Test non-Web3 term
        result = await is_web3_term(word="computer")
        
        assert result["success"] == True
        assert result["data"] == False
    
    @pytest.mark.asyncio
    async def test_check_file_spelling(self):
        """Test checking spelling in a file"""
        result = await check_file_spelling(file_path="test_file.md")
        
        # Should return a result
        assert "success" in result
        assert "data" in result


class TestSpellToolsIntegration:
    """Test cases for spell tools integration"""
    
    @pytest.mark.asyncio
    async def test_spell_check_and_correct(self):
        """Test spell checking and correction workflow"""
        text = "This is a test with some typos"
        
        # Check spelling
        check_result = await check_spelling(text=text)
        
        if check_result.get("success") and check_result["data"]:
            # Correct spelling
            correct_result = await correct_spelling(text=text)
            
            assert correct_result["success"] == True
            assert correct_result["data"] is not None
    
    @pytest.mark.asyncio
    async def test_web3_term_filtering(self):
        """Test Web3 term filtering"""
        text = "This blockchain project uses smart contracts"
        
        # Check spelling
        result = await check_spelling(text=text)
        
        # Should not flag Web3 terms as typos
        if result.get("success"):
            typos = result["data"]
            
            # Check that "blockchain" and "smart" are not flagged
            typo_words = [t.get("typo", "") for t in typos]
            assert "blockchain" not in typo_words
            assert "smart" not in typo_words
    
    @pytest.mark.asyncio
    async def test_suggestion_quality(self):
        """Test quality of spelling suggestions"""
        result = await get_spelling_suggestions(word="typo")
        
        if result.get("success"):
            suggestions = result["data"]
            
            # Should return suggestions
            assert isinstance(suggestions, list)
            assert len(suggestions) > 0


class TestSpellToolsEdgeCases:
    """Test cases for spell tools edge cases"""
    
    @pytest.mark.asyncio
    async def test_empty_text(self):
        """Test checking empty text"""
        result = await check_spelling(text="")
        
        # Should handle empty text gracefully
        assert "success" in result
    
    @pytest.mark.asyncio
    async def test_special_characters(self):
        """Test checking text with special characters"""
        result = await check_spelling(text="Test @#$% special chars")
        
        # Should handle special characters
        assert "success" in result
    
    @pytest.mark.asyncio
    async def test_very_long_text(self):
        """Test checking very long text"""
        long_text = "word " * 10000
        
        result = await check_spelling(text=long_text)
        
        # Should handle long text
        assert "success" in result
    
    @pytest.mark.asyncio
    async def test_unicode_text(self):
        """Test checking unicode text"""
        result = await check_spelling(text="Test with unicode: 你好世界")
        
        # Should handle unicode
        assert "success" in result
    
    @pytest.mark.asyncio
    async def test_code_snippets(self):
        """Test checking code snippets"""
        code = """
def my_function():
    return "hello world"
        """
        
        result = await check_spelling(text=code)
        
        # Should handle code
        assert "success" in result
        
        # Should not flag code identifiers
        if result.get("success"):
            typos = result["data"]
            typo_words = [t.get("typo", "") for t in typos]
            assert "my_function" not in typo_words


class TestSpellToolsPerformance:
    """Test cases for spell tools performance"""
    
    @pytest.mark.asyncio
    async def test_large_file_check(self):
        """Test checking spelling in large file"""
        # Create large text
        large_text = "This is a test. " * 10000
        
        import time
        start = time.time()
        
        result = await check_spelling(text=large_text)
        
        duration = time.time() - start
        
        # Should complete in reasonable time
        assert duration < 10.0  # 10 seconds
        assert result["success"] == True
    
    @pytest.mark.asyncio
    async def test_batch_processing(self):
        """Test processing multiple texts"""
        texts = ["This is test " + str(i) for i in range(100)]
        
        results = []
        for text in texts:
            result = await check_spelling(text=text)
            results.append(result)
        
        # All should succeed
        assert all(r["success"] for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
