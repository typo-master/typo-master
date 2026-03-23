"""
TypoAgent Skill Manager - High-level skill orchestration for TypoAgent

Provides convenient methods for common TypoAgent workflows.
"""

import os
from typing import Any, Dict, List, Optional
from pathlib import Path

from ..agent_framework.skill_system import SkillContext, SkillResult
from ..agent_framework.logger import get_logger
from . import (
    RepositoryScanSkill,
    TypoFixSkill,
    TypoReportSkill,
    GitOperationsSkill,
    PullRequestSkill,
)

logger = get_logger(__name__)


class TypoAgentSkillManager:
    """
    High-level skill manager for TypoAgent

    Orchestrates multiple skills to complete complex workflows.
    """

    def __init__(self, agent=None):
        self.agent = agent
        self.context = SkillContext(agent)

        # Initialize skills
        self.scan_skill = RepositoryScanSkill()
        self.fix_skill = TypoFixSkill()
        self.report_skill = TypoReportSkill()
        self.git_skill = GitOperationsSkill()
        self.pr_skill = PullRequestSkill()

        logger.info("TypoAgentSkillManager initialized")

    async def scan_and_fix(
        self,
        repo_path: str,
        auto_fix: bool = False,
        max_files: Optional[int] = None,
    ) -> SkillResult:
        """
        Scan repository and optionally fix typos

        Args:
            repo_path: Path to repository
            auto_fix: Whether to automatically fix typos
            max_files: Maximum files to scan

        Returns:
            Combined scan and fix result
        """
        logger.info(f"Starting scan and fix for: {repo_path}")

        # Step 1: Scan
        scan_result = await self.scan_skill.execute(
            self.context,
            repo_path=repo_path,
            max_files=max_files,
        )

        if not scan_result.success:
            return scan_result

        typos_found = scan_result.data.get("total_typos", 0)

        if typos_found == 0:
            return SkillResult(
                success=True,
                data={
                    "message": "No typos found",
                    "scan": scan_result.data,
                }
            )

        # Step 2: Fix if requested
        fix_results = []
        if auto_fix:
            scan_details = scan_result.data.get("scan", {})
            results = scan_details.get("results", [])

            for typo_info in results:
                fix_result = await self.fix_skill.execute(
                    self.context,
                    file_path=typo_info.get("file_path"),
                    typo=typo_info.get("typo"),
                    correction=typo_info.get("correction"),
                    create_backup=True,
                )
                fix_results.append(fix_result)

        return SkillResult(
            success=True,
            data={
                "scan": scan_result.data,
                "fixes": fix_results,
                "typos_found": typos_found,
                "typos_fixed": len([f for f in fix_results if f.success]),
            }
        )

    async def scan_fix_and_pr(
        self,
        repo_path: str,
        owner: str,
        repo: str,
        max_files: Optional[int] = None,
    ) -> SkillResult:
        """
        Complete workflow: scan, fix, commit, and create PR

        Args:
            repo_path: Path to local repository
            owner: GitHub repository owner
            repo: GitHub repository name
            max_files: Maximum files to scan

        Returns:
            Complete workflow result
        """
        logger.info(f"Starting complete workflow for: {owner}/{repo}")

        # Step 1: Scan and fix
        fix_result = await self.scan_and_fix(
            repo_path=repo_path,
            auto_fix=True,
            max_files=max_files,
        )

        if not fix_result.success:
            return fix_result

        typos_fixed = fix_result.data.get("typos_fixed", 0)

        if typos_fixed == 0:
            return SkillResult(
                success=True,
                data={
                    "message": "No typos to fix",
                    "scan": fix_result.data.get("scan"),
                }
            )

        # Step 2: Create branch
        branch_name = await self.git_skill.create_typo_fix_branch(
            self.context,
            repo_path=repo_path,
            typo_count=typos_fixed,
        )

        # Step 3: Git operations
        # Collect fixed files
        fixes = fix_result.data.get("fixes", [])
        fixed_files = [f.data.get("file_path") for f in fixes if f.success]

        git_result = await self.git_skill.execute(
            self.context,
            repo_path=repo_path,
            files=fixed_files,
            commit_message=f"Fix {typos_fixed} typo(s)",
            create_branch=branch_name,
            push=False,
        )

        if not git_result.success:
            return SkillResult(
                success=False,
                error=f"Git operations failed: {git_result.error}",
                data={"fix_result": fix_result.data}
            )

        # Step 4: Generate report
        report_path = os.path.join(repo_path, "TYPO_FIX_REPORT.md")

        typos = []
        for f in fixes:
            if f.success:
                typos.append({
                    "file_path": f.data.get("file_path"),
                    "typo": f.data.get("typo"),
                    "correction": f.data.get("correction"),
                })

        report_result = await self.report_skill.execute(
            self.context,
            typos=typos,
            output_path=report_path,
            format="markdown",
        )

        return SkillResult(
            success=True,
            data={
                "scan": fix_result.data.get("scan"),
                "fixes_applied": typos_fixed,
                "branch": branch_name,
                "files_fixed": fixed_files,
                "report": report_result.data if report_result.success else None,
            }
        )

    async def generate_scan_report(
        self,
        repo_path: str,
        output_path: str,
        format: str = "markdown",
    ) -> SkillResult:
        """
        Scan repository and generate report

        Args:
            repo_path: Path to repository
            output_path: Output report path
            format: Report format

        Returns:
            Report generation result
        """
        # Scan
        scan_result = await self.scan_skill.execute(
            self.context,
            repo_path=repo_path,
        )

        if not scan_result.success:
            return scan_result

        # Extract typos from scan result
        scan_data = scan_result.data.get("scan", {})
        results = scan_data.get("results", [])

        typos = []
        for r in results:
            typos.append({
                "file_path": r.get("file_path"),
                "line_number": r.get("line_number"),
                "typo": r.get("typo"),
                "correction": r.get("correction"),
                "context": r.get("context"),
            })

        # Generate report
        return await self.report_skill.execute(
            self.context,
            typos=typos,
            output_path=output_path,
            format=format,
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics from all skills"""
        return {
            "scan": self.scan_skill.get_stats(),
            "fix": self.fix_skill.get_stats(),
            "report": self.report_skill.get_stats(),
            "git": self.git_skill.get_stats(),
            "pr": self.pr_skill.get_stats(),
        }
