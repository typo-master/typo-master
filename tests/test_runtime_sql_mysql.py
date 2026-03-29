import pytest

import app.agent.runtime as runtime_module
from app.agent.runtime import TypeAgentRuntime


@pytest.mark.asyncio
async def test_execute_sql_skill_uses_mysql_select() -> None:
    runtime = TypeAgentRuntime()

    result = await runtime._execute_sql_skill(
        "run_sql",
        {
            "database": "typomaster",
            "query": "SELECT 1 AS ok",
            "read_only": True,
            "max_rows": 10,
        },
    )

    assert result.get("success") is True
    rows = (result.get("result") or {}).get("rows") or []
    assert rows
    assert rows[0]["ok"] == 1


@pytest.mark.asyncio
async def test_execute_sql_skill_blocks_non_readonly_statement() -> None:
    runtime = TypeAgentRuntime()

    result = await runtime._execute_sql_skill(
        "run_sql",
        {
            "database": "typomaster",
            "query": "DELETE FROM conversations",
            "read_only": True,
        },
    )

    assert result.get("success") is False
    assert "read_only mode" in str(result.get("error", ""))


@pytest.mark.asyncio
async def test_execute_sql_allows_local_mysql_when_permission_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runtime_module, "is_permission_allowed", lambda *args, **kwargs: False)
    monkeypatch.setattr(runtime_module, "get_permission_denial_message", lambda *args, **kwargs: "denied")

    runtime = TypeAgentRuntime()
    result = await runtime.execute_sql(
        database="typomaster",
        query="SELECT 1 AS ok",
        args=[],
        read_only=True,
        max_rows=10,
    )

    assert result.get("success") is True
    rows = (result.get("result") or {}).get("rows") or []
    assert rows
    assert rows[0]["ok"] == 1


@pytest.mark.asyncio
async def test_execute_skill_sql_blocks_remote_host_when_permission_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runtime_module, "is_permission_allowed", lambda *args, **kwargs: False)
    monkeypatch.setattr(runtime_module, "get_permission_denial_message", lambda *args, **kwargs: "denied")

    runtime = TypeAgentRuntime()
    result = await runtime.execute_skill(
        "run_sql",
        {
            "host": "8.8.8.8",
            "database": "typomaster",
            "query": "SELECT 1 AS ok",
            "read_only": True,
        },
    )

    assert result.get("success") is False
    assert result.get("error") == "denied"
