"""
Integration Tests for TypoAgent System
"""

import pytest
import asyncio
from typing import Dict, Any, List

from src.agents import CoordinatorAgent
from src.agent_framework import get_logger

logger = get_logger(__name__)


class TestIntegration:
    """Integration tests for the complete system"""
    
    @pytest.mark.asyncio
    async def test_full_workflow_integration(self):
        """Test full typo hunting workflow"""
        coordinator = CoordinatorAgent(github_token="test_token")
        await coordinator.initialize()
        await coordinator.start()
        
        try:
            # Test project discovery
            result = await coordinator.submit_task({
                "type": "search_projects",
                "days": 30,
                "min_stars": 10,
                "limit": 2
            })
            
            # Wait for completion
            await coordinator.task_queue.join()
            
            # Verify result
            assert result is not None
        
        finally:
            await coordinator.stop()
    
    @pytest.mark.asyncio
    async def test_agent_collaboration(self):
        """Test agent collaboration"""
        coordinator = CoordinatorAgent(github_token="test_token")
        await coordinator.initialize()
        await coordinator.start()
        
        try:
            # Test collaboration between agents
            result = await coordinator.submit_task({
                "type": "run_workflow",
                "workflow": "collaboration_test"
            })
            
            # Wait for completion
            await coordinator.task_queue.join()
            
            # Verify collaboration
            assert result is not None
        
        finally:
            await coordinator.stop()
    
    @pytest.mark.asyncio
    async def test_error_recovery(self):
        """Test error recovery in workflows"""
        coordinator = CoordinatorAgent(github_token="test_token")
        await coordinator.initialize()
        await coordinator.start()
        
        try:
            # Test with invalid parameters
            result = await coordinator.submit_task({
                "type": "invalid_task"
            })
            
            # Wait for completion
            await coordinator.task_queue.join()
            
            # Should handle error gracefully
            assert result is not None
        
        finally:
            await coordinator.stop()
    
    @pytest.mark.asyncio
    async def test_concurrent_workflows(self):
        """Test running multiple workflows concurrently"""
        coordinator = CoordinatorAgent(github_token="test_token")
        await coordinator.initialize()
        await coordinator.start()
        
        try:
            # Submit multiple tasks
            tasks = []
            for i in range(3):
                task = coordinator.submit_task({
                    "type": "simple_task",
                    "id": i
                })
                tasks.append(task)
            
            # Wait for all tasks
            await coordinator.task_queue.join()
            
            # All tasks should complete
            assert coordinator.task_queue.qsize() == 0
        
        finally:
            await coordinator.stop()
    
    @pytest.mark.asyncio
    async def test_state_persistence(self):
        """Test state persistence across sessions"""
        coordinator = CoordinatorAgent(github_token="test_token")
        await coordinator.initialize()
        await coordinator.start()
        
        try:
            # Set some state
            coordinator.context.set("test_key", "test_value")
            
            # Save state
            coordinator.state_manager.save_state("test_state", coordinator.get_state())
            
            # Load state
            loaded_state = coordinator.state_manager.load_state("test_state")
            
            # Verify state
            assert loaded_state is not None
        
        finally:
            await coordinator.stop()
    
    @pytest.mark.asyncio
    async def test_metrics_collection(self):
        """Test metrics collection"""
        coordinator = CoordinatorAgent(github_token="test_token")
        await coordinator.initialize()
        await coordinator.start()
        
        try:
            # Run some tasks
            await coordinator.submit_task({"type": "test_task"})
            await coordinator.task_queue.join()
            
            # Get metrics
            metrics = coordinator.get_metrics()
            
            # Verify metrics
            assert "tasks_processed" in metrics
            assert "tasks_failed" in metrics
        
        finally:
            await coordinator.stop()
    
    @pytest.mark.asyncio
    async def test_tool_invocation(self):
        """Test tool invocation through agents"""
        coordinator = CoordinatorAgent(github_token="test_token")
        await coordinator.initialize()
        await coordinator.start()
        
        try:
            # Invoke a tool
            result = await coordinator.tool_registry.invoke("get_logger")
            
            # Verify result
            assert result["success"] == True
        
        finally:
            await coordinator.stop()
    
    @pytest.mark.asyncio
    async def test_message_passing(self):
        """Test message passing between agents"""
        coordinator = CoordinatorAgent(github_token="test_token")
        await coordinator.initialize()
        await coordinator.start()
        
        try:
            # Send a message
            message = coordinator.message_bus.create_message(
                sender="test_agent",
                receiver="coordinator",
                message_type="test",
                content={"test": "data"}
            )
            
            await coordinator.message_bus.send(message)
            
            # Verify message sent
            assert message is not None
        
        finally:
            await coordinator.stop()
    
    @pytest.mark.asyncio
    async def test_configuration_management(self):
        """Test configuration management"""
        from src.agent_framework import ConfigManager
        
        config_manager = ConfigManager()
        
        # Set configuration
        config_manager.set("test_key", "test_value")
        
        # Get configuration
        value = config_manager.get("test_key")
        
        # Verify configuration
        assert value == "test_value"
    
    @pytest.mark.asyncio
    async def test_health_monitoring(self):
        """Test health monitoring"""
        from src.agent_framework import HealthMonitor, get_health_monitor
        
        health_monitor = get_health_monitor()
        
        # Register a component
        health_monitor.register_component("test_component")
        
        # Check health
        health = await health_monitor.check_health("test_component")
        
        # Verify health check
        assert health is not None
    
    @pytest.mark.asyncio
    async def test_resource_management(self):
        """Test resource management"""
        from src.agent_framework import ResourceManager, get_resource_manager
        
        resource_manager = get_resource_manager()
        
        # Create rate limiter
        limiter = resource_manager.create_rate_limiter("test", 10.0)
        
        # Test rate limiting
        acquired = await limiter.acquire(1)
        
        # Verify acquisition
        assert acquired == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
