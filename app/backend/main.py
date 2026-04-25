"""
Typo Master Backend API Server

Product-facing API for conversation, capabilities, and agent workflow control.
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from app.agent.runtime import WorkflowRunRequest, agent_runtime
from app.backend.storage import (
    ConversationNotFoundError,
    MySQLStorage,
    WorkflowTaskNotFoundError,
)

from app.backend.auth import (
    get_github_auth_url,
    exchange_github_code,
    get_github_user_info,
    create_jwt_token,
    get_current_user,
    require_login,
)

# MCP SSE Server
_mcp_router: Optional[Any] = None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class HealthResponse(BaseModel):
    ok: bool
    service: str
    timestamp: str


class ConversationCreateResponse(BaseModel):
    conversation_id: str
    created_at: str


class ChatMessageRequest(BaseModel):
    message: str = Field(min_length=1)


class ChatMessageRecord(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    created_at: str


class ChatMessageResponse(BaseModel):
    success: bool
    mode: str
    reply: str
    conversation_id: str
    warning: Optional[str] = None
    action_result: Optional[Dict[str, Any]] = None
    model: Optional[str] = None


class RunWorkflowRequest(BaseModel):
    workflow: Literal["single_project", "batch_projects"] = "single_project"
    create_pr: bool = False
    owner: Optional[str] = None
    repo: Optional[str] = None
    days: int = Field(default=30, ge=1, description="Number of days must be at least 1")
    min_stars: int = Field(default=100, ge=0, description="Minimum stars must be non-negative")
    limit: int = Field(default=5, ge=1, le=100, description="Limit must be between 1 and 100")


class WorkflowTaskResponse(BaseModel):
    task_id: str
    status: str
    created_at: str
    updated_at: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class SkillExecuteRequest(BaseModel):
    skill_name: str = Field(min_length=1, max_length=256, description="Skill name must be between 1 and 256 characters")
    params: Dict[str, Any] = Field(default_factory=dict)
    skill: Optional[Dict[str, Any]] = None
    conversation_id: str = ""

    @field_validator('skill_name')
    @classmethod
    def validate_skill_name(cls, v: str) -> str:
        """Validate skill name doesn't contain dangerous characters."""
        # Check for potential script injection
        if '<' in v or '>' in v:
            raise ValueError('skill_name cannot contain angle brackets')
        # Check for command injection patterns
        if ';' in v and ('rm' in v.lower() or 'drop' in v.lower() or 'delete' in v.lower()):
            raise ValueError('skill_name contains potentially dangerous characters')
        return v


class SkillExecuteResponse(BaseModel):
    success: bool
    skill_name: str
    mode: str
    message: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    executed_at: str


class SkillUpsertRequest(BaseModel):
    skill: Dict[str, Any] = Field(default_factory=dict)


class MCPServerUpsertRequest(BaseModel):
    server: Dict[str, Any] = Field(default_factory=dict)


class MCPExecuteRequest(BaseModel):
    server_id: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    arguments: Dict[str, Any] = Field(default_factory=dict)


class MCPCatalogInstallRequest(BaseModel):
    overrides: Dict[str, Any] = Field(default_factory=dict)


class SQLExecuteRequest(BaseModel):
    database: str = Field(min_length=1, max_length=256)
    query: str = Field(min_length=1)
    args: List[Any] = Field(default_factory=list)
    read_only: bool = True
    max_rows: int = Field(default=200, ge=1, le=10000)

    @field_validator('database')
    @classmethod
    def validate_database_name(cls, v: str) -> str:
        """Validate database name doesn't contain dangerous characters."""
        import re
        # Check for path traversal
        if '..' in v or '/' in v or '\\' in v:
            raise ValueError('database name cannot contain path characters')
        # Check for SQL injection patterns
        if ';' in v or '--' in v or '/*' in v:
            raise ValueError('database name cannot contain SQL special characters')
        # Check for HTML/script tags
        if '<' in v or '>' in v:
            raise ValueError('database name cannot contain angle brackets')
        # Check for valid database name characters (alphanumeric, underscore, hyphen)
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('database name can only contain letters, numbers, underscores, and hyphens')
        return v


class PermissionsUpdateRequest(BaseModel):
    permissions: Dict[str, Any] = Field(default_factory=dict)


