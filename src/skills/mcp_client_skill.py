"""
MCP Client Skill

支持通过 Skill 调用外部 MCP Server 的 Tools。
"""

import json
from typing import Any, Dict, List, Optional, AsyncGenerator
from dataclasses import dataclass

from src.agent_framework.skill_system import BaseSkill, SkillMetadata, SkillResult, SkillContext, SkillCategory
from src.agent_framework.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MCPClientConfig:
    """MCP 客户端配置"""
    server_url: str  # SSE 端点 URL
    timeout: float = 30.0


class MCPClientSkill(BaseSkill):
    """
    MCP 客户端 Skill

    用于连接外部 MCP Server 并调用其 Tools。
    支持通过 SSE 协议与 MCP Server 通信。
    """

    def __init__(self):
        super().__init__(SkillMetadata(
            name="mcp_client",
            description="调用外部 MCP Server 的 Tools",
            category=SkillCategory.CUSTOM,
            version="1.0.0",
            tags=["mcp", "client", "integration"]
        ))
        self._connections: Dict[str, Any] = {}

    async def execute(
        self,
        context: SkillContext,
        server_url: str,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> SkillResult:
        """
        执行 MCP Tool 调用

        Args:
            server_url: MCP Server SSE 端点 URL
            tool_name: 要调用的 Tool 名称
            arguments: Tool 参数

        Returns:
            SkillResult 包含调用结果
        """
        arguments = arguments or {}

        try:
            # 使用 aiohttp 连接 MCP SSE Server
            result = await self._call_mcp_tool(server_url, tool_name, arguments)

            return SkillResult(
                success=True,
                data=result,
                metadata={
                    "server_url": server_url,
                    "tool_name": tool_name,
                }
            )

        except Exception as e:
            logger.exception(f"MCP tool call failed: {tool_name}")
            return SkillResult(
                success=False,
                error=str(e),
                metadata={
                    "server_url": server_url,
                    "tool_name": tool_name,
                }
            )

    async def _call_mcp_tool(
        self,
        server_url: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        调用 MCP Tool

        实现 MCP 协议：
        1. 连接 SSE 端点获取 session_id
        2. 发送 initialize 请求
        3. 调用 tools/call
        4. 接收 SSE 结果
        """
        import aiohttp
        import asyncio

        async with aiohttp.ClientSession() as session:
            # 1. 连接 SSE 获取 endpoint
            headers = {
                "Accept": "text/event-stream",
                "Cache-Control": "no-cache",
            }

            async with session.get(server_url, headers=headers) as resp:
                if resp.status != 200:
                    raise Exception(f"Failed to connect to MCP SSE: {resp.status}")

                # 读取 SSE 事件获取 endpoint
                message_endpoint = None
                server_info = None

                async for line in resp.content:
                    line = line.decode('utf-8').strip()

                    if line.startswith("event: endpoint"):
                        # 下一行是 data
                        pass
                    elif line.startswith("data:") and message_endpoint is None:
                        try:
                            data = json.loads(line[5:].strip())
                            if "uri" in data:
                                message_endpoint = data["uri"]
                                # 构建完整 URL
                                base_url = server_url.replace("/sse", "")
                                if message_endpoint.startswith("/"):
                                    message_endpoint = base_url + message_endpoint
                                else:
                                    message_endpoint = base_url + "/" + message_endpoint
                        except:
                            pass
                    elif line.startswith("data:") and server_info is None:
                        try:
                            data = json.loads(line[5:].strip())
                            if data.get("result") and "name" in data["result"]:
                                server_info = data["result"]
                        except:
                            pass

                    if message_endpoint and server_info:
                        break

                if not message_endpoint:
                    raise Exception("Failed to get message endpoint from MCP SSE")

            # 2. 发送 initialize 请求
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "typoagent-mcp-client",
                        "version": "1.0.0"
                    }
                }
            }

            async with session.post(
                message_endpoint,
                json=init_request,
                headers={"Content-Type": "application/json"}
            ) as resp:
                if resp.status != 200:
                    raise Exception(f"Initialize failed: {resp.status}")
                init_response = await resp.json()
                if "error" in init_response:
                    raise Exception(f"Initialize error: {init_response['error']}")

            # 3. 发送 initialized 通知
            initialized_notification = {
                "jsonrpc": "2.0",
                "method": "initialized",
                "params": {}
            }
            async with session.post(
                message_endpoint,
                json=initialized_notification,
                headers={"Content-Type": "application/json"}
            ) as resp:
                pass  # 不需要等待响应

            # 4. 调用 tool
            tool_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }

            async with session.post(
                message_endpoint,
                json=tool_request,
                headers={"Content-Type": "application/json"}
            ) as resp:
                if resp.status != 200:
                    raise Exception(f"Tool call failed: {resp.status}")
                tool_response = await resp.json()

                # 5. 接收 SSE 结果
                # 重新连接 SSE 获取结果
                result_data = None

                async with session.get(server_url, headers=headers) as sse_resp:
                    async for line in sse_resp.content:
                        line = line.decode('utf-8').strip()

                        if line.startswith("data:"):
                            try:
                                data = json.loads(line[5:].strip())
                                # 检查是否是 tool 调用结果
                                if data.get("id") == 2 and "result" in data:
                                    result_data = data["result"]
                                    break
                                elif data.get("id") == 2 and "error" in data:
                                    raise Exception(f"Tool error: {data['error']}")
                            except json.JSONDecodeError:
                                continue

                if result_data is None:
                    # 如果 SSE 没有返回，使用 HTTP 响应
                    if "result" in tool_response:
                        result_data = tool_response["result"]
                    elif "error" in tool_response:
                        raise Exception(f"Tool error: {tool_response['error']}")
                    else:
                        result_data = {"status": "pending"}

                return {
                    "tool_name": tool_name,
                    "result": result_data,
                    "server_info": server_info
                }


# 便捷函数
async def call_mcp_tool(
    server_url: str,
    tool_name: str,
    arguments: Optional[Dict[str, Any]] = None,
    context: Optional[SkillContext] = None
) -> SkillResult:
    """
    便捷函数：调用 MCP Tool

    Args:
        server_url: MCP Server SSE URL
        tool_name: Tool 名称
        arguments: Tool 参数
        context: Skill 上下文

    Returns:
        SkillResult
    """
    skill = MCPClientSkill()
    ctx = context or SkillContext()

    return await skill.execute(
        context=ctx,
        server_url=server_url,
        tool_name=tool_name,
        arguments=arguments or {}
    )
