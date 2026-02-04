"""
Test cases for Agent Communication
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock

from src.agent_framework import (
    BaseAgent,
    AgentConfig,
    Message,
    MessageType,
    MessageHandler,
    MessageBus,
)
from src.agent_framework.logger import get_logger

logger = get_logger(__name__)


class TestMessage:
    """Test cases for Message class"""
    
    def test_message_creation(self):
        """Test creating a message"""
        message = Message(
            sender="agent1",
            receiver="agent2",
            type=MessageType.REQUEST,
            content={"action": "test"},
        )
        
        assert message.sender == "agent1"
        assert message.receiver == "agent2"
        assert message.type == MessageType.REQUEST
        assert message.content == {"action": "test"}
        assert message.timestamp is not None
        assert message.id is not None
    
    def test_message_serialization(self):
        """Test message serialization"""
        message = Message(
            sender="agent1",
            receiver="agent2",
            type=MessageType.REQUEST,
            content={"action": "test"},
        )
        
        # Convert to dict and back
        message_dict = message.to_dict()
        new_message = Message.from_dict(message_dict)
        
        assert new_message.sender == message.sender
        assert new_message.receiver == message.receiver
        assert new_message.type == message.type
        assert new_message.content == message.content


class TestMessageBus:
    """Test cases for MessageBus"""
    
    @pytest.mark.asyncio
    async def test_message_bus_publish(self):
        """Test publishing messages"""
        bus = MessageBus()
        
        message = Message(
            sender="agent1",
            receiver="agent2",
            type=MessageType.REQUEST,
            content={"action": "test"},
        )
        
        # Publish message
        await bus.publish(message)
        
        # Message should be in queue
        assert bus.message_queue.qsize() == 1
    
    @pytest.mark.asyncio
    async def test_message_bus_send(self):
        """Test sending messages to specific receiver"""
        bus = MessageBus()
        
        received_messages = []
        
        async def handler(message):
            received_messages.append(message)
        
        # Register handler
        bus.register_handler("agent2", handler)
        
        # Send message
        message = Message(
            sender="agent1",
            receiver="agent2",
            type=MessageType.REQUEST,
            content={"action": "test"},
        )
        
        await bus.send(message)
        
        # Wait for delivery
        await asyncio.sleep(0.1)
        
        # Message should be received
        assert len(received_messages) == 1
    
    @pytest.mark.asyncio
    async def test_message_bus_broadcast(self):
        """Test broadcasting messages"""
        bus = MessageBus()
        
        received_messages = []
        
        async def handler(message):
            received_messages.append(message)
        
        # Register multiple handlers
        bus.register_handler("agent1", handler)
        bus.register_handler("agent2", handler)
        
        # Broadcast message
        message = Message(
            sender="coordinator",
            receiver="all",
            type=MessageType.NOTIFICATION,
            content={"action": "test"},
        )
        
        await bus.broadcast(message)
        
        # Wait for delivery
        await asyncio.sleep(0.1)
        
        # Both handlers should receive message
        assert len(received_messages) == 2
    
    @pytest.mark.asyncio
    async def test_message_bus_subscribe(self):
        """Test subscribing to messages"""
        bus = MessageBus()
        
        received_messages = []
        
        async def handler(message):
            received_messages.append(message)
        
        # Subscribe to messages
        bus.subscribe(handler)
        
        # Send message
        message = Message(
            sender="agent1",
            receiver="agent2",
            type=MessageType.REQUEST,
            content={"action": "test"},
        )
        
        await bus.send(message)
        
        # Wait for delivery
        await asyncio.sleep(0.1)
        
        # Message should be received
        assert len(received_messages) == 1
    
    @pytest.mark.asyncio
    async def test_message_bus_filter(self):
        """Test filtering messages"""
        bus = MessageBus()
        
        request_messages = []
        notification_messages = []
        
        async def request_handler(message):
            request_messages.append(message)
        
        async def notification_handler(message):
            notification_messages.append(message)
        
        # Register handlers with filters
        bus.register_handler("agent1", request_handler, filter_type=MessageType.REQUEST)
        bus.register_handler("agent1", notification_handler, filter_type=MessageType.NOTIFICATION)
        
        # Send request
        request_message = Message(
            sender="agent2",
            receiver="agent1",
            type=MessageType.REQUEST,
            content={"action": "test"},
        )
        await bus.send(request_message)
        
        # Send notification
        notification_message = Message(
            sender="coordinator",
            receiver="agent1",
            type=MessageType.NOTIFICATION,
            content={"action": "test"},
        )
        await bus.send(notification_message)
        
        # Wait for delivery
        await asyncio.sleep(0.1)
        
        # Messages should be filtered correctly
        assert len(request_messages) == 1
        assert len(notification_messages) == 1
        assert request_messages[0].type == MessageType.REQUEST
        assert notification_messages[0].type == MessageType.NOTIFICATION


class TestAgentCommunication:
    """Test cases for agent communication"""
    
    @pytest.mark.asyncio
    async def test_agent_message_sending(self):
        """Test agent sending messages"""
        class TestAgent(BaseAgent):
            def __init__(self):
                config = AgentConfig(
                    name="TestAgent",
                    version="1.0.0",
                )
                super().__init__(config)
                self.received_messages = []
            
            async def on_initialize(self):
                async def handler(message):
                    self.received_messages.append(message)
                
                self.message_bus.register_handler(self.name, handler)
        
        agent1 = TestAgent()
        agent2 = TestAgent()
        
        await agent1.initialize()
        await agent2.initialize()
        
        # Send message
        message = Message(
            sender=agent1.name,
            receiver=agent2.name,
            type=MessageType.REQUEST,
            content={"action": "test"},
        )
        
        await agent1.message_bus.send(message)
        
        # Wait for delivery
        await asyncio.sleep(0.1)
        
        # Message should be received
        assert len(agent2.received_messages) == 1
    
    @pytest.mark.asyncio
    async def test_agent_message_handling(self):
        """Test agent handling messages"""
        class TestAgent(BaseAgent):
            def __init__(self):
                config = AgentConfig(
                    name="TestAgent",
                    version="1.0.0",
                )
                super().__init__(config)
                self.handled_messages = []
            
            async def on_initialize(self):
                async def handler(message):
                    self.handled_messages.append(message)
                    return {"success": True}
                
                self.message_bus.register_handler(self.name, handler)
        
        agent = TestAgent()
        await agent.initialize()
        
        # Send message
        message = Message(
            sender="coordinator",
            receiver=agent.name,
            type=MessageType.REQUEST,
            content={"action": "test"},
        )
        
        await agent.message_bus.send(message)
        
        # Wait for handling
        await asyncio.sleep(0.1)
        
        # Message should be handled
        assert len(agent.handled_messages) == 1
    
    @pytest.mark.asyncio
    async def test_agent_broadcast(self):
        """Test agent broadcasting messages"""
        agents = []
        
        for i in range(3):
            class TestAgent(BaseAgent):
                def __init__(self):
                    config = AgentConfig(
                        name=f"Agent{i}",
                        version="1.0.0",
                    )
                    super().__init__(config)
                    self.received_messages = []
                
                async def on_initialize(self):
                    async def handler(message):
                        self.received_messages.append(message)
                    
                    self.message_bus.register_handler(self.name, handler)
            
            agent = TestAgent()
            agents.append(agent)
            await agent.initialize()
        
        # Broadcast from first agent
        message = Message(
            sender=agents[0].name,
            receiver="all",
            type=MessageType.NOTIFICATION,
            content={"action": "test"},
        )
        
        await agents[0].message_bus.broadcast(message)
        
        # Wait for delivery
        await asyncio.sleep(0.1)
        
        # All agents should receive message
        for agent in agents[1:]:
            assert len(agent.received_messages) == 1


class TestMessageHandler:
    """Test cases for MessageHandler"""
    
    @pytest.mark.asyncio
    async def test_message_handler_creation(self):
        """Test creating a message handler"""
        handler = MessageHandler(
            name="test_handler",
            handler_type=MessageType.REQUEST,
        )
        
        assert handler.name == "test_handler"
        assert handler.handler_type == MessageType.REQUEST
    
    @pytest.mark.asyncio
    async def test_message_handler_execution(self):
        """Test executing message handler"""
        executed = False
        result_data = None
        
        async def handler_func(message):
            nonlocal executed, result_data
            executed = True
            result_data = {"result": "success"}
            return result_data
        
        handler = MessageHandler(
            name="test_handler",
            handler_type=MessageType.REQUEST,
            handler=handler_func,
        )
        
        # Create message
        message = Message(
            sender="agent1",
            receiver="agent2",
            type=MessageType.REQUEST,
            content={"action": "test"},
        )
        
        # Execute handler
        result = await handler.handle(message)
        
        assert executed == True
        assert result == {"result": "success"}
    
    @pytest.mark.asyncio
    async def test_message_handler_with_filter(self):
        """Test message handler with filter"""
        handled_messages = []
        
        async def handler_func(message):
            handled_messages.append(message)
            return {"success": True}
        
        handler = MessageHandler(
            name="test_handler",
            handler_type=MessageType.REQUEST,
            handler=handler_func,
            filter_type=MessageType.REQUEST,
        )
        
        # Test request message
        request_message = Message(
            sender="agent1",
            receiver="agent2",
            type=MessageType.REQUEST,
            content={"action": "test"},
        )
        
        result = await handler.handle(request_message)
        assert result is not None
        
        # Test notification message
        notification_message = Message(
            sender="agent1",
            receiver="agent2",
            type=MessageType.NOTIFICATION,
            content={"action": "test"},
        )
        
        result = await handler.handle(notification_message)
        # Should not handle notification
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
