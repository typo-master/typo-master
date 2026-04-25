# ChatInput 输入框样式优化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: `superpowers:subagent-driven-development`
> Steps use checkbox (`- [ ]`) syntax.

**Goal:** 将聊天输入框从简陋的 inline style TextArea 升级为现代风格的独立 ChatInput 组件，包含圆角胶囊容器、聚焦发光效果、自适应高度、发送按钮动效和命令提示栏优化。

**Architecture:** 用户输入 → ChatInput 组件（封装 TextArea + 发送按钮 + 命令提示） → 通过回调将输入值传给 AIChat 父组件。ChatInput 使用 CSS Modules 管理样式，AutocompleteDropdown 仍由 AIChat 控制（position: relative 在 ChatInput 容器上）。

**Tech Stack:** React 18, TypeScript 5, Ant Design 5 (Input.TextArea, Button), CSS Modules (Vite 5 原生支持)

**Risks:**
- TextArea ref 需通过 forwardRef 传递，确保 AIChat 中的 textareaRef.current?.focus() 仍可用 → 缓解：ChatInput 使用 useImperativeHandle 暴露 focus 方法
- AutocompleteDropdown 定位依赖输入区域的 position: relative → 缓解：ChatInput 根容器保持 position: relative
- 清理 styles.css 旧样式可能影响其他使用 .chat-input-area 的地方 → 缓解：先 grep 确认该 class 仅在 AIChat 使用

---

### Task 1: 创建 ChatInput 组件和 CSS Module

**Depends on:** None
**Files:**
- Create: `app/frontend/src/components/AIChat/ChatInput.module.css`
- Create: `app/frontend/src/components/AIChat/ChatInput.tsx`

- [ ] **Step 1: 创建 ChatInput.module.css — 定义现代输入框样式**

```css
.inputWrapper {
  position: relative;
  flex-shrink: 0;
}

.inputContainer {
  display: flex;
  align-items: flex-end;
  gap: 0;
  border-radius: 16px;
  border: 1.5px solid #e5e7eb;
  background: #ffffff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
  overflow: hidden;
}

.inputContainer:focus-within {
  border-color: #22c55e;
  box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.12), 0 1px 3px rgba(0, 0, 0, 0.04);
}

.textArea {
  flex: 1;
  border: none !important;
  box-shadow: none !important;
  background: transparent !important;
  padding: 12px 16px !important;
  font-size: 14px !important;
  line-height: 1.5 !important;
  resize: none !important;
  border-radius: 0 !important;
  min-height: 48px !important;
}

.textArea:focus {
  border: none !important;
  box-shadow: none !important;
}

.textArea::placeholder {
  color: #9ca3af;
}

.sendButton {
  height: auto !important;
  min-width: 48px !important;
  padding: 8px 16px !important;
  margin: 6px 6px 6px 0 !important;
  border-radius: 12px !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  border: none !important;
  background: #22c55e !important;
  color: #ffffff !important;
  transition: all 0.2s ease !important;
  display: flex !important;
  align-items: center !important;
  gap: 4px !important;
  flex-shrink: 0;
}

.sendButton:hover:not(:disabled) {
  background: #16a34a !important;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(34, 197, 94, 0.3) !important;
}

.sendButton:active:not(:disabled) {
  transform: translateY(0);
}

.sendButton:disabled {
  background: #e5e7eb !important;
  color: #9ca3af !important;
  cursor: not-allowed !important;
}

.sendButtonLoading {
  background: #f3f4f6 !important;
  color: #22c55e !important;
}

.commandBar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px 8px;
  font-size: 11px;
  color: #9ca3af;
}

.commandTag {
  padding: 1px 6px;
  border-radius: 4px;
  background: #f3f4f6;
  color: #374151;
  font-size: 10px;
  font-family: "SF Mono", "Fira Code", monospace;
  cursor: pointer;
  transition: background 0.15s ease;
}

.commandTag:hover {
  background: #e5e7eb;
}

.shortcutHint {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 4px;
  color: #d1d5db;
  font-size: 10px;
}

.shortcutKey {
  padding: 1px 5px;
  border-radius: 3px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  font-size: 10px;
  font-family: monospace;
  color: #9ca3af;
}
```

