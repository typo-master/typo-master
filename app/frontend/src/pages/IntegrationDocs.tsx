import { useState } from "react";
import {
  Card,
  Typography,
  Tabs,
  Alert,
  Steps,
  Divider,
  Space,
  Tag,
  Button,
  message,
  Collapse,
  Table,
  Badge,
  Timeline,
} from "antd";
import {
  ApiOutlined,
  CodeOutlined,
  ThunderboltOutlined,
  LinkOutlined,
  GlobalOutlined,
  RobotOutlined,
  CopyOutlined,
  CheckCircleOutlined,
  MessageOutlined,
  BugOutlined,
  SafetyOutlined,
  RocketOutlined,
  FileTextOutlined,
} from "@ant-design/icons";

const { Title, Paragraph, Text, Link } = Typography;
const { Panel } = Collapse;

// 代码复制组件
const CodeBlock = ({ code, language = "bash" }: { code: string; language?: string }) => {
  const copyToClipboard = () => {
    navigator.clipboard.writeText(code);
    message.success("已复制到剪贴板");
  };

  return (
    <div style={{ position: "relative", margin: "16px 0" }}>
      <div
        style={{
          position: "absolute",
          top: "0",
          left: "0",
          right: "0",
          padding: "4px 16px",
          background: "#2d2d2d",
          borderRadius: "4px 4px 0 0",
          fontSize: "11px",
          color: "#888",
          textTransform: "uppercase",
        }}
      >
        {language}
      </div>
      <pre
        style={{
          background: "#1e1e1e",
          color: "#d4d4d4",
          padding: "32px 16px 16px",
          borderRadius: "4px",
          overflow: "auto",
          fontSize: "13px",
          lineHeight: "1.5",
          margin: 0,
        }}
      >
        <code>{code}</code>
      </pre>
      <Button
        size="small"
        icon={<CopyOutlined />}
        onClick={copyToClipboard}
        style={{
          position: "absolute",
          top: "28px",
          right: "8px",
          background: "rgba(255,255,255,0.1)",
          border: "none",
          color: "#fff",
        }}
      >
        复制
      </Button>
    </div>
  );
};

// 端点状态徽章
const EndpointStatus = ({ status }: { status: "online" | "offline" | "testing" }) => {
  const statusMap = {
    online: { color: "green", text: "运行中" },
    offline: { color: "red", text: "离线" },
    testing: { color: "blue", text: "测试" },
  };
  return <Badge status={statusMap[status].color as any} text={statusMap[status].text} />;
};

// MCP Tools 列表
const mcpTools = [
  {
    name: "typoagent_chat",
    description: "与 TypoAgent 进行对话，获取智能回复",
    params: '{"message": "你好", "conversation_id": "可选"}',
  },
  {
    name: "typoagent_execute_skill",
    description: "执行 TypoAgent 的 Skill",
    params: '{"skill_name": "scan_typo", "params": {...}}',
  },
  {
    name: "typoagent_list_skills",
    description: "列出所有可用的 Skills",
    params: '{"category": "可选，按类别筛选"}',
  },
  {
    name: "typoagent_run_workflow",
    description: "运行 Agent 工作流",
    params: '{"workflow": "single_project", "owner": "...", "repo": "..."}',
  },
  {
    name: "typoagent_get_capabilities",
    description: "获取 Agent 的能力信息",
    params: "{}",
  },
  {
    name: "typoagent_execute_mcp_tool",
    description: "执行外部 MCP Server 的 Tool",
    params: '{"server_id": "...", "tool_name": "...", "arguments": {...}}',
  },
  {
    name: "typoagent_list_mcp_servers",
    description: "列出配置的 MCP Servers",
    params: "{}",
  },
];

