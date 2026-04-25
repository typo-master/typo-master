import { useEffect, useMemo, useState, useCallback } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Col,
  Divider,
  Form,
  Input,
  InputNumber,
  Progress,
  Row,
  Space,
  Switch,
  Tag,
  Typography,
  message,
  Empty,
  Statistic,
  Timeline,
  Avatar,
  Menu,
  Layout,
} from "antd";
import {
  PlayCircleOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  LoadingOutlined,
  GithubOutlined,
  StarOutlined,
  CalendarOutlined,
  FileTextOutlined,
  PullRequestOutlined,
  AppstoreOutlined,
  UserOutlined,
  DashboardOutlined,
  CheckOutlined,
  RobotOutlined,
  ToolOutlined,
  ThunderboltOutlined,
  HistoryOutlined,
  ScheduleOutlined,
  ApiOutlined,
  MessageOutlined,
  FireOutlined,
  CodeOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
} from "@ant-design/icons";
import { useNavigate, useParams } from "react-router-dom";
import { useConfig } from "../config";
import { runWorkflow, getWorkflowTask } from "../api";
import AIChat from "../components/AIChat";
import SkillList from "../components/SkillList";
import TriggerManager from "../components/TriggerManager";
import MCPManager from "../components/MCPManager";
import { skillStore, chatStore, triggerStore, logStore, type AgentSkill } from "../db";
import type { WorkflowRequest, WorkflowTaskResponse } from "../types";

const { Title, Text, Paragraph } = Typography;
const { Sider, Content } = Layout;
const WORKSPACE_TABS = ["chat", "skills", "mcp", "triggers", "tasks"] as const;
type WorkspaceTabKey = (typeof WORKSPACE_TABS)[number];
const WORKSPACE_TAB_SET = new Set<WorkspaceTabKey>(WORKSPACE_TABS);
const DEFAULT_WORKSPACE_TAB: WorkspaceTabKey = "chat";

// 状态标签配置
const statusConfig: Record<string, { color: string; icon: React.ReactNode; text: string }> = {
  queued: { color: "default", icon: <ClockCircleOutlined />, text: "等待中" },
  running: { color: "processing", icon: <LoadingOutlined spin />, text: "运行中" },
  succeeded: { color: "success", icon: <CheckCircleOutlined />, text: "成功" },
  failed: { color: "error", icon: <CloseCircleOutlined />, text: "失败" }
};

