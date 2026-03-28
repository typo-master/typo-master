"""
Typo Master Agent Runtime

Bridges product-facing backend APIs with LangGraph-based CoordinatorAgent and
LLM-backed chat support.
"""

import asyncio
import json
import os
import re
import yaml
from pathlib import Path
from urllib import request as urlrequest
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import pymysql
from pymysql.cursors import DictCursor

from src.agents.coordinator_agent import CoordinatorAgent
from src.agent_framework.logger import get_logger
from src.agent_framework.llm_client import OpenAICompatibleResponsesClient
from src.agent_framework.permissions import (
    normalize_permissions,
    set_current_permissions,
    PERMISSION_GROUPS,
    get_current_permissions,
    is_permission_allowed,
    get_permission_denial_message,
)
from app.agent.registry import RuntimeRegistry

# Optional: LangChain MCP adapter (requires Python >= 3.10)
# Falls back to mock implementation on Python 3.9
try:
    from langchain_mcp_adapters.client import MultiServerMCPClient
    _MCP_AVAILABLE = True
except ImportError:
    _MCP_AVAILABLE = False
    MultiServerMCPClient = None  # type: ignore

logger = get_logger(__name__)


def _load_config() -> Dict[str, Any]:
    """Load configuration from config.yml with fallback to empty dict."""
    return _load_config_with_path()[0]


def _load_config_with_path() -> Tuple[Dict[str, Any], Optional[Path]]:
    """Load configuration from config.yml and return config plus path."""
    # Try multiple strategies to find config file
    script_dir = Path(__file__).parent.parent.parent
    cwd = Path.cwd()

    config_paths = [
        cwd / "config.yml",
        script_dir / "config.yml",
        Path("/Users/cc11001100/github/typo-master/typo-master/config.yml"),
    ]

    for config_path in config_paths:
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                    if config:
                        logger.info(f"Loaded configuration from {config_path}")
                        return config, config_path
            except Exception as e:
                logger.warning(f"Failed to load config from {config_path}: {e}")

    logger.warning("No config file found, using environment variables only")
    return {}, None


@dataclass
class WorkflowRunRequest:
    workflow: str
    create_pr: bool
    owner: Optional[str] = None
    repo: Optional[str] = None
    days: int = 30
    min_stars: int = 100
    limit: int = 5


