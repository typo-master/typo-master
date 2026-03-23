"""
SOTA Agent Framework for Web3 Typo Hunter

A state-of-the-art multi-agent framework designed for intelligent typo hunting
in Web3 projects with advanced capabilities including:
- Multi-agent orchestration
- Tool system with automatic discovery
- Memory and context management
- State persistence and recovery
- Distributed communication
- Comprehensive monitoring and observability
"""

from .base_agent import BaseAgent, AgentConfig, AgentState
from .message import Message, MessageType, MessageHandler
from .tool_system import ToolRegistry, tool
from .context import Context, ContextManager
from .state import StateManager, StateStore
from .logger import get_logger, setup_logging
from .error_handler import ErrorHandler, retry_on_error, with_error_handling, CircuitBreaker
from .config import ConfigManager, get_config
from .metrics import MetricsCollector, PerformanceMonitor, get_metrics_collector
from .health import HealthMonitor, Heartbeat, get_health_monitor, get_heartbeat
from .resources import ResourceManager, get_resource_manager
from .security import AuthManager, SecurityContext, get_auth_manager, get_security_context
from .vector_db import MemoryStore, EmbeddingModel, get_memory_store, get_embedding_model
from .collaboration import CollaborationManager, ConsensusManager, get_collaboration_manager, get_consensus_manager
from .knowledge_base import KnowledgeBase, KnowledgeManager, get_knowledge_base, get_knowledge_manager
from .audit import AuditLogger, Tracer, get_audit_logger, get_tracer
from .plugin import PluginManager, get_plugin_manager
from .orchestration import WorkflowEngine, TaskScheduler, get_workflow_engine, get_task_scheduler
from .distributed import ClusterManager, ServiceDiscovery, get_cluster_manager, get_service_discovery
from .fault_tolerance import FaultToleranceManager, get_fault_tolerance_manager
from .analytics import AnalyticsEngine, get_analytics_engine
from .deployment import DeploymentManager, ConfigGenerator, get_deployment_manager, get_config_generator
from .async_utils import AsyncQueue, AsyncLockManager, get_async_queue, get_async_lock_manager
from .testing import TestRunner, MockAgent, MockTool, TestHelper, get_test_runner, get_test_helper
from .learning import LearningAgent, KnowledgeAccumulator, PerformanceTracker, get_learning_agent, get_knowledge_accumulator, get_performance_tracker
from .versioning import VersionManager, Version, get_version_manager
from .optimization import Optimizer, Cache, get_optimizer
from .memory import (
    MemoryEntry,
    MemoryQuery,
    MemoryConfig,
    UnifiedMemoryManager,
    get_memory_manager,
    BaseMemoryBackend,
    FileBackend,
    ChromaBackend,
    Mem0Backend,
)
from .skill_system import (
    SkillCategory,
    SkillLevel,
    SkillMetadata,
    SkillResult,
    SkillContext,
    BaseSkill,
    SkillRegistry,
    skill,
)
from .skill_langgraph import (
    SkillState,
    SkillNodeConfig,
    SkillNodeWrapper,
    SkillGraphBuilder,
    SkillOrchestrator,
)
from .skill_agent import (
    SkillAgentConfig,
    SkillEnabledAgent,
)
from .sku_system import (
    SKUMetadata,
    SKUState,
    LoadedSKU,
    SKULoader,
    SKUManager,
    SKUExtensionMixin,
)

__version__ = "0.2.0"
__all__ = [
    # Core
    "BaseAgent",
    "AgentConfig",
    "AgentState",
    # Communication
    "Message",
    "MessageType",
    "MessageHandler",
    # Tools
    "ToolRegistry",
    "tool",
    # Context & State
    "Context",
    "ContextManager",
    "StateManager",
    "StateStore",
    # Logging
    "get_logger",
    "setup_logging",
    # Error Handling
    "ErrorHandler",
    "retry_on_error",
    "with_error_handling",
    "CircuitBreaker",
    # Configuration
    "ConfigManager",
    "get_config",
    # Metrics
    "MetricsCollector",
    "PerformanceMonitor",
    "get_metrics_collector",
    # Health
    "HealthMonitor",
    "Heartbeat",
    "get_health_monitor",
    "get_heartbeat",
    # Resources
    "ResourceManager",
    "get_resource_manager",
    # Security
    "AuthManager",
    "SecurityContext",
    "get_auth_manager",
    "get_security_context",
    # Vector DB
    "MemoryStore",
    "EmbeddingModel",
    "get_memory_store",
    "get_embedding_model",
    # Collaboration
    "CollaborationManager",
    "ConsensusManager",
    "get_collaboration_manager",
    "get_consensus_manager",
    # Knowledge Base
    "KnowledgeBase",
    "KnowledgeManager",
    "get_knowledge_base",
    "get_knowledge_manager",
    # Audit
    "AuditLogger",
    "Tracer",
    "get_audit_logger",
    "get_tracer",
    # Plugin
    "PluginManager",
    "get_plugin_manager",
    # Orchestration
    "WorkflowEngine",
    "TaskScheduler",
    "get_workflow_engine",
    "get_task_scheduler",
    # Distributed
    "ClusterManager",
    "ServiceDiscovery",
    "get_cluster_manager",
    "get_service_discovery",
    # Async Utils
    "AsyncQueue",
    "AsyncLockManager",
    "get_async_queue",
    "get_async_lock_manager",
    # Testing
    "TestRunner",
    "MockAgent",
    "MockTool",
    "TestHelper",
    "get_test_runner",
    "get_test_helper",
    # Learning
    "LearningAgent",
    "KnowledgeAccumulator",
    "PerformanceTracker",
    "get_learning_agent",
    "get_knowledge_accumulator",
    "get_performance_tracker",
    # Versioning
    "VersionManager",
    "Version",
    "get_version_manager",
    # Optimization
    "Optimizer",
    "Cache",
    "get_optimizer",
    # Unified Memory (New)
    "MemoryEntry",
    "MemoryQuery",
    "MemoryConfig",
    "UnifiedMemoryManager",
    "get_memory_manager",
    "BaseMemoryBackend",
    "FileBackend",
    "ChromaBackend",
    "Mem0Backend",
    # Skills (New)
    "SkillCategory",
    "SkillLevel",
    "SkillMetadata",
    "SkillResult",
    "SkillContext",
    "BaseSkill",
    "SkillRegistry",
    "skill",
    # Skill-LangGraph Integration (New)
    "SkillState",
    "SkillNodeConfig",
    "SkillNodeWrapper",
    "SkillGraphBuilder",
    "SkillOrchestrator",
    # Skill-Enabled Agent (New)
    "SkillAgentConfig",
    "SkillEnabledAgent",
    # SKU Extension System (New)
    "SKUMetadata",
    "SKUState",
    "LoadedSKU",
    "SKULoader",
    "SKUManager",
    "SKUExtensionMixin",
]
