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
