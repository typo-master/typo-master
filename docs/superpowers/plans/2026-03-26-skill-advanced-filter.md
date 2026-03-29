# Skill 列表高级筛选功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 Skill 列表添加高级筛选功能，支持关键词搜索、状态筛选、分类筛选、来源筛选和标签筛选。

**Architecture:** 基于现有 SkillList 组件扩展，新增筛选栏组件、筛选逻辑 Hook 和筛选算法工具函数。筛选状态在前端管理，实时响应用户输入。

**Tech Stack:** React + TypeScript + Ant Design

---

## File Structure

```
app/frontend/src/components/SkillList/
├── index.tsx                    # 修改：整合筛选状态
├── components/
│   ├── SkillFilterBar.tsx       # 创建：筛选栏组件
│   ├── CategoryFilter.tsx       # 创建：分类快捷筛选
│   ├── ActiveFilters.tsx        # 创建：已选筛选展示
│   └── EmptyResult.tsx          # 创建：空结果提示
├── hooks/
│   └── useSkillFilter.ts        # 创建：筛选逻辑 Hook
└── utils/
    └── filterSkills.ts          # 创建：筛选算法
```

---

## Task 1: 创建筛选算法工具函数

**Files:**
- Create: `app/frontend/src/components/SkillList/utils/filterSkills.ts`

- [ ] **Step 1: 创建筛选算法**

```typescript
import type { AgentSkill } from "../../../db";

export interface SkillFilterState {
  keyword: string;
  status: 'all' | 'enabled' | 'disabled';
  categories: string[];
  sources: string[];
  tags: string[];
}

export const defaultFilterState: SkillFilterState = {
  keyword: '',
  status: 'all',
  categories: [],
  sources: [],
  tags: [],
};

export function filterSkills(
  skills: AgentSkill[],
  filter: SkillFilterState
): AgentSkill[] {
  return skills.filter(skill => {
    // 关键词匹配（名称、描述、标签）
    if (filter.keyword.trim()) {
      const keyword = filter.keyword.toLowerCase().trim();
      const matchName = skill.name.toLowerCase().includes(keyword);
      const matchDesc = skill.description?.toLowerCase().includes(keyword) ?? false;
      const matchTags = skill.tags?.some(t => t.toLowerCase().includes(keyword)) ?? false;
      if (!matchName && !matchDesc && !matchTags) return false;
    }

    // 状态筛选
    if (filter.status !== 'all' && skill.enabled !== (filter.status === 'enabled')) {
      return false;
    }

    // 分类筛选
    if (filter.categories.length > 0 && !filter.categories.includes(skill.category || 'default')) {
      return false;
    }

    // 来源筛选
    if (filter.sources.length > 0 && !filter.sources.includes(skill.source || 'default')) {
      return false;
    }

    // 标签筛选（筛选条件标签需要全部匹配）
    if (filter.tags.length > 0) {
      const skillTags = skill.tags || [];
      const hasAllTags = filter.tags.every(t => skillTags.includes(t));
      if (!hasAllTags) return false;
    }

    return true;
  });
}

export interface FilterCounts {
  total: number;
  byCategory: Record<string, number>;
  bySource: Record<string, number>;
  byStatus: { enabled: number; disabled: number };
}

export function calculateFilterCounts(skills: AgentSkill[]): FilterCounts {
  const byCategory: Record<string, number> = {};
  const bySource: Record<string, number> = {};
  let enabled = 0;
  let disabled = 0;

  for (const skill of skills) {
    // 分类计数
    const category = skill.category || 'default';
    byCategory[category] = (byCategory[category] || 0) + 1;

    // 来源计数
    const source = skill.source || 'default';
    bySource[source] = (bySource[source] || 0) + 1;

    // 状态计数
    if (skill.enabled) {
      enabled++;
    } else {
      disabled++;
    }
  }

  return {
    total: skills.length,
    byCategory,
    bySource,
    byStatus: { enabled, disabled },
  };
}
```

