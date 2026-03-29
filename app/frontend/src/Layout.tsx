import { Outlet, Link, useLocation } from "react-router-dom";
import {
  Layout,
  Menu,
  Avatar,
  Typography,
  Space,
  Button,
  Badge,
  Tooltip,
} from "antd";
import {
  HomeOutlined,
  DashboardOutlined,
  SettingOutlined,
  RobotOutlined,
  ThunderboltOutlined,
  GithubOutlined,
  ApiOutlined,
  BookOutlined,
} from "@ant-design/icons";
import { useConfig } from "./config";

const { Header, Content } = Layout;
const { Title, Text } = Typography;

export default function MainLayout() {
  const location = useLocation();
  const { config } = useConfig();
  const isWorkspaceRoute = location.pathname.startsWith("/workspace");
  const selectedMenuKey = location.pathname.startsWith("/workspace")
    ? "/workspace"
    : location.pathname.startsWith("/settings")
      ? "/settings"
      : location.pathname.startsWith("/docs")
        ? "/docs"
        : "/";

  const menuItems = [
    {
      key: "/",
      icon: <HomeOutlined />,
      label: <Link to="/">首页</Link>,
    },
    {
      key: "/workspace",
      icon: <DashboardOutlined />,
      label: <Link to="/workspace">工作台</Link>,
    },
    {
      key: "/docs",
      icon: <BookOutlined />,
      label: <Link to="/docs">对接文档</Link>,
    },
    {
      key: "/settings",
      icon: <SettingOutlined />,
      label: <Link to="/settings">设置</Link>,
    },
  ];

  return (
    <Layout className={`page-layout${isWorkspaceRoute ? " page-layout-workspace" : ""}`}>
      {/* 顶部导航栏 */}
      <Header className="main-header">
        <div className="header-brand">
          <Avatar
            size={40}
            icon={<RobotOutlined />}
            style={{ background: "#166534", border: "1px solid #86efac" }}
          />
          <div className="brand-text">
            <Title level={5} className="brand-title">
              <ThunderboltOutlined /> Typo Master
            </Title>
            <Text className="brand-subtitle">Agent Automation Console</Text>
          </div>
        </div>

        <Menu
          mode="horizontal"
          selectedKeys={[selectedMenuKey]}
          items={menuItems}
          className="main-menu"
          style={{ flex: 1, minWidth: 0, border: "none", background: "transparent" }}
        />

        <div className="header-actions">
          <Space size={12}>
            {/* LLM 状态指示 */}
            <Badge
              status={config.llm.enabled ? "success" : "default"}
              text={
                <span style={{ color: "#ecfdf5", fontSize: 12, fontWeight: 500 }}>
                  <ApiOutlined /> {config.llm.enabled ? "AI 已启用" : "AI 未启用"}
                </span>
              }
            />
            {/* GitHub 徽标 */}
            <Tooltip title="去 GitHub star 支持我们" placement="bottom">
              <a
                href="https://github.com/cc11001100/typo-master"
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: "flex",
                  alignItems: "center",
                  color: "#ecfdf5",
                  fontSize: 20,
                  transition: "color 0.3s",
                }}
                className="github-link"
              >
                <GithubOutlined />
              </a>
            </Tooltip>
          </Space>
        </div>
      </Header>

      <Content className={`main-content${isWorkspaceRoute ? " main-content-workspace" : ""}`}>
        <Outlet />
      </Content>

      {/* 页脚 */}
      <footer className="main-footer">
        <Text type="secondary" style={{ fontSize: 12 }}>
          © 2024 Typo Master · Intelligent Code Quality Agent Platform
        </Text>
      </footer>
    </Layout>
  );
}
