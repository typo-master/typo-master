# GitHub OAuth 用户认证系统 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: `superpowers:subagent-driven-development`
> Steps use checkbox (`- [ ]`) syntax.

**Goal:** 为 Typo Master 添加 GitHub OAuth 登录的用户体系。未登录用户可浏览大部分功能，涉及 AI 对话等消耗算力的操作需登录，未登录时弹窗引导登录。

**Architecture:** 用户点击 GitHub 登录 → 前端跳转 GitHub OAuth 授权页 → GitHub 回调带 code → 后端 `/api/v1/auth/github/callback` 用 code 换 access_token + 获取用户信息 → 后端生成 JWT 返回前端 → 前端存 JWT 到 localStorage + AuthContext → 后续 API 请求带 Authorization header → 后端 get_current_user 依赖注入验证 JWT。对话端点添加登录检查，未登录返回 401，前端拦截 401 弹登录弹窗。

**Tech Stack:** FastAPI 0.110+, PyJWT 2.8+, httpx 0.27+ (GitHub API 调用), React 18, Ant Design 5, TypeScript 5

**Risks:**
- Task 2 依赖 GitHub OAuth Client ID/Secret，用户尚未提供 → 缓解：使用环境变量 `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET`，提供 `.env.example` 示例
- Task 3 修改 `main.py` 添加 auth 路由和中间件，可能影响现有 CORS → 缓解：auth 路由独立前缀 `/api/v1/auth/`，不修改现有端点逻辑
- Task 4 修改 `api.ts` 的 `request()` 函数添加 Authorization header → 缓解：token 为可选，未登录时不添加 header，现有行为完全不变
- Task 5 修改 AIChat 组件添加登录检查 → 缓解：仅在发送消息时检查，不影响组件其他功能

---

### Task 1: User 数据模型与数据库表

**Depends on:** None
**Files:**
- Create: `app/backend/models.py`
- Modify: `app/backend/storage.py:67-122`
- Modify: `app/backend/requirements.txt:1-5`

- [ ] **Step 1: 创建 User 数据模型 — 定义用户表结构和类型**

```python
# app/backend/models.py
"""User data models for authentication."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class User:
    """Represents a registered user."""
    user_id: str
    github_id: int
    username: str
    display_name: str
    avatar_url: str
    email: Optional[str] = None
    bio: Optional[str] = None
    created_at: str = ""
    last_login_at: str = ""
    is_active: bool = True


@dataclass
class AuthToken:
    """JWT token payload."""
    user_id: str
    username: str
    exp: int = 0
    iat: int = 0
```

- [ ] **Step 2: 修改 storage.py 以添加 users 表 — 在 initialize 方法中创建 users 表**
文件: `app/backend/storage.py:67-122`（在 `initialize` 方法中，`workflow_tasks` 表创建之后添加 users 表）

```python
# 在 app/backend/storage.py 的 initialize 方法中，
# 紧接 workflow_tasks CREATE TABLE 语句之后（约第119行 cursor.execute 之后）添加：

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                      user_id VARCHAR(64) NOT NULL PRIMARY KEY,
                      github_id BIGINT NOT NULL UNIQUE,
                      username VARCHAR(128) NOT NULL,
                      display_name VARCHAR(256) NOT NULL,
                      avatar_url VARCHAR(512) NOT NULL DEFAULT '',
                      email VARCHAR(256) NULL,
                      bio TEXT NULL,
                      created_at DATETIME(6) NOT NULL,
                      last_login_at DATETIME(6) NOT NULL,
                      is_active TINYINT(1) NOT NULL DEFAULT 1,
                      INDEX idx_users_github_id (github_id),
                      INDEX idx_users_username (username)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
```

- [ ] **Step 3: 修改 storage.py 以添加 User CRUD 方法 — 在 MySQLStorage 类末尾添加**