- [ ] **Step 2: 提交**

```bash
git add app/frontend/src/components/SkillList/utils/filterSkills.ts
git commit -m "feat(skill-filter): add filter algorithm and types"
```

---

## Task 2: 创建筛选逻辑 Hook

**Files:**
- Create: `app/frontend/src/components/SkillList/hooks/useSkillFilter.ts`

- [ ] **Step 1: 创建 useSkillFilter Hook**

```typescript
import { useState, useMemo, useCallback } from "react";
import type { AgentSkill } from "../../../db";
import {
  filterSkills,
  calculateFilterCounts,
  type SkillFilterState,
  defaultFilterState,
} from "../utils/filterSkills";

export interface UseSkillFilterReturn {
  filter: SkillFilterState;
  setFilter: React.Dispatch<React.SetStateAction<SkillFilterState>>;
  filteredSkills: AgentSkill[];
  counts: ReturnType<typeof calculateFilterCounts>;
  hasActiveFilters: boolean;
  clearFilters: () => void;
  setKeyword: (keyword: string) => void;
  setStatus: (status: SkillFilterState['status']) => void;
  toggleCategory: (category: string) => void;
  toggleSource: (source: string) => void;
  toggleTag: (tag: string) => void;
  removeCategory: (category: string) => void;
  removeSource: (source: string) => void;
  removeTag: (tag: string) => void;
}

export function useSkillFilter(skills: AgentSkill[]): UseSkillFilterReturn {
  const [filter, setFilter] = useState<SkillFilterState>(defaultFilterState);

  // 筛选结果（带缓存）
  const filteredSkills = useMemo(() => {
    return filterSkills(skills, filter);
  }, [skills, filter]);

  // 基于原始数据的计数
  const counts = useMemo(() => {
    return calculateFilterCounts(skills);
  }, [skills]);

  // 是否有活跃筛选
  const hasActiveFilters = useMemo(() => {
    return (
      filter.keyword.trim() !== '' ||
      filter.status !== 'all' ||
      filter.categories.length > 0 ||
      filter.sources.length > 0 ||
      filter.tags.length > 0
    );
  }, [filter]);

  // 清除所有筛选
  const clearFilters = useCallback(() => {
    setFilter(defaultFilterState);
  }, []);

  // 设置关键词（防抖将在组件层处理）
  const setKeyword = useCallback((keyword: string) => {
    setFilter(prev => ({ ...prev, keyword }));
  }, []);

  // 设置状态
  const setStatus = useCallback((status: SkillFilterState['status']) => {
    setFilter(prev => ({ ...prev, status }));
  }, []);

  // 切换分类
  const toggleCategory = useCallback((category: string) => {
    setFilter(prev => {
      const categories = prev.categories.includes(category)
        ? prev.categories.filter(c => c !== category)
        : [...prev.categories, category];
      return { ...prev, categories };
    });
  }, []);

  // 切换来源
  const toggleSource = useCallback((source: string) => {
    setFilter(prev => {
      const sources = prev.sources.includes(source)
        ? prev.sources.filter(s => s !== source)
        : [...prev.sources, source];
      return { ...prev, sources };
    });
  }, []);

  // 切换标签
  const toggleTag = useCallback((tag: string) => {
    setFilter(prev => {
      const tags = prev.tags.includes(tag)
        ? prev.tags.filter(t => t !== tag)
        : [...prev.tags, tag];
      return { ...prev, tags };
    });
  }, []);

  // 移除单个分类
  const removeCategory = useCallback((category: string) => {
    setFilter(prev => ({
      ...prev,
      categories: prev.categories.filter(c => c !== category),
    }));
  }, []);

  // 移除单个来源
  const removeSource = useCallback((source: string) => {
    setFilter(prev => ({
      ...prev,
      sources: prev.sources.filter(s => s !== source),
    }));
  }, []);

  // 移除单个标签
  const removeTag = useCallback((tag: string) => {
    setFilter(prev => ({
      ...prev,
      tags: prev.tags.filter(t => t !== tag),
    }));
  }, []);

  return {
    filter,
    setFilter,
    filteredSkills,
    counts,
    hasActiveFilters,
    clearFilters,
    setKeyword,
    setStatus,
    toggleCategory,
    toggleSource,
    toggleTag,
    removeCategory,
    removeSource,
    removeTag,
  };
}
```

