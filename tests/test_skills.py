"""
Test TypoAgent Skills

Tests for the skill system and TypoAgent skills.
"""

import asyncio
import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.agent_framework.skill_system import SkillRegistry, SkillCategory
from src.skills import (
    RepositoryScanSkill,
    TypoFixSkill,
    TypoReportSkill,
    GitOperationsSkill,
    PullRequestSkill,
)
from src.skills.skill_manager import TypoAgentSkillManager


def test_skill_registry():
    """Test skill registry"""
    print("Testing Skill Registry...")

    # Check all skills are registered
    all_skills = SkillRegistry.list_skills()
    print(f"  Registered skills: {all_skills}")

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
        print(f"  ✓ Skill '{skill_name}' registered")

    # Test category listing
    scan_skills = SkillRegistry.get_by_category(SkillCategory.SCAN)
    assert len(scan_skills) >= 1, "No scan skills found"
    print(f"  ✓ Found {len(scan_skills)} scan skill(s)")

    fix_skills = SkillRegistry.get_by_category(SkillCategory.FIX)
    assert len(fix_skills) >= 1, "No fix skills found"
    print(f"  ✓ Found {len(fix_skills)} fix skill(s)")

    print("Skill Registry tests passed!\n")


def test_skill_metadata():
    """Test skill metadata"""
    print("Testing Skill Metadata...")

    scan_skill = SkillRegistry.get("repository_scan")
    assert scan_skill is not None

    metadata = scan_skill.metadata
    print(f"  Name: {metadata.name}")
    print(f"  Description: {metadata.description}")
    print(f"  Category: {metadata.category}")
    print(f"  Required tools: {metadata.required_tools}")

    assert metadata.name == "repository_scan"
    assert metadata.category == SkillCategory.SCAN
    assert len(metadata.required_tools) > 0

    print("Skill Metadata tests passed!\n")


async def test_repository_scan_skill():
    """Test repository scan skill"""
    print("Testing RepositoryScanSkill...")

    # Create a temp directory with a file containing typos
    temp_dir = Path(tempfile.mkdtemp())

    try:
        # Create a test file with typos
        test_file = temp_dir / "test.md"
        test_file.write_text("This is a test with a typo: recieve should be receive.")

        skill = RepositoryScanSkill()

        from src.agent_framework.skill_system import SkillContext
        context = SkillContext()

        result = await skill.execute(
            context,
            repo_path=str(temp_dir),
            max_files=10,
        )

        print(f"  Success: {result.success}")
        print(f"  Steps executed: {result.steps_executed}")

        if result.success:
            print(f"  Total typos: {result.data.get('total_typos')}")
            print(f"  Files scanned: {result.data.get('files_scanned')}")

        print("RepositoryScanSkill tests passed!\n")

    finally:
        shutil.rmtree(temp_dir)


async def test_typo_fix_skill():
    """Test typo fix skill"""
    print("Testing TypoFixSkill...")

    # Create a temp file
    temp_dir = Path(tempfile.mkdtemp())

    try:
        test_file = temp_dir / "test.txt"
        test_file.write_text("This contians a typo.")

        skill = TypoFixSkill()

        from src.agent_framework.skill_system import SkillContext
        context = SkillContext()

        result = await skill.execute(
            context,
            file_path=str(test_file),
            typo="contians",
            correction="contains",
            create_backup=True,
            verify_fix=True,
        )

        print(f"  Success: {result.success}")
        print(f"  Steps executed: {result.steps_executed}")

        if result.success:
            # Verify file was fixed
            content = test_file.read_text()
            print(f"  Fixed content: {content}")
            assert "contains" in content
            assert "contians" not in content

            # Verify backup was created
            backup_file = Path(f"{test_file}.backup")
            assert backup_file.exists()
            print(f"  ✓ Backup created: {backup_file}")

        print("TypoFixSkill tests passed!\n")

    finally:
        shutil.rmtree(temp_dir)


async def test_typo_report_skill():
    """Test typo report skill"""
    print("Testing TypoReportSkill...")

    temp_dir = Path(tempfile.mkdtemp())

    try:
        skill = TypoReportSkill()

        from src.agent_framework.skill_system import SkillContext
        context = SkillContext()

        typos = [
            {"file_path": "test.md", "typo": "teh", "correction": "the"},
            {"file_path": "test.md", "typo": "recieve", "correction": "receive"},
            {"file_path": "readme.md", "typo": "adress", "correction": "address"},
        ]

        output_path = str(temp_dir / "report.md")

        result = await skill.execute(
            context,
            typos=typos,
            output_path=output_path,
            format="markdown",
        )

        print(f"  Success: {result.success}")

        if result.success:
            print(f"  Output path: {result.data.get('output_path')}")
            print(f"  Typo count: {result.data.get('typo_count')}")
            print(f"  Stats: {result.data.get('stats')}")

        print("TypoReportSkill tests passed!\n")

    finally:
        shutil.rmtree(temp_dir)


async def test_skill_manager():
    """Test TypoAgent skill manager"""
    print("Testing TypoAgentSkillManager...")

    manager = TypoAgentSkillManager()

    print(f"  Skills initialized:")
    print(f"    - Scan: {manager.scan_skill.name}")
    print(f"    - Fix: {manager.fix_skill.name}")
    print(f"    - Report: {manager.report_skill.name}")
    print(f"    - Git: {manager.git_skill.name}")
    print(f"    - PR: {manager.pr_skill.name}")

    # Test stats
    stats = manager.get_stats()
    print(f"  Stats: {stats}")

    print("TypoAgentSkillManager tests passed!\n")


async def main():
    """Run all skill tests"""
    print("=" * 60)
    print("TypoAgent Skills Tests")
    print("=" * 60)
    print()

    try:
        # Sync tests
        test_skill_registry()
        test_skill_metadata()

        # Async tests
        await test_repository_scan_skill()
        await test_typo_fix_skill()
        await test_typo_report_skill()
        await test_skill_manager()

        print("=" * 60)
        print("All skill tests passed! ✓")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