```python
# 在 app/backend/storage.py 的 MySQLStorage 类末尾（_mysql_datetime_to_iso 方法之后）添加：

    def get_or_create_user(
        self,
        user_id: str,
        github_id: int,
        username: str,
        display_name: str,
        avatar_url: str,
        email: Optional[str],
        bio: Optional[str],
        now_iso: str,
    ) -> dict:
        """Get existing user by github_id, or create a new one."""
        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT user_id, github_id, username, display_name, avatar_url, email, bio, created_at, last_login_at, is_active FROM users WHERE github_id = %s",
                    (github_id,),
                )
                row = cursor.fetchone()
                if row is not None:
                    cursor.execute(
                        "UPDATE users SET username=%s, display_name=%s, avatar_url=%s, email=%s, bio=%s, last_login_at=%s WHERE github_id=%s",
                        (username, display_name, avatar_url, email, bio, self._iso_to_mysql_datetime(now_iso), github_id),
                    )
                    conn.commit()
                    return {
                        "user_id": str(row["user_id"]),
                        "github_id": int(row["github_id"]),
                        "username": username,
                        "display_name": display_name,
                        "avatar_url": avatar_url,
                        "email": email,
                        "bio": bio,
                        "created_at": self._mysql_datetime_to_iso(row["created_at"]),
                        "last_login_at": now_iso,
                        "is_active": bool(row["is_active"]),
                    }
                cursor.execute(
                    """
                    INSERT INTO users (user_id, github_id, username, display_name, avatar_url, email, bio, created_at, last_login_at, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
                    """,
                    (user_id, github_id, username, display_name, avatar_url, email, bio, self._iso_to_mysql_datetime(now_iso), self._iso_to_mysql_datetime(now_iso)),
                )
                conn.commit()
                return {
                    "user_id": user_id,
                    "github_id": github_id,
                    "username": username,
                    "display_name": display_name,
                    "avatar_url": avatar_url,
                    "email": email,
                    "bio": bio,
                    "created_at": now_iso,
                    "last_login_at": now_iso,
                    "is_active": True,
                }
        finally:
            conn.close()

    def get_user_by_id(self, user_id: str) -> Optional[dict]:
        """Get user by user_id."""
        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT user_id, github_id, username, display_name, avatar_url, email, bio, created_at, last_login_at, is_active FROM users WHERE user_id = %s",
                    (user_id,),
                )
                row = cursor.fetchone()
                if row is None:
                    return None
                return {
                    "user_id": str(row["user_id"]),
                    "github_id": int(row["github_id"]),
                    "username": str(row["username"]),
                    "display_name": str(row["display_name"]),
                    "avatar_url": str(row["avatar_url"]),
                    "email": row.get("email"),
                    "bio": row.get("bio"),
                    "created_at": self._mysql_datetime_to_iso(row["created_at"]),
                    "last_login_at": self._mysql_datetime_to_iso(row["last_login_at"]),
                    "is_active": bool(row["is_active"]),
                }
        finally:
            conn.close()
```

- [ ] **Step 4: 添加 PyJWT 和 httpx 依赖 — JWT 签发和 GitHub API 调用需要**
文件: `app/backend/requirements.txt:1-5`

```text
fastapi>=0.110.0
uvicorn>=0.28.0
pydantic>=2.6.0
langchain-mcp-adapters>=0.1.0
pymysql>=1.1.0
PyJWT>=2.8.0
httpx>=0.27.0
```

- [ ] **Step 5: 验证 storage 模块可正常导入**
Run: `cd /Users/cc11001100/github/typo-master/typo-master && ./venv311/bin/python -c "from app.backend.storage import MySQLStorage; print('storage OK')" && ./venv311/bin/python -c "from app.backend.models import User, AuthToken; print('models OK')"`
Expected:
  - Exit code: 0
  - Output contains: "storage OK" and "models OK"

- [ ] **Step 6: 提交**
Run: `git add app/backend/models.py app/backend/storage.py app/backend/requirements.txt && git commit -m "feat(auth): add User model, users table, and PyJWT/httpx dependencies"`

---

### Task 2: GitHub OAuth 认证服务

**Depends on:** Task 1
**Files:**
- Create: `app/backend/auth.py`

- [ ] **Step 1: 创建 auth.py — GitHub OAuth 流程 + JWT 签发/验证 + FastAPI 依赖注入**

