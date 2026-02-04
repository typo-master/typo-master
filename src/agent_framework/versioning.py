"""
Agent Versioning and Migration
"""

import json
import time
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from .logger import get_logger

logger = get_logger(__name__)


class VersionType(Enum):
    """Version types"""
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"
    BUILD = "build"


@dataclass
class Version:
    """Version information"""
    major: int = 0
    minor: int = 1
    patch: int = 0
    build: int = 0
    prerelease: str = ""
    metadata: str = ""
    
    def __str__(self) -> str:
        """String representation"""
        version = f"{self.major}.{self.minor}.{self.patch}"
        
        if self.build > 0:
            version += f".{self.build}"
        
        if self.prerelease:
            version += f"-{self.prerelease}"
        
        if self.metadata:
            version += f"+{self.metadata}"
        
        return version
    
    def increment(self, version_type: VersionType) -> 'Version':
        """Increment version"""
        if version_type == VersionType.MAJOR:
            self.major += 1
            self.minor = 0
            self.patch = 0
            self.build = 0
        elif version_type == VersionType.MINOR:
            self.minor += 1
            self.patch = 0
            self.build = 0
        elif version_type == VersionType.PATCH:
            self.patch += 1
            self.build = 0
        elif version_type == VersionType.BUILD:
            self.build += 1
        
        return self
    
    def __gt__(self, other) -> bool:
        """Greater than comparison"""
        if self.major != other.major:
            return self.major > other.major
        if self.minor != other.minor:
            return self.minor > other.minor
        if self.patch != other.patch:
            return self.patch > other.patch
        if self.build != other.build:
            return self.build > other.build
        return False
    
    def __eq__(self, other) -> bool:
        """Equality comparison"""
        return (
            self.major == other.major and
            self.minor == other.minor and
            self.patch == other.patch and
            self.build == other.build
        )


class Migration:
    """Migration for version changes"""
    
    def __init__(
        self,
        from_version: str,
        to_version: str,
        migrate_func: Callable
    ):
        """
        Initialize migration
        
        Args:
            from_version: Source version
            to_version: Target version
            migrate_func: Migration function
        """
        self.from_version = from_version
        self.to_version = to_version
        self.migrate_func = migrate_func
    
    async def migrate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute migration
        
        Args:
            data: Data to migrate
            
        Returns:
            Migrated data
        """
        logger.info(f"Migrating from {self.from_version} to {self.to_version}")
        return await self.migrate_func(data)


class VersionManager:
    """
    Manager for agent versioning
    
    Provides:
    - Version tracking
    - Migration support
    - Compatibility checking
    """
    
    def __init__(self):
        """Initialize version manager"""
        self.current_version = Version()
        self.migrations: List[Migration] = []
        self.version_history: List[Dict[str, Any]] = []
    
    def set_version(self, version: Version) -> None:
        """
        Set current version
        
        Args:
            version: Version to set
        """
        old_version = self.current_version
        self.current_version = version
        
        # Record in history
        self.version_history.append({
            "version": str(version),
            "timestamp": time.time(),
            "previous": str(old_version)
        })
        
        logger.info(f"Version updated to {version}")
    
    def get_version(self) -> Version:
        """Get current version"""
        return self.current_version
    
    def register_migration(self, migration: Migration) -> None:
        """
        Register a migration
        
        Args:
            migration: Migration to register
        """
        self.migrations.append(migration)
        logger.info(f"Registered migration: {migration.from_version} -> {migration.to_version}")
    
    async def migrate_to(
        self,
        target_version: str,
        data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Migrate to target version
        
        Args:
            target_version: Target version
            data: Data to migrate
            
        Returns:
            Migrated data
        """
        if data is None:
            data = {}
        
        current = str(self.current_version)
        
        if current == target_version:
            return data
        
        # Find applicable migrations
        for migration in self.migrations:
            if migration.from_version == current and migration.to_version == target_version:
                data = await migration.migrate(data)
                self.set_version(Version(*map(int, target_version.split('.'))))
                break
        
        return data
    
    def check_compatibility(
        self,
        version: str
    ) -> bool:
        """
        Check version compatibility
        
        Args:
            version: Version to check
            
        Returns:
            True if compatible
        """
        # Simple compatibility check
        parts = version.split('.')
        current_parts = str(self.current_version).split('.')
        
        # Major version must match
        if parts[0] != current_parts[0]:
            return False
        
        return True
    
    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get version history
        
        Args:
            limit: Maximum history entries
            
        Returns:
            Version history
        """
        return self.version_history[-limit:]


def get_version_manager() -> VersionManager:
    """Get global version manager instance"""
    if not hasattr(get_version_manager, "_instance"):
        get_version_manager._instance = VersionManager()
    return get_version_manager._instance