- [ ] **Step 2: 提交**

```bash
git add app/frontend/src/components/SkillList/hooks/useSkillFilter.ts
git commit -m "feat(skill-filter): add useSkillFilter hook"
```

---

## Task 3: 创建空结果提示组件

**Files:**
- Create: `app/frontend/src/components/SkillList/components/EmptyResult.tsx`

- [ ] **Step 1: 创建 EmptyResult 组件**

```typescript
import { Empty, Button, Space, Typography } from "antd";
import { SearchOutlined } from "@ant-design/icons";

const { Text } = Typography;

interface EmptyResultProps {
  onClearFilters?: () => void;
}

export default function EmptyResult({ onClearFilters }: EmptyResultProps) {
  return (
    <Empty
      image={Empty.PRESENTED_IMAGE_SIMPLE}
      description={
        <Space direction="vertical" size={8}>
          <Text strong>没有找到匹配的 Skill</Text>
          <Text type="secondary">尝试调整筛选条件或清除筛选</Text>
        </Space>
      }
    >
      {onClearFilters && (
        <Button type="primary" icon={<SearchOutlined />} onClick={onClearFilters}>
          清除全部筛选
        </Button>
      )}
    </Empty>
  );
}
```

- [ ] **Step 2: 提交**

```bash
git add app/frontend/src/components/SkillList/components/EmptyResult.tsx
git commit -m "feat(skill-filter): add EmptyResult component"
```

---

## Task 4: 创建已选筛选展示组件

**Files:**
- Create: `app/frontend/src/components/SkillList/components/ActiveFilters.tsx`

- [ ] **Step 1: 创建 ActiveFilters 组件**

```typescript
import { Space, Tag, Button } from "antd";
import { CloseOutlined } from "@ant-design/icons";
import { CATEGORY_META } from "../index";
import { SOURCE_META } from "../index";
import type { SkillFilterState } from "../utils/filterSkills";

interface ActiveFiltersProps {
  filter: SkillFilterState;
  onClearAll: () => void;
  onRemoveCategory: (category: string) => void;
  onRemoveSource: (source: string) => void;
  onRemoveTag: (tag: string) => void;
}

export default function ActiveFilters({
  filter,
  onClearAll,
  onRemoveCategory,
  onRemoveSource,
  onRemoveTag,
}: ActiveFiltersProps) {
  const hasFilters =
    filter.keyword.trim() ||
    filter.status !== 'all' ||
    filter.categories.length > 0 ||
    filter.sources.length > 0 ||
    filter.tags.length > 0;

  if (!hasFilters) return null;

  return (
    <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid #f0f0f0' }}>
      <Space wrap size={8}>
        <span style={{ color: '#666', fontSize: 12 }}>已选筛选:</span>

        {filter.keyword.trim() && (
          <Tag closable onClose={() => {}}>
            关键词: {filter.keyword}
          </Tag>
        )}

        {filter.status !== 'all' && (
          <Tag closable onClose={() => {}}>
            状态: {filter.status === 'enabled' ? '已启用' : '已禁用'}
          </Tag>
        )}

        {filter.categories.map(category => (
          <Tag
            key={category}
            closable
            onClose={() => onRemoveCategory(category)}
            color={CATEGORY_META[category]?.color}
          >
            {CATEGORY_META[category]?.label || category}
          </Tag>
        ))}

        {filter.sources.map(source => (
          <Tag
            key={source}
            closable
            onClose={() => onRemoveSource(source)}
            color={SOURCE_META[source]?.color}
          >
            {SOURCE_META[source]?.label || source}
          </Tag>
        ))}

        {filter.tags.map(tag => (
          <Tag key={tag} closable onClose={() => onRemoveTag(tag)}>
            #{tag}
          </Tag>
        ))}

        <Button type="link" size="small" onClick={onClearAll}>
          清除全部
        </Button>
      </Space>
    </div>
  );
}
```

