"""
MCP SSE Server

基于 Server-Sent Events 的 MCP (Model Context Protocol) 服务端实现，
支持外部 MCP 客户端通过 HTTP SSE 连接调用 TypoAgent 的能力。
"""

import json
import asyncio
import uuid
from typing import Any, Dict, Optional, Set, Callable
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import Request, Response
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask

from src.agent_framework.logger import get_logger
from .mcp_agent_adapter import MCPAgentAdapter

logger = get_logger(__name__)


class MCPSSEServer:
    """
    MCP SSE 服务端

    实现 MCP 协议，支持：
    1. /mcp/sse - SSE 连接端点，用于 Server -> Client 消息
    2. /mcp/messages - 客户端消息接收端点

    消息格式遵循 MCP 协议规范：
    https://spec.modelcontextprotocol.io/
    """

    def __init__(self, agent_adapter: MCPAgentAdapter):
        self.agent_adapter = agent_adapter
        self._sessions: Dict[str, "MCPSession"] = {}
        self._lock = asyncio.Lock()

    async def create_session(self, request: Request) -> "MCPSession":
        """创建新的 MCP 会话"""
        session_id = str(uuid.uuid4())
        session = MCPSession(
            session_id=session_id,
            server=self,
            client_info={
                "user_agent": request.headers.get("user-agent", "unknown"),
                "remote_addr": request.client.host if request.client else "unknown"
            }
        )
        async with self._lock:
            self._sessions[session_id] = session
        logger.info(f"Created MCP session: {session_id}")
        return session

    async def get_session(self, session_id: str) -> Optional["MCPSession"]:
        """获取会话"""
        return self._sessions.get(session_id)

    async def close_session(self, session_id: str) -> None:
        """关闭会话"""
        async with self._lock:
            session = self._sessions.pop(session_id, None)
        if session:
            await session.close()
            logger.info(f"Closed MCP session: {session_id}")

    async def handle_sse(self, request: Request) -> StreamingResponse:
        """
        处理 SSE 连接请求

        返回 SSE 流，用于向客户端发送：
        - Server Info (初始化)
        - Tool 列表更新
        - Resource 列表更新
        - Tool 调用结果
        """
        session = await self.create_session(request)

        async def event_generator():
            """SSE 事件生成器"""
            try:
                # 发送 endpoint 信息
                yield self._format_sse_event(
                    "endpoint",
                    json.dumps({
                        "uri": f"/mcp/messages?session_id={session.session_id}"
                    })
                )

                # 发送 Server Info
                yield self._format_sse_event(
                    "message",
                    json.dumps({
                        "jsonrpc": "2.0",
                        "id": 0,
                        "result": self.agent_adapter.get_server_info()
                    })
                )

                # 发送 Tools 列表
                yield self._format_sse_event(
                    "message",
                    json.dumps({
                        "jsonrpc": "2.0",
                        "method": "tools/list",
                        "params": {
                            "tools": self.agent_adapter.get_tools_list()
                        }
                    })
                )

                # 保持连接，等待会话关闭或客户端断开
                while session.is_active:
                    # 检查是否有待发送的消息
                    message = await session.get_message(timeout=1.0)
                    if message:
                        yield self._format_sse_event("message", json.dumps(message))

            except asyncio.CancelledError:
                logger.info(f"SSE connection cancelled for session: {session.session_id}")
            except Exception as e:
                logger.exception(f"SSE error for session: {session.session_id}")
                yield self._format_sse_event(
                    "error",
                    json.dumps({"error": str(e)})
                )
            finally:
                await self.close_session(session.session_id)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
            },
            background=BackgroundTask(self._cleanup_session, session.session_id)
        )

    async def handle_message(self, request: Request) -> Response:
        """
        处理客户端消息

        接收客户端发送的 JSON-RPC 请求，处理并返回响应。
        """
        session_id = request.query_params.get("session_id")
        if not session_id:
            return Response(
                content=json.dumps({
                    "jsonrpc": "2.0",
                    "error": {"code": -32600, "message": "Missing session_id"}
                }),
                media_type="application/json",
                status_code=400
            )

        session = await self.get_session(session_id)
        if not session:
            return Response(
                content=json.dumps({
                    "jsonrpc": "2.0",
                    "error": {"code": -32600, "message": "Invalid session_id"}
                }),
                media_type="application/json",
                status_code=400
            )

        try:
            body = await request.json()
        except Exception as e:
            return Response(
                content=json.dumps({
                    "jsonrpc": "2.0",
                    "error": {"code": -32700, "message": f"Parse error: {str(e)}"}
                }),
                media_type="application/json",
                status_code=400
            )

        # 处理 JSON-RPC 请求
        response = await self._handle_jsonrpc(session, body)

        return Response(
            content=json.dumps(response),
            media_type="application/json",
            status_code=200
        )

    async def _handle_jsonrpc(
        self,
        session: "MCPSession",
        request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """处理 JSON-RPC 请求"""

        # 检查 JSON-RPC 版本
        if request.get("jsonrpc") != "2.0":
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {"code": -32600, "message": "Invalid Request: expected jsonrpc 2.0"}
            }

        method = request.get("method", "")
        params = request.get("params", {})
        request_id = request.get("id")

        try:
            if method == "initialize":
                return await self._handle_initialize(session, request_id, params)

            elif method == "initialized":
                # 客户端确认初始化完成
                return {"jsonrpc": "2.0", "id": request_id, "result": None}

            elif method == "tools/list":
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"tools": self.agent_adapter.get_tools_list()}
                }

            elif method == "tools/call":
                # Tool 调用 - 需要异步处理并发送结果到 SSE
                asyncio.create_task(
                    self._handle_tool_call_async(session, request_id, params)
                )
                # 立即返回空结果，实际结果通过 SSE 发送
                return {"jsonrpc": "2.0", "id": request_id, "result": None}

            elif method == "resources/list":
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"resources": self.agent_adapter.get_resources_list()}
                }

            elif method == "resources/read":
                uri = params.get("uri", "")
                resource = await self.agent_adapter.read_resource(uri)
                if resource:
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": resource
                    }
                else:
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -32602, "message": f"Resource not found: {uri}"}
                    }

            elif method == "ping":
                return {"jsonrpc": "2.0", "id": request_id, "result": {}}

            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"}
                }

        except Exception as e:
            logger.exception(f"Error handling method: {method}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32603, "message": f"Internal error: {str(e)}"}
            }

    async def _handle_initialize(
        self,
        session: "MCPSession",
        request_id: Any,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """处理 initialize 请求"""
        client_info = params.get("clientInfo", {})
        session.client_info.update(client_info)

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": True},
                    "resources": {"subscribe": False, "listChanged": True}
                },
                "serverInfo": self.agent_adapter.get_server_info()
            }
        }

    async def _handle_tool_call_async(
        self,
        session: "MCPSession",
        request_id: Any,
        params: Dict[str, Any]
    ) -> None:
        """异步处理 Tool 调用"""
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        try:
            async for event in self.agent_adapter.call_tool(
                session.session_id,
                tool_name,
                arguments
            ):
                if event["type"] == "result":
                    # 最终结果
                    result = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "content": event["content"]
                        }
                    }
                    await session.send_message(result)

                elif event["type"] == "progress":
                    # 进度更新
                    progress_notification = {
                        "jsonrpc": "2.0",
                        "method": "notifications/progress",
                        "params": {
                            "progress": event.get("progress", 0),
                            "message": event.get("message", "")
                        }
                    }
                    await session.send_message(progress_notification)

                elif event["type"] == "error":
                    # 错误
                    error_result = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32603,
                            "message": event.get("error", "Unknown error")
                        }
                    }
                    await session.send_message(error_result)

        except Exception as e:
            logger.exception(f"Tool call failed: {tool_name}")
            error_result = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": f"Tool execution failed: {str(e)}"
                }
            }
            await session.send_message(error_result)

    def _format_sse_event(self, event_type: str, data: str) -> str:
        """格式化 SSE 事件"""
        return f"event: {event_type}\ndata: {data}\n\n"

    async def _cleanup_session(self, session_id: str) -> None:
        """清理会话"""
        await self.close_session(session_id)

    async def shutdown(self) -> None:
        """关闭服务端"""
        session_ids = list(self._sessions.keys())
        for session_id in session_ids:
            await self.close_session(session_id)
        logger.info("MCP SSE Server shutdown complete")


