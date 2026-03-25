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