- [ ] **Step 2: 修改导入路径**

注意：需要从 index.tsx 导出 CATEGORY_META 和 SOURCE_META，或者在这个文件中重新定义。

修改 `app/frontend/src/components/SkillList/index.tsx`：
- 将 `CATEGORY_META` 和 `SOURCE_META` 导出

在 index.tsx 文件末尾添加：
```typescript
export { CATEGORY_META, SOURCE_META };
```

- [ ] **Step 3: 提交**

```bash
git add app/frontend/src/components/SkillList/components/ActiveFilters.tsx
git add app/frontend/src/components/SkillList/index.tsx
git commit -m "feat(skill-filter): add ActiveFilters component and export meta"
```

---

## Task 5: 创建分类快捷筛选组件

**Files:**
- Create: `app/frontend/src/components/SkillList/components/CategoryFilter.tsx`

- [ ] **Step 1: 创建 CategoryFilter 组件**

```typescript
import { Space, Tag } from "antd";
import { CheckOutlined } from "@ant-design/icons";
import { CATEGORY_META } from "../index";

interface CategoryFilterProps {
  categories: string[];
  selectedCategories: string[];
  counts: Record<string, number>;
  onToggle: (category: string) => void;
}

export default function CategoryFilter({
  categories,
  selectedCategories,
  counts,
  onToggle,
}: CategoryFilterProps) {
  const allCategories = categories.length > 0 ? categories : Object.keys(CATEGORY_META);

  return (
    <div style={{ marginTop: 12 }}>
      <Space wrap size={8}>
        <span style={{ color: '#666', fontSize: 12 }}>分类筛选:</span>
        {allCategories.map(category => {
          const meta = CATEGORY_META[category] || CATEGORY_META.default;
          const isSelected = selectedCategories.includes(category);
          const count = counts[category] || 0;

          if (count === 0) return null;

          return (
            <Tag
              key={category}
              color={isSelected ? meta.color : undefined}
              style={{
                cursor: 'pointer',
                opacity: isSelected ? 1 : 0.7,
                fontSize: 12,
              }}
              onClick={() => onToggle(category)}
              icon={isSelected ? <CheckOutlined /> : undefined}
            >
              {meta.label} ({count})
            </Tag>
          );
        })}
      </Space>
    </div>
  );
}
```

- [ ] **Step 2: 提交**

```bash
git add app/frontend/src/components/SkillList/components/CategoryFilter.tsx
git commit -m "feat(skill-filter): add CategoryFilter component"
```

---

## Task 6: 创建筛选栏组件

**Files:**
- Create: `app/frontend/src/components/SkillList/components/SkillFilterBar.tsx`

- [ ] **Step 1: 创建 SkillFilterBar 组件**

