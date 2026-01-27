#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志工具模块 - 统一的日志记录功能
"""

import os
import sys
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler

from ..config.settings import RESULTS_DIR


def setup_logger(name, log_file=None, level=logging.INFO):
    """
    设置项目的日志记录器
    
    Args:
        name: 日志记录器名称
        log_file: 日志文件路径（可选）
        level: 日志级别
        
    Returns:
        配置好的日志记录器
    """
    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 防止重复添加处理器
    if logger.handlers:
        return logger
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # 格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    # 添加控制台处理器
    logger.addHandler(console_handler)
    
    # 如果提供了日志文件，添加文件处理器
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


# 创建默认日志记录器
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
default_log_file = os.path.join(RESULTS_DIR, f"web3_typo_hunter_{timestamp}.log")
logger = setup_logger("web3_typo_hunter", default_log_file) 