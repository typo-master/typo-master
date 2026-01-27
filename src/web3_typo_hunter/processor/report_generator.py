#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告生成模块 - 生成项目分析和修复报告
"""

import os
import json
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..utils.logger import logger
from ..config.settings import RESULTS_DIR


class ReportGenerator:
    """报告生成类"""
    
    def __init__(self, output_dir: str = RESULTS_DIR):
        """
        初始化报告生成器
        
        Args:
            output_dir: 输出目录
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_repo_analysis_report(self, repos_data: pd.DataFrame, 
                                     output_format: str = "csv") -> str:
        """
        生成仓库分析报告
        
        Args:
            repos_data: 仓库数据DataFrame
            output_format: 输出格式 (csv, excel, json)
            
        Returns:
            报告文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(self.output_dir, f"web3_projects_{timestamp}")
        
        logger.info(f"生成仓库分析报告: {output_format} 格式")
        
        if output_format == "csv":
            output_file += ".csv"
            repos_data.to_csv(output_file, index=False)
        elif output_format == "excel":
            output_file += ".xlsx"
            repos_data.to_excel(output_file, index=False)
        elif output_format == "json":
            output_file += ".json"
            repos_data.to_json(output_file, orient="records", indent=2)
        else:
            raise ValueError(f"不支持的输出格式: {output_format}")
        
        logger.info(f"报告已保存至: {output_file}")
        return output_file
    
    def generate_typo_fix_report(self, repos_info: List[Dict[str, Any]]) -> str:
        """
        生成拼写错误修复报告
        
        Args:
            repos_info: 多个仓库的信息列表
            
        Returns:
            报告文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(self.output_dir, f"typo_fixes_{timestamp}.json")
        
        # 准备报告数据
        report_data = self._prepare_fix_report_data(repos_info)
        
        # 写入JSON文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"拼写错误修复报告已保存至: {output_file}")
        
        # 同时生成CSV格式的简要报告
        csv_output_file = os.path.join(self.output_dir, f"typo_fixes_{timestamp}.csv")
        self._generate_fix_summary_csv(report_data, csv_output_file)
        
        return output_file
    
    def _prepare_fix_report_data(self, repos_info: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        准备修复报告数据
        
        Args:
            repos_info: 多个仓库的信息列表
            
        Returns:
            结构化的报告数据
        """
        total_scanned = len(repos_info)
        total_with_typos = sum(1 for repo in repos_info if repo.get("typos_count", 0) > 0)
        total_with_fixes = sum(1 for repo in repos_info if repo.get("fixed_files_count", 0) > 0)
        total_with_pr = sum(1 for repo in repos_info if repo.get("pr_created", False))
        
        report = {
            "summary": {
                "timestamp": datetime.now().isoformat(),
                "total_repos_scanned": total_scanned,
                "repos_with_typos_found": total_with_typos,
                "repos_with_fixes_applied": total_with_fixes,
                "repos_with_pr_created": total_with_pr
            },
            "repositories": []
        }
        
        # 添加每个仓库的详细信息
        for repo in repos_info:
            repo_details = {
                "name": repo.get("name", ""),
                "full_name": repo.get("full_name", ""),
                "url": repo.get("url", ""),
                "stars": repo.get("stars", 0),
                "scanning": {
                    "typos_found": repo.get("typos_count", 0),
                    "confirmed_typos": repo.get("confirmed_typos_count", 0)
                },
                "fixing": {
                    "files_fixed": repo.get("fixed_files_count", 0),
                    "files_list": repo.get("fixed_files", [])
                },
                "pr": {
                    "created": repo.get("pr_created", False),
                    "url": repo.get("pr_url", ""),
                    "error": repo.get("pr_error", "")
                }
            }
            
            report["repositories"].append(repo_details)
        
        return report
    
    def _generate_fix_summary_csv(self, report_data: Dict[str, Any], output_file: str) -> None:
        """
        生成简要的CSV格式修复摘要
        
        Args:
            report_data: 完整报告数据
            output_file: 输出文件路径
        """
        summary = []
        
        for repo in report_data["repositories"]:
            summary.append({
                "repo_name": repo["full_name"],
                "stars": repo["stars"],
                "typos_found": repo["scanning"]["typos_found"],
                "confirmed_typos": repo["scanning"]["confirmed_typos"],
                "files_fixed": repo["fixing"]["files_fixed"],
                "pr_created": "Yes" if repo["pr"]["created"] else "No",
                "pr_url": repo["pr"]["url"],
                "pr_error": repo["pr"]["error"]
            })
        
        df = pd.DataFrame(summary)
        df.to_csv(output_file, index=False)
        logger.info(f"拼写错误修复摘要已保存至: {output_file}")
    
    def generate_markdown_report(self, repos_info: List[Dict[str, Any]]) -> str:
        """
        生成Markdown格式的报告
        
        Args:
            repos_info: 多个仓库的信息列表
            
        Returns:
            报告文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(self.output_dir, f"typo_fixes_{timestamp}.md")
        
        total_scanned = len(repos_info)
        total_with_typos = sum(1 for repo in repos_info if repo.get("typos_count", 0) > 0)
        total_with_fixes = sum(1 for repo in repos_info if repo.get("fixed_files_count", 0) > 0)
        total_with_pr = sum(1 for repo in repos_info if repo.get("pr_created", False))
        
        # 构建Markdown内容
        md_lines = [
            "# Web3项目拼写错误修复报告",
            f"*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
            "",
            "## 摘要",
            "",
            f"- **扫描仓库总数**: {total_scanned}",
            f"- **发现拼写错误的仓库**: {total_with_typos}",
            f"- **应用修复的仓库**: {total_with_fixes}",
            f"- **成功创建PR的仓库**: {total_with_pr}",
            "",
            "## 详细信息",
            ""
        ]
        
        # 添加每个仓库的详细信息
        for repo in repos_info:
            md_lines.append(f"### {repo.get('full_name', 'Unknown Repo')}")
            md_lines.append(f"- **项目URL**: {repo.get('url', 'N/A')}")
            md_lines.append(f"- **Stars**: {repo.get('stars', 0)}")
            md_lines.append(f"- **发现拼写错误数**: {repo.get('typos_count', 0)}")
            md_lines.append(f"- **确认拼写错误数**: {repo.get('confirmed_typos_count', 0)}")
            md_lines.append(f"- **修复文件数**: {repo.get('fixed_files_count', 0)}")
            
            if repo.get("fixed_files"):
                md_lines.append("\n**修复的文件**:")
                for file in repo.get("fixed_files", []):
                    md_lines.append(f"- {file}")
            
            md_lines.append("")
            
            if repo.get("pr_created", False):
                md_lines.append(f"**PR URL**: {repo.get('pr_url', 'N/A')}")
            else:
                md_lines.append(f"**PR创建失败**: {repo.get('pr_error', 'Unknown error')}")
            
            md_lines.append("")
        
        # 写入文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(md_lines))
        
        logger.info(f"Markdown报告已保存至: {output_file}")
        return output_file 