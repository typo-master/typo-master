"""
Agent Analytics and Performance Analysis
"""

import time
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

from .logger import get_logger

logger = get_logger(__name__)


class MetricType(Enum):
    """Metric types"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricData:
    """Metric data point"""
    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    tags: Dict[str, str] = field(default_factory=dict)


class PerformanceAnalyzer:
    """
    Performance analyzer for agents
    
    Provides:
    - Performance metrics
    - Bottleneck detection
    - Performance profiling
    - Optimization suggestions
    """
    
    def __init__(self):
        """Initialize performance analyzer"""
        self.metrics: Dict[str, List[MetricData]] = defaultdict(list)
        self.operation_times: Dict[str, List[float]] = defaultdict(list)
        self._lock = None
    
    def record_metric(
        self,
        name: str,
        value: float,
        tags: Dict[str, str] = None
    ) -> None:
        """
        Record a metric
        
        Args:
            name: Metric name
            value: Metric value
            tags: Metric tags
        """
        metric = MetricData(
            name=name,
            value=value,
            tags=tags or {}
        )
        
        self.metrics[name].append(metric)
        
        # Keep only recent metrics
        if len(self.metrics[name]) > 10000:
            self.metrics[name] = self.metrics[name][-10000:]
    
    def record_operation_time(
        self,
        operation: str,
        duration: float
    ) -> None:
        """
        Record operation time
        
        Args:
            operation: Operation name
            duration: Duration in seconds
        """
        self.operation_times[operation].append(duration)
        
        # Keep only recent times
        if len(self.operation_times[operation]) > 10000:
            self.operation_times[operation] = self.operation_times[operation][-10000:]
    
    def get_operation_stats(self, operation: str) -> Dict[str, float]:
        """
        Get operation statistics
        
        Args:
            operation: Operation name
            
        Returns:
            Statistics
        """
        times = self.operation_times.get(operation, [])
        
        if not times:
            return {}
        
        times_sorted = sorted(times)
        
        return {
            "count": len(times),
            "min": times_sorted[0],
            "max": times_sorted[-1],
            "avg": sum(times) / len(times),
            "total": sum(times),
            "p50": times_sorted[int(len(times) * 0.5)],
            "p95": times_sorted[int(len(times) * 0.95)],
            "p99": times_sorted[int(len(times) * 0.99)],
        }
    
    def get_slow_operations(
        self,
        threshold: float = 1.0
    ) -> List[Dict[str, Any]]:
        """
        Get slow operations
        
        Args:
            threshold: Threshold in seconds
            
        Returns:
            List of slow operations
        """
        slow_ops = []
        
        for operation, times in self.operation_times.items():
            stats = self.get_operation_stats(operation)
            
            if stats.get("avg", 0) > threshold:
                slow_ops.append({
                    "operation": operation,
                    "avg_time": stats["avg"],
                    "max_time": stats["max"],
                    "count": stats["count"]
                })
        
        # Sort by average time
        slow_ops.sort(key=lambda x: x["avg_time"], reverse=True)
        
        return slow_ops
    
    def get_bottlenecks(self, threshold: float = 0.1) -> List[Dict[str, Any]]:
        """
        Detect bottlenecks
        
        Args:
            threshold: Bottleneck threshold
            
        Returns:
            List of bottlenecks
        """
        bottlenecks = []
        
        for operation, times in self.operation_times.items():
            if len(times) < 10:
                continue
            
            stats = self.get_operation_stats(operation)
            
            # Check for high variance
            if stats["max"] - stats["min"] > threshold * stats["avg"]:
                bottlenecks.append({
                    "type": "high_variance",
                    "operation": operation,
                    "variance": stats["max"] - stats["min"],
                    "avg": stats["avg"]
                })
            
            # Check for slow operations
            if stats["avg"] > 1.0:
                bottlenecks.append({
                    "type": "slow_operation",
                    "operation": operation,
                    "avg_time": stats["avg"],
                    "max_time": stats["max"]
                })
        
        return bottlenecks
    
    def get_optimization_suggestions(self) -> List[str]:
        """Get optimization suggestions"""
        suggestions = []
        
        # Check for slow operations
        slow_ops = self.get_slow_operations(threshold=0.5)
        
        if slow_ops:
            for op in slow_ops[:5]:
                suggestions.append(
                    f"Consider optimizing {op['operation']} "
                    f"(avg: {op['avg_time']:.2f}s, max: {op['max_time']:.2f}s)"
                )
        
        # Check for high frequency operations
        for operation, times in self.operation_times.items():
            if len(times) > 1000:
                stats = self.get_operation_stats(operation)
                suggestions.append(
                    f"Consider caching results for {operation} "
                    f"(called {len(times)} times)"
                )
        
        return suggestions


class Profiler:
    """
    Profiler for agent operations
    
    Provides:
    - Operation profiling
    - Call stack tracking
    - Performance breakdown
    """
    
    def __init__(self):
        """Initialize profiler"""
        self.profiles: Dict[str, List[float]] = defaultdict(list)
        self.call_stack: List[str] = []
        self._enabled = False
    
    def profile(self, operation: str):
        """
        Context manager for profiling
        
        Args:
            operation: Operation name
            
        Returns:
            Context manager
        """
        class ProfileContext:
            def __init__(self, profiler, op):
                self.profiler = profiler
                self.op = op
                self.start_time = None
            
            def __enter__(self):
                if self.profiler._enabled:
                    self.start_time = time.time()
                    self.profiler.call_stack.append(self.op)
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                if self.profiler._enabled:
                    duration = time.time() - self.start_time
                    self.profiler.profiles[self.op].append(duration)
                    if self.profiler.call_stack:
                        self.profiler.call_stack.pop()
                return False
        
        return ProfileContext(self, operation)
    
    def enable(self) -> None:
        """Enable profiling"""
        self._enabled = True
        logger.info("Profiling enabled")
    
    def disable(self) -> None:
        """Disable profiling"""
        self._enabled = False
        logger.info("Profiling disabled")
    
    def get_profile_stats(self, operation: str) -> Dict[str, float]:
        """
        Get profile statistics
        
        Args:
            operation: Operation name
            
        Returns:
            Statistics
        """
        times = self.profiles.get(operation, [])
        
        if not times:
            return {}
        
        times_sorted = sorted(times)
        
        return {
            "count": len(times),
            "min": times_sorted[0],
            "max": times_sorted[-1],
            "avg": sum(times) / len(times),
            "total": sum(times),
            "p50": times_sorted[int(len(times) * 0.5)],
            "p95": times_sorted[int(len(times) * 0.95)],
            "p99": times_sorted[int(len(times) * 0.99)],
        }
    
    def get_all_profiles(self) -> Dict[str, Dict[str, float]]:
        """Get all profiles"""
        return {
            op: self.get_profile_stats(op)
            for op in self.profiles.keys()
        }


class AnalyticsEngine:
    """
    Analytics engine for agent operations
    
    Provides:
    - Data collection
    - Analysis
    - Reporting
    - Visualization
    """
    
    def __init__(self):
        """Initialize analytics engine"""
        self.performance_analyzer = PerformanceAnalyzer()
        self.profiler = Profiler()
        self.events: List[Dict[str, Any]] = []
    
    def record_event(
        self,
        event_type: str,
        agent_id: str,
        data: Dict[str, Any] = None
    ) -> None:
        """
        Record an event
        
        Args:
            event_type: Event type
            agent_id: Agent ID
            data: Event data
        """
        event = {
            "event_type": event_type,
            "agent_id": agent_id,
            "timestamp": time.time(),
            "data": data or {}
        }
        
        self.events.append(event)
        
        # Keep only recent events
        if len(self.events) > 10000:
            self.events = self.events[-10000:]
    
    def get_events(
        self,
        event_type: str = None,
        agent_id: str = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get events
        
        Args:
            event_type: Filter by event type
            agent_id: Filter by agent ID
            limit: Maximum results
            
        Returns:
            List of events
        """
        events = self.events
        
        if event_type:
            events = [e for e in events if e["event_type"] == event_type]
        
        if agent_id:
            events = [e for e in events if e["agent_id"] == agent_id]
        
        # Sort by timestamp (newest first)
        events.sort(key=lambda e: e["timestamp"], reverse=True)
        
        return events[:limit]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get overall statistics"""
        event_counts = defaultdict(int)
        agent_counts = defaultdict(int)
        
        for event in self.events:
            event_counts[event["event_type"]] += 1
            agent_counts[event["agent_id"]] += 1
        
        return {
            "total_events": len(self.events),
            "event_counts": dict(event_counts),
            "agent_counts": dict(agent_counts),
            "operation_stats": {
                op: self.performance_analyzer.get_operation_stats(op)
                for op in self.performance_analyzer.operation_times.keys()
            }
        }
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate analytics report"""
        return {
            "statistics": self.get_statistics(),
            "slow_operations": self.performance_analyzer.get_slow_operations(),
            "bottlenecks": self.performance_analyzer.get_bottlenecks(),
            "optimizations": self.performance_analyzer.get_optimization_suggestions(),
            "profiles": self.profiler.get_all_profiles()
        }


def get_analytics_engine() -> AnalyticsEngine:
    """Get global analytics engine instance"""
    if not hasattr(get_analytics_engine, "_instance"):
        get_analytics_engine._instance = AnalyticsEngine()
    return get_analytics_engine._instance
