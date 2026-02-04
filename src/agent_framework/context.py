"""
Context Management - Agent Context and Memory System

This module provides context management for agents, including short-term
and long-term memory, context propagation, and context isolation.
"""

import json
import time
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime
from collections import deque
import threading

from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class ContextEntry:
    """Single context entry"""
    key: str
    value: Any
    timestamp: float = field(default_factory=time.time)
    ttl: Optional[float] = None  # Time to live in seconds
    metadata: Dict[str, Any] = field(default_factory=dict)


class Context:
    """
    Agent context - stores working variables and state
    
    Provides:
    - Key-value storage
    - TTL support
    - Metadata tracking
    - Context isolation
    """
    
    def __init__(self, context_id: str, parent: Optional['Context'] = None):
        """
        Initialize context
        
        Args:
            context_id: Unique context ID
            parent: Optional parent context for inheritance
        """
        self.context_id = context_id
        self.parent = parent
        self.data: Dict[str, ContextEntry] = {}
        self._lock = threading.Lock()
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None, metadata: Optional[Dict] = None) -> None:
        """
        Set a value in context
        
        Args:
            key: Key to set
            value: Value to store
            ttl: Optional time-to-live in seconds
            metadata: Optional metadata
        """
        with self._lock:
            entry = ContextEntry(
                key=key,
                value=value,
                ttl=ttl,
                timestamp=time.time(),
                metadata=metadata or {},
            )
            self.data[key] = entry
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value from context
        
        Args:
            key: Key to retrieve
            default: Default value if not found
            
        Returns:
            Value or default
        """
        with self._lock:
            # Check local context
            entry = self.data.get(key)
            if entry:
                # Check TTL
                if entry.ttl and (time.time() - entry.timestamp) > entry.ttl:
                    del self.data[key]
                    return default
                return entry.value
            
            # Check parent context
            if self.parent:
                return self.parent.get(key, default)
            
            return default
    
    def delete(self, key: str) -> bool:
        """
        Delete a value from context
        
        Args:
            key: Key to delete
            
        Returns:
            True if deleted
        """
        with self._lock:
            if key in self.data:
                del self.data[key]
                return True
            return False
    
    def has(self, key: str) -> bool:
        """
        Check if key exists in context
        
        Args:
            key: Key to check
            
        Returns:
            True if exists
        """
        with self._lock:
            if key in self.data:
                entry = self.data[key]
                # Check TTL
                if entry.ttl and (time.time() - entry.timestamp) > entry.ttl:
                    del self.data[key]
                    return False
                return True
            
            if self.parent:
                return self.parent.has(key)
            
            return False
    
    def keys(self) -> List[str]:
        """Get all keys in context"""
        with self._lock:
            keys = list(self.data.keys())
            if self.parent:
                keys.extend(self.parent.keys())
            return list(set(keys))
    
    def clear(self) -> None:
        """Clear all context data"""
        with self._lock:
            self.data.clear()
    
    def cleanup_expired(self) -> int:
        """
        Clean up expired entries
        
        Returns:
            Number of entries removed
        """
        with self._lock:
            current_time = time.time()
            expired_keys = [
                key for key, entry in self.data.items()
                if entry.ttl and (current_time - entry.timestamp) > entry.ttl
            ]
            
            for key in expired_keys:
                del self.data[key]
            
            return len(expired_keys)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary"""
        with self._lock:
            return {
                key: entry.value
                for key, entry in self.data.items()
                if not entry.ttl or (time.time() - entry.timestamp) <= entry.ttl
            }
    
    def merge(self, other: 'Context') -> None:
        """
        Merge another context into this one
        
        Args:
            other: Context to merge
        """
        with self._lock:
            for key, entry in other.data.items():
                if key not in self.data:
                    self.data[key] = entry


class ContextManager:
    """
    Manages multiple contexts and their lifecycle
    
    Provides:
    - Context creation and management
    - Context isolation
    - Context inheritance
    - Context cleanup
    """
    
    def __init__(self):
        self.contexts: Dict[str, Context] = {}
        self.root_context = Context("root")
        self.contexts["root"] = self.root_context
        self._lock = threading.Lock()
    
    def create_context(self, context_id: str, parent_id: Optional[str] = None) -> Context:
        """
        Create a new context
        
        Args:
            context_id: Unique context ID
            parent_id: Optional parent context ID
            
        Returns:
            New context
        """
        with self._lock:
            parent = self.contexts.get(parent_id) if parent_id else self.root_context
            context = Context(context_id, parent=parent)
            self.contexts[context_id] = context
            logger.debug(f"Created context: {context_id}")
            return context
    
    def get_context(self, context_id: str) -> Optional[Context]:
        """
        Get a context by ID
        
        Args:
            context_id: Context ID
            
        Returns:
            Context or None
        """
        with self._lock:
            return self.contexts.get(context_id)
    
    def delete_context(self, context_id: str) -> bool:
        """
        Delete a context
        
        Args:
            context_id: Context ID
            
        Returns:
            True if deleted
        """
        with self._lock:
            if context_id in self.contexts and context_id != "root":
                del self.contexts[context_id]
                logger.debug(f"Deleted context: {context_id}")
                return True
            return False
    
    def cleanup_all(self) -> int:
        """
        Clean up expired entries in all contexts
        
        Returns:
            Total number of entries removed
        """
        with self._lock:
            total = 0
            for context in self.contexts.values():
                total += context.cleanup_expired()
            return total
    
    def get_all_contexts(self) -> List[str]:
        """Get all context IDs"""
        with self._lock:
            return list(self.contexts.keys())
    
    def clear_all(self) -> None:
        """Clear all contexts except root"""
        with self._lock:
            for context_id in list(self.contexts.keys()):
                if context_id != "root":
                    del self.contexts[context_id]
            self.root_context.clear()