- [ ] **Step 2: 创建 ChatInput.tsx — 封装输入框、发送按钮和命令提示栏**

```typescript
import { forwardRef, useImperativeHandle, useRef } from "react";
import { Input, Button } from "antd";
import { SendOutlined, LoadingOutlined } from "@ant-design/icons";
import styles from "./ChatInput.module.css";

const { TextArea } = Input;

export interface ChatInputHandle {
  focus: () => void;
}

interface ChatInputProps {
  value: string;
  onChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  onKeyDown: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  onSend: () => void;
  loading: boolean;
  placeholder?: string;
  commands?: string[];
  onCommandClick?: (cmd: string) => void;
}

const ChatInput = forwardRef<ChatInputHandle, ChatInputProps>(
  ({ value, onChange, onKeyDown, onSend, loading, placeholder = "输入消息... 使用 / 查看命令", commands = ["skill", "help", "clear", "settings"], onCommandClick }, ref) => {
    const textAreaRef = useRef<HTMLTextAreaElement>(null);

    useImperativeHandle(ref, () => ({
      focus: () => textAreaRef.current?.focus(),
    }));

    const handleCommandClick = (cmd: string) => {
      if (onCommandClick) {
        onCommandClick(cmd);
      } else {
        onChange({ target: { value: `/${cmd} ` } } as React.ChangeEvent<HTMLTextAreaElement>);
        textAreaRef.current?.focus();
      }
    };

    return (
      <div className={styles.inputWrapper}>
        <div className={styles.inputContainer}>
          <TextArea
            ref={textAreaRef}
            value={value}
            onChange={onChange}
            onKeyDown={onKeyDown}
            placeholder={placeholder}
            autoSize={{ minRows: 1, maxRows: 6 }}
            className={styles.textArea}
          />
          <Button
            type="default"
            icon={loading ? <LoadingOutlined /> : <SendOutlined />}
            onClick={onSend}
            loading={loading}
            disabled={!value.trim()}
            className={`${styles.sendButton} ${loading ? styles.sendButtonLoading : ""}`}
          />
        </div>
        <div className={styles.commandBar}>
          {commands.map(cmd => (
            <span key={cmd} className={styles.commandTag} onClick={() => handleCommandClick(cmd)}>
              /{cmd}
            </span>
          ))}
          <span className={styles.shortcutHint}>
            <span className={styles.shortcutKey}>Enter</span> 发送
            <span className={styles.shortcutKey}>Shift+Enter</span> 换行
          </span>
        </div>
      </div>
    );
  }
);

ChatInput.displayName = "ChatInput";

export default ChatInput;
```

- [ ] **Step 3: 验证 ChatInput 组件编译**
Run: `cd /Users/cc11001100/github/typo-master/typo-master/app/frontend && npx tsc --noEmit --pretty 2>&1 | head -20`
Expected:
  - Exit code: 0
  - Output does NOT contain: "error TS"

- [ ] **Step 4: 提交**
Run: `git add app/frontend/src/components/AIChat/ChatInput.module.css app/frontend/src/components/AIChat/ChatInput.tsx && git commit -m "feat(frontend): add ChatInput component with modern styling"`

---

### Task 2: 将 ChatInput 集成到 AIChat 组件

**Depends on:** Task 1
**Files:**
- Modify: `app/frontend/src/components/AIChat/index.tsx:32-38`（添加 import）
- Modify: `app/frontend/src/components/AIChat/index.tsx:74`（替换 textareaRef 为 chatInputRef）
- Modify: `app/frontend/src/components/AIChat/index.tsx:230`（更新 focus 调用）
- Modify: `app/frontend/src/components/AIChat/index.tsx:547-586`（替换输入区域为 ChatInput 组件）

- [ ] **Step 1: 添加 ChatInput import — 引入新组件和类型**
文件: `app/frontend/src/components/AIChat/index.tsx:32-35`

```typescript
// Extracted sub-components
import ChatEmptyState from "./ChatEmptyState";
import AutocompleteDropdown, { type SlashCommand, type AutocompleteType } from "./AutocompleteDropdown";
import SessionSidebar, { type ChatSession } from "./SessionSidebar";
import MessageList from "./MessageList";
import ChatInput, { type ChatInputHandle } from "./ChatInput";
```

