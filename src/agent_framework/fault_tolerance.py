"""
Agent Fault Tolerance and Recovery
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum

from .logger import get_logger

logger = get_logger(__name__)


class FailureMode(Enum):
    """Failure modes"""
    TRANSIENT = "transient"
    PERMANENT = "permanent"
    NETWORK = "network"
    TIMEOUT = "timeout"
    RESOURCE = "resource"


@dataclass
class FailureInfo:
    """Failure information"""
    mode: FailureMode
    component: str
    message: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """
    Circuit breaker for fault tolerance
    
    Provides:
    - Failure detection
    - Circuit state management
    - Automatic recovery
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        half_open_max_calls: int = 3
    ):
        """
        Initialize circuit breaker
        
        Args:
            failure_threshold: Failures before opening
            timeout: Time in open state
            half_open_max_calls: Max calls in half-open state
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.half_open_max_calls = half_open_max_calls
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0.0
        self.half_open_calls = 0
    
    def record_success(self) -> None:
        """Record a successful call"""
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_calls += 1
            
            if self.half_open_calls >= self.half_open_max_calls:
                self.state = CircuitState.CLOSED
                self.half_open_calls = 0
                self.failure_count = 0
                logger.info("Circuit breaker closed")
        
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0
    
    def record_failure(self, failure_info: FailureInfo) -> None:
        """
        Record a failure
        
        Args:
            failure_info: Failure information
        """
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    def can_execute(self) -> bool:
        """Check if execution is allowed"""
        if self.state == CircuitState.CLOSED:
            return True
        
        elif self.state == CircuitState.OPEN:
            # Check if timeout has passed
            if time.time() - self.last_failure_time > self.timeout:
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                logger.info("Circuit breaker moved to half-open")
                return True
            return False
        
        elif self.state == CircuitState.HALF_OPEN:
            return self.half_open_calls < self.half_open_max_calls
        
        return False
    
    def get_state(self) -> CircuitState:
        """Get current state"""
        return self.state
    
    def reset(self) -> None:
        """Reset circuit breaker"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.half_open_calls = 0
        logger.info("Circuit breaker reset")


class FailoverManager:
    """
    Failover manager for component redundancy
    
    Provides:
    - Primary/secondary failover
    - Health checking
    - Automatic switching
    """
    
    def __init__(self):
        """Initialize failover manager"""
        self.primary: Optional[str] = None
        self.secondaries: List[str] = []
        self.current: Optional[str] = None
        self.failed_components: Set[str] = set()
        self._lock = asyncio.Lock()
    
    def configure(
        self,
        primary: str,
        secondaries: List[str] = None
    ) -> None:
        """
        Configure failover
        
        Args:
            primary: Primary component
            secondaries: Secondary components
        """
        self.primary = primary
        self.secondaries = secondaries or []
        self.current = primary
        logger.info(f"Configured failover: primary={primary}, secondaries={self.secondaries}")
    
    async def failover(self, failed_component: str) -> Optional[str]:
        """
        Perform failover
        
        Args:
            failed_component: Failed component
            
        Returns:
            New active component
        """
        async with self._lock:
            self.failed_components.add(failed_component)
            
            # Find available component
            available = [
                c for c in [self.primary] + self.secondaries
                if c not in self.failed_components
            ]
            
            if not available:
                logger.error("No available components for failover")
                return None
            
            self.current = available[0]
            
            logger.info(f"Failover to {self.current}")
            return self.current
    
    def get_current(self) -> Optional[str]:
        """Get current active component"""
        return self.current
    
    def is_healthy(self) -> bool:
        """Check if current component is healthy"""
        return self.current and self.current not in self.failed_components


