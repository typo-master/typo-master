#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PR创建模块 - 负责创建和管理GitHub拉取请求
"""

from typing import Dict, Any, Optional
import os

from ..utils.logger import logger
from ..utils.github_api import GitHubAPI
from ..discovery.repo_manager import RepoManager
from ..scanner.typo_fixer import TypoFixer
from ..config.settings import PR_TEMPLATE


class PRCreator:
    """PR创建类"""
    
    def __init__(self, token: Optional[str] = None):
        """
        初始化PR创建器
        
        Args:
            token: GitHub API令牌
        """
        self.github_api = GitHubAPI(token)
        self.repo_manager = RepoManager()
        self.token = token
    
    def prepare_and_create_pr(self, repo_info: Dict[str, Any], 
                             pr_title: Optional[str] = None,
                             pr_body: Optional[str] = None) -> Dict[str, Any]:
        """
        准备并创建PR
        
        Args:
            repo_info: 仓库信息，包含fixed_files等
            pr_title: PR标题（可选）
            pr_body: PR正文（可选）
            
        Returns:
            带有PR信息的仓库信息
        """
        if not repo_info.get("fixed_files"):
            logger.warning(f"仓库 {repo_info.get('name', 'unknown')} 没有修复的文件，跳过PR创建")
            repo_info["pr_created"] = False
            repo_info["pr_error"] = "没有修复的文件"
            return repo_info
        
        if not self.token:
            logger.error("缺少GitHub Token，无法创建PR")
            repo_info["pr_created"] = False
            repo_info["pr_error"] = "缺少GitHub Token"
            return repo_info
        
        # 准备分支
        try:
            if not repo_info.get("branch_name"):
                repo_info = self.repo_manager.create_branch(repo_info)
            
            # 提交更改
            commit_message = self._generate_commit_message(repo_info)
            repo_info = self.repo_manager.commit_changes(repo_info, commit_message)
            
            # 推送更改
            repo_info = self.repo_manager.push_changes(repo_info)
            
            if not repo_info.get("pushed", False):
                logger.error(f"推送更改失败: {repo_info.get('push_error', '未知错误')}")
                repo_info["pr_created"] = False
                repo_info["pr_error"] = f"推送更改失败: {repo_info.get('push_error', '未知错误')}"
                return repo_info
            
            # 创建PR
            return self._create_pull_request(repo_info, pr_title, pr_body)
            
        except Exception as e:
            logger.error(f"准备和创建PR时出错: {str(e)}")
            repo_info["pr_created"] = False
            repo_info["pr_error"] = f"准备和创建PR时出错: {str(e)}"
            return repo_info
    
    def _create_pull_request(self, repo_info: Dict[str, Any],
                            pr_title: Optional[str] = None,
                            pr_body: Optional[str] = None) -> Dict[str, Any]:
        """
        创建拉取请求
        
        Args:
            repo_info: 仓库信息
            pr_title: PR标题
            pr_body: PR正文
            
        Returns:
            包含PR信息的仓库信息
        """
        # 提取仓库所有者和名称
        owner, repo = repo_info["full_name"].split("/")
        branch_name = repo_info["branch_name"]
        
        # 生成PR标题
        if not pr_title:
            fix_summary = TypoFixer().get_fixed_content_summary(repo_info)
            pr_title = f"Fix {fix_summary['total_fixes']} typos in {fix_summary['total_files']} files"
        
        # 生成PR正文
        if not pr_body:
            fix_report = TypoFixer().generate_fix_report(repo_info)
            fixed_files = "\n".join([f"- {f}" for f in repo_info["fixed_files"]])
            pr_body = PR_TEMPLATE.format(fixed_files=fixed_files)
            pr_body += "\n\n" + fix_report
        
        logger.info(f"创建PR: {owner}/{repo} - {pr_title}")
        
        try:
            # 调用GitHub API创建PR
            response = self.github_api.create_pull_request(
                owner=owner,
                repo=repo,
                title=pr_title,
                body=pr_body,
                head=branch_name
            )
            
            # 处理结果
            if response.get("html_url"):
                repo_info["pr_created"] = True
                repo_info["pr_url"] = response["html_url"]
                repo_info["pr_number"] = response["number"]
                logger.info(f"成功创建PR: {response['html_url']}")
            else:
                repo_info["pr_created"] = False
                repo_info["pr_error"] = f"创建PR失败: {response.get('message', '未知错误')}"
                logger.error(f"创建PR失败: {response.get('message', '未知错误')}")
                
            return repo_info
            
        except Exception as e:
            logger.error(f"创建PR时出错: {str(e)}")
            repo_info["pr_created"] = False
            repo_info["pr_error"] = f"创建PR时出错: {str(e)}"
            return repo_info
    
    def _generate_commit_message(self, repo_info: Dict[str, Any]) -> str:
        """
        生成提交信息
        
        Args:
            repo_info: 仓库信息
            
        Returns:
            提交信息
        """
        fix_summary = TypoFixer().get_fixed_content_summary(repo_info)
        
        if fix_summary["total_files"] == 1:
            return f"Fix {fix_summary['total_fixes']} typo(s) in {repo_info['fixed_files'][0]}"
        else:
            return f"Fix {fix_summary['total_fixes']} typo(s) in {fix_summary['total_files']} files" 