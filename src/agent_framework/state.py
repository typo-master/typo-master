"""
State Management - Agent State Persistence and Recovery

This module provides state management for agents, including state
persistence, recovery, and versioning.
"""

import json
import os
import time
import threading
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
import hashlib

from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class StateSnapshot:
    """State snapshot"""
    state_id: str
    agent_id: str
    timestamp: float
    state_data: Dict[str, Any]
    version: str = "1.0.0"
    checksum: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Calculate checksum after initialization"""
        if not self.checksum:
            self.checksum = self._calculate_checksum()
    
    def _calculate_checksum(self) -> str:
        """Calculate checksum of state data"""
        state_str = json.dumps(self.state_data, sort_keys=True)
        return hashlib.sha256(state_str.encode()).hexdigest()
    
    def verify(self) -> bool:
        """Verify state integrity"""
        return self._calculate_checksum() == self.checksum


class StateStore:
    """
    State storage backend
    
    Provides:
    - File-based storage
    - State versioning
    - Checksum verification
    - Backup and restore
    """
    
    def __init__(self, storage_path: str = "./agent_states"):
        """
        Initialize state store
        
        Args:
            storage_path: Path to store state files
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
    
    def save(self, snapshot: StateSnapshot) -> str:
        """
        Save state snapshot
        
        Args:
            snapshot: State snapshot to save
            
        Returns:
            File path
        """
        with self._lock:
            # Create agent directory
            agent_dir = self.storage_path / snapshot.agent_id
            agent_dir.mkdir(exist_ok=True)
            
            # Save state
            file_path = agent_dir / f"{snapshot.state_id}.json"
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(snapshot), f, indent=2, default=str)
            
            logger.debug(f"Saved state snapshot: {snapshot.state_id}")
            return str(file_path)
    
    def load(self, agent_id: str, state_id: str) -> Optional[StateSnapshot]:
        """
        Load state snapshot
        
        Args:
            agent_id: Agent ID
            state_id: State ID
            
        Returns:
            State snapshot or None
        """
        with self._lock:
            file_path = self.storage_path / agent_id / f"{state_id}.json"
            
            if not file_path.exists():
                return None
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                snapshot = StateSnapshot(**data)
                
                # Verify integrity
                if not snapshot.verify():
                    logger.warning(f"State snapshot {state_id} checksum mismatch")
                    return None
                
                logger.debug(f"Loaded state snapshot: {state_id}")
                return snapshot
            
            except Exception as e:
                logger.error(f"Error loading state snapshot: {e}")
                return None
    
    def list_snapshots(self, agent_id: str) -> List[str]:
        """
        List all state snapshots for an agent
        
        Args:
            agent_id: Agent ID
            
        Returns:
            List of state IDs
        """
        with self._lock:
            agent_dir = self.storage_path / agent_id
            
            if not agent_dir.exists():
                return []
            
            snapshots = []
            for file_path in agent_dir.glob("*.json"):
                state_id = file_path.stem
                snapshots.append(state_id)
            
            return sorted(snapshots)
    
    def get_latest_snapshot(self, agent_id: str) -> Optional[StateSnapshot]:
        """
        Get the latest state snapshot for an agent
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Latest state snapshot or None
        """
        snapshots = self.list_snapshots(agent_id)
        
        if not snapshots:
            return None
        
        latest_id = snapshots[-1]
        return self.load(agent_id, latest_id)
    
    def delete_snapshot(self, agent_id: str, state_id: str) -> bool:
        """
        Delete a state snapshot
        
        Args:
            agent_id: Agent ID
            state_id: State ID
            
        Returns:
            True if deleted
        """
        with self._lock:
            file_path = self.storage_path / agent_id / f"{state_id}.json"
            
            if file_path.exists():
                file_path.unlink()
                logger.debug(f"Deleted state snapshot: {state_id}")
                return True
            
            return False
    
    def cleanup_old_snapshots(self, agent_id: str, keep_count: int = 10) -> int:
        """
        Cleanup old snapshots, keeping only the most recent ones
        
        Args:
            agent_id: Agent ID
            keep_count: Number of snapshots to keep
            
        Returns:
            Number of snapshots deleted
        """
        snapshots = self.list_snapshots(agent_id)
        
        if len(snapshots) <= keep_count:
            return 0
        
        to_delete = snapshots[:-keep_count]
        deleted_count = 0
        
        for state_id in to_delete:
            if self.delete_snapshot(agent_id, state_id):
                deleted_count += 1
        
        logger.debug(f"Cleaned up {deleted_count} old snapshots")
        return deleted_count


