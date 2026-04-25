export interface CapabilityPayload {
  success: boolean;
  framework: string;
  workflows: Record<string, boolean>;
  pipeline_nodes: string[];
  features: Record<string, boolean>;
  llm: {
    enabled: boolean;
    model: string | null;
  };
  limitations: string[];
  skill_registry?: {
    total: number;
    enabled: number;
    builtin: number;
    custom: number;
  };
  mcp?: {
    enabled_servers: number;
    total_servers: number;
    adapter: string;
  };
}

export interface PermissionsResponse {
  success: boolean;
  permissions: Record<string, boolean>;
  groups: Record<string, string[]>;
}

export interface WorkflowRequest {
  workflow: "single_project" | "batch_projects";
  create_pr: boolean;
  owner?: string;
  repo?: string;
  days?: number;
  min_stars?: number;
  limit?: number;
}

export interface WorkflowTaskResponse {
  task_id: string;
  status: string;
  created_at: string;
  updated_at: string;
  result?: Record<string, unknown>;
  error?: string | null;
}

export interface ConversationCreateResponse {
  conversation_id: string;
  created_at: string;
}

export interface ChatMessageResponse {
  success: boolean;
  mode: string;
  reply: string;
  conversation_id: string;
  warning?: string;
  action_result?: Record<string, unknown>;
  model?: string;
}

export interface SkillExecuteResponse {
  success: boolean;
  skill_name: string;
  mode: string;
  message: string;
  result?: Record<string, unknown> | null;
  error?: string | null;
  executed_at: string;
}

export interface SkillRecord {
  name: string;
  description: string;
  category: string;
  enabled: boolean;
  source?: "builtin" | "custom" | "community" | string;
  sourceUrl?: string;
  version?: string;
  homepage?: string;
  tags?: string[];
  parameters?: Array<{
    name: string;
    type: string;
    required: boolean;
    description?: string;
  }>;
  executor?: Record<string, unknown>;
  installMethod?: "manual" | "url" | "catalog" | "json" | string;
  createdAt?: number;
  updatedAt?: number;
}

export interface SkillListResponse {
  success: boolean;
  skills: SkillRecord[];
}

export interface MCPServerRecord {
  id: string;
  name: string;
  description?: string;
  enabled: boolean;
  transport: "stdio" | "http" | "sse" | "streamable_http" | string;
  command?: string | null;
  args?: string[];
  url?: string | null;
  headers?: Record<string, string>;
  env?: Record<string, string>;
  timeout?: number;
  createdAt?: number;
  updatedAt?: number;
  metadata?: Record<string, unknown>;
}

export interface MCPListResponse {
  success: boolean;
  servers: MCPServerRecord[];
  adapter: {
    name: string;
    note: string;
  };
}

export interface MCPCatalogItem {
  catalog_id: string;
  name: string;
  description: string;
  tags: string[];
  server: MCPServerRecord;
}

export interface MCPCatalogListResponse {
  success: boolean;
  query: string;
  items: MCPCatalogItem[];
}

export interface MCPExecuteResponse {
  success: boolean;
  mode?: string;
  error?: string;
  result?: Record<string, unknown>;
}

export interface AuthUser {
  user_id: string;
  github_id: number;
  username: string;
  display_name: string;
  avatar_url: string;
  email: string | null;
  bio: string | null;
  created_at: string;
  last_login_at: string;
  is_active: boolean;
}

export interface AuthMeResponse {
  authenticated: boolean;
  user: AuthUser | null;
}

export interface GitHubCallbackResponse {
  success: boolean;
  token: string;
  user: AuthUser;
}
