"""
Runtime registry for product-managed skills and MCP servers.
"""

from __future__ import annotations

import json
import os
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.agent_framework.logger import get_logger

logger = get_logger(__name__)

ALLOWED_MCP_TRANSPORTS = {"stdio", "http", "sse", "streamable_http"}

BUILTIN_SKILLS: List[Dict[str, Any]] = [
    {
        "name": "scan_typo",
        "description": "Scan a repository for typo issues",
        "category": "scanner",
    },
    {
        "name": "fix_typo",
        "description": "Run typo fixing workflow for a repository",
        "category": "fixer",
    },
    {
        "name": "create_pr",
        "description": "Run workflow and create pull request if needed",
        "category": "github",
    },
    {
        "name": "batch_scan",
        "description": "Run batch typo scan workflow",
        "category": "automation",
    },
    {
        "name": "search_github_repos",
        "description": "Discover repositories with typo-fix opportunities",
        "category": "discovery",
    },
    {
        "name": "search_trending_repos",
        "description": "Discover trending repositories for typo scans",
        "category": "discovery",
    },
    {
        "name": "ask_ai",
        "description": "Use LLM to answer arbitrary question",
        "category": "ai",
    },
    {
        "name": "summarize_diff",
        "description": "Summarize code diff with LLM",
        "category": "ai",
    },
    {
        "name": "webhook_notify",
        "description": "Call remote webhook endpoint",
        "category": "integration",
    },
    {
        "name": "scan_security_secrets",
        "description": "Scan repository for secrets",
        "category": "security",
    },
    {
        "name": "scan_dependency_vulns",
        "description": "Check dependency manifest for risky packages",
        "category": "security",
    },
    {
        "name": "open_secret_guard",
        "description": "Community secret scanner",
        "category": "security",
    },
    {
        "name": "open_dependency_audit",
        "description": "Community dependency audit skill",
        "category": "security",
    },
    {
        "name": "open_insecure_pattern_scan",
        "description": "Community insecure-pattern scanner",
        "category": "security",
    },
    {
        "name": "open_auto_triage",
        "description": "Community auto-triage workflow",
        "category": "automation",
    },
    {
        "name": "open_create_issue",
        "description": "Community create-issue workflow",
        "category": "github",
    },
    {
        "name": "open_release_note_builder",
        "description": "Community release-note builder workflow",
        "category": "report",
    },
    {
        "name": "run_sql",
        "description": "Execute SQL query against configured database",
        "category": "analysis",
    },
    {
        "name": "mcp_client",
        "description": "Call external MCP Server Tools via SSE",
        "category": "integration",
        "parameters": [
            {"name": "server_url", "type": "string", "required": True, "description": "MCP Server SSE URL"},
            {"name": "tool_name", "type": "string", "required": True, "description": "Tool name to call"},
            {"name": "arguments", "type": "object", "required": False, "description": "Tool arguments"},
        ],
    },
    # Web3 Airdrop Skills
    {
        "name": "web3_search_airdrop_projects",
        "description": "Search for Web3 projects with high airdrop potential",
        "category": "web3",
        "parameters": [
            {"name": "days", "type": "integer", "required": False, "description": "Recent activity days (default: 30)"},
            {"name": "min_stars", "type": "integer", "required": False, "description": "Minimum stars (default: 100)"},
            {"name": "limit", "type": "integer", "required": False, "description": "Max results (default: 10)"},
        ],
    },
    {
        "name": "web3_analyze_project",
        "description": "Analyze a Web3 project for airdrop potential and contribution opportunities",
        "category": "web3",
        "parameters": [
            {"name": "owner", "type": "string", "required": True, "description": "Repository owner"},
            {"name": "repo", "type": "string", "required": True, "description": "Repository name"},
        ],
    },
    {
        "name": "web3_find_typo_opportunities",
        "description": "Find typo-fix opportunities in Web3 projects for airdrop farming",
        "category": "web3",
        "parameters": [
            {"name": "owner", "type": "string", "required": True, "description": "Repository owner"},
            {"name": "repo", "type": "string", "required": True, "description": "Repository name"},
            {"name": "auto_fix", "type": "boolean", "required": False, "description": "Auto fix typos (default: false)"},
        ],
    },
    {
        "name": "web3_contribute_and_pr",
        "description": "Complete workflow: find typos, fix them, and create PR for airdrop eligibility",
        "category": "web3",
        "parameters": [
            {"name": "owner", "type": "string", "required": True, "description": "Repository owner"},
            {"name": "repo", "type": "string", "required": True, "description": "Repository name"},
            {"name": "create_pr", "type": "boolean", "required": False, "description": "Create PR after fixing (default: true)"},
        ],
    },
    {
        "name": "web3_batch_farm",
        "description": "Batch process multiple Web3 projects for airdrop farming",
        "category": "web3",
        "parameters": [
            {"name": "projects", "type": "array", "required": True, "description": "List of {owner, repo} objects"},
            {"name": "create_prs", "type": "boolean", "required": False, "description": "Create PRs for each (default: true)"},
        ],
    },
]

MCP_CATALOG_TEMPLATES: List[Dict[str, Any]] = [
    {
        "catalog_id": "filesystem",
        "name": "Filesystem MCP",
        "description": "Read and write files via MCP filesystem server",
        "tags": ["filesystem", "local", "official"],
        "server": {
            "id": "filesystem",
            "name": "Filesystem MCP",
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
            "enabled": True,
        },
    },
    {
        "catalog_id": "fetch",
        "name": "Fetch MCP",
        "description": "Fetch remote URLs and web resources via MCP",
        "tags": ["http", "web", "official"],
        "server": {
            "id": "fetch",
            "name": "Fetch MCP",
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-fetch"],
            "enabled": True,
        },
    },
    {
        "catalog_id": "github",
        "name": "GitHub MCP",
        "description": "Operate GitHub resources via MCP (issues, PRs, repos)",
        "tags": ["github", "git", "official"],
        "server": {
            "id": "github",
            "name": "GitHub MCP",
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "enabled": True,
            "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "YOUR_GITHUB_TOKEN"},
        },
    },
    {
        "catalog_id": "postgres",
        "name": "Postgres MCP",
        "description": "Query PostgreSQL databases through MCP",
        "tags": ["sql", "postgres", "database"],
        "server": {
            "id": "postgres",
            "name": "Postgres MCP",
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-postgres"],
            "enabled": True,
            "env": {"DATABASE_URL": "postgresql://user:pass@localhost:5432/dbname"},
        },
    },
]


def now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


