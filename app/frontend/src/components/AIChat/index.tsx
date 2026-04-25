import { useEffect, useState, useRef, useCallback, useMemo } from "react";
import {
  Card,
  Input,
  Button,
  Tag,
  Typography,
  Space,
  Tooltip,
  Popconfirm,
  message,
} from "antd";
import {
  SendOutlined,
  RobotOutlined,
  ClearOutlined,
  ToolOutlined,
  ThunderboltOutlined,
  LoadingOutlined,
  FullscreenOutlined,
  FullscreenExitOutlined,
  SettingOutlined,
  QuestionCircleOutlined,
} from "@ant-design/icons";
import { chatStore, getConversationMessages, skillStore, type ChatMessage, type ExecutionStep } from "../../db";
import { createConversation, sendChatMessage, executeSkill as executeSkillApi } from "../../api";
import { useConfig } from "../../config";
import { useAuth } from "../../contexts/AuthContext";
import SkillList from "../SkillList";
import LoginModal from "../LoginModal";
import type { AgentSkill } from "../../db";

// Extracted sub-components
import ChatEmptyState from "./ChatEmptyState";
import AutocompleteDropdown, { type SlashCommand, type AutocompleteType } from "./AutocompleteDropdown";
import SessionSidebar, { type ChatSession } from "./SessionSidebar";
import MessageList from "./MessageList";

const { Text } = Typography;
const { TextArea } = Input;

interface AIChatProps {
  agentId?: string;
  onExecuteSkill?: (skill: string, params: any) => void;
}

const BASE_COMMANDS: SlashCommand[] = [
  { name: "skill", description: "执行 Agent Skill", icon: <ToolOutlined />, usage: "/skill <skill_name> [params]" },
  { name: "help", description: "显示帮助信息", icon: <QuestionCircleOutlined />, usage: "/help" },
  { name: "clear", description: "清空当前对话", icon: <ClearOutlined />, usage: "/clear" },
  { name: "settings", description: "查看当前配置", icon: <SettingOutlined />, usage: "/settings" },
];

const generateDynamicCommands = (skills: AgentSkill[]): SlashCommand[] => {
  return skills
    .filter(s => ["search_github_repos", "scan_typo", "fix_typo", "get_github_repo"].includes(s.name))
    .map(skill => ({
      name: skill.name.replace(/_/g, ""),
      description: skill.description,
      icon: <ToolOutlined />,
      usage: `/${skill.name.replace(/_/g, "")} ${skill.parameters?.filter(p => p.required).map(p => p.name).join(" ") || ""}`,
    }));
};

