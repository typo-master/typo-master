"""
Async Utilities for Agent Framework
"""

import asyncio
from typing import Any, Callable, Optional, List, Dict
from functools import wraps
from contextlib import asynccontextmanager

from .logger import get_logger

logger = get_logger(__name__)


def async_retry(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Async retry decorator
    
    Args:
        max_retries: Maximum retry attempts
        delay: Initial delay in seconds
        backoff: Backoff multiplier
        exceptions: Exceptions to catch
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_retries - 1:
                        raise
                    
                    logger.warning(
                        f"Retry {attempt + 1}/{max_retries} for {func.__name__}: {e}"
                    )
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
            
            raise last_exception
        
        return wrapper
    return decorator


def async_timeout(timeout: float):
    """
    Async timeout decorator
    
    Args:
        timeout: Timeout in seconds
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                logger.error(f"Timeout after {timeout}s for {func.__name__}")
                raise
        
        return wrapper
    return decorator


def async_limiter(rate: float, burst: int = 1):
    """
    Async rate limiter
    
    Args:
        rate: Requests per second
        burst: Burst capacity
    """
    limiter = asyncio.Semaphore(burst)
    interval = 1.0 / rate
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            async with limiter:
                result = await func(*args, **kwargs)
                await asyncio.sleep(interval)
                return result
        
        return wrapper
    return decorator


@asynccontextmanager
async def async_context(*args, **kwargs):
    """
    Generic async context manager
    
    Args:
        *args: Context arguments
        **kwargs: Context keyword arguments
    """
    # Placeholder for async context
    yield None


class AsyncQueue:
    """
    Async queue with priority support
    
    Provides:
    - Priority queue
    - Async operations
    - Size management
    """
    
    def __init__(self, maxsize: int = 0):
        """
        Initialize async queue
        
        Args:
            maxsize: Maximum queue size (0 for unlimited)
        """
        self.queue = asyncio.PriorityQueue(maxsize=maxsize)
        self._closed = False
    
    async def put(self, item: Any, priority: float = 0) -> None:
        """
        Put item in queue
        
        Args:
            item: Item to put
            priority: Item priority (lower is higher priority)
        """
        if self._closed:
            raise RuntimeError("Queue is closed")
        
        await self.queue.put((priority, item))
    
    async def get(self) -> Any:
        """
        Get item from queue
        
        Returns:
            Queue item
        """
        if self._closed and self.queue.empty():
            raise RuntimeError("Queue is closed")
        
        priority, item = await self.queue.get()
        return item
    
    async def get_nowait(self) -> Any:
        """
        Get item without waiting
        
        Returns:
            Queue item or None
        """
        try:
            priority, item = self.queue.get_nowait()
            return item
        except asyncio.QueueEmpty:
            return None
    
    def task_done(self) -> None:
        """Mark task as done"""
        self.queue.task_done()
    
    def qsize(self) -> int:
        """Get queue size"""
        return self.queue.qsize()
    
    def empty(self) -> bool:
        """Check if queue is empty"""
        return self.queue.empty()
    
    def close(self) -> None:
        """Close the queue"""
        self._closed = True
    
    def __aiter__(self):
        """Make queue iterable"""
        return self
    
    async def __anext__(self):
        """Get next item"""
        item = await self.get()
        return item


class AsyncLockManager:
    """
    Manager for async locks
    
    Provides:
    - Named locks
    - Lock acquisition
    - Lock release
    """
    
    def __init__(self):
        """Initialize lock manager"""
        self.locks: Dict[str, asyncio.Lock] = {}
        self._lock = asyncio.Lock()
    
    async def acquire(self, name: str) -> None:
        """
        Acquire a lock
        
        Args:
            name: Lock name
        """
        async with self._lock:
            if name not in self.locks:
                self.locks[name] = asyncio.Lock()
            
            await self.locks[name].acquire()
    
    async def release(self, name: str) -> None:
        """
        Release a lock
        
        Args:
            name: Lock name
        """
        if name in self.locks:
            self.locks[name].release()
    
    @asynccontextmanager
    async def lock(self, name: str):
        """
        Context manager for lock
        
        Args:
            name: Lock name
        """
        await self.acquire(name)
        try:
            yield
        finally:
            await self.release(name)


class AsyncBatchProcessor:
    """
    Batch processor for async operations
    
    Provides:
    - Batch processing
    - Error handling
    - Progress tracking
    """
    
    def __init__(self, batch_size: int = 10):
        """
        Initialize batch processor
        
        Args:
            batch_size: Batch size
        """
        self.batch_size = batch_size
    
    async def process_batch(
        self,
        items: List[Any],
        processor: Callable,
        *args,
        **kwargs
    ) -> List[Any]:
        """
        Process items in batches
        
        Args:
            items: Items to process
            processor: Processing function
            *args: Additional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Processed results
        """
        results = []
        
        for i in range(0, len(items), self.batch_size):
            batch = items[i:i + self.batch_size]
            
            try:
                batch_results = await processor(batch, *args, **kwargs)
                results.extend(batch_results)
            except Exception as e:
                logger.error(f"Batch processing failed: {e}")
                # Add None for failed items
                results.extend([None] * len(batch))
        
        return results
    
    async def process_concurrent(
        self,
        items: List[Any],
        processor: Callable,
        max_concurrent: int = 5,
        *args,
        **kwargs
    ) -> List[Any]:
        """
        Process items concurrently
        
        Args:
            items: Items to process
            processor: Processing function
            max_concurrent: Maximum concurrent operations
            *args: Additional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Processed results
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        results = []
        
        async def process_item(item):
            async with semaphore:
                return await processor(item, *args, **kwargs)
        
        tasks = [process_item(item) for item in items]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return results


def get_async_queue(maxsize: int = 0) -> AsyncQueue:
    """Get async queue instance"""
    return AsyncQueue(maxsize)


def get_async_lock_manager() -> AsyncLockManager:
    """Get async lock manager instance"""
    if not hasattr(get_async_lock_manager, "_instance"):
        get_async_lock_manager._instance = AsyncLockManager()
    return get_async_lock_manager._instance