```typescript
import { useState, useEffect, useCallback } from "react";
import { Input, Select, Space, Segmented, Badge } from "antd";
import {
  SearchOutlined,
  FilterOutlined,
} from "@ant-design/icons";
import CategoryFilter from "./CategoryFilter";
import ActiveFilters from "./ActiveFilters";
import type { SkillFilterState } from "../utils/filterSkills";
import type { UseSkillFilterReturn } from "../hooks/useSkillFilter";

const { Option } = Select;

interface SkillFilterBarProps {
  filter: SkillFilterState;
  counts: UseSkillFilterReturn['counts'];
  hasActiveFilters: boolean;
  allCategories: string[];
  allSources: string[];
  onKeywordChange: (keyword: string) => void;
  onStatusChange: (status: SkillFilterState['status']) => void;
  onCategoryToggle: (category: string) => void;
  onSourceToggle: (source: string) => void;
  onClearFilters: () => void;
  onRemoveCategory: (category: string) => void;
  onRemoveSource: (source: string) => void;
  onRemoveTag: (tag: string) => void;
}

export default function SkillFilterBar({
  filter,
  counts,
  hasActiveFilters,
  allCategories,
  allSources,
  onKeywordChange,
  onStatusChange,
  onCategoryToggle,
  onSourceToggle,
  onClearFilters,
  onRemoveCategory,
  onRemoveSource,
  onRemoveTag,
}: SkillFilterBarProps) {
  const [inputValue, setInputValue] = useState(filter.keyword);

  // 防抖处理
  useEffect(() => {
    const timer = setTimeout(() => {
      if (inputValue !== filter.keyword) {
        onKeywordChange(inputValue);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [inputValue, filter.keyword, onKeywordChange]);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setInputValue(e.target.value);
  }, []);

  return (
    <div style={{ marginBottom: 16 }}>
      {/* 第一行：搜索和状态筛选 */}
      <Space wrap style={{ width: '100%' }}>
        <Input
          placeholder="搜索 Skill 名称、描述..."
          prefix={<SearchOutlined />}
          value={inputValue}
          onChange={handleInputChange}
          style={{ width: 280 }}
          allowClear
        />

        <Segmented
          options={[
            { label: '全部', value: 'all' },
            { label: `已启用 (${counts.byStatus.enabled})`, value: 'enabled' },
            { label: `已禁用 (${counts.byStatus.disabled})`, value: 'disabled' },
          ]}
          value={filter.status}
          onChange={(value) => onStatusChange(value as SkillFilterState['status'])}
        />

        <Select
          placeholder="选择来源"
          style={{ width: 140 }}
          value={filter.sources.length > 0 ? filter.sources[0] : undefined}
          onChange={(value) => {
            if (value) {
              onSourceToggle(value);
            }
          }}
          allowClear
        >
          {allSources.map(source => (
            <Option key={source} value={source}>
              {source} ({counts.bySource[source] || 0})
            </Option>
          ))}
        </Select>

        {hasActiveFilters && (
          <Badge count={filter.categories.length + filter.sources.length + filter.tags.length + (filter.keyword ? 1 : 0) + (filter.status !== 'all' ? 1 : 0)}>
            <FilterOutlined style={{ color: '#1890ff' }} />
          </Badge>
        )}
      </Space>

      {/* 第二行：分类筛选 */}
      <CategoryFilter
        categories={allCategories}
        selectedCategories={filter.categories}
        counts={counts.byCategory}
        onToggle={onCategoryToggle}
      />

      {/* 第三行：已选筛选 */}
      <ActiveFilters
        filter={filter}
        onClearAll={onClearFilters}
        onRemoveCategory={onRemoveCategory}
        onRemoveSource={onRemoveSource}
        onRemoveTag={onRemoveTag}
      />
    </div>
  );
}
```

- [ ] **Step 2: 提交**

```bash
git add app/frontend/src/components/SkillList/components/SkillFilterBar.tsx
git commit -m "feat(skill-filter): add SkillFilterBar component"
```

---

## Task 7: 整合筛选功能到 SkillList

**Files:**
- Modify: `app/frontend/src/components/SkillList/index.tsx`

- [ ] **Step 1: 导入新组件和 Hook**

在 index.tsx 顶部添加导入：

```typescript
import { useSkillFilter } from "./hooks/useSkillFilter";
import SkillFilterBar from "./components/SkillFilterBar";
import EmptyResult from "./components/EmptyResult";
```

