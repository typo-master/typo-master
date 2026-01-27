#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web3 Typo Hunter 安装脚本
"""

from setuptools import setup, find_packages

setup(
    name="web3_typo_hunter",
    version="0.1.0",
    description="一个用于查找Web3项目中的拼写错误并提交PR的工具",
    author="CC11001100",
    author_email="",  # 请填写您的邮箱或保持为空
    url="https://github.com/CC11001100/typo-master",
    packages=find_packages("src"),
    package_dir={"": "src"},
    include_package_data=True,
    scripts=["web3_typo_hunter_cli.py"],
    entry_points={
        "console_scripts": [
            "web3-typo-hunter=src.scripts.web3_typo_hunter_cli:main",
        ],
    },
    install_requires=[
        "requests",
        "pandas",
        "pycorrector",
        "gitpython",
    ],
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
) 