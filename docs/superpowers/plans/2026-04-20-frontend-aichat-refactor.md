# AIChat 组件拆分与样式重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: `superpowers:subagent-driven-development`
> Steps use checkbox (`- [ ]`) syntax.

**Goal:** 将 1900 行的 AIChat 巨型组件拆分为 5 个独立子组件，内联样式迁移到 CSS modules，修复 Workspace.tsx 中两个 stub 函数。

**Architecture:** AIChat/index.tsx 保留为编排层（状态管理 + 事件处理），子组件负责纯渲染。数据流：AIChat 持有 state → 通过 props 下发给子组件 → 子组件通过 callback 上报事件。子组件样式从 inline `style={{}}` 迁移到 `.module.css`，与现有全局 `styles.css` 并存。

**Tech Stack:** React 18, TypeScript 5, Ant Design 5, Vite 5 (原生 CSS Modules 支持), Vitest

**Risks:**
- AIChat 状态与渲染深度耦合，提取时可能遗漏 props → 缓解：每个提取的组件先建 props 接口，对照原代码逐一传递
- Workspace.tsx stub 函数缺少后端 API 接口定义 → 缓解：复用现有 `executeSkillApi` 和 `sendChatMessage`
- CSS modules 与全局 styles.css 可能有选择器冲突 → 缓解：CSS modules 自动 scoped，不冲突

---

### Task 1: Extract ExecutionSteps 组件

**Depends on:** None
**Files:**
- Create: `app/frontend/src/components/AIChat/ExecutionSteps.tsx`
- Create: `app/frontend/src/components/AIChat/ExecutionSteps.module.css`

- [ ] **Step 1: 创建 ExecutionSteps 组件 — 从 AIChat 底部提取独立的步骤流程展示组件**

```typescript
// app/frontend/src/components/AIChat/ExecutionSteps.tsx
import { Tag, Typography } from "antd";
import {
  ApiOutlined,
  BranchesOutlined,
  CheckCircleOutlined,
  CheckOutlined,
  CloseCircleOutlined,
  DotChartOutlined,
  LoadingOutlined,
  PlayCircleOutlined,
  SettingOutlined,
  ToolOutlined,
} from "@ant-design/icons";
import type { ExecutionStep } from "../../db";
import styles from "./ExecutionSteps.module.css";

const { Text } = Typography;

interface ExecutionStepsProps {
  steps: ExecutionStep[];
}

export default function ExecutionSteps({ steps }: ExecutionStepsProps) {
  const getStepIcon = (icon: string, status: ExecutionStep["status"]) => {
    const iconStyle = { fontSize: 14 };
    const spin = status === "running";
    switch (icon) {
      case "tool": return spin ? <LoadingOutlined style={iconStyle} spin /> : <ToolOutlined style={iconStyle} />;
      case "shield": return spin ? <LoadingOutlined style={iconStyle} spin /> : <ApiOutlined style={iconStyle} />;
      case "setting": return spin ? <LoadingOutlined style={iconStyle} spin /> : <SettingOutlined style={iconStyle} />;
      case "play": return spin ? <LoadingOutlined style={iconStyle} spin /> : <PlayCircleOutlined style={iconStyle} />;
      case "result": return spin ? <LoadingOutlined style={iconStyle} spin /> : <DotChartOutlined style={iconStyle} />;
      default: return spin ? <LoadingOutlined style={iconStyle} spin /> : <CheckCircleOutlined style={iconStyle} />;
    }
  };

  const getStepColor = (status: ExecutionStep["status"]) => {
    switch (status) {
      case "completed": return "#22c55e";
      case "running": return "#3b82f6";
      case "failed": return "#ef4444";
      default: return "#94a3b8";
    }
  };

  const completedCount = steps.filter((s) => s.status === "completed").length;
  const runningCount = steps.filter((s) => s.status === "running").length;
  const failedCount = steps.filter((s) => s.status === "failed").length;

  const totalProgress = steps.reduce((sum, step) => {
    if (step.status === "completed") return sum + 100;
    if (step.status === "running") return sum + (step.progress || 50);
    return sum;
  }, 0) / steps.length;

  return (
    <div className={styles.container}>
      <div className={styles.progressHeader}>
        <Text className={styles.progressLabel}>
          <BranchesOutlined /> 执行进度
        </Text>
        <Text className={styles.progressInfo}>
          {completedCount}/{steps.length} 完成
          {failedCount > 0 && ` · ${failedCount} 失败`}
          {runningCount > 0 && ` · ${runningCount} 进行中`}
        </Text>
      </div>
      <div className={styles.progressBarTrack}>
        <div
          className={styles.progressBarFill}
          style={{
            width: `${totalProgress}%`,
            background: failedCount > 0
              ? "linear-gradient(90deg, #22c55e, #f59e0b)"
              : "linear-gradient(90deg, #22c55e, #4ade80)",
          }}
        />
      </div>

      <div className={styles.stepList}>
        {steps.map((step) => {
          const color = getStepColor(step.status);
          return (
            <div key={step.id} className={styles.stepItem}>
              <div
                className={styles.stepIcon}
                style={{
                  background: step.status === "pending" ? "#f1f5f9" : `${color}15`,
                  borderColor: step.status === "pending" ? "#cbd5e1" : color,
                  color: step.status === "pending" ? "#94a3b8" : color,
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

              <div className={styles.stepContent}>
                <div className={styles.stepTitleRow}>
                  <Text
                    className={styles.stepTitle}
                    style={{
                      fontWeight: step.status === "running" ? 600 : 500,
                      color: step.status === "pending" ? "#64748b" : "#1e293b",
                    }}
                  >
                    {step.name}
                  </Text>
                  {step.status === "running" && (
                    <Tag color="processing" className={styles.stepTag}>进行中</Tag>
                  )}
                  {step.status === "failed" && (
                    <Tag color="error" className={styles.stepTag}>失败</Tag>
                  )}
                </div>
                {step.description && step.status !== "pending" && (
                  <Text className={styles.stepDesc}>{step.description}</Text>
                )}
                {step.subSteps && step.subSteps.length > 0 && step.status !== "pending" && (
                  <div className={styles.subStepList}>
                    {step.subSteps.map((subStep) => (
                      <div key={subStep.id} className={styles.subStepItem}>
                        <div
                          className={styles.subStepDot}
                          style={{ background: getStepColor(subStep.status) }}
                        />
                        <Text className={styles.subStepText}>{subStep.name}</Text>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {step.status === "completed" && step.endTime && step.startTime && (
                <Text className={styles.stepDuration}>
                  {((step.endTime - step.startTime) / 1000).toFixed(1)}s
                </Text>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 创建 ExecutionSteps CSS module**

```css
/* app/frontend/src/components/AIChat/ExecutionSteps.module.css */
.container {
  margin-top: 12px;
  padding: 12px;
  background: transparent;
  border-radius: 4px;
  border: 1px solid #bbf7d0;
}

