"""
PR Tools - Pull Request Operations

This module provides tools for pull request operations.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from ..agent_framework.tool_system import tool, ToolCategory
from ..agent_framework.logger import get_logger

logger = get_logger(__name__)


@tool(
    name="create_pr",
    description="Create a pull request",
    category=ToolCategory.PR,
    examples=[
        {
            "input": {
                "owner": "ethereum",
                "repo": "solidity",
                "title": "Fix typo in README",
                "head": "fix-typo",
                "base": "main",
                "body": "Fixed spelling errors in README"
            },
            "output": {"pr_number": 123, "url": "..."}
        }
    ]
)
async def create_pr(
    owner: str,
    repo: str,
    title: str,
    head: str,
    base: str,
    body: str = "",
    token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a pull request
    
    Args:
        owner: Repository owner
        repo: Repository name
        title: PR title
        head: Head branch
        base: Base branch
        body: PR description
        token: GitHub token
        
    Returns:
        PR information
    """
    from .github_tools import create_pull_request as github_create_pr
    
    pr_data = await github_create_pr(
        owner=owner,
        repo=repo,
        title=title,
        head=head,
        base=base,
        body=body,
        token=token,
    )
    
    return {
        "pr_number": pr_data.get("number"),
        "url": pr_data.get("html_url"),
        "title": pr_data.get("title"),
        "state": pr_data.get("state"),
        "created_at": pr_data.get("created_at"),
    }


@tool(
    name="generate_pr_title",
    description="Generate a PR title from changes",
    category=ToolCategory.PR,
    examples=[
        {
            "input": {"changes": [{"file": "README.md", "typos": 5}]},
            "output": "Fix 5 typos in README.md"
        }
    ]
)
async def generate_pr_title(
    changes: List[Dict[str, Any]],
) -> str:
    """
    Generate a PR title from changes
    
    Args:
        changes: List of changes
        
    Returns:
        PR title
    """
    if not changes:
        return "Fix typos"
    
    # Count total typos
    total_typos = sum(c.get("typos", 0) for c in changes)
    
    # Get main files changed
    main_files = [c.get("file", "") for c in changes[:3]]
    main_files_str = ", ".join(main_files)
    
    if total_typos == 1:
        return f"Fix typo in {main_files[0]}"
    elif total_typos <= 5:
        return f"Fix {total_typos} typos in {main_files_str}"
    else:
        return f"Fix {total_typos} typos across multiple files"


@tool(
    name="generate_pr_body",
    description="Generate a PR description from changes",
    category=ToolCategory.PR,
    examples=[
        {
            "input": {"changes": [{"file": "README.md", "typos": [{"typo": "typo", "correction": "type"}]}]},
            "output": "## Summary\n\nFixed spelling errors..."
        }
    ]
)
async def generate_pr_body(
    changes: List[Dict[str, Any]],
) -> str:
    """
    Generate a PR description from changes
    
    Args:
        changes: List of changes
        
    Returns:
        PR description
    """
    if not changes:
        return "No changes made."
    
    total_typos = sum(c.get("typos", len(c.get("typos_list", []))) for c in changes)
    
    body = f"""## Summary

Fixed {total_typos} spelling error{'s' if total_typos != 1 else ''} in {len(changes)} file{'s' if len(changes) != 1 else ''}.

## Changes

"""
    
    for change in changes:
        file_path = change.get("file", "")
        typos_list = change.get("typos_list", [])
        
        if typos_list:
            body += f"### {file_path}\n\n"
            for typo_info in typos_list[:5]:  # Show first 5 typos
                typo = typo_info.get("typo", "")
                correction = typo_info.get("correction", "")
                body += f"- `{typo}` → `{correction}`\n"
            
            if len(typos_list) > 5:
                body += f"- ... and {len(typos_list) - 5} more\n"
            
            body += "\n"
    
    body += """## Testing

- [ ] Manual testing completed
- [ ] No breaking changes introduced

## Checklist

- [ ] Code follows project style guidelines
- [ ] Self-review of the code has been completed
- [ ] Comments have been added where necessary
"""
    
    return body


@tool(
    name="prepare_pr",
    description="Prepare all components for creating a PR",
    category=ToolCategory.PR,
    examples=[
        {
            "input": {
                "owner": "ethereum",
                "repo": "solidity",
                "changes": [...]
            },
            "output": {"title": "...", "body": "...", "ready": True}
        }
    ]
)
async def prepare_pr(
    owner: str,
    repo: str,
    changes: List[Dict[str, Any]],
    token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Prepare all components for creating a PR
    
    Args:
        owner: Repository owner
        repo: Repository name
        changes: List of changes
        token: GitHub token
        
    Returns:
        PR preparation data
    """
    title = await generate_pr_title(changes)
    body = await generate_pr_body(changes)
    
    return {
        "owner": owner,
        "repo": repo,
        "title": title,
        "body": body,
        "ready": True,
    }


@tool(
    name="validate_pr",
    description="Validate PR before creation",
    category=ToolCategory.PR,
    examples=[
        {
            "input": {"title": "Fix typo", "body": "...", "changes": [...]},
            "output": {"valid": True, "errors": []}
        }
    ]
)
async def validate_pr(
    title: str,
    body: str,
    changes: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Validate PR before creation
    
    Args:
        title: PR title
        body: PR body
        changes: List of changes
        
    Returns:
        Validation result
    """
    errors = []
    
    # Validate title
    if not title or len(title) < 5:
        errors.append("Title is too short")
    
    if not title or len(title) > 200:
        errors.append("Title is too long")
    
    # Validate body
    if not body or len(body) < 10:
        errors.append("Body is too short")
    
    # Validate changes
    if not changes:
        errors.append("No changes to commit")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }


@tool(
    name="format_pr_description",
    description="Format PR description with proper markdown",
    category=ToolCategory.PR,
    examples=[
        {
            "input": {"description": "Fixed typos"},
            "output": "## Summary\n\nFixed typos..."
        }
    ]
)
async def format_pr_description(
    description: str,
    template: Optional[str] = None,
) -> str:
    """
    Format PR description with proper markdown
    
    Args:
        description: Description text
        template: Optional template
        
    Returns:
        Formatted description
    """
    if template:
        # Apply template
        formatted = template.format(description=description)
    else:
        # Default template
        formatted = f"""## Summary

{description}

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing

- [ ] Unit tests
- [ ] Integration tests
- [ ] Manual testing

## Checklist

- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Comments added where necessary
"""
    
    return formatted
