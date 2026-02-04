"""
Agent Health Check and Monitoring
"""

import time
import asyncio
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from enum import Enum

from .logger import get_logger

logger = get_logger(__name__)


class HealthStatus(Enum):
    """Health status"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Health check result"""
    name: str
    status: HealthStatus
    message: str
    timestamp: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComponentHealth:
    """Component health information"""
    name: str
    status: HealthStatus
    checks: List[HealthCheck] = field(default_factory=list)
    last_check: float = field(default_factory=time.time)


class HealthMonitor:
    """
    Health monitor for agents
    
    Provides:
    - Health checks
    - Component monitoring
    - Health status aggregation
    - Health alerts
    """
    
    def __init__(self):
        """Initialize health monitor"""
        self.components: Dict[str, ComponentHealth] = {}
        self.checks: Dict[str, Callable] = {}
        self.alert_callbacks: List[Callable] = []
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
    
    def register_check(self, name: str, check_func: Callable) -> None:
        """
        Register a health check
        
        Args:
            name: Check name
            check_func: Check function that returns HealthCheck
        """
        self.checks[name] = check_func
        logger.info(f"Registered health check: {name}")
    
    def register_component(self, name: str) -> None:
        """
        Register a component for monitoring
        
        Args:
            name: Component name
        """
        self.components[name] = ComponentHealth(name=name)
        logger.info(f"Registered component for monitoring: {name}")
    
    async def check_health(self, component: Optional[str] = None) -> Dict[str, Any]:
        """
        Check health of component or all components
        
        Args:
            component: Component name (optional)
            
        Returns:
            Health status
        """
        if component:
            return await self._check_component(component)
        else:
            return await self._check_all()
    
    async def _check_component(self, name: str) -> Dict[str, Any]:
        """Check health of a specific component"""
        if name not in self.components:
            return {
                "status": HealthStatus.UNKNOWN.value,
                "message": f"Unknown component: {name}"
            }
        
        component = self.components[name]
        checks = []
        
        # Run all checks for this component
        for check_name, check_func in self.checks.items():
            if check_name.startswith(f"{name}_"):
                try:
                    result = await check_func()
                    checks.append(result)
                except Exception as e:
                    logger.error(f"Health check failed: {check_name}: {e}")
                    checks.append(HealthCheck(
                        name=check_name,
                        status=HealthStatus.UNHEALTHY,
                        message=str(e)
                    ))
        
        # Determine overall status
        if not checks:
            status = HealthStatus.UNKNOWN
        elif all(c.status == HealthStatus.HEALTHY for c in checks):
            status = HealthStatus.HEALTHY
        elif any(c.status == HealthStatus.UNHEALTHY for c in checks):
            status = HealthStatus.UNHEALTHY
        else:
            status = HealthStatus.DEGRADED
        
        component.checks = checks
        component.last_check = time.time()
        
        return {
            "component": name,
            "status": status.value,
            "checks": [
                {
                    "name": c.name,
                    "status": c.status.value,
                    "message": c.message,
                    "timestamp": c.timestamp
                }
                for c in checks
            ],
            "last_check": component.last_check
        }
    
    async def _check_all(self) -> Dict[str, Any]:
        """Check health of all components"""
        results = {}
        
        for name in self.components:
            results[name] = await self._check_component(name)
        
        # Determine overall status
        statuses = [r["status"] for r in results.values()]
        
        if all(s == HealthStatus.HEALTHY.value for s in statuses):
            overall = HealthStatus.HEALTHY
        elif any(s == HealthStatus.UNHEALTHY.value for s in statuses):
            overall = HealthStatus.UNHEALTHY
        elif any(s == HealthStatus.DEGRADED.value for s in statuses):
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.UNKNOWN
        
        return {
            "status": overall.value,
            "components": results,
            "timestamp": time.time()
        }
    
    def register_alert_callback(self, callback: Callable) -> None:
        """
        Register an alert callback
        
        Args:
            callback: Callback function
        """
        self.alert_callbacks.append(callback)
    
    async def start_monitoring(self, interval: float = 60.0) -> None:
        """
        Start continuous health monitoring
        
        Args:
            interval: Check interval in seconds
        """
        if self._monitoring:
            logger.warning("Health monitoring already started")
            return
        
        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop(interval))
        logger.info(f"Started health monitoring (interval: {interval}s)")
    
    async def stop_monitoring(self) -> None:
        """Stop health monitoring"""
        if not self._monitoring:
            return
        
        self._monitoring = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped health monitoring")
    
    async def _monitor_loop(self, interval: float) -> None:
        """Monitor loop"""
        while self._monitoring:
            try:
                # Check health
                health = await self.check_health()
                
                # Check for unhealthy components
                if health["status"] != HealthStatus.HEALTHY.value:
                    # Trigger alerts
                    for callback in self.alert_callbacks:
                        try:
                            await callback(health)
                        except Exception as e:
                            logger.error(f"Alert callback failed: {e}")
                
                # Wait for next interval
                await asyncio.sleep(interval)
            
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(interval)


