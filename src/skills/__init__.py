"""
TypoAgent Skills - Core skills for typo detection and correction

This module provides skills for the TypoAgent to accomplish its tasks.
"""

import os
import asyncio
from typing import Any, Dict, List, Optional
from pathlib import Path

from ..agent_framework.skill_system import (
    BaseSkill, SkillContext, SkillResult, SkillCategory, skill,
)
from ..agent_framework.tool_system import ToolResult
from ..agent_framework.logger import get_logger

logger = get_logger(__name__)


@skill(
    name="repository_scan",
    description="Scan a repository for typos and spelling errors",
    category=SkillCategory.SCAN,
    version="1.0.0",
    author="TypoAgent",
    required_tools=["scan_local_repo", "scan_single_file", "get_typo_summary"],
    tags=["typo", "scan", "repository"],
    examples=[
        {
            "input": {"repo_path": "./repos/solidity"},
            "output": "Scan report with typos found"
        }
    ]
)
class RepositoryScanSkill(BaseSkill):
    """
    Skill for scanning repositories for typos

    Combines multiple scanning tools to provide comprehensive typo detection.
    """

    def __init__(self, metadata):
        super().__init__(metadata)
        self._scan_history: List[Dict] = []

    async def execute(
        self,
        context: SkillContext,
        repo_path: str,
        max_files: Optional[int] = None,
        include_summary: bool = True,
    ) -> SkillResult:
        """
        Execute repository scan

        Args:
            context: Skill context
            repo_path: Path to repository
            max_files: Maximum files to scan
            include_summary: Whether to include summary statistics

        Returns:
            Scan result with typos found
        """
        steps = []

        try:
            # Step 1: Scan repository
            logger.info(f"Scanning repository: {repo_path}")
            steps.append("scan_repository")

            scan_result = await context.call_tool(
                "scan_local_repo",
                repo_directory=repo_path,
                max_files=max_files,
            )

            if not scan_result.success:
                return SkillResult(
                    success=False,
                    error=f"Scan failed: {scan_result.error}",
                    steps_executed=steps
                )

            scan_data = scan_result.data

            # Step 2: Get summary if requested and typos found
            summary_data = None
            if include_summary and scan_data.get("typos_found", 0) > 0:
                logger.info("Generating typo summary")
                steps.append("generate_summary")

                summary_result = await context.call_tool(
                    "get_typo_summary",
                    repo_directory=repo_path,
                )

                if summary_result.success:
                    summary_data = summary_result.data

            # Build result
            result_data = {
                "repo_path": repo_path,
                "scan": scan_data,
                "summary": summary_data,
                "total_typos": scan_data.get("typos_found", 0),
                "files_scanned": scan_data.get("scanned_files", 0),
            }

            # Remember scan in agent memory
            if context.memory:
                await context.memory.remember_workflow(
                    workflow_name="repository_scan",
                    state=result_data,
                    importance=0.8
                )

            # Store in skill history
            self._scan_history.append({
                "repo_path": repo_path,
                "typos_found": result_data["total_typos"],
                "files_scanned": result_data["files_scanned"],
            })

            return SkillResult(
                success=True,
                data=result_data,
                steps_executed=steps
            )

        except Exception as e:
            logger.error(f"Repository scan failed: {e}")
            return SkillResult(
                success=False,
                error=str(e),
                steps_executed=steps
            )

    def get_scan_history(self) -> List[Dict]:
        """Get history of scans performed"""
        return self._scan_history.copy()


@skill(
    name="typo_fix",
    description="Fix typos in files and create corrections",
    category=SkillCategory.FIX,
    version="1.0.0",
    author="TypoAgent",
    required_tools=["correct_spelling", "read_file", "write_file"],
    tags=["typo", "fix", "correction"],
    examples=[
        {
            "input": {"file_path": "./README.md", "typo": "teh", "correction": "the"},
            "output": "Fixed file content"
        }
    ]
)
class TypoFixSkill(BaseSkill):
    """
    Skill for fixing typos in files

    Provides intelligent typo correction with backup and verification.
    """

    def __init__(self, metadata):
        super().__init__(metadata)
        self._fixes_applied: List[Dict] = []

    async def execute(
        self,
        context: SkillContext,
        file_path: str,
        typo: str,
        correction: str,
        create_backup: bool = True,
        verify_fix: bool = True,
    ) -> SkillResult:
        """
        Execute typo fix

        Args:
            context: Skill context
            file_path: Path to file
            typo: Typo to fix
            correction: Correct spelling
            create_backup: Whether to create backup
            verify_fix: Whether to verify the fix

        Returns:
            Fix result
        """
        steps = []

        try:
            # Step 1: Read file
            logger.info(f"Reading file: {file_path}")
            steps.append("read_file")

            read_result = await context.call_tool(
                "read_file",
                file_path=file_path,
            )

            if isinstance(read_result, ToolResult) and not read_result.success:
                return SkillResult(
                    success=False,
                    error=f"Failed to read file: {read_result.error}",
                    steps_executed=steps
                )

            # Extract content from ToolResult or assume it's the content directly
            if isinstance(read_result, ToolResult):
                content = read_result.data
            else:
                content = str(read_result)

            # Step 2: Create backup if requested
            if create_backup:
                logger.info("Creating backup")
                steps.append("create_backup")

                backup_path = f"{file_path}.backup"
                await context.call_tool(
                    "write_file",
                    file_path=backup_path,
                    content=content,
                )

            # Step 3: Apply correction
            logger.info(f"Applying correction: {typo} -> {correction}")
            steps.append("apply_correction")

            corrected_content = content.replace(typo, correction)

            # Step 4: Verify fix if requested
            if verify_fix:
                logger.info("Verifying fix")
                steps.append("verify_fix")

                if typo in corrected_content:
                    return SkillResult(
                        success=False,
                        error="Fix verification failed: typo still present",
                        steps_executed=steps
                    )

            # Step 5: Write corrected content
            logger.info("Writing corrected file")
            steps.append("write_file")

            write_result = await context.call_tool(
                "write_file",
                file_path=file_path,
                content=corrected_content,
            )

            if isinstance(write_result, ToolResult) and not write_result.success:
                return SkillResult(
                    success=False,
                    error=f"Failed to write file: {write_result.error}",
                    steps_executed=steps
                )

            # Record fix
            fix_record = {
                "file_path": file_path,
                "typo": typo,
                "correction": correction,
            }
            self._fixes_applied.append(fix_record)

            # Remember in agent memory
            if context.memory:
                await context.memory.remember_experience(
                    task_type="typo_fix",
                    input_data={"file": file_path, "typo": typo},
                    result={"success": True, "correction": correction},
                    success=True
                )

            return SkillResult(
                success=True,
                data={
                    "file_path": file_path,
                    "typo": typo,
                    "correction": correction,
                    "backup_created": create_backup,
                },
                steps_executed=steps
            )

        except Exception as e:
            logger.error(f"Typo fix failed: {e}")
            return SkillResult(
                success=False,
                error=str(e),
                steps_executed=steps
            )

    async def fix_multiple(
        self,
        context: SkillContext,
        file_path: str,
        corrections: List[Dict[str, str]],
        create_backup: bool = True,
    ) -> SkillResult:
        """
        Fix multiple typos in a file

        Args:
            context: Skill context
            file_path: Path to file
            corrections: List of {typo, correction} dictionaries
            create_backup: Whether to create backup

        Returns:
            Fix result with all corrections applied
        """
        steps = []
        applied_fixes = []
        failed_fixes = []

        try:
            # Read file once
            read_result = await context.call_tool(
                "read_file",
                file_path=file_path,
            )

            if isinstance(read_result, ToolResult) and not read_result.success:
                return SkillResult(
                    success=False,
                    error=f"Failed to read file: {read_result.error}",
                    steps_executed=steps
                )

            content = read_result.data if isinstance(read_result, ToolResult) else str(read_result)

            # Create backup
            if create_backup:
                await context.call_tool(
                    "write_file",
                    file_path=f"{file_path}.backup",
                    content=content,
                )
                steps.append("create_backup")

            # Apply corrections
            corrected_content = content
            for correction in corrections:
                typo = correction.get("typo")
                fix = correction.get("correction")

                if typo and fix and typo in corrected_content:
                    corrected_content = corrected_content.replace(typo, fix)
                    applied_fixes.append({"typo": typo, "correction": fix})
                else:
                    failed_fixes.append(correction)

            # Write corrected content
            write_result = await context.call_tool(
                "write_file",
                file_path=file_path,
                content=corrected_content,
            )

            steps.append("write_file")

            return SkillResult(
                success=len(failed_fixes) == 0,
                data={
                    "file_path": file_path,
                    "applied_fixes": applied_fixes,
                    "failed_fixes": failed_fixes,
                    "total_applied": len(applied_fixes),
                    "total_failed": len(failed_fixes),
                },
                steps_executed=steps
            )

        except Exception as e:
            return SkillResult(
                success=False,
                error=str(e),
                steps_executed=steps
            )

    def get_fix_history(self) -> List[Dict]:
        """Get history of fixes applied"""
        return self._fixes_applied.copy()