class RuntimeRegistry:
    def __init__(self, file_path: Optional[str] = None) -> None:
        default_path = os.getenv("TYPOMASTER_REGISTRY_PATH", "./agent_states/runtime_registry.json")
        self.file_path = Path(file_path or default_path).expanduser().resolve()
        self.skills: Dict[str, Dict[str, Any]] = {}
        self.mcp_servers: Dict[str, Dict[str, Any]] = {}
        self.load()
        if self.ensure_builtin_skills():
            self.save()

    def load(self) -> None:
        if not self.file_path.exists():
            return
        try:
            data = json.loads(self.file_path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to load runtime registry: %s", exc)
            return

        skills_raw = data.get("skills", {})
        if isinstance(skills_raw, dict):
            for key, value in skills_raw.items():
                if isinstance(value, dict):
                    normalized = self._normalize_skill(value, fallback_name=key)
                    self.skills[normalized["name"]] = normalized
        elif isinstance(skills_raw, list):
            for item in skills_raw:
                if isinstance(item, dict):
                    normalized = self._normalize_skill(item)
                    self.skills[normalized["name"]] = normalized

        servers_raw = data.get("mcp_servers", {})
        if isinstance(servers_raw, dict):
            for key, value in servers_raw.items():
                if isinstance(value, dict):
                    normalized = self._normalize_mcp_server(value, fallback_id=key)
                    self.mcp_servers[normalized["id"]] = normalized
        elif isinstance(servers_raw, list):
            for item in servers_raw:
                if isinstance(item, dict):
                    normalized = self._normalize_mcp_server(item)
                    self.mcp_servers[normalized["id"]] = normalized

    def save(self) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "skills": self.skills,
            "mcp_servers": self.mcp_servers,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def ensure_builtin_skills(self) -> bool:
        changed = False
        for template in BUILTIN_SKILLS:
            name = template["name"]
            existing = self.skills.get(name)
            merged = {
                **template,
                **(existing or {}),
                "name": name,
                "description": existing.get("description") if isinstance(existing, dict) and existing.get("description") else template["description"],
                "category": existing.get("category") if isinstance(existing, dict) and existing.get("category") else template["category"],
                "source": "builtin",
                "installMethod": "catalog",
                "enabled": bool(existing.get("enabled", True)) if isinstance(existing, dict) else True,
            }
            normalized = self._normalize_skill(merged, fallback_name=name)
            if existing != normalized:
                self.skills[name] = normalized
                changed = True
        return changed

    def list_skills(self) -> List[Dict[str, Any]]:
        return [deepcopy(self.skills[name]) for name in sorted(self.skills)]

    def get_skill(self, name: str) -> Optional[Dict[str, Any]]:
        item = self.skills.get(name)
        return deepcopy(item) if item else None

    def upsert_skill(self, name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        existing = self.skills.get(name)
        base = deepcopy(existing) if existing else {}
        merged = {**base, **(payload or {}), "name": name}
        normalized = self._normalize_skill(merged, fallback_name=name)
        if existing and existing.get("source") == "builtin":
            normalized["source"] = "builtin"
            normalized["installMethod"] = "catalog"
        self.skills[name] = normalized
        return deepcopy(normalized)

    def delete_skill(self, name: str) -> bool:
        item = self.skills.get(name)
        if not item:
            return False
        if item.get("source") == "builtin":
            return False
        self.skills.pop(name, None)
        return True

    def list_mcp_servers(self) -> List[Dict[str, Any]]:
        return [deepcopy(self.mcp_servers[name]) for name in sorted(self.mcp_servers)]

    def get_mcp_server(self, server_id: str) -> Optional[Dict[str, Any]]:
        item = self.mcp_servers.get(server_id)
        return deepcopy(item) if item else None

    def upsert_mcp_server(self, server_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        existing = self.mcp_servers.get(server_id)
        base = deepcopy(existing) if existing else {}
        merged = {**base, **(payload or {}), "id": server_id}
        normalized = self._normalize_mcp_server(merged, fallback_id=server_id)
        self.mcp_servers[server_id] = normalized
        return deepcopy(normalized)

    def delete_mcp_server(self, server_id: str) -> bool:
        if server_id not in self.mcp_servers:
            return False
        self.mcp_servers.pop(server_id, None)
        return True

    def list_mcp_catalog(self, query: str = "") -> List[Dict[str, Any]]:
        normalized_query = (query or "").strip().lower()
        if not normalized_query:
            return deepcopy(MCP_CATALOG_TEMPLATES)

        def matches(item: Dict[str, Any]) -> bool:
            haystack = " ".join(
                [
                    str(item.get("catalog_id", "")),
                    str(item.get("name", "")),
                    str(item.get("description", "")),
                    " ".join([str(tag) for tag in item.get("tags", [])]),
                ]
            ).lower()
            return normalized_query in haystack

        return [deepcopy(item) for item in MCP_CATALOG_TEMPLATES if matches(item)]

    def install_mcp_from_catalog(
        self, catalog_id: str, overrides: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        normalized_id = (catalog_id or "").strip()
        if not normalized_id:
            raise ValueError("catalog_id is required")

        template = next(
            (item for item in MCP_CATALOG_TEMPLATES if str(item.get("catalog_id")) == normalized_id),
            None,
        )
        if not template:
            raise ValueError(f"mcp catalog item not found: {normalized_id}")

        base_server = deepcopy(template["server"])
        merged = {**base_server, **(overrides or {})}
        server_id = str(merged.get("id") or base_server.get("id") or normalized_id).strip()
        if not server_id:
            raise ValueError("resolved mcp server id is empty")

        return self.upsert_mcp_server(server_id, merged)

    @staticmethod
    def _normalize_skill(payload: Dict[str, Any], fallback_name: Optional[str] = None) -> Dict[str, Any]:
        current_ms = now_ms()
        name = str(payload.get("name") or fallback_name or "").strip()
        if not name:
            raise ValueError("skill name is required")

        record: Dict[str, Any] = {
            "name": name,
            "description": str(payload.get("description") or f"{name} skill").strip(),
            "category": str(payload.get("category") or "default").strip() or "default",
            "enabled": bool(payload.get("enabled", True)),
            "source": str(payload.get("source") or "custom").strip() or "custom",
            "sourceUrl": payload.get("sourceUrl"),
            "version": str(payload.get("version") or "1.0.0").strip() or "1.0.0",
            "homepage": payload.get("homepage"),
            "tags": payload.get("tags") if isinstance(payload.get("tags"), list) else [],
            "parameters": payload.get("parameters") if isinstance(payload.get("parameters"), list) else [],
            "executor": payload.get("executor") if isinstance(payload.get("executor"), dict) else None,
            "installMethod": str(payload.get("installMethod") or "manual").strip() or "manual",
            "createdAt": int(payload.get("createdAt") or current_ms),
            "updatedAt": int(payload.get("updatedAt") or current_ms),
        }
        if record["source"] == "builtin":
            record["installMethod"] = "catalog"
        return record

    @staticmethod
    def _normalize_mcp_server(payload: Dict[str, Any], fallback_id: Optional[str] = None) -> Dict[str, Any]:
        current_ms = now_ms()
        server_id = str(payload.get("id") or fallback_id or "").strip()
        if not server_id:
            raise ValueError("mcp server id is required")

        transport = str(payload.get("transport") or "stdio").strip().lower()
        if transport not in ALLOWED_MCP_TRANSPORTS:
            raise ValueError(f"unsupported mcp transport: {transport}")

        args = payload.get("args")
        if isinstance(args, str):
            args = [args]
        if not isinstance(args, list):
            args = []
        args = [str(item) for item in args]

        headers = payload.get("headers")
        if not isinstance(headers, dict):
            headers = {}
        env = payload.get("env")
        if not isinstance(env, dict):
            env = {}

        timeout = payload.get("timeout", 30)
        try:
            timeout = int(timeout)
        except Exception:
            timeout = 30
        timeout = max(3, min(timeout, 600))

        record = {
            "id": server_id,
            "name": str(payload.get("name") or server_id).strip() or server_id,
            "description": str(payload.get("description") or "").strip(),
            "enabled": bool(payload.get("enabled", True)),
            "transport": transport,
            "command": str(payload.get("command") or "").strip() or None,
            "args": args,
            "url": str(payload.get("url") or "").strip() or None,
            "headers": {str(k): str(v) for k, v in headers.items()},
            "env": {str(k): str(v) for k, v in env.items()},
            "timeout": timeout,
            "createdAt": int(payload.get("createdAt") or current_ms),
            "updatedAt": int(payload.get("updatedAt") or current_ms),
            "metadata": payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {},
        }
        return record
