#!/usr/bin/env python3
"""
Memory System Demo - 记忆系统演示

展示新的统一记忆系统功能
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent_framework.memory import (
    UnifiedMemoryManager,
    get_memory_manager,
    FileBackend,
    ChromaBackend,
    MemoryEntry,
)


async def demo_workflow_memory():
    """演示工作流记忆"""
    print("=" * 60)
    print("演示1: 工作流记忆 (Workflow Memory)")
    print("=" * 60)

    # 创建记忆管理器
    manager = UnifiedMemoryManager(
        agent_id="demo_coordinator",
        enable_mem0=False,
        enable_chroma=True,
        enable_file=True,
    )

    print("\n1. 模拟扫描项目...")
    scan_result = {
        "owner": "ethereum",
        "repo": "go-ethereum",
        "typos_found": 15,
        "files_scanned": 245,
    }

    await manager.remember_workflow(
        workflow_name="single_project",
        state=scan_result,
        importance=0.9
    )
    print(f"   ✓ 记录工作流: {scan_result['owner']}/{scan_result['repo']}")
    print(f"   ✓ 发现 {scan_result['typos_found']} 个 typo")

    print("\n2. 模拟修复...")
    fix_result = {
        "typos_fixed": 14,
        "failed": 1,
        "quality_score": 0.93,
    }

    await manager.remember_experience(
        task_type="fix_typos",
        input_data={"typos_count": 15},
        result=fix_result,
        success=True
    )
    print(f"   ✓ 记录经验: 修复了 {fix_result['typos_fixed']} 个 typo")
    print(f"   ✓ 质量评分: {fix_result['quality_score']}")

    print("\n3. 检索相似经验...")
    experiences = await manager.get_similar_experiences("fix_typos", limit=5)
    print(f"   ✓ 找到 {len(experiences)} 条相关经验")
    for exp in experiences:
        print(f"     - {exp.content}")

    print("\n4. 构建LLM上下文...")
    context = await manager.build_context("How to fix typos?")
    print(f"   ✓ 上下文长度: {len(context)} 字符")
    print(f"\n   上下文预览:\n{context[:400]}...")


async def demo_conversation_memory():
    """演示对话记忆"""
    print("\n" + "=" * 60)
    print("演示2: 对话记忆 (Conversation Memory)")
    print("=" * 60)

    manager = get_memory_manager("demo_chat")

    conversation_id = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    print(f"\n对话ID: {conversation_id}")

    # 模拟对话
    conversations = [
        ("user", "你能帮我做什么？"),
        ("assistant", "我是TypoMaster，可以帮你扫描和修复代码中的拼写错误。"),
        ("user", "怎么使用？"),
        ("assistant", "你只需要提供GitHub仓库地址，例如: /run owner/repo"),
        ("user", "支持哪些语言？"),
        ("assistant", "目前支持Python、JavaScript、TypeScript、Go、Rust等主流语言。"),
    ]

    print("\n记录对话...")
    for role, content in conversations:
        await manager.remember_conversation(role, content, conversation_id)
        print(f"   [{role}] {content[:40]}...")

    print("\n检索对话历史...")
    history = await manager.get_recent_conversation(conversation_id, limit=10)
    print(f"   ✓ 共 {len(history)} 条消息")

    print("\n语义搜索对话...")
    results = await manager.recall(
        query="支持什么语言",
        category="conversation",
        limit=3
    )
    print(f"   ✓ 找到 {len(results)} 条相关消息:")
    for r in results:
        print(f"     - {r.content[:50]}...")


async def demo_knowledge_memory():
    """演示知识记忆"""
    print("\n" + "=" * 60)
    print("演示3: 知识记忆 (Knowledge Memory)")
    print("=" * 60)

    manager = get_memory_manager("demo_knowledge")

    print("\n存储Web3知识...")
    knowledge_items = [
        ("ethereum_consensus", "Ethereum使用Proof of Stake共识机制", 0.95),
        ("solidity_types", "Solidity支持uint256、address、bool等类型", 0.9),
        ("web3_terms", "DeFi、NFT、DAO是Web3核心概念", 0.85),
        ("common_typos", "recieve -> receive, seperate -> separate", 0.8),
    ]

    for key, content, importance in knowledge_items:
        await manager.remember_knowledge(
            key=key,
            value=content,
            importance=importance
        )
        print(f"   ✓ [{key}] {content[:30]}... (重要性: {importance})")

    print("\n搜索知识...")
    queries = [
        "Ethereum共识机制",
        "Solidity类型",
        "常见拼写错误",
    ]

    for query in queries:
        results = await manager.recall(query, category="knowledge", limit=3)
        print(f"\n   查询: '{query}'")
        print(f"   ✓ 找到 {len(results)} 条知识:")
        for r in results:
            print(f"     - {r.content[:50]}...")


async def demo_memory_levels():
    """演示多层记忆"""
    print("\n" + "=" * 60)
    print("演示4: 多层记忆架构 (Memory Levels)")
    print("=" * 60)

    temp_dir = Path("./demo_memory_levels")
    temp_dir.mkdir(exist_ok=True)

    manager = UnifiedMemoryManager(
        agent_id="demo_levels",
        enable_chroma=True,
        enable_file=True,
        storage_path=str(temp_dir)
    )

    print("\n1. 仅存储到工作内存 (Working Memory)")
    await manager.remember(
        content="This is temporary data",
        category="test",
        level="working"
    )

    print("   ✓ 数据仅存在于内存")

    print("\n2. 存储到文件 (File Backend)")
    await manager.remember(
        content="This is important backup data",
        category="test",
        level="file"
    )
    print("   ✓ 数据已持久化到文件")

    print("\n3. 存储到向量数据库 (ChromaDB)")
    await manager.remember(
        content="This data supports semantic search",
        category="test",
        level="chroma"
    )
    print("   ✓ 数据已向量化存储")

    print("\n4. 存储到所有层级 (All Levels)")
    await manager.remember(
        content="This critical data goes everywhere",
        category="test",
        level="all"
    )
    print("   ✓ 数据存储到所有层级")

    print("\n5. 跨层级检索...")
    for level in ["working", "file", "chroma", "all"]:
        results = await manager.recall("data", level=level, limit=10)
        print(f"   [{level:8s}] 找到 {len(results)} 条")

    # Cleanup
    import shutil
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


async def demo_agent_integration():
    """演示Agent集成"""
    print("\n" + "=" * 60)
    print("演示5: Agent集成 (Agent Integration)")
    print("=" * 60)

    from src.agents.coordinator_agent import CoordinatorAgent

    print("\n初始化 CoordinatorAgent...")
    coordinator = CoordinatorAgent(
        github_token=None,
        work_dir="./demo_work"
    )

    print("   ✓ Agent创建成功")
    print(f"   ✓ Agent ID: {coordinator.agent_id[:8]}...")
    print(f"   ✓ Memory Manager: {coordinator.memory_manager is not None}")
    print(f"   ✓ Conversation History: {coordinator.conversation_history is not None}")

    print("\n使用Agent记忆方法...")

    # Remember
    await coordinator.remember(
        content="Coordinator agent initialized successfully",
        category="system",
        importance=1.0
    )
    print("   ✓ coordinator.remember() works")

    # Recall
    results = await coordinator.recall("initialized")
    print(f"   ✓ coordinator.recall() works: {len(results)} results")

    # Conversation
    await coordinator.add_to_conversation("user", "Start workflow", "demo_001")
    await coordinator.add_to_conversation("assistant", "Workflow started", "demo_001")
    print(f"   ✓ coordinator.add_to_conversation() works: {len(coordinator.conversation_history)} messages")

    print("\nAgent记忆功能已完全集成！")


async def show_memory_stats():
    """显示记忆统计"""
    print("\n" + "=" * 60)
    print("记忆系统统计")
    print("=" * 60)

    manager = get_memory_manager("demo_stats")

    # Store some data
    for i in range(5):
        await manager.remember(
            content=f"Sample memory {i}",
            category="stats_test",
            importance=0.5 + i * 0.1
        )

    # Show stats
    all_memories = await manager.recall("Sample", limit=100)

    print(f"\n总记忆数: {len(all_memories)}")

    categories = {}
    for m in all_memories:
        cat = m.category
        categories[cat] = categories.get(cat, 0) + 1

    print(f"分类统计:")
    for cat, count in categories.items():
        print(f"   - {cat}: {count}")

    if all_memories:
        avg_importance = sum(m.importance for m in all_memories) / len(all_memories)
        print(f"平均重要性: {avg_importance:.2f}")


async def main():
    """运行所有演示"""
    print("\n" + "=" * 60)
    print(" TypoMaster 统一记忆系统演示")
    print("=" * 60)
    print("\n本演示展示新的记忆系统功能:")
    print("  - 多层记忆架构 (Working/Chroma/File)")
    print("  - 对话历史持久化")
    print("  - 知识存储与检索")
    print("  - 经验学习与复用")
    print("  - LLM上下文构建")
    print()

    try:
        await demo_workflow_memory()
        await demo_conversation_memory()
        await demo_knowledge_memory()
        await demo_memory_levels()
        await demo_agent_integration()
        await show_memory_stats()

        print("\n" + "=" * 60)
        print("演示完成！")
        print("=" * 60)
        print("\n记忆系统已准备就绪，可以用于:")
        print("  1. 工作流状态持久化")
        print("  2. 跨会话对话记忆")
        print("  3. 项目知识积累")
        print("  4. 经验学习与优化")
        print()

    except Exception as e:
        print(f"\n演示出错: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
