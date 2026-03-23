import { useEffect, useState, useCallback } from "react";
import {
  Card,
  List,
  Button,
  Modal,
  Form,
  Input,
  InputNumber,
  Switch,
  Typography,
  Space,
  Tag,
  Tooltip,
  Badge,
  Popconfirm,
  Empty,
  Spin,
  message,
  Select,
  Divider,
  Avatar,
} from "antd";
import {
  ClockCircleOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  HistoryOutlined,
  FireOutlined,
  CalendarOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from "@ant-design/icons";
import { triggerStore, logStore, type Trigger, type ExecutionLog } from "../../db";

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;
const { Option } = Select;

interface TriggerManagerProps {
  onTriggerExecute?: (triggerId: number, prompt: string) => void;
}

export default function TriggerManager({ onTriggerExecute }: TriggerManagerProps) {
  const [triggers, setTriggers] = useState<Trigger[]>([]);
  const [logs, setLogs] = useState<ExecutionLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingTrigger, setEditingTrigger] = useState<Trigger | null>(null);
  const [isLogsModalOpen, setIsLogsModalOpen] = useState(false);
  const [form] = Form.useForm();

  // 加载触发器和日志
  const loadData = useCallback(async () => {
    try {
      const [triggerData, logData] = await Promise.all([
        triggerStore.getAll(),
        logStore.getAll(),
      ]);
      // 按创建时间倒序
      setTriggers(triggerData.sort((a, b) => b.createdAt - a.createdAt));
      setLogs(logData.sort((a, b) => b.timestamp - a.timestamp).slice(0, 50));
    } catch (error) {
      console.error("Failed to load triggers:", error);
      message.error("加载触发器失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    // 每30秒刷新一次
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, [loadData]);

  // 创建或更新触发器
  const handleSave = async (values: any) => {
    try {
      const now = Date.now();
      const interval = values.interval || 60;

      if (editingTrigger?.id) {
        // 更新
        const updated: Trigger = {
          ...editingTrigger,
          name: values.name,
          description: values.description,
          prompt: values.prompt,
          interval: interval,
          enabled: values.enabled,
          targetAgent: values.targetAgent || "default",
          nextRun: editingTrigger.lastRun
            ? editingTrigger.lastRun + interval * 60 * 1000
            : now + interval * 60 * 1000,
        };
        await triggerStore.update(updated);
        message.success("触发器已更新");
      } else {
        // 创建
        const newTrigger: Omit<Trigger, "id"> = {
          name: values.name,
          description: values.description,
          prompt: values.prompt,
          interval: interval,
          enabled: values.enabled,
          targetAgent: values.targetAgent || "default",
          createdAt: now,
          runCount: 0,
          lastRun: undefined,
          nextRun: now + interval * 60 * 1000,
        };
        await triggerStore.add(newTrigger);
        message.success("触发器已创建");
      }

      setIsModalOpen(false);
      setEditingTrigger(null);
      form.resetFields();
      await loadData();
    } catch (error) {
      message.error("保存失败: " + String(error));
    }
  };

  // 删除触发器
  const handleDelete = async (id: number) => {
    try {
      await triggerStore.delete(id);
      message.success("触发器已删除");
      await loadData();
    } catch (error) {
      message.error("删除失败");
    }
  };

  // 切换启用状态
  const handleToggle = async (trigger: Trigger) => {
    try {
      const updated = { ...trigger, enabled: !trigger.enabled };
      if (updated.enabled && !updated.nextRun) {
        updated.nextRun = Date.now() + updated.interval * 60 * 1000;
      }
      await triggerStore.update(updated);
      await loadData();
      message.success(updated.enabled ? "触发器已启用" : "触发器已暂停");
    } catch (error) {
      message.error("操作失败");
    }
  };

  // 手动执行触发器
  const handleManualExecute = async (trigger: Trigger) => {
    try {
      // 创建执行日志
      const log: Omit<ExecutionLog, "id"> = {
        triggerId: trigger.id!,
        triggerName: trigger.name,
        prompt: trigger.prompt,
        status: "running",
        timestamp: Date.now(),
      };
      const logId = await logStore.add(log);

      // 更新触发器执行时间
      await triggerStore.update({
        ...trigger,
        lastRun: Date.now(),
        nextRun: Date.now() + trigger.interval * 60 * 1000,
        runCount: trigger.runCount + 1,
      });

      // 调用外部回调
      if (onTriggerExecute) {
        onTriggerExecute(trigger.id!, trigger.prompt);
      }

      // 模拟执行完成（实际应由外部处理）
      setTimeout(async () => {
        await logStore.update({
          id: logId,
          ...log,
          status: "success",
          result: "执行成功",
          duration: 2000,
        });
        await loadData();
      }, 2000);

      message.success("触发器已开始执行");
      await loadData();
    } catch (error) {
      message.error("执行失败");
    }
  };

  // 打开编辑弹窗
  const openEditModal = (trigger?: Trigger) => {
    if (trigger) {
      setEditingTrigger(trigger);
      form.setFieldsValue({
        name: trigger.name,
        description: trigger.description,
        prompt: trigger.prompt,
        interval: trigger.interval,
        enabled: trigger.enabled,
        targetAgent: trigger.targetAgent || "default",
      });
    } else {
      setEditingTrigger(null);
      form.setFieldsValue({
        interval: 60,
        enabled: true,
        targetAgent: "default",
      });
    }
    setIsModalOpen(true);
  };

  // 格式化下次执行时间
  const formatNextRun = (nextRun?: number) => {
    if (!nextRun) return "未安排";
    const diff = nextRun - Date.now();
    if (diff <= 0) return "即将执行";
    const minutes = Math.floor(diff / 60000);
    if (minutes < 60) return `${minutes}分钟后`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}小时后`;
    const days = Math.floor(hours / 24);
    return `${days}天后`;
  };

  // 获取状态颜色
  const getStatusColor = (status: string) => {
    switch (status) {
      case "success":
        return "success";
      case "failed":
        return "error";
      case "running":
        return "processing";
      default:
        return "default";
    }
  };

  // 获取状态文字
  const getStatusText = (status: string) => {
    switch (status) {
      case "success":
        return "成功";
      case "failed":
        return "失败";
      case "running":
        return "执行中";
      default:
        return "未知";
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: 40 }}>
        <Spin tip="加载触发器中..." />
      </div>
    );
  }

  return (
    <div className="trigger-manager">
      {/* 触发器列表 */}
      <Card
        title={
          <Space>
            <ClockCircleOutlined />
            <span>定时触发器</span>
            <Badge count={triggers.filter((t) => t.enabled).length} color="#22c55e" />
          </Space>
        }
        extra={
          <Space>
            <Button
              type="text"
              icon={<HistoryOutlined />}
              onClick={() => setIsLogsModalOpen(true)}
            >
              执行日志
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => openEditModal()}
            >
              新建触发器
            </Button>
          </Space>
        }
      >
        {triggers.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              <span>
                暂无触发器
                <br />
                <Text type="secondary">创建定时任务，让 Agent 自动执行</Text>
              </span>
            }
          >
            <Button type="primary" icon={<PlusOutlined />} onClick={() => openEditModal()}>
              创建触发器
            </Button>
          </Empty>
        ) : (
          <List
            dataSource={triggers}
            renderItem={(trigger) => (
              <List.Item
                actions={[
                  <Tooltip title="手动执行" key="run">
                    <Button
                      type="text"
                      icon={<PlayCircleOutlined />}
                      onClick={() => handleManualExecute(trigger)}
                    />
                  </Tooltip>,
                  <Tooltip title={trigger.enabled ? "暂停" : "启用"} key="toggle">
                    <Button
                      type="text"
                      icon={trigger.enabled ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
                      onClick={() => handleToggle(trigger)}
                    />
                  </Tooltip>,
                  <Tooltip title="编辑" key="edit">
                    <Button
                      type="text"
                      icon={<EditOutlined />}
                      onClick={() => openEditModal(trigger)}
                    />
                  </Tooltip>,
                  <Tooltip title="删除" key="delete">
                    <Popconfirm
                      title="确认删除"
                      description={`确定要删除触发器 "${trigger.name}" 吗？`}
                      onConfirm={() => handleDelete(trigger.id!)}
                      okText="删除"
                      cancelText="取消"
                    >
                      <Button type="text" danger icon={<DeleteOutlined />} />
                    </Popconfirm>
                  </Tooltip>,
                ]}
              >
                <List.Item.Meta
                  avatar={
                    <Avatar
                      size="large"
                      icon={<ClockCircleOutlined />}
                      style={{
                        background: trigger.enabled ? "#22c55e" : "#ccc",
                      }}
                    />
                  }
                  title={
                    <Space>
                      <Text strong>{trigger.name}</Text>
                      {trigger.enabled ? (
                        <Tag color="success">
                          <CheckCircleOutlined /> 运行中
                        </Tag>
                      ) : (
                        <Tag color="default">
                          <CloseCircleOutlined /> 已暂停
                        </Tag>
                      )}
                    </Space>
                  }
                  description={
                    <Space direction="vertical" size={4} style={{ width: "100%" }}>
                      <Text type="secondary" ellipsis style={{ maxWidth: 400 }}>
                        {trigger.description || "暂无描述"}
                      </Text>
                      <Space size={16}>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          <CalendarOutlined /> 间隔: {trigger.interval}分钟
                        </Text>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          <FireOutlined /> 已执行: {trigger.runCount}次
                        </Text>
                        {trigger.enabled && trigger.nextRun && (
                          <Text type="success" style={{ fontSize: 12 }}>
                            <ClockCircleOutlined /> 下次: {formatNextRun(trigger.nextRun)}
                          </Text>
                        )}
                      </Space>
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Card>

      {/* 快速提示 */}
      {triggers.length > 0 && (
        <Card size="small" style={{ marginTop: 16 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            <ClockCircleOutlined /> 提示: 触发器会在后台自动检查，到达设定时间后会向 Agent 发送提示词执行相应任务。
          </Text>
        </Card>
      )}

      {/* 创建/编辑弹窗 */}
      <Modal
        title={editingTrigger ? "编辑触发器" : "新建触发器"}
        open={isModalOpen}
        onCancel={() => {
          setIsModalOpen(false);
          setEditingTrigger(null);
          form.resetFields();
        }}
        onOk={() => form.submit()}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSave}
          style={{ marginTop: 16 }}
        >
          <Form.Item
            name="name"
            label="触发器名称"
            rules={[{ required: true, message: "请输入触发器名称" }]}
          >
            <Input placeholder="例如: 每日代码扫描" />
          </Form.Item>

          <Form.Item name="description" label="描述">
            <Input placeholder="简要说明触发器的作用" />
          </Form.Item>

          <Form.Item
            name="prompt"
            label="提示词"
            rules={[{ required: true, message: "请输入提示词" }]}
            extra="触发时发送给 Agent 的消息，Agent 会根据这个提示词执行任务"
          >
            <TextArea
              rows={4}
              placeholder="例如: 帮我扫描最近的代码变更，检查是否有新的拼写错误"
            />
          </Form.Item>

          <Form.Item
            name="interval"
            label="执行间隔（分钟）"
            rules={[{ required: true, min: 1, message: "间隔至少1分钟" }]}
            initialValue={60}
          >
            <InputNumber
              min={1}
              style={{ width: "100%" }}
              placeholder="60"
            />
          </Form.Item>

          <Form.Item
            name="targetAgent"
            label="目标 Agent"
            initialValue="default"
          >
            <Select>
              <Option value="default">默认 Agent</Option>
              <Option value="typo">拼写检查 Agent</Option>
              <Option value="github">GitHub Agent</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="enabled"
            label="立即启用"
            valuePropName="checked"
            initialValue={true}
          >
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      {/* 执行日志弹窗 */}
      <Modal
        title={
          <Space>
            <HistoryOutlined />
            <span>执行日志</span>
          </Space>
        }
        open={isLogsModalOpen}
        onCancel={() => setIsLogsModalOpen(false)}
        width={700}
        footer={null}
      >
        {logs.length === 0 ? (
          <Empty description="暂无执行记录" />
        ) : (
          <List
            style={{ maxHeight: 400, overflow: "auto" }}
            dataSource={logs}
            renderItem={(log) => (
              <List.Item>
                <List.Item.Meta
                  title={
                    <Space>
                      <Text strong>{log.triggerName}</Text>
                      <Badge status={getStatusColor(log.status)} text={getStatusText(log.status)} />
                    </Space>
                  }
                  description={
                    <Space direction="vertical" size={2} style={{ width: "100%" }}>
                      <Text type="secondary" ellipsis style={{ maxWidth: 600 }}>
                        {log.prompt}
                      </Text>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {new Date(log.timestamp).toLocaleString()}
                        {log.duration && ` · 耗时 ${log.duration}ms`}
                      </Text>
                      {log.error && (
                        <Text type="danger" style={{ fontSize: 12 }}>
                          错误: {log.error}
                        </Text>
                      )}
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Modal>
    </div>
  );
}