class RecoveryManager:
    """
    Recovery manager for failed components
    
    Provides:
    - Component recovery
    - Health restoration
    - State restoration
    """
    
    def __init__(self):
        """Initialize recovery manager"""
        self.recovery_strategies: Dict[str, Callable] = {}
        self.recovery_history: List[Dict[str, Any]] = []
    
    def register_strategy(
        self,
        component_type: str,
        strategy: Callable
    ) -> None:
        """
        Register a recovery strategy
        
        Args:
            component_type: Component type
            strategy: Recovery function
        """
        self.recovery_strategies[component_type] = strategy
        logger.info(f"Registered recovery strategy: {component_type}")
    
    async def recover(
        self,
        component: str,
        component_type: str,
        failure_info: FailureInfo
    ) -> bool:
        """
        Attempt to recover a component
        
        Args:
            component: Component identifier
            component_type: Component type
            failure_info: Failure information
            
        Returns:
            True if recovered
        """
        strategy = self.recovery_strategies.get(component_type)
        
        if not strategy:
            logger.warning(f"No recovery strategy for {component_type}")
            return False
        
        try:
            result = await strategy(component, failure_info)
            
            # Record recovery
            self.recovery_history.append({
                "component": component,
                "component_type": component_type,
                "timestamp": time.time(),
                "success": result
            })
            
            if result:
                logger.info(f"Recovered component: {component}")
            
            return result
        
        except Exception as e:
            logger.error(f"Recovery failed for {component}: {e}")
            return False
    
    def get_recovery_history(
        self,
        component: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recovery history
        
        Args:
            component: Filter by component
            limit: Maximum results
            
        Returns:
            Recovery history
        """
        history = self.recovery_history
        
        if component:
            history = [h for h in history if h["component"] == component]
        
        return history[-limit:]


class HealthChecker:
    """
    Health checker for components
    
    Provides:
    - Health checks
    - Component monitoring
    - Health status tracking
    """
    
    def __init__(self):
        """Initialize health checker"""
        self.health_checks: Dict[str, Callable] = {}
        self.health_status: Dict[str, bool] = {}
        self._lock = asyncio.Lock()
    
    def register_check(
        self,
        component: str,
        check_func: Callable
    ) -> None:
        """
        Register a health check
        
        Args:
            component: Component name
            check_func: Check function
        """
        self.health_checks[component] = check_func
        logger.info(f"Registered health check: {component}")
    
    async def check_health(self, component: str) -> bool:
        """
        Check component health
        
        Args:
            component: Component name
            
        Returns:
            True if healthy
        """
        check_func = self.health_checks.get(component)
        
        if not check_func:
            logger.warning(f"No health check for {component}")
            return False
        
        try:
            healthy = await check_func()
            
            async with self._lock:
                self.health_status[component] = healthy
            
            return healthy
        
        except Exception as e:
            logger.error(f"Health check failed for {component}: {e}")
            
            async with self._lock:
                self.health_status[component] = False
            
            return False
    
    async def check_all(self) -> Dict[str, bool]:
        """Check all components"""
        results = {}
        
        for component in self.health_checks:
            results[component] = await self.check_health(component)
        
        return results
    
    def get_status(self, component: str) -> Optional[bool]:
        """Get component health status"""
        return self.health_status.get(component)
    
    def get_all_status(self) -> Dict[str, bool]:
        """Get all health status"""
        return dict(self.health_status)


class FaultToleranceManager:
    """
    Manager for fault tolerance features
    
    Provides:
    - Circuit breaking
    - Failover management
    - Recovery management
    - Health checking
    """
    
    def __init__(self):
        """Initialize fault tolerance manager"""
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.failover_manager = FailoverManager()
        self.recovery_manager = RecoveryManager()
        self.health_checker = HealthChecker()
    
    def get_circuit_breaker(self, name: str) -> CircuitBreaker:
        """Get or create circuit breaker"""
        if name not in self.circuit_breakers:
            self.circuit_breakers[name] = CircuitBreaker()
        
        return self.circuit_breakers[name]
    
    def get_failover_manager(self) -> FailoverManager:
        """Get failover manager"""
        return self.failover_manager
    
    def get_recovery_manager(self) -> RecoveryManager:
        """Get recovery manager"""
        return self.recovery_manager
    
    def get_health_checker(self) -> HealthChecker:
        """Get health checker"""
        return self.health_checker
    
    async def execute_with_circuit_breaker(
        self,
        circuit_name: str,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function with circuit breaker protection
        
        Args:
            circuit_name: Circuit breaker name
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
        """
        circuit = self.get_circuit_breaker(circuit_name)
        
        if not circuit.can_execute():
            raise Exception(f"Circuit breaker {circuit_name} is open")
        
        try:
            result = await func(*args, **kwargs)
            circuit.record_success()
            return result
        
        except Exception as e:
            failure_info = FailureInfo(
                mode=FailureMode.TRANSIENT,
                component=circuit_name,
                message=str(e)
            )
            circuit.record_failure(failure_info)
            raise


def get_fault_tolerance_manager() -> FaultToleranceManager:
    """Get global fault tolerance manager instance"""
    if not hasattr(get_fault_tolerance_manager, "_instance"):
        get_fault_tolerance_manager._instance = FaultToleranceManager()
    return get_fault_tolerance_manager._instance
