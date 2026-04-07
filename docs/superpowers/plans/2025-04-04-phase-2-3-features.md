# Phase 2 & 3 功能扩展实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现文档翻译功能（第二阶段）和 Bug/Feature 自动发现功能（第三阶段），采用 TDD 模式开发，确保充足的单元测试覆盖。

**Architecture:** 
- **文档翻译模块**: 独立的 `translator/` 模块，支持 README 多语言翻译，集成 LLM 进行高质量翻译，保留原始格式
- **Bug/Feature 发现模块**: 独立的 `issue_finder/` 模块，分析 GitHub Issues 寻找可贡献机会，使用 LLM 评估难度和价值
- **Agent 集成**: 扩展现有 CoordinatorAgent 支持新工作流，保持与现有拼写检查流程的一致性

**Tech Stack:** Python 3.11, FastAPI, LangGraph, OpenAI API, pytest, pytest-asyncio, unittest.mock

---

## 文件结构

```
src/web3_typo_hunter/
├── translator/
│   ├── __init__.py
│   ├── document_translator.py    # 文档翻译核心
│   ├── language_detector.py      # 语言检测
│   └── translation_cache.py      # 翻译缓存
├── issue_finder/
│   ├── __init__.py
│   ├── issue_analyzer.py         # Issue 分析器
│   ├── issue_filter.py           # Issue 过滤器
│   └── contribution_evaluator.py # 贡献价值评估
└── ...existing modules

tests/web3_typo_hunter/
├── translator/
│   ├── test_document_translator.py
│   ├── test_language_detector.py
│   └── test_translation_cache.py
├── issue_finder/
│   ├── test_issue_analyzer.py
│   ├── test_issue_filter.py
│   └── test_contribution_evaluator.py
└── ...existing tests
```

---

## Task 1: 语言检测模块

**Files:**
- Create: `src/web3_typo_hunter/translator/language_detector.py`
- Create: `tests/web3_typo_hunter/translator/test_language_detector.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/web3_typo_hunter/translator/test_language_detector.py
import pytest
from src.web3_typo_hunter.translator.language_detector import LanguageDetector


class TestLanguageDetector:
    """语言检测模块测试"""
    
    def test_detect_english_text(self):
        """测试检测英文文本"""
        detector = LanguageDetector()
        text = "This is an English document for testing."
        result = detector.detect(text)
        assert result == "en"
    
    def test_detect_chinese_text(self):
        """测试检测中文文本"""
        detector = LanguageDetector()
        text = "这是一个中文文档用于测试。"
        result = detector.detect(text)
        assert result == "zh"
    
    def test_detect_with_confidence(self):
        """测试带置信度的语言检测"""
        detector = LanguageDetector()
        text = "Hello World"
        result = detector.detect_with_confidence(text)
        assert result["language"] == "en"
        assert result["confidence"] > 0.8
    
    def test_detect_empty_text(self):
        """测试空文本处理"""
        detector = LanguageDetector()
        result = detector.detect("")
        assert result is None
    
    def test_is_document_translated(self):
        """测试判断文档是否已有翻译"""
        detector = LanguageDetector()
        
        # 只有英文 README
        files_en_only = ["README.md", "CONTRIBUTING.md"]
        assert detector.has_translation(files_en_only, "zh") is False
        
        # 已有中文翻译
        files_with_cn = ["README.md", "README.zh.md", "CONTRIBUTING.md"]
        assert detector.has_translation(files_with_cn, "zh") is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/web3_typo_hunter/translator/test_language_detector.py -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'src.web3_typo_hunter.translator'"

- [ ] **Step 3: Write minimal implementation**

```python
# src/web3_typo_hunter/translator/language_detector.py
"""语言检测模块 - 检测文档语言和判断翻译状态"""

import re
from typing import Optional, Dict, Any


class LanguageDetector:
    """语言检测器"""
    
    # 简单字符特征检测
    CHINESE_CHAR_PATTERN = re.compile(r'[\u4e00-\u9fff]')
    JAPANESE_CHAR_PATTERN = re.compile(r'[\u3040-\u309f\u30a0-\u30ff]')
    KOREAN_CHAR_PATTERN = re.compile(r'[\uac00-\ud7af]')
    
    def detect(self, text: str) -> Optional[str]:
        """
        检测文本语言
        
        Args:
            text: 待检测文本
            
        Returns:
            语言代码 (en, zh, ja, ko) 或 None
        """
        if not text or not text.strip():
            return None
        
        text = text.strip()
        
        # 基于字符特征检测
        if self.CHINESE_CHAR_PATTERN.search(text):
            return "zh"
        if self.JAPANESE_CHAR_PATTERN.search(text):
            return "ja"
        if self.KOREAN_CHAR_PATTERN.search(text):
            return "ko"
        
        # 默认英文
        return "en"
    
    def detect_with_confidence(self, text: str) -> Dict[str, Any]:
        """
        带置信度的语言检测
        
        Args:
            text: 待检测文本
            
        Returns:
            包含 language 和 confidence 的字典
        """
        if not text or not text.strip():
            return {"language": None, "confidence": 0.0}
        
        language = self.detect(text)
        
        # 简单的置信度计算：基于字符比例
        confidence = 0.9
        if language == "en":
            # 检查是否包含非ASCII字符
            non_ascii = sum(1 for c in text if ord(c) > 127)
            if non_ascii > 0:
                confidence = min(0.95, 1.0 - (non_ascii / len(text)) * 0.2)
        
        return {
            "language": language,
            "confidence": confidence
        }
    
    def has_translation(self, readme_files: list, target_language: str) -> bool:
        """
        检查是否已有目标语言的翻译
        
        Args:
            readme_files: 仓库中的 README 文件列表
            target_language: 目标语言代码
            
        Returns:
            是否已有翻译
        """
        translation_patterns = [
            f"README.{target_language}.md",
            f"README-{target_language}.md",
            f"README_{target_language}.md",
        ]
        
        for filename in readme_files:
            for pattern in translation_patterns:
                if filename.lower().endswith(pattern.lower()):
                    return True
        
        return False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/web3_typo_hunter/translator/test_language_detector.py -v`

Expected: PASS (5 tests passed)

- [ ] **Step 5: Commit**

```bash
git add tests/web3_typo_hunter/translator/test_language_detector.py \
        src/web3_typo_hunter/translator/language_detector.py \
        src/web3_typo_hunter/translator/__init__.py
git commit -m "feat(translator): add language detection module with TDD

- Add LanguageDetector class for detecting document language
- Support en/zh/ja/ko language detection
- Add has_translation() to check existing translations
- Full test coverage with pytest"
```

---

## Task 2: 翻译缓存模块

**Files:**
- Create: `src/web3_typo_hunter/translator/translation_cache.py`
- Create: `tests/web3_typo_hunter/translator/test_translation_cache.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/web3_typo_hunter/translator/test_translation_cache.py
import pytest
import tempfile
import json
import os
from pathlib import Path
from src.web3_typo_hunter.translator.translation_cache import TranslationCache


