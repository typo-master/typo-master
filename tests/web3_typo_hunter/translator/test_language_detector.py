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
