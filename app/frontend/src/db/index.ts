/**
 * IndexDB 存储管理器
 * 用于存储对话记录、触发器配置、Agent Skill 等数据
 */

const DB_NAME = "TypoMasterDB";
const DB_VERSION = 1;

// 存储对象名称
export const STORES = {
  CHAT_HISTORY: "chat_history",
  TRIGGERS: "triggers",
  AGENT_SKILLS: "agent_skills",
  EXECUTION_LOGS: "execution_logs",
} as const;

// 打开数据库
function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);

    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;

      // 对话历史存储
      if (!db.objectStoreNames.contains(STORES.CHAT_HISTORY)) {
        const chatStore = db.createObjectStore(STORES.CHAT_HISTORY, {
          keyPath: "id",
          autoIncrement: true,
        });
        chatStore.createIndex("conversationId", "conversationId", { unique: false });
        chatStore.createIndex("timestamp", "timestamp", { unique: false });
        chatStore.createIndex("agentId", "agentId", { unique: false });
      }

      // 触发器配置存储
      if (!db.objectStoreNames.contains(STORES.TRIGGERS)) {
        const triggerStore = db.createObjectStore(STORES.TRIGGERS, {
          keyPath: "id",
          autoIncrement: true,
        });
        triggerStore.createIndex("enabled", "enabled", { unique: false });
        triggerStore.createIndex("nextRun", "nextRun", { unique: false });
      }

      // Agent Skill 存储
      if (!db.objectStoreNames.contains(STORES.AGENT_SKILLS)) {
        const skillStore = db.createObjectStore(STORES.AGENT_SKILLS, {
          keyPath: "name",
        });
        skillStore.createIndex("category", "category", { unique: false });
      }

      // 执行日志存储
      if (!db.objectStoreNames.contains(STORES.EXECUTION_LOGS)) {
        const logStore = db.createObjectStore(STORES.EXECUTION_LOGS, {
          keyPath: "id",
          autoIncrement: true,
        });
        logStore.createIndex("triggerId", "triggerId", { unique: false });
        logStore.createIndex("timestamp", "timestamp", { unique: false });
        logStore.createIndex("status", "status", { unique: false });
      }
    };
  });
}

// 通用 CRUD 操作
class Store<T> {
  private storeName: string;

  constructor(storeName: string) {
    this.storeName = storeName;
  }

  // 添加数据
  async add(data: Omit<T, "id">): Promise<number> {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(this.storeName, "readwrite");
      const store = transaction.objectStore(this.storeName);
      const request = store.add(data);

      request.onsuccess = () => resolve(request.result as number);
      request.onerror = () => reject(request.error);
    });
  }

  // 获取单条数据
  async get(id: number | string): Promise<T | undefined> {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(this.storeName, "readonly");
      const store = transaction.objectStore(this.storeName);
      const request = store.get(id);

      request.onsuccess = () => resolve(request.result as T);
      request.onerror = () => reject(request.error);
    });
  }

  // 获取所有数据
  async getAll(): Promise<T[]> {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(this.storeName, "readonly");
      const store = transaction.objectStore(this.storeName);
      const request = store.getAll();

      request.onsuccess = () => resolve(request.result as T[]);
      request.onerror = () => reject(request.error);
    });
  }

  // 更新数据
  async update(data: T): Promise<void> {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(this.storeName, "readwrite");
      const store = transaction.objectStore(this.storeName);
      const request = store.put(data);

      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }

  // 删除数据
  async delete(id: number | string): Promise<void> {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(this.storeName, "readwrite");
      const store = transaction.objectStore(this.storeName);
      const request = store.delete(id);

      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }

  // 根据索引查询
  async getByIndex(indexName: string, value: any): Promise<T[]> {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(this.storeName, "readonly");
      const store = transaction.objectStore(this.storeName);
      const index = store.index(indexName);
      const request = index.getAll(value);

      request.onsuccess = () => resolve(request.result as T[]);
      request.onerror = () => reject(request.error);
    });
  }

  // 清空存储
  async clear(): Promise<void> {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(this.storeName, "readwrite");
      const store = transaction.objectStore(this.storeName);
      const request = store.clear();

      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }
}

// 数据类型定义
export interface ChatMessage {
  id?: number;
  conversationId: string;
  agentId?: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: number;
  mode?: string;
  skills?: string[];
  metadata?: Record<string, any>;
  steps?: ExecutionStep[]; // 执行步骤
}

