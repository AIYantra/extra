import type { MissionRun } from "../data/dashboard";

export interface ServerHealth {
  status: "healthy" | "unhealthy" | "offline";
  version?: string;
  platform?: string;
}

export interface LiveTelemetryResponse {
  status: string;
  active_client: string;
  target_window: string;
  target_pid?: number;
  target_proc?: string;
  active_tool: string;
  latency_ms: number;
  memory_mb: number;
  tokens_saved: number;
  cost_saved_usd: number;
  tasks_completed: number;
  actions_dispatched?: number;
  time_saved_sec?: number;
  turns_saved?: number;
  top_apps?: Record<string, number>;
  speed_mode: "turbo" | "balanced" | "smart";
  is_paused: boolean;
  last_action?: any;
}

export interface LineageDeliverable {
  id: string;
  name: string;
  path: string;
  size: string;
  sizeBytes: number;
  hash: string;
  origin: string;
  verifiedAt: string;
}

export interface DesktopWindow {
  hwnd: number;
  title: string;
  proc_name: string;
  pid: number;
  rect: number[];
  is_browser: boolean;
  is_minimized: boolean;
}

export interface SkillCatalogItem {
  id: string;
  name: string;
  app: string;
  category: "Creative" | "Productivity" | "Developer" | "Media";
  description: string;
  hotkeys: string[];
  fastPath: string;
  guardrail: string;
}

const DEFAULT_SERVER_URL = "http://127.0.0.1:8000";

export class LoopbackTelemetryClient {
  private baseUrl: string;
  private pollIntervalId: number | null = null;
  private isPolling = false;
  private sessionToken: string | null = null;
  private tokenPromise: Promise<string | null> | null = null;

  constructor(baseUrl: string = DEFAULT_SERVER_URL) {
    this.baseUrl = baseUrl;
  }

  async getSessionToken(): Promise<string | null> {
    if (this.sessionToken) return this.sessionToken;
    if (this.tokenPromise) return this.tokenPromise;

    this.tokenPromise = (async () => {
      try {
        const res = await fetch("/api/extra/session-token");
        if (res.ok) {
          const data = await res.json();
          if (data?.token) {
            this.sessionToken = data.token;
            return data.token;
          }
        }
      } catch {}
      return null;
    })();

    const token = await this.tokenPromise;
    this.tokenPromise = null;
    return token;
  }

  private async authHeaders(custom: Record<string, string> = {}): Promise<Record<string, string>> {
    const headers: Record<string, string> = { ...custom };
    const token = await this.getSessionToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    return headers;
  }

