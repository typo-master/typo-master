# Example Extension

这是一个示例 SKU (Skill/Extension Unit) 扩展包，展示了如何为 TypoAgent 添加自定义能力。

## 目录结构

```
example_extension/
├── manifest.json      # SKU 元数据（必需）
├── sku.py            # 主入口文件（必需）
├── requirements.txt  # 依赖（可选）
└── README.md         # 说明文档（可选）
```

## 提供的功能

### Skills

1. **example_hello** - 打招呼
   - 输入: `name` (可选，默认 "World")
   - 输出: 问候语

2. **example_calculate** - 简单计算
   - 输入: `operation` (add/subtract/multiply/divide), `a`, `b`
   - 输出: 计算结果

### Tools

1. **example_reverse** - 反转字符串
2. **example_word_count** - 统计字数

## 使用方法

```python
# 从本地路径加载
result = await agent.process_task({
    "type": "load_sku",
    "source": "path",
    "path": "./skus/example_extension"
})

# 执行 Skill
result = await agent.process_task({
    "type": "execute_skill",
    "skill_name": "example_hello",
    "params": {"name": "TypoAgent"}
})

# 查看所有能力
capabilities = await agent.process_task({
    "type": "get_capabilities"
})
```

## 开发自己的 SKU

1. 复制这个目录作为模板
2. 修改 `manifest.json` 中的元数据
3. 在 `sku.py` 中实现你的 Skills 和 Tools
4. 添加需要的依赖到 `requirements.txt`
5. 将 SKU 放到 `./skus/` 目录或使用 `load_sku` 加载

## 配置

在 `manifest.json` 中可以定义配置项：

```json
{
  "config_schema": {
    "greeting": {
      "type": "string",
      "description": "问候语",
      "default": "Hello"
    }
  },
  "default_config": {
    "greeting": "Hello from Example Extension!"
  }
}
```

## 生命周期钩子

`sku.py` 中可以定义以下钩子函数：

- `initialize()` - SKU 加载后调用
- `cleanup()` - SKU 卸载前调用

## 更多信息

参考 `src/agent_framework/sku_system.py` 了解完整的 SKU API。
