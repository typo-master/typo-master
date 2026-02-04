"""
Agent Resource Management and Rate Limiting
"""

import time
import asyncio
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from collections import deque
from enum import Enum

from .logger import get_logger

logger = get_logger(__name__)


class ResourceType(Enum):
    """Resource types"""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    API = "api"


@dataclass
class ResourceUsage:
    """Resource usage information"""
    resource_type: ResourceType
    current: float
    maximum: float
    unit: str = "%"
    timestamp: float = field(default_factory=time.time)


class ResourceMonitor:
    """
    Resource monitor for agents
    
    Provides:
    - Resource usage tracking
    - Resource limit enforcement
    - Resource alerts
    """
    
    def __init__(self):
        """Initialize resource monitor"""
        self.resources: Dict[ResourceType, ResourceUsage] = {}
        self.limits: Dict[ResourceType, float] = {}
        self.alert_callbacks: List[Callable] = []
        self._monitor_task: Optional[asyncio.Task] = None
        self._monitoring = False
    
    def set_limit(self, resource_type: ResourceType, limit: float) -> None:
        """
        Set resource limit
        
        Args:
            resource_type: Resource type
            limit: Limit value
        """
        self.limits[resource_type] = limit
        logger.info(f"Set resource limit: {resource_type} = {limit}")
    
    def update_usage(self, resource_type: ResourceType, current: float, maximum: float = 100.0) -> None:
        """
        Update resource usage
        
        Args:
            resource_type: Resource type
            current: Current usage
            maximum: Maximum possible value
        """
        self.resources[resource_type] = ResourceUsage(
            resource_type=resource_type,
            current=current,
            maximum=maximum
        )
        
        # Check if limit exceeded
        if resource_type in self.limits:
            limit = self.limits[resource_type]
            if current > limit:
                self._trigger_alert(resource_type, current, limit)
    
    def get_usage(self, resource_type: ResourceType) -> Optional[ResourceUsage]:
        """
        Get resource usage
        
        Args:
            resource_type: Resource type
            
        Returns:
            Resource usage
        """
        return self.resources.get(resource_type)
    
    def get_all_usage(self) -> Dict[str, ResourceUsage]:
        """Get all resource usage"""
        return {k.value: v for k, v in self.resources.items()}
    
    def is_over_limit(self, resource_type: ResourceType) -> bool:
        """
        Check if resource is over limit
        
        Args:
            resource_type: Resource type
            
        Returns:
            True if over limit
        """
        if resource_type not in self.resources:
            return False
        
        if resource_type not in self.limits:
            return False
        
        return self.resources[resource_type].current > self.limits[resource_type]
    
    def register_alert_callback(self, callback: Callable) -> None:
        """
        Register an alert callback
        
        Args:
            callback: Callback function
        """
        self.alert_callbacks.append(callback)
    
    def _trigger_alert(self, resource_type: ResourceType, current: float, limit: float) -> None:
        """Trigger alert for resource limit"""
        for callback in self.alert_callbacks:
            try:
                callback(resource_type, current, limit)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")
    
    async def start_monitoring(self, interval: float = 10.0) -> None:
        """
        Start resource monitoring
        
        Args:
            interval: Check interval in seconds
        """
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop(interval))
        logger.info("Started resource monitoring")
    
    async def stop_monitoring(self) -> None:
        """Stop resource monitoring"""
        if not self._monitoring:
            return
        
        self._monitoring = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped resource monitoring")
    
    async def _monitor_loop(self, interval: float) -> None:
        """Monitor loop"""
        while self._monitoring:
            try:
                # Update resource usage (mock)
                # In real implementation, this would query system resources
                pass
                
                await asyncio.sleep(interval)
            
            except Exception as e:
                logger.error(f"Resource monitoring error: {e}")
                await asyncio.sleep(interval)