@skill(
    name="typo_report",
    description="Generate comprehensive typo reports",
    category=SkillCategory.REPORT,
    version="1.0.0",
    author="TypoAgent",
    required_tools=["generate_csv_report", "generate_json_report", "generate_markdown_report"],
    tags=["typo", "report", "export"],
    examples=[
        {
            "input": {
                "typos": [{"file": "test.md", "typo": "teh", "correction": "the"}],
                "format": "markdown"
            },
            "output": "Report file path"
        }
    ]
)
class TypoReportSkill(BaseSkill):
    """
    Skill for generating typo reports

    Creates various report formats (Markdown, JSON, CSV, HTML).
    """

    def __init__(self, metadata):
        super().__init__(metadata)
        self._reports_generated: List[Dict] = []

    async def execute(
        self,
        context: SkillContext,
        typos: List[Dict[str, Any]],
        output_path: str,
        format: str = "markdown",
        include_stats: bool = True,
    ) -> SkillResult:
        """
        Generate typo report

        Args:
            context: Skill context
            typos: List of typo records
            output_path: Output file path
            format: Report format (markdown, json, csv, html)
            include_stats: Whether to include statistics

        Returns:
            Report generation result
        """
        steps = []

        try:
            logger.info(f"Generating {format} report")
            steps.append(f"generate_{format}_report")

            # Calculate statistics
            stats = None
            if include_stats:
                stats = self._calculate_stats(typos)

            # Prepare report data
            report_data = {
                "typos": typos,
                "stats": stats,
                "total_typos": len(typos),
            }

            # Generate report based on format
            if format == "markdown":
                result = await context.call_tool(
                    "generate_markdown_report",
                    typos=typos,
                    output_path=output_path,
                    stats=stats,
                )
            elif format == "json":
                result = await context.call_tool(
                    "generate_json_report",
                    data=report_data,
                    output_path=output_path,
                )
            elif format == "csv":
                result = await context.call_tool(
                    "generate_csv_report",
                    typos=typos,
                    output_path=output_path,
                )
            else:
                return SkillResult(
                    success=False,
                    error=f"Unsupported format: {format}",
                    steps_executed=steps
                )

            # Record report generation
            self._reports_generated.append({
                "format": format,
                "output_path": output_path,
                "typo_count": len(typos),
            })

            if isinstance(result, ToolResult) and not result.success:
                return SkillResult(
                    success=False,
                    error=result.error,
                    steps_executed=steps
                )

            return SkillResult(
                success=True,
                data={
                    "output_path": output_path,
                    "format": format,
                    "typo_count": len(typos),
                    "stats": stats,
                },
                steps_executed=steps
            )

        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            return SkillResult(
                success=False,
                error=str(e),
                steps_executed=steps
            )

    def _calculate_stats(self, typos: List[Dict]) -> Dict[str, Any]:
        """Calculate typo statistics"""
        if not typos:
            return {}

        # Count by file
        files = {}
        typo_types = {}

        for typo in typos:
            file_path = typo.get("file_path", "unknown")
            files[file_path] = files.get(file_path, 0) + 1

            typo_word = typo.get("typo", "unknown")
            typo_types[typo_word] = typo_types.get(typo_word, 0) + 1

        return {
            "total_typos": len(typos),
            "unique_files": len(files),
            "files_with_typos": files,
            "common_typos": sorted(typo_types.items(), key=lambda x: x[1], reverse=True)[:10],
        }

    async def generate_summary(
        self,
        context: SkillContext,
        scan_results: List[Dict],
        output_path: str,
    ) -> SkillResult:
        """Generate summary report from multiple scan results"""
        try:
            total_typos = sum(r.get("total_typos", 0) for r in scan_results)
            total_files = sum(r.get("files_scanned", 0) for r in scan_results)

            summary = {
                "scan_count": len(scan_results),
                "total_typos": total_typos,
                "total_files_scanned": total_files,
                "scans": scan_results,
            }

            # Write summary
            import json
            with open(output_path, 'w') as f:
                json.dump(summary, f, indent=2)

            return SkillResult(
                success=True,
                data={
                    "output_path": output_path,
                    "summary": summary,
                }
            )

        except Exception as e:
            return SkillResult(
                success=False,
                error=str(e)
            )


