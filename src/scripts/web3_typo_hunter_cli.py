#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
命令行入口脚本 - 提供命令行界面操作Web3TypoHunter Agent系统
"""

import argparse
import asyncio
import json
import sys

from src.agents.coordinator_agent import CoordinatorAgent
from src.agents.decision_agent import DecisionAgent
from src.agent_framework.logger import get_logger

logger = get_logger(__name__)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="Web3 Typo Hunter Agent - 基于Agent的Web3拼写错误查找工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 查找潜在空投项目
  python web3_typo_hunter_cli.py find --token YOUR_TOKEN --days 30 --min-stars 100 --limit 50

  # 扫描单个项目
  python web3_typo_hunter_cli.py scan --token YOUR_TOKEN --repo owner/repo --create-pr

  # 批量处理项目
  python web3_typo_hunter_cli.py process --token YOUR_TOKEN --days 30 --min-stars 100 --limit 5 --create-pr

  # 检查LLM API连通性（需设置 OPENAI_API_KEY/OPENAI_BASE_URL/OPENAI_MODEL）
  python web3_typo_hunter_cli.py llm-check

  # 查看当前 Agent 能力矩阵
  python web3_typo_hunter_cli.py capabilities
        """
    )

    # 顶级子命令
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # 'find' 子命令，用于查找潜在项目
    find_parser = subparsers.add_parser("find", help="查找潜在空投的Web3项目")
    find_parser.add_argument("--token", type=str, required=True, help="GitHub API令牌")
    find_parser.add_argument("--days", type=int, default=30, help="最近活动天数 (默认30)")
    find_parser.add_argument("--min-stars", type=int, default=100, help="最小星星数 (默认100)")
    find_parser.add_argument("--limit", type=int, default=50, help="返回结果数量限制 (默认50)")
    find_parser.add_argument("--format", type=str, choices=["csv", "excel", "json"], default="csv", help="输出格式 (默认csv)")

    # 'scan' 子命令，用于扫描单个项目
    scan_parser = subparsers.add_parser("scan", help="扫描单个项目的拼写错误")
    scan_parser.add_argument("--token", type=str, required=True, help="GitHub API令牌")
    scan_parser.add_argument("--repo", type=str, required=True, help="仓库完整名称 (owner/repo)")
    scan_parser.add_argument("--create-pr", action="store_true", help="创建PR")

    # 'process' 子命令，用于批量处理项目
    process_parser = subparsers.add_parser("process", help="批量处理Web3项目")
    process_parser.add_argument("--token", type=str, required=True, help="GitHub API令牌")
    process_parser.add_argument("--days", type=int, default=30, help="最近活动天数 (默认30)")
    process_parser.add_argument("--min-stars", type=int, default=100, help="最小星星数 (默认100)")
    process_parser.add_argument("--limit", type=int, default=5, help="处理项目数量限制 (默认5)")
    process_parser.add_argument("--create-pr", action="store_true", help="创建PR")

    # 'llm-check' 子命令，检查 OpenAI 兼容 API
    subparsers.add_parser("llm-check", help="检查 LLM API 连通性和 DecisionAgent 接入")

    # 'capabilities' 子命令，查看能力矩阵
    cap_parser = subparsers.add_parser("capabilities", help="查看 Type Agent 当前能力")
    cap_parser.add_argument("--token", type=str, required=False, help="可选 GitHub Token，用于后续联网能力验证")

    # 'translate' 子命令 - 翻译文档
    translate_parser = subparsers.add_parser("translate", help="翻译仓库 README 文档")
    translate_parser.add_argument("--token", type=str, required=True, help="GitHub API令牌")
    translate_parser.add_argument("--repo", type=str, required=True, help="仓库完整名称 (owner/repo)")
    translate_parser.add_argument("--target-lang", type=str, default="zh", help="目标语言代码 (默认: zh)")

    # 'find-issues' 子命令 - 查找 Issues
    find_issues_parser = subparsers.add_parser("find-issues", help="查找仓库中的可贡献 Issues")
    find_issues_parser.add_argument("--token", type=str, required=True, help="GitHub API令牌")
    find_issues_parser.add_argument("--repo", type=str, required=True, help="仓库完整名称 (owner/repo)")
    find_issues_parser.add_argument("--limit", type=int, default=30, help="最大 Issue 数量 (默认: 30)")

    # 'find-contributions' 子命令 - 批量查找贡献机会
    find_contributions_parser = subparsers.add_parser("find-contributions", help="批量查找多个仓库的贡献机会")
    find_contributions_parser.add_argument("--token", type=str, required=True, help="GitHub API令牌")
    find_contributions_parser.add_argument(
        "--repos",
        nargs="+",
        required=True,
        help="仓库列表 (空格分隔，如: owner/repo1 owner/repo2)"
    )
    find_contributions_parser.add_argument("--limit", type=int, default=10, help="每个仓库最大 Issue 数量 (默认: 10)")

    args = parser.parse_args()

    # 如果没有指定命令，显示帮助
    if not args.command:
        parser.print_help()
        sys.exit(1)

    return args


