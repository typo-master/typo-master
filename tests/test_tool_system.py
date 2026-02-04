"""
Test cases for Tool System
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock

from src.agent_framework import tool, ToolCategory, ToolRegistry
from src.agent_framework.logger import get_logger

logger = get_logger(__name__)


class TestToolDecorator:
    """Test cases for @tool decorator"""
    
    def test_tool_decorator_basic(self):
        """Test basic tool decorator"""
        @tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.UTILITY
        )
        async def my_tool(param: str) -> str:
            return f"Processed: {param}"
        
        assert my_tool.name == "test_tool"
        assert my_tool.description == "Test tool"
        assert my_tool.category == ToolCategory.UTILITY
    
    def test_tool_decorator_with_examples(self):
        """Test tool decorator with examples"""
        @tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.UTILITY,
            examples=[
                {
                    "input": {"param": "value"},
                    "output": "Processed: value"
                }
            ]
        )
        async def my_tool(param: str) -> str:
            return f"Processed: {param}"
        
        assert len(my_tool.examples) == 1
    
    def test_tool_decorator_with_parameters(self):
        """Test tool decorator with parameters"""
        @tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.UTILITY,
            parameters=[
                {"name": "param1", "type": "str", "description": "Parameter 1"},
                {"name": "param2", "type": "int", "description": "Parameter 2"}
            ]
        )
        async def my_tool(param1: str, param2: int) -> str:
            return f"Processed: {param1}, {param2}"
        
        assert len(my_tool.parameters) == 2


class TestToolRegistry:
    """Test cases for ToolRegistry"""
    
    @pytest.mark.asyncio
    async def test_tool_registration(self):
        """Test tool registration"""
        registry = ToolRegistry()
        
        async def my_tool(param: str) -> str:
            return f"Processed: {param}"
        
        # Register tool
        registry.register(my_tool)
        
        # Check tool is registered
        tools = registry.list_tools()
        assert "my_tool" in tools
        
        # Get tool metadata
        metadata = registry.get_tool_metadata("my_tool")
        assert metadata is not None
    
    @pytest.mark.asyncio
    async def test_tool_invocation(self):
        """Test tool invocation"""
        registry = ToolRegistry()
        
        async def my_tool(param: str) -> str:
            return f"Processed: {param}"
        
        registry.register(my_tool)
        
        # Invoke tool
        result = await registry.invoke("my_tool", param="test")
        
        assert result["success"] == True
        assert result["data"] == "Processed: test"
    
    @pytest.mark.asyncio
    async def test_tool_invocation_with_error(self):
        """Test tool invocation with error"""
        registry = ToolRegistry()
        
        async def failing_tool():
            raise ValueError("Test error")
        
        registry.register(failing_tool)
        
        # Invoke tool
        result = await registry.invoke("failing_tool")
        
        assert result["success"] == False
        assert result["error"] is not None
    
    @pytest.mark.asyncio
    async def test_tool_invocation_with_timeout(self):
        """Test tool invocation with timeout"""
        registry = ToolRegistry()
        
        async def slow_tool():
            await asyncio.sleep(10)
            return "Done"
        
        registry.register(slow_tool)
        
        # Invoke tool with timeout
        result = await registry.invoke("slow_tool", timeout=1.0)
        
        assert result["success"] == False
    
    @pytest.mark.asyncio
    async def test_multiple_tools(self):
        """Test multiple tools"""
        registry = ToolRegistry()
        
        async def tool1(param: str) -> str:
            return f"Tool1: {param}"
        
        async def tool2(param: str) -> str:
            return f"Tool2: {param}"
        
        registry.register(tool1)
        registry.register(tool2)
        
        # Check both tools are registered
        tools = registry.list_tools()
        assert len(tools) == 2
        
        # Invoke both tools
        result1 = await registry.invoke("tool1", param="test")
        result2 = await registry.invoke("tool2", param="test")
        
        assert result1["data"] == "Tool1: test"
        assert result2["data"] == "Tool2: test"
    
    @pytest.mark.asyncio
    async def test_tool_category_filtering(self):
        """Test tool category filtering"""
        registry = ToolRegistry()
        
        async def github_tool():
            return "GitHub"
        
        async def git_tool():
            return "Git"
        
        async def spell_tool():
            return "Spell"
        
        registry.register(github_tool, category=ToolCategory.GITHUB)
        registry.register(git_tool, category=ToolCategory.GIT)
        registry.register(spell_tool, category=ToolCategory.SPELL_CHECK)
        
        # Filter by category
        github_tools = registry.list_tools(category=ToolCategory.GITHUB)
        spell_tools = registry.list_tools(category=ToolCategory.SPELL_CHECK)
        
        assert len(github_tools) == 2
        assert len(spell_tools) == 1
    
    @pytest.mark.asyncio
    async def test_tool_metadata(self):
        """Test tool metadata"""
        registry = ToolRegistry()
        
        @tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.UTILITY,
            examples=[{"input": {}, "output": "result"}]
        )
        async def my_tool():
            return "result"
        
        registry.register(my_tool)
        
        # Get metadata
        metadata = registry.get_tool_metadata("test_tool")
        
        assert metadata.name == "test_tool"
        assert metadata.description == "Test tool"
        assert metadata.category == ToolCategory.UTILITY
        assert len(metadata.examples) == 1
    
    @pytest.mark.asyncio
    async def test_tool_discovery(self):
        """Test automatic tool discovery"""
        registry = ToolRegistry()
        
        # Create a module with tools
        async def tool1():
            return "tool1"
        
        async def tool2():
            return "tool2"
        
        # Register tools
        registry.register(tool1)
        registry.register(tool2)
        
        # Discover tools
        tools = registry.list_tools()
        assert "tool1" in tools
        assert "tool2" in tools
    
    @pytest.mark.asyncio
    async def test_tool_parameter_validation(self):
        """Test tool parameter validation"""
        registry = ToolRegistry()
        
        @tool(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.UTILITY,
            parameters=[
                {"name": "required_param", "type": "str", "required": True},
                {"name": "optional_param", "type": "str", "required": False}
            ]
        )
        async def my_tool(required_param: str, optional_param: str = None):
            return f"{required_param}, {optional_param}"
        
        registry.register(my_tool)
        
        # Test with required parameter
        result = await registry.invoke("test_tool", required_param="test")
        assert result["success"] == True
        
        # Test without required parameter
        result = await registry.invoke("test_tool")
        assert result["success"] == False


class TestToolIntegration:
    """Test cases for tool integration"""
    
    @pytest.mark.asyncio
    async def test_tool_with_agent(self):
        """Test tool usage with agent"""
        from src.agent_framework import BaseAgent, AgentConfig
        
        class TestAgent(BaseAgent):
            def __init__(self):
                config = AgentConfig(
                    name="TestAgent",
                    version="1.0.0",
                )
                super().__init__(config)
            
            async def on_initialize(self):
                # Register tool
                async def my_tool(param: str) -> str:
                    return f"Processed: {param}"
                
                self.tool_registry.register(my_tool)
            
            async def process_task(self, task):
                # Invoke tool
                result = await self.tool_registry.invoke("my_tool", param="test")
                return result
        
        agent = TestAgent()
        await agent.initialize()
        await agent.start()
        
        # Submit task
        await agent.submit_task({"type": "test_task"})
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        await agent.stop()
    
    @pytest.mark.asyncio
    async def test_tool_error_handling(self):
        """Test tool error handling"""
        registry = ToolRegistry()
        
        async def failing_tool():
            raise ValueError("Test error")
        
        registry.register(failing_tool)
        
        # Invoke tool
        result = await registry.invoke("failing_tool")
        
        # Check error handling
        assert result["success"] == False
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_tool_retry(self):
        """Test tool retry logic"""
        from src.agent_framework import retry_on_error
        
        call_count = 0
        
        @retry_on_error(strategy_name="default", max_retries=3)
        async def flaky_tool():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Not yet")
            return "Success"
        
        # Register and invoke
        registry = ToolRegistry()
        registry.register(flaky_tool)
        
        result = await registry.invoke("flaky_tool")
        
        # Should succeed after retries
        assert result["success"] == True
        assert call_count == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