class MCPSession:
    """MCP 会话"""

    def __init__(
        self,
        session_id: str,
        server: MCPSSEServer,
        client_info: Optional[Dict[str, Any]] = None
    ):
        self.session_id = session_id
        self.server = server
        self.client_info = client_info or {}
        self.is_active = True
        self._message_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
        self._created_at = datetime.now()

    async def send_message(self, message: Dict[str, Any]) -> None:
        """发送消息到客户端"""
        if self.is_active:
            await self._message_queue.put(message)

    async def get_message(self, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """获取消息（非阻塞）"""
        if not self.is_active:
            return None

        try:
            return await asyncio.wait_for(
                self._message_queue.get(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            return None

    async def close(self) -> None:
        """关闭会话"""
        self.is_active = False
        # 清空消息队列
        while not self._message_queue.empty():
            try:
                self._message_queue.get_nowait()
            except asyncio.QueueEmpty:
                break


# ===== FastAPI Router Factory =====

def create_mcp_router(agent_runtime: Any) -> Any:
    """
    创建 FastAPI MCP Router

    使用示例:
        from fastapi import FastAPI
        from app.agent.mcp_sse_server import create_mcp_router

        app = FastAPI()
        mcp_router = create_mcp_router(agent_runtime)
        app.include_router(mcp_router, prefix="/mcp")
    """
    from fastapi import APIRouter
    from .mcp_agent_adapter import MCPAgentAdapter

    adapter = MCPAgentAdapter(agent_runtime)
    mcp_server = MCPSSEServer(adapter)

    router = APIRouter()

    @router.get("/sse")
    async def mcp_sse_endpoint(request: Request):
        """MCP SSE 连接端点"""
        return await mcp_server.handle_sse(request)

    @router.post("/messages")
    async def mcp_messages_endpoint(request: Request):
        """MCP 消息接收端点"""
        return await mcp_server.handle_message(request)

    @router.get("/health")
    async def mcp_health():
        """MCP 健康检查"""
        return {
            "status": "ok",
            "server": "typoagent-mcp-server",
            "version": "1.0.0",
            "sessions": len(mcp_server._sessions),
            "tools": len(adapter.tools),
            "resources": len(adapter.resources)
        }

    # 附加服务器实例到 router，用于关闭时清理
    router.mcp_server = mcp_server  # type: ignore

    return router
