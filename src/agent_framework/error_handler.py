"""
Error Handler - Agent Error Recovery and Retry Mechanism

This module provides error handling, retry logic, and recovery mechanisms for agents.
"""

import asyncio
import time
import traceback
from typing import Any, Callable, Dict, List, Optional, Type
from dataclasses import dataclass, field
from enum import Enum
import functools

from .logger import get_logger

logger = get_logger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories"""
    NETWORK = "network"
    API = "api"
    DATABASE = "database"
    FILESYSTEM = "filesystem"
    VALIDATION = "validation"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass
class ErrorInfo:
    """Error information"""
    exception: Exception
    category: ErrorCategory
    severity: ErrorSeverity
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    traceback_str: str = ""
    
    def __post_init__(self):
        """Capture traceback"""
        self.traceback_str = "".join(traceback.format_exception(
            type(self.exception),
            self.exception,
            self.exception.__traceback__
        ))


class RetryStrategy:
    """Retry strategy configuration"""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_backoff: bool = True,
        jitter: bool = True,
    ):
        """
        Initialize retry strategy
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay between retries (seconds)
            max_delay: Maximum delay between retries (seconds)
            exponential_backoff: Use exponential backoff
            jitter: Add random jitter to delay
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_backoff = exponential_backoff
        self.jitter = jitter
    
    def get_delay(self, attempt: int) -> float:
        """
        Calculate delay for retry attempt
        
        Args:
            attempt: Retry attempt number (0-indexed)
            
        Returns:
            Delay in seconds
        """
        if self.exponential_backoff:
            delay = self.base_delay * (2 ** attempt)
        else:
            delay = self.base_delay
        
        delay = min(delay, self.max_delay)
        
        if self.jitter:
            import random
            delay = delay * (0.5 + random.random())
        
        return delay


class ErrorHandler:
    """
    Error handler for agents
    
    Provides:
    - Error classification
    - Retry logic
    - Recovery strategies
    - Error logging
    """
    
    def __init__(self, agent_id: str):
        """
        Initialize error handler
        
        Args:
            agent_id: Agent ID
        """
        self.agent_id = agent_id
        self.error_history: List[ErrorInfo] = []
        self.retry_strategies: Dict[str, RetryStrategy] = {}
        self.recovery_handlers: Dict[ErrorCategory, List[Callable]] = {}
        self._lock = asyncio.Lock()
    
    def register_retry_strategy(self, name: str, strategy: RetryStrategy) -> None:
        """
        Register a retry strategy
        
        Args:
            name: Strategy name
            strategy: Retry strategy
        """
        self.retry_strategies[name] = strategy
        logger.debug(f"Registered retry strategy: {name}")
    
    def register_recovery_handler(
        self,
        category: ErrorCategory,
        handler: Callable[[ErrorInfo], Any]
    ) -> None:
        """
        Register a recovery handler
        
        Args:
            category: Error category
            handler: Recovery handler
        """
        if category not in self.recovery_handlers:
            self.recovery_handlers[category] = []
        self.recovery_handlers[category].append(handler)
        logger.debug(f"Registered recovery handler for {category.value}")
    
    def classify_error(self, exception: Exception) -> ErrorCategory:
        """
        Classify an exception
        
        Args:
            exception: Exception to classify
            
        Returns:
            Error category
        """
        exception_type = type(exception).__name__.lower()
        exception_module = type(exception).__module__.lower()
        
        # Network errors
        if any(keyword in exception_type or keyword in exception_module 
               for keyword in ['connection', 'timeout', 'network', 'socket']):
            return ErrorCategory.NETWORK
        
        # API errors
        if any(keyword in exception_type or keyword in exception_module 
               for keyword in ['http', 'api', 'request']):
            return ErrorCategory.API
        
        # Database errors
        if any(keyword in exception_type or keyword in exception_module 
               for keyword in ['database', 'db', 'sql', 'query']):
            return ErrorCategory.DATABASE
        
        # Filesystem errors
        if any(keyword in exception_type or keyword in exception_module 
               for keyword in ['file', 'io', 'os', 'path']):
            return ErrorCategory.FILESYSTEM
        
        # Validation errors
        if any(keyword in exception_type or keyword in exception_module 
               for keyword in ['validation', 'value', 'type']):
            return ErrorCategory.VALIDATION
        
        # Timeout errors
        if 'timeout' in exception_type:
            return ErrorCategory.TIMEOUT
        
        return ErrorCategory.UNKNOWN
    
    def assess_severity(self, exception: Exception) -> ErrorSeverity:
        """
        Assess error severity
        
        Args:
            exception: Exception to assess
            
        Returns:
            Error severity
        """
        exception_type = type(exception).__name__
        
        # Critical errors
        if exception_type in ['SystemExit', 'KeyboardInterrupt']:
            return ErrorSeverity.CRITICAL
        
        # High severity
        if any(keyword in exception_type for keyword in ['Critical', 'Fatal', 'Memory']):
            return ErrorSeverity.HIGH
        
        # Medium severity
        if any(keyword in exception_type for keyword in ['Error', 'Exception']):
            return ErrorSeverity.MEDIUM
        
        return ErrorSeverity.LOW
    
    async def handle_error(self, exception: Exception, context: Optional[Dict] = None) -> ErrorInfo:
        """
        Handle an error
        
        Args:
            exception: Exception to handle
            context: Error context
            
        Returns:
            Error information
        """
        # Classify error
        category = self.classify_error(exception)
        severity = self.assess_severity(exception)
        
        # Create error info
        error_info = ErrorInfo(
            exception=exception,
            category=category,
            severity=severity,
            context=context or {},
        )
        
        # Log error
        logger.error(
            f"Agent {self.agent_id} encountered {severity.value} {category.value} error: "
            f"{str(exception)}"
        )
        
        # Store in history
        async with self._lock:
            self.error_history.append(error_info)
            # Keep only last 100 errors
            if len(self.error_history) > 100:
                self.error_history.pop(0)
        
        # Attempt recovery
        await self._attempt_recovery(error_info)
        
        return error_info
    
    async def _attempt_recovery(self, error_info: ErrorInfo) -> None:
        """
        Attempt error recovery
        
        Args:
            error_info: Error information
        """
        handlers = self.recovery_handlers.get(error_info.category, [])
        
        for handler in handlers:
            try:
                result = await handler(error_info)
                if result:
                    logger.info(f"Recovery successful for {error_info.category.value} error")
                    return
            except Exception as e:
                logger.error(f"Recovery handler failed: {e}")
    
    def get_error_history(
        self,
        category: Optional[ErrorCategory] = None,
        severity: Optional[ErrorSeverity] = None,
        limit: int = 50
    ) -> List[ErrorInfo]:
        """
        Get error history
        
        Args:
            category: Optional category filter
            severity: Optional severity filter
            limit: Maximum number of errors to return
            
        Returns:
            List of error information
        """
        errors = self.error_history
        
        if category:
            errors = [e for e in errors if e.category == category]
        
        if severity:
            errors = [e for e in errors if e.severity == severity]
        
        return errors[-limit:]
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        total_errors = len(self.error_history)
        
        if total_errors == 0:
            return {
                "total_errors": 0,
                "by_category": {},
                "by_severity": {},
            }
        
        by_category = {}
        by_severity = {}
        
        for error in self.error_history:
            cat = error.category.value
            sev = error.severity.value
            
            by_category[cat] = by_category.get(cat, 0) + 1
            by_severity[sev] = by_severity.get(sev, 0) + 1
        
        return {
            "total_errors": total_errors,
            "by_category": by_category,
            "by_severity": by_severity,
        }


