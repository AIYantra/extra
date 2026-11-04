import { useState, useEffect } from "react";
import {
  RefreshCw,
  Copy,
  Check,
  Laptop,
  Terminal,
  Zap,
  Globe,
  Link2,
  Cable,
  ArrowRight,
} from "lucide-react";
import { clientConfigService, type AIClient } from "../../services/clientConfigService";
import { soundEngine } from "../../utils/sound";
import { getClientLogo } from "../../utils/clientLogos";
import { toast } from "sonner";

interface ConnectedAppsViewProps {
  onNavigateTab?: (tab: string) => void;
}

export function ConnectedAppsView({ onNavigateTab }: ConnectedAppsViewProps) {
  const [clients, setClients] = useState<AIClient[]>([]);
  const [loading, setLoading] = useState(true);
  const [updatingId, setUpdatingId] = useState<string | null>(null);
  const [isConfiguringAll, setIsConfiguringAll] = useState(false);
  const [copiedSnippet, setCopiedSnippet] = useState(false);

  const loadClients = async () => {
    setLoading(true);
    const list = await clientConfigService.fetchInstalledClients();
    setClients(list);
    setLoading(false);
  };

  useEffect(() => {
    loadClients();
  }, []);

  const handleToggle = async (clientId: string) => {
    setUpdatingId(clientId);
    soundEngine.playTick();
    const success = await clientConfigService.configureClient(clientId);
    if (success) {
      if (clientId === "chatgpt") {
        try {
          navigator.clipboard.writeText("https://extra.yantraos.com/sse");
        } catch {}
        toast.success("ChatGPT Desktop / Cloud linked! SSE URL copied to clipboard.");
      } else {
        const clientName = clients.find((c) => c.client_id === clientId)?.name || clientId.replace("_", " ");
        toast.success(`${clientName} linked successfully`);
      }
      soundEngine.playSuccessChime();
    } else {
      toast.error(`Could not configure ${clientId}`);
    }
    await loadClients();
    setUpdatingId(null);
  };

  const handleConnectAll = async () => {
    setIsConfiguringAll(true);
    soundEngine.playTick();
    const results = await clientConfigService.configureAllClients();
    const count = Object.values(results).filter(Boolean).length;
    if (count > 0) {
      toast.success(`Connected ${count} environments`);
      soundEngine.playSuccessChime();
    } else {
      toast.info("All detected clients are connected");
    }
    await loadClients();
    setIsConfiguringAll(false);
  };

  const getClientIcon = (id?: string) => {
    if (!id) return Globe;
    switch (id) {
      case "claude_desktop":
      case "claude_code":
        return Terminal;
      case "cursor":
        return Laptop;
      case "antigravity":
        return Zap;
      default:
        return Globe;
    }
  };

  const mcpConfigSnippet = JSON.stringify(
    {
      mcpServers: {
        extra: {
          url: "http://127.0.0.1:8000/sse",
        },
      },
    },
    null,
    2
  );

  const handleCopySnippet = () => {
    soundEngine.playTick();
    navigator.clipboard.writeText(mcpConfigSnippet);
    setCopiedSnippet(true);
    toast.success("Configuration copied");
    setTimeout(() => setCopiedSnippet(false), 2000);
  };

  const installedCount = clients.filter((c) => c.is_installed).length;
  const connectedCount = clients.filter((c) => c.is_configured).length;

  return (
    <div className="space-y-4 pb-12 animate-in fade-in duration-150">
      {/* Calm Unboxed Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#dfe4eb] select-none">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-[#0a0d14] tracking-tight">
              Connected AI Environments
            </h2>
            <span className="text-[10px] font-mono text-[#525866] bg-[#f8f9fb] border border-[#dfe4eb] px-1.5 py-0.5 rounded-md tabular-nums">
              {connectedCount} of {installedCount} linked
            </span>
          </div>
          <p className="text-xs text-[#525866] mt-0.5">
            Hardware bridge for Claude, Cursor, Antigravity, and Windsurf
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={loadClients}
            disabled={loading}
            className="p-1.5 rounded-lg border border-[#dfe4eb] bg-white text-[#868c98] hover:text-[#0a0d14] hover:bg-[#f8f9fb] transition-colors duration-150 cursor-pointer"
            title="Rescan"
          >
            <RefreshCw className={`size-3.5 ${loading ? "animate-spin text-[#1677ff]" : ""}`} />
          </button>

          <button
            onClick={handleConnectAll}
            disabled={isConfiguringAll || loading || installedCount === 0}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#1a1a1c] hover:bg-[#2c3038] text-white font-medium text-xs shadow-2xs transition-colors duration-150 cursor-pointer disabled:opacity-50"
          >
            <Link2 className="size-3.5" />
            <span>Connect all ({installedCount})</span>
          </button>
        </div>
      </div>

      {/* Plugin & Web Connectors Callout Banner */}
      <div className="p-3.5 rounded-xl bg-gradient-to-r from-[#1677ff]/5 via-white to-[#1677ff]/5 border border-[#1677ff]/20 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-2xs">
        <div className="flex items-center gap-3">
          <div className="size-8 rounded-lg bg-[#1677ff]/10 border border-[#1677ff]/20 flex items-center justify-center shrink-0">
            <Cable className="size-4 text-[#1677ff]" />
          </div>
          <div>
            <h3 className="text-xs font-semibold text-[#1a1a1c] flex items-center gap-1.5">
              <span>ChatGPT.com & Claude.ai Connectors Guide</span>
              <span className="text-[10px] font-mono bg-[#1677ff] text-white px-1.5 py-0.2 rounded-md font-medium">
                New
              </span>
            </h3>
            <p className="text-[11px] text-[#525866] mt-0.5">
              Step-by-step setup for OpenAI Custom GPT Actions, OpenAPI schemas, and Claude.ai Web Projects
            </p>
          </div>
        </div>

        <button
          onClick={() => {
            soundEngine.playTick();
            onNavigateTab?.("connectors");
          }}
          className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-[#1677ff] hover:bg-[#0958d9] text-white text-xs font-medium shadow-2xs transition-colors cursor-pointer shrink-0"
        >
          <span>Open Setup Page</span>
          <ArrowRight className="size-3" />
        </button>
      </div>

      {/* Lightweight Clients Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {clients.map((client, idx) => {
          const clientId = client.client_id || client.name?.toLowerCase().replace(/\s+/g, "_") || `client_${idx}`;
          const logoUrl = getClientLogo(client.client_id) || getClientLogo(client.name);
          const Icon = getClientIcon(clientId);
          const isUpdating = updatingId === clientId || isConfiguringAll;

          return (
            <div
              key={clientId}
              className="p-3.5 rounded-xl bg-white border border-[#dfe4eb] shadow-2xs hover:border-[#1677ff]/30 transition-colors duration-150 flex items-center justify-between gap-3 group"
            >
              <div className="flex items-center gap-3 min-w-0">
                <div className="size-9 rounded-lg bg-[#f8f9fb] border border-[#dfe4eb] flex items-center justify-center p-1.5 shrink-0 group-hover:border-[#1677ff]/30 transition-colors">
                  {logoUrl ? (
                    <img
                      src={logoUrl}
                      alt={client.name}
                      className="size-5 object-contain"
                    />
                  ) : (
                    <Icon className="size-4 text-[#525866]" />
                  )}
                </div>

                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-xs text-[#0a0d14] tracking-tight truncate">
                      {client.name}
                    </h3>
                    <span className="inline-flex items-center gap-1.5 text-xs text-[#525866] font-normal shrink-0">
                      <span
                        className={`size-1.5 rounded-full ${
                          client.is_configured
                            ? "bg-[#0e8345]"
                            : client.is_installed
                            ? "bg-[#1677ff]"
                            : "bg-[#868c98]"
                        }`}
                      />
                      <span>
                        {client.is_configured ? "Linked" : client.is_installed ? "Ready" : "Missing"}
                      </span>
                    </span>
                  </div>

                  {client.config_path ? (
                    <p className="text-[11px] font-mono text-[#868c98] truncate max-w-[240px] mt-0.5">
                      {client.config_path}
                    </p>
                  ) : (
                    <p className="text-[11px] text-[#868c98] mt-0.5">
                      {client.details || "Direct loopback"}
                    </p>
                  )}
                </div>
              </div>

              <button
                onClick={() => handleToggle(clientId)}
                disabled={isUpdating || client.is_installed === false}
                className={`px-3 py-1 rounded-lg text-xs font-medium shadow-2xs transition-colors duration-150 cursor-pointer shrink-0 disabled:opacity-50 ${
                  client.is_configured
                    ? "bg-[#f8f9fb] hover:bg-[#eceff4] text-[#1a1a1c] border border-[#dfe4eb]"
                    : "bg-white hover:bg-[#f8f9fb] text-[#1677ff] hover:text-[#0958d9] border border-[#1677ff]/30"
                }`}
              >
                {isUpdating ? "Linking..." : client.is_configured ? "Re-link" : "Connect"}
              </button>
            </div>
          );
        })}
      </div>

      {/* Manual JSON Config Snippet */}
      <div className="p-3.5 rounded-xl bg-white border border-[#dfe4eb] shadow-2xs space-y-2.5">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-xs text-[#0a0d14]">
              Manual MCP Configuration
            </h3>
            <p className="text-[11px] text-[#525866]">
              Standard loopback schema for custom agents
            </p>
          </div>

          <button
            onClick={handleCopySnippet}
            className="flex items-center gap-1 px-2.5 py-1 rounded-lg border border-[#dfe4eb] bg-white hover:bg-[#f8f9fb] text-[#0a0d14] text-xs font-medium shadow-2xs transition-colors duration-150 cursor-pointer"
          >
            {copiedSnippet ? <Check className="size-3.5 text-[#0e8345]" /> : <Copy className="size-3.5 text-[#525866]" />}
            <span>{copiedSnippet ? "Copied" : "Copy"}</span>
          </button>
        </div>

        <pre className="p-2.5 rounded-lg bg-[#f8f9fb] border border-[#dfe4eb] font-mono text-xs text-[#0a0d14] overflow-x-auto">
          {mcpConfigSnippet}
        </pre>
      </div>
    </div>
  );
}