class Memory:
    """
    Agent memory system - stores and retrieves information
    
    Provides:
    - Short-term memory (in-memory)
    - Long-term memory (persistent)
    - Semantic search
    - Context retrieval
    """
    
    def __init__(self, agent_id: str, max_short_term: int = 1000):
        """
        Initialize memory
        
        Args:
            agent_id: Agent ID
            max_short_term: Maximum short-term memory entries
        """
        self.agent_id = agent_id
        self.short_term: deque = deque(maxlen=max_short_term)
        self.long_term: Dict[str, Any] = {}
        self._lock = threading.Lock()
    
    def remember(self, key: str, value: Any, category: str = "general") -> None:
        """
        Remember information
        
        Args:
            key: Memory key
            value: Value to remember
            category: Memory category
        """
        with self._lock:
            # Add to short-term memory
            self.short_term.append({
                "key": key,
                "value": value,
                "category": category,
                "timestamp": time.time(),
            })
            
            # Add to long-term memory
            if category not in self.long_term:
                self.long_term[category] = {}
            self.long_term[category][key] = {
                "value": value,
                "timestamp": time.time(),
            }
    
    def recall(self, key: str, category: Optional[str] = None) -> Optional[Any]:
        """
        Recall information from memory
        
        Args:
            key: Memory key
            category: Optional category filter
            
        Returns:
            Recalled value or None
        """
        with self._lock:
            # Search in specific category
            if category and category in self.long_term:
                entry = self.long_term[category].get(key)
                if entry:
                    return entry["value"]
            
            # Search all categories
            for cat_data in self.long_term.values():
                entry = cat_data.get(key)
                if entry:
                    return entry["value"]
            
            return None
    
    def recall_recent(self, limit: int = 10, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Recall recent memories
        
        Args:
            limit: Maximum number of entries
            category: Optional category filter
            
        Returns:
            List of recent memories
        """
        with self._lock:
            memories = list(self.short_term)
            
            if category:
                memories = [m for m in memories if m["category"] == category]
            
            return memories[-limit:]
    
    def forget(self, key: str, category: Optional[str] = None) -> bool:
        """
        Forget information
        
        Args:
            key: Memory key
            category: Optional category
            
        Returns:
            True if forgotten
        """
        with self._lock:
            if category and category in self.long_term:
                if key in self.long_term[category]:
                    del self.long_term[category][key]
                    return True
            else:
                for cat_data in self.long_term.values():
                    if key in cat_data:
                        del cat_data[key]
                        return True
            return False
    
    def search(self, query: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search memory
        
        Args:
            query: Search query
            category: Optional category filter
            
        Returns:
            List of matching memories
        """
        with self._lock:
            results = []
            query_lower = query.lower()
            
            # Search long-term memory
            for cat_name, cat_data in self.long_term.items():
                if category and cat_name != category:
                    continue
                
                for key, entry in cat_data.items():
                    value = entry["value"]
                    if isinstance(value, str) and query_lower in value.lower():
                        results.append({
                            "key": key,
                            "value": value,
                            "category": cat_name,
                            "timestamp": entry["timestamp"],
                        })
                    elif query_lower in key.lower():
                        results.append({
                            "key": key,
                            "value": value,
                            "category": cat_name,
                            "timestamp": entry["timestamp"],
                        })
            
            return results
    
    def clear_category(self, category: str) -> None:
        """
        Clear all memories in a category
        
        Args:
            category: Category to clear
        """
        with self._lock:
            if category in self.long_term:
                del self.long_term[category]
    
    def get_categories(self) -> List[str]:
        """Get all memory categories"""
        with self._lock:
            return list(self.long_term.keys())
    
    def export(self) -> Dict[str, Any]:
        """Export memory to dictionary"""
        with self._lock:
            return {
                "agent_id": self.agent_id,
                "long_term": self.long_term,
                "short_term_count": len(self.short_term),
            }
    
    def import_data(self, data: Dict[str, Any]) -> None:
        """
        Import memory from dictionary
        
        Args:
            data: Memory data
        """
        with self._lock:
            self.long_term = data.get("long_term", {})
