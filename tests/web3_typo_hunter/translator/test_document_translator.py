# tests/web3_typo_hunter/translator/test_document_translator.py
import pytest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
import tempfile

from src.web3_typo_hunter.translator.document_translator import DocumentTranslator
from src.web3_typo_hunter.translator.translation_cache import TranslationCache


class TestDocumentTranslator:
    """文档翻译模块测试"""

    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM 客户端"""
        client = Mock()
        client.translate = AsyncMock(return_value="这是翻译后的文本")
        return client

    @pytest.fixture
    def translator(self, mock_llm_client):
        """翻译器实例"""
        return DocumentTranslator(llm_client=mock_llm_client)

    def test_extract_markdown_sections(self, translator):
        """测试提取 Markdown 章节"""
        content = """# Title

## Section 1
Content 1

## Section 2
Content 2
"""
        sections = translator._extract_sections(content)

        assert len(sections) == 3
        assert sections[0]["title"] == "# Title"
        assert sections[1]["title"] == "## Section 1"

    def test_preserve_code_blocks(self, translator):
        """测试保留代码块"""
        content = """# Example

```python
def hello():
    pass
```

Some text.
"""
        placeholders = {}
        processed = translator._extract_code_blocks(content, placeholders)

        assert "CODE_BLOCK_0" in processed
        assert len(placeholders) == 1
        assert "def hello()" in placeholders["CODE_BLOCK_0"]

    @pytest.mark.asyncio
    async def test_translate_document(self, translator, mock_llm_client):
        """测试翻译完整文档"""
        content = "# Hello\n\nThis is a test document for translation."

        result = await translator.translate(
            content=content,
            source_lang="en",
            target_lang="zh"
        )

        assert result["success"] is True
        assert "translated_content" in result
        mock_llm_client.translate.assert_called()

    @pytest.mark.asyncio
    async def test_translate_with_cache(self, translator, mock_llm_client):
        """测试使用缓存翻译"""
        content = "Hello World"

        # 第一次翻译
        await translator.translate(content, "en", "zh")

        # 第二次翻译应该使用缓存
        mock_llm_client.translate.reset_mock()
        result = await translator.translate(content, "en", "zh")

        assert result["success"] is True
        mock_llm_client.translate.assert_not_called()

    @pytest.mark.asyncio
    async def test_translate_empty_content(self, translator):
        """测试空内容处理"""
        result = await translator.translate("", "en", "zh")

        assert result["success"] is False
        assert "error" in result

    def test_detect_target_readme_filename(self, translator):
        """测试生成目标 README 文件名"""
        assert translator._get_target_filename("README.md", "zh") == "README.zh.md"
        assert translator._get_target_filename("readme.md", "zh") == "readme.zh.md"
        assert translator._get_target_filename("README.zh.md", "ja") == "README.ja.md"

    @pytest.mark.asyncio
    async def test_translate_large_document(self, translator, mock_llm_client):
        """测试大文档分块翻译"""
        # 模拟大文档（超过4000字符）
        content = "\n\n".join([f"## Section {i}\n\nContent {i} with some longer text to exceed chunk size." for i in range(200)])

        result = await translator.translate(content, "en", "zh")

        assert result["success"] is True
        assert result["chunks_translated"] >= 1  # 至少有一个块
