# Tool API Documentation

This document provides detailed API documentation for all tools available in the Web3 Typo Hunter Agent system.

## Table of Contents

- [GitHub Tools](#github-tools)
- [Git Tools](#git-tools)
- [Spell Tools](#spell-tools)
- [File Tools](#file-tools)
- [PR Tools](#pr-tools)
- [Report Tools](#report-tools)

---

## GitHub Tools

### search_github_repos

Search for GitHub repositories.

**Parameters:**
- `query` (str): Search query
- `limit` (int, optional): Maximum number of results (default: 100)
- `sort` (str, optional): Sort field (default: "updated")
- `order` (str, optional): Sort order (default: "desc")
- `token` (str, optional): GitHub API token

**Returns:**
```python
{
    "success": bool,
    "data": List[Dict[str, Any]],  # List of repositories
    "error": Optional[str]
}
```

**Example:**
```python
from src.tools import search_github_repos

result = await search_github_repos(
    query="topic:blockchain pushed:>2024-01-01 stars:>100",
    limit=50,
    token="YOUR_TOKEN"
)
```

---

### get_github_repo

Get detailed information about a GitHub repository.

**Parameters:**
- `owner` (str): Repository owner
- `repo` (str): Repository name
- `token` (str, optional): GitHub API token

**Returns:**
```python
{
    "success": bool,
    "data": Dict[str, Any],  # Repository details
    "error": Optional[str]
}
```

**Example:**
```python
from src.tools import get_github_repo

result = await get_github_repo(
    owner="ethereum",
    repo="solidity",
    token="YOUR_TOKEN"
)
```

---

### list_pull_requests

List pull requests for a repository.

**Parameters:**
- `owner` (str): Repository owner
- `repo` (str): Repository name
- `state` (str, optional): PR state (default: "open")
- `limit` (int, optional): Maximum number of results (default: 100)
- `token` (str, optional): GitHub API token

**Returns:**
```python
{
    "success": bool,
    "data": List[Dict[str, Any]],  # List of PRs
    "error": Optional[str]
}
```

---

### create_pull_request

Create a pull request.

**Parameters:**
- `owner` (str): Repository owner
- `repo` (str): Repository name
- `title` (str): PR title
- `head` (str): Head branch
- `base` (str): Base branch
- `body` (str, optional): PR description
- `token` (str, optional): GitHub API token

**Returns:**
```python
{
    "success": bool,
    "data": Dict[str, Any],  # Created PR data
    "error": Optional[str]
}
```

---

### get_file_contents

Get file contents from a repository.

**Parameters:**
- `owner` (str): Repository owner
- `repo` (str): Repository name
- `path` (str): File path
- `ref` (str, optional): Git reference
- `token` (str, optional): GitHub API token

**Returns:**
```python
{
    "success": bool,
    "data": Dict[str, Any],  # File contents
    "error": Optional[str]
}
```

---

### update_file

Update a file in a repository.

**Parameters:**
- `owner` (str): Repository owner
- `repo` (str): Repository name
- `path` (str): File path
- `content` (str): File content (base64 encoded)
- `message` (str): Commit message
- `sha` (str): Current file SHA
- `branch` (str, optional): Branch name
- `token` (str, optional): GitHub API token

**Returns:**
```python
{
    "success": bool,
    "data": Dict[str, Any],  # Updated file data
    "error": Optional[str]
}
```

---

### create_branch

Create a new branch.

**Parameters:**
- `owner` (str): Repository owner
- `repo` (str): Repository name
- `branch` (str): Branch name
- `sha` (str): Commit SHA
- `token` (str, optional): GitHub API token

**Returns:**
```python
{
    "success": bool,
    "data": Dict[str, Any],  # Created branch data
    "error": Optional[str]
}
```

---

### get_default_branch

Get the default branch of a repository.

**Parameters:**
- `owner` (str): Repository owner
- `repo` (str): Repository name
- `token` (str, optional): GitHub API token

**Returns:**
```python
{
    "success": bool,
    "data": str,  # Default branch name
    "error": Optional[str]
}
```

---

## Git Tools

### git_clone

Clone a Git repository.

**Parameters:**
- `url` (str): Repository URL
- `destination` (str, optional): Destination path

**Returns:**
```python
{
    "success": bool,
    "data": str,  # Cloned repository path
    "error": Optional[str]
}
```

---

### git_checkout

Checkout a Git branch.

**Parameters:**
- `repo_path` (str): Repository path
- `branch` (str): Branch name

**Returns:**
```python
{
    "success": bool,
    "data": None,
    "error": Optional[str]
}
```

---

### git_create_branch

Create a new Git branch.

**Parameters:**
- `repo_path` (str): Repository path
- `branch` (str): Branch name
- `base` (str, optional): Base branch

**Returns:**
```python
{
    "success": bool,
    "data": None,
    "error": Optional[str]
}
```

---

### git_add

Stage files in Git.

**Parameters:**
- `repo_path` (str): Repository path
- `files` (List[str]): Files to stage

**Returns:**
```python
{
    "success": bool,
    "data": None,
    "error": Optional[str]
}
```

---

### git_commit

Commit changes in Git.

**Parameters:**
- `repo_path` (str): Repository path
- `message` (str): Commit message

**Returns:**
```python
{
    "success": bool,
    "data": None,
    "error": Optional[str]
}
```

---

### git_push

Push changes to remote.

**Parameters:**
- `repo_path` (str): Repository path
- `remote` (str, optional): Remote name (default: "origin")
- `branch` (str, optional): Branch name

**Returns:**
```python
{
    "success": bool,
    "data": None,
    "error": Optional[str]
}
```

---

### git_get_current_branch

Get current Git branch.

**Parameters:**
- `repo_path` (str): Repository path

**Returns:**
```python
{
    "success": bool,
    "data": str,  # Branch name
    "error": Optional[str]
}
```

---

### git_get_changes

Get changed files in Git.

**Parameters:**
- `repo_path` (str): Repository path

**Returns:**
```python
{
    "success": bool,
    "data": {
        "staged": List[str],
        "unstaged": List[str]
    },
    "error": Optional[str]
}
```

---

### git_get_file_content

Get file content from Git repository.

**Parameters:**
- `repo_path` (str): Repository path
- `file_path` (str): File path

**Returns:**
```python
{
    "success": bool,
    "data": str,  # File content
    "error": Optional[str]
}
```

---

### git_update_file

Update file content in Git repository.

**Parameters:**
- `repo_path` (str): Repository path
- `file_path` (str): File path
- `content` (str): New content

**Returns:**
```python
{
    "success": bool,
    "data": None,
    "error": Optional[str]
}
```

---

## Spell Tools

### check_spelling

Check text for spelling errors.

**Parameters:**
- `text` (str): Text to check

**Returns:**
```python
{
    "success": bool,
    "data": List[Dict[str, str]],  # List of {typo, correction}
    "error": Optional[str]
}
```

**Example:**
```python
from src.tools import check_spelling

result = await check_spelling(text="This is a test with some typos")
```

---

### correct_spelling

Correct spelling errors in text.

**Parameters:**
- `text` (str): Text to correct

**Returns:**
```python
{
    "success": bool,
    "data": str,  # Corrected text
    "error": Optional[str]
}
```

---

### get_spelling_suggestions

Get spelling suggestions for a word.

**Parameters:**
- `word` (str): Word to get suggestions for
- `max_suggestions` (int, optional): Maximum suggestions (default: 5)

**Returns:**
```python
{
    "success": bool,
    "data": List[str],  # List of suggestions
    "error": Optional[str]
}
```

---

### is_web3_term

Check if a word is a Web3 term.

**Parameters:**
- `word` (str): Word to check

**Returns:**
```python
{
    "success": bool,
    "data": bool,  # True if Web3 term
    "error": Optional[str]
}
```

---

### check_file_spelling

Check spelling in a file.

**Parameters:**
- `file_path` (str): Path to file

**Returns:**
```python
{
    "success": bool,
    "data": {
        "file": str,
        "errors": List[Dict[str, str]],
        "error_count": int
    },
    "error": Optional[str]
}
```

---

## File Tools

### read_file

Read content from a file.

**Parameters:**
- `file_path` (str): Path to file
- `encoding` (str, optional): File encoding (default: "utf-8")

**Returns:**
```python
{
    "success": bool,
    "data": str,  # File content
    "error": Optional[str]
}
```

---

### write_file

Write content to a file.

**Parameters:**
- `file_path` (str): Path to file
- `content` (str): Content to write
- `encoding` (str, optional): File encoding (default: "utf-8")

**Returns:**
```python
{
    "success": bool,
    "data": str,  # Success message
    "error": Optional[str]
}
```

---

### list_files

List files in a directory.

**Parameters:**
- `directory` (str): Directory path
- `pattern` (str, optional): File pattern
- `recursive` (bool, optional): Search recursively (default: False)

**Returns:**
```python
{
    "success": bool,
    "data": List[str],  # List of file paths
    "error": Optional[str]
}
```

---

### file_exists

Check if a file exists.

**Parameters:**
- `file_path` (str): Path to file

**Returns:**
```python
{
    "success": bool,
    "data": bool,  # True if exists
    "error": Optional[str]
}
```

---

### delete_file

Delete a file.

**Parameters:**
- `file_path` (str): Path to file

**Returns:**
```python
{
    "success": bool,
    "data": str,  # Success message
    "error": Optional[str]
}
```

---

### create_directory

Create a directory.

**Parameters:**
- `directory` (str): Directory path
- `parents` (bool, optional): Create parent directories (default: True)

**Returns:**
```python
{
    "success": bool,
    "data": str,  # Success message
    "error": Optional[str]
}
```

---

### get_file_info

Get file information.

**Parameters:**
- `file_path` (str): Path to file

**Returns:**
```python
{
    "success": bool,
    "data": {
        "size": int,
        "modified": float,
        "created": float,
        "type": str,
        "extension": str
    },
    "error": Optional[str]
}
```

---

### search_files

Search for files containing text.

**Parameters:**
- `directory` (str): Directory to search
- `search_text` (str): Text to search for
- `pattern` (str, optional): File pattern
- `case_sensitive` (bool, optional): Case sensitive (default: False)

**Returns:**
```python
{
    "success": bool,
    "data": List[str],  # List of matching files
    "error": Optional[str]
}
```

---

### replace_in_file

Replace text in a file.

**Parameters:**
- `file_path` (str): Path to file
- `old_text` (str): Text to replace
- `new_text` (str): Replacement text
- `count` (int, optional): Number of replacements (default: -1 for all)

**Returns:**
```python
{
    "success": bool,
    "data": str,  # Success message
    "error": Optional[str]
}
```

---

## PR Tools

### create_pr

Create a pull request.

**Parameters:**
- `owner` (str): Repository owner
- `repo` (str): Repository name
- `title` (str): PR title
- `head` (str): Head branch
- `base` (str): Base branch
- `body` (str, optional): PR description
- `token` (str, optional): GitHub token

**Returns:**
```python
{
    "success": bool,
    "data": {
        "pr_number": int,
        "url": str,
        "title": str,
        "state": str,
        "created_at": str
    },
    "error": Optional[str]
}
```

---

### generate_pr_title

Generate a PR title from changes.

**Parameters:**
- `changes` (List[Dict]): List of changes

**Returns:**
```python
{
    "success": bool,
    "data": str,  # Generated title
    "error": Optional[str]
}
```

---

### generate_pr_body

Generate a PR description from changes.

**Parameters:**
- `changes` (List[Dict]): List of changes

**Returns:**
```python
{
    "success": bool,
    "data": str,  # Generated body
    "error": Optional[str]
}
```

---

### prepare_pr

Prepare all components for creating a PR.

**Parameters:**
- `owner` (str): Repository owner
- `repo` (str): Repository name
- `changes` (List[Dict]): List of changes
- `token` (str, optional): GitHub token

**Returns:**
```python
{
    "success": bool,
    "data": {
        "title": str,
        "body": str,
        "ready": bool
    },
    "error": Optional[str]
}
```

---

### validate_pr

Validate a pull request before creation.

**Parameters:**
- `title` (str): PR title
- `body` (str): PR body
- `changes` (List[Dict]): List of changes

**Returns:**
```python
{
    "success": bool,
    "data": {
        "valid": bool,
        "errors": List[str]
    },
    "error": Optional[str]
}
```

---

### format_pr_description

Format PR description with proper markdown.

**Parameters:**
- `description` (str): Description text
- `template` (str, optional): Optional template

**Returns:**
```python
{
    "success": bool,
    "data": str,  # Formatted description
    "error": Optional[str]
}
```

---

## Report Tools

### generate_csv_report

Generate a CSV report.

**Parameters:**
- `data` (List[Dict]): Data to report
- `columns` (List[str]): Column names
- `output_file` (str): Output file path

**Returns:**
```python
{
    "success": bool,
    "data": str,  # Success message
    "error": Optional[str]
}
```

---

### generate_json_report

Generate a JSON report.

**Parameters:**
- `data` (Dict): Data to report
- `output_file` (str): Output file path
- `indent` (int, optional): JSON indentation (default: 2)

**Returns:**
```python
{
    "success": bool,
    "data": str,  # Success message
    "error": Optional[str]
}
```

---

### generate_markdown_report

Generate a Markdown report.

**Parameters:**
- `title` (str): Report title
- `sections` (List[Dict]): List of {title, content} sections
- `output_file` (str): Output file path

**Returns:**
```python
{
    "success": bool,
    "data": str,  # Success message
    "error": Optional[str]
}
```

---

### generate_html_report

Generate an HTML report.

**Parameters:**
- `title` (str): Report title
- `content` (str): HTML content
- `output_file` (str): Output file path

**Returns:**
```python
{
    "success": bool,
    "data": str,  # Success message
    "error": Optional[str]
}
```

---

### generate_summary_report

Generate a summary report from data.

**Parameters:**
- `data` (Dict): Data to summarize
- `output_file` (str): Output file path
- `format` (str, optional): Report format (default: "json")

**Returns:**
```python
{
    "success": bool,
    "data": str,  # Success message
    "error": Optional[str]
}
```

---

### generate_typo_fix_report

Generate a typo fix report.

**Parameters:**
- `results` (List[Dict]): Typo fix results
- `output_file` (str): Output file path

**Returns:**
```python
{
    "success": bool,
    "data": str,  # Success message
    "error": Optional[str]
}
```

---

## Error Handling

All tools return results in a consistent format:

```python
{
    "success": bool,
    "data": Any,  # Result data if successful
    "error": Optional[str]  # Error message if failed
}
```

Always check the `success` field before accessing `data`.

## Tool Categories

Tools are organized into categories:

- `ToolCategory.GITHUB` - GitHub API operations
- `ToolCategory.GIT` - Git operations
- `ToolCategory.SPELL_CHECK` - Spell checking
- `ToolCategory.FILE` - File operations
- `ToolCategory.PR` - Pull request operations
- `ToolCategory.REPORT` - Report generation
- `ToolCategory.UTILITY` - Utility functions

## Tool Metadata

Each tool has metadata including:
- `name`: Tool name
- `description`: Tool description
- `category`: Tool category
- `examples`: Usage examples

You can access tool metadata through the ToolRegistry:

```python
from src.agent_framework import ToolRegistry

registry = ToolRegistry()
metadata = registry.get_tool_metadata("search_github_repos")
print(metadata.description)
```
