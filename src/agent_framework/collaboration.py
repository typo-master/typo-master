"""
Agent Collaboration and Conflict Resolution
"""

import asyncio
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

from .logger import get_logger

logger = get_logger(__name__)


class ConflictType(Enum):
    """Types of conflicts"""
    RESOURCE = "resource"
    DATA = "data"
    OPINION = "opinion"
    TIMING = "timing"
    PRIORITY = "priority"


@dataclass
class Conflict:
    """Conflict information"""
    id: str
    type: ConflictType
    agents: List[str]
    description: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: __import__('time').time())
    resolved: bool = False


class CollaborationMode(Enum):
    """Collaboration modes"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HIERARCHICAL = "hierarchical"
    PEER_TO_PEER = "peer_to_peer"


class CollaborationManager:
    """
    Manager for agent collaboration
    
    Provides:
    - Agent coordination
    - Task distribution
    - Conflict detection
    - Conflict resolution
    """
    
    def __init__(self):
        """Initialize collaboration manager"""
        self.agents: Dict[str, Any] = {}
        self.conflicts: List[Conflict] = []
        self.resolutions: Dict[str, Callable] = {}
        self.collaboration_mode = CollaborationMode.SEQUENTIAL
        self._lock = asyncio.Lock()
    
    def register_agent(self, agent_id: str, agent: Any) -> None:
        """
        Register an agent
        
        Args:
            agent_id: Agent ID
            agent: Agent instance
        """
        self.agents[agent_id] = agent
        logger.info(f"Registered agent: {agent_id}")
    
    def unregister_agent(self, agent_id: str) -> None:
        """
        Unregister an agent
        
        Args:
            agent_id: Agent ID
        """
        if agent_id in self.agents:
            del self.agents[agent_id]
            logger.info(f"Unregistered agent: {agent_id}")
    
    def set_collaboration_mode(self, mode: CollaborationMode) -> None:
        """
        Set collaboration mode
        
        Args:
            mode: Collaboration mode
        """
        self.collaboration_mode = mode
        logger.info(f"Set collaboration mode: {mode}")
    
    async def detect_conflicts(self) -> List[Conflict]:
        """
        Detect conflicts between agents
        
        Returns:
            List of conflicts
        """
        conflicts = []
        
        # Check for resource conflicts
        resource_usage = defaultdict(list)
        for agent_id, agent in self.agents.items():
            if hasattr(agent, 'get_resources'):
                resources = agent.get_resources()
                for resource in resources:
                    resource_usage[resource].append(agent_id)
        
        for resource, agents in resource_usage.items():
            if len(agents) > 1:
                conflict = Conflict(
                    id=f"resource_{resource}",
                    type=ConflictType.RESOURCE,
                    agents=agents,
                    description=f"Multiple agents using resource: {resource}",
                    data={"resource": resource}
                )
                conflicts.append(conflict)
        
        # Check for data conflicts
        data_access = defaultdict(list)
        for agent_id, agent in self.agents.items():
            if hasattr(agent, 'get_data_access'):
                data = agent.get_data_access()
                for item in data:
                    data_access[item].append(agent_id)
        
        for item, agents in data_access.items():
            if len(agents) > 1:
                conflict = Conflict(
                    id=f"data_{item}",
                    type=ConflictType.DATA,
                    agents=agents,
                    description=f"Multiple agents accessing data: {item}",
                    data={"data": item}
                )
                conflicts.append(conflict)
        
        self.conflicts.extend(conflicts)
        return conflicts
    
    async def resolve_conflict(self, conflict: Conflict) -> bool:
        """
        Resolve a conflict
        
        Args:
            conflict: Conflict to resolve
            
        Returns:
            True if resolved
        """
        resolution_func = self.resolutions.get(conflict.type.value)
        
        if resolution_func:
            try:
                result = await resolution_func(conflict)
                conflict.resolved = True
                return result
            except Exception as e:
                logger.error(f"Conflict resolution failed: {e}")
                return False
        
        # Default resolution: sequential access
        return await self._default_resolution(conflict)
    
    async def _default_resolution(self, conflict: Conflict) -> bool:
        """Default conflict resolution"""
        if conflict.type == ConflictType.RESOURCE:
            # Implement resource locking
            logger.info(f"Implementing resource locking for {conflict.data.get('resource')}")
            return True
        
        elif conflict.type == ConflictType.DATA:
            # Implement data locking
            logger.info(f"Implementing data locking for {conflict.data.get('data')}")
            return True
        
        return False
    
    def register_resolution(self, conflict_type: ConflictType, resolver: Callable) -> None:
        """
        Register a conflict resolver
        
        Args:
            conflict_type: Conflict type
            resolver: Resolver function
        """
        self.resolutions[conflict_type.value] = resolver
        logger.info(f"Registered resolver for: {conflict_type}")
    
    async def coordinate_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Coordinate task execution among agents
        
        Args:
            task: Task to execute
            
        Returns:
            Task result
        """
        if self.collaboration_mode == CollaborationMode.SEQUENTIAL:
            return await self._sequential_coordination(task)
        elif self.collaboration_mode == CollaborationMode.PARALLEL:
            return await self._parallel_coordination(task)
        elif self.collaboration_mode == CollaborationMode.HIERARCHICAL:
            return await self._hierarchical_coordination(task)
        elif self.collaboration_mode == CollaborationMode.PEER_TO_PEER:
            return await self._peer_to_peer_coordination(task)
        else:
            return {"error": "Unknown collaboration mode"}
    
    async def _sequential_coordination(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Sequential task coordination"""
        results = {}
        
        for agent_id, agent in self.agents.items():
            if hasattr(agent, 'process_task'):
                try:
                    result = await agent.process_task(task)
                    results[agent_id] = result
                except Exception as e:
                    logger.error(f"Agent {agent_id} failed: {e}")
                    results[agent_id] = {"error": str(e)}
        
        return {"results": results}
    
    async def _parallel_coordination(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Parallel task coordination"""
        tasks = []
        
        for agent_id, agent in self.agents.items():
            if hasattr(agent, 'process_task'):
                tasks.append(self._run_agent_task(agent_id, agent, task))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {"results": results}
    
    async def _run_agent_task(self, agent_id: str, agent: Any, task: Dict[str, Any]):
        """Run task for a single agent"""
        try:
            result = await agent.process_task(task)
            return {"agent": agent_id, "result": result}
        except Exception as e:
            logger.error(f"Agent {agent_id} failed: {e}")
            return {"agent": agent_id, "error": str(e)}
    
    async def _hierarchical_coordination(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Hierarchical task coordination"""
        # Find coordinator agent
        coordinator = None
        for agent_id, agent in self.agents.items():
            if hasattr(agent, 'is_coordinator') and agent.is_coordinator():
                coordinator = agent
                break
        
        if coordinator and hasattr(coordinator, 'coordinate'):
            return await coordinator.coordinate(task, self.agents)
        
        # Fallback to sequential
        return await self._sequential_coordination(task)
    
    async def _peer_to_peer_coordination(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Peer-to-peer task coordination"""
        # Agents communicate directly
        results = {}
        
        for agent_id, agent in self.agents.items():
            if hasattr(agent, 'process_task'):
                try:
                    result = await agent.process_task(task)
                    results[agent_id] = result
                except Exception as e:
                    logger.error(f"Agent {agent_id} failed: {e}")
                    results[agent_id] = {"error": str(e)}
        
        return {"results": results}
    
    def get_conflicts(self) -> List[Conflict]:
        """Get all conflicts"""
        return self.conflicts
    
    def get_active_conflicts(self) -> List[Conflict]:
        """Get unresolved conflicts"""
        return [c for c in self.conflicts if not c.resolved]


class ConsensusManager:
    """
    Manager for consensus among agents
    
    Provides:
    - Voting mechanisms
    - Consensus algorithms
    - Conflict arbitration
    """
    
    def __init__(self):
        """Initialize consensus manager"""
        self.votes: Dict[str, List[str]] = {}
        self.decisions: Dict[str, Any] = {}
    
    async def vote(self, proposal_id: str, agent_id: str, vote: str) -> None:
        """
        Cast a vote
        
        Args:
            proposal_id: Proposal ID
            agent_id: Agent ID
            vote: Vote value
        """
        if proposal_id not in self.votes:
            self.votes[proposal_id] = []
        
        self.votes[proposal_id].append({"agent": agent_id, "vote": vote})
        logger.info(f"Vote cast: {agent_id} -> {vote} for {proposal_id}")
    
    async def get_consensus(self, proposal_id: str, threshold: float = 0.5) -> Optional[str]:
        """
        Get consensus for a proposal
        
        Args:
            proposal_id: Proposal ID
            threshold: Consensus threshold
            
        Returns:
            Consensus decision or None
        """
        if proposal_id not in self.votes:
            return None
        
        votes = self.votes[proposal_id]
        
        if not votes:
            return None
        
        # Count votes
        vote_counts = defaultdict(int)
        for vote in votes:
            vote_counts[vote["vote"]] += 1
        
        total = len(votes)
        
        # Check for consensus
        for vote_value, count in vote_counts.items():
            if count / total >= threshold:
                self.decisions[proposal_id] = vote_value
                return vote_value
        
        return None
    
    async def propose(self, proposal_id: str, proposer: str, proposal: Any) -> None:
        """
        Propose a decision
        
        Args:
            proposal_id: Proposal ID
            proposer: Proposer ID
            proposal: Proposal content
        """
        logger.info(f"Proposal: {proposer} -> {proposal_id}")
        # In a real system, this would broadcast to all agents


def get_collaboration_manager() -> CollaborationManager:
    """Get global collaboration manager instance"""
    if not hasattr(get_collaboration_manager, "_instance"):
        get_collaboration_manager._instance = CollaborationManager()
    return get_collaboration_manager._instance


def get_consensus_manager() -> ConsensusManager:
    """Get global consensus manager instance"""
    if not hasattr(get_consensus_manager, "_instance"):
        get_consensus_manager._instance = ConsensusManager()
    return get_consensus_manager._instance
