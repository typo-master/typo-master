import type {
  CapabilityPayload,
  ChatMessageResponse,
  ConversationCreateResponse,
  MCPCatalogListResponse,
  MCPExecuteResponse,
  MCPListResponse,
  MCPServerRecord,
  SkillListResponse,
  SkillRecord,
  SkillExecuteResponse,
  WorkflowRequest,
  WorkflowTaskResponse,
  PermissionsResponse
} from "./types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:50120";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = localStorage.getItem("typomaster_jwt");
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string> ?? {})
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const response = await fetch(`${BASE_URL}${path}`, {
    headers,
    ...init
  });

  if (response.status === 401) {
    localStorage.removeItem("typomaster_jwt");
    localStorage.removeItem("typomaster_user");
    window.dispatchEvent(new CustomEvent("auth:unauthorized"));
  }

  if (!response.ok) {
    const payload = await response.text();
    throw new Error(`HTTP ${response.status}: ${payload}`);
  }
  return response.json() as Promise<T>;
}

export async function fetchCapabilities(): Promise<CapabilityPayload> {
  return request<CapabilityPayload>("/api/v1/capabilities");
}

export async function createConversation(): Promise<ConversationCreateResponse> {
  return request<ConversationCreateResponse>("/api/v1/conversations", {
    method: "POST"
  });
}

export async function sendChatMessage(
  conversationId: string,
  message: string
): Promise<ChatMessageResponse> {
  return request<ChatMessageResponse>(
    `/api/v1/conversations/${conversationId}/messages`,
    {
      method: "POST",
      body: JSON.stringify({ message })
    }
  );
}

export async function runWorkflow(payload: WorkflowRequest): Promise<WorkflowTaskResponse> {
  return request<WorkflowTaskResponse>("/api/v1/agent/workflows", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function getWorkflowTask(taskId: string): Promise<WorkflowTaskResponse> {
  return request<WorkflowTaskResponse>(`/api/v1/agent/workflows/${taskId}`);
}

export async function executeSkill(
  skillName: string,
  params: Record<string, unknown>,
  skill?: Record<string, unknown>,
  conversationId = ""
): Promise<SkillExecuteResponse> {
  return request<SkillExecuteResponse>("/api/v1/skills/execute", {
    method: "POST",
    body: JSON.stringify({
      skill_name: skillName,
      params,
      skill,
      conversation_id: conversationId
    })
  });
}

export async function listSkills(): Promise<SkillListResponse> {
  return request<SkillListResponse>("/api/v1/skills");
}

export async function upsertSkill(
  skillName: string,
  skill: SkillRecord
): Promise<{ success: boolean; skill: SkillRecord }> {
  return request<{ success: boolean; skill: SkillRecord }>(
    `/api/v1/skills/${encodeURIComponent(skillName)}`,
    {
      method: "PUT",
      body: JSON.stringify({ skill })
    }
  );
}

export async function deleteSkill(
  skillName: string
): Promise<{ success: boolean; skill_name: string }> {
  return request<{ success: boolean; skill_name: string }>(
    `/api/v1/skills/${encodeURIComponent(skillName)}`,
    {
      method: "DELETE"
    }
  );
}

export async function listMCPServers(): Promise<MCPListResponse> {
  return request<MCPListResponse>("/api/v1/mcp/servers");
}

export async function listMCPCatalog(query = ""): Promise<MCPCatalogListResponse> {
  const suffix = query.trim() ? `?q=${encodeURIComponent(query.trim())}` : "";
  return request<MCPCatalogListResponse>(`/api/v1/mcp/catalog${suffix}`);
}

export async function installMCPCatalog(
  catalogId: string,
  overrides: Record<string, unknown>
): Promise<{ success: boolean; server: MCPServerRecord }> {
  return request<{ success: boolean; server: MCPServerRecord }>(
    `/api/v1/mcp/catalog/${encodeURIComponent(catalogId)}/install`,
    {
      method: "POST",
      body: JSON.stringify({ overrides })
    }
  );
}

export async function upsertMCPServer(
  serverId: string,
  server: MCPServerRecord
): Promise<{ success: boolean; server: MCPServerRecord }> {
  return request<{ success: boolean; server: MCPServerRecord }>(
    `/api/v1/mcp/servers/${encodeURIComponent(serverId)}`,
    {
      method: "PUT",
      body: JSON.stringify({ server })
    }
  );
}

export async function deleteMCPServer(
  serverId: string
): Promise<{ success: boolean; server_id: string }> {
  return request<{ success: boolean; server_id: string }>(
    `/api/v1/mcp/servers/${encodeURIComponent(serverId)}`,
    {
      method: "DELETE"
    }
  );
}

export async function probeMCPServer(serverId: string): Promise<MCPExecuteResponse> {
  return request<MCPExecuteResponse>(
    `/api/v1/mcp/servers/${encodeURIComponent(serverId)}/probe`,
    {
      method: "POST"
    }
  );
}

export async function executeMCPTool(
  serverId: string,
  toolName: string,
  argumentsPayload: Record<string, unknown>
): Promise<MCPExecuteResponse> {
  return request<MCPExecuteResponse>("/api/v1/mcp/execute", {
    method: "POST",
    body: JSON.stringify({
      server_id: serverId,
      tool_name: toolName,
      arguments: argumentsPayload
    })
  });
}

export async function fetchPermissions(): Promise<PermissionsResponse> {
  return request<PermissionsResponse>("/api/v1/permissions");
}

export async function updatePermissions(
  permissions: Record<string, boolean>
): Promise<PermissionsResponse> {
  return request<PermissionsResponse>("/api/v1/permissions", {
    method: "PUT",
    body: JSON.stringify({ permissions })
  });
}
