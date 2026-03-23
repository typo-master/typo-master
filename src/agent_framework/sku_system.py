"""
SKU (Skill/Extension Unit) Extension Framework

Provides a plugin system for dynamically extending Agent capabilities.

Architecture:
    Agent
      └── SkillManager (Skill/SKU 管理器)
           ├── Built-in Skills (内置技能)
           ├── Loaded SKUs (动态加载的扩展包)
           │    ├── SKU Package (扩展包)
           │    │    ├── manifest.json (元数据)
           │    │    ├── skills/ (技能实现)
           │    │    ├── tools/ (工具实现)
           │    │    └── requirements.txt (依赖)
           └── Registry (注册表)

Usage:
    # 加载本地 SKU
    await agent.sku_manager.load_sku("./skus/my_extension")

    # 从 GitHub 加载
    await agent.sku_manager.load_sku_from_github(
        "owner/repo",
        ref="main"
    )

    # 列出所有能力
    capabilities = agent.sku_manager.list_capabilities()
"""

from typing import Any, Dict, List, Optional, Callable, Type
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
import json
import importlib.util
import sys
import os
import shutil
import asyncio
import tempfile
import zipfile
from abc import ABC, abstractmethod

from .skill_system import BaseSkill, SkillMetadata, SkillCategory, SkillLevel
from .tool_system import ToolRegistry, ToolResult
from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class SKUMetadata:
    """SKU (Skill/Extension Unit) 元数据"""
    # 基本信息
    name: str
    version: str
    description: str
    author: str

    # 分类
    category: str = "general"  # general, scan, fix, report, git, pr, custom
    tags: List[str] = field(default_factory=list)

    # 依赖
    required_skills: List[str] = field(default_factory=list)
    required_tools: List[str] = field(default_factory=list)
    required_packages: List[str] = field(default_factory=list)

    # 入口点
    entry_point: str = "sku.py"  # 主入口文件
    skill_module: str = "skills"  # Skill 子模块名
    tool_module: str = "tools"  # Tool 子模块名

    # 配置
    config_schema: Dict[str, Any] = field(default_factory=dict)
    default_config: Dict[str, Any] = field(default_factory=dict)

    # 元信息
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    homepage: Optional[str] = None
    repository: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SKUMetadata":
        """从字典创建元数据"""
        return cls(
            name=data.get("name", "unknown"),
            version=data.get("version", "0.1.0"),
            description=data.get("description", ""),
            author=data.get("author", "unknown"),
            category=data.get("category", "general"),
            tags=data.get("tags", []),
            required_skills=data.get("required_skills", []),
            required_tools=data.get("required_tools", []),
            required_packages=data.get("required_packages", []),
            entry_point=data.get("entry_point", "sku.py"),
            skill_module=data.get("skill_module", "skills"),
            tool_module=data.get("tool_module", "tools"),
            config_schema=data.get("config_schema", {}),
            default_config=data.get("default_config", {}),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            homepage=data.get("homepage"),
            repository=data.get("repository"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "category": self.category,
            "tags": self.tags,
            "required_skills": self.required_skills,
            "required_tools": self.required_tools,
            "required_packages": self.required_packages,
            "entry_point": self.entry_point,
            "skill_module": self.skill_module,
            "tool_module": self.tool_module,
            "config_schema": self.config_schema,
            "default_config": self.default_config,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "homepage": self.homepage,
            "repository": self.repository,
        }


@dataclass
class SKUState:
    """SKU 状态"""
    LOADED = "loaded"  # 已加载
    ACTIVE = "active"  # 已激活
    ERROR = "error"  # 加载错误
    DISABLED = "disabled"  # 已禁用


@dataclass
class LoadedSKU:
    """已加载的 SKU"""
    metadata: SKUMetadata
    path: Path
    state: str = SKUState.LOADED
    config: Dict[str, Any] = field(default_factory=dict)
    skills: List[Type[BaseSkill]] = field(default_factory=list)
    tools: List[Callable] = field(default_factory=list)
    module: Any = None
    error: Optional[str] = None
    loaded_at: Optional[datetime] = None


class SKULoader:
    """
    SKU 加载器

    负责从各种来源加载 SKU 包。
    """

    def __init__(self, sku_dir: Optional[Path] = None):
        self.sku_dir = sku_dir or Path("./skus")
        self.sku_dir.mkdir(parents=True, exist_ok=True)

    async def load_from_path(self, path: Path) -> Optional[LoadedSKU]:
        """
        从本地路径加载 SKU

        Args:
            path: SKU 包路径（文件夹或 zip 文件）

        Returns:
            LoadedSKU 或 None
        """
        try:
            path = Path(path)

            # 处理 zip 文件
            if path.suffix == ".zip":
                path = await self._extract_zip(path)

            if not path.exists():
                logger.error(f"SKU path does not exist: {path}")
                return None

            # 读取 manifest
            manifest_path = path / "manifest.json"
            if not manifest_path.exists():
                logger.error(f"SKU manifest not found: {manifest_path}")
                return None

            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)

            metadata = SKUMetadata.from_dict(manifest_data)

            # 创建 LoadedSKU
            sku = LoadedSKU(
                metadata=metadata,
                path=path,
                loaded_at=datetime.now()
            )

            # 安装依赖
            await self._install_dependencies(sku)

            # 加载模块
            await self._load_modules(sku)

            sku.state = SKUState.ACTIVE
            logger.info(f"SKU '{metadata.name}' v{metadata.version} loaded successfully")
            return sku

        except Exception as e:
            logger.error(f"Failed to load SKU from {path}: {e}")
            return None

    async def load_from_github(
        self,
        repo: str,
        ref: str = "main",
        subdir: Optional[str] = None
    ) -> Optional[LoadedSKU]:
        """
        从 GitHub 仓库加载 SKU

        Args:
            repo: "owner/repo" 格式
            ref: 分支或标签
            subdir: SKU 在仓库中的子目录

        Returns:
            LoadedSKU 或 None
        """
        try:
            import aiohttp

            # 下载 zip
            url = f"https://github.com/{repo}/archive/{ref}.zip"

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to download from GitHub: {response.status}")
                        return None

                    data = await response.read()

            # 保存到临时文件
            temp_zip = Path(tempfile.gettempdir()) / f"{repo.replace('/', '_')}_{ref}.zip"
            with open(temp_zip, "wb") as f:
                f.write(data)

            # 提取
            extract_dir = Path(tempfile.gettempdir()) / f"{repo.replace('/', '_')}_{ref}"
            if extract_dir.exists():
                shutil.rmtree(extract_dir)

            with zipfile.ZipFile(temp_zip, 'r') as z:
                z.extractall(extract_dir)

            # 找到实际目录（GitHub zip 会有一层文件夹）
            subdirs = [d for d in extract_dir.iterdir() if d.is_dir()]
            if subdirs:
                sku_path = subdirs[0]
                if subdir:
                    sku_path = sku_path / subdir
            else:
                logger.error("Invalid GitHub zip structure")
                return None

            # 复制到 sku_dir
            target_path = self.sku_dir / sku_path.name
            if target_path.exists():
                shutil.rmtree(target_path)
            shutil.copytree(sku_path, target_path)

            # 清理临时文件
            os.remove(temp_zip)
            shutil.rmtree(extract_dir)

            return await self.load_from_path(target_path)

        except Exception as e:
            logger.error(f"Failed to load SKU from GitHub {repo}: {e}")
            return None

    async def load_from_url(self, url: str) -> Optional[LoadedSKU]:
        """从 URL 加载 SKU"""
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to download SKU: {response.status}")
                        return None

                    data = await response.read()

            # 保存临时文件
            temp_file = Path(tempfile.gettempdir()) / "sku_download.zip"
            with open(temp_file, "wb") as f:
                f.write(data)

            return await self.load_from_path(temp_file)

        except Exception as e:
            logger.error(f"Failed to load SKU from URL {url}: {e}")
            return None

    async def _extract_zip(self, zip_path: Path) -> Path:
        """解压 zip 文件"""
        extract_dir = self.sku_dir / zip_path.stem
        if extract_dir.exists():
            shutil.rmtree(extract_dir)

        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(extract_dir)

        return extract_dir

    async def _install_dependencies(self, sku: LoadedSKU):
        """安装 SKU 依赖"""
        req_file = sku.path / "requirements.txt"
        if req_file.exists():
            logger.info(f"Installing dependencies for SKU '{sku.metadata.name}'")
            import subprocess
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", str(req_file)],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                logger.warning(f"Failed to install some dependencies: {result.stderr}")

    async def _load_modules(self, sku: LoadedSKU):
        """加载 SKU 模块"""
        # 添加到 Python 路径
        if str(sku.path) not in sys.path:
            sys.path.insert(0, str(sku.path))

        # 加载入口模块
        entry_file = sku.path / sku.metadata.entry_point
        if entry_file.exists():
            spec = importlib.util.spec_from_file_location(
                f"sku_{sku.metadata.name}",
                entry_file
            )
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[f"sku_{sku.metadata.name}"] = module
                spec.loader.exec_module(module)
                sku.module = module

                # 调用初始化钩子（如果存在）
                if hasattr(module, "initialize"):
                    await module.initialize()


