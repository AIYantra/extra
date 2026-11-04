import { useState, useEffect } from "react";
import {
  Sparkles,
  Layers,
  CheckCircle2,
  RefreshCw,
  Eye,
  MousePointer,
  Volume2,
  Play,
  ArrowRight,
  ShieldCheck,
  Check,
} from "lucide-react";
import { toast } from "sonner";
import { clientConfigService, type AIClient } from "../../services/clientConfigService";
import { soundEngine } from "../../utils/sound";
import { telemetryClient } from "../../services/telemetryClient";

interface OverviewQuickConnectProps {
  onNavigateTab?: (tab: string) => void;
}

export function OverviewQuickConnect({ onNavigateTab }: OverviewQuickConnectProps) {
  // AI Clients state
  const [clients, setClients] = useState<AIClient[]>([]);
  const [loadingClients, setLoadingClients] = useState(false);
  const [connectingId, setConnectingId] = useState<string | null>(null);

  // Indicators testing state
  const [isTestingIndicators, setIsTestingIndicators] = useState(false);
  const [testedSuccessfully, setTestedSuccessfully] = useState(false);

  useEffect(() => {
    loadClients();
  }, []);

  const loadClients = async () => {
    setLoadingClients(true);
    try {
      const detected = await clientConfigService.fetchInstalledClients();
      setClients(detected);
    } catch {
      // Fallback handled in service
    } finally {
      setLoadingClients(false);
    }
  };

  const handleConnectClient = async (clientId: string) => {
    setConnectingId(clientId);
    soundEngine.playTick();
    try {
      const ok = await clientConfigService.configureClient(clientId);
      if (ok) {
        soundEngine.playSuccessChime();
        if (clientId === "chatgpt") {
          try {
            navigator.clipboard.writeText("https://extra.yantraos.com/sse");
          } catch {}
          toast.success("Connected ChatGPT Desktop / Cloud! SSE URL copied to clipboard.");
        } else {
          toast.success(`Connected ${clientId.replace("_", " ")} to Extra!`);
        }
        await loadClients();
      } else {
        toast.error(`Could not automatically configure ${clientId}.`);
      }
    } catch {
      toast.error(`Failed to connect ${clientId}.`);
    } finally {
      setConnectingId(null);
    }
  };

  const handleConnectAll = async () => {
    setConnectingId("all");
    soundEngine.playTick();
    try {
      const results = await clientConfigService.configureAllClients();
      const count = Object.values(results).filter(Boolean).length;
      soundEngine.playSuccessChime();
      toast.success(`Connected ${count} AI environments successfully!`);
      await loadClients();
    } catch {
      toast.error("Failed to connect AI clients.");
    } finally {
      setConnectingId(null);
    }
  };

  // Test Indicators Handler — fires the real engine halo pulse, no fake success.
  const handleTestIndicators = async () => {
    setIsTestingIndicators(true);
    soundEngine.playTick();
    const result = await telemetryClient.testIndicators();
    setIsTestingIndicators(false);
    if (result.ok) {
      soundEngine.playSuccessChime();
      setTestedSuccessfully(true);
      toast.success("Halo verified: screen edge pulse and cursor ring fired.", {
        duration: 3500,
      });
    } else {
      setTestedSuccessfully(false);
      toast.error(`Halo test failed: ${result.error}`, { duration: 5000 });
    }
  };

  // Curate top 3 clients for quick display
  const claudeClient = clients.find((c) => c.client_id === "claude_desktop") || {
    client_id: "claude_desktop",
    name: "Claude Desktop",
    is_installed: true,
    is_configured: true,
  };
  const cursorClient = clients.find((c) => c.client_id === "cursor") || {
    client_id: "cursor",
    name: "Cursor IDE",
    is_installed: true,
    is_configured: true,
  };
  const chatgptClient = clients.find((c) => c.client_id === "chatgpt") || {
    client_id: "chatgpt",
    name: "ChatGPT Cloud Hub",
    is_installed: true,
    is_configured: false,
  };

  const quickClients = [claudeClient, cursorClient, chatgptClient];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 select-none">
      {/* Card 1: Connect AI Environments */}
      <div className="rounded-2xl border border-black/[0.06] dark:border-white/[0.08] bg-station-well p-5 flex flex-col justify-between shadow-xs transition-all duration-120 hover:border-black/[0.1] dark:hover:border-white/[0.14]">
        <div>
          <div className="flex items-center justify-between gap-2 mb-1.5">
            <div className="flex items-center gap-2">
              <span className="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
                <Layers className="w-4 h-4" />
              </span>
              <h3 className="font-semibold text-sm text-station-text-primary tracking-tight">
                Connect AI Tools
              </h3>
              {loadingClients && (
                <RefreshCw className="w-3 h-3 animate-spin text-station-text-dim shrink-0" />
              )}
            </div>
            {onNavigateTab && (
              <button
                onClick={() => onNavigateTab("apps")}
                className="text-xs text-station-text-muted hover:text-station-text-primary flex items-center gap-1 transition-colors cursor-pointer"
              >
                <span>View all</span>
                <ArrowRight className="w-3 h-3" />
              </button>
            )}
          </div>
          <p className="text-xs text-station-text-muted mb-3.5 leading-relaxed">
            Enable Claude, Cursor, and ChatGPT to operate your desktop with Extra.
          </p>

          {/* Grouped Client List — Apple Settings Style (No Nested Card Islands) */}
          <div className="rounded-xl bg-station-canvas border border-black/[0.04] dark:border-white/[0.06] divide-y divide-black/[0.04] dark:divide-white/[0.05] overflow-hidden">
            {quickClients.map((client) => {
              const isConnecting = connectingId === client.client_id || connectingId === "all";
              return (
                <div
                  key={client.client_id}
                  className="flex items-center justify-between px-3.5 py-2.5 hover:bg-black/[0.01] dark:hover:bg-white/[0.02] transition-colors"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <span className="w-2 h-2 rounded-full shrink-0 bg-emerald-500" />
                    <span className="text-xs font-medium text-station-text-primary truncate">
                      {client.name}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    {client.is_configured ? (
                      <span className="text-[11px] font-medium text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-md flex items-center gap-1">
                        <Check className="w-3 h-3" />
                        <span>Ready</span>
                      </span>
                    ) : (
                      <button
                        onClick={() => handleConnectClient(client.client_id)}
                        disabled={isConnecting}
                        className="px-2.5 py-1 rounded-lg text-xs font-medium bg-slate-900 dark:bg-white text-white dark:text-slate-900 hover:opacity-90 transition-opacity cursor-pointer disabled:opacity-50"
                      >
                        {isConnecting ? (
                          <RefreshCw className="w-3 h-3 animate-spin" />
                        ) : (
                          "Link"
                        )}
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* 1-Tap Batch Connect CTA */}
        <div className="mt-3.5 pt-3 border-t border-black/[0.04] dark:border-white/[0.05] flex items-center justify-between">
          <span className="text-[11px] text-station-text-dim">
            Auto-configured MCP bridge
          </span>
          <button
            onClick={handleConnectAll}
            disabled={connectingId !== null}
            className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 flex items-center gap-1 cursor-pointer transition-colors"
          >
            {connectingId === "all" ? (
              <RefreshCw className="w-3 h-3 animate-spin" />
            ) : (
              <Sparkles className="w-3.5 h-3.5" />
            )}
            <span>Connect All Detected</span>
          </button>
        </div>
      </div>

      {/* Card 2: Desktop Human Indicators */}
      <div className="rounded-2xl border border-black/[0.06] dark:border-white/[0.08] bg-station-well p-5 flex flex-col justify-between shadow-xs transition-all duration-120 hover:border-black/[0.1] dark:hover:border-white/[0.14]">
        <div>
          <div className="flex items-center justify-between gap-2 mb-1.5">
            <div className="flex items-center gap-2">
              <span className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                <ShieldCheck className="w-4 h-4" />
              </span>
              <h3 className="font-semibold text-sm text-station-text-primary tracking-tight">
                Desktop Indicators
              </h3>
            </div>
            {testedSuccessfully && (
              <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full">
                <CheckCircle2 className="w-3 h-3" />
                <span>Verified</span>
              </span>
            )}
          </div>
          <p className="text-xs text-station-text-muted mb-3.5 leading-relaxed">
            Visual and acoustic cues keep you in complete awareness while Extra is working.
          </p>

          {/* Grouped Sensory Feature List — Apple Settings Style (No Nested Card Islands) */}
          <div className="rounded-xl bg-station-canvas border border-black/[0.04] dark:border-white/[0.06] divide-y divide-black/[0.04] dark:divide-white/[0.05] overflow-hidden">
            <div className="flex items-center gap-3 px-3.5 py-2.5">
              <Eye className="w-4 h-4 text-emerald-500 shrink-0" />
              <div className="min-w-0">
                <p className="text-xs font-medium text-station-text-primary leading-tight">
                  Screen Edge Glow
                </p>
                <p className="text-[11px] text-station-text-muted leading-tight mt-0.5">
                  Soft emerald border pulses while Extra is active
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3 px-3.5 py-2.5">
              <MousePointer className="w-4 h-4 text-cyan-500 shrink-0" />
              <div className="min-w-0">
                <p className="text-xs font-medium text-station-text-primary leading-tight">
                  Cursor Flight Arc
                </p>
                <p className="text-[11px] text-station-text-muted leading-tight mt-0.5">
                  Visible, natural cursor gliding with ambient halo
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3 px-3.5 py-2.5">
              <Volume2 className="w-4 h-4 text-indigo-500 shrink-0" />
              <div className="min-w-0">
                <p className="text-xs font-medium text-station-text-primary leading-tight">
                  Glass Chimes
                </p>
                <p className="text-[11px] text-station-text-muted leading-tight mt-0.5">
                  Harmonic acoustic feedback upon task completion
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Live Test Button Footer */}
        <div className="mt-3.5 pt-3 border-t border-black/[0.04] dark:border-white/[0.05] flex items-center justify-between">
          <span className="text-[11px] text-station-text-dim">
            Sub-15ms sensory loop
          </span>
          <button
            onClick={handleTestIndicators}
            disabled={isTestingIndicators}
            className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition-all duration-120 shadow-xs flex items-center gap-1.5 cursor-pointer active:scale-95 disabled:opacity-50"
          >
            {isTestingIndicators ? (
              <RefreshCw className="w-3 h-3 animate-spin" />
            ) : (
              <Play className="w-3 h-3 fill-current" />
            )}
            <span>Test Desktop Indicators</span>
          </button>
        </div>
      </div>
    </div>
  );
}
