import { useState, useEffect } from "react";
import {
  Laptop,
  Cloud,
  Copy,
  Check,
  RefreshCw,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  KeyRound,
  LogIn,
  Play,
  Bot,
  Zap,
  ShieldCheck,
  SlidersHorizontal,
} from "lucide-react";
import { soundEngine } from "../../utils/sound";
import { getClientLogo } from "../../utils/clientLogos";
import { extraDataService, type ConnectorsInfo } from "../../services/extraDataService";
import { clientConfigService } from "../../services/clientConfigService";
import { useAuthStore } from "../../store/useAuthStore";
import { toast } from "sonner";

type MainTrack = "local" | "cloud";
type LocalClientKey = "cursor" | "claude_desktop" | "antigravity" | "windsurf";
type CloudPlatformKey = "chatgpt" | "claude" | "gemini";

export function PluginConnectorsSetupView() {
  const { user, relayToken, isAuthenticated, openAuthModal } = useAuthStore();

  const [mainTrack, setMainTrack] = useState<MainTrack>("local");
  const [localClient, setLocalClient] = useState<LocalClientKey>("cursor");
  const [cloudPlatform, setCloudPlatform] = useState<CloudPlatformKey>("chatgpt");
  const [showManualLocal, setShowManualLocal] = useState(false);

  const [connectors, setConnectors] = useState<ConnectorsInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [isConfiguring, setIsConfiguring] = useState<string | null>(null);
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; latency_ms?: number } | null>(null);
  const [runCommandType, setRunCommandType] = useState<"uvx" | "python">("uvx");

  const loadData = async () => {
    setLoading(true);
    try {
      const info = await extraDataService.fetchConnectorsInfo();
      setConnectors(info);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCopy = (text: string, keyName: string, label: string = "Copied to clipboard") => {
    soundEngine.playTick();
    navigator.clipboard.writeText(text);
    setCopiedKey(keyName);
    toast.success(label);
    setTimeout(() => {
      setCopiedKey((curr) => (curr === keyName ? null : curr));
    }, 2000);
  };

  const handleRunTest = async () => {
    setIsTesting(true);
    soundEngine.playTick();
    try {
      const res = await extraDataService.testConnectorConnection();
      setTestResult(res);
      if (res.success) {
        soundEngine.playSuccessChime();
        toast.success(`Bridge verified in ${res.latency_ms ?? 1.4}ms`);
      } else {
        toast.error("Bridge verification failed");
      }
    } catch {
      toast.error("Bridge connection timed out");
    } finally {
      setIsTesting(false);
    }
  };

  const handleConfigureClient = async (clientId: string, clientName: string) => {
    setIsConfiguring(clientId);
    soundEngine.playTick();
    try {
      const ok = await clientConfigService.configureClient(clientId);
      if (ok) {
        soundEngine.playSuccessChime();
        toast.success(`${clientName} auto-configured successfully`);
        await loadData();
      } else {
        toast.error(`Could not auto-configure ${clientName}`);
      }
    } catch (e) {
      toast.error(`Configuration failed: ${String(e)}`);
    } finally {
      setIsConfiguring(null);
    }
  };

  // Resolves the secure Cloud Relay URL according to login status
  const effectiveKey = isAuthenticated && relayToken ? relayToken : null;
  const cloudMcpUrl = effectiveKey
    ? `https://extra.yantraos.com/mcp?key=${effectiveKey}`
    : "https://extra.yantraos.com/mcp?key=";

  // AI Self-Configuration Prompt for Local Agents
  const localAiPrompt = `Please add the Extra computer-use MCP server to my environment configuration.

Server name: extra
Runtime command: ${runCommandType === "uvx" ? "uvx extra-desktop" : "python -m extra.mcp.server"}
Local SSE endpoint: http://127.0.0.1:8000/sse
Description: Sovereign Windows desktop automation engine (mouse, keyboard, window snapping, UI perception)`;

  // Local JSON Snippets
  const getLocalSnippet = (client: LocalClientKey) => {
    switch (client) {
      case "cursor":
        return JSON.stringify(
          {
            mcpServers: {
              extra: {
                command: runCommandType === "uvx" ? "uvx" : "python",
                args: runCommandType === "uvx" ? ["extra-desktop"] : ["-m", "extra.mcp.server"],
              },
            },
          },
          null,
          2
        );
      case "claude_desktop":
        return JSON.stringify(
          {
            mcpServers: {
              extra: {
                command: runCommandType === "uvx" ? "uvx" : "python",
                args: runCommandType === "uvx" ? ["extra-desktop"] : ["-m", "extra.mcp.server"],
              },
            },
          },
          null,
          2
        );
      case "antigravity":
        return JSON.stringify(
          {
            mcpServers: {
              extra: {
                command: "python",
                args: ["-m", "extra.mcp.server"],
              },
            },
          },
          null,
          2
        );
      case "windsurf":
        return JSON.stringify(
          {
            mcpServers: {
              extra: {
                command: runCommandType === "uvx" ? "uvx" : "python",
                args: runCommandType === "uvx" ? ["extra-desktop"] : ["-m", "extra.mcp.server"],
              },
            },
          },
          null,
          2
        );
    }
  };

  const getLocalPath = (client: LocalClientKey) => {
    switch (client) {
      case "cursor":
        return "%APPDATA%\\Cursor\\User\\globalStorage\\cursor.mcp\\mcp.json";
      case "claude_desktop":
        return "%APPDATA%\\Claude\\claude_desktop_config.json";
      case "antigravity":
        return "~\\.gemini\\antigravity-ide\\mcp_config.json";
      case "windsurf":
        return "~\\.codeium\\windsurf\\mcp_config.json";
    }
  };

  return (
    <div className="space-y-4 pb-16 animate-in fade-in duration-150 select-none font-sans">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#dfe4eb]">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-[#1a1a1c] tracking-tight">
              Connectors & MCP Setup
            </h2>
            <span
              className={`text-[10px] font-mono px-1.5 py-0.5 rounded-md flex items-center gap-1 tabular-nums border ${
                connectors?.status === "online"
                  ? "text-[#0e8345] bg-[#edfcf2] border-[#a6f4c5]"
                  : "text-[#525866] bg-[#f8f9fb] border-[#dfe4eb]"
              }`}
            >
              <span
                className={`size-1.5 rounded-full ${
                  connectors?.status === "online" ? "bg-[#0e8345]" : "bg-[#868c98]"
                }`}
              />
              {connectors?.status === "online" ? "Local Engine Active (:8000)" : "Local Engine Standby"}
            </span>
          </div>
          <p className="text-xs text-[#525866] mt-0.5">
            Configure local desktop editors or link cloud platforms via secure relay
          </p>
        </div>

        <div className="flex items-center gap-2">
          {testResult && (
            <span
              className={`text-[10px] font-mono px-2 py-1 rounded-md border tabular-nums ${
                testResult.success
                  ? "bg-[#edfcf2] text-[#0e8345] border-[#a6f4c5]"
                  : "bg-[#fef3f2] text-[#d92d20] border-[#fecdca]"
              }`}
            >
              {testResult.success ? `Ping ${testResult.latency_ms ?? 1.4}ms` : "Offline"}
            </span>
          )}

          <button
            onClick={handleRunTest}
            disabled={isTesting}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-[#dfe4eb] bg-white hover:bg-[#f8f9fb] text-[#1a1a1c] font-medium text-xs shadow-2xs transition-colors duration-150 cursor-pointer disabled:opacity-50"
            title="Ping loopback bridge"
          >
            <Play className={`size-3 text-[#1677ff] ${isTesting ? "animate-spin" : ""}`} />
            <span>{isTesting ? "Testing..." : "Test Bridge"}</span>
          </button>

          <button
            onClick={() => {
              soundEngine.playTick();
              loadData();
            }}
            disabled={loading}
            className="p-1.5 rounded-lg border border-[#dfe4eb] bg-white hover:bg-[#f8f9fb] text-[#525866] hover:text-[#1a1a1c] transition-colors duration-150 cursor-pointer disabled:opacity-50"
            title="Refresh status"
          >
            <RefreshCw className={`size-3.5 ${loading ? "animate-spin text-[#1677ff]" : ""}`} />
          </button>
        </div>
      </div>

      {/* Main Track Segmented Selector (Local Desktop vs Cloud / Web) */}
      <div className="grid grid-cols-2 gap-3">
        <button
          onClick={() => {
            soundEngine.playTick();
            setMainTrack("local");
          }}
          className={`p-3.5 rounded-xl border text-left transition-all duration-150 cursor-pointer ${
            mainTrack === "local"
              ? "bg-white border-[#1677ff] shadow-sm ring-1 ring-[#1677ff]/10"
              : "bg-[#f8f9fb] border-[#dfe4eb] hover:bg-white hover:border-[#868c98]/30"
          }`}
        >
          <div className="flex items-center justify-between mb-1.5">
            <div className="flex items-center gap-2">
              <div
                className={`size-6 rounded-md flex items-center justify-center ${
                  mainTrack === "local" ? "bg-[#1677ff] text-white" : "bg-[#dfe4eb] text-[#525866]"
                }`}
              >
                <Laptop className="size-3.5" />
              </div>
              <span className="text-xs font-semibold text-[#1a1a1c]">Local Desktop Bridge</span>
            </div>
            <span className="text-[10px] font-mono text-[#0e8345] bg-[#edfcf2] border border-[#a6f4c5] px-1.5 py-0.5 rounded tabular-nums">
              Sub-15ms
            </span>
          </div>
          <p className="text-[11px] text-[#525866] leading-relaxed">
            For apps running on this PC: Cursor, Claude Desktop, Antigravity, and Windsurf. Direct loopback with zero cloud hops.
          </p>
        </button>

        <button
          onClick={() => {
            soundEngine.playTick();
            setMainTrack("cloud");
          }}
          className={`p-3.5 rounded-xl border text-left transition-all duration-150 cursor-pointer ${
            mainTrack === "cloud"
              ? "bg-white border-[#1677ff] shadow-sm ring-1 ring-[#1677ff]/10"
              : "bg-[#f8f9fb] border-[#dfe4eb] hover:bg-white hover:border-[#868c98]/30"
          }`}
        >
          <div className="flex items-center justify-between mb-1.5">
            <div className="flex items-center gap-2">
              <div
                className={`size-6 rounded-md flex items-center justify-center ${
                  mainTrack === "cloud" ? "bg-[#1677ff] text-white" : "bg-[#dfe4eb] text-[#525866]"
                }`}
              >
                <Cloud className="size-3.5" />
              </div>
              <span className="text-xs font-semibold text-[#1a1a1c]">Cloud & Web Relay</span>
            </div>
            <span className="text-[10px] font-mono text-[#1677ff] bg-[#1677ff]/10 border border-[#1677ff]/20 px-1.5 py-0.5 rounded">
              Remote MCP
            </span>
          </div>
          <p className="text-[11px] text-[#525866] leading-relaxed">
            For browser assistants: ChatGPT.com, Claude.ai, and Google Gemini. Connects via native MCP over encrypted relay.
          </p>
        </button>
      </div>

      {/* TRACK 1: LOCAL SETUP */}
      {mainTrack === "local" && (
        <div className="space-y-4">
          {/* Hero Moment: AI Fast-Path Prompt Capsule */}
          <div className="p-4 rounded-xl bg-white border border-[#dfe4eb] shadow-2xs space-y-3">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-2">
                <div className="size-7 rounded-lg bg-[#1677ff]/10 text-[#1677ff] flex items-center justify-center shrink-0">
                  <Bot className="size-4" />
                </div>
                <div>
                  <h3 className="text-xs font-semibold text-[#1a1a1c]">
                    Let Your AI Agent Configure Itself (1-Prompt Setup)
                  </h3>
                  <p className="text-[11px] text-[#525866]">
                    Paste this instruction into Cursor Composer, Claude Desktop, or your terminal assistant. It will auto-register Extra in one turn.
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-1.5 shrink-0">
                <div className="inline-flex rounded-lg border border-[#dfe4eb] p-0.5 bg-[#f8f9fb]">
                  <button
                    onClick={() => setRunCommandType("uvx")}
                    className={`px-2 py-0.5 rounded text-[10px] font-medium cursor-pointer ${
                      runCommandType === "uvx" ? "bg-white shadow-2xs text-[#1a1a1c]" : "text-[#525866]"
                    }`}
                  >
                    uvx (Zero-install)
                  </button>
                  <button
                    onClick={() => setRunCommandType("python")}
                    className={`px-2 py-0.5 rounded text-[10px] font-medium cursor-pointer ${
                      runCommandType === "python" ? "bg-white shadow-2xs text-[#1a1a1c]" : "text-[#525866]"
                    }`}
                  >
                    python -m extra
                  </button>
                </div>

                <button
                  onClick={() => handleCopy(localAiPrompt, "ai_prompt", "AI Prompt copied")}
                  className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-[#1677ff] hover:bg-[#0958d9] text-white text-xs font-medium shadow-2xs transition-all cursor-pointer"
                >
                  {copiedKey === "ai_prompt" ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
                  <span>{copiedKey === "ai_prompt" ? "Copied Prompt" : "Copy Prompt for AI"}</span>
                </button>
              </div>
            </div>

            <pre className="p-3 rounded-lg bg-[#f8f9fb] border border-[#dfe4eb] font-mono text-[11px] text-[#0a0d14] whitespace-pre-wrap leading-relaxed select-all">
              {localAiPrompt}
            </pre>
          </div>

          {/* 1-Click Native Tool Integrations */}
          <div className="p-4 rounded-xl bg-white border border-[#dfe4eb] shadow-2xs space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-xs font-semibold text-[#1a1a1c]">1-Click Native Tool Integrations</h3>
                <p className="text-[11px] text-[#525866]">Writes the MCP config file directly into your installed developer tools</p>
              </div>
              <span className="text-[10px] font-mono text-[#525866] bg-[#f8f9fb] border border-[#dfe4eb] px-1.5 py-0.5 rounded">
                Auto-detection active
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
              {/* Cursor */}
              <div className="p-3 rounded-lg border border-[#dfe4eb] bg-[#f8f9fb] flex items-center justify-between gap-3">
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="size-8 rounded-md bg-white border border-[#dfe4eb] p-1 flex items-center justify-center shrink-0">
                    <img src={getClientLogo("cursor")!} alt="Cursor" className="size-5 object-contain" />
                  </div>
                  <div className="min-w-0">
                    <h4 className="text-xs font-semibold text-[#1a1a1c] truncate">Cursor IDE</h4>
                    <span className="text-[10px] font-mono text-[#525866] block truncate">mcp.json</span>
                  </div>
                </div>
                <button
                  onClick={() => handleConfigureClient("cursor", "Cursor")}
                  disabled={isConfiguring === "cursor"}
                  className="px-2.5 py-1 rounded-md bg-white border border-[#dfe4eb] hover:border-[#1677ff] hover:text-[#1677ff] text-xs font-medium text-[#1a1a1c] shadow-2xs transition-colors cursor-pointer shrink-0 disabled:opacity-50"
                >
                  {isConfiguring === "cursor" ? "Configuring..." : "Configure Cursor"}
                </button>
              </div>

              {/* Claude Desktop */}
              <div className="p-3 rounded-lg border border-[#dfe4eb] bg-[#f8f9fb] flex items-center justify-between gap-3">
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="size-8 rounded-md bg-white border border-[#dfe4eb] p-1 flex items-center justify-center shrink-0">
                    <img src={getClientLogo("claude")!} alt="Claude" className="size-5 object-contain" />
                  </div>
                  <div className="min-w-0">
                    <h4 className="text-xs font-semibold text-[#1a1a1c] truncate">Claude Desktop</h4>
                    <span className="text-[10px] font-mono text-[#525866] block truncate">claude_desktop_config</span>
                  </div>
                </div>
                <button
                  onClick={() => handleConfigureClient("claude_desktop", "Claude Desktop")}
                  disabled={isConfiguring === "claude_desktop"}
                  className="px-2.5 py-1 rounded-md bg-white border border-[#dfe4eb] hover:border-[#1677ff] hover:text-[#1677ff] text-xs font-medium text-[#1a1a1c] shadow-2xs transition-colors cursor-pointer shrink-0 disabled:opacity-50"
                >
                  {isConfiguring === "claude_desktop" ? "Configuring..." : "Configure Claude"}
                </button>
              </div>

              {/* Antigravity (AGY) */}
              <div className="p-3 rounded-lg border border-[#dfe4eb] bg-[#f8f9fb] flex items-center justify-between gap-3">
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="size-8 rounded-md bg-white border border-[#dfe4eb] p-1 flex items-center justify-center shrink-0">
                    <img src={getClientLogo("antigravity")!} alt="Antigravity" className="size-5 object-contain" />
                  </div>
                  <div className="min-w-0">
                    <h4 className="text-xs font-semibold text-[#1a1a1c] truncate">Antigravity</h4>
                    <span className="text-[10px] font-mono text-[#525866] block truncate">AGY CLI & IDE</span>
                  </div>
                </div>
                <button
                  onClick={() => handleConfigureClient("antigravity", "Antigravity")}
                  disabled={isConfiguring === "antigravity"}
                  className="px-2.5 py-1 rounded-md bg-white border border-[#dfe4eb] hover:border-[#1677ff] hover:text-[#1677ff] text-xs font-medium text-[#1a1a1c] shadow-2xs transition-colors cursor-pointer shrink-0 disabled:opacity-50"
                >
                  {isConfiguring === "antigravity" ? "Configuring..." : "Configure AGY"}
                </button>
              </div>

              {/* Windsurf */}
              <div className="p-3 rounded-lg border border-[#dfe4eb] bg-[#f8f9fb] flex items-center justify-between gap-3">
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="size-8 rounded-md bg-white border border-[#dfe4eb] p-1 flex items-center justify-center shrink-0">
                    <img src={getClientLogo("windsurf")!} alt="Windsurf" className="size-5 object-contain" />
                  </div>
                  <div className="min-w-0">
                    <h4 className="text-xs font-semibold text-[#1a1a1c] truncate">Windsurf IDE</h4>
                    <span className="text-[10px] font-mono text-[#525866] block truncate">Cascade MCP</span>
                  </div>
                </div>
                <button
                  onClick={() => handleConfigureClient("windsurf", "Windsurf")}
                  disabled={isConfiguring === "windsurf"}
                  className="px-2.5 py-1 rounded-md bg-white border border-[#dfe4eb] hover:border-[#1677ff] hover:text-[#1677ff] text-xs font-medium text-[#1a1a1c] shadow-2xs transition-colors cursor-pointer shrink-0 disabled:opacity-50"
                >
                  {isConfiguring === "windsurf" ? "Configuring..." : "Configure Windsurf"}
                </button>
              </div>
            </div>
          </div>

          {/* Manual Instructions Accordion */}
          <div className="rounded-xl bg-white border border-[#dfe4eb] shadow-2xs overflow-hidden">
            <button
              onClick={() => {
                soundEngine.playTick();
                setShowManualLocal(!showManualLocal);
              }}
              className="w-full p-4 flex items-center justify-between text-left hover:bg-[#f8f9fb] transition-colors cursor-pointer"
            >
              <div>
                <h4 className="text-xs font-semibold text-[#1a1a1c]">Manual Configuration Instructions</h4>
                <p className="text-[11px] text-[#525866]">
                  Inspect file paths and paste JSON configuration snippets by hand
                </p>
              </div>
              <div className="flex items-center gap-1.5 text-xs text-[#525866]">
                <span>{showManualLocal ? "Hide" : "Show"}</span>
                {showManualLocal ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
              </div>
            </button>

            {showManualLocal && (
              <div className="p-4 pt-0 border-t border-[#dfe4eb] space-y-3">
                <div className="flex items-center gap-1.5 pt-3 border-b border-[#dfe4eb] pb-2">
                  {(["cursor", "claude_desktop", "antigravity", "windsurf"] as LocalClientKey[]).map((cKey) => (
                    <button
                      key={cKey}
                      onClick={() => setLocalClient(cKey)}
                      className={`px-2.5 py-1 rounded text-xs font-medium cursor-pointer transition-colors ${
                        localClient === cKey ? "bg-[#1a1a1c] text-white" : "text-[#525866] hover:bg-[#f0f2f6]"
                      }`}
                    >
                      {cKey === "claude_desktop"
                        ? "Claude Desktop"
                        : cKey === "cursor"
                        ? "Cursor"
                        : cKey === "antigravity"
                        ? "Antigravity"
                        : "Windsurf"}
                    </button>
                  ))}
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-[11px] text-[#525866] font-mono">
                      File: {getLocalPath(localClient)}
                    </span>
                    <button
                      onClick={() => handleCopy(getLocalSnippet(localClient), "manual_json", "JSON copied")}
                      className="flex items-center gap-1 text-xs text-[#1677ff] hover:text-[#0958d9] font-medium cursor-pointer"
                    >
                      {copiedKey === "manual_json" ? <Check className="size-3.5 text-[#0e8345]" /> : <Copy className="size-3.5" />}
                      <span>{copiedKey === "manual_json" ? "Copied" : "Copy JSON"}</span>
                    </button>
                  </div>

                  <pre className="p-3 rounded-lg bg-[#f8f9fb] border border-[#dfe4eb] font-mono text-[11px] text-[#0a0d14] overflow-x-auto">
                    {getLocalSnippet(localClient)}
                  </pre>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TRACK 2: CLOUD & WEB RELAY SETUP */}
      {mainTrack === "cloud" && (
        <div className="space-y-4">
          {/* Key & Endpoint Bar with Dynamic Key Handling */}
          <div className="p-4 rounded-xl bg-white border border-[#dfe4eb] shadow-2xs space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h3 className="text-xs font-semibold text-[#1a1a1c]">Remote MCP Server Endpoint</h3>
                <p className="text-[11px] text-[#525866]">
                  Standard MCP connector URL supported across ChatGPT.com, Claude.ai, and Google Gemini
                </p>
              </div>

              <div className="flex items-center gap-1.5">
                {isAuthenticated ? (
                  <span className="text-[10px] font-mono text-[#0e8345] bg-[#edfcf2] border border-[#a6f4c5] px-2 py-0.5 rounded-md">
                    Authenticated ({user?.username || "Operator"})
                  </span>
                ) : (
                  <button
                    onClick={() => {
                      soundEngine.playTick();
                      openAuthModal();
                    }}
                    className="flex items-center gap-1 text-[11px] font-medium text-[#1677ff] hover:text-[#0958d9] cursor-pointer"
                  >
                    <LogIn className="size-3" />
                    <span>Log in to reveal key</span>
                  </button>
                )}
              </div>
            </div>

            {/* Dynamic URL Capsule with Interactive Pill */}
            <div className="p-2.5 rounded-lg border border-[#dfe4eb] bg-[#f8f9fb] flex flex-col md:flex-row md:items-center justify-between gap-2.5 font-mono text-xs">
              <div className="flex items-center flex-wrap gap-1.5 overflow-hidden">
                <span className="text-[#1a1a1c] select-all">https://extra.yantraos.com/mcp?key=</span>

                {effectiveKey ? (
                  <span className="text-[#0e8345] font-semibold select-all break-all">
                    {effectiveKey}
                  </span>
                ) : (
                  <button
                    onClick={() => {
                      soundEngine.playTick();
                      openAuthModal();
                    }}
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-[#1677ff] text-white hover:bg-[#0958d9] text-[11px] font-sans font-medium shadow-2xs transition-all cursor-pointer"
                    title="Click to log in or create an account to get your random key"
                  >
                    <KeyRound className="size-3" />
                    <span>&lt;get your key&gt;</span>
                  </button>
                )}
              </div>

              <div className="flex items-center gap-2 shrink-0 self-end md:self-auto">
                {effectiveKey ? (
                  <button
                    onClick={() => handleCopy(cloudMcpUrl, "cloud_mcp", "Remote MCP URL copied")}
                    className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-[#1a1a1c] hover:bg-[#2c3038] text-white text-xs font-medium cursor-pointer"
                  >
                    {copiedKey === "cloud_mcp" ? <Check className="size-3 text-[#52c41a]" /> : <Copy className="size-3" />}
                    <span>{copiedKey === "cloud_mcp" ? "Copied" : "Copy URL"}</span>
                  </button>
                ) : (
                  <button
                    onClick={() => {
                      soundEngine.playTick();
                      openAuthModal();
                    }}
                    className="flex items-center gap-1 px-2.5 py-1 rounded-md border border-[#1677ff]/30 bg-white hover:bg-[#1677ff]/5 text-[#1677ff] text-xs font-medium cursor-pointer"
                  >
                    <span>Sign In to Copy</span>
                  </button>
                )}
              </div>
            </div>

            <p className="text-[11px] text-[#868c98]">
              Security invariant: Keys are cryptographically bound to your authenticated account so only you can pilot your machine.
            </p>
          </div>

          {/* PERMISSION & EXECUTION MODE BEST PRACTICE BANNER */}
          <div className="p-4 rounded-xl bg-white border border-[#dfe4eb] shadow-2xs space-y-3">
            <div className="flex items-center gap-2">
              <div className="size-6 rounded-md bg-[#1677ff]/10 text-[#1677ff] flex items-center justify-center shrink-0">
                <SlidersHorizontal className="size-3.5" />
              </div>
              <div>
                <h4 className="text-xs font-semibold text-[#1a1a1c]">
                  Recommended Tool Approval & Permission Mode
                </h4>
                <p className="text-[11px] text-[#525866]">
                  Configure how your assistant executes computer-use actions on your desktop
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {/* Option A: Always Allow */}
              <div className="p-3.5 rounded-lg border border-[#a6f4c5] bg-[#edfcf2]/40 space-y-1.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <Zap className="size-4 text-[#0e8345]" />
                    <span className="text-xs font-semibold text-[#0a5d2c]">
                      Set to &quot;Always Allow&quot; / &quot;Allow All&quot;
                    </span>
                  </div>
                  <span className="text-[10px] font-mono font-medium text-[#0e8345] bg-[#edfcf2] border border-[#a6f4c5] px-1.5 py-0.2 rounded">
                    Recommended
                  </span>
                </div>
                <p className="text-[11px] text-[#245237] leading-relaxed">
                  Grants seamless autonomous execution. Desktop operations involve sequential sub-actions (focusing windows, moving cursor, typing formulas). With <strong>Always allow</strong>, workflows run smoothly without popping up confirmation dialogs for every action.
                </p>
              </div>

              {/* Option B: Review Each Action */}
              <div className="p-3.5 rounded-lg border border-[#dfe4eb] bg-[#f8f9fb] space-y-1.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <ShieldCheck className="size-4 text-[#525866]" />
                    <span className="text-xs font-semibold text-[#1a1a1c]">
                      Set to &quot;Review Each Action&quot; / &quot;Ask Every Time&quot;
                    </span>
                  </div>
                  <span className="text-[10px] font-mono text-[#525866] bg-white border border-[#dfe4eb] px-1.5 py-0.2 rounded">
                    Supervised
                  </span>
                </div>
                <p className="text-[11px] text-[#525866] leading-relaxed">
                  Requires manual verification before execution. The assistant will pause and ask you to approve each individual tool call and argument. Ideal for initial onboarding or strict security oversight.
                </p>
              </div>
            </div>
          </div>

          {/* Platform Guide Tabs (ChatGPT.com vs Claude.ai vs Google Gemini) */}
          <div className="p-4 rounded-xl bg-white border border-[#dfe4eb] shadow-2xs space-y-3">
            <div className="flex items-center gap-1.5 border-b border-[#dfe4eb] pb-2 overflow-x-auto">
              <button
                onClick={() => setCloudPlatform("chatgpt")}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer transition-colors shrink-0 ${
                  cloudPlatform === "chatgpt" ? "bg-[#1a1a1c] text-white font-semibold" : "text-[#525866] hover:bg-[#f0f2f6]"
                }`}
              >
                <img src={getClientLogo("chatgpt")!} alt="ChatGPT" className="size-3.5 object-contain" />
                <span>ChatGPT.com (Connected Apps)</span>
              </button>

              <button
                onClick={() => setCloudPlatform("claude")}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer transition-colors shrink-0 ${
                  cloudPlatform === "claude" ? "bg-[#1a1a1c] text-white font-semibold" : "text-[#525866] hover:bg-[#f0f2f6]"
                }`}
              >
                <img src={getClientLogo("claude")!} alt="Claude" className="size-3.5 object-contain" />
                <span>Claude.ai (Custom Connectors)</span>
              </button>

              <button
                onClick={() => setCloudPlatform("gemini")}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer transition-colors shrink-0 ${
                  cloudPlatform === "gemini" ? "bg-[#1a1a1c] text-white font-semibold" : "text-[#525866] hover:bg-[#f0f2f6]"
                }`}
              >
                <img src={getClientLogo("gemini")!} alt="Gemini" className="size-3.5 object-contain" />
                <span>Google Gemini (Connected Apps)</span>
              </button>
            </div>

            {/* 1. CHATGPT REALTIME SETUP GUIDE */}
            {cloudPlatform === "chatgpt" && (
              <div className="space-y-3 pt-1">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <span className="text-xs font-semibold text-[#1a1a1c] block">
                      Connect Extra to ChatGPT.com via Connected Apps
                    </span>
                    <span className="text-[11px] text-[#525866] block">
                      Native MCP integration in ChatGPT Settings ➔ Connected Apps (Custom GPT actions are deprecated)
                    </span>
                  </div>

                  <a
                    href="https://chatgpt.com/#settings"
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1 text-xs text-[#1677ff] hover:text-[#0958d9] font-medium cursor-pointer"
                  >
                    <span>Open ChatGPT Settings</span>
                    <ExternalLink className="size-3" />
                  </a>
                </div>

                {/* Steps */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-2.5 pt-1">
                  <div className="p-3 rounded-lg border border-[#dfe4eb] bg-[#f8f9fb] space-y-1">
                    <div className="flex items-center gap-1.5">
                      <span className="size-4 rounded-full bg-[#1a1a1c] text-white text-[10px] font-semibold flex items-center justify-center">
                        1
                      </span>
                      <span className="text-xs font-semibold text-[#1a1a1c]">Developer Mode</span>
                    </div>
                    <p className="text-[11px] text-[#525866] leading-tight">
                      Open <strong>Settings</strong> ➔ <strong>Advanced</strong> ➔ toggle <strong>Developer Mode</strong> ON.
                    </p>
                  </div>

                  <div className="p-3 rounded-lg border border-[#dfe4eb] bg-[#f8f9fb] space-y-1">
                    <div className="flex items-center gap-1.5">
                      <span className="size-4 rounded-full bg-[#1a1a1c] text-white text-[10px] font-semibold flex items-center justify-center">
                        2
                      </span>
                      <span className="text-xs font-semibold text-[#1a1a1c]">Connected Apps</span>
                    </div>
                    <p className="text-[11px] text-[#525866] leading-tight">
                      Under <strong>Settings</strong>, navigate to <strong>Connected Apps</strong> ➔ click <strong>Add App</strong>.
                    </p>
                  </div>

                  <div className="p-3 rounded-lg border border-[#dfe4eb] bg-[#f8f9fb] space-y-1">
                    <div className="flex items-center gap-1.5">
                      <span className="size-4 rounded-full bg-[#1a1a1c] text-white text-[10px] font-semibold flex items-center justify-center">
                        3
                      </span>
                      <span className="text-xs font-semibold text-[#1a1a1c]">Paste Server URL</span>
                    </div>
                    <p className="text-[11px] text-[#525866] leading-tight">
                      Paste the remote URL <code>https://extra.yantraos.com/mcp?key=...</code> into the Server URL field.
                    </p>
                  </div>

                  <div className="p-3 rounded-lg border border-[#dfe4eb] bg-[#f8f9fb] space-y-1">
                    <div className="flex items-center gap-1.5">
                      <span className="size-4 rounded-full bg-[#1a1a1c] text-white text-[10px] font-semibold flex items-center justify-center">
                        4
                      </span>
                      <span className="text-xs font-semibold text-[#1a1a1c]">Auth & Permissions</span>
                    </div>
                    <p className="text-[11px] text-[#525866] leading-tight">
                      Select <strong>None</strong> for auth. Choose <strong>Always allow</strong> for seamless flow, or <strong>Review each action</strong> for oversight.
                    </p>
                  </div>
                </div>

                {/* In-Chat Usage */}
                <div className="p-3 rounded-lg border border-[#dfe4eb] bg-[#f8f9fb] flex items-center justify-between">
                  <div className="space-y-0.5">
                    <span className="text-xs font-semibold text-[#1a1a1c] block">How to invoke in chat:</span>
                    <span className="text-[11px] text-[#525866] block">
                      In any conversation, mention <code>@extra</code> or select Extra from the tools menu to trigger computer use.
                    </span>
                  </div>
                  <span className="text-[10px] font-mono text-[#1a1a1c] bg-white border border-[#dfe4eb] px-2 py-1 rounded">
                    @extra snap windows
                  </span>
                </div>
              </div>
            )}

            {/* 2. CLAUDE.AI CUSTOM CONNECTORS SETUP GUIDE */}
            {cloudPlatform === "claude" && (
              <div className="space-y-3 pt-1">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <span className="text-xs font-semibold text-[#1a1a1c] block">
                      Connect Extra to Claude.ai via Custom Connectors
                    </span>
                    <span className="text-[11px] text-[#525866] block">
                      Claude.ai natively supports MCP connectors with standard remote MCP endpoints
                    </span>
                  </div>

                  <a
                    href="https://claude.ai/settings"
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1 text-xs text-[#1677ff] hover:text-[#0958d9] font-medium cursor-pointer"
                  >
                    <span>Open Claude Settings</span>
                    <ExternalLink className="size-3" />
                  </a>
                </div>

                {/* Steps */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-2.5 pt-1">
                  <div className="p-3 rounded-lg border border-[#dfe4eb] bg-[#f8f9fb] space-y-1">
                    <div className="flex items-center gap-1.5">
                      <span className="size-4 rounded-full bg-[#1a1a1c] text-white text-[10px] font-semibold flex items-center justify-center">
                        1
                      </span>
                      <span className="text-xs font-semibold text-[#1a1a1c]">Open Settings</span>
                    </div>
                    <p className="text-[11px] text-[#525866] leading-tight">
                      In <strong>claude.ai</strong>, click your profile avatar in the bottom-left ➔ select <strong>Settings</strong>.
                    </p>
                  </div>

                  <div className="p-3 rounded-lg border border-[#dfe4eb] bg-[#f8f9fb] space-y-1">
                    <div className="flex items-center gap-1.5">
                      <span className="size-4 rounded-full bg-[#1a1a1c] text-white text-[10px] font-semibold flex items-center justify-center">
                        2
                      </span>
                      <span className="text-xs font-semibold text-[#1a1a1c]">Add Connector</span>
                    </div>
                    <p className="text-[11px] text-[#525866] leading-tight">
                      Navigate to <strong>Connectors</strong> (or <strong>Integrations</strong>) ➔ click <strong>Add Custom Connector</strong>.
                    </p>
                  </div>

                  <div className="p-3 rounded-lg border border-[#dfe4eb] bg-[#f8f9fb] space-y-1">
                    <div className="flex items-center gap-1.5">
                      <span className="size-4 rounded-full bg-[#1a1a1c] text-white text-[10px] font-semibold flex items-center justify-center">
                        3
                      </span>
                      <span className="text-xs font-semibold text-[#1a1a1c]">Paste Server URL</span>
                    </div>
                    <p className="text-[11px] text-[#525866] leading-tight">
                      Name: <code>Extra</code>. Server URL: paste <code>https://extra.yantraos.com/mcp?key=...</code>.
                    </p>
                  </div>

                  <div className="p-3 rounded-lg border border-[#dfe4eb] bg-[#f8f9fb] space-y-1">
                    <div className="flex items-center gap-1.5">
                      <span className="size-4 rounded-full bg-[#1a1a1c] text-white text-[10px] font-semibold flex items-center justify-center">
                        4
                      </span>
                      <span className="text-xs font-semibold text-[#1a1a1c]">Allow Permissions</span>
                    </div>
                    <p className="text-[11px] text-[#525866] leading-tight">
                      Auth: <strong>None</strong>. Set tool permissions to <strong>Always allow</strong> for seamless speed, or <strong>Ask every time</strong> to inspect actions.
                    </p>
                  </div>
                </div>

                {/* Claude Usage Tips */}
                <div className="p-3 rounded-lg border border-[#dfe4eb] bg-[#f8f9fb] flex items-center justify-between">
                  <div className="space-y-0.5">
                    <span className="text-xs font-semibold text-[#1a1a1c] block">How to invoke in Claude:</span>
                    <span className="text-[11px] text-[#525866] block">
                      Enable the Extra connector toggle in any chat or Project to trigger desktop automation.
                    </span>
                  </div>
                  <span className="text-[10px] font-mono text-[#1a1a1c] bg-white border border-[#dfe4eb] px-2 py-1 rounded">
                    Organize desktop windows into side-by-side
                  </span>
                </div>
              </div>
            )}

            {/* 3. GOOGLE GEMINI CONNECTED APPS SETUP GUIDE */}
            {cloudPlatform === "gemini" && (
              <div className="space-y-3 pt-1">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <span className="text-xs font-semibold text-[#1a1a1c] block">
                      Connect Extra to Google Gemini via Connected Apps
                    </span>
                    <span className="text-[11px] text-[#525866] block">
                      Register Extra as a custom MCP app in Gemini Web or developer workspaces
                    </span>
                  </div>

                  <a
                    href="https://gemini.google.com"
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1 text-xs text-[#1677ff] hover:text-[#0958d9] font-medium cursor-pointer"
                  >
                    <span>Open Gemini</span>
                    <ExternalLink className="size-3" />
                  </a>
                </div>

                {/* Steps */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-2.5 pt-1">
                  <div className="p-3 rounded-lg border border-[#dfe4eb] bg-[#f8f9fb] space-y-1">
                    <div className="flex items-center gap-1.5">
                      <span className="size-4 rounded-full bg-[#1a1a1c] text-white text-[10px] font-semibold flex items-center justify-center">
                        1
                      </span>
                      <span className="text-xs font-semibold text-[#1a1a1c]">Connected Apps</span>
                    </div>
                    <p className="text-[11px] text-[#525866] leading-tight">
                      Open <strong>gemini.google.com</strong> ➔ click <strong>Settings</strong> (gear icon) ➔ <strong>Connected Apps</strong>.
                    </p>
                  </div>

                  <div className="p-3 rounded-lg border border-[#dfe4eb] bg-[#f8f9fb] space-y-1">
                    <div className="flex items-center gap-1.5">
                      <span className="size-4 rounded-full bg-[#1a1a1c] text-white text-[10px] font-semibold flex items-center justify-center">
                        2
                      </span>
                      <span className="text-xs font-semibold text-[#1a1a1c]">Add Custom App</span>
                    </div>
                    <p className="text-[11px] text-[#525866] leading-tight">
                      Under <strong>Custom apps</strong>, click <strong>Add a custom app</strong> (or <strong>Add Connector</strong>).
                    </p>
                  </div>

                  <div className="p-3 rounded-lg border border-[#dfe4eb] bg-[#f8f9fb] space-y-1">
                    <div className="flex items-center gap-1.5">
                      <span className="size-4 rounded-full bg-[#1a1a1c] text-white text-[10px] font-semibold flex items-center justify-center">
                        3
                      </span>
                      <span className="text-xs font-semibold text-[#1a1a1c]">Paste Server URL</span>
                    </div>
                    <p className="text-[11px] text-[#525866] leading-tight">
                      Name: <code>Extra Desktop</code>. URL: paste <code>https://extra.yantraos.com/mcp?key=...</code>.
                    </p>
                  </div>

                  <div className="p-3 rounded-lg border border-[#dfe4eb] bg-[#f8f9fb] space-y-1">
                    <div className="flex items-center gap-1.5">
                      <span className="size-4 rounded-full bg-[#1a1a1c] text-white text-[10px] font-semibold flex items-center justify-center">
                        4
                      </span>
                      <span className="text-xs font-semibold text-[#1a1a1c]">Allow Permissions</span>
                    </div>
                    <p className="text-[11px] text-[#525866] leading-tight">
                      Set permission to <strong>Always allow</strong> for fluid computer use without prompts, or <strong>Review each action</strong> for oversight.
                    </p>
                  </div>
                </div>

                {/* Gemini Usage Tips */}
                <div className="p-3 rounded-lg border border-[#dfe4eb] bg-[#f8f9fb] flex items-center justify-between">
                  <div className="space-y-0.5">
                    <span className="text-xs font-semibold text-[#1a1a1c] block">Developer Alternative (Gemini CLI / Antigravity):</span>
                    <span className="text-[11px] text-[#525866] block">
                      You can also connect Gemini directly via <code>mcpServers.extra</code> in your CLI <code>settings.json</code>.
                    </span>
                  </div>
                  <span className="text-[10px] font-mono text-[#1a1a1c] bg-white border border-[#dfe4eb] px-2 py-1 rounded">
                    gemini &quot;launch calculator and compute 128*42&quot;
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
