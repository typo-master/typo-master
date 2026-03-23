#!/usr/bin/env python3
"""
Test memory system with real LLM API
"""

import asyncio
import os
import sys
from pathlib import Path

# Set API configuration
os.environ["OPENAI_API_KEY"] = "sk-sp-6ae28092e0874696a091f765c7e0118b"
os.environ["OPENAI_BASE_URL"] = "https://coding.dashscope.aliyuncs.com/apps/anthropic"
os.environ["OPENAI_MODEL"] = "kimi-k2.5"
os.environ["LLM_ENABLED"] = "true"

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent_framework.llm_client import OpenAICompatibleResponsesClient
from src.agent_framework.unified_memory import UnifiedMemoryManager, get_memory_manager


async def test_llm_connection():
    """Test LLM API connection"""
    print("=" * 50)
    print("Testing LLM API Connection")
    print("=" * 50)

    client = OpenAICompatibleResponsesClient.from_env()

    print(f"Config:")
    print(f"  Enabled: {client.config.enabled}")
    print(f"  Base URL: {client.config.base_url}")
    print(f"  Model: {client.config.model}")
    print(f"  API Key: {client.config.api_key[:10]}..." if client.config.api_key else "  No API Key")

    if not client.is_enabled:
        print("❌ LLM client is not enabled")
        return False

    # Test health check
    print("\nTesting health check...")
    result = client.health_check()

    if result.get("success"):
        print(f"✓ Health check passed")
        print(f"  Response: {result.get('response_text')}")
        return True
    else:
        print(f"❌ Health check failed: {result.get('error')}")
        return False


async def test_memory_with_llm():
    """Test memory system with LLM integration"""
    print("\n" + "=" * 50)
    print("Testing Memory System with LLM")
    print("=" * 50)

    temp_dir = Path("./test_memory_llm")
    temp_dir.mkdir(exist_ok=True)

    try:
        # Create memory manager
        manager = UnifiedMemoryManager(
            agent_id="test_agent_llm",
            enable_mem0=False,  # Skip mem0 for now
            enable_chroma=True,
            enable_file=True,
            storage_path=str(temp_dir)
        )

        print("✓ Memory manager initialized")

        # Test 1: Store knowledge
        print("\n1. Testing knowledge storage...")
        memory_id = await manager.remember(
            content="TypoMaster is an AI agent that fixes typos in Web3 projects",
            category="knowledge",
            importance=0.9,
            metadata={"topic": "product", "tags": ["web3", "typos"]}
        )
        print(f"✓ Stored knowledge: {memory_id[:8]}...")

        # Test 2: Semantic search (requires embedding)
        print("\n2. Testing semantic search...")
        results = await manager.recall(
            query="What does TypoMaster do?",
            category="knowledge",
            limit=3
        )
        print(f"✓ Found {len(results)} results")
        for r in results:
            print(f"  - {r.content[:60]}...")

        # Test 3: Conversation memory
        print("\n3. Testing conversation memory...")
        await manager.remember_conversation(
            role="user",
            content="Can you help me fix typos in my project?",
            conversation_id="test_convo_001"
        )
        await manager.remember_conversation(
            role="assistant",
            content="Yes! I can scan your code and find typos. Just provide your GitHub repo.",
            conversation_id="test_convo_001"
        )

        convo = await manager.get_recent_conversation("test_convo_001", limit=10)
        print(f"✓ Retrieved {len(convo)} conversation messages")

        # Test 4: Experience memory
        print("\n4. Testing experience memory...")
        await manager.remember_experience(
            task_type="scan_project",
            input_data={"owner": "ethereum", "repo": "go-ethereum"},
            result={"typos_found": 12, "typos_fixed": 10, "quality_score": 0.85},
            success=True
        )

        experiences = await manager.get_similar_experiences("scan_project", limit=5)
        print(f"✓ Found {len(experiences)} similar experiences")

        # Test 5: Build LLM context
        print("\n5. Testing LLM context building...")
        context = await manager.build_context(
            query="How to fix typos in a project?",
            max_tokens=1000
        )
        print(f"✓ Built context ({len(context)} chars)")
        print(f"\nContext preview:\n{context[:500]}...")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup
        import shutil
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


async def test_with_coordinator():
    """Test with CoordinatorAgent"""
    print("\n" + "=" * 50)
    print("Testing CoordinatorAgent Memory")
    print("=" * 50)

    from src.agents.coordinator_agent import CoordinatorAgent

    try:
        # Create coordinator with memory enabled
        coordinator = CoordinatorAgent(
            github_token=os.getenv("GITHUB_TOKEN"),
            work_dir="./test_work"
        )

        # Check memory manager exists
        assert hasattr(coordinator, 'memory_manager'), "No memory_manager"
        assert hasattr(coordinator, 'conversation_history'), "No conversation_history"

        print("✓ Coordinator has memory_manager")
        print("✓ Coordinator has conversation_history")

        # Test memory methods
        await coordinator.remember(
            content="Test memory from coordinator",
            category="workflow"
        )
        print("✓ Coordinator.remember works")

        results = await coordinator.recall("Test memory")
        print(f"✓ Coordinator.recall works: {len(results)} results")

        # Test conversation
        await coordinator.add_to_conversation("user", "Hello", "test_convo")
        await coordinator.add_to_conversation("assistant", "Hi there!", "test_convo")
        print(f"✓ Conversation history: {len(coordinator.conversation_history)} messages")

        return True

    except Exception as e:
        print(f"❌ Coordinator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("Memory System + LLM Integration Tests")
    print("=" * 60 + "\n")

    results = []

    # Test 1: LLM Connection
    results.append(("LLM Connection", await test_llm_connection()))

    # Test 2: Memory System
    results.append(("Memory System", await test_memory_with_llm()))

    # Test 3: Coordinator Integration
    results.append(("Coordinator Agent", await test_with_coordinator()))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for name, passed in results:
        status = "✓ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")

    all_passed = all(passed for _, passed in results)

    if all_passed:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed")
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
