import { createContext, useContext, useEffect, useState } from "react";

// 配置类型
export interface LLMConfig {
  enabled: boolean;
  baseUrl: string;
  model: string;
  apiKey: string;
  timeout: number;
  maxOutputTokens: number;
}

export interface AppConfig {
  llm: LLMConfig;
  githubToken: string;
  permissions: Record<string, boolean>;
}

// 默认配置
export const defaultConfig: AppConfig = {
  llm: {
    enabled: true,
    baseUrl: "https://ai.last.ee/v1",
    model: "gpt-5.4",
    apiKey: "sk-14542413024fcbcc0cc6f6bd725bf2fca3449c8596a48bb030dfcf2bad6582f6",
    timeout: 30,
    maxOutputTokens: 300,
  },
  githubToken: "",
  permissions: {},
};

// 配置上下文
interface ConfigContextType {
  config: AppConfig;
  updateConfig: (config: AppConfig) => void;
  updateLLMConfig: (llmConfig: LLMConfig) => void;
}

const ConfigContext = createContext<ConfigContextType | undefined>(undefined);

export function ConfigProvider({ children }: { children: React.ReactNode }) {
  const [config, setConfig] = useState<AppConfig>(defaultConfig);

  useEffect(() => {
    // 从 localStorage 加载配置
    const saved = localStorage.getItem("typo-hunter-config");
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        setConfig({ ...defaultConfig, ...parsed });
      } catch {
        console.error("Failed to parse config");
      }
    }
  }, []);

  const updateConfig = (newConfig: AppConfig) => {
    setConfig(newConfig);
    localStorage.setItem("typo-hunter-config", JSON.stringify(newConfig));
  };

  const updateLLMConfig = (llmConfig: LLMConfig) => {
    const newConfig = { ...config, llm: llmConfig };
    updateConfig(newConfig);
  };

  return (
    <ConfigContext.Provider value={{ config, updateConfig, updateLLMConfig }}>
      {children}
    </ConfigContext.Provider>
  );
}

export function useConfig() {
  const context = useContext(ConfigContext);
  if (!context) {
    throw new Error("useConfig must be used within ConfigProvider");
  }
  return context;
}