def retry_on_error(
    strategy_name: str = "default",
    exceptions: Optional[Type[Exception]] = None,
):
    """
    Decorator for retrying functions on error
    
    Args:
        strategy_name: Retry strategy name
        exceptions: Exception types to retry on
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Get error handler from instance
            handler = None
            if args and hasattr(args[0], '_error_handler'):
                handler = args[0]._error_handler
            
            strategy = handler.retry_strategies.get(strategy_name) if handler else None
            
            if not strategy:
                strategy = RetryStrategy()
            
            last_exception = None
            
            for attempt in range(strategy.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    # Check if we should retry
                    if exceptions and not isinstance(e, exceptions):
                        raise
                    
                    if attempt < strategy.max_retries:
                        delay = strategy.get_delay(attempt)
                        logger.warning(
                            f"Attempt {attempt + 1}/{strategy.max_retries} failed: {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"All {strategy.max_retries} retries failed")
                        raise
            
            raise last_exception
        
        return wrapper
    
    return decorator


def with_error_handling(
    category: ErrorCategory = ErrorCategory.UNKNOWN,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    default_return: Any = None,
):
    """
    Decorator for automatic error handling
    
    Args:
        category: Error category
        severity: Error severity
        default_return: Default return value on error
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Get error handler from instance
                handler = None
                if args and hasattr(args[0], '_error_handler'):
                    handler = args[0]._error_handler
                
                if handler:
                    await handler.handle_error(e, {
                        "function": func.__name__,
                        "args": args,
                        "kwargs": kwargs,
                    })
                else:
                    logger.error(f"Error in {func.__name__}: {e}")
                
                return default_return
        
        return wrapper
    
    return decorator


class CircuitBreaker:
    """
    Circuit breaker pattern implementation
    
    Prevents cascading failures by stopping calls to failing services.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception,
    ):
        """
        Initialize circuit breaker
        
        Args:
            failure_threshold: Number of failures before opening
            timeout: Time to wait before attempting recovery (seconds)
            expected_exception: Exception type that counts as failure
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half-open
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call function with circuit breaker protection
        
        Args:
            func: Function to call
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
        """
        async with self._lock:
            if self.state == "open":
                # Check if we should attempt recovery
                if (self.last_failure_time and 
                    time.time() - self.last_failure_time > self.timeout):
                    self.state = "half-open"
                    logger.info("Circuit breaker entering half-open state")
                else:
                    raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            
            # Success
            async with self._lock:
                if self.state == "half-open":
                    self.state = "closed"
                    self.failure_count = 0
                    logger.info("Circuit breaker closed")
            
            return result
        
        except self.expected_exception as e:
            async with self._lock:
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                if self.failure_count >= self.failure_threshold:
                    self.state = "open"
                    logger.error(
                        f"Circuit breaker OPEN after {self.failure_count} failures"
                    )
            
            raise
