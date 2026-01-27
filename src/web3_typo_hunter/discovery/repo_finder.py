#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
仓库发现模块 - 负责从GitHub发现和过滤Web3项目
"""

import time
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from ..utils.logger import logger
from ..utils.github_api import GitHubAPI
from ..config.settings import WEB3_TOPICS, DEFAULT_SEARCH_PARAMS


class RepoFinder:
    """Web3仓库发现类"""
    
    def __init__(self, token: Optional[str] = None):
        """
        初始化仓库发现器
        
        Args:
            token: GitHub API令牌
        """
        self.github_api = GitHubAPI(token)
        self.token = token
        
    def search_web3_repos(self, days: int = None, min_stars: int = None, 
                         limit: int = None) -> List[Dict]:
        """
        搜索Web3相关仓库
        
        Args:
            days: 最近多少天内有更新的项目
            min_stars: 最小星星数
            limit: 返回结果数量限制
            
        Returns:
            符合条件的仓库列表
        """
        # 使用默认参数或者传入参数
        days = days if days is not None else DEFAULT_SEARCH_PARAMS["days"]
        min_stars = min_stars if min_stars is not None else DEFAULT_SEARCH_PARAMS["min_stars"]
        limit = limit if limit is not None else DEFAULT_SEARCH_PARAMS["limit"]
        
        logger.info(f"开始搜索最近{days}天内更新的Web3项目，星星数大于{min_stars}...")
        
        date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        all_repos = []
        
        for topic in WEB3_TOPICS:
            # 构建查询语句
            query = f"topic:{topic} pushed:>={date_from} stars:>={min_stars}"
            
            logger.info(f"搜索主题: {topic}")
            
            try:
                result = self.github_api.search_repositories(
                    query=query,
                    sort="updated",
                    order="desc",
                    per_page=min(100, limit)
                )
                
                repos = result.get("items", [])
                all_repos.extend(repos)
                logger.info(f"找到 {len(repos)} 个符合条件的 {topic} 项目")
                
                # 避免API速率限制
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"搜索 {topic} 项目时出错: {str(e)}")
        
        # 删除重复项
        unique_repos = {}
        for repo in all_repos:
            if repo["id"] not in unique_repos:
                unique_repos[repo["id"]] = repo
        
        # 排序（按更新时间和星星数）
        sorted_repos = sorted(
            unique_repos.values(), 
            key=lambda x: (datetime.strptime(x["pushed_at"], "%Y-%m-%dT%H:%M:%SZ"), x["stargazers_count"]),
            reverse=True
        )
        
        result_repos = sorted_repos[:limit]
        logger.info(f"总共找到 {len(result_repos)} 个符合条件的Web3项目")
        
        return result_repos
    
    def analyze_repo_contribution(self, repo_info: Dict) -> Dict:
        """
        分析仓库的贡献活跃度
        
        Args:
            repo_info: 仓库信息
            
        Returns:
            带有活跃度信息的仓库信息
        """
        owner, repo = repo_info["full_name"].split("/")
        logger.info(f"分析项目贡献情况: {repo_info['full_name']}")
        
        try:
            prs = self.github_api.get_pull_requests(
                owner=owner,
                repo=repo,
                state="closed",
                sort="updated",
                direction="desc",
                per_page=30
            )
            
            # 计算最近合并的PR数量
            recent_merged_prs = sum(1 for pr in prs if pr.get("merged_at") and 
                               datetime.strptime(pr["merged_at"], "%Y-%m-%dT%H:%M:%SZ") > 
                               datetime.now() - timedelta(days=30))
            
            # 计算PR接受率
            if prs:
                merged_prs = sum(1 for pr in prs if pr.get("merged_at"))
                acceptance_rate = merged_prs / len(prs)
            else:
                acceptance_rate = 0
            
            # 添加PR活动信息
            repo_info.update({
                "recent_prs": len(prs),
                "recent_merged_prs": recent_merged_prs,
                "pr_acceptance_rate": acceptance_rate,
                "airdrop_potential_score": self._calculate_airdrop_potential(repo_info, {
                    "recent_prs": len(prs),
                    "recent_merged_prs": recent_merged_prs,
                    "acceptance_rate": acceptance_rate
                })
            })
            
        except Exception as e:
            logger.error(f"分析项目 {repo_info['full_name']} 贡献情况时出错: {str(e)}")
            repo_info.update({
                "recent_prs": 0,
                "recent_merged_prs": 0,
                "pr_acceptance_rate": 0,
                "airdrop_potential_score": 0
            })
        
        return repo_info
    
    def find_potential_airdrop_projects(self, days: int = None, min_stars: int = None, 
                                       limit: int = None) -> pd.DataFrame:
        """
        寻找潜在空投机会的项目
        
        Args:
            days: 最近活动天数
            min_stars: 最小星星数
            limit: 返回结果数量限制
            
        Returns:
            DataFrame形式的项目列表
        """
        # 搜索仓库
        repos = self.search_web3_repos(days, min_stars, limit)
        
        results = []
        for i, repo in enumerate(repos):
            logger.info(f"[{i+1}/{len(repos)}] 分析项目: {repo['full_name']}")
            
            try:
                # 分析贡献活跃度
                repo_data = self.analyze_repo_contribution(repo)
                
                # 提取关键信息
                result = {
                    "name": repo_data["name"],
                    "full_name": repo_data["full_name"],
                    "url": repo_data["html_url"],
                    "clone_url": repo_data["clone_url"],
                    "description": repo_data["description"],
                    "stars": repo_data["stargazers_count"],
                    "forks": repo_data["forks_count"],
                    "language": repo_data["language"],
                    "last_updated": repo_data["pushed_at"],
                    "topics": ", ".join(repo_data.get("topics", [])),
                    "recent_prs": repo_data["recent_prs"],
                    "recent_merged_prs": repo_data["recent_merged_prs"],
                    "pr_acceptance_rate": f"{repo_data['pr_acceptance_rate']:.2%}",
                    "airdrop_potential_score": repo_data["airdrop_potential_score"]
                }
                
                results.append(result)
                
                # 避免API速率限制
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"分析项目 {repo['full_name']} 时出错: {str(e)}")
                continue
        
        # 根据空投潜力评分排序
        results.sort(key=lambda x: x["airdrop_potential_score"], reverse=True)
        
        return pd.DataFrame(results)
        
    def _calculate_airdrop_potential(self, repo_info: Dict, pr_activity: Dict) -> float:
        """
        计算项目可能进行空投的潜力评分
        
        Args:
            repo_info: 仓库信息
            pr_activity: PR活动信息
            
        Returns:
            潜力评分（0-100）
        """
        # 1. 项目活跃度（占比30%）
        pushed_date = datetime.strptime(repo_info["pushed_at"], "%Y-%m-%dT%H:%M:%SZ")
        days_since_update = (datetime.now() - pushed_date).days
        activity_score = max(0, 30 - (days_since_update / 2))  # 两周内更新得满分
        
        # 2. 社区规模（占比20%）
        community_score = min(20, repo_info["stargazers_count"] / 1000 * 10 + repo_info["forks_count"] / 500 * 10)
        
        # 3. PR接受度（占比30%）
        pr_score = min(30, pr_activity["recent_merged_prs"] * 3 + pr_activity["acceptance_rate"] * 15)
        
        # 4. Web3相关度（占比20%）
        web3_keywords = ["token", "blockchain", "web3", "ethereum", "solidity", "defi", "nft", "dao", "crypto"]
        
        description = (repo_info.get("description") or "").lower()
        topics = repo_info.get("topics", [])
        
        keyword_matches = sum(1 for keyword in web3_keywords if keyword in description.lower() or keyword in [t.lower() for t in topics])
        relevance_score = min(20, keyword_matches * 5)
        
        # 总分
        total_score = activity_score + community_score + pr_score + relevance_score
        
        return round(total_score, 1) 