async def run_find_command(args):
    """执行find命令"""
    logger.info("=== 查找潜在空投项目 ===")
    logger.info(f"参数: days={args.days}, min_stars={args.min_stars}, limit={args.limit}")

    coordinator = CoordinatorAgent(github_token=args.token)
    await coordinator.initialize()
    await coordinator.start()

    try:
        result = await coordinator.process_task({
            "type": "run_workflow",
            "workflow": "batch_projects",
            "days": args.days,
            "min_stars": args.min_stars,
            "limit": args.limit,
            "create_pr": False,
        })
        logger.info("发现任务完成")
        logger.info("结果: %s", json.dumps(result, ensure_ascii=False))
        return result
    finally:
        await coordinator.stop()


async def run_scan_command(args):
    """执行scan命令"""
    logger.info("=== 扫描项目 ===")
    logger.info(f"仓库: {args.repo}, 创建PR: {args.create_pr}")

    coordinator = CoordinatorAgent(github_token=args.token)
    await coordinator.initialize()
    await coordinator.start()

    try:
        owner, repo = args.repo.split("/")
        result = await coordinator.process_task({
            "type": "run_workflow",
            "workflow": "single_project",
            "owner": owner,
            "repo": repo,
            "create_pr": args.create_pr,
        })

        logger.info("扫描任务完成")
        logger.info("结果: %s", json.dumps(result, ensure_ascii=False))
        return result
    finally:
        await coordinator.stop()


async def run_process_command(args):
    """执行process命令"""
    logger.info("=== 批量处理项目 ===")
    logger.info(f"参数: days={args.days}, min_stars={args.min_stars}, limit={args.limit}, create_pr={args.create_pr}")

    coordinator = CoordinatorAgent(github_token=args.token)
    await coordinator.initialize()
    await coordinator.start()

    try:
        result = await coordinator.process_task({
            "type": "run_workflow",
            "workflow": "batch_projects",
            "days": args.days,
            "min_stars": args.min_stars,
            "limit": args.limit,
            "create_pr": args.create_pr,
        })

        logger.info("批量处理任务完成")
        logger.info("结果: %s", json.dumps(result, ensure_ascii=False))
        return result
    finally:
        await coordinator.stop()


async def run_llm_check_command():
    """执行 llm-check 命令"""
    logger.info("=== LLM API 连通性检查 ===")

    agent = DecisionAgent()
    await agent.initialize()

    try:
        health_result = await agent.process_task({"type": "llm_health_check"})
        logger.info("LLM健康检查: %s", json.dumps(health_result, ensure_ascii=False))

        if not health_result.get("success"):
            return health_result

        sample_decision = await agent.process_task({
            "type": "recommend_action",
            "context": {
                "project": {"stars": 120, "activity_score": 80},
                "scan_result": {"total_typos": 4},
            },
        })
        logger.info("DecisionAgent 样例决策: %s", json.dumps(sample_decision, ensure_ascii=False))

        return {
            "success": True,
            "health": health_result,
            "sample_decision": sample_decision,
        }
    finally:
        await agent.stop()


async def run_capabilities_command(args):
    """执行 capabilities 命令"""
    logger.info("=== Type Agent 能力矩阵 ===")

    coordinator = CoordinatorAgent(github_token=getattr(args, "token", None))
    await coordinator.initialize()
    try:
        result = await coordinator.process_task({"type": "get_capabilities"})
        logger.info("能力: %s", json.dumps(result, ensure_ascii=False))
        return result
    finally:
        await coordinator.stop()


