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
