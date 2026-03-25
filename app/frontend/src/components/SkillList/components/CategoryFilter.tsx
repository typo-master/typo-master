import { Space, Tag } from "antd";
import { CheckOutlined } from "@ant-design/icons";

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
