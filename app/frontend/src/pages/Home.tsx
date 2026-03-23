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
  CodeOutlined,
  DashboardOutlined,
  DatabaseOutlined,
  FileSearchOutlined,
  FileTextOutlined,
  GithubOutlined,
  LinkOutlined,
  PlayCircleOutlined,
  PullRequestOutlined,
  RocketOutlined,
  SafetyOutlined,
  SearchOutlined,
  SettingOutlined,
  TeamOutlined,
  ThunderboltOutlined,
  ToolOutlined,
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

const valueProps = [
  {
    title: "问题 1：拼写与术语问题容易漏检",
    desc: "代码、注释、文档分散在多个文件里，人工检查很难稳定覆盖。",
    icon: <FileSearchOutlined />,
  },
  {
    title: "问题 2：手工排查和修复太耗时",
    desc: "从发现问题到逐个修复、再整理说明，过程重复且容易中断。",
    icon: <BugOutlined />,
  },
  {
    title: "问题 3：结果难沉淀、难复用",
    desc: "没有统一流程时，问题历史和修复质量难以持续追踪与复用。",
    icon: <SafetyOutlined />,
  },
];

const useCases = [
  {
    title: "开源维护者",
    desc: "在每次发布前快速扫描仓库，减少低级错误进入主分支。",
    icon: <GithubOutlined />,
  },
  {
    title: "独立开发者",
    desc: "把重复的质量检查自动化，把时间留给功能开发本身。",
    icon: <CodeOutlined />,
  },
  {
    title: "技术内容创作者",
    desc: "写文档、教程、示例代码时保持术语一致和表达专业。",
    icon: <TeamOutlined />,
  },
];

const activationSteps = [
  {
    title: "完成配置",
    description: "在设置页配置 LLM、GitHub Token 与权限策略",
  },
  {
    title: "跑通首个任务",
    description: "在任务执行页选择仓库并启动单仓库扫描流程",
  },
  {
    title: "形成你的日常流程",
    description: "根据你的节奏配置 Skill、触发器与对接方式",
  },
];

const integrationCards = [
  {
    title: "MCP SSE",
    detail: "提供 /mcp/sse 与 /mcp/messages，可被外部 MCP 客户端直接调用。",
    icon: <ApiOutlined />,
  },
  {
    title: "REST API",
    detail: "覆盖 Skills、MCP、Workflow、Permissions 等核心能力接口。",
    icon: <LinkOutlined />,
  },
  {
    title: "权限治理",
    detail: "支持 Git/GitHub/Shell/外部访问等细粒度权限开关。",
    icon: <SettingOutlined />,
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
            把仓库质量治理从“人工排查”升级成“自动化流水线”
          </Title>
          <Paragraph className="marketing-subtitle">
            Type Master 把仓库发现、拼写扫描、质量评估、自动修复与 PR 决策串成一条可复用流程，
            帮你持续减少低质量拼写问题，并把修复结果沉淀为可追踪资产。
          </Paragraph>

          <Space wrap size={12} className="marketing-cta-row">
            <Link to="/workspace/tasks">
              <Button type="primary" size="large" icon={<PlayCircleOutlined />}>
                立即体验
              </Button>
            </Link>
            <Link to="/docs">
              <Button size="large" icon={<ArrowRightOutlined />}>
                查看对接方式
              </Button>
            </Link>
          </Space>

          <Space wrap size={[8, 10]} className="marketing-status-tags">
            <Tag color={caps?.llm?.enabled ? "success" : "default"}>{llmBadge}</Tag>
            <Tag color={config.githubToken ? "success" : "default"}>
              GitHub Token: {config.githubToken ? "已配置" : "未配置"}
            </Tag>
            {caps?.framework && <Tag color="processing">{caps.framework}</Tag>}
            {mcpSseEnabled && <Tag color="blue">MCP SSE 已启用</Tag>}
          </Space>

          <div className="marketing-highlight-line">
            <span>解决真实问题</span>
            <span>自动化执行</span>
            <span>结果可追踪</span>
            <span>能力可扩展</span>
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
          <Title level={2}>我们解决哪些问题</Title>
        </div>
        <Row gutter={[14, 14]}>
          {valueProps.map((item) => (
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
          <Title level={2}>我们怎么解决</Title>
          <Paragraph type="secondary">
            通过“发现 → 分析 → 修复 → 决策 → 报告”的链路，把质量治理变成稳定可重复的流程。
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
              <Tag key={node} color="geekblue">
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
          <Title level={2}>适用场景</Title>
        </div>
        <Row gutter={[14, 14]}>
          {useCases.map((item) => (
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

      <section className="marketing-section">
        <div className="marketing-section-head">
          <Title level={2}>3 步启动流程</Title>
        </div>
        <Card className="marketing-steps-card">
          <Steps
            direction="vertical"
            current={-1}
            items={activationSteps.map((step) => ({
              title: step.title,
              description: step.description,
              icon: <CheckCircleOutlined />,
            }))}
          />
        </Card>
      </section>

      <section className="marketing-section marketing-section-alt">
        <div className="marketing-section-head">
          <Title level={2}>集成与治理能力</Title>
        </div>
        <Row gutter={[14, 14]}>
          {integrationCards.map((item) => (
            <Col key={item.title} xs={24} md={8}>
              <Card className="marketing-integration-card">
                <Space size={8}>
                  {item.icon}
                  <Text strong>{item.title}</Text>
                </Space>
                <Paragraph type="secondary" style={{ marginTop: 10, marginBottom: 0 }}>
                  {item.detail}
                </Paragraph>
              </Card>
            </Col>
          ))}
        </Row>
      </section>

      <section className="marketing-final-cta">
        <Card className="marketing-final-card">
          <Title level={3}>准备好把质量治理流程自动化了吗？</Title>
          <Paragraph>
            先完成设置，再跑一个公开仓库，你就能直观看到：问题是怎么被发现、怎么被修复、结果如何呈现的。
          </Paragraph>
          <Space wrap size={12}>
            <Link to="/settings">
              <Button type="primary" icon={<SettingOutlined />}>
                先完成配置
              </Button>
            </Link>
            <Link to="/workspace/tasks">
              <Button icon={<RocketOutlined />}>运行首个任务</Button>
            </Link>
            <Link to="/workspace/skills">
              <Button icon={<ToolOutlined />}>查看技能库</Button>
            </Link>
          </Space>
        </Card>
      </section>
    </div>
  );
}
