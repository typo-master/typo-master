#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
拼写错误修复模块 - 用于修复确认的拼写错误
"""

import os
from typing import Dict, List, Any, Tuple, Set

from ..utils.logger import logger


class TypoFixer:
    """拼写错误修复类"""
    
    def __init__(self):
        """初始化拼写错误修复器"""
        pass
    
    def fix_typos(self, repo_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        修复仓库中的拼写错误
        
        Args:
            repo_info: 仓库信息，包含local_path和confirmed_typos
            
        Returns:
            带有修复结果的仓库信息
        """
        repo_path = repo_info["local_path"]
        confirmed_typos = repo_info.get("confirmed_typos", {})
        
        logger.info(f"修复仓库 {os.path.basename(repo_path)} 中的拼写错误")
        
        if not confirmed_typos:
            logger.warning("没有确认的拼写错误，跳过修复")
            repo_info["fixed_files"] = []
            repo_info["fixed_files_count"] = 0
            repo_info["fixes"] = {}
            return repo_info
        
        fixed_files = []
        fixes = {}
        
        for rel_file_path, typos in confirmed_typos.items():
            file_path = os.path.join(repo_path, rel_file_path)
            file_fixes = []
            
            try:
                # 读取文件内容
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                original_content = content
                
                # 修复每个拼写错误
                for typo, correction in typos:
                    if typo in content:
                        # 记录修复
                        file_fixes.append({
                            "typo": typo,
                            "correction": correction,
                            "count": content.count(typo)
                        })
                        
                        # 执行替换
                        content = content.replace(typo, correction)
                
                # 如果内容有变化，写回文件
                if content != original_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    fixed_files.append(rel_file_path)
                    fixes[rel_file_path] = file_fixes
                    logger.info(f"已修复文件: {rel_file_path}")
                
            except Exception as e:
                logger.error(f"修复文件 {file_path} 中的拼写错误时出错: {str(e)}")
        
        # 更新仓库信息
        repo_info["fixed_files"] = fixed_files
        repo_info["fixed_files_count"] = len(fixed_files)
        repo_info["fixes"] = fixes
        
        logger.info(f"共修复了 {len(fixed_files)} 个文件中的拼写错误")
        return repo_info
    
    def generate_fix_report(self, repo_info: Dict[str, Any]) -> str:
        """
        生成修复报告
        
        Args:
            repo_info: 仓库信息，包含fixes
            
        Returns:
            修复报告文本
        """
        fixes = repo_info.get("fixes", {})
        
        if not fixes:
            return "没有进行任何修复"
        
        report_lines = ["## 修复的拼写错误\n"]
        
        for file_path, file_fixes in fixes.items():
            report_lines.append(f"### {file_path}")
            
            for fix in file_fixes:
                typo = fix["typo"]
                correction = fix["correction"]
                count = fix["count"]
                report_lines.append(f"- 将 `{typo}` 修正为 `{correction}` ({count} 处)")
            
            report_lines.append("")
        
        return "\n".join(report_lines)
    
    def get_fixed_content_summary(self, repo_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取修复内容的摘要
        
        Args:
            repo_info: 仓库信息，包含fixes
            
        Returns:
            修复内容摘要，包括：
            - total_files: 修复的文件总数
            - total_fixes: 修复的错误总数
            - unique_typos: 修复的唯一错误类型
        """
        fixes = repo_info.get("fixes", {})
        
        total_files = len(fixes)
        total_fixes = 0
        unique_typos: Set[str] = set()
        
        for file_path, file_fixes in fixes.items():
            for fix in file_fixes:
                typo = fix["typo"]
                count = fix["count"]
                total_fixes += count
                unique_typos.add(typo)
        
        return {
            "total_files": total_files,
            "total_fixes": total_fixes,
            "unique_typos": len(unique_typos)
        } 