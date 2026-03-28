import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  Alert,
  Button,
  Card,
  Col,
  Row,
  Space,
  Steps,
  Tag,
  Typography,
} from "antd";
import {
  ApiOutlined,
  ArrowRightOutlined,
  BranchesOutlined,
  BugOutlined,
  CheckCircleOutlined,
  CloudOutlined,
  DashboardOutlined,
  DatabaseOutlined,
  FileSearchOutlined,
  FileTextOutlined,
  GithubOutlined,
  PlayCircleOutlined,
  PullRequestOutlined,
  RocketOutlined,
  SafetyOutlined,
  SearchOutlined,
  SettingOutlined,
  TeamOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";
import { Link } from "react-router-dom";
import { useConfig } from "../config";
import { fetchCapabilities } from "../api";
import type { CapabilityPayload } from "../types";

const { Title, Paragraph, Text } = Typography;

interface CapabilityFeatureMeta {
  title: string;
  description: string;
  icon: ReactNode;
}

const capabilityFeatureMeta: Record<string, CapabilityFeatureMeta> = {
  project_discovery: {
    title: "仓库发现",
    description: "快速定位值得治理的目标仓库和文档目录",
    icon: <SearchOutlined />,
  },
  typo_scan: {
    title: "智能扫描",
    description: "覆盖代码与文档，自动识别拼写与术语问题",
    icon: <FileSearchOutlined />,
  },
  quality_evaluation: {
    title: "质量评估",
    description: "结合上下文过滤误报，输出更可信的结果",
    icon: <SafetyOutlined />,
  },
  typo_fix: {
    title: "自动修复",
    description: "批量生成修复建议，尽量不破坏语义",
    icon: <BugOutlined />,
  },
  pr_decision: {
    title: "PR 决策",
    description: "按规则判断是否值得提交 PR",
    icon: <PullRequestOutlined />,
  },
  pr_creation: {
    title: "PR 生成",
    description: "自动整理修改说明并发起 Pull Request",
    icon: <GithubOutlined />,
  },
  report_generation: {
    title: "结果报告",
    description: "支持 JSON / Markdown / HTML / CSV 输出",
    icon: <FileTextOutlined />,
  },
  llm_decision_support: {
    title: "LLM 辅助",
    description: "在关键节点提供模型推理支持",
    icon: <ThunderboltOutlined />,
  },
  mcp_tool_execution: {
    title: "MCP 互联",
    description: "可直接调用外部 MCP Server 的工具能力",
    icon: <CloudOutlined />,
  },
  sql_execution: {
    title: "SQL 分析",
    description: "通过 Skill 执行查询，辅助质量诊断",
    icon: <DatabaseOutlined />,
  },
};

const painPoints = [
  {
    title: "代码审查总漏掉拼写细节",
    desc: "变量名、注释、文档里的拼写错误，人工 review 很难全面覆盖，上线后才发现尴尬。",
    icon: <FileSearchOutlined />,
  },
  {
    title: "术语不一致影响专业形象",
    desc: "代码里叫 userId，文档里叫 user_id，API 里叫 userID，混乱的术语让协作成本飙升。",
    icon: <BranchesOutlined />,
  },
  {
    title: "质量检查沦为重复劳动",
    desc: "每次发版前手工检查拼写、核对术语，耗时耗力还容易遗漏，开发体验糟糕。",
    icon: <BugOutlined />,
  },
];

const scenarios = [
  {
    title: "开源项目维护",
    desc: "自动扫描大量文档和代码，确保专业形象，减少外部贡献者的拼写困扰。",
    icon: <TeamOutlined />,
  },
  {
    title: "企业代码治理",
    desc: "统一多仓库术语规范，建立可重复的质量检查流程，降低协作摩擦。",
    icon: <CloudOutlined />,
  },
  {
    title: "技术文档交付",
    desc: "在发布前自动检查文档拼写和术语一致性，提升交付质量。",
    icon: <FileTextOutlined />,
  },
];

const solutionSteps = [
  { title: "自动发现", desc: "智能识别目标仓库和文档目录" },
  { title: "深度扫描", desc: "代码、注释、文档全覆盖检测" },
  { title: "精准评估", desc: "上下文分析过滤误报" },
  { title: "一键修复", desc: "批量生成修复建议" },
  { title: "自动提交", desc: "直接发起 Pull Request" },
];

const advantages = [
  {
    title: "全链路自动化",
    desc: "从发现问题到提交 PR，全程无需人工干预，真正解放生产力。",
    icon: <ThunderboltOutlined />,
  },
  {
    title: "上下文感知",
    desc: "不只是拼写检查，更能理解代码语义，大幅降低误报率。",
    icon: <SafetyOutlined />,
  },
  {
    title: "无缝集成",
    desc: "MCP 协议、REST API、GitHub Action，轻松接入现有工作流。",
    icon: <ApiOutlined />,
  },
  {
    title: "持续追踪",
    desc: "问题历史、修复质量、团队表现，数据可视化一目了然。",
    icon: <DashboardOutlined />,
  },
];

function toTitleFromKey(raw: string): string {
  return raw
    .split("_")
    .map((part) => (part ? part[0].toUpperCase() + part.slice(1) : part))
    .join(" ");
}

export default function HomePage() {
  const { config } = useConfig();
  const [caps, setCaps] = useState<CapabilityPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [capsError, setCapsError] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    fetchCapabilities()
      .then((payload) => {
        if (!active) return;
        setCaps(payload);
        setCapsError("");
      })
      .catch((error: unknown) => {
        if (!active) return;
        setCapsError(String(error));
      })
      .finally(() => {
        if (!active) return;
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  const metricCards = useMemo(() => {
    if (!caps) {
      return [
        { key: "workflow", label: "可用工作流", value: "--", hint: loading ? "加载中" : "等待数据" },
        { key: "nodes", label: "流程节点", value: "--", hint: "LangGraph Pipeline" },
        { key: "skills", label: "启用技能", value: "--", hint: "Skill Registry" },
        { key: "mcp", label: "MCP 服务", value: "--", hint: "集成能力" },
      ];
    }

    const enabledWorkflows = Object.values(caps.workflows || {}).filter(Boolean).length;
    return [
      {
        key: "workflow",
        label: "可用工作流",
        value: String(enabledWorkflows),
        hint: `${Object.keys(caps.workflows || {}).length} 个流程定义`,
      },
      {
        key: "nodes",
        label: "流程节点",
        value: String((caps.pipeline_nodes || []).length),
        hint: "LangGraph Pipeline",
      },
      {
        key: "skills",
        label: "启用技能",
        value: caps.skill_registry
          ? `${caps.skill_registry.enabled}/${caps.skill_registry.total}`
          : "--",
        hint: caps.skill_registry
          ? `内置 ${caps.skill_registry.builtin} · 自定义 ${caps.skill_registry.custom}`
          : "Skill Registry",
      },
      {
        key: "mcp",
        label: "MCP 服务",
        value: caps.mcp ? `${caps.mcp.enabled_servers}/${caps.mcp.total_servers}` : "--",
        hint: caps.mcp ? caps.mcp.adapter : "MCP Adapter",
      },
    ];
  }, [caps, loading]);

  const capabilityCards = useMemo(() => {
    if (!caps?.features) return [];
    return Object.entries(caps.features)
      .filter(([, enabled]) => Boolean(enabled))
      .map(([key]) => {
        const meta = capabilityFeatureMeta[key];
        return {
          key,
          title: meta?.title ?? toTitleFromKey(key),
          description: meta?.description ?? "能力已启用",
          icon: meta?.icon ?? <CheckCircleOutlined />,
        };
      });
  }, [caps]);

  const llmBadge = caps?.llm?.enabled
    ? `LLM: ${caps.llm.model || "已启用"}`
    : "LLM: 未启用";

  const mcpSseEnabled = Boolean(
    (caps as (CapabilityPayload & { mcp_sse?: { enabled?: boolean } }) | null)?.mcp_sse?.enabled
  );

  return (
    <div className="home-page home-page-marketing">
      <section className="marketing-hero">
        <div className="marketing-hero-glow" />
        <div className="marketing-hero-inner">
          <Tag color="green" className="marketing-badge">
            面向真实开发问题的智能质量助手
          </Tag>
          <Title level={1} className="marketing-title">
            让代码质量检查从此自动化
          </Title>
          <Paragraph className="marketing-subtitle">
            面向开发团队的智能代码质量治理平台。自动发现拼写错误、统一术语规范、生成修复建议，让每一次代码提交都更专业。
          </Paragraph>

          <Space wrap size={12} className="marketing-cta-row">
            <Link to="/workspace/tasks">
              <Button type="primary" size="large" icon={<PlayCircleOutlined />}>
                立即体验
              </Button>
            </Link>
            <Link to="/docs">
              <Button size="large" icon={<ArrowRightOutlined />}>
                查看文档
              </Button>
            </Link>
          </Space>

          <div className="marketing-highlight-line">
            <span>自动扫描</span>
            <span>智能修复</span>
            <span>一键提交</span>
            <span>持续追踪</span>
          </div>
        </div>
      </section>

      <section className="marketing-proof">
        <div className="marketing-section-head">
          <Title level={2}>解决得如何</Title>
          <Paragraph type="secondary">
            下面这些指标来自当前实例的实时能力数据，用来证明系统不仅能做，而且已经在做。
          </Paragraph>
        </div>

        {capsError && (
          <Alert
            type="warning"
            showIcon
            style={{ marginBottom: 14 }}
            message="能力数据加载失败"
            description={capsError}
          />
        )}

        <Row gutter={[14, 14]}>
          {metricCards.map((metric) => (
            <Col key={metric.key} xs={12} md={6}>
              <Card className="marketing-metric-card">
                <Text type="secondary">{metric.label}</Text>
                <div className="marketing-metric-value">{metric.value}</div>
                <Text type="secondary" className="marketing-metric-hint">
                  {metric.hint}
                </Text>
              </Card>
            </Col>
          ))}
        </Row>
      </section>

      <section className="marketing-section marketing-section-alt">
        <div className="marketing-section-head">
          <Title level={2}>解决什么问题</Title>
          <Paragraph type="secondary">
            这些困扰开发团队的日常痛点，Typo Master 帮你一次性解决
          </Paragraph>
        </div>
        <Row gutter={[14, 14]}>
          {painPoints.map((item) => (
            <Col key={item.title} xs={24} md={8}>
              <Card className="marketing-value-card">
                <div className="marketing-value-icon">{item.icon}</div>
                <Title level={4}>{item.title}</Title>
                <Paragraph type="secondary">{item.desc}</Paragraph>
              </Card>
            </Col>
          ))}
        </Row>
      </section>

      <section className="marketing-section">
        <div className="marketing-section-head">
          <Title level={2}>完整工作流</Title>
          <Paragraph type="secondary">
            从发现到修复的 5 步闭环，让质量治理变成稳定可重复的流程
          </Paragraph>
        </div>

        <Row gutter={[14, 14]}>
          {capabilityCards.map((item) => (
            <Col key={item.key} xs={24} sm={12} lg={8}>
              <Card className="marketing-capability-card" hoverable>
                <div className="marketing-capability-icon">{item.icon}</div>
                <Title level={4}>{item.title}</Title>
                <Paragraph type="secondary">{item.description}</Paragraph>
              </Card>
            </Col>
          ))}
        </Row>

        {caps?.pipeline_nodes && caps.pipeline_nodes.length > 0 && (
          <div className="marketing-node-strip">
            {caps.pipeline_nodes.map((node) => (
              <Tag key={node} color="green">
                {node}
              </Tag>
            ))}
          </div>
        )}

        {caps?.limitations && caps.limitations.length > 0 && (
          <Alert
            style={{ marginTop: 12 }}
            type="info"
            showIcon
            message="运行注意事项"
            description={
              <ul className="marketing-limit-list">
                {caps.limitations.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            }
          />
        )}
      </section>

      <section className="marketing-section marketing-section-alt">
        <div className="marketing-section-head">
          <Title level={2}>核心优势</Title>
          <Paragraph type="secondary">
            不止于拼写检查，更关注代码质量的全面提升
          </Paragraph>
        </div>
        <Row gutter={[14, 14]}>
          {advantages.map((item) => (
            <Col key={item.title} xs={24} md={12}>
              <Card className="marketing-value-card">
                <div className="marketing-value-icon">{item.icon}</div>
                <Title level={4}>{item.title}</Title>
                <Paragraph type="secondary">{item.desc}</Paragraph>
              </Card>
            </Col>
          ))}
        </Row>
      </section>

      <section className="marketing-section">
        <div className="marketing-section-head">
          <Title level={2}>适用场景</Title>
          <Paragraph type="secondary">
            无论是开源项目还是企业代码库，都能获得专业级的质量保障
          </Paragraph>
        </div>
        <Row gutter={[14, 14]}>
          {scenarios.map((item) => (
            <Col key={item.title} xs={24} md={8}>
              <Card className="marketing-usecase-card">
                <Space size={8} className="marketing-usecase-title">
                  {item.icon}
                  <Text strong>{item.title}</Text>
                </Space>
                <Paragraph type="secondary" style={{ marginBottom: 0 }}>
                  {item.desc}
                </Paragraph>
              </Card>
            </Col>
          ))}
        </Row>
      </section>

      <section className="marketing-section marketing-section-alt">
        <div className="marketing-section-head">
          <Title level={2}>快速启动</Title>
          <Paragraph type="secondary">
            三步完成配置，立即开始自动化质量治理
          </Paragraph>
        </div>
        <Card className="marketing-steps-card">
          <Steps
            direction="vertical"
            current={-1}
            items={solutionSteps.map((step) => ({
              title: step.title,
              description: step.desc,
              icon: <CheckCircleOutlined />,
            }))}
          />
        </Card>
      </section>

      <section className="marketing-final-cta">
        <Card className="marketing-final-card">
          <Title level={3}>准备好把质量治理流程自动化了吗？</Title>
          <Paragraph>
            完成配置，运行一个公开仓库，直观感受自动化质量治理的价值
          </Paragraph>
          <Space wrap size={12}>
            <Link to="/settings">
              <Button type="primary" icon={<SettingOutlined />}>
                完成配置
              </Button>
            </Link>
            <Link to="/workspace/tasks">
              <Button icon={<RocketOutlined />}>运行任务</Button>
            </Link>
          </Space>
        </Card>
      </section>
    </div>
  );
}