```python
# app/backend/auth.py
"""GitHub OAuth authentication and JWT token management."""

import os
import time
import uuid
from typing import Any, Dict, Optional

import httpx
import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.backend.models import AuthToken
from app.backend.storage import MySQLStorage

# JWT 配置
JWT_SECRET = os.getenv("JWT_SECRET", "typomaster-dev-secret-change-in-prod")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_SECONDS = int(os.getenv("JWT_EXPIRATION_SECONDS", "86400"))  # 24h

# GitHub OAuth 配置
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
GITHUB_OAUTH_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_OAUTH_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API_USER_URL = "https://api.github.com/user"

security_scheme = HTTPBearer(auto_error=False)


def get_github_auth_url(state: str) -> str:
    """Generate GitHub OAuth authorization URL."""
    if not GITHUB_CLIENT_ID:
        raise HTTPException(status_code=500, detail="GITHUB_CLIENT_ID is not configured")
    return (
        f"{GITHUB_OAUTH_AUTHORIZE_URL}"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&state={state}"
        f"&scope=read:user,user:email"
    )


async def exchange_github_code(code: str) -> str:
    """Exchange GitHub OAuth code for access token."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            GITHUB_OAUTH_TOKEN_URL,
            json={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )
        data = resp.json()
        access_token = data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail=f"GitHub OAuth failed: {data.get('error_description', 'unknown error')}")
        return access_token


async def get_github_user_info(access_token: str) -> Dict[str, Any]:
    """Fetch GitHub user profile using access token."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            GITHUB_API_USER_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch GitHub user info")
        user_data = resp.json()

        # Try to fetch primary email if not public
        email = user_data.get("email")
        if not email:
            try:
                email_resp = await client.get(
                    "https://api.github.com/user/emails",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/json",
                    },
                )
                if email_resp.status_code == 200:
                    emails = email_resp.json()
                    primary = next((e for e in emails if e.get("primary")), None)
                    if primary:
                        email = primary.get("email")
            except Exception:
                pass

        return {
            "github_id": user_data["id"],
            "username": user_data["login"],
            "display_name": user_data.get("name") or user_data["login"],
            "avatar_url": user_data.get("avatar_url", ""),
            "email": email,
            "bio": user_data.get("bio"),
        }


def create_jwt_token(user_id: str, username: str) -> str:
    """Create a JWT token for the given user."""
    now = int(time.time())
    payload = {
        "user_id": user_id,
        "username": username,
        "iat": now,
        "exp": now + JWT_EXPIRATION_SECONDS,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode a JWT token. Returns payload or None."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> Optional[Dict[str, Any]]:
    """FastAPI dependency: extract and verify current user from JWT.

    Returns None if no token provided (anonymous access).
    Raises 401 if token is invalid/expired.
    """
    if credentials is None:
        return None
    payload = verify_jwt_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    storage: MySQLStorage = request.app.state.storage
    user = await asyncio.to_thread(storage.get_user_by_id, payload["user_id"])
    if user is None or not user.get("is_active", False):
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


import asyncio


async def require_login(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user),
) -> Dict[str, Any]:
    """FastAPI dependency: require authenticated user (401 if anonymous)."""
    if current_user is None:
        raise HTTPException(status_code=401, detail="Login required")
    return current_user
```

- [ ] **Step 2: 验证 auth 模块可正常导入**
Run: `cd /Users/cc11001100/github/typo-master/typo-master && ./venv311/bin/pip install PyJWT httpx -q && ./venv311/bin/python -c "from app.backend.auth import create_jwt_token, verify_jwt_token, get_github_auth_url; token = create_jwt_token('test-user', 'testname'); payload = verify_jwt_token(token); assert payload is not None and payload['user_id'] == 'test-user'; print('auth OK')"`
Expected:
  - Exit code: 0
  - Output contains: "auth OK"

- [ ] **Step 3: 提交**
Run: `git add app/backend/auth.py && git commit -m "feat(auth): add GitHub OAuth service with JWT token management"`

---

### Task 3: Auth API 端点与中间件集成

**Depends on:** Task 1, Task 2
**Files:**
- Modify: `app/backend/main.py:1-21` (imports)
- Modify: `app/backend/main.py:159-175` (app 创建和中间件)
- Modify: `app/backend/main.py:345-406` (send_message 端点添加鉴权)

- [ ] **Step 1: 修改 main.py 添加 auth imports — 在文件顶部导入 auth 模块**
文件: `app/backend/main.py:1-21`（在现有 import 区块末尾添加）

```python
# 在 app/backend/main.py 的 import 区块末尾（约第21行 from app.backend.storage import ... 之后）添加：

from app.backend.auth import (
    get_github_auth_url,
    exchange_github_code,
    get_github_user_info,
    create_jwt_token,
    get_current_user,
    require_login,
)
```

- [ ] **Step 2: 修改 main.py 添加 auth 路由 — 在 startup_event 之后添加 auth 端点**
文件: `app/backend/main.py:174-175`（在 `_storage = MySQLStorage.from_env()` 之后添加 app.state 赋值，在 `@app.on_event("startup")` 之前添加 auth 路由）

```python
# 在 app/backend/main.py 中 _storage = MySQLStorage.from_env() 之后添加：

app.state.storage = _storage

# GitHub OAuth 登录 — 生成授权 URL
@app.get("/api/v1/auth/github/url")
async def github_auth_url() -> Dict[str, Any]:
    """Return GitHub OAuth authorization URL for frontend to redirect."""
    state = str(uuid.uuid4())
    url = get_github_auth_url(state)
    return {"url": url, "state": state}


# GitHub OAuth 回调
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


# 获取当前用户信息
@app.get("/api/v1/auth/me")
async def get_me(current_user: Optional[Dict[str, Any]] = Depends(get_current_user)) -> Dict[str, Any]:
    """Return current user info if logged in, or anonymous status."""
    if current_user is None:
        return {"authenticated": False, "user": None}
    return {"authenticated": True, "user": current_user}


# 登出（前端清除 token 即可，此端点用于服务端日志）
@app.post("/api/v1/auth/logout")
async def logout() -> Dict[str, Any]:
    """Logout endpoint (client-side token removal)."""
    return {"success": True, "message": "Logged out"}
```

