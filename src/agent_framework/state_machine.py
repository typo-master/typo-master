"""
State Machine - Agent Behavior Orchestration

This module provides state machine implementation for agent behavior orchestration,
including state definitions, transitions, and event handling.
"""

import asyncio
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Set
from dataclasses import dataclass, field
import time

from .logger import get_logger

logger = get_logger(__name__)


class StateTransitionError(Exception):
    """Exception raised for invalid state transitions"""
    pass


@dataclass
class State:
    """Agent state definition"""
    name: str
    on_enter: Optional[Callable] = None
    on_exit: Optional[Callable] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Transition:
    """State transition definition"""
    from_state: str
    to_state: str
    event: str
    condition: Optional[Callable] = None
    action: Optional[Callable] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class StateMachine:
    """
    State machine for agent behavior orchestration
    
    Provides:
    - State definitions
    - Transition rules
    - Event handling
    - State persistence
    """
    
    def __init__(self, initial_state: str):
        """
        Initialize state machine
        
        Args:
            initial_state: Initial state name
        """
        self.states: Dict[str, State] = {}
        self.transitions: Dict[str, List[Transition]] = {}
        self.current_state: Optional[str] = None
        self.initial_state = initial_state
        self.history: List[str] = []
        self._lock = asyncio.Lock()
        self._event_handlers: Dict[str, List[Callable]] = {}
    
    def add_state(self, state: State) -> None:
        """
        Add a state to the machine
        
        Args:
            state: State to add
        """
        self.states[state.name] = state
        logger.debug(f"Added state: {state.name}")
    
    def add_transition(self, transition: Transition) -> None:
        """
        Add a transition to the machine
        
        Args:
            transition: Transition to add
        """
        key = f"{transition.from_state}:{transition.event}"
        
        if key not in self.transitions:
            self.transitions[key] = []
        
        self.transitions[key].append(transition)
        logger.debug(f"Added transition: {transition.from_state} --({transition.event})--> {transition.to_state}")
    
    async def initialize(self) -> None:
        """Initialize the state machine"""
        if self.initial_state not in self.states:
            raise ValueError(f"Initial state {self.initial_state} not defined")
        
        self.current_state = self.initial_state
        await self._on_state_enter(self.initial_state)
        logger.info(f"State machine initialized in state: {self.initial_state}")
    
    async def trigger_event(self, event: str, **kwargs) -> Optional[str]:
        """
        Trigger an event and perform state transition
        
        Args:
            event: Event to trigger
            **kwargs: Event data
            
        Returns:
            New state name or None if no transition occurred
        """
        async with self._lock:
            if not self.current_state:
                raise StateTransitionError("State machine not initialized")
            
            key = f"{self.current_state}:{event}"
            transitions = self.transitions.get(key, [])
            
            if not transitions:
                logger.debug(f"No transition for event '{event}' from state '{self.current_state}'")
                return None
            
            # Find matching transition
            for transition in transitions:
                # Check condition
                if transition.condition:
                    if not await transition.condition(**kwargs):
                        continue
                
                # Perform transition
                new_state = await self._perform_transition(transition, **kwargs)
                return new_state
            
            logger.debug(f"No matching transition for event '{event}' from state '{self.current_state}'")
            return None
    
    async def _perform_transition(self, transition: Transition, **kwargs) -> str:
        """
        Perform a state transition
        
        Args:
            transition: Transition to perform
            **kwargs: Event data
            
        Returns:
            New state name
        """
        old_state = self.current_state
        new_state = transition.to_state
        
        logger.info(f"Transitioning: {old_state} -> {new_state} (event: {transition.event})")
        
        # Exit old state
        await self._on_state_exit(old_state)
        
        # Perform transition action
        if transition.action:
            await transition.action(**kwargs)
        
        # Enter new state
        self.current_state = new_state
        self.history.append(new_state)
        await self._on_state_enter(new_state)
        
        return new_state
    
    async def _on_state_enter(self, state_name: str) -> None:
        """Handle state entry"""
        state = self.states.get(state_name)
        if state and state.on_enter:
            await state.on_enter()
    
    async def _on_state_exit(self, state_name: str) -> None:
        """Handle state exit"""
        state = self.states.get(state_name)
        if state and state.on_exit:
            await state.on_exit()
    
    def get_current_state(self) -> Optional[str]:
        """Get current state"""
        return self.current_state
    
    def get_state_history(self) -> List[str]:
        """Get state transition history"""
        return self.history.copy()
    
    def get_available_events(self) -> List[str]:
        """Get events that can be triggered from current state"""
        if not self.current_state:
            return []
        
        events = set()
        for key in self.transitions.keys():
            from_state, event = key.split(":")
            if from_state == self.current_state:
                events.add(event)
        
        return list(events)
    
    def register_event_handler(self, event: str, handler: Callable) -> None:
        """
        Register an event handler
        
        Args:
            event: Event name
            handler: Handler function
        """
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)
    
    async def emit_event(self, event: str, **kwargs) -> None:
        """
        Emit an event to registered handlers
        
        Args:
            event: Event name
            **kwargs: Event data
        """
        handlers = self._event_handlers.get(event, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(**kwargs)
                else:
                    handler(**kwargs)
            except Exception as e:
                logger.error(f"Error in event handler for '{event}': {e}")


class Workflow:
    """
    Workflow definition and execution
    
    Provides:
    - Workflow definition
    - Step execution
    - Error handling
    - Progress tracking
    """
    
    def __init__(self, name: str):
        """
        Initialize workflow
        
        Args:
            name: Workflow name
        """
        self.name = name
        self.steps: List[Dict[str, Any]] = []
        self.current_step: int = 0
        self.context: Dict[str, Any] = {}
        self._lock = asyncio.Lock()
    
    def add_step(self, name: str, action: Callable, condition: Optional[Callable] = None, **metadata) -> None:
        """
        Add a step to the workflow
        
        Args:
            name: Step name
            action: Step action
            condition: Optional condition for executing step
            **metadata: Step metadata
        """
        self.steps.append({
            "name": name,
            "action": action,
            "condition": condition,
            "metadata": metadata,
        })
        logger.debug(f"Added step to workflow '{self.name}': {name}")
    
    async def execute(self, initial_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute the workflow
        
        Args:
            initial_context: Initial context data
            
        Returns:
            Final context
        """
        if initial_context:
            self.context = initial_context.copy()
        
        async with self._lock:
            self.current_step = 0
            logger.info(f"Starting workflow: {self.name}")
            
            while self.current_step < len(self.steps):
                step = self.steps[self.current_step]
                
                # Check condition
                if step["condition"]:
                    if not await step["condition"](**self.context):
                        logger.debug(f"Skipping step '{step['name']}' due to condition")
                        self.current_step += 1
                        continue
                
                # Execute step
                logger.info(f"Executing step: {step['name']}")
                
                try:
                    result = await step["action"](**self.context)
                    
                    # Update context
                    if isinstance(result, dict):
                        self.context.update(result)
                    
                    self.current_step += 1
                
                except Exception as e:
                    logger.error(f"Error in step '{step['name']}': {e}")
                    raise
            
            logger.info(f"Workflow '{self.name}' completed")
            return self.context
    
    def get_progress(self) -> Dict[str, Any]:
        """Get workflow progress"""
        return {
            "name": self.name,
            "total_steps": len(self.steps),
            "current_step": self.current_step,
            "progress": self.current_step / len(self.steps) if self.steps else 0.0,
            "current_step_name": self.steps[self.current_step]["name"] if self.current_step < len(self.steps) else None,
        }
    
    def reset(self) -> None:
        """Reset workflow"""
        self.current_step = 0
        self.context = {}
        logger.debug(f"Reset workflow: {self.name}")


class Orchestrator:
    """
    Orchestrates multiple agents and workflows
    
    Provides:
    - Agent coordination
    - Workflow execution
    - Dependency management
    - Error handling
    """
    
    def __init__(self):
        """Initialize orchestrator"""
        self.agents: Dict[str, Any] = {}
        self.workflows: Dict[str, Workflow] = {}
        self.dependencies: Dict[str, List[str]] = {}
        self._lock = asyncio.Lock()
    
    def register_agent(self, agent_id: str, agent: Any) -> None:
        """
        Register an agent
        
        Args:
            agent_id: Agent ID
            agent: Agent instance
        """
        self.agents[agent_id] = agent
        logger.debug(f"Registered agent: {agent_id}")
    
    def register_workflow(self, workflow: Workflow) -> None:
        """
        Register a workflow
        
        Args:
            workflow: Workflow instance
        """
        self.workflows[workflow.name] = workflow
        logger.debug(f"Registered workflow: {workflow.name}")
    
    def add_dependency(self, workflow_name: str, agent_id: str) -> None:
        """
        Add a dependency between workflow and agent
        
        Args:
            workflow_name: Workflow name
            agent_id: Agent ID
        """
        if workflow_name not in self.dependencies:
            self.dependencies[workflow_name] = []
        self.dependencies[workflow_name].append(agent_id)
        logger.debug(f"Added dependency: {workflow_name} -> {agent_id}")
    
    async def execute_workflow(self, workflow_name: str, **kwargs) -> Dict[str, Any]:
        """
        Execute a workflow
        
        Args:
            workflow_name: Workflow name
            **kwargs: Execution parameters
            
        Returns:
            Execution result
        """
        workflow = self.workflows.get(workflow_name)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_name}")
        
        # Ensure dependencies are ready
        dependencies = self.dependencies.get(workflow_name, [])
        for agent_id in dependencies:
            agent = self.agents.get(agent_id)
            if agent and hasattr(agent, 'get_status'):
                status = await agent.get_status()
                if status.get('state') != 'running':
                    logger.warning(f"Agent {agent_id} is not running")
        
        # Execute workflow
        return await workflow.execute(**kwargs)
    
    def get_agent(self, agent_id: str) -> Optional[Any]:
        """Get an agent by ID"""
        return self.agents.get(agent_id)
    
    def get_workflow(self, workflow_name: str) -> Optional[Workflow]:
        """Get a workflow by name"""
        return self.workflows.get(workflow_name)
    
    def list_agents(self) -> List[str]:
        """List all registered agents"""
        return list(self.agents.keys())
    
    def list_workflows(self) -> List[str]:
        """List all registered workflows"""
        return list(self.workflows.keys())
