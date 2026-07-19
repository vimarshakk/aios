const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json() as Promise<T>;
}

export type ToolInfo = {
  name: string;
  description: string;
  category: string;
  enabled: boolean;
};

export type AgentInfo = {
  name: string;
  role: string;
  status: string;
  model?: string;
  type?: string;
  description?: string;
  capabilities?: string[];
};

export type ModelInfo = {
  id?: string;
  name: string;
  provider: string;
  active: boolean;
};

export type HealthResponse = {
  status: string;
  version: string;
};

export type GoalSnapshot = {
  goal_id: string;
  objective: string;
  status: string;
  steps: GoalStep[];
  elapsed_ms?: number;
  started_at?: number;
  error?: string;
};

export type GoalStep = {
  id: string;
  name?: string;
  capability?: string;
  description: string;
  status: string;
};

export type RepositoryInfo = {
  id: string;
  name: string;
  path: string;
  branch: string;
  status: string;
  language: string;
  files: number;
  lastCommit?: string;
  workers: string[];
  uncommittedChanges: number;
};

export type MemoryEntry = {
  id: string;
  type: string;
  content: string;
  tags: string[];
  createdAt: number;
  created_at?: number;
  importance?: number;
  confidence?: number;
  source?: string;
};

export type ProjectInfo = {
  id: string;
  name: string;
  path: string;
  language: string;
  languages?: string[];
  description?: string;
  status: string;
  lastModified?: number;
  last_accessed?: number;
  file_count?: number;
};

