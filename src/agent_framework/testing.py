"""
Testing Framework for Agents
"""

import asyncio
from typing import Dict, Any, List, Optional, Callable, Type
from dataclasses import dataclass, field
from enum import Enum
from unittest.mock import Mock, AsyncMock

from .logger import get_logger

logger = get_logger(__name__)


class TestStatus(Enum):
    """Test status"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TestCase:
    """Test case definition"""
    name: str
    test_func: Callable
    description: str = ""
    timeout: float = 30.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestResult:
    """Test result"""
    test_case: TestCase
    status: TestStatus
    duration: float = 0.0
    error: Optional[str] = None
    output: str = ""


class TestRunner:
    """
    Test runner for agent testing
    
    Provides:
    - Test execution
    - Result collection
    - Reporting
    """
    
    def __init__(self):
        """Initialize test runner"""
        self.test_cases: List[TestCase] = []
        self.results: List[TestResult] = []
        self.setup_func: Optional[Callable] = None
        self.teardown_func: Optional[Callable] = None
    
    def add_test(
        self,
        name: str,
        test_func: Callable,
        description: str = "",
        timeout: float = 30.0,
        metadata: Dict[str, Any] = None
    ) -> None:
        """
        Add a test case
        
        Args:
            name: Test name
            test_func: Test function
            description: Test description
            timeout: Test timeout
            metadata: Test metadata
        """
        test_case = TestCase(
            name=name,
            test_func=test_func,
            description=description,
            timeout=timeout,
            metadata=metadata or {}
        )
        self.test_cases.append(test_case)
    
    def setup(self, func: Callable) -> None:
        """
        Set up function
        
        Args:
            func: Setup function
        """
        self.setup_func = func
    
    def teardown(self, func: Callable) -> None:
        """
        Set teardown function
        
        Args:
            func: Teardown function
        """
        self.teardown_func = func
    
    async def run_tests(self) -> List[TestResult]:
        """
        Run all tests
        
        Returns:
            Test results
        """
        self.results = []
        
        # Run setup
        if self.setup_func:
            try:
                await self.setup_func()
            except Exception as e:
                logger.error(f"Setup failed: {e}")
                return self.results
        
        # Run tests
        for test_case in self.test_cases:
            result = await self._run_test(test_case)
            self.results.append(result)
        
        # Run teardown
        if self.teardown_func:
            try:
                await self.teardown_func()
            except Exception as e:
                logger.error(f"Teardown failed: {e}")
        
        return self.results
    
    async def _run_test(self, test_case: TestCase) -> TestResult:
        """
        Run a single test
        
        Args:
            test_case: Test case
            
        Returns:
            Test result
        """
        import time
        
        test_case.status = TestStatus.RUNNING
        start_time = time.time()
        
        try:
            result = await asyncio.wait_for(
                test_case.test_func(),
                timeout=test_case.timeout
            )
            
            duration = time.time() - start_time
            
            return TestResult(
                test_case=test_case,
                status=TestStatus.PASSED,
                duration=duration,
                output=str(result)
            )
        
        except asyncio.TimeoutError as e:
            duration = time.time() - start_time
            return TestResult(
                test_case=test_case,
                status=TestStatus.FAILED,
                duration=duration,
                error=f"Timeout after {test_case.timeout}s",
                output=str(e)
            )
        
        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                test_case=test_case,
                status=TestStatus.FAILED,
                duration=duration,
                error=str(e),
                output=""
            )
    
    def get_results(self) -> List[TestResult]:
        """Get test results"""
        return self.results
    
    def get_summary(self) -> Dict[str, Any]:
        """Get test summary"""
        passed = sum(1 for r in self.results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in self.results if r.status == TestStatus.FAILED)
        skipped = sum(1 for r in self.results if r.status == TestStatus.SKIPPED)
        total = len(self.results)
        
        durations = [r.duration for r in self.results]
        total_duration = sum(durations)
        
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "success_rate": passed / total if total > 0 else 0,
            "total_duration": total_duration,
            "avg_duration": total_duration / total if total > 0 else 0
        }


class MockAgent:
    """
    Mock agent for testing
    
    Provides:
    - Agent simulation
    - Tool mocking
    - State tracking
    """
    
    def __init__(self, name: str = "mock_agent"):
        """Initialize mock agent"""
        self.name = name
        self.state = "idle"
        self.tools: Dict[str, Callable] = {}
        self.messages: List[Dict[str, Any]] = []
        self.metrics: Dict[str, Any] = {}
    
    def register_tool(self, name: str, func: Callable) -> None:
        """
        Register a tool
        
        Args:
            name: Tool name
            func: Tool function
        """
        self.tools[name] = func
    
    async def invoke_tool(self, name: str, *args, **kwargs) -> Any:
        """
        Invoke a tool
        
        Args:
            name: Tool name
            *args: Tool arguments
            **kwargs: Tool keyword arguments
            
        Returns:
            Tool result
        """
        if name not in self.tools:
            raise ValueError(f"Tool not found: {name}")
        
        return await self.tools[name](*args, **kwargs)
    
    def send_message(self, message: Dict[str, Any]) -> None:
        """
        Send a message
        
        Args:
            message: Message to send
        """
        self.messages.append(message)
    
    def get_state(self) -> str:
        """Get current state"""
        return self.state
    
    def set_state(self, state: str) -> None:
        """
        Set state
        
        Agent:
            state: New state
        """
        self.state = state
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get metrics"""
        return self.metrics


