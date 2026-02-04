"""
Agent Deployment Support
"""

import os
import yaml
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from .logger import get_logger

logger = get_logger(__name__)


class DeploymentType(Enum):
    """Deployment types"""
    LOCAL = "local"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    SERVERLESS = "serverless"


class Environment(Enum):
    """Deployment environments"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class DeploymentConfig:
    """Deployment configuration"""
    type: DeploymentType
    environment: Environment
    replicas: int = 1
    resources: Dict[str, str] = field(default_factory=dict)
    env_vars: Dict[str, str] = field(default_factory=dict)
    ports: List[int] = field(default_factory=list)
    volumes: List[Dict[str, str]] = field(default_factory=list)
    health_check: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class DeploymentManager:
    """
    Manager for agent deployment
    
    Provides:
    - Configuration management
    - Deployment validation
    - Environment setup
    - Health checking
    """
    
    def __init__(self):
        """Initialize deployment manager"""
        self.configs: Dict[str, DeploymentConfig] = {}
        self.active_deployments: Dict[str, str] = {}
    
    def load_config(self, config_file: str) -> Optional[DeploymentConfig]:
        """
        Load deployment configuration
        
        Args:
            config_file: Configuration file path
            
        Returns:
            Deployment config or None
        """
        try:
            path = Path(config_file)
            
            if not path.exists():
                logger.error(f"Config file not found: {config_file}")
                return None
            
            with open(path, 'r', encoding='utf-8') as f:
                if path.suffix in ['.yaml', '.yml']:
                    data = yaml.safe_load(f)
                elif path.suffix == '.json':
                    data = json.load(f)
                else:
                    logger.error(f"Unsupported config format: {path.suffix}")
                    return None
            
            config = DeploymentConfig(
                type=DeploymentType(data.get('type', 'local')),
                environment=Environment(data.get('environment', 'development')),
                replicas=data.get('replicas', 1),
                resources=data.get('resources', {}),
                env_vars=data.get('env_vars', {}),
                ports=data.get('ports', []),
                volumes=data.get('volumes', []),
                health_check=data.get('health_check', {}),
                metadata=data.get('metadata', {})
            )
            
            self.configs[path.stem] = config
            logger.info(f"Loaded config: {path.stem}")
            
            return config
        
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return None
    
    def validate_config(self, config: DeploymentConfig) -> bool:
        """
        Validate deployment configuration
        
        Args:
            config: Configuration to validate
            
        Returns:
            True if valid
        """
        # Check replicas
        if config.replicas < 1:
            logger.error("Replicas must be >= 1")
            return False
        
        # Check ports
        for port in config.ports:
            if not 1 <= port <= 65535:
                logger.error(f"Invalid port: {port}")
                return False
        
        return True
    
    def deploy(
        self,
        name: str,
        config: DeploymentConfig
    ) -> bool:
        """
        Deploy agent
        
        Args:
            name: Deployment name
            config: Deployment configuration
            
        Returns:
            True if deployed
        """
        if not self.validate_config(config):
            return False
        
        # In a real system, this would deploy to the target platform
        logger.info(f"Deploying {name} with {config.type.value} to {config.environment.value}")
        
        # Simulate deployment
        self.active_deployments[name] = config.type.value
        
        return True
    
    def undeploy(self, name: str) -> bool:
        """
        Undeploy agent
        
        Args:
            name: Deployment name
            
        Returns:
            True if undeployed
        """
        if name not in self.active_deployments:
            logger.warning(f"Deployment not found: {name}")
            return False
        
        logger.info(f"Undeploying {name}")
        del self.active_deployments[name]
        
        return True
    
    def get_status(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get deployment status
        
        Args:
            name: Deployment name
            
        Returns:
            Status information
        """
        if name not in self.active_deployments:
            return None
        
        return {
            "name": name,
            "type": self.active_deployments[name],
            "status": "running"
        }
    
    def list_deployments(self) -> List[str]:
        """List all deployments"""
        return list(self.active_deployments.keys())


class ConfigGenerator:
    """
    Generator for deployment configurations
    
    Provides:
    - Docker Compose generation
    - Kubernetes manifests
    - Environment configs
    """
    
    def generate_docker_compose(
        self,
        service_name: str,
        config: DeploymentConfig
    ) -> str:
        """
        Generate Docker Compose configuration
        
        Args:
            service_name: Service name
            config: Deployment configuration
            
        Returns:
            Docker Compose YAML
        """
        compose = {
            "version": "3.8",
            "services": {
                service_name: {
                    "image": f"typoagent:{service_name}",
                    "replicas": config.replicas,
                    "ports": [f"{p}:{p}" for p in config.ports],
                    "environment": config.env_vars,
                    "volumes": [f"{v['source']}:{v['target']}" for v in config.volumes]
                }
            }
        }
        
        if config.health_check:
            compose["services"][service_name]["healthcheck"] = config.health_check
        
        return yaml.dump(compose, default_flow_style=False)
    
    def generate_kubernetes_manifest(
        self,
        service_name: str,
        config: DeploymentConfig
    ) -> str:
        """
        Generate Kubernetes manifest
        
        Args:
            service_name: Service name
            config: Deployment configuration
            
        Returns:
            Kubernetes YAML
        """
        manifest = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": service_name
            },
            "spec": {
                "replicas": config.replicas,
                "selector": {
                    "matchLabels": {
                        "app": service_name
                    }
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "app": service_name
                        }
                    },
                    "spec": {
                        "containers": [{
                            "name": service_name,
                            "image": f"typoagent:{service_name}",
                            "ports": [{"containerPort": p} for p in config.ports],
                            "env": [
                                {"name": k, "value": v}
                                for k, v in config.env_vars.items()
                            ],
                            "resources": config.resources
                        }]
                    }
                }
            }
        }
        
        if config.health_check:
            manifest["spec"]["template"]["spec"]["containers"][0]["livenessProbe"] = config.health_check
        
        return yaml.dump(manifest, default_flow_style=False)
    
    def generate_env_file(
        self,
        config: DeploymentConfig
    ) -> str:
        """
        Generate environment file
        
        Args:
            config: Deployment configuration
            
        Returns:
            Environment file content
        """
        lines = [f"{k}={v}" for k, v in config.env_vars.items()]
        return "\n".join(lines)


def get_deployment_manager() -> DeploymentManager:
    """Get global deployment manager instance"""
    if not hasattr(get_deployment_manager, "_instance"):
        get_deployment_manager._instance = DeploymentManager()
    return get_deployment_manager._instance


def get_config_generator() -> ConfigGenerator:
    """Get global config generator instance"""
    if not hasattr(get_config_generator, "_instance"):
        get_config_generator._instance = ConfigGenerator()
    return get_config_generator._instance
