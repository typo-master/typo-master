"""
Message System - Agent Communication Protocol

This module provides the message protocol for agent-to-agent communication,
including message types, serialization, and handling.
"""

import json
import uuid
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
import asyncio

from .logger import get_logger

logger = get_logger(__name__)


class MessageType(Enum):
    """Standard message types"""
    REQUEST = "request"
    RESPONSE = "response"
    EVENT = "event"
    ERROR = "error"
    STATUS = "status"
    SHUTDOWN = "shutdown"
    TASK = "task"
    RESULT = "result"
    NOTIFICATION = "notification"
    QUERY = "query"
    COMMAND = "command"


@dataclass
class Message:
    """
    Standard message format for agent communication
    
    Attributes:
        type: Message type
        sender: Sender agent ID
        receiver: Receiver agent ID (or None for broadcast)
        content: Message content
        message_id: Unique message ID
        timestamp: Message timestamp
        correlation_id: ID for correlating request/response pairs
        headers: Additional metadata
        reply_to: Message ID to reply to (if any)
    """
    type: MessageType
    sender: str
    receiver: Optional[str] = None
    content: Any = None
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    correlation_id: Optional[str] = None
    headers: Dict[str, Any] = field(default_factory=dict)
    reply_to: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary"""
        return {
            "type": self.type.value,
            "sender": self.sender,
            "receiver": self.receiver,
            "content": self.content,
            "message_id": self.message_id,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
            "headers": self.headers,
            "reply_to": self.reply_to,
        }
    
    def to_json(self) -> str:
        """Convert message to JSON string"""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create message from dictionary"""
        return cls(
            type=MessageType(data["type"]),
            sender=data["sender"],
            receiver=data.get("receiver"),
            content=data.get("content"),
            message_id=data.get("message_id"),
            timestamp=data.get("timestamp"),
            correlation_id=data.get("correlation_id"),
            headers=data.get("headers", {}),
            reply_to=data.get("reply_to"),
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> "Message":
        """Create message from JSON string"""
        return cls.from_dict(json.loads(json_str))
    
    def create_response(self, content: Any) -> "Message":
        """
        Create a response message to this message
        
        Args:
            content: Response content
            
        Returns:
            Response message
        """
        return Message(
            type=MessageType.RESPONSE,
            sender=self.receiver or "unknown",
            receiver=self.sender,
            content=content,
            correlation_id=self.message_id,
            reply_to=self.message_id,
        )
    
    def create_error(self, error: str) -> "Message":
        """
        Create an error message in response to this message
        
        Args:
            error: Error message
            
        Returns:
            Error message
        """
        return Message(
            type=MessageType.ERROR,
            sender=self.receiver or "unknown",
            receiver=self.sender,
            content={"error": error},
            correlation_id=self.message_id,
            reply_to=self.message_id,
        )


class MessageHandler:
    """
    Message handler with filtering and routing capabilities
    """
    
    def __init__(self):
        self.handlers: Dict[str, List[Callable]] = {}
        self.filters: Dict[str, List[Callable]] = {}
        self.middleware: List[Callable] = []
    
    def register_handler(
        self,
        message_type: MessageType,
        handler: Callable,
        filter_func: Optional[Callable] = None,
    ) -> None:
        """
        Register a message handler
        
        Args:
            message_type: Type of message to handle
            handler: Handler function
            filter_func: Optional filter function
        """
        type_key = message_type.value
        
        if type_key not in self.handlers:
            self.handlers[type_key] = []
            self.filters[type_key] = []
        
        self.handlers[type_key].append(handler)
        if filter_func:
            self.filters[type_key].append(filter_func)
        
        logger.debug(f"Registered handler for {message_type}")
    
    def register_middleware(self, middleware: Callable) -> None:
        """
        Register middleware for message processing
        
        Args:
            middleware: Middleware function
        """
        self.middleware.append(middleware)
        logger.debug("Registered middleware")
    
    async def handle(self, message: Message) -> Optional[Message]:
        """
        Handle a message through registered handlers and middleware
        
        Args:
            message: Message to handle
            
        Returns:
            Optional response message
        """
        type_key = message.type.value
        
        # Apply middleware
        for middleware in self.middleware:
            try:
                message = await middleware(message)
                if message is None:
                    return None
            except Exception as e:
                logger.error(f"Middleware error: {e}")
                return message.create_error(f"Middleware error: {str(e)}")
        
        # Get handlers for this message type
        handlers = self.handlers.get(type_key, [])
        filters = self.filters.get(type_key, [])
        
        if not handlers:
            logger.warning(f"No handlers for message type: {type_key}")
            return None
        
        # Apply filters
        for filter_func in filters:
            try:
                if not filter_func(message):
                    logger.debug(f"Message filtered out by filter")
                    return None
            except Exception as e:
                logger.error(f"Filter error: {e}")
                continue
        
        # Call handlers
        response = None
        for handler in handlers:
            try:
                result = await handler(message)
                if result:
                    response = result
            except Exception as e:
                logger.error(f"Handler error: {e}")
                response = message.create_error(f"Handler error: {str(e)}")
        
        return response


class MessageBus:
    """
    Central message bus for agent communication
    
    Provides pub/sub messaging, routing, and message queuing.
    """
    
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}
        self.queues: Dict[str, asyncio.Queue] = {}
        self.message_history: List[Message] = []
        self.max_history = 1000
    
    def subscribe(self, agent_id: str, handler: Callable) -> None:
        """
        Subscribe an agent to receive messages
        
        Args:
            agent_id: Agent ID
            handler: Message handler function
        """
        if agent_id not in self.subscribers:
            self.subscribers[agent_id] = []
        self.subscribers[agent_id].append(handler)
        logger.debug(f"Agent {agent_id} subscribed to message bus")
    
    def unsubscribe(self, agent_id: str) -> None:
        """
        Unsubscribe an agent
        
        Args:
            agent_id: Agent ID
        """
        if agent_id in self.subscribers:
            del self.subscribers[agent_id]
            logger.debug(f"Agent {agent_id} unsubscribed from message bus")
    
    async def publish(self, message: Message) -> None:
        """
        Publish a message to all subscribers
        
        Args:
            message: Message to publish
        """
        logger.debug(f"Publishing message: {message.type} from {message.sender}")
        
        # Add to history
        self.message_history.append(message)
        if len(self.message_history) > self.max_history:
            self.message_history.pop(0)
        
        # Send to subscribers
        if message.receiver:
            # Direct message to specific receiver
            handlers = self.subscribers.get(message.receiver, [])
            for handler in handlers:
                try:
                    asyncio.create_task(handler(message))
                except Exception as e:
                    logger.error(f"Error delivering message to {message.receiver}: {e}")
        else:
            # Broadcast to all subscribers
            for agent_id, handlers in self.subscribers.items():
                if agent_id != message.sender:  # Don't send to sender
                    for handler in handlers:
                        try:
                            asyncio.create_task(handler(message))
                        except Exception as e:
                            logger.error(f"Error delivering message to {agent_id}: {e}")
    
    async def send(self, message: Message) -> Optional[Message]:
        """
        Send a message and wait for response
        
        Args:
            message: Message to send
            
        Returns:
            Optional response message
        """
        if not message.receiver:
            raise ValueError("Message must have a receiver for send()")
        
        # Create response queue
        response_queue = asyncio.Queue()
        response_queue_key = f"{message.sender}:{message.message_id}"
        self.queues[response_queue_key] = response_queue
        
        # Subscribe to response
        async def response_handler(msg: Message):
            if msg.correlation_id == message.message_id:
                await response_queue.put(msg)
        
        self.subscribe(message.sender, response_handler)
        
        # Send message
        await self.publish(message)
        
        # Wait for response
        try:
            response = await asyncio.wait_for(response_queue.get(), timeout=30.0)
            return response
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for response to {message.message_id}")
            return None
        finally:
            # Cleanup
            self.unsubscribe(message.sender)
            if response_queue_key in self.queues:
                del self.queues[response_queue_key]
    
    def get_history(self, agent_id: Optional[str] = None, limit: int = 100) -> List[Message]:
        """
        Get message history
        
        Args:
            agent_id: Optional agent ID to filter by
            limit: Maximum number of messages to return
            
        Returns:
            List of messages
        """
        messages = self.message_history
        
        if agent_id:
            messages = [m for m in messages if m.sender == agent_id or m.receiver == agent_id]
        
        return messages[-limit:]
    
    def clear_history(self) -> None:
        """Clear message history"""
        self.message_history.clear()
        logger.debug("Message history cleared")
