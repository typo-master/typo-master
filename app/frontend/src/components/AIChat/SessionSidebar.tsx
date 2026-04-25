import { Button, Empty, Popconfirm, Space, Tooltip, Typography } from "antd";
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
