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
  RocketOutlined,
  StarOutlined,
  MessageOutlined,
  SearchOutlined,
  BulbOutlined,
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

  // 处理示例对话点击
  const handleExampleClick = (exampleText: string) => {
    setInput(exampleText);
    // 使用 setTimeout 确保输入已更新后再发送
    setTimeout(() => {
      handleSend();
    }, 100);
  };

  // 生成示例卡片数据 - 使用玻璃拟态设计
  const exampleCards = useMemo(() => [
    {
      id: "web3",
      title: "Web3 空投项目搜索",
      description: "搜索适合贡献的 Web3 项目",
      icon: <RocketOutlined />,
      color: "#22c55e",
      bgGradient: "linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%)",
      query: "搜索一些适合贡献的 Web3 项目",
    },
    {
      id: "typo",
      title: "扫描代码拼写错误",
      description: "检测指定仓库的 typo 问题",
      icon: <SearchOutlined />,
      color: "#3b82f6",
      bgGradient: "linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%)",
      query: "扫描 ethereum/solidity 仓库的 typo",
    },
    {
      id: "github",
      title: "搜索热门项目",
      description: "按条件查找 GitHub 仓库",
      icon: <StarOutlined />,
      color: "#8b5cf6",
      bgGradient: "linear-gradient(135deg, #ede9fe 0%, #ddd6fe 100%)",
      query: "帮我找一些 stars 数超过 1000 的 Python 项目",
    },
    {
      id: "chat",
      title: "AI 咨询",
      description: "询问开源贡献相关问题",
      icon: <MessageOutlined />,
      color: "#f59e0b",
      bgGradient: "linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)",
      query: "如何参与开源项目的 typo 修复？",
    },
  ], []);

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
    if (!input.trim()) return;

    const content = input.trim();
    setInput("");
    setShowAutocomplete(false);
    setLoading(true);

    // 确保有有效的 conversation
    let currentConversationId = conversationId;
    if (!currentConversationId) {
      try {
        const created = await createConversation();
        currentConversationId = created.conversation_id;
        setConversationId(currentConversationId);
      } catch (error) {
        message.error("创建会话失败: " + String(error));
        setLoading(false);
        return;
      }
    }

    // 保存用户消息
    const userMessage: ChatMessage = {
      conversationId: currentConversationId,
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
        let reply;
        try {
          reply = await sendChatMessage(currentConversationId, content);
        } catch (error: any) {
          // 如果是 conversation not found，尝试重新创建会话并重试
          if (error.message?.includes("conversation not found")) {
            const created = await createConversation();
            currentConversationId = created.conversation_id;
            setConversationId(currentConversationId);
            // 使用新的 conversation ID 重试
            reply = await sendChatMessage(currentConversationId, content);
            // 更新用户消息的 conversation ID
            userMessage.conversationId = currentConversationId;
          } else {
            throw error;
          }
        }
        const aiMessage: ChatMessage = {
          conversationId: currentConversationId,
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
      style={{
        borderRadius: 12,
        background: "#ffffff",
        boxShadow: "0 1px 3px rgba(0,0,0,0.05), 0 1px 2px rgba(0,0,0,0.03)",
        border: "1px solid #e5e7eb",
      }}
      title={
        <Space size={10}>
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 10,
              background: "#22c55e",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <RobotOutlined style={{ color: "#fff", fontSize: 18 }} />
          </div>
          <span style={{ fontWeight: 600, fontSize: 16, color: "#111827" }}>AI 助手</span>
          {!config.llm.enabled && (
            <Tag color="warning" style={{ borderRadius: 4, fontSize: 11, fontWeight: 500 }}>
              AI 未启用
            </Tag>
          )}
        </Space>
      }
      extra={
        <Space size={6}>
          <Tooltip title={isFullscreen ? "退出全屏" : "全屏"}>
            <Button
              type="text"
              size="small"
              icon={isFullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
              onClick={() => setIsFullscreen((prev) => !prev)}
              style={{ borderRadius: 8, width: 32, height: 32 }}
            />
          </Tooltip>
          <Tooltip title="Skill 列表">
            <Button
              type={showSkillPanel ? "primary" : "text"}
              size="small"
              icon={<ToolOutlined />}
              onClick={() => setShowSkillPanel(!showSkillPanel)}
              style={{ borderRadius: 8, width: 32, height: 32 }}
            />
          </Tooltip>
          <Tooltip title="新对话">
            <Button
              size="small"
              icon={<ThunderboltOutlined />}
              onClick={newConversation}
              style={{ borderRadius: 8, width: 32, height: 32 }}
            />
          </Tooltip>
          <Tooltip title="清空">
            <Popconfirm
              title="确认清空当前会话？"
              description="清空后不可恢复。"
              okText="清空"
              cancelText="取消"
              okButtonProps={{ danger: true }}
              onConfirm={() => { void clearChat(); }}
            >
              <Button
                size="small"
                icon={<ClearOutlined />}
                danger
                style={{ borderRadius: 8, width: 32, height: 32 }}
              />
            </Popconfirm>
          </Tooltip>
        </Space>
      }
    >
      <div
        style={{
          display: "flex",
          gap: 16,
          height: isFullscreen ? "calc(100vh - 180px)" : "calc(100vh - 280px)",
          minHeight: 480,
        }}
      >
        {/* 左侧：对话历史 - 扁平化风格 */}
        <div
          style={{
            width: 220,
            borderRight: "1px solid #e5e7eb",
            paddingRight: 16,
            display: "flex",
            flexDirection: "column",
            flexShrink: 0,
          }}
        >
          <div style={{
            marginBottom: 16,
            fontSize: 12,
            fontWeight: 600,
            color: "#6b7280",
            letterSpacing: "0.3px",
            textTransform: "uppercase",
            display: "flex",
            alignItems: "center",
            gap: 8,
            padding: "10px 12px",
            background: "#f9fafb",
            borderRadius: 8,
            border: "1px solid #e5e7eb",
          }}>
            <HistoryOutlined style={{ fontSize: 14, color: "#6b7280" }} /> 历史会话
          </div>
          <div style={{ flex: 1, overflow: "auto", padding: "0 4px" }}>
            {sessions.map((session) => (
              <div
                key={session.id}
                onClick={() => switchConversation(session.id)}
                style={{
                  padding: "12px 14px",
                  cursor: "pointer",
                  borderRadius: 8,
                  marginBottom: 6,
                  background: session.id === conversationId
                    ? "#dcfce7"
                    : "transparent",
                  border: session.id === conversationId
                    ? "1px solid #86efac"
                    : "1px solid transparent",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: 10,
                  transition: "all 0.15s ease",
                }}
                className="session-item-flat"
              >
                <div style={{ flex: 1, overflow: "hidden", minWidth: 0 }}>
                  <Text strong style={{ fontSize: 13, color: session.id === conversationId ? "#166534" : "#111827", display: "block" }} ellipsis>
                    {session.title}
                  </Text>
                  <Text style={{ fontSize: 11, color: session.id === conversationId ? "#16a34a" : "#9ca3af", marginTop: 2 }} ellipsis>
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
                    style={{
                      padding: "4px 8px",
                      minWidth: 28,
                      height: 28,
                      borderRadius: 6,
                      opacity: 0,
                      transition: "all 0.15s ease",
                    }}
                    className="session-delete-btn-flat"
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
              <div
                style={{
                  height: "100%",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  padding: 32,
                }}
              >
                {/* 扁平化风格 Empty 状态 */}
                <div
                  style={{
                    padding: "32px 40px",
                    borderRadius: 12,
                    background: "#ffffff",
                    border: "1px solid #e5e7eb",
                    boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
                    textAlign: "center",
                    maxWidth: 480,
                    width: "100%",
                  }}
                >
                  <div
                    style={{
                      width: 64,
                      height: 64,
                      borderRadius: "50%",
                      background: "#22c55e",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      margin: "0 auto 16px",
                    }}
                  >
                    <RobotOutlined style={{ fontSize: 28, color: "#fff" }} />
                  </div>
                  <Title level={4} style={{ marginBottom: 8, color: "#111827", fontWeight: 600 }}>
                    开始对话
                  </Title>
                  <Text style={{ fontSize: 14, color: "#6b7280", lineHeight: 1.6 }}>
                    我是 Typo Master AI 助手，可以帮助您搜索 GitHub 项目、<br />
                    扫描代码 typo、管理 Web3 空投任务等。
                  </Text>
                </div>

                {/* 示例卡片区域 - 扁平化 */}
                <div style={{ marginTop: 28, width: "100%", maxWidth: 680 }}>
                  <div style={{ textAlign: "center", marginBottom: 16 }}>
                    <div
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 6,
                        padding: "4px 12px",
                        borderRadius: 6,
                        background: "#f3f4f6",
                        border: "1px solid #e5e7eb",
                      }}
                    >
                      <BulbOutlined style={{ color: "#22c55e", fontSize: 14 }} />
                      <Text style={{ fontSize: 12, color: "#374151", fontWeight: 500 }}>
                        快速开始，选择一个示例
                      </Text>
                    </div>
                  </div>

                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
                      gap: 12,
                    }}
                  >
                    {exampleCards.map((card) => (
                      <div
                        key={card.id}
                        onClick={() => handleExampleClick(card.query)}
                        style={{
                          cursor: "pointer",
                          padding: 16,
                          borderRadius: 10,
                          background: "#ffffff",
                          border: "1px solid #e5e7eb",
                          boxShadow: "0 1px 2px rgba(0,0,0,0.03)",
                          transition: "all 0.15s ease",
                          display: "flex",
                          alignItems: "flex-start",
                          gap: 12,
                        }}
                        className="example-card-flat"
                      >
                        <div
                          style={{
                            width: 40,
                            height: 40,
                            borderRadius: 8,
                            background: card.color + "15",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            flexShrink: 0,
                          }}
                        >
                          <span style={{ color: card.color, fontSize: 18 }}>{card.icon}</span>
                        </div>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <Text
                            strong
                            style={{
                              display: "block",
                              fontSize: 13,
                              color: "#111827",
                              marginBottom: 2,
                              fontWeight: 600,
                            }}
                          >
                            {card.title}
                          </Text>
                          <Text
                            style={{
                              fontSize: 11,
                              color: "#6b7280",
                              lineHeight: 1.4,
                            }}
                          >
                            {card.description}
                          </Text>
                        </div>
                        <ArrowRightOutlined
                          style={{
                            color: "#9ca3af",
                            fontSize: 12,
                            flexShrink: 0,
                            marginTop: 4,
                          }}
                        />
                      </div>
                    ))}
                  </div>
                </div>
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
                          background: msg.role === "user"
                            ? "#22c55e"
                            : "#3b82f6",
                          flexShrink: 0,
                        }}
                      />
                      <div
                        style={{
                          maxWidth: "85%",
                          minWidth: 120,
                          padding: "10px 14px",
                          borderRadius: msg.role === "user" ? "12px 12px 2px 12px" : "12px 12px 12px 2px",
                          background: msg.role === "user"
                            ? "#22c55e"
                            : "#f3f4f6",
                          border: msg.role === "user"
                            ? "none"
                            : "1px solid #e5e7eb",
                        }}
                      >
                        {msg.skills && msg.skills.length > 0 && (
                          <div style={{ marginBottom: 6 }}>
                            {msg.skills.map((skill) => (
                              <Tag key={skill} style={{
                                fontSize: 10,
                                padding: "2px 8px",
                                background: "#dbeafe",
                                border: "1px solid #bfdbfe",
                                color: "#1d4ed8",
                                borderRadius: 4,
                              }}>
                                <ToolOutlined /> {skill}
                              </Tag>
                            ))}
                          </div>
                        )}
                        <Paragraph style={{
                          margin: 0,
                          whiteSpace: "pre-wrap",
                          fontSize: 14,
                          lineHeight: 1.5,
                          color: msg.role === "user" ? "#fff" : "#111827",
                        }}>
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

            {/* AI 思考中提示 - 扁平化设计 */}
            {loading && (
              <List.Item
                style={{
                  justifyContent: "flex-start",
                  padding: "8px 0",
                }}
              >
                <Space
                  align="start"
                  style={{
                    flexDirection: "row",
                    gap: "10px",
                  }}
                >
                  <Avatar
                    size="small"
                    icon={<RobotOutlined />}
                    style={{
                      background: "linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)",
                      flexShrink: 0,
                      boxShadow: "0 0 12px rgba(99, 102, 241, 0.4)",
                    }}
                  />
                  <div
                    style={{
                      maxWidth: "85%",
                      minWidth: 160,
                      padding: "12px 16px",
                      borderRadius: 16,
                      background: "linear-gradient(135deg, #1e1b4b 0%, #312e81 100%)",
                      border: "1px solid rgba(99, 102, 241, 0.3)",
                      boxShadow: "0 4px 20px rgba(99, 102, 241, 0.2), inset 0 1px 0 rgba(255,255,255,0.05)",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                      {/* Neural Quantum 动画 */}
                      <div className="ai-thinking-indicator">
                        <div className="ai-thinking-core"></div>
                        <div className="ai-thinking-ring-inner"></div>
                        <div className="ai-thinking-ring-outer"></div>
                      </div>
                      <span className="ai-thinking-text">AI 思考中</span>
                    </div>
                  </div>
                </Space>
              </List.Item>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* 输入区域 */}
          <div style={{ position: "relative", flexShrink: 0 }}>
            {/* 自动补全下拉菜单 - 扁平化风格 */}
            {showAutocomplete && (
              <div
                style={{
                  position: "absolute",
                  bottom: "100%",
                  left: 0,
                  right: 80,
                  marginBottom: 8,
                  background: "#ffffff",
                  borderRadius: 10,
                  boxShadow: "0 10px 25px rgba(0,0,0,0.1), 0 2px 8px rgba(0,0,0,0.05)",
                  border: "1px solid #e5e7eb",
                  maxHeight: 300,
                  overflow: "auto",
                  zIndex: 1000,
                }}
              >
                {/* 命令补全 */}
                {autocompleteType === "command" && (
                  <div>
                    <div
                      style={{
                        padding: "10px 16px",
                        background: "transparent",
                        borderBottom: "1px solid rgba(226,232,240,0.6)",
                        fontSize: 11,
                        color: "#64748b",
                        fontWeight: 600,
                        letterSpacing: "0.3px",
                        textTransform: "uppercase",
                      }}
                    >
                      可用命令 ({filteredCommands.length})
                    </div>
                    {filteredCommands.map((cmd, index) => (
                      <div
                        key={cmd.name}
                        onClick={() => selectAutocompleteItem(index)}
                        style={{
                          padding: "12px 16px",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          gap: 12,
                          background: index === selectedIndex ? "rgba(34,197,94,0.08)" : "transparent",
                          borderBottom: "1px solid rgba(241,245,249,0.6)",
                          transition: "all 0.15s ease",
                        }}
                        onMouseEnter={() => setSelectedIndex(index)}
                      >
                        <span style={{
                          color: "#22c55e",
                          fontSize: 18,
                          width: 28,
                          height: 28,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          borderRadius: 8,
                          background: "rgba(34,197,94,0.1)",
                        }}>{cmd.icon}</span>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 2 }}>
                            <Text strong style={{ fontSize: 14, color: "#1e293b" }}>
                              /{cmd.name}
                            </Text>
                            <Text style={{ fontSize: 12, color: "#64748b" }}>
                              {cmd.description}
                            </Text>
                          </div>
                          {cmd.usage && (
                            <code style={{
                              fontSize: 11,
                              padding: "2px 6px",
                              borderRadius: 4,
                              background: "rgba(34,197,94,0.08)",
                              color: "#166534",
                            }}>
                              {cmd.usage}
                            </code>
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
                        padding: "10px 16px",
                        background: "transparent",
                        borderBottom: "1px solid rgba(226,232,240,0.6)",
                        fontSize: 11,
                        color: "#64748b",
                        fontWeight: 600,
                        letterSpacing: "0.3px",
                        textTransform: "uppercase",
                      }}
                    >
                      可用技能 ({filteredSkills.length})
                    </div>
                    {filteredSkills.map((skill, index) => (
                      <div
                        key={skill.name}
                        onClick={() => selectAutocompleteItem(index)}
                        style={{
                          padding: "12px 16px",
                          cursor: "pointer",
                          background: index === selectedIndex ? "rgba(34,197,94,0.08)" : "transparent",
                          borderBottom: "1px solid rgba(241,245,249,0.6)",
                          transition: "all 0.15s ease",
                        }}
                        onMouseEnter={() => setSelectedIndex(index)}
                      >
                        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                          <span style={{
                            fontSize: 11,
                            padding: "2px 8px",
                            borderRadius: 6,
                            background: "rgba(59,130,246,0.1)",
                            color: "#2563eb",
                            fontWeight: 500,
                          }}>
                            {skill.category}
                          </span>
                          <Text strong style={{ fontSize: 14, color: "#1e293b" }}>
                            {skill.name}
                          </Text>
                        </div>
                        <Text style={{ fontSize: 12, color: "#64748b", marginTop: 4, display: "block" }}>
                          {skill.description}
                        </Text>
                        {skill.parameters && skill.parameters.length > 0 && (
                          <div style={{ marginTop: 6, display: "flex", flexWrap: "wrap", gap: 4 }}>
                            {skill.parameters.slice(0, 3).map((param) => (
                              <span
                                key={param.name}
                                style={{
                                  fontSize: 10,
                                  padding: "2px 8px",
                                  borderRadius: 4,
                                  background: param.required ? "rgba(239,68,68,0.08)" : "rgba(148,163,184,0.1)",
                                  color: param.required ? "#dc2626" : "#64748b",
                                  border: param.required ? "1px solid rgba(239,68,68,0.2)" : "1px solid rgba(148,163,184,0.2)",
                                }}
                              >
                                {param.name}
                                {param.required && <span style={{ color: "#dc2626" }}>*</span>}
                              </span>
                            ))}
                            {skill.parameters.length > 3 && (
                              <span style={{ fontSize: 10, color: "#94a3b8" }}>
                                +{skill.parameters.length - 3}
                              </span>
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
                    padding: "10px 16px",
                    background: "rgba(248,250,252,0.8)",
                    borderTop: "1px solid rgba(226,232,240,0.6)",
                    fontSize: 11,
                    color: "#94a3b8",
                    display: "flex",
                    gap: 16,
                    fontWeight: 500,
                  }}
                >
                  <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                    <kbd style={{
                      padding: "2px 6px",
                      borderRadius: 4,
                      background: "#fff",
                      border: "1px solid #e2e8f0",
                      fontSize: 10,
                      fontFamily: "monospace",
                    }}>↑↓</kbd> 选择
                  </span>
                  <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                    <kbd style={{
                      padding: "2px 6px",
                      borderRadius: 4,
                      background: "#fff",
                      border: "1px solid #e2e8f0",
                      fontSize: 10,
                      fontFamily: "monospace",
                    }}>↵</kbd> 确认
                  </span>
                  <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                    <kbd style={{
                      padding: "2px 6px",
                      borderRadius: 4,
                      background: "#fff",
                      border: "1px solid #e2e8f0",
                      fontSize: 10,
                      fontFamily: "monospace",
                    }}>Tab</kbd> 补全
                  </span>
                  <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                    <kbd style={{
                      padding: "2px 6px",
                      borderRadius: 4,
                      background: "#fff",
                      border: "1px solid #e2e8f0",
                      fontSize: 10,
                      fontFamily: "monospace",
                    }}>Esc</kbd> 关闭
                  </span>
                </div>
              </div>
            )}

            <div style={{ display: "flex", gap: 10, alignItems: "stretch" }}>
              <TextArea
                ref={textareaRef}
                value={input}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                placeholder="输入消息... 使用 / 查看命令"
                rows={2}
                style={{
                  flex: 1,
                  resize: "none",
                  borderRadius: 10,
                  border: "1px solid #d1d5db",
                  background: "#ffffff",
                  padding: "10px 14px",
                  fontSize: 14,
                  lineHeight: 1.5,
                  transition: "all 0.15s ease",
                }}
              />
              <Button
                type="primary"
                icon={loading ? <LoadingOutlined /> : <SendOutlined />}
                onClick={handleSend}
                loading={loading}
                disabled={!input.trim()}
                style={{
                  height: "auto",
                  minWidth: 56,
                  fontSize: 13,
                  borderRadius: 10,
                  background: "linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)",
                  border: "none",
                  boxShadow: "0 4px 14px rgba(99, 102, 241, 0.4)",
                  transition: "all 0.2s ease",
                }}
              >
                发送
              </Button>
            </div>

            {/* 快捷命令提示 */}
            <div style={{ marginTop: 8, fontSize: 11 }}>
              <Text style={{ color: "#9ca3af" }}>
                可用命令:{" "}
                <code style={{ padding: "1px 4px", borderRadius: 4, background: "#f3f4f6", color: "#374151", fontSize: 10 }}>/skill</code>{" "}
                <code style={{ padding: "1px 4px", borderRadius: 4, background: "#f3f4f6", color: "#374151", fontSize: 10 }}>/help</code>{" "}
                <code style={{ padding: "1px 4px", borderRadius: 4, background: "#f3f4f6", color: "#374151", fontSize: 10 }}>/clear</code>{" "}
                <code style={{ padding: "1px 4px", borderRadius: 4, background: "#f3f4f6", color: "#374151", fontSize: 10 }}>/settings</code>
              </Text>
            </div>
          </div>
        </div>

        {/* 右侧：Skill 面板 - 扁平化风格 */}
        {showSkillPanel && (
          <div
            style={{
              width: 260,
              borderLeft: "1px solid #e5e7eb",
              paddingLeft: 16,
              overflow: "auto",
              flexShrink: 0,
            }}
          >
            <div style={{
              marginBottom: 12,
              fontSize: 11,
              fontWeight: 600,
              color: "#6b7280",
              letterSpacing: "0.3px",
              textTransform: "uppercase",
              display: "flex",
              alignItems: "center",
              gap: 6,
              padding: "8px 12px",
              background: "#f9fafb",
              borderRadius: 6,
              border: "1px solid #e5e7eb",
            }}>
              <ToolOutlined style={{ fontSize: 14, color: "#6b7280" }} /> 技能
            </div>
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