class TypeAgentRuntime:
    """
    Runtime façade for the product backend.
    """

    def __init__(self):
        self._coordinator: Optional[CoordinatorAgent] = None
        self._config_file: Optional[Path] = None
        # Load config and initialize LLM client with config file support
        logger.info(f"Initializing TypeAgentRuntime from cwd: {os.getcwd()}")
        self._config, self._config_file = _load_config_with_path()
        permissions = self._config.get("permissions") if isinstance(self._config, dict) else None
        set_current_permissions(normalize_permissions(permissions))
        logger.info(f"Config loaded, has llm section: {'llm' in self._config}")
        self._llm_client = OpenAICompatibleResponsesClient.from_config(self._config)
        if self._llm_client.is_enabled:
            logger.info(f"LLM client initialized with model: {self._llm_client.config.model}")
        else:
            logger.warning("LLM client not enabled - chat will use fallback responses")
        self._lock = asyncio.Lock()
        self._registry_lock = asyncio.Lock()
        self._registry = RuntimeRegistry()

    async def initialize(self) -> None:
        async with self._lock:
            if self._coordinator is not None:
                return

            self._coordinator = CoordinatorAgent(
                github_token=os.getenv("GITHUB_TOKEN"),
                work_dir=os.getenv("AGENT_WORK_DIR", "./work"),
                llm_client=self._llm_client,
            )
            await self._coordinator.initialize()
            self._registry.ensure_builtin_skills()
            self._registry.save()
            logger.info("TypeAgentRuntime initialized")

    async def shutdown(self) -> None:
        async with self._lock:
            if self._coordinator is None:
                return
            await self._coordinator.stop()
            self._coordinator = None
            logger.info("TypeAgentRuntime shutdown complete")

    async def get_capabilities(self) -> Dict[str, Any]:
        if not self._coordinator:
            return {"success": False, "error": "Agent runtime is not initialized"}
        caps = await self._coordinator.process_task({"type": "get_capabilities"})
        if not isinstance(caps, dict):
            return {"success": False, "error": "invalid capabilities payload"}

        skills = self._registry.list_skills()
        mcp_servers = self._registry.list_mcp_servers()
        caps["skill_registry"] = {
            "total": len(skills),
            "enabled": len([item for item in skills if item.get("enabled", True)]),
            "builtin": len([item for item in skills if item.get("source") == "builtin"]),
            "custom": len([item for item in skills if item.get("source") != "builtin"]),
        }
        caps["mcp"] = {
            "enabled_servers": len([item for item in mcp_servers if item.get("enabled", True)]),
            "total_servers": len(mcp_servers),
            "adapter": "langchain-mcp-adapters",
        }
        features = caps.get("features")
        if isinstance(features, dict):
            features["mcp_tool_execution"] = True
            features["sql_execution"] = True
        return caps

    async def run_workflow(self, req: WorkflowRunRequest) -> Dict[str, Any]:
        if not self._coordinator:
            return {"success": False, "error": "Agent runtime is not initialized"}

        task: Dict[str, Any] = {
            "type": "run_workflow",
            "workflow": req.workflow,
            "create_pr": req.create_pr,
            "days": req.days,
            "min_stars": req.min_stars,
            "limit": req.limit,
            "owner": req.owner,
            "repo": req.repo,
        }
        return await self._coordinator.process_task(task)

    async def list_skills(self) -> List[Dict[str, Any]]:
        return self._registry.list_skills()

    async def upsert_skill(self, skill_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        normalized_name = (skill_name or "").strip()
        if not normalized_name:
            return {"success": False, "error": "skill name is required"}
        try:
            async with self._registry_lock:
                record = self._registry.upsert_skill(normalized_name, payload)
                self._registry.save()
            return {"success": True, "skill": record}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def delete_skill(self, skill_name: str) -> Dict[str, Any]:
        normalized_name = (skill_name or "").strip()
        if not normalized_name:
            return {"success": False, "error": "skill name is required"}
        async with self._registry_lock:
            found = self._registry.get_skill(normalized_name)
            if not found:
                return {"success": False, "error": f"skill not found: {normalized_name}"}
            deleted = self._registry.delete_skill(normalized_name)
            if not deleted:
                return {"success": False, "error": "builtin skill cannot be deleted"}
            self._registry.save()
        return {"success": True, "skill_name": normalized_name}

    async def list_mcp_servers(self) -> Dict[str, Any]:
        servers = self._registry.list_mcp_servers()
        return {
            "success": True,
            "servers": servers,
            "adapter": {
                "name": "langchain-mcp-adapters",
                "available": True,
                "note": "MCP support enabled",
            },
        }

    async def list_mcp_catalog(self, query: str = "") -> Dict[str, Any]:
        items = self._registry.list_mcp_catalog(query=query)
        return {
            "success": True,
            "items": items,
            "query": query,
        }

    def get_permissions(self) -> Dict[str, Any]:
        return {
            "success": True,
            "permissions": normalize_permissions(
                self._config.get("permissions") if isinstance(self._config, dict) else None
            ),
            "groups": {key: list(value) for key, value in PERMISSION_GROUPS.items()},
        }

    def update_permissions(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            return {"success": False, "error": "permissions payload must be an object"}
        normalized = normalize_permissions(payload)
        set_current_permissions(normalized)
        if not isinstance(self._config, dict):
            self._config = {}
        self._config["permissions"] = normalized
        if not self._config_file:
            return {"success": False, "error": "config file not found"}
        try:
            with open(self._config_file, "w", encoding="utf-8") as f:
                yaml.safe_dump(self._config, f, allow_unicode=True, sort_keys=False)
        except Exception as exc:
            return {"success": False, "error": str(exc)}
        return {
            "success": True,
            "permissions": normalized,
            "groups": {key: list(value) for key, value in PERMISSION_GROUPS.items()},
        }

    async def install_mcp_from_catalog(
        self, catalog_id: str, overrides: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        normalized_id = (catalog_id or "").strip()
        if not normalized_id:
            return {"success": False, "error": "catalog_id is required"}
        try:
            async with self._registry_lock:
                record = self._registry.install_mcp_from_catalog(normalized_id, overrides=overrides or {})
                self._registry.save()
            return {"success": True, "server": record}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def upsert_mcp_server(self, server_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        normalized_id = (server_id or "").strip()
        if not normalized_id:
            return {"success": False, "error": "server id is required"}
        try:
            async with self._registry_lock:
                record = self._registry.upsert_mcp_server(normalized_id, payload)
                self._registry.save()
            return {"success": True, "server": record}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def delete_mcp_server(self, server_id: str) -> Dict[str, Any]:
        normalized_id = (server_id or "").strip()
        if not normalized_id:
            return {"success": False, "error": "server id is required"}
        async with self._registry_lock:
            if not self._registry.get_mcp_server(normalized_id):
                return {"success": False, "error": f"mcp server not found: {normalized_id}"}
            self._registry.delete_mcp_server(normalized_id)
            self._registry.save()
        return {"success": True, "server_id": normalized_id}

    async def probe_mcp_server(self, server_id: str) -> Dict[str, Any]:
        normalized_id = (server_id or "").strip()
        if not normalized_id:
            return {"success": False, "error": "server id is required"}
        server = self._registry.get_mcp_server(normalized_id)
        if not server:
            return {"success": False, "error": f"mcp server not found: {normalized_id}"}
        return await self._list_mcp_tools(server)

    async def execute_mcp_tool(
        self, server_id: str, tool_name: str, arguments: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        normalized_id = (server_id or "").strip()
        normalized_tool = (tool_name or "").strip()
        if not normalized_id:
            return {"success": False, "mode": "mcp", "error": "server_id is required"}
        if not normalized_tool:
            return {"success": False, "mode": "mcp", "error": "tool_name is required"}
        permissions = get_current_permissions()
        if not is_permission_allowed("api_call", permissions):
            return {
                "success": False,
                "mode": "mcp",
                "error": get_permission_denial_message("api_call"),
            }

        server = self._registry.get_mcp_server(normalized_id)
        if not server:
            return {"success": False, "mode": "mcp", "error": f"mcp server not found: {normalized_id}"}
        if not server.get("enabled", True):
            return {"success": False, "mode": "mcp", "error": f"mcp server is disabled: {normalized_id}"}

        return await self._invoke_mcp_tool(server, normalized_tool, arguments or {})

    async def execute_sql(
        self,
        database: str,
        query: str,
        args: Optional[List[Any]] = None,
        read_only: bool = True,
        max_rows: int = 200,
    ) -> Dict[str, Any]:
        params = {
            "database": database,
            "query": query,
            "args": args or [],
            "read_only": read_only,
            "max_rows": max_rows,
        }
        permissions = get_current_permissions()
        if not is_permission_allowed("api_call", permissions):
            if not self._allow_local_mysql_sql_without_api_permission(params):
                return {
                    "success": False,
                    "mode": "sql",
                    "error": get_permission_denial_message("api_call"),
                }
        return await self._execute_sql_skill("run_sql", params)

    async def execute_skill(
        self,
        skill_name: str,
        params: Optional[Dict[str, Any]] = None,
        skill_definition: Optional[Dict[str, Any]] = None,
        conversation_id: str = "",
    ) -> Dict[str, Any]:
        normalized_name = (skill_name or "").strip()
        if not normalized_name:
            return {"success": False, "error": "skill_name is required"}

        normalized_params = params or {}
        registered_skill = self._registry.get_skill(normalized_name)
        effective_skill: Dict[str, Any] = {}
        if isinstance(registered_skill, dict):
            effective_skill.update(registered_skill)
        if isinstance(skill_definition, dict):
            effective_skill.update(skill_definition)
        if effective_skill and "name" not in effective_skill:
            effective_skill["name"] = normalized_name
        if effective_skill and not bool(effective_skill.get("enabled", True)):
            return {
                "success": False,
                "mode": "skill_disabled",
                "error": f"Skill is disabled: {normalized_name}",
            }

        # Custom executor has highest priority so user-installed skills can define their own runtime behavior.
        executor = effective_skill.get("executor")
        if isinstance(executor, dict):
            custom_result = await self._execute_custom_executor(
                normalized_name,
                executor=executor,
                params=normalized_params,
                conversation_id=conversation_id,
            )
            if custom_result.get("success"):
                return custom_result
            return custom_result

        workflow_skills = {
            "scan_typo",
            "fix_typo",
            "create_pr",
            "batch_scan",
            "search_github_repos",
            "search_trending_repos",
            "open_auto_triage",
            "open_create_issue",
            "open_release_note_builder",
        }
        web3_skills = {
            "web3_search_airdrop_projects",
            "web3_analyze_project",
            "web3_find_typo_opportunities",
            "web3_contribute_and_pr",
            "web3_batch_farm",
        }
        secret_skills = {"scan_security_secrets", "open_secret_guard"}
        insecure_pattern_skills = {"open_insecure_pattern_scan"}
        dependency_skills = {"scan_dependency_vulns", "open_dependency_audit"}
        sql_skills = {"run_sql", "query_sql"}
        llm_skills = {"ask_ai", "summarize_diff"}
        webhook_skills = {"webhook_notify"}

        try:
            if normalized_name in workflow_skills:
                return await self._execute_workflow_skill(normalized_name, normalized_params)
            if normalized_name in web3_skills:
                return await self._execute_web3_skill(normalized_name, normalized_params)
            if normalized_name in secret_skills:
                return await self._execute_security_pattern_skill(normalized_name, normalized_params, mode="secret")
            if normalized_name in insecure_pattern_skills:
                return await self._execute_security_pattern_skill(normalized_name, normalized_params, mode="insecure")
            if normalized_name in dependency_skills:
                return await self._execute_dependency_audit_skill(normalized_name, normalized_params)
            if normalized_name in sql_skills:
                permission_key = "api_call"
                if not is_permission_allowed(permission_key):
                    if not self._allow_local_mysql_sql_without_api_permission(normalized_params):
                        return {
                            "success": False,
                            "mode": "sql",
                            "error": get_permission_denial_message(permission_key),
                        }
                return await self._execute_sql_skill(normalized_name, normalized_params)
            if normalized_name in webhook_skills:
                permission_key = "api_call"
                if not is_permission_allowed(permission_key):
                    return {
                        "success": False,
                        "mode": "webhook",
                        "error": get_permission_denial_message(permission_key),
                    }
                return await self._execute_webhook_skill(normalized_name, normalized_params)
            if normalized_name in llm_skills:
                prompt = str(
                    normalized_params.get("question")
                    or normalized_params.get("prompt")
                    or normalized_params.get("diff")
                    or ""
                ).strip()
                if not prompt:
                    prompt = f"Execute skill {normalized_name} with params: {json.dumps(normalized_params, ensure_ascii=False)}"
                chat_result = await self.chat(prompt, [], conversation_id=conversation_id)
                if not chat_result.get("success"):
                    return chat_result
                return {
                    "success": True,
                    "mode": "llm_skill",
                    "message": "LLM skill executed",
                    "result": {
                        "reply": chat_result.get("reply", ""),
                        "model": chat_result.get("model"),
                        "mode": chat_result.get("mode"),
                    },
                }
            if normalized_name == "mcp_client":
                return await self._execute_mcp_client_skill(normalized_name, normalized_params)
        except Exception as exc:
            logger.exception("Skill execution failed: %s", normalized_name)
            return {"success": False, "error": str(exc), "mode": "error"}

        if effective_skill:
            return {
                "success": False,
                "mode": "unsupported",
                "error": f"Skill {normalized_name} is configured but has no supported executor",
            }

        # Final fallback for unrecognized skills: run through LLM instruction flow.
        fallback_prompt = (
            f"You are executing a custom skill named '{normalized_name}'.\n"
            f"Parameters: {json.dumps(normalized_params, ensure_ascii=False)}\n"
            "Return concise execution guidance and expected outputs."
        )
        fallback_result = await self.chat(fallback_prompt, [], conversation_id=conversation_id)
        if not fallback_result.get("success"):
            return {
                "success": False,
                "error": f"Unsupported skill: {normalized_name}",
                "mode": "unsupported",
            }
        return {
            "success": True,
            "mode": "custom_fallback",
            "message": f"Skill {normalized_name} executed via fallback",
            "result": {
                "reply": fallback_result.get("reply", ""),
                "model": fallback_result.get("model"),
            },
        }

    async def _execute_custom_executor(
        self,
        skill_name: str,
        executor: Dict[str, Any],
        params: Dict[str, Any],
        conversation_id: str = "",
    ) -> Dict[str, Any]:
        executor_type = str(executor.get("type", "")).strip().lower()
        if not executor_type:
            return {"success": False, "error": "executor.type is required", "mode": "custom_executor"}

        if executor_type in {"workflow", "run_workflow"}:
            workflow = str(executor.get("workflow", "single_project")).strip() or "single_project"
            owner_key = str(executor.get("ownerParam", "owner"))
            repo_key = str(executor.get("repoParam", "repo"))
            owner = params.get(owner_key) or params.get("owner")
            repo = params.get(repo_key) or params.get("repo")
            create_pr = bool(executor.get("create_pr", params.get("create_pr", False)))
            days = int(params.get("days", executor.get("days", 30)))
            min_stars = int(params.get("min_stars", executor.get("min_stars", 100)))
            limit = int(params.get("limit", executor.get("limit", 5)))

            if workflow == "single_project" and (not owner or not repo):
                return {
                    "success": False,
                    "mode": "custom_executor",
                    "error": "single_project workflow requires owner and repo params",
                }

            workflow_result = await self.run_workflow(
                WorkflowRunRequest(
                    workflow=workflow,
                    create_pr=create_pr,
                    owner=str(owner) if owner else None,
                    repo=str(repo) if repo else None,
                    days=days,
                    min_stars=min_stars,
                    limit=limit,
                )
            )
            return {
                "success": bool(workflow_result.get("success", False)),
                "mode": "custom_executor_workflow",
                "message": f"Custom workflow executor finished for {skill_name}",
                "result": workflow_result,
                "error": workflow_result.get("error"),
            }

        if executor_type in {"mcp", "mcp_tool"}:
            server_id = str(executor.get("server_id") or params.get("server_id") or "").strip()
            tool_name = str(
                executor.get("tool")
                or executor.get("tool_name")
                or params.get("tool")
                or params.get("tool_name")
                or ""
            ).strip()
            arguments = params.get("arguments")
            if not isinstance(arguments, dict):
                arguments = {
                    key: value
                    for key, value in params.items()
                    if key not in {"server_id", "tool", "tool_name", "arguments"}
                }
            mcp_result = await self.execute_mcp_tool(server_id, tool_name, arguments)
            return {
                "success": bool(mcp_result.get("success", False)),
                "mode": "custom_executor_mcp",
                "message": f"Custom MCP executor finished for {skill_name}",
                "result": mcp_result.get("result"),
                "error": mcp_result.get("error"),
            }

        if executor_type in {"sql", "database"}:
            permission_key = "api_call"
            merged_params = {**params}
            for key in ("host", "port", "user", "password", "database", "query", "read_only", "max_rows"):
                if key in executor and key not in merged_params:
                    merged_params[key] = executor.get(key)
            if not is_permission_allowed(permission_key):
                if not self._allow_local_mysql_sql_without_api_permission(merged_params):
                    return {
                        "success": False,
                        "mode": "custom_executor_sql",
                        "error": get_permission_denial_message(permission_key),
                    }
            sql_result = await self._execute_sql_skill(skill_name, merged_params)
            return {
                "success": bool(sql_result.get("success", False)),
                "mode": "custom_executor_sql",
                "message": f"Custom SQL executor finished for {skill_name}",
                "result": sql_result.get("result"),
                "error": sql_result.get("error"),
            }

        if executor_type in {"http", "webhook"}:
            permission_key = "api_call"
            if not is_permission_allowed(permission_key):
                return {
                    "success": False,
                    "mode": "custom_executor",
                    "error": get_permission_denial_message(permission_key),
                }
            url = str(executor.get("url") or params.get("url") or "").strip()
            if not url:
                return {"success": False, "mode": "custom_executor", "error": "executor.url is required for http executor"}
            method = str(executor.get("method", "POST")).upper()
            payload = params.get("payload", params)
            return await self._execute_webhook_skill(
                skill_name,
                {"url": url, "method": method, "payload": payload},
            )

        if executor_type in {"llm", "prompt"}:
            permission_key = "llm_request"
            if not is_permission_allowed(permission_key):
                return {
                    "success": False,
                    "mode": "custom_executor_llm",
                    "error": get_permission_denial_message(permission_key),
                }
            template = str(executor.get("prompt") or executor.get("template") or "").strip()
            prompt = template or f"Execute custom skill {skill_name} with params {json.dumps(params, ensure_ascii=False)}"
            chat_result = await self.chat(prompt, [], conversation_id=conversation_id)
            if not chat_result.get("success"):
                return chat_result
            return {
                "success": True,
                "mode": "custom_executor_llm",
                "message": f"Custom LLM executor finished for {skill_name}",
                "result": {
                    "reply": chat_result.get("reply", ""),
                    "model": chat_result.get("model"),
                    "mode": chat_result.get("mode"),
                },
            }

        return {"success": False, "mode": "custom_executor", "error": f"Unsupported executor type: {executor_type}"}

    async def _execute_workflow_skill(self, skill_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        owner, repo = self._extract_owner_repo(params)
        days = int(params.get("days", 30))
        min_stars = int(params.get("minStars", params.get("min_stars", 100)))
        limit = int(params.get("limit", 5))

        if skill_name in {"search_github_repos", "search_trending_repos"}:
            workflow_result = await self.run_workflow(
                WorkflowRunRequest(
                    workflow="batch_projects",
                    create_pr=False,
                    days=days,
                    min_stars=min_stars,
                    limit=limit,
                )
            )
            return {
                "success": bool(workflow_result.get("success", False)),
                "mode": "workflow_skill",
                "message": f"{skill_name} executed via batch workflow",
                "result": workflow_result,
                "error": workflow_result.get("error"),
            }

        if skill_name in {"batch_scan"}:
            workflow_result = await self.run_workflow(
                WorkflowRunRequest(
                    workflow="batch_projects",
                    create_pr=bool(params.get("create_pr", False)),
                    days=days,
                    min_stars=min_stars,
                    limit=limit,
                )
            )
            return {
                "success": bool(workflow_result.get("success", False)),
                "mode": "workflow_skill",
                "message": "batch_scan executed",
                "result": workflow_result,
                "error": workflow_result.get("error"),
            }

        if not owner or not repo:
            return {
                "success": False,
                "mode": "workflow_skill",
                "error": "owner/repo are required. You can pass {\"owner\":\"...\",\"repo\":\"...\"} or {\"repository\":\"owner/repo\"}.",
            }

        create_pr = skill_name in {"create_pr", "open_create_issue"} or bool(params.get("create_pr", False))
        workflow_result = await self.run_workflow(
            WorkflowRunRequest(
                workflow="single_project",
                create_pr=create_pr,
                owner=owner,
                repo=repo,
                days=days,
                min_stars=min_stars,
                limit=limit,
            )
        )
        return {
            "success": bool(workflow_result.get("success", False)),
            "mode": "workflow_skill",
            "message": f"{skill_name} executed on {owner}/{repo}",
            "result": workflow_result,
            "error": workflow_result.get("error"),
        }

    async def _execute_web3_skill(self, skill_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Web3 airdrop-related skills."""
        from src.web3_typo_hunter.discovery.repo_finder import RepoFinder
        from src.web3_typo_hunter.scanner.typo_scanner import TypoScanner
        from src.web3_typo_hunter.processor.pr_creator import PRCreator
        from src.web3_typo_hunter.discovery.repo_manager import RepoManager

        github_token = os.getenv("GITHUB_TOKEN")

        try:
            if skill_name == "web3_search_airdrop_projects":
                days = int(params.get("days", 30))
                min_stars = int(params.get("min_stars", 100))
                limit = int(params.get("limit", 10))

                finder = RepoFinder(github_token)
                projects_df = finder.find_potential_airdrop_projects(days, min_stars, limit)

                # Convert DataFrame to list of dicts
                projects = projects_df.to_dict('records') if not projects_df.empty else []

                return {
                    "success": True,
                    "mode": "web3_skill",
                    "message": f"Found {len(projects)} potential airdrop projects",
                    "result": {
                        "total": len(projects),
                        "projects": projects,
                    },
                }

            if skill_name == "web3_analyze_project":
                owner, repo = self._extract_owner_repo(params)
                if not owner or not repo:
                    return {
                        "success": False,
                        "mode": "web3_skill",
                        "error": "owner and repo are required",
                    }

                finder = RepoFinder(github_token)
                # Get basic repo info from GitHub API
                from src.web3_typo_hunter.utils.github_api import GitHubAPI
                github_api = GitHubAPI(github_token)
                repo_info = github_api.get_repository(owner, repo)

                if not repo_info:
                    return {
                        "success": False,
                        "mode": "web3_skill",
                        "error": f"Repository {owner}/{repo} not found",
                    }

                # Analyze contribution activity
                analyzed = finder.analyze_repo_contribution(repo_info)

                return {
                    "success": True,
                    "mode": "web3_skill",
                    "message": f"Analyzed {owner}/{repo}",
                    "result": {
                        "name": analyzed.get("name"),
                        "full_name": analyzed.get("full_name"),
                        "url": analyzed.get("html_url"),
                        "stars": analyzed.get("stargazers_count"),
                        "forks": analyzed.get("forks_count"),
                        "airdrop_potential_score": analyzed.get("airdrop_potential_score", 0),
                        "recent_prs": analyzed.get("recent_prs", 0),
                        "recent_merged_prs": analyzed.get("recent_merged_prs", 0),
                        "pr_acceptance_rate": analyzed.get("pr_acceptance_rate", 0),
                        "description": analyzed.get("description"),
                        "topics": analyzed.get("topics", []),
                    },
                }

            if skill_name == "web3_find_typo_opportunities":
                owner, repo = self._extract_owner_repo(params)
                if not owner or not repo:
                    return {
                        "success": False,
                        "mode": "web3_skill",
                        "error": "owner and repo are required",
                    }

                auto_fix = bool(params.get("auto_fix", False))

                # Clone repo
                repo_manager = RepoManager()
                clone_result = repo_manager.clone_repo(f"{owner}/{repo}")

                if not clone_result.get("success"):
                    return {
                        "success": False,
                        "mode": "web3_skill",
                        "error": f"Failed to clone repo: {clone_result.get('error')}",
                    }

                repo_path = clone_result.get("path")

                # Scan for typos
                scanner = TypoScanner()
                scan_results = scanner.scan_repository(repo_path)

                typos_found = scan_results.get("typos", [])

                result = {
                    "success": True,
                    "mode": "web3_skill",
                    "message": f"Found {len(typos_found)} typos in {owner}/{repo}",
                    "result": {
                        "owner": owner,
                        "repo": repo,
                        "typos_count": len(typos_found),
                        "typos": typos_found,
                        "auto_fixed": False,
                    },
                }

                # Auto fix if requested
                if auto_fix and typos_found:
                    from src.web3_typo_hunter.scanner.typo_fixer import TypoFixer
                    fixer = TypoFixer()
                    fix_result = fixer.fix_typos(repo_path, typos_found)
                    result["result"]["auto_fixed"] = fix_result.get("success", False)
                    result["result"]["fixed_files"] = fix_result.get("fixed_files", [])

                return result

            if skill_name == "web3_contribute_and_pr":
                owner, repo = self._extract_owner_repo(params)
                if not owner or not repo:
                    return {
                        "success": False,
                        "mode": "web3_skill",
                        "error": "owner and repo are required",
                    }

                create_pr = bool(params.get("create_pr", True))

                # Step 1: Find typos
                finder_result = await self._execute_web3_skill("web3_find_typo_opportunities", {
                    "owner": owner,
                    "repo": repo,
                    "auto_fix": True,
                })

                if not finder_result.get("success"):
                    return finder_result

                typos_count = finder_result.get("result", {}).get("typos_count", 0)

                if typos_count == 0:
                    return {
                        "success": True,
                        "mode": "web3_skill",
                        "message": f"No typos found in {owner}/{repo}, no PR needed",
                        "result": {
                            "owner": owner,
                            "repo": repo,
                            "pr_created": False,
                            "reason": "No typos to fix",
                        },
                    }

                # Step 2: Create PR if requested
                if create_pr and github_token:
                    pr_creator = PRCreator(github_token)
                    repo_manager = RepoManager()

                    # Prepare repo info for PR creation
                    repo_info = {
                        "full_name": f"{owner}/{repo}",
                        "owner": owner,
                        "repo": repo,
                        "fixed_files": finder_result.get("result", {}).get("fixed_files", []),
                        "branch_name": f"fix/typos-{datetime.now().strftime('%Y%m%d')}",
                    }

                    pr_result = pr_creator.prepare_and_create_pr(repo_info)

                    return {
                        "success": pr_result.get("pr_created", False),
                        "mode": "web3_skill",
                        "message": f"PR created for {owner}/{repo}" if pr_result.get("pr_created") else f"Failed to create PR: {pr_result.get('pr_error')}",
                        "result": {
                            "owner": owner,
                            "repo": repo,
                            "typos_fixed": typos_count,
                            "pr_created": pr_result.get("pr_created", False),
                            "pr_url": pr_result.get("pr_url"),
                            "pr_number": pr_result.get("pr_number"),
                            "error": pr_result.get("pr_error"),
                        },
                    }
                else:
                    return {
                        "success": True,
                        "mode": "web3_skill",
                        "message": f"Fixed {typos_count} typos in {owner}/{repo} (PR creation skipped)",
                        "result": {
                            "owner": owner,
                            "repo": repo,
                            "typos_fixed": typos_count,
                            "pr_created": False,
                            "fixed_files": finder_result.get("result", {}).get("fixed_files", []),
                        },
                    }

            if skill_name == "web3_batch_farm":
                projects = params.get("projects", [])
                create_prs = bool(params.get("create_prs", True))

                if not projects or not isinstance(projects, list):
                    return {
                        "success": False,
                        "mode": "web3_skill",
                        "error": "projects must be a list of {owner, repo} objects",
                    }

                results = []
                for project in projects:
                    owner = project.get("owner")
                    repo = project.get("repo")
                    if owner and repo:
                        project_result = await self._execute_web3_skill("web3_contribute_and_pr", {
                            "owner": owner,
                            "repo": repo,
                            "create_pr": create_prs,
                        })
                        results.append({
                            "owner": owner,
                            "repo": repo,
                            "result": project_result,
                        })

                successful = sum(1 for r in results if r["result"].get("success"))

                return {
                    "success": successful > 0,
                    "mode": "web3_skill",
                    "message": f"Batch farm completed: {successful}/{len(projects)} successful",
                    "result": {
                        "total": len(projects),
                        "successful": successful,
                        "failed": len(projects) - successful,
                        "details": results,
                    },
                }

            return {
                "success": False,
                "mode": "web3_skill",
                "error": f"Unknown Web3 skill: {skill_name}",
            }

        except Exception as exc:
            logger.exception("Web3 skill execution failed: %s", skill_name)
            return {"success": False, "error": str(exc), "mode": "web3_skill"}

    @staticmethod
    def _extract_owner_repo(params: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
        owner = params.get("owner")
        repo = params.get("repo")
        if owner and repo:
            return str(owner), str(repo)

        for key in ("repository", "repoFullName", "target"):
            value = params.get(key)
            if isinstance(value, str) and "/" in value:
                maybe_owner, maybe_repo = value.split("/", 1)
                maybe_owner = maybe_owner.strip()
                maybe_repo = maybe_repo.strip()
                if maybe_owner and maybe_repo:
                    return maybe_owner, maybe_repo
        return None, None

    async def _execute_webhook_skill(self, skill_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        url = str(params.get("url") or "").strip()
        if not url.startswith("http://") and not url.startswith("https://"):
            return {"success": False, "mode": "webhook", "error": "webhook url must start with http:// or https://"}

        method = str(params.get("method", "POST")).upper()
        payload = params.get("payload", {})
        headers = {"Content-Type": "application/json"}
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        def _send_request() -> Dict[str, Any]:
            req = urlrequest.Request(url, data=body, headers=headers, method=method)
            with urlrequest.urlopen(req, timeout=12) as resp:  # nosec B310
                response_body = resp.read().decode("utf-8", errors="replace")
                return {
                    "status": getattr(resp, "status", 200),
                    "body": response_body[:4000],
                }

        response_data = await asyncio.to_thread(_send_request)
        ok = 200 <= int(response_data.get("status", 0)) < 400
        return {
            "success": ok,
            "mode": "webhook",
            "message": f"Webhook executed for {skill_name}",
            "result": response_data,
            "error": None if ok else "Webhook returned non-success status",
        }

    async def _execute_mcp_client_skill(self, skill_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute MCP client skill to call external MCP Server"""
        server_url = str(params.get("server_url") or "").strip()
        tool_name = str(params.get("tool_name") or "").strip()
        arguments = params.get("arguments", {}) or {}

        if not server_url:
            return {"success": False, "mode": "mcp_client", "error": "server_url is required"}
        if not tool_name:
            return {"success": False, "mode": "mcp_client", "error": "tool_name is required"}

        # Check permission
        if not is_permission_allowed("api_call"):
            return {
                "success": False,
                "mode": "mcp_client",
                "error": get_permission_denial_message("api_call"),
            }

        try:
            from src.skills.mcp_client_skill import call_mcp_tool
            from src.agent_framework.skill_system import SkillContext

            ctx = SkillContext()
            result = await call_mcp_tool(
                server_url=server_url,
                tool_name=tool_name,
                arguments=arguments,
                context=ctx
            )

            if result.success:
                return {
                    "success": True,
                    "mode": "mcp_client",
                    "message": f"MCP tool {tool_name} executed successfully",
                    "result": result.data,
                    "metadata": result.metadata,
                }
            else:
                return {
                    "success": False,
                    "mode": "mcp_client",
                    "error": result.error or "MCP tool execution failed",
                    "metadata": result.metadata,
                }
        except Exception as e:
            logger.exception("MCP client skill execution failed")
            return {
                "success": False,
                "mode": "mcp_client",
                "error": f"MCP client execution failed: {str(e)}",
            }

    async def _execute_security_pattern_skill(self, skill_name: str, params: Dict[str, Any], mode: str) -> Dict[str, Any]:
        base_path = str(params.get("path") or params.get("target") or ".").strip() or "."
        root = Path(base_path).expanduser().resolve()
        if not root.exists():
            return {"success": False, "mode": "security_scan", "error": f"path not found: {root}"}

        secret_patterns = [
            ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}")),
            ("openai_like_key", re.compile(r"sk-[A-Za-z0-9]{20,}")),
            ("private_key_block", re.compile(r"BEGIN (?:RSA|OPENSSH|EC) PRIVATE KEY")),
            ("generic_api_key", re.compile(r"api[_-]?key\s*[:=]\s*['\"][^'\"]+['\"]", re.IGNORECASE)),
        ]
        insecure_patterns = [
            ("javascript_eval", re.compile(r"\beval\s*\(")),
            ("python_exec", re.compile(r"\bexec\s*\(")),
            ("shell_true", re.compile(r"shell\s*=\s*True")),
            ("weak_hash_md5", re.compile(r"\bmd5\s*\(")),
            ("weak_hash_sha1", re.compile(r"\bsha1\s*\(")),
            ("dom_innerhtml", re.compile(r"\.innerHTML\s*=")),
        ]

        selected_patterns = secret_patterns if mode == "secret" else insecure_patterns
        files = self._iter_candidate_files(root, max_files=int(params.get("max_files", 300)))
        findings: List[Dict[str, Any]] = []

        for file_path in files:
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            lines = content.splitlines()
            for line_no, line in enumerate(lines, start=1):
                for pattern_name, pattern in selected_patterns:
                    match = pattern.search(line)
                    if not match:
                        continue
                    findings.append(
                        {
                            "file": str(file_path),
                            "line": line_no,
                            "pattern": pattern_name,
                            "snippet": line.strip()[:200],
                        }
                    )
                    if len(findings) >= int(params.get("max_findings", 200)):
                        break
                if len(findings) >= int(params.get("max_findings", 200)):
                    break
            if len(findings) >= int(params.get("max_findings", 200)):
                break

        return {
            "success": True,
            "mode": "security_scan",
            "message": f"{skill_name} scan finished",
            "result": {
                "path": str(root),
                "files_scanned": len(files),
                "findings_count": len(findings),
                "findings": findings,
            },
        }

    async def _execute_dependency_audit_skill(self, skill_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        manifest = str(params.get("manifest") or "").strip()
        root = Path(str(params.get("path") or ".")).expanduser().resolve()
        manifest_candidates = []
        if manifest:
            manifest_candidates.append(Path(manifest).expanduser().resolve())
        else:
            manifest_candidates.extend([root / "package.json", root / "requirements.txt", root / "go.mod"])

        manifest_path = next((item for item in manifest_candidates if item.exists()), None)
        if not manifest_path:
            return {
                "success": False,
                "mode": "dependency_audit",
                "error": "No dependency manifest found. Provide {\"manifest\":\"/path/to/package.json\"}.",
            }

        risky_packages = {
            "event-stream": "Known supply chain incident history",
            "ua-parser-js": "Known compromised release history",
            "log4j-core": "Historically high-impact CVEs",
            "pyyaml": "Unsafe loader misuse risk",
            "lodash": "Prototype pollution risk in outdated versions",
            "requests": "Review pinned version and TLS settings",
        }

        detected: List[str] = []
        try:
            content = manifest_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as exc:
            return {"success": False, "mode": "dependency_audit", "error": f"Cannot read manifest: {exc}"}

        lower_content = content.lower()
        for pkg in risky_packages:
            if pkg.lower() in lower_content:
                detected.append(pkg)

        findings = [{"package": pkg, "reason": risky_packages[pkg]} for pkg in detected]
        return {
            "success": True,
            "mode": "dependency_audit",
            "message": f"{skill_name} audit finished",
            "result": {
                "manifest": str(manifest_path),
                "findings_count": len(findings),
                "findings": findings,
            },
        }

    @staticmethod
    def _allow_local_mysql_sql_without_api_permission(params: Optional[Dict[str, Any]] = None) -> bool:
        payload = params or {}
        host = str(payload.get("host") or os.getenv("MYSQL_HOST", "127.0.0.1")).strip().lower()
        return host in {"127.0.0.1", "localhost", "::1"}

    async def _execute_sql_skill(self, skill_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        host = str(params.get("host") or os.getenv("MYSQL_HOST", "127.0.0.1")).strip()
        port_raw = params.get("port", os.getenv("MYSQL_PORT", "3306"))
        user = str(params.get("user") or os.getenv("MYSQL_USER", "root")).strip()
        password = str(params.get("password") or os.getenv("MYSQL_PASSWORD", "nopasswd"))
        database = str(params.get("database") or params.get("db") or "").strip()

        if not database:
            database = str(os.getenv("MYSQL_DATABASE", "typomaster")).strip()

        try:
            port = int(port_raw)
        except Exception:
            return {
                "success": False,
                "mode": "sql",
                "error": f"invalid mysql port: {port_raw}",
            }

        query = str(params.get("query") or params.get("sql") or "").strip()
        if not database:
            return {
                "success": False,
                "mode": "sql",
                "error": "database is required. Example: {\"database\":\"typomaster\"}",
            }
        if not query:
            return {
                "success": False,
                "mode": "sql",
                "error": "query is required. Example: {\"query\":\"SELECT * FROM users LIMIT 10\"}",
            }

        read_only = bool(params.get("read_only", True))
        normalized_sql = query.strip().lower()
        if read_only:
            allowed_prefixes = ("select", "with", "show", "describe", "desc", "explain")
            if not normalized_sql.startswith(allowed_prefixes):
                return {
                    "success": False,
                    "mode": "sql",
                    "error": "read_only mode only allows SELECT/WITH/SHOW/DESCRIBE/EXPLAIN statements",
                }

        max_rows_raw = params.get("max_rows", 200)
        try:
            max_rows = int(max_rows_raw)
        except Exception:
            max_rows = 200
        max_rows = max(1, min(max_rows, 5000))

        args_raw = params.get("args", [])
        if isinstance(args_raw, list):
            args = args_raw
        else:
            args = [args_raw]

        conn = None
        try:
            conn = pymysql.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                charset="utf8mb4",
                cursorclass=DictCursor,
                autocommit=False,
            )
            cursor = conn.cursor()
            cursor.execute(query, tuple(args))
            description = cursor.description
            if description:
                rows = [dict(row) for row in cursor.fetchmany(max_rows)]
                return {
                    "success": True,
                    "mode": "sql",
                    "message": f"{skill_name} query executed",
                    "result": {
                        "database": database,
                        "host": host,
                        "port": port,
                        "query": query,
                        "row_count": len(rows),
                        "rows": rows,
                        "truncated": len(rows) == max_rows,
                    },
                }

            affected = int(cursor.rowcount or 0)
            conn.commit()
            return {
                "success": True,
                "mode": "sql",
                "message": f"{skill_name} statement executed",
                "result": {
                    "database": database,
                    "host": host,
                    "port": port,
                    "query": query,
                    "affected_rows": affected,
                },
            }
        except Exception as exc:
            return {
                "success": False,
                "mode": "sql",
                "error": f"SQL execution failed: {exc}",
            }
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

    @staticmethod
    def _iter_candidate_files(root: Path, max_files: int = 300) -> List[Path]:
        skip_dirs = {".git", "node_modules", ".venv", ".pm2", "dist", "build", "__pycache__"}
        files: List[Path] = []
        for current_root, dirs, filenames in os.walk(root):
            dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]
            for filename in filenames:
                if filename.startswith("."):
                    continue
                full_path = Path(current_root) / filename
                try:
                    if full_path.stat().st_size > 512 * 1024:
                        continue
                except Exception:
                    continue
                files.append(full_path)
                if len(files) >= max_files:
                    return files
        return files

    async def _list_mcp_tools(self, server: Dict[str, Any]) -> Dict[str, Any]:
        if not _MCP_AVAILABLE:
            return {
                "success": False,
                "mode": "mcp",
                "error": "MCP support requires Python >= 3.10. Current Python version does not support MCP.",
            }
        client = None
        try:
            client = MultiServerMCPClient({server["id"]: self._build_mcp_client_config(server)})
            tools = await client.get_tools()
            tool_names = [str(getattr(tool, "name", "")).strip() for tool in tools if getattr(tool, "name", None)]
            return {
                "success": True,
                "mode": "mcp",
                "result": {
                    "server_id": server["id"],
                    "tools": sorted(tool_names),
                },
            }
        except Exception as exc:
            return {
                "success": False,
                "mode": "mcp",
                "error": f"Failed to load MCP tools from {server['id']}: {exc}",
            }
        finally:
            if client is not None:
                close_fn = getattr(client, "aclose", None)
                if callable(close_fn):
                    try:
                        await close_fn()
                    except Exception:
                        pass

    async def _invoke_mcp_tool(
        self, server: Dict[str, Any], tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not _MCP_AVAILABLE:
            return {
                "success": False,
                "mode": "mcp",
                "error": "MCP support requires Python >= 3.10. Current Python version does not support MCP.",
            }
        client = None
        try:
            client = MultiServerMCPClient({server["id"]: self._build_mcp_client_config(server)})
            tools = await client.get_tools()
            selected = None
            available: List[str] = []
            for tool in tools:
                name = str(getattr(tool, "name", "")).strip()
                if name:
                    available.append(name)
                if name == tool_name:
                    selected = tool

            if selected is None:
                return {
                    "success": False,
                    "mode": "mcp",
                    "error": f"MCP tool not found: {tool_name}",
                    "result": {"available_tools": sorted(available)},
                }

            output = await selected.ainvoke(arguments or {})
            return {
                "success": True,
                "mode": "mcp",
                "result": {
                    "server_id": server["id"],
                    "tool_name": tool_name,
                    "output": self._to_json_safe(output),
                },
            }
        except Exception as exc:
            return {
                "success": False,
                "mode": "mcp",
                "error": f"MCP invocation failed ({server['id']}/{tool_name}): {exc}",
            }
        finally:
            if client is not None:
                close_fn = getattr(client, "aclose", None)
                if callable(close_fn):
                    try:
                        await close_fn()
                    except Exception:
                        pass

    @staticmethod
    def _build_mcp_client_config(server: Dict[str, Any]) -> Dict[str, Any]:
        transport = str(server.get("transport") or "stdio").strip().lower()
        if transport == "streamable_http":
            transport = "http"

        config: Dict[str, Any] = {"transport": transport}
        if transport == "stdio":
            command = str(server.get("command") or "").strip()
            if not command:
                raise ValueError("stdio transport requires command")
            config["command"] = command
            args = server.get("args")
            config["args"] = args if isinstance(args, list) else []
            env = server.get("env")
            if isinstance(env, dict) and env:
                config["env"] = env
        else:
            url = str(server.get("url") or "").strip()
            if not url:
                raise ValueError(f"{transport} transport requires url")
            config["url"] = url
            headers = server.get("headers")
            if isinstance(headers, dict) and headers:
                config["headers"] = headers
        return config

    @staticmethod
    def _to_json_safe(value: Any) -> Any:
        try:
            json.dumps(value, ensure_ascii=False)
            return value
        except Exception:
            if isinstance(value, bytes):
                try:
                    return value.decode("utf-8", errors="replace")
                except Exception:
                    return str(value)
            if isinstance(value, datetime):
                return value.astimezone(timezone.utc).isoformat()
            return str(value)

    async def chat(
        self,
        message: str,
        conversation_history: List[Dict[str, str]],
        conversation_id: str = "",
    ) -> Dict[str, Any]:
        """
        Chat endpoint support with memory integration.

        Supports both:
        - natural language responses (LLM mode)
        - lightweight autonomous actions via slash command:
          /run owner/repo
        """
        normalized = (message or "").strip()
        if not normalized:
            return {"success": False, "error": "message is empty"}

        # Record conversation to memory
        if self._coordinator and conversation_id:
            await self._coordinator.add_to_conversation(
                role="user", content=normalized, conversation_id=conversation_id
            )

        if normalized.startswith("/run "):
            result = await self._handle_run_command(normalized)
            # Record response
            if self._coordinator and conversation_id:
                await self._coordinator.add_to_conversation(
                    role="assistant", content=result.get("reply", ""), conversation_id=conversation_id
                )
            return result

        # Build context from memory
        memory_context = ""
        if self._coordinator and self._coordinator.config.enable_memory:
            try:
                memory_context = await self._coordinator.build_llm_context(normalized)
            except Exception as e:
                logger.warning(f"Failed to build memory context: {e}")

        if not self._llm_client.is_enabled:
            fallback = self._rule_based_chat_fallback(normalized)
            # Record response
            if self._coordinator and conversation_id:
                await self._coordinator.add_to_conversation(
                    role="assistant", content=fallback, conversation_id=conversation_id
                )
            return {
                "success": True,
                "mode": "fallback",
                "reply": fallback,
            }

        system_prompt = (
            "You are Typo Master Agent assistant. Help users operate typo-fix agent workflows. "
            "Be concise, practical, and execution-oriented."
        )

        # Include memory context if available
        history_text = self._history_to_text(conversation_history)
        context_section = f"\n\n### Relevant Context from Memory:\n{memory_context}\n" if memory_context else ""

        user_prompt = (
            f"Conversation history:\n{history_text}\n"
            f"{context_section}\n"
            f"User message:\n{normalized}\n\n"
            "Respond with practical next actions. If the user asks to run workflow, "
            "suggest using /run owner/repo command."
        )

        permissions = get_current_permissions()
        if not is_permission_allowed("llm_request", permissions):
            fallback = self._rule_based_chat_fallback(normalized)
            if self._coordinator and conversation_id:
                await self._coordinator.add_to_conversation(
                    role="assistant", content=fallback, conversation_id=conversation_id
                )
            return {
                "success": True,
                "mode": "fallback",
                "reply": fallback,
                "warning": get_permission_denial_message("llm_request"),
            }

        llm_result = await asyncio.to_thread(
            self._llm_client.generate_text,
            system_prompt,
            user_prompt,
            0.2,
        )
        if not llm_result.get("success"):
            fallback = self._rule_based_chat_fallback(normalized)
            # Record response
            if self._coordinator and conversation_id:
                await self._coordinator.add_to_conversation(
                    role="assistant", content=fallback, conversation_id=conversation_id
                )
            return {
                "success": True,
                "mode": "fallback",
                "reply": fallback,
                "warning": llm_result.get("error"),
            }

        reply = llm_result.get("text", "").strip()

        # Record response
        if self._coordinator and conversation_id:
            await self._coordinator.add_to_conversation(
                role="assistant", content=reply, conversation_id=conversation_id
            )

        return {
            "success": True,
            "mode": "llm",
            "reply": reply,
            "model": self._llm_client.config.model,
        }

    async def _handle_run_command(self, text: str) -> Dict[str, Any]:
        if not self._coordinator:
            return {"success": False, "error": "Agent runtime is not initialized"}

        payload = text[len("/run "):].strip()
        if "/" not in payload:
            return {
                "success": False,
                "error": "Invalid /run format, expected: /run owner/repo",
            }

        owner, repo = payload.split("/", 1)
        owner = owner.strip()
        repo = repo.strip()
        if not owner or not repo:
            return {
                "success": False,
                "error": "Invalid /run format, expected: /run owner/repo",
            }

        permissions = get_current_permissions()
        if not is_permission_allowed("github_read", permissions):
            return {
                "success": False,
                "mode": "agent_action",
                "reply": get_permission_denial_message("github_read"),
                "action_result": {"success": False, "error": "github_read disabled"},
            }

        result = await self.run_workflow(
            WorkflowRunRequest(
                workflow="single_project",
                owner=owner,
                repo=repo,
                create_pr=False,
            )
        )
        return {
            "success": True,
            "mode": "agent_action",
            "reply": f"Workflow finished for {owner}/{repo}",
            "action_result": result,
        }

    @staticmethod
    def _history_to_text(history: List[Dict[str, str]]) -> str:
        if not history:
            return "(empty)"
        lines = []
        for item in history[-12:]:
            role = item.get("role", "user")
            content = item.get("content", "")
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    @staticmethod
    def _rule_based_chat_fallback(message: str) -> str:
        msg = message.lower()
        if "capab" in msg or "能力" in msg:
            return "Use the capabilities endpoint to inspect current agent features."
        if "run" in msg or "执行" in msg or "扫描" in msg:
            return "You can run a workflow with slash command: /run owner/repo"
        return "LLM is not configured. Set OPENAI_API_KEY/OPENAI_BASE_URL/OPENAI_MODEL for full chat."


agent_runtime = TypeAgentRuntime()