class Heartbeat:
    """
    Heartbeat mechanism for agents
    
    Provides:
    - Heartbeat generation
    - Heartbeat monitoring
    - Timeout detection
    """
    
    def __init__(self, timeout: float = 300.0):
        """
        Initialize heartbeat
        
        Args:
            timeout: Heartbeat timeout in seconds
        """
        self.timeout = timeout
        self.heartbeats: Dict[str, float] = {}
        self._monitor_task: Optional[asyncio.Task] = None
        self._monitoring = False
        self.timeout_callbacks: List[Callable] = []
    
    def register(self, agent_id: str) -> None:
        """
        Register an agent for heartbeat monitoring
        
        Args:
            agent_id: Agent ID
        """
        self.heartbeats[agent_id] = time.time()
        logger.info(f"Registered agent for heartbeat: {agent_id}")
    
    def heartbeat(self, agent_id: str) -> None:
        """
        Record a heartbeat
        
        Args:
            agent_id: Agent ID
        """
        self.heartbeats[agent_id] = time.time()
    
    def get_last_heartbeat(self, agent_id: str) -> Optional[float]:
        """
        Get last heartbeat time
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Last heartbeat timestamp
        """
        return self.heartbeats.get(agent_id)
    
    def is_alive(self, agent_id: str) -> bool:
        """
        Check if agent is alive
        
        Args:
            agent_id: Agent ID
            
        Returns:
            True if alive
        """
        last_heartbeat = self.heartbeats.get(agent_id)
        if last_heartbeat is None:
            return False
        
        return (time.time() - last_heartbeat) < self.timeout
    
    async def start_monitoring(self, check_interval: float = 30.0) -> None:
        """
        Start heartbeat monitoring
        
        Args:
            check_interval: Check interval in seconds
        """
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_task = asyncio.create_task(
            self._monitor_loop(check_interval)
        )
        logger.info("Started heartbeat monitoring")
    
    async def stop_monitoring(self) -> None:
        """Stop heartbeat monitoring"""
        if not self._monitoring:
            return
        
        self._monitoring = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped heartbeat monitoring")
    
    def register_timeout_callback(self, callback: Callable) -> None:
        """
        Register a timeout callback
        
        Args:
            callback: Callback function
        """
        self.timeout_callbacks.append(callback)
    
    async def _monitor_loop(self, interval: float) -> None:
        """Monitor loop"""
        while self._monitoring:
            try:
                current_time = time.time()
                
                # Check for timeouts
                for agent_id, last_heartbeat in list(self.heartbeats.items()):
                    if (current_time - last_heartbeat) > self.timeout:
                        # Agent timed out
                        for callback in self.timeout_callbacks:
                            try:
                                await callback(agent_id)
                            except Exception as e:
                                logger.error(f"Timeout callback failed: {e}")
                
                await asyncio.sleep(interval)
            
            except Exception as e:
                logger.error(f"Heartbeat monitoring error: {e}")
                await asyncio.sleep(interval)


def get_health_monitor() -> HealthMonitor:
    """Get global health monitor instance"""
    if not hasattr(get_health_monitor, "_instance"):
        get_health_monitor._instance = HealthMonitor()
    return get_health_monitor._instance


def get_heartbeat() -> Heartbeat:
    """Get global heartbeat instance"""
    if not hasattr(get_heartbeat, "_instance"):
        get_heartbeat._instance = Heartbeat()
    return get_heartbeat._instance