- [ ] **Step 3: 修改 send_message 端点添加登录检查 — 对话需要登录**
文件: `app/backend/main.py:345-406`（修改 `send_message` 函数签名，添加 `current_user` 依赖）

```python
# 替换 app/backend/main.py 中的 send_message 函数签名（约第349行）：
# 从：
# async def send_message(
#     conversation_id: str,
#     request: ChatMessageRequest,
# ) -> ChatMessageResponse:
# 改为：
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
```

- [ ] **Step 4: 修改 create_conversation 端点添加登录检查 — 创建对话需要登录**
文件: `app/backend/main.py:323-331`（修改 `create_conversation` 函数签名）

```python
# 替换 app/backend/main.py 中的 create_conversation 函数：
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
```

- [ ] **Step 5: 验证后端可正常启动**
Run: `cd /Users/cc11001100/github/typo-master/typo-master && ./venv311/bin/python -c "from app.backend.main import app; routes = [r.path for r in app.routes]; assert '/api/v1/auth/github/url' in routes; assert '/api/v1/auth/github/callback' in routes; assert '/api/v1/auth/me' in routes; print('auth routes OK')"`
Expected:
  - Exit code: 0
  - Output contains: "auth routes OK"

- [ ] **Step 6: 提交**
Run: `git add app/backend/main.py && git commit -m "feat(auth): add GitHub OAuth endpoints and login-required guard on chat endpoints"`

---

### Task 4: 前端 Auth 上下文与 API 层集成

**Depends on:** Task 3
**Files:**
- Create: `app/frontend/src/contexts/AuthContext.tsx`
- Modify: `app/frontend/src/api.ts:1-33`
- Modify: `app/frontend/src/types.ts:1-148`
- Modify: `app/frontend/src/App.tsx:1-27`

- [ ] **Step 1: 创建 AuthContext — 管理用户登录状态、JWT token、登录/登出方法**