- [ ] **Step 2: 在组件中使用筛选功能**

在 SkillList 函数内部，替换现有的 filteredSkills 逻辑：

```typescript
// 使用筛选 Hook
const {
  filter,
  filteredSkills,
  counts,
  hasActiveFilters,
  clearFilters,
  setKeyword,
  setStatus,
  toggleCategory,
  toggleSource,
  toggleTag,
  removeCategory,
  removeSource,
  removeTag,
} = useSkillFilter(skills);

// 获取所有分类和来源（用于筛选下拉）
const allCategories = useMemo(() => {
  return Object.keys(groupedSkills);
}, [groupedSkills]);

const allSources = useMemo(() => {
  const sources = new Set<string>();
  skills.forEach(s => sources.add(s.source || 'default'));
  return Array.from(sources);
}, [skills]);
```

- [ ] **Step 3: 替换筛选后的分组逻辑**

替换 `groupedSkills` 的 useMemo：

```typescript
// 基于筛选后的 skills 进行分组
const groupedFilteredSkills = useMemo(() => {
  return filteredSkills.reduce((acc, skill) => {
    const category = skill.category || "default";
    if (!acc[category]) acc[category] = [];
    acc[category].push(skill);
    return acc;
  }, {} as Record<string, AgentSkill[]>);
}, [filteredSkills]);
```

- [ ] **Step 4: 在渲染区域添加筛选栏**

在 Skill 列表 Card 之前添加筛选栏：

```typescript
{/* 筛选栏 */}
<SkillFilterBar
  filter={filter}
  counts={counts}
  hasActiveFilters={hasActiveFilters}
  allCategories={allCategories}
  allSources={allSources}
  onKeywordChange={setKeyword}
  onStatusChange={setStatus}
  onCategoryToggle={toggleCategory}
  onSourceToggle={toggleSource}
  onClearFilters={clearFilters}
  onRemoveCategory={removeCategory}
  onRemoveSource={removeSource}
  onRemoveTag={removeTag}
/>
```

- [ ] **Step 5: 修改分组渲染逻辑**

将渲染部分的 `Object.entries(groupedSkills)` 改为 `Object.entries(groupedFilteredSkills)`，并添加空结果处理：

```typescript
{filteredSkills.length === 0 ? (
  <EmptyResult onClearFilters={clearFilters} />
) : (
  Object.entries(groupedFilteredSkills).map(([category, categorySkills]) => {
    // ... 原有渲染逻辑
  })
)}
```

- [ ] **Step 6: 导出 META 常量（用于 ActiveFilters）**

在文件末尾添加：

```typescript
export { CATEGORY_META, SOURCE_META };
```

- [ ] **Step 7: 提交**

```bash
git add app/frontend/src/components/SkillList/index.tsx
git commit -m "feat(skill-filter): integrate filter into SkillList"
```

---

## Task 8: 验证和测试

**Files:**
- Test: 浏览器手动验证

- [ ] **Step 1: 启动开发服务器**

```bash
cd app/frontend && npm run dev
```

- [ ] **Step 2: 验证功能点**

1. 打开 Skill 列表页面
2. 测试关键词搜索
3. 测试状态切换（全部/启用/禁用）
4. 测试分类点击筛选
5. 验证筛选结果数量显示正确
6. 验证"清除全部"功能
7. 验证空结果提示

- [ ] **Step 3: 提交最终版本**

```bash
git add .
git commit -m "feat(skill-filter): complete advanced filter feature for Skill list"
```

---

## 注意事项

1. **类型导入**：确保从正确的模块导入类型
2. **Ant Design 组件**：使用项目已有的组件（Input, Select, Tag, Segmented 等）
3. **样式**：保持与现有风格一致，使用内联 style 或 CSS 类
4. **性能**：使用 useMemo 缓存筛选结果
5. **空状态**：当没有匹配结果时显示友好提示
