#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
拼写错误扫描模块 - 负责扫描项目中的拼写错误
"""

import os
import pycorrector
from typing import Dict, List, Any, Tuple

from ..utils.logger import logger
from ..config.settings import SUPPORTED_EXTENSIONS, WEB3_TERMS


class TypoScanner:
    """拼写错误扫描类"""
    
    def __init__(self, max_file_size: int = 100000):
        """
        初始化扫描器
        
        Args:
            max_file_size: 最大文件大小限制（字节）
        """
        self.max_file_size = max_file_size
    
    def scan_repo(self, repo_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        扫描仓库中的拼写错误
        
        Args:
            repo_info: 仓库信息，包含local_path
            
        Returns:
            带有扫描结果的仓库信息
        """
        repo_path = repo_info["local_path"]
        logger.info(f"扫描仓库: {os.path.basename(repo_path)}")
        
        typo_files = {}
        
        for root, _, files in os.walk(repo_path):
            # 跳过.git目录
            if ".git" in root:
                continue
                
            for file in files:
                # 只处理支持的文件类型
                file_extension = os.path.splitext(file)[1].lower()
                if file_extension not in SUPPORTED_EXTENSIONS:
                    continue
                    
                file_path = os.path.join(root, file)
                
                try:
                    # 读取文件内容
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    # 跳过过大的文件
                    if len(content) > self.max_file_size:
                        logger.debug(f"跳过过大文件: {file_path}")
                        continue
                    
                    # 检测拼写错误
                    rel_path = os.path.relpath(file_path, repo_path)
                    file_typos = self._detect_typos(content, rel_path)
                    
                    if file_typos:
                        typo_files[rel_path] = file_typos
                    
                except Exception as e:
                    logger.error(f"处理文件 {file_path} 时出错: {str(e)}")
                    continue
        
        # 更新仓库信息
        repo_info["typos"] = typo_files
        repo_info["typos_count"] = sum(len(typos) for typos in typo_files.values())
        
        logger.info(f"在仓库 {os.path.basename(repo_path)} 中发现 {repo_info['typos_count']} 个潜在拼写错误")
        return repo_info
    
    def _detect_typos(self, content: str, file_path: str) -> List[Tuple[str, str]]:
        """
        检测文本中的拼写错误
        
        Args:
            content: 文件内容
            file_path: 文件路径（用于日志）
            
        Returns:
            拼写错误列表，每个元素为(错误, 修正)元组
        """
        try:
            logger.debug(f"检测文件拼写错误: {file_path}")
            _, details = pycorrector.correct(content)
            
            # 过滤Web3术语相关的误报
            filtered_details = []
            for detail in details:
                typo, correction = detail
                
                # 检查是否是Web3术语，如果是则跳过
                if any(term.lower() in typo.lower() for term in WEB3_TERMS):
                    continue
                
                filtered_details.append(detail)
            
            return filtered_details
            
        except Exception as e:
            logger.error(f"检测文件 {file_path} 拼写错误时出错: {str(e)}")
            return []
    
    def confirm_typos(self, repo_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        确认检测到的拼写错误
        
        Args:
            repo_info: 仓库信息，包含local_path和typos
            
        Returns:
            带有已确认拼写错误的仓库信息
        """
        repo_path = repo_info["local_path"]
        typo_files = repo_info.get("typos", {})
        logger.info(f"确认仓库 {os.path.basename(repo_path)} 中的拼写错误")
        
        if not typo_files:
            logger.warning("没有找到拼写错误")
            repo_info["confirmed_typos"] = {}
            repo_info["confirmed_typos_count"] = 0
            return repo_info
        
        confirmed_typos = {}
        
        for rel_file_path, errors in typo_files.items():
            confirmed_errors = []
            file_path = os.path.join(repo_path, rel_file_path)
            
            try:
                # 读取文件内容
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # 确认每个拼写错误
                for error in errors:
                    typo, correction = error
                    
                    # 简单确认：检查原文中是否确实存在这个拼写错误
                    if typo in content:
                        # 进一步验证：避免误报代码中的有意义标识符
                        if self._is_valid_correction(typo, correction, rel_file_path, content):
                            confirmed_errors.append(error)
                
                if confirmed_errors:
                    confirmed_typos[rel_file_path] = confirmed_errors
                    
            except Exception as e:
                logger.error(f"确认文件 {file_path} 中的拼写错误时出错: {str(e)}")
        
        # 更新仓库信息
        repo_info["confirmed_typos"] = confirmed_typos
        repo_info["confirmed_typos_count"] = sum(len(errors) for errors in confirmed_typos.values())
        
        logger.info(f"确认了 {repo_info['confirmed_typos_count']} 个拼写错误")
        return repo_info
    
    def _is_valid_correction(self, typo: str, correction: str, file_path: str, content: str) -> bool:
        """
        验证是否是有效的拼写纠正
        
        Args:
            typo: 错误拼写
            correction: 纠正后的拼写
            file_path: 文件路径
            content: 文件内容
            
        Returns:
            是否是有效的纠正
        """
        # 检查文件扩展名
        ext = os.path.splitext(file_path)[1].lower()
        
        # 如果是代码文件，需要更谨慎
        if ext in ['.js', '.ts', '.jsx', '.tsx', '.py', '.sol']:
            # 避免修改可能是变量名、函数名的内容
            # 简化实现：如果出现在引号或注释外的代码中，可能是标识符
            # 完整实现应该使用语法分析，但这里使用简化逻辑
            
            # 检查是否在类定义、函数定义、变量声明等上下文中
            code_contexts = [
                f"class {typo}", f"function {typo}", f"const {typo}", f"let {typo}", 
                f"var {typo}", f"def {typo}", f"import {typo}", f"from {typo}",
                f"{typo} =", f"{typo}="
            ]
            
            for context in code_contexts:
                if context in content:
                    return False
        
        # 避免修改URL、路径等
        if "/" in typo or "://" in typo:
            return False
        
        # 避免修改短单词（容易误报）
        if len(typo) <= 3:
            return False
            
        return True 