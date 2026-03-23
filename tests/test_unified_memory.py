"""
Test for unified memory system
"""

import asyncio
import pytest
import os
import shutil
from pathlib import Path

# Skip if no OPENAI_API_KEY
pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set"
)

from src.agent_framework.memory import (
    UnifiedMemoryManager,
    MemoryEntry,
    get_memory_manager,
    FileBackend,
    ChromaBackend,
)


@pytest.fixture
def temp_memory_dir(tmp_path):
    """Create temporary memory directory"""
    memory_dir = tmp_path / "test_memory"
    memory_dir.mkdir()
    yield str(memory_dir)
    # Cleanup
    if memory_dir.exists():
        shutil.rmtree(memory_dir)


@pytest.fixture
def memory_manager(temp_memory_dir):
    """Create memory manager for testing"""
    manager = UnifiedMemoryManager(
        agent_id="test_agent",
        enable_mem0=False,  # Skip Mem0 for unit tests
        enable_chroma=True,
        enable_file=True,
        storage_path=temp_memory_dir
    )
    return manager


class TestUnifiedMemory:
    """Test unified memory system"""

    @pytest.mark.asyncio
    async def test_remember_and_recall(self, memory_manager):
        """Test basic remember and recall"""
        # Store a memory
        memory_id = await memory_manager.remember(
            content="Test content about Ethereum smart contracts",
            category="knowledge",
            importance=0.9,
            metadata={"topic": "ethereum"}
        )

        assert memory_id != ""

        # Recall it
        results = await memory_manager.recall(
            query="Ethereum smart contracts",
            category="knowledge",
            limit=5
        )

        assert len(results) > 0
        assert any("Ethereum" in r.content for r in results)

    @pytest.mark.asyncio
    async def test_conversation_memory(self, memory_manager):
        """Test conversation memory"""
        convo_id = "test_convo_123"

        # Add conversation messages
        await memory_manager.remember_conversation(
            role="user",
            content="What can you do?",
            conversation_id=convo_id
        )

        await memory_manager.remember_conversation(
            role="assistant",
            content="I can help you fix typos in code.",
            conversation_id=convo_id
        )

        # Retrieve conversation
        messages = await memory_manager.get_recent_conversation(convo_id, limit=10)

        assert len(messages) == 2
        assert any("What can you do" in m.content for m in messages)
        assert any("fix typos" in m.content for m in messages)

    @pytest.mark.asyncio
    async def test_experience_memory(self, memory_manager):
        """Test experience memory for learning"""
        # Record successful experience
        await memory_manager.remember_experience(
            task_type="scan_project",
            input_data={"owner": "test", "repo": "repo"},
            result={"typos_found": 5, "typos_fixed": 5},
            success=True
        )

        # Record failed experience
        await memory_manager.remember_experience(
            task_type="scan_project",
            input_data={"owner": "test2", "repo": "repo2"},
            result={"error": "Network timeout"},
            success=False
        )

        # Retrieve experiences
        experiences = await memory_manager.get_similar_experiences("scan_project", limit=5)

        assert len(experiences) == 2
        # Successful experience should have higher importance
        success_exp = [e for e in experiences if e.metadata.get("success")]
        assert len(success_exp) > 0

    @pytest.mark.asyncio
    async def test_knowledge_memory(self, memory_manager):
        """Test knowledge storage"""
        await memory_manager.remember_knowledge(
            key="web3_terms",
            value=["ethereum", "solidity", "defi", "nft"],
            importance=1.0
        )

        # Recall knowledge
        results = await memory_manager.recall(
            query="web3 terms ethereum",
            category="knowledge",
            limit=5
        )

        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_build_context(self, memory_manager):
        """Test building LLM context from memory"""
        # Store some knowledge
        await memory_manager.remember(
            content="Python is a programming language",
            category="knowledge",
            importance=0.8
        )

        await memory_manager.remember_conversation(
            role="user",
            content="Tell me about programming",
            conversation_id="ctx_test"
        )

        # Build context
        context = await memory_manager.build_context(
            query="programming language",
            max_tokens=1000
        )

        assert "Python" in context or "programming" in context

    @pytest.mark.asyncio
    async def test_memory_levels(self, memory_manager):
        """Test different memory storage levels"""
        # Store at different levels
        id1 = await memory_manager.remember(
            content="Working only",
            level="working"
        )

        id2 = await memory_manager.remember(
            content="File backup",
            level="file"
        )

        id3 = await memory_manager.remember(
            content="Chroma vector",
            level="chroma"
        )

        # Working memory should have all
        working_results = await memory_manager.recall("Working only", level="working")
        assert len(working_results) >= 1

        # File should have file and chroma
        file_results = await memory_manager.recall("File backup", level="file")
        assert len(file_results) >= 1


class TestMemorySingleton:
    """Test memory manager singleton pattern"""

    def test_get_memory_manager(self, temp_memory_dir):
        """Test singleton pattern"""
        # Mock the storage path by patching
        import src.agent_framework.unified_memory as um
        original_init = um.UnifiedMemoryManager.__init__

        def mock_init(self, agent_id, **kwargs):
            kwargs['storage_path'] = temp_memory_dir
            original_init(self, agent_id, **kwargs)

        um.UnifiedMemoryManager.__init__ = mock_init

        try:
            manager1 = get_memory_manager("singleton_test")
            manager2 = get_memory_manager("singleton_test")

            assert manager1 is manager2
            assert manager1.agent_id == "singleton_test"
        finally:
            um.UnifiedMemoryManager.__init__ = original_init


class TestFileBackend:
    """Test file-based memory backend"""

    @pytest.mark.asyncio
    async def test_file_backend_basic(self, temp_memory_dir):
        """Test file backend operations"""
        backend = FileBackend(storage_path=temp_memory_dir)

        # Store
        entry = MemoryEntry(
            id="test-123",
            content="Test content",
            category="test",
            importance=0.8
        )

        success = await backend.store(entry)
        assert success

        # Retrieve
        results = await backend.retrieve("Test", limit=10)
        assert len(results) == 1
        assert results[0].content == "Test content"

        # Get by ID
        retrieved = await backend.get_by_id("test-123")
        assert retrieved is not None
        assert retrieved.content == "Test content"

        # Delete
        deleted = await backend.delete("test-123")
        assert deleted

        # Verify deletion
        retrieved_after = await backend.get_by_id("test-123")
        assert retrieved_after is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
