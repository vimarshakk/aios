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
};

export type ModelInfo = {
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
};

export type GoalStep = {
  id: string;
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

export const api = {
  async getTools(): Promise<ToolInfo[]> { return http("/tools"); },
  async getAgents(): Promise<AgentInfo[]> { return http("/agents"); },
  async getModels(): Promise<ModelInfo[]> { return http("/models"); },
  async getHealth(): Promise<HealthResponse> { return http("/health"); },

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

  repositories: {
    async list(): Promise<RepositoryInfo[]> {
      return http("/repositories");
    },
    async get(id: string): Promise<RepositoryInfo> {
      return http(`/repositories/${encodeURIComponent(id)}`);
    },
  },

  subscribeGoal: async (_goalId: string, _cb: (snapshot: GoalSnapshot) => void): Promise<() => void> => {
    // WebSocket subscription — stub for legacy pages
    return () => {};
  },
};
