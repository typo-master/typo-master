import { useEffect, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Empty,
  Form,
  Input,
  InputNumber,
  List,
  Modal,
  Popconfirm,
  Select,
  Space,
  Switch,
  Tabs,
  Tag,
  Typography,
  message,
} from "antd";
import {
  ApiOutlined,
  CheckCircleOutlined,
  DeleteOutlined,
  DownloadOutlined,
  EditOutlined,
  PlusOutlined,
  SearchOutlined,
} from "@ant-design/icons";
import {
  deleteMCPServer,
  installMCPCatalog,
  listMCPCatalog,
  listMCPServers,
  probeMCPServer,
  upsertMCPServer,
} from "../../api";
import type { MCPCatalogItem, MCPServerRecord } from "../../types";

const { Text, Paragraph } = Typography;

interface MCPFormValues {
  id: string;
  name: string;
  description?: string;
  enabled: boolean;
  transport: "stdio" | "http" | "sse" | "streamable_http";
  command?: string;
  argsJson?: string;
  url?: string;
  headersJson?: string;
  envJson?: string;
  timeout: number;
}

const TRANSPORT_OPTIONS = [
  { label: "STDIO", value: "stdio" },
  { label: "HTTP", value: "http" },
  { label: "SSE", value: "sse" },
  { label: "Streamable HTTP", value: "streamable_http" },
];

function parseJsonObject(label: string, raw?: string): Record<string, string> {
  if (!raw || !raw.trim()) return {};
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    throw new Error(`${label} 必须是合法 JSON 对象`);
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error(`${label} 必须是 JSON 对象`);
  }
  return Object.fromEntries(
    Object.entries(parsed as Record<string, unknown>).map(([key, value]) => [String(key), String(value)])
  );
}

function parseJsonArray(label: string, raw?: string): string[] {
  if (!raw || !raw.trim()) return [];
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    throw new Error(`${label} 必须是合法 JSON 数组`);
  }
  if (!Array.isArray(parsed)) {
    throw new Error(`${label} 必须是 JSON 数组`);
  }
  return parsed.map((item) => String(item));
}