  async checkHealth(timeoutMs: number = 1000): Promise<ServerHealth> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const res = await fetch(`${this.baseUrl}/health`, {
        method: "GET",
        signal: controller.signal,
      });
      clearTimeout(timer);
      if (res.ok) {
        const data = await res.json();
        return {
          status: "healthy",
          version: data.version,
          platform: data.platform,
        };
      }
      return { status: "unhealthy" };
    } catch {
      clearTimeout(timer);
      return { status: "offline" };
    }
  }

  async fetchTelemetry(timeoutMs: number = 1500): Promise<LiveTelemetryResponse | null> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const headers = await this.authHeaders();
      const res = await fetch(`${this.baseUrl}/telemetry`, {
        method: "GET",
        headers,
        signal: controller.signal,
      });
      clearTimeout(timer);
      if (res.ok) {
        return (await res.json()) as LiveTelemetryResponse;
      }
      return null;
    } catch {
      clearTimeout(timer);
      return null;
    }
  }

  async fetchRuns(): Promise<MissionRun[]> {
    try {
      const headers = await this.authHeaders();
      const res = await fetch(`${this.baseUrl}/api/runs`, { method: "GET", headers });
      if (res.ok) {
        return (await res.json()) as MissionRun[];
      }
      return [];
    } catch {
      return [];
    }
  }

  async fetchLineage(): Promise<LineageDeliverable[]> {
    try {
      const headers = await this.authHeaders();
      const res = await fetch(`${this.baseUrl}/api/lineage`, { method: "GET", headers });
      if (res.ok) {
        return (await res.json()) as LineageDeliverable[];
      }
      return [];
    } catch {
      return [];
    }
  }

  async revealFile(path: string): Promise<boolean> {
    try {
      const headers = await this.authHeaders({ "Content-Type": "application/json" });
      const res = await fetch(`${this.baseUrl}/api/reveal`, {
        method: "POST",
        headers,
        body: JSON.stringify({ path }),
      });
      return res.ok;
    } catch {
      return false;
    }
  }

  async fetchWindows(): Promise<DesktopWindow[]> {
    try {
      const headers = await this.authHeaders();
      const res = await fetch(`${this.baseUrl}/api/windows`, { method: "GET", headers });
      if (res.ok) {
        return (await res.json()) as DesktopWindow[];
      }
      return [];
    } catch {
      return [];
    }
  }

  async fetchSkills(): Promise<SkillCatalogItem[]> {
    try {
      const headers = await this.authHeaders();
      const res = await fetch(`${this.baseUrl}/api/skills`, { method: "GET", headers });
      if (res.ok) {
        return (await res.json()) as SkillCatalogItem[];
      }
      return [];
    } catch {
      return [];
    }
  }

  async fetchInspect(): Promise<any> {
    try {
      const headers = await this.authHeaders();
      const res = await fetch(`${this.baseUrl}/api/inspect`, { method: "GET", headers });
      if (res.ok) {
        return await res.json();
      }
      return { success: false, elements: [] };
    } catch {
      return { success: false, elements: [] };
    }
  }

  async dispatchIntent(intent: string): Promise<any> {
    try {
      const headers = await this.authHeaders({ "Content-Type": "application/json" });
      const res = await fetch(`${this.baseUrl}/api/dispatch`, {
        method: "POST",
        headers,
        body: JSON.stringify({ intent }),
      });
      return await res.json();
    } catch (e: any) {
      return { status: "error", message: e.message };
    }
  }

  async setSpeedMode(mode: "turbo" | "balanced" | "smart"): Promise<boolean> {
    try {
      const headers = await this.authHeaders({ "Content-Type": "application/json" });
      const res = await fetch(`${this.baseUrl}/api/speed-mode`, {
        method: "POST",
        headers,
        body: JSON.stringify({ mode }),
      });
      return res.ok;
    } catch {
      return false;
    }
  }

  async sendPanicStop(): Promise<boolean> {
    try {
      const headers = await this.authHeaders({ "Content-Type": "application/json" });
      const res = await fetch(`${this.baseUrl}/api/panic-stop`, {
        method: "POST",
        headers,
      });
      return res.ok;
    } catch {
      return false;
    }
  }

  async sendResume(): Promise<boolean> {
    try {
      const headers = await this.authHeaders({ "Content-Type": "application/json" });
      const res = await fetch(`${this.baseUrl}/api/resume`, {
        method: "POST",
        headers,
      });
      return res.ok;
    } catch {
      return false;
    }
  }

  async testIndicators(): Promise<{ ok: boolean; status: string; error?: string }> {
    try {
      const headers = await this.authHeaders({ "Content-Type": "application/json" });
      const res = await fetch(`${this.baseUrl}/api/indicators/pulse`, {
        method: "POST",
        headers,
      });
      if (res.ok) {
        const data = await res.json().catch(() => ({}));
        if (data?.status === "ok") return { ok: true, status: "pulse" };
        return { ok: false, status: "engine-error", error: data?.message || "Engine rejected the halo test" };
      }
      if (res.status === 401 || res.status === 403) {
        return { ok: false, status: "unauthorized", error: "Engine rejected this app's token — restart the engine" };
      }
      return { ok: false, status: `http-${res.status}`, error: `Engine returned HTTP ${res.status}` };
    } catch (e: any) {
      return { ok: false, status: "unreachable", error: e?.message || "Engine unreachable" };
    }
  }

  async fetchEngineStatus(): Promise<{
    state: string;
    port_open: boolean;
    healthy: boolean;
    authorized: boolean;
    pid: number | null;
    uptime_sec: number;
    log_tail: string[];
    message?: string;
  } | null> {
    try {
      const res = await fetch("/api/extra/engine/status", { method: "GET" });
      if (res.ok) return (await res.json()) as any;
      return null;
    } catch {
      return null;
    }
  }

  async restartEngine(): Promise<{ ok: boolean; state: string; message: string }> {
    try {
      const res = await fetch("/api/extra/engine/restart", { method: "POST" });
      const data = await res.json().catch(() => ({}));
      if (res.ok && (data?.state === "online" || data?.authorized)) {
        return { ok: true, state: data.state, message: data.message || "Engine restarted" };
      }
      return { ok: false, state: data?.state || "unknown", message: data?.message || `Restart failed (HTTP ${res.status})` };
    } catch (e: any) {
      return { ok: false, state: "unreachable", message: e?.message || "App server unreachable" };
    }
  }

  startPolling(
    callback: (data: LiveTelemetryResponse | null, isOnline: boolean) => void,
    intervalMs: number = 2000
  ): () => void {
    if (this.isPolling) {
      return () => this.stopPolling();
    }

    this.isPolling = true;

    const tick = async () => {
      const health = await this.checkHealth(1000);
      const isOnline = health.status === "healthy";

      if (isOnline) {
        const data = await this.fetchTelemetry(1500);
        callback(data, true);
      } else {
        callback(null, false);
      }
    };

    tick();
    this.pollIntervalId = window.setInterval(tick, intervalMs);

    return () => this.stopPolling();
  }

  stopPolling(): void {
    if (this.pollIntervalId !== null) {
      clearInterval(this.pollIntervalId);
      this.pollIntervalId = null;
    }
    this.isPolling = false;
  }
}

export const telemetryClient = new LoopbackTelemetryClient();
