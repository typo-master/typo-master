"""文档翻译模块 - 翻译 README 等文档"""

import re
import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from .translation_cache import TranslationCache
from .language_detector import LanguageDetector


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
            return {
                "success": False,
                "error": str(e)
            }
