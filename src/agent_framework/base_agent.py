"""
Base Agent Module - Core Agent Framework

This module provides the abstract base class for all agents in the system,
defining the standard interface and lifecycle management.
"""

import asyncio
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, TypeVar, Generic
from datetime import datetime
import json
import traceback

from .message import Message, MessageType
from .tool_system import ToolRegistry
from .context import ContextManager
from .state import StateManager
from .logger import get_logger

logger = get_logger(__name__)


class AgentState(Enum):
    """Agent lifecycle states"""
    INITIALIZING = "initializing"
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class AgentPriority(Enum):
    """Agent task priority levels"""
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3


@dataclass
class AgentConfig:
    """Agent configuration"""
    name: str
    version: str = "1.0.0"
    description: str = ""
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: float = 300.0
    enable_persistence: bool = True
    enable_monitoring: bool = True
    enable_caching: bool = True
    log_level: str = "INFO"
    custom_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentMetrics:
    """Agent performance metrics"""
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    total_execution_time: float = 0.0
    average_execution_time: float = 0.0
    last_execution_time: Optional[float] = None
    error_rate: float = 0.0
    uptime: float = 0.0
    start_time: Optional[float] = None
    last_activity: Optional[float] = None


class BaseAgent(ABC):
    """
    Abstract base class for all agents
    
    Provides:
    - Lifecycle management (init, start, stop, cleanup)
    - Message handling and routing
    - State management
    - Tool integration
    - Error handling and recovery
    - Metrics collection
    """
    
    def __init__(self, config: AgentConfig):
        """
        Initialize the agent
        
        Args:
            config: Agent configuration
        """
        self.config = config
        self.agent_id = str(uuid.uuid4())
        self.state = AgentState.INITIALIZING
        self.metrics = AgentMetrics()
        
        # Core components
        self.tool_registry = ToolRegistry()
        self.context_manager = ContextManager()
        self.state_manager = StateManager(self.agent_id, enable_persistence=config.enable_persistence)
        
        # Message handlers
        self.message_handlers: Dict[MessageType, List[Callable]] = {}
        
        # Task queue
        self.task_queue = asyncio.Queue()
        self.current_task: Optional[Any] = None
        
        # Event loop
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._shutdown_event = asyncio.Event()
        
        # Locks
        self._state_lock = asyncio.Lock()
        self._task_lock = asyncio.Lock()
        
        logger.info(f"Agent {self.config.name} ({self.agent_id}) initialized")
    
    async def initialize(self) -> None:
        """
        Initialize the agent
        
        This method should be called after construction to complete initialization.
        Subclasses can override this to perform custom initialization.
        """
        logger.info(f"Initializing agent {self.config.name}")
        
        # Register default tools
        await self._register_default_tools()
        
        # Register default message handlers
        self._register_default_handlers()
        
        # Load previous state if available
        if self.config.enable_persistence:
            await self.state_manager.load_state()
        
        # Custom initialization
        await self.on_initialize()
        
        self.state = AgentState.IDLE
        logger.info(f"Agent {self.config.name} initialized successfully")
    
    async def start(self) -> None:
        """
        Start the agent
        
        Begins processing tasks and handling messages.
        """
        logger.info(f"Starting agent {self.config.name}")
        
        async with self._state_lock:
            if self.state == AgentState.RUNNING:
                logger.warning(f"Agent {self.config.name} is already running")
                return
            
            self.state = AgentState.RUNNING
            self.metrics.start_time = time.time()
        
        # Start background tasks
        self._loop = asyncio.get_running_loop()
        asyncio.create_task(self._process_tasks())
        asyncio.create_task(self._monitor_health())
        
        await self.on_start()
        logger.info(f"Agent {self.config.name} started")
    
    async def stop(self, timeout: float = 30.0) -> None:
        """
        Stop the agent gracefully
        
        Args:
            timeout: Maximum time to wait for tasks to complete
        """
        logger.info(f"Stopping agent {self.config.name}")
        
        async with self._state_lock:
            if self.state == AgentState.STOPPED:
                logger.warning(f"Agent {self.config.name} is already stopped")
                return
            
            self.state = AgentState.STOPPING
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Wait for tasks to complete
        try:
            await asyncio.wait_for(self._wait_for_tasks(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Agent {self.config.name} did not complete all tasks within {timeout}s")
        
        # Save state
        if self.config.enable_persistence:
            await self.state_manager.save_state()
        
        # Cleanup
        await self.on_stop()
        
        async with self._state_lock:
            self.state = AgentState.STOPPED
        
        logger.info(f"Agent {self.config.name} stopped")
    
    async def pause(self) -> None:
        """Pause the agent"""
        logger.info(f"Pausing agent {self.config.name}")
        
        async with self._state_lock:
            if self.state != AgentState.RUNNING:
                logger.warning(f"Agent {self.config.name} is not running")
                return
            
            self.state = AgentState.PAUSED
        
        await self.on_pause()
        logger.info(f"Agent {self.config.name} paused")
    
    async def resume(self) -> None:
        """Resume the agent"""
        logger.info(f"Resuming agent {self.config.name}")
        
        async with self._state_lock:
            if self.state != AgentState.PAUSED:
                logger.warning(f"Agent {self.config.name} is not paused")
                return
            
            self.state = AgentState.RUNNING
        
        await self.on_resume()
        logger.info(f"Agent {self.config.name} resumed")
    
    async def send_message(self, message: Message) -> Optional[Message]:
        """
        Send a message to this agent
        
        Args:
            message: Message to send
            
        Returns:
            Optional response message
        """
        logger.debug(f"Agent {self.config.name} received message: {message.type}")
        
        try:
            handlers = self.message_handlers.get(message.type, [])
            
            if not handlers:
                logger.warning(f"No handlers for message type: {message.type}")
                return None
            
            response = None
            for handler in handlers:
                try:
                    result = await handler(message)
                    if result:
                        response = result
                except Exception as e:
                    logger.error(f"Error in message handler: {e}")
                    traceback.print_exc()
            
            return response
        
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            traceback.print_exc()
            return None
    
    async def submit_task(self, task: Any, priority: AgentPriority = AgentPriority.MEDIUM) -> None:
        """
        Submit a task to the agent
        
        Args:
            task: Task to execute
            priority: Task priority
        """
        logger.debug(f"Submitting task to agent {self.config.name}")
        
        task_data = {
            "task": task,
            "priority": priority,
            "submitted_at": time.time(),
        }
        
        await self.task_queue.put((priority.value, task_data))
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the agent
        
        Returns:
            Dictionary containing agent status information
        """
        uptime = 0.0
        if self.metrics.start_time:
            uptime = time.time() - self.metrics.start_time
        
        return {
            "agent_id": self.agent_id,
            "name": self.config.name,
            "version": self.config.version,
            "state": self.state.value,
            "metrics": {
                "total_tasks": self.metrics.total_tasks,
                "successful_tasks": self.metrics.successful_tasks,
                "failed_tasks": self.metrics.failed_tasks,
                "error_rate": self.metrics.error_rate,
                "average_execution_time": self.metrics.average_execution_time,
                "uptime": uptime,
            },
            "queue_size": self.task_queue.qsize(),
        }
    
    # Abstract methods that subclasses must implement
    
    @abstractmethod
    async def on_initialize(self) -> None:
        """
        Called during agent initialization
        
        Subclasses should override this to perform custom initialization.
        """
        pass
    
    @abstractmethod
    async def on_start(self) -> None:
        """
        Called when the agent starts
        
        Subclasses should override this to perform custom start logic.
        """
        pass
    
    @abstractmethod
    async def on_stop(self) -> None:
        """
        Called when the agent stops
        
        Subclasses should override this to perform custom cleanup.
        """
        pass
    
    @abstractmethod
    async def on_pause(self) -> None:
        """
        Called when the agent is paused
        
        Subclasses should override this to perform custom pause logic.
        """
        pass
    
    @abstractmethod
    async def on_resume(self) -> None:
        """
        Called when the agent resumes
        
        Subclasses should override this to perform custom resume logic.
        """
        pass
    
    @abstractmethod
    async def process_task(self, task: Any) -> Any:
        """
        Process a single task
        
        Args:
            task: Task to process
            
        Returns:
            Task result
        """
        pass
    
    # Protected methods
    
    async def _process_tasks(self) -> None:
        """Background task that processes the task queue"""
        logger.info(f"Starting task processor for agent {self.config.name}")
        
        while not self._shutdown_event.is_set():
            try:
                # Check if agent is running
                if self.state != AgentState.RUNNING:
                    await asyncio.sleep(0.1)
                    continue
                
                # Get next task with timeout
                try:
                    priority, task_data = await asyncio.wait_for(
                        self.task_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Process task
                task = task_data["task"]
                self.current_task = task
                
                start_time = time.time()
                
                try:
                    result = await self._execute_task(task)
                    
                    # Update metrics
                    self.metrics.total_tasks += 1
                    self.metrics.successful_tasks += 1
                    execution_time = time.time() - start_time
                    self.metrics.total_execution_time += execution_time
                    self.metrics.average_execution_time = (
                        self.metrics.total_execution_time / self.metrics.total_tasks
                    )
                    self.metrics.last_execution_time = execution_time
                    self.metrics.last_activity = time.time()
                    
                    logger.debug(f"Task completed successfully in {execution_time:.2f}s")
                
                except Exception as e:
                    logger.error(f"Task execution failed: {e}")
                    traceback.print_exc()
                    
                    # Update metrics
                    self.metrics.total_tasks += 1
                    self.metrics.failed_tasks += 1
                    
                    # Retry logic
                    retries = task_data.get("retries", 0)
                    if retries < self.config.max_retries:
                        task_data["retries"] = retries + 1
                        await asyncio.sleep(self.config.retry_delay)
                        await self.task_queue.put((priority, task_data))
                
                finally:
                    self.current_task = None
                    self.task_queue.task_done()
            
            except Exception as e:
                logger.error(f"Error in task processor: {e}")
                traceback.print_exc()
                await asyncio.sleep(1.0)
        
        logger.info(f"Task processor stopped for agent {self.config.name}")
    
    async def _execute_task(self, task: Any) -> Any:
        """
        Execute a task with timeout and error handling
        
        Args:
            task: Task to execute
            
        Returns:
            Task result
        """
        try:
            result = await asyncio.wait_for(
                self.process_task(task),
                timeout=self.config.timeout
            )
            return result
        except asyncio.TimeoutError:
            raise TimeoutError(f"Task execution timed out after {self.config.timeout}s")
    
    async def _wait_for_tasks(self) -> None:
        """Wait for all tasks to complete"""
        while not self.task_queue.empty() or self.current_task is not None:
            await asyncio.sleep(0.1)
    
    async def _monitor_health(self) -> None:
        """Monitor agent health and update metrics"""
        while not self._shutdown_event.is_set():
            try:
                if self.state == AgentState.RUNNING:
                    # Update error rate
                    if self.metrics.total_tasks > 0:
                        self.metrics.error_rate = (
                            self.metrics.failed_tasks / self.metrics.total_tasks
                        )
                    
                    # Update uptime
                    if self.metrics.start_time:
                        self.metrics.uptime = time.time() - self.metrics.start_time
                
                await asyncio.sleep(60.0)  # Check every minute
            
            except Exception as e:
                logger.error(f"Error in health monitor: {e}")
                await asyncio.sleep(1.0)
    
    def _register_default_handlers(self) -> None:
        """Register default message handlers"""
        self.register_handler(MessageType.STATUS, self._handle_status_message)
        self.register_handler(MessageType.SHUTDOWN, self._handle_shutdown_message)
    
    async def _handle_status_message(self, message: Message) -> Message:
        """Handle status request messages"""
        status = await self.get_status()
        return Message(
            type=MessageType.RESPONSE,
            sender=self.agent_id,
            receiver=message.sender,
            content=status,
        )
    
    async def _handle_shutdown_message(self, message: Message) -> Message:
        """Handle shutdown messages"""
        logger.info(f"Received shutdown request from {message.sender}")
        asyncio.create_task(self.stop())
        return Message(
            type=MessageType.RESPONSE,
            sender=self.agent_id,
            receiver=message.sender,
            content={"status": "shutdown_initiated"},
        )
    
    async def _register_default_tools(self) -> None:
        """Register default tools"""
        # Subclasses can override this
        pass
    
    def register_handler(self, message_type: MessageType, handler: Callable) -> None:
        """
        Register a message handler
        
        Args:
            message_type: Type of message to handle
            handler: Handler function
        """
        if message_type not in self.message_handlers:
            self.message_handlers[message_type] = []
        self.message_handlers[message_type].append(handler)
        logger.debug(f"Registered handler for {message_type}")
