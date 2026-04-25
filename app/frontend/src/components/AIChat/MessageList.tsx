import { Avatar, List, Space, Tag, Typography } from "antd";
import { RobotOutlined, ToolOutlined } from "@ant-design/icons";

const { Paragraph } = Typography;
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
