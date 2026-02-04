"""
Agent Audit Logging and Tracing
"""

import json
import time
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from collections import deque

from .logger import get_logger

logger = get_logger(__name__)


class AuditEventType(Enum):
    """Audit event types"""
    AGENT_START = "agent_start"
    AGENT_STOP = "agent_stop"
    TASK_SUBMIT = "task_submit"
    TASK_COMPLETE = "task_complete"
    TASK_FAIL = "task_fail"
    TOOL_INVOKE = "tool_invoke"
    TOOL_RESULT = "tool_result"
    MESSAGE_SEND = "message_send"
    MESSAGE_RECEIVE = "message_receive"
    STATE_CHANGE = "state_change"
    ERROR = "error"
    SECURITY = "security"
    RESOURCE = "resource"


@dataclass
class AuditEvent:
    """Audit event"""
    event_type: AuditEventType
    agent_id: str
    timestamp: float = field(default_factory=time.time)
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class AuditLogger:
    """
    Audit logger for agent operations
    
    Provides:
    - Event logging
    - Audit trail
    - Event filtering
    - Export functionality
    """
    
    def __init__(self, max_events: int = 10000):
        """
        Initialize audit logger
        
        Args:
            max_events: Maximum events to keep in memory
        """
        self.events: deque = deque(maxlen=max_events)
        self.filters: Dict[str, Any] = {}
        self.export_callbacks: List[Callable] = []
    
    def log_event(
        self,
        event_type: AuditEventType,
        agent_id: str,
        data: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None
    ) -> None:
        """
        Log an audit event
        
        Args:
            event_type: Event type
            agent_id: Agent ID
            data: Event data
            metadata: Additional metadata
        """
        event = AuditEvent(
            event_type=event_type,
            agent_id=agent_id,
            data=data or {},
            metadata=metadata or {}
        )
        
        self.events.append(event)
        logger.debug(f"Audit event: {event_type.value} by {agent_id}")
    
    def get_events(
        self,
        event_type: Optional[AuditEventType] = None,
        agent_id: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: int = 100
    ) -> List[AuditEvent]:
        """
        Get filtered audit events
        
        Args:
            event_type: Filter by event type
            agent_id: Filter by agent ID
            start_time: Start timestamp
            end_time: End timestamp
            limit: Maximum results
            
        Returns:
            List of events
        """
        events = list(self.events)
        
        # Apply filters
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        if agent_id:
            events = [e for e in events if e.agent_id == agent_id]
        
        if start_time:
            events = [e for e in events if e.timestamp >= start_time]
        
        if end_time:
            events = [e for e in events if e.timestamp <= end_time]
        
        # Sort by timestamp (newest first)
        events.sort(key=lambda e: e.timestamp, reverse=True)
        
        return events[:limit]
    
    def get_event_count(
        self,
        event_type: Optional[AuditEventType] = None,
        agent_id: Optional[str] = None
    ) -> int:
        """
        Get event count
        
        Args:
            event_type: Filter by event type
            agent_id: Filter by agent ID
            
        Returns:
            Event count
        """
        events = self.get_events(event_type=event_type, agent_id=agent_id, limit=100000)
        return len(events)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get audit statistics"""
        event_counts = {}
        agent_counts = {}
        
        for event in self.events:
            # Count by type
            etype = event.event_type.value
            event_counts[etype] = event_counts.get(etype, 0) + 1
            
            # Count by agent
            agent_counts[event.agent_id] = agent_counts.get(event.agent_id, 0) + 1
        
        return {
            "total_events": len(self.events),
            "event_counts": event_counts,
            "agent_counts": agent_counts,
            "oldest_event": self.events[0].timestamp if self.events else None,
            "newest_event": self.events[-1].timestamp if self.events else None
        }
    
    def export_events(
        self,
        output_file: str,
        event_type: Optional[AuditEventType] = None,
        agent_id: Optional[str] = None,
        format: str = "json"
    ) -> bool:
        """
        Export audit events
        
        Args:
            output_file: Output file path
            event_type: Filter by event type
            agent_id: Filter by agent ID
            format: Export format (json, csv)
            
        Returns:
            True if successful
        """
        events = self.get_events(
            event_type=event_type,
            agent_id=agent_id,
            limit=100000
        )
        
        try:
            path = Path(output_file)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            if format == "json":
                data = [asdict(e) for e in events]
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
            
            elif format == "csv":
                import csv
                with open(path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(["timestamp", "event_type", "agent_id", "data"])
                    for event in events:
                        writer.writerow([
                            event.timestamp,
                            event.event_type.value,
                            event.agent_id,
                            json.dumps(event.data)
                        ])
            
            logger.info(f"Exported {len(events)} events to {output_file}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to export events: {e}")
            return False
    
    def clear_events(
        self,
        event_type: Optional[AuditEventType] = None,
        agent_id: Optional[str] = None
    ) -> int:
        """
        Clear audit events
        
        Args:
            event_type: Filter by event type
            agent_id: Filter by agent ID
            
        Returns:
            Number of events cleared
        """
        before_count = len(self.events)
        
        if event_type or agent_id:
            # Filter and keep
            filtered = []
            for event in self.events:
                if event_type and event.event_type != event_type:
                    filtered.append(event)
                elif agent_id and event.agent_id != agent_id:
                    filtered.append(event)
                else:
                    filtered.append(event)
            
            self.events = deque(filtered, maxlen=self.events.maxlen)
        else:
            # Clear all
            self.events.clear()
        
        cleared = before_count - len(self.events)
        logger.info(f"Cleared {cleared} audit events")
        return cleared


class Tracer:
    """
    Distributed tracer for agent operations
    
    Provides:
    - Operation tracing
    - Span management
    - Trace context propagation
    """
    
    def __init__(self):
        """Initialize tracer"""
        self.traces: Dict[str, Dict[str, Any]] = {}
        self.current_trace: Optional[str] = None
    
    def start_trace(
        self,
        operation_name: str,
        agent_id: str,
        parent_id: Optional[str] = None
    ) -> str:
        """
        Start a trace
        
        Args:
            operation_name: Operation name
            agent_id: Agent ID
            parent_id: Parent trace ID
            
        Returns:
            Trace ID
        """
        import uuid
        
        trace_id = str(uuid.uuid4())
        
        self.traces[trace_id] = {
            "trace_id": trace_id,
            "operation_name": operation_name,
            "agent_id": agent_id,
            "parent_id": parent_id,
            "start_time": time.time(),
            "end_time": None,
            "spans": [],
            "metadata": {}
        }
        
        self.current_trace = trace_id
        
        logger.debug(f"Started trace: {trace_id} for {operation_name}")
        return trace_id
    
    def end_trace(self, trace_id: Optional[str] = None) -> None:
        """
        End a trace
        
        Args:
            trace_id: Trace ID (uses current if None)
        """
        trace_id = trace_id or self.current_trace
        
        if trace_id and trace_id in self.traces:
            self.traces[trace_id]["end_time"] = time.time()
            logger.debug(f"Ended trace: {trace_id}")
    
    def start_span(
        self,
        span_name: str,
        metadata: Dict[str, Any] = None
    ) -> None:
        """
        Start a span within current trace
        
        Args:
            span_name: Span name
            metadata: Span metadata
        """
        if not self.current_trace:
            return
        
        trace = self.traces[self.current_trace]
        
        span = {
            "name": span_name,
            "start_time": time.time(),
            "end_time": None,
            "metadata": metadata or {}
        }
        
        trace["spans"].append(span)
    
    def end_span(self, span_name: str = None) -> None:
        """
        End a span
        
        Args:
            span_name: Span name (ends last if None)
        """
        if not self.current_trace:
            return
        
        trace = self.traces[self.current_trace]
        
        if span_name:
            # Find span by name
            for span in reversed(trace["spans"]):
                if span["name"] == span_name and span["end_time"] is None:
                    span["end_time"] = time.time()
                    break
        else:
            # End last span
            for span in reversed(trace["spans"]):
                if span["end_time"] is None:
                    span["end_time"] = time.time()
                    break
    
    def get_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """
        Get trace details
        
        Args:
            trace_id: Trace ID
            
        Returns:
            Trace details
        """
        return self.traces.get(trace_id)
    
    def get_current_trace(self) -> Optional[Dict[str, Any]]:
        """Get current trace"""
        if self.current_trace:
            return self.traces.get(self.current_trace)
        return None
    
    def list_traces(
        self,
        agent_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List traces
        
        Args:
            agent_id: Filter by agent ID
            limit: Maximum results
            
        Returns:
            List of traces
        """
        traces = list(self.traces.values())
        
        if agent_id:
            traces = [t for t in traces if t["agent_id"] == agent_id]
        
        # Sort by start time (newest first)
        traces.sort(key=lambda t: t["start_time"], reverse=True)
        
        return traces[:limit]


def get_audit_logger() -> AuditLogger:
    """Get global audit logger instance"""
    if not hasattr(get_audit_logger, "_instance"):
        get_audit_logger._instance = AuditLogger()
    return get_audit_logger._instance


def get_tracer() -> Tracer:
    """Get global tracer instance"""
    if not hasattr(get_tracer, "_instance"):
        get_tracer._instance = Tracer()
    return get_tracer._instance