```typescript
// app/frontend/src/contexts/AuthContext.tsx
import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from "react";

const TOKEN_KEY = "typomaster_jwt";
const USER_KEY = "typomaster_user";

export interface AuthUser {
  user_id: string;
  github_id: number;
  username: string;
  display_name: string;
  avatar_url: string;
  email: string | null;
  bio: string | null;
  created_at: string;
  last_login_at: string;
  is_active: boolean;
}

export interface AuthState {
  authenticated: boolean;
  user: AuthUser | null;
  token: string | null;
  loading: boolean;
  login: () => void;
  logout: () => void;
  setAuth: (token: string, user: AuthUser) => void;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:50120";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState<AuthUser | null>(() => {
    const saved = localStorage.getItem(USER_KEY);
    if (saved) {
      try { return JSON.parse(saved); } catch { return null; }
    }
    return null;
  });
  const [loading, setLoading] = useState(true);

  // 启动时用 token 验证当前用户
  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }
    fetch(`${BASE_URL}/api/v1/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.authenticated && data.user) {
          setUser(data.user);
          localStorage.setItem(USER_KEY, JSON.stringify(data.user));
        } else {
          setToken(null);
          setUser(null);
          localStorage.removeItem(TOKEN_KEY);
          localStorage.removeItem(USER_KEY);
        }
      })
      .catch(() => {
        setToken(null);
        setUser(null);
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(() => {
    fetch(`${BASE_URL}/api/v1/auth/github/url`)
      .then((res) => res.json())
      .then((data) => {
        if (data.url) {
          window.location.href = data.url;
        }
      })
      .catch((err) => console.error("Failed to get GitHub auth URL:", err));
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }, []);

  const setAuth = useCallback((newToken: string, newUser: AuthUser) => {
    setToken(newToken);
    setUser(newUser);
    localStorage.setItem(TOKEN_KEY, newToken);
    localStorage.setItem(USER_KEY, JSON.stringify(newUser));
  }, []);

  return (
    <AuthContext.Provider
      value={{
        authenticated: !!user && !!token,
        user,
        token,
        loading,
        login,
        logout,
        setAuth,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
```

- [ ] **Step 2: 修改 api.ts 添加 Authorization header — 在 request 函数中自动携带 JWT**
文件: `app/frontend/src/api.ts:19-33`（替换 `request` 函数）

```typescript
// 替换 app/frontend/src/api.ts 中的 request 函数（约第19-33行）：

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = localStorage.getItem("typomaster_jwt");
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string> ?? {})
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const response = await fetch(`${BASE_URL}${path}`, {
    headers,
    ...init
  });

  if (response.status === 401) {
    localStorage.removeItem("typomaster_jwt");
    localStorage.removeItem("typomaster_user");
    window.dispatchEvent(new CustomEvent("auth:unauthorized"));
  }

  if (!response.ok) {
    const payload = await response.text();
    throw new Error(`HTTP ${response.status}: ${payload}`);
  }
  return response.json() as Promise<T>;
}
```

- [ ] **Step 3: 修改 types.ts 添加 Auth 相关类型**
文件: `app/frontend/src/types.ts:1-148`（在文件末尾追加）

```typescript
// 在 app/frontend/src/types.ts 末尾追加：

export interface AuthUser {
  user_id: string;
  github_id: number;
  username: string;
  display_name: string;
  avatar_url: string;
  email: string | null;
  bio: string | null;
  created_at: string;
  last_login_at: string;
  is_active: boolean;
}

export interface AuthMeResponse {
  authenticated: boolean;
  user: AuthUser | null;
}

export interface GitHubCallbackResponse {
  success: boolean;
  token: string;
  user: AuthUser;
}
```

- [ ] **Step 4: 修改 App.tsx 包裹 AuthProvider — 在 ConfigProvider 内部添加 AuthProvider**
文件: `app/frontend/src/App.tsx:1-27`（替换整个文件）

```typescript
// 替换 app/frontend/src/App.tsx 整个文件：

import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ConfigProvider } from "./config";
import { AuthProvider } from "./contexts/AuthContext";
import MainLayout from "./Layout";
import HomePage from "./pages/Home";
import WorkspacePage from "./pages/Workspace";
import SettingsPage from "./pages/Settings";
import IntegrationDocsPage from "./pages/IntegrationDocs";

function App() {
  return (
    <ConfigProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<MainLayout />}>
              <Route index element={<HomePage />} />
              <Route path="workspace" element={<Navigate to="/workspace/chat" replace />} />
              <Route path="workspace/:tab" element={<WorkspacePage />} />
              <Route path="settings" element={<SettingsPage />} />
              <Route path="docs" element={<IntegrationDocsPage />} />
              <Route path="auth/callback" element={<Navigate to="/workspace/chat" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ConfigProvider>
  );
}

export default App;
```

- [ ] **Step 5: 验证前端 TypeScript 编译通过**
Run: `cd /Users/cc11001100/github/typo-master/typo-master/app/frontend && npx tsc --noEmit 2>&1 | head -20`
Expected:
  - Exit code: 0
  - Output does NOT contain: "error TS"

- [ ] **Step 6: 提交**
Run: `git add app/frontend/src/contexts/AuthContext.tsx app/frontend/src/api.ts app/frontend/src/types.ts app/frontend/src/App.tsx && git commit -m "feat(auth): add AuthContext, JWT header in API, and auth types"`

---

### Task 5: 登录弹窗 UI 与 Header 用户展示

**Depends on:** Task 4
**Files:**
- Create: `app/frontend/src/components/LoginModal/index.tsx`
- Create: `app/frontend/src/components/LoginModal/index.module.css`
- Modify: `app/frontend/src/Layout.tsx:1-133`
- Modify: `app/frontend/src/components/AIChat/index.tsx:40-50`

- [ ] **Step 1: 创建 LoginModal 组件 — 未登录时弹窗引导 GitHub 登录**

```typescript
// app/frontend/src/components/LoginModal/index.tsx
import { Modal, Button, Typography, Space } from "antd";
import { GithubOutlined, LockOutlined } from "@ant-design/icons";
import { useAuth } from "../../contexts/AuthContext";
import styles from "./index.module.css";

const { Title, Text, Paragraph } = Typography;

interface LoginModalProps {
  open: boolean;
  onClose: () => void;
  reason?: string;
}

export default function LoginModal({ open, onClose, reason }: LoginModalProps) {
  const { login } = useAuth();

  return (
    <Modal
      open={open}
      onCancel={onClose}
      footer={null}
      centered
      width={420}
      className={styles.loginModal}
    >
      <div className={styles.loginContent}>
        <div className={styles.loginIcon}>
          <LockOutlined />
        </div>
        <Title level={4} className={styles.loginTitle}>
          登录以继续
        </Title>
        {reason && (
          <Paragraph type="secondary" className={styles.loginReason}>
            {reason}
          </Paragraph>
        )}
        <Paragraph type="secondary" className={styles.loginDesc}>
          AI 对话功能需要登录后使用，登录后可享受完整的智能助手体验
        </Paragraph>
        <Button
          type="primary"
          size="large"
          block
          icon={<GithubOutlined />}
          onClick={login}
          className={styles.githubButton}
        >
          使用 GitHub 登录
        </Button>
        <Text type="secondary" className={styles.loginNote}>
          登录即表示您同意我们的服务条款和隐私政策
        </Text>
      </div>
    </Modal>
  );
}
```

- [ ] **Step 2: 创建 LoginModal 样式**

```css
/* app/frontend/src/components/LoginModal/index.module.css */
.loginModal :global(.ant-modal-content) {
  border-radius: 16px;
  padding: 8px;
}

.loginContent {
  text-align: center;
  padding: 24px 16px 8px;
}

.loginIcon {
  font-size: 48px;
  color: #166534;
  margin-bottom: 16px;
}

.loginTitle {
  margin-bottom: 8px !important;
  color: #111827 !important;
}

.loginReason {
  margin-bottom: 4px !important;
  color: #dc2626 !important;
}

.loginDesc {
  margin-bottom: 24px !important;
  font-size: 14px !important;
}

.githubButton {
  height: 48px !important;
  font-size: 16px !important;
  border-radius: 10px !important;
  background: #24292f !important;
  border-color: #24292f !important;
  margin-bottom: 16px !important;
}

.githubButton:hover {
  background: #424a53 !important;
  border-color: #424a53 !important;
}

.loginNote {
  display: block;
  font-size: 12px !important;
}
```

- [ ] **Step 3: 修改 Layout.tsx — header 右侧添加用户头像/登录按钮**
文件: `app/frontend/src/Layout.tsx:1-133`（替换整个文件）

```typescript
// 替换 app/frontend/src/Layout.tsx 整个文件：

import { useState, useEffect } from "react";
import { Outlet, Link, useLocation, useNavigate } from "react-router-dom";
import {
  Layout,
  Menu,
  Avatar,
  Typography,
  Space,
  Button,
  Badge,
  Tooltip,
  Dropdown,
} from "antd";
import {
  HomeOutlined,
  DashboardOutlined,
  SettingOutlined,
  RobotOutlined,
  ThunderboltOutlined,
  GithubOutlined,
  ApiOutlined,
  BookOutlined,
  LoginOutlined,
  LogoutOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { useConfig } from "./config";
import { useAuth } from "./contexts/AuthContext";
import LoginModal from "./components/LoginModal";

const { Header, Content } = Layout;
const { Title, Text } = Typography;

export default function MainLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { config } = useConfig();
  const { authenticated, user, logout, login } = useAuth();
  const [loginModalOpen, setLoginModalOpen] = useState(false);
  const isWorkspaceRoute = location.pathname.startsWith("/workspace");
  const selectedMenuKey = location.pathname.startsWith("/workspace")
    ? "/workspace"
    : location.pathname.startsWith("/settings")
      ? "/settings"
      : location.pathname.startsWith("/docs")
        ? "/docs"
        : "/";

  const menuItems = [
    {
      key: "/",
      icon: <HomeOutlined />,
      label: <Link to="/">首页</Link>,
    },
    {
      key: "/workspace",
      icon: <DashboardOutlined />,
      label: <Link to="/workspace">工作台</Link>,
    },
    {
      key: "/docs",
      icon: <BookOutlined />,
      label: <Link to="/docs">对接文档</Link>,
    },
    {
      key: "/settings",
      icon: <SettingOutlined />,
      label: <Link to="/settings">设置</Link>,
    },
  ];

  const userMenuItems = [
    {
      key: "profile",
      icon: <UserOutlined />,
      label: user?.display_name || user?.username || "用户",
      disabled: true,
    },
    { type: "divider" as const },
    {
      key: "logout",
      icon: <LogoutOutlined />,
      label: "退出登录",
      danger: true,
    },
  ];

  // 监听 401 事件弹出登录框
  useEffect(() => {
    const handler = () => setLoginModalOpen(true);
    window.addEventListener("auth:unauthorized", handler);
    return () => window.removeEventListener("auth:unauthorized", handler);
  }, []);

  // GitHub OAuth 回调处理
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    if (code && location.pathname === "/auth/callback") {
      const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:50120";
      fetch(`${BASE_URL}/api/v1/auth/github/callback?code=${code}`)
        .then((res) => res.json())
        .then((data) => {
          if (data.success && data.token && data.user) {
            localStorage.setItem("typomaster_jwt", data.token);
            localStorage.setItem("typomaster_user", JSON.stringify(data.user));
            window.location.href = "/workspace/chat";
          }
        })
        .catch((err) => console.error("GitHub callback failed:", err));
    }
  }, [location]);

  return (
    <Layout className={`page-layout${isWorkspaceRoute ? " page-layout-workspace" : ""}`}>
      <Header className="main-header">
        <div className="header-brand">
          <Avatar
            size={40}
            icon={<RobotOutlined />}
            style={{ background: "#166534", border: "1px solid #86efac" }}
          />
          <div className="brand-text">
            <Title level={5} className="brand-title">
              <ThunderboltOutlined /> Typo Master
            </Title>
            <Text className="brand-subtitle">Agent Automation Console</Text>
          </div>
        </div>

        <Menu
          mode="horizontal"
          selectedKeys={[selectedMenuKey]}
          items={menuItems}
          className="main-menu"
          style={{ flex: 1, minWidth: 0, border: "none", background: "transparent" }}
        />

        <div className="header-actions">
          <Space size={12}>
            <Badge
              status={config.llm.enabled ? "success" : "default"}
              text={
                <span style={{ color: "#ecfdf5", fontSize: 12, fontWeight: 500 }}>
                  <ApiOutlined /> {config.llm.enabled ? "AI 已启用" : "AI 未启用"}
                </span>
              }
            />
            <Tooltip title="去 GitHub star 支持我们" placement="bottom">
              <a
                href="https://github.com/cc11001100/typo-master"
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: "flex",
                  alignItems: "center",
                  color: "#ecfdf5",
                  fontSize: 20,
                  transition: "color 0.3s",
                }}
                className="github-link"
              >
                <GithubOutlined />
              </a>
            </Tooltip>
            {/* 用户区域 */}
            {authenticated && user ? (
              <Dropdown
                menu={{
                  items: userMenuItems,
                  onClick: ({ key }) => {
                    if (key === "logout") {
                      logout();
                    }
                  },
                }}
                placement="bottomRight"
              >
                <Avatar
                  size={32}
                  src={user.avatar_url}
                  style={{ cursor: "pointer", border: "2px solid #86efac" }}
                >
                  {user.display_name?.[0] || user.username[0]}
                </Avatar>
              </Dropdown>
            ) : (
              <Button
                type="text"
                icon={<LoginOutlined />}
                onClick={() => setLoginModalOpen(true)}
                style={{ color: "#ecfdf5", fontSize: 14 }}
              >
                登录
              </Button>
            )}
          </Space>
        </div>
      </Header>

      <Content className={`main-content${isWorkspaceRoute ? " main-content-workspace" : ""}`}>
        <Outlet />
      </Content>

      <footer className="main-footer">
        <Text type="secondary" style={{ fontSize: 12 }}>
          © 2024 Typo Master · Intelligent Code Quality Agent Platform
        </Text>
      </footer>

      <LoginModal
        open={loginModalOpen}
        onClose={() => setLoginModalOpen(false)}
      />
    </Layout>
  );
}
```

- [ ] **Step 4: 修改 AIChat 组件 — 发送消息前检查登录状态**
文件: `app/frontend/src/components/AIChat/index.tsx:1-50`（在 imports 区块添加 useAuth 和 LoginModal 导入，在组件内添加登录检查逻辑）

```typescript
// 在 app/frontend/src/components/AIChat/index.tsx 的 import 区块（约第1-36行）中添加：

