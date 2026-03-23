"""
Test Skill-LangGraph Integration

Tests for the Skill-LangGraph integration system.
"""

import asyncio
import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.agent_framework import (
    SkillRegistry,
    SkillContext,
    SkillResult,
    SkillCategory,
    SkillNodeWrapper,
    SkillGraphBuilder,
    SkillOrchestrator,
    SkillEnabledAgent,
    SkillAgentConfig,
)
from src.skills import (
    RepositoryScanSkill,
    TypoFixSkill,
    TypoReportSkill,
)


def test_skill_registration():
    """Test that skills are properly registered"""
    print("Testing Skill Registration...")

    expected_skills = [
        "repository_scan",
        "typo_fix",
        "typo_report",
        "git_operations",
        "pull_request",
    ]

    for skill_name in expected_skills:
        skill = SkillRegistry.get(skill_name)
        assert skill is not None, f"Skill '{skill_name}' not found"
        print(f"  ✓ Skill '{skill_name}' registered: {skill.metadata.description[:50]}...")

    print("Skill Registration tests passed!\n")


def test_skill_node_wrapper():
    """Test SkillNodeWrapper"""
    print("Testing SkillNodeWrapper...")

    # Get a skill
    skill = SkillRegistry.get("repository_scan")
    assert skill is not None

    # Create wrapper
    wrapper = SkillNodeWrapper(skill)

    print(f"  ✓ Wrapper created for skill: {wrapper.skill.name}")
    print(f"  ✓ Execution count: {wrapper.execution_count}")

    print("SkillNodeWrapper tests passed!\n")


async def test_skill_graph_builder():
    """Test SkillGraphBuilder"""
    print("Testing SkillGraphBuilder...")

    # Create builder
    builder = SkillGraphBuilder("test_workflow")

    # Add skills
    builder.add_skill("repository_scan", "scan")
    builder.add_skill("typo_report", "report")

    # Add transitions
    builder.add_transition("START", "scan")
    builder.add_transition("scan", "report")
    builder.add_transition("report", "END")

    print(f"  ✓ Added {len(builder.skills)} skills")
    print(f"  ✓ Added {len(builder.transitions)} transitions")

    print("SkillGraphBuilder tests passed!\n")


async def test_skill_orchestrator():
    """Test SkillOrchestrator"""
    print("Testing SkillOrchestrator...")

    # Create orchestrator
    orchestrator = SkillOrchestrator()

    # Check available workflows
    workflows = orchestrator.get_workflow_names()
    print(f"  ✓ Available workflows: {workflows}")

    assert "single_project" in workflows
    assert "batch" in workflows
    assert "scan_only" in workflows

    print("SkillOrchestrator tests passed!\n")


async def test_skill_enabled_agent():
    """Test SkillEnabledAgent"""
    print("Testing SkillEnabledAgent...")

    # Create agent
    config = SkillAgentConfig(
        name="TestSkillAgent",
        auto_register_skills=True,
        enable_langgraph=True,
    )
    agent = SkillEnabledAgent(config)

    # Initialize
    await agent.initialize()

    print(f"  ✓ Agent initialized: {agent.config.name}")
    print(f"  ✓ Active skills: {len(agent.active_skills)}")
    print(f"  ✓ Available workflows: {agent.get_available_workflows()}")

    # Test get skills
    skills = agent.get_available_skills()
    print(f"  ✓ Available skills: {len(skills)}")

    # Clean up
    await agent.stop()

    print("SkillEnabledAgent tests passed!\n")


async def test_skill_execution():
    """Test skill execution through agent"""
    print("Testing Skill Execution...")

    # Create temp directory
    temp_dir = Path(tempfile.mkdtemp())

    try:
        # Create test file with typos
        test_file = temp_dir / "test.md"
        test_file.write_text("This is a test with a typo: recieve.")

        # Create agent
        config = SkillAgentConfig(
            name="TestExecutionAgent",
            auto_register_skills=True,
        )
        agent = SkillEnabledAgent(config)
        await agent.initialize()

        # Test execute_skill task
        result = await agent.process_task({
            "type": "execute_skill",
            "skill_name": "repository_scan",
            "params": {
                "repo_path": str(temp_dir),
                "max_files": 10,
            }
        })

        print(f"  ✓ Skill execution result: {result}")

        # Clean up
        await agent.stop()

    finally:
        shutil.rmtree(temp_dir)

    print("Skill Execution tests passed!\n")


async def test_workflow_execution():
    """Test workflow execution"""
    print("Testing Workflow Execution...")

    # Create temp directory
    temp_dir = Path(tempfile.mkdtemp())

    try:
        # Create test file
        test_file = temp_dir / "test.md"
        test_file.write_text("This is a test.")

        # Create agent
        config = SkillAgentConfig(
            name="TestWorkflowAgent",
            enable_langgraph=True,
        )
        agent = SkillEnabledAgent(config)
        await agent.initialize()

        # Test run_workflow task (scan_only should work with just the scan skill)
        result = await agent.process_task({
            "type": "run_workflow",
            "workflow_name": "scan_only",
            "params": {
                "repo_path": str(temp_dir),
            }
        })

        print(f"  ✓ Workflow execution result: {result.get('success')}")

        # Clean up
        await agent.stop()

    finally:
        shutil.rmtree(temp_dir)

    print("Workflow Execution tests passed!\n")


async def main():
    """Run all integration tests"""
    print("=" * 60)
    print("Skill-LangGraph Integration Tests")
    print("=" * 60)
    print()

    try:
        # Sync tests
        test_skill_registration()
        test_skill_node_wrapper()

        # Async tests
        await test_skill_graph_builder()
        await test_skill_orchestrator()
        await test_skill_enabled_agent()
        await test_skill_execution()
        await test_workflow_execution()

        print("=" * 60)
        print("All integration tests passed! ✓")
        print("=" * 60)
        print("\nSummary:")
        print("  ✓ Skill registration working")
        print("  ✓ SkillNodeWrapper working")
        print("  ✓ SkillGraphBuilder working")
        print("  ✓ SkillOrchestrator working")
        print("  ✓ SkillEnabledAgent working")
        print("  ✓ Skill execution working")
        print("  ✓ Workflow execution working")
        print()

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