class TestTranslationCache:
    """翻译缓存模块测试"""
    
    @pytest.fixture
    def temp_cache_dir(self):
        """临时缓存目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_cache_translation(self, temp_cache_dir):
        """测试缓存翻译结果"""
        cache = TranslationCache(temp_cache_dir)
        
        cache.set("hello", "en", "zh", "你好")
        result = cache.get("hello", "en", "zh")
        
        assert result == "你好"
    
    def test_cache_miss(self, temp_cache_dir):
        """测试缓存未命中"""
        cache = TranslationCache(temp_cache_dir)
        
        result = cache.get("nonexistent", "en", "zh")
        assert result is None
    
    def test_cache_persistence(self, temp_cache_dir):
        """测试缓存持久化"""
        cache1 = TranslationCache(temp_cache_dir)
        cache1.set("test", "en", "zh", "测试")
        
        # 新实例读取缓存
        cache2 = TranslationCache(temp_cache_dir)
        result = cache2.get("test", "en", "zh")
        
        assert result == "测试"
    
    def test_cache_invalidation(self, temp_cache_dir):
        """测试缓存失效"""
        cache = TranslationCache(temp_cache_dir)
        cache.set("old", "en", "zh", "旧")
        
        # 更新缓存
        cache.set("old", "en", "zh", "新")
        result = cache.get("old", "en", "zh")
        
        assert result == "新"
    
    def test_cache_clear(self, temp_cache_dir):
        """测试清空缓存"""
        cache = TranslationCache(temp_cache_dir)
        cache.set("key1", "en", "zh", "值1")
        cache.set("key2", "en", "zh", "值2")
        
        cache.clear()
        
        assert cache.get("key1", "en", "zh") is None
        assert cache.get("key2", "en", "zh") is None
    
    def test_generate_cache_key(self, temp_cache_dir):
        """测试缓存键生成"""
        cache = TranslationCache(temp_cache_dir)
        
        key1 = cache._generate_key("hello world", "en", "zh")
        key2 = cache._generate_key("hello world", "en", "zh")
        
        assert key1 == key2
        assert isinstance(key1, str)
        assert len(key1) == 64  # SHA-256 hash
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/web3_typo_hunter/translator/test_translation_cache.py -v`

Expected: FAIL with "ImportError: cannot import name 'TranslationCache'"

- [ ] **Step 3: Write minimal implementation**

```python
# src/web3_typo_hunter/translator/translation_cache.py
"""翻译缓存模块 - 缓存翻译结果避免重复调用 API"""

import json
import hashlib
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta


class TranslationCache:
    """翻译缓存管理器"""
    
    def __init__(self, cache_dir: str = ".translation_cache"):
        """
        初始化翻译缓存
        
        Args:
            cache_dir: 缓存目录路径
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "translations.json"
        self._cache = self._load_cache()
    
    def _load_cache(self) -> dict:
        """加载缓存文件"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}
    
    def _save_cache(self):
        """保存缓存到文件"""
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self._cache, f, ensure_ascii=False, indent=2)
    
    def _generate_key(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        生成缓存键
        
        Args:
            text: 原文
            source_lang: 源语言
            target_lang: 目标语言
            
        Returns:
            SHA-256 hash 作为缓存键
        """
        key_data = f"{text}:{source_lang}:{target_lang}"
        return hashlib.sha256(key_data.encode('utf-8')).hexdigest()
    
    def get(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        """
        获取缓存的翻译
        
        Args:
            text: 原文
            source_lang: 源语言
            target_lang: 目标语言
            
        Returns:
            缓存的翻译结果或 None
        """
        key = self._generate_key(text, source_lang, target_lang)
        entry = self._cache.get(key)
        
        if entry is None:
            return None
        
        # 检查缓存是否过期（30天）
        cached_time = datetime.fromisoformat(entry.get("timestamp", "2000-01-01"))
        if datetime.now() - cached_time > timedelta(days=30):
            del self._cache[key]
            self._save_cache()
            return None
        
        return entry.get("translation")
    
    def set(self, text: str, source_lang: str, target_lang: str, translation: str):
        """
        设置缓存
        
        Args:
            text: 原文
            source_lang: 源语言
            target_lang: 目标语言
            translation: 翻译结果
        """
        key = self._generate_key(text, source_lang, target_lang)
        self._cache[key] = {
            "translation": translation,
            "timestamp": datetime.now().isoformat(),
            "source_lang": source_lang,
            "target_lang": target_lang
        }
        self._save_cache()
    
    def clear(self):
        """清空所有缓存"""
        self._cache = {}
        if self.cache_file.exists():
            self.cache_file.unlink()
    
    def get_stats(self) -> dict:
        """获取缓存统计信息"""
        return {
            "total_entries": len(self._cache),
            "cache_file": str(self.cache_file),
            "cache_dir": str(self.cache_dir)
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/web3_typo_hunter/translator/test_translation_cache.py -v`

Expected: PASS (7 tests passed)

- [ ] **Step 5: Commit**

```bash
git add tests/web3_typo_hunter/translator/test_translation_cache.py \
        src/web3_typo_hunter/translator/translation_cache.py
git commit -m "feat(translator): add translation cache module

- Add TranslationCache for caching translation results
- Support persistent JSON cache with 30-day TTL
- Cache key based on SHA-256 hash
- Full test coverage including persistence tests"
```

---

## Task 3: 文档翻译核心模块

**Files:**
- Create: `src/web3_typo_hunter/translator/document_translator.py`
- Create: `tests/web3_typo_hunter/translator/test_document_translator.py`
- Modify: `src/agent_framework/llm_client.py` (添加翻译方法)

- [ ] **Step 1: Write the failing test**

```python
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
        assert sections[0]["title"] == "Title"
        assert sections[1]["title"] == "Section 1"
    
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
        content = "# Hello\n\nThis is a test document."
        
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
        # 模拟大文档
        content = "\n\n".join([f"## Section {i}\n\nContent {i}" for i in range(100)])
        
        result = await translator.translate(content, "en", "zh")
        
        assert result["success"] is True
        assert result["chunks_translated"] > 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/web3_typo_hunter/translator/test_document_translator.py -v`

Expected: FAIL with "ImportError: cannot import name 'DocumentTranslator'"

- [ ] **Step 3: Write minimal implementation**

```python
# src/web3_typo_hunter/translator/document_translator.py
"""文档翻译模块 - 翻译 README 等文档"""

import re
import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from .translation_cache import TranslationCache
from .language_detector import LanguageDetector
from ..utils.logger import logger


@dataclass
class TranslationResult:
    """翻译结果"""
    success: bool
    translated_content: str = ""
    source_lang: str = ""
    target_lang: str = ""
    chunks_translated: int = 0
    from_cache: bool = False
    error: Optional[str] = None


class DocumentTranslator:
    """文档翻译器"""
    
    # 代码块占位符
    CODE_BLOCK_PLACEHOLDER = "CODE_BLOCK_{idx}"
    
    def __init__(
        self,
        llm_client=None,
        cache: Optional[TranslationCache] = None,
        max_chunk_size: int = 4000
    ):
        """
        初始化文档翻译器
        
        Args:
            llm_client: LLM 客户端
            cache: 翻译缓存
            max_chunk_size: 最大分块大小
        """
        self.llm_client = llm_client
        self.cache = cache or TranslationCache()
        self.language_detector = LanguageDetector()
        self.max_chunk_size = max_chunk_size
    
    def _extract_code_blocks(
        self,
        content: str,
        placeholders: Dict[str, str]
    ) -> str:
        """
        提取代码块并用占位符替换
        
        Args:
            content: 原始内容
            placeholders: 占位符字典（会被修改）
            
        Returns:
            替换后的内容
        """
        code_block_pattern = r'```[\s\S]*?```'
        idx = 0
        
        def replace_block(match):
            nonlocal idx
            placeholder = self.CODE_BLOCK_PLACEHOLDER.format(idx=idx)
            placeholders[placeholder] = match.group(0)
            idx += 1
            return placeholder
        
        return re.sub(code_block_pattern, replace_block, content)
    
    def _restore_code_blocks(
        self,
        content: str,
        placeholders: Dict[str, str]
    ) -> str:
        """
        恢复代码块
        
        Args:
            content: 处理后的内容
            placeholders: 占位符字典
            
        Returns:
            恢复后的内容
        """
        for placeholder, code in placeholders.items():
            content = content.replace(placeholder, code)
        return content
    
    def _extract_sections(self, content: str) -> List[Dict[str, Any]]:
        """
        提取 Markdown 章节
        
        Args:
            content: Markdown 内容
            
        Returns:
            章节列表
        """
        sections = []
        
        # 按标题分割
        header_pattern = r'^(#{1,6}\s+.+)$'
        parts = re.split(header_pattern, content, flags=re.MULTILINE)
        
        current_section = {"title": "", "content": ""}
        for i, part in enumerate(parts):
            if re.match(header_pattern, part.strip()):
                if current_section["content"]:
                    sections.append(current_section)
                current_section = {
                    "title": part.strip(),
                    "content": ""
                }
            else:
                current_section["content"] += part
        
        if current_section["content"] or current_section["title"]:
            sections.append(current_section)
        
        return sections
    
    def _split_into_chunks(self, content: str) -> List[str]:
        """
        将内容分割成可翻译的块
        
        Args:
            content: 原始内容
            
        Returns:
            内容块列表
        """
        sections = self._extract_sections(content)
        chunks = []
        current_chunk = ""
        
        for section in sections:
            section_text = f"{section['title']}\n{section['content']}"
            
            if len(current_chunk) + len(section_text) < self.max_chunk_size:
                current_chunk += section_text + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = section_text + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks if chunks else [content]
    
    async def _translate_chunk(
        self,
        chunk: str,
        source_lang: str,
        target_lang: str
    ) -> str:
        """
        翻译单个块
        
        Args:
            chunk: 文本块
            source_lang: 源语言
            target_lang: 目标语言
            
        Returns:
            翻译后的文本
        """
        # 检查缓存
        cached = self.cache.get(chunk, source_lang, target_lang)
        if cached:
            return cached
        
        if not self.llm_client:
            raise ValueError("LLM client is required for translation")
        
        # 调用 LLM 翻译
        translation = await self.llm_client.translate(
            text=chunk,
            source_lang=source_lang,
            target_lang=target_lang
        )
        
        # 保存缓存
        self.cache.set(chunk, source_lang, target_lang, translation)
        
        return translation
    
    async def translate(
        self,
        content: str,
        source_lang: str,
        target_lang: str = "zh"
    ) -> Dict[str, Any]:
        """
        翻译文档
        
        Args:
            content: 文档内容
            source_lang: 源语言
            target_lang: 目标语言
            
        Returns:
            翻译结果字典
        """
        if not content or not content.strip():
            return {
                "success": False,
                "error": "Content is empty",
                "translated_content": ""
            }
        
        try:
            # 提取代码块
            code_placeholders = {}
            content_without_code = self._extract_code_blocks(
                content,
                code_placeholders
            )
            
            # 分块翻译
            chunks = self._split_into_chunks(content_without_code)
            translated_chunks = []
            
            for chunk in chunks:
                translated = await self._translate_chunk(
                    chunk,
                    source_lang,
                    target_lang
                )
                translated_chunks.append(translated)
            
            # 合并翻译结果
            translated_content = "\n\n".join(translated_chunks)
            
            # 恢复代码块
            final_content = self._restore_code_blocks(
                translated_content,
                code_placeholders
            )
            
            return {
                "success": True,
                "translated_content": final_content,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "chunks_translated": len(chunks)
            }
        
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "translated_content": ""
            }
    
    def _get_target_filename(self, original_filename: str, target_lang: str) -> str:
        """
        生成目标文件名
        
        Args:
            original_filename: 原始文件名
            target_lang: 目标语言
            
        Returns:
            目标文件名
        """
        # 移除已有的语言后缀
        base = re.sub(r'\.[a-z]{2}(\.md)?$', '', original_filename, flags=re.IGNORECASE)
        if not base.endswith('.md'):
            base += '.md'
        
        # 插入语言后缀
        name = base[:-3]  # 移除 .md
        return f"{name}.{target_lang}.md"
    
    async def translate_repo_readme(
        self,
        repo_full_name: str,
        github_api,
        target_lang: str = "zh"
    ) -> Dict[str, Any]:
        """
        翻译仓库 README
        
        Args:
            repo_full_name: 仓库全名 (owner/repo)
            github_api: GitHub API 实例
            target_lang: 目标语言
            
        Returns:
            翻译结果
        """
        try:
            # 获取 README 内容
            readme_content = await github_api.get_readme(repo_full_name)
            if not readme_content:
                return {
                    "success": False,
                    "error": "README not found"
                }
            
            # 检测源语言
            source_lang = self.language_detector.detect(readme_content)
            if source_lang == target_lang:
                return {
                    "success": False,
                    "error": f"Source language is already {target_lang}"
                }
            
            # 翻译
            result = await self.translate(
                readme_content,
                source_lang,
                target_lang
            )
            
            if result["success"]:
                result["target_filename"] = self._get_target_filename(
                    "README.md",
                    target_lang
                )
            
            return result
        
        except Exception as e:
            logger.error(f"Failed to translate repo {repo_full_name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/web3_typo_hunter/translator/test_document_translator.py -v`

Expected: PASS (8 tests passed)

- [ ] **Step 5: Commit**

```bash
git add tests/web3_typo_hunter/translator/test_document_translator.py \
        src/web3_typo_hunter/translator/document_translator.py
git commit -m "feat(translator): add document translation core module

- Add DocumentTranslator with section extraction
- Preserve code blocks during translation
- Support chunked translation for large documents
- Integrate with TranslationCache for performance
- Add translate_repo_readme() for GitHub repos"
```

---

## Task 4: Issue 分析器模块

**Files:**
- Create: `src/web3_typo_hunter/issue_finder/issue_analyzer.py`
- Create: `tests/web3_typo_hunter/issue_finder/test_issue_analyzer.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/web3_typo_hunter/issue_finder/test_issue_analyzer.py
import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from src.web3_typo_hunter.issue_finder.issue_analyzer import IssueAnalyzer, IssueInfo


class TestIssueAnalyzer:
    """Issue 分析器测试"""
    
    @pytest.fixture
    def mock_github_api(self):
        """Mock GitHub API"""
        api = Mock()
        return api
    
    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM 客户端"""
        client = Mock()
        client.analyze_issue = AsyncMock(return_value={
            "difficulty": "beginner",
            "type": "bug",
            "skills_required": ["python"],
            "estimated_hours": 2,
            "description_summary": "Fix typo in docs"
        })
        return client
    
    @pytest.fixture
    def analyzer(self, mock_github_api, mock_llm_client):
        """分析器实例"""
        return IssueAnalyzer(
            github_api=mock_github_api,
            llm_client=mock_llm_client
        )
    
    def test_parse_issue_data(self, analyzer):
        """测试解析 Issue 数据"""
        raw_issue = {
            "number": 123,
            "title": "Bug in login",
            "body": "Users cannot login",
            "state": "open",
            "created_at": "2024-01-01T00:00:00Z",
            "labels": [{"name": "bug"}, {"name": "good first issue"}],
            "user": {"login": "reporter"},
            "comments": 5
        }
        
        issue = analyzer._parse_issue(raw_issue)
        
        assert issue.number == 123
        assert issue.title == "Bug in login"
        assert issue.issue_type == "bug"
        assert "good first issue" in issue.labels
    
    def test_classify_issue_type(self, analyzer):
        """测试 Issue 类型分类"""
        assert analyzer._classify_type(["bug", "critical"]) == "bug"
        assert analyzer._classify_type(["enhancement", "feature"]) == "feature"
        assert analyzer._classify_type(["documentation"]) == "documentation"
        assert analyzer._classify_type([]) == "other"
    
    @pytest.mark.asyncio
    async def test_analyze_single_issue(self, analyzer, mock_llm_client):
        """测试分析单个 Issue"""
        issue = IssueInfo(
            number=123,
            title="Bug in login",
            body="Users cannot login",
            state="open",
            created_at=datetime.now(),
            labels=["bug"],
            author="reporter",
            comments_count=5
        )
        
        result = await analyzer.analyze_issue(issue)
        
        assert result["issue_number"] == 123
        assert "analysis" in result
        assert result["analysis"]["difficulty"] == "beginner"
        mock_llm_client.analyze_issue.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fetch_and_analyze_issues(self, analyzer, mock_github_api):
        """测试获取并分析 Issues"""
        mock_github_api.get_issues = AsyncMock(return_value=[
            {
                "number": 1,
                "title": "Bug 1",
                "body": "Description 1",
                "state": "open",
                "created_at": "2024-01-01T00:00:00Z",
                "labels": [{"name": "bug"}],
                "user": {"login": "user1"},
                "comments": 2
            },
            {
                "number": 2,
                "title": "Feature 1",
                "body": "Description 2",
                "state": "open",
                "created_at": "2024-01-02T00:00:00Z",
                "labels": [{"name": "enhancement"}],
                "user": {"login": "user2"},
                "comments": 0
            }
        ])
        
        results = await analyzer.fetch_and_analyze_issues(
            repo_full_name="owner/repo",
            state="open",
            limit=10
        )
        
        assert len(results) == 2
        assert results[0]["issue_number"] == 1
        assert results[1]["issue_number"] == 2
    
    def test_calculate_issue_score(self, analyzer):
        """测试 Issue 评分"""
        issue = IssueInfo(
            number=1,
            title="Good first issue",
            body="Easy to fix",
            state="open",
            created_at=datetime.now(),
            labels=["good first issue", "bug"],
            author="user",
            comments_count=2
        )
        
        analysis = {
            "difficulty": "beginner",
            "estimated_hours": 1
        }
        
        score = analyzer._calculate_score(issue, analysis)
        
        assert score > 0
        # good first issue 标签应该增加分数
        assert score >= 50
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/web3_typo_hunter/issue_finder/test_issue_analyzer.py -v`

Expected: FAIL with "ImportError: cannot import name 'IssueAnalyzer'"

- [ ] **Step 3: Write minimal implementation**

```python
# src/web3_typo_hunter/issue_finder/issue_analyzer.py
"""Issue 分析器 - 分析 GitHub Issues 寻找可贡献机会"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from ..utils.logger import logger


class IssueType(Enum):
    """Issue 类型"""
    BUG = "bug"
    FEATURE = "feature"
    DOCUMENTATION = "documentation"
    OTHER = "other"


class DifficultyLevel(Enum):
    """难度等级"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


@dataclass
class IssueInfo:
    """Issue 信息"""
    number: int
    title: str
    body: str
    state: str
    created_at: datetime
    labels: List[str]
    author: str
    comments_count: int
    issue_type: str = "other"
    
    def __post_init__(self):
        if not self.issue_type or self.issue_type == "other":
            self.issue_type = self._detect_type()
    
    def _detect_type(self) -> str:
        """根据标签检测类型"""
        label_lower = [l.lower() for l in self.labels]
        
        if any(l in label_lower for l in ["bug", "fix", "error", "crash"]):
            return "bug"
        elif any(l in label_lower for l in ["feature", "enhancement", "request"]):
            return "feature"
        elif any(l in label_lower for l in ["documentation", "docs", "readme"]):
            return "documentation"
        
        return "other"


@dataclass
class IssueAnalysis:
    """Issue 分析结果"""
    issue_number: int
    difficulty: str
    issue_type: str
    skills_required: List[str]
    estimated_hours: int
    description_summary: str
    contribution_value: int  # 1-100
    recommended_for_beginner: bool


class IssueAnalyzer:
    """Issue 分析器"""
    
    def __init__(self, github_api=None, llm_client=None):
        """
        初始化 Issue 分析器
        
        Args:
            github_api: GitHub API 实例
            llm_client: LLM 客户端
        """
        self.github_api = github_api
        self.llm_client = llm_client
    
    def _parse_issue(self, raw_issue: Dict[str, Any]) -> IssueInfo:
        """
        解析原始 Issue 数据
        
        Args:
            raw_issue: GitHub API 返回的 Issue 数据
            
        Returns:
            IssueInfo 对象
        """
        labels = [label["name"] for label in raw_issue.get("labels", [])]
        
        created_at_str = raw_issue.get("created_at", "")
        try:
            created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
        except:
            created_at = datetime.now()
        
        return IssueInfo(
            number=raw_issue.get("number", 0),
            title=raw_issue.get("title", ""),
            body=raw_issue.get("body", ""),
            state=raw_issue.get("state", "open"),
            created_at=created_at,
            labels=labels,
            author=raw_issue.get("user", {}).get("login", ""),
            comments_count=raw_issue.get("comments", 0)
        )
    
    def _classify_type(self, labels: List[str]) -> str:
        """
        根据标签分类 Issue 类型
        
        Args:
            labels: 标签列表
            
        Returns:
            类型字符串
        """
        label_lower = [l.lower() for l in labels]
        
        if any(l in label_lower for l in ["bug", "fix", "error", "crash", "defect"]):
            return "bug"
        elif any(l in label_lower for l in ["feature", "enhancement", "request", "proposal"]):
            return "feature"
        elif any(l in label_lower for l in ["documentation", "docs", "readme", "wiki"]):
            return "documentation"
        elif any(l in label_lower for l in ["good first issue", "beginner friendly", "easy"]):
            return "good_first_issue"
        
        return "other"
    
    async def analyze_issue(self, issue: IssueInfo) -> Dict[str, Any]:
        """
        分析单个 Issue
        
        Args:
            issue: Issue 信息
            
        Returns:
            分析结果字典
        """
        if not self.llm_client:
            # 没有 LLM 时使用基本分析
            return self._basic_analysis(issue)
        
        try:
            # 使用 LLM 分析
            analysis = await self.llm_client.analyze_issue(
                title=issue.title,
                body=issue.body,
                labels=issue.labels
            )
            
            score = self._calculate_score(issue, analysis)
            
            return {
                "issue_number": issue.number,
                "title": issue.title,
                "issue_type": issue.issue_type,
                "analysis": analysis,
                "score": score,
                "recommended": score >= 60,
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Failed to analyze issue #{issue.number}: {e}")
            return {
                "issue_number": issue.number,
                "title": issue.title,
                "error": str(e),
                "recommended": False
            }
    
    def _basic_analysis(self, issue: IssueInfo) -> Dict[str, Any]:
        """
        基本分析（无 LLM）
        
        Args:
            issue: Issue 信息
            
        Returns:
            分析结果
        """
        labels_lower = [l.lower() for l in issue.labels]
        
        # 基于标签的分析
        difficulty = "intermediate"
        if any(l in labels_lower for l in ["good first issue", "beginner"]):
            difficulty = "beginner"
        elif any(l in labels_lower for l in ["hard", "complex", "advanced"]):
            difficulty = "advanced"
        
        estimated_hours = 4
        if difficulty == "beginner":
            estimated_hours = 2
        elif difficulty == "advanced":
            estimated_hours = 16
        
        analysis = {
            "difficulty": difficulty,
            "type": issue.issue_type,
            "skills_required": [],
            "estimated_hours": estimated_hours,
            "description_summary": issue.body[:200] if issue.body else ""
        }
        
        score = self._calculate_score(issue, analysis)
        
        return {
            "issue_number": issue.number,
            "title": issue.title,
            "issue_type": issue.issue_type,
            "analysis": analysis,
            "score": score,
            "recommended": score >= 60,
            "timestamp": datetime.now().isoformat()
        }
    
    def _calculate_score(self, issue: IssueInfo, analysis: Dict[str, Any]) -> int:
        """
        计算 Issue 的贡献价值分数
        
        Args:
            issue: Issue 信息
            analysis: 分析结果
            
        Returns:
            0-100 的分数
        """
        score = 50  # 基础分
        
        # 难度加分（beginner friendly 更适合贡献）
        difficulty = analysis.get("difficulty", "intermediate")
        if difficulty == "beginner":
            score += 20
        elif difficulty == "advanced":
            score -= 10
        
        # 标签加分
        labels_lower = [l.lower() for l in issue.labels]
        if any(l in labels_lower for l in ["good first issue", "help wanted", "beginner friendly"]):
            score += 15
        if any(l in labels_lower for l in ["bug", "critical", "urgent"]):
            score += 10
        
        # 讨论活跃度（有讨论但不太多的更适合参与）
        if 1 <= issue.comments_count <= 10:
            score += 5
        
        # 预估时间（短时间可完成的更好）
        hours = analysis.get("estimated_hours", 4)
        if hours <= 2:
            score += 10
        elif hours > 16:
            score -= 10
        
        return max(0, min(100, score))
    
    async def fetch_and_analyze_issues(
        self,
        repo_full_name: str,
        state: str = "open",
        labels: Optional[List[str]] = None,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """
        获取并分析仓库 Issues
        
        Args:
            repo_full_name: 仓库全名
            state: Issue 状态
            labels: 标签过滤
            limit: 数量限制
            
        Returns:
            分析结果列表
        """
        if not self.github_api:
            raise ValueError("GitHub API is required")
        
        try:
            # 获取 Issues
            raw_issues = await self.github_api.get_issues(
                repo_full_name,
                state=state,
                labels=labels,
                limit=limit
            )
            
            results = []
            for raw_issue in raw_issues:
                issue = self._parse_issue(raw_issue)
                analysis = await self.analyze_issue(issue)
                results.append(analysis)
            
            # 按分数排序
            results.sort(key=lambda x: x.get("score", 0), reverse=True)
            
            return results
        
        except Exception as e:
            logger.error(f"Failed to fetch issues for {repo_full_name}: {e}")
            return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/web3_typo_hunter/issue_finder/test_issue_analyzer.py -v`

Expected: PASS (6 tests passed)

- [ ] **Step 5: Commit**

```bash
git add tests/web3_typo_hunter/issue_finder/test_issue_analyzer.py \
        src/web3_typo_hunter/issue_finder/issue_analyzer.py \
        src/web3_typo_hunter/issue_finder/__init__.py
git commit -m "feat(issue-finder): add issue analyzer module

- Add IssueAnalyzer for analyzing GitHub Issues
- Parse and classify issues by type and difficulty
- Score issues based on contribution value
- Support LLM-based and basic analysis modes
- Full test coverage"
```

---

## Task 5: Issue 过滤器模块

**Files:**
- Create: `src/web3_typo_hunter/issue_finder/issue_filter.py`
- Create: `tests/web3_typo_hunter/issue_finder/test_issue_filter.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/web3_typo_hunter/issue_finder/test_issue_filter.py
import pytest
from datetime import datetime, timedelta

from src.web3_typo_hunter.issue_finder.issue_filter import IssueFilter, FilterCriteria


class TestIssueFilter:
    """Issue 过滤器测试"""
    
    @pytest.fixture
    def sample_issues(self):
        """示例 Issues"""
        return [
            {
                "issue_number": 1,
                "title": "Fix typo",
                "issue_type": "documentation",
                "analysis": {
                    "difficulty": "beginner",
                    "estimated_hours": 1
                },
                "score": 85,
                "recommended": True
            },
            {
                "issue_number": 2,
                "title": "Add feature X",
                "issue_type": "feature",
                "analysis": {
                    "difficulty": "advanced",
                    "estimated_hours": 20
                },
                "score": 40,
                "recommended": False
            },
            {
                "issue_number": 3,
                "title": "Bug in login",
                "issue_type": "bug",
                "analysis": {
                    "difficulty": "intermediate",
                    "estimated_hours": 4
                },
                "score": 75,
                "recommended": True
            }
        ]
    
    def test_filter_by_difficulty(self, sample_issues):
        """测试按难度过滤"""
        criteria = FilterCriteria(difficulty="beginner")
        filter_obj = IssueFilter(criteria)
        
        results = filter_obj.filter(sample_issues)
        
        assert len(results) == 1
        assert results[0]["issue_number"] == 1
    
    def test_filter_by_type(self, sample_issues):
        """测试按类型过滤"""
        criteria = FilterCriteria(issue_types=["bug"])
        filter_obj = IssueFilter(criteria)
        
        results = filter_obj.filter(sample_issues)
        
        assert len(results) == 1
        assert results[0]["issue_number"] == 3
    
    def test_filter_by_score(self, sample_issues):
        """测试按分数过滤"""
        criteria = FilterCriteria(min_score=70)
        filter_obj = IssueFilter(criteria)
        
        results = filter_obj.filter(sample_issues)
        
        assert len(results) == 2
        assert all(r["score"] >= 70 for r in results)
    
    def test_filter_by_max_hours(self, sample_issues):
        """测试按预估时间过滤"""
        criteria = FilterCriteria(max_estimated_hours=5)
        filter_obj = IssueFilter(criteria)
        
        results = filter_obj.filter(sample_issues)
        
        assert len(results) == 2
        assert all(r["analysis"]["estimated_hours"] <= 5 for r in results)
    
    def test_filter_by_recommended_only(self, sample_issues):
        """测试只显示推荐的"""
        criteria = FilterCriteria(recommended_only=True)
        filter_obj = IssueFilter(criteria)
        
        results = filter_obj.filter(sample_issues)
        
        assert len(results) == 2
        assert all(r["recommended"] for r in results)
    
    def test_combined_filters(self, sample_issues):
        """测试组合过滤条件"""
        criteria = FilterCriteria(
            difficulty="beginner",
            min_score=80,
            recommended_only=True
        )
        filter_obj = IssueFilter(criteria)
        
        results = filter_obj.filter(sample_issues)
        
        assert len(results) == 1
        assert results[0]["issue_number"] == 1
    
    def test_empty_criteria(self, sample_issues):
        """测试空过滤条件"""
        criteria = FilterCriteria()
        filter_obj = IssueFilter(criteria)
        
        results = filter_obj.filter(sample_issues)
        
        assert len(results) == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/web3_typo_hunter/issue_finder/test_issue_filter.py -v`

Expected: FAIL with "ImportError: cannot import name 'IssueFilter'"

- [ ] **Step 3: Write minimal implementation**

```python
# src/web3_typo_hunter/issue_finder/issue_filter.py
"""Issue 过滤器 - 根据条件筛选 Issues"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class IssueTypeFilter(Enum):
    """Issue 类型过滤"""
    BUG = "bug"
    FEATURE = "feature"
    DOCUMENTATION = "documentation"
    GOOD_FIRST_ISSUE = "good_first_issue"
    OTHER = "other"


class DifficultyFilter(Enum):
    """难度过滤"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    ANY = "any"


@dataclass
class FilterCriteria:
    """过滤条件"""
    issue_types: Optional[List[str]] = None
    difficulty: Optional[str] = None
    min_score: Optional[int] = None
    max_score: Optional[int] = None
    max_estimated_hours: Optional[int] = None
    recommended_only: bool = False
    exclude_assigned: bool = True
    has_labels: List[str] = field(default_factory=list)
    exclude_labels: List[str] = field(default_factory=list)


class IssueFilter:
    """Issue 过滤器"""
    
    def __init__(self, criteria: Optional[FilterCriteria] = None):
        """
        初始化过滤器
        
        Args:
            criteria: 过滤条件
        """
        self.criteria = criteria or FilterCriteria()
    
    def filter(self, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        过滤 Issues
        
        Args:
            issues: Issue 列表
            
        Returns:
            过滤后的 Issue 列表
        """
        results = issues
        
        # 按类型过滤
        if self.criteria.issue_types:
            results = [
                i for i in results
                if i.get("issue_type", "other") in self.criteria.issue_types
            ]
        
        # 按难度过滤
        if self.criteria.difficulty:
            results = [
                i for i in results
                if self._matches_difficulty(i, self.criteria.difficulty)
            ]
        
        # 按分数过滤
        if self.criteria.min_score is not None:
            results = [
                i for i in results
                if i.get("score", 0) >= self.criteria.min_score
            ]
        
        if self.criteria.max_score is not None:
            results = [
                i for i in results
                if i.get("score", 0) <= self.criteria.max_score
            ]
        
        # 按预估时间过滤
        if self.criteria.max_estimated_hours is not None:
            results = [
                i for i in results
                if self._get_estimated_hours(i) <= self.criteria.max_estimated_hours
            ]
        
        # 只显示推荐的
        if self.criteria.recommended_only:
            results = [
                i for i in results
                if i.get("recommended", False)
            ]
        
        # 按标签过滤
        if self.criteria.has_labels:
            results = [
                i for i in results
                if self._has_any_label(i, self.criteria.has_labels)
            ]
        
        # 排除标签
        if self.criteria.exclude_labels:
            results = [
                i for i in results
                if not self._has_any_label(i, self.criteria.exclude_labels)
            ]
        
        return results
    
    def _matches_difficulty(self, issue: Dict[str, Any], difficulty: str) -> bool:
        """
        检查 Issue 是否匹配难度
        
        Args:
            issue: Issue 字典
            difficulty: 目标难度
            
        Returns:
            是否匹配
        """
        if difficulty == "any":
            return True
        
        analysis = issue.get("analysis", {})
        issue_difficulty = analysis.get("difficulty", "intermediate")
        
        return issue_difficulty == difficulty
    
    def _get_estimated_hours(self, issue: Dict[str, Any]) -> int:
        """
        获取预估时间
        
        Args:
            issue: Issue 字典
            
        Returns:
            预估小时数
        """
        analysis = issue.get("analysis", {})
        return analysis.get("estimated_hours", 4)
    
    def _has_any_label(self, issue: Dict[str, Any], labels: List[str]) -> bool:
        """
        检查 Issue 是否有任一标签
        
        Args:
            issue: Issue 字典
            labels: 标签列表
            
        Returns:
            是否有匹配标签
        """
        # 这里假设 issue 中有 labels 字段
        # 实际实现中可能需要根据具体情况调整
        issue_labels = issue.get("labels", [])
        labels_lower = [l.lower() for l in labels]
        issue_labels_lower = [l.lower() for l in issue_labels]
        
        return any(l in issue_labels_lower for l in labels_lower)
    
    def sort_by_score(
        self,
        issues: List[Dict[str, Any]],
        descending: bool = True
    ) -> List[Dict[str, Any]]:
        """
        按分数排序
        
        Args:
            issues: Issue 列表
            descending: 是否降序
            
        Returns:
            排序后的列表
        """
        return sorted(
            issues,
            key=lambda x: x.get("score", 0),
            reverse=descending
        )
    
    def get_stats(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        获取 Issue 统计信息
        
        Args:
            issues: Issue 列表
            
        Returns:
            统计信息字典
        """
        if not issues:
            return {
                "total": 0,
                "avg_score": 0,
                "recommended_count": 0
            }
        
        scores = [i.get("score", 0) for i in issues]
        recommended = sum(1 for i in issues if i.get("recommended", False))
        
        # 按类型统计
        by_type = {}
        for issue in issues:
            issue_type = issue.get("issue_type", "other")
            by_type[issue_type] = by_type.get(issue_type, 0) + 1
        
        return {
            "total": len(issues),
            "avg_score": sum(scores) / len(scores),
            "max_score": max(scores),
            "min_score": min(scores),
            "recommended_count": recommended,
            "by_type": by_type
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/web3_typo_hunter/issue_finder/test_issue_filter.py -v`

Expected: PASS (7 tests passed)

- [ ] **Step 5: Commit**

```bash
git add tests/web3_typo_hunter/issue_finder/test_issue_filter.py \
        src/web3_typo_hunter/issue_finder/issue_filter.py
git commit -m "feat(issue-finder): add issue filter module

- Add IssueFilter with flexible FilterCriteria
- Support filtering by difficulty, type, score, estimated hours
- Add sort_by_score() and get_stats() utilities
- Full test coverage for all filter combinations"
```

---

## Task 6: 贡献价值评估器

**Files:**
- Create: `src/web3_typo_hunter/issue_finder/contribution_evaluator.py`
- Create: `tests/web3_typo_hunter/issue_finder/test_contribution_evaluator.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/web3_typo_hunter/issue_finder/test_contribution_evaluator.py
import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from src.web3_typo_hunter.issue_finder.contribution_evaluator import ContributionEvaluator


class TestContributionEvaluator:
    """贡献价值评估器测试"""
    
    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM 客户端"""
        client = Mock()
        return client
    
    @pytest.fixture
    def evaluator(self, mock_llm_client):
        """评估器实例"""
        return ContributionEvaluator(llm_client=mock_llm_client)
    
    def test_evaluate_repo_metrics(self, evaluator):
        """测试评估仓库指标"""
        repo_data = {
            "stargazers_count": 1500,
            "forks_count": 200,
            "open_issues_count": 50,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }
        
        metrics = evaluator._evaluate_repo_metrics(repo_data)
        
        assert "star_score" in metrics
        assert "activity_score" in metrics
        assert "overall" in metrics
        assert metrics["overall"] > 0
    
    def test_calculate_airdrop_potential(self, evaluator):
        """测试计算空投潜力"""
        repo_data = {
            "topics": ["web3", "ethereum", "defi"],
            "stargazers_count": 2000,
            "forks_count": 500
        }
        
        potential = evaluator._calculate_airdrop_potential(repo_data)
        
        assert 0 <= potential <= 100
        # Web3 项目应该有更高的空投潜力
        assert potential >= 30
    
    def test_evaluate_issue_contribution_value(self, evaluator):
        """测试评估 Issue 贡献价值"""
        issue = {
            "issue_number": 1,
            "title": "Fix critical bug",
            "issue_type": "bug",
            "score": 80,
            "analysis": {
                "difficulty": "intermediate",
                "skills_required": ["python", "blockchain"]
            }
        }
        
        value = evaluator._evaluate_issue_value(issue)
        
        assert "total_value" in value
        assert "learning_value" in value
        assert "visibility_value" in value
        assert value["total_value"] > 0
    
    @pytest.mark.asyncio
    async def test_generate_contribution_strategy(self, evaluator, mock_llm_client):
        """测试生成贡献策略"""
        mock_llm_client.generate_strategy = AsyncMock(return_value={
            "approach": "Start with documentation issues",
            "priority": "low",
            "steps": ["Find good first issues", "Comment to claim"]
        })
        
        repo_data = {"full_name": "owner/repo", "topics": ["web3"]}
        issues = [{"issue_number": 1, "title": "Fix docs"}]
        
        strategy = await evaluator.generate_strategy(repo_data, issues)
        
        assert "approach" in strategy
        assert "priority" in strategy
        mock_llm_client.generate_strategy.assert_called_once()
    
    def test_rank_contribution_opportunities(self, evaluator):
        """测试排序贡献机会"""
        opportunities = [
            {
                "issue_number": 1,
                "total_value": {"total_value": 75},
                "airdrop_potential": 60
            },
            {
                "issue_number": 2,
                "total_value": {"total_value": 85},
                "airdrop_potential": 80
            },
            {
                "issue_number": 3,
                "total_value": {"total_value": 60},
                "airdrop_potential": 40
            }
        ]
        
        ranked = evaluator.rank_opportunities(opportunities)
        
        assert len(ranked) == 3
        # 应该按综合价值排序
        assert ranked[0]["issue_number"] == 2  # 最高价值
        assert ranked[2]["issue_number"] == 3  # 最低价值
    
    def test_evaluate_empty_repo(self, evaluator):
        """测试评估空仓库数据"""
        metrics = evaluator._evaluate_repo_metrics({})
        
        assert "overall" in metrics
        assert metrics["overall"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/web3_typo_hunter/issue_finder/test_contribution_evaluator.py -v`

Expected: FAIL with "ImportError: cannot import name 'ContributionEvaluator'"

- [ ] **Step 3: Write minimal implementation**

```python
# src/web3_typo_hunter/issue_finder/contribution_evaluator.py
"""贡献价值评估器 - 评估贡献的价值和空投潜力"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from ..utils.logger import logger


@dataclass
class ContributionValue:
    """贡献价值"""
    total_value: int  # 0-100
    learning_value: int  # 学习价值
    visibility_value: int  # 曝光价值
    skill_match_value: int  # 技能匹配价值
    airdrop_potential: int  # 空投潜力


@dataclass
class RepoMetrics:
    """仓库指标"""
    star_score: int
    fork_score: int
    activity_score: int
    web3_relevance: int
    overall: int


class ContributionEvaluator:
    """贡献价值评估器"""
    
    # Web3 相关主题
    WEB3_TOPICS = [
        "web3", "ethereum", "blockchain", "defi", "nft",
        "crypto", "solidity", "smart-contracts", "dao",
        "token", "airdrop", "wallet", "metamask"
    ]
    
    def __init__(self, llm_client=None):
        """
        初始化评估器
        
        Args:
            llm_client: LLM 客户端
        """
        self.llm_client = llm_client
    
    def _evaluate_repo_metrics(self, repo_data: Dict[str, Any]) -> Dict[str, int]:
        """
        评估仓库指标
        
        Args:
            repo_data: 仓库数据
            
        Returns:
            指标评分
        """
        if not repo_data:
            return {"overall": 0}
        
        stars = repo_data.get("stargazers_count", 0)
        forks = repo_data.get("forks_count", 0)
        open_issues = repo_data.get("open_issues_count", 0)
        
        # Star 分数 (0-25)
        if stars >= 10000:
            star_score = 25
        elif stars >= 1000:
            star_score = 20
        elif stars >= 500:
            star_score = 15
        elif stars >= 100:
            star_score = 10
        else:
            star_score = 5
        
        # Fork 分数 (0-15)
        if forks >= 1000:
            fork_score = 15
        elif forks >= 500:
            fork_score = 12
        elif forks >= 100:
            fork_score = 8
        else:
            fork_score = 4
        
        # 活跃度分数 (0-20)
        updated_at = repo_data.get("updated_at", "")
        try:
            last_update = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            days_since_update = (datetime.now() - last_update).days
            
            if days_since_update <= 7:
                activity_score = 20
            elif days_since_update <= 30:
                activity_score = 15
            elif days_since_update <= 90:
                activity_score = 10
            else:
                activity_score = 5
        except:
            activity_score = 5
        
        # Web3 相关度 (0-20)
        topics = repo_data.get("topics", [])
        web3_match = sum(1 for t in topics if t.lower() in self.WEB3_TOPICS)
        web3_relevance = min(20, web3_match * 5)
        
        # 社区活跃度 (0-20) - 基于 open issues
        if open_issues >= 50:
            community_score = 20
        elif open_issues >= 20:
            community_score = 15
        elif open_issues >= 5:
            community_score = 10
        else:
            community_score = 5
        
        overall = star_score + fork_score + activity_score + web3_relevance + community_score
        
        return {
            "star_score": star_score,
            "fork_score": fork_score,
            "activity_score": activity_score,
            "web3_relevance": web3_relevance,
            "community_score": community_score,
            "overall": overall
        }
    
    def _calculate_airdrop_potential(self, repo_data: Dict[str, Any]) -> int:
        """
        计算空投潜力
        
        Args:
            repo_data: 仓库数据
            
        Returns:
            0-100 的空投潜力分数
        """
        if not repo_data:
            return 0
        
        score = 0
        
        # Web3 相关度
        topics = repo_data.get("topics", [])
        web3_match = sum(1 for t in topics if t.lower() in self.WEB3_TOPICS)
        score += min(40, web3_match * 10)
        
        # 项目规模 (stars)
        stars = repo_data.get("stargazers_count", 0)
        if stars >= 5000:
            score += 25
        elif stars >= 1000:
            score += 20
        elif stars >= 500:
            score += 15
        elif stars >= 100:
            score += 10
        
        # 活跃度
        updated_at = repo_data.get("updated_at", "")
        try:
            last_update = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            days_since_update = (datetime.now() - last_update).days
            
            if days_since_update <= 30:
                score += 20
            elif days_since_update <= 90:
                score += 15
            elif days_since_update <= 180:
                score += 10
        except:
            pass
        
        # Fork 数（社区参与度）
        forks = repo_data.get("forks_count", 0)
        if forks >= 500:
            score += 15
        elif forks >= 100:
            score += 10
        elif forks >= 50:
            score += 5
        
        return min(100, score)
    
    def _evaluate_issue_value(self, issue: Dict[str, Any]) -> Dict[str, int]:
        """
        评估单个 Issue 的贡献价值
        
        Args:
            issue: Issue 数据
            
        Returns:
            价值评估结果
        """
        analysis = issue.get("analysis", {})
        difficulty = analysis.get("difficulty", "intermediate")
        score = issue.get("score", 50)
        issue_type = issue.get("issue_type", "other")
        
        # 学习价值 (0-30)
        difficulty_learning = {
            "beginner": 15,
            "intermediate": 25,
            "advanced": 30,
            "expert": 20  # 专家级难度太高，可能不适合学习
        }
        learning_value = difficulty_learning.get(difficulty, 20)
        
        # 曝光价值 (0-30) - 基于 Issue 关注度和类型
        if issue_type == "bug":
            type_value = 25
        elif issue_type == "feature":
            type_value = 20
        elif issue_type == "documentation":
            type_value = 15
        else:
            type_value = 10
        
        comments_count = issue.get("comments_count", 0)
        visibility_value = min(30, type_value + comments_count * 2)
        
        # 技能匹配价值 (0-20) - 基于技能要求的热门程度
        skills = analysis.get("skills_required", [])
        skill_match_value = min(20, len(skills) * 5)
        
        # 综合价值
        total_value = (score * 0.4 + 
                      learning_value * 0.3 + 
                      visibility_value * 0.2 + 
                      skill_match_value * 0.1)
        
        return {
            "total_value": int(total_value),
            "learning_value": learning_value,
            "visibility_value": visibility_value,
            "skill_match_value": skill_match_value,
            "base_score": score
        }
    
    async def generate_strategy(
        self,
        repo_data: Dict[str, Any],
        issues: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        生成贡献策略
        
        Args:
            repo_data: 仓库数据
            issues: Issue 列表
            
        Returns:
            策略建议
        """
        if not self.llm_client:
            # 返回基本策略
            return self._generate_basic_strategy(repo_data, issues)
        
        try:
            strategy = await self.llm_client.generate_strategy(
                repo_name=repo_data.get("full_name", ""),
                repo_description=repo_data.get("description", ""),
                issues_summary=[{
                    "number": i.get("issue_number"),
                    "title": i.get("title"),
                    "type": i.get("issue_type"),
                    "difficulty": i.get("analysis", {}).get("difficulty")
                } for i in issues[:5]]
            )
            
            return strategy
        
        except Exception as e:
            logger.error(f"Failed to generate strategy: {e}")
            return self._generate_basic_strategy(repo_data, issues)
    
    def _generate_basic_strategy(
        self,
        repo_data: Dict[str, Any],
        issues: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        生成基本贡献策略
        
        Args:
            repo_data: 仓库数据
            issues: Issue 列表
            
        Returns:
            策略建议
        """
        # 统计 Issue 类型
        type_counts = {}
        for issue in issues:
            issue_type = issue.get("issue_type", "other")
            type_counts[issue_type] = type_counts.get(issue_type, 0) + 1
        
        # 推荐优先级
        if type_counts.get("documentation", 0) > 0:
            recommended_start = "documentation"
            approach = "Start with documentation improvements to understand the project"
        elif type_counts.get("good_first_issue", 0) > 0:
            recommended_start = "good_first_issue"
            approach = "Look for issues labeled 'good first issue' to get started"
        else:
            recommended_start = "beginner-friendly bugs"
            approach = "Start with small bug fixes to build familiarity"
        
        return {
            "approach": approach,
            "recommended_start": recommended_start,
            "priority": "medium",
            "steps": [
                "Read the project's CONTRIBUTING.md",
                f"Find and comment on {recommended_start} issues",
                "Wait for assignment or approval",
                "Submit a draft PR early for feedback"
            ]
        }
    
    def rank_opportunities(
        self,
        opportunities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        排序贡献机会
        
        Args:
            opportunities: 机会列表
            
        Returns:
            排序后的列表
        """
        def get_composite_score(opp: Dict[str, Any]) -> float:
            issue_value = opp.get("total_value", {}).get("total_value", 0)
            airdrop_potential = opp.get("airdrop_potential", 0)
            
            # 综合评分：60% 贡献价值 + 40% 空投潜力
            return issue_value * 0.6 + airdrop_potential * 0.4
        
        return sorted(
            opportunities,
            key=get_composite_score,
            reverse=True
        )
    
    def evaluate_contribution_opportunity(
        self,
        repo_data: Dict[str, Any],
        issue: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        评估单个贡献机会
        
        Args:
            repo_data: 仓库数据
            issue: Issue 数据
            
        Returns:
            完整评估结果
        """
        repo_metrics = self._evaluate_repo_metrics(repo_data)
        airdrop_potential = self._calculate_airdrop_potential(repo_data)
        issue_value = self._evaluate_issue_value(issue)
        
        # 综合评分
        composite_score = (
            repo_metrics["overall"] * 0.3 +
            issue_value["total_value"] * 0.5 +
            airdrop_potential * 0.2
        )
        
        return {
            "repo_name": repo_data.get("full_name", ""),
            "issue_number": issue.get("issue_number"),
            "issue_title": issue.get("title"),
            "repo_metrics": repo_metrics,
            "issue_value": issue_value,
            "airdrop_potential": airdrop_potential,
            "composite_score": int(composite_score),
            "recommendation": "highly_recommended" if composite_score >= 70 else "recommended" if composite_score >= 50 else "optional"
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/web3_typo_hunter/issue_finder/test_contribution_evaluator.py -v`

Expected: PASS (6 tests passed)

- [ ] **Step 5: Commit**

```bash
git add tests/web3_typo_hunter/issue_finder/test_contribution_evaluator.py \
        src/web3_typo_hunter/issue_finder/contribution_evaluator.py
git commit -m "feat(issue-finder): add contribution evaluator module

- Add ContributionEvaluator for assessing contribution value
- Calculate airdrop potential based on Web3 relevance
- Evaluate repo metrics (stars, forks, activity)
- Generate contribution strategies with LLM support
- Rank opportunities by composite score"
```

---

## Task 7: 集成到 CoordinatorAgent

**Files:**
- Modify: `src/agents/coordinator_agent.py`
- Create: `tests/agents/test_coordinator_agent_integration.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/agents/test_coordinator_agent_integration.py
import pytest
from unittest.mock import Mock, AsyncMock, patch

from src.agents.coordinator_agent import CoordinatorAgent


class TestCoordinatorAgentIntegration:
    """CoordinatorAgent 集成测试"""
    
    @pytest.fixture
    def agent(self):
        """CoordinatorAgent 实例"""
        return CoordinatorAgent(github_token="test_token")
    
    @pytest.mark.asyncio
    async def test_translate_document_workflow(self, agent):
        """测试文档翻译工作流"""
        with patch.object(agent, '_get_translator') as mock_get_translator:
            mock_translator = Mock()
            mock_translator.translate_repo_readme = AsyncMock(return_value={
                "success": True,
                "translated_content": "# 标题\n\n这是翻译后的内容",
                "target_filename": "README.zh.md"
            })
            mock_get_translator.return_value = mock_translator
            
            result = await agent.process_task({
                "type": "translate_document",
                "repo": "owner/repo",
                "target_lang": "zh"
            })
            
            assert result["success"] is True
            assert "translated_content" in result
    
    @pytest.mark.asyncio
    async def test_find_issues_workflow(self, agent):
        """测试查找 Issues 工作流"""
        with patch.object(agent, '_get_issue_analyzer') as mock_get_analyzer:
            mock_analyzer = Mock()
            mock_analyzer.fetch_and_analyze_issues = AsyncMock(return_value=[
                {
                    "issue_number": 1,
                    "title": "Bug fix",
                    "score": 80,
                    "recommended": True
                }
            ])
            mock_get_analyzer.return_value = mock_analyzer
            
            result = await agent.process_task({
                "type": "find_issues",
                "repo": "owner/repo",
                "limit": 10
            })
            
            assert result["success"] is True
            assert len(result["issues"]) == 1
    
    @pytest.mark.asyncio
    async def test_batch_find_contributions_workflow(self, agent):
        """测试批量查找贡献机会工作流"""
        with patch.object(agent, '_get_issue_analyzer') as mock_get_analyzer, \
             patch.object(agent, '_get_contribution_evaluator') as mock_get_evaluator:
            
            mock_analyzer = Mock()
            mock_analyzer.fetch_and_analyze_issues = AsyncMock(return_value=[
                {"issue_number": 1, "score": 80}
            ])
            mock_get_analyzer.return_value = mock_analyzer
            
            mock_evaluator = Mock()
            mock_evaluator.evaluate_contribution_opportunity = Mock(return_value={
                "composite_score": 75,
                "recommendation": "recommended"
            })
            mock_get_evaluator.return_value = mock_evaluator
            
            result = await agent.process_task({
                "type": "batch_find_contributions",
                "repos": ["owner/repo1", "owner/repo2"],
                "limit": 5
            })
            
            assert result["success"] is True
            assert "opportunities" in result
    
    def test_get_capabilities_includes_new_features(self, agent):
        """测试能力列表包含新功能"""
        capabilities = agent.get_capabilities()
        
        assert "document_translation" in capabilities.get("features", {})
        assert "issue_discovery" in capabilities.get("features", {})
        assert "contribution_evaluation" in capabilities.get("features", {})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/agents/test_coordinator_agent_integration.py -v`

Expected: FAIL - 测试中的新方法和功能尚未实现

- [ ] **Step 3: Write minimal implementation**

在 `src/agents/coordinator_agent.py` 中添加新方法：

```python
# 在 __init__ 方法中添加新的 agent 引用
self.translator: Optional[Any] = None
self.issue_analyzer: Optional[Any] = None
self.contribution_evaluator: Optional[Any] = None

# 在 on_initialize 方法中初始化新的 agents
from ..web3_typo_hunter.translator.document_translator import DocumentTranslator
from ..web3_typo_hunter.issue_finder.issue_analyzer import IssueAnalyzer
from ..web3_typo_hunter.issue_finder.contribution_evaluator import ContributionEvaluator

self.translator = DocumentTranslator(llm_client=self.llm_client)
self.issue_analyzer = IssueAnalyzer(
    github_api=self.discovery_agent.github_api if self.discovery_agent else None,
    llm_client=self.llm_client
)
self.contribution_evaluator = ContributionEvaluator(llm_client=self.llm_client)

# 修改 process_task 方法，添加新的任务类型
async def process_task(self, task: Any) -> Any:
    """
    Process workflow tasks.
    """
    task_type = task.get("type")
    if task_type == "run_workflow":
        return await self._run_workflow(task)
    if task_type == "process_project":
        return await self._process_project(task)
    if task_type == "get_status":
        return await self.get_status()
    if task_type == "get_capabilities":
        return await self.get_capabilities()
    # 新增任务类型
    if task_type == "translate_document":
        return await self._translate_document_task(task)
    if task_type == "find_issues":
        return await self._find_issues_task(task)
    if task_type == "batch_find_contributions":
        return await self._batch_find_contributions_task(task)
    logger.warning(f"Unknown task type: {task_type}")
    return {"success": False, "error": f"Unknown task type: {task_type}"}

# 添加新的任务处理方法
async def _translate_document_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
    """处理文档翻译任务"""
    repo = task.get("repo")
    target_lang = task.get("target_lang", "zh")
    
    if not repo:
        return {"success": False, "error": "repo is required"}
    
    if not self.translator:
        return {"success": False, "error": "Translator not initialized"}
    
    try:
        from ..web3_typo_hunter.utils.github_api import GitHubAPI
        github_api = GitHubAPI(self.github_token)
        
        result = await self.translator.translate_repo_readme(
            repo_full_name=repo,
            github_api=github_api,
            target_lang=target_lang
        )
        
        return result
    except Exception as exc:
        logger.error(f"Error translating document: {exc}")
        return {"success": False, "error": str(exc)}

async def _find_issues_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
    """处理查找 Issues 任务"""
    repo = task.get("repo")
    limit = task.get("limit", 30)
    
    if not repo:
        return {"success": False, "error": "repo is required"}
    
    if not self.issue_analyzer:
        return {"success": False, "error": "Issue analyzer not initialized"}
    
    try:
        issues = await self.issue_analyzer.fetch_and_analyze_issues(
            repo_full_name=repo,
            limit=limit
        )
        
        return {
            "success": True,
            "repo": repo,
            "issues": issues,
            "count": len(issues)
        }
    except Exception as exc:
        logger.error(f"Error finding issues: {exc}")
        return {"success": False, "error": str(exc)}

async def _batch_find_contributions_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
    """处理批量查找贡献机会任务"""
    repos = task.get("repos", [])
    limit = task.get("limit", 10)
    
    if not repos:
        return {"success": False, "error": "repos list is required"}
    
    opportunities = []
    
    for repo in repos:
        try:
            # 获取仓库信息
            from ..web3_typo_hunter.utils.github_api import GitHubAPI
            github_api = GitHubAPI(self.github_token)
            repo_data = await github_api.get_repo(repo)
            
            # 获取并分析 Issues
            issues = await self.issue_analyzer.fetch_and_analyze_issues(
                repo_full_name=repo,
                limit=limit
            )
            
            # 评估每个 Issue
            for issue in issues:
                if issue.get("recommended"):
                    opportunity = self.contribution_evaluator.evaluate_contribution_opportunity(
                        repo_data=repo_data,
                        issue=issue
                    )
                    opportunities.append(opportunity)
        
        except Exception as exc:
            logger.error(f"Error processing repo {repo}: {exc}")
            continue
    
    # 排序机会
    ranked_opportunities = self.contribution_evaluator.rank_opportunities(opportunities)
    
    return {
        "success": True,
        "opportunities": ranked_opportunities[:20],  # 返回前20个
        "total": len(ranked_opportunities)
    }

# 修改 get_capabilities 方法，添加新功能
async def get_capabilities(self) -> Dict[str, Any]:
    """
    Return coordinator capabilities and readiness signals.
    """
    llm_enabled = False
    llm_model = None
    if self.decision_agent and getattr(self.decision_agent, "llm_client", None):
        llm_enabled = bool(getattr(self.decision_agent, "llm_enabled", False))
        llm_model = self.decision_agent.llm_client.config.model if llm_enabled else None

    return {
        "success": True,
        "framework": "LangGraph",
        "workflows": {
            "single_project": True,
            "batch_projects": True,
            "document_translation": self.translator is not None,
            "issue_discovery": self.issue_analyzer is not None,
            "contribution_evaluation": self.contribution_evaluator is not None,
        },
        "pipeline_nodes": [
            "scan_project",
            "evaluate_quality",
            "fix_typos",
            "decide_pr",
            "create_pull_request",
            "generate_report",
        ],
        "features": {
            "project_discovery": True,
            "typo_scan": True,
            "quality_evaluation": True,
            "typo_fix": True,
            "pr_decision": True,
            "pr_creation": True,
            "report_generation": True,
            "llm_decision_support": llm_enabled,
            "document_translation": self.translator is not None,
            "issue_discovery": self.issue_analyzer is not None,
            "contribution_evaluation": self.contribution_evaluator is not None,
        },
        "llm": {
            "enabled": llm_enabled,
            "model": llm_model,
        },
        "limitations": [
            "Pycorrector backend may return empty results if kenlm/model assets are missing",
            "GitHub API rate limits apply when scanning/discovery at scale",
        ],
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/agents/test_coordinator_agent_integration.py -v`

Expected: PASS (4 tests passed)

- [ ] **Step 5: Commit**

```bash
git add tests/agents/test_coordinator_agent_integration.py \
        src/agents/coordinator_agent.py
git commit -m "feat(agent): integrate translator and issue finder into CoordinatorAgent

- Add document translation workflow support
- Add issue discovery workflow support
- Add batch contribution opportunity finder
- Update capabilities to include new features
- Full integration tests"
```

---

## Task 8: LLM 客户端扩展

**Files:**
- Modify: `src/agent_framework/llm_client.py`
- Create: `tests/agent_framework/test_llm_client_extensions.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/agent_framework/test_llm_client_extensions.py
import pytest
from unittest.mock import Mock, patch, AsyncMock

from src.agent_framework.llm_client import OpenAICompatibleResponsesClient


class TestLLMClientExtensions:
    """LLM 客户端扩展测试"""
    
    @pytest.fixture
    def client(self):
        """LLM 客户端实例"""
        return OpenAICompatibleResponsesClient(
            base_url="https://api.example.com",
            api_key="test_key",
            model="gpt-4"
        )
    
    @pytest.mark.asyncio
    async def test_translate_text(self, client):
        """测试翻译文本"""
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "choices": [{"message": {"content": "你好世界"}}]
            }
            
            result = await client.translate(
                text="Hello World",
                source_lang="en",
                target_lang="zh"
            )
            
            assert result == "你好世界"
            mock_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_issue(self, client):
        """测试分析 Issue"""
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "choices": [{"message": {"content": '''{
                    "difficulty": "beginner",
                    "type": "bug",
                    "skills_required": ["python"],
                    "estimated_hours": 2,
                    "description_summary": "Fix typo"
                }'''}}]
            }
            
            result = await client.analyze_issue(
                title="Fix typo in docs",
                body="There is a typo in README",
                labels=["documentation", "good first issue"]
            )
            
            assert result["difficulty"] == "beginner"
            assert result["type"] == "bug"
    
    @pytest.mark.asyncio
    async def test_generate_strategy(self, client):
        """测试生成策略"""
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "choices": [{"message": {"content": '''{
                    "approach": "Start with docs",
                    "priority": "low",
                    "steps": ["Read CONTRIBUTING.md", "Find issues"]
                }'''}}]
            }
            
            result = await client.generate_strategy(
                repo_name="owner/repo",
                repo_description="A web3 project",
                issues_summary=[{"number": 1, "title": "Fix docs"}]
            )
            
            assert "approach" in result
            assert "steps" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/agent_framework/test_llm_client_extensions.py -v`

Expected: FAIL - 新方法尚未实现

- [ ] **Step 3: Write minimal implementation**

```python
# 添加到 src/agent_framework/llm_client.py

async def translate(
    self,
    text: str,
    source_lang: str,
    target_lang: str
) -> str:
    """
    翻译文本
    
    Args:
        text: 待翻译文本
        source_lang: 源语言代码
        target_lang: 目标语言代码
        
    Returns:
        翻译后的文本
    """
    prompt = f"""Translate the following text from {source_lang} to {target_lang}.
    Preserve markdown formatting and code blocks.
    Do not translate code, only translate natural language text.
    
    Text to translate:
    {text}
    
    Translation:"""
    
    response = await self._make_request(
        messages=[
            {"role": "system", "content": "You are a professional translator."},
            {"role": "user", "content": prompt}
        ]
    )
    
    content = response["choices"][0]["message"]["content"]
    return content.strip()

async def analyze_issue(
    self,
    title: str,
    body: str,
    labels: list
) -> dict:
    """
    分析 GitHub Issue
    
    Args:
        title: Issue 标题
        body: Issue 内容
        labels: 标签列表
        
    Returns:
        分析结果字典
    """
    prompt = f"""Analyze the following GitHub Issue and provide a structured assessment:
    
    Title: {title}
    Body: {body}
    Labels: {', '.join(labels)}
    
    Provide a JSON response with:
    - difficulty: one of [beginner, intermediate, advanced, expert]
    - type: one of [bug, feature, documentation, other]
    - skills_required: list of required skills
    - estimated_hours: estimated hours to complete (number)
    - description_summary: brief summary of the issue
    
    JSON:"""
    
    response = await self._make_request(
        messages=[
            {"role": "system", "content": "You are a code contribution assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    
    content = response["choices"][0]["message"]["content"]
    
    # 解析 JSON 响应
    import json
    try:
        # 尝试直接解析
        result = json.loads(content)
    except json.JSONDecodeError:
        # 尝试从代码块中提取
        import re
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', content)
        if json_match:
            result = json.loads(json_match.group(1))
        else:
            # 返回默认结果
            result = {
                "difficulty": "intermediate",
                "type": "other",
                "skills_required": [],
                "estimated_hours": 4,
                "description_summary": title
            }
    
    return result

async def generate_strategy(
    self,
    repo_name: str,
    repo_description: str,
    issues_summary: list
) -> dict:
    """
    生成贡献策略
    
    Args:
        repo_name: 仓库名称
        repo_description: 仓库描述
        issues_summary: Issue 摘要列表
        
    Returns:
        策略建议字典
    """
    prompt = f"""Generate a contribution strategy for a new contributor:
    
    Repository: {repo_name}
    Description: {repo_description}
    
    Available Issues:
    {chr(10).join(f"- #{i['number']}: {i['title']} ({i.get('type', 'unknown')}, {i.get('difficulty', 'unknown')})" for i in issues_summary[:5])}
    
    Provide a JSON response with:
    - approach: overall approach description
    - priority: one of [low, medium, high]
    - steps: list of actionable steps
    
    JSON:"""
    
    response = await self._make_request(
        messages=[
            {"role": "system", "content": "You are an open source contribution advisor."},
            {"role": "user", "content": prompt}
        ]
    )
    
    content = response["choices"][0]["message"]["content"]
    
    # 解析 JSON
    import json
    import re
    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', content)
        if json_match:
            result = json.loads(json_match.group(1))
        else:
            result = {
                "approach": "Start with documentation issues to understand the project",
                "priority": "medium",
                "steps": ["Read CONTRIBUTING.md", "Find good first issues", "Comment to claim"]
            }
    
    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/agent_framework/test_llm_client_extensions.py -v`

Expected: PASS (3 tests passed)

- [ ] **Step 5: Commit**

```bash
git add tests/agent_framework/test_llm_client_extensions.py \
        src/agent_framework/llm_client.py
git commit -m "feat(llm): add translate, analyze_issue, generate_strategy methods

- Add translate() for document translation
- Add analyze_issue() for issue analysis
- Add generate_strategy() for contribution guidance
- Support JSON response parsing with fallback
- Full test coverage for new methods"
```

---

## Task 9: CLI 命令扩展

**Files:**
- Modify: `src/scripts/web3_typo_hunter_cli.py`
- Create: `tests/scripts/test_cli_extensions.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/scripts/test_cli_extensions.py
import pytest
from unittest.mock import Mock, patch, AsyncMock
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/scripts/test_cli_extensions.py -v`

Expected: FAIL - 新的子命令尚未添加

- [ ] **Step 3: Write minimal implementation**

```python
# 添加到 src/scripts/web3_typo_hunter_cli.py

# 在 parse_args() 函数中添加新的子命令

# 'translate' 子命令
translate_parser = subparsers.add_parser(
    "translate",
    help="翻译仓库 README 文档"
)
translate_parser.add_argument("--token", type=str, required=True, help="GitHub API令牌")
translate_parser.add_argument("--repo", type=str, required=True, help="仓库完整名称 (owner/repo)")
translate_parser.add_argument("--target-lang", type=str, default="zh", help="目标语言代码 (默认: zh)")

# 'find-issues' 子命令
find_issues_parser = subparsers.add_parser(
    "find-issues",
    help="查找仓库中的可贡献 Issues"
)
find_issues_parser.add_argument("--token", type=str, required=True, help="GitHub API令牌")
find_issues_parser.add_argument("--repo", type=str, required=True, help="仓库完整名称 (owner/repo)")
find_issues_parser.add_argument("--limit", type=int, default=30, help="最大 Issue 数量 (默认: 30)")

# 'find-contributions' 子命令
find_contributions_parser = subparsers.add_parser(
    "find-contributions",
    help="批量查找多个仓库的贡献机会"
)
find_contributions_parser.add_argument("--token", type=str, required=True, help="GitHub API令牌")
find_contributions_parser.add_argument(
    "--repos",
    nargs="+",
    required=True,
    help="仓库列表 (空格分隔，如: owner/repo1 owner/repo2)"
)
find_contributions_parser.add_argument("--limit", type=int, default=10, help="每个仓库最大 Issue 数量 (默认: 10)")

# 添加对应的处理函数

async def run_translate_command(args):
    """执行 translate 命令"""
    logger.info("=== 翻译文档 ===")
    logger.info(f"仓库: {args.repo}, 目标语言: {args.target_lang}")
    
    coordinator = CoordinatorAgent(github_token=args.token)
    await coordinator.initialize()
    await coordinator.start()
    
    try:
        result = await coordinator.process_task({
            "type": "translate_document",
            "repo": args.repo,
            "target_lang": args.target_lang
        })
        
        if result.get("success"):
            logger.info(f"✅ 翻译成功!")
            logger.info(f"目标文件: {result.get('target_filename')}")
            # 保存翻译内容到文件
            output_file = f"{args.repo.replace('/', '_')}_README.{args.target_lang}.md"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(result.get("translated_content", ""))
            logger.info(f"翻译内容已保存到: {output_file}")
        else:
            logger.error(f"❌ 翻译失败: {result.get('error')}")
    
    finally:
        await coordinator.stop()

async def run_find_issues_command(args):
    """执行 find-issues 命令"""
    logger.info("=== 查找 Issues ===")
    logger.info(f"仓库: {args.repo}, 限制: {args.limit}")
    
    coordinator = CoordinatorAgent(github_token=args.token)
    await coordinator.initialize()
    await coordinator.start()
    
    try:
        result = await coordinator.process_task({
            "type": "find_issues",
            "repo": args.repo,
            "limit": args.limit
        })
        
        if result.get("success"):
            issues = result.get("issues", [])
            logger.info(f"✅ 找到 {len(issues)} 个 Issues")
            
            # 输出推荐的 Issues
            recommended = [i for i in issues if i.get("recommended")]
            if recommended:
                logger.info(f"\n⭐ 推荐 Issues ({len(recommended)} 个):")
                for issue in recommended[:10]:
                    analysis = issue.get("analysis", {})
                    logger.info(f"  #{issue['issue_number']}: {issue['title']}")
                    logger.info(f"     难度: {analysis.get('difficulty', 'unknown')}, 分数: {issue.get('score', 0)}")
        else:
            logger.error(f"❌ 查找失败: {result.get('error')}")
    
    finally:
        await coordinator.stop()

async def run_find_contributions_command(args):
    """执行 find-contributions 命令"""
    logger.info("=== 批量查找贡献机会 ===")
    logger.info(f"仓库列表: {', '.join(args.repos)}")
    
    coordinator = CoordinatorAgent(github_token=args.token)
    await coordinator.initialize()
    await coordinator.start()
    
    try:
        result = await coordinator.process_task({
            "type": "batch_find_contributions",
            "repos": args.repos,
            "limit": args.limit
        })
        
        if result.get("success"):
            opportunities = result.get("opportunities", [])
            logger.info(f"✅ 找到 {len(opportunities)} 个贡献机会")
            
            # 输出前10个机会
            for i, opp in enumerate(opportunities[:10], 1):
                logger.info(f"\n{i}. {opp['repo_name']} - Issue #{opp['issue_number']}")
                logger.info(f"   标题: {opp['issue_title']}")
                logger.info(f"   综合评分: {opp['composite_score']}")
                logger.info(f"   空投潜力: {opp['airdrop_potential']}")
                logger.info(f"   推荐度: {opp['recommendation']}")
        else:
            logger.error(f"❌ 查找失败: {result.get('error')}")
    
    finally:
        await coordinator.stop()

# 在 main() 函数中添加新命令的处理
async def main():
    args = parse_args()
    
    if args.command == "find":
        await run_find_command(args)
    elif args.command == "scan":
        await run_scan_command(args)
    elif args.command == "process":
        await run_process_command(args)
    elif args.command == "llm-check":
        await run_llm_check_command()
    elif args.command == "capabilities":
        await run_capabilities_command(args)
    # 新命令
    elif args.command == "translate":
        await run_translate_command(args)
    elif args.command == "find-issues":
        await run_find_issues_command(args)
    elif args.command == "find-contributions":
        await run_find_contributions_command(args)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/scripts/test_cli_extensions.py -v`

Expected: PASS (4 tests passed)

- [ ] **Step 5: Commit**

```bash
git add tests/scripts/test_cli_extensions.py \
        src/scripts/web3_typo_hunter_cli.py
git commit -m "feat(cli): add translate, find-issues, find-contributions commands

- Add translate command for document translation
- Add find-issues command for issue discovery
- Add find-contributions command for batch opportunity finding
- Implement corresponding run functions
- Full test coverage for CLI arguments"
```

---

## 执行切换（两步决策）

### Step 1: 分析任务特性

- **任务数量**: 9 个主要任务
- **复杂度因素**:
  - 多个独立模块需要集成
  - 需要与现有代码库协作
  - 涉及 LLM 客户端扩展
  - 需要 CLI 集成
- **风险等级**: 中等（涉及多个模块修改）
- **上下文污染风险**: 高（多个文件修改）

---

## 总结

本实施计划包含 **9 个任务**，采用 TDD 模式开发：

### 文档翻译功能（第二阶段）
1. **Task 1**: 语言检测模块
2. **Task 2**: 翻译缓存模块  
3. **Task 3**: 文档翻译核心模块

### Bug/Feature 自动发现（第三阶段）
4. **Task 4**: Issue 分析器模块
5. **Task 5**: Issue 过滤器模块
6. **Task 6**: 贡献价值评估器

### 集成与扩展
7. **Task 7**: 集成到 CoordinatorAgent
8. **Task 8**: LLM 客户端扩展
9. **Task 9**: CLI 命令扩展

### 测试覆盖
- 每个模块都有完整的单元测试
- 集成测试验证模块协作
- CLI 测试验证参数解析

### 文件统计
- 新建文件: 18 个
- 修改文件: 3 个
- 测试文件: 9 个

计划已保存至: `docs/superpowers/plans/2025-04-04-phase-2-3-features.md`