.progressHeader {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.progressLabel {
  font-size: 11px;
  font-weight: 600;
  color: #166534;
}

.progressInfo {
  font-size: 10px;
  color: #22c55e;
}

.progressBarTrack {
  height: 4px;
  background: #e2e8f0;
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 12px;
}

.progressBarFill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.5s ease;
}

.stepList {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stepItem {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.stepIcon {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 2px solid;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.3s ease;
}

.stepContent {
  flex: 1;
  min-width: 0;
}

.stepTitleRow {
  display: flex;
  align-items: center;
  gap: 6px;
}

.stepTitle {
  font-size: 12px;
}

.stepTag {
  font-size: 9px;
  padding: 0 4px;
  height: 16px;
  line-height: 14px;
}

.stepDesc {
  font-size: 10px;
  color: #64748b;
  display: block;
}

.subStepList {
  margin-top: 6px;
  padding-left: 12px;
}

.subStepItem {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}

.subStepDot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.subStepText {
  font-size: 10px;
  color: #64748b;
}

.stepDuration {
  font-size: 9px;
  color: #94a3b8;
  flex-shrink: 0;
}
```

- [ ] **Step 3: 验证 ExecutionSteps 提取**
Run: `cd /Users/cc11001100/github/typo-master/typo-master/app/frontend && npx tsc --noEmit --pretty 2>&1 | head -20`
Expected:
  - Exit code: 0 (or errors unrelated to ExecutionSteps)
  - Output does NOT contain: "ExecutionSteps" in error messages

- [ ] **Step 4: 提交**
Run: `cd /Users/cc11001100/github/typo-master/typo-master && git add app/frontend/src/components/AIChat/ExecutionSteps.tsx app/frontend/src/components/AIChat/ExecutionSteps.module.css && git commit -m "refactor(frontend): extract ExecutionSteps component from AIChat"`

---

### Task 2: Extract ChatEmptyState 组件

**Depends on:** None
**Files:**
- Create: `app/frontend/src/components/AIChat/ChatEmptyState.tsx`
- Create: `app/frontend/src/components/AIChat/ChatEmptyState.module.css`

- [ ] **Step 1: 创建 ChatEmptyState 组件 — 从 AIChat 提取欢迎界面和示例卡片**

```typescript
// app/frontend/src/components/AIChat/ChatEmptyState.tsx
import { Typography, Space } from "antd";
import {
  ArrowRightOutlined,
  BulbOutlined,
  MessageOutlined,
  RobotOutlined,
  RocketOutlined,
  SearchOutlined,
  StarOutlined,
} from "@ant-design/icons";
import styles from "./ChatEmptyState.module.css";

const { Title, Text } = Typography;

interface ExampleCard {
  id: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  color: string;
  query: string;
}

interface ChatEmptyStateProps {
  exampleCards: ExampleCard[];
  onExampleClick: (query: string) => void;
}

export default function ChatEmptyState({ exampleCards, onExampleClick }: ChatEmptyStateProps) {
  return (
    <div className={styles.container}>
      <div className={styles.welcomeBox}>
        <div className={styles.iconBox}>
          <RobotOutlined style={{ fontSize: 28, color: "#fff" }} />
        </div>
        <Title level={4} className={styles.title}>开始对话</Title>
        <Text className={styles.subtitle}>
          我是 Typo Master AI 助手，可以帮助您搜索 GitHub 项目、<br />
          扫描代码 typo、管理 Web3 空投任务等。
        </Text>
      </div>

      <div className={styles.examplesSection}>
        <div className={styles.exampleHeader}>
          <div className={styles.exampleLabel}>
            <BulbOutlined style={{ color: "#22c55e", fontSize: 14 }} />
            <Text className={styles.exampleLabelText}>快速开始，选择一个示例</Text>
          </div>
        </div>
        <div className={styles.exampleGrid}>
          {exampleCards.map((card) => (
            <div
              key={card.id}
              className={styles.exampleCard}
              onClick={() => onExampleClick(card.query)}
            >
              <div className={styles.exampleIcon} style={{ background: card.color + "15" }}>
                <span style={{ color: card.color, fontSize: 18 }}>{card.icon}</span>
              </div>
              <div className={styles.exampleContent}>
                <Text strong className={styles.exampleTitle}>{card.title}</Text>
                <Text className={styles.exampleDesc}>{card.description}</Text>
              </div>
              <ArrowRightOutlined className={styles.exampleArrow} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 创建 ChatEmptyState CSS module**

```css
/* app/frontend/src/components/AIChat/ChatEmptyState.module.css */
.container {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px;
}

.welcomeBox {
  padding: 32px 40px;
  border-radius: 12px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  text-align: center;
  max-width: 480px;
  width: 100%;
}

.iconBox {
  width: 64px;
  height: 64px;
  border-radius: 8px;
  background: #22c55e;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
}

.title {
  margin-bottom: 8px !important;
  color: #111827 !important;
  font-weight: 600 !important;
}

.subtitle {
  font-size: 14px;
  color: #6b7280;
  line-height: 1.6;
}

.examplesSection {
  margin-top: 28px;
  width: 100%;
  max-width: 680px;
}

.exampleHeader {
  text-align: center;
  margin-bottom: 16px;
}

.exampleLabel {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: 6px;
  background: #f3f4f6;
  border: 1px solid #e5e7eb;
}

.exampleLabelText {
  font-size: 12px;
  color: #374151;
  font-weight: 500;
}

.exampleGrid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 12px;
}

.exampleCard {
  cursor: pointer;
  padding: 16px;
  border-radius: 6px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
  transition: all 0.15s ease;
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.exampleCard:hover {
  border-color: #d1d5db !important;
  background: #fafafa !important;
}

.exampleCard:active {
  background: #f3f4f6 !important;
}

.exampleIcon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.exampleContent {
  flex: 1;
  min-width: 0;
}

.exampleTitle {
  display: block;
  font-size: 13px;
  color: #111827;
  margin-bottom: 2px;
}

.exampleDesc {
  font-size: 11px;
  color: #6b7280;
  line-height: 1.4;
}

.exampleArrow {
  color: #9ca3af;
  font-size: 12px;
  flex-shrink: 0;
  margin-top: 4px;
}
```

- [ ] **Step 3: 提交**
Run: `cd /Users/cc11001100/github/typo-master/typo-master && git add app/frontend/src/components/AIChat/ChatEmptyState.tsx app/frontend/src/components/AIChat/ChatEmptyState.module.css && git commit -m "refactor(frontend): extract ChatEmptyState component from AIChat"`

---

### Task 3: Extract AutocompleteDropdown 组件

**Depends on:** None
**Files:**
- Create: `app/frontend/src/components/AIChat/AutocompleteDropdown.tsx`
- Create: `app/frontend/src/components/AIChat/AutocompleteDropdown.module.css`

- [ ] **Step 1: 创建 AutocompleteDropdown 组件 — 从 AIChat 提取命令/技能自动补全菜单**

```typescript
// app/frontend/src/components/AIChat/AutocompleteDropdown.tsx
import { Typography, Space } from "antd";
import { ToolOutlined } from "@ant-design/icons";
import type { AgentSkill } from "../../db";
import styles from "./AutocompleteDropdown.module.css";

const { Text } = Typography;

export interface SlashCommand {
  name: string;
  description: string;
  icon: React.ReactNode;
  usage?: string;
}

export type AutocompleteType = "command" | "skill" | null;

interface AutocompleteDropdownProps {
  visible: boolean;
  type: AutocompleteType;
  commands: SlashCommand[];
  skills: AgentSkill[];
  selectedIndex: number;
  onSelect: (index: number) => void;
  onMouseEnter: (index: number) => void;
}

export default function AutocompleteDropdown({
  visible,
  type,
  commands,
  skills,
  selectedIndex,
  onSelect,
  onMouseEnter,
}: AutocompleteDropdownProps) {
  if (!visible) return null;

  return (
    <div className={styles.dropdown}>
      {type === "command" && (
        <>
          <div className={styles.sectionHeader}>
            可用命令 ({commands.length})
          </div>
          {commands.map((cmd, index) => (
            <div
              key={cmd.name}
              className={`${styles.item} ${index === selectedIndex ? styles.itemSelected : ""}`}
              onClick={() => onSelect(index)}
              onMouseEnter={() => onMouseEnter(index)}
            >
              <span className={styles.itemIcon}>{cmd.icon}</span>
              <div className={styles.itemContent}>
                <div className={styles.itemTitleRow}>
                  <Text strong className={styles.itemName}>/{cmd.name}</Text>
                  <Text className={styles.itemDesc}>{cmd.description}</Text>
                </div>
                {cmd.usage && (
                  <code className={styles.itemUsage}>{cmd.usage}</code>
                )}
              </div>
            </div>
          ))}
        </>
      )}

      {type === "skill" && (
        <>
          <div className={styles.sectionHeader}>
            可用技能 ({skills.length})
          </div>
          {skills.map((skill, index) => (
            <div
              key={skill.name}
              className={`${styles.item} ${index === selectedIndex ? styles.itemSelected : ""}`}
              onClick={() => onSelect(index)}
              onMouseEnter={() => onMouseEnter(index)}
            >
              <div className={styles.skillMeta}>
                <span className={styles.skillCategory}>{skill.category}</span>
                <Text strong className={styles.itemName}>{skill.name}</Text>
              </div>
              <Text className={styles.skillDescFull}>{skill.description}</Text>
              {skill.parameters && skill.parameters.length > 0 && (
                <div className={styles.paramList}>
                  {skill.parameters.slice(0, 3).map((param) => (
                    <span
                      key={param.name}
                      className={`${styles.paramTag} ${param.required ? styles.paramRequired : ""}`}
                    >
                      {param.name}
                      {param.required && <span className={styles.paramStar}>*</span>}
                    </span>
                  ))}
                  {skill.parameters.length > 3 && (
                    <span className={styles.paramMore}>+{skill.parameters.length - 3}</span>
                  )}
                </div>
              )}
            </div>
          ))}
        </>
      )}

      <div className={styles.footer}>
        <span className={styles.footerHint}>
          <kbd className={styles.kbd}>↑↓</kbd> 选择
        </span>
        <span className={styles.footerHint}>
          <kbd className={styles.kbd}>↵</kbd> 确认
        </span>
        <span className={styles.footerHint}>
          <kbd className={styles.kbd}>Tab</kbd> 补全
        </span>
        <span className={styles.footerHint}>
          <kbd className={styles.kbd}>Esc</kbd> 关闭
        </span>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 创建 AutocompleteDropdown CSS module**

```css
/* app/frontend/src/components/AIChat/AutocompleteDropdown.module.css */
.dropdown {
  position: absolute;
  bottom: 100%;
  left: 0;
  right: 80;
  margin-bottom: 8px;
  background: #ffffff;
  border-radius: 8px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1), 0 2px 8px rgba(0, 0, 0, 0.05);
  border: 1px solid #e5e7eb;
  max-height: 300px;
  overflow: auto;
  z-index: 1000;
}

.sectionHeader {
  padding: 10px 16px;
  background: transparent;
  border-bottom: 1px solid rgba(226, 232, 240, 0.6);
  font-size: 11px;
  color: #64748b;
  font-weight: 600;
  letter-spacing: 0.3px;
  text-transform: uppercase;
}

.item {
  padding: 12px 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid rgba(241, 245, 249, 0.6);
  transition: all 0.15s ease;
}

.itemSelected {
  background: rgba(34, 197, 94, 0.08);
}

.itemIcon {
  color: #22c55e;
  font-size: 18px;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: rgba(34, 197, 94, 0.1);
}

.itemContent {
  flex: 1;
  min-width: 0;
}

.itemTitleRow {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 2px;
}

.itemName {
  font-size: 14px;
  color: #1e293b;
}

.itemDesc {
  font-size: 12px;
  color: #64748b;
}

.itemUsage {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(34, 197, 94, 0.08);
  color: #166534;
}

.skillMeta {
  display: flex;
  align-items: center;
  gap: 10px;
}

.skillCategory {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 6px;
  background: rgba(59, 130, 246, 0.1);
  color: #2563eb;
  font-weight: 500;
}

.skillDescFull {
  font-size: 12px;
  color: #64748b;
  margin-top: 4px;
  display: block;
}

.paramList {
  margin-top: 6px;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.paramTag {
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(148, 163, 184, 0.1);
  color: #64748b;
  border: 1px solid rgba(148, 163, 184, 0.2);
}

.paramRequired {
  background: rgba(239, 68, 68, 0.08);
  color: #dc2626;
  border-color: rgba(239, 68, 68, 0.2);
}

.paramStar {
  color: #dc2626;
}

.paramMore {
  font-size: 10px;
  color: #94a3b8;
}

.footer {
  padding: 10px 16px;
  background: rgba(248, 250, 252, 0.8);
  border-top: 1px solid rgba(226, 232, 240, 0.6);
  font-size: 11px;
  color: #94a3b8;
  display: flex;
  gap: 16px;
  font-weight: 500;
}

.footerHint {
  display: flex;
  align-items: center;
  gap: 4px;
}

.kbd {
  padding: 2px 6px;
  border-radius: 4px;
  background: #fff;
  border: 1px solid #e2e8f0;
  font-size: 10px;
  font-family: monospace;
}
```

- [ ] **Step 3: 提交**
Run: `cd /Users/cc11001100/github/typo-master/typo-master && git add app/frontend/src/components/AIChat/AutocompleteDropdown.tsx app/frontend/src/components/AIChat/AutocompleteDropdown.module.css && git commit -m "refactor(frontend): extract AutocompleteDropdown component from AIChat"`

---

### Task 4: Extract SessionSidebar 和 MessageList 组件

**Depends on:** None
**Files:**
- Create: `app/frontend/src/components/AIChat/SessionSidebar.tsx`
- Create: `app/frontend/src/components/AIChat/SessionSidebar.module.css`
- Create: `app/frontend/src/components/AIChat/MessageList.tsx`
- Create: `app/frontend/src/components/AIChat/MessageList.module.css`

- [ ] **Step 1: 创建 SessionSidebar 组件 — 从 AIChat 提取左侧历史会话面板**

```typescript
// app/frontend/src/components/AIChat/SessionSidebar.tsx
import { Avatar, Button, Empty, Popconfirm, Space, Tooltip, Typography } from "antd";
import {
  DeleteOutlined,
  HistoryOutlined,
  LeftOutlined,
  RightOutlined,
} from "@ant-design/icons";
import styles from "./SessionSidebar.module.css";

const { Text } = Typography;

export interface ChatSession {
  id: string;
  title: string;
  lastMessage: string;
  timestamp: number;
  messageCount: number;
}

interface SessionSidebarProps {
  sessions: ChatSession[];
  activeSessionId: string;
  collapsed: boolean;
  onSwitchSession: (sessionId: string) => void;
  onDeleteSession: (sessionId: string) => void;
  onToggleCollapse: () => void;
}

export default function SessionSidebar({
  sessions,
  activeSessionId,
  collapsed,
  onSwitchSession,
  onDeleteSession,
  onToggleCollapse,
}: SessionSidebarProps) {
  const getCompactLabel = (index: number) => {
    const label = index + 1;
    return label > 99 ? "99+" : String(label);
  };

  return (
    <div className={styles.container} style={{ width: collapsed ? 56 : 220 }}>
      <div className={styles.header} style={{ padding: collapsed ? "10px 6px" : "10px 12px" }}>
        {!collapsed ? (
          <Space size={8}>
            <HistoryOutlined style={{ fontSize: 14, color: "#6b7280" }} />
            <span>历史会话</span>
          </Space>
        ) : (
          <HistoryOutlined style={{ fontSize: 14, color: "#6b7280" }} />
        )}
        <Tooltip title={collapsed ? "展开历史会话" : "折叠历史会话"}>
          <Button
            type="text"
            size="small"
            icon={collapsed ? <RightOutlined /> : <LeftOutlined />}
            onClick={onToggleCollapse}
            data-testid="history-collapse-toggle"
            className={styles.collapseBtn}
          />
        </Tooltip>
      </div>

      <div className={styles.list} style={{ padding: collapsed ? 0 : "0 4px" }}>
        {sessions.length === 0 ? (
          !collapsed && (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description="暂无历史会话"
              style={{ marginTop: 24 }}
            />
          )
        ) : (
          sessions.map((session, index) =>
            collapsed ? (
              <Tooltip key={session.id} title={`${session.title}\n${session.lastMessage}`}>
                <button
                  type="button"
                  data-testid="history-compact-item"
                  className={`${styles.compactItem} ${session.id === activeSessionId ? styles.compactItemActive : ""}`}
                  onClick={() => onSwitchSession(session.id)}
                >
                  {getCompactLabel(index)}
                </button>
              </Tooltip>
            ) : (
              <div
                key={session.id}
                onClick={() => onSwitchSession(session.id)}
                className={`${styles.sessionItem} ${session.id === activeSessionId ? styles.sessionItemActive : ""}`}
              >
                <div className={styles.sessionContent}>
                  <Text
                    strong
                    className={styles.sessionTitle}
                    style={{ color: session.id === activeSessionId ? "#166534" : "#111827" }}
                    ellipsis
                  >
                    {session.title}
                  </Text>
                  <Text
                    className={styles.sessionPreview}
                    style={{ color: session.id === activeSessionId ? "#16a34a" : "#9ca3af" }}
                    ellipsis
                  >
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
                    onDeleteSession(session.id);
                  }}
                  onCancel={(e) => e?.stopPropagation?.()}
                >
                  <Button
                    type="text"
                    size="small"
                    icon={<DeleteOutlined />}
                    onClick={(e) => e.stopPropagation()}
                    danger
                    className={styles.sessionDeleteBtn}
                  />
                </Popconfirm>
              </div>
            )
          )
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 创建 SessionSidebar CSS module**

```css
/* app/frontend/src/components/AIChat/SessionSidebar.module.css */
.container {
  border-right: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  transition: width 0.2s ease;
}

.header {
  margin-bottom: 16px;
  font-size: 12px;
  font-weight: 600;
  color: #6b7280;
  letter-spacing: 0.3px;
  text-transform: uppercase;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  background: #f9fafb;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.collapseBtn {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  color: #6b7280;
}

.list {
  flex: 1;
  overflow: auto;
}

.sessionItem {
  padding: 12px 14px;
  cursor: pointer;
  border-radius: 8px;
  margin-bottom: 6px;
  border: 1px solid transparent;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  transition: all 0.15s ease;
}

.sessionItem:hover {
  background: #f3f4f6 !important;
  border-color: #d1d5db !important;
}

.sessionItem:hover .sessionDeleteBtn {
  opacity: 1 !important;
}

.sessionItemActive {
  background: #dcfce7;
  border-color: #86efac;
}

.sessionContent {
  flex: 1;
  overflow: hidden;
  min-width: 0;
}

.sessionTitle {
  font-size: 13px;
  display: block;
}

.sessionPreview {
  font-size: 11px;
  margin-top: 2px;
}

.sessionDeleteBtn {
  padding: 4px 8px;
  min-width: 28px;
  height: 28px;
  border-radius: 6px;
  opacity: 0;
  transition: all 0.15s ease;
}

.sessionDeleteBtn:hover {
  background: #fee2e2 !important;
}

.compactItem {
  width: 36px;
  height: 36px;
  margin: 6px auto;
  border-radius: 8px;
  border: 1px solid transparent;
  background: #f9fafb;
  color: #374151;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s ease;
}

.compactItemActive {
  background: #dcfce7;
  border-color: #86efac;
  color: #166534;
}
```

- [ ] **Step 3: 创建 MessageList 组件 — 从 AIChat 提取消息渲染区域**

```typescript
// app/frontend/src/components/AIChat/MessageList.tsx
import { Avatar, List, Paragraph, Space, Tag } from "antd";
import { RobotOutlined, ToolOutlined } from "@ant-design/icons";
import type { ChatMessage } from "../../db";
import ExecutionSteps from "./ExecutionSteps";
import styles from "./MessageList.module.css";

interface MessageListProps {
  messages: ChatMessage[];
  loading: boolean;
}

export default function MessageList({ messages, loading }: MessageListProps) {
  if (messages.length === 0) return null;

  return (
    <>
      <List
        dataSource={messages}
        renderItem={(msg) => (
          <List.Item
            className={styles.messageItem}
            style={{ justifyContent: msg.role === "user" ? "flex-end" : "flex-start" }}
          >
            <Space
              align="start"
              style={{ flexDirection: msg.role === "user" ? "row-reverse" : "row", gap: "6px" }}
            >
              <Avatar
                size="small"
                icon={msg.role === "user" ? undefined : <RobotOutlined />}
                src={msg.role === "user" ? "/claude-code-logo.svg" : undefined}
                style={{
                  background: msg.role === "user" ? "#22c55e" : "#3b82f6",
                  flexShrink: 0,
                }}
              />
              <div
                className={`${styles.bubble} ${msg.role === "user" ? styles.bubbleUser : styles.bubbleAI}`}
              >
                {msg.skills && msg.skills.length > 0 && (
                  <div className={styles.skillTags}>
                    {msg.skills.map((skill) => (
                      <Tag key={skill} className={styles.skillTag}>
                        <ToolOutlined /> {skill}
                      </Tag>
                    ))}
                  </div>
                )}
                <Paragraph
                  className={styles.messageText}
                  style={{ color: msg.role === "user" ? "#fff" : "#111827" }}
                >
                  {msg.content}
                </Paragraph>
                {msg.steps && msg.steps.length > 0 && <ExecutionSteps steps={msg.steps} />}
                {msg.mode && <Tag className={styles.modeTag}>{msg.mode}</Tag>}
              </div>
            </Space>
          </List.Item>
        )}
      />

      {loading && (
        <List.Item className={styles.messageItem} style={{ justifyContent: "flex-start" }}>
          <Space align="start" style={{ flexDirection: "row", gap: "10px" }}>
            <Avatar
              size="small"
              icon={<RobotOutlined />}
              className={styles.thinkingAvatar}
            />
            <div className={styles.thinkingBubble}>
              <div className="ai-thinking-indicator">
                <div className="ai-thinking-core"></div>
                <div className="ai-thinking-ring-inner"></div>
                <div className="ai-thinking-ring-outer"></div>
              </div>
              <span className="ai-thinking-text">AI 思考中</span>
            </div>
          </Space>
        </List.Item>
      )}
    </>
  );
}
```

- [ ] **Step 4: 创建 MessageList CSS module**

```css
/* app/frontend/src/components/AIChat/MessageList.module.css */
.messageItem {
  padding: 4px 0;
}

.bubble {
  max-width: 85%;
  min-width: 120px;
  padding: 10px 14px;
  border-radius: 8px;
}

.bubbleUser {
  background: #22c55e;
  border: none;
  border-radius: 8px 8px 2px 8px;
}

.bubbleAI {
  background: #f3f4f6;
  border: 1px solid #e5e7eb;
  border-radius: 8px 8px 8px 2px;
}

.skillTags {
  margin-bottom: 6px;
}

.skillTag {
  font-size: 10px;
  padding: 2px 8px;
  background: #dbeafe;
  border: 1px solid #bfdbfe;
  color: #1d4ed8;
  border-radius: 4px;
}

.messageText {
  margin: 0;
  white-space: pre-wrap;
  font-size: 14px;
  line-height: 1.5;
}

.modeTag {
  margin-top: 3px;
  font-size: 10px;
  padding: 0 4px;
}

.thinkingAvatar {
  background: linear-gradient(135deg, #3b82f6 0%, #22c55e 100%);
  flex-shrink: 0;
  box-shadow: 0 0 12px rgba(59, 130, 246, 0.3);
}

.thinkingBubble {
  max-width: 85%;
  min-width: 160px;
  padding: 10px 14px;
  border-radius: 8px;
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.1);
  display: flex;
  align-items: center;
  gap: 12px;
}
```

- [ ] **Step 5: 提交**
Run: `cd /Users/cc11001100/github/typo-master/typo-master && git add app/frontend/src/components/AIChat/SessionSidebar.tsx app/frontend/src/components/AIChat/SessionSidebar.module.css app/frontend/src/components/AIChat/MessageList.tsx app/frontend/src/components/AIChat/MessageList.module.css && git commit -m "refactor(frontend): extract SessionSidebar and MessageList components from AIChat"`

---

### Task 5: Refactor AIChat/index.tsx to compose extracted components

**Depends on:** Task 1, Task 2, Task 3, Task 4
**Files:**
- Modify: `app/frontend/src/components/AIChat/index.tsx` (entire file refactor)

- [ ] **Step 1: 重写 AIChat/index.tsx — 编排层，导入子组件，移除已提取的内联渲染代码**

文件: `app/frontend/src/components/AIChat/index.tsx`

重写为以下结构（保留所有业务逻辑，替换 JSX 渲染部分为子组件调用）：

```typescript
// app/frontend/src/components/AIChat/index.tsx
import { useEffect, useState, useRef, useCallback, useMemo } from "react";
import {
  Card, Input, Button, Tag, Typography, Space, Tooltip, Badge,
  Popconfirm, message, Select,
} from "antd";
import {
  SendOutlined, RobotOutlined, ClearOutlined, ToolOutlined,
  ThunderboltOutlined, FullscreenOutlined, FullscreenExitOutlined,
  SettingOutlined, QuestionCircleOutlined, LoadingOutlined,
} from "@ant-design/icons";
import { chatStore, getConversationMessages, skillStore, type ChatMessage, type ExecutionStep } from "../../db";
import { createConversation, sendChatMessage, executeSkill as executeSkillApi } from "../../api";
import { useConfig } from "../../config";
import SkillList from "../SkillList";
import type { AgentSkill } from "../../db";

// Extracted sub-components
import ExecutionSteps from "./ExecutionSteps";
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

  // --- Effects (unchanged) ---
  useEffect(() => { const loadSkills = async () => { const skills = await skillStore.getAll(); setAvailableSkills(skills.filter(s => s.enabled)); }; loadSkills(); }, []);
  useEffect(() => { const init = async () => { try { const created = await createConversation(); setConversationId(created.conversation_id); } catch { setConversationId(`conv_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`); } await loadSessions(); }; init(); }, []);
  useEffect(() => { if (conversationId) loadMessages(); }, [conversationId]);
  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  // --- Session management (unchanged) ---
  const loadSessions = async () => { /* same as original */ const allMessages = await chatStore.getAll(); const map = new Map<string, ChatSession>(); allMessages.forEach((msg) => { const session = map.get(msg.conversationId); if (!session) { map.set(msg.conversationId, { id: msg.conversationId, title: `对话 ${msg.conversationId.slice(0, 8)}`, lastMessage: msg.content.slice(0, 50), timestamp: msg.timestamp, messageCount: 1 }); } else { session.messageCount++; if (msg.timestamp > session.timestamp) { session.timestamp = msg.timestamp; session.lastMessage = msg.content.slice(0, 50); } } }); setSessions(Array.from(map.values()).sort((a, b) => b.timestamp - a.timestamp)); };
  const loadMessages = async () => { if (!conversationId) return; const msgs = await getConversationMessages(conversationId); setMessages(msgs); };
  const switchConversation = (id: string) => setConversationId(id);
  const deleteSession = async (sessionId: string) => { const sessionMessages = await getConversationMessages(sessionId); for (const msg of sessionMessages) { if (msg.id) await chatStore.delete(msg.id); } await loadSessions(); if (conversationId === sessionId) newConversation(); message.success("会话已删除"); };
  const newConversation = async () => { try { const created = await createConversation(); setConversationId(created.conversation_id); } catch { setConversationId(`conv_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`); } setMessages([]); };
  const clearChat = async () => { if (messages.length === 0) return; for (const msg of messages) { if (msg.id) await chatStore.delete(msg.id); } setMessages([]); await loadSessions(); message.success("对话已清空"); };

  // --- Autocomplete (unchanged logic, uses extracted dropdown component) ---
  const updateAutocomplete = useCallback((value: string, cursorPos: number) => { const textBeforeCursor = value.slice(0, cursorPos); const commandMatch = textBeforeCursor.match(/^\/([a-zA-Z_]*)$/); if (commandMatch) { const query = commandMatch[1].toLowerCase(); setFilteredCommands(SLASH_COMMANDS.filter(cmd => cmd.name.toLowerCase().startsWith(query))); setAutocompleteType("command"); setShowAutocomplete(true); setSelectedIndex(0); return; } const skillMatch = textBeforeCursor.match(/^\/skill\s+([a-zA-Z0-9_:-]*)$/i); if (skillMatch) { const query = skillMatch[1].toLowerCase(); setFilteredSkills(availableSkills.filter(skill => skill.name.toLowerCase().includes(query))); setAutocompleteType("skill"); setShowAutocomplete(true); setSelectedIndex(0); return; } setShowAutocomplete(false); setAutocompleteType(null); }, [SLASH_COMMANDS, availableSkills]);

  const selectAutocompleteItem = (index: number) => { if (autocompleteType === "command") { const command = filteredCommands[index]; setInput(`/${command.name} `); setShowAutocomplete(false); if (command.name === "skill") { setTimeout(() => { setFilteredSkills(availableSkills); setAutocompleteType("skill"); setShowAutocomplete(availableSkills.length > 0); setSelectedIndex(0); }, 0); } } else if (autocompleteType === "skill") { const skill = filteredSkills[index]; const params = skill.parameters?.filter(p => p.required).map(p => `"${p.name}": "..."`).join(", "); setInput(`/skill ${skill.name}${params ? ` {${params}}` : ""}`); setShowAutocomplete(false); } setTimeout(() => textareaRef.current?.focus(), 0); };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => { setInput(e.target.value); updateAutocomplete(e.target.value, e.target.selectionStart); };
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => { if (!showAutocomplete) { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } return; } switch (e.key) { case "ArrowDown": e.preventDefault(); setSelectedIndex(prev => (prev + 1) % (autocompleteType === "command" ? filteredCommands.length : filteredSkills.length)); break; case "ArrowUp": e.preventDefault(); setSelectedIndex(prev => (prev - 1 + (autocompleteType === "command" ? filteredCommands.length : filteredSkills.length)) % (autocompleteType === "command" ? filteredCommands.length : filteredSkills.length)); break; case "Enter": case "Tab": e.preventDefault(); selectAutocompleteItem(selectedIndex); break; case "Escape": e.preventDefault(); setShowAutocomplete(false); break; } };

  // --- Send & Skill execution (unchanged) ---
  const addSystemMessage = async (content: string) => { const m: ChatMessage = { conversationId, agentId, role: "assistant", content, timestamp: Date.now(), mode: "system" }; await chatStore.add(m); setMessages(prev => [...prev, m]); };
  const showHelpMessage = async () => { await addSystemMessage(`📚 **可用命令列表**\n\n${SLASH_COMMANDS.map(cmd => `\n**/${cmd.name}** - ${cmd.description}\n${cmd.usage ? `\`\`\`${cmd.usage}\`\`\`` : ""}`).join("\n")}\n\n💡 **提示**\n- 输入 "/" 查看所有可用命令\n- 输入 "/skill " 查看所有可用技能\n- 使用 ↑↓ 选择，↵ 或 Tab 确认，Esc 关闭`); };
  const showSettingsMessage = async () => { await addSystemMessage(`⚙️ **当前配置**\n\n| 配置项 | 状态 |\n|--------|------|\n| AI 功能 | ${config.llm.enabled ? "✅ 已启用" : "❌ 未启用"} |\n| 模型 | ${config.llm.model || "未配置"} |\n| GitHub Token | ${config.githubToken ? "✅ 已配置" : "❌ 未配置"} |\n| 可用技能 | ${availableSkills.length} 个 |\n\n${!config.llm.enabled ? "\n⚠️ 请在设置页面配置大模型 API" : ""}`); };

  const generateExecutionSteps = (skillName: string): ExecutionStep[] => [
    { id: "1", name: "参数解析", description: "解析输入参数", status: "pending", icon: "tool" },
    { id: "2", name: "权限检查", description: "验证执行权限", status: "pending", icon: "shield" },
    { id: "3", name: "环境准备", description: "初始化执行环境", status: "pending", icon: "setting" },
    { id: "4", name: "执行 Skill", description: `运行 ${skillName}`, status: "pending", icon: "play" },
    { id: "5", name: "结果处理", description: "处理执行结果", status: "pending", icon: "result" },
  ];
  const updateStepStatus = (steps: ExecutionStep[], stepId: string, status: ExecutionStep["status"], progress?: number): ExecutionStep[] => steps.map(step => step.id === stepId ? { ...step, status, progress, startTime: status === "running" ? Date.now() : step.startTime, endTime: status === "completed" || status === "failed" ? Date.now() : step.endTime } : step);
  const simulateDelay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));
  const updateMessageSteps = async (msg: ChatMessage, steps: ExecutionStep[]) => { const updated = { ...msg, steps }; await chatStore.update(updated); setMessages(prev => prev.map(m => m.timestamp === msg.timestamp ? updated : m)); };

  const executeSkill = async (skillName: string, params: any) => { const steps = generateExecutionSteps(skillName); const sysMsg: ChatMessage = { conversationId, agentId, role: "assistant", content: `正在执行 Skill: ${skillName}...`, timestamp: Date.now(), mode: "skill", skills: [skillName], steps }; await chatStore.add(sysMsg); setMessages(prev => [...prev, sysMsg]); try { let cs = updateStepStatus(steps, "1", "running", 50); updateMessageSteps(sysMsg, cs); await simulateDelay(300); cs = updateStepStatus(cs, "1", "completed", 100); updateMessageSteps(sysMsg, cs); cs = updateStepStatus(cs, "2", "running", 50); updateMessageSteps(sysMsg, cs); await simulateDelay(400); cs = updateStepStatus(cs, "2", "completed", 100); updateMessageSteps(sysMsg, cs); cs = updateStepStatus(cs, "3", "running", 50); updateMessageSteps(sysMsg, cs); await simulateDelay(500); cs = updateStepStatus(cs, "3", "completed", 100); updateMessageSteps(sysMsg, cs); cs = updateStepStatus(cs, "4", "running", 30); updateMessageSteps(sysMsg, cs); const skillDef = await skillStore.get(skillName); const execution = await executeSkillApi(skillName, params ?? {}, skillDef ? (skillDef as unknown as Record<string, unknown>) : undefined, conversationId); cs = updateStepStatus(cs, "4", "completed", 100); updateMessageSteps(sysMsg, cs); if (onExecuteSkill) onExecuteSkill(skillName, params); cs = updateStepStatus(cs, "5", "running", 50); updateMessageSteps(sysMsg, cs); await simulateDelay(300); const body = execution.result && Object.keys(execution.result).length > 0 ? execution.result : { message: execution.message, mode: execution.mode, error: execution.error ?? null }; cs = updateStepStatus(cs, "5", execution.success ? "completed" : "failed", 100); const resultMsg: ChatMessage = { conversationId, agentId, role: "assistant", content: `${execution.success ? "✅" : "❌"} Skill "${skillName}" ${execution.success ? "执行完成" : "执行失败"}！\n\n\`\`\`json\n${JSON.stringify(body, null, 2)}\n\`\`\``, timestamp: Date.now(), mode: execution.success ? "skill_result" : "skill_error", skills: [skillName], steps: cs }; await chatStore.add(resultMsg); setMessages(prev => [...prev, resultMsg]); if (!execution.success) message.error(execution.error || execution.message || "Skill 执行失败"); } catch (error) { const failedSteps = steps.map(s => ({ ...s, status: (s.id === "4" ? "failed" : s.status === "completed" ? "completed" : "pending") as ExecutionStep["status"] })); const resultMsg: ChatMessage = { conversationId, agentId, role: "assistant", content: `❌ Skill "${skillName}" 执行失败：${String(error)}`, timestamp: Date.now(), mode: "skill_error", skills: [skillName], steps: failedSteps }; await chatStore.add(resultMsg); setMessages(prev => [...prev, resultMsg]); message.error("Skill 执行失败: " + String(error)); } };

  const handleSlashCommand = async (content: string): Promise<boolean> => { const parts = content.slice(1).split(/\s+/); const command = parts[0].toLowerCase(); const args = parts.slice(1).join(" "); switch (command) { case "help": await showHelpMessage(); return true; case "clear": await clearChat(); return true; case "settings": await showSettingsMessage(); return true; } const matchedSkill = availableSkills.find(s => s.name.replace(/_/g, "").toLowerCase() === command); if (matchedSkill) { let params: Record<string, any> = {}; if (args) { try { params = JSON.parse(args); } catch { const firstRequiredParam = matchedSkill.parameters?.find(p => p.required); params = firstRequiredParam ? { [firstRequiredParam.name]: args } : { query: args }; } } await executeSkill(matchedSkill.name, params); return true; } return false; };

  const handleSend = async () => { if (!input.trim()) return; const content = input.trim(); setInput(""); setShowAutocomplete(false); setLoading(true); let currentConversationId = conversationId; if (!currentConversationId) { try { const created = await createConversation(); currentConversationId = created.conversation_id; setConversationId(currentConversationId); } catch (error) { message.error("创建会话失败: " + String(error)); setLoading(false); return; } } const userMessage: ChatMessage = { conversationId: currentConversationId, agentId, role: "user", content, timestamp: Date.now() }; await chatStore.add(userMessage); setMessages(prev => [...prev, userMessage]); try { if (content.startsWith("/")) { const handled = await handleSlashCommand(content); if (handled) { setLoading(false); await loadSessions(); return; } } const skillMatch = content.match(/^\/skill\s+([a-zA-Z0-9_:-]+)(.*)?$/); if (skillMatch) { const skillName = skillMatch[1]; const paramsStr = skillMatch[2]?.trim(); let params = {}; if (paramsStr) { try { params = JSON.parse(paramsStr); } catch { params = { query: paramsStr }; } } await executeSkill(skillName, params); } else { let reply; try { reply = await sendChatMessage(currentConversationId, content); } catch (error: any) { if (error.message?.includes("conversation not found")) { const created = await createConversation(); currentConversationId = created.conversation_id; setConversationId(currentConversationId); userMessage.conversationId = currentConversationId; reply = await sendChatMessage(currentConversationId, content); } else { throw error; } } const aiMessage: ChatMessage = { conversationId: currentConversationId, agentId, role: "assistant", content: reply.reply, timestamp: Date.now(), mode: reply.mode, metadata: { warning: reply.warning, model: reply.model } }; await chatStore.add(aiMessage); setMessages(prev => [...prev, aiMessage]); } } catch (error) { message.error("发送失败: " + String(error)); } finally { setLoading(false); await loadSessions(); } };

  const handleSkillSelect = (skill: AgentSkill) => { const params = skill.parameters ? skill.parameters.filter(p => p.required).map(p => `"${p.name}": "..."`).join(", ") : ""; setInput(`/skill ${skill.name}${params ? ` {${params}}` : ""}`); setShowSkillPanel(false); };
  const handleExampleClick = (query: string) => { setInput(query); setTimeout(() => handleSend(), 100); };

  return (
    <Card className="ai-chat-card" bordered={false}
      style={{ borderRadius: 12, background: "#ffffff", boxShadow: "0 1px 3px rgba(0,0,0,0.05), 0 1px 2px rgba(0,0,0,0.03)", border: "1px solid #e5e7eb" }}
      title={<Space size={10}><div style={{ width: 36, height: 36, borderRadius: 10, background: "#22c55e", display: "flex", alignItems: "center", justifyContent: "center" }}><RobotOutlined style={{ color: "#fff", fontSize: 18 }} /></div><span style={{ fontWeight: 600, fontSize: 16, color: "#111827" }}>AI 助手</span>{!config.llm.enabled && <Tag color="warning" style={{ borderRadius: 4, fontSize: 11, fontWeight: 500 }}>AI 未启用</Tag>}</Space>}
      extra={
        <Space size={6}>
          <Tooltip title={isFullscreen ? "退出全屏" : "全屏"}><Button type="text" size="small" icon={isFullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />} onClick={() => setIsFullscreen(prev => !prev)} style={{ borderRadius: 8, width: 32, height: 32 }} /></Tooltip>
          <Tooltip title="Skill 列表"><Button type={showSkillPanel ? "primary" : "text"} size="small" icon={<ToolOutlined />} onClick={() => setShowSkillPanel(!showSkillPanel)} style={{ borderRadius: 8, width: 32, height: 32 }} /></Tooltip>
          <Tooltip title="新对话"><Button size="small" icon={<ThunderboltOutlined />} onClick={newConversation} data-testid="new-conversation-button" style={{ borderRadius: 8, width: 32, height: 32 }} /></Tooltip>
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
              <TextArea ref={textareaRef} value={input} onChange={handleInputChange} onKeyDown={handleKeyDown} placeholder="输入消息... 使用 / 查看命令" rows={2} style={{ flex: 1, resize: "none", borderRadius: 6, border: "1px solid #d1d5db", background: "#ffffff", padding: "10px 14px", fontSize: 14, lineHeight: 1.5 }} />
              <Button type="default" icon={loading ? <LoadingOutlined /> : <SendOutlined />} onClick={handleSend} loading={loading} disabled={!input.trim()} style={{ height: "auto", minWidth: 56, fontSize: 13, borderRadius: 6, background: "#ffffff", border: "1px solid #22c55e", color: "#22c55e" }}>发送</Button>
            </div>
            <div style={{ marginTop: 8, fontSize: 11 }}>
              <Text style={{ color: "#9ca3af" }}>可用命令: <code style={{ padding: "1px 4px", borderRadius: 4, background: "#f3f4f6", color: "#374151", fontSize: 10 }}>/skill</code> <code style={{ padding: "1px 4px", borderRadius: 4, background: "#f3f4f6", color: "#374151", fontSize: 10 }}>/help</code> <code style={{ padding: "1px 4px", borderRadius: 4, background: "#f3f4f6", color: "#374151", fontSize: 10 }}>/clear</code> <code style={{ padding: "1px 4px", borderRadius: 4, background: "#f3f4f6", color: "#374151", fontSize: 10 }}>/settings</code></Text>
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
    </Card>
  );
}
```

- [ ] **Step 2: 删除 AIChat 中已提取的旧代码（ExecutionSteps 内联定义、空状态的旧 JSX、自动补全旧 JSX、会话面板旧 JSX、消息列表旧内联渲染）**

这一步在 Step 1 的重写中已完成 — 新的 `index.tsx` 不再包含这些内联渲染代码。所有渲染已委托给子组件。

- [ ] **Step 3: 验证编译通过**
Run: `cd /Users/cc11001100/github/typo-master/typo-master/app/frontend && npx tsc --noEmit --pretty 2>&1 | head -30`
Expected:
  - Exit code: 0
  - Output does NOT contain: "error TS" for any of the extracted component files

- [ ] **Step 4: 验证开发服务器启动正常**
Run: `cd /Users/cc11001100/github/typo-master/typo-master/app/frontend && timeout 15 npx vite build --mode development 2>&1 | tail -10`
Expected:
  - Exit code: 0
  - Output does NOT contain: "error" or "failed"

- [ ] **Step 5: 提交**
Run: `cd /Users/cc11001100/github/typo-master/typo-master && git add app/frontend/src/components/AIChat/index.tsx && git commit -m "refactor(frontend): rewrite AIChat to compose extracted sub-components"`

---

### Task 6: Fix stub functions in Workspace.tsx

**Depends on:** Task 5 (AIChat refactor should be done first to avoid merge conflicts)
**Files:**
- Modify: `app/frontend/src/pages/Workspace.tsx:205-216`

- [ ] **Step 1: 替换 handleExecuteSkill stub — 连接到实际 Skill 执行 API**
文件: `app/frontend/src/pages/Workspace.tsx:205-209`（替换整个 handleExecuteSkill 函数）

```typescript
// 替换 app/frontend/src/pages/Workspace.tsx:205-209
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
```

- [ ] **Step 2: 替换 handleTriggerExecute stub — 连接到实际对话 API**
文件: `app/frontend/src/pages/Workspace.tsx:212-216`（替换整个 handleTriggerExecute 函数）

```typescript
// 替换 app/frontend/src/pages/Workspace.tsx:212-216
const handleTriggerExecute = async (triggerId: number, prompt: string) => {
    try {
      const { createConversation, sendChatMessage } = await import("../api");
      const conversation = await createConversation();
      const result = await sendChatMessage(conversation.conversation_id, prompt);
      message.success(`触发器 #${triggerId} 执行完成`);
    } catch (error) {
      message.error(`触发器执行失败: ${String(error)}`);
    }
  };
```

- [ ] **Step 3: 验证编译通过**
Run: `cd /Users/cc11001100/github/typo-master/typo-master/app/frontend && npx tsc --noEmit --pretty 2>&1 | head -20`
Expected:
  - Exit code: 0
  - Output does NOT contain: "Workspace" in error messages

- [ ] **Step 4: 提交**
Run: `cd /Users/cc11001100/github/typo-master/typo-master && git add app/frontend/src/pages/Workspace.tsx && git commit -m "fix(frontend): wire up stub functions in Workspace to actual backend APIs"`
