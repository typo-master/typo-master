import { Modal, Button, Typography } from "antd";
import { GithubOutlined, LockOutlined } from "@ant-design/icons";
import { useAuth } from "../../contexts/AuthContext";
import styles from "./index.module.css";

const { Title, Text, Paragraph } = Typography;

interface LoginModalProps {
  open: boolean;
  onClose: () => void;
  reason?: string;
}

export default function LoginModal({ open, onClose, reason }: LoginModalProps) {
  const { login } = useAuth();

  return (
    <Modal
      open={open}
      onCancel={onClose}
      footer={null}
      centered
      width={420}
      className={styles.loginModal}
    >
      <div className={styles.loginContent}>
        <div className={styles.loginIcon}>
          <LockOutlined />
        </div>
        <Title level={4} className={styles.loginTitle}>
          登录以继续
        </Title>
        {reason && (
          <Paragraph type="secondary" className={styles.loginReason}>
            {reason}
          </Paragraph>
        )}
        <Paragraph type="secondary" className={styles.loginDesc}>
          AI 对话功能需要登录后使用，登录后可享受完整的智能助手体验
        </Paragraph>
        <Button
          type="primary"
          size="large"
          block
          icon={<GithubOutlined />}
          onClick={login}
          className={styles.githubButton}
        >
          使用 GitHub 登录
        </Button>
        <Text type="secondary" className={styles.loginNote}>
          登录即表示您同意我们的服务条款和隐私政策
        </Text>
      </div>
    </Modal>
  );
}
