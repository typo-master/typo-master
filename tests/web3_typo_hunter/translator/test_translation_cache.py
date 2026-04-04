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
