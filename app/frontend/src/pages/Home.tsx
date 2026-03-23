import { useEffect, useState } from "react";
import {
  Card,
  Row,
  Col,
  Typography,
  Space,
  Tag,
  Button,
  Statistic,
  Steps,
  Alert,
  Badge,
  Divider,
  List,
  Avatar,
  Carousel,
} from "antd";
import {
  ThunderboltOutlined,
  RobotOutlined,
  GithubOutlined,
  CheckCircleOutlined,
  SearchOutlined,
  FileSearchOutlined,
  BugOutlined,
  PullRequestOutlined,
  FileTextOutlined,
  SafetyOutlined,
  BranchesOutlined,
  StarOutlined,
  ArrowRightOutlined,
  PlayCircleOutlined,
  GlobalOutlined,
  CodeOutlined,
  TeamOutlined,
  TrophyOutlined,
  RocketOutlined,
  ToolOutlined,
  DashboardOutlined,
  ApiOutlined,
} from "@ant-design/icons";
import { Link } from "react-router-dom";
import { useConfig } from "../config";
import { fetchCapabilities } from "../api";
import type { CapabilityPayload } from "../types";

const { Title, Text, Paragraph } = Typography;
const { Step } = Steps;

// 功能特性数据
const features = [
  {
    icon: <SearchOutlined />,
    title: "智能发现",
    desc: "自动搜索 GitHub 热门仓库，支持按星标数、更新时间筛选",
    color: "#22c55e",
  },
  {
    icon: <FileSearchOutlined />,
    title: "深度扫描",
    desc: "多语言代码拼写检查，支持 MD/TXT/PY/JS/TS/SOL 等格式",
    color: "#3b82f6",
  },
  {
    icon: <SafetyOutlined />,
    title: "质量评估",
    desc: "AI 智能评估拼写错误严重程度，过滤 Web3 专业术语误报",
    color: "#8b5cf6",
  },
  {
    icon: <BugOutlined />,
    title: "自动修复",
    desc: "一键生成拼写修复补丁，智能保留代码语义",
    color: "#f59e0b",
  },
  {
    icon: <PullRequestOutlined />,
    title: "PR 创建",
    desc: "自动创建 Pull Request，生成专业的 PR 描述",
    color: "#ec4899",
  },
  {
    icon: <FileTextOutlined />,
    title: "报告生成",
    desc: "支持 CSV/JSON/Markdown/HTML 多种格式报告导出",
    color: "#14b8a6",
  },
];

// 支持的编程语言
const languages = [
  { name: "Markdown", ext: ".md", color: "#000" },
  { name: "Python", ext: ".py", color: "#3776ab" },
  { name: "JavaScript", ext: ".js", color: "#f7df1e" },
  { name: "TypeScript", ext: ".ts", color: "#3178c6" },
  { name: "Solidity", ext: ".sol", color: "#363636" },
  { name: "Rust", ext: ".rs", color: "#dea584" },
  { name: "Go", ext: ".go", color: "#00add8" },
  { name: "Java", ext: ".java", color: "#007396" },
];

// 工作流步骤
const workflowSteps = [
  { title: "发现项目", desc: "搜索 GitHub 仓库" },
  { title: "扫描代码", desc: "检测拼写错误" },
  { title: "质量评估", desc: "AI 智能分析" },
  { title: "生成修复", desc: "自动修复建议" },
  { title: "创建 PR", desc: "提交修复补丁" },
];

// 统计数据
const stats = [
  { label: "支持语言", value: "15+", suffix: "种" },
  { label: "检测准确率", value: "95", suffix: "%" },
  { label: "平均处理", value: "2", suffix: "秒/文件" },
  { label: "开源社区", value: "1000+", suffix: "Stars" },
];

