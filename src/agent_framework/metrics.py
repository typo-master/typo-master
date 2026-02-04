"""
Metrics and Monitoring - Agent Performance Metrics

This module provides metrics collection and monitoring for agents.
"""

import time
import threading
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime

from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class Metric:
    """Metric data point"""
    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class Counter:
    """Counter metric"""
    name: str
    value: int = 0
    tags: Dict[str, str] = field(default_factory=dict)
    
    def increment(self, amount: int = 1) -> None:
        """Increment counter"""
        self.value += amount
    
    def decrement(self, amount: int = 1) -> None:
        """Decrement counter"""
        self.value -= amount
    
    def get(self) -> int:
        """Get current value"""
        return self.value
    
    def reset(self) -> None:
        """Reset counter"""
        self.value = 0


@dataclass
class Gauge:
    """Gauge metric"""
    name: str
    value: float = 0.0
    tags: Dict[str, str] = field(default_factory=dict)
    
    def set(self, value: float) -> None:
        """Set gauge value"""
        self.value = value
    
    def increment(self, amount: float = 1.0) -> None:
        """Increment gauge"""
        self.value += amount
    
    def decrement(self, amount: float = 1.0) -> None:
        """Decrement gauge"""
        self.value -= amount
    
    def get(self) -> float:
        """Get current value"""
        return self.value


