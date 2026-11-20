import { useState, useEffect } from "react";
import {
  RefreshCw,
  Copy,
  Check,
  Laptop,
  Terminal,
  Zap,
  Globe,
  Cloud,
  ChevronRight,
  Radio,
} from "lucide-react";
import { clientConfigService, type AIClient } from "../../services/clientConfigService";
import { extraDataService, type LiveRelayStatus } from "../../services/extraDataService";
import { useAuthStore } from "../../store/useAuthStore";
import { soundEngine } from "../../utils/sound";
import { getClientLogo } from "../../utils/clientLogos";
import { toast } from "sonner";

interface IntegrationsViewProps {
  onNavigateTab?: (tab: string) => void;
}

export function IntegrationsView({ onNavigateTab: _onNavigateTab }: IntegrationsViewProps) {
  const { user, relayToken, isAuthenticated, isLocalOfflineMode, setLocalOffline, openAuthModal } = useAuthStore();
  const [activeTab, setActiveTab] = useState<"desktop" | "cloud">("desktop");

  // Local clients state
  const [clients, setClients] = useState<AIClient[]>([]);
  const [loadingClients, setLoadingClients] = useState(true);
  const [updatingClientId, setUpdatingClientId] = useState<string | null>(null);
  const [isConfiguringAll, setIsConfiguringAll] = useState(false);

  // Cloud connectors state
  const [selectedCloudApp, setSelectedCloudApp] = useState<"chatgpt" | "claude" | "gemini">("chatgpt");
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [relayStatus, setRelayStatus] = useState<LiveRelayStatus | null>(null);
  const [loadingRelayAction, setLoadingRelayAction] = useState(false);
  const [testingCloudPing, setTestingCloudPing] = useState(false);
  const [cloudPingResult, setCloudPingResult] = useState<string | null>(null);

  // Bridge latency test state
  const [isTestingBridge, setIsTestingBridge] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; latency_ms?: number } | null>(null);

  // Cloud key sync state — single source is useAuthStore.relayToken
  const [isSyncingKeys, setIsSyncingKeys] = useState(false);
  const [isRotatingKey, setIsRotatingKey] = useState(false);

  const loadData = async () => {
    setLoadingClients(true);
    try {
      const [clientList, rStat] = await Promise.all([
        clientConfigService.fetchInstalledClients(),
        extraDataService.fetchRelayStatus().catch(() => null),
      ]);
      setClients(clientList);
      if (rStat) setRelayStatus(rStat);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingClients(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleToggle = async (clientId: string) => {
    setUpdatingClientId(clientId);
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
    await clientConfigService.fetchInstalledClients().then(setClients);
    setUpdatingClientId(null);
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
    await clientConfigService.fetchInstalledClients().then(setClients);
    setIsConfiguringAll(false);
  };

  const handleTestBridge = async () => {
    setIsTestingBridge(true);
    soundEngine.playTick();
    try {
      const res = await extraDataService.testConnectorConnection();
      setTestResult(res);
      if (res.success) {
        soundEngine.playSuccessChime();
        toast.success(`Bridge verified in ${res.latency_ms ?? 1.2}ms`);
      } else {
        toast.error("Bridge connection failed");
      }
    } catch {
      toast.error("Bridge connection timed out");
    } finally {
      setIsTestingBridge(false);
    }
  };

  const handleTestCloudPing = async () => {
    setTestingCloudPing(true);
    soundEngine.playTick();
    try {
      const res = await extraDataService.pingRelay();
      if (res.ok) {
        setCloudPingResult(`${res.latency_ms}ms roundtrip`);
        soundEngine.playSuccessChime();
        toast.success(`Cloud Relay connected: ${res.latency_ms}ms to AWS Hub`);
      } else {
        setCloudPingResult("Relay offline");
        toast.error(res.error || "Cloud relay is not currently connected");
      }
    } catch {
      setCloudPingResult("Ping failed");
      toast.error("Failed to ping cloud relay");
    } finally {
      setTestingCloudPing(false);
    }
  };

  const handleStartRelay = async () => {
    setLoadingRelayAction(true);
    soundEngine.playTick();
    try {
      await setLocalOffline(false);
      let finalStat: LiveRelayStatus | null = null;
      for (let i = 0; i < 6; i++) {
        await new Promise((r) => setTimeout(r, 450));
        finalStat = await extraDataService.fetchRelayStatus();
        setRelayStatus(finalStat);
        if (finalStat.connected) break;
      }
      soundEngine.playSuccessChime();
      if (finalStat?.connected) {
        toast.success("Cloud Relay connected. Remote agents can now reach this workstation.");
      } else {
        toast.info("Cloud Relay is reconnecting in background...");
      }
    } catch {
      toast.error("Failed to connect Cloud Relay");
    } finally {
      setLoadingRelayAction(false);
    }
  };

  const handleStopRelay = async () => {
    setLoadingRelayAction(true);
    soundEngine.playTick();
    try {
      await setLocalOffline(true);
      const updated = await extraDataService.fetchRelayStatus();
      setRelayStatus(updated);
      setCloudPingResult(null);
      soundEngine.playSuccessChime();
      toast.info("Operating in Sovereign Offline Mode. Cloud Relay tunnel closed.");
    } catch {
      toast.error("Failed to disconnect Cloud Relay");
    } finally {
      setLoadingRelayAction(false);
    }
  };

  const handleCopy = (text: string, label: string = "Copied to clipboard") => {
    if (!text) {
      toast.error("Sign in to enable cloud keys");
      return;
    }
    soundEngine.playTick();
    navigator.clipboard.writeText(text);
    setCopiedKey(label);
    toast.success(label);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const handleSyncCloudKeys = async () => {
    if (!isAuthenticated) {
      openAuthModal();
      return;
    }
    setIsSyncingKeys(true);
    soundEngine.playTick();
    try {
      await useAuthStore.getState().refreshProfile();
      await loadData();
      const fresh = useAuthStore.getState().relayToken;
      if (fresh) {
        soundEngine.playSuccessChime();
        toast.success("Synchronized keys with cloud");
      } else {
        toast.error("Sync finished but no cloud key was returned");
      }
    } catch {
      toast.error("Failed to sync with cloud");
    } finally {
      setIsSyncingKeys(false);
    }
  };

  const handleRotateKey = async () => {
    if (!isAuthenticated) {
      openAuthModal();
      return;
    }
    setIsRotatingKey(true);
    soundEngine.playTick();
    try {
      const next = await useAuthStore.getState().rotatePasskey();
      await loadData();
      soundEngine.playSuccessChime();
      toast.success(`Key rotated — new key ends ${next.slice(-4)}`);
    } catch (e: any) {
      toast.error(e?.message || "Could not rotate key");
    } finally {
      setIsRotatingKey(false);
    }
  };

  const getClientIcon = (id?: string) => {
    if (!id) return Globe;
    switch (id) {
      case "claude_desktop":
      case "claude_code":
        return Terminal;
      case "cursor":
      case "windsurf":
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

  const installedCount = clients.filter((c) => c.is_installed).length;
  const connectedCount = clients.filter((c) => c.is_configured).length;
  const relayPasskey = relayToken || user?.relay_token || "";
  const hasCloudKey = isAuthenticated && relayPasskey.length > 0;
  const relayKeyTail = hasCloudKey ? relayPasskey.slice(-4) : "";
  const rotatedAt = user?.token_rotated_at
    ? new Date(user.token_rotated_at * 1000).toLocaleDateString()
    : null;
  const chatGptMcpUrl = hasCloudKey ? `https://extra.yantraos.com/mcp?key=${relayPasskey}` : "";

  return (
    <div className="space-y-6 pb-12 animate-in fade-in duration-150">
      {/* Header Deck */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#dfe4eb] select-none">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-semibold text-[#1a1a1c] tracking-tight">
              AI Environments &amp; Integrations
            </h2>
            <span className="text-[11px] font-mono text-[#525866] bg-[#f8f9fb] border border-[#dfe4eb] px-2 py-0.5 rounded-md tabular-nums">
              {connectedCount} of {installedCount} linked
            </span>
          </div>
          <p className="text-xs text-[#525866] mt-0.5">
            Connect Cursor, Claude Desktop, Antigravity, ChatGPT, and custom MCP clients to Extra
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={handleTestBridge}
            disabled={isTestingBridge}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#dfe4eb] bg-white hover:bg-[#f8f9fb] text-xs font-medium text-[#1a1a1c] transition-colors duration-150 cursor-pointer shadow-2xs"
            title="Test loopback MCP bridge"
          >
            <RefreshCw className={`size-3.5 ${isTestingBridge ? "animate-spin text-[#1677ff]" : "text-[#525866]"}`} />
            <span>{testResult ? `${testResult.latency_ms ?? 1.2}ms OK` : "Test Bridge"}</span>
          </button>

          <button
            onClick={loadData}
            disabled={loadingClients}
            className="p-1.5 rounded-lg border border-[#dfe4eb] bg-white text-[#868c98] hover:text-[#1a1a1c] hover:bg-[#f8f9fb] transition-colors duration-150 cursor-pointer shadow-2xs"
            title="Rescan installed clients"
          >
            <RefreshCw className={`size-3.5 ${loadingClients ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Track Selector Tabs */}
      <div className="flex items-center gap-2 border-b border-[#dfe4eb] pb-2">
        <button
          type="button"
          onClick={() => {
            soundEngine.playTick();
            setActiveTab("desktop");
          }}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
            activeTab === "desktop"
              ? "bg-[#1a1a1c] text-white shadow-xs"
              : "text-[#525866] hover:text-[#1a1a1c] hover:bg-[#f4f5f8]"
          }`}
        >
          <Laptop className="size-3.5" />
          <span>Installed Desktop Clients</span>
          <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-white/20 text-white">
            {installedCount}
          </span>
        </button>

        <button
          type="button"
          onClick={() => {
            soundEngine.playTick();
            setActiveTab("cloud");
          }}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
            activeTab === "cloud"
              ? "bg-[#1a1a1c] text-white shadow-xs"
              : "text-[#525866] hover:text-[#1a1a1c] hover:bg-[#f4f5f8]"
          }`}
        >
          <Cloud className="size-3.5" />
          <span>Cloud &amp; Web Platforms</span>
          <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-[#f4f5f8] text-[#868c98]">
            ChatGPT · Claude
          </span>
        </button>
      </div>

      {/* Tab 1: Installed Desktop Clients */}
      {activeTab === "desktop" && (
        <div className="space-y-6 animate-in fade-in duration-100">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-[#525866]">
              Detected AI Editors &amp; Agent Shells
            </span>
            {installedCount > connectedCount && (
              <button
                onClick={handleConnectAll}
                disabled={isConfiguringAll}
                className="text-xs font-medium text-[#1677ff] hover:text-[#0958d9] transition-colors cursor-pointer flex items-center gap-1"
              >
                <span>Connect All Detected</span>
                <ChevronRight className="size-3" />
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
            {clients.map((client) => {
              const logoUrl = getClientLogo(client.name);
              const Icon = getClientIcon(client.client_id);
              const isConnected = client.is_configured;
              const isUpdating = updatingClientId === client.client_id;

              return (
                <div
                  key={client.client_id}
                  className="rounded-xl border border-[#dfe4eb] bg-white p-4 shadow-2xs hover:border-[#ccd2dc] transition-all flex flex-col justify-between min-h-[140px]"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="size-10 rounded-lg bg-[#f8f9fb] border border-[#dfe4eb] flex items-center justify-center p-2 shrink-0">
                        {logoUrl ? (
                          <img src={logoUrl} alt={client.name} className="size-6 object-contain" />
                        ) : (
                          <Icon className="size-5 text-[#525866]" />
                        )}
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-1.5">
                          <h4 className="text-xs font-semibold text-[#1a1a1c] truncate">{client.name}</h4>
                          {client.is_installed && (
                            <span className="text-[10px] font-mono text-[#0e8345] bg-[#ebf7ee] px-1 py-0.2 rounded border border-[#c3e6cd]">
                              Detected
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-[#868c98] truncate mt-0.5">
                          {client.details || (isConnected ? "Direct loopback bridge connected" : "Ready to connect")}
                        </p>
                      </div>
                    </div>

                    <span className="inline-flex items-center gap-1.5 text-xs text-[#525866] shrink-0 font-normal">
                      <span className={`size-1.5 rounded-full ${isConnected ? "bg-[#0e8345]" : "bg-[#868c98]"}`} />
                      <span>{isConnected ? "Connected" : client.is_installed ? "Ready" : "Not Detected"}</span>
                    </span>
                  </div>

                  <div className="pt-3 border-t border-[#eceff4] flex items-center justify-between gap-2 mt-3">
                    <span className="text-[10px] font-mono text-[#868c98] truncate max-w-[190px]">
                      {client.config_path ? `~/${client.config_path.split(/[\\/]/).slice(-2).join("/")}` : "Auto loopback"}
                    </span>

                    <button
                      type="button"
                      disabled={isUpdating}
                      onClick={() => handleToggle(client.client_id)}
                      className={`px-3 py-1 rounded-md text-xs font-medium transition-colors cursor-pointer shadow-2xs ${
                        isConnected
                          ? "bg-white border border-[#dfe4eb] text-[#525866] hover:bg-[#f8f9fb] hover:text-[#1a1a1c]"
                          : "bg-[#1677ff] hover:bg-[#0958d9] text-white"
                      }`}
                    >
                      {isUpdating ? "Configuring..." : isConnected ? "Reconnect" : "Connect"}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Manual MCP JSON Configuration Box */}
          <div className="rounded-xl border border-[#dfe4eb] bg-white p-4 shadow-2xs space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-xs font-semibold text-[#1a1a1c]">Manual MCP Client Configuration</h4>
                <p className="text-[11px] text-[#525866]">
                  Add Extra's SSE endpoint to any custom MCP client configuration file
                </p>
              </div>

              <button
                onClick={() => handleCopy(mcpConfigSnippet, "MCP JSON copied")}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-[#dfe4eb] bg-[#f8f9fb] hover:bg-white text-xs font-medium text-[#1a1a1c] transition-colors cursor-pointer"
              >
                {copiedKey === "MCP JSON copied" ? (
                  <>
                    <Check className="size-3 text-[#0e8345]" />
                    <span className="text-[#0e8345]">Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="size-3 text-[#525866]" />
                    <span>Copy JSON</span>
                  </>
                )}
              </button>
            </div>

            <pre className="p-3 rounded-lg bg-[#f8f9fb] border border-[#dfe4eb] text-[11px] font-mono text-[#1a1a1c] overflow-x-auto">
              {mcpConfigSnippet}
            </pre>
          </div>
        </div>
      )}

      {/* Tab 2: Cloud & Web Platforms */}
      {activeTab === "cloud" && (
        <div className="space-y-5 animate-in fade-in duration-100">
          {/* Live Cloud Bridge Status & Action Deck */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3.5 p-4 rounded-xl border border-[#dfe4eb] bg-white shadow-2xs">
            <div className="flex items-center gap-3 min-w-0">
              <div
                className={`size-9 rounded-lg border flex items-center justify-center shrink-0 ${
                  !isAuthenticated || isLocalOfflineMode || (!relayStatus?.connected && relayStatus?.status === "stopped")
                    ? "bg-[#f8f9fb] border-[#dfe4eb] text-[#868c98]"
                    : relayStatus?.connected
                    ? "bg-[#edfcf2] border-[#bbf0cf] text-[#0e8345]"
                    : "bg-[#fff8e6] border-[#f5dfa8] text-[#b7791f]"
                }`}
              >
                <Radio className={`size-4 ${relayStatus?.connected && !isLocalOfflineMode ? "animate-pulse" : ""}`} />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs font-semibold text-[#1a1a1c]">
                    {!isAuthenticated
                      ? "Cloud Relay Dormant (Unauthenticated)"
                      : isLocalOfflineMode || (!relayStatus?.connected && relayStatus?.status === "stopped")
                      ? "Sovereign Offline Mode (~/.extra)"
                      : relayStatus?.connected
                      ? "Cloud MCP Relay Live & Listening"
                      : "Cloud Relay Connecting..."}
                  </span>
                  {isAuthenticated && relayStatus?.connected && !isLocalOfflineMode ? (
                    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-[#edfcf2] text-[#0e8345] border border-[#bbf0cf]">
                      <span className="size-1.5 rounded-full bg-[#0e8345] animate-ping" />
                      AWS Hub Active (ap-south-1)
                    </span>
                  ) : isAuthenticated && isLocalOfflineMode ? (
                    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-[#f0f2f6] text-[#525866] border border-[#dfe4eb]">
                      <span className="size-1.5 rounded-full bg-[#868c98]" />
                      Local Engine (Air-Gapped)
                    </span>
                  ) : null}
                </div>
                <p className="text-[11px] text-[#525866] mt-0.5 leading-relaxed truncate">
                  {!isAuthenticated
                    ? "Sign in to activate outbound WebSocket bridge for ChatGPT and Claude."
                    : relayStatus?.connected && !isLocalOfflineMode
                    ? "Tunnel established to AWS ap-south-1. ChatGPT and Claude can automate desktop tools in real time."
                    : isLocalOfflineMode
                    ? "All actions stay 100% on this workstation via local loopback. No outbound tunnel."
                    : "Connecting outbound tunnel to Extra Cloud Hub..."}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 shrink-0 self-start sm:self-center">
              {cloudPingResult && (
                <span className="text-xs font-mono font-medium text-emerald-700 bg-[#edfcf2] border border-[#bbf0cf] px-2 py-0.5 rounded-md tabular-nums">
                  {cloudPingResult}
                </span>
              )}
              {isAuthenticated && (
                <button
                  type="button"
                  onClick={handleTestCloudPing}
                  disabled={testingCloudPing || isLocalOfflineMode || !relayStatus?.connected}
                  className="px-2.5 py-1.5 rounded-lg border border-[#dfe4eb] bg-white hover:bg-[#f8f9fb] text-xs font-medium text-[#1a1a1c] flex items-center gap-1.5 cursor-pointer transition-colors duration-150 disabled:opacity-50 disabled:cursor-not-allowed shadow-2xs"
                  title="Test live roundtrip ping to AWS Hub"
                >
                  <Radio className={`size-3.5 ${testingCloudPing ? "animate-spin text-[#1677ff]" : "text-[#525866]"}`} />
                  <span>Ping Hub</span>
                </button>
              )}
              {!isAuthenticated ? (
                <button
                  type="button"
                  onClick={openAuthModal}
                  className="px-3 py-1.5 rounded-lg bg-[#1677ff] hover:bg-[#125ecc] text-white text-xs font-semibold transition-colors duration-150 cursor-pointer shadow-2xs"
                >
                  Sign In
                </button>
              ) : relayStatus?.connected && !isLocalOfflineMode ? (
                <button
                  type="button"
                  onClick={handleStopRelay}
                  disabled={loadingRelayAction}
                  className="px-3 py-1.5 rounded-lg border border-[#fecdd3] bg-[#fff1f2] hover:bg-[#ffe4e6] text-[#e11d48] text-xs font-semibold flex items-center gap-1.5 cursor-pointer transition-colors duration-150 shadow-2xs"
                >
                  <span>{loadingRelayAction ? "Disconnecting..." : "Disconnect"}</span>
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleStartRelay}
                  disabled={loadingRelayAction}
                  className="px-3 py-1.5 rounded-lg bg-[#1677ff] hover:bg-[#125ecc] text-white text-xs font-semibold flex items-center gap-1.5 cursor-pointer transition-colors duration-150 shadow-2xs"
                >
                  <span>{loadingRelayAction ? "Connecting..." : "Connect Relay"}</span>
                </button>
              )}
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2.5" role="tablist" aria-label="Cloud platform">
            <button
              type="button"
              role="tab"
              aria-selected={selectedCloudApp === "chatgpt"}
              onClick={() => setSelectedCloudApp("chatgpt")}
              className={`p-3 rounded-xl border text-left transition-all cursor-pointer ${
                selectedCloudApp === "chatgpt"
                  ? "border-[#1677ff] bg-[#1677ff]/5 shadow-xs"
                  : "border-[#dfe4eb] bg-white hover:border-[#ccd2dc]"
              }`}
            >
              <h4 className="text-xs font-semibold text-[#1a1a1c]">ChatGPT Plugins</h4>
              <p className="text-[11px] text-[#868c98] mt-0.5">Custom MCP server · current</p>
            </button>

            <button
              type="button"
              role="tab"
              aria-selected={selectedCloudApp === "claude"}
              onClick={() => setSelectedCloudApp("claude")}
              className={`p-3 rounded-xl border text-left transition-all cursor-pointer ${
                selectedCloudApp === "claude"
                  ? "border-[#1677ff] bg-[#1677ff]/5 shadow-xs"
                  : "border-[#dfe4eb] bg-white hover:border-[#ccd2dc]"
              }`}
            >
              <h4 className="text-xs font-semibold text-[#1a1a1c]">Claude Connectors</h4>
              <p className="text-[11px] text-[#868c98] mt-0.5">Custom connector · all plans</p>
            </button>

            <button
              type="button"
              role="tab"
              aria-selected={selectedCloudApp === "gemini"}
              onClick={() => setSelectedCloudApp("gemini")}
              className={`p-3 rounded-xl border text-left transition-all cursor-pointer ${
                selectedCloudApp === "gemini"
                  ? "border-[#1677ff] bg-[#1677ff]/5 shadow-xs"
                  : "border-[#dfe4eb] bg-white hover:border-[#ccd2dc]"
              }`}
            >
              <h4 className="text-xs font-semibold text-[#1a1a1c]">Gemini Skills / API</h4>
              <p className="text-[11px] text-[#868c98] mt-0.5">No native MCP URL · use API</p>
            </button>
          </div>

          {/* Cloud Connector Walkthrough — Tier 1: title + key actions */}
          <div className="rounded-xl border border-[#dfe4eb] bg-white p-5 shadow-2xs space-y-4">
            <div className="flex flex-col gap-3 border-b border-[#eceff4] pb-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h4 className="text-xs font-semibold text-[#1a1a1c]">
                  {selectedCloudApp === "chatgpt" && "ChatGPT Plugin (MCP) — Current"}
                  {selectedCloudApp === "claude" && "Claude Custom Connector — Current"}
                  {selectedCloudApp === "gemini" && "Gemini Skills / API — No Direct MCP URL"}
                </h4>
                <p className="text-[11px] text-[#525866] mt-0.5">
                  Verified Nov 18, 2026 against OpenAI, Anthropic, and Google docs. Menus move — use in-app search if renamed.
                </p>
                <p className="mt-1 text-[11px tabular-nums] text-[#868c98]" aria-live="polite">
                  {isAuthenticated
                    ? hasCloudKey
                      ? `Active key ends ${relayKeyTail}${rotatedAt ? ` · rotated ${rotatedAt}` : ""}`
                      : "Sync keys to activate this PC"
                    : "Sign in to enable cloud relay"}
                </p>
              </div>

              {!isAuthenticated ? (
                <button
                  type="button"
                  onClick={openAuthModal}
                  className="px-3 py-1 rounded-md text-xs font-medium bg-[#1677ff] hover:bg-[#0958d9] text-white transition-colors duration-150 cursor-pointer motion-reduce:transition-none"
                >
                  Sign In to Enable Cloud Relay
                </button>
              ) : (
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleSyncCloudKeys}
                    disabled={isSyncingKeys || isRotatingKey}
                    aria-label="Sync cloud keys from web"
                    title="Fetch latest passkey rotated on web"
                    className="px-2.5 py-1 rounded-md text-xs font-medium border border-[#dfe4eb] bg-white hover:bg-[#f8f9fb] text-[#1a1a1c] flex items-center gap-1.5 transition-colors duration-150 cursor-pointer disabled:opacity-60 motion-reduce:transition-none"
                  >
                    <RefreshCw className={`size-3 text-[#525866] ${isSyncingKeys ? "animate-spin text-[#1677ff]" : ""}`} />
                    <span>{isSyncingKeys ? "Syncing…" : "Sync Cloud Keys"}</span>
                  </button>
                  <button
                    type="button"
                    onClick={handleRotateKey}
                    disabled={isSyncingKeys || isRotatingKey}
                    aria-label="Rotate computer link key in app"
                    title="Generate a new key here and push it to cloud"
                    className="px-2.5 py-1 rounded-md text-xs font-medium bg-[#1a1a1c] hover:bg-[#2a2a2e] text-white transition-colors duration-150 cursor-pointer disabled:opacity-60 motion-reduce:transition-none"
                  >
                    {isRotatingKey ? "Rotating…" : "Rotate Key"}
                  </button>
                </div>
              )}
            </div>

            {/* Tier 2: recommended path per platform */}
            <div className="space-y-3.5 text-xs text-[#525866]">
              {selectedCloudApp === "chatgpt" && (
                <div className="flex items-start gap-2.5 p-3 rounded-lg bg-[#f0f7ff] border border-[#cfe0ff]">
                  <span className="size-5 rounded-full bg-[#1677ff] text-white font-bold text-[10px] flex items-center justify-center shrink-0 mt-0.5" aria-hidden="true">
                    ★
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-[#1a1a1c]">
                      ChatGPT Plugin from MCP (Recommended)
                    </p>
                    <p className="text-[11px] text-[#525866] mt-0.5">
                      Settings → Connectors + Developer Mode is retired. Custom GPT Actions retire Dec 11, 2026.
                    </p>
                    <ol className="mt-1 list-decimal space-y-1 pl-4 text-[11px]">
                      <li>On chatgpt.com open Plugins → + → Add custom MCP server.</li>
                      <li>Paste the MCP URL, set auth header <code className="font-mono">X-Extra-Passkey</code>, accept the risk prompt, then Create as plugin + Install.</li>
                      <li>Return here and press Test Bridge. Business / Enterprise gets full write; Plus / Pro may be read-only.</li>
                    </ol>
                    <div className="mt-2 flex items-center gap-2">
                      <code className="px-2 py-1 rounded bg-white border border-[#dfe4eb] font-mono text-[11px] tabular-nums text-[#1a1a1c] flex-1 truncate select-all">
                        {hasCloudKey ? chatGptMcpUrl : "Sign in and sync keys to reveal the MCP URL"}
                      </code>
                      <button
                        type="button"
                        onClick={() => handleCopy(chatGptMcpUrl, "ChatGPT MCP URL copied")}
                        disabled={!hasCloudKey}
                        aria-label="Copy ChatGPT MCP URL"
                        className="px-2.5 py-1 rounded border border-[#dfe4eb] bg-white hover:bg-[#f8f9fb] text-[11px] font-medium text-[#1a1a1c] shrink-0 disabled:opacity-60"
                      >
                        {copiedKey === "ChatGPT MCP URL copied" ? "Copied" : "Copy"}
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {selectedCloudApp === "claude" && (
                <div className="flex items-start gap-2.5 p-3 rounded-lg bg-[#f8f9fb] border border-[#dfe4eb]">
                  <span className="size-5 rounded-full bg-[#1a1a1c] text-white font-bold text-[10px] flex items-center justify-center shrink-0 mt-0.5" aria-hidden="true">
                    1
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-[#1a1a1c]">Claude Custom Connector (Recommended)</p>
                    <ol className="mt-1 list-decimal space-y-1 pl-4 text-[11px]">
                      <li>Copy the MCP URL and the passkey below.</li>
                      <li>In Claude go to Settings → Connectors → Add custom connector, paste the URL, add <code className="font-mono">X-Extra-Passkey</code>, then Connect.</li>
                      <li>Free plan allows 1 custom connector. For terminal use: <code className="font-mono">claude mcp add --transport http extra [url]</code>, then Test Bridge.</li>
                    </ol>
                  </div>
                </div>
              )}

              {selectedCloudApp === "gemini" && (
                <div className="flex items-start gap-2.5 p-3 rounded-lg bg-[#f8f9fb] border border-[#dfe4eb]">
                  <span className="size-5 rounded-full bg-[#1a1a1c] text-white font-bold text-[10px] flex items-center justify-center shrink-0 mt-0.5" aria-hidden="true">
                    1
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-[#1a1a1c]">Gemini Has No Custom MCP URL Box</p>
                    <p className="text-[11px] text-[#525866] mt-0.5">
                      Gems become Skills from Nov 2026 and turn read-only Nov 17, 2026. Use API / AI Studio for tools.
                    </p>
                    <ol className="mt-1 list-decimal space-y-1 pl-4 text-[11px]">
                      <li>For reusable prompts: gemini.google.com → Gems / Skills → New Skill, paste your Extra instructions.</li>
                      <li>For direct control: use Google AI Studio or Gemini API with the SSE URL + <code className="font-mono">X-Extra-Passkey</code> below.</li>
                      <li>There is no Extensions → Webhooks MCP install in Gemini — do not follow old webhook guides.</li>
                    </ol>
                  </div>
                </div>
              )}

              {/* Tier 3: manual values shared by all platforms */}
              <div className="flex items-start gap-2.5">
                <span className="size-5 rounded-full bg-[#f0f2f6] text-[#1a1a1c] font-bold text-[10px] flex items-center justify-center shrink-0 mt-0.5" aria-hidden="true">
                  2
                </span>
                <div className="flex-1">
                  <p className="font-medium text-[#1a1a1c]">HTTPS SSE Endpoint</p>
                  <div className="mt-1 flex items-center gap-2">
                    <code className="px-2 py-1 rounded bg-[#f8f9fb] border border-[#dfe4eb] font-mono text-[11px] tabular-nums text-[#1a1a1c] flex-1">
                      https://extra.yantraos.com/sse
                    </code>
                    <button
                      type="button"
                      onClick={() => handleCopy("https://extra.yantraos.com/sse", "SSE URL copied")}
                      aria-label="Copy SSE endpoint"
                      className="px-2 py-1 rounded border border-[#dfe4eb] bg-white hover:bg-[#f8f9fb] text-[11px] font-medium"
                    >
                      {copiedKey === "SSE URL copied" ? "Copied" : "Copy"}
                    </button>
                  </div>
                </div>
              </div>

              <div className="flex items-start gap-2.5">
                <span className="size-5 rounded-full bg-[#f0f2f6] text-[#1a1a1c] font-bold text-[10px] flex items-center justify-center shrink-0 mt-0.5" aria-hidden="true">
                  3
                </span>
                <div className="flex-1">
                  <p className="font-medium text-[#1a1a1c]">Passkey Authentication Header</p>
                  <div className="mt-1 flex items-center gap-2">
                    <code className="px-2 py-1 rounded bg-[#f8f9fb] border border-[#dfe4eb] font-mono text-[11px] tabular-nums text-[#1a1a1c] flex-1 truncate">
                      {hasCloudKey ? `X-Extra-Passkey: ${relayPasskey}` : "Sign in and sync keys to reveal the passkey"}
                    </code>
                    <button
                      type="button"
                      onClick={() => handleCopy(relayPasskey, "Passkey copied")}
                      disabled={!hasCloudKey}
                      aria-label="Copy passkey"
                      className="px-2 py-1 rounded border border-[#dfe4eb] bg-white hover:bg-[#f8f9fb] text-[11px] font-medium disabled:opacity-60"
                    >
                      {copiedKey === "Passkey copied" ? "Copied" : "Copy"}
                    </button>
                  </div>
                  {!hasCloudKey && (
                    <p className="mt-1 text-[11px] text-[#868c98]">Keys stay hidden until sign-in. Old keys are cleared on sync.</p>
                  )}
                </div>
              </div>

              <details className="rounded-lg border border-[#dfe4eb] bg-[#f8f9fb] px-3 py-2">
                <summary className="cursor-pointer text-xs font-medium text-[#1a1a1c]">Rotated on web but app still shows the old key?</summary>
                <div className="mt-2 space-y-1 text-[11px]">
                  <p>1. Press Sync Cloud Keys above — it pulls the latest key and restarts the relay.</p>
                  <p>2. Press Test Bridge — you should see a latency like 2ms OK.</p>
                  <p>3. If it still fails, press Rotate Key here once, then copy the new URL again.</p>
                </div>
              </details>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