class MockTool:
    """
    Mock tool for testing
    
    Provides:
    - Tool simulation
    - Result mocking
    - Call tracking
    """
    
    def __init__(self, name: str, result: Any = None):
        """
        Initialize mock tool
        
        Args:
            name: Tool name
            result: Default result
        """
        self.name = name
        self.default_result = result
        self.calls: List[Dict[str, Any]] = []
    
    async def __call__(self, *args, **kwargs) -> Any:
        """Call the tool"""
        self.calls.append({
            "args": args,
            "kwargs": kwargs,
            "timestamp": __import__('time').time()
        })
        
        if callable(self.default_result):
            return self.default_result(*args, **kwargs)
        
        return self.default_result
    
    def get_call_count(self) -> int:
        """Get call count"""
        return len(self.calls)
    
    def get_last_call(self) -> Optional[Dict[str, Any]]:
        """Get last call"""
        return self.calls[-1] if self.calls else None


class TestHelper:
    """
    Helper for testing
    
    Provides:
    - Test utilities
    - Assertion helpers
    - Mock creation
    """
    
    @staticmethod
    def create_mock_agent(name: str = "mock_agent") -> MockAgent:
        """Create a mock agent"""
        return MockAgent(name)
    
    @staticmethod
    def create_mock_tool(name: str, result: Any = None) -> MockTool:
        """Create a mock tool"""
        return MockTool(name, result)
    
    @staticmethod
    async def wait_for_condition(
        condition: Callable,
        timeout: float = 10.0,
        interval: float = 0.1
    ) -> bool:
        """
        Wait for a condition
        
        Args:
            condition: Condition function
            timeout: Maximum wait time
            interval: Check interval
            
        Returns:
            True if condition met
        """
        start_time = __import__('time').time()
        
        while time.time() - start_time < timeout:
            if await condition():
                return True
            await asyncio.sleep(interval)
        
        return False
    
    @staticmethod
    def assert_equal(actual: Any, expected: Any, message: str = "") -> None:
        """Assert equality"""
        if actual != expected:
            raise AssertionError(
                f"{message}: Expected {expected}, got {actual}"
            )
    
    @staticmethod
    def assert_true(value: bool, message: str = "") -> None:
        """Assert truth"""
        if not value:
            raise AssertionError(f"{message}: Expected True, got False")
    
    @staticmethod
    def assert_in(item: Any, container: Any, message: str = "") -> None:
        """Assert containment"""
        if item not in container:
            raise AssertionError(
                f"{message}: {item} not in {container}"
            )


def get_test_runner() -> TestRunner:
    """Get global test runner instance"""
    if not hasattr(get_test_runner, "_instance"):
        get_test_runner._instance = TestRunner()
    return get_test_runner._instance


def get_test_helper() -> TestHelper:
    """Get global test helper instance"""
    if not hasattr(get_test_helper, "_instance"):
        get_test_helper._instance = TestHelper()
    return get_test_helper._instance
