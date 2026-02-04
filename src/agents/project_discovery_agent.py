"""
Project Discovery Agent - Discovers Web3 projects with airdrop potential

This agent is responsible for discovering and analyzing Web3 projects
from GitHub to identify those with high airdrop potential.
"""

import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from ..agent_framework.base_agent import BaseAgent, AgentConfig, AgentState
from ..agent_framework.tool_system import ToolRegistry
from ..agent_framework.logger import get_logger

logger = get_logger(__name__)


class ProjectDiscoveryAgent(BaseAgent):
    """
    Agent for discovering Web3 projects with airdrop potential
    
    Responsibilities:
    - Search GitHub for Web3 projects
    - Analyze project metadata
    - Evaluate airdrop potential
    - Rank projects by priority
    """
    
    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize project discovery agent
        
        Args:
            github_token: GitHub API token
        """
        config = AgentConfig(
            name="ProjectDiscoveryAgent",
            version="1.0.0",
            description="Discovers Web3 projects with airdrop potential",
            max_retries=3,
            timeout=300.0,
        )
        
        super().__init__(config)
        self.github_token = github_token
        
        # Web3 topics to search
        self.web3_topics = [
            "blockchain", "ethereum", "web3", "defi", "nft", "dao",
            "smart-contracts", "solidity", "crypto", "dapp", "wallet",
        ]
    
    async def on_initialize(self) -> None:
        """Initialize agent and register tools"""
        # Import and register GitHub tools
        from ..tools.github_tools import (
            search_github_repos,
            get_github_repo,
            list_pull_requests,
        )
        
        self.tool_registry.register(search_github_repos)
        self.tool_registry.register(get_github_repo)
        self.tool_registry.register(list_pull_requests)
        
        logger.info("Project discovery agent initialized")
    
    async def on_start(self) -> None:
        """Called when agent starts"""
        logger.info("Project discovery agent started")
    
    async def on_stop(self) -> None:
        """Called when agent stops"""
        logger.info("Project discovery agent stopped")
    
    async def on_pause(self) -> None:
        """Called when agent is paused"""
        logger.info("Project discovery agent paused")
    
    async def on_resume(self) -> None:
        """Called when agent resumes"""
        logger.info("Project discovery agent resumed")
    
    async def process_task(self, task: Any) -> Any:
        """
        Process a discovery task
        
        Args:
            task: Task to process
            
        Returns:
            Task result
        """
        task_type = task.get("type")
        
        if task_type == "search_projects":
            return await self._search_projects(task)
        elif task_type == "analyze_project":
            return await self._analyze_project(task)
        elif task_type == "evaluate_potential":
            return await self._evaluate_potential(task)
        else:
            logger.warning(f"Unknown task type: {task_type}")
            return {"error": f"Unknown task type: {task_type}"}
    
    async def _search_projects(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search for Web3 projects
        
        Args:
            task: Task parameters
            
        Returns:
            Search results
        """
        days = task.get("days", 30)
        min_stars = task.get("min_stars", 100)
        limit = task.get("limit", 50)
        
        logger.info(f"Searching for Web3 projects (days={days}, stars>={min_stars}, limit={limit})")
        
        # Build search query
        date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        all_repos = []
        
        # Search for each topic
        for topic in self.web3_topics:
            query = f"topic:{topic} pushed:>={date_from} stars:>={min_stars}"
            
            try:
                repos = await self.tool_registry.invoke(
                    "search_github_repos",
                    query=query,
                    limit=limit,
                    token=self.github_token,
                )
                
                if repos.get("success"):
                    all_repos.extend(repos["data"])
                
                # Avoid rate limiting
                await asyncio.sleep(2)
            
            except Exception as e:
                logger.error(f"Error searching for {topic}: {e}")
        
        # Remove duplicates
        unique_repos = {}
        for repo in all_repos:
            repo_id = repo.get("id")
            if repo_id and repo_id not in unique_repos:
                unique_repos[repo_id] = repo
        
        # Sort by stars and update time
        sorted_repos = sorted(
            unique_repos.values(),
            key=lambda x: (x.get("stargazers_count", 0), x.get("pushed_at", "")),
            reverse=True,
        )
        
        result_repos = sorted_repos[:limit]
        
        logger.info(f"Found {len(result_repos)} Web3 projects")
        
        return {
            "repos": result_repos,
            "count": len(result_repos),
            "search_params": {
                "days": days,
                "min_stars": min_stars,
                "limit": limit,
            },
        }
    
    async def _analyze_project(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a single project
        
        Args:
            task: Task parameters
            
        Returns:
            Project analysis
        """
        owner = task.get("owner")
        repo = task.get("repo")
        
        logger.info(f"Analyzing project: {owner}/{repo}")
        
        # Get repository details
        repo_result = await self.tool_registry.invoke(
            "get_github_repo",
            owner=owner,
            repo=repo,
            token=self.github_token,
        )
        
        if not repo_result.get("success"):
            return {"error": "Failed to get repository details"}
        
        repo_data = repo_result["data"]
        
        # Get recent PRs
        prs_result = await self.tool_registry.invoke(
            "list_pull_requests",
            owner=owner,
            repo=repo,
            state="closed",
            limit=30,
            token=self.github_token,
        )
        
        prs = prs_result.get("data", []) if prs_result.get("success") else []
        
        # Calculate PR acceptance rate
        recent_prs = [pr for pr in prs if pr.get("merged_at")]
        merged_count = len(recent_prs)
        acceptance_rate = merged_count / len(prs) if prs else 0
        
        # Calculate airdrop potential score
        airdrop_score = self._calculate_airdrop_score(repo_data, prs, acceptance_rate)
        
        return {
            "owner": owner,
            "repo": repo,
            "name": repo_data.get("name"),
            "full_name": repo_data.get("full_name"),
            "description": repo_data.get("description"),
            "stars": repo_data.get("stargazers_count"),
            "forks": repo_data.get("forks_count"),
            "language": repo_data.get("language"),
            "updated_at": repo_data.get("updated_at"),
            "recent_prs": merged_count,
            "acceptance_rate": acceptance_rate,
            "airdrop_score": airdrop_score,
        }
    
    async def _evaluate_potential(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate airdrop potential for multiple projects
        
        Args:
            task: Task parameters
            
        Returns:
            Ranked projects
        """
        projects = task.get("projects", [])
        
        logger.info(f"Evaluating potential for {len(projects)} projects")
        
        results = []
        for project in projects:
            try:
                analysis = await self._analyze_project({
                    "owner": project.get("owner"),
                    "repo": project.get("name"),
                })
                results.append(analysis)
            except Exception as e:
                logger.error(f"Error analyzing project: {e}")
        
        # Sort by airdrop score
        ranked_projects = sorted(
            results,
            key=lambda x: x.get("airdrop_score", 0),
            reverse=True,
        )
        
        return {
            "projects": ranked_projects,
            "count": len(ranked_projects),
        }
    
    def _calculate_airdrop_score(
        self,
        repo_data: Dict[str, Any],
        prs: List[Dict[str, Any]],
        acceptance_rate: float,
    ) -> float:
        """
        Calculate airdrop potential score
        
        Args:
            repo_data: Repository data
            prs: Pull requests
            acceptance_rate: PR acceptance rate
            
        Returns:
            Airdrop score (0-100)
        """
        score = 0.0
        
        # Activity score (30%)
        stars = repo_data.get("stargazers_count", 0)
        forks = repo_data.get("forks_count", 0)
        activity_score = min(30, (stars / 1000 * 20) + (forks / 500 * 10))
        score += activity_score
        
        # PR acceptance score (30%)
        pr_score = min(30, acceptance_rate * 30)
        score += pr_score
        
        # Recent activity score (20%)
        updated_at = repo_data.get("updated_at", "")
        if updated_at:
            days_since_update = (datetime.now() - datetime.fromisoformat(updated_at.replace("Z", "+00:00"))).days
            recency_score = max(0, 20 - (days_since_update / 7))
            score += recency_score
        
        # Web3 relevance score (20%)
        description = repo_data.get("description", "").lower()
        web3_keywords = ["token", "airdrop", "blockchain", "crypto", "defi", "nft", "dao"]
        keyword_count = sum(1 for kw in web3_keywords if kw in description)
        relevance_score = min(20, keyword_count * 5)
        score += relevance_score
        
        return round(score, 1)