class SKUManager:
    """
    SKU 管理器

    管理所有已加载的 SKU，提供统一的访问接口。

    Usage:
        manager = SKUManager(agent)
        await manager.initialize()

        # 加载 SKU
        sku = await manager.load_sku("./skus/my_extension")

        # 列出所有能力
        capabilities = manager.list_capabilities()

        # 获取 Skill
        skill = manager.get_skill("my_extension.custom_scan")

        # 卸载 SKU
        await manager.unload_sku("my_extension")
    """

    def __init__(self, agent: Optional[Any] = None):
        self.agent = agent
        self.loader = SKULoader()
        self.loaded_skus: Dict[str, LoadedSKU] = {}
        self._skill_registry: Dict[str, Type[BaseSkill]] = {}
        self._tool_registry: Dict[str, Callable] = {}
        self._hooks: Dict[str, List[Callable]] = {
            "before_load": [],
            "after_load": [],
            "before_unload": [],
            "after_unload": [],
        }

    async def initialize(self):
        """初始化 SKU 管理器"""
        # 加载 sku_dir 中的所有 SKU
        if self.loader.sku_dir.exists():
            for item in self.loader.sku_dir.iterdir():
                if item.is_dir() and (item / "manifest.json").exists():
                    await self.load_sku(item)

    def register_hook(self, event: str, callback: Callable):
        """注册生命周期钩子"""
        if event in self._hooks:
            self._hooks[event].append(callback)

    async def _call_hooks(self, event: str, sku: LoadedSKU):
        """调用钩子"""
        for callback in self._hooks.get(event, []):
            try:
                await callback(sku)
            except Exception as e:
                logger.warning(f"Hook error for {event}: {e}")

    async def load_sku(self, path: Path) -> Optional[LoadedSKU]:
        """
        加载 SKU

        Args:
            path: SKU 路径

        Returns:
            LoadedSKU 或 None
        """
        await self._call_hooks("before_load", LoadedSKU(
            metadata=SKUMetadata(name="temp", version="0.0.0", description="", author=""),
            path=Path(path)
        ))

        sku = await self.loader.load_from_path(Path(path))
        if not sku:
            return None

        # 检查名称冲突
        if sku.metadata.name in self.loaded_skus:
            logger.warning(f"SKU '{sku.metadata.name}' already loaded, skipping")
            return None

        # 检查依赖
        for dep in sku.metadata.required_skills:
            if dep not in self._skill_registry:
                logger.warning(f"SKU '{sku.metadata.name}' requires skill '{dep}'")

        # 注册 SKU
        self.loaded_skus[sku.metadata.name] = sku

        # 注册 Skill
        if sku.module and hasattr(sku.module, "SKILLS"):
            for skill_class in sku.module.SKILLS:
                full_name = f"{sku.metadata.name}.{skill_class.__name__}"
                self._skill_registry[full_name] = skill_class
                logger.debug(f"Registered skill: {full_name}")

        # 注册 Tool
        if sku.module and hasattr(sku.module, "TOOLS"):
            for tool in sku.module.TOOLS:
                # Get tool name from metadata
                if hasattr(tool, '_tool_metadata'):
                    tool_name = tool._tool_metadata.name
                else:
                    tool_name = tool.__name__
                full_name = f"{sku.metadata.name}.{tool_name}"
                self._tool_registry[full_name] = tool
                ToolRegistry().register(tool)
                logger.debug(f"Registered tool: {full_name}")

        await self._call_hooks("after_load", sku)

        logger.info(f"SKU '{sku.metadata.name}' loaded with "
                   f"{len(sku.skills)} skills and {len(sku.tools)} tools")
        return sku

    async def load_sku_from_github(
        self,
        repo: str,
        ref: str = "main",
        subdir: Optional[str] = None
    ) -> Optional[LoadedSKU]:
        """从 GitHub 加载 SKU"""
        return await self.loader.load_from_github(repo, ref, subdir)

    async def unload_sku(self, name: str) -> bool:
        """
        卸载 SKU

        Args:
            name: SKU 名称

        Returns:
            是否成功
        """
        if name not in self.loaded_skus:
            logger.warning(f"SKU '{name}' not loaded")
            return False

        sku = self.loaded_skus[name]
        await self._call_hooks("before_unload", sku)

        # 注销 Skill
        skills_to_remove = [
            k for k in self._skill_registry.keys()
            if k.startswith(f"{name}.")
        ]
        for k in skills_to_remove:
            del self._skill_registry[k]

        # 注销 Tool
        tools_to_remove = [
            k for k in self._tool_registry.keys()
            if k.startswith(f"{name}.")
        ]
        for k in tools_to_remove:
            tool_func = self._tool_registry.pop(k)
            # 从 ToolRegistry 移除
            # 获取工具名（去掉 SKU 前缀）
            tool_name = k.split(".")[-1] if "." in k else k
            if tool_name in ToolRegistry().tools:
                del ToolRegistry().tools[tool_name]

        # 调用清理钩子
        if sku.module and hasattr(sku.module, "cleanup"):
            try:
                await sku.module.cleanup()
            except Exception as e:
                logger.warning(f"Cleanup error for SKU '{name}': {e}")

        # 从路径中移除
        if str(sku.path) in sys.path:
            sys.path.remove(str(sku.path))

        # 从内存中移除模块
        module_name = f"sku_{name}"
        if module_name in sys.modules:
            del sys.modules[module_name]

        del self.loaded_skus[name]

        await self._call_hooks("after_unload", sku)

        logger.info(f"SKU '{name}' unloaded")
        return True

    def get_sku(self, name: str) -> Optional[LoadedSKU]:
        """获取已加载的 SKU"""
        return self.loaded_skus.get(name)

    def list_skus(self) -> List[Dict[str, Any]]:
        """列出所有已加载的 SKU"""
        return [
            {
                "name": sku.metadata.name,
                "version": sku.metadata.version,
                "description": sku.metadata.description,
                "author": sku.metadata.author,
                "category": sku.metadata.category,
                "state": sku.state,
                "skills": len(sku.skills),
                "tools": len(sku.tools),
            }
            for sku in self.loaded_skus.values()
        ]

    def get_skill(self, name: str) -> Optional[Type[BaseSkill]]:
        """
        获取 Skill 类

        支持以下格式：
        - "sku_name.SkillName" - 完整名称
        - "SkillName" - 简短名称（如果唯一）
        """
        # 完整名称
        if name in self._skill_registry:
            return self._skill_registry[name]

        # 简短名称查找
        matches = [
            v for k, v in self._skill_registry.items()
            if k.endswith(f".{name}")
        ]
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            logger.warning(f"Ambiguous skill name '{name}', use full name")

        return None

    def get_tool(self, name: str) -> Optional[Callable]:
        """获取 Tool"""
        if name in self._tool_registry:
            return self._tool_registry[name]

        # 简短名称查找
        matches = [
            v for k, v in self._tool_registry.items()
            if k.endswith(f".{name}")
        ]
        if len(matches) == 1:
            return matches[0]

        return None

    def list_capabilities(self) -> Dict[str, Any]:
        """
        列出所有可用能力

        Returns:
            包含所有 SKU、Skill、Tool 的信息
        """
        return {
            "skus": self.list_skus(),
            "skills": [
                {
                    "name": name,
                    "sku": name.split(".")[0] if "." in name else "builtin",
                }
                for name in self._skill_registry.keys()
            ],
            "tools": [
                {
                    "name": name,
                    "sku": name.split(".")[0] if "." in name else "builtin",
                }
                for name in self._tool_registry.keys()
            ],
        }

    def get_skill_instance(self, name: str, **kwargs) -> Optional[BaseSkill]:
        """
        创建 Skill 实例

        Args:
            name: Skill 名称
            **kwargs: 传递给 Skill 构造函数的参数

        Returns:
            Skill 实例或 None
        """
        skill_class = self.get_skill(name)
        if not skill_class:
            return None

        try:
            # 检查是否需要 metadata 参数
            import inspect
            sig = inspect.signature(skill_class.__init__)
            if 'metadata' in sig.parameters:
                # 从装饰器获取 metadata
                if hasattr(skill_class, '_skill_metadata'):
                    return skill_class(skill_class._skill_metadata, **kwargs)
            return skill_class(**kwargs)
        except Exception as e:
            logger.error(f"Failed to create skill instance '{name}': {e}")
            return None


class SKUExtensionMixin:
    """
    SKU 扩展混入类

    为 Agent 添加 SKU 管理能力。

    Usage:
        class MyAgent(SKUExtensionMixin, BaseAgent):
            async def on_initialize(self):
                await super().on_initialize()
                # SKU 管理器已自动初始化
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sku_manager: Optional[SKUManager] = None

    async def on_initialize(self) -> None:
        """初始化时创建 SKU 管理器"""
        await super().on_initialize()

        self.sku_manager = SKUManager(self)
        await self.sku_manager.initialize()

        logger.info(f"SKU Manager initialized with "
                   f"{len(self.sku_manager.loaded_skus)} SKUs")


# Export
__all__ = [
    "SKUMetadata",
    "SKUState",
    "LoadedSKU",
    "SKULoader",
    "SKUManager",
    "SKUExtensionMixin",
]
