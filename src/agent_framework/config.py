"""
Configuration Management - Agent Configuration System

This module provides configuration management for agents.
"""

import os
import json
import yaml
from typing import Any, Dict, List, Optional
from pathlib import Path
from dataclasses import dataclass, field, asdict

from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class AgentConfig:
    """Agent configuration"""
    name: str
    version: str = "1.0.0"
    description: str = ""
    max_retries: int = 3
    timeout: float = 300.0
    log_level: str = "INFO"
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemConfig:
    """System-wide configuration"""
    log_level: str = "INFO"
    log_file: Optional[str] = None
    state_dir: str = "./state"
    cache_dir: str = "./cache"
    temp_dir: str = "./temp"
    max_concurrent_tasks: int = 10
    task_timeout: float = 3600.0
    enable_metrics: bool = True
    enable_tracing: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GitHubConfig:
    """GitHub API configuration"""
    token: Optional[str] = None
    base_url: str = "https://api.github.com"
    timeout: float = 30.0
    max_retries: int = 3
    rate_limit_delay: float = 1.0


@dataclass
class SpellConfig:
    """Spell checking configuration"""
    enabled: bool = True
    min_confidence: float = 0.7
    max_corrections_per_file: int = 50
    filter_web3_terms: bool = True
    filter_code_identifiers: bool = True


@dataclass
class PRConfig:
    """Pull request configuration"""
    auto_create: bool = False
    min_typos_for_pr: int = 1
    min_stars_for_pr: int = 50
    min_activity_score: int = 30
    validate_before_create: bool = True
    include_detailed_description: bool = True


@dataclass
class AppConfig:
    """Application configuration"""
    system: SystemConfig = field(default_factory=SystemConfig)
    github: GitHubConfig = field(default_factory=GitHubConfig)
    spell: SpellConfig = field(default_factory=SpellConfig)
    pr: PRConfig = field(default_factory=PRConfig)
    custom: Dict[str, Any] = field(default_factory=dict)


class ConfigManager:
    """
    Configuration manager for agents
    
    Provides:
    - Configuration loading from files
    - Configuration validation
    - Configuration updates
    - Environment variable support
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration manager
        
        Args:
            config_file: Configuration file path
        """
        self.config_file = config_file
        self.config: Optional[AppConfig] = None
        self._watchers: List[callable] = []
    
    def load(self, config_file: Optional[str] = None) -> AppConfig:
        """
        Load configuration from file
        
        Args:
            config_file: Configuration file path
            
        Returns:
            Loaded configuration
        """
        config_file = config_file or self.config_file
        
        if not config_file:
            logger.warning("No config file specified, using defaults")
            # Apply environment variable overrides even with defaults
            data = self._apply_env_overrides({})
            self.config = self._build_config(data)
            return self.config
        
        config_path = Path(config_file)
        
        if not config_path.exists():
            logger.warning(f"Config file not found: {config_file}, using defaults")
            # Apply environment variable overrides even with defaults
            data = self._apply_env_overrides({})
            self.config = self._build_config(data)
            return self.config
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                if config_path.suffix in ['.yaml', '.yml']:
                    data = yaml.safe_load(f)
                elif config_path.suffix == '.json':
                    data = json.load(f)
                else:
                    raise ValueError(f"Unsupported config file format: {config_path.suffix}")
            
            # Apply environment variable overrides
            data = self._apply_env_overrides(data)
            
            # Build configuration
            self.config = self._build_config(data)
            
            logger.info(f"Loaded configuration from {config_file}")
            return self.config
        
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            self.config = AppConfig()
            return self.config
    
    def save(self, config_file: Optional[str] = None) -> None:
        """
        Save configuration to file
        
        Args:
            config_file: Configuration file path
        """
        config_file = config_file or self.config_file
        
        if not config_file:
            raise ValueError("No config file specified")
        
        if not self.config:
            raise ValueError("No configuration to save")
        
        config_path = Path(config_file)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            data = asdict(self.config)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                if config_path.suffix in ['.yaml', '.yml']:
                    yaml.dump(data, f, default_flow_style=False)
                elif config_path.suffix == '.json':
                    json.dump(data, f, indent=2)
                else:
                    raise ValueError(f"Unsupported config file format: {config_path.suffix}")
            
            logger.info(f"Saved configuration to {config_file}")
        
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            raise
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value
        
        Args:
            key: Configuration key (dot-separated)
            default: Default value
            
        Returns:
            Configuration value
        """
        if not self.config:
            return default
        
        keys = key.split('.')
        value = asdict(self.config)
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value
        
        Args:
            key: Configuration key (dot-separated)
            value: Value to set
        """
        if not self.config:
            self.config = AppConfig()
        
        keys = key.split('.')
        config_dict = asdict(self.config)
        
        # Navigate to parent
        current = config_dict
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        # Set value
        current[keys[-1]] = value
        
        # Rebuild config from dict
        self.config = self._build_config(config_dict)
    
    def validate(self) -> bool:
        """
        Validate configuration
        
        Returns:
            True if valid
        """
        if not self.config:
            return False
        
        # Validate system config
        if self.config.system.max_concurrent_tasks < 1:
            logger.error("max_concurrent_tasks must be >= 1")
            return False
        
        if self.config.system.task_timeout < 0:
            logger.error("task_timeout must be >= 0")
            return False
        
        # Validate GitHub config
        if self.config.github.timeout < 0:
            logger.error("github.timeout must be >= 0")
            return False
        
        # Validate spell config
        if not 0 <= self.config.spell.min_confidence <= 1:
            logger.error("spell.min_confidence must be between 0 and 1")
            return False
        
        return True
    
    def watch(self, callback: callable) -> None:
        """
        Register a configuration change watcher
        
        Args:
            callback: Callback function
        """
        self._watchers.append(callback)
    
    def _apply_env_overrides(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply environment variable overrides
        
        Args:
            data: Configuration data
            
        Returns:
            Updated configuration data
        """
        # GitHub token
        if 'GITHUB_TOKEN' in os.environ:
            if 'github' not in data:
                data['github'] = {}
            data['github']['token'] = os.environ['GITHUB_TOKEN']
        
        # Log level
        if 'LOG_LEVEL' in os.environ:
            if 'system' not in data:
                data['system'] = {}
            data['system']['log_level'] = os.environ['LOG_LEVEL']
        
        return data
    
    def _build_config(self, data: Dict[str, Any]) -> AppConfig:
        """
        Build configuration from data
        
        Args:
            data: Configuration data
            
        Returns:
            Application configuration
        """
        # Build nested configs
        system_data = data.get('system', {})
        system_config = SystemConfig(**system_data)
        
        github_data = data.get('github', {})
        github_config = GitHubConfig(**github_data)
        
        spell_data = data.get('spell', {})
        spell_config = SpellConfig(**spell_data)
        
        pr_data = data.get('pr', {})
        pr_config = PRConfig(**pr_data)
        
        custom_data = data.get('custom', {})
        
        return AppConfig(
            system=system_config,
            github=github_config,
            spell=spell_config,
            pr=pr_config,
            custom=custom_data,
        )


def get_config(config_file: Optional[str] = None) -> ConfigManager:
    """
    Get configuration manager instance
    
    Args:
        config_file: Configuration file path
        
    Returns:
        Configuration manager
    """
    manager = ConfigManager(config_file)
    manager.load()
    return manager