app = FastAPI(
    title="Typo Master API",
    version="0.2.0",
    description="Conversation + Agent control API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


_storage = MySQLStorage.from_env()
_task_lock = asyncio.Lock()

app.state.storage = _storage


@app.get("/api/v1/auth/github/url")
async def github_auth_url() -> Dict[str, Any]:
    """Return GitHub OAuth authorization URL for frontend to redirect."""
    state = str(uuid.uuid4())
    url = get_github_auth_url(state)
    return {"url": url, "state": state}


@app.get("/api/v1/auth/github/callback")
async def github_auth_callback(code: str, state: str = "") -> Dict[str, Any]:
    """Handle GitHub OAuth callback: exchange code, create/get user, return JWT."""
    access_token = await exchange_github_code(code)
    github_info = await get_github_user_info(access_token)
    now_iso = utc_now_iso()
    user = await asyncio.to_thread(
        _storage.get_or_create_user,
        str(uuid.uuid4()),
        github_info["github_id"],
        github_info["username"],
        github_info["display_name"],
        github_info["avatar_url"],
        github_info.get("email"),
        github_info.get("bio"),
        now_iso,
    )
    jwt_token = create_jwt_token(user["user_id"], user["username"])
    return {
        "success": True,
        "token": jwt_token,
        "user": user,
    }


@app.get("/api/v1/auth/me")
async def get_me(current_user: Optional[Dict[str, Any]] = Depends(get_current_user)) -> Dict[str, Any]:
    """Return current user info if logged in, or anonymous status."""
    if current_user is None:
        return {"authenticated": False, "user": None}
    return {"authenticated": True, "user": current_user}


@app.post("/api/v1/auth/logout")
async def logout() -> Dict[str, Any]:
    """Logout endpoint (client-side token removal)."""
    return {"success": True, "message": "Logged out"}


@app.on_event("startup")
async def startup_event() -> None:
    global _mcp_router
    await asyncio.to_thread(_storage.initialize)
    await agent_runtime.initialize()
    # Initialize MCP SSE Server
    try:
        from app.agent.mcp_sse_server import create_mcp_router
        _mcp_router = create_mcp_router(agent_runtime)
        app.include_router(_mcp_router, prefix="/mcp")
        print("MCP SSE Server initialized at /mcp")
    except Exception as e:
        print(f"Failed to initialize MCP SSE Server: {e}")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    global _mcp_router
    await agent_runtime.shutdown()
    # Shutdown MCP SSE Server
    if _mcp_router and hasattr(_mcp_router, 'mcp_server'):
        await _mcp_router.mcp_server.shutdown()


@app.get("/api/v1/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(ok=True, service="typomaster-backend", timestamp=utc_now_iso())


@app.get("/api/v1/capabilities")
async def capabilities() -> Dict[str, Any]:
    caps = await agent_runtime.get_capabilities()
    # Add MCP SSE endpoint info
    caps["mcp_sse"] = {
        "enabled": True,
        "endpoint": "/mcp/sse",
        "messages_endpoint": "/mcp/messages",
        "description": "MCP SSE Server for external clients to call TypoAgent"
    }
    return caps


@app.get("/api/v1/skills")
async def list_skills() -> Dict[str, Any]:
    skills = await agent_runtime.list_skills()
    return {"success": True, "skills": skills}


@app.put("/api/v1/skills/{skill_name}")
async def upsert_skill(skill_name: str, request: SkillUpsertRequest) -> Dict[str, Any]:
    result = await agent_runtime.upsert_skill(skill_name, request.skill)
    if not result.get("success", False):
        raise HTTPException(status_code=400, detail=result.get("error", "upsert skill failed"))
    return result


@app.delete("/api/v1/skills/{skill_name}")
async def delete_skill(skill_name: str) -> Dict[str, Any]:
    result = await agent_runtime.delete_skill(skill_name)
    if not result.get("success", False):
        raise HTTPException(status_code=400, detail=result.get("error", "delete skill failed"))
    return result


@app.get("/api/v1/mcp/servers")
async def list_mcp_servers() -> Dict[str, Any]:
    return await agent_runtime.list_mcp_servers()


@app.get("/api/v1/mcp/catalog")
async def list_mcp_catalog(q: str = "") -> Dict[str, Any]:
    return await agent_runtime.list_mcp_catalog(query=q)


@app.post("/api/v1/mcp/catalog/{catalog_id}/install")
async def install_mcp_catalog(catalog_id: str, request: MCPCatalogInstallRequest) -> Dict[str, Any]:
    result = await agent_runtime.install_mcp_from_catalog(catalog_id, overrides=request.overrides)
    if not result.get("success", False):
        raise HTTPException(status_code=400, detail=result.get("error", "install mcp catalog failed"))
    return result


@app.put("/api/v1/mcp/servers/{server_id}")
async def upsert_mcp_server(server_id: str, request: MCPServerUpsertRequest) -> Dict[str, Any]:
    result = await agent_runtime.upsert_mcp_server(server_id, request.server)
    if not result.get("success", False):
        raise HTTPException(status_code=400, detail=result.get("error", "upsert mcp server failed"))
    return result


@app.delete("/api/v1/mcp/servers/{server_id}")
async def delete_mcp_server(server_id: str) -> Dict[str, Any]:
    result = await agent_runtime.delete_mcp_server(server_id)
    if not result.get("success", False):
        raise HTTPException(status_code=400, detail=result.get("error", "delete mcp server failed"))
    return result


@app.post("/api/v1/mcp/servers/{server_id}/probe")
async def probe_mcp_server(server_id: str) -> Dict[str, Any]:
    result = await agent_runtime.probe_mcp_server(server_id)
    if not result.get("success", False):
        raise HTTPException(status_code=400, detail=result.get("error", "probe mcp server failed"))
    return result


@app.post("/api/v1/mcp/execute")
async def execute_mcp_tool(request: MCPExecuteRequest) -> Dict[str, Any]:
    result = await agent_runtime.execute_mcp_tool(
        server_id=request.server_id,
        tool_name=request.tool_name,
        arguments=request.arguments,
    )
    if not result.get("success", False):
        raise HTTPException(status_code=400, detail=result.get("error", "mcp execution failed"))
    return result


@app.post("/api/v1/sql/execute")
async def execute_sql(request: SQLExecuteRequest) -> Dict[str, Any]:
    result = await agent_runtime.execute_sql(
        database=request.database,
        query=request.query,
        args=request.args,
        read_only=request.read_only,
        max_rows=request.max_rows,
    )
    if not result.get("success", False):
        raise HTTPException(status_code=400, detail=result.get("error", "sql execution failed"))
    return result


@app.get("/api/v1/permissions")
async def get_permissions() -> Dict[str, Any]:
    return agent_runtime.get_permissions()


@app.put("/api/v1/permissions")
async def update_permissions(request: PermissionsUpdateRequest) -> Dict[str, Any]:
    result = agent_runtime.update_permissions(request.permissions)
    if not result.get("success", False):
        raise HTTPException(status_code=400, detail=result.get("error", "update permissions failed"))
    return result


@app.post("/api/v1/conversations", response_model=ConversationCreateResponse)
async def create_conversation(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user),
) -> ConversationCreateResponse:
    if current_user is None:
        raise HTTPException(status_code=401, detail="Login required to create conversations")
    conversation_id = str(uuid.uuid4())
    created_at = utc_now_iso()
    await asyncio.to_thread(_storage.create_conversation, conversation_id, created_at)
    return ConversationCreateResponse(
        conversation_id=conversation_id,
        created_at=created_at,
    )


@app.get("/api/v1/conversations/{conversation_id}/messages")
async def list_messages(conversation_id: str) -> Dict[str, Any]:
    messages = await asyncio.to_thread(_storage.get_conversation_messages, conversation_id)
    if messages is None:
        raise HTTPException(status_code=404, detail="conversation not found")
    return {
        "conversation_id": conversation_id,
        "messages": messages,
    }


@app.post(
    "/api/v1/conversations/{conversation_id}/messages",
    response_model=ChatMessageResponse,
)
async def send_message(
    conversation_id: str,
    request: ChatMessageRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user),
) -> ChatMessageResponse:
    # 检查登录状态
    if current_user is None:
        raise HTTPException(status_code=401, detail="Login required to send messages")
    messages = await asyncio.to_thread(_storage.get_conversation_messages, conversation_id)
    if messages is None:
        raise HTTPException(status_code=404, detail="conversation not found")

    user_record = ChatMessageRecord(
        role="user",
        content=request.message,
        created_at=utc_now_iso(),
    )
    try:
        await asyncio.to_thread(
            _storage.append_message,
            conversation_id,
            user_record.role,
            user_record.content,
            user_record.created_at,
        )
    except ConversationNotFoundError:
        raise HTTPException(status_code=404, detail="conversation not found")

    runtime_result = await agent_runtime.chat(
        request.message,
        [*messages, user_record.model_dump()],
        conversation_id=conversation_id,
    )
    if not runtime_result.get("success", False):
        raise HTTPException(status_code=500, detail=runtime_result.get("error", "chat failed"))

    reply_text = runtime_result.get("reply", "")
    assistant_record = ChatMessageRecord(
        role="assistant",
        content=reply_text,
        created_at=utc_now_iso(),
    )
    try:
        await asyncio.to_thread(
            _storage.append_message,
            conversation_id,
            assistant_record.role,
            assistant_record.content,
            assistant_record.created_at,
        )
    except ConversationNotFoundError:
        raise HTTPException(status_code=404, detail="conversation not found")

    return ChatMessageResponse(
        success=True,
        mode=runtime_result.get("mode", "fallback"),
        reply=reply_text,
        conversation_id=conversation_id,
        warning=runtime_result.get("warning"),
        action_result=runtime_result.get("action_result"),
        model=runtime_result.get("model"),
    )