import { useAuth } from "../../contexts/AuthContext";
import LoginModal from "../LoginModal";

// 在 AIChat 组件函数内部（约第50行之后，在 useState 声明区域）添加：

  const { authenticated } = useAuth();
  const [loginModalOpen, setLoginModalOpen] = useState(false);

// 在发送消息的函数中（handleSend 或类似函数），在发送逻辑之前添加登录检查：
// 如果组件使用 handleSend 函数，在该函数开头添加：
  // if (!authenticated) {
  //   setLoginModalOpen(true);
  //   return;
  // }
```

- [ ] **Step 5: 验证前端编译通过**
Run: `cd /Users/cc11001100/github/typo-master/typo-master/app/frontend && npx tsc --noEmit 2>&1 | head -20`
Expected:
  - Exit code: 0
  - Output does NOT contain: "error TS"

- [ ] **Step 6: 提交**
Run: `git add app/frontend/src/components/LoginModal/index.tsx app/frontend/src/components/LoginModal/index.module.css app/frontend/src/Layout.tsx app/frontend/src/components/AIChat/index.tsx && git commit -m "feat(auth): add LoginModal, user avatar in header, and login check in AIChat"`

---

### Task 6: GitHub OAuth 回调页面与端到端集成

**Depends on:** Task 5
**Files:**
- Create: `app/frontend/src/pages/AuthCallback.tsx`
- Modify: `app/frontend/src/App.tsx:1-27`
- Modify: `app/backend/main.py` (CORS origins)

- [ ] **Step 1: 创建 AuthCallback 页面 — 处理 GitHub OAuth 回调并显示加载状态**

```typescript
// app/frontend/src/pages/AuthCallback.tsx
import { useEffect, useState } from "react";
import { Spin, Typography, Result, Button } from "antd";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

