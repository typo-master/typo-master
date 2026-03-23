import { useState, useEffect } from "react";
import {
  Card,
  Form,
  Input,
  InputNumber,
  Switch,
  Button,
  Typography,
  Space,
  Divider,
  Alert,
  message,
  Tabs,
  Tag,
} from "antd";
import {
  SettingOutlined,
  ApiOutlined,
  GithubOutlined,
  SaveOutlined,
  EyeOutlined,
  EyeInvisibleOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
  RobotOutlined,
  KeyOutlined,
  LinkOutlined,
  ClockCircleOutlined,
  FileTextOutlined,
} from "@ant-design/icons";
import { useConfig, defaultConfig } from "../config";
import {
  fetchPermissions,
  updatePermissions
} from "../api";
import MCPManager from "../components/MCPManager";

const { Title, Text, Paragraph } = Typography;

export default function SettingsPage() {
  const { config, updateConfig, updateLLMConfig } = useConfig();
  const [llmForm] = Form.useForm();
  const [githubForm] = Form.useForm();
  const [showApiKey, setShowApiKey] = useState(false);
  const [showGithubToken, setShowGithubToken] = useState(false);
  const [activeTab, setActiveTab] = useState("llm");
  const [permissions, setPermissions] = useState<Record<string, boolean>>({});
  const [permissionGroups, setPermissionGroups] = useState<Record<string, string[]>>({});

  // 初始化表单
  useEffect(() => {
    llmForm.setFieldsValue({
      enabled: config.llm.enabled,
      baseUrl: config.llm.baseUrl,
      model: config.llm.model,
      apiKey: config.llm.apiKey,
      timeout: config.llm.timeout,
      maxOutputTokens: config.llm.maxOutputTokens,
    });
    githubForm.setFieldsValue({
      token: config.githubToken,
    });
  }, [config, llmForm, githubForm]);

  useEffect(() => {
    const loadPermissions = async () => {
      try {
        const payload = await fetchPermissions();
        if (payload.success) {
          setPermissions(payload.permissions ?? {});
          setPermissionGroups(payload.groups ?? {});
          updateConfig({ ...config, permissions: payload.permissions ?? {} });
        }
      } catch (err: any) {
        message.error(`权限配置加载失败: ${err?.message ?? err}`);
      }
    };
    loadPermissions();
  }, []);

  const handleSaveLLM = (values: any) => {
    updateLLMConfig({
      ...config.llm,
      ...values,
    });
    message.success({
      content: "LLM 配置已保存",
      icon: <CheckCircleOutlined />,
    });
  };

  const handleSaveGithub = (values: any) => {
    updateConfig({
      ...config,
      githubToken: values.token,
    });
    message.success({
      content: "GitHub Token 已保存",
      icon: <CheckCircleOutlined />,
    });
  };

  const handleSavePermissions = async (key: string, value: boolean) => {
    const next = { ...permissions, [key]: value };
    const previous = permissions;
    setPermissions(next);
    try {
      const payload = await updatePermissions(next);
      if (payload.success) {
        setPermissions(payload.permissions ?? next);
        updateConfig({ ...config, permissions: payload.permissions ?? next });
        message.success({ content: "权限配置已保存", icon: <CheckCircleOutlined /> });
      }
    } catch (err: any) {
      message.error(`权限配置保存失败: ${err?.message ?? err}`);
      setPermissions(previous);
    }
  };

  const permissionGroupMeta: Record<string, { title: string; description: string }> = {
    global: { title: "全局设置", description: "控制所有远程/高风险操作的总开关" },
    git: { title: "Git", description: "本地与远程 Git 操作权限" },
    github: { title: "GitHub/PR", description: "远程仓库与 PR/Issue 操作权限" },
    filesystem: { title: "文件系统", description: "本地文件读写与删除" },
    commands: { title: "命令执行", description: "Shell 命令与依赖安装" },
    external: { title: "外部访问", description: "网络访问与 LLM 请求" },
  };

  // 权限描述与风险提示
  const permissionDescriptions: Record<string, { label: string; description: string; risk?: string }> = {
    global_remote_enabled: {
      label: "远程/高风险操作总开关",
      description: "关闭时，所有远程/高风险操作将被全局禁用",
      risk: "关闭后所有远程操作（Git推送、PR创建、外部API调用等）将被拒绝"
    },
    git_clone: { label: "Git Clone", description: "克隆远程仓库", risk: "允许从远程仓库下载代码" },
    git_fetch: { label: "Git Fetch", description: "获取远程更新", risk: "允许与远程仓库通信" },
    git_pull: { label: "Git Pull", description: "拉取远程变更", risk: "允许从远程仓库获取并合并代码" },
    git_push: { label: "Git Push", description: "推送到远程", risk: "允许将本地变更推送到远程仓库，会修改远程代码" },
    git_checkout: { label: "Git Checkout", description: "切换分支" },
    git_create_branch: { label: "Git 创建分支", description: "创建新分支" },
    git_add: { label: "Git Add", description: "添加文件到暂存区" },
    git_commit: { label: "Git Commit", description: "提交变更" },
    github_read: { label: "GitHub 读取", description: "读取仓库、PR、Issue 信息", risk: "允许访问 GitHub API 获取仓库数据" },
    pr_create: { label: "创建 PR", description: "创建 Pull Request", risk: "允许在远程仓库创建 PR，会对外部仓库产生影响" },
    pr_update: { label: "更新 PR", description: "更新 PR 标题/描述" },
    pr_comment: { label: "PR 评论", description: "添加 PR 评论", risk: "允许在远程 PR 上发表评论" },
    pr_merge: { label: "合并 PR", description: "合并 Pull Request", risk: "允许合并远程 PR，会修改远程代码" },
    pr_close: { label: "关闭 PR", description: "关闭 Pull Request" },
    issue_create: { label: "创建 Issue", description: "创建 GitHub Issue", risk: "允许在远程仓库创建 Issue" },
    issue_comment: { label: "Issue 评论", description: "添加 Issue 评论", risk: "允许在远程 Issue 上发表评论" },
    issue_close: { label: "关闭 Issue", description: "关闭 GitHub Issue" },
    fs_read: { label: "文件读取", description: "读取本地文件内容" },
    fs_write: { label: "文件写入", description: "写入本地文件", risk: "允许修改本地文件内容" },
    fs_delete: { label: "文件删除", description: "删除本地文件", risk: "允许删除本地文件，操作不可逆" },
    shell_run: { label: "Shell 命令", description: "执行 Shell 命令", risk: "允许执行任意系统命令，存在安全风险" },
    run_tests: { label: "运行测试", description: "运行项目测试命令", risk: "允许执行测试脚本" },
    install_deps: { label: "安装依赖", description: "安装项目依赖", risk: "允许执行包管理器安装命令" },
    web_fetch: { label: "网络获取", description: "获取远程网页内容", risk: "允许访问外部网络资源" },
    api_call: { label: "API 调用", description: "调用外部 API", risk: "允许向外部服务发送请求" },
    llm_request: { label: "LLM 请求", description: "调用大语言模型", risk: "允许发送请求到 LLM 服务，可能产生费用" },
  };

  const handleReset = () => {
    updateConfig(defaultConfig);
    llmForm.setFieldsValue(defaultConfig.llm);
    githubForm.setFieldsValue({ token: "" });
    setPermissions({});
    setPermissionGroups({});
    message.success("已重置为默认配置");
  };

  const items = [
    {
      key: "llm",
      label: (
        <Space>
          <RobotOutlined />
          大模型配置
        </Space>
      ),
      children: (
        <Card className="flat-card">
          <Alert
            type="info"
            showIcon
            icon={<InfoCircleOutlined />}
            message="关于 LLM 配置"
            description="配置大模型 API 后，系统将使用 AI 进行智能拼写检查、修复建议和 PR 决策。支持 OpenAI 格式 API 的任何模型。"
            style={{ marginBottom: 24 }}
          />

          <Form
            form={llmForm}
            layout="vertical"
            onFinish={handleSaveLLM}
            initialValues={config.llm}
          >
            <Form.Item
              label={
                <Space>
                  <ApiOutlined />
                  <span>启用 AI 功能</span>
                </Space>
              }
              name="enabled"
              valuePropName="checked"
              extra="开启后系统将使用大模型进行智能分析"
            >
              <Switch
                checkedChildren="已启用"
                unCheckedChildren="已禁用"
              />
            </Form.Item>

            <Divider />

            <Form.Item
              label={
                <Space>
                  <LinkOutlined />
                  <span>API 地址</span>
                </Space>
              }
              name="baseUrl"
              rules={[{ required: config.llm.enabled, message: "请输入 API 地址" }]}
              extra="支持 OpenAI 格式的 API，如 https://api.openai.com/v1"
            >
              <Input
                placeholder="https://api.openai.com/v1"
                prefix={<LinkOutlined />}
              />
            </Form.Item>

            <Form.Item
              label={
                <Space>
                  <RobotOutlined />
                  <span>模型名称</span>
                </Space>
              }
              name="model"
              rules={[{ required: config.llm.enabled, message: "请输入模型名称" }]}
              extra="例如：gpt-3.5-turbo, gpt-4, claude-3-sonnet 等"
            >
              <Input
                placeholder="gpt-3.5-turbo"
                prefix={<RobotOutlined />}
              />
            </Form.Item>

            <Form.Item
              label={
                <Space>
                  <KeyOutlined />
                  <span>API Key</span>
                </Space>
              }
              name="apiKey"
              rules={[{ required: config.llm.enabled, message: "请输入 API Key" }]}
              extra="您的 OpenAI API Key 或兼容服务的 API Key"
            >
              <Input
                type={showApiKey ? "text" : "password"}
                placeholder="sk-xxxxxxxxxxxxxxxxxxxxxxxx"
                prefix={<KeyOutlined />}
                suffix={
                  <Button
                    type="text"
                    size="small"
                    icon={showApiKey ? <EyeInvisibleOutlined /> : <EyeOutlined />}
                    onClick={() => setShowApiKey(!showApiKey)}
                  />
                }
              />
            </Form.Item>

            <Divider />

            <Form.Item
              label={
                <Space>
                  <ClockCircleOutlined />
                  <span>请求超时 (秒)</span>
                </Space>
              }
              name="timeout"
              rules={[{ required: true, message: "请输入超时时间" }]}
            >
              <InputNumber min={5} max={300} style={{ width: "100%" }} />
            </Form.Item>

            <Form.Item
              label={
                <Space>
                  <FileTextOutlined />
                  <span>最大输出 Token 数</span>
                </Space>
              }
              name="maxOutputTokens"
              rules={[{ required: true, message: "请输入最大 Token 数" }]}
              extra="限制 AI 回复的长度，建议 300-1000"
            >
              <InputNumber min={100} max={4000} style={{ width: "100%" }} />
            </Form.Item>

            <Form.Item>
              <Space>
                <Button
                  type="primary"
                  htmlType="submit"
                  icon={<SaveOutlined />}
                  size="large"
                >
                  保存 LLM 配置
                </Button>
                <Button onClick={handleReset} danger>
                  重置所有配置
                </Button>
              </Space>
            </Form.Item>
          </Form>
        </Card>
      ),
    },
    {
      key: "github",
      label: (
        <Space>
          <GithubOutlined />
          GitHub 配置
        </Space>
      ),
      children: (
        <Card className="flat-card">
          <Alert
            type="info"
            showIcon
            icon={<InfoCircleOutlined />}
            message="关于 GitHub Token"
            description="配置 GitHub Token 后，系统可以扫描您的仓库、创建 Pull Request 以及获取仓库信息。Token 仅保存在本地浏览器中。"
            style={{ marginBottom: 24 }}
          />

          <Form
            form={githubForm}
            layout="vertical"
            onFinish={handleSaveGithub}
          >
            <Form.Item
              label={
                <Space>
                  <KeyOutlined />
                  <span>GitHub Token</span>
                  {config.githubToken && (
                    <Tag color="success" icon={<CheckCircleOutlined />}>
                      已配置
                    </Tag>
                  )}
                </Space>
              }
              name="token"
              rules={[{ required: true, message: "请输入 GitHub Token" }]}
              extra={
                <>
                  前往{" "}
                  <a
                    href="https://github.com/settings/tokens"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    GitHub Settings → Developer settings → Personal access tokens
                  </a>
                  {" "}生成 Token，需要勾选 repo 权限
                </>
              }
            >
              <Input
                type={showGithubToken ? "text" : "password"}
                placeholder="ghp_xxxxxxxxxxxxxxxxxxxxxxxx"
                prefix={<GithubOutlined />}
                suffix={
                  <Button
                    type="text"
                    size="small"
                    icon={showGithubToken ? <EyeInvisibleOutlined /> : <EyeOutlined />}
                    onClick={() => setShowGithubToken(!showGithubToken)}
                  />
                }
              />
            </Form.Item>

            <Form.Item>
              <Button
                type="primary"
                htmlType="submit"
                icon={<SaveOutlined />}
                size="large"
              >
                保存 GitHub Token
              </Button>
            </Form.Item>
          </Form>

          <Divider />

          <Title level={5}>Token 权限说明</Title>
          <Paragraph>
            <ul>
              <li>
                <strong>repo</strong> - 访问私有仓库（如需扫描私有仓库）
              </li>
              <li>
                <strong>public_repo</strong> - 访问公开仓库
              </li>
              <li>
                <strong>workflow</strong> - 访问 GitHub Actions（可选）
              </li>
            </ul>
          </Paragraph>
        </Card>
      ),
    },
    {
      key: "permissions",
      label: (
        <Space>
          <KeyOutlined />
          权限控制
        </Space>
      ),
      children: (
        <Card className="flat-card">
          <Alert
            type="warning"
            showIcon
            message="权限控制"
            description="管理系统功能权限，关闭时对应功能将被拒绝执行。"
            style={{ marginBottom: 24 }}
          />

          {/* 全局总开关 */}
          <Card className="flat-card" style={{ marginBottom: 16, backgroundColor: "#fff7e6" }}>
            <Space direction="vertical" style={{ width: "100%" }}>
              <Space style={{ width: "100%", justifyContent: "space-between" }}>
                <Space direction="vertical" size={0}>
                  <Title level={5} style={{ margin: 0, color: "#d46b08" }}>
                    🔒 远程/高风险操作总开关
                  </Title>
                  <Text type="secondary">
                    {permissionDescriptions["global_remote_enabled"]?.description}
                  </Text>
                </Space>
                <Switch
                  checked={Boolean(permissions["global_remote_enabled"])}
                  onChange={(checked) => handleSavePermissions("global_remote_enabled", checked)}
                  checkedChildren="已启用"
                  unCheckedChildren="已禁用"
                />
              </Space>
              {!permissions["global_remote_enabled"] && (
                <Alert
                  type="error"
                  showIcon
                  message="总开关已关闭"
                  description={permissionDescriptions["global_remote_enabled"]?.risk}
                  style={{ marginTop: 12 }}
                />
              )}
            </Space>
          </Card>

          {Object.keys(permissionGroups).length === 0 && (
            <Alert
              type="info"
              showIcon
              message="暂无权限配置"
              description="请先在后端配置权限项。"
              style={{ marginBottom: 24 }}
            />
          )}

          {Object.entries(permissionGroups).map(([groupKey, items]) => {
            const meta = permissionGroupMeta[groupKey] ?? {
              title: groupKey,
              description: ""
            };
            return (
              <Card key={groupKey} className="flat-card" style={{ marginBottom: 16 }}>
                <Title level={5} style={{ marginBottom: 4 }}>
                  {meta.title}
                </Title>
                {meta.description && (
                  <Text type="secondary">{meta.description}</Text>
                )}
                <Divider style={{ margin: "12px 0" }} />
                <Space direction="vertical" style={{ width: "100%" }} size="middle">
                  {items.map((permissionKey) => {
                    const desc = permissionDescriptions[permissionKey];
                    const isRemote = permissionKey !== "global_remote_enabled" &&
                      !["git_checkout", "git_create_branch", "git_add", "git_commit", "fs_read"].includes(permissionKey);
                    const isDisabled = isRemote && !permissions["global_remote_enabled"];
                    return (
                      <Space
                        key={permissionKey}
                        style={{ width: "100%", justifyContent: "space-between" }}
                        align="start"
                      >
                        <Space direction="vertical" size={0} style={{ maxWidth: "70%" }}>
                          <Text strong={desc?.risk !== undefined} style={{ color: desc?.risk ? "#d46b08" : undefined }}>
                            {desc?.label || permissionKey}
                            {desc?.risk && " ⚠️"}
                          </Text>
                          {desc?.description && (
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              {desc.description}
                            </Text>
                          )}
                          {desc?.risk && (
                            <Text type="danger" style={{ fontSize: 12 }}>
                              风险提示：{desc.risk}
                            </Text>
                          )}
                        </Space>
                        <Switch
                          checked={Boolean(permissions[permissionKey])}
                          onChange={(checked) => handleSavePermissions(permissionKey, checked)}
                          checkedChildren="已启用"
                          unCheckedChildren="已禁用"
                          disabled={isDisabled}
                        />
                      </Space>
                    );
                  })}
                </Space>
              </Card>
            );
          })}
        </Card>
      )
    },
    {
      key: "mcp",
      label: (
        <Space>
          <ApiOutlined />
          MCP 配置
        </Space>
      ),
      children: <MCPManager />
    },
  ];

  return (
    <div className="settings-page">
      <Title level={2} style={{ margin: 0, color: "#166534", marginBottom: 16 }}>
        <SettingOutlined /> 系统设置
      </Title>

      <Paragraph style={{ color: "#5a6c7d", marginBottom: 24 }}>
        配置大模型 API、GitHub Token，并管理系统权限开关
      </Paragraph>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={items}
        type="card"
        size="large"
      />
    </div>
  );
}