export default function WorkspacePage() {
  const { config } = useConfig();
  const navigate = useNavigate();
  const { tab } = useParams<{ tab?: string }>();
  const [workflowForm] = Form.useForm<WorkflowRequest>();
  const [taskId, setTaskId] = useState<string>("");
  const [task, setTask] = useState<WorkflowTaskResponse | null>(null);
  const [workflowLoading, setWorkflowLoading] = useState(false);
  const [taskHistory, setTaskHistory] = useState<WorkflowTaskResponse[]>([]);
  const [stats, setStats] = useState({
    messages: 0,
    skills: 0,
    triggers: 0,
    tasks: 0,
  });
  const [siderCollapsed, setSiderCollapsed] = useState(false);

  const canPoll = useMemo(() => {
    return Boolean(taskId && task && (task.status === "queued" || task.status === "running"));
  }, [taskId, task]);

  const activeTab = useMemo<WorkspaceTabKey>(() => {
    if (tab && WORKSPACE_TAB_SET.has(tab as WorkspaceTabKey)) {
      return tab as WorkspaceTabKey;
    }
    return DEFAULT_WORKSPACE_TAB;
  }, [tab]);

  // 加载统计数据
  const loadStats = useCallback(async () => {
    try {
      const [messages, skills, triggers] = await Promise.all([
        chatStore.getAll(),
        skillStore.getAll(),
        triggerStore.getAll(),
      ]);
      setStats({
        messages: messages.length,
        skills: skills.filter((s) => s.enabled).length,
        triggers: triggers.filter((t) => t.enabled).length,
        tasks: taskHistory.length,
      });
    } catch (error) {
      console.error("Failed to load stats:", error);
    }
  }, [taskHistory.length]);

  useEffect(() => {
    loadStats();
    const interval = setInterval(loadStats, 10000);
    return () => clearInterval(interval);
  }, [loadStats]);

  useEffect(() => {
    workflowForm.setFieldsValue({
      workflow: "single_project",
      create_pr: false,
      owner: "octocat",
      repo: "Hello-World",
      days: 30,
      min_stars: 100,
      limit: 5
    });
  }, [workflowForm]);

  useEffect(() => {
    if (!canPoll) return;
    const timer = setInterval(() => {
      void refreshTask();
    }, 2000);
    return () => clearInterval(timer);
  }, [canPoll]);

  useEffect(() => {
    if (!tab || !WORKSPACE_TAB_SET.has(tab as WorkspaceTabKey)) {
      navigate(`/workspace/${DEFAULT_WORKSPACE_TAB}`, { replace: true });
    }
  }, [tab, navigate]);

  const handleTabChange = useCallback(
    (key: string) => {
      if (key === activeTab) return;
      if (WORKSPACE_TAB_SET.has(key as WorkspaceTabKey)) {
        navigate(`/workspace/${key}`);
      }
    },
    [activeTab, navigate]
  );

  async function handleRunWorkflow(values: WorkflowRequest) {
    if (!config.githubToken) {
      message.warning("请先配置 GitHub Token，前往设置页面");
      return;
    }

    setWorkflowLoading(true);
    try {
      const created = await runWorkflow(values);
      setTaskId(created.task_id);
      setTask(created);
      setTaskHistory(prev => [created, ...prev]);
      message.success({
        content: "任务已创建",
        icon: <CheckCircleOutlined />
      });
    } catch (error) {
      message.error("创建任务失败: " + String(error));
    } finally {
      setWorkflowLoading(false);
    }
  }

  async function refreshTask() {
    if (!taskId) return;
    try {
      const next = await getWorkflowTask(taskId);
      setTask(next);
      setTaskHistory(prev =>
        prev.map(t => t.task_id === taskId ? next : t)
      );
    } catch (error) {
      message.error("刷新状态失败: " + String(error));
    }
  }

  // 处理 Skill 执行
  const handleExecuteSkill = async (skillName: string, params: any) => {
    try {
      const { executeSkill: executeSkillApi } = await import("../api");
      const result = await executeSkillApi(skillName, params ?? {});
      if (result.success) {
        message.success(`Skill "${skillName}" 执行成功`);
      } else {
        message.error(result.error || `Skill "${skillName}" 执行失败`);
      }
    } catch (error) {
      message.error(`Skill 执行失败: ${String(error)}`);
    }
  };

  // 处理触发器执行
  const handleTriggerExecute = async (triggerId: number, prompt: string) => {
    try {
      const { createConversation, sendChatMessage } = await import("../api");
      const conversation = await createConversation();
      await sendChatMessage(conversation.conversation_id, prompt);
      message.success(`触发器 #${triggerId} 执行完成`);
    } catch (error) {
      message.error(`触发器执行失败: ${String(error)}`);
    }
  };

  const statusInfo = task ? statusConfig[task.status] : null;

  const workspaceMenuItems = useMemo(
    () => [
      {
        key: "chat",
        icon: <MessageOutlined />,
        label: "AI 对话",
      },
      {
        key: "skills",
        icon: <ToolOutlined />,
        label: "Skill 技能",
      },
      {
        key: "mcp",
        icon: <ApiOutlined />,
        label: "MCP 服务",
      },
      {
        key: "triggers",
        icon: <ScheduleOutlined />,
        label: "定时触发器",
      },
      {
        key: "tasks",
        icon: <FireOutlined />,
        label: (
          <Space size={6}>
            任务执行
            {task && (task.status === "queued" || task.status === "running") && (
              <Badge status="processing" />
            )}
          </Space>
        ),
        title: "任务执行",
      },
    ],
    [task]
  );

  return (
    <div className="workspace-page">
      {/* 顶部统计栏 - 仅在非聊天 tab 显示 */}
      {activeTab !== "chat" && (
        <Card className="flat-card" style={{ marginBottom: 16 }}>
          <Row gutter={[24, 16]} align="middle">
            <Col xs={24} md={8}>
              <Space>
                <Avatar size="large" style={{ background: "#22c55e" }}>
                  <RobotOutlined />
                </Avatar>
                <div>
                  <Title level={4} style={{ margin: 0 }}>
                    <DashboardOutlined /> 工作台
                  </Title>
                  <Text type="secondary">智能任务管理与 AI 对话中心</Text>
                </div>
              </Space>
            </Col>
            <Col xs={24} md={16}>
              <Row gutter={24}>
                <Col span={6}>
                  <Statistic
                    title={<Space><MessageOutlined /> 对话消息</Space>}
                    value={stats.messages}
                    valueStyle={{ color: "#22c55e", fontSize: 20 }}
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title={<Space><ToolOutlined /> 可用技能</Space>}
                    value={stats.skills}
                    valueStyle={{ color: "#3b82f6", fontSize: 20 }}
                    suffix={`/${stats.skills}`}
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title={<Space><ScheduleOutlined /> 定时触发器</Space>}
                    value={stats.triggers}
                    valueStyle={{ color: "#f59e0b", fontSize: 20 }}
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title={<Space><HistoryOutlined /> 执行任务</Space>}
                    value={stats.tasks}
                    valueStyle={{ color: "#8b5cf6", fontSize: 20 }}
                  />
                </Col>
              </Row>
            </Col>
          </Row>
        </Card>
      )}

      {/* 状态提示 */}
      {activeTab !== "chat" && !config.llm.enabled && (
        <Alert
          type="warning"
          showIcon
          message="AI 功能未启用"
          description="请在设置页面配置大模型 API，以启用 AI 对话功能"
          style={{ marginBottom: 16 }}
          action={
            <Button size="small" type="primary">
              去配置
            </Button>
          }
        />
      )}

      {/* 主内容区 */}
      <Layout className="workspace-shell">
        <Sider
          width={200}
          collapsedWidth={56}
          collapsible
          collapsed={siderCollapsed}
          onCollapse={setSiderCollapsed}
          trigger={null}
          className="workspace-side-menu"
          theme="light"
        >
          <div
            className="workspace-sider-toggle"
            data-collapsed={siderCollapsed}
          >
            <Button
              type="text"
              icon={siderCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={() => setSiderCollapsed(!siderCollapsed)}
              aria-label={siderCollapsed ? "展开侧边栏" : "收起侧边栏"}
              className="workspace-sider-toggle-btn"
              data-collapsed={siderCollapsed}
            />
          </div>
          <Menu
            mode={siderCollapsed ? "vertical" : "inline"}
            selectedKeys={[activeTab]}
            items={workspaceMenuItems}
            onClick={({ key }) => handleTabChange(key)}
            className="workspace-nav-menu"
          />
        </Sider>
        <Content className="workspace-main-content">
          {/* AI 对话 */}
          {activeTab === "chat" && (
            <div className="workspace-chat-container">
              <AIChat
                agentId="default"
                onExecuteSkill={handleExecuteSkill}
              />
            </div>
          )}

          {/* Skill 系统 */}
          {activeTab === "skills" && (
            <Row gutter={[16, 16]}>
              <Col xs={24} lg={16}>
                <Card
                  title={
                    <Space>
                      <ThunderboltOutlined />
                      可用技能
                      <Badge count={stats.skills} color="#22c55e" />
                    </Space>
                  }
                  className="flat-card"
                >
                  <SkillList showDisabled={false} />
                </Card>
              </Col>
              <Col xs={24} lg={8}>
                <Card
                  title={
                    <Space>
                      <CodeOutlined />
                      使用说明
                    </Space>
                  }
                  className="flat-card"
                >
                  <Space direction="vertical" size={16} style={{ width: "100%" }}>
                    <div>
                      <Text strong>1. 通过对话调用</Text>
                      <Paragraph type="secondary">
                        在 AI 对话中输入 <Text code>/skill 技能名</Text> 来调用技能
                      </Paragraph>
                    </div>
                    <div>
                      <Text strong>2. 参数传递</Text>
                      <Paragraph type="secondary">
                        支持 JSON 格式参数，例如:
                        <br />
                        <Text code>/skill scan_typo {"{"}path: "./src"{"}"}</Text>
                      </Paragraph>
                    </div>
                    <div>
                      <Text strong>3. 定时触发</Text>
                      <Paragraph type="secondary">
                        在触发器管理中设置定时任务，自动触发技能执行
                      </Paragraph>
                    </div>
                    <Divider />
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      当前支持 {stats.skills} 个技能，可在下方开关启用或禁用
                    </Text>
                  </Space>
                </Card>
              </Col>
            </Row>
          )}

          {activeTab === "mcp" && <MCPManager />}

          {/* 触发器 */}
          {activeTab === "triggers" && (
            <TriggerManager onTriggerExecute={handleTriggerExecute} />
          )}

          {/* 任务执行 */}
          {activeTab === "tasks" && (
            <Row gutter={[16, 16]}>
              {/* 左侧：任务配置 */}
              <Col xs={24} lg={12}>
                <Card
                  className="flat-card"
                  title={
                    <Space>
                      <PlayCircleOutlined />
                      <span>运行扫描任务</span>
                    </Space>
                  }
                >
                  {!config.githubToken && (
                    <Alert
                      type="warning"
                      showIcon
                      message="GitHub Token 未配置"
                      description="请在设置页面配置 GitHub Token 后才能运行扫描任务"
                      style={{ marginBottom: 16 }}
                    />
                  )}

                  <Form form={workflowForm} layout="vertical" onFinish={handleRunWorkflow}>
                    <Row gutter={16}>
                      <Col xs={24} md={12}>
                        <Form.Item
                          label={
                            <Space>
                              <GithubOutlined />
                              <span>仓库所有者 (Owner)</span>
                            </Space>
                          }
                          name="owner"
                          rules={[{ required: true, message: "请输入仓库所有者" }]}
                        >
                          <Input prefix={<UserOutlined />} placeholder="例如: octocat" />
                        </Form.Item>
                      </Col>
                      <Col xs={24} md={12}>
                        <Form.Item
                          label={
                            <Space>
                              <AppstoreOutlined />
                              <span>仓库名称 (Repo)</span>
                            </Space>
                          }
                          name="repo"
                          rules={[{ required: true, message: "请输入仓库名称" }]}
                        >
                          <Input prefix={<GithubOutlined />} placeholder="例如: Hello-World" />
                        </Form.Item>
                      </Col>
                    </Row>

                    <Row gutter={16}>
                      <Col xs={24} md={8}>
                        <Form.Item
                          label={
                            <Space>
                              <CalendarOutlined />
                              <span>时间范围 (天)</span>
                            </Space>
                          }
                          name="days"
                        >
                          <InputNumber min={1} style={{ width: "100%" }} />
                        </Form.Item>
                      </Col>
                      <Col xs={24} md={8}>
                        <Form.Item
                          label={
                            <Space>
                              <StarOutlined />
                              <span>最小星标数</span>
                            </Space>
                          }
                          name="min_stars"
                        >
                          <InputNumber min={0} style={{ width: "100%" }} />
                        </Form.Item>
                      </Col>
                      <Col xs={24} md={8}>
                        <Form.Item
                          label={
                            <Space>
                              <FileTextOutlined />
                              <span>扫描数量限制</span>
                            </Space>
                          }
                          name="limit"
                        >
                          <InputNumber min={1} style={{ width: "100%" }} />
                        </Form.Item>
                      </Col>
                    </Row>

                    <Form.Item
                      label={
                        <Space>
                          <PullRequestOutlined />
                          <span>自动创建 PR</span>
                        </Space>
                      }
                      name="create_pr"
                      valuePropName="checked"
                    >
                      <Switch checkedChildren="开启" unCheckedChildren="关闭" />
                    </Form.Item>

                    <Space>
                      <Button
                        type="primary"
                        htmlType="submit"
                        loading={workflowLoading}
                        icon={<PlayCircleOutlined />}
                        size="large"
                        disabled={!config.githubToken}
                      >
                        {workflowLoading ? "启动中..." : "开始扫描"}
                      </Button>
                      <Button
                        onClick={refreshTask}
                        disabled={!taskId}
                        icon={<ReloadOutlined />}
                        style={{
                          borderRadius: 6,
                          border: "1px solid #d1d5db",
                          background: "#f9fafb",
                          color: "#374151",
                        }}
                      >
                        刷新状态
                      </Button>
                    </Space>
                  </Form>

                  <Divider />

                  {/* 任务状态显示 */}
                  {task ? (
                    <Space direction="vertical" size={12} style={{ width: "100%" }}>
                      <Row gutter={16}>
                        <Col span={12}>
                          <Card size="small">
                            <Statistic
                              title="任务ID"
                              value={task.task_id.slice(0, 12) + "..."}
                              valueStyle={{ fontSize: 12 }}
                            />
                          </Card>
                        </Col>
                        <Col span={12}>
                          <Card size="small">
                            <div className="status-display">
                              <Text type="secondary">状态</Text>
                              <br />
                              {statusInfo && (
                                <Tag
                                  icon={statusInfo.icon}
                                  color={statusInfo.color as any}
                                  style={{ fontSize: 14, padding: "4px 12px" }}
                                >
                                  {statusInfo.text}
                                </Tag>
                              )}
                            </div>
                          </Card>
                        </Col>
                      </Row>

                      {(task.status === "queued" || task.status === "running") && (
                        <Progress
                          percent={task.status === "running" ? 50 : 10}
                          status="active"
                          strokeColor="#22c55e"
                        />
                      )}

                      {task.error && (
                        <Alert
                          type="error"
                          showIcon
                          icon={<CloseCircleOutlined />}
                          message="任务执行出错"
                          description={task.error}
                        />
                      )}

                      {task.result && (
                        <Card
                          size="small"
                          title={
                            <Space>
                              <FileTextOutlined />
                              <span>执行结果</span>
                            </Space>
                          }
                          className="result-card"
                        >
                          <pre className="result-box">{JSON.stringify(task.result, null, 2)}</pre>
                        </Card>
                      )}
                    </Space>
                  ) : (
                    <Empty
                      image={Empty.PRESENTED_IMAGE_SIMPLE}
                      description="暂无运行中的任务"
                    />
                  )}
                </Card>
              </Col>

              {/* 右侧：任务历史 */}
              <Col xs={24} lg={12}>
                <Card
                  className="flat-card"
                  title={
                    <Space>
                      <CheckOutlined />
                      <span>任务历史</span>
                    </Space>
                  }
                >
                  {taskHistory.length === 0 ? (
                    <Empty
                      image={Empty.PRESENTED_IMAGE_SIMPLE}
                      description="暂无任务历史"
                    />
                  ) : (
                    <Timeline mode="left">
                      {taskHistory.map((t) => {
                        const s = statusConfig[t.status];
                        return (
                          <Timeline.Item
                            key={t.task_id}
                            dot={s?.icon}
                            color={s?.color as any}
                            label={new Date(t.created_at).toLocaleString()}
                          >
                            <Space direction="vertical" size={4} style={{ width: "100%" }}>
                              <Text strong>任务: {t.task_id.slice(0, 8)}...</Text>
                              <Tag icon={s?.icon} color={s?.color as any}>
                                {s?.text}
                              </Tag>
                              {t.error && (
                                <Text type="danger" style={{ fontSize: 12 }}>
                                  错误: {t.error}
                                </Text>
                              )}
                            </Space>
                          </Timeline.Item>
                        );
                      })}
                    </Timeline>
                  )}
                </Card>
              </Col>
            </Row>
          )}
        </Content>
      </Layout>
    </div>
  );
}