export const api = {
  async getTools(): Promise<ToolInfo[]> { return http("/tools"); },

  // Backward-compat alias (legacy pages expect api.tools())
  tools: async (): Promise<ToolInfo[]> => api.getTools(),
  async getAgents(): Promise<AgentInfo[]> { return http("/agents"); },
  async getModels(): Promise<ModelInfo[]> { return http("/models"); },
  async getHealth(): Promise<HealthResponse> { return http("/health"); },

  // Backward-compat alias (legacy pages expect api.health())
  health: async (): Promise<HealthResponse> => api.getHealth(),

  // Backward-compat aliases (legacy pages expect api.agents()/api.models())
  agents: async (): Promise<AgentInfo[]> => api.getAgents(),
  models: async (): Promise<ModelInfo[]> => api.getModels(),

  workforce: {
    async listWorkers(): Promise<Record<string, unknown>[]> {
      return http("/workforce/workers");
    },
    async getWorker(id: string): Promise<Record<string, unknown>> {
      return http(`/workforce/workers/${encodeURIComponent(id)}`);
    },
    async findByCapability(capability: string): Promise<Record<string, unknown>[]> {
      return http(`/workforce/capability/${encodeURIComponent(capability)}`);
    },
    async assignTask(workerId: string, task: string): Promise<Record<string, unknown>> {
      return http("/workforce/assign", {
        method: "POST",
        body: JSON.stringify({ worker_id: workerId, task }),
      });
    },
    async completeTask(workerId: string): Promise<Record<string, unknown>> {
      return http("/workforce/complete", {
        method: "POST",
        body: JSON.stringify({ worker_id: workerId }),
      });
    },
    async failTask(workerId: string): Promise<Record<string, unknown>> {
      return http("/workforce/fail", {
        method: "POST",
        body: JSON.stringify({ worker_id: workerId }),
      });
    },
    async getState(): Promise<Record<string, unknown>> {
      return http("/workforce/state");
    },
  },

  cli: {
    async activeProcesses(): Promise<Record<string, unknown>[]> {
      return http("/cli/active");
    },
    async spawn(options: Record<string, unknown>): Promise<Record<string, unknown>> {
      return http("/cli/spawn", {
        method: "POST",
        body: JSON.stringify(options),
      });
    },
  },

  reviews: {
    async listActive(): Promise<Record<string, unknown>[]> {
      return http("/review/active");
    },
    async create(data: Record<string, unknown>): Promise<Record<string, unknown>> {
      return http("/review/create", {
        method: "POST",
        body: JSON.stringify(data),
      });
    },
    async verdict(reviewId: string, verdict: string): Promise<Record<string, unknown>> {
      return http(`/review/${encodeURIComponent(reviewId)}/verdict`, {
        method: "POST",
        body: JSON.stringify({ verdict }),
      });
    },
    async getState(): Promise<Record<string, unknown>> {
      return http("/review/state");
    },
  },

  memory: {
    async recentMemory(limit = 30): Promise<MemoryEntry[]> {
      return http(`/memory/recent?limit=${limit}`);
    },
    async searchMemory(query: string): Promise<MemoryEntry[]> {
      return http(`/memory/search?q=${encodeURIComponent(query)}`);
    },
    async rememberMemory(data: { content: string; type?: string; tags?: string[] }): Promise<MemoryEntry> {
      return http("/memory/remember", {
        method: "POST",
        body: JSON.stringify(data),
      });
    },
  },

  // Top-level memory aliases (legacy pages expect api.recentMemory() etc.)
  recentMemory: async (limit = 30): Promise<MemoryEntry[]> => api.memory.recentMemory(limit),
  searchMemory: async (query: string): Promise<MemoryEntry[]> => api.memory.searchMemory(query),
  rememberMemory: async (data: { content: string; type?: string; tags?: string[] }): Promise<MemoryEntry> =>
    api.memory.rememberMemory(data),

  // Memory explorer / graph stubs
  async memoryStats(): Promise<Record<string, unknown>> {
    return http("/memory/stats");
  },
  async consolidateMemory(): Promise<Record<string, unknown>> {
    return http("/memory/consolidate", { method: "POST" });
  },
  async listWorkspaces(): Promise<Array<{ id: string; name: string; description?: string }>> {
    return http("/memory/workspaces");
  },
  async getWorkspace(id: string): Promise<Record<string, unknown>> {
    return http(`/memory/workspaces/${encodeURIComponent(id)}`);
  },
  async createWorkspace(name: string, description: string): Promise<Record<string, unknown>> {
    return http("/memory/workspaces", {
      method: "POST",
      body: JSON.stringify({ name, description }),
    });
  },
  async deleteWorkspace(id: string): Promise<Record<string, unknown>> {
    return http(`/memory/workspaces/${encodeURIComponent(id)}`, { method: "DELETE" });
  },
  async workspaceSearch(id: string, query: string): Promise<MemoryEntry[]> {
    return http(`/memory/workspaces/${encodeURIComponent(id)}/search?q=${encodeURIComponent(query)}`);
  },
  async workspaceRemember(id: string, content: string): Promise<MemoryEntry> {
    return http(`/memory/workspaces/${encodeURIComponent(id)}/remember`, {
      method: "POST",
      body: JSON.stringify({ content }),
    });
  },
  async graphNodes(type?: string, limit = 100): Promise<Array<Record<string, unknown>>> {
    const q = new URLSearchParams();
    if (type) q.set("type", type);
    q.set("limit", String(limit));
    return http(`/graph/nodes?${q.toString()}`);
  },
  async graphEdges(type?: string, limit = 100): Promise<Array<Record<string, unknown>>> {
    const q = new URLSearchParams();
    if (type) q.set("type", type);
    q.set("limit", String(limit));
    return http(`/graph/edges?${q.toString()}`);
  },
  async graphComponents(): Promise<Array<Record<string, unknown>>> {
    return http("/graph/components");
  },
  async graphShortestPath(source: string, target: string): Promise<Record<string, unknown>> {
    return http(`/graph/shortest-path?source=${encodeURIComponent(source)}&target=${encodeURIComponent(target)}`);
  },
  async hybridSearch(
    query: string,
    limit = 20,
    opts?: { use_vector?: boolean; use_graph?: boolean; use_keyword?: boolean },
  ): Promise<Array<Record<string, unknown>>> {
    return http("/memory/hybrid-search", {
      method: "POST",
      body: JSON.stringify({ query, limit, ...opts }),
    });
  },
  async exportMemory(format: string): Promise<Record<string, unknown>> {
    return http(`/memory/export?format=${encodeURIComponent(format)}`);
  },
  async importMemory(data: unknown, format: string): Promise<Record<string, unknown>> {
    return http(`/memory/import?format=${encodeURIComponent(format)}`, {
      method: "POST",
      body: JSON.stringify({ data }),
    });
  },

  repositories: {
    async list(): Promise<RepositoryInfo[]> {
      return http("/repositories");
    },
    async get(id: string): Promise<RepositoryInfo> {
      return http(`/repositories/${encodeURIComponent(id)}`);
    },
  },

  async listProjects(): Promise<ProjectInfo[]> {
    return http("/projects");
  },
  async scanProjects(): Promise<ProjectInfo[]> {
    return http("/projects/scan", { method: "POST" });
  },

  // Goal creation — stub for the conversation workspace.
  async createGoal(opts: { objective: string }): Promise<{ goal_id: string }> {
    return http("/goals", {
      method: "POST",
      body: JSON.stringify(opts),
    });
  },

  async listGoals(): Promise<GoalSnapshot[]> {
    return http("/goals");
  },

  async pauseGoal(id: string): Promise<Record<string, unknown>> {
    return http(`/goals/${encodeURIComponent(id)}/pause`, { method: "POST" });
  },
  async resumeGoal(id: string): Promise<Record<string, unknown>> {
    return http(`/goals/${encodeURIComponent(id)}/resume`, { method: "POST" });
  },
  async cancelGoal(id: string): Promise<Record<string, unknown>> {
    return http(`/goals/${encodeURIComponent(id)}/cancel`, { method: "POST" });
  },

  subscribeAllGoals(
    _cb: (snapshots: GoalSnapshot[]) => void,
    _onClosed?: () => void,
    _onError?: (err: Error) => void,
  ): (() => void) {
    // WebSocket subscription — stub for legacy pages
    return () => {};
  },

  subscribeGoal: (
    _goalId: string,
    _cb: (snapshot: GoalSnapshot) => void,
    _onClosed?: () => void,
    _onError?: (err: Error) => void,
  ): (() => void) => {
    // WebSocket subscription — stub for legacy pages
    return () => {};
  },

  // Streaming chat — stub for the conversation workspace.
  streamChat: (
    _opts: { message: string; agent?: string; model?: string },
    _onChunk: (chunk: string) => void,
    _onDone?: () => void,
    _onError?: (err: Error) => void,
    _extra?: {
      onToolCall?: (tool: { name: string; status?: string }) => void;
      onToolResult?: (toolName: string, success: boolean) => void;
      onReasoning?: (text: string) => void;
    },
  ): (() => void) => {
    return () => {};
  },
};
