"""
LLM Client - OpenAI-compatible Responses API client

This module provides a minimal client used by agents to call OpenAI-compatible
Responses APIs (including self-hosted compatible gateways).

Priority: Environment Variables > Config File > Defaults
"""

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests

from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class LLMClientConfig:
    """LLM client configuration"""
    enabled: bool = False
    base_url: str = "https://api.openai.com"
    api_key: Optional[str] = None
    model: str = "gpt-5.4"
    timeout: float = 30.0
    max_output_tokens: int = 300


class OpenAICompatibleResponsesClient:
    """
    Small OpenAI-compatible client for the /v1/responses endpoint.
    """

    def __init__(self, config: LLMClientConfig):
        self.config = config

    @classmethod
    def from_env(cls) -> "OpenAICompatibleResponsesClient":
        """Build client configuration from environment variables (legacy)."""
        return cls.from_config({})

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "OpenAICompatibleResponsesClient":
        """
        Build client configuration with priority:
        1. Environment variables (highest priority)
        2. Config file values
        3. Default values (lowest priority)
        """
        # Start with config file values or defaults
        llm_config = config.get("llm", {})

        enabled = llm_config.get("enabled", False)
        base_url = llm_config.get("base_url", "https://api.openai.com")
        api_key = llm_config.get("api_key")
        model = llm_config.get("model", "gpt-5.4")
        timeout = float(llm_config.get("timeout", 30))
        max_output_tokens = int(llm_config.get("max_output_tokens", 300))

        # Environment variables override config file
        if "OPENAI_API_KEY" in os.environ:
            api_key = os.environ["OPENAI_API_KEY"]
            logger.debug("Using OPENAI_API_KEY from environment variable")

        if "OPENAI_BASE_URL" in os.environ:
            base_url = os.environ["OPENAI_BASE_URL"]
            logger.debug("Using OPENAI_BASE_URL from environment variable")

        if "OPENAI_MODEL" in os.environ:
            model = os.environ["OPENAI_MODEL"]
            logger.debug("Using OPENAI_MODEL from environment variable")

        if "OPENAI_TIMEOUT" in os.environ:
            try:
                timeout = float(os.environ["OPENAI_TIMEOUT"])
            except ValueError:
                logger.warning("Invalid OPENAI_TIMEOUT, using config/default value")

        if "OPENAI_MAX_OUTPUT_TOKENS" in os.environ:
            try:
                max_output_tokens = int(os.environ["OPENAI_MAX_OUTPUT_TOKENS"])
            except ValueError:
                logger.warning("Invalid OPENAI_MAX_OUTPUT_TOKENS, using config/default value")

        # LLM_ENABLED can force enable/disable
        if "LLM_ENABLED" in os.environ:
            enabled = os.environ["LLM_ENABLED"].strip().lower() in {"1", "true", "yes", "on"}
            logger.debug("Using LLM_ENABLED from environment variable")
        elif api_key:
            # If API key is present (from config or env), enable LLM
            enabled = True

        return cls(
            LLMClientConfig(
                enabled=enabled,
                base_url=base_url,
                api_key=api_key,
                model=model,
                timeout=timeout,
                max_output_tokens=max_output_tokens,
            )
        )

    @property
    def is_enabled(self) -> bool:
        """Whether this client can make authenticated calls."""
        return bool(
            self.config.enabled
            and self.config.api_key
            and self.config.base_url
            and self.config.model
        )

    def _chat_completions_url(self) -> str:
        return f"{self.config.base_url.rstrip('/')}/v1/chat/completions"

    def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_output_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Generate text from an OpenAI-compatible Chat Completions endpoint.
        """
        if not self.is_enabled:
            return {
                "success": False,
                "error": "LLM client is not configured",
            }

        payload: Dict[str, Any] = {
            "model": self.config.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            "max_tokens": max_output_tokens or self.config.max_output_tokens,
        }

        if temperature is not None:
            payload["temperature"] = temperature

        try:
            response = requests.post(
                self._chat_completions_url(),
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.config.timeout,
            )

            if not response.ok:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text[:500]}",
                    "status_code": response.status_code,
                }

            # Force UTF-8 encoding for proper handling of non-ASCII characters
            # Some APIs return text/event-stream without charset, causing
            # requests to default to ISO-8859-1 which breaks Chinese characters
            response.encoding = "utf-8"
            data = response.json()
            output_text = self.extract_output_text(data)
            if not output_text:
                return {
                    "success": False,
                    "error": "No text output found in response",
                    "raw": data,
                }

            return {
                "success": True,
                "text": output_text,
                "raw": data,
            }

        except requests.RequestException as exc:
            return {
                "success": False,
                "error": f"Request failed: {exc}",
            }
        except ValueError as exc:
            return {
                "success": False,
                "error": f"Invalid JSON response: {exc}",
            }

    def health_check(self) -> Dict[str, Any]:
        """Simple connectivity + auth + model health check."""
        result = self.generate_text(
            system_prompt="You are a health check assistant.",
            user_prompt="Reply with exactly: OK",
            temperature=0.0,
            max_output_tokens=10,
        )

        if not result.get("success"):
            return result

        response_text = str(result.get("text", "")).strip()
        if not response_text.upper().startswith("OK"):
            return {
                "success": False,
                "error": f"Unexpected health check response: {response_text}",
            }

        return {
            "success": True,
            "model": self.config.model,
            "base_url": self.config.base_url,
            "response_text": response_text,
        }

    @staticmethod
    def extract_output_text(response_data: Dict[str, Any]) -> str:
        """Extract text across common OpenAI-compatible response formats."""
        output_text = response_data.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()

        texts = []
        for item in response_data.get("output", []):
            if not isinstance(item, dict):
                continue
            for content in item.get("content", []):
                if not isinstance(content, dict):
                    continue
                text = content.get("text")
                if isinstance(text, str) and text.strip():
                    texts.append(text.strip())

        if texts:
            return "\n".join(texts)

        # Fallback for chat-completions-compatible gateways.
        choices = response_data.get("choices", [])
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                message = first.get("message", {})
                if isinstance(message, dict):
                    content = message.get("content")
                    if isinstance(content, str) and content.strip():
                        return content.strip()

        return ""

    # =========================================================================
    # Phase 2 & 3 Extension Methods
    # =========================================================================

    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str
    ) -> str:
        """
        Translate text using LLM.

        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code

        Returns:
            Translated text
        """
        system_prompt = """You are a professional translator. Translate the given text while:
