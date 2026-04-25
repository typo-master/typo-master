import { useEffect, useState } from "react";
import { Spin, Typography, Result, Button } from "antd";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

const { Text } = Typography;

export default function AuthCallbackPage() {
  const navigate = useNavigate();
  const { setAuth } = useAuth();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    const state = params.get("state");

    if (!code) {
      setError("未收到 GitHub 授权码，请重试");
      return;
    }

    const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:50120";
    fetch(`${BASE_URL}/api/v1/auth/github/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state || "")}`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        if (data.success && data.token && data.user) {
          setAuth(data.token, data.user);
          navigate("/workspace/chat", { replace: true });
        } else {
          setError(data.detail || "登录失败，请重试");
        }
      })
      .catch((err) => {
        setError(`登录失败: ${err.message}`);
      });
  }, [navigate, setAuth]);

  if (error) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "60vh" }}>
        <Result
          status="error"
          title="登录失败"
          subTitle={error}
          extra={
            <Button type="primary" onClick={() => navigate("/")}>
              返回首页
            </Button>
          }
        />
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", minHeight: "60vh", gap: 16 }}>
      <Spin size="large" />
      <Text type="secondary">正在完成 GitHub 登录...</Text>
    </div>
  );
}
