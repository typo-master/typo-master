import { useEffect, useState, useRef, useCallback, useMemo } from "react";
import {
  Card,
  Input,
  Button,
  List,
  Avatar,
  Tag,
  Typography,
  Space,
  Empty,
  Spin,
  message,
  Tooltip,
  Badge,
  Popconfirm,
  Popover,
  Select,
  Divider,
} from "antd";
import {
  SendOutlined,
  RobotOutlined,
  UserOutlined,
  ClearOutlined,
  ToolOutlined,
  ThunderboltOutlined,
  HistoryOutlined,
  DeleteOutlined,
  LoadingOutlined,
  CheckCircleOutlined,
  ApiOutlined,
  CodeOutlined,
  FullscreenOutlined,
  FullscreenExitOutlined,
  SettingOutlined,
  QuestionCircleOutlined,
  PlayCircleOutlined,
  CheckOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
  ArrowRightOutlined,
  DotChartOutlined,
  DatabaseOutlined,
  CloudOutlined,
  FileSearchOutlined,
  EditOutlined,
  BranchesOutlined,
} from "@ant-design/icons";
import { chatStore, getConversationMessages, skillStore, type ChatMessage, type ExecutionStep } from "../../db";
import { createConversation, sendChatMessage, executeSkill as executeSkillApi } from "../../api";
import { useConfig } from "../../config";
import SkillList from "../SkillList";
import type { AgentSkill } from "../../db";

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;
const { Option } = Select;

interface ChatSession {
  id: string;
  title: string;
  lastMessage: string;
  timestamp: number;
  messageCount: number;
}

interface AIChatProps {
  agentId?: string;
  onExecuteSkill?: (skill: string, params: any) => void;
}

// 斜杠命令定义 - 仅包含系统级命令
interface SlashCommand {
  name: string;
  description: string;
  icon: React.ReactNode;
  usage?: string;
  params?: { name: string; description: string; optional?: boolean }[];
  isDynamic?: boolean; // 标记是否为动态从后端获取的命令
}

// 基础系统命令（固定）
const BASE_COMMANDS: SlashCommand[] = [
  {
    name: "skill",
    description: "执行 Agent Skill",
    icon: <ToolOutlined />,
    usage: "/skill <skill_name> [params]",
    params: [
      { name: "skill_name", description: "技能名称", optional: false },
      { name: "params", description: "JSON 参数（可选）", optional: true },
    ],
  },
  {
    name: "help",
    description: "显示帮助信息",
    icon: <QuestionCircleOutlined />,
    usage: "/help",
  },
  {
    name: "clear",
    description: "清空当前对话",
    icon: <ClearOutlined />,
    usage: "/clear",
  },
  {
    name: "settings",
    description: "查看当前配置",
    icon: <SettingOutlined />,
    usage: "/settings",
  },
];

// 动态命令生成函数 - 从后端 Skill 生成快捷命令
const generateDynamicCommands = (skills: AgentSkill[]): SlashCommand[] => {
  const dynamicCommands: SlashCommand[] = [];

  // 为常用 Skill 生成快捷命令
  const shortcutSkills = skills.filter(s =>
    ["search_github_repos", "scan_typo", "fix_typo", "get_github_repo"].includes(s.name)
  );

  shortcutSkills.forEach(skill => {
    const paramStr = skill.parameters
      ?.filter(p => p.required)
      .map(p => p.name)
      .join(" ") || "";

    dynamicCommands.push({
      name: skill.name.replace(/_/g, ""),
      description: skill.description,
      icon: <ToolOutlined />,
      usage: `/${skill.name.replace(/_/g, "")} ${paramStr}`,
      isDynamic: true,
    });
  });

  return dynamicCommands;
};

// 自动补全状态类型
type AutocompleteType = "command" | "skill" | null;

