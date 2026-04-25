# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Typo Master is a modular agent system for finding/fixing typos in GitHub repos, with product UI for conversational interaction. Three layers:

- **Agent Framework** (`src/agent_framework/`): Core agent infrastructure with LangGraph orchestration
- **Product Interface** (`app/`): FastAPI backend + React frontend for chat-based interaction
- **CLI** (`src/scripts/`): Batch operations via command line

## Commands

### Services (PM2)

```bash
./start.sh                          # Start all services via PM2 (backend + frontend)
./scripts/pm2_status.sh             # Check service status
./scripts/pm2_logs.sh 100           # View logs (last N lines)
./scripts/pm2_stop_all.sh           # Stop all services and clear ports
```

Manual startup (for development with hot reload):
```bash
python app/backend/run.py           # Backend on :50120 (uvicorn with --reload)
cd app/frontend && npm run dev      # Frontend on :50121 (vite)
```

Service endpoints: Frontend `http://127.0.0.1:50121`, Backend API `http://127.0.0.1:50120/api/v1`, Health `http://127.0.0.1:50120/api/v1/health`

### Install Dependencies

```bash
pip install -r requirements.txt && pip install -e .       # Core Python deps
pip install -r app/backend/requirements.txt                # Backend API deps
cd app/frontend && npm install                             # Frontend deps
```

Python environment: `venv311/` (Python 3.11)

### Testing

```bash
# Python tests (pytest)
pytest tests/ -v --tb=short              # All tests
pytest tests/ -v -m unit                 # Unit only
pytest tests/ -v -m integration          # Integration only
pytest tests/ -v -m "not slow"           # Skip slow tests
pytest tests/path/to/test_file.py::test_name -v  # Single test
python run_tests.py unit                 # Helper runner

# Frontend tests
cd app/frontend && npm test              # vitest

# Coverage
pytest tests/ --cov=src --cov-report=html
```

Test markers: `unit`, `integration`, `e2e`, `slow`, `database`, `regression`, `security`, `critical`

### Code Quality

```bash
make format     # black src/ tests/
make lint       # flake8 + black --check + mypy
make lint-fix   # auto-fix lint issues
make test-unit  # unit tests only
```

## Architecture

### Request Flow

```
Frontend (React/Ant Design) → Backend API (FastAPI :50120)
  → Agent Runtime (app/agent/runtime.py: TypeAgentRuntime)
    → CoordinatorAgent (src/agents/coordinator_agent.py: LangGraph StateGraph)
      → discover → scan → evaluate → fix → decide → create_pr → report
```

### Agent System

The `CoordinatorAgent` (`src/agents/coordinator_agent.py`) orchestrates a LangGraph `StateGraph` workflow through seven stages. Each stage has a dedicated agent class in `src/agents/`. Agent base infrastructure lives in `src/agent_framework/base_agent.py` with lifecycle management, tool system, memory backends (ChromaDB/mem0), and state persistence.

### Agent Framework (`src/agent_framework/`)

- `base_agent.py`: Abstract base with lifecycle hooks
- `llm_client.py`: OpenAI-compatible API client — **forces UTF-8 encoding** at line 175 (`response.encoding = "utf-8"`) to handle `text/event-stream` responses missing charset
- `tool_system.py`: Tool registration and execution
- `permissions.py`: Fine-grained permission matrix for dangerous operations (git push, PR create, etc.)

### Product Backend (`app/backend/`)

FastAPI server providing conversation management, async workflow execution (queued → running → succeeded/failed via MySQL), skill registry, and MCP server integration over SSE.

Key endpoints:
- `POST /api/v1/conversations/{id}/messages` — Chat
- `POST /api/v1/agent/workflows` — Start async workflow (returns task_id immediately)
- `GET /api/v1/agent/workflows/{task_id}` — Poll workflow status
- `POST /api/v1/skills/execute` — Execute skill
- `GET /api/v1/capabilities` — List capabilities

### Agent Runtime Adapter (`app/agent/`)

Bridges FastAPI to the LangGraph coordinator:
- `runtime.py`: Singleton `TypeAgentRuntime` — routes `execute_skill` / `run_workflow` to `CoordinatorAgent`
- `registry.py`: In-memory skill + MCP server registry, loads built-in skills on startup
- `mcp_agent_adapter.py` + `mcp_sse_server.py`: Exposes agent capabilities as MCP Tools over SSE

### Frontend (`app/frontend/`)

React 18 + TypeScript + Ant Design + Vite. Uses `react-router-dom` v7 for routing, `vitest` for testing.

### Phase 2/3 Modules

Beyond typo hunting (`src/web3_typo_hunter/`):
- **Translation** (`translator/`): README/doc translation with language detection and caching to `.translation_cache/`
- **Issue Discovery** (`issue_finder/`): Filters open issues by difficulty, airdrop potential, PR acceptance rate

## Configuration

### Environment Variables

LLM (required):
```bash
export OPENAI_BASE_URL="https://your-endpoint"
export OPENAI_MODEL="your-model"
export OPENAI_API_KEY="sk-xxxx"
```

MySQL (required for backend):
```bash
export MYSQL_HOST=127.0.0.1
export MYSQL_PORT=3306
export MYSQL_USER=root
export MYSQL_PASSWORD=nopasswd
export MYSQL_DATABASE=typomaster
```

### Config File

`config.yml` (gitignored) contains GitHub token, LLM settings, scanner config (file extensions, skip dirs), and permission matrix. See `config.example.yml` for template.

### PM2 Config

`ecosystem.config.js` contains hardcoded paths and env vars including API keys. The `run_prod.py` entrypoint is used by PM2 (no hot reload); `run.py` is for dev (with hot reload).

## Key Conventions

- LLM client encoding: always force `response.encoding = "utf-8"` before parsing — the API returns `text/event-stream` without charset
- Skill execution flow: Request → `main.py` → `TypeAgentRuntime` → `CoordinatorAgent.execute_skill_with_fallback()` → built-in or custom skill
- Workflows are async tasks in MySQL; task_id is returned immediately, client polls for completion
- Agent state persisted to `agent_states/` directory
- Conversations stored in ChromaDB per conversation_id
- All Python tests must use pytest markers (`@pytest.mark.unit`, etc.)
- `config.yml` is gitignored — never commit real API keys
- `venv311/` is the local Python 3.11 virtual environment
