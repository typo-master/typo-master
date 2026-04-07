# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Typo Master (Web3 Typo Hunter) is a modular agent system for finding and fixing typos in GitHub repositories. It consists of:

- **Agent Framework** (`src/agent_framework/`): Core agent infrastructure with LangGraph orchestration
- **Product Interface** (`app/`): FastAPI backend + React frontend for conversational interaction
- **CLI Tools** (`src/scripts/`): Command-line interface for batch operations

## Common Development Commands

### Running Services

```bash
# Start all services (backend + frontend) via PM2
./start.sh

# Check service status
./scripts/pm2_status.sh

# View logs (last N lines)
./scripts/pm2_logs.sh 100

# Stop all PM2 services and clear port listeners
./scripts/pm2_stop_all.sh

# Manual backend startup (dev mode with hot reload)
python app/backend/run.py

# Manual frontend startup
cd app/frontend && npm run dev
```

Service endpoints:
- Frontend: http://127.0.0.1:50121
- Backend API: http://127.0.0.1:50120/api/v1
- Health check: http://127.0.0.1:50120/api/v1/health

### Installing Dependencies

```bash
# Core Python dependencies
pip install -r requirements.txt
pip install -e .

# Backend product interface dependencies (required for app/backend/)
pip install -r app/backend/requirements.txt

# Frontend dependencies
cd app/frontend && npm install
```

### Testing

```bash
# Run all tests
pytest tests/ -v --tb=short

# Run by category using the helper runner
python run_tests.py unit
python run_tests.py integration
python run_tests.py regression
python run_tests.py security
python run_tests.py critical
python run_tests.py all --parallel --coverage

# Run specific test markers
pytest tests/ -v -m unit
pytest tests/ -v -m integration
pytest tests/ -v -m "not slow"

# Run single test file
pytest tests/path/to/test_file.py -v

# Run single test function
pytest tests/path/to/test_file.py::test_function_name -v

# Coverage report
pytest tests/ --cov=src --cov-report=html
```

Test markers defined in `pytest.ini`:
- `unit`: Fast, isolated tests
- `integration`: Tests requiring external services
- `e2e`: End-to-end tests
- `slow`: Skip in quick runs
- `database`: Tests requiring MySQL
- `regression`: API contract stability tests
- `security`: Security-focused tests
- `critical`: Must-pass critical tests

### Code Quality

```bash
# Format code
make format
black src/ tests/

# Lint check
make lint
flake8 src/ --max-line-length=100 --ignore=E501,W503
mypy src/ --ignore-missing-imports

# Fix lint issues
make lint-fix
```

### CLI Usage

```bash
# Check LLM API connectivity
python src/scripts/web3_typo_hunter_cli.py llm-check

# View agent capabilities
python src/scripts/web3_typo_hunter_cli.py capabilities

# Scan single repo
python src/scripts/web3_typo_hunter_cli.py scan --token $GITHUB_TOKEN --repo owner/repo

# Batch process
python src/scripts/web3_typo_hunter_cli.py process --token $GITHUB_TOKEN --days 30 --limit 5

# Translate repository README
python src/scripts/web3_typo_hunter_cli.py translate --token $GITHUB_TOKEN --repo owner/repo --target-lang zh

# Find contributable issues in a repo
python src/scripts/web3_typo_hunter_cli.py find-issues --token $GITHUB_TOKEN --repo owner/repo --limit 30

# Batch find contribution opportunities across repos
python src/scripts/web3_typo_hunter_cli.py find-contributions --token $GITHUB_TOKEN --repos owner/repo1 owner/repo2 --limit 10
```

## Architecture

### Agent System (LangGraph-based)

The coordinator agent (`src/agents/coordinator_agent.py`) orchestrates a state machine workflow:

```
discover → scan → evaluate → fix → decide → create_pr → report
```

Key agents:
- `ProjectDiscoveryAgent`: Finds Web3 repos via GitHub API
- `TypoScannerAgent`: Scans code for spelling errors
- `QualityEvaluatorAgent`: Filters false positives
- `TypoFixerAgent`: Generates corrections
- `DecisionAgent`: LLM-powered PR decisions
- `PRCreatorAgent`: Creates GitHub PRs
- `ReportGeneratorAgent`: Generates reports

### Agent Framework

Located in `src/agent_framework/`:

- `base_agent.py`: Abstract base with lifecycle management
- `llm_client.py`: OpenAI-compatible API client (forces UTF-8 encoding)
- `tool_system.py`: Tool registration and execution
- `memory/`: Memory backends (ChromaDB, mem0)
- `state.py`: Agent state persistence
- `permissions.py`: Fine-grained permission controls for dangerous operations

### Product Backend

FastAPI server (`app/backend/main.py`) providing:

- Conversation management (chat with memory)
- Workflow execution (async task queue)
- Skill registry (built-in + custom skills)
- MCP server integration (SSE transport)
- Permission system

