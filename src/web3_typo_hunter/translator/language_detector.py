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
