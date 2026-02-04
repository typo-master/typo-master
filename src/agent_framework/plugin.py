"""
Agent Plugin System
"""

import importlib
import inspect
import sys
from typing import Dict, Any, List, Optional, Type, Callable
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

from .logger import get_logger

logger = get_logger(__name__)


class PluginStatus(Enum):
    """Plugin status"""
    LOADED = "loaded"
    UNLOADED = "unloaded"
    ERROR = "error"


@dataclass
class PluginInfo:
    """Plugin information"""
    name: str
    version: str
    description: str
    author: str = ""
    dependencies: List[str] = field(default_factory=list)
    status: PluginStatus = PluginStatus.UNLOADED
    module: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class PluginManager:
    """
    Plugin manager for agents
    
    Provides:
    - Plugin loading
    - Plugin lifecycle management
    - Plugin discovery
    - Plugin dependencies
    """
    
    def __init__(self, plugin_dir: Optional[str] = None):
        """
        Initialize plugin manager
        
        Args:
            plugin_dir: Plugin directory path
        """
        self.plugin_dir = plugin_dir
        self.plugins: Dict[str, PluginInfo] = {}
        self.hooks: Dict[str, List[Callable]] = {}
    
    def discover_plugins(self) -> List[PluginInfo]:
        """
        Discover plugins in plugin directory
        
        Returns:
            List of discovered plugins
        """
        if not self.plugin_dir:
            logger.warning("No plugin directory specified")
            return []
        
        plugin_dir = Path(self.plugin_dir)
        if not plugin_dir.exists():
            logger.warning(f"Plugin directory does not exist: {self.plugin_dir}")
            return []
        
        plugins = []
        
        for plugin_file in plugin_dir.glob("*.py"):
            if plugin_file.name.startswith("_"):
                continue
            
            try:
                plugin_info = self._load_plugin_info(plugin_file)
                if plugin_info:
                    plugins.append(plugin_info)
            except Exception as e:
                logger.error(f"Failed to load plugin info from {plugin_file}: {e}")
        
        logger.info(f"Discovered {len(plugins)} plugins")
        return plugins
    
    def _load_plugin_info(self, plugin_file: Path) -> Optional[PluginInfo]:
        """
        Load plugin info from file
        
        Args:
            plugin_file: Plugin file path
            
        Returns:
            Plugin info or None
        """
        try:
            # Import module
            spec = importlib.util.spec_from_file_location(
                plugin_file.stem,
                plugin_file
            )
            
            if spec is None or spec.loader is None:
                return None
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Get plugin metadata
            if hasattr(module, 'PLUGIN_INFO'):
                info = module.PLUGIN_INFO
                return PluginInfo(
                    name=info.get('name', plugin_file.stem),
                    version=info.get('version', '0.1.0'),
                    description=info.get('description', ''),
                    author=info.get('author', ''),
                    dependencies=info.get('dependencies', []),
                    metadata=info.get('metadata', {}),
                    module=module
                )
            
            return None
        
        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_file}: {e}")
            return None
    
    def load_plugin(self, name: str) -> bool:
        """
        Load a plugin
        
        Args:
            name: Plugin name
            
        Returns:
            True if loaded
        """
        if name not in self.plugins:
            logger.warning(f"Plugin not found: {name}")
            return False
        
        plugin = self.plugins[name]
        
        if plugin.status == PluginStatus.LOADED:
            logger.warning(f"Plugin already loaded: {name}")
            return True
        
        try:
            # Check dependencies
            for dep in plugin.dependencies:
                if dep not in self.plugins:
                    logger.error(f"Missing dependency: {dep}")
                    return False
                
                if self.plugins[dep].status != PluginStatus.LOADED:
                    logger.error(f"Dependency not loaded: {dep}")
                    return False
            
            # Initialize plugin
            if hasattr(plugin.module, 'initialize'):
                plugin.module.initialize()
            
            plugin.status = PluginStatus.LOADED
            logger.info(f"Loaded plugin: {name}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to load plugin {name}: {e}")
            plugin.status = PluginStatus.ERROR
            return False
    
    def unload_plugin(self, name: str) -> bool:
        """
        Unload a plugin
        
        Args:
            name: Plugin name
            
        Returns:
            True if unloaded
        """
        if name not in self.plugins:
            return False
        
        plugin = self.plugins[name]
        
        if plugin.status != PluginStatus.LOADED:
            return True
        
        try:
            # Cleanup plugin
            if hasattr(plugin.module, 'cleanup'):
                plugin.module.cleanup()
            
            plugin.status = PluginStatus.UNLOADED
            logger.info(f"Unloaded plugin: {name}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to unload plugin {name}: {e}")
            return False
    
    def register_hook(self, hook_name: str, callback: Callable) -> None:
        """
        Register a hook callback
        
        Args:
            hook_name: Hook name
            callback: Callback function
        """
        if hook_name not in self.hooks:
            self.hooks[hook_name] = []
        
        self.hooks[hook_name].append(callback)
    
    def trigger_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """
        Trigger a hook
        
        Args:
            hook_name: Hook name
            *args: Hook arguments
            **kwargs: Hook keyword arguments
            
        Returns:
            List of results
        """
        results = []
        
        for callback in self.hooks.get(hook_name, []):
            try:
                result = callback(*args, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"Hook callback failed: {e}")
        
        return results
    
    def get_plugin(self, name: str) -> Optional[PluginInfo]:
        """
        Get plugin by name
        
        Args:
            name: Plugin name
            
        Returns:
            Plugin info or None
        """
        return self.plugins.get(name)
    
    def list_plugins(self, status: Optional[PluginStatus] = None) -> List[PluginInfo]:
        """
        List plugins
        
        Args:
            status: Filter by status
            
        Returns:
            List of plugins
        """
        plugins = list(self.plugins.values())
        
        if status:
            plugins = [p for p in plugins if p.status == status]
        
        return plugins
    
    def get_plugin_count(self) -> Dict[str, int]:
        """Get plugin counts by status"""
        counts = {
            "total": len(self.plugins),
            "loaded": 0,
            "unloaded": 0,
            "error": 0
        }
        
        for plugin in self.plugins.values():
            counts[plugin.status.value] = counts.get(plugin.status.value, 0) + 1
        
        return counts


def get_plugin_manager(plugin_dir: Optional[str] = None) -> PluginManager:
    """Get global plugin manager instance"""
    if not hasattr(get_plugin_manager, "_instance"):
        get_plugin_manager._instance = PluginManager(plugin_dir)
    return get_plugin_manager._instance
