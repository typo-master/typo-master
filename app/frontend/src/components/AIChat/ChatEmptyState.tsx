import { Typography } from "antd";
import {
  ArrowRightOutlined,
  BulbOutlined,
  RobotOutlined,
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