export interface ExecutionStep {
  id: string;
  name: string;
  description?: string;
  status: "pending" | "running" | "completed" | "failed";
  startTime?: number;
  endTime?: number;
  progress?: number; // 0-100
  icon?: string;
  subSteps?: ExecutionStep[];
}

export interface Trigger {
  id?: number;
  name: string;
  description?: string;
  enabled: boolean;
  interval: number; // 间隔时间（分钟）
  prompt: string; // 触发时发送给 Agent 的话
  targetAgent?: string;
  lastRun?: number;
  nextRun?: number;
  createdAt: number;
  runCount: number;
}

export interface AgentSkill {
  name: string;
  description: string;
  category: string;
  parameters?: {
    name: string;
    type: string;
    required: boolean;
    description?: string;
  }[];
  enabled: boolean;
  source?: "builtin" | "custom" | "community";
  sourceUrl?: string;
  version?: string;
  homepage?: string;
  tags?: string[];
  executor?: {
    type: string;
    [key: string]: any;
  };
  installMethod?: "manual" | "url" | "catalog" | "json";
  createdAt?: number;
  updatedAt?: number;
}

export interface ExecutionLog {
  id?: number;
  triggerId: number;
  triggerName: string;
  prompt: string;
  status: "success" | "failed" | "running";
  result?: string;
  error?: string;
  timestamp: number;
  duration?: number;
}

// 创建存储实例
export const chatStore = new Store<ChatMessage>(STORES.CHAT_HISTORY);
export const triggerStore = new Store<Trigger>(STORES.TRIGGERS);
export const skillStore = new Store<AgentSkill>(STORES.AGENT_SKILLS);
export const logStore = new Store<ExecutionLog>(STORES.EXECUTION_LOGS);

// 获取某个对话的所有消息
export async function getConversationMessages(
  conversationId: string
): Promise<ChatMessage[]> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(STORES.CHAT_HISTORY, "readonly");
    const store = transaction.objectStore(STORES.CHAT_HISTORY);
    const index = store.index("conversationId");
    const request = index.getAll(conversationId);

    request.onsuccess = () => {
      const messages = request.result as ChatMessage[];
      // 按时间排序
      messages.sort((a, b) => a.timestamp - b.timestamp);
      resolve(messages);
    };
    request.onerror = () => reject(request.error);
  });
}

// 获取启用的触发器
export async function getEnabledTriggers(): Promise<Trigger[]> {
  return triggerStore.getByIndex("enabled", true);
}

// 获取待执行的触发器
export async function getPendingTriggers(): Promise<Trigger[]> {
  const now = Date.now();
  const triggers = await triggerStore.getAll();
  return triggers.filter(
    (t) => t.enabled && (!t.nextRun || t.nextRun <= now)
  );
}

// 更新触发器下次执行时间
export async function updateTriggerNextRun(
  triggerId: number,
  interval: number
): Promise<void> {
  const trigger = await triggerStore.get(triggerId);
  if (trigger) {
    trigger.lastRun = Date.now();
    trigger.nextRun = Date.now() + interval * 60 * 1000;
    trigger.runCount += 1;
    await triggerStore.update(trigger);
  }
}

// 导出数据库（用于备份）
export async function exportDB(): Promise<{
  chatHistory: ChatMessage[];
  triggers: Trigger[];
  skills: AgentSkill[];
  logs: ExecutionLog[];
}> {
  return {
    chatHistory: await chatStore.getAll(),
    triggers: await triggerStore.getAll(),
    skills: await skillStore.getAll(),
    logs: await logStore.getAll(),
  };
}

// 导入数据库
export async function importDB(data: {
  chatHistory: ChatMessage[];
  triggers: Trigger[];
  skills: AgentSkill[];
  logs: ExecutionLog[];
}): Promise<void> {
  // 清空现有数据
  await chatStore.clear();
  await triggerStore.clear();
  await skillStore.clear();
  await logStore.clear();

  // 导入新数据
  for (const item of data.chatHistory) {
    await chatStore.add(item);
  }
  for (const item of data.triggers) {
    await triggerStore.add(item);
  }
  for (const item of data.skills) {
    await skillStore.add(item);
  }
  for (const item of data.logs) {
    await logStore.add(item);
  }
}
