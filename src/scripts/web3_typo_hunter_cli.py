#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
命令行入口脚本 - 提供命令行界面操作Web3TypoHunter
"""

import argparse
import sys
from src.web3_typo_hunter.controller import Web3TypoHunterController
from src.web3_typo_hunter.utils.logger import logger


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="Web3TypoHunter - 查找Web3项目中的拼写错误并提交PR"
    )
    
    # 顶级子命令
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    # 'find' 子命令，用于查找潜在项目
    find_parser = subparsers.add_parser("find", help="查找潜在空投的Web3项目")
    find_parser.add_argument("--token", type=str, help="GitHub API令牌")
    find_parser.add_argument("--days", type=int, default=30, help="最近活动天数")
    find_parser.add_argument("--min-stars", type=int, default=100, help="最小星星数")
    find_parser.add_argument("--limit", type=int, default=50, help="返回结果数量限制")
    find_parser.add_argument("--format", type=str, choices=["csv", "excel", "json"], default="csv", help="输出格式")
    
    # 'scan' 子命令，用于扫描单个项目
    scan_parser = subparsers.add_parser("scan", help="扫描单个项目的拼写错误")
    scan_parser.add_argument("--token", type=str, help="GitHub API令牌")
    scan_parser.add_argument("--repo", type=str, required=True, help="仓库完整名称 (owner/repo)")
    scan_parser.add_argument("--create-pr", action="store_true", help="创建PR")
    
    # 'process' 子命令，用于批量处理项目
    process_parser = subparsers.add_parser("process", help="批量处理Web3项目")
    process_parser.add_argument("--token", type=str, help="GitHub API令牌")
    process_parser.add_argument("--days", type=int, default=30, help="最近活动天数")
    process_parser.add_argument("--min-stars", type=int, default=100, help="最小星星数")
    process_parser.add_argument("--limit", type=int, default=5, help="处理项目数量限制")
    process_parser.add_argument("--create-pr", action="store_true", help="创建PR")
    
    args = parser.parse_args()
    
    # 如果没有指定命令，显示帮助
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    return args


def main():
    """主函数"""
    args = parse_args()
    
    # 根据命令执行相应操作
    if args.command == "find":
        controller = Web3TypoHunterController(args.token)
        report_path = controller.find_potential_projects(
            days=args.days,
            min_stars=args.min_stars,
            limit=args.limit,
            output_format=args.format
        )
        logger.info(f"报告已保存至: {report_path}")
        
    elif args.command == "scan":
        controller = Web3TypoHunterController(args.token)
        owner, repo = args.repo.split("/")
        repo_info = {
            "full_name": args.repo,
            "name": repo,
            "clone_url": f"https://github.com/{args.repo}.git",
            "url": f"https://github.com/{args.repo}"
        }
        result = controller.scan_and_fix_project(repo_info, args.create_pr)
        if result.get("pr_created"):
            logger.info(f"成功创建PR: {result.get('pr_url')}")
        
    elif args.command == "process":
        controller = Web3TypoHunterController(args.token)
        report_path = controller.process_batch_projects(
            days=args.days,
            min_stars=args.min_stars,
            limit=args.limit,
            create_pr=args.create_pr
        )
        logger.info(f"报告已保存至: {report_path}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n操作已中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"执行过程中出错: {str(e)}")
        sys.exit(1) 