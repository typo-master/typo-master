# Agent Usage Guide

This guide explains how to use the Web3 Typo Hunter Agent system.

## Table of Contents

- [Quick Start](#quick-start)
- [Architecture Overview](#architecture-overview)
- [Using Agents](#using-agents)
- [Configuration](#configuration)
- [CLI Usage](#cli-usage)
- [Examples](#examples)
- [Best Practices](#best-practices)

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/typo-master.git
cd typo-master

# Install dependencies
pip install -r requirements.txt
```

### Basic Usage

```bash
# Find potential projects
python web3_typo_hunter_cli.py find --token YOUR_GITHUB_TOKEN --days 30 --min-stars 100 --limit 50

# Scan a single project
python web3_typo_hunter_cli.py scan --token YOUR_GITHUB_TOKEN --repo ethereum/solidity --create-pr

# Process multiple projects
python web3_typo_hunter_cli.py process --token YOUR_GITHUB_TOKEN --days 30 --min-stars 100 --limit 5 --create-pr
```

## Architecture Overview

### Core Components

The agent system consists of:

1. **Agent Framework** (`src/agent_framework/`)
   - Base agent classes
   - Tool system
   - Message passing
   - State management
   - Error handling

2. **Tools** (`src/tools/`)
   - GitHub API tools
   - Git operations
   - Spell checking
   - File operations
   - PR creation
   - Report generation

3. **Agents** (`src/agents/`)
   - ProjectDiscoveryAgent - Finds Web3 projects
   - TypoScannerAgent - Scans for typos
   - TypoFixerAgent - Fixes typos
   - PRCreatorAgent - Creates PRs
   - ReportGeneratorAgent - Generates reports
   - CoordinatorAgent - Orchestrates workflows
   - QualityEvaluatorAgent - Validates fixes
   - DecisionAgent - Makes decisions

### Agent Lifecycle

```
Initialize → Start → Process Tasks → Stop
```

Each agent follows this lifecycle:
1. **Initialize**: Register tools, set up resources
2. **Start**: Begin processing tasks
3. **Process Tasks**: Execute tasks from the queue
4. **Stop**: Clean up and shutdown

## Using Agents

### Creating a Custom Agent

```python
from src.agent_framework import BaseAgent, AgentConfig
from src.agent_framework.logger import get_logger

logger = get_logger(__name__)

class MyAgent(BaseAgent):
    def __init__(self):
        config = AgentConfig(
            name="MyAgent",
            version="1.0.0",
            description="My custom agent",
        )
        super().__init__(config)
    
    async def on_initialize(self):
        """Initialize the agent"""
        # Register tools
        from src.tools import search_github_repos
        self.tool_registry.register(search_github_repos)
        
        logger.info(f"{self.name} initialized")
    
    async def on_start(self):
        """Called when agent starts"""
        logger.info(f"{self.name} started")
    
    async def on_stop(self):
        """Called when agent stops"""
        logger.info(f"{self.name} stopped")
    
    async def process_task(self, task):
        """Process a task"""
        # Implement your logic here
        result = await self.tool_registry.invoke("search_github_repos", ...)
        return result
```

### Using the Coordinator Agent

The CoordinatorAgent orchestrates the entire workflow:

```python
import asyncio
from src.agents import CoordinatorAgent

async def main():
    # Create coordinator
    coordinator = CoordinatorAgent(github_token="YOUR_TOKEN")
    
    # Initialize and start
    await coordinator.initialize()
    await coordinator.start()
    
    try:
        # Submit workflow task
        result = await coordinator.submit_task({
            "type": "run_workflow",
            "workflow": "single_project",
            "owner": "ethereum",
            "repo": "solidity",
            "create_pr": True,
        })
        
        # Wait for completion
        await coordinator.task_queue.join()
        
        print(f"Result: {result}")
    
    finally:
        await coordinator.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

## Configuration

### Configuration File

Create a `config.yaml` file:

```yaml
system:
  log_level: INFO
  log_file: logs/agent.log
  state_dir: ./state
  cache_dir: ./cache
  temp_dir: ./temp
  max_concurrent_tasks: 10
  task_timeout: 3600.0

github:
  token: YOUR_GITHUB_TOKEN
  base_url: https://api.github.com
  timeout: 30.0
  max_retries: 3

spell:
  enabled: true
  min_confidence: 0.7
  max_corrections_per_file: 50
  filter_web3_terms: true
  filter_code_identifiers: true

pr:
  auto_create: false
  min_typos_for_pr: 1
  min_stars_for_pr: 50
  min_activity_score: 30
  validate_before_create: true
```

### Loading Configuration

```python
from src.agent_framework import get_config

# Load configuration
config_manager = get_config("config.yaml")

# Get configuration values
log_level = config_manager.get("system.log_level")
github_token = config_manager.get("github.token")

# Set configuration values
config_manager.set("system.log_level", "DEBUG")

# Save configuration
config_manager.save()
```

### Environment Variables

You can override configuration using environment variables:

```bash
export GITHUB_TOKEN=your_token
export LOG_LEVEL=DEBUG
```

## CLI Usage

### Commands

#### Find Projects

```bash
python web3_typo_hunter_cli.py find \
  --token YOUR_TOKEN \
  --days 30 \
  --min-stars 100 \
  --limit 50 \
  --format csv
```

#### Scan Project

```bash
python web3_typo_hunter_cli.py scan \
  --token YOUR_TOKEN \
  --repo ethereum/solidity \
  --create-pr
```

#### Process Projects

```bash
python web3_typo_hunter_cli.py process \
  --token YOUR_TOKEN \
  --days 30 \
  --min-stars 100 \
  --limit 5 \
  --create-pr
```

## Examples

### Example 1: Simple Project Scan

```python
import asyncio
from src.agents import TypoScannerAgent

async def scan_project():
    scanner = TypoScannerAgent()
    await scanner.initialize()
    await scanner.start()
    
    try:
        result = await scanner.submit_task({
            "type": "scan_repo",
            "repo_path": "./repos/ethereum/solidity",
        })
        
        await scanner.task_queue.join()
        print(f"Found {result['total_typos']} typos")
    
    finally:
        await scanner.stop()

asyncio.run(scan_project())
```

### Example 2: Complete Workflow

```python
import asyncio
from src.agents import CoordinatorAgent

async def run_workflow():
    coordinator = CoordinatorAgent(github_token="YOUR_TOKEN")
    await coordinator.initialize()
    await coordinator.start()
    
    try:
        # Find projects
        discovery_result = await coordinator.submit_task({
            "type": "run_workflow",
            "workflow": "batch_projects",
            "days": 30,
            "min_stars": 100,
            "limit": 5,
            "create_pr": True,
        })
        
        await coordinator.task_queue.join()
        print(f"Processed {discovery_result['projects_processed']} projects")
    
    finally:
        await coordinator.stop()

asyncio.run(run_workflow())
```

### Example 3: Custom Tool

```python
from src.agent_framework import tool, ToolCategory

@tool(
    name="my_custom_tool",
    description="My custom tool",
    category=ToolCategory.UTILITY,
    examples=[
        {
            "input": {"param1": "value1"},
            "output": "result"
        }
    ]
)
async def my_custom_tool(param1: str) -> str:
    """Custom tool implementation"""
    return f"Processed: {param1}"

# Register with agent
agent.tool_registry.register(my_custom_tool)
```

## Best Practices

### 1. Use Async/Await

Always use async/await for I/O operations:

```python
# Good
async def process_data():
    data = await fetch_data()
    result = await process(data)
    return result

# Bad
def process_data():
    data = fetch_data()  # Blocking
    result = process(data)
    return result
```

### 2. Handle Errors Properly

Use the error handling decorators:

```python
from src.agent_framework import retry_on_error, with_error_handling

@retry_on_error(strategy_name="default", exceptions=(Exception,))
async def risky_operation():
    # This will automatically retry on failure
    pass

@with_error_handling(category="network", severity="medium")
async def network_operation():
    # This will handle errors gracefully
    pass
```

### 3. Use Metrics

Monitor performance with metrics:

```python
from src.agent_framework import get_metrics_collector

metrics = get_metrics_collector()

# Track operation count
metrics.increment_counter("operations_completed")

# Track operation duration
metrics.observe_histogram("operation_duration", 1.5)

# Track gauge values
metrics.set_gauge("active_connections", 10)
```

### 4. Use Configuration

Store configuration in files, not in code:

```python
# Good
config_manager = get_config("config.yaml")
token = config_manager.get("github.token")

# Bad
token = "hardcoded_token"  # Don't do this
```

### 5. Log Appropriately

Use structured logging:

```python
from src.agent_framework import get_logger

logger = get_logger(__name__)

logger.info("Processing started", extra={"task_id": 123})
logger.error("Processing failed", extra={"error": str(e)})
```

### 6. Validate Inputs

Always validate inputs before processing:

```python
async def process_task(self, task):
    if not task.get("repo_path"):
        return {"error": "repo_path is required"}
    
    if not os.path.exists(task["repo_path"]):
        return {"error": "repo_path does not exist"}
    
    # Process task
    return await self._process(task)
```

### 7. Use State Management

Persist state for recovery:

```python
from src.agent_framework import StateManager

state_manager = StateManager()

# Save state
state_manager.save_state("agent_state", {"processed": 10})

# Load state
state = state_manager.load_state("agent_state")
```

## Troubleshooting

### Common Issues

#### 1. GitHub API Rate Limiting

If you hit rate limits, add delays:

```python
import asyncio

await asyncio.sleep(2)  # Wait between requests
```

#### 2. Memory Issues

For large projects, process in batches:

```python
files = list_files(repo_path)
for i in range(0, len(files), 100):
    batch = files[i:i+100]
    await process_batch(batch)
```

#### 3. Task Queue Blocking

Make sure to await task completion:

```python
await coordinator.task_queue.join()  # Wait for all tasks
```

## Next Steps

- Read the [Architecture Documentation](AGENT_ARCHITECTURE.md)
- Explore the [Tool API Documentation](TOOL_API.md)
- Check out the [Examples](examples/)
- Review the [Test Cases](tests/)
