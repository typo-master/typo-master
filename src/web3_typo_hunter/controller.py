#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
控制器模块 - 集成所有功能并提供高层接口
"""

from typing import Dict, List, Any, Optional
import pandas as pd

from .utils.logger import logger
from .discovery.repo_finder import RepoFinder
from .discovery.repo_manager import RepoManager
from .scanner.typo_scanner import TypoScanner
from .scanner.typo_fixer import TypoFixer
from .processor.pr_creator import PRCreator
from .processor.report_generator import ReportGenerator


class Web3TypoHunterController:
    """Web3拼写错误猎手控制器"""
    
    def __init__(self, github_token: Optional[str] = None):
        """
        初始化控制器
        
        Args:
            github_token: GitHub API令牌
        """
        self.github_token = github_token
        self.repo_finder = RepoFinder(github_token)
        self.repo_manager = RepoManager()
        self.typo_scanner = TypoScanner()
        self.typo_fixer = TypoFixer()
        self.pr_creator = PRCreator(github_token)
        self.report_generator = ReportGenerator()
    
    def find_potential_projects(self, days: int = None, min_stars: int = None, 
                               limit: int = None, output_format: str = "csv") -> str:
        """
        查找潜在空投项目并生成报告
        
        Args:
            days: 最近活动天数
            min_stars: 最小星星数
            limit: 返回结果数量限制
            output_format: 输出格式 (csv, excel, json)
            
        Returns:
            报告文件路径
        """
        logger.info("开始查找潜在空投项目")
        
        # 查找项目
        repos_data = self.repo_finder.find_potential_airdrop_projects(days, min_stars, limit)
        
        # 生成报告
        report_path = self.report_generator.generate_repo_analysis_report(repos_data, output_format)
        
        # 打印前10个结果
        logger.info("\n可能有空投的Top 10项目：")
        logger.info(repos_data[["full_name", "stars", "airdrop_potential_score", 
                           "recent_merged_prs", "pr_acceptance_rate"]].head(10))
        
        return report_path
    
    def scan_and_fix_project(self, repo_info: Dict[str, Any], create_pr: bool = True) -> Dict[str, Any]:
        """
        扫描并修复单个项目的拼写错误
        
        Args:
            repo_info: 仓库信息，包含url和name
            create_pr: 是否创建PR
            
        Returns:
            处理后的仓库信息
        """
        repo_name = repo_info.get('name', 'unknown')
        logger.info(f"开始处理仓库: {repo_name}")
        
        try:
            # 1. 克隆仓库
            repo_info = self.repo_manager.clone_repo(repo_info)
            
            # 2. 扫描拼写错误
            repo_info = self.typo_scanner.scan_repo(repo_info)
            logger.info(f"发现 {repo_info.get('typos_count', 0)} 个潜在拼写错误")
            
            if repo_info.get('typos_count', 0) == 0:
                logger.info(f"仓库 {repo_name} 没有发现拼写错误，跳过")
                return repo_info
            
            # 3. 确认拼写错误
            repo_info = self.typo_scanner.confirm_typos(repo_info)
            logger.info(f"确认了 {repo_info.get('confirmed_typos_count', 0)} 个拼写错误")
            
            if repo_info.get('confirmed_typos_count', 0) == 0:
                logger.info(f"仓库 {repo_name} 没有确认的拼写错误，跳过")
                return repo_info
            
            # 4. 修复拼写错误
            repo_info = self.typo_fixer.fix_typos(repo_info)
            logger.info(f"修复了 {repo_info.get('fixed_files_count', 0)} 个文件中的拼写错误")
            
            if repo_info.get('fixed_files_count', 0) == 0:
                logger.info(f"仓库 {repo_name} 没有修复的文件，跳过")
                return repo_info
            
            # 5. 创建PR（如果需要）
            if create_pr and self.github_token:
                repo_info = self.pr_creator.prepare_and_create_pr(repo_info)
                if repo_info.get('pr_created'):
                    logger.info(f"成功创建PR: {repo_info.get('pr_url')}")
                else:
                    logger.error(f"创建PR失败: {repo_info.get('pr_error', '未知错误')}")
            
            return repo_info
            
        except Exception as e:
            logger.error(f"处理仓库 {repo_name} 时出错: {str(e)}")
            repo_info["process_error"] = str(e)
            return repo_info
    
    def process_batch_projects(self, days: int = None, min_stars: int = None, 
                              limit: int = None, create_pr: bool = True) -> str:
        """
        批量处理Web3项目，查找并修复拼写错误
        
        Args:
            days: 最近活动天数
            min_stars: 最小星星数
            limit: 返回结果数量限制
            create_pr: 是否创建PR
            
        Returns:
            报告文件路径
        """
        logger.info("开始批量处理Web3项目")
        
        # 1. 查找潜在项目
        repos_data = self.repo_finder.find_potential_airdrop_projects(days, min_stars, limit)
        repos_list = repos_data.to_dict('records')
        
        logger.info(f"找到 {len(repos_list)} 个潜在的Web3项目")
        
        # 2. 逐个处理项目
        results = []
        for i, repo in enumerate(repos_list):
            logger.info(f"[{i+1}/{len(repos_list)}] 处理项目: {repo.get('full_name')}")
            
            try:
                result = self.scan_and_fix_project(repo, create_pr)
                results.append(result)
            except Exception as e:
                logger.error(f"处理项目出错: {str(e)}")
                repo["process_error"] = str(e)
                results.append(repo)
        
        # 3. 生成报告
        logger.info("生成处理报告")
        report_path = self.report_generator.generate_typo_fix_report(results)
        md_report_path = self.report_generator.generate_markdown_report(results)
        
        # 4. 打印摘要
        self._print_processing_summary(results)
        
        return report_path
    
    def _print_processing_summary(self, results: List[Dict[str, Any]]) -> None:
        """
        打印处理摘要
        
        Args:
            results: 处理结果列表
        """
        total = len(results)
        with_typos = sum(1 for r in results if r.get('typos_count', 0) > 0)
        with_fixes = sum(1 for r in results if r.get('fixed_files_count', 0) > 0)
        with_pr = sum(1 for r in results if r.get('pr_created', False))
        
        logger.info("\n============ 处理摘要 ============")
        logger.info(f"总共处理项目数: {total}")
        logger.info(f"发现拼写错误的项目数: {with_typos}")
        logger.info(f"成功修复的项目数: {with_fixes}")
        logger.info(f"成功创建PR的项目数: {with_pr}")
        
        if with_pr > 0:
            logger.info("\n成功创建PR的项目:")
            for result in results:
                if result.get('pr_created', False):
                    logger.info(f"- {result.get('full_name')}: {result.get('pr_url')}")
        
        logger.info("===================================") 