@dataclass
class Histogram:
    """Histogram metric"""
    name: str
    values: List[float] = field(default_factory=list)
    tags: Dict[str, str] = field(default_factory=dict)
    max_samples: int = 1000
    
    def observe(self, value: float) -> None:
        """Observe a value"""
        self.values.append(value)
        
        # Keep only recent values
        if len(self.values) > self.max_samples:
            self.values = self.values[-self.max_samples:]
    
    def get_count(self) -> int:
        """Get count of observations"""
        return len(self.values)
    
    def get_sum(self) -> float:
        """Get sum of observations"""
        return sum(self.values)
    
    def get_avg(self) -> float:
        """Get average of observations"""
        if not self.values:
            return 0.0
        return self.get_sum() / len(self.values)
    
    def get_min(self) -> float:
        """Get minimum observation"""
        return min(self.values) if self.values else 0.0
    
    def get_max(self) -> float:
        """Get maximum observation"""
        return max(self.values) if self.values else 0.0
    
    def get_percentile(self, percentile: float) -> float:
        """Get percentile value"""
        if not self.values:
            return 0.0
        
        sorted_values = sorted(self.values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def reset(self) -> None:
        """Reset histogram"""
        self.values.clear()


class MetricsCollector:
    """
    Metrics collector for agents
    
    Provides:
    - Counter metrics
    - Gauge metrics
    - Histogram metrics
    - Metric aggregation
    - Metric export
    """
    
    def __init__(self):
        """Initialize metrics collector"""
        self.counters: Dict[str, Counter] = {}
        self.gauges: Dict[str, Gauge] = {}
        self.histograms: Dict[str, Histogram] = {}
        self._lock = threading.Lock()
    
    def counter(self, name: str, tags: Optional[Dict[str, str]] = None) -> Counter:
        """
        Get or create a counter
        
        Args:
            name: Counter name
            tags: Optional tags
            
        Returns:
            Counter instance
        """
        key = self._make_key(name, tags)
        
        with self._lock:
            if key not in self.counters:
                self.counters[key] = Counter(name=name, tags=tags or {})
            return self.counters[key]
    
    def gauge(self, name: str, tags: Optional[Dict[str, str]] = None) -> Gauge:
        """
        Get or create a gauge
        
        Args:
            name: Gauge name
            tags: Optional tags
            
        Returns:
            Gauge instance
        """
        key = self._make_key(name, tags)
        
        with self._lock:
            if key not in self.gauges:
                self.gauges[key] = Gauge(name=name, tags=tags or {})
            return self.gauges[key]
    
    def histogram(self, name: str, tags: Optional[Dict[str, str]] = None) -> Histogram:
        """
        Get or create a histogram
        
        Args:
            name: Histogram name
            tags: Optional tags
            
        Returns:
            Histogram instance
        """
        key = self._make_key(name, tags)
        
        with self._lock:
            if key not in self.histograms:
                self.histograms[key] = Histogram(name=name, tags=tags or {})
            return self.histograms[key]
    
    def increment_counter(self, name: str, amount: int = 1, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Increment a counter
        
        Args:
            name: Counter name
            amount: Amount to increment
            tags: Optional tags
        """
        counter = self.counter(name, tags)
        counter.increment(amount)
    
    def decrement_counter(self, name: str, amount: int = 1, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Decrement a counter
        
        Args:
            name: Counter name
            amount: Amount to decrement
            tags: Optional tags
        """
        counter = self.counter(name, tags)
        counter.decrement(amount)
    
    def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Set a gauge value
        
        Args:
            name: Gauge name
            value: Value to set
            tags: Optional tags
        """
        gauge = self.gauge(name, tags)
        gauge.set(value)
    
    def observe_histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Observe a histogram value
        
        Args:
            name: Histogram name
            value: Value to observe
            tags: Optional tags
        """
        histogram = self.histogram(name, tags)
        histogram.observe(value)
    
    def get_all_metrics(self) -> Dict[str, List[Metric]]:
        """
        Get all metrics
        
        Returns:
            Dictionary of metric type to list of metrics
        """
        metrics = {
            "counters": [],
            "gauges": [],
            "histograms": [],
        }
        
        with self._lock:
            # Collect counters
            for counter in self.counters.values():
                metrics["counters"].append(Metric(
                    name=counter.name,
                    value=float(counter.value),
                    tags=counter.tags,
                ))
            
            # Collect gauges
            for gauge in self.gauges.values():
                metrics["gauges"].append(Metric(
                    name=gauge.name,
                    value=gauge.value,
                    tags=gauge.tags,
                ))
            
            # Collect histograms
            for histogram in self.histograms.values():
                if histogram.values:
                    metrics["histograms"].append(Metric(
                        name=histogram.name,
                        value=histogram.get_avg(),
                        tags=histogram.tags,
                    ))
        
        return metrics
    
    def reset(self) -> None:
        """Reset all metrics"""
        with self._lock:
            for counter in self.counters.values():
                counter.reset()
            
            for histogram in self.histograms.values():
                histogram.reset()
    
    def _make_key(self, name: str, tags: Optional[Dict[str, str]] = None) -> str:
        """
        Make a unique key for a metric
        
        Args:
            name: Metric name
            tags: Optional tags
            
        Returns:
            Unique key
        """
        if tags:
            tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
            return f"{name}{{{tag_str}}}"
        return name


class PerformanceMonitor:
    """
    Performance monitor for agent operations
    
    Provides:
    - Timing measurements
    - Performance metrics
    - Slow operation detection
    """
    
    def __init__(self, metrics_collector: MetricsCollector):
        """
        Initialize performance monitor
        
        Args:
            metrics_collector: Metrics collector
        """
        self.metrics = metrics_collector
        self._operations: Dict[str, List[float]] = defaultdict(list)
    
    def time_operation(self, name: str, tags: Optional[Dict[str, str]] = None):
        """
        Context manager for timing operations
        
        Args:
            name: Operation name
            tags: Optional tags
            
        Returns:
            Context manager
        """
        class Timer:
            def __init__(self, monitor, op_name, op_tags):
                self.monitor = monitor
                self.op_name = op_name
                self.op_tags = op_tags
                self.start_time = None
            
            def __enter__(self):
                self.start_time = time.time()
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                if self.start_time:
                    duration = time.time() - self.start_time
                    self.monitor.record_operation(self.op_name, duration, self.op_tags)
                return False
        
        return Timer(self, name, tags)
    
    def record_operation(self, name: str, duration: float, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Record an operation duration
        
        Args:
            name: Operation name
            duration: Duration in seconds
            tags: Optional tags
        """
        # Record in histogram
        self.metrics.observe_histogram(f"{name}_duration", duration, tags)
        
        # Store for slow operation detection
        self._operations[name].append(duration)
        
        # Keep only recent operations
        if len(self._operations[name]) > 100:
            self._operations[name] = self._operations[name][-100:]
    
    def get_operation_stats(self, name: str) -> Dict[str, float]:
        """
        Get statistics for an operation
        
        Args:
            name: Operation name
            
        Returns:
            Statistics dictionary
        """
        durations = self._operations.get(name, [])
        
        if not durations:
            return {
                "count": 0,
                "avg": 0.0,
                "min": 0.0,
                "max": 0.0,
                "p50": 0.0,
                "p95": 0.0,
                "p99": 0.0,
            }
        
        sorted_durations = sorted(durations)
        
        return {
            "count": len(durations),
            "avg": sum(durations) / len(durations),
            "min": sorted_durations[0],
            "max": sorted_durations[-1],
            "p50": sorted_durations[int(len(sorted_durations) * 0.5)],
            "p95": sorted_durations[int(len(sorted_durations) * 0.95)],
            "p99": sorted_durations[int(len(sorted_durations) * 0.99)],
        }
    
    def is_slow_operation(self, name: str, threshold: float = 1.0) -> bool:
        """
        Check if an operation is slow
        
        Args:
            name: Operation name
            threshold: Threshold in seconds
            
        Returns:
            True if slow
        """
        durations = self._operations.get(name, [])
        
        if not durations:
            return False
        
        avg_duration = sum(durations) / len(durations)
        return avg_duration > threshold


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector instance"""
    if not hasattr(get_metrics_collector, "_instance"):
        get_metrics_collector._instance = MetricsCollector()
    return get_metrics_collector._instance
