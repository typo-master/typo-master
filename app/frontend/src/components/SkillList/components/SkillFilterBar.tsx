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

// 重新定义 META 常量以避免循环依赖
const SOURCE_META: Record<string, { label: string; color: string }> = {
  builtin: { label: "内置", color: "green" },
  custom: { label: "自定义", color: "gold" },
  community: { label: "社区", color: "blue" },
  default: { label: "未知", color: "default" },
};

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
              {SOURCE_META[source]?.label || source} ({counts.bySource[source] || 0})
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