- [ ] **Step 2: 替换 textareaRef 为 chatInputRef — 使用 ChatInputHandle 类型**
文件: `app/frontend/src/components/AIChat/index.tsx:74`

```typescript
  const chatInputRef = useRef<ChatInputHandle>(null);
```

- [ ] **Step 3: 更新 focus 调用 — 使用 chatInputRef 的 focus 方法**
文件: `app/frontend/src/components/AIChat/index.tsx:230`

```typescript
    setTimeout(() => chatInputRef.current?.focus(), 0);
```

- [ ] **Step 4: 替换输入区域为 ChatInput 组件 — 用新组件替换 inline style 的 TextArea**
文件: `app/frontend/src/components/AIChat/index.tsx:547-586`

```tsx
          {/* Input area */}
          <ChatInput
            ref={chatInputRef}
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            onSend={handleSend}
            loading={loading}
            onCommandClick={(cmd) => {
              setInput(`/${cmd} `);
              chatInputRef.current?.focus();
            }}
          />
```

注意：AutocompleteDropdown 的定位需要在 ChatInput 的 inputWrapper 之上，所以 AutocompleteDropdown 仍保留在 ChatInput 外面，紧邻 ChatInput 渲染：

文件: `app/frontend/src/components/AIChat/index.tsx:547` 之前插入 AutocompleteDropdown

```tsx
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
            <ChatInput
              ref={chatInputRef}
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              onSend={handleSend}
              loading={loading}
              onCommandClick={(cmd) => {
                setInput(`/${cmd} `);
                chatInputRef.current?.focus();
              }}
            />
          </div>
```

- [ ] **Step 5: 验证 AIChat 编译和构建**
Run: `cd /Users/cc11001100/github/typo-master/typo-master/app/frontend && npx tsc --noEmit --pretty 2>&1 | head -20`
Expected:
  - Exit code: 0
  - Output does NOT contain: "error TS"

- [ ] **Step 6: 提交**
Run: `git add app/frontend/src/components/AIChat/index.tsx && git commit -m "refactor(frontend): integrate ChatInput component into AIChat"`

---

### Task 3: 清理旧的全局输入框样式

**Depends on:** Task 2
**Files:**
- Modify: `app/frontend/src/styles.css:494-508`（删除 .chat-input-area 相关样式）
- Modify: `app/frontend/src/styles.css:1451-1458`（删除 .ai-chat-card textarea:focus 和 .ant-btn-primary:hover 旧样式）

- [ ] **Step 1: 确认 .chat-input-area 仅被 AIChat 使用**
Run: `cd /Users/cc11001100/github/typo-master/typo-master && grep -rn "chat-input-area" app/frontend/src/`
Expected:
  - Output contains: only references in styles.css (no component uses this class anymore)

- [ ] **Step 2: 删除 .chat-input-area 样式块 — 已被 ChatInput.module.css 替代**
文件: `app/frontend/src/styles.css:494-508`

删除以下内容：

```css
/* 输入区域 */
.chat-input-area {
  padding-top: 12px;
  border-top: 1px solid var(--line);
}

.chat-input-area .ant-input {
  border-radius: 4px;
  border-color: var(--line);
  resize: none;
}

.chat-input-area .ant-input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px rgba(34, 197, 94, 0.1);
}
```

- [ ] **Step 3: 删除 .ai-chat-card textarea:focus 和 .ant-btn-primary:hover 旧样式 — 已被 ChatInput.module.css 替代**
文件: `app/frontend/src/styles.css:1451-1458`

删除以下内容：

```css
/* 输入框聚焦效果 */
.ai-chat-card textarea:focus {
  border-color: #22c55e !important;
  box-shadow: 0 0 0 2px rgba(34,197,94,0.1) !important;
}

/* 发送按钮悬停 */
.ai-chat-card .ant-btn-primary:hover {
  background: #16a34a !important;
}
```

- [ ] **Step 4: 验证构建和页面渲染**
Run: `cd /Users/cc11001100/github/typo-master/typo-master/app/frontend && npx vite build 2>&1 | tail -5`
Expected:
  - Exit code: 0
  - Output contains: "built in"

- [ ] **Step 5: 提交**
Run: `git add app/frontend/src/styles.css && git commit -m "chore(frontend): remove legacy chat input global styles replaced by CSS Modules"`