@skill(
    name="git_operations",
    description="Execute Git operations for typo fixes",
    category=SkillCategory.GIT,
    version="1.0.0",
    author="TypoAgent",
    required_tools=["git_add", "git_commit", "git_push", "git_create_branch"],
    tags=["git", "commit", "branch"],
    examples=[
        {
            "input": {
                "repo_path": "./repos/solidity",
                "files": ["README.md"],
                "commit_message": "Fix typos"
            },
            "output": "Git operation results"
        }
    ]
)
class GitOperationsSkill(BaseSkill):
    """
    Skill for Git operations

    Handles creating branches, committing changes, and pushing.
    """

    def __init__(self, metadata):
        super().__init__(metadata)
        self._commits_made: List[Dict] = []

    async def execute(
        self,
        context: SkillContext,
        repo_path: str,
        files: List[str],
        commit_message: str,
        create_branch: Optional[str] = None,
        push: bool = False,
    ) -> SkillResult:
        """
        Execute Git operations

        Args:
            context: Skill context
            repo_path: Repository path
            files: Files to commit
            commit_message: Commit message
            create_branch: Branch name to create (optional)
            push: Whether to push

        Returns:
            Git operation results
        """
        steps = []

        try:
            # Step 1: Create branch if requested
            if create_branch:
                logger.info(f"Creating branch: {create_branch}")
                steps.append("create_branch")

                branch_result = await context.call_tool(
                    "git_create_branch",
                    repo_path=repo_path,
                    branch_name=create_branch,
                )

                if isinstance(branch_result, ToolResult) and not branch_result.success:
                    return SkillResult(
                        success=False,
                        error=f"Failed to create branch: {branch_result.error}",
                        steps_executed=steps
                    )

            # Step 2: Add files
            logger.info(f"Adding files: {files}")
            steps.append("add_files")

            for file_path in files:
                add_result = await context.call_tool(
                    "git_add",
                    repo_path=repo_path,
                    file_path=file_path,
                )

                if isinstance(add_result, ToolResult) and not add_result.success:
                    logger.warning(f"Failed to add file {file_path}: {add_result.error}")

            # Step 3: Commit
            logger.info(f"Committing with message: {commit_message}")
            steps.append("commit")

            commit_result = await context.call_tool(
                "git_commit",
                repo_path=repo_path,
                message=commit_message,
            )

            if isinstance(commit_result, ToolResult) and not commit_result.success:
                return SkillResult(
                    success=False,
                    error=f"Failed to commit: {commit_result.error}",
                    steps_executed=steps
                )

            commit_hash = commit_result.data if isinstance(commit_result, ToolResult) else None

            # Step 4: Push if requested
            push_result = None
            if push:
                logger.info("Pushing changes")
                steps.append("push")

                push_result = await context.call_tool(
                    "git_push",
                    repo_path=repo_path,
                )

            # Record commit
            self._commits_made.append({
                "repo_path": repo_path,
                "files": files,
                "message": commit_message,
                "branch": create_branch,
            })

            return SkillResult(
                success=True,
                data={
                    "repo_path": repo_path,
                    "files_committed": files,
                    "commit_message": commit_message,
                    "branch": create_branch,
                    "commit_hash": commit_hash,
                    "pushed": push,
                },
                steps_executed=steps
            )

        except Exception as e:
            logger.error(f"Git operations failed: {e}")
            return SkillResult(
                success=False,
                error=str(e),
                steps_executed=steps
            )

    async def create_typo_fix_branch(
        self,
        context: SkillContext,
        repo_path: str,
        typo_count: int = 1,
    ) -> str:
        """Create a branch for typo fixes"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d")
        branch_name = f"fix/typos-{timestamp}-{typo_count}"

        await context.call_tool(
            "git_create_branch",
            repo_path=repo_path,
            branch_name=branch_name,
        )

        return branch_name


@skill(
    name="pull_request",
    description="Create and manage pull requests for typo fixes",
    category=SkillCategory.GITHUB,
    version="1.0.0",
    author="TypoAgent",
    required_tools=["create_pull_request", "create_pr", "prepare_pr"],
    tags=["pr", "github", "pull-request"],
    examples=[
        {
            "input": {
                "owner": "ethereum",
                "repo": "solidity",
                "title": "Fix typos",
                "body": "This PR fixes typos",
                "head_branch": "fix/typos"
            },
            "output": "PR URL"
        }
    ]
)
class PullRequestSkill(BaseSkill):
    """
    Skill for creating pull requests

    Handles PR creation with proper title and description generation.
    """

    def __init__(self, metadata):
        super().__init__(metadata)
        self._prs_created: List[Dict] = []

    async def execute(
        self,
        context: SkillContext,
        owner: str,
        repo: str,
        head_branch: str,
        title: Optional[str] = None,
        body: Optional[str] = None,
        base_branch: str = "main",
        generate_description: bool = True,
        typos: Optional[List[Dict]] = None,
    ) -> SkillResult:
        """
        Create pull request

        Args:
            context: Skill context
            owner: Repository owner
            repo: Repository name
            head_branch: Branch with changes
            title: PR title (auto-generated if not provided)
            body: PR body (auto-generated if not provided)
            base_branch: Target branch
            generate_description: Whether to auto-generate description
            typos: List of typos for description generation

        Returns:
            PR creation result
        """
        steps = []

        try:
            # Step 1: Prepare PR
            logger.info("Preparing PR")
            steps.append("prepare_pr")

            if generate_description and typos:
                # Generate title
                if not title:
                    title = self._generate_pr_title(typos)

                # Generate body
                if not body:
                    body = self._generate_pr_body(typos)

            # Step 2: Create PR
            logger.info(f"Creating PR: {title}")
            steps.append("create_pr")

            pr_result = await context.call_tool(
                "create_pull_request",
                owner=owner,
                repo=repo,
                title=title or "Fix typos",
                body=body or "This PR fixes typos",
                head=head_branch,
                base=base_branch,
            )

            if isinstance(pr_result, ToolResult) and not pr_result.success:
                return SkillResult(
                    success=False,
                    error=f"Failed to create PR: {pr_result.error}",
                    steps_executed=steps
                )

            pr_data = pr_result.data if isinstance(pr_result, ToolResult) else pr_result

            # Record PR
            self._prs_created.append({
                "owner": owner,
                "repo": repo,
                "title": title,
                "branch": head_branch,
            })

            return SkillResult(
                success=True,
                data={
                    "owner": owner,
                    "repo": repo,
                    "title": title,
                    "branch": head_branch,
                    "pr_data": pr_data,
                },
                steps_executed=steps
            )

        except Exception as e:
            logger.error(f"PR creation failed: {e}")
            return SkillResult(
                success=False,
                error=str(e),
                steps_executed=steps
            )

    def _generate_pr_title(self, typos: List[Dict]) -> str:
        """Generate PR title from typos"""
        if not typos:
            return "Fix typos"

        unique_files = len(set(t.get("file_path") for t in typos))
        total_typos = len(typos)

        if unique_files == 1:
            return f"Fix {total_typos} typo(s) in {typos[0].get('file_path', 'file')}"
        else:
            return f"Fix {total_typos} typo(s) across {unique_files} files"

    def _generate_pr_body(self, typos: List[Dict]) -> str:
        """Generate PR description from typos"""
        if not typos:
            return "This PR fixes typos."

        body = "## Typo Fixes\n\n"
        body += "This PR fixes the following typos:\n\n"

        # Group by file
        by_file = {}
        for typo in typos:
            file_path = typo.get("file_path", "unknown")
            if file_path not in by_file:
                by_file[file_path] = []
            by_file[file_path].append(typo)

        for file_path, file_typos in by_file.items():
            body += f"### {file_path}\n"
            for t in file_typos:
                body += f"- `{t.get('typo')}` → `{t.get('correction')}`\n"
            body += "\n"

        return body


@skill(
    name="repository_clone",
    description="Clone a Git repository from remote",
    category=SkillCategory.GIT,
    version="1.0.0",
    author="TypoAgent",
    required_tools=["git_clone", "read_file"],
    tags=["git", "clone", "repository"],
    examples=[
        {
            "input": {"repo_url": "https://github.com/ethereum/solidity.git", "local_path": "./repos/solidity"},
            "output": "Cloned repository path"
        }
    ]
)
class RepositoryCloneSkill(BaseSkill):
    """
    Skill for cloning repositories

    Supports cloning from GitHub, GitLab, and other Git repositories.
    """

    def __init__(self, metadata):
        super().__init__(metadata)
        self._cloned_repos: List[Dict] = []

    async def execute(
        self,
        context: SkillContext,
        repo_url: str,
        local_path: str,
        branch: Optional[str] = None,
        depth: Optional[int] = None,
    ) -> SkillResult:
        """
        Clone a repository

        Args:
            context: Skill context
            repo_url: Repository URL
            local_path: Local path to clone to
            branch: Specific branch to clone
            depth: Clone depth (for shallow clone)

        Returns:
            Clone result
        """
        steps = []

        try:
            logger.info(f"Cloning repository: {repo_url}")
            steps.append("clone_repository")

            # Build clone arguments
            clone_args = {
                "repo_url": repo_url,
                "local_path": local_path,
            }
            if branch:
                clone_args["branch"] = branch
            if depth:
                clone_args["depth"] = depth

            clone_result = await context.call_tool(
                "git_clone",
                **clone_args
            )

            if isinstance(clone_result, ToolResult) and not clone_result.success:
                return SkillResult(
                    success=False,
                    error=f"Clone failed: {clone_result.error}",
                    steps_executed=steps
                )

            # Record clone
            self._cloned_repos.append({
                "repo_url": repo_url,
                "local_path": local_path,
                "branch": branch,
            })

            return SkillResult(
                success=True,
                data={
                    "repo_url": repo_url,
                    "local_path": local_path,
                    "branch": branch,
                },
                steps_executed=steps
            )

        except Exception as e:
            logger.error(f"Repository clone failed: {e}")
            return SkillResult(
                success=False,
                error=str(e),
                steps_executed=steps
            )


@skill(
    name="repository_download",
    description="Download a repository as ZIP from GitHub/GitLab",
    category=SkillCategory.GITHUB,
    version="1.0.0",
    author="TypoAgent",
    required_tools=["download_github_repo", "extract_zip"],
    tags=["download", "zip", "repository", "github"],
    examples=[
        {
            "input": {"owner": "ethereum", "repo": "solidity", "output_dir": "./repos"},
            "output": "Downloaded and extracted path"
        }
    ]
)
class RepositoryDownloadSkill(BaseSkill):
    """
    Skill for downloading repositories as ZIP

    Downloads from GitHub/GitLab and extracts to local directory.
    """

    def __init__(self, metadata):
        super().__init__(metadata)
        self._downloaded_repos: List[Dict] = []

    async def execute(
        self,
        context: SkillContext,
        owner: str,
        repo: str,
        output_dir: str,
        branch: str = "main",
        extract: bool = True,
    ) -> SkillResult:
        """
        Download a repository

        Args:
            context: Skill context
            owner: Repository owner
            repo: Repository name
            output_dir: Output directory
            branch: Branch to download
            extract: Whether to extract the ZIP

        Returns:
            Download result
        """
        steps = []

        try:
            logger.info(f"Downloading repository: {owner}/{repo}")
            steps.append("download_repo")

            # Download
            download_result = await context.call_tool(
                "download_github_repo",
                owner=owner,
                repo=repo,
                branch=branch,
                output_dir=output_dir,
            )

            if isinstance(download_result, ToolResult) and not download_result.success:
                return SkillResult(
                    success=False,
                    error=f"Download failed: {download_result.error}",
                    steps_executed=steps
                )

            zip_path = download_result.data if isinstance(download_result, ToolResult) else download_result

            # Extract if requested
            extract_path = None
            if extract and zip_path:
                logger.info("Extracting ZIP")
                steps.append("extract_zip")

                extract_result = await context.call_tool(
                    "extract_zip",
                    zip_path=zip_path,
                    output_dir=output_dir,
                )

                if isinstance(extract_result, ToolResult):
                    extract_path = extract_result.data
                else:
                    extract_path = extract_result

            # Record download
            self._downloaded_repos.append({
                "owner": owner,
                "repo": repo,
                "branch": branch,
                "output_dir": output_dir,
            })

            return SkillResult(
                success=True,
                data={
                    "owner": owner,
                    "repo": repo,
                    "branch": branch,
                    "zip_path": zip_path,
                    "extract_path": extract_path,
                },
                steps_executed=steps
            )

        except Exception as e:
            logger.error(f"Repository download failed: {e}")
            return SkillResult(
                success=False,
                error=str(e),
                steps_executed=steps
            )


@skill(
    name="pr_monitor",
    description="Monitor pull request status and changes",
    category=SkillCategory.GITHUB,
    version="1.0.0",
    author="TypoAgent",
    required_tools=["get_pull_request", "get_pr_status", "list_pr_commits"],
    tags=["pr", "monitor", "github", "track"],
    examples=[
        {
            "input": {"owner": "ethereum", "repo": "solidity", "pr_number": 123},
            "output": "PR status and details"
        }
    ]
)
class PRMonitorSkill(BaseSkill):
    """
    Skill for monitoring pull requests

    Tracks PR status, reviews, and updates.
    """

    def __init__(self, metadata):
        super().__init__(metadata)
        self._monitored_prs: Dict[str, Dict] = {}

    async def execute(
        self,
        context: SkillContext,
        owner: str,
        repo: str,
        pr_number: int,
        action: str = "status",  # status, check, wait_for_merge
    ) -> SkillResult:
        """
        Monitor a pull request

        Args:
            context: Skill context
            owner: Repository owner
            repo: Repository name
            pr_number: PR number
            action: Action to perform

        Returns:
            PR monitoring result
        """
        steps = []

        try:
            pr_key = f"{owner}/{repo}#{pr_number}"
            logger.info(f"Monitoring PR: {pr_key}")
            steps.append("get_pr_info")

            # Get PR info
            pr_result = await context.call_tool(
                "get_pull_request",
                owner=owner,
                repo=repo,
                pr_number=pr_number,
            )

            if isinstance(pr_result, ToolResult) and not pr_result.success:
                return SkillResult(
                    success=False,
                    error=f"Failed to get PR: {pr_result.error}",
                    steps_executed=steps
                )

            pr_data = pr_result.data if isinstance(pr_result, ToolResult) else pr_result

            # Get status
            steps.append("get_pr_status")
            status_result = await context.call_tool(
                "get_pr_status",
                owner=owner,
                repo=repo,
                pr_number=pr_number,
            )

            status_data = status_result.data if isinstance(status_result, ToolResult) else status_result

            # Store monitoring data
            self._monitored_prs[pr_key] = {
                "owner": owner,
                "repo": repo,
                "pr_number": pr_number,
                "last_check": datetime.now().isoformat(),
                "status": status_data,
            }

            return SkillResult(
                success=True,
                data={
                    "pr": pr_data,
                    "status": status_data,
                    "action": action,
                },
                steps_executed=steps
            )

        except Exception as e:
            logger.error(f"PR monitoring failed: {e}")
            return SkillResult(
                success=False,
                error=str(e),
                steps_executed=steps
            )

    async def check_all_monitored(self, context: SkillContext) -> SkillResult:
        """Check all monitored PRs for updates"""
        updates = []

        for pr_key, pr_info in self._monitored_prs.items():
            result = await self.execute(
                context,
                pr_info["owner"],
                pr_info["repo"],
                pr_info["pr_number"],
                action="status"
            )

            if result.success:
                updates.append({
                    "pr_key": pr_key,
                    "status": result.data.get("status"),
                })

        return SkillResult(
            success=True,
            data={"updates": updates, "total_monitored": len(self._monitored_prs)}
        )


@skill(
    name="issue_track",
    description="Track and manage GitHub issues",
    category=SkillCategory.GITHUB,
    version="1.0.0",
    author="TypoAgent",
    required_tools=["get_issue", "list_issues", "create_issue"],
    tags=["issue", "track", "github"],
    examples=[
        {
            "input": {"owner": "ethereum", "repo": "solidity", "action": "list", "state": "open"},
            "output": "List of issues"
        }
    ]
)
class IssueTrackSkill(BaseSkill):
    """
    Skill for tracking GitHub issues

    Lists, creates, and monitors issues.
    """

    def __init__(self, metadata):
        super().__init__(metadata)
        self._tracked_issues: Dict[str, Dict] = {}

    async def execute(
        self,
        context: SkillContext,
        owner: str,
        repo: str,
        action: str = "list",
        issue_number: Optional[int] = None,
        state: str = "open",
        labels: Optional[List[str]] = None,
    ) -> SkillResult:
        """
        Track issues

        Args:
            context: Skill context
            owner: Repository owner
            repo: Repository name
            action: Action (list, get, create)
            issue_number: Issue number (for get action)
            state: Issue state filter
            labels: Label filters

        Returns:
            Issue tracking result
        """
        steps = []

        try:
            if action == "list":
                logger.info(f"Listing issues for {owner}/{repo}")
                steps.append("list_issues")

                result = await context.call_tool(
                    "list_issues",
                    owner=owner,
                    repo=repo,
                    state=state,
                    labels=labels,
                )

                if isinstance(result, ToolResult) and not result.success:
                    return SkillResult(
                        success=False,
                        error=f"Failed to list issues: {result.error}",
                        steps_executed=steps
                    )

                issues = result.data if isinstance(result, ToolResult) else result

                return SkillResult(
                    success=True,
                    data={"issues": issues, "count": len(issues)},
                    steps_executed=steps
                )

            elif action == "get" and issue_number:
                logger.info(f"Getting issue #{issue_number}")
                steps.append("get_issue")

                result = await context.call_tool(
                    "get_issue",
                    owner=owner,
                    repo=repo,
                    issue_number=issue_number,
                )

                issue_data = result.data if isinstance(result, ToolResult) else result

                # Track this issue
                issue_key = f"{owner}/{repo}#{issue_number}"
                self._tracked_issues[issue_key] = {
                    "owner": owner,
                    "repo": repo,
                    "issue_number": issue_number,
                    "last_check": datetime.now().isoformat(),
                }

                return SkillResult(
                    success=True,
                    data={"issue": issue_data},
                    steps_executed=steps
                )

            else:
                return SkillResult(
                    success=False,
                    error=f"Unknown action: {action}",
                    steps_executed=steps
                )

        except Exception as e:
            logger.error(f"Issue tracking failed: {e}")
            return SkillResult(
                success=False,
                error=str(e),
                steps_executed=steps
            )


@skill(
    name="notification",
    description="Send notifications about scan/fix results",
    category=SkillCategory.REPORT,
    version="1.0.0",
    author="TypoAgent",
    required_tools=[],
    tags=["notify", "report", "alert"],
    examples=[
        {
            "input": {"message": "Scan complete", "channel": "slack"},
            "output": "Notification sent"
        }
    ]
)
class NotificationSkill(BaseSkill):
    """
    Skill for sending notifications

    Supports multiple channels (console, file, webhook).
    """

    def __init__(self, metadata):
        super().__init__(metadata)
        self._notifications_sent: List[Dict] = []

    async def execute(
        self,
        context: SkillContext,
        message: str,
        channel: str = "console",
        data: Optional[Dict] = None,
        webhook_url: Optional[str] = None,
    ) -> SkillResult:
        """
        Send notification

        Args:
            context: Skill context
            message: Notification message
            channel: Channel (console, file, webhook)
            data: Additional data
            webhook_url: Webhook URL for webhook channel

        Returns:
            Notification result
        """
        steps = []

        try:
            logger.info(f"Sending notification via {channel}")
            steps.append(f"send_{channel}")

            if channel == "console":
                print(f"\n{'='*60}")
                print(f"NOTIFICATION: {message}")
                print(f"{'='*60}")
                if data:
                    print(f"Data: {data}")

            elif channel == "file" and data:
                # Write to file
                output_path = data.get("output_path", "notification.txt")
                with open(output_path, 'w') as f:
                    f.write(f"{message}\n")
                    f.write(f"Data: {data}\n")

            elif channel == "webhook" and webhook_url:
                # Could implement webhook call here
                logger.info(f"Would send webhook to: {webhook_url}")

            # Record notification
            self._notifications_sent.append({
                "channel": channel,
                "message": message,
                "timestamp": datetime.now().isoformat(),
            })

            return SkillResult(
                success=True,
                data={"channel": channel, "message": message},
                steps_executed=steps
            )

        except Exception as e:
            logger.error(f"Notification failed: {e}")
            return SkillResult(
                success=False,
                error=str(e),
                steps_executed=steps
            )

    def get_notification_history(self) -> List[Dict]:
        """Get history of notifications sent"""
        return self._notifications_sent.copy()


@skill(
    name="batch_processing",
    description="Process multiple repositories in batch",
    category=SkillCategory.SCAN,
    version="1.0.0",
    author="TypoAgent",
    required_tools=[],
    tags=["batch", "bulk", "multiple"],
    examples=[
        {
            "input": {"repos": [{"owner": "org1", "repo": "repo1"}, {"owner": "org2", "repo": "repo2"}]},
            "output": "Batch processing results"
        }
    ]
)
class BatchProcessingSkill(BaseSkill):
    """
    Skill for batch processing multiple repositories

    Processes multiple repos in parallel.
    """

    def __init__(self, metadata):
        super().__init__(metadata)
        self._batch_results: List[Dict] = []

    async def execute(
        self,
        context: SkillContext,
        repos: List[Dict[str, str]],
        action: str = "scan",  # scan, fix, full_workflow
        max_concurrent: int = 3,
    ) -> SkillResult:
        """
        Process multiple repositories

        Args:
            context: Skill context
            repos: List of {owner, repo} dictionaries
            action: Action to perform on each repo
            max_concurrent: Maximum parallel processes

        Returns:
            Batch processing result
        """
        steps = []

        try:
            logger.info(f"Starting batch processing of {len(repos)} repositories")
            steps.append("start_batch")

            results = []
            errors = []

            # Process in batches
            for i in range(0, len(repos), max_concurrent):
                batch = repos[i:i + max_concurrent]
                logger.info(f"Processing batch {i//max_concurrent + 1}: {[r['repo'] for r in batch]}")

                # Create tasks for this batch
                tasks = []
                for repo_info in batch:
                    task = self._process_single_repo(context, repo_info, action)
                    tasks.append(task)

                # Wait for batch to complete
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                for repo_info, result in zip(batch, batch_results):
                    if isinstance(result, Exception):
                        errors.append({"repo": repo_info, "error": str(result)})
                    else:
                        results.append({"repo": repo_info, "result": result})

            steps.append("complete_batch")

            # Record batch
            self._batch_results.append({
                "repos_count": len(repos),
                "action": action,
                "success_count": len(results),
                "error_count": len(errors),
            })

            return SkillResult(
                success=len(errors) == 0,
                data={
                    "total_repos": len(repos),
                    "successful": len(results),
                    "failed": len(errors),
                    "results": results,
                    "errors": errors,
                },
                steps_executed=steps
            )

        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            return SkillResult(
                success=False,
                error=str(e),
                steps_executed=steps
            )

    async def _process_single_repo(
        self,
        context: SkillContext,
        repo_info: Dict[str, str],
        action: str
    ) -> Dict[str, Any]:
        """Process a single repository"""
        owner = repo_info["owner"]
        repo = repo_info["repo"]

        logger.info(f"Processing {owner}/{repo}")

        # This would integrate with other skills
        # For now, return a placeholder
        return {
            "owner": owner,
            "repo": repo,
            "action": action,
            "status": "processed",
        }

    def get_batch_history(self) -> List[Dict]:
        """Get history of batch operations"""
        return self._batch_results.copy()
__all__ = [
    "RepositoryScanSkill",
    "TypoFixSkill",
    "TypoReportSkill",
    "GitOperationsSkill",
    "PullRequestSkill",
    "RepositoryCloneSkill",
    "RepositoryDownloadSkill",
    "PRMonitorSkill",
    "IssueTrackSkill",
    "NotificationSkill",
    "BatchProcessingSkill",
    "SecretDetectionSkill",
    "VulnerabilityScanSkill",
    "InsecurePatternSkill",
    "HardcodedCredentialSkill",
    "DependencyAuditSkill",
]


# ============ Security Skills ============

@skill(
    name="secret_detection",
    description="Detect exposed secrets, API keys, and credentials in code",
    category=SkillCategory.SCAN,
    version="1.0.0",
    author="TypoAgent",
    required_tools=["scan_local_repo", "read_file"],
    tags=["security", "secret", "credential", "api-key"],
    examples=[
        {
            "input": {"repo_path": "./repos/solidity"},
            "output": "List of exposed secrets found"
        }
    ]
)
class SecretDetectionSkill(BaseSkill):
    """
    Skill for detecting exposed secrets in code

    Scans for API keys, passwords, tokens, private keys, and other sensitive data.
    This can help prevent security breaches and is a valuable contribution to any repo.
    """

    # Patterns for detecting secrets
    SECRET_PATTERNS = {
        "api_key": [
            r'api[_-]?key["\']?\s*[:=]\s*["\'][a-zA-Z0-9_\-]{16,}["\']',
            r'apikey["\']?\s*[:=]\s*["\'][a-zA-Z0-9_\-]{16,}["\']',
        ],
        "aws_key": [
            r'AKIA[0-9A-Z]{16}',
            r'aws[_-]?secret[_-]?access[_-]?key["\']?\s*[:=]\s*["\'][^"\']{20,}["\']',
        ],
        "github_token": [
            r'gh[pousr]_[A-Za-z0-9_]{36,}',
            r'github[_-]?token["\']?\s*[:=]\s*["\'][^"\']{35,}["\']',
        ],
        "private_key": [
            r'-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----',
            r'-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----[^\-]*-----END',
        ],
        "password": [
            r'password["\']?\s*[:=]\s*["\'][^"\']{8,}["\']',
            r'passwd["\']?\s*[:=]\s*["\'][^"\']{8,}["\']',
            r'pwd["\']?\s*[:=]\s*["\'][^"\']{8,}["\']',
        ],
        "database_url": [
            r'(mongodb|mysql|postgresql|postgres|redis)://[^\s\"\']+:[^\s@\"\']+@[^\s\"\']+',
        ],
        "jwt_token": [
            r'eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*',
        ],
        "slack_token": [
            r'xox[baprs]-[0-9a-zA-Z]{10,48}',
        ],
        "stripe_key": [
            r'sk_live_[0-9a-zA-Z]{24,}',
            r'pk_live_[0-9a-zA-Z]{24,}',
        ],
    }

    def __init__(self, metadata):
        super().__init__(metadata)
        self._secrets_found: List[Dict] = []

    async def execute(
        self,
        context: SkillContext,
        repo_path: str,
        file_extensions: Optional[List[str]] = None,
    ) -> SkillResult:
        """
        Detect secrets in repository

        Args:
            context: Skill context
            repo_path: Path to repository
            file_extensions: Specific file extensions to scan (default: code files)

        Returns:
            Detection result with found secrets
        """
        import re
        import os

        steps = []

        try:
            logger.info(f"Scanning for secrets: {repo_path}")
            steps.append("scan_secrets")

            if not file_extensions:
                file_extensions = ['.py', '.js', '.ts', '.java', '.go', '.rs', '.cpp', '.c', '.h', '.yml', '.yaml', '.json', '.env', '.sh', '.rb', '.php']

            secrets_found = []
            files_scanned = 0

            # Walk through repository
            for root, dirs, files in os.walk(repo_path):
                # Skip common non-source directories
                dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', 'venv', '__pycache__', '.venv', 'dist', 'build']]

                for filename in files:
                    if any(filename.endswith(ext) for ext in file_extensions):
                        file_path = os.path.join(root, filename)
                        relative_path = os.path.relpath(file_path, repo_path)

                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                lines = content.split('\n')

                            files_scanned += 1

                            # Check each pattern
                            for secret_type, patterns in self.SECRET_PATTERNS.items():
                                for pattern in patterns:
                                    for line_num, line in enumerate(lines, 1):
                                        matches = re.finditer(pattern, line, re.IGNORECASE)
                                        for match in matches:
                                            secrets_found.append({
                                                "file_path": relative_path,
                                                "line_number": line_num,
                                                "line_content": line.strip(),
                                                "secret_type": secret_type,
                                                "match": match.group(0)[:50] + "..." if len(match.group(0)) > 50 else match.group(0),
                                                "severity": "high" if secret_type in ["private_key", "aws_key", "database_url"] else "medium",
                                            })

                        except Exception as e:
                            logger.warning(f"Error reading file {file_path}: {e}")

            # Store results
            self._secrets_found = secrets_found

            # Severity summary
            severity_summary = {"high": 0, "medium": 0, "low": 0}
            for secret in secrets_found:
                severity_summary[secret["severity"]] += 1

            return SkillResult(
                success=True,
                data={
                    "repo_path": repo_path,
                    "files_scanned": files_scanned,
                    "secrets_found": len(secrets_found),
                    "secrets": secrets_found,
                    "severity_summary": severity_summary,
                    "by_type": self._group_by_type(secrets_found),
                },
                steps_executed=steps
            )

        except Exception as e:
            logger.error(f"Secret detection failed: {e}")
            return SkillResult(
                success=False,
                error=str(e),
                steps_executed=steps
            )

    def _group_by_type(self, secrets: List[Dict]) -> Dict[str, int]:
        """Group secrets by type"""
        result = {}
        for secret in secrets:
            secret_type = secret["secret_type"]
            result[secret_type] = result.get(secret_type, 0) + 1
        return result

    def get_secrets_history(self) -> List[Dict]:
        """Get history of detected secrets"""
        return self._secrets_found.copy()


@skill(
    name="vulnerability_scan",
    description="Scan dependencies for known security vulnerabilities",
    category=SkillCategory.SCAN,
    version="1.0.0",
    author="TypoAgent",
    required_tools=["read_file"],
    tags=["security", "vulnerability", "dependency", "cve"],
    examples=[
        {
            "input": {"repo_path": "./repos/solidity", "package_file": "package.json"},
            "output": "Vulnerability scan report"
        }
    ]
)
class VulnerabilityScanSkill(BaseSkill):
    """
    Skill for scanning dependencies for known vulnerabilities

    Checks package.json, requirements.txt, Cargo.toml, etc. for vulnerable dependencies.
    """

    def __init__(self, metadata):
        super().__init__(metadata)
        self._vulnerabilities: List[Dict] = []

    async def execute(
        self,
        context: SkillContext,
        repo_path: str,
        check_updates: bool = True,
    ) -> SkillResult:
        """
        Scan for vulnerable dependencies

        Args:
            context: Skill context
            repo_path: Path to repository
            check_updates: Whether to check for available updates

        Returns:
            Vulnerability scan result
        """
        import os
        import json

        steps = []
        vulnerabilities = []

        try:
            logger.info(f"Scanning for vulnerabilities: {repo_path}")
            steps.append("scan_dependencies")

            # Check for various package files
            package_files = {
                "package.json": self._scan_npm,
                "requirements.txt": self._scan_pip,
                "Pipfile": self._scan_pipfile,
                "Cargo.toml": self._scan_cargo,
                "go.mod": self._scan_go,
                "Gemfile": self._scan_gem,
            }

            for filename, scanner in package_files.items():
                file_path = os.path.join(repo_path, filename)
                if os.path.exists(file_path):
                    logger.info(f"Found {filename}, scanning...")
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        result = await scanner(file_path, content)
                        if result:
                            vulnerabilities.extend(result)
                    except Exception as e:
                        logger.warning(f"Error scanning {filename}: {e}")

            steps.append("analyze_results")

            # Group by severity
            severity_count = {"critical": 0, "high": 0, "medium": 0, "low": 0}
            for vuln in vulnerabilities:
                severity = vuln.get("severity", "medium").lower()
                if severity in severity_count:
                    severity_count[severity] += 1

            self._vulnerabilities = vulnerabilities

            return SkillResult(
                success=True,
                data={
                    "repo_path": repo_path,
                    "vulnerabilities_found": len(vulnerabilities),
                    "vulnerabilities": vulnerabilities,
                    "severity_count": severity_count,
                    "by_package": self._group_by_package(vulnerabilities),
                },
                steps_executed=steps
            )

        except Exception as e:
            logger.error(f"Vulnerability scan failed: {e}")
            return SkillResult(
                success=False,
                error=str(e),
                steps_executed=steps
            )

    async def _scan_npm(self, file_path: str, content: str) -> List[Dict]:
        """Scan npm package.json for vulnerabilities"""
        import json
        vulnerabilities = []

        try:
            data = json.loads(content)
            dependencies = {**data.get("dependencies", {}), **data.get("devDependencies", {})}

            # Check for known vulnerable packages (simplified check)
            known_vulns = {
                "lodash": ["<4.17.21"],
                "minimist": ["<1.2.6"],
                "axios": ["<0.21.1"],
                "express": ["<4.17.3"],
                "debug": ["<4.3.1"],
            }

            for pkg, version in dependencies.items():
                if pkg in known_vulns:
                    vulnerabilities.append({
                        "package": pkg,
                        "current_version": version,
                        "file": file_path,
                        "type": "npm",
                        "severity": "medium",
                        "description": f"Potentially vulnerable version of {pkg}",
                        "recommendation": f"Update {pkg} to latest version",
                    })

        except json.JSONDecodeError:
            pass

        return vulnerabilities

    async def _scan_pip(self, file_path: str, content: str) -> List[Dict]:
        """Scan Python requirements.txt"""
        vulnerabilities = []
        known_vulns = {
            "requests": ["<2.25.0"],
            "urllib3": ["<1.26.0"],
            "django": ["<3.1.13"],
            "flask": ["<1.0.0"],
            "jinja2": ["<2.11.3"],
        }

        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                pkg_name = line.split('==')[0].split('>=')[0].split('<')[0].strip()
                if pkg_name in known_vulns:
                    vulnerabilities.append({
                        "package": pkg_name,
                        "current_version": line,
                        "file": file_path,
                        "type": "pip",
                        "severity": "medium",
                        "description": f"Potentially vulnerable version of {pkg_name}",
                    })

        return vulnerabilities

    async def _scan_pipfile(self, file_path: str, content: str) -> List[Dict]:
        """Scan Pipfile"""
        return []  # Simplified

    async def _scan_cargo(self, file_path: str, content: str) -> List[Dict]:
        """Scan Cargo.toml"""
        return []  # Simplified

    async def _scan_go(self, file_path: str, content: str) -> List[Dict]:
        """Scan go.mod"""
        return []  # Simplified

    async def _scan_gem(self, file_path: str, content: str) -> List[Dict]:
        """Scan Gemfile"""
        return []  # Simplified

    def _group_by_package(self, vulnerabilities: List[Dict]) -> Dict[str, List[Dict]]:
        """Group vulnerabilities by package"""
        result = {}
        for vuln in vulnerabilities:
            pkg = vuln.get("package", "unknown")
            if pkg not in result:
                result[pkg] = []
            result[pkg].append(vuln)
        return result


@skill(
    name="insecure_pattern",
    description="Detect insecure code patterns and anti-patterns",
    category=SkillCategory.SCAN,
    version="1.0.0",
    author="TypoAgent",
    required_tools=["scan_local_repo", "read_file"],
    tags=["security", "pattern", "insecure", "best-practice"],
    examples=[
        {
            "input": {"repo_path": "./repos/solidity", "language": "python"},
            "output": "Insecure patterns found"
        }
    ]
)
class InsecurePatternSkill(BaseSkill):
    """
    Skill for detecting insecure code patterns

    Identifies common security anti-patterns like SQL injection, XSS, weak crypto, etc.
    """

    # Language-specific insecure patterns
    PATTERNS = {
        "python": {
            "sql_injection": [
                r'execute\s*\(\s*["\'].*%s',
                r'execute\s*\(\s*f["\']',
                r'\.format\s*\([^)]*\)\s*.*SELECT|INSERT|UPDATE|DELETE',
            ],
            "eval_danger": [
                r'eval\s*\(',
                r'exec\s*\(',
            ],
            "weak_crypto": [
                r'md5\s*\(',
                r'sha1\s*\(',
                r'hashlib\.md5',
                r'hashlib\.sha1',
            ],
            "hardcoded_ip": [
                r'\b(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b',
            ],
        },
        "javascript": {
            "xss_vulnerable": [
                r'innerHTML\s*=',
                r'document\.write\s*\(',
                r'eval\s*\(',
            ],
            "prototype_pollution": [
                r'\_\_proto\_\_',
                r'constructor\s*\[\s*["\']prototype',
            ],
        },
        "general": {
            "disabled_security": [
                r'ssl_verify.*false',
                r'verify.*false.*ssl',
                r'DisableSecurity',
                r'skip.*verify',
            ],
            "todo_security": [
                r'TODO.*security',
                r'FIXME.*security',
                r'HACK.*security',
                r'XXX.*security',
            ],
        }
    }

    def __init__(self, metadata):
        super().__init__(metadata)
        self._patterns_found: List[Dict] = []

    async def execute(
        self,
        context: SkillContext,
        repo_path: str,
        languages: Optional[List[str]] = None,
    ) -> SkillResult:
        """
        Scan for insecure patterns

        Args:
            context: Skill context
            repo_path: Path to repository
            languages: Languages to check (default: auto-detect)

        Returns:
            Patterns found
        """
        import re
        import os

        steps = []

        try:
            logger.info(f"Scanning for insecure patterns: {repo_path}")
            steps.append("scan_patterns")

            patterns_found = []
            files_scanned = 0

            # Auto-detect languages if not specified
            if not languages:
                languages = self._detect_languages(repo_path)

            for root, dirs, files in os.walk(repo_path):
                dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', 'venv', '__pycache__']]

                for filename in files:
                    file_path = os.path.join(root, filename)
                    relative_path = os.path.relpath(file_path, repo_path)

                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            lines = content.split('\n')

                        files_scanned += 1

                        # Check patterns for each language
                        for lang in languages:
                            if lang in self.PATTERNS:
                                for pattern_name, patterns in self.PATTERNS[lang].items():
                                    for pattern in patterns:
                                        for line_num, line in enumerate(lines, 1):
                                            if re.search(pattern, line, re.IGNORECASE):
                                                patterns_found.append({
                                                    "file_path": relative_path,
                                                    "line_number": line_num,
                                                    "line_content": line.strip()[:100],
                                                    "pattern_type": pattern_name,
                                                    "language": lang,
                                                    "severity": self._get_severity(pattern_name),
                                                })

                        # Check general patterns
                        for pattern_name, patterns in self.PATTERNS["general"].items():
                            for pattern in patterns:
                                for line_num, line in enumerate(lines, 1):
                                    if re.search(pattern, line, re.IGNORECASE):
                                        patterns_found.append({
                                            "file_path": relative_path,
                                            "line_number": line_num,
                                            "line_content": line.strip()[:100],
                                            "pattern_type": pattern_name,
                                            "language": "general",
                                            "severity": self._get_severity(pattern_name),
                                        })

                    except Exception as e:
                        logger.warning(f"Error reading file {file_path}: {e}")

            self._patterns_found = patterns_found

            return SkillResult(
                success=True,
                data={
                    "repo_path": repo_path,
                    "files_scanned": files_scanned,
                    "patterns_found": len(patterns_found),
                    "patterns": patterns_found,
                    "by_type": self._group_by_type(patterns_found),
                    "by_language": self._group_by_language(patterns_found),
                },
                steps_executed=steps
            )

        except Exception as e:
            logger.error(f"Pattern scan failed: {e}")
            return SkillResult(
                success=False,
                error=str(e),
                steps_executed=steps
            )

    def _detect_languages(self, repo_path: str) -> List[str]:
        """Auto-detect languages in repo"""
        languages = []
        if os.path.exists(os.path.join(repo_path, "package.json")):
            languages.append("javascript")
        if os.path.exists(os.path.join(repo_path, "requirements.txt")) or os.path.exists(os.path.join(repo_path, "setup.py")):
            languages.append("python")
        if os.path.exists(os.path.join(repo_path, "Cargo.toml")):
            languages.append("rust")
        if os.path.exists(os.path.join(repo_path, "go.mod")):
            languages.append("go")
        return languages if languages else ["python", "javascript"]

    def _get_severity(self, pattern_type: str) -> str:
        """Get severity for pattern type"""
        high = ["sql_injection", "xss_vulnerable", "eval_danger", "disabled_security"]
        medium = ["weak_crypto", "prototype_pollution", "hardcoded_ip"]
        if pattern_type in high:
            return "high"
        elif pattern_type in medium:
            return "medium"
        return "low"

    def _group_by_type(self, patterns: List[Dict]) -> Dict[str, int]:
        """Group by pattern type"""
        result = {}
        for p in patterns:
            t = p["pattern_type"]
            result[t] = result.get(t, 0) + 1
        return result

    def _group_by_language(self, patterns: List[Dict]) -> Dict[str, int]:
        """Group by language"""
        result = {}
        for p in patterns:
            lang = p["language"]
            result[lang] = result.get(lang, 0) + 1
        return result


@skill(
    name="hardcoded_credential",
    description="Detect hardcoded credentials and tokens in source code",
    category=SkillCategory.SCAN,
    version="1.0.0",
    author="TypoAgent",
    required_tools=["scan_local_repo", "read_file"],
    tags=["security", "credential", "hardcoded", "password"],
    examples=[
        {
            "input": {"repo_path": "./repos/solidity"},
            "output": "Hardcoded credentials found"
        }
    ]
)
class HardcodedCredentialSkill(BaseSkill):
    """
    Skill specifically for detecting hardcoded credentials

    Focuses on passwords, tokens, and sensitive configuration in code.
    """

    CREDENTIAL_PATTERNS = [
        (r'password\s*=\s*["\'][^"\']+["\']', "hardcoded_password", "high"),
        (r'passwd\s*=\s*["\'][^"\']+["\']', "hardcoded_password", "high"),
        (r'secret\s*=\s*["\'][^"\']{8,}["\']', "hardcoded_secret", "high"),
        (r'token\s*=\s*["\'][^"\']{10,}["\']', "hardcoded_token", "high"),
        (r'api_key\s*=\s*["\'][^"\']{10,}["\']', "hardcoded_api_key", "high"),
        (r'auth_token\s*=\s*["\'][^"\']{10,}["\']', "hardcoded_auth_token", "high"),
        (r'access_token\s*=\s*["\'][^"\']{10,}["\']', "hardcoded_access_token", "high"),
        (r'private_key\s*=\s*["\'][^"\']+["\']', "hardcoded_private_key", "critical"),
        (r'admin.*password', "admin_password", "critical"),
        (r'root.*password', "root_password", "critical"),
    ]

    def __init__(self, metadata):
        super().__init__(metadata)
        self._credentials_found: List[Dict] = []

    async def execute(
        self,
        context: SkillContext,
        repo_path: str,
        exclude_tests: bool = True,
    ) -> SkillResult:
        """
        Scan for hardcoded credentials

        Args:
            context: Skill context
            repo_path: Path to repository
            exclude_tests: Whether to exclude test files

        Returns:
            Credentials found
        """
        import re
        import os

        steps = []

        try:
            logger.info(f"Scanning for hardcoded credentials: {repo_path}")
            steps.append("scan_credentials")

            credentials_found = []
            files_scanned = 0

            for root, dirs, files in os.walk(repo_path):
                dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', 'venv', '__pycache__']]

                for filename in files:
                    # Skip test files if requested
                    if exclude_tests and ('test' in filename.lower() or 'spec' in filename.lower()):
                        continue

                    if filename.endswith(('.py', '.js', '.ts', '.java', '.go', '.rs', '.cpp', '.c', '.h', '.yml', '.yaml', '.json', '.env')):
                        file_path = os.path.join(root, filename)
                        relative_path = os.path.relpath(file_path, repo_path)

                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                lines = content.split('\n')

                            files_scanned += 1

                            for pattern, cred_type, severity in self.CREDENTIAL_PATTERNS:
                                for line_num, line in enumerate(lines, 1):
                                    if re.search(pattern, line, re.IGNORECASE):
                                        # Check if it's not a placeholder
                                        if not self._is_placeholder(line):
                                            credentials_found.append({
                                                "file_path": relative_path,
                                                "line_number": line_num,
                                                "credential_type": cred_type,
                                                "severity": severity,
                                                "line_preview": line.strip()[:80] + "..." if len(line.strip()) > 80 else line.strip(),
                                            })

                        except Exception as e:
                            logger.warning(f"Error reading file {file_path}: {e}")

            self._credentials_found = credentials_found

            return SkillResult(
                success=True,
                data={
                    "repo_path": repo_path,
                    "files_scanned": files_scanned,
                    "credentials_found": len(credentials_found),
                    "credentials": credentials_found,
                    "by_type": self._group_by_type(credentials_found),
                    "by_severity": self._group_by_severity(credentials_found),
                },
                steps_executed=steps
            )

        except Exception as e:
            logger.error(f"Credential scan failed: {e}")
            return SkillResult(
                success=False,
                error=str(e),
                steps_executed=steps
            )

    def _is_placeholder(self, line: str) -> bool:
        """Check if the value is a placeholder"""
        placeholders = ['your_', 'example', 'placeholder', 'changeme', 'default', 'null', 'none', 'empty', 'todo', 'xxx', '***', 'fake', 'dummy', 'test']
        line_lower = line.lower()
        return any(p in line_lower for p in placeholders)

    def _group_by_type(self, credentials: List[Dict]) -> Dict[str, int]:
        """Group by credential type"""
        result = {}
        for c in credentials:
            t = c["credential_type"]
            result[t] = result.get(t, 0) + 1
        return result

    def _group_by_severity(self, credentials: List[Dict]) -> Dict[str, int]:
        """Group by severity"""
        result = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for c in credentials:
            s = c.get("severity", "medium")
            if s in result:
                result[s] += 1
        return result


@skill(
    name="dependency_audit",
    description="Audit and analyze project dependencies for risks",
    category=SkillCategory.ANALYSIS,
    version="1.0.0",
    author="TypoAgent",
    required_tools=["read_file"],
    tags=["security", "dependency", "audit", "risk"],
    examples=[
        {
            "input": {"repo_path": "./repos/solidity"},
            "output": "Dependency audit report"
        }
    ]
)
class DependencyAuditSkill(BaseSkill):
    """
    Skill for auditing dependencies

    Analyzes dependencies for:
    - Outdated packages
    - Unmaintained projects
    - License compatibility
    - Supply chain risks
    """

    def __init__(self, metadata):
        super().__init__(metadata)
        self._audit_results: List[Dict] = []

    async def execute(
        self,
        context: SkillContext,
        repo_path: str,
        check_outdated: bool = True,
        check_licenses: bool = True,
    ) -> SkillResult:
        """
        Audit dependencies

        Args:
            context: Skill context
            repo_path: Path to repository
            check_outdated: Check for outdated packages
            check_licenses: Check license compatibility

        Returns:
            Audit report
        """
        import os

        steps = []

        try:
            logger.info(f"Auditing dependencies: {repo_path}")
            steps.append("audit_dependencies")

            findings = []

            # Check various dependency files
            dep_files = [
                ("package.json", "npm"),
                ("requirements.txt", "pip"),
                ("Pipfile", "pipenv"),
                ("Cargo.toml", "cargo"),
                ("go.mod", "go"),
                ("Gemfile", "bundler"),
                ("composer.json", "composer"),
            ]

            for filename, pkg_manager in dep_files:
                file_path = os.path.join(repo_path, filename)
                if os.path.exists(file_path):
                    logger.info(f"Found {filename}")

                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()

                        # Parse and analyze
                        deps = self._parse_dependencies(filename, content)

                        finding = {
                            "file": filename,
                            "manager": pkg_manager,
                            "dependencies": len(deps),
                            "recommendations": [],
                        }

                        # Add recommendations
                        if len(deps) > 50:
                            finding["recommendations"].append(f"Large number of dependencies ({len(deps)}), consider auditing for unused packages")

                        # Check for known problematic packages
                        problematic = self._check_problematic(deps, pkg_manager)
                        if problematic:
                            finding["problematic"] = problematic

                        findings.append(finding)

                    except Exception as e:
                        logger.warning(f"Error analyzing {filename}: {e}")

            steps.append("analyze_results")

            self._audit_results = findings

            return SkillResult(
                success=True,
                data={
                    "repo_path": repo_path,
                    "dependency_files_found": len(findings),
                    "findings": findings,
                    "risk_level": self._calculate_risk(findings),
                },
                steps_executed=steps
            )

        except Exception as e:
            logger.error(f"Dependency audit failed: {e}")
            return SkillResult(
                success=False,
                error=str(e),
                steps_executed=steps
            )

    def _parse_dependencies(self, filename: str, content: str) -> List[Dict]:
        """Parse dependencies from file"""
        deps = []

        if filename == "package.json":
            try:
                import json
                data = json.loads(content)
                deps = list(data.get("dependencies", {}).keys())
                deps.extend(list(data.get("devDependencies", {}).keys()))
            except:
                pass

        elif filename == "requirements.txt":
            for line in content.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    deps.append(line.split('==')[0].split('>=')[0].strip())

        return [{"name": d} for d in deps]

    def _check_problematic(self, deps: List[Dict], pkg_manager: str) -> List[str]:
        """Check for known problematic packages"""
        problematic = {
            "npm": ["left-pad", "event-stream"],
            "pip": ["", ""],
        }

        found = []
        if pkg_manager in problematic:
            for dep in deps:
                if dep["name"] in problematic[pkg_manager]:
                    found.append(dep["name"])

        return found

    def _calculate_risk(self, findings: List[Dict]) -> str:
        """Calculate overall risk level"""
        if not findings:
            return "unknown"

        problematic_count = sum(len(f.get("problematic", [])) for f in findings)
        if problematic_count > 0:
            return "high"
        if len(findings) > 3:
            return "medium"
        return "low"


# MCP Client Skill
from .mcp_client_skill import MCPClientSkill, call_mcp_tool

__all__ = [
    "MCPClientSkill",
    "call_mcp_tool",
]