class RateLimiter:
    """
    Rate limiter for API calls
    
    Provides:
    - Rate limit enforcement
    - Token bucket algorithm
    - Sliding window tracking
    """
    
    def __init__(self, rate: float, capacity: int = 10):
        """
        Initialize rate limiter
        
        Args:
            rate: Rate in requests per second
            capacity: Token bucket capacity
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
        self._lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1) -> bool:
        """
        Acquire tokens
        
        Args:
            tokens: Number of tokens to acquire
            
        Returns:
            True if acquired
        """
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_update
            
            # Refill tokens
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.rate
            )
            
            self.last_update = now
            
            # Check if enough tokens
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            return False
    
    async def acquire_with_wait(self, tokens: int = 1, timeout: float = 30.0) -> bool:
        """
        Acquire tokens with wait
        
        Args:
            tokens: Number of tokens to acquire
            timeout: Maximum wait time
            
        Returns:
            True if acquired
        """
        start = time.time()
        
        while (time.time() - start) < timeout:
            if await self.acquire(tokens):
                return True
            
            # Calculate wait time
            wait_time = (tokens - self.tokens) / self.rate
            await asyncio.sleep(min(wait_time, 0.1))
        
        return False
    
    def get_available_tokens(self) -> float:
        """Get available tokens"""
        return self.tokens
    
    def get_usage(self) -> float:
        """Get current usage"""
        return (self.capacity - self.tokens) / self.capacity


class ConcurrencyLimiter:
    """
    Concurrency limiter for parallel operations
    
    Provides:
    - Concurrency limit enforcement
    - Semaphore-based limiting
    - Wait queue management
    """
    
    def __init__(self, limit: int):
        """
        Initialize concurrency limiter
        
        Args:
            limit: Maximum concurrent operations
        """
        self.limit = limit
        self.semaphore = asyncio.Semaphore(limit)
        self.active_count = 0
    
    async def acquire(self) -> None:
        """Acquire permit"""
        await self.semaphore.acquire()
        self.active_count += 1
    
    async def release(self) -> None:
        """Release permit"""
        self.active_count -= 1
        self.semaphore.release()
    
    async def __aenter__(self):
        """Context manager entry"""
        await self.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.release()
    
    def get_active_count(self) -> int:
        """Get active operation count"""
        return self.active_count
    
    def get_available_slots(self) -> int:
        """Get available slots"""
        return self.limit - self.active_count


class ResourceManager:
    """
    Resource manager for agents
    
    Provides:
    - Resource monitoring
    - Rate limiting
    - Concurrency limiting
    - Resource allocation
    """
    
    def __init__(self):
        """Initialize resource manager"""
        self.resource_monitor = ResourceMonitor()
        self.rate_limiters: Dict[str, RateLimiter] = {}
        self.concurrency_limiters: Dict[str, ConcurrencyLimiter] = {}
    
    def create_rate_limiter(self, name: str, rate: float, capacity: int = 10) -> RateLimiter:
        """
        Create a rate limiter
        
        Args:
            name: Limiter name
            rate: Rate in requests per second
            capacity: Token bucket capacity
            
        Returns:
            Rate limiter
        """
        limiter = RateLimiter(rate, capacity)
        self.rate_limiters[name] = limiter
        return limiter
    
    def create_concurrency_limiter(self, name: str, limit: int) -> ConcurrencyLimiter:
        """
        Create a concurrency limiter
        
        Args:
            name: Limiter name
            limit: Maximum concurrent operations
            
        Returns:
            Concurrency limiter
        """
        limiter = ConcurrencyLimiter(limit)
        self.concurrency_limiters[name] = limiter
        return limiter
    
    def get_rate_limiter(self, name: str) -> Optional[RateLimiter]:
        """Get rate limiter by name"""
        return self.rate_limiters.get(name)
    
    def get_concurrency_limiter(self, name: str) -> Optional[ConcurrencyLimiter]:
        """Get concurrency limiter by name"""
        return self.concurrency_limiters.get(name)
    
    def get_resource_monitor(self) -> ResourceMonitor:
        """Get resource monitor"""
        return self.resource_monitor


def get_resource_manager() -> ResourceManager:
    """Get global resource manager instance"""
    if not hasattr(get_resource_manager, "_instance"):
        get_resource_manager._instance = ResourceManager()
    return get_resource_manager._instance
