#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
仓库管理模块 - 负责克隆、更新和管理本地仓库
"""

import os
import shutil
from typing import Dict, Any, List, Optional
from git import Repo, GitCommandError
import time

from ..utils.logger import logger
from ..config.settings import REPOS_DIR


class RepoManager:
    """仓库管理类"""
    
    def __init__(self, base_path: str = REPOS_DIR):
        """
        初始化仓库管理器
        
        Args:
            base_path: 仓库存储的基础路径
        """
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)
        
    def clone_repo(self, repo_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        克隆仓库到本地
        
        Args:
            repo_info: 仓库信息，包含clone_url和name
            
        Returns:
            更新后的仓库信息，包含本地路径
        """
        repo_url = repo_info["clone_url"]
        repo_name = repo_info["name"]
        local_path = os.path.join(self.base_path, repo_name)
        
        logger.info(f"处理仓库: {repo_name}")
        
        if os.path.exists(local_path):
            logger.info(f"仓库 {repo_name} 已存在，尝试更新...")
            try:
                repo = Repo(local_path)
                origin = repo.remotes.origin
                origin.pull()
                logger.info(f"已更新仓库 {repo_name}")
            except GitCommandError as e:
                logger.error(f"更新仓库 {repo_name} 失败: {str(e)}")
                # 如果更新失败，删除后重新克隆
                shutil.rmtree(local_path, ignore_errors=True)
                logger.info(f"删除失败仓库，重新克隆: {repo_name}")
                Repo.clone_from(repo_url, local_path)
        else:
            logger.info(f"克隆仓库 {repo_name} 到 {local_path}")
            Repo.clone_from(repo_url, local_path)
        
        # 更新仓库信息
        repo_info["local_path"] = local_path
        return repo_info
    
    def create_branch(self, repo_info: Dict[str, Any], branch_name: Optional[str] = None) -> Dict[str, Any]:
        """
        在仓库中创建新分支
        
        Args:
            repo_info: 仓库信息，包含local_path
            branch_name: 分支名称，如果为None则自动生成
            
        Returns:
            更新后的仓库信息，包含分支名称
        """
        if not branch_name:
            branch_name = f"fix-typos-{int(time.time())}"
            
        local_path = repo_info["local_path"]
        logger.info(f"在仓库 {os.path.basename(local_path)} 中创建分支: {branch_name}")
        
        try:
            repo = Repo(local_path)
            
            # 确保在主分支上
            try:
                repo.git.checkout("main")
            except GitCommandError:
                # 如果main不存在，尝试master
                repo.git.checkout("master")
                
            # 创建并切换到新分支
            current = repo.create_head(branch_name)
            current.checkout()
            
            # 更新仓库信息
            repo_info["branch_name"] = branch_name
            return repo_info
            
        except GitCommandError as e:
            logger.error(f"创建分支失败: {str(e)}")
            raise
    
    def commit_changes(self, repo_info: Dict[str, Any], commit_message: str) -> Dict[str, Any]:
        """
        提交仓库中的更改
        
        Args:
            repo_info: 仓库信息，包含local_path
            commit_message: 提交信息
            
        Returns:
            更新后的仓库信息
        """
        local_path = repo_info["local_path"]
        logger.info(f"提交更改: {os.path.basename(local_path)}")
        
        try:
            repo = Repo(local_path)
            
            # 检查是否有更改
            if not repo.is_dirty():
                logger.warning("没有发现更改，跳过提交")
                return repo_info
            
            # 添加并提交更改
            repo.git.add(update=True)
            repo.index.commit(commit_message)
            
            # 更新仓库信息
            repo_info["commit_message"] = commit_message
            return repo_info
            
        except GitCommandError as e:
            logger.error(f"提交更改失败: {str(e)}")
            raise
    
    def push_changes(self, repo_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        推送更改到远程仓库
        
        Args:
            repo_info: 仓库信息，包含local_path和branch_name
            
        Returns:
            更新后的仓库信息
        """
        local_path = repo_info["local_path"]
        branch_name = repo_info["branch_name"]
        logger.info(f"推送分支 {branch_name} 到远程仓库")
        
        try:
            repo = Repo(local_path)
            origin = repo.remote("origin")
            
            # 推送到远程分支
            origin.push(refspec=f"{branch_name}:{branch_name}")
            
            # 更新仓库信息
            repo_info["pushed"] = True
            return repo_info
            
        except GitCommandError as e:
            logger.error(f"推送更改失败: {str(e)}")
            repo_info["pushed"] = False
            repo_info["push_error"] = str(e)
            return repo_info
    
    def clean_repo(self, repo_info: Dict[str, Any]) -> bool:
        """
        清理仓库，删除本地克隆
        
        Args:
            repo_info: 仓库信息，包含local_path
            
        Returns:
            是否成功清理
        """
        local_path = repo_info["local_path"]
        
        if not os.path.exists(local_path):
            return True
        
        try:
            logger.info(f"清理仓库: {os.path.basename(local_path)}")
            shutil.rmtree(local_path)
            return True
        except Exception as e:
            logger.error(f"清理仓库失败: {str(e)}")
            return False
    
    def batch_clone_repos(self, repos_info: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量克隆多个仓库
        
        Args:
            repos_info: 仓库信息列表
            
        Returns:
            更新后的仓库信息列表
        """
        logger.info(f"批量克隆 {len(repos_info)} 个仓库")
        
        results = []
        for repo_info in repos_info:
            try:
                result = self.clone_repo(repo_info)
                results.append(result)
            except Exception as e:
                logger.error(f"克隆仓库 {repo_info.get('name', 'unknown')} 失败: {str(e)}")
                repo_info["clone_error"] = str(e)
                results.append(repo_info)
        
        return results 