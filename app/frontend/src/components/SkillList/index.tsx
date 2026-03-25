import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Avatar,
  Badge,
  Button,
  Card,
  Empty,
  Form,
  Input,
  List,
  Modal,
  Popconfirm,
  Select,
  Space,
  Spin,
  Tag,
  Tooltip,
  Typography,
  message,
} from "antd";
import {
  ApiOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  CloudDownloadOutlined,
  DeleteOutlined,
  DownloadOutlined,
  EditOutlined,
  FileSearchOutlined,
  FileTextOutlined,
  GitlabOutlined,
  LinkOutlined,
  PlusOutlined,
  SafetyOutlined,
  ThunderboltOutlined,
  ToolOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import { skillStore, type AgentSkill } from "../../db";
import {
  deleteSkill as deleteSkillApi,
  listSkills as listSkillsApi,
  upsertSkill as upsertSkillApi,
} from "../../api";
import { useSkillFilter } from "./hooks/useSkillFilter";
import SkillFilterBar from "./components/SkillFilterBar";
import EmptyResult from "./components/EmptyResult";

const { Text, Paragraph } = Typography;
const { TextArea } = Input;

interface SkillListProps {
  onSkillClick?: (skill: AgentSkill) => void;
  showDisabled?: boolean;
}

interface CreateSkillFormValue {
  name: string;
  description: string;
  category: string;
  enabled: boolean;
  version?: string;
  sourceUrl?: string;
  tags?: string;
  parameters?: string;
  executor?: string;
}

interface InstallUrlFormValue {
  url: string;
}

interface InstallJsonFormValue {
  manifest: string;
}

interface SkillPack {
  id: string;
  name: string;
  description: string;
  skills: AgentSkill[];
}

type ManifestPayload = AgentSkill | AgentSkill[] | { skills: AgentSkill[] };

const CATEGORY_META: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  discovery: { label: "发现", color: "blue", icon: <FileSearchOutlined /> },
  scanner: { label: "扫描", color: "cyan", icon: <FileSearchOutlined /> },
  fixer: { label: "修复", color: "green", icon: <EditOutlined /> },
  github: { label: "GitHub", color: "purple", icon: <GitlabOutlined /> },
  report: { label: "报告", color: "orange", icon: <FileTextOutlined /> },
  ai: { label: "AI", color: "geekblue", icon: <ApiOutlined /> },
  automation: { label: "自动化", color: "gold", icon: <ThunderboltOutlined /> },
  integration: { label: "集成", color: "magenta", icon: <CloudDownloadOutlined /> },
  security: { label: "安全", color: "red", icon: <SafetyOutlined /> },
  analysis: { label: "分析", color: "lime", icon: <ToolOutlined /> },
  default: { label: "其他", color: "default", icon: <ToolOutlined /> },
};

const SOURCE_META: Record<string, { label: string; color: string }> = {
  builtin: { label: "内置", color: "green" },
  custom: { label: "自定义", color: "gold" },
  community: { label: "社区", color: "blue" },
  default: { label: "未知", color: "default" },
};

const SKILL_CATEGORIES = [
  "discovery",
  "scanner",
  "fixer",
  "github",
  "report",
  "ai",
  "automation",
  "integration",
  "security",
  "analysis",
  "default",
];

const OPEN_SKILL_PACKS: SkillPack[] = [
  {
    id: "open-security-pack",
    name: "Open Skill Security Pack",
    description: "社区安全扫描技能包（Secrets / 依赖漏洞 / 不安全模式）",
    skills: [
      {
        name: "open_secret_guard",
        description: "扫描仓库中可能泄露的 Token、密钥和敏感配置。",
        category: "security",
        enabled: true,
        parameters: [
          { name: "path", type: "string", required: true, description: "待扫描目录" },
          { name: "strict", type: "boolean", required: false, description: "是否严格模式" },
        ],
        version: "1.0.0",
        tags: ["security", "secrets", "scan"],
      },
      {
        name: "open_dependency_audit",
        description: "检查依赖漏洞并输出修复建议。",
        category: "security",
        enabled: true,
        parameters: [
          { name: "manifest", type: "string", required: true, description: "依赖清单文件路径" },
          { name: "ecosystem", type: "string", required: false, description: "npm/pip/go" },
        ],
        version: "1.0.0",
        tags: ["security", "dependency"],
      },
      {
        name: "open_insecure_pattern_scan",
        description: "检测常见不安全代码模式（eval、弱加密、硬编码凭据等）。",
        category: "security",
        enabled: true,
        parameters: [
          { name: "path", type: "string", required: true, description: "扫描路径" },
          { name: "language", type: "string", required: false, description: "指定语言" },
        ],
        version: "1.0.0",
        tags: ["security", "static-analysis"],
      },
    ],
  },
  {
    id: "open-repo-automation-pack",
    name: "Open Skill Repo Automation Pack",
    description: "社区仓库自动化技能包（Issue/PR/发布辅助）",
    skills: [
      {
        name: "open_create_issue",
        description: "自动创建 Issue 并附带上下文与优先级。",
        category: "github",
        enabled: true,
        parameters: [
          { name: "owner", type: "string", required: true, description: "仓库 owner" },
          { name: "repo", type: "string", required: true, description: "仓库名" },
          { name: "title", type: "string", required: true, description: "Issue 标题" },
          { name: "body", type: "string", required: true, description: "Issue 内容" },
        ],
        version: "1.0.0",
        tags: ["github", "issue"],
      },
      {
        name: "open_release_note_builder",
        description: "根据提交记录和 PR 自动生成发布说明。",
        category: "report",
        enabled: true,
        parameters: [
          { name: "fromTag", type: "string", required: true, description: "起始 tag" },
          { name: "toTag", type: "string", required: true, description: "结束 tag" },
        ],
        version: "1.0.0",
        tags: ["release", "report"],
      },
      {
        name: "open_auto_triage",
        description: "按规则自动分派 Issue/PR 标签并给出下一步建议。",
        category: "automation",
        enabled: true,
        parameters: [
          { name: "owner", type: "string", required: true, description: "仓库 owner" },
          { name: "repo", type: "string", required: true, description: "仓库名" },
        ],
        version: "1.0.0",
        tags: ["automation", "triage"],
      },
    ],
  },
];

function sortSkills(a: AgentSkill, b: AgentSkill): number {
  const byCategory = String(a.category || "").localeCompare(String(b.category || ""));
  if (byCategory !== 0) return byCategory;
  return String(a.name || "").localeCompare(String(b.name || ""));
}

function parseManifest(payload: ManifestPayload): AgentSkill[] {
  if (Array.isArray(payload)) {
    return payload;
  }
  if (payload && typeof payload === "object" && Array.isArray((payload as any).skills)) {
    return (payload as any).skills;
  }
  if (
    payload &&
    typeof payload === "object" &&
    typeof (payload as AgentSkill).name === "string" &&
    typeof (payload as AgentSkill).description === "string"
  ) {
    return [payload as AgentSkill];
  }
  throw new Error("Manifest 格式不正确，支持 skill 对象、skills 数组、或 { skills: [] }");
}

function normalizeSkill(
  raw: AgentSkill,
  defaults?: { source?: AgentSkill["source"]; sourceUrl?: string; installMethod?: AgentSkill["installMethod"] }
): AgentSkill {
  const now = Date.now();
  const name = String(raw.name || "").trim();
  const description = String(raw.description || "").trim();

  if (!name) throw new Error("Skill 缺少 name");
  if (!description) throw new Error("Skill " + name + " 缺少 description");

  const parameters = Array.isArray(raw.parameters)
    ? raw.parameters
        .filter((item) => item && item.name)
        .map((item) => ({
          name: String(item.name || "").trim(),
          type: String(item.type || "string").trim() || "string",
          required: Boolean(item.required),
          description: item.description ? String(item.description).trim() : undefined,
        }))
    : undefined;

  const tags = Array.isArray(raw.tags)
    ? Array.from(
        new Set(
          raw.tags
            .map((item) => String(item || "").trim())
            .filter(Boolean)
        )
      )
    : undefined;

  return {
    ...raw,
    name,
    description,
    category: String(raw.category || "default"),
    enabled: raw.enabled ?? true,
    parameters,
    tags,
    source: raw.source ?? defaults?.source ?? "custom",
    sourceUrl: raw.sourceUrl ?? defaults?.sourceUrl,
    installMethod: raw.installMethod ?? defaults?.installMethod ?? "manual",
    createdAt: raw.createdAt ?? now,
    updatedAt: now,
  };
}

function buildDefaultSkills(): AgentSkill[] {
  return [
    {
      name: "search_github_repos",
      description: "搜索 GitHub 仓库，支持星标、语言、更新时间筛选。",
      category: "discovery",
      enabled: true,
      parameters: [
        { name: "query", type: "string", required: true, description: "搜索关键词" },
        { name: "minStars", type: "number", required: false, description: "最小星标数" },
        { name: "language", type: "string", required: false, description: "编程语言" },
      ],
      source: "builtin",
      installMethod: "catalog",
      version: "1.0.0",
      tags: ["github", "discovery"],
    },
    {
      name: "search_trending_repos",
      description: "按时间窗口检索热门趋势仓库。",
      category: "discovery",
      enabled: true,
      parameters: [
        { name: "window", type: "string", required: false, description: "daily/weekly/monthly" },
        { name: "language", type: "string", required: false, description: "编程语言" },
      ],
      source: "builtin",
      installMethod: "catalog",
      version: "1.0.0",
      tags: ["github", "trending"],
    },
    {
      name: "scan_typo",
      description: "扫描代码和文档中的拼写错误。",
      category: "scanner",
      enabled: true,
      parameters: [
        { name: "path", type: "string", required: true, description: "扫描路径" },
        { name: "extensions", type: "array", required: false, description: "文件扩展名列表" },
      ],
      source: "builtin",
      installMethod: "catalog",
      version: "1.0.0",
      tags: ["scanner", "typo"],
    },
    {
      name: "scan_markdown_quality",
      description: "扫描 Markdown 标题、链接、术语一致性问题。",
      category: "scanner",
      enabled: true,
      parameters: [{ name: "path", type: "string", required: true, description: "文档目录" }],
      source: "builtin",
      installMethod: "catalog",
      version: "1.0.0",
      tags: ["docs", "quality"],
    },
    {
      name: "scan_security_secrets",
      description: "检测敏感信息泄露（API Key、Token、私钥片段等）。",
      category: "security",
      enabled: true,
      parameters: [
        { name: "path", type: "string", required: true, description: "扫描路径" },
        { name: "strict", type: "boolean", required: false, description: "严格模式" },
      ],
      source: "builtin",
      installMethod: "catalog",
      version: "1.0.0",
      tags: ["security", "secrets"],
    },
    {
      name: "scan_dependency_vulns",
      description: "扫描依赖漏洞并输出高危项清单。",
      category: "security",
      enabled: true,
      parameters: [
        { name: "manifest", type: "string", required: true, description: "依赖清单路径" },
        { name: "ecosystem", type: "string", required: false, description: "npm/pip/go" },
      ],
      source: "builtin",
      installMethod: "catalog",
      version: "1.0.0",
      tags: ["security", "dependency"],
    },
    {
      name: "evaluate_quality",
      description: "评估扫描结果质量并过滤误报。",
      category: "analysis",
      enabled: true,
      parameters: [{ name: "findings", type: "array", required: true, description: "扫描结果列表" }],
      source: "builtin",
      installMethod: "catalog",
      version: "1.0.0",
      tags: ["analysis", "quality"],
    },
    {
      name: "run_sql",
      description: "执行 SQL 查询（默认建议只读查询）。",
      category: "analysis",
      enabled: true,
      parameters: [
        { name: "database", type: "string", required: true, description: "SQLite 数据库文件路径" },
        { name: "query", type: "string", required: true, description: "SQL 语句" },
        { name: "args", type: "array", required: false, description: "SQL 参数列表" },
      ],
      executor: {
        type: "sql",
        read_only: true,
      },
      source: "builtin",
      installMethod: "catalog",
      version: "1.0.0",
      tags: ["sql", "database", "analysis"],
    },
    {
      name: "fix_typo",
      description: "自动修复拼写错误并生成变更摘要。",
      category: "fixer",
      enabled: true,
      parameters: [
        { name: "file", type: "string", required: true, description: "文件路径" },
        { name: "replacements", type: "array", required: true, description: "替换规则列表" },
      ],
      source: "builtin",
      installMethod: "catalog",
      version: "1.0.0",
      tags: ["fix", "typo"],
    },
    {
      name: "fix_markdown_typo",
      description: "针对 Markdown 内容进行保守修复，尽量不破坏格式。",
      category: "fixer",
      enabled: true,
      parameters: [{ name: "file", type: "string", required: true, description: "文档路径" }],
      source: "builtin",
      installMethod: "catalog",
      version: "1.0.0",
      tags: ["fix", "docs"],
    },
    {
      name: "create_pr",
      description: "创建 Pull Request 提交修复结果。",
      category: "github",
      enabled: true,
      parameters: [
        { name: "owner", type: "string", required: true, description: "仓库 owner" },
        { name: "repo", type: "string", required: true, description: "仓库名" },
        { name: "title", type: "string", required: true, description: "PR 标题" },
        { name: "description", type: "string", required: false, description: "PR 描述" },
      ],
      source: "builtin",
      installMethod: "catalog",
      version: "1.0.0",
      tags: ["github", "pr"],
    },
    {
      name: "create_issue",
      description: "创建 Issue 并附加问题上下文。",
      category: "github",
      enabled: true,
      parameters: [
        { name: "owner", type: "string", required: true, description: "仓库 owner" },
        { name: "repo", type: "string", required: true, description: "仓库名" },
        { name: "title", type: "string", required: true, description: "Issue 标题" },
        { name: "body", type: "string", required: true, description: "Issue 内容" },
      ],
      source: "builtin",
      installMethod: "catalog",
      version: "1.0.0",
      tags: ["github", "issue"],
    },
    {
      name: "generate_report",
      description: "生成 JSON/Markdown/HTML 报告。",
      category: "report",
      enabled: true,
      parameters: [
        { name: "format", type: "string", required: true, description: "json/md/html/csv" },
        { name: "data", type: "object", required: true, description: "报告数据" },
      ],
      source: "builtin",
      installMethod: "catalog",
      version: "1.0.0",
      tags: ["report"],
    },
    {
      name: "export_report_csv",
      description: "将结果导出为 CSV，方便外部系统分析。",
      category: "report",
      enabled: true,
      parameters: [
        { name: "rows", type: "array", required: true, description: "导出数据行" },
        { name: "output", type: "string", required: true, description: "输出文件路径" },
      ],
      source: "builtin",
      installMethod: "catalog",
      version: "1.0.0",
      tags: ["report", "csv"],
    },
    {
      name: "ask_ai",
      description: "向 AI 助手提问并获得建议。",
      category: "ai",
      enabled: true,
      parameters: [
        { name: "question", type: "string", required: true, description: "问题内容" },
        { name: "context", type: "string", required: false, description: "上下文信息" },
      ],
      source: "builtin",
      installMethod: "catalog",
      version: "1.0.0",
      tags: ["ai"],
    },
    {
      name: "summarize_diff",
      description: "总结代码变更，生成审阅摘要和风险提示。",
      category: "ai",
      enabled: true,
      parameters: [{ name: "diff", type: "string", required: true, description: "Git diff 内容" }],
      source: "builtin",
      installMethod: "catalog",
      version: "1.0.0",
      tags: ["ai", "summary"],
    },
    {
      name: "batch_scan",
      description: "并发扫描多个仓库或目录。",
      category: "automation",
      enabled: true,
      parameters: [
        { name: "targets", type: "array", required: true, description: "扫描目标列表" },
        { name: "concurrency", type: "number", required: false, description: "并发数" },
      ],
      source: "builtin",
      installMethod: "catalog",
      version: "1.0.0",
      tags: ["automation", "batch"],
    },
    {
      name: "webhook_notify",
      description: "将执行结果推送到 Webhook（飞书/Slack/自定义服务）。",
      category: "integration",
      enabled: true,
      parameters: [
        { name: "url", type: "string", required: true, description: "Webhook 地址" },
        { name: "payload", type: "object", required: true, description: "推送内容" },
      ],
      source: "builtin",
      installMethod: "catalog",
      version: "1.0.0",
      tags: ["integration", "webhook"],
    },
  ];
}

export default function SkillList({ onSkillClick, showDisabled = true }: SkillListProps) {
  const [skills, setSkills] = useState<AgentSkill[]>([]);
  const [loading, setLoading] = useState(true);
  const [installing, setInstalling] = useState(false);

  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [installUrlModalOpen, setInstallUrlModalOpen] = useState(false);
  const [installJsonModalOpen, setInstallJsonModalOpen] = useState(false);

  const [createForm] = Form.useForm<CreateSkillFormValue>();
  const [installUrlForm] = Form.useForm<InstallUrlFormValue>();
  const [installJsonForm] = Form.useForm<InstallJsonFormValue>();

  const loadSkills = async () => {
    setLoading(true);
    try {
      let existingRaw: AgentSkill[] = [];
      let useBackendRegistry = false;
      try {
        const remote = await listSkillsApi();
        existingRaw = (remote.skills as AgentSkill[]) ?? [];
        useBackendRegistry = true;
      } catch (error) {
        console.warn("Skill registry API unavailable, fallback to local IndexedDB:", error);
        existingRaw = await skillStore.getAll();
      }

      const existingMap = new Map<string, AgentSkill>();

      for (const raw of existingRaw) {
        try {
          const normalized = normalizeSkill(raw, {
            source: raw.source ?? "custom",
            sourceUrl: raw.sourceUrl,
            installMethod: raw.installMethod ?? "manual",
          });
          existingMap.set(normalized.name, normalized);
        } catch (error) {
          console.warn("Skip invalid skill record:", raw, error);
        }
      }

      const defaults = buildDefaultSkills();
      const mergedMap = new Map(existingMap);

      for (const defaultSkill of defaults) {
        const normalizedDefault = normalizeSkill(defaultSkill, {
          source: "builtin",
          installMethod: "catalog",
        });
        const current = mergedMap.get(normalizedDefault.name);

        if (!current) {
          mergedMap.set(normalizedDefault.name, normalizedDefault);
          await skillStore.update(normalizedDefault);
          if (useBackendRegistry) {
            await upsertSkillApi(normalizedDefault.name, normalizedDefault);
          }
          continue;
        }

        const mergedBuiltin = normalizeSkill(
          {
            ...normalizedDefault,
            ...current,
            source: "builtin",
            installMethod: current.installMethod ?? "catalog",
            enabled: current.enabled ?? normalizedDefault.enabled,
            createdAt: current.createdAt ?? normalizedDefault.createdAt,
          },
          { source: "builtin", installMethod: "catalog" }
        );

        mergedMap.set(mergedBuiltin.name, mergedBuiltin);
        await skillStore.update(mergedBuiltin);
        if (useBackendRegistry) {
          await upsertSkillApi(mergedBuiltin.name, mergedBuiltin);
        }
      }

      setSkills(Array.from(mergedMap.values()).sort(sortSkills));
    } catch (error) {
      console.error("Failed to load skills:", error);
      message.error("加载 Skill 失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadSkills();
  }, []);

  // 使用筛选 Hook，根据 showDisabled 设置初始状态
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
  } = useSkillFilter(skills, showDisabled);

  // 获取所有分类和来源（用于筛选下拉）
  const allCategories = useMemo(() => {
    return Object.keys(groupedSkills);
  }, [groupedSkills]);

  const allSources = useMemo(() => {
    const sources = new Set<string>();
    skills.forEach(s => sources.add(s.source || 'default'));
    return Array.from(sources);
  }, [skills]);

  const groupedSkills = useMemo(() => {
    return skills.reduce((acc, skill) => {
      const category = skill.category || "default";
      if (!acc[category]) acc[category] = [];
      acc[category].push(skill);
      return acc;
    }, {} as Record<string, AgentSkill[]>);
  }, [skills]);

  // 基于筛选后的 skills 进行分组
  const groupedFilteredSkills = useMemo(() => {
    return filteredSkills.reduce((acc, skill) => {
      const category = skill.category || "default";
      if (!acc[category]) acc[category] = [];
      acc[category].push(skill);
      return acc;
    }, {} as Record<string, AgentSkill[]>);
  }, [filteredSkills]);

  const upsertSkills = async (incoming: AgentSkill[]) => {
    for (const raw of incoming) {
      const existing = await skillStore.get(raw.name);
      const normalized = normalizeSkill(
        {
          ...(existing || {}),
          ...raw,
          name: raw.name,
          createdAt: existing?.createdAt ?? raw.createdAt,
        },
        {
          source: raw.source ?? existing?.source ?? "custom",
          sourceUrl: raw.sourceUrl ?? existing?.sourceUrl,
          installMethod: raw.installMethod ?? existing?.installMethod ?? "manual",
        }
      );
      await upsertSkillApi(normalized.name, normalized);
      await skillStore.update(normalized);
    }
    await loadSkills();
  };

  const handleToggleSkill = async (skill: AgentSkill) => {
    try {
      const updated = normalizeSkill(
        { ...skill, enabled: !skill.enabled },
        {
          source: skill.source,
          sourceUrl: skill.sourceUrl,
          installMethod: skill.installMethod,
        }
      );
      await upsertSkillApi(updated.name, updated);
      await skillStore.update(updated);
      setSkills((prev) => prev.map((item) => (item.name === updated.name ? updated : item)).sort(sortSkills));
    } catch (error) {
      console.error("Failed to toggle skill:", error);
      message.error("切换 Skill 状态失败");
    }
  };

  const handleDeleteSkill = async (skill: AgentSkill) => {
    if (skill.source === "builtin") {
      message.warning("内置 Skill 不支持删除");
      return;
    }
    try {
      await deleteSkillApi(skill.name);
      await skillStore.delete(skill.name);
      setSkills((prev) => prev.filter((item) => item.name !== skill.name));
      message.success("已删除 Skill: " + skill.name);
    } catch (error) {
      console.error("Failed to delete skill:", error);
      message.error("删除 Skill 失败");
    }
  };

  const installFromManifest = async (
    payload: ManifestPayload,
    defaults: { source: AgentSkill["source"]; sourceUrl?: string; installMethod: AgentSkill["installMethod"] }
  ) => {
    const rawSkills = parseManifest(payload);
    if (!rawSkills.length) {
      throw new Error("Manifest 中未找到任何 Skill");
    }

    const normalized = rawSkills.map((skill) =>
      normalizeSkill(
        {
          ...skill,
          source: skill.source ?? defaults.source,
          sourceUrl: skill.sourceUrl ?? defaults.sourceUrl,
          installMethod: skill.installMethod ?? defaults.installMethod,
        },
        defaults
      )
    );

    await upsertSkills(normalized);
    return normalized.length;
  };

  const handleCreateSkill = async () => {
    try {
      const values = await createForm.validateFields();

      const existing = skills.find((skill) => skill.name === values.name.trim());
      if (existing?.source === "builtin") {
        message.error("内置 Skill 名称不可覆盖，请换一个名称");
        return;
      }

      let parsedParameters: AgentSkill["parameters"];
      if (values.parameters && values.parameters.trim()) {
        try {
          const parsed = JSON.parse(values.parameters);
          if (!Array.isArray(parsed)) {
            message.error("参数 JSON 必须是数组");
            return;
          }
          parsedParameters = parsed;
        } catch (error) {
          message.error("参数 JSON 格式错误，示例: [{\"name\":\"query\",\"type\":\"string\",\"required\":true}]");
          return;
        }
      }

      const tags = values.tags
        ? values.tags
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean)
        : undefined;

      let parsedExecutor: AgentSkill["executor"];
      if (values.executor && values.executor.trim()) {
        try {
          const parsed = JSON.parse(values.executor);
          if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
            message.error("执行器 JSON 必须是对象，例如 {\"type\":\"workflow\",\"workflow\":\"single_project\"}");
            return;
          }
          parsedExecutor = parsed as AgentSkill["executor"];
        } catch (error) {
          message.error("执行器 JSON 格式错误");
          return;
        }
      }

      const skill = normalizeSkill(
        {
          name: values.name.trim(),
          description: values.description.trim(),
          category: values.category,
          enabled: values.enabled,
          version: values.version?.trim(),
          sourceUrl: values.sourceUrl?.trim() || undefined,
          tags,
          parameters: parsedParameters,
          executor: parsedExecutor,
          source: "custom",
          installMethod: "manual",
        },
        { source: "custom", installMethod: "manual" }
      );

      await upsertSkills([skill]);
      message.success(existing ? "已更新 Skill: " + skill.name : "已创建 Skill: " + skill.name);

      setCreateModalOpen(false);
      createForm.resetFields();
    } catch (error) {
      if (error instanceof Error && error.message.includes("out of date")) return;
      console.error("Failed to create skill:", error);
    }
  };

  const handleInstallFromUrl = async () => {
    try {
      const values = await installUrlForm.validateFields();
      setInstalling(true);

      const url = values.url.trim();
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error("下载失败: HTTP " + response.status);
      }
      const payload = (await response.json()) as ManifestPayload;
      const count = await installFromManifest(payload, {
        source: "community",
        sourceUrl: url,
        installMethod: "url",
      });

      message.success("已从 URL 安装/更新 " + count + " 个 Skill");
      setInstallUrlModalOpen(false);
      installUrlForm.resetFields();
    } catch (error) {
      if (error instanceof Error && error.message.includes("out of date")) return;
      console.error("Install from URL failed:", error);
      message.error(error instanceof Error ? error.message : "从 URL 安装失败");
    } finally {
      setInstalling(false);
    }
  };

  const handleInstallFromJson = async () => {
    try {
      const values = await installJsonForm.validateFields();
      setInstalling(true);

      let payload: ManifestPayload;
      try {
        payload = JSON.parse(values.manifest);
      } catch (error) {
        message.error("JSON 解析失败，请检查格式");
        return;
      }

      const count = await installFromManifest(payload, {
        source: "community",
        installMethod: "json",
      });

      message.success("已从 JSON 安装/更新 " + count + " 个 Skill");
      setInstallJsonModalOpen(false);
      installJsonForm.resetFields();
    } catch (error) {
      if (error instanceof Error && error.message.includes("out of date")) return;
      console.error("Install from JSON failed:", error);
      message.error(error instanceof Error ? error.message : "从 JSON 安装失败");
    } finally {
      setInstalling(false);
    }
  };

  const handleInstallPack = async (pack: SkillPack) => {
    try {
      setInstalling(true);
      const count = await installFromManifest(
        { skills: pack.skills },
        { source: "community", installMethod: "catalog" }
      );
      message.success("已安装技能包「" + pack.name + "」，共 " + count + " 个 Skill");
    } catch (error) {
      console.error("Install pack failed:", error);
      message.error(error instanceof Error ? error.message : "安装技能包失败");
    } finally {
      setInstalling(false);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: 40 }}>
        <Spin tip="加载 Skill 中..." />
      </div>
    );
  }

  return (
    <div className="skill-list">
      <Card
        size="small"
        style={{ marginBottom: 16 }}
        title={
          <Space>
            <ToolOutlined />
            <Text strong>Skill 扩展中心</Text>
            <Tag color="green">{skills.length} 总数</Tag>
          </Space>
        }
      >
        <Space wrap>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalOpen(true)}>
            创建 Skill
          </Button>
          <Button icon={<LinkOutlined />} onClick={() => setInstallUrlModalOpen(true)}>
            从 URL 安装
          </Button>
          <Button icon={<UploadOutlined />} onClick={() => setInstallJsonModalOpen(true)}>
            粘贴 JSON 安装
          </Button>
          <Button icon={<DownloadOutlined />} onClick={() => void loadSkills()}>
            刷新列表
          </Button>
        </Space>
        <Alert
          style={{ marginTop: 12 }}
          type="info"
          showIcon
          message="支持 Open Skill 自定义安装"
          description={
            <Space direction="vertical" size={4}>
              <Text type="secondary">可安装 skill manifest（单个 Skill、Skill 数组、或 {"{ skills: [] }"}）。</Text>
              <Text type="secondary">推荐把开源仓库里的 manifest.json/raw URL 粘贴到「从 URL 安装」。</Text>
            </Space>
          }
        />
      </Card>

      <Card
        size="small"
        style={{ marginBottom: 16 }}
        title={
          <Space>
            <CloudDownloadOutlined />
            <Text strong>社区技能包（示例）</Text>
          </Space>
        }
      >
        <List
          size="small"
          dataSource={OPEN_SKILL_PACKS}
          renderItem={(pack) => (
            <List.Item
              actions={[
                <Button
                  key={pack.id}
                  size="small"
                  type="link"
                  loading={installing}
                  onClick={() => void handleInstallPack(pack)}
                >
                  一键安装
                </Button>,
              ]}
            >
              <List.Item.Meta
                title={<Text strong>{pack.name}</Text>}
                description={
                  <Space direction="vertical" size={0}>
                    <Text type="secondary">{pack.description}</Text>
                    <Text type="secondary">包含 {pack.skills.length} 个 Skill</Text>
                  </Space>
                }
              />
            </List.Item>
          )}
        />
      </Card>

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

      {filteredSkills.length === 0 ? (
        <EmptyResult onClearFilters={clearFilters} />
      ) : (
        Object.entries(groupedFilteredSkills).map(([category, categorySkills]) => {
          const categoryMeta = CATEGORY_META[category] || CATEGORY_META.default;

          return (
            <Card
              key={category}
              size="small"
              title={
                <Space>
                  <Tag color={categoryMeta.color}>{categoryMeta.label}</Tag>
                  <Text type="secondary">({categorySkills.length})</Text>
                </Space>
              }
              style={{ marginBottom: 16 }}
            >
              <List
                size="small"
                dataSource={categorySkills.sort(sortSkills)}
                renderItem={(skill) => {
                  const sourceMeta = SOURCE_META[skill.source || "default"] || SOURCE_META.default;
                  const icon = (CATEGORY_META[skill.category || "default"] || CATEGORY_META.default).icon;

                  return (
                    <List.Item
                      onClick={() => onSkillClick?.(skill)}
                      style={{ cursor: onSkillClick ? "pointer" : "default" }}
                      actions={[
                        <Tooltip title={skill.enabled ? "点击禁用" : "点击启用"} key="toggle">
                          <Badge
                            status={skill.enabled ? "success" : "default"}
                            text={
                              skill.enabled ? (
                                <CheckCircleOutlined style={{ color: "#22c55e" }} />
                              ) : (
                                <CloseCircleOutlined style={{ color: "#999" }} />
                              )
                            }
                            onClick={(event) => {
                              event.stopPropagation();
                              void handleToggleSkill(skill);
                            }}
                          />
                        </Tooltip>,
                        skill.source !== "builtin" ? (
                          <Popconfirm
                            key="delete"
                            title={"删除 Skill: " + skill.name + " ?"}
                            onConfirm={(event) => {
                              event?.stopPropagation();
                              void handleDeleteSkill(skill);
                            }}
                          >
                            <Button
                              type="text"
                              size="small"
                              icon={<DeleteOutlined />}
                              onClick={(event) => event.stopPropagation()}
                            />
                          </Popconfirm>
                        ) : null,
                      ].filter(Boolean)}
                    >
                      <List.Item.Meta
                        avatar={
                          <Avatar
                            size="small"
                            icon={icon}
                            style={{ background: skill.enabled ? "#22c55e" : "#ccc" }}
                          />
                        }
                        title={
                          <Space wrap>
                            <Text strong>{skill.name}</Text>
                            <Tag color={sourceMeta.color}>{sourceMeta.label}</Tag>
                            {skill.version ? <Tag>{skill.version}</Tag> : null}
                            {skill.parameters && skill.parameters.length > 0 ? (
                              <Tag color="blue">{skill.parameters.length} 参数</Tag>
                            ) : null}
                          </Space>
                        }
                        description={
                          <Space direction="vertical" size={2} style={{ width: "100%" }}>
                            <Paragraph type="secondary" style={{ margin: 0, fontSize: 12 }} ellipsis={{ rows: 2 }}>
                              {skill.description}
                            </Paragraph>
                            <Space size={4} wrap>
                              {(skill.tags || []).slice(0, 4).map((tag) => (
                                <Tag key={tag}>{tag}</Tag>
                              ))}
                              {skill.sourceUrl ? (
                                <Text type="secondary" style={{ fontSize: 12 }}>
                                  来源: {skill.sourceUrl}
                                </Text>
                              ) : null}
                            </Space>
                          </Space>
                        }
                      />
                    </List.Item>
                  );
                }}
              />
            </Card>
          );
        })
      )}

      <Modal
        title="创建自定义 Skill"
        open={createModalOpen}
        onCancel={() => {
          setCreateModalOpen(false);
          createForm.resetFields();
        }}
        onOk={() => void handleCreateSkill()}
        okText="保存"
      >
        <Form
          layout="vertical"
          form={createForm}
          initialValues={{
            category: "default",
            enabled: true,
          }}
        >
          <Form.Item
            label="Skill 名称"
            name="name"
            rules={[
              { required: true, message: "请输入 Skill 名称" },
              { pattern: /^[a-zA-Z0-9_:-]+$/, message: "仅支持字母数字、下划线、冒号、短横线" },
            ]}
          >
            <Input placeholder="例如: custom_repo_summary" />
          </Form.Item>

          <Form.Item label="描述" name="description" rules={[{ required: true, message: "请输入描述" }]}>
            <TextArea rows={3} placeholder="描述这个 Skill 的作用和输出" />
          </Form.Item>

          <Form.Item label="分类" name="category" rules={[{ required: true, message: "请选择分类" }]}>
            <Select>
              {SKILL_CATEGORIES.map((category) => (
                <Select.Option key={category} value={category}>
                  {(CATEGORY_META[category] || CATEGORY_META.default).label}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item label="版本（可选）" name="version">
            <Input placeholder="例如: 1.0.0" />
          </Form.Item>

          <Form.Item label="来源 URL（可选）" name="sourceUrl">
            <Input placeholder="例如: https://github.com/xxx/skills/manifest.json" />
          </Form.Item>

          <Form.Item label="标签（逗号分隔）" name="tags">
            <Input placeholder="例如: security,scanner,custom" />
          </Form.Item>

          <Form.Item label="参数定义 JSON（可选）" name="parameters">
            <TextArea
              rows={4}
              placeholder='例如: [{"name":"query","type":"string","required":true,"description":"搜索词"}]'
            />
          </Form.Item>

          <Form.Item label="执行器 JSON（可选）" name="executor">
            <TextArea
              rows={4}
              placeholder='例如: {"type":"workflow","workflow":"single_project","ownerParam":"owner","repoParam":"repo"}'
            />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="从 URL 安装 Skill"
        open={installUrlModalOpen}
        onCancel={() => {
          setInstallUrlModalOpen(false);
          installUrlForm.resetFields();
        }}
        onOk={() => void handleInstallFromUrl()}
        okText="安装"
        confirmLoading={installing}
      >
        <Form layout="vertical" form={installUrlForm}>
          <Form.Item
            label="Manifest URL"
            name="url"
            rules={[
              { required: true, message: "请输入 manifest URL" },
              { type: "url", message: "请输入有效 URL" },
            ]}
          >
            <Input placeholder="https://raw.githubusercontent.com/.../skills.json" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="粘贴 JSON 安装 Skill"
        open={installJsonModalOpen}
        onCancel={() => {
          setInstallJsonModalOpen(false);
          installJsonForm.resetFields();
        }}
        onOk={() => void handleInstallFromJson()}
        okText="安装"
        confirmLoading={installing}
        width={760}
      >
        <Form layout="vertical" form={installJsonForm}>
          <Form.Item
            label="Skill Manifest JSON"
            name="manifest"
            rules={[{ required: true, message: "请粘贴 JSON" }]}
          >
            <TextArea
              rows={10}
              placeholder='支持三种格式: {"name":"..."} / [{"name":"..."}] / {"skills":[...]}'
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

export function SkillDetail({ skill }: { skill: AgentSkill }) {
  const categoryMeta = CATEGORY_META[skill.category || "default"] || CATEGORY_META.default;
  const sourceMeta = SOURCE_META[skill.source || "default"] || SOURCE_META.default;

  return (
    <Card title={skill.name}>
      <Paragraph>{skill.description}</Paragraph>
      <Space wrap>
        <Tag color={categoryMeta.color}>{categoryMeta.label}</Tag>
        <Tag color={sourceMeta.color}>{sourceMeta.label}</Tag>
        {skill.version ? <Tag>{skill.version}</Tag> : null}
      </Space>
      <Paragraph style={{ marginTop: 12 }}>
        {skill.parameters?.length ? "参数数量: " + skill.parameters.length : "无参数定义"}
      </Paragraph>
    </Card>
  );
}
