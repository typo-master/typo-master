import asyncio

from src.agents.coordinator_agent import CoordinatorAgent


def test_coordinator_capabilities_contains_langgraph_framework():
    async def run():
        agent = CoordinatorAgent()
        await agent.initialize()
        try:
            result = await agent.process_task({"type": "get_capabilities"})
            assert result.get("success") is True
            assert result.get("framework") == "LangGraph"
            assert result.get("features", {}).get("quality_evaluation") is True
            assert result.get("features", {}).get("pr_decision") is True
        finally:
            await agent.stop()

    asyncio.run(run())
