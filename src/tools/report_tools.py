"""
Report Tools - Report Generation

This module provides tools for generating reports.
"""

import json
import csv
from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path

from ..agent_framework.tool_system import tool, ToolCategory
from ..agent_framework.logger import get_logger

logger = get_logger(__name__)


@tool(
    name="generate_csv_report",
    description="Generate a CSV report",
    category=ToolCategory.REPORT,
    examples=[
        {
            "input": {
                "data": [{"name": "Project1", "stars": 100}],
                "columns": ["name", "stars"],
                "output_file": "report.csv"
            },
            "output": "Generated report.csv"
        }
    ]
)
async def generate_csv_report(
    data: List[Dict[str, Any]],
    columns: List[str],
    output_file: str,
) -> str:
    """
    Generate a CSV report
    
    Args:
        data: Data to report
        columns: Column names
        output_file: Output file path
        
    Returns:
        Success message
    """
    # Create directory if needed
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(data)
    
    return f"Generated CSV report: {output_file}"


@tool(
    name="generate_json_report",
    description="Generate a JSON report",
    category=ToolCategory.REPORT,
    examples=[
        {
            "input": {
                "data": {"projects": [...], "summary": "..."},
                "output_file": "report.json"
            },
            "output": "Generated report.json"
        }
    ]
)
async def generate_json_report(
    data: Dict[str, Any],
    output_file: str,
    indent: int = 2,
) -> str:
    """
    Generate a JSON report
    
    Args:
        data: Data to report
        output_file: Output file path
        indent: JSON indentation
        
    Returns:
        Success message
    """
    # Create directory if needed
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, default=str)
    
    return f"Generated JSON report: {output_file}"


@tool(
    name="generate_markdown_report",
    description="Generate a Markdown report",
    category=ToolCategory.REPORT,
    examples=[
        {
            "input": {
                "title": "Typo Fix Report",
                "sections": [{"title": "Summary", "content": "..."}],
                "output_file": "report.md"
            },
            "output": "Generated report.md"
        }
    ]
)
async def generate_markdown_report(
    title: str,
    sections: List[Dict[str, str]],
    output_file: str,
) -> str:
    """
    Generate a Markdown report
    
    Args:
        title: Report title
        sections: List of {title, content} sections
        output_file: Output file path
        
    Returns:
        Success message
    """
    # Create directory if needed
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    # Generate markdown
    markdown = f"# {title}\n\n"
    markdown += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    markdown += "---\n\n"
    
    for section in sections:
        section_title = section.get("title", "")
        section_content = section.get("content", "")
        
        markdown += f"## {section_title}\n\n{section_content}\n\n"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(markdown)
    
    return f"Generated Markdown report: {output_file}"


@tool(
    name="generate_summary_report",
    description="Generate a summary report from data",
    category=ToolCategory.REPORT,
    examples=[
        {
            "input": {
                "data": {"total_projects": 10, "typos_fixed": 50},
                "output_file": "summary.json"
            },
            "output": "Generated summary report"
        }
    ]
)
async def generate_summary_report(
    data: Dict[str, Any],
    output_file: str,
    format: str = "json",
) -> str:
    """
    Generate a summary report
    
    Args:
        data: Data to summarize
        output_file: Output file path
        format: Report format (json, csv, markdown)
        
    Returns:
        Success message
    """
    if format == "json":
        return await generate_json_report(data, output_file)
    elif format == "csv":
        # Convert dict to list of dicts for CSV
        csv_data = [{"key": k, "value": v} for k, v in data.items()]
        return await generate_csv_report(csv_data, ["key", "value"], output_file)
    elif format == "markdown":
        sections = [
            {
                "title": "Summary",
                "content": "\n".join(f"- {k}: {v}" for k, v in data.items())
            }
        ]
        return await generate_markdown_report("Summary Report", sections, output_file)
    else:
        raise ValueError(f"Unsupported format: {format}")


@tool(
    name="generate_typo_fix_report",
    description="Generate a typo fix report",
    category=ToolCategory.REPORT,
    examples=[
        {
            "input": {
                "results": [{"project": "Project1", "typos_fixed": 5}],
                "output_file": "typo_report.md"
            },
            "output": "Generated typo fix report"
        }
    ]
)
async def generate_typo_fix_report(
    results: List[Dict[str, Any]],
    output_file: str,
) -> str:
    """
    Generate a typo fix report
    
    Args:
        results: List of results
        output_file: Output file path
        
    Returns:
        Success message
    """
    # Calculate statistics
    total_projects = len(results)
    total_typos = sum(r.get("typos_fixed", 0) for r in results)
    total_files = sum(r.get("files_fixed", 0) for r in results)
    
    # Generate sections
    sections = [
        {
            "title": "Summary",
            "content": f"""
- Total projects processed: {total_projects}
- Total typos fixed: {total_typos}
- Total files modified: {total_files}
"""
        },
        {
            "title": "Project Details",
            "content": "\n".join(
                f"### {r.get('project', 'Unknown')}\n\n"
                f"- Typos fixed: {r.get('typos_fixed', 0)}\n"
                f"- Files modified: {r.get('files_fixed', 0)}\n"
                f"- PR created: {'Yes' if r.get('pr_created') else 'No'}\n"
                for r in results
            )
        },
    ]
    
    return await generate_markdown_report("Typo Fix Report", sections, output_file)


@tool(
    name="generate_html_report",
    description="Generate an HTML report",
    category=ToolCategory.REPORT,
    examples=[
        {
            "input": {
                "title": "Report",
                "content": "<h1>Report</h1>",
                "output_file": "report.html"
            },
            "output": "Generated report.html"
        }
    ]
)
async def generate_html_report(
    title: str,
    content: str,
    output_file: str,
) -> str:
    """
    Generate an HTML report
    
    Args:
        title: Report title
        content: HTML content
        output_file: Output file path
        
    Returns:
        Success message
    """
    # Create directory if needed
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
        }}
        h1 {{
            color: #333;
            border-bottom: 2px solid #333;
            padding-bottom: 10px;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }}
        th {{
            background-color: #f2f2f2;
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    {content}
    <p style="color: #666; font-size: 12px;">
        Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </p>
</body>
</html>
"""
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return f"Generated HTML report: {output_file}"