export default function AIChat({ agentId = "default", onExecuteSkill }: AIChatProps) {
  const { config } = useConfig();
  const { authenticated } = useAuth();
  const [loginModalOpen, setLoginModalOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string>("");
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [showSkillPanel, setShowSkillPanel] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [historyCollapsed, setHistoryCollapsed] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Autocomplete state
  const [showAutocomplete, setShowAutocomplete] = useState(false);
  const [autocompleteType, setAutocompleteType] = useState<AutocompleteType>(null);
  const [filteredCommands, setFilteredCommands] = useState<SlashCommand[]>([]);
  const [filteredSkills, setFilteredSkills] = useState<AgentSkill[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [availableSkills, setAvailableSkills] = useState<AgentSkill[]>([]);

  const SLASH_COMMANDS = useMemo(() => [...BASE_COMMANDS, ...generateDynamicCommands(availableSkills)], [availableSkills]);

  const exampleCards = useMemo(() => [
    { id: "web3", title: "Web3 空投项目搜索", description: "搜索适合贡献的 Web3 项目", icon: "🚀", color: "#22c55e", query: "搜索一些适合贡献的 Web3 项目" },
    { id: "typo", title: "扫描代码拼写错误", description: "检测指定仓库的 typo 问题", icon: "🔍", color: "#3b82f6", query: "扫描 ethereum/solidity 仓库的 typo" },
    { id: "github", title: "搜索热门项目", description: "按条件查找 GitHub 仓库", icon: "⭐", color: "#8b5cf6", query: "帮我找一些 stars 数超过 1000 的 Python 项目" },
    { id: "chat", title: "AI 咨询", description: "询问开源贡献相关问题", icon: "💬", color: "#f59e0b", query: "如何参与开源项目的 typo 修复？" },
  ], []);

  // --- Effects ---
  useEffect(() => {
    const loadSkills = async () => {
      const skills = await skillStore.getAll();
      setAvailableSkills(skills.filter(s => s.enabled));
    };
    loadSkills();
  }, []);

  useEffect(() => {
    const init = async () => {
      try {
        const created = await createConversation();
        setConversationId(created.conversation_id);
      } catch {
        setConversationId(`conv_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`);
      }
      await loadSessions();
    };
    init();
  }, []);

  useEffect(() => {
    if (conversationId) loadMessages();
  }, [conversationId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // --- Session management ---
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
    setSessions(Array.from(sessionsMap.values()).sort((a, b) => b.timestamp - a.timestamp));
  };

  const loadMessages = async () => {
    if (!conversationId) return;
    const msgs = await getConversationMessages(conversationId);
    setMessages(msgs);
  };

  const switchConversation = (sessionId: string) => setConversationId(sessionId);

  const deleteSession = async (sessionId: string) => {
    const sessionMessages = await getConversationMessages(sessionId);
    for (const msg of sessionMessages) {
      if (msg.id) await chatStore.delete(msg.id);
    }
    await loadSessions();
    if (conversationId === sessionId) newConversation();
    message.success("会话已删除");
  };

  const newConversation = async () => {
    try {
      const created = await createConversation();
      setConversationId(created.conversation_id);
    } catch {
      setConversationId(`conv_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`);
    }
    setMessages([]);
  };

  const clearChat = async () => {
    if (messages.length === 0) return;
    for (const msg of messages) {
      if (msg.id) await chatStore.delete(msg.id);
    }
    setMessages([]);
    await loadSessions();
    message.success("对话已清空");
  };

  // --- Autocomplete ---
  const updateAutocomplete = useCallback((value: string, cursorPos: number) => {
    const textBeforeCursor = value.slice(0, cursorPos);
    const commandMatch = textBeforeCursor.match(/^\/([a-zA-Z_]*)$/);
    if (commandMatch) {
      const query = commandMatch[1].toLowerCase();
      setFilteredCommands(SLASH_COMMANDS.filter(cmd => cmd.name.toLowerCase().startsWith(query)));
      setAutocompleteType("command");
      setShowAutocomplete(true);
      setSelectedIndex(0);
      return;
    }
    const skillMatch = textBeforeCursor.match(/^\/skill\s+([a-zA-Z0-9_:-]*)$/i);
    if (skillMatch) {
      const query = skillMatch[1].toLowerCase();
      setFilteredSkills(availableSkills.filter(skill => skill.name.toLowerCase().includes(query)));
      setAutocompleteType("skill");
      setShowAutocomplete(true);
      setSelectedIndex(0);
      return;
    }
    setShowAutocomplete(false);
    setAutocompleteType(null);
  }, [SLASH_COMMANDS, availableSkills]);

  const selectAutocompleteItem = (index: number) => {
    if (autocompleteType === "command") {
      const command = filteredCommands[index];
      setInput(`/${command.name} `);
      setShowAutocomplete(false);
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
      const params = skill.parameters?.filter(p => p.required).map(p => `"${p.name}": "..."`).join(", ");
      setInput(`/skill ${skill.name}${params ? ` {${params}}` : ""}`);
      setShowAutocomplete(false);
    }
    setTimeout(() => textareaRef.current?.focus(), 0);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    updateAutocomplete(e.target.value, e.target.selectionStart);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (!showAutocomplete) {
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
        setSelectedIndex(prev => (prev + 1) % items.length);
        break;
      case "ArrowUp":
        e.preventDefault();
        setSelectedIndex(prev => (prev - 1 + items.length) % items.length);
        break;
      case "Enter":
      case "Tab":
        e.preventDefault();
        selectAutocompleteItem(selectedIndex);
        break;
      case "Escape":
        e.preventDefault();
        setShowAutocomplete(false);
        break;
    }
  };

  // --- Messages ---
  const addSystemMessage = async (content: string) => {
    const m: ChatMessage = {
      conversationId, agentId, role: "assistant", content, timestamp: Date.now(), mode: "system",
    };
    await chatStore.add(m);
    setMessages(prev => [...prev, m]);
  };

  const showHelpMessage = async () => {
    await addSystemMessage(`📚 **可用命令列表**\n\n${SLASH_COMMANDS.map(cmd => `\n**/${cmd.name}** - ${cmd.description}\n${cmd.usage ? `\`\`\`${cmd.usage}\`\`\`` : ""}`).join("\n")}\n\n💡 **提示**\n- 输入 "/" 查看所有可用命令\n- 输入 "/skill " 查看所有可用技能\n- 使用 ↑↓ 选择，↵ 或 Tab 确认，Esc 关闭`);
  };

  const showSettingsMessage = async () => {
    await addSystemMessage(`⚙️ **当前配置**\n\n| 配置项 | 状态 |\n|--------|------|\n| AI 功能 | ${config.llm.enabled ? "✅ 已启用" : "❌ 未启用"} |\n| 模型 | ${config.llm.model || "未配置"} |\n| GitHub Token | ${config.githubToken ? "✅ 已配置" : "❌ 未配置"} |\n| 可用技能 | ${availableSkills.length} 个 |\n\n${!config.llm.enabled ? "\n⚠️ 请在设置页面配置大模型 API" : ""}`);
  };

  // --- Skill execution ---
  const generateExecutionSteps = (skillName: string): ExecutionStep[] => [
    { id: "1", name: "参数解析", description: "解析输入参数", status: "pending", icon: "tool" },
    { id: "2", name: "权限检查", description: "验证执行权限", status: "pending", icon: "shield" },
    { id: "3", name: "环境准备", description: "初始化执行环境", status: "pending", icon: "setting" },
    { id: "4", name: "执行 Skill", description: `运行 ${skillName}`, status: "pending", icon: "play" },
    { id: "5", name: "结果处理", description: "处理执行结果", status: "pending", icon: "result" },
  ];

  const updateStepStatus = (steps: ExecutionStep[], stepId: string, status: ExecutionStep["status"], progress?: number): ExecutionStep[] =>
    steps.map(step => step.id === stepId ? { ...step, status, progress, startTime: status === "running" ? Date.now() : step.startTime, endTime: status === "completed" || status === "failed" ? Date.now() : step.endTime } : step);

  const simulateDelay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

  const updateMessageSteps = async (msg: ChatMessage, steps: ExecutionStep[]) => {
    const updated = { ...msg, steps };
    await chatStore.update(updated);
    setMessages(prev => prev.map(m => m.timestamp === msg.timestamp ? updated : m));
  };

  const executeSkill = async (skillName: string, params: any) => {
    const steps = generateExecutionSteps(skillName);
    const sysMsg: ChatMessage = {
      conversationId, agentId, role: "assistant", content: `正在执行 Skill: ${skillName}...`,
      timestamp: Date.now(), mode: "skill", skills: [skillName], steps,
    };
    await chatStore.add(sysMsg);
    setMessages(prev => [...prev, sysMsg]);

    try {
      let cs = updateStepStatus(steps, "1", "running", 50);
      updateMessageSteps(sysMsg, cs);
      await simulateDelay(300);
      cs = updateStepStatus(cs, "1", "completed", 100);
      updateMessageSteps(sysMsg, cs);

      cs = updateStepStatus(cs, "2", "running", 50);
      updateMessageSteps(sysMsg, cs);
      await simulateDelay(400);
      cs = updateStepStatus(cs, "2", "completed", 100);
      updateMessageSteps(sysMsg, cs);

      cs = updateStepStatus(cs, "3", "running", 50);
      updateMessageSteps(sysMsg, cs);
      await simulateDelay(500);
      cs = updateStepStatus(cs, "3", "completed", 100);
      updateMessageSteps(sysMsg, cs);

      cs = updateStepStatus(cs, "4", "running", 30);
      updateMessageSteps(sysMsg, cs);

      const skillDef = await skillStore.get(skillName);
      const execution = await executeSkillApi(skillName, params ?? {}, skillDef ? (skillDef as unknown as Record<string, unknown>) : undefined, conversationId);

      cs = updateStepStatus(cs, "4", "completed", 100);
      updateMessageSteps(sysMsg, cs);

      if (onExecuteSkill) onExecuteSkill(skillName, params);

      cs = updateStepStatus(cs, "5", "running", 50);
      updateMessageSteps(sysMsg, cs);
      await simulateDelay(300);

      const body = execution.result && Object.keys(execution.result).length > 0
        ? execution.result
        : { message: execution.message, mode: execution.mode, error: execution.error ?? null };

      cs = updateStepStatus(cs, "5", execution.success ? "completed" : "failed", 100);

      const resultMsg: ChatMessage = {
        conversationId, agentId, role: "assistant",
        content: `${execution.success ? "✅" : "❌"} Skill "${skillName}" ${execution.success ? "执行完成" : "执行失败"}！\n\n\`\`\`json\n${JSON.stringify(body, null, 2)}\n\`\`\``,
        timestamp: Date.now(), mode: execution.success ? "skill_result" : "skill_error",
        skills: [skillName], steps: cs,
      };
      await chatStore.add(resultMsg);
      setMessages(prev => [...prev, resultMsg]);

      if (!execution.success) message.error(execution.error || execution.message || "Skill 执行失败");
    } catch (error) {
      const failedSteps = steps.map(s => ({
        ...s,
        status: (s.id === "4" ? "failed" : s.status === "completed" ? "completed" : "pending") as ExecutionStep["status"],
      }));
      const resultMsg: ChatMessage = {
        conversationId, agentId, role: "assistant",
        content: `❌ Skill "${skillName}" 执行失败：${String(error)}`,
        timestamp: Date.now(), mode: "skill_error", skills: [skillName], steps: failedSteps,
      };
      await chatStore.add(resultMsg);
      setMessages(prev => [...prev, resultMsg]);
      message.error("Skill 执行失败: " + String(error));
    }
  };

  const handleSlashCommand = async (content: string): Promise<boolean> => {
    const parts = content.slice(1).split(/\s+/);
    const command = parts[0].toLowerCase();
    const args = parts.slice(1).join(" ");

    switch (command) {
      case "help": await showHelpMessage(); return true;
      case "clear": await clearChat(); return true;
      case "settings": await showSettingsMessage(); return true;
    }

    const matchedSkill = availableSkills.find(s => s.name.replace(/_/g, "").toLowerCase() === command);
    if (matchedSkill) {
      let params: Record<string, any> = {};
      if (args) {
        try { params = JSON.parse(args); }
        catch {
          const firstRequiredParam = matchedSkill.parameters?.find(p => p.required);
          params = firstRequiredParam ? { [firstRequiredParam.name]: args } : { query: args };
        }
      }
      await executeSkill(matchedSkill.name, params);
      return true;
    }
    return false;
  };

  const handleSend = async () => {
    if (!authenticated) {
      setLoginModalOpen(true);
      return;
    }
    if (!input.trim()) return;
    const content = input.trim();
    setInput("");
    setShowAutocomplete(false);
    setLoading(true);

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

    const userMessage: ChatMessage = {
      conversationId: currentConversationId, agentId, role: "user", content, timestamp: Date.now(),
    };
    await chatStore.add(userMessage);
    setMessages(prev => [...prev, userMessage]);

    try {
      if (content.startsWith("/")) {
        const handled = await handleSlashCommand(content);
        if (handled) {
          setLoading(false);
          await loadSessions();
          return;
        }
      }

      const skillMatch = content.match(/^\/skill\s+([a-zA-Z0-9_:-]+)(.*)?$/);
      if (skillMatch) {
        const skillName = skillMatch[1];
        const paramsStr = skillMatch[2]?.trim();
        let params = {};
        if (paramsStr) {
          try { params = JSON.parse(paramsStr); }
          catch { params = { query: paramsStr }; }
        }
        await executeSkill(skillName, params);
      } else {
        let reply;
        try {
          reply = await sendChatMessage(currentConversationId, content);
        } catch (error: any) {
          if (error.message?.includes("conversation not found")) {
            const created = await createConversation();
            currentConversationId = created.conversation_id;
            setConversationId(currentConversationId);
            userMessage.conversationId = currentConversationId;
            reply = await sendChatMessage(currentConversationId, content);
          } else {
            throw error;
          }
        }
        const aiMessage: ChatMessage = {
          conversationId: currentConversationId, agentId, role: "assistant",
          content: reply.reply, timestamp: Date.now(), mode: reply.mode,
          metadata: { warning: reply.warning, model: reply.model },
        };
        await chatStore.add(aiMessage);
        setMessages(prev => [...prev, aiMessage]);
      }
    } catch (error) {
      message.error("发送失败: " + String(error));
    } finally {
      setLoading(false);
      await loadSessions();
    }
  };

  const handleSkillSelect = (skill: AgentSkill) => {
    const params = skill.parameters?.filter(p => p.required).map(p => `"${p.name}": "..."`).join(", ") ?? "";
    setInput(`/skill ${skill.name}${params ? ` {${params}}` : ""}`);
    setShowSkillPanel(false);
  };

  const handleExampleClick = (query: string) => {
    setInput(query);
    setTimeout(() => handleSend(), 100);
  };

  return (
    <Card className="ai-chat-card" bordered={false}
      style={{ borderRadius: 12, background: "#ffffff", boxShadow: "0 1px 3px rgba(0,0,0,0.05), 0 1px 2px rgba(0,0,0,0.03)", border: "1px solid #e5e7eb" }}
      title={
        <Space size={10}>
          <div style={{ width: 36, height: 36, borderRadius: 10, background: "#22c55e", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <RobotOutlined style={{ color: "#fff", fontSize: 18 }} />
          </div>
          <span style={{ fontWeight: 600, fontSize: 16, color: "#111827" }}>AI 助手</span>
          {!config.llm.enabled && <Tag color="warning" style={{ borderRadius: 4, fontSize: 11, fontWeight: 500 }}>AI 未启用</Tag>}
        </Space>
      }
      extra={
        <Space size={6}>
          <Tooltip title={isFullscreen ? "退出全屏" : "全屏"}>
            <Button type="text" size="small" icon={isFullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />} onClick={() => setIsFullscreen(prev => !prev)} style={{ borderRadius: 8, width: 32, height: 32 }} />
          </Tooltip>
          <Tooltip title="Skill 列表">
            <Button type={showSkillPanel ? "primary" : "text"} size="small" icon={<ToolOutlined />} onClick={() => setShowSkillPanel(!showSkillPanel)} style={{ borderRadius: 8, width: 32, height: 32 }} />
          </Tooltip>
          <Tooltip title="新对话">
            <Button size="small" icon={<ThunderboltOutlined />} onClick={newConversation} data-testid="new-conversation-button" style={{ borderRadius: 8, width: 32, height: 32 }} />
          </Tooltip>
          <Popconfirm title="确认清空当前会话？" description="清空后不可恢复。" okText="清空" cancelText="取消" okButtonProps={{ danger: true }} onConfirm={() => { void clearChat(); }}>
            <Button size="small" icon={<ClearOutlined />} danger style={{ borderRadius: 8, width: 32, height: 32 }} />
          </Popconfirm>
        </Space>
      }
    >
      <div style={{ display: "flex", gap: 16, height: isFullscreen ? "calc(100vh - 180px)" : "calc(100vh - 280px)", minHeight: 480 }}>
        {/* Left: Session Sidebar */}
        <SessionSidebar
          sessions={sessions}
          activeSessionId={conversationId}
          collapsed={historyCollapsed}
          onSwitchSession={switchConversation}
          onDeleteSession={deleteSession}
          onToggleCollapse={() => setHistoryCollapsed(prev => !prev)}
        />

        {/* Middle: Chat area */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
          <div style={{ flex: 1, overflow: "auto", padding: "6px", background: "transparent", borderRadius: 4, marginBottom: 10 }}>
            {messages.length === 0 ? (
              <ChatEmptyState exampleCards={exampleCards} onExampleClick={handleExampleClick} />
            ) : (
              <MessageList messages={messages} loading={loading} />
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input area */}
          <div style={{ position: "relative", flexShrink: 0 }}>
            <AutocompleteDropdown
              visible={showAutocomplete}
              type={autocompleteType}
              commands={filteredCommands}
              skills={filteredSkills}
              selectedIndex={selectedIndex}
              onSelect={selectAutocompleteItem}
              onMouseEnter={setSelectedIndex}
            />
            <div style={{ display: "flex", gap: 10, alignItems: "stretch" }}>
              <TextArea
                ref={textareaRef}
                value={input}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                placeholder="输入消息... 使用 / 查看命令"
                rows={2}
                style={{ flex: 1, resize: "none", borderRadius: 6, border: "1px solid #d1d5db", background: "#ffffff", padding: "10px 14px", fontSize: 14, lineHeight: 1.5 }}
              />
              <Button
                type="default"
                icon={loading ? <LoadingOutlined /> : <SendOutlined />}
                onClick={handleSend}
                loading={loading}
                disabled={!input.trim()}
                style={{ height: "auto", minWidth: 56, fontSize: 13, borderRadius: 6, background: "#ffffff", border: "1px solid #22c55e", color: "#22c55e" }}
              >
                发送
              </Button>
            </div>
            <div style={{ marginTop: 8, fontSize: 11 }}>
              <Text style={{ color: "#9ca3af" }}>可用命令:{" "}
                <code style={{ padding: "1px 4px", borderRadius: 4, background: "#f3f4f6", color: "#374151", fontSize: 10 }}>/skill</code>{" "}
                <code style={{ padding: "1px 4px", borderRadius: 4, background: "#f3f4f6", color: "#374151", fontSize: 10 }}>/help</code>{" "}
                <code style={{ padding: "1px 4px", borderRadius: 4, background: "#f3f4f6", color: "#374151", fontSize: 10 }}>/clear</code>{" "}
                <code style={{ padding: "1px 4px", borderRadius: 4, background: "#f3f4f6", color: "#374151", fontSize: 10 }}>/settings</code>
              </Text>
            </div>
          </div>
        </div>

        {/* Right: Skill panel */}
        {showSkillPanel && (
          <div style={{ width: 260, borderLeft: "1px solid #e5e7eb", paddingLeft: 16, overflow: "auto", flexShrink: 0 }}>
            <div style={{ marginBottom: 12, fontSize: 11, fontWeight: 600, color: "#6b7280", letterSpacing: "0.3px", textTransform: "uppercase", display: "flex", alignItems: "center", gap: 6, padding: "8px 12px", background: "#f9fafb", borderRadius: 4, border: "1px solid #e5e7eb" }}>
              <ToolOutlined style={{ fontSize: 14, color: "#6b7280" }} /> 技能
            </div>
            <SkillList onSkillClick={handleSkillSelect} showDisabled={false} />
          </div>
        )}
      </div>
      <LoginModal
        open={loginModalOpen}
        onClose={() => setLoginModalOpen(false)}
        reason="AI 对话功能需要登录后使用"
      />
    </Card>
  );
}
