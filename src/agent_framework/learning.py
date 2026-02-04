"""
Agent Learning Mechanisms
"""

import time
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

from .logger import get_logger

logger = get_logger(__name__)


class LearningType(Enum):
    """Types of learning"""
    REINFORCEMENT = "reinforcement"
    SUPERVISED = "supervised"
    UNSUPERVISED = "unsupervised"
    TRANSFER = "transfer"
    ONLINE = "online"


@dataclass
class Experience:
    """Learning experience"""
    state: Dict[str, Any]
    action: str
    reward: float
    next_state: Dict[str, Any]
    done: bool
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Policy:
    """Agent policy"""
    state: Dict[str, Any]
    action: str
    value: float
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ExperienceReplay:
    """
    Experience replay buffer for learning
    
    Provides:
    - Experience storage
    - Sampling
    - Prioritized replay
    """
    
    def __init__(self, capacity: int = 10000):
        """
        Initialize experience replay
        
        Args:
            capacity: Buffer capacity
        """
        self.capacity = capacity
        self.experiences: List[Experience] = []
        self.priorities: List[float] = []
    
    def add_experience(
        self,
        experience: Experience,
        priority: float = 0.0
    ) -> None:
        """
        Add an experience
        
        Args:
            experience: Experience to add
            priority: Experience priority
        """
        self.experiences.append(experience)
        self.priorities.append(priority)
        
        # Keep within capacity
        if len(self.experiences) > self.capacity:
            # Remove lowest priority
            min_index = self.priorities.index(min(self.priorities))
            del self.experiences[min_index]
            del self.priorities[min_index]
    
    def sample(
        self,
        batch_size: int = 32,
        prioritize: bool = False
    ) -> List[Experience]:
        """
        Sample experiences
        
        Args:
            batch_size: Batch size
            prioritize: Use prioritized sampling
            
        Returns:
            Sampled experiences
        """
        if prioritize and self.priorities:
            # Prioritized sampling
            import random
            indices = [
                i for i, p in enumerate(self.priorities)
                if random.random() < p
            ]
            
            if len(indices) > batch_size:
                indices = indices[:batch_size]
            
            return [self.experiences[i] for i in indices]
        
        # Random sampling
        import random
        indices = random.sample(
            range(len(self.experiences)),
            min(batch_size, len(self.experiences))
        )
        
        return [self.experiences[i] for i in indices]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get replay buffer statistics"""
        return {
            "total_experiences": len(self.experiences),
            "capacity": self.capacity,
            "utilization": len(self.experiences) / self.capacity
        }


class LearningAgent:
    """
    Learning agent for agents
    
    Provides:
    - Experience collection
    - Policy learning
    - Reward optimization
    - Knowledge accumulation
    """
    
    def __init__(self):
        """Initialize learning agent"""
        self.experience_replay = ExperienceReplay()
        self.policies: Dict[str, Policy] = {}
        self.rewards: List[float] = []
        self.episodes: List[Dict[str, Any]] = []
        self.current_episode: Dict[str, Any] = {}
    
    def record_experience(
        self,
        state: Dict[str, Any],
        action: str,
        reward: float,
        next_state: Dict[str, Any],
        done: bool = False,
        priority: float = 0.0
    ) -> None:
        """
        Record an experience
        
        Args:
            state: Current state
            action: Action taken
            reward: Reward received
            next_state: Next state
            done: Whether episode ended
            priority: Experience priority
        """
        experience = Experience(
            state=state,
            action=action,
            reward=reward,
            next_state=next_state,
            done=done
        )
        
        self.experience_replay.add_experience(experience, priority)
        self.rewards.append(reward)
    
    def start_episode(self) -> None:
        """Start a new episode"""
        self.current_episode = {
            "start_time": time.time(),
            "experiences": 0,
            "total_reward": 0.0,
            "done": False
        }
    
    def end_episode(self) -> None:
        """End current episode"""
        if self.current_episode:
            self.current_episode["end_time"] = time.time()
            self.current_episode["done"] = True
            self.episodes.append(self.current_episode)
    
    def get_episode_stats(self) -> Dict[str, Any]:
        """Get episode statistics"""
        if not self.episodes:
            return {}
        
        total_episodes = len(self.episodes)
        total_reward = sum(ep.get("total_reward", 0) for ep in self.episodes)
        avg_reward = total_reward / total_episodes
        
        return {
            "total_episodes": total_episodes,
            "total_reward": total_reward,
            "avg_reward": avg_reward,
            "experience_count": sum(ep.get("experiences", 0) for ep in self.episodes)
        }
    
    def learn(
        self,
        learning_rate: float = 0.1,
        discount_factor: float = 0.99
    ) -> Dict[str, Any]:
        """
        Learn from experiences
        
        Args:
            learning_rate: Learning rate
            discount_factor: Discount factor
            
        Returns:
            Learning statistics
        """
        experiences = self.experience_replay.sample(batch_size=32)
        
        if not experiences:
            return {"error": "No experiences to learn from"}
        
        # Simple Q-learning update
        for exp in experiences:
            state_key = str(exp.state)
            action_key = exp.action
            
            # Get current policy value
            current_policy = self.policies.get(
                f"{state_key}_{action_key}",
                Policy(state=exp.state, action=action_key, value=0.0)
            )
            
            # Calculate target value
            target = exp.reward
            if not exp.done:
                next_state_key = str(exp.next_state)
                # Find best action for next state
                next_policies = [
                    p for k, p in self.policies.items()
                    if k.startswith(next_state_key)
                ]
                
                if next_policies:
                    best_next = max(next_policies, key=lambda p: p.value)
                    target += discount_factor * best_next.value
            
            # Update policy value
            new_value = (
                (1 - learning_rate) * current_policy.value +
                learning_rate * target
            )
            
            self.policies[f"{state_key}_{action_key}"] = Policy(
                state=exp.state,
                action=action_key,
                value=new_value
            )
        
        return {
            "policy_count": len(self.policies),
            "experience_count": len(self.experience_replay.experiences),
            "learning_rate": learning_rate,
            "discount_factor": discount_factor
        }
    
    def get_policy(self, state: Dict[str, Any]) -> Optional[Policy]:
        """
        Get policy for state
        
        Args:
            state: State to query
            
        Returns:
            Policy or None
        """
        state_key = str(state)
        
        policies = [
            p for k, p in self.policies.items()
            if k.startswith(state_key)
        ]
        
        if not policies:
            return None
        
        # Return policy with highest value
        return max(policies, key=lambda p: p.value)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get learning statistics"""
        return {
            "experience_replay": self.experience_replay.get_stats(),
            "policy_count": len(self.policies),
            "episode_stats": self.get_episode_stats(),
            "total_rewards": sum(self.rewards),
            "avg_reward": sum(self.rewards) / len(self.rewards) if self.rewards else 0
        }