class StateManager:
    """
    State manager for agents
    
    Provides:
    - State persistence
    - State recovery
    - State versioning
    - Automatic cleanup
    """
    
    def __init__(self, agent_id: str, enable_persistence: bool = True):
        """
        Initialize state manager
        
        Args:
            agent_id: Agent ID
            enable_persistence: Enable state persistence
        """
        self.agent_id = agent_id
        self.enable_persistence = enable_persistence
        self.store = StateStore()
        self.current_state: Dict[str, Any] = {}
        self.state_version = 0
        self.last_save_time: Optional[float] = None
        self.auto_save_interval = 300.0  # 5 minutes
        self._lock = threading.Lock()
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a state value
        
        Args:
            key: State key
            value: State value
        """
        with self._lock:
            self.current_state[key] = value
            self.state_version += 1
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a state value
        
        Args:
            key: State key
            default: Default value
            
        Returns:
            State value or default
        """
        with self._lock:
            return self.current_state.get(key, default)
    
    def delete(self, key: str) -> bool:
        """
        Delete a state value
        
        Args:
            key: State key
            
        Returns:
            True if deleted
        """
        with self._lock:
            if key in self.current_state:
                del self.current_state[key]
                self.state_version += 1
                return True
            return False
    
    def get_all(self) -> Dict[str, Any]:
        """Get all state values"""
        with self._lock:
            return self.current_state.copy()
    
    def clear(self) -> None:
        """Clear all state"""
        with self._lock:
            self.current_state.clear()
            self.state_version = 0
    
    async def save_state(self) -> Optional[str]:
        """
        Save current state
        
        Returns:
            State ID or None
        """
        if not self.enable_persistence:
            return None
        
        with self._lock:
            state_id = f"{self.agent_id}_{int(time.time())}_{self.state_version}"
            
            snapshot = StateSnapshot(
                state_id=state_id,
                agent_id=self.agent_id,
                timestamp=time.time(),
                state_data=self.current_state.copy(),
                metadata={
                    "version": self.state_version,
                }
            )
            
            try:
                file_path = self.store.save(snapshot)
                self.last_save_time = time.time()
                logger.info(f"Saved state: {state_id}")
                return state_id
            except Exception as e:
                logger.error(f"Error saving state: {e}")
                return None
    
    async def load_state(self) -> bool:
        """
        Load latest state
        
        Returns:
            True if loaded successfully
        """
        if not self.enable_persistence:
            return False
        
        with self._lock:
            snapshot = self.store.get_latest_snapshot(self.agent_id)
            
            if not snapshot:
                logger.info(f"No previous state found for agent {self.agent_id}")
                return False
            
            try:
                self.current_state = snapshot.state_data.copy()
                self.state_version = snapshot.metadata.get("version", 0)
                logger.info(f"Loaded state: {snapshot.state_id}")
                return True
            except Exception as e:
                logger.error(f"Error loading state: {e}")
                return False
    
    async def restore_state(self, state_id: str) -> bool:
        """
        Restore a specific state
        
        Args:
            state_id: State ID to restore
            
        Returns:
            True if restored successfully
        """
        if not self.enable_persistence:
            return False
        
        with self._lock:
            snapshot = self.store.load(self.agent_id, state_id)
            
            if not snapshot:
                logger.warning(f"State snapshot not found: {state_id}")
                return False
            
            try:
                self.current_state = snapshot.state_data.copy()
                self.state_version = snapshot.metadata.get("version", 0)
                logger.info(f"Restored state: {state_id}")
                return True
            except Exception as e:
                logger.error(f"Error restoring state: {e}")
                return False
    
    def list_states(self) -> List[str]:
        """List all available states"""
        return self.store.list_snapshots(self.agent_id)
    
    def should_auto_save(self) -> bool:
        """Check if auto-save should be triggered"""
        if not self.enable_persistence:
            return False
        
        if self.last_save_time is None:
            return True
        
        return (time.time() - self.last_save_time) >= self.auto_save_interval
    
    def cleanup_old_states(self, keep_count: int = 10) -> int:
        """
        Cleanup old state snapshots
        
        Args:
            keep_count: Number of snapshots to keep
            
        Returns:
            Number of snapshots deleted
        """
        return self.store.cleanup_old_snapshots(self.agent_id, keep_count)
