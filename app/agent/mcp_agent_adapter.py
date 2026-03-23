"""
MCP Agent Adapter

将 TypoAgent 的能力暴露为 MCP (Model Context Protocol) Tools，
使外部 MCP 客户端可以通过 SSE 连接调用 Agent 的能力。
"""

import json
import asyncio
from typing import Any, Dict, List, Optional, Callable, AsyncGenerator
from dataclasses import dataclass
from datetime import datetime

from src.agent_framework.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MCPToolDefinition:
    """MCP Tool 定义"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable[..., Any]


@dataclass
class MCPResourceDefinition:
    """MCP Resource 定义"""
    uri: str
    name: str
    description: str
    mime_type: str
    handler: Callable[..., Any]


class MCPAgentAdapter:
    """
    Agent 的 MCP 适配器

    将 TypeMaster Agent 的能力（Skills、Tools、Workflows）暴露为 MCP Tools，
    支持外部 MCP 客户端通过 SSE 连接调用。
    """

    def __init__(self, agent_runtime: Any):
        self.agent_runtime = agent_runtime
        self.tools: Dict[str, MCPToolDefinition] = {}
        self.resources: Dict[str, MCPResourceDefinition] = {}
        self._session_id_counter = 0
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._register_builtin_tools()

    def _register_builtin_tools(self) -> None:
        """注册内置的 MCP Tools"""
        # Agent 能力 Tools
        self.register_tool(
            name="typoagent_chat",
            description="与 TypoAgent 进行对话，获取智能回复",
            input_schema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "用户输入的消息"
                    },
                    "conversation_id": {
                        "type": "string",
                        "description": "对话 ID（可选）"
                    }
                },
                "required": ["message"]
            },
            handler=self._handle_chat
        )

        self.register_tool(
            name="typoagent_execute_skill",
            description="执行 TypoAgent 的 Skill",
            input_schema={
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "Skill 名称"
                    },
                    "params": {
                        "type": "object",
                        "description": "Skill 参数"
                    },
                    "conversation_id": {
                        "type": "string",
                        "description": "对话 ID（可选）"
                    }
                },
                "required": ["skill_name"]
            },
            handler=self._handle_execute_skill
        )

        self.register_tool(
            name="typoagent_list_skills",
            description="列出所有可用的 Skills",
            input_schema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "按类别筛选（可选）"
                    }
                }
            },
            handler=self._handle_list_skills
        )

        self.register_tool(
            name="typoagent_run_workflow",
            description="运行 Agent 工作流",
            input_schema={
                "type": "object",
                "properties": {
                    "workflow": {
                        "type": "string",
                        "enum": ["single_project", "batch_projects"],
                        "description": "工作流类型"
                    },
                    "owner": {
                        "type": "string",
                        "description": "GitHub 仓库所有者"
                    },
                    "repo": {
                        "type": "string",
                        "description": "GitHub 仓库名"
                    },
                    "create_pr": {
                        "type": "boolean",
                        "description": "是否创建 PR"
                    }
                },
                "required": ["workflow"]
            },
            handler=self._handle_run_workflow
        )

        self.register_tool(
            name="typoagent_get_capabilities",
            description="获取 Agent 的能力信息",
            input_schema={
                "type": "object",
                "properties": {}
            },
            handler=self._handle_get_capabilities
        )

        self.register_tool(
            name="typoagent_execute_mcp_tool",
            description="执行外部 MCP Server 的 Tool",
            input_schema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "MCP Server ID"
                    },
                    "tool_name": {
                        "type": "string",
                        "description": "Tool 名称"
                    },
                    "arguments": {
                        "type": "object",
                        "description": "Tool 参数"
                    }
                },
                "required": ["server_id", "tool_name"]
            },
            handler=self._handle_execute_mcp_tool
        )

        self.register_tool(
            name="typoagent_list_mcp_servers",
            description="列出配置的 MCP Servers",
            input_schema={
                "type": "object",
                "properties": {}
            },
            handler=self._handle_list_mcp_servers
        )

        # 注册 Resources
        self.register_resource(
            uri="typoagent://skills",
            name="Agent Skills",
            description="List of available TypoAgent skills",
            mime_type="application/json",
            handler=self._handle_resource_skills
        )

        self.register_resource(
            uri="typoagent://capabilities",
            name="Agent Capabilities",
            description="TypoAgent capabilities and features",
            mime_type="application/json",
            handler=self._handle_resource_capabilities
        )

    def register_tool(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        handler: Callable[..., Any]
    ) -> None:
        """注册 MCP Tool"""
        self.tools[name] = MCPToolDefinition(
            name=name,
            description=description,
            input_schema=input_schema,
            handler=handler
        )
        logger.info(f"Registered MCP tool: {name}")

    def register_resource(
        self,
        uri: str,
        name: str,
        description: str,
        mime_type: str,
        handler: Callable[..., Any]
    ) -> None:
        """注册 MCP Resource"""
        self.resources[uri] = MCPResourceDefinition(
            uri=uri,
            name=name,
            description=description,
            mime_type=mime_type,
            handler=handler
        )
        logger.info(f"Registered MCP resource: {uri}")

    def create_session(self) -> str:
        """创建新的 MCP 会话"""
        self._session_id_counter += 1
        session_id = f"session_{self._session_id_counter}_{datetime.now().timestamp()}"
        self._sessions[session_id] = {
            "created_at": datetime.now().isoformat(),
            "conversation_id": None,
        }
        logger.info(f"Created MCP session: {session_id}")
        return session_id

    def close_session(self, session_id: str) -> None:
        """关闭 MCP 会话"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"Closed MCP session: {session_id}")

    def get_server_info(self) -> Dict[str, Any]:
        """获取 MCP Server 信息"""
        return {
            "name": "typoagent-mcp-server",
            "version": "1.0.0",
            "display_name": "TypoAgent MCP Server",
            "description": "TypeMaster Agent 的 MCP 服务端，支持通过 SSE 连接调用 Agent 能力",
            "capabilities": {
                "tools": {
                    "listChanged": True
                },
                "resources": {
                    "subscribe": False,
                    "listChanged": True
                }
            }
        }

    def get_tools_list(self) -> List[Dict[str, Any]]:
        """获取所有 Tools 列表"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema
            }
            for tool in self.tools.values()
        ]

    def get_resources_list(self) -> List[Dict[str, Any]]:
        """获取所有 Resources 列表"""
        return [
            {
                "uri": resource.uri,
                "name": resource.name,
                "description": resource.description,
                "mimeType": resource.mime_type
            }
            for resource in self.resources.values()
        ]

    async def call_tool(
        self,
        session_id: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """调用 MCP Tool"""
        tool = self.tools.get(tool_name)
        if not tool:
            yield {
                "type": "error",
                "error": f"Tool not found: {tool_name}"
            }
            return

        try:
            # 发送进度更新
            yield {
                "type": "progress",
                "progress": 10,
                "message": f"Starting execution of {tool_name}"
            }

            # 执行 tool handler
            result = await tool.handler(session_id, arguments)

            yield {
                "type": "progress",
                "progress": 100,
                "message": "Execution completed"
            }

            yield {
                "type": "result",
                "content": result
            }

        except Exception as e:
            logger.exception(f"Tool execution failed: {tool_name}")
            yield {
                "type": "error",
                "error": str(e)
            }

    async def read_resource(self, uri: str) -> Optional[Dict[str, Any]]:
        """读取 MCP Resource"""
        resource = self.resources.get(uri)
        if not resource:
            return None

        try:
            content = await resource.handler()
            return {
                "uri": resource.uri,
                "mimeType": resource.mime_type,
                "content": content
            }
        except Exception as e:
            logger.exception(f"Resource read failed: {uri}")
            return None

    # ===== Tool Handlers =====

    async def _handle_chat(
        self,
        session_id: str,
        arguments: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """处理 chat tool 调用"""
        message = arguments.get("message", "")
        conversation_id = arguments.get("conversation_id") or self._get_or_create_conversation(session_id)

        result = await self.agent_runtime.chat(
            message,
            [],
            conversation_id=conversation_id
        )

        return [{
            "type": "text",
            "text": result.get("reply", ""),
            "metadata": {
                "mode": result.get("mode"),
                "model": result.get("model"),
                "conversation_id": conversation_id
            }
        }]

    async def _handle_execute_skill(
        self,
        session_id: str,
        arguments: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """处理 execute_skill tool 调用"""
        skill_name = arguments.get("skill_name", "")
        params = arguments.get("params", {})
        conversation_id = arguments.get("conversation_id") or self._get_or_create_conversation(session_id)

        result = await self.agent_runtime.execute_skill(
            skill_name=skill_name,
            params=params,
            conversation_id=conversation_id
        )

        content_text = result.get("message", "")
        if result.get("error"):
            content_text += f"\nError: {result['error']}"

        return [{
            "type": "text",
            "text": content_text,
            "metadata": {
                "success": result.get("success"),
                "skill_name": skill_name,
                "mode": result.get("mode"),
                "result": result.get("result") if result.get("success") else None
            }
        }]

    async def _handle_list_skills(
        self,
        session_id: str,
        arguments: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """处理 list_skills tool 调用"""
        skills = await self.agent_runtime.list_skills()
        category = arguments.get("category")

        if category:
            skills = [s for s in skills if s.get("category") == category]

        return [{
            "type": "text",
            "text": json.dumps({
                "total": len(skills),
                "skills": [
                    {
                        "name": s.get("name"),
                        "description": s.get("description"),
                        "category": s.get("category"),
                        "enabled": s.get("enabled", True)
                    }
                    for s in skills
                ]
            }, ensure_ascii=False, indent=2),
            "metadata": {
                "total": len(skills),
                "filtered_by_category": category
            }
        }]

    async def _handle_run_workflow(
        self,
        session_id: str,
        arguments: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """处理 run_workflow tool 调用"""
        from app.agent.runtime import WorkflowRunRequest

        request = WorkflowRunRequest(
            workflow=arguments.get("workflow", "single_project"),
            create_pr=arguments.get("create_pr", False),
            owner=arguments.get("owner"),
            repo=arguments.get("repo"),
        )

        result = await self.agent_runtime.run_workflow(request)

        return [{
            "type": "text",
            "text": json.dumps(result, ensure_ascii=False, indent=2),
            "metadata": {
                "success": result.get("success"),
                "workflow": request.workflow
            }
        }]

    async def _handle_get_capabilities(
        self,
        session_id: str,
        arguments: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """处理 get_capabilities tool 调用"""
        caps = await self.agent_runtime.get_capabilities()

        return [{
            "type": "text",
            "text": json.dumps(caps, ensure_ascii=False, indent=2),
            "metadata": {
                "service": "typoagent",
                "version": "1.0.0"
            }
        }]

    async def _handle_execute_mcp_tool(
        self,
        session_id: str,
        arguments: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """处理外部 MCP tool 执行"""
        server_id = arguments.get("server_id", "")
        tool_name = arguments.get("tool_name", "")
        tool_arguments = arguments.get("arguments", {})

        result = await self.agent_runtime.execute_mcp_tool(
            server_id=server_id,
            tool_name=tool_name,
            arguments=tool_arguments
        )

        return [{
            "type": "text",
            "text": json.dumps(result, ensure_ascii=False, indent=2),
            "metadata": {
                "success": result.get("success"),
                "server_id": server_id,
                "tool_name": tool_name
            }
        }]

    async def _handle_list_mcp_servers(
        self,
        session_id: str,
        arguments: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """处理 list_mcp_servers tool 调用"""
        result = await self.agent_runtime.list_mcp_servers()

        return [{
            "type": "text",
            "text": json.dumps(result, ensure_ascii=False, indent=2),
            "metadata": {
                "count": len(result.get("servers", []))
            }
        }]

    # ===== Resource Handlers =====

    async def _handle_resource_skills(self) -> str:
        """处理 skills resource 读取"""
        skills = await self.agent_runtime.list_skills()
        return json.dumps({
            "skills": skills,
            "total": len(skills),
            "updated_at": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)

    async def _handle_resource_capabilities(self) -> str:
        """处理 capabilities resource 读取"""
        caps = await self.agent_runtime.get_capabilities()
        return json.dumps({
            "capabilities": caps,
            "updated_at": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)

    # ===== Helper Methods =====

    def _get_or_create_conversation(self, session_id: str) -> str:
        """获取或创建对话 ID"""
        session = self._sessions.get(session_id)
        if session and session.get("conversation_id"):
            return session["conversation_id"]

        conversation_id = f"mcp_conv_{session_id}_{datetime.now().timestamp()}"
        if session:
            session["conversation_id"] = conversation_id
        return conversation_id