class KnowledgeAccumulator:
    """
    Knowledge accumulator for agents
    
    Provides:
    - Knowledge collection
    - Knowledge organization
    - Knowledge retrieval
    - Knowledge sharing
    """
    
    def __init__(self):
        """Initialize knowledge accumulator"""
        self.knowledge: Dict[str, List[Dict[str, Any]]] = {}
        self.usage_count: Dict[str, int] = defaultdict(int)
    
    def add_knowledge(
        self,
        category: str,
        knowledge: Dict[str, Any],
        confidence: float = 1.0
    ) -> None:
        """
        Add knowledge
        
        Args:
            category: Knowledge category
            knowledge: Knowledge data
            confidence: Confidence score
        """
        knowledge["confidence"] = confidence
        
        if category not in self.knowledge:
            self.knowledge[category] = []
        
        self.knowledge[category].append(knowledge)
        logger.info(f"Added knowledge to {category}")
    
    def retrieve_knowledge(
        self,
        category: str,
        query: Dict[str, Any] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve knowledge
        
        Args:
            category: Knowledge category
            query: Query filters
            limit: Maximum results
            
        Returns:
            Retrieved knowledge
        """
        if category not in self.knowledge:
            return []
        
        knowledge = self.knowledge[category]
        
        # Update usage count
        self.usage_count[category] += 1
        
        if not query:
            return knowledge[:limit]
        
        # Filter by query
        results = []
        for k in knowledge:
            match = True
            for key, value in query.items():
                if key not in k or k[key] != value:
                    match = False
                    break
            
            if match:
                results.append(k)
        
        # Sort by confidence
        results.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        
        return results[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge statistics"""
        category_counts = {
            cat: len(items)
            for cat, items in self.knowledge.items()
        }
        
        return {
            "total_categories": len(self.knowledge),
            "total_knowledge": sum(len(items) for items in self.knowledge.values()),
            "category_counts": category_counts,
            "usage_counts": dict(self.usage_count)
        }


class PerformanceTracker:
    """
    Performance tracker for agents
    
    Provides:
    - Performance metrics
    - Trend analysis
    - Benchmarking
    """
    
    def __init__(self):
        """Initialize performance tracker"""
        self.metrics: Dict[str, List[float]] = defaultdict(list)
        self.benchmarks: Dict[str, float] = {}
    
    def record_metric(
        self,
        metric_name: str,
        value: float,
        timestamp: Optional[float] = None
    ) -> None:
        """
        Record a metric
        
        Args:
            metric_name: Metric name
            value: Metric value
            timestamp: Timestamp
        """
        timestamp = timestamp or time.time()
        
        self.metrics[metric_name].append((timestamp, value))
        
        # Keep only recent metrics
        if len(self.metrics[metric_name]) > 10000:
            self.metrics[metric_name] = self.metrics[metric_name][-10000:]
    
    def get_metric_stats(
        self,
        metric_name: str,
        window: int = 100
    ) -> Dict[str, float]:
        """
        Get metric statistics
        
        Args:
            metric_name: Metric name
            window: Time window
            
        Returns:
            Statistics
        """
        values = self.metrics.get(metric_name, [])
        
        if not values:
            return {}
        
        recent_values = values[-window:]
        
        if not recent_values:
            return {}
        
        values_sorted = sorted(recent_values)
        
        return {
            "count": len(recent_values),
            "min": values_sorted[0],
            "max": values_sorted[-1],
            "avg": sum(recent_values) / len(recent_values),
            "p50": values_sorted[int(len(values_sorted) * 0.5)],
            "p95": values_sorted[int(len(values_sorted) * 0.95)],
            "p99": values_sorted[int(len(values_sorted) * 0.99)]
        }
    
    def set_benchmark(
        self,
        metric_name: str,
        value: float
    ) -> None:
        """
        Set benchmark
        
        Args:
            metric_name: Metric name
            value: Benchmark value
        """
        self.benchmarks[metric_name] = value
        logger.info(f"Set benchmark for {metric_name}: {value}")
    
    def check_benchmark(
        self,
        metric_name: str
    ) -> bool:
        """
        Check if metric meets benchmark
        
        Args:
            metric_name: Metric name
            
        Returns:
            True if benchmark met
        """
        if metric_name not in self.benchmarks:
            return True
        
        stats = self.get_metric_stats(metric_name)
        avg = stats.get("avg", 0)
        
        return avg >= self.benchmarks[metric_name]
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get performance report"""
        report = {}
        
        for metric_name in self.metrics:
            stats = self.get_metric_stats(metric_name)
            benchmark_met = self.check_benchmark(metric_name)
            
            report[metric_name] = {
                "stats": stats,
                "benchmark": self.benchmarks.get(metric_name),
                "benchmark_met": benchmark_met
            }
        
        return report


def get_learning_agent() -> LearningAgent:
    """Get global learning agent instance"""
    if not hasattr(get_learning_agent, "_instance"):
        get_learning_agent._instance = LearningAgent()
    return get_learning_agent._instance


def get_knowledge_accumulator() -> KnowledgeAccumulator:
    """Get global knowledge accumulator instance"""
    if not hasattr(get_knowledge_accumulator, "_instance"):
        get_knowledge_accumulator._instance = KnowledgeAccumulator()
    return get_knowledge_accumulator._instance


def get_performance_tracker() -> PerformanceTracker:
    """Get global performance tracker instance"""
    if not hasattr(get_performance_tracker, "_instance"):
        get_performance_tracker._instance = PerformanceTracker()
    return get_performance_tracker._instance