1. Preserving markdown formatting and code blocks
2. Not translating code, only natural language text
3. Maintaining the original structure and style"""

        user_prompt = f"""Translate the following text from {source_lang} to {target_lang}:

{text}

Translation:"""

        result = self.generate_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3
        )

        if result.get("success"):
            return result.get("text", "").strip()
        return ""

    async def analyze_issue(
        self,
        title: str,
        body: str,
        labels: list
    ) -> dict:
        """
        Analyze a GitHub Issue using LLM.

        Args:
            title: Issue title
            body: Issue body
            labels: List of labels

        Returns:
            Analysis result dictionary
        """
        system_prompt = """You are a code contribution assistant. Analyze GitHub issues and provide structured assessments.
Respond with valid JSON only."""

        user_prompt = f"""Analyze the following GitHub Issue:

Title: {title}
Body: {body}
Labels: {', '.join(labels)}

Provide a JSON response with these fields:
- difficulty: one of [beginner, intermediate, advanced, expert]
- type: one of [bug, feature, documentation, other]
- skills_required: list of required skills
- estimated_hours: estimated hours to complete (number)
- description_summary: brief summary of the issue

JSON:"""

        result = self.generate_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
            max_output_tokens=500
        )

        if not result.get("success"):
            return self._default_issue_analysis()

        content = result.get("text", "").strip()
        return self._parse_json_response(content, self._default_issue_analysis())

    async def generate_strategy(
        self,
        repo_name: str,
        repo_description: str,
        issues_summary: list
    ) -> dict:
        """
        Generate contribution strategy using LLM.

        Args:
            repo_name: Repository name
            repo_description: Repository description
            issues_summary: List of issue summaries

        Returns:
            Strategy dictionary
        """
        system_prompt = """You are an open source contribution advisor. Help new contributors find the best way to start contributing.
Respond with valid JSON only."""

        issues_text = "\n".join([
            f"- #{i.get('number', 'N/A')}: {i.get('title', 'Unknown')} ({i.get('type', 'unknown')}, {i.get('difficulty', 'unknown')})"
            for i in issues_summary[:5]
        ])

        user_prompt = f"""Generate a contribution strategy for a new contributor:

Repository: {repo_name}
Description: {repo_description}

Available Issues:
{issues_text}

Provide a JSON response with:
- approach: overall approach description
- priority: one of [low, medium, high]
- steps: list of actionable steps

JSON:"""

        result = self.generate_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.4,
            max_output_tokens=500
        )

        if not result.get("success"):
            return self._default_strategy()

        content = result.get("text", "").strip()
        return self._parse_json_response(content, self._default_strategy())

    def _parse_json_response(self, content: str, default: dict) -> dict:
        """Parse JSON response with fallback to default."""
        import json
        import re

        try:
            # Try direct parsing
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Try extracting from code block
        try:
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', content)
            if json_match:
                return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

        return default

    def _default_issue_analysis(self) -> dict:
        """Default issue analysis result."""
        return {
            "difficulty": "intermediate",
            "type": "other",
            "skills_required": [],
            "estimated_hours": 4,
            "description_summary": "Unable to analyze"
        }

    def _default_strategy(self) -> dict:
        """Default contribution strategy."""
        return {
            "approach": "Start with documentation issues to understand the project",
            "priority": "medium",
            "steps": [
                "Read CONTRIBUTING.md",
                "Find good first issues",
                "Comment to claim"
            ]
        }
