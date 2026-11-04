/**
 * Project Extra — AI Client Auto-Configurator Service
 * Scans host for installed AI environments (Claude Desktop, Cursor, Windsurf, Claude Code, Antigravity)
 * and provisions them to use the local Extra MCP server with 1 tap.
 */

export interface AIClient {
  client_id: string;
  name: string;
  is_installed: boolean;
  is_configured: boolean;
  config_path?: string | null;
  details?: string;
}

const LOCAL_SERVER_BASE_URL = "";

class ClientConfigService {
  private baseUrl: string;

  constructor(baseUrl: string = LOCAL_SERVER_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  /**
   * Scans the host system for supported AI developer tools.
   */
  async fetchInstalledClients(): Promise<AIClient[]> {
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 2000);

      const res = await fetch(`${this.baseUrl}/api/clients`, {
        signal: controller.signal,
      });
      clearTimeout(timer);

      if (res.ok) {
        const data = await res.json();
        if (data.status === "ok" && Array.isArray(data.clients)) {
          return data.clients;
        }
      }
      return this.getFallbackClients();
    } catch {
      return this.getFallbackClients();
    }
  }

  /**
   * Configures a single AI client to use the Extra MCP server.
   */
  async configureClient(clientId: string): Promise<boolean> {
    try {
      const res = await fetch(`${this.baseUrl}/api/clients/configure`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ client_id: clientId }),
      });
      if (res.ok) {
        const data = await res.json();
        return !!(data.results?.[clientId] || (data.success && data.configured === clientId));
      }
      return false;
    } catch (e) {
      console.error(`[ClientConfigService] Failed to configure ${clientId}:`, e);
      return false;
    }
  }

  /**
   * Configures all detected AI clients in one batch.
   */
  async configureAllClients(): Promise<Record<string, boolean>> {
    try {
      const res = await fetch(`${this.baseUrl}/api/clients/configure`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ all: true }),
      });
      if (res.ok) {
        const data = await res.json();
        return data.results || {};
      }
      return {};
    } catch (e) {
      console.error("[ClientConfigService] Failed to configure all clients:", e);
      return {};
    }
  }

  /**
   * Safe fallback client list if the daemon is offline.
   */
  private getFallbackClients(): AIClient[] {
    return [
      {
        client_id: "claude_desktop",
        name: "Claude Desktop",
        is_installed: true,
        is_configured: false,
        details: "Claude for macOS and Windows",
      },
      {
        client_id: "cursor",
        name: "Cursor IDE",
        is_installed: true,
        is_configured: false,
        details: "AI-first Code Editor",
      },
      {
        client_id: "chatgpt",
        name: "ChatGPT Desktop / Cloud",
        is_installed: true,
        is_configured: false,
        details: "Connect via Extra Cloud Hub",
      },
      {
        client_id: "windsurf",
        name: "Windsurf IDE",
        is_installed: false,
        is_configured: false,
        details: "Codeium AI Editor",
      },
    ];
  }
}

export const clientConfigService = new ClientConfigService();