@app.post("/api/v1/agent/workflows", response_model=WorkflowTaskResponse)
async def run_workflow(request: RunWorkflowRequest) -> WorkflowTaskResponse:
    if request.workflow == "single_project":
        if not request.owner or not request.repo:
            raise HTTPException(status_code=422, detail="owner and repo are required for single_project workflow")

    task_id = str(uuid.uuid4())
    created_at = utc_now_iso()
    async with _task_lock:
        await asyncio.to_thread(
            _storage.create_workflow_task,
            task_id,
            "queued",
            created_at,
            created_at,
            None,
            None,
        )

    asyncio.create_task(_execute_workflow_task(task_id, request))
    return WorkflowTaskResponse(
        task_id=task_id,
        status="queued",
        created_at=created_at,
        updated_at=created_at,
        result=None,
        error=None,
    )


@app.post("/api/v1/skills/execute", response_model=SkillExecuteResponse)
async def execute_skill(request: SkillExecuteRequest) -> SkillExecuteResponse:
    result = await agent_runtime.execute_skill(
        skill_name=request.skill_name,
        params=request.params,
        skill_definition=request.skill,
        conversation_id=request.conversation_id,
    )

    # Check for permission/security errors
    error_msg = result.get("error", "")
    if error_msg and "permission denied" in error_msg.lower():
        raise HTTPException(status_code=403, detail=error_msg)

    return SkillExecuteResponse(
        success=bool(result.get("success", False)),
        skill_name=request.skill_name,
        mode=str(result.get("mode", "skill")),
        message=str(result.get("message", "")),
        result=result.get("result") if isinstance(result.get("result"), dict) else None,
        error=result.get("error"),
        executed_at=utc_now_iso(),
    )