export default function MCPManager() {
  const [form] = Form.useForm<MCPFormValues>();
  const [servers, setServers] = useState<MCPServerRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  const [catalogItems, setCatalogItems] = useState<MCPCatalogItem[]>([]);
  const [catalogQuery, setCatalogQuery] = useState("");
  const [catalogLoading, setCatalogLoading] = useState(false);

  const transport = Form.useWatch("transport", form);

  const loadServers = async () => {
    setLoading(true);
    try {
      const payload = await listMCPServers();
      setServers((payload.servers || []).slice().sort((a, b) => a.id.localeCompare(b.id)));
    } catch (error) {
      console.error("Failed to load MCP servers:", error);
      message.error("加载 MCP 配置失败");
    } finally {
      setLoading(false);
    }
  };

  const loadCatalog = async (query = "") => {
    setCatalogLoading(true);
    try {
      const payload = await listMCPCatalog(query);
      setCatalogItems(payload.items || []);
    } catch (error) {
      console.error("Failed to load MCP catalog:", error);
      message.error("加载 MCP 市场失败");
    } finally {
      setCatalogLoading(false);
    }
  };

  useEffect(() => {
    void loadServers();
    void loadCatalog("");
  }, []);

  const resetForm = () => {
    form.resetFields();
    form.setFieldsValue({
      enabled: true,
      transport: "stdio",
      timeout: 30,
      argsJson: "[]",
      headersJson: "{}",
      envJson: "{}",
    });
  };

  const openCreate = () => {
    setEditingId(null);
    resetForm();
    setModalOpen(true);
  };

  const openEdit = (server: MCPServerRecord) => {
    setEditingId(server.id);
    form.setFieldsValue({
      id: server.id,
      name: server.name,
      description: server.description || "",
      enabled: Boolean(server.enabled),
      transport: (server.transport as MCPFormValues["transport"]) || "stdio",
      command: server.command || "",
      argsJson: JSON.stringify(server.args || [], null, 2),
      url: server.url || "",
      headersJson: JSON.stringify(server.headers || {}, null, 2),
      envJson: JSON.stringify(server.env || {}, null, 2),
      timeout: server.timeout || 30,
    });
    setModalOpen(true);
  };

  const handleDelete = async (server: MCPServerRecord) => {
    try {
      await deleteMCPServer(server.id);
      message.success(`已删除 MCP 服务: ${server.id}`);
      await loadServers();
    } catch (error) {
      console.error("Delete MCP server failed:", error);
      message.error("删除 MCP 服务失败");
    }
  };

  const handleProbe = async (server: MCPServerRecord) => {
    try {
      const result = await probeMCPServer(server.id);
      const tools = Array.isArray(result.result?.tools) ? result.result.tools : [];
      message.success(`连接成功，发现 ${tools.length} 个工具`);
    } catch (error) {
      console.error("Probe MCP server failed:", error);
      message.error("探测 MCP 服务失败");
    }
  };

  const handleInstallCatalog = async (item: MCPCatalogItem) => {
    try {
      await installMCPCatalog(item.catalog_id, {});
      message.success(`已安装 MCP: ${item.name}`);
      await loadServers();
    } catch (error) {
      console.error("Install MCP catalog failed:", error);
      message.error("安装 MCP 失败");
    }
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      const serverId = values.id.trim();
      const payload: MCPServerRecord = {
        id: serverId,
        name: values.name.trim(),
        description: values.description?.trim() || "",
        enabled: Boolean(values.enabled),
        transport: values.transport,
        command: values.command?.trim() || null,
        args: parseJsonArray("启动参数", values.argsJson),
        url: values.url?.trim() || null,
        headers: parseJsonObject("HTTP Headers", values.headersJson),
        env: parseJsonObject("环境变量", values.envJson),
        timeout: Number(values.timeout || 30),
      };

      await upsertMCPServer(serverId, payload);
      setModalOpen(false);
      message.success(editingId ? "MCP 服务已更新" : "MCP 服务已创建");
      await loadServers();
    } catch (error) {
      if (error instanceof Error && error.message.includes("out of date")) return;
      if (error instanceof Error) {
        message.error(error.message);
      }
    }
  };

  const tabItems = [
    {
      key: "installed",
      label: (
        <Space>
          <ApiOutlined />
          已安装服务
        </Space>
      ),
      children: (
        <Card
          size="small"
          style={{ marginTop: 8 }}
          title={
            <Space>
              <Text strong>当前服务</Text>
              <Tag color="blue">{servers.length} 个</Tag>
            </Space>
          }
          extra={
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
              手动新增
            </Button>
          }
        >
          {servers.length === 0 ? (
            <Empty description="暂无 MCP 服务配置" />
          ) : (
            <List
              loading={loading}
              dataSource={servers}
              renderItem={(server) => (
                <List.Item
                  actions={[
                    <Button key="probe" type="link" icon={<SearchOutlined />} onClick={() => void handleProbe(server)}>
                      探测
                    </Button>,
                    <Button key="edit" type="link" icon={<EditOutlined />} onClick={() => openEdit(server)}>
                      编辑
                    </Button>,
                    <Popconfirm
                      key="delete"
                      title="删除 MCP 服务"
                      description={`确认删除 ${server.id}?`}
                      onConfirm={() => void handleDelete(server)}
                    >
                      <Button type="link" danger icon={<DeleteOutlined />}>
                        删除
                      </Button>
                    </Popconfirm>,
                  ]}
                >
                  <List.Item.Meta
                    title={
                      <Space>
                        <Text strong>{server.name}</Text>
                        <Tag>{server.id}</Tag>
                        <Tag color={server.enabled ? "green" : "default"}>
                          {server.enabled ? (
                            <>
                              <CheckCircleOutlined /> 已启用
                            </>
                          ) : (
                            "已禁用"
                          )}
                        </Tag>
                        <Tag color="blue">{server.transport}</Tag>
                      </Space>
                    }
                    description={
                      <Space direction="vertical" size={2}>
                        <Text type="secondary">{server.description || "暂无描述"}</Text>
                        {server.transport === "stdio" ? (
                          <Text type="secondary">
                            command: <Text code>{server.command || "(未配置)"}</Text>
                          </Text>
                        ) : (
                          <Text type="secondary">
                            url: <Text code>{server.url || "(未配置)"}</Text>
                          </Text>
                        )}
                      </Space>
                    }
                  />
                </List.Item>
              )}
            />
          )}
        </Card>
      ),
    },
    {
      key: "market",
      label: (
        <Space>
          <DownloadOutlined />
          MCP 市场
        </Space>
      ),
      children: (
        <Card size="small" style={{ marginTop: 8 }}>
          <Space direction="vertical" style={{ width: "100%" }} size={12}>
            <Input.Search
              value={catalogQuery}
              allowClear
              placeholder="搜索 MCP（如 github / sql / filesystem）"
              enterButton="搜索"
              onChange={(e) => setCatalogQuery(e.target.value)}
              onSearch={(value) => void loadCatalog(value)}
            />
            {catalogItems.length === 0 ? (
              <Empty description={catalogLoading ? "加载中..." : "未找到匹配的 MCP"} />
            ) : (
              <List
                loading={catalogLoading}
                dataSource={catalogItems}
                renderItem={(item) => (
                  <List.Item
                    actions={[
                      <Button
                        key="install"
                        type="link"
                        icon={<DownloadOutlined />}
                        onClick={() => void handleInstallCatalog(item)}
                      >
                        一键安装
                      </Button>,
                    ]}
                  >
                    <List.Item.Meta
                      title={
                        <Space>
                          <Text strong>{item.name}</Text>
                          <Tag>{item.catalog_id}</Tag>
                          <Tag color="blue">{item.server.transport}</Tag>
                        </Space>
                      }
                      description={
                        <Space direction="vertical" size={4}>
                          <Text type="secondary">{item.description}</Text>
                          <Space wrap>
                            {(item.tags || []).map((tag) => (
                              <Tag key={tag}>{tag}</Tag>
                            ))}
                          </Space>
                        </Space>
                      }
                    />
                  </List.Item>
                )}
              />
            )}
          </Space>
        </Card>
      ),
    },
  ];

  return (
    <div>
      <Alert
        type="info"
        showIcon
        message="MCP 服务管理"
        description={
          <Paragraph style={{ marginBottom: 0 }}>
            管理 Model Context Protocol (MCP) 服务器，从市场一键安装或手动配置自定义 MCP 服务。
          </Paragraph>
        }
        style={{ marginBottom: 16 }}
      />

      <Tabs defaultActiveKey="installed" items={tabItems} />

      <Modal
        title={editingId ? "编辑 MCP 服务" : "新增 MCP 服务"}
        open={modalOpen}
        onCancel={() => {
          setModalOpen(false);
          resetForm();
        }}
        onOk={() => void handleSave()}
        width={760}
      >
        <Form layout="vertical" form={form}>
          <Form.Item
            label="服务 ID"
            name="id"
            rules={[{ required: true, message: "请输入服务 ID" }]}
            extra="用于在 Skill 执行器中引用该 MCP 服务"
          >
            <Input disabled={Boolean(editingId)} placeholder="例如: local-filesystem" />
          </Form.Item>

          <Form.Item
            label="服务名称"
            name="name"
            rules={[{ required: true, message: "请输入服务名称" }]}
          >
            <Input placeholder="例如: Local Files MCP" />
          </Form.Item>

          <Form.Item label="描述" name="description">
            <Input.TextArea rows={2} placeholder="该 MCP 服务的用途说明" />
          </Form.Item>

          <Form.Item label="启用状态" name="enabled" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>

          <Form.Item label="Transport" name="transport" rules={[{ required: true }]}>
            <Select options={TRANSPORT_OPTIONS} />
          </Form.Item>

          {transport === "stdio" && (
            <>
              <Form.Item label="启动命令" name="command" rules={[{ required: true, message: "stdio 模式必须配置 command" }]}>
                <Input placeholder="例如: npx" />
              </Form.Item>
              <Form.Item label="启动参数 JSON 数组" name="argsJson">
                <Input.TextArea rows={3} placeholder='例如: ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]' />
              </Form.Item>
              <Form.Item label="环境变量 JSON 对象" name="envJson">
                <Input.TextArea rows={3} placeholder='例如: {"API_KEY":"xxx"}' />
              </Form.Item>
            </>
          )}

          {transport !== "stdio" && (
            <>
              <Form.Item label="服务 URL" name="url" rules={[{ required: true, message: "HTTP/SSE 模式必须配置 URL" }]}>
                <Input placeholder="例如: http://127.0.0.1:3001/mcp" />
              </Form.Item>
              <Form.Item label="HTTP Headers JSON 对象" name="headersJson">
                <Input.TextArea rows={3} placeholder='例如: {"Authorization":"Bearer token"}' />
              </Form.Item>
            </>
          )}

          <Form.Item label="超时时间（秒）" name="timeout">
            <InputNumber min={3} max={600} style={{ width: "100%" }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
