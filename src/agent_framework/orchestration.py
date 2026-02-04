"""
Agent Orchestration and Workflow Engine
"""

import asyncio
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque

from .logger import get_logger

logger = get_logger(__name__)


class WorkflowStatus(Enum):
    """Workflow status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStatus(Enum):
    """Task status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Task:
    """Workflow task"""
    id: str
    name: str
    agent: str
    data: Dict[str, Any] = field(default_factory=dict)
    dependencies: Set[str] = field(default_factory=set)
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class Workflow:
    """Workflow definition"""
    id: str
    name: str
    tasks: List[Task] = field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=lambda: __import__('time').time())
    started_at: Optional[float] = None
    completed_at: Optional[float] = None


class WorkflowEngine:
    """
    Workflow engine for agent orchestration
    
    Provides:
    - Workflow execution
    - Task scheduling
    - Dependency management
    - Error handling
    """
    
    def __init__(self):
        """Initialize workflow engine"""
        self.workflows: Dict[str, Workflow] = {}
        self.task_queue: deque = deque()
        self.running_tasks: Set[str] = set()
        self._lock = asyncio.Lock()
        self._workers: List[asyncio.Task] = []
        self._stop_event = asyncio.Event()
    
    async def create_workflow(
        self,
        name: str,
        tasks: List[Dict[str, Any]],
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        Create a workflow
        
        Args:
            name: Workflow name
            tasks: Task definitions
            metadata: Workflow metadata
            
        Returns:
            Workflow ID
        """
        import uuid
        
        workflow_id = str(uuid.uuid4())
        
        workflow_tasks = []
        for task_def in tasks:
            task = Task(
                id=task_def.get("id", str(uuid.uuid4())),
                name=task_def.get("name", "task"),
                agent=task_def.get("agent", "default"),
                data=task_def.get("data", {}),
                dependencies=set(task_def.get("dependencies", [])),
                max_retries=task_def.get("max_retries", 3)
            )
            workflow_tasks.append(task)
        
        workflow = Workflow(
            id=workflow_id,
            name=name,
            tasks=workflow_tasks,
            metadata=metadata or {}
        )
        
        self.workflows[workflow_id] = workflow
        
        logger.info(f"Created workflow: {workflow_id}")
        return workflow_id
    
    async def execute_workflow(
        self,
        workflow_id: str,
        max_workers: int = 4
    ) -> Dict[str, Any]:
        """
        Execute a workflow
        
        Args:
            workflow_id: Workflow ID
            max_workers: Maximum concurrent workers
            
        Returns:
            Execution result
        """
        workflow = self.workflows.get(workflow_id)
        
        if not workflow:
            return {"error": "Workflow not found"}
        
        if workflow.status != WorkflowStatus.PENDING:
            return {"error": "Workflow already executed"}
        
        workflow.status = WorkflowStatus.RUNNING
        workflow.started_at = __import__('time').time()
        
        try:
            # Build task graph
            task_graph = self._build_task_graph(workflow.tasks)
            
            # Execute tasks
            await self._execute_tasks(workflow, task_graph, max_workers)
            
            # Check workflow status
            if all(t.status in [TaskStatus.COMPLETED, TaskStatus.SKIPPED] for t in workflow.tasks):
                workflow.status = WorkflowStatus.COMPLETED
            else:
                workflow.status = WorkflowStatus.FAILED
            
            workflow.completed_at = __import__('time').time()
            
            return {
                "success": workflow.status == WorkflowStatus.COMPLETED,
                "status": workflow.status.value,
                "tasks": [
                    {
                        "id": t.id,
                        "name": t.name,
                        "status": t.status.value,
                        "result": t.result,
                        "error": t.error
                    }
                    for t in workflow.tasks
                ]
            }
        
        except Exception as e:
            workflow.status = WorkflowStatus.FAILED
            logger.error(f"Workflow execution failed: {e}")
            return {"error": str(e)}
    
    def _build_task_graph(self, tasks: List[Task]) -> Dict[str, List[str]]:
        """Build task dependency graph"""
        graph = {}
        
        for task in tasks:
            graph[task.id] = list(task.dependencies)
        
        return graph
    
    async def _execute_tasks(
        self,
        workflow: Workflow,
        task_graph: Dict[str, List[str]],
        max_workers: int
    ) -> None:
        """Execute workflow tasks"""
        completed_tasks = set()
        failed_tasks = set()
        
        while len(completed_tasks) + len(failed_tasks) < len(workflow.tasks):
            # Find ready tasks
            ready_tasks = []
            
            for task in workflow.tasks:
                if task.status != TaskStatus.PENDING:
                    continue
                
                # Check dependencies
                deps_met = all(
                    dep_id in completed_tasks
                    for dep_id in task.dependencies
                )
                
                if deps_met:
                    ready_tasks.append(task)
            
            if not ready_tasks:
                # Check if we're stuck
                if not self._running_tasks:
                    # No tasks running and no ready tasks - deadlock
                    logger.error("Workflow deadlock detected")
                    break
                
                # Wait for running tasks to complete
                await asyncio.sleep(0.1)
                continue
            
            # Execute ready tasks
            tasks_to_execute = ready_tasks[:max_workers]
            
            for task in tasks_to_execute:
                task.status = TaskStatus.RUNNING
                self._running_tasks.add(task.id)
            
            # Execute tasks concurrently
            await asyncio.gather(
                *[self._execute_task(task) for task in tasks_to_execute],
                return_exceptions=True
            )
            
            # Update completed and failed tasks
            for task in workflow.tasks:
                if task.status == TaskStatus.COMPLETED:
                    completed_tasks.add(task.id)
                elif task.status == TaskStatus.FAILED:
                    failed_tasks.add(task.id)
                
                self._running_tasks.discard(task.id)
    
    async def _execute_task(self, task: Task) -> None:
        """Execute a single task"""
        try:
            # In a real system, this would call the agent
            # For now, simulate execution
            await asyncio.sleep(0.1)
            
            # Simulate task result
            task.result = {"success": True, "data": f"Result for {task.name}"}
            task.status = TaskStatus.COMPLETED
            
            logger.info(f"Completed task: {task.name}")
        
        except Exception as e:
            task.error = str(e)
            
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.PENDING
                logger.warning(f"Retrying task {task.name} (attempt {task.retry_count})")
            else:
                task.status = TaskStatus.FAILED
                logger.error(f"Task failed: {task.name} - {e}")
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get workflow by ID"""
        return self.workflows.get(workflow_id)
    
    def list_workflows(self, status: Optional[WorkflowStatus] = None) -> List[Workflow]:
        """List workflows"""
        workflows = list(self.workflows.values())
        
        if status:
            workflows = [w for w in workflows if w.status == status]
        
        return workflows
    
    def cancel_workflow(self, workflow_id: str) -> bool:
        """
        Cancel a workflow
        
        Args:
            workflow_id: Workflow ID
            
        Returns:
            True if cancelled
        """
        workflow = self.workflows.get(workflow_id)
        
        if not workflow:
            return False
        
        if workflow.status not in [WorkflowStatus.PENDING, WorkflowStatus.RUNNING]:
            return False
        
        workflow.status = WorkflowStatus.CANCELLED
        
        # Cancel running tasks
        for task in workflow.tasks:
            if task.status == TaskStatus.RUNNING:
                task.status = TaskStatus.SKIPPED
        
        logger.info(f"Cancelled workflow: {workflow_id}")
        return True


class TaskScheduler:
    """
    Task scheduler for agent operations
    
    Provides:
    - Task queuing
    - Priority management
    - Rate limiting
    - Load balancing
    """
    
    def __init__(self, max_concurrent: int = 10):
        """
        Initialize task scheduler
        
        Args:
            max_concurrent: Maximum concurrent tasks
        """
        self.max_concurrent = max_concurrent
        self.pending_tasks: deque = deque()
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def submit_task(
        self,
        task_id: str,
        task_func: Callable,
        priority: int = 0
    ) -> None:
        """
        Submit a task
        
        Args:
            task_id: Task ID
            task_func: Task function
            priority: Task priority
        """
        # Add to queue with priority
        self.pending_tasks.append((priority, task_id, task_func))
        
        # Sort by priority
        self.pending_tasks = deque(
            sorted(self.pending_tasks, key=lambda x: x[0], reverse=True)
        )
    
    async def process_tasks(self) -> None:
        """Process pending tasks"""
        while self.pending_tasks or self.running_tasks:
            # Start new tasks if capacity available
            while self.pending_tasks and len(self.running_tasks) < self.max_concurrent:
                priority, task_id, task_func = self.pending_tasks.popleft()
                
                async def run_task():
                    async with self.semaphore:
                        try:
                            await task_func()
                        finally:
                            self.running_tasks.pop(task_id, None)
                
                self.running_tasks[task_id] = asyncio.create_task(run_task())
            
            # Wait for a task to complete
            if self.running_tasks:
                done, pending = await asyncio.wait(
                    self.running_tasks.values(),
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # Clean up completed tasks
                for task in done:
                    for tid, t in list(self.running_tasks.items()):
                        if t == task:
                            del self.running_tasks[tid]
                            break
            
            await asyncio.sleep(0.01)
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status"""
        return {
            "pending": len(self.pending_tasks),
            "running": len(self.running_tasks),
            "max_concurrent": self.max_concurrent
        }


def get_workflow_engine() -> WorkflowEngine:
    """Get global workflow engine instance"""
    if not hasattr(get_workflow_engine, "_instance"):
        get_workflow_engine._instance = WorkflowEngine()
    return get_workflow_engine._instance


def get_task_scheduler(max_concurrent: int = 10) -> TaskScheduler:
    """Get global task scheduler instance"""
    if not hasattr(get_task_scheduler, "_instance"):
        get_task_scheduler._instance = TaskScheduler(max_concurrent)
    return get_task_scheduler._instance