export default function AIChat({ agentId = "default", onExecuteSkill }: AIChatProps) {
  const { config } = useConfig();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string>("");
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [showSkillPanel, setShowSkillPanel] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // 自动补全相关状态
  const [showAutocomplete, setShowAutocomplete] = useState(false);
  const [autocompleteType, setAutocompleteType] = useState<AutocompleteType>(null);
  const [filteredCommands, setFilteredCommands] = useState<SlashCommand[]>([]);
  const [filteredSkills, setFilteredSkills] = useState<AgentSkill[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [availableSkills, setAvailableSkills] = useState<AgentSkill[]>([]);
  const [cursorPosition, setCursorPosition] = useState(0);

  // 动态生成命令列表
  const SLASH_COMMANDS = useMemo(() => {
    return [...BASE_COMMANDS, ...generateDynamicCommands(availableSkills)];
  }, [availableSkills]);

  // 加载可用技能
  useEffect(() => {
    const loadSkills = async () => {
      const skills = await skillStore.getAll();
      setAvailableSkills(skills.filter((s) => s.enabled));
    };
    loadSkills();
  }, []);

  // 初始化对话
  useEffect(() => {
    const initConversation = async () => {
      try {
        const created = await createConversation();
        setConversationId(created.conversation_id);
      } catch (error) {
        console.error("Failed to create conversation", error);
        const newId = `conv_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        setConversationId(newId);
      }
      await loadSessions();
    };
    initConversation();
  }, []);

  // 加载消息
  useEffect(() => {
    if (conversationId) {
      loadMessages();
    }
  }, [conversationId]);

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const loadSessions = async () => {
    const allMessages = await chatStore.getAll();
    const sessionsMap = new Map<string, ChatSession>();

    allMessages.forEach((msg) => {
      const session = sessionsMap.get(msg.conversationId);
      if (!session) {
        sessionsMap.set(msg.conversationId, {
          id: msg.conversationId,
          title: `对话 ${msg.conversationId.slice(0, 8)}`,
          lastMessage: msg.content.slice(0, 50),
          timestamp: msg.timestamp,
          messageCount: 1,
        });
      } else {
        session.messageCount++;
        if (msg.timestamp > session.timestamp) {
          session.timestamp = msg.timestamp;
          session.lastMessage = msg.content.slice(0, 50);
        }
      }
    });

    setSessions(
      Array.from(sessionsMap.values()).sort((a, b) => b.timestamp - a.timestamp)
    );
  };

  // 自动补全逻辑
  const updateAutocomplete = useCallback((value: string, cursorPos: number) => {
    const textBeforeCursor = value.slice(0, cursorPos);

    // 检查是否在输入命令
    const commandMatch = textBeforeCursor.match(/^\/([a-zA-Z_]*)$/);
    if (commandMatch) {
      const query = commandMatch[1].toLowerCase();
      const filtered = SLASH_COMMANDS.filter(
        (cmd) => cmd.name.toLowerCase().startsWith(query)
      );
      setFilteredCommands(filtered);
      setAutocompleteType("command");
      setShowAutocomplete(filtered.length > 0);
      setSelectedIndex(0);
      return;
    }

    // 检查是否在输入 /skill 命令后的技能名称
    const skillMatch = textBeforeCursor.match(/^\/skill\s+([a-zA-Z0-9_:-]*)$/i);
    if (skillMatch) {
      const query = skillMatch[1].toLowerCase();
      const filtered = availableSkills.filter(
        (skill) => skill.name.toLowerCase().includes(query)
      );
      setFilteredSkills(filtered);
      setAutocompleteType("skill");
      setShowAutocomplete(filtered.length > 0);
      setSelectedIndex(0);
      return;
    }

    // 不匹配任何自动补全模式
    setShowAutocomplete(false);
    setAutocompleteType(null);
  }, [availableSkills]);

  // 处理输入变化
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    const cursorPos = e.target.selectionStart;
    setInput(value);
    setCursorPosition(cursorPos);
    updateAutocomplete(value, cursorPos);
  };

  // 选择自动补全项
  const selectAutocompleteItem = (index: number) => {
    if (autocompleteType === "command") {
      const command = filteredCommands[index];
      const newInput = `/${command.name} `;
      setInput(newInput);
      setShowAutocomplete(false);
      // 如果选择了 skill 命令，保持自动补全以显示技能列表
      if (command.name === "skill") {
        setTimeout(() => {
          setFilteredSkills(availableSkills);
          setAutocompleteType("skill");
          setShowAutocomplete(availableSkills.length > 0);
          setSelectedIndex(0);
        }, 0);
      }
    } else if (autocompleteType === "skill") {
      const skill = filteredSkills[index];
      // 构建带参数模板的命令
      const params = skill.parameters
        ?.filter((p) => p.required)
        .map((p) => `"${p.name}": "..."`)
        .join(", ");
      const newInput = `/skill ${skill.name}${params ? ` {${params}}` : ""}`;
      setInput(newInput);
      setShowAutocomplete(false);
    }
    // 聚焦回输入框
    setTimeout(() => textareaRef.current?.focus(), 0);
  };

  // 键盘导航处理
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (!showAutocomplete) {
      // 只有不在自动补全模式时才处理发送
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
      return;
    }

    const items = autocompleteType === "command" ? filteredCommands : filteredSkills;

    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setSelectedIndex((prev) => (prev + 1) % items.length);
        break;
      case "ArrowUp":
        e.preventDefault();
        setSelectedIndex((prev) => (prev - 1 + items.length) % items.length);
        break;
      case "Enter":
        e.preventDefault();
        selectAutocompleteItem(selectedIndex);
        break;
      case "Escape":
        e.preventDefault();
        setShowAutocomplete(false);
        break;
      case "Tab":
        e.preventDefault();
        selectAutocompleteItem(selectedIndex);
        break;
    }
  };

  const loadMessages = async () => {
    if (!conversationId) return;
    const msgs = await getConversationMessages(conversationId);
    setMessages(msgs);
  };

  const handleSend = async () => {
    if (!input.trim() || !conversationId) return;

    const content = input.trim();
    setInput("");
    setShowAutocomplete(false);
    setLoading(true);

    // 保存用户消息
    const userMessage: ChatMessage = {
      conversationId,
      agentId,
      role: "user",
      content,
      timestamp: Date.now(),
    };
    await chatStore.add(userMessage);
    setMessages((prev) => [...prev, userMessage]);

    try {
      // 处理内置斜杠命令
      if (content.startsWith("/")) {
        const handled = await handleSlashCommand(content);
        if (handled) {
          setLoading(false);
          await loadSessions();
          return;
        }
      }

      // 检查是否是 Skill 调用命令（向后兼容）
      const skillMatch = content.match(/^\/skill\s+([a-zA-Z0-9_:-]+)(.*)?$/);
      if (skillMatch) {
        const skillName = skillMatch[1];
        const paramsStr = skillMatch[2]?.trim();
        let params = {};
        if (paramsStr) {
          try {
            params = JSON.parse(paramsStr);
          } catch {
            // 如果不是 JSON，作为字符串参数
            params = { query: paramsStr };
          }
        }
        await executeSkill(skillName, params);
      } else {
        // 普通对话
        const reply = await sendChatMessage(conversationId, content);
        const aiMessage: ChatMessage = {
          conversationId,
          agentId,
          role: "assistant",
          content: reply.reply,
          timestamp: Date.now(),
          mode: reply.mode,
          metadata: {
            warning: reply.warning,
            model: reply.model,
          },
        };
        await chatStore.add(aiMessage);
        setMessages((prev) => [...prev, aiMessage]);
      }
    } catch (error) {
      message.error("发送失败: " + String(error));
    } finally {
      setLoading(false);
      await loadSessions();
    }
  };

  // 处理斜杠命令
  const handleSlashCommand = async (content: string): Promise<boolean> => {
    const parts = content.slice(1).split(/\s+/);
    const command = parts[0].toLowerCase();
    const args = parts.slice(1).join(" ");

    // 基础系统命令
    switch (command) {
      case "help":
        await showHelpMessage();
        return true;
      case "clear":
        await clearChat();
        return true;
      case "settings":
        await showSettingsMessage();
        return true;
    }

    // 处理动态快捷命令 - 检查是否匹配某个 Skill 的快捷方式
    const matchedSkill = availableSkills.find(s =>
      s.name.replace(/_/g, "").toLowerCase() === command
    );

    if (matchedSkill) {
      // 构建参数
      let params: Record<string, any> = {};
      if (args) {
        try {
          // 尝试解析为 JSON
          params = JSON.parse(args);
        } catch {
          // 如果不是 JSON，将参数映射到第一个必需参数
          const firstRequiredParam = matchedSkill.parameters?.find(p => p.required);
          if (firstRequiredParam) {
            params = { [firstRequiredParam.name]: args };
          } else {
            // 如果没有必需参数，使用 query 作为默认参数名
            params = { query: args };
          }
        }
      }
      await executeSkill(matchedSkill.name, params);
      return true;
    }

    return false;
  };

  // 添加系统消息
  const addSystemMessage = async (content: string) => {
    const systemMessage: ChatMessage = {
      conversationId,
      agentId,
      role: "assistant",
      content,
      timestamp: Date.now(),
      mode: "system",
    };
    await chatStore.add(systemMessage);
    setMessages((prev) => [...prev, systemMessage]);
  };

  // 显示帮助信息
  const showHelpMessage = async () => {
    const helpContent = `📚 **可用命令列表**

${SLASH_COMMANDS.map(cmd => `
**/${cmd.name}** - ${cmd.description}
${cmd.usage ? `\`\`\`${cmd.usage}\`\`\`` : ""}`).join("\n")}

💡 **提示**
- 输入 "/" 查看所有可用命令
- 输入 "/skill " 查看所有可用技能
- 使用 ↑↓ 选择，↵ 或 Tab 确认，Esc 关闭`;

    await addSystemMessage(helpContent);
  };

  // 显示设置信息
  const showSettingsMessage = async () => {
    const settingsContent = `⚙️ **当前配置**

| 配置项 | 状态 |
|--------|------|
| AI 功能 | ${config.llm.enabled ? "✅ 已启用" : "❌ 未启用"} |
| 模型 | ${config.llm.model || "未配置"} |
| GitHub Token | ${config.githubToken ? "✅ 已配置" : "❌ 未配置"} |
| 可用技能 | ${availableSkills.length} 个 |

${!config.llm.enabled ? "\n⚠️ 请在设置页面配置大模型 API" : ""}`;

    await addSystemMessage(settingsContent);
  };

  // 生成执行步骤
  const generateExecutionSteps = (skillName: string): ExecutionStep[] => {
    return [
      { id: "1", name: "参数解析", description: "解析输入参数", status: "pending" as ExecutionStep["status"], icon: "tool" },
      { id: "2", name: "权限检查", description: "验证执行权限", status: "pending" as ExecutionStep["status"], icon: "shield" },
      { id: "3", name: "环境准备", description: "初始化执行环境", status: "pending" as ExecutionStep["status"], icon: "setting" },
      { id: "4", name: "执行 Skill", description: `运行 ${skillName}`, status: "pending" as ExecutionStep["status"], icon: "play" },
      { id: "5", name: "结果处理", description: "处理执行结果", status: "pending" as ExecutionStep["status"], icon: "result" },
    ];
  };

  // 更新步骤状态
  const updateStepStatus = (
    steps: ExecutionStep[],
    stepId: string,
    status: ExecutionStep["status"],
    progress?: number
  ): ExecutionStep[] => {
    return steps.map((step) => {
      if (step.id === stepId) {
        return {
          ...step,
          status,
          progress,
          startTime: status === "running" ? Date.now() : step.startTime,
          endTime: status === "completed" || status === "failed" ? Date.now() : step.endTime,
        };
      }
      return step;
    });
  };

  const executeSkill = async (skillName: string, params: any) => {
    // 生成步骤
    const steps = generateExecutionSteps(skillName);

    // 添加带步骤的系统消息
    const systemMessage: ChatMessage = {
      conversationId,
      agentId,
      role: "assistant",
      content: `正在执行 Skill: ${skillName}...`,
      timestamp: Date.now(),
      mode: "skill",
      skills: [skillName],
      steps: steps,
    };
    await chatStore.add(systemMessage);
    setMessages((prev) => [...prev, systemMessage]);

    try {
      // 步骤 1: 参数解析
      let currentSteps = updateStepStatus(steps, "1", "running", 50);
      updateMessageSteps(systemMessage, currentSteps);
      await simulateDelay(300);
      currentSteps = updateStepStatus(currentSteps, "1", "completed", 100);
      updateMessageSteps(systemMessage, currentSteps);

      // 步骤 2: 权限检查
      currentSteps = updateStepStatus(currentSteps, "2", "running", 50);
      updateMessageSteps(systemMessage, currentSteps);
      await simulateDelay(400);
      currentSteps = updateStepStatus(currentSteps, "2", "completed", 100);
      updateMessageSteps(systemMessage, currentSteps);

      // 步骤 3: 环境准备
      currentSteps = updateStepStatus(currentSteps, "3", "running", 50);
      updateMessageSteps(systemMessage, currentSteps);
      await simulateDelay(500);
      currentSteps = updateStepStatus(currentSteps, "3", "completed", 100);
      updateMessageSteps(systemMessage, currentSteps);

      // 步骤 4: 执行 Skill
      currentSteps = updateStepStatus(currentSteps, "4", "running", 30);
      updateMessageSteps(systemMessage, currentSteps);

      const skillDef = await skillStore.get(skillName);
      const execution = await executeSkillApi(
        skillName,
        params ?? {},
        skillDef ? (skillDef as unknown as Record<string, unknown>) : undefined,
        conversationId
      );

      // 更新执行进度
      currentSteps = updateStepStatus(currentSteps, "4", "completed", 100);
      updateMessageSteps(systemMessage, currentSteps);

      if (onExecuteSkill) {
        onExecuteSkill(skillName, params);
      }

      // 步骤 5: 结果处理
      currentSteps = updateStepStatus(currentSteps, "5", "running", 50);
      updateMessageSteps(systemMessage, currentSteps);
      await simulateDelay(300);

      const body =
        execution.result && Object.keys(execution.result).length > 0
          ? execution.result
          : { message: execution.message, mode: execution.mode, error: execution.error ?? null };

      currentSteps = updateStepStatus(
        currentSteps,
        "5",
        execution.success ? "completed" : "failed",
        100
      );

      const resultMessage: ChatMessage = {
        conversationId,
        agentId,
        role: "assistant",
        content: `${execution.success ? "✅" : "❌"} Skill "${skillName}" ${execution.success ? "执行完成" : "执行失败"}！\n\n\`\`\`json\n${JSON.stringify(body, null, 2)}\n\`\`\``,
        timestamp: Date.now(),
        mode: execution.success ? "skill_result" : "skill_error",
        skills: [skillName],
        steps: currentSteps,
      };
      await chatStore.add(resultMessage);
      setMessages((prev) => [...prev, resultMessage]);

      if (!execution.success) {
        message.error(execution.error || execution.message || "Skill 执行失败");
      }
    } catch (error) {
      const failedSteps: ExecutionStep[] = steps.map((s) => ({
        ...s,
        status: (s.id === "4" ? "failed" : s.status === "completed" ? "completed" : "pending") as ExecutionStep["status"],
      }));

      const resultMessage: ChatMessage = {
        conversationId,
        agentId,
        role: "assistant",
        content: `❌ Skill "${skillName}" 执行失败：${String(error)}`,
        timestamp: Date.now(),
        mode: "skill_error",
        skills: [skillName],
        steps: failedSteps,
      };
      await chatStore.add(resultMessage);
      setMessages((prev) => [...prev, resultMessage]);
      message.error("Skill 执行失败: " + String(error));
    }
  };

  // 辅助函数：模拟延迟
  const simulateDelay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

  // 辅助函数：更新消息中的步骤
  const updateMessageSteps = async (message: ChatMessage, steps: ExecutionStep[]) => {
    const updatedMessage = { ...message, steps };
    await chatStore.update(updatedMessage);
    setMessages((prev) =>
      prev.map((m) => (m.timestamp === message.timestamp ? updatedMessage : m))
    );
  };


  const handleSkillSelect = (skill: AgentSkill) => {
    // 生成 Skill 调用命令
    const params = skill.parameters
      ? skill.parameters
          .filter((p) => p.required)
          .map((p) => `"${p.name}": "..."`)
          .join(", ")
      : "";
    const command = `/skill ${skill.name}${params ? ` {${params}}` : ""}`;
    setInput(command);
    setShowSkillPanel(false);
  };

  const clearChat = async () => {
    if (messages.length === 0) return;
    // 删除当前对话的所有消息
    for (const msg of messages) {
      if (msg.id) {
        await chatStore.delete(msg.id);
      }
    }
    setMessages([]);
    await loadSessions();
    message.success("对话已清空");
  };

  const newConversation = async () => {
    const createNewConversation = async () => {
      try {
        const created = await createConversation();
        return created.conversation_id;
      } catch (error) {
        console.error("Failed to create conversation", error);
        return `conv_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      }
    };

    const newId = await createNewConversation();
    setConversationId(newId);
    setMessages([]);
  };

  const switchConversation = (sessionId: string) => {
    setConversationId(sessionId);
  };

  const deleteSession = async (sessionId: string) => {
    // 删除该会话的所有消息
    const sessionMessages = await getConversationMessages(sessionId);
    for (const msg of sessionMessages) {
      if (msg.id) {
        await chatStore.delete(msg.id);
      }
    }
    await loadSessions();
    if (conversationId === sessionId) {
      newConversation();
    }
    message.success("会话已删除");
  };

  return (
    <Card
      className="ai-chat-card"
      bordered={false}
      title={
        <Space size={4}>
          <RobotOutlined />
          <span>AI 助手</span>
          {!config.llm.enabled && (
            <Tag color="warning">
              AI 未启用
            </Tag>
          )}
        </Space>
      }
      extra={
        <Space size={4}>
          <Tooltip title={isFullscreen ? "退出全屏" : "全屏"}>
            <Button
              type="text"
              size="small"
              icon={isFullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
              onClick={() => setIsFullscreen((prev) => !prev)}
            />
          </Tooltip>
          <Tooltip title="Skill 列表">
            <Button
              type={showSkillPanel ? "primary" : "text"}
              size="small"
              icon={<ToolOutlined />}
              onClick={() => setShowSkillPanel(!showSkillPanel)}
            />
          </Tooltip>
          <Tooltip title="新对话">
            <Button size="small" icon={<ThunderboltOutlined />} onClick={newConversation} />
          </Tooltip>
          <Tooltip title="清空">
            <Popconfirm
              title="确认清空当前会话？"
              description="清空后不可恢复。"
              okText="清空"
              cancelText="取消"
              okButtonProps={{ danger: true }}
              onConfirm={() => {
                void clearChat();
              }}
            >
              <Button size="small" icon={<ClearOutlined />} />
            </Popconfirm>
          </Tooltip>
        </Space>
      }
    >
      <div
        style={{
          display: "flex",
          gap: 12,
          height: isFullscreen ? "calc(100vh - 180px)" : "calc(100vh - 280px)",
          minHeight: 480,
        }}
      >
        {/* 左侧：对话历史 */}
        <div
          style={{
            width: 180,
            borderRight: "1px solid #f0f0f0",
            paddingRight: 12,
            display: "flex",
            flexDirection: "column",
            flexShrink: 0,
          }}
        >
          <Text type="secondary" style={{ marginBottom: 6, fontSize: 11, fontWeight: 500 }}>
            <HistoryOutlined /> 历史会话
          </Text>
          <div style={{ flex: 1, overflow: "auto" }}>
            {sessions.map((session) => (
              <div
                key={session.id}
                onClick={() => switchConversation(session.id)}
                style={{
                  padding: "6px 8px",
                  cursor: "pointer",
                  borderRadius: 4,
                  marginBottom: 4,
                  background: "transparent",
                  border:
                    session.id === conversationId
                      ? "1px solid #22c55e"
                      : "1px solid transparent",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: 4,
                }}
              >
                <div style={{ flex: 1, overflow: "hidden", minWidth: 0 }}>
                  <Text strong style={{ fontSize: 12 }} ellipsis>
                    {session.title}
                  </Text>
                  <br />
                  <Text type="secondary" style={{ fontSize: 10 }} ellipsis>
                    {session.lastMessage}
                  </Text>
                </div>
                <Popconfirm
                  title="确认删除该会话？"
                  description="删除后不可恢复。"
                  okText="删除"
                  cancelText="取消"
                  okButtonProps={{ danger: true }}
                  onConfirm={(e) => {
                    e?.stopPropagation?.();
                    void deleteSession(session.id);
                  }}
                  onCancel={(e) => e?.stopPropagation?.()}
                >
                  <Button
                    type="text"
                    size="small"
                    icon={<DeleteOutlined />}
                    onClick={(e) => e.stopPropagation()}
                    danger
                    style={{ padding: "0 4px", minWidth: 24, height: 24 }}
                  />
                </Popconfirm>
              </div>
            ))}
          </div>
        </div>

        {/* 中间：聊天区域 */}
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            minWidth: 0,
          }}
        >
          {/* 消息列表 */}
          <div
            style={{
              flex: 1,
              overflow: "auto",
              padding: "6px",
              background: "transparent",
              borderRadius: 4,
              marginBottom: 10,
            }}
          >
            {messages.length === 0 ? (
              <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <Empty
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description="开始对话吧！"
                />
              </div>
            ) : (
              <List
                dataSource={messages}
                renderItem={(msg) => (
                  <List.Item
                    style={{
                      justifyContent:
                        msg.role === "user" ? "flex-end" : "flex-start",
                      padding: "4px 0",
                    }}
                  >
                    <Space
                      align="start"
                      style={{
                        flexDirection: msg.role === "user" ? "row-reverse" : "row",
                        gap: "6px",
                      }}
                    >
                      <Avatar
                        size="small"
                        icon={msg.role === "user" ? <UserOutlined /> : <RobotOutlined />}
                        style={{
                          background: msg.role === "user" ? "#22c55e" : "#1677ff",
                          flexShrink: 0,
                        }}
                      />
                      <div
                        style={{
                          maxWidth: "85%",
                          minWidth: 120,
                          padding: "8px 12px",
                          borderRadius: 4,
                          background: "transparent",
                          border:
                            msg.role === "user"
                              ? "1px solid #bbf7d0"
                              : "1px solid #e5e7eb",
                          boxShadow: "0 1px 2px rgba(0,0,0,0.04)",
                        }}
                      >
                        {msg.skills && msg.skills.length > 0 && (
                          <div style={{ marginBottom: 3 }}>
                            {msg.skills.map((skill) => (
                              <Tag key={skill} color="blue" style={{ fontSize: 10, padding: "0 4px" }}>
                                <ToolOutlined /> {skill}
                              </Tag>
                            ))}
                          </div>
                        )}
                        <Paragraph style={{ margin: 0, whiteSpace: "pre-wrap", fontSize: 13, lineHeight: 1.5 }}>
                          {msg.content}
                        </Paragraph>
                        {/* 步骤流程展示 */}
                        {msg.steps && msg.steps.length > 0 && (
                          <ExecutionSteps steps={msg.steps} />
                        )}
                        {msg.mode && (
                          <Tag style={{ marginTop: 3, fontSize: 10, padding: "0 4px" }}>
                            {msg.mode}
                          </Tag>
                        )}
                      </div>
                    </Space>
                  </List.Item>
                )}
              />
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* 输入区域 */}
          <div style={{ position: "relative", flexShrink: 0 }}>
            {/* 自动补全下拉菜单 */}
            {showAutocomplete && (
              <div
                style={{
                  position: "absolute",
                  bottom: "100%",
                  left: 0,
                  right: 80,
                  marginBottom: 8,
                  background: "#fff",
                  borderRadius: 4,
                  boxShadow: "0 4px 20px rgba(0,0,0,0.15)",
                  border: "1px solid #e5e7eb",
                  maxHeight: 280,
                  overflow: "auto",
                  zIndex: 1000,
                }}
              >
                {/* 命令补全 */}
                {autocompleteType === "command" && (
                  <div>
                    <div
                      style={{
                        padding: "6px 12px",
                        background: "transparent",
                        borderBottom: "1px solid #f0f0f0",
                        fontSize: 11,
                        color: "#64748b",
                        fontWeight: 500,
                      }}
                    >
                      可用命令 ({filteredCommands.length})
                    </div>
                    {filteredCommands.map((cmd, index) => (
                      <div
                        key={cmd.name}
                        onClick={() => selectAutocompleteItem(index)}
                        style={{
                          padding: "8px 12px",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          gap: 10,
                          background: "transparent",
                          borderBottom: "1px solid #f8fafc",
                        }}
                        onMouseEnter={() => setSelectedIndex(index)}
                      >
                        <span style={{ color: "#22c55e", fontSize: 16 }}>{cmd.icon}</span>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            <Text strong style={{ fontSize: 13 }}>
                              /{cmd.name}
                            </Text>
                            <Text type="secondary" style={{ fontSize: 11 }}>
                              {cmd.description}
                            </Text>
                          </div>
                          {cmd.usage && (
                            <Text type="secondary" style={{ fontSize: 10 }} code>
                              {cmd.usage}
                            </Text>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* 技能补全 */}
                {autocompleteType === "skill" && (
                  <div>
                    <div
                      style={{
                        padding: "6px 12px",
                        background: "transparent",
                        borderBottom: "1px solid #f0f0f0",
                        fontSize: 11,
                        color: "#64748b",
                        fontWeight: 500,
                      }}
                    >
                      可用技能 ({filteredSkills.length})
                    </div>
                    {filteredSkills.map((skill, index) => (
                      <div
                        key={skill.name}
                        onClick={() => selectAutocompleteItem(index)}
                        style={{
                          padding: "8px 12px",
                          cursor: "pointer",
                          background: "transparent",
                          borderBottom: "1px solid #f8fafc",
                        }}
                        onMouseEnter={() => setSelectedIndex(index)}
                      >
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          <Tag color="blue" style={{ fontSize: 10 }}>
                            {skill.category}
                          </Tag>
                          <Text strong style={{ fontSize: 13 }}>
                            {skill.name}
                          </Text>
                        </div>
                        <Text type="secondary" style={{ fontSize: 11, marginLeft: 0 }}>
                          {skill.description}
                        </Text>
                        {skill.parameters && skill.parameters.length > 0 && (
                          <div style={{ marginTop: 2 }}>
                            {skill.parameters.slice(0, 3).map((param) => (
                              <Tag
                                key={param.name}
                                style={{
                                  fontSize: 9,
                                  padding: "0 4px",
                                  marginRight: 4,
                                  color: param.required ? "#dc2626" : "#64748b",
                                  borderColor: param.required ? "#fca5a5" : "#e5e7eb",
                                }}
                              >
                                {param.name}
                                {param.required && "*"}
                              </Tag>
                            ))}
                            {skill.parameters.length > 3 && (
                              <Text style={{ fontSize: 9, color: "#94a3b8" }}>
                                +{skill.parameters.length - 3}
                              </Text>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {/* 快捷键提示 */}
                <div
                  style={{
                    padding: "4px 12px",
                    background: "transparent",
                    borderTop: "1px solid #f0f0f0",
                    fontSize: 10,
                    color: "#94a3b8",
                    display: "flex",
                    gap: 12,
                  }}
                >
                  <span>↑↓ 选择</span>
                  <span>↵ 确认</span>
                  <span>Tab 补全</span>
                  <span>Esc 关闭</span>
                </div>
              </div>
            )}

            <div style={{ display: "flex", gap: 8, alignItems: "stretch" }}>
              <TextArea
                ref={textareaRef}
                value={input}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                placeholder="输入消息... 使用 / 查看命令"
                rows={2}
                style={{ flex: 1, resize: "none" }}
              />
              <Button
                type="primary"
                icon={loading ? <LoadingOutlined /> : <SendOutlined />}
                onClick={handleSend}
                loading={loading}
                style={{ height: "auto", minWidth: 56, fontSize: 12 }}
              >
                发送
              </Button>
            </div>

            {/* 快捷命令提示 */}
            <div style={{ marginTop: 4, fontSize: 10 }}>
              <Text type="secondary">
                可用命令: /skill | /help | /clear | /search | /scan | /github | /settings
              </Text>
            </div>
          </div>
        </div>

        {/* 右侧：Skill 面板 */}
        {showSkillPanel && (
          <div
            style={{
              width: 240,
              borderLeft: "1px solid #f0f0f0",
              paddingLeft: 12,
              overflow: "auto",
              flexShrink: 0,
            }}
          >
            <Text type="secondary" style={{ marginBottom: 6, fontSize: 11, fontWeight: 500 }}>
              <ToolOutlined /> 技能
            </Text>
            <SkillList
              onSkillClick={handleSkillSelect}
              showDisabled={false}
            />
          </div>
        )}
      </div>
    </Card>
  );
}

// 步骤流程展示组件
interface ExecutionStepsProps {
  steps: ExecutionStep[];
}

const ExecutionSteps: React.FC<ExecutionStepsProps> = ({ steps }) => {
  const getStepIcon = (icon: string, status: ExecutionStep["status"]) => {
    const iconStyle = { fontSize: 14 };
    const spin = status === "running";

    switch (icon) {
      case "tool":
        return spin ? <LoadingOutlined style={iconStyle} spin /> : <ToolOutlined style={iconStyle} />;
      case "shield":
        return spin ? <LoadingOutlined style={iconStyle} spin /> : <ApiOutlined style={iconStyle} />;
      case "setting":
        return spin ? <LoadingOutlined style={iconStyle} spin /> : <SettingOutlined style={iconStyle} />;
      case "play":
        return spin ? <LoadingOutlined style={iconStyle} spin /> : <PlayCircleOutlined style={iconStyle} />;
      case "result":
        return spin ? <LoadingOutlined style={iconStyle} spin /> : <DotChartOutlined style={iconStyle} />;
      default:
        return spin ? <LoadingOutlined style={iconStyle} spin /> : <CheckCircleOutlined style={iconStyle} />;
    }
  };

  const getStepColor = (status: ExecutionStep["status"]) => {
    switch (status) {
      case "completed":
        return "#22c55e";
      case "running":
        return "#3b82f6";
      case "failed":
        return "#ef4444";
      case "pending":
      default:
        return "#94a3b8";
    }
  };

  const completedCount = steps.filter((s) => s.status === "completed").length;
  const runningCount = steps.filter((s) => s.status === "running").length;
  const failedCount = steps.filter((s) => s.status === "failed").length;

  // 计算总进度
  const totalProgress = steps.reduce((sum, step) => {
    if (step.status === "completed") return sum + 100;
    if (step.status === "running") return sum + (step.progress || 50);
    return sum;
  }, 0) / steps.length;

  return (
    <div
      style={{
        marginTop: 12,
        padding: 12,
        background: "transparent",
        borderRadius: 4,
        border: "1px solid #bbf7d0",
      }}
    >
      {/* 总进度条 */}
      <div style={{ marginBottom: 12 }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 6,
          }}
        >
          <Text style={{ fontSize: 11, fontWeight: 600, color: "#166534" }}>
            <BranchesOutlined /> 执行进度
          </Text>
          <Text style={{ fontSize: 10, color: "#22c55e" }}>
            {completedCount}/{steps.length} 完成
            {failedCount > 0 && ` · ${failedCount} 失败`}
            {runningCount > 0 && ` · ${runningCount} 进行中`}
          </Text>
        </div>
        <div
          style={{
            height: 4,
            background: "#e2e8f0",
            borderRadius: 2,
            overflow: "hidden",
          }}
        >
          <div
            style={{
              height: "100%",
              width: `${totalProgress}%`,
              background: failedCount > 0
                ? "linear-gradient(90deg, #22c55e, #f59e0b)"
                : "linear-gradient(90deg, #22c55e, #4ade80)",
              borderRadius: 2,
              transition: "width 0.5s ease",
            }}
          />
        </div>
      </div>

      {/* 步骤列表 */}
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {steps.map((step, index) => {
          const isLast = index === steps.length - 1;
          const color = getStepColor(step.status);

          return (
            <div key={step.id} style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
              {/* 步骤图标 */}
              <div
                style={{
                  width: 24,
                  height: 24,
                  borderRadius: "50%",
                  background: step.status === "pending" ? "#f1f5f9" : `${color}15`,
                  border: `2px solid ${step.status === "pending" ? "#cbd5e1" : color}`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                  color: step.status === "pending" ? "#94a3b8" : color,
                  transition: "all 0.3s ease",
                }}
              >
                {step.status === "completed" ? (
                  <CheckOutlined style={{ fontSize: 12, fontWeight: "bold" }} />
                ) : step.status === "failed" ? (
                  <CloseCircleOutlined style={{ fontSize: 12 }} />
                ) : (
                  getStepIcon(step.icon || "", step.status)
                )}
              </div>

              {/* 步骤内容 */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <Text
                    style={{
                      fontSize: 12,
                      fontWeight: step.status === "running" ? 600 : 500,
                      color: step.status === "pending" ? "#64748b" : "#1e293b",
                    }}
                  >
                    {step.name}
                  </Text>
                  {step.status === "running" && (
                    <Tag
                      color="processing"
                      style={{
                        fontSize: 9,
                        padding: "0 4px",
                        height: 16,
                        lineHeight: "14px",
                      }}
                    >
                      进行中
                    </Tag>
                  )}
                  {step.status === "failed" && (
                    <Tag
                      color="error"
                      style={{
                        fontSize: 9,
                        padding: "0 4px",
                        height: 16,
                        lineHeight: "14px",
                      }}
                    >
                      失败
                    </Tag>
                  )}
                </div>
                {step.description && step.status !== "pending" && (
                  <Text style={{ fontSize: 10, color: "#64748b", display: "block" }}>
                    {step.description}
                  </Text>
                )}

                {/* 子步骤 */}
                {step.subSteps && step.subSteps.length > 0 && step.status !== "pending" && (
                  <div style={{ marginTop: 6, paddingLeft: 12 }}>
                    {step.subSteps.map((subStep) => (
                      <div
                        key={subStep.id}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 6,
                          marginBottom: 4,
                        }}
                      >
                        <div
                          style={{
                            width: 6,
                            height: 6,
                            borderRadius: "50%",
                            background: getStepColor(subStep.status),
                          }}
                        />
                        <Text style={{ fontSize: 10, color: "#64748b" }}>
                          {subStep.name}
                        </Text>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* 时间戳 */}
              {step.status === "completed" && step.endTime && step.startTime && (
                <Text style={{ fontSize: 9, color: "#94a3b8", flexShrink: 0 }}>
                  {((step.endTime - step.startTime) / 1000).toFixed(1)}s
                </Text>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
