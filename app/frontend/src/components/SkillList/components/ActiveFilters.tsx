import { Space, Tag, Button } from "antd";
import type { SkillFilterState } from "../utils/filterSkills";

// 重新定义 META 常量以避免循环依赖
const CATEGORY_META: Record<string, { label: string; color: string }> = {
  discovery: { label: "发现", color: "blue" },
  scanner: { label: "扫描", color: "cyan" },
  fixer: { label: "修复", color: "green" },
  github: { label: "GitHub", color: "purple" },
  report: { label: "报告", color: "orange" },
  ai: { label: "AI", color: "geekblue" },
  automation: { label: "自动化", color: "gold" },
  integration: { label: "集成", color: "magenta" },
  security: { label: "安全", color: "red" },
  analysis: { label: "分析", color: "lime" },
  default: { label: "其他", color: "default" },
};

const SOURCE_META: Record<string, { label: string; color: string }> = {
  builtin: { label: "内置", color: "green" },
  custom: { label: "自定义", color: "gold" },
  community: { label: "社区", color: "blue" },
  default: { label: "未知", color: "default" },
};

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