Key endpoints:
- `POST /api/v1/conversations/{id}/messages` - Chat endpoint
- `POST /api/v1/agent/workflows` - Start workflow
- `POST /api/v1/skills/execute` - Execute skill
- `GET /api/v1/capabilities` - List capabilities

### Agent Runtime Adapter

`app/agent/` connects the FastAPI backend to the LangGraph coordinator:

- `runtime.py` (`TypeAgentRuntime`): Entry point for skill execution and workflow dispatch from the backend. Initializes the `CoordinatorAgent` as a singleton and routes `execute_skill` / `run_workflow` calls.
- `registry.py`: In-memory skill and MCP server registry. Loads built-in skills on startup and supports custom skill CRUD.
- `mcp_agent_adapter.py`: Exposes TypoAgent capabilities as MCP (Model Context Protocol) Tools over SSE, allowing external MCP clients to invoke agent skills.
- `mcp_sse_server.py`: SSE transport server for MCP connections.

### Frontend

React + TypeScript + Ant Design (`app/frontend/src/`):

- Chat interface with message history
- Skill management UI
- MCP server configuration
- Workflow monitoring

### Phase 2 & 3 Modules

Beyond typo hunting, the system now supports:

- **Translation** (`src/web3_typo_hunter/translator/`):
  - `document_translator.py`: Translates README and documentation
  - `language_detector.py`: Detects source language
  - `translation_cache.py`: Caches translation results to `.translation_cache/`

- **Issue Discovery** (`src/web3_typo_hunter/issue_finder/`):
  - `issue_filter.py`: Filters and scores open issues
  - `issue_analyzer.py`: Analyzes issue difficulty and required skills
  - `contribution_evaluator.py`: Scores issues by airdrop potential, PR acceptance rate, and community friendliness

## Configuration

### Environment Variables

Required for LLM:
```bash
export OPENAI_BASE_URL="https://your-endpoint"
export OPENAI_MODEL="gpt-5.4"
export OPENAI_API_KEY="sk-xxxx"
```

Required for MySQL:
```bash
export MYSQL_HOST=127.0.0.1
export MYSQL_PORT=3306
export MYSQL_USER=root
export MYSQL_PASSWORD=nopasswd
export MYSQL_DATABASE=typomaster
```

### Config File

`config.yml` contains:
- GitHub token and API settings
- LLM configuration
- Scanner settings (file extensions, skip directories)
- Permission matrix

## Key Directories

```
src/
  agent_framework/    # Core agent infrastructure
  agents/            # Agent implementations
  tools/             # Tool definitions (GitHub, file, git, etc.)
  skills/            # Skill definitions (built-in + custom)
  web3_typo_hunter/  # Legacy typo hunting + Phase 2/3 modules
    discovery/
    scanner/
    processor/
    translator/
    issue_finder/

app/
  backend/           # FastAPI server
  frontend/          # React frontend
  agent/             # Runtime adapter (runtime, registry, MCP)

tests/
  unit/              # Unit tests
  integration/       # Integration tests
  regression/        # API contract and schema tests
  security/          # Security tests
  agent_framework/   # Framework-specific tests
  agents/            # Coordinator agent tests
  scripts/           # CLI tests
  web3_typo_hunter/  # Module-specific tests
```

## Important Implementation Details

### LLM Client Encoding Fix

The API returns `Content-Type: text/event-stream` without charset, causing Chinese characters to display incorrectly. Fixed in `src/agent_framework/llm_client.py:175`:

```python
response.encoding = "utf-8"  # Force UTF-8 before response.json()
```

### Skill Execution Flow

1. Request → `main.py:execute_skill()`
2. → `agent_runtime.execute_skill()` (`app/agent/runtime.py`)
3. → `coordinator_agent.execute_skill_with_fallback()`
4. → Built-in skill OR custom skill via fallback

### Workflow State Machine

Workflows are async tasks stored in MySQL:
- Status: `queued` → `running` → `succeeded`/`failed`
- Task ID returned immediately
- Poll `GET /api/v1/agent/workflows/{task_id}` for status

### Memory System

Uses ChromaDB for vector storage:
- Conversations stored per conversation_id
- LLM context built from relevant memories
- State persisted to `agent_states/` directory

## Testing Strategy

- Unit tests: Test individual functions with mocked dependencies
- Integration tests: Test with real services (GitHub API, LLM)
- E2E tests: Full workflow from CLI/API entry to completion
- Regression tests: API contract and database schema stability
- Security tests: Input validation, authz, SQL injection, data exposure

Always use markers:
```python
@pytest.mark.unit
def test_function():
    pass
```

## Security Notes

- Never commit `config.yml` with real API keys
- GitHub token should have `repo` scope for PR creation
- Permission system controls dangerous operations (git push, PR create, etc.)
