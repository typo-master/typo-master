# Web3 Typo Hunter

一个模块化的工具，用于寻找Web3项目中的拼写错误，提交PR修复，并有可能获得项目的代币空投（airdrop）奖励。

## 项目简介

本项目是基于原始的Typo Master重构而来，采用了模块化的架构设计，更易于维护和扩展。它具有以下主要功能：

1. **发现Web3项目** - 从GitHub上发现并分析潜在的Web3项目，评估空投可能性
2. **扫描拼写错误** - 自动扫描项目中的拼写错误，过滤Web3术语
3. **修复和提交PR** - 自动修复拼写错误并创建PR

## 模块化架构

项目采用了清晰的模块化设计，所有代码位于`src`目录下：

- **src/web3_typo_hunter/** - 主要的项目代码
  - **discovery/** - 项目发现模块，负责从GitHub上发现和管理Web3项目
    - `repo_finder.py` - 使用GitHub API查找Web3项目并分析空投潜力
    - `repo_manager.py` - 管理本地仓库，处理克隆、分支和推送等操作
  - **scanner/** - 扫描模块，负责检测和修复拼写错误
    - `typo_scanner.py` - 扫描并确认项目中的拼写错误 
    - `typo_fixer.py` - 修复确认的拼写错误
  - **processor/** - 处理模块，处理扫描结果
    - `pr_creator.py` - 创建和管理GitHub PR
    - `report_generator.py` - 生成各种格式的报告
  - **utils/** - 工具模块，提供通用功能
    - `github_api.py` - GitHub API封装
    - `logger.py` - 日志工具
  - **config/** - 配置模块
    - `settings.py` - 全局配置设置
  - `controller.py` - 主控制器
- **src/scripts/** - 命令行脚本
  - `web3_typo_hunter_cli.py` - CLI实现

## 安装说明

### 安装依赖

```bash
pip install -r requirements.txt
```

### 开发模式安装

```bash
pip install -e .
```

这将以开发模式安装项目，允许你在修改代码后不需要重新安装。

对于pycorrector模型文件，需要单独下载：
```
参考：https://github.com/shibing624/pycorrector/issues/119
```
下载好后放在`~/.pycorrector/datasets`文件夹下。

## 使用方法

项目提供了直观的命令行界面，有三种主要操作模式：

### 1. 寻找潜在空投项目

```bash
python web3_typo_hunter_cli.py find --token YOUR_GITHUB_TOKEN --days 30 --min-stars 100 --limit 50 --format csv
```

或者安装后使用：

```bash
web3-typo-hunter find --token YOUR_GITHUB_TOKEN --days 30 --min-stars 100 --limit 50 --format csv
```

参数说明：
- `--token`: GitHub API令牌
- `--days`: 搜索最近多少天内更新的项目（默认30天）
- `--min-stars`: 项目最小星星数（默认100）
- `--limit`: 返回结果数量限制（默认50）
- `--format`: 输出格式 (csv/excel/json)

### 2. 扫描单个项目

```bash
python web3_typo_hunter_cli.py scan --token YOUR_GITHUB_TOKEN --repo owner/repo --create-pr
```

或者安装后使用：

```bash
web3-typo-hunter scan --token YOUR_GITHUB_TOKEN --repo owner/repo --create-pr
```

参数说明：
- `--token`: GitHub API令牌
- `--repo`: 要扫描的仓库（格式：owner/repo）
- `--create-pr`: 是否创建PR（可选）

### 3. 批量处理项目

```bash
python web3_typo_hunter_cli.py process --token YOUR_GITHUB_TOKEN --days 30 --min-stars 100 --limit 5 --create-pr
```

或者安装后使用：

```bash
web3-typo-hunter process --token YOUR_GITHUB_TOKEN --days 30 --min-stars 100 --limit 5 --create-pr
```

参数说明：
- `--token`: GitHub API令牌
- `--days`: 搜索最近多少天内更新的项目（默认30天）
- `--min-stars`: 项目最小星星数（默认100）
- `--limit`: 处理项目数量限制（默认5）
- `--create-pr`: 是否创建PR（可选）

## 扩展开发

项目采用模块化设计，便于扩展。如果要添加新功能，通常只需要在相应模块中添加新的类或方法。

### 添加新的发现方式

在`src/web3_typo_hunter/discovery`模块中扩展`repo_finder.py`，添加新的发现方法。

### 添加新的扫描策略

在`src/web3_typo_hunter/scanner`模块中扩展或修改`typo_scanner.py`，添加新的扫描策略。

### 添加新的报告格式

在`src/web3_typo_hunter/processor`模块中扩展`report_generator.py`，添加新的报告格式。

### 添加新的命令行功能

在`src/scripts/web3_typo_hunter_cli.py`中添加新的命令行选项和功能。

## 获取GitHub Token

要获取GitHub Token，请按照以下步骤操作：

1. 登录到GitHub
2. 点击右上角头像，选择"Settings"
3. 在左侧菜单中选择"Developer settings"
4. 点击"Personal access tokens" → "Tokens (classic)"
5. 点击"Generate new token"
6. 选择至少包含以下权限：
   - repo (全选)
   - workflow
7. 点击"Generate token"按钮
8. 保存生成的token（这是唯一可以看到完整token的机会）

## Web3空投策略建议

为了最大化获得空投的机会，建议：

1. 优先选择近期有活跃更新的Web3项目
2. 优先选择最近合并过PR的项目（表明项目方乐于接受社区贡献）
3. 优先选择有明确路线图的项目（可能在未来会有代币发行）
4. 不要只关注修复拼写错误，也可以：
   - 提供文档翻译
   - 修复小的bug
   - 添加测试用例
   - 改进项目文档

## 注意事项

- 使用GitHub API时请注意API访问限制
- 确保你的PR是有价值的贡献，不要仅仅为了空投而提交无意义的更改
- 遵循项目的贡献指南和代码风格
- 空投并不是必然的，它取决于项目方的决定

## 免责声明

本工具仅用于辅助开发者发现并修复开源项目中的问题。使用本工具进行的任何活动均应遵守GitHub的服务条款和相关法律法规。作者不对使用本工具造成的任何后果负责。

---

## 原项目信息

本项目是基于原始的Typo Master修改而来，原项目的目标是：

- 第一阶段目标：用于从GitHub上寻找有拼写错误的并且有一些Star的项目来用于蹭PR。
- 第二阶段目标：寻找高赞但是没有中文使用文档的项目
- 第三阶段目标：用于从GitHub上寻找有待解决的Bug或者Feature的项目。
- 第四阶段目标：对GitHub上的项目自动审计、Review，检出Bug或者漏洞进行修复。




语言：Python
输入：Git仓库
扫描内容：
- Markdown（v0.0.1）
- 代码文件
  - 注释
  - 函数名 
  - 





# 一、目标

## 第一阶段目标  

用于从GitHub上寻找有拼写错误的并且有一些Star的项目来用于蹭PR。

## 第二阶段目标

寻找高赞但是没有中文使用文档的项目 

## 第三阶段目标

用于从GitHub上寻找有待解决的Bug或者Feature的项目。 

## 第四阶段目标

对GitHub上的项目自动审计、Review，检出Bug或者漏洞进行修复。



此项目只负责完成第一阶段的目标，如果能成功完成，会有后续项目继续接力完成后续目标。



# 第一阶段的实现思路

## 项目的获取 

- 按照人的粉丝之类的去搜索寻找
- 按照标签搜索寻找

## 项目的检查

- 中文词典
- 英文词典 
- 对于有过合并typo先例的项目增加其权重推荐优先撸它
  - 判断依据是pr合并，并且commit中有typo关键字 









