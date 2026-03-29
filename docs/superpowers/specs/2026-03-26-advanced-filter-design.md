# 高级筛选功能设计文档

## 1. 设计概述

为 Skill 列表添加高级筛选功能，采用**顶部搜索栏 + 筛选标签 + 分类快捷筛选**的组合模式。

## 2. 目标

- 提升 Skill 列表的可发现性
- 支持多维度组合筛选
- 保持界面简洁，筛选操作高效
- 筛选状态可视化，易于管理

## 3. 非目标

- 不涉及后端筛选（当前数据量适用前端筛选）
- 不实现复杂的表达式筛选（如 AND/OR 逻辑）
- 不实现筛选条件保存/分享功能（后续迭代）

## 4. 筛选维度

| 筛选类型 | 实现方式 | 说明 |
|---------|---------|------|
| 关键词搜索 | Input 搜索框 | 搜索名称、描述、标签 |
| 状态筛选 | Segmented 切换 | 全部/仅启用/仅禁用 |
| 分类筛选 | Tag 多选 | 可多选分类（discovery/scanner 等） |
| 来源筛选 | Select 下拉 | 内置/自定义/社区 |
| 标签筛选 | Tag 输入 | 输入标签名筛选 |

## 5. 交互设计

### 5.1 顶部筛选栏布局

```
┌─────────────────────────────────────────────────────────┐
│ [搜索框] 🔍 搜索 Skill...              [状态▼] [来源▼]   │
│                                                         │
│ 分类筛选: [全部] [发现] [扫描] [修复] [GitHub] [...]     │
│                                                         │
│ 已选: [发现 ✕] [内置 ✕]                    [清除全部]    │
└─────────────────────────────────────────────────────────┘
```

### 5.2 筛选行为

- **关键词搜索**: 实时防抖（300ms），搜索名称、描述、标签
- **分类快捷标签**: 点击切换，支持多选，显示数量徽章
- **筛选结果**: 实时更新，显示"找到 X 个 Skill"
- **空结果提示**: "没有找到匹配的 Skill，尝试调整筛选条件"

### 5.3 筛选状态管理

- 已选筛选以 Tag 形式展示
- 点击 Tag 上的 ✕ 移除单个条件
- "清除全部"按钮一键重置

## 6. 组件结构

```
SkillList/
├── index.tsx              # 主组件，整合筛选状态
├── components/
│   ├── SkillFilterBar.tsx # 筛选栏组件
│   ├── CategoryFilter.tsx # 分类快捷筛选
│   ├── ActiveFilters.tsx  # 已选筛选展示
│   ├── SkillGrid.tsx      # Skill 网格展示
│   └── EmptyResult.tsx    # 空结果提示
├── hooks/
│   └── useSkillFilter.ts  # 筛选逻辑 Hook
└── utils/
    └── filterSkills.ts    # 筛选算法
```

## 7. 数据结构

```typescript
interface SkillFilterState {
  keyword: string;           // 关键词
  status: 'all' | 'enabled' | 'disabled';
  categories: string[];      // 多选分类
  sources: string[];         // 多选来源
  tags: string[];            // 多选标签
}

interface FilterCounts {
  total: number;
  byCategory: Record<string, number>;
  bySource: Record<string, number>;
  byStatus: { enabled: number; disabled: number };
}
```

## 8. 筛选算法

```typescript
function filterSkills(
  skills: AgentSkill[],
  filter: SkillFilterState
): AgentSkill[] {
  return skills.filter(skill => {
    // 关键词匹配
    if (filter.keyword) {
      const keyword = filter.keyword.toLowerCase();
      const matchName = skill.name.toLowerCase().includes(keyword);
      const matchDesc = skill.description?.toLowerCase().includes(keyword);
      const matchTags = skill.tags?.some(t => t.toLowerCase().includes(keyword));
      if (!matchName && !matchDesc && !matchTags) return false;
    }

    // 状态筛选
    if (filter.status !== 'all' && skill.enabled !== (filter.status === 'enabled')) {
      return false;
    }

    // 分类筛选
    if (filter.categories.length > 0 && !filter.categories.includes(skill.category)) {
      return false;
    }

    // 来源筛选
    if (filter.sources.length > 0 && !filter.sources.includes(skill.source || 'default')) {
      return false;
    }

    // 标签筛选
    if (filter.tags.length > 0 && !filter.tags.some(t => skill.tags?.includes(t))) {
      return false;
    }

    return true;
  });
}
```

## 9. 性能优化

- 使用 `useMemo` 缓存筛选结果
- 防抖处理搜索输入（300ms）
- 筛选计数预计算，避免重复遍历

## 10. 无障碍设计

- 筛选控件有清晰的 aria-label
- 键盘可访问（Tab 切换，Enter 确认）
- 屏幕阅读器友好

## 11. 验收标准

1. 可以通过关键词搜索 Skill 名称、描述、标签
2. 可以按状态筛选（全部/启用/禁用）
3. 可以按分类多选筛选
4. 可以按来源筛选
5. 筛选结果实时更新
6. 显示筛选结果数量
7. 支持清除单个/全部筛选条件
8. 空结果时显示友好提示

## 12. 技术实现要点

- 基于现有 SkillList 组件扩展
- 使用 Ant Design 的 Input、Select、Tag、Segmented 组件
- 筛选状态使用 useState 管理
- 筛选逻辑抽取为独立 Hook
