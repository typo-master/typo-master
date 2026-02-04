"""
File Tools - File Operations

This module provides tools for file operations.
"""

import os
from typing import Any, Dict, List, Optional
from pathlib import Path

from ..agent_framework.tool_system import tool, ToolCategory
from ..agent_framework.logger import get_logger

logger = get_logger(__name__)


@tool(
    name="read_file",
    description="Read content from a file",
    category=ToolCategory.FILE,
    examples=[
        {
            "input": {"file_path": "/path/to/file.txt"},
            "output": "File content"
        }
    ]
)
async def read_file(
    file_path: str,
    encoding: str = "utf-8",
) -> str:
    """
    Read content from a file
    
    Args:
        file_path: Path to file
        encoding: File encoding
        
    Returns:
        File content
    """
    with open(file_path, 'r', encoding=encoding) as f:
        return f.read()


@tool(
    name="write_file",
    description="Write content to a file",
    category=ToolCategory.FILE,
    examples=[
        {
            "input": {"file_path": "/path/to/file.txt", "content": "Hello, World!"},
            "output": "Written to file"
        }
    ]
)
async def write_file(
    file_path: str,
    content: str,
    encoding: str = "utf-8",
) -> str:
    """
    Write content to a file
    
    Args:
        file_path: Path to file
        content: Content to write
        encoding: File encoding
        
    Returns:
        Success message
    """
    # Create directory if it doesn't exist
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, 'w', encoding=encoding) as f:
        f.write(content)
    
    return f"Written to {file_path}"


@tool(
    name="list_files",
    description="List files in a directory",
    category=ToolCategory.FILE,
    examples=[
        {
            "input": {"directory": "/path/to/dir"},
            "output": ["file1.txt", "file2.txt"]
        }
    ]
)
async def list_files(
    directory: str,
    pattern: Optional[str] = None,
    recursive: bool = False,
) -> List[str]:
    """
    List files in a directory
    
    Args:
        directory: Directory path
        pattern: Optional file pattern
        recursive: Whether to search recursively
        
    Returns:
        List of file paths
    """
    path = Path(directory)
    
    if recursive:
        if pattern:
            files = [str(f) for f in path.rglob(pattern)]
        else:
            files = [str(f) for f in path.rglob("*")]
    else:
        if pattern:
            files = [str(f) for f in path.glob(pattern)]
        else:
            files = [str(f) for f in path.glob("*")]
    
    # Filter only files (not directories)
    files = [f for f in files if Path(f).is_file()]
    
    return files


@tool(
    name="file_exists",
    description="Check if a file exists",
    category=ToolCategory.FILE,
    examples=[
        {
            "input": {"file_path": "/path/to/file.txt"},
            "output": True
        }
    ]
)
async def file_exists(
    file_path: str,
) -> bool:
    """
    Check if a file exists
    
    Args:
        file_path: Path to file
        
    Returns:
        True if file exists
    """
    return Path(file_path).exists()


@tool(
    name="delete_file",
    description="Delete a file",
    category=ToolCategory.FILE,
    examples=[
        {
            "input": {"file_path": "/path/to/file.txt"},
            "output": "Deleted file"
        }
    ]
)
async def delete_file(
    file_path: str,
) -> str:
    """
    Delete a file
    
    Args:
        file_path: Path to file
        
    Returns:
        Success message
    """
    Path(file_path).unlink()
    return f"Deleted {file_path}"


@tool(
    name="create_directory",
    description="Create a directory",
    category=ToolCategory.FILE,
    examples=[
        {
            "input": {"directory": "/path/to/dir"},
            "output": "Created directory"
        }
    ]
)
async def create_directory(
    directory: str,
    parents: bool = True,
) -> str:
    """
    Create a directory
    
    Args:
        directory: Directory path
        parents: Whether to create parent directories
        
    Returns:
        Success message
    """
    Path(directory).mkdir(parents=parents, exist_ok=True)
    return f"Created directory {directory}"


@tool(
    name="get_file_info",
    description="Get file information",
    category=ToolCategory.FILE,
    examples=[
        {
            "input": {"file_path": "/path/to/file.txt"},
            "output": {"size": 1024, "modified": "...", "type": "file"}
        }
    ]
)
async def get_file_info(
    file_path: str,
) -> Dict[str, Any]:
    """
    Get file information
    
    Args:
        file_path: Path to file
        
    Returns:
        File information dictionary
    """
    path = Path(file_path)
    stat = path.stat()
    
    return {
        "size": stat.st_size,
        "modified": stat.st_mtime,
        "created": stat.st_ctime,
        "type": "file" if path.is_file() else "directory",
        "extension": path.suffix,
    }


@tool(
    name="search_files",
    description="Search for files containing text",
    category=ToolCategory.FILE,
    examples=[
        {
            "input": {"directory": "/path/to/dir", "search_text": "hello"},
            "output": ["/path/to/dir/file1.txt", "/path/to/dir/file2.txt"]
        }
    ]
)
async def search_files(
    directory: str,
    search_text: str,
    pattern: Optional[str] = None,
    case_sensitive: bool = False,
) -> List[str]:
    """
    Search for files containing text
    
    Args:
        directory: Directory to search
        search_text: Text to search for
        pattern: Optional file pattern
        case_sensitive: Whether search is case sensitive
        
    Returns:
        List of file paths
    """
    matching_files = []
    path = Path(directory)
    
    # Get files to search
    if pattern:
        files = path.rglob(pattern)
    else:
        files = path.rglob("*")
    
    for file_path in files:
        if not file_path.is_file():
            continue
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            if case_sensitive:
                if search_text in content:
                    matching_files.append(str(file_path))
            else:
                if search_text.lower() in content.lower():
                    matching_files.append(str(file_path))
        
        except Exception as e:
            logger.warning(f"Error reading {file_path}: {e}")
    
    return matching_files


@tool(
    name="replace_in_file",
    description="Replace text in a file",
    category=ToolCategory.FILE,
    examples=[
        {
            "input": {
                "file_path": "/path/to/file.txt",
                "old_text": "hello",
                "new_text": "hi"
            },
            "output": "Replaced text in file"
        }
    ]
)
async def replace_in_file(
    file_path: str,
    old_text: str,
    new_text: str,
    count: int = -1,
) -> str:
    """
    Replace text in a file
    
    Args:
        file_path: Path to file
        old_text: Text to replace
        new_text: Replacement text
        count: Number of replacements (-1 for all)
        
    Returns:
        Success message
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = content.replace(old_text, new_text, count)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    return f"Replaced text in {file_path}"