// 错误码对照表
const errorCodes = [
  { code: "-32700", name: "Parse Error", desc: "JSON 解析失败", solution: "检查请求体是否为有效的 JSON" },
  { code: "-32600", name: "Invalid Request", desc: "无效的 JSON-RPC 请求", solution: "确保包含必需的 jsonrpc、method 字段" },
  { code: "-32601", name: "Method Not Found", desc: "请求的方法不存在", solution: "检查 method 名称是否正确" },
  { code: "-32602", name: "Invalid Params", desc: "参数错误或缺失", solution: "检查 params 是否符合工具要求" },
  { code: "-32603", name: "Internal Error", desc: "服务器内部错误", solution: "查看服务器日志获取详细信息" },
  { code: "-32000", name: "Permission Denied", desc: "权限不足", solution: "检查 config.yml 中的权限设置" },
];

// API 列表
const apiList = [
  { method: "GET", endpoint: "/api/v1/health", desc: "健康检查", auth: false },
  { method: "GET", endpoint: "/api/v1/capabilities", desc: "获取 Agent 能力", auth: false },
  { method: "GET", endpoint: "/api/v1/skills", desc: "列出所有 Skills", auth: false },
  { method: "POST", endpoint: "/api/v1/skills/execute", desc: "执行 Skill", auth: false },
  { method: "GET", endpoint: "/api/v1/skills/:name", desc: "获取 Skill 详情", auth: false },
  { method: "PUT", endpoint: "/api/v1/skills/:name", desc: "更新 Skill", auth: false },
  { method: "DELETE", endpoint: "/api/v1/skills/:name", desc: "删除 Skill", auth: false },
  { method: "GET", endpoint: "/api/v1/mcp/servers", desc: "列出 MCP Servers", auth: false },
  { method: "POST", endpoint: "/api/v1/mcp/execute", desc: "执行 MCP Tool", auth: false },
  { method: "POST", endpoint: "/api/v1/mcp/servers/:id/probe", desc: "探测 MCP Server", auth: false },
  { method: "GET", endpoint: "/api/v1/permissions", desc: "获取权限配置", auth: false },
  { method: "PUT", endpoint: "/api/v1/permissions", desc: "更新权限配置", auth: false },
  { method: "POST", endpoint: "/api/v1/conversations", desc: "创建对话", auth: false },
  { method: "POST", endpoint: "/api/v1/conversations/:id/messages", desc: "发送消息", auth: false },
];

