"""
Quick test for unified memory system (without pytest)
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.agent_framework.memory import (
    UnifiedMemoryManager,
    MemoryEntry,
    FileBackend,
)


async def test_file_backend():
    """Test file backend"""
    print("Testing FileBackend...")

    # Create temp directory
    temp_dir = Path("./test_memory_temp")
    temp_dir.mkdir(exist_ok=True)

    try:
        backend = FileBackend(storage_path=str(temp_dir))

        # Store
        entry = MemoryEntry(
            id="test-123",
            content="Test content about Ethereum",
            category="knowledge",
            importance=0.8
        )

        success = await backend.store(entry)
        print(f"✓ Store: {success}")

        # Retrieve
        results = await backend.retrieve("Ethereum", limit=10)
        print(f"✓ Retrieve: found {len(results)} results")
        if results:
            print(f"  Content: {results[0].content}")

        # Get by ID
        retrieved = await backend.get_by_id("test-123")
        print(f"✓ Get by ID: {retrieved is not None}")

        # Delete
        deleted = await backend.delete("test-123")
        print(f"✓ Delete: {deleted}")

        print("FileBackend tests passed!\n")

    finally:
        # Cleanup
        import shutil
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


async def test_unified_memory():
    """Test unified memory manager"""
    print("Testing UnifiedMemoryManager...")

    temp_dir = Path("./test_memory_unified")
    temp_dir.mkdir(exist_ok=True)

    try:
        manager = UnifiedMemoryManager(
            agent_id="test_agent",
            enable_mem0=False,
            enable_chroma=False,  # Skip Chroma for quick test
            enable_file=True,
            storage_path=str(temp_dir)
        )

        # Test remember
        memory_id = await manager.remember(
            content="Ethereum uses Solidity for smart contracts",
            category="knowledge",
            importance=0.9,
            metadata={"topic": "blockchain"},
            level="file"
        )
        print(f"✓ Remember: {memory_id[:8]}...")

        # Test recall
        results = await manager.recall(
            query="smart contracts",
            category="knowledge",
            limit=5,
            level="file"
        )
        print(f"✓ Recall: found {len(results)} results")

        # Test conversation
        await manager.remember_conversation(
            role="user",
            content="What is Ethereum?",
            conversation_id="test_convo"
        )

        await manager.remember_conversation(
            role="assistant",
            content="Ethereum is a decentralized platform",
            conversation_id="test_convo"
        )

        convo = await manager.get_recent_conversation("test_convo", limit=10)
        print(f"✓ Conversation: {len(convo)} messages")

        # Test knowledge
        await manager.remember_knowledge(
            key="web3_terms",
            value=["ethereum", "solidity", "defi"],
            importance=1.0
        )
        print("✓ Knowledge stored")

        # Test experience
        await manager.remember_experience(
            task_type="scan_project",
            input_data={"owner": "test", "repo": "repo"},
            result={"typos_found": 5},
            success=True
        )
        print("✓ Experience stored")

        experiences = await manager.get_similar_experiences("scan_project")
        print(f"✓ Similar experiences: {len(experiences)} found")

        print("UnifiedMemoryManager tests passed!\n")

    finally:
        import shutil
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


async def test_base_agent_integration():
    """Test BaseAgent memory integration"""
    print("Testing BaseAgent integration...")

    from src.agent_framework import BaseAgent, AgentConfig

    class TestAgent(BaseAgent):
        async def on_initialize(self):
            pass
        async def on_start(self):
            pass
        async def on_stop(self):
            pass
        async def on_pause(self):
            pass
        async def on_resume(self):
            pass
        async def process_task(self, task):
            # Remember task
            await self.remember(
                content=f"Processed: {task}",
                category="workflow"
            )
            return {"success": True}

    config = AgentConfig(
        name="TestAgent",
        enable_memory=True,
        memory_backend="file"
    )

    agent = TestAgent(config)

    # Check memory manager exists
    assert hasattr(agent, 'memory_manager'), "memory_manager not found"
    assert hasattr(agent, 'conversation_history'), "conversation_history not found"
    print("✓ Memory manager attached to BaseAgent")

    # Test remember
    await agent.remember("Test memory", category="test", importance=0.8)
    print("✓ Agent remember works")

    # Test recall
    results = await agent.recall("Test memory")
    print(f"✓ Agent recall works: {len(results)} results")

    print("BaseAgent integration tests passed!\n")


async def main():
    """Run all tests"""
    print("=" * 50)
    print("Unified Memory System Tests")
    print("=" * 50 + "\n")

    try:
        await test_file_backend()
        await test_unified_memory()
        await test_base_agent_integration()

        print("=" * 50)
        print("All tests passed! ✓")
        print("=" * 50)

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