@app.get("/api/v1/agent/workflows/{task_id}", response_model=WorkflowTaskResponse)
async def get_workflow_task(task_id: str) -> WorkflowTaskResponse:
    task = await asyncio.to_thread(_storage.get_workflow_task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return _serialize_task(task_id, task)


async def _execute_workflow_task(task_id: str, request: RunWorkflowRequest) -> None:
    try:
        await asyncio.to_thread(
            _storage.update_workflow_task,
            task_id,
            "running",
            utc_now_iso(),
            None,
            None,
        )
    except WorkflowTaskNotFoundError:
        return

    try:
        result = await agent_runtime.run_workflow(
            WorkflowRunRequest(
                workflow=request.workflow,
                create_pr=request.create_pr,
                owner=request.owner,
                repo=request.repo,
                days=request.days,
                min_stars=request.min_stars,
                limit=request.limit,
            )
        )
        status = "succeeded" if result.get("success", False) else "failed"
        error = None if status == "succeeded" else result.get("error", "workflow failed")
        await asyncio.to_thread(
            _storage.update_workflow_task,
            task_id,
            status,
            utc_now_iso(),
            result,
            error,
        )
    except Exception as exc:
        await asyncio.to_thread(
            _storage.update_workflow_task,
            task_id,
            "failed",
            utc_now_iso(),
            {"success": False, "error": str(exc)},
            str(exc),
        )


def _serialize_task(task_id: str, task: Dict[str, Any]) -> WorkflowTaskResponse:
    result = task.get("result")
    error = task.get("error")
    return WorkflowTaskResponse(
        task_id=task_id,
        status=str(task.get("status", "queued")),
        created_at=str(task.get("created_at", utc_now_iso())),
        updated_at=str(task.get("updated_at", utc_now_iso())),
        result=result if isinstance(result, dict) else None,
        error=str(error) if error is not None else None,
    )
