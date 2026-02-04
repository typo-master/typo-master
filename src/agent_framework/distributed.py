"""
Distributed Agent System Support
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

from .logger import get_logger

logger = get_logger(__name__)


class NodeStatus(Enum):
    """Node status"""
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    ERROR = "error"


@dataclass
class Node:
    """Cluster node"""
    id: str
    host: str
    port: int
    status: NodeStatus = NodeStatus.ONLINE
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_heartbeat: float = field(default_factory=lambda: __import__('time').time())


class ClusterManager:
    """
    Manager for distributed agent clusters
    
    Provides:
    - Node management
    - Load balancing
    - Failover handling
    - Cluster coordination
    """
    
    def __init__(self):
        """Initialize cluster manager"""
        self.nodes: Dict[str, Node] = {}
        self.leader: Optional[str] = None
        self._lock = asyncio.Lock()
    
    async def add_node(
        self,
        node_id: str,
        host: str,
        port: int,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """
        Add a node to the cluster
        
        Args:
            node_id: Node ID
            host: Host address
            port: Port number
            metadata: Node metadata
            
        Returns:
            True if added
        """
        async with self._lock:
            if node_id in self.nodes:
                logger.warning(f"Node already exists: {node_id}")
                return False
            
            node = Node(
                id=node_id,
                host=host,
                port=port,
                metadata=metadata or {}
            )
            
            self.nodes[node_id] = node
            
            # Elect leader if needed
            if not self.leader:
                self.leader = node_id
            
            logger.info(f"Added node: {node_id} at {host}:{port}")
            return True
    
    async def remove_node(self, node_id: str) -> bool:
        """
        Remove a node from the cluster
        
        Args:
            node_id: Node ID
            
        Returns:
            True if removed
        """
        async with self._lock:
            if node_id not in self.nodes:
                return False
            
            del self.nodes[node_id]
            
            # Re-elect leader if needed
            if self.leader == node_id:
                self.leader = None
                if self.nodes:
                    self.leader = list(self.nodes.keys())[0]
            
            logger.info(f"Removed node: {node_id}")
            return True
    
    async def update_heartbeat(self, node_id: str) -> bool:
        """
        Update node heartbeat
        
        Args:
            node_id: Node ID
            
        Returns:
            True if updated
        """
        async with self._lock:
            node = self.nodes.get(node_id)
            
            if not node:
                return False
            
            node.last_heartbeat = __import__('time').time()
            node.status = NodeStatus.ONLINE
            
            return True
    
    async def check_node_health(self, timeout: float = 60.0) -> List[str]:
        """
        Check node health
        
        Args:
            timeout: Heartbeat timeout
            
        Returns:
            List of unhealthy node IDs
        """
        current_time = __import__('time').time()
        unhealthy = []
        
        for node_id, node in self.nodes.items():
            if current_time - node.last_heartbeat > timeout:
                node.status = NodeStatus.OFFLINE
                unhealthy.append(node_id)
            elif node.status == NodeStatus.BUSY:
                # Check if still busy
                pass
        
        return unhealthy
    
    def get_leader(self) -> Optional[str]:
        """Get cluster leader"""
        return self.leader
    
    def get_nodes(self, status: Optional[NodeStatus] = None) -> List[Node]:
        """
        Get cluster nodes
        
        Args:
            status: Filter by status
            
        Returns:
            List of nodes
        """
        nodes = list(self.nodes.values())
        
        if status:
            nodes = [n for n in nodes if n.status == status]
        
        return nodes
    
    def get_node(self, node_id: str) -> Optional[Node]:
        """Get node by ID"""
        return self.nodes.get(node_id)


class LoadBalancer:
    """
    Load balancer for distributed agents
    
    Provides:
    - Round-robin balancing
    - Least-connections balancing
    - Weighted balancing
    """
    
    def __init__(self):
        """Initialize load balancer"""
        self.current_index = 0
        self.connections: Dict[str, int] = defaultdict(int)
    
    def select_node(
        self,
        nodes: List[Node],
        strategy: str = "round_robin"
    ) -> Optional[Node]:
        """
        Select a node based on strategy
        
        Args:
            nodes: Available nodes
            strategy: Balancing strategy
            
        Returns:
            Selected node or None
        """
        if not nodes:
            return None
        
        if strategy == "round_robin":
            return self._round_robin(nodes)
        elif strategy == "least_connections":
            return self._least_connections(nodes)
        elif strategy == "random":
            import random
            return random.choice(nodes)
        else:
            return nodes[0]
    
    def _round_robin(self, nodes: List[Node]) -> Node:
        """Round-robin selection"""
        node = nodes[self.current_index % len(nodes)]
        self.current_index += 1
        return node
    
    def _least_connections(self, nodes: List[Node]) -> Node:
        """Least-connections selection"""
        return min(nodes, key=lambda n: self.connections[n.id])
    
    def increment_connections(self, node_id: str) -> None:
        """Increment connection count"""
        self.connections[node_id] += 1
    
    def decrement_connections(self, node_id: str) -> None:
        """Decrement connection count"""
        self.connections[node_id] = max(0, self.connections[node_id] - 1)


class DistributedCoordinator:
    """
    Coordinator for distributed agent operations
    
    Provides:
    - Task distribution
    - Result aggregation
    - Consensus management
    - Failover handling
    """
    
    def __init__(self, cluster_manager: ClusterManager):
        """
        Initialize coordinator
        
        Args:
            cluster_manager: Cluster manager
        """
        self.cluster = cluster_manager
        self.load_balancer = LoadBalancer()
        self.task_results: Dict[str, Any] = {}
    
    async def distribute_task(
        self,
        task: Dict[str, Any],
        strategy: str = "round_robin"
    ) -> Optional[Dict[str, Any]]:
        """
        Distribute task to a node
        
        Args:
            task: Task to distribute
            strategy: Balancing strategy
            
        Returns:
            Task result or None
        """
        # Get available nodes
        nodes = self.cluster.get_nodes(status=NodeStatus.ONLINE)
        
        if not nodes:
            logger.error("No available nodes")
            return None
        
        # Select node
        node = self.load_balancer.select_node(nodes, strategy)
        
        if not node:
            return None
        
        # Increment connections
        self.load_balancer.increment_connections(node.id)
        
        try:
            # In a real system, this would send task to node
            # For now, simulate execution
            result = await self._execute_on_node(node, task)
            return result
        
        finally:
            # Decrement connections
            self.load_balancer.decrement_connections(node.id)
    
    async def _execute_on_node(self, node: Node, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute task on node
        
        Args:
            node: Target node
            task: Task to execute
            
        Returns:
            Task result
        """
        # Simulate execution
        await asyncio.sleep(0.1)
        
        return {
            "success": True,
            "node_id": node.id,
            "result": f"Result from {node.id}"
        }
    
    async def broadcast_task(
        self,
        task: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Broadcast task to all nodes
        
        Args:
            task: Task to broadcast
            
        Returns:
            List of results
        """
        nodes = self.cluster.get_nodes(status=NodeStatus.ONLINE)
        
        if not nodes:
            return []
        
        # Execute on all nodes
        tasks = [self._execute_on_node(node, task) for node in nodes]
        results = await asyncio.gather(*tasks)
        
        return results
    
    async def aggregate_results(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Aggregate results for a task
        
        Args:
            task_id: Task ID
            
        Returns:
            Aggregated results
        """
        return self.task_results.get(task_id)


class ServiceDiscovery:
    """
    Service discovery for agents
    
    Provides:
    - Service registration
    - Service lookup
    - Health checking
    """
    
    def __init__(self):
        """Initialize service discovery"""
        self.services: Dict[str, List[Node]] = defaultdict(list)
    
    def register_service(
        self,
        service_name: str,
        node: Node
    ) -> None:
        """
        Register a service
        
        Args:
            service_name: Service name
            node: Service node
        """
        self.services[service_name].append(node)
        logger.info(f"Registered service: {service_name} on {node.id}")
    
    def discover_service(
        self,
        service_name: str,
        healthy_only: bool = True
    ) -> List[Node]:
        """
        Discover service instances
        
        Args:
            service_name: Service name
            healthy_only: Only healthy nodes
            
        Returns:
            List of service nodes
        """
        nodes = self.services.get(service_name, [])
        
        if healthy_only:
            nodes = [n for n in nodes if n.status == NodeStatus.ONLINE]
        
        return nodes
    
    def unregister_service(
        self,
        service_name: str,
        node_id: str
    ) -> bool:
        """
        Unregister a service
        
        Args:
            service_name: Service name
            node_id: Node ID
            
        Returns:
            True if unregistered
        """
        if service_name not in self.services:
            return False
        
        nodes = self.services[service_name]
        self.services[service_name] = [n for n in nodes if n.id != node_id]
        
        logger.info(f"Unregistered service: {service_name} from {node_id}")
        return True


def get_cluster_manager() -> ClusterManager:
    """Get global cluster manager instance"""
    if not hasattr(get_cluster_manager, "_instance"):
        get_cluster_manager._instance = ClusterManager()
    return get_cluster_manager._instance


def get_service_discovery() -> ServiceDiscovery:
    """Get global service discovery instance"""
    if not hasattr(get_service_discovery, "_instance"):
        get_service_discovery._instance = ServiceDiscovery()
    return get_service_discovery._instance