export default function IntegrationDocsPage() {
  const [activeTab, setActiveTab] = useState("overview");

  // 代码示例
  const sseCompleteExample = `// 完整的 MCP SSE 客户端实现 (TypeScript)
interface MCPMessage {
  jsonrpc: "2.0";
  id?: number;
  method?: string;
  params?: any;
  result?: any;
  error?: { code: number; message: string };
}

class TypoAgentMCPClient {
  private sessionId: string | null = null;
  private messageEndpoint: string | null = null;
  private eventSource: EventSource | null = null;

  async connect(): Promise<void> {
    this.eventSource = new EventSource('http://localhost:50120/mcp/sse');

    return new Promise((resolve, reject) => {
      // 监听 endpoint 事件
      this.eventSource!.addEventListener('endpoint', (e) => {
        const data = JSON.parse(e.data);
        this.messageEndpoint = 'http://localhost:50120' + data.uri;
        console.log('Message endpoint:', this.messageEndpoint);
      });

      // 监听消息事件
      this.eventSource!.addEventListener('message', (e) => {
        const msg: MCPMessage = JSON.parse(e.data);
        console.log('Received:', msg);

        if (msg.id === 0 && msg.result) {
          // 初始化完成
          resolve();
        }
      });

      this.eventSource!.onerror = (err) => {
        reject(err);
      };
    });
  }

  async callTool(name: string, args: any): Promise<any> {
    const request: MCPMessage = {
      jsonrpc: "2.0",
      id: Date.now(),
      method: "tools/call",
      params: { name, arguments: args }
    };

    const response = await fetch(this.messageEndpoint!, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    });

    return response.json();
  }

  disconnect() {
    this.eventSource?.close();
  }
}

// 使用示例
const client = new TypoAgentMCPClient();
await client.connect();
const result = await client.callTool('typoagent_list_skills', {});
console.log(result);`;

  const pythonFullExample = `#!/usr/bin/env python3
"""完整的 TypoAgent MCP 客户端示例"""

import asyncio
import json
import aiohttp
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class MCPMessage:
    jsonrpc: str = "2.0"
    id: Optional[int] = None
    method: Optional[str] = None
    params: Optional[Dict] = None
    result: Optional[Any] = None
    error: Optional[Dict] = None

class TypoAgentMCPClient:
    def __init__(self, base_url: str = "http://localhost:50120"):
        self.base_url = base_url
        self.session_id: Optional[str] = None
        self.message_endpoint: Optional[str] = None

    async def connect(self) -> None:
        """建立 SSE 连接"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/mcp/sse") as resp:
                # 解析 SSE 事件
                async for line in resp.content:
                    line = line.decode('utf-8').strip()
                    if line.startswith('event: endpoint'):
                        pass  # 下一行是 data
                    elif line.startswith('data:'):
                        data = json.loads(line[5:].strip())
                        if 'uri' in data:
                            self.message_endpoint = self.base_url + data['uri']
                            break
                    elif line.startswith('event: message'):
                        pass  # 等待下一条 data

    async def initialize(self) -> Dict:
        """发送 initialize 请求"""
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "python-mcp-client",
                    "version": "1.0.0"
                }
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.message_endpoint,
                json=init_request
            ) as resp:
                return await resp.json()

    async def call_tool(self, name: str, arguments: Dict) -> Dict:
        """调用 MCP Tool"""
        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": arguments
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.message_endpoint,
                json=request
            ) as resp:
                return await resp.json()

    async def list_tools(self) -> Dict:
        """列出所有可用 Tools"""
        request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/list"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.message_endpoint,
                json=request
            ) as resp:
                return await resp.json()

# 使用示例
async def main():
    client = TypoAgentMCPClient()

    # 1. 连接
    print("Connecting...")
    await client.connect()

    # 2. 初始化
    print("Initializing...")
    await client.initialize()

    # 3. 列出 Tools
    print("\\nListing tools:")
    tools = await client.list_tools()
    print(json.dumps(tools, indent=2, ensure_ascii=False))

    # 4. 调用 Tool
    print("\\nCalling typoagent_list_skills:")
    result = await client.call_tool("typoagent_list_skills", {})
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())`;

  const goExample = `package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
)

type MCPClient struct {
	BaseURL          string
	MessageEndpoint  string
}

func NewMCPClient(baseURL string) *MCPClient {
	return &MCPClient{BaseURL: baseURL}
}

func (c *MCPClient) Connect() error {
	resp, err := http.Get(c.BaseURL + "/mcp/sse")
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	// 读取 SSE 事件
	reader := resp.Body
	buf := make([]byte, 1024)

	for {
		n, err := reader.Read(buf)
		if err != nil {
			break
		}

		lines := string(buf[:n])
		if strings.Contains(lines, "event: endpoint") {
			// 解析 endpoint
			parts := strings.Split(lines, "\\n")
			for _, part := range parts {
				if strings.HasPrefix(part, "data:") {
					data := strings.TrimPrefix(part, "data:")
					var endpoint map[string]string
					json.Unmarshal([]byte(data), &endpoint)
					c.MessageEndpoint = c.BaseURL + endpoint["uri"]
					return nil
				}
			}
		}
	}

	return fmt.Errorf("failed to get endpoint")
}

func (c *MCPClient) CallTool(name string, args map[string]interface{}) (map[string]interface{}, error) {
	reqBody := map[string]interface{}{
		"jsonrpc": "2.0",
		"id":      1,
		"method":  "tools/call",
		"params": map[string]interface{}{
			"name":      name,
			"arguments": args,
		},
	}

	jsonBody, _ := json.Marshal(reqBody)
	resp, err := http.Post(c.MessageEndpoint, "application/json", bytes.NewBuffer(jsonBody))
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	var result map[string]interface{}
	json.Unmarshal(body, &result)

	return result, nil
}

func main() {
	client := NewMCPClient("http://localhost:50120")

	fmt.Println("Connecting...")
	client.Connect()

	fmt.Println("Calling tool...")
	result, _ := client.CallTool("typoagent_list_skills", map[string]interface{}{})
	fmt.Printf("Result: %+v\\n", result)
}`;

  const langchainExample = `# LangChain 集成示例
from langchain.agents import Tool, AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
import requests

# 定义 TypoAgent Tool
def typoagent_skill_executor(skill_name: str, params: dict = None) -> str:
    """通过 REST API 调用 TypoAgent Skill"""
    response = requests.post(
        "http://localhost:50120/api/v1/skills/execute",
        json={
            "skill_name": skill_name,
            "params": params or {}
        }
    )
    result = response.json()
    if result.get("success"):
        return json.dumps(result.get("result", {}), ensure_ascii=False)
    return f"Error: {result.get('error', 'Unknown error')}"

# 创建 LangChain Tools
tools = [
    Tool(
        name="typoagent_scan",
        func=lambda x: typoagent_skill_executor("scan_typo", {"repo_path": x}),
        description="扫描代码仓库中的拼写错误，输入为仓库路径"
    ),
    Tool(
        name="typoagent_fix",
        func=lambda x: typoagent_skill_executor("fix_typo", {"repo_path": x}),
        description="自动修复代码仓库中的拼写错误，输入为仓库路径"
    ),
    Tool(
        name="typoagent_list_skills",
        func=lambda x: typoagent_skill_executor("list_skills", {}),
        description="列出所有可用的 Skills"
    ),
]

# 创建 Agent
prompt = PromptTemplate.from_template("""Answer the following questions as best you can.

You have access to the following tools:
{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}""")

agent = create_react_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# 使用
result = agent_executor.invoke({
    "input": "扫描 ./my-project 仓库的拼写错误并修复它们"
})
print(result)`;

  const webhookExample = `# Webhook 集成配置
# 在 config.yml 中配置 webhook

webhooks:
  - name: "slack_notification"
    url: "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
    events: ["skill.completed", "skill.failed", "workflow.completed"]
    headers:
      Content-Type: "application/json"
    payload_template: |
      {
        "text": "Skill {{skill_name}} {{status}}",
        "blocks": [
          {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": "*{{skill_name}}*\\nStatus: {{status}}\\nResult: {{result}}"
            }
          }
        ]
      }

# 使用 webhook_notify Skill 发送自定义通知
{
  "skill_name": "webhook_notify",
  "params": {
    "url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
    "payload": {
      "text": "扫描完成！",
      "channel": "#alerts"
    }
  }
}`;

  const errorHandlingExample = `// 错误处理最佳实践
try {
  const result = await fetch('http://localhost:50120/api/v1/skills/execute', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      skill_name: 'scan_typo',
      params: { repo_path: './my-project' }
    })
  });

  const data = await result.json();

  if (!data.success) {
    // 处理业务错误
    console.error('Skill execution failed:', data.error);

    // 根据错误类型采取不同策略
    if (data.error?.includes('Permission denied')) {
      // 检查权限配置
      await checkPermissions();
    } else if (data.error?.includes('MCP server not found')) {
      // 检查 MCP 服务器配置
      await checkMCPServers();
    }

    return;
  }

  console.log('Success:', data.result);

} catch (networkError) {
  // 处理网络错误
  if (networkError.name === 'TypeError' && networkError.message.includes('fetch')) {
    console.error('Network error: Is the backend running?');
    console.log('Check: curl http://localhost:50120/api/v1/health');
  }
}`;

  const securityExample = `# 安全配置指南

# 1. 配置文件权限 (config.yml)
permissions:
  git_push: false          # 禁用 Git 推送
  pr_create: false         # 禁用 PR 创建
  issue_create: true       # 允许 Issue 创建
  fs_write: true           # 允许文件写入
  fs_delete: false         # 禁用文件删除
  shell_exec: false        # 禁用 Shell 执行
  api_call: true           # 允许 API 调用
  web_fetch: true          # 允许 Web 抓取

# 2. 使用环境变量存储敏感信息
# .env 文件
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxx

# 3. API 认证 (如果需要)
# 在请求头中添加认证
headers = {
    'Authorization': 'Bearer YOUR_API_TOKEN',
    'Content-Type': 'application/json'
}

# 4. 限制 CORS (app/backend/main.py)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)`;

  const performanceExample = `# 性能优化建议

# 1. 使用连接池
import aiohttp

async with aiohttp.ClientSession(
    connector=aiohttp.TCPConnector(limit=100)
) as session:
    # 复用连接
    pass

# 2. 批量调用 Skills
async def batch_execute(skills: list):
    tasks = [
        execute_skill(skill["name"], skill["params"])
        for skill in skills
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results

# 3. 缓存 Capabilities
capabilities_cache = None
cache_time = 0

async def get_capabilities_cached():
    global capabilities_cache, cache_time
    if time.time() - cache_time < 60:  # 缓存 60 秒
        return capabilities_cache

    capabilities_cache = await fetch_capabilities()
    cache_time = time.time()
    return capabilities_cache

# 4. 使用 SSE 而非轮询
# SSE 连接保持打开状态，服务器推送更新
# 比轮询更高效`;

  const debuggingExample = `# 调试技巧

# 1. 启用详细日志
export TYPOAGENT_LOG_LEVEL=DEBUG

# 2. 检查后端日志
pm2 logs typemaster-backend

# 3. 使用 curl 测试 API
curl -v http://localhost:50120/api/v1/health
curl -X POST http://localhost:50120/api/v1/skills/execute \\
  -H "Content-Type: application/json" \\
  -d '{"skill_name":"scan_typo","params":{"repo_path":"./test"}}'

# 4. 监控 SSE 事件
curl -N http://localhost:50120/mcp/sse 2>&1 | tee sse.log

# 5. 使用浏览器开发者工具
# - Network 面板查看 HTTP 请求
# - Console 查看 JavaScript 错误`;

  const useCasesExample = `// 使用案例：自动化代码审查流程
async function automatedCodeReview(repoPath: string) {
  const steps = [];

  // 1. 扫描拼写错误
  console.log("🔍 扫描拼写错误...");
  const scanResult = await executeSkill("scan_typo", { repo_path: repoPath });
  steps.push({ step: "scan", result: scanResult });

  if (scanResult.success && scanResult.result.typos_found > 0) {
    // 2. 自动修复
    console.log("🔧 修复拼写错误...");
    const fixResult = await executeSkill("fix_typo", { repo_path: repoPath });
    steps.push({ step: "fix", result: fixResult });

    // 3. 创建 PR
    console.log("📤 创建 Pull Request...");
    const prResult = await executeSkill("create_pr", {
      owner: "myorg",
      repo: "myrepo",
      title: "Fix typos",
      branch: "fix/typos"
    });
    steps.push({ step: "pr", result: prResult });

    // 4. 发送通知
    await executeSkill("webhook_notify", {
      url: process.env.SLACK_WEBHOOK_URL,
      payload: {
        text: \`创建了 PR: \${prResult.result.pr_url}\`
      }
    });
  }

  return steps;
}`;

  const openaiExample = `# OpenAI / ChatGPT 插件集成
import openai
import json

# 定义 TypoAgent 函数
functions = [
    {
        "name": "typoagent_execute_skill",
        "description": "执行 TypoAgent Skill",
        "parameters": {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "enum": ["scan_typo", "fix_typo", "create_pr", "ask_ai"]
                },
                "params": { "type": "object" }
            },
            "required": ["skill_name", "params"]
        }
    }
]

# 创建 Chat Completion
response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "你是一个代码质量助手，可以帮助扫描和修复代码中的拼写错误。"},
        {"role": "user", "content": "请扫描 ./my-project 仓库并修复拼写错误"}
    ],
    functions=functions,
    function_call="auto"
)

# 处理函数调用
if response.choices[0].message.get("function_call"):
    func = response.choices[0].message["function_call"]
    args = json.loads(func["arguments"])

    # 调用 TypoAgent
    result = requests.post(
        "http://localhost:50120/api/v1/skills/execute",
        json=args
    ).json()

    print(f"执行结果: {result}")`;

  const tabItems = [
    {
      key: "overview",
      label: (
        <span>
          <RocketOutlined /> 快速开始
        </span>
      ),
      children: (
        <div>
          <Alert
            type="success"
            showIcon
            icon={<CheckCircleOutlined />}
            message="TypoAgent 已就绪"
            description={
              <Space direction="vertical" style={{ marginTop: 8 }}>
                <Text>
                  <EndpointStatus status="online" /> MCP SSE 端点: <Text code>http://localhost:50120/mcp/sse</Text>
                </Text>
                <Text>
                  <EndpointStatus status="online" /> REST API 端点: <Text code>http://localhost:50120/api/v1</Text>
                </Text>
                <Text>
                  <EndpointStatus status="online" /> WebSocket: <Text code>计划支持</Text>
                </Text>
              </Space>
            }
            style={{ marginBottom: 24 }}
          />

          <Title level={4}>🚀 一分钟快速开始</Title>

          <Timeline
            items={[
              {
                dot: <CheckCircleOutlined style={{ color: "#52c41a" }} />,
                children: (
                  <div>
                    <Text strong>确认服务状态</Text>
                    <CodeBlock code={`curl http://localhost:50120/api/v1/health`} />
                  </div>
                ),
              },
              {
                dot: <ApiOutlined style={{ color: "#1890ff" }} />,
                children: (
                  <div>
                    <Text strong>测试 MCP 端点</Text>
                    <CodeBlock code={`curl http://localhost:50120/mcp/health`} />
                  </div>
                ),
              },
              {
                dot: <ThunderboltOutlined style={{ color: "#faad14" }} />,
                children: (
                  <div>
                    <Text strong>执行第一个 Skill</Text>
                    <CodeBlock
                      code={`curl -X POST http://localhost:50120/api/v1/skills/execute \\
  -H "Content-Type: application/json" \\
  -d '{
    "skill_name": "ask_ai",
    "params": {
      "question": "你好，TypoAgent!"
    }
  }'`}
                    />
                  </div>
                ),
              },
            ]}
          />

          <Divider />

          <Title level={4}>📋 选择集成方式</Title>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
            <Card title="MCP SSE" size="small" hoverable>
              <Paragraph>适合 Claude Desktop、Cursor 等 MCP 客户端</Paragraph>
              <Tag color="green">推荐</Tag>
            </Card>
            <Card title="REST API" size="small" hoverable>
              <Paragraph>适合自定义应用、脚本、CI/CD 集成</Paragraph>
              <Tag color="blue">通用</Tag>
            </Card>
            <Card title="Skill 调用" size="small" hoverable>
              <Paragraph>适合 Agent 间协作、复杂工作流</Paragraph>
              <Tag color="orange">高级</Tag>
            </Card>
          </div>
        </div>
      ),
    },
    {
      key: "mcp",
      label: (
        <span>
          <ApiOutlined /> MCP SSE
        </span>
      ),
      children: (
        <div>
          <Title level={4}>MCP SSE 服务端</Title>
          <Paragraph>
            TypoAgent 实现了基于 <Link href="https://spec.modelcontextprotocol.io/" target="_blank">MCP (Model Context Protocol)</Link> 的 SSE 服务端，
            允许外部 MCP 客户端通过 HTTP SSE 连接调用 Agent 的能力。
          </Paragraph>

          <Alert
            type="success"
            message="服务端点"
            description={
              <Space direction="vertical">
                <Text code>SSE 连接：http://localhost:50120/mcp/sse</Text>
                <Text code>消息端点：http://localhost:50120/mcp/messages</Text>
                <Text code>健康检查：http://localhost:50120/mcp/health</Text>
              </Space>
            }
            style={{ margin: "16px 0" }}
          />

          <Title level={5}>支持的 MCP Tools</Title>
          <Table
            dataSource={mcpTools}
            pagination={false}
            size="small"
            columns={[
              { title: "Tool 名称", dataIndex: "name", key: "name", render: (text) => <Text code>{text}</Text> },
              { title: "描述", dataIndex: "description", key: "description" },
              { title: "参数示例", dataIndex: "params", key: "params", render: (text) => <Text type="secondary" ellipsis>{text}</Text> },
            ]}
          />

          <Divider />

          <Title level={5}>完整客户端实现</Title>
          <Collapse defaultActiveKey={["ts"]}>
            <Panel header="TypeScript 完整示例" key="ts">
              <Paragraph>包含连接管理、消息处理和错误处理的完整实现</Paragraph>
              <CodeBlock code={sseCompleteExample} language="typescript" />
            </Panel>
            <Panel header="Python 完整示例" key="py">
              <Paragraph>基于 aiohttp 的异步 MCP 客户端</Paragraph>
              <CodeBlock code={pythonFullExample} language="python" />
            </Panel>
            <Panel header="Go 示例" key="go">
              <Paragraph>Go 语言 MCP 客户端实现</Paragraph>
              <CodeBlock code={goExample} language="go" />
            </Panel>
          </Collapse>
        </div>
      ),
    },
    {
      key: "api",
      label: (
        <span>
          <CodeOutlined /> REST API
        </span>
      ),
      children: (
        <div>
          <Title level={4}>REST API 对接</Title>
          <Paragraph>TypoAgent 提供标准的 REST API，支持通过 HTTP 请求直接调用 Skills 和其他功能。</Paragraph>

          <Alert
            type="warning"
            message="API 端点"
            description={
              <Space direction="vertical">
                <Text>基础地址：<Text code>http://localhost:50120</Text></Text>
                <Text>所有 API 都返回 JSON 格式，包含 <Text code>success</Text> 字段指示操作是否成功</Text>
              </Space>
            }
            style={{ margin: "16px 0" }}
          />

          <Title level={5}>API 列表</Title>
          <Table
            dataSource={apiList}
            pagination={false}
            size="small"
            columns={[
              {
                title: "方法",
                dataIndex: "method",
                key: "method",
                width: 80,
                render: (text) => <Tag color={text === "GET" ? "blue" : text === "POST" ? "green" : "orange"}>{text}</Tag>,
              },
              { title: "端点", dataIndex: "endpoint", key: "endpoint", render: (text) => <Text code style={{ fontSize: "12px" }}>{text}</Text> },
              { title: "描述", dataIndex: "desc", key: "desc" },
              { title: "认证", dataIndex: "auth", key: "auth", width: 80, render: (text) => text ? <Tag>需要</Tag> : <Tag color="success">公开</Tag> },
            ]}
          />

          <Divider />

          <Title level={5}>常见用法示例</Title>
          <Collapse>
            <Panel header="执行 Skill" key="1">
              <CodeBlock code={`curl -X POST http://localhost:50120/api/v1/skills/execute \\
  -H "Content-Type: application/json" \\
  -d '{
    "skill_name": "scan_typo",
    "params": {
      "repo_path": "./my-project",
      "max_files": 100
    },
    "conversation_id": "conv-123"
  }'`} />
            </Panel>
            <Panel header="执行 MCP Tool" key="2">
              <CodeBlock code={`curl -X POST http://localhost:50120/api/v1/mcp/execute \\
  -H "Content-Type: application/json" \\
  -d '{
    "server_id": "filesystem",
    "tool_name": "read_file",
    "arguments": {
      "path": "/path/to/file.txt"
    }
  }'`} />
            </Panel>
            <Panel header="获取 Capabilities" key="3">
              <CodeBlock code={`curl http://localhost:50120/api/v1/capabilities | jq '.'`} />
            </Panel>
          </Collapse>
        </div>
      ),
    },
    {
      key: "integration",
      label: (
        <span>
          <ThunderboltOutlined /> 框架集成
        </span>
      ),
      children: (
        <div>
          <Title level={4}>与主流框架集成</Title>

          <Collapse defaultActiveKey={["langchain"]}>
            <Panel header={<Space><ThunderboltOutlined /> LangChain 集成</Space>} key="langchain">
              <Paragraph>将 TypoAgent Skills 作为 LangChain Tools 使用</Paragraph>
              <CodeBlock code={langchainExample} language="python" />
            </Panel>
            <Panel header={<Space><RobotOutlined /> OpenAI 函数调用</Space>} key="openai">
              <Paragraph>在 ChatGPT/OpenAI 应用中集成 TypoAgent</Paragraph>
              <CodeBlock code={openaiExample} language="python" />
            </Panel>
            <Panel header={<Space><LinkOutlined /> Webhook 通知</Space>} key="webhook">
              <Paragraph>配置 Webhook 接收执行事件通知</Paragraph>
              <CodeBlock code={webhookExample} language="yaml" />
            </Panel>
          </Collapse>
        </div>
      ),
    },
    {
      key: "advanced",
      label: (
        <span>
          <FileTextOutlined /> 高级主题
        </span>
      ),
      children: (
        <div>
          <Title level={4}>高级配置与最佳实践</Title>

          <Collapse>
            <Panel header={<Space><SafetyOutlined /> 安全配置</Space>} key="security">
              <Paragraph>权限控制和安全最佳实践</Paragraph>
              <CodeBlock code={securityExample} language="yaml" />
            </Panel>
            <Panel header={<Space><RocketOutlined /> 性能优化</Space>} key="performance">
              <Paragraph>提升集成性能的实用技巧</Paragraph>
              <CodeBlock code={performanceExample} language="python" />
            </Panel>
            <Panel header={<Space><BugOutlined /> 错误处理</Space>} key="error">
              <Paragraph>错误码说明和处理策略</Paragraph>
              <Table
                dataSource={errorCodes}
                pagination={false}
                size="small"
                columns={[
                  { title: "错误码", dataIndex: "code", key: "code", render: (text) => <Text code>{text}</Text> },
                  { title: "名称", dataIndex: "name", key: "name" },
                  { title: "描述", dataIndex: "desc", key: "desc" },
                  { title: "解决方案", dataIndex: "solution", key: "solution" },
                ]}
              />
              <Divider />
              <Paragraph>错误处理示例</Paragraph>
              <CodeBlock code={errorHandlingExample} language="typescript" />
            </Panel>
            <Panel header={<Space><CodeOutlined /> 调试技巧</Space>} key="debug">
              <Paragraph>排查问题的实用命令和技巧</Paragraph>
              <CodeBlock code={debuggingExample} language="bash" />
            </Panel>
            <Panel header={<Space><FileTextOutlined /> 使用案例</Space>} key="cases">
              <Paragraph>自动化代码审查流程示例</Paragraph>
              <CodeBlock code={useCasesExample} language="typescript" />
            </Panel>
          </Collapse>
        </div>
      ),
    },
  ];

  return (
    <div className="integration-docs-page">
      <div className="page-header" style={{ marginBottom: 24 }}>
        <div className="header-left">
          <Title level={4} style={{ margin: 0 }}>
            <LinkOutlined /> 外部系统对接文档
          </Title>
          <Paragraph style={{ margin: "8px 0 0", color: "#666" }}>
            通过 MCP、REST API 和框架集成，将 TypoAgent 能力扩展到任何应用
          </Paragraph>
        </div>
      </div>

      <Card bordered={false} className="flat-card">
        <Tabs activeKey={activeTab} onChange={setActiveTab} type="card" items={tabItems} />
      </Card>

      <Card
        title={
          <Space>
            <MessageOutlined />
            <span>需要帮助？</span>
          </Space>
        }
        style={{ marginTop: 24 }}
        className="flat-card"
      >
        <Space direction="vertical">
          <Text>• 查看 <Link href="https://spec.modelcontextprotocol.io/" target="_blank">MCP 协议规范</Link></Text>
          <Text>• 查看 <Link href="https://github.com/anthropics/anthropic-cookbook/tree/main/mcp" target="_blank">MCP 示例代码</Link></Text>
          <Text>• 在 GitHub 提交 <Link href="https://github.com/your-repo/typo-agent/issues" target="_blank">Issue</Link></Text>
          <Text>• 发送邮件至 <Text code>support@typoagent.dev</Text></Text>
        </Space>
      </Card>
    </div>
  );
}