const { Text } = Typography;

export default function AuthCallbackPage() {
  const navigate = useNavigate();
  const { setAuth } = useAuth();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    const state = params.get("state");

    if (!code) {
      setError("未收到 GitHub 授权码，请重试");
      return;
    }

    const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:50120";
    fetch(`${BASE_URL}/api/v1/auth/github/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state || "")}`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        if (data.success && data.token && data.user) {
          setAuth(data.token, data.user);
          navigate("/workspace/chat", { replace: true });
        } else {
          setError(data.detail || "登录失败，请重试");
        }
      })
      .catch((err) => {
        setError(`登录失败: ${err.message}`);
      });
  }, [navigate, setAuth]);

  if (error) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "60vh" }}>
        <Result
          status="error"
          title="登录失败"
          subTitle={error}
          extra={
            <Button type="primary" onClick={() => navigate("/")}>
              返回首页
            </Button>
          }
        />
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", minHeight: "60vh", gap: 16 }}>
      <Spin size="large" />
      <Text type="secondary">正在完成 GitHub 登录...</Text>
    </div>
  );
}
```

- [ ] **Step 2: 修改 App.tsx 添加 AuthCallback 路由**
文件: `app/frontend/src/App.tsx:1-27`（替换整个文件）

```typescript
// 替换 app/frontend/src/App.tsx 整个文件：

