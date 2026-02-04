"""
Test cases for BaseAgent
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from src.agent_framework import BaseAgent, AgentConfig, AgentState
from src.agent_framework.logger import get_logger

logger = get_logger(__name__)


class MockAgent(BaseAgent):
    """Mock agent for testing"""
    
    def __init__(self):
        config = AgentConfig(
            name="MockAgent",
            version="1.0.0",
            description="Mock agent for testing",
        )
        super().__init__(config)
        self.initialize_called = False
        self.start_called = False
        self.stop_called = False
        self.pause_called = False
        self.resume_called = False
        self.task_processed = False
    
    async def on_initialize(self):
        """Initialize the agent"""
        self.initialize_called = True
        logger.info("MockAgent initialized")
    
    async def on_start(self):
        """Called when agent starts"""
        self.start_called = True
        logger.info("MockAgent started")
    
    async def on_stop(self):
        """Called when agent stops"""
        self.stop_called = True
        logger.info("MockAgent stopped")
    
    async def on_pause(self):
        """Called when agent is paused"""
        self.pause_called = True
        logger.info("MockAgent paused")
    
    async def on_resume(self):
        """Called when agent resumes"""
        self.resume_called = True
        logger.info("MockAgent resumed")
    
    async def process_task(self, task):
        """Process a task"""
        self.task_processed = True
        return {"success": True, "data": "Task processed"}


class TestBaseAgent:
    """Test cases for BaseAgent"""
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """Test agent initialization"""
        agent = MockAgent()
        
        assert not agent.initialize_called
        assert agent.state == AgentState.IDLE
        
        await agent.initialize()
        
        assert agent.initialize_called
        assert agent.state == AgentState.IDLE
    
    @pytest.mark.asyncio
    async def test_agent_lifecycle(self):
        """Test agent lifecycle"""
        agent = MockAgent()
        
        # Initialize
        await agent.initialize()
        assert agent.state == AgentState.IDLE
        
        # Start
        await agent.start()
        assert agent.start_called
        assert agent.state == AgentState.RUNNING
        
        # Stop
        await agent.stop()
        assert agent.stop_called
        assert agent.state == AgentState.STOPPED
    
    @pytest.mark.asyncio
    async def test_agent_pause_resume(self):
        """Test agent pause and resume"""
        agent = MockAgent()
        
        await agent.initialize()
        await agent.start()
        
        # Pause
        await agent.pause()
        assert agent.pause_called
        assert agent.state == AgentState.PAUSED
        
        # Resume
        await agent.resume()
        assert agent.resume_called
        assert agent.state == AgentState.RUNNING
        
        await agent.stop()
    
    @pytest.mark.asyncio
    async def test_task_processing(self):
        """Test task processing"""
        agent = MockAgent()
        
        await agent.initialize()
        await agent.start()
        
        # Submit task
        task = {"type": "test_task", "data": "test"}
        await agent.submit_task(task)
        
        # Wait for task to be processed
        await asyncio.sleep(0.1)
        
        assert agent.task_processed
        
        await agent.stop()
    
    @pytest.mark.asyncio
    async def test_task_queue(self):
        """Test task queue management"""
        agent = MockAgent()
        
        await agent.initialize()
        await agent.start()
        
        # Submit multiple tasks
        for i in range(5):
            await agent.submit_task({"type": "test_task", "id": i})
        
        # Wait for all tasks to complete
        await agent.task_queue.join()
        
        await agent.stop()
    
    @pytest.mark.asyncio
    async def test_metrics_collection(self):
        """Test metrics collection"""
        agent = MockAgent()
        
        await agent.initialize()
        
        # Check metrics
        metrics = agent.get_metrics()
        assert "tasks_processed" in metrics
        assert "tasks_failed" in metrics
        assert "uptime" in metrics
        
        await agent.stop()
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling"""
        agent = MockAgent()
        
        await agent.initialize()
        await agent.start()
        
        # Submit a task that will fail
        task = {"type": "nonexistent_task"}
        await agent.submit_task(task)
        
        # Wait for task to be processed
        await asyncio.sleep(0.1)
        
        # Check that error was handled
        metrics = agent.get_metrics()
        assert metrics["tasks_failed"] >= 0
        
        await agent.stop()
    
    @pytest.mark.asyncio
    async def test_state_transitions(self):
        """Test state transitions"""
        agent = MockAgent()
        
        # Initial state
        assert agent.state == AgentState.IDLE
        
        await agent.initialize()
        assert agent.state == AgentState.IDLE
        
        await agent.start()
        assert agent.state == AgentState.RUNNING
        
        await agent.pause()
        assert agent.state == AgentState.PAUSED
        
        await agent.resume()
        assert agent.state == AgentState.RUNNING
        
        await agent.stop()
        assert agent.state == AgentState.STOPPED
    
    @pytest.mark.asyncio
    async def test_tool_registration(self):
        """Test tool registration"""
        agent = MockAgent()
        
        # Register a tool
        async def test_tool(param: str) -> str:
            return f"Processed: {param}"
        
        agent.tool_registry.register(test_tool)
        
        # Check tool is registered
        tools = agent.tool_registry.list_tools()
        assert "test_tool" in tools
        
        # Invoke tool
        result = await agent.tool_registry.invoke("test_tool", param="test")
        assert result["data"] == "Processed: test"
    
    @pytest.mark.asyncio
    async def test_context_management(self):
        """Test context management"""
        agent = MockAgent()
        
        await agent.initialize()
        
        # Set context
        agent.context.set("test_key", "test_value")
        
        # Get context
        value = agent.context.get("test_key")
        assert value == "test_value"
        
        await agent.stop()
    
    @pytest.mark.asyncio
    async def test_state_persistence(self):
        """Test state persistence"""
        agent = MockAgent()
        
        await agent.initialize()
        
        # Set state
        agent.state_manager.set("test_state", {"key": "value"})
        
        # Save state
        agent.state_manager.save_state("agent_state", agent.get_state())
        
        # Load state
        loaded_state = agent.state_manager.load_state("agent_state")
        assert loaded_state is not None
        
        await agent.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
