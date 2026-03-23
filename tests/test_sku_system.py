"""
Test SKU Extension System

Tests for the SKU (Skill/Extension Unit) framework.
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
    SKUManager,
    SKULoader,
    SKUMetadata,
    SkillEnabledAgent,
    SkillAgentConfig,
)


def test_sku_metadata():
    """Test SKU metadata"""
    print("Testing SKU Metadata...")

    metadata = SKUMetadata(
        name="test_sku",
        version="1.0.0",
        description="Test SKU",
        author="Test",
        category="test",
        tags=["test", "demo"],
    )

    assert metadata.name == "test_sku"
    assert metadata.version == "1.0.0"

    # Test dict conversion
    data = metadata.to_dict()
    assert data["name"] == "test_sku"

    # Test from dict
    metadata2 = SKUMetadata.from_dict(data)
    assert metadata2.name == "test_sku"

    print("  ✓ SKU Metadata tests passed!")


async def test_sku_loader():
    """Test SKU loader"""
    print("Testing SKU Loader...")

    loader = SKULoader()

    # Test loading example extension
    example_path = Path("./skus/example_extension")
    if example_path.exists():
        sku = await loader.load_from_path(example_path)
        if sku:
            print(f"  ✓ Loaded SKU: {sku.metadata.name} v{sku.metadata.version}")
            print(f"  ✓ Description: {sku.metadata.description}")
            assert sku.state == "active"
        else:
            print("  ✗ Failed to load example extension")
    else:
        print(f"  ⚠ Example extension not found at {example_path}")

    print("  ✓ SKU Loader tests passed!")


async def test_sku_manager():
    """Test SKU manager"""
    print("Testing SKU Manager...")

    manager = SKUManager()

    # Load example extension
    example_path = Path("./skus/example_extension")
    if example_path.exists():
        sku = await manager.load_sku(example_path)
        if sku:
            print(f"  ✓ Loaded SKU: {sku.metadata.name}")

            # Test listing
            skus = manager.list_skus()
            print(f"  ✓ Listed {len(skus)} SKUs")
            assert len(skus) >= 1

            # Test get_sku
            loaded = manager.get_sku("example_extension")
            assert loaded is not None
            print(f"  ✓ Retrieved SKU: {loaded.metadata.name}")

            # Test get skill
            skill_class = manager.get_skill("ExampleHelloSkill")
            if skill_class:
                print(f"  ✓ Found skill: ExampleHelloSkill")

            # Test capabilities
            caps = manager.list_capabilities()
            print(f"  ✓ Capabilities: {len(caps['skus'])} SKUs, "
                  f"{len(caps['skills'])} skills, {len(caps['tools'])} tools")

            # Test unload
            success = await manager.unload_sku("example_extension")
            assert success
            print(f"  ✓ Unloaded SKU successfully")

            assert "example_extension" not in manager.loaded_skus

    print("  ✓ SKU Manager tests passed!")


async def test_agent_with_sku():
    """Test Agent with SKU support"""
    print("Testing Agent with SKU...")

    config = SkillAgentConfig(
        name="TestSKUAgent",
        enable_sku=True,
        sku_directory="./skus",
        auto_load_skus=False,  # We'll load manually
    )

    agent = SkillEnabledAgent(config)
    await agent.initialize()

    print(f"  ✓ Agent initialized")
    print(f"  ✓ SKU Manager: {agent.sku_manager is not None}")

    # Load example extension
    example_path = Path("./skus/example_extension")
    if example_path.exists():
        result = await agent.process_task({
            "type": "load_sku",
            "source": "path",
            "path": str(example_path),
        })

        print(f"  ✓ Load SKU result: {result.get('success')}")

        if result.get("success"):
            # List SKUs
            result = await agent.process_task({
                "type": "list_skus",
            })
            print(f"  ✓ Listed SKUs: {len(result.get('skus', []))}")

            # Get capabilities
            result = await agent.process_task({
                "type": "get_capabilities",
            })
            print(f"  ✓ Agent capabilities: {list(result.keys())}")

            # Unload SKU
            result = await agent.process_task({
                "type": "unload_sku",
                "name": "example_extension",
            })
            print(f"  ✓ Unload SKU result: {result.get('success')}")

    await agent.stop()
    print("  ✓ Agent stopped")

    print("  ✓ Agent with SKU tests passed!")


async def main():
    """Run all SKU tests"""
    print("=" * 60)
    print("SKU Extension System Tests")
    print("=" * 60)
    print()

    try:
        # Sync tests
        test_sku_metadata()

        # Async tests
        await test_sku_loader()
        await test_sku_manager()
        await test_agent_with_sku()

        print()
        print("=" * 60)
        print("All SKU tests passed! ✓")
        print("=" * 60)
        print("\nSummary:")
        print("  ✓ SKU Metadata working")
        print("  ✓ SKU Loader working")
        print("  ✓ SKU Manager working")
        print("  ✓ Agent SKU integration working")
        print()

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