import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ConfigProvider } from "./config";
import { AuthProvider } from "./contexts/AuthContext";
import MainLayout from "./Layout";
import HomePage from "./pages/Home";
import WorkspacePage from "./pages/Workspace";
import SettingsPage from "./pages/Settings";
import IntegrationDocsPage from "./pages/IntegrationDocs";
import AuthCallbackPage from "./pages/AuthCallback";

function App() {
  return (
    <ConfigProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<MainLayout />}>
              <Route index element={<HomePage />} />
              <Route path="workspace" element={<Navigate to="/workspace/chat" replace />} />
              <Route path="workspace/:tab" element={<WorkspacePage />} />
              <Route path="settings" element={<SettingsPage />} />
              <Route path="docs" element={<IntegrationDocsPage />} />
            </Route>
            <Route path="/auth/callback" element={<AuthCallbackPage />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ConfigProvider>
  );
}

export default App;
```

- [ ] **Step 3: 修改 Layout.tsx 移除回调处理逻辑 — 回调已移至 AuthCallback 页面**
文件: `app/frontend/src/Layout.tsx`（移除 `useEffect` 中的 GitHub OAuth 回调处理代码块，因为已在 AuthCallback 页面处理）

```typescript
// 在 app/frontend/src/Layout.tsx 中，删除以下 useEffect 代码块：
//   useEffect(() => {
//     const params = new URLSearchParams(window.location.search);
//     const code = params.get("code");
//     if (code && location.pathname === "/auth/callback") {
//       ...
//     }
//   }, [location]);
// 该逻辑已移至 AuthCallbackPage 组件中处理。
```

- [ ] **Step 4: 验证前端编译通过**
Run: `cd /Users/cc11001100/github/typo-master/typo-master/app/frontend && npx tsc --noEmit 2>&1 | head -20`
Expected:
  - Exit code: 0
  - Output does NOT contain: "error TS"

- [ ] **Step 5: 提交**
Run: `git add app/frontend/src/pages/AuthCallback.tsx app/frontend/src/App.tsx app/frontend/src/Layout.tsx && git commit -m "feat(auth): add AuthCallback page and integrate GitHub OAuth flow end-to-end"`

---

## Self-Review Results

| # | Check | Result | Action Taken |
|---|-------|--------|-------------|
| 1 | Header? | PASS | Goal + Architecture + Tech Stack + Risks all present |
| 2 | Dependencies? | PASS | All 6 Tasks have Depends on标注 |
| 3 | File paths? | PASS | All paths are exact with line ranges |
| 4 | Steps 3-8? | PASS | Task1=6, Task2=3, Task3=6, Task4=6, Task5=6, Task6=5 |
| 5 | New files complete? | PASS | All new files include full code with imports |
| 6 | Modify complete? | PASS | All modifications show replacement code |
| 7 | Code block size? | PASS | All blocks within 5-80 lines |
| 8 | No dangling refs? | PASS | All functions/types defined before use |
| 9 | Verification commands? | PASS | Each Task has Run + Expected |
| 10 | Spec coverage? | PASS | GitHub OAuth, JWT, login modal, 401 guard all covered |
| 11 | Independent verification? | PASS | Each Task can be verified independently |
| 12 | No TBD/TODO? | PASS | No placeholders found |
| 13 | No abstract instructions? | PASS | All steps have concrete code |
| 14 | Cross-task consistency? | PASS | AuthUser, token key, API paths all consistent |
| 15 | Save location? | PASS | docs/superpowers/plans/2026-04-25-github-oauth-auth.md |

**Status:** ✅ ALL PASS

---

## Execution Selection

**Tasks:** 6
**Dependencies:** yes (sequential chain)
**User Preference:** none
**Decision:** Subagent-Driven
**Reasoning:** 6 tasks with dependencies, exceeds 3-task threshold for subagent-driven execution

**Auto-invoking:** `superpowers:subagent-driven-development`
