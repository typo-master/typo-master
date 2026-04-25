"""
MySQL-backed storage for backend conversation and workflow state.
"""

import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pymysql
from pymysql.cursors import DictCursor


class ConversationNotFoundError(KeyError):
    """Raised when conversation does not exist."""


class WorkflowTaskNotFoundError(KeyError):
    """Raised when workflow task does not exist."""


class MySQLStorage:
    _IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_]+$")

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
    ) -> None:
        if not self._IDENTIFIER_RE.fullmatch(database):
            raise ValueError("MYSQL_DATABASE contains unsupported characters")

        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database

    @classmethod
    def from_env(cls) -> "MySQLStorage":
        return cls(
            host=os.getenv("MYSQL_HOST", "127.0.0.1"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            user=os.getenv("MYSQL_USER", "root"),
            password=os.getenv("MYSQL_PASSWORD", "nopasswd"),
            database=os.getenv("MYSQL_DATABASE", "typomaster"),
        )

    def _connect(self, include_database: bool = True) -> pymysql.connections.Connection:
        kwargs: Dict[str, Any] = {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "password": self.password,
            "charset": "utf8mb4",
            "cursorclass": DictCursor,
            "autocommit": False,
        }
        if include_database:
            kwargs["database"] = self.database
        return pymysql.connect(**kwargs)

    def initialize(self) -> None:
        conn = self._connect(include_database=False)
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{self.database}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            conn.commit()
        finally:
            conn.close()

        conn = self._connect(include_database=True)
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS conversations (
                      conversation_id VARCHAR(64) NOT NULL PRIMARY KEY,
                      created_at DATETIME(6) NOT NULL,
                      INDEX idx_conversations_created_at (created_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS conversation_messages (
                      id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                      conversation_id VARCHAR(64) NOT NULL,
                      role VARCHAR(16) NOT NULL,
                      content LONGTEXT NOT NULL,
                      created_at DATETIME(6) NOT NULL,
                      INDEX idx_messages_conversation_created (conversation_id, id),
                      CONSTRAINT fk_messages_conversation
                        FOREIGN KEY (conversation_id)
                        REFERENCES conversations(conversation_id)
                        ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS workflow_tasks (
                      task_id VARCHAR(64) NOT NULL PRIMARY KEY,
                      status VARCHAR(32) NOT NULL,
                      created_at DATETIME(6) NOT NULL,
                      updated_at DATETIME(6) NOT NULL,
                      result_json LONGTEXT NULL,
                      error_text LONGTEXT NULL,
                      INDEX idx_workflow_tasks_updated_at (updated_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
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
            conn.commit()
        finally:
            conn.close()

    def create_conversation(self, conversation_id: str, created_at: str) -> None:
        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO conversations (conversation_id, created_at)
                    VALUES (%s, %s)
                    """,
                    (conversation_id, self._iso_to_mysql_datetime(created_at)),
                )
            conn.commit()
        finally:
            conn.close()

    def get_conversation_messages(self, conversation_id: str) -> Optional[List[Dict[str, Any]]]:
        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT conversation_id
                    FROM conversations
                    WHERE conversation_id = %s
                    LIMIT 1
                    """,
                    (conversation_id,),
                )
                if cursor.fetchone() is None:
                    return None

                cursor.execute(
                    """
                    SELECT role, content, created_at
                    FROM conversation_messages
                    WHERE conversation_id = %s
                    ORDER BY id ASC
                    """,
                    (conversation_id,),
                )
                rows = cursor.fetchall()
                return [
                    {
                        "role": str(row["role"]),
                        "content": str(row["content"]),
                        "created_at": self._mysql_datetime_to_iso(row["created_at"]),
                    }
                    for row in rows
                ]
        finally:
            conn.close()

    def append_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        created_at: str,
    ) -> None:
        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO conversation_messages (conversation_id, role, content, created_at)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        conversation_id,
                        role,
                        content,
                        self._iso_to_mysql_datetime(created_at),
                    ),
                )
            conn.commit()
        except pymysql.err.IntegrityError as exc:
            conn.rollback()
            raise ConversationNotFoundError(f"conversation not found: {conversation_id}") from exc
        finally:
            conn.close()

    def create_workflow_task(
        self,
        task_id: str,
        status: str,
        created_at: str,
        updated_at: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> None:
        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO workflow_tasks (
                      task_id, status, created_at, updated_at, result_json, error_text
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        task_id,
                        status,
                        self._iso_to_mysql_datetime(created_at),
                        self._iso_to_mysql_datetime(updated_at),
                        self._dump_json(result),
                        error,
                    ),
                )
            conn.commit()
        finally:
            conn.close()

    def update_workflow_task(
        self,
        task_id: str,
        status: str,
        updated_at: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> None:
        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE workflow_tasks
                    SET status = %s,
                        updated_at = %s,
                        result_json = %s,
                        error_text = %s
                    WHERE task_id = %s
                    """,
                    (
                        status,
                        self._iso_to_mysql_datetime(updated_at),
                        self._dump_json(result),
                        error,
                        task_id,
                    ),
                )
                if cursor.rowcount == 0:
                    raise WorkflowTaskNotFoundError(f"task not found: {task_id}")
            conn.commit()
        finally:
            conn.close()

    def get_workflow_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT task_id, status, created_at, updated_at, result_json, error_text
                    FROM workflow_tasks
                    WHERE task_id = %s
                    LIMIT 1
                    """,
                    (task_id,),
                )
                row = cursor.fetchone()
                if row is None:
                    return None

                return {
                    "task_id": str(row["task_id"]),
                    "status": str(row["status"]),
                    "created_at": self._mysql_datetime_to_iso(row["created_at"]),
                    "updated_at": self._mysql_datetime_to_iso(row["updated_at"]),
                    "result": self._load_json(row.get("result_json")),
                    "error": row.get("error_text"),
                }
        finally:
            conn.close()

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

    @staticmethod
    def _dump_json(payload: Optional[Dict[str, Any]]) -> Optional[str]:
        if payload is None:
            return None
        return json.dumps(payload, ensure_ascii=False)

    @staticmethod
    def _load_json(payload: Any) -> Optional[Dict[str, Any]]:
        if payload is None:
            return None
        if isinstance(payload, dict):
            return payload
        if isinstance(payload, str):
            try:
                parsed = json.loads(payload)
                if isinstance(parsed, dict):
                    return parsed
                return {"value": parsed}
            except Exception:
                return {"raw": payload}
        return {"value": payload}

    @staticmethod
    def _iso_to_mysql_datetime(value: str) -> datetime:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).replace(tzinfo=None)

    @staticmethod
    def _mysql_datetime_to_iso(value: Any) -> str:
        if isinstance(value, str):
            parsed = datetime.fromisoformat(value)
        elif isinstance(value, datetime):
            parsed = value
        else:
            parsed = datetime.fromtimestamp(0, timezone.utc)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat()