export default function HomePage() {
  const { config } = useConfig();
  const [caps, setCaps] = useState<CapabilityPayload | null>(null);

  useEffect(() => {
    fetchCapabilities().then(setCaps).catch(console.error);
  }, []);

  return (
    <div className="home-page">
      {/* Hero 区域 */}
      <section className="hero-section">
        <div className="hero-content">
          <Badge.Ribbon text="v0.2.0" color="#22c55e">
            <Title level={1} className="hero-title">
              <RobotOutlined /> 拼写猎人
              <ThunderboltOutlined style={{ color: "#22c55e" }} />
            </Title>
          </Badge.Ribbon>
          <Paragraph className="hero-subtitle">
            智能代码拼写检查与自动修复系统
            <br />
            <Text type="secondary">让代码文档更专业，让开源贡献更轻松</Text>
          </Paragraph>
          <Space size="large" className="hero-actions">
            <Link to="/workspace">
              <Button type="primary" size="large" icon={<PlayCircleOutlined />}>
                开始使用
              </Button>
            </Link>
            <Link to="/settings">
              <Button size="large" icon={<ToolOutlined />}>
                配置系统
              </Button>
            </Link>
          </Space>

          {/* 状态提示 */}
          <div className="hero-status">
            <Space size="large">
              <Tag
                icon={config.llm.enabled ? <CheckCircleOutlined /> : <ApiOutlined />}
                color={config.llm.enabled ? "success" : "default"}
                style={{ fontSize: 14, padding: "4px 12px" }}
              >
                AI 功能: {config.llm.enabled ? "已启用" : "未启用"}
              </Tag>
              <Tag
                icon={config.githubToken ? <CheckCircleOutlined /> : <GithubOutlined />}
                color={config.githubToken ? "success" : "default"}
                style={{ fontSize: 14, padding: "4px 12px" }}
              >
                GitHub: {config.githubToken ? "已配置" : "未配置"}
              </Tag>
              {caps && (
                <Tag color="processing" style={{ fontSize: 14, padding: "4px 12px" }}>
                  <DashboardOutlined /> {caps.framework}
                </Tag>
              )}
            </Space>
          </div>
        </div>
      </section>

      {/* 统计数据 */}
      <section className="stats-section">
        <Row gutter={[24, 24]} justify="center">
          {stats.map((stat, index) => (
            <Col key={index} xs={12} sm={6} md={3}>
              <Card className="stat-card" bordered={false}>
                <Statistic
                  value={stat.value}
                  suffix={stat.suffix}
                  valueStyle={{
                    fontSize: 36,
                    fontWeight: 700,
                    color: "#22c55e",
                    fontFamily: '"DIN Alternate", "PingFang SC", sans-serif'
                  }}
                />
                <Text type="secondary" style={{ fontSize: 14 }}>{stat.label}</Text>
              </Card>
            </Col>
          ))}
        </Row>
      </section>

      {/* 核心功能 */}
      <section className="features-section">
        <div className="section-header">
          <Title level={2}>
            <RocketOutlined /> 核心功能
          </Title>
          <Paragraph type="secondary">全流程自动化，让拼写检查不再繁琐</Paragraph>
        </div>

        <Row gutter={[24, 24]}>
          {features.map((feature, index) => (
            <Col key={index} xs={24} sm={12} md={8}>
              <Card className="feature-card" hoverable>
                <div className="feature-icon" style={{ color: feature.color }}>
                  {feature.icon}
                </div>
                <Title level={4} style={{ margin: "16px 0 8px" }}>
                  {feature.title}
                </Title>
                <Paragraph type="secondary">{feature.desc}</Paragraph>
              </Card>
            </Col>
          ))}
        </Row>
      </section>

      {/* 工作流程 */}
      <section className="workflow-section">
        <div className="section-header">
          <Title level={2}>
            <BranchesOutlined /> 工作流程
          </Title>
          <Paragraph type="secondary">五步完成从发现到修复的完整流程</Paragraph>
        </div>

        <Card className="workflow-card">
          <Steps direction="horizontal" current={-1} size="default">
            {workflowSteps.map((step, index) => (
              <Step
                key={index}
                title={step.title}
                description={step.desc}
                icon={
                  <Avatar
                    size="large"
                    style={{
                      background: index === 0 ? "#22c55e" : "#e5e7eb",
                      color: index === 0 ? "#fff" : "#9ca3af"
                    }}
                  >
                    {index + 1}
                  </Avatar>
                }
              />
            ))}
          </Steps>

          <Divider />

          <Row gutter={[48, 24]} align="middle">
            <Col xs={24} md={12}>
              <Title level={4}>自动化流水线</Title>
              <Paragraph>
                系统采用 LangGraph 构建工作流，每个步骤都可以独立运行，
                也可以串联成完整的自动化流程。支持断点续传和状态持久化。
              </Paragraph>
              <List
                size="small"
                split={false}
                dataSource={[
                  "支持批量处理多个仓库",
                  "可配置扫描范围和规则",
                  "智能错误分级和过滤",
                  "自动决策是否创建 PR",
                ]}
                renderItem={(item) => (
                  <List.Item>
                    <CheckCircleOutlined style={{ color: "#22c55e", marginRight: 8 }} />
                    {item}
                  </List.Item>
                )}
              />
            </Col>
            <Col xs={24} md={12}>
              <div className="workflow-diagram">
                <img
                  src="/workflow.svg"
                  alt="Workflow"
                  style={{ width: "100%", maxWidth: 400 }}
                />
              </div>
            </Col>
          </Row>
        </Card>
      </section>

      {/* 支持的语言 */}
      <section className="languages-section">
        <div className="section-header">
          <Title level={2}>
            <CodeOutlined /> 支持的语言
          </Title>
          <Paragraph type="secondary">覆盖主流编程语言和文档格式</Paragraph>
        </div>

        <Card className="languages-card">
          <Row gutter={[16, 16]}>
            {languages.map((lang, index) => (
              <Col key={index} xs={12} sm={6} md={3}>
                <div className="language-item">
                  <Avatar
                    size={48}
                    style={{
                      background: lang.color,
                      color: "#fff",
                      fontSize: 14,
                      fontWeight: 600
                    }}
                  >
                    {lang.ext.slice(1)}
                  </Avatar>
                  <Text strong style={{ marginTop: 8, display: "block" }}>
                    {lang.name}
                  </Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {lang.ext}
                  </Text>
                </div>
              </Col>
            ))}
          </Row>
          <Divider />
          <Text type="secondary" style={{ textAlign: "center", display: "block" }}>
            以及 Markdown、Text、RST、AsciiDoc 等文档格式
          </Text>
        </Card>
      </section>

      {/* 技术特点 */}
      <section className="tech-section">
        <div className="section-header">
          <Title level={2}>
            <ToolOutlined /> 技术特点
          </Title>
        </div>

        <Row gutter={[24, 24]}>
          <Col xs={24} md={8}>
            <Card className="tech-card">
              <Title level={4}>
                <ApiOutlined /> AI 驱动
              </Title>
              <Paragraph>
                支持 OpenAI、Claude 等大模型 API，智能识别专业术语，
                避免误报，提供上下文感知的修复建议。
              </Paragraph>
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card className="tech-card">
              <Title level={4}>
                <GlobalOutlined /> Web3 友好
              </Title>
              <Paragraph>
                内置 Web3 专业术语词典，智能识别 Solidity 关键词、
                区块链术语，减少误报率。
              </Paragraph>
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card className="tech-card">
              <Title level={4}>
                <TeamOutlined /> 开源协作
              </Title>
              <Paragraph>
                自动生成标准化的 PR，包含详细的修改说明和影响分析，
                方便项目维护者审阅。
              </Paragraph>
            </Card>
          </Col>
        </Row>
      </section>

      {/* 使用场景 */}
      <section className="scenarios-section">
        <div className="section-header">
          <Title level={2}>
            <DashboardOutlined /> 使用场景
          </Title>
        </div>

        <Row gutter={[24, 24]}>
          {[
            {
              title: "开源项目维护",
              desc: "定期检查文档和注释中的拼写错误，提升项目专业度",
              icon: <GithubOutlined />,
            },
            {
              title: "技术文档编写",
              desc: "在发布前扫描技术文档，确保专业术语拼写正确",
              icon: <FileTextOutlined />,
            },
            {
              title: "代码审查辅助",
              desc: "作为 CI/CD 流程的一部分，自动检测拼写问题",
              icon: <SafetyOutlined />,
            },
            {
              title: "多语言本地化",
              desc: "检查多语言资源文件，确保翻译质量和拼写正确",
              icon: <GlobalOutlined />,
            },
          ].map((scenario, index) => (
            <Col key={index} xs={24} sm={12}>
              <Card className="scenario-card" hoverable>
                <div className="scenario-icon" style={{ color: "#22c55e" }}>
                  {scenario.icon}
                </div>
                <Title level={4}>{scenario.title}</Title>
                <Paragraph type="secondary">{scenario.desc}</Paragraph>
              </Card>
            </Col>
          ))}
        </Row>
      </section>

      {/* CTA 区域 */}
      <section className="cta-section">
        <Card className="cta-card" bordered={false}>
          <Title level={2}>
            <TrophyOutlined /> 开始使用
          </Title>
          <Paragraph style={{ fontSize: 16, marginBottom: 24 }}>
            配置您的 GitHub Token 和大模型 API，开启智能拼写检查之旅
          </Paragraph>
          <Space size="large">
            <Link to="/settings">
              <Button type="primary" size="large" icon={<ToolOutlined />}>
                立即配置
              </Button>
            </Link>
            <Link to="/workspace">
              <Button size="large" icon={<ArrowRightOutlined />}>
                进入工作台
              </Button>
            </Link>
          </Space>
        </Card>
      </section>
    </div>
  );
}
