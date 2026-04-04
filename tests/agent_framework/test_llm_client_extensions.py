# tests/agent_framework/test_llm_client_extensions.py
import pytest
from unittest.mock import Mock, patch, AsyncMock

from src.agent_framework.llm_client import OpenAICompatibleResponsesClient, LLMClientConfig


class TestLLMClientExtensions:
    """LLM 客户端扩展测试"""

    @pytest.fixture
    def client(self):
        """LLM 客户端实例"""
        config = LLMClientConfig(
            enabled=True,
            base_url="https://api.example.com",
            api_key="test_key",
            model="gpt-4"
        )
        return OpenAICompatibleResponsesClient(config)

    @pytest.mark.asyncio
    async def test_translate_text(self, client):
        """测试翻译文本"""
        with patch.object(client, 'generate_text') as mock_generate:
            mock_generate.return_value = {
                "success": True,
                "text": "你好世界"
            }

            result = await client.translate(
                text="Hello World",
                source_lang="en",
                target_lang="zh"
            )

            assert result == "你好世界"
            mock_generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_issue(self, client):
        """测试分析 Issue"""
        with patch.object(client, 'generate_text') as mock_generate:
            mock_generate.return_value = {
                "success": True,
                "text": '''{
                    "difficulty": "beginner",
                    "type": "bug",
                    "skills_required": ["python"],
                    "estimated_hours": 2,
                    "description_summary": "Fix typo"
                }'''
            }

            result = await client.analyze_issue(
                title="Fix typo in docs",
                body="There is a typo in README",
                labels=["documentation", "good first issue"]
            )

            assert result["difficulty"] == "beginner"
            assert result["type"] == "bug"
            mock_generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_strategy(self, client):
        """测试生成策略"""
        with patch.object(client, 'generate_text') as mock_generate:
            mock_generate.return_value = {
                "success": True,
                "text": '''{
                    "approach": "Start with docs",
                    "priority": "low",
                    "steps": ["Read CONTRIBUTING.md", "Find issues"]
                }'''
            }

            result = await client.generate_strategy(
                repo_name="owner/repo",
                repo_description="A web3 project",
                issues_summary=[{"number": 1, "title": "Fix docs"}]
            )

            assert "approach" in result
            assert "steps" in result
            mock_generate.assert_called_once()
