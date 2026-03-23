"""
Example Extension - 示例 SKU 扩展包

这个文件是 SKU 的主入口，负责初始化和清理。
"""

from src.agent_framework.skill_system import BaseSkill, SkillContext, SkillResult, SkillCategory, skill
from src.agent_framework.tool_system import tool as tool_decorator
from src.agent_framework.logger import get_logger

logger = get_logger(__name__)

# SKU 配置（会从 manifest.json 加载）
config = {}

# 导出给 SKU Manager
SKILLS = []
TOOLS = []


async def initialize():
    """SKU 初始化时调用"""
    global config
    logger.info("Example Extension initializing...")

    # 这里可以做一些初始化工作
    # 比如加载配置文件、连接外部服务等

    logger.info(f"Example Extension initialized with config: {config}")


async def cleanup():
    """SKU 卸载时调用"""
    logger.info("Example Extension cleaning up...")

    # 这里做清理工作
    # 比如关闭连接、释放资源等

    logger.info("Example Extension cleaned up")


# ============ Skills ============

@skill(
    name="example_hello",
    description="示例 Skill：打招呼",
    category=SkillCategory.CUSTOM,
    version="1.0.0",
    author="Example Extension",
    tags=["example", "greeting"],
)
class ExampleHelloSkill(BaseSkill):
    """示例 Skill：向用户打招呼"""

    async def execute(self, context: SkillContext, name: str = "World") -> SkillResult:
        """
        执行打招呼

        Args:
            context: Skill 上下文
            name: 要问候的名字

        Returns:
            包含问候语的 SkillResult
        """
        greeting = config.get("greeting", "Hello")
        message = f"{greeting}, {name}!"

        logger.info(f"ExampleHelloSkill: {message}")

        return SkillResult(
            success=True,
            data={
                "message": message,
                "timestamp": str(__import__('datetime').datetime.now()),
            }
        )


@skill(
    name="example_calculate",
    description="示例 Skill：简单计算",
    category=SkillCategory.CUSTOM,
    version="1.0.0",
    author="Example Extension",
    tags=["example", "math"],
)
class ExampleCalculateSkill(BaseSkill):
    """示例 Skill：执行简单计算"""

    async def execute(
        self,
        context: SkillContext,
        operation: str,
        a: float,
        b: float
    ) -> SkillResult:
        """
        执行计算

        Args:
            context: Skill 上下文
            operation: 操作类型 (add, subtract, multiply, divide)
            a: 第一个数字
            b: 第二个数字

        Returns:
            包含计算结果的 SkillResult
        """
        try:
            if operation == "add":
                result = a + b
            elif operation == "subtract":
                result = a - b
            elif operation == "multiply":
                result = a * b
            elif operation == "divide":
                if b == 0:
                    return SkillResult(
                        success=False,
                        error="Cannot divide by zero"
                    )
                result = a / b
            else:
                return SkillResult(
                    success=False,
                    error=f"Unknown operation: {operation}"
                )

            return SkillResult(
                success=True,
                data={
                    "operation": operation,
                    "a": a,
                    "b": b,
                    "result": result,
                }
            )

        except Exception as e:
            return SkillResult(
                success=False,
                error=str(e)
            )


# 注册 Skills
SKILLS = [ExampleHelloSkill, ExampleCalculateSkill]


# ============ Tools ============

@tool_decorator(name="example_reverse", description="反转字符串")
def example_reverse_tool(text: str) -> str:
    """
    示例 Tool：反转字符串

    Args:
        text: 要反转的字符串

    Returns:
        反转后的字符串
    """
    return text[::-1]


@tool_decorator(name="example_word_count", description="统计字数")
def example_word_count_tool(text: str) -> dict:
    """
    示例 Tool：统计字数

    Args:
        text: 要统计的文本

    Returns:
        包含字数统计的字典
    """
    words = text.split()
    return {
        "characters": len(text),
        "characters_no_spaces": len(text.replace(" ", "")),
        "words": len(words),
        "lines": len(text.split("\n")),
    }


# 注册 Tools
TOOLS = [
    example_reverse_tool,
    example_word_count_tool,
]