async def main_async():
    """异步主函数"""
    args = parse_args()

    # 根据命令执行相应操作
    if args.command == "find":
        await run_find_command(args)
    elif args.command == "scan":
        await run_scan_command(args)
    elif args.command == "process":
        await run_process_command(args)
    elif args.command == "llm-check":
        await run_llm_check_command()
    elif args.command == "capabilities":
        await run_capabilities_command(args)
    # New Phase 2 & 3 commands
    elif args.command == "translate":
        await run_translate_command(args)
    elif args.command == "find-issues":
        await run_find_issues_command(args)
    elif args.command == "find-contributions":
        await run_find_contributions_command(args)
    else:
        logger.error(f"未知命令: {args.command}")


def main():
    """主函数"""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("\n操作已中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"执行过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


# ============================================================================
# Phase 2 & 3 New Command Handlers
# ============================================================================

async def run_translate_command(args):
    """执行 translate 命令"""
    logger.info("=== 翻译文档 ===")
    logger.info(f"仓库: {args.repo}, 目标语言: {args.target_lang}")

    coordinator = CoordinatorAgent(github_token=args.token)
    await coordinator.initialize()
    await coordinator.start()

    try:
        result = await coordinator.process_task({
            "type": "translate_document",
            "repo": args.repo,
            "target_lang": args.target_lang
        })

        if result.get("success"):
            logger.info(f"✅ 翻译成功!")
            logger.info(f"目标文件: {result.get('target_filename')}")
            # 保存翻译内容到文件
            output_file = f"{args.repo.replace('/', '_')}_README.{args.target_lang}.md"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(result.get("translated_content", ""))
            logger.info(f"翻译内容已保存到: {output_file}")
        else:
            logger.error(f"❌ 翻译失败: {result.get('error')}")

    finally:
        await coordinator.stop()


async def run_find_issues_command(args):
    """执行 find-issues 命令"""
    logger.info("=== 查找 Issues ===")
    logger.info(f"仓库: {args.repo}, 限制: {args.limit}")

    coordinator = CoordinatorAgent(github_token=args.token)
    await coordinator.initialize()
    await coordinator.start()

    try:
        result = await coordinator.process_task({
            "type": "find_issues",
            "repo": args.repo,
            "limit": args.limit
        })

        if result.get("success"):
            issues = result.get("issues", [])
            logger.info(f"✅ 找到 {len(issues)} 个 Issues")

            # 输出推荐的 Issues
            recommended = [i for i in issues if i.get("recommended")]
            if recommended:
                logger.info(f"\n⭐ 推荐 Issues ({len(recommended)} 个):")
                for issue in recommended[:10]:
                    analysis = issue.get("analysis", {})
                    logger.info(f"  #{issue['issue_number']}: {issue['title']}")
                    logger.info(f"     难度: {analysis.get('difficulty', 'unknown')}, 分数: {issue.get('score', 0)}")
        else:
            logger.error(f"❌ 查找失败: {result.get('error')}")

    finally:
        await coordinator.stop()


async def run_find_contributions_command(args):
    """执行 find-contributions 命令"""
    logger.info("=== 批量查找贡献机会 ===")
    logger.info(f"仓库列表: {', '.join(args.repos)}")

    coordinator = CoordinatorAgent(github_token=args.token)
    await coordinator.initialize()
    await coordinator.start()

    try:
        result = await coordinator.process_task({
            "type": "batch_find_contributions",
            "repos": args.repos,
            "limit": args.limit
        })

        if result.get("success"):
            opportunities = result.get("opportunities", [])
            logger.info(f"✅ 找到 {len(opportunities)} 个贡献机会")

            # 输出前10个机会
            for i, opp in enumerate(opportunities[:10], 1):
                logger.info(f"\n{i}. {opp['repo_name']} - Issue #{opp['issue_number']}")
                logger.info(f"   标题: {opp['issue_title']}")
                logger.info(f"   综合评分: {opp['composite_score']}")
                logger.info(f"   空投潜力: {opp['airdrop_potential']}")
                logger.info(f"   推荐度: {opp['recommendation']}")
        else:
            logger.error(f"❌ 查找失败: {result.get('error')}")

    finally:
        await coordinator.stop()
