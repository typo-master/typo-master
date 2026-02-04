"""
Agent Optimization and Performance
"""

import time
import asyncio
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from .logger import get_logger

logger = get_logger(__name__)


class OptimizationType(Enum):
    """Optimization types"""
    CACHING = "caching"
    BATCHING = "batching"
    PARALLELIZATION = "parallelization"
    LAZY_LOADING = "lazy_loading"
    CONNECTION_POOLING = "connection_pooling"
    COMPRESSION = "compression"


@dataclass
class OptimizationResult:
    """Optimization result"""
    type: OptimizationType
    before_time: float
    after_time: float
    improvement: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class Cache:
    """
    Simple cache for optimization
    
    Provides:
    - Key-value caching
    - TTL support
    - Size limits
    """
    
    def __init__(self, max_size: int = 1000, ttl: float = 3600.0):
        """
        Initialize cache
        
        Args:
            max_size: Maximum cache size
            ttl: Time to live in seconds
        """
        self.max_size = max_size
        self.ttl = ttl
        self.cache: Dict[str, Any] = {}
        self.timestamps: Dict[str, float] = {}
        self.access_count: Dict[str, int] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        if key not in self.cache:
            return None
        
        # Check TTL
        if time.time() - self.timestamps[key] > self.ttl:
            del self.cache[key]
            del self.timestamps[key]
            del self.access_count[key]
            return None
        
        # Update access count
        self.access_count[key] += 1
        return self.cache[key]
    
    def set(self, key: str, value: Any) -> None:
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache
        """
        # Check size limit
        if len(self.cache) >= self.max_size:
            # Remove least recently used
            lru_key = min(self.access_count, key=self.access_count.get)
            del self.cache[lru_key]
            del self.timestamps[lru_key]
            del self.access_count[lru_key]
        
        self.cache[key] = value
        self.timestamps[key] = time.time()
        self.access_count[key] = 1
    
    def clear(self) -> None:
        """Clear cache"""
        self.cache.clear()
        self.timestamps.clear()
        self.access_count.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "utilization": len(self.cache) / self.max_size
        }


class Optimizer:
    """
    Optimizer for agent operations
    
    Provides:
    - Caching
    - Batching
    - Parallelization
    - Performance tracking
    """
    
    def __init__(self):
        """Initialize optimizer"""
        self.caches: Dict[str, Cache] = {}
        self.optimizations: List[OptimizationResult] = []
    
    def get_cache(self, name: str = "default") -> Cache:
        """
        Get or create cache
        
        Args:
            name: Cache name
            
        Returns:
            Cache instance
        """
        if name not in self.caches:
            self.caches[name] = Cache()
        
        return self.caches[name]
    
    def cache_result(
        self,
        cache_name: str,
        key: str,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Cache function result
        
        Args:
            cache_name: Cache name
            key: Cache key
            func: Function to cache
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
        """
        cache = self.get_cache(cache_name)
        
        # Check cache
        result = cache.get(key)
        if result is not None:
            return result
        
        # Execute function
        result = func(*args, **kwargs)
        
        # Cache result
        cache.set(key, result)
        
        return result
    
    async def batch_operations(
        self,
        items: List[Any],
        batch_size: int,
        operation: Callable,
        *args,
        **kwargs
    ) -> List[Any]:
        """
        Execute operations in batches
        
        Args:
            items: Items to process
            batch_size: Batch size
            operation: Operation function
            *args: Additional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Results
        """
        results = []
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            
            try:
                batch_results = await operation(batch, *args, **kwargs)
                results.extend(batch_results)
            except Exception as e:
                logger.error(f"Batch processing failed: {e}")
        
        return results
    
    async def parallel_execute(
        self,
        tasks: List[Callable],
        max_concurrent: int = 5
    ) -> List[Any]:
        """
        Execute tasks in parallel
        
        Args:
            tasks: Tasks to execute
            max_concurrent: Maximum concurrent tasks
            
        Returns:
            Results
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        results = []
        
        async def execute_task(task):
            async with semaphore:
                return await task()
        
        tasks_to_run = [execute_task(task) for task in tasks]
        results = await asyncio.gather(*tasks_to_run, return_exceptions=True)
        
        return results
    
    async def optimize_operation(
        self,
        operation: Callable,
        optimization_type: OptimizationType,
        *args,
        **kwargs
    ) -> OptimizationResult:
        """
        Optimize an operation
        
        Args:
            operation: Operation to optimize
            optimization_type: Type of optimization
            *args: Operation arguments
            **kwargs: Operation keyword arguments
            
        Returns:
            Optimization result
        """
        before_time = time.time()
        
        # Execute operation
        result = await operation(*args, **kwargs)
        
        after_time = time.time()
        
        # Calculate improvement
        improvement = 0.0
        
        optimization_result = OptimizationResult(
            type=optimization_type,
            before_time=before_time,
            after_time=after_time,
            improvement=improvement,
            metadata={"result": result}
        )
        
        self.optimizations.append(optimization_result)
        
        return optimization_result
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get optimization statistics"""
        if not self.optimizations:
            return {}
        
        improvements = [o.improvement for o in self.optimizations]
        
        return {
            "total_optimizations": len(self.optimizations),
            "avg_improvement": sum(improvements) / len(improvements),
            "by_type": {
                opt_type.value: len([o for o in self.optimizations if o.type == opt_type])
                for opt_type in OptimizationType
            }
        }
    
    def get_cache_stats(self, cache_name: str = None) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Args:
            cache_name: Cache name (None for all)
            
        Returns:
            Cache statistics
        """
        if cache_name:
            cache = self.get_cache(cache_name)
            return cache.get_stats()
        
        # Get all cache stats
        return {
            name: cache.get_stats()
            for name, cache in self.caches.items()
        }


def get_optimizer() -> Optimizer:
    """Get global optimizer instance"""
    if not hasattr(get_optimizer, "_instance"):
        get_optimizer._instance = Optimizer()
    return get_optimizer._instance
