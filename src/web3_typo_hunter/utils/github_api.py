#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub API工具模块 - 封装GitHub API相关操作
"""

import time
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from ..config.settings import GITHUB_API_BASE_URL, GITHUB_API_HEADERS


class GitHubAPI:
    """GitHub API操作封装类"""

    def __init__(self, token: Optional[str] = None):
        """
        初始化GitHub API工具
        
        Args:
            token: GitHub API令牌
        """
        self.headers = GITHUB_API_HEADERS.copy()
        if token:
            self.headers["Authorization"] = f"token {token}"
            
    def search_repositories(self, query: str, sort: str = "updated", order: str = "desc", 
                           per_page: int = 100, page: int = 1) -> Dict:
        """
        搜索GitHub仓库
        
        Args:
            query: 搜索查询字符串
            sort: 排序字段
            order: 排序顺序
            per_page: 每页结果数
            page: 页码
            
        Returns:
            API响应
        """
        url = f"{GITHUB_API_BASE_URL}/search/repositories"
        params = {
            "q": query,
            "sort": sort,
            "order": order,
            "per_page": per_page,
            "page": page
        }
        
        return self._make_request("GET", url, params=params)
    
    def get_repository(self, owner: str, repo: str) -> Dict:
        """
        获取仓库信息
        
        Args:
            owner: 仓库所有者
            repo: 仓库名称
            
        Returns:
            仓库信息
        """
        url = f"{GITHUB_API_BASE_URL}/repos/{owner}/{repo}"
        return self._make_request("GET", url)
    
    def get_pull_requests(self, owner: str, repo: str, state: str = "all", 
                         sort: str = "updated", direction: str = "desc", 
                         per_page: int = 30, page: int = 1) -> List:
        """
        获取仓库的PR列表
        
        Args:
            owner: 仓库所有者
            repo: 仓库名称
            state: PR状态 (open, closed, all)
            sort: 排序字段
            direction: 排序方向
            per_page: 每页结果数
            page: 页码
            
        Returns:
            PR列表
        """
        url = f"{GITHUB_API_BASE_URL}/repos/{owner}/{repo}/pulls"
        params = {
            "state": state,
            "sort": sort,
            "direction": direction,
            "per_page": per_page,
            "page": page
        }
        
        return self._make_request("GET", url, params=params)
    
    def create_pull_request(self, owner: str, repo: str, title: str, body: str, 
                          head: str, base: str = "main") -> Dict:
        """
        创建PR
        
        Args:
            owner: 仓库所有者
            repo: 仓库名称
            title: PR标题
            body: PR正文
            head: 来源分支
            base: 目标分支
            
        Returns:
            创建结果
        """
        url = f"{GITHUB_API_BASE_URL}/repos/{owner}/{repo}/pulls"
        data = {
            "title": title,
            "body": body,
            "head": head,
            "base": base
        }
        
        result = self._make_request("POST", url, json=data)
        
        # 如果失败，尝试使用master作为基础分支
        if isinstance(result, Dict) and result.get("message") and "base" in result.get("message", "").lower():
            data["base"] = "master"
            result = self._make_request("POST", url, json=data)
            
        return result
    
    def _make_request(self, method: str, url: str, params: Dict = None, 
                     json: Dict = None, retry_count: int = 3) -> Any:
        """
        发送请求到GitHub API
        
        Args:
            method: HTTP方法
            url: 请求URL
            params: URL参数
            json: JSON请求体
            retry_count: 重试次数
            
        Returns:
            API响应
        """
        for attempt in range(retry_count):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    params=params,
                    json=json
                )
                
                # 处理API速率限制
                if response.status_code == 403 and "rate limit" in response.text.lower():
                    reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
                    if reset_time:
                        wait_time = max(reset_time - int(time.time()), 0) + 1
                        print(f"API速率限制，等待 {wait_time} 秒后重试...")
                        time.sleep(wait_time)
                        continue
                    else:
                        wait_time = 60 * (attempt + 1)  # 指数退避
                        print(f"API速率限制，等待 {wait_time} 秒后重试...")
                        time.sleep(wait_time)
                        continue
                
                # 成功返回JSON响应
                if 200 <= response.status_code < 300:
                    return response.json() if response.text else {}
                
                # 处理错误
                print(f"API请求失败: {response.status_code} - {response.text}")
                if attempt < retry_count - 1:
                    time.sleep(2 * (attempt + 1))  # 指数退避
                
            except Exception as e:
                print(f"API请求异常: {str(e)}")
                if attempt < retry_count - 1:
                    time.sleep(2 * (attempt + 1))
        
        # 所有重试都失败
        return {"error": "请求失败，已达到最大重试次数"} 