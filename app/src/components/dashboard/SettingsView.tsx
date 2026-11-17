import { useState, useEffect } from "react";
import {
  RefreshCw,
  Volume2,
  Play,
  Eye,
  FolderOpen,
  Copy,
  Check,
  LogOut,
  Key,
  Shield,
  Lock,
  Zap,
  Gauge,
  Radio,
  Cloud,
  Power,
  ArrowUpCircle,
  ChevronRight,
} from "lucide-react";
import { Switch } from "../ui/switch";
import { useEngineStore } from "../../store/useEngineStore";
import { useAuthStore } from "../../store/useAuthStore";
import { soundEngine } from "../../utils/sound";
import {
  extraDataService,
  type LiveRelayStatus,
  type AutostartInfo,
} from "../../services/extraDataService";
import { telemetryClient } from "../../services/telemetryClient";
import { toast } from "sonner";
import type { SpeedMode } from "../../services/ipc";
import { SPEED_MODE_META } from "../../utils/speedModes";
import { APP_VERSION_LABEL } from "../../utils/appMeta";
import { useUpdateStore } from "../../store/useUpdateStore";

interface SettingsViewProps {
  onNavigateTab?: (tab: string) => void;
}

export function SettingsView({ onNavigateTab }: SettingsViewProps = {}) {
  const speedMode = useEngineStore((state) => state.speedMode);
  const setSpeedMode = useEngineStore((state) => state.setSpeedMode);
  const isPanicActive = useEngineStore((state) => state.isPanicActive);
  const panicStop = useEngineStore((state) => state.panicStop);
  const resumePilot = useEngineStore((state) => state.resumePilot);

  const {
    isAuthenticated,
    user,
    relayToken,
    openAuthModal,
    logout,
    refreshProfile,
    rotatePasskey,
  } = useAuthStore();

  const [testingPing, setTestingPing] = useState(false);
  const [pingResult, setPingResult] = useState<string | null>(null);
  const [testingSound, setTestingSound] = useState(false);
  const [testingIndicators, setTestingIndicators] = useState(false);
  const [copiedToken, setCopiedToken] = useState(false);
  const [copiedPath, setCopiedPath] = useState(false);
  const [rotatingKey, setRotatingKey] = useState(false);
  const [armRotateKey, setArmRotateKey] = useState(false);
  const [refreshingProfile, setRefreshingProfile] = useState(false);
  const [workspacePath, setWorkspacePath] = useState("~/.extra/workspace");
  const [engineState, setEngineState] = useState<string | null>(null);
  const [enginePid, setEnginePid] = useState<number | null>(null);
  const [engineLogTail, setEngineLogTail] = useState<string[]>([]);
  const [restartingEngine, setRestartingEngine] = useState(false);
  const [autostartInfo, setAutostartInfo] = useState<AutostartInfo | null>(null);
  const [loadingAutostart, setLoadingAutostart] = useState(false);
  const [relayStatus, setRelayStatus] = useState<LiveRelayStatus | null>(null);
  const [loadingRelayAction, setLoadingRelayAction] = useState(false);
  const [testingCloudPing, setTestingCloudPing] = useState(false);
  const [cloudPingResult, setCloudPingResult] = useState<string | null>(null);
  const [copiedCloudMcpUrl, setCopiedCloudMcpUrl] = useState(false);

  const {
    installedVersionLabel,
    updateAvailable,
    latestTag,
    checking: checkingUpdate,
    updating: updatingApp,
    progressPercent: updateProgress,
    statusMessage: updateStatusMsg,
    lastCheckedAt,
    autoCheck,
    autoUpdate,
    setAutoCheck,
    setAutoUpdate,
    checkNow,
    performUpdateNow,
  } = useUpdateStore();

  const activeVerLabel = installedVersionLabel || APP_VERSION_LABEL;

  useEffect(() => {
    extraDataService.fetchDoctor().then((doc) => {
      if (doc?.controlled_folder_access?.safe_workspace) {
        setWorkspacePath(doc.controlled_folder_access.safe_workspace);
      }
    }).catch(() => {});
    telemetryClient.fetchEngineStatus().then((s) => {
      if (s) {
        setEngineState(s.state);
        setEnginePid(s.pid);
        setEngineLogTail(s.log_tail || []);
      }
    }).catch(() => {});
    extraDataService.fetchAutostartStatus().then((info) => {
      setAutostartInfo(info);
    }).catch(() => {});
    extraDataService.fetchRelayStatus().then((rStat) => {
      setRelayStatus(rStat);
    }).catch(() => {});
  }, []);

  const testPing = async () => {
    setTestingPing(true);
    soundEngine.playTick();
    const t0 = performance.now();
    try {
      const res = await fetch("http://127.0.0.1:8000/health", { method: "GET" });
      const elapsed = Math.round(performance.now() - t0);
      if (res.ok) {
        setPingResult(`${elapsed}ms loopback`);
        soundEngine.playSuccessChime();
        toast.success(`Loopback verified in ${elapsed}ms`);
      } else {
        setPingResult(`HTTP ${res.status}`);
      }
    } catch {
      setPingResult("unreachable");
      toast.error("Engine unreachable — restart the engine daemon below", { duration: 5000 });
    } finally {
      setTestingPing(false);
      setTimeout(() => setPingResult(null), 3000);
    }
  };

  const handleSpeedModeChange = async (mode: SpeedMode) => {
    soundEngine.playTick();
    setSpeedMode(mode);
    await extraDataService.updateConfig({ speed_mode: mode });
    toast.success(`Speed mode set to ${mode.toUpperCase()}`);
  };

  const handleTestChimes = () => {
    setTestingSound(true);
    soundEngine.playSuccessChime();
    toast.success("Acoustic feedback verified");
    setTimeout(() => setTestingSound(false), 500);
  };

  const handleTestIndicators = async () => {
    setTestingIndicators(true);
    soundEngine.playTick();
    const result = await telemetryClient.testIndicators();
    setTestingIndicators(false);
    if (result.ok) {
      soundEngine.playSuccessChime();
      toast.success("Halo verified: screen edge pulse and cursor ring fired", { duration: 3500 });
    } else {
      toast.error(`Halo test failed: ${result.error}`, { duration: 5000 });
    }
  };

  const handleRestartEngine = async () => {
    setRestartingEngine(true);
    soundEngine.playTick();
    const result = await telemetryClient.restartEngine();
    const status = await telemetryClient.fetchEngineStatus();
    if (status) {
      setEngineState(status.state);
      setEnginePid(status.pid);
      setEngineLogTail(status.log_tail || []);
    }
    setRestartingEngine(false);
    if (result.ok) {
      soundEngine.playSuccessChime();
      toast.success(result.message || "Engine daemon restarted");
    } else {
      toast.error(result.message || "Engine restart failed", { duration: 5000 });
    }
  };

  const handleCopyPasskey = () => {
    if (relayToken) {
      navigator.clipboard.writeText(relayToken);
      setCopiedToken(true);
      toast.success("Passkey copied to clipboard");
      setTimeout(() => setCopiedToken(false), 2000);
    }
  };

  const handleRotatePasskey = async () => {
    if (!armRotateKey) {
      setArmRotateKey(true);
      setTimeout(() => setArmRotateKey(false), 6000);
      return;
    }
    setArmRotateKey(false);
    setRotatingKey(true);
    soundEngine.playTick();
    try {
      await rotatePasskey();
      soundEngine.playSuccessChime();
      toast.success("New passkey generated and saved everywhere.");
    } catch (err: any) {
      toast.error(err?.message || "Could not rotate passkey");
    } finally {
      setRotatingKey(false);
    }
  };

  const handleSyncCloudCredentials = async () => {
    setRefreshingProfile(true);
    soundEngine.playTick();
    try {
      await refreshProfile();
      soundEngine.playSuccessChime();
      toast.success("Credentials synchronized with cloud.");
    } catch (err: any) {
      toast.error(err?.message || "Failed to sync credentials");
    } finally {
      setRefreshingProfile(false);
    }
  };

  const handleCopyWorkspacePath = () => {
    navigator.clipboard.writeText(workspacePath);
    setCopiedPath(true);
    toast.success("Workspace path copied");
    setTimeout(() => setCopiedPath(false), 2000);
  };

  const handleToggleAutostart = async () => {
    if (!autostartInfo) return;
    setLoadingAutostart(true);
    soundEngine.playTick();
    try {
      const nextEnabled = !autostartInfo.enabled;
      const res = await extraDataService.setAutostart(nextEnabled, true);
      if (res.enabled === nextEnabled || res.success) {
        setAutostartInfo({
          ...autostartInfo,
          enabled: res.enabled,
          current_command: res.current_command || autostartInfo.current_command,
        });
        soundEngine.playSuccessChime();
        toast.success(res.enabled ? "Autostart on Windows login enabled" : "Autostart disabled");
      } else {
        toast.error(res.error || "Failed to update autostart setting");
      }
    } catch {
      toast.error("Failed to communicate with Extra daemon");
    } finally {
      setLoadingAutostart(false);
    }
  };

  const handleStartRelay = async () => {
    setLoadingRelayAction(true);
    soundEngine.playTick();
    try {
      const res = await extraDataService.startRelay(relayToken || undefined);
      if (res.success) {
        toast.success("Initiating Cloud Relay tunnel...");
        const updated = await extraDataService.fetchRelayStatus();
        setRelayStatus(updated);
        soundEngine.playSuccessChime();
      } else {
        toast.error("Could not start Cloud Relay");
      }
    } finally {
      setLoadingRelayAction(false);
    }
  };

  const handleStopRelay = async () => {
    setLoadingRelayAction(true);
    soundEngine.playTick();
    try {
      const ok = await extraDataService.stopRelay();
      if (ok) {
        toast.success("Cloud Relay disconnected");
        const updated = await extraDataService.fetchRelayStatus();
        setRelayStatus(updated);
      }
    } finally {
      setLoadingRelayAction(false);
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
      setTimeout(() => setCloudPingResult(null), 4000);
    }
  };

  const handleCopyCloudMcpUrl = () => {
    soundEngine.playTick();
    const url = relayStatus?.cloud_mcp_url || (relayToken ? `https://extra.yantraos.com/mcp?key=${relayToken}` : "https://extra.yantraos.com/sse");
    navigator.clipboard.writeText(url);
    setCopiedCloudMcpUrl(true);
    toast.success("Cloud MCP endpoint copied for ChatGPT / Claude");
    setTimeout(() => setCopiedCloudMcpUrl(false), 2000);
  };

  return (
    <div className="max-w-4xl space-y-6 pb-16 animate-in fade-in duration-150">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-[#dfe4eb] select-none">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-[#1a1a1c] tracking-tight">
              Settings & Preferences
            </h2>
            <span className="text-[10px] font-mono text-[#525866] bg-[#f0f2f6] border border-[#dfe4eb] px-1.5 py-0.5 rounded-md">
              {useUpdateStore((s) => s.installedVersionLabel) || APP_VERSION_LABEL} local
            </span>
          </div>
          <p className="text-xs text-[#525866] mt-0.5">
            Hardware pacer, sensory telemetry, workspace safety boundaries, and sovereign identity
          </p>
        </div>

        <div className="flex items-center gap-2">
          {pingResult && (
            <span className="text-xs font-mono font-medium text-emerald-700 bg-[#edfcf2] border border-[#bbf0cf] px-2 py-0.5 rounded-md tabular-nums">
              {pingResult}
            </span>
          )}
          <button
            onClick={testPing}
            disabled={testingPing}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#dfe4eb] bg-white text-xs font-medium text-[#1a1a1c] hover:bg-[#f0f2f6] transition-colors cursor-pointer"
          >
            <RefreshCw className={`size-3.5 ${testingPing ? "animate-spin text-[#1677ff]" : "text-[#525866]"}`} />
            <span>Test ping</span>
          </button>
        </div>
      </div>

      {/* Main Settings Sections */}
      <div className="space-y-6">
        {/* Section 0: Software Updates & Engine Release Channel */}
        <section className="bg-white rounded-xl border border-[#dfe4eb] overflow-hidden shadow-2xs">
          <div className="px-5 py-4 border-b border-[#dfe4eb] flex items-center justify-between bg-white">
            <div className="flex items-center gap-3">
              <div className="size-8 rounded-lg bg-[#f0f2f6] border border-[#dfe4eb] flex items-center justify-center shrink-0">
                <RefreshCw className="size-4 text-[#1677ff]" />
              </div>
              <div>
                <h3 className="text-xs font-semibold text-[#1a1a1c] tracking-tight">
                  Software Updates
                </h3>
                <p className="text-[11px] text-[#525866] mt-0.5">
                  Release verification, engine hot-reload & automated security patches
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded-md bg-[#f8f9fb] text-[#1a1a1c] border border-[#dfe4eb] tabular-nums">
                {activeVerLabel}
              </span>
            </div>
          </div>

          <div className="p-5 space-y-4">
            {/* If Update Available: Elevated Emerald Banner */}
            {updateAvailable && latestTag ? (
              <div className="rounded-xl border border-[#bbf0cf] bg-[#edfcf2] p-4 text-[#0e8345]">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="size-2 rounded-full bg-[#0e8345] animate-ping" />
                      <span className="font-semibold text-xs text-[#0e8345] tracking-tight">
                        Extra {latestTag} is ready to install
                      </span>
                      <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-white text-[#0e8345] border border-[#bbf0cf]">
                        New Release
                      </span>
                    </div>
                    <p className="text-[11px] text-[#0e8345]/90">
                      Installed version {activeVerLabel}. Includes performance optimizations and security hardening.
                    </p>
                  </div>

                  <div className="flex items-center gap-2 self-start sm:self-auto">
                    <button
                      onClick={() => void performUpdateNow()}
                      disabled={updatingApp}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#0e8345] hover:bg-[#0b6b37] text-white text-xs font-medium transition-colors shadow-2xs cursor-pointer disabled:opacity-50"
                    >
                      <ArrowUpCircle className={`size-3.5 ${updatingApp ? "animate-spin" : ""}`} />
                      <span>{updatingApp ? "Updating..." : "Update Now"}</span>
                    </button>
                    {onNavigateTab && (
                      <button
                        onClick={() => {
                          soundEngine.playTick();
                          onNavigateTab("about");
                        }}
                        className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-[#bbf0cf] bg-white hover:bg-[#edfcf2] text-xs font-medium text-[#0e8345] transition-colors cursor-pointer"
                      >
                        <span>Changelog</span>
                        <ChevronRight className="size-3" />
                      </button>
                    )}
                  </div>
                </div>

                {/* Live Progress Bar when updating */}
                {updatingApp && (
                  <div className="mt-3 pt-3 border-t border-[#bbf0cf]/60 space-y-1.5">
                    <div className="flex items-center justify-between text-[11px] font-mono">
                      <span>{updateStatusMsg || "Applying updates..."}</span>
                      <span className="tabular-nums font-semibold">{updateProgress}%</span>
                    </div>
                    <div className="w-full h-1.5 bg-white/70 rounded-full overflow-hidden border border-[#bbf0cf]">
                      <div
                        className="h-full bg-[#0e8345] rounded-full transition-all duration-300"
                        style={{ width: `${Math.max(5, updateProgress)}%` }}
                      />
                    </div>
                  </div>
                )}
              </div>
            ) : (
              /* Up to Date Status Banner */
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3.5 rounded-lg bg-[#f8f9fb] border border-[#dfe4eb]">
                <div className="flex items-center gap-2.5">
                  <div className="size-5 rounded-full bg-[#edfcf2] border border-[#bbf0cf] flex items-center justify-center shrink-0">
                    <Check className="size-3 text-[#0e8345]" />
                  </div>
                  <div>
                    <span className="text-xs font-medium text-[#1a1a1c] block">
                      Extra is up to date
                    </span>
                    <span className="text-[11px] font-mono text-[#868c98] block">
                      {lastCheckedAt ? `Last checked ${new Date(lastCheckedAt).toLocaleTimeString()}` : "Checked on startup"}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => void checkNow()}
                    disabled={checkingUpdate || updatingApp}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#dfe4eb] bg-white text-xs font-medium text-[#1a1a1c] hover:bg-[#f0f2f6] transition-colors cursor-pointer disabled:opacity-50 shadow-2xs"
                  >
                    <RefreshCw className={`size-3.5 ${checkingUpdate ? "animate-spin text-[#1677ff]" : "text-[#525866]"}`} />
                    <span>{checkingUpdate ? "Checking..." : "Check for updates"}</span>
                  </button>
                  {onNavigateTab && (
                    <button
                      onClick={() => {
                        soundEngine.playTick();
                        onNavigateTab("about");
                      }}
                      className="text-xs text-[#1677ff] hover:underline cursor-pointer px-1.5 py-1"
                    >
                      Release Notes
                    </button>
                  )}
                </div>
              </div>
            )}

            {/* Toggle Preferences */}
            <div className="pt-2 border-t border-[#dfe4eb] divide-y divide-[#dfe4eb]">
              <div className="py-2.5 flex items-center justify-between gap-4">
                <div>
                  <span className="text-xs font-medium text-[#1a1a1c] block">
                    Automatic update checks
                  </span>
                  <span className="text-[11px] text-[#525866] block">
                    Periodically query official release channels and surface unobtrusive notifications
                  </span>
                </div>
                <Switch
                  checked={autoCheck}
                  onCheckedChange={setAutoCheck}
                />
              </div>

              <div className="py-2.5 flex items-center justify-between gap-4">
                <div>
                  <span className="text-xs font-medium text-[#1a1a1c] block">
                    Download updates automatically
                  </span>
                  <span className="text-[11px] text-[#525866] block">
                    Fetch verified signed packages in background as soon as they are published
                  </span>
                </div>
                <Switch
                  checked={autoUpdate}
                  onCheckedChange={setAutoUpdate}
                />
              </div>
            </div>
          </div>
        </section>

        {/* Section 1: Execution Pacing */}
        <section className="bg-white rounded-xl border border-[#dfe4eb] overflow-hidden">
          <div className="px-5 py-4 border-b border-[#dfe4eb] flex items-center justify-between bg-white">
            <div>
              <h3 className="text-xs font-semibold text-[#1a1a1c] tracking-tight">
                Execution Speed & Pacing
              </h3>
              <p className="text-[11px] text-[#525866] mt-0.5">
                How fast Extra works through each step on your computer
              </p>
            </div>
            <span className="text-[10px] font-mono text-[#868c98] px-2 py-0.5 rounded bg-[#f0f2f6] border border-[#dfe4eb]">
              SOUL-Gateman
            </span>
          </div>

          <div className="divide-y divide-[#dfe4eb]">
            {[
              {
                mode: "turbo",
                icon: Zap,
                title: SPEED_MODE_META.turbo.label,
                desc: SPEED_MODE_META.turbo.desc,
                latency: SPEED_MODE_META.turbo.pace,
                recommended: SPEED_MODE_META.turbo.recommended,
              },
              {
                mode: "balanced",
                icon: Gauge,
                title: SPEED_MODE_META.balanced.label,
                desc: SPEED_MODE_META.balanced.desc,
                latency: SPEED_MODE_META.balanced.pace,
                recommended: SPEED_MODE_META.balanced.recommended,
              },
              {
                mode: "smart",
                icon: Shield,
                title: SPEED_MODE_META.smart.label,
                desc: SPEED_MODE_META.smart.desc,
                latency: SPEED_MODE_META.smart.pace,
                recommended: SPEED_MODE_META.smart.recommended,
              },
            ].map((item) => {
              const isSelected = speedMode === item.mode;
              const Icon = item.icon;
              return (
                <div
                  key={item.mode}
                  onClick={() => handleSpeedModeChange(item.mode as SpeedMode)}
                  className={`px-5 py-3.5 flex items-center justify-between gap-4 cursor-pointer transition-colors ${
                    isSelected ? "bg-[#f8f9fb]" : "hover:bg-[#fafbfc]"
                  }`}
                >
                  <div className="flex items-start gap-3.5 min-w-0">
                    <div
                      className={`size-8 rounded-lg flex items-center justify-center shrink-0 border ${
                        isSelected
                          ? "bg-white border-[#1677ff]/30 text-[#1677ff]"
                          : "bg-[#f0f2f6] border-[#dfe4eb] text-[#525866]"
                      }`}
                    >
                      <Icon className="size-4" />
                    </div>

                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-[#1a1a1c]">
                          {item.title}
                        </span>
                        {item.recommended && (
                          <span className="text-[10px] font-medium text-[#1677ff] bg-[#eff6ff] border border-[#bfdbfe] px-1.5 py-0.2 rounded">
                            Recommended
                          </span>
                        )}
                        <span className="text-[10px] font-mono text-[#525866] bg-white border border-[#dfe4eb] px-1.5 py-0.2 rounded">
                          {item.latency}
                        </span>
                      </div>
                      <p className="text-[11px] text-[#525866] mt-0.5 line-clamp-1">
                        {item.desc}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center shrink-0">
                    <div
                      className={`size-4 rounded-full border flex items-center justify-center transition-colors ${
                        isSelected
                          ? "border-[#1677ff] bg-[#1677ff]"
                          : "border-[#ccd2dc] bg-white"
                      }`}
                    >
                      {isSelected && <span className="size-1.5 rounded-full bg-white" />}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* Section 2: Sensory Telemetry & Halos */}
        <section className="bg-white rounded-xl border border-[#dfe4eb] overflow-hidden">
          <div className="px-5 py-4 border-b border-[#dfe4eb]">
            <h3 className="text-xs font-semibold text-[#1a1a1c] tracking-tight">
              Sensory Feedback & Desktop Cues
            </h3>
            <p className="text-[11px] text-[#525866] mt-0.5">
              Live feedback channels providing real-time awareness during autonomous execution
            </p>
          </div>

          <div className="divide-y divide-[#dfe4eb]">
            <div className="px-5 py-3.5 flex items-center justify-between gap-4">
              <div>
                <div className="text-xs font-semibold text-[#1a1a1c]">Acoustic Chime</div>
                <div className="text-[11px] text-[#525866] mt-0.5">
                  Synthesized dual-tone glass marimba chord upon subtask completion or milestone resolution
                </div>
              </div>
              <button
                onClick={handleTestChimes}
                disabled={testingSound}
                className="px-3 py-1.5 rounded-lg border border-[#dfe4eb] bg-[#f8f9fb] hover:bg-[#eceff4] text-xs font-medium text-[#1a1a1c] flex items-center gap-1.5 cursor-pointer shrink-0 transition-colors"
              >
                <Volume2 className="size-3.5 text-[#525866]" />
                <span>Test chime</span>
              </button>
            </div>

            <div className="px-5 py-3.5 flex items-center justify-between gap-4">
              <div>
                <div className="text-xs font-semibold text-[#1a1a1c]">Desktop Halos & Glow</div>
                <div className="text-[11px] text-[#525866] mt-0.5">
                  Subtle ambient screen edge pulse and cursor ring indicating active computer-use
                </div>
              </div>
              <button
                onClick={handleTestIndicators}
                disabled={testingIndicators}
                className="px-3 py-1.5 rounded-lg border border-[#dfe4eb] bg-[#f8f9fb] hover:bg-[#eceff4] text-xs font-medium text-[#1a1a1c] flex items-center gap-1.5 cursor-pointer shrink-0 transition-colors"
              >
                <Eye className="size-3.5 text-[#525866]" />
                <span>Test halo</span>
              </button>
            </div>
          </div>
        </section>

        {/* Section 2b: Engine Daemon */}
        <section className="bg-white rounded-xl border border-[#dfe4eb] overflow-hidden">
          <div className="px-5 py-4 border-b border-[#dfe4eb] flex items-center justify-between">
            <div>
              <h3 className="text-xs font-semibold text-[#1a1a1c] tracking-tight">
                Engine Daemon
              </h3>
              <p className="text-[11px] text-[#525866] mt-0.5">
                Local MCP engine on 127.0.0.1:8000 — powers telemetry, halos, and tool dispatch
              </p>
            </div>
            <span
              className={`text-[10px] font-mono px-2 py-0.5 rounded-md border ${
                engineState === "online"
                  ? "bg-[#edfcf2] text-[#0e8345] border-[#bbf0cf]"
                  : engineState === "auth-mismatch"
                    ? "bg-[#fff8e6] text-[#b7791f] border-[#f5dfa8]"
                    : "bg-[#fff1f2] text-[#e11d48] border-[#fecdd3]"
              }`}
            >
              {engineState === "online"
                ? "Online"
                : engineState === "auth-mismatch"
                  ? "Token mismatch"
                  : engineState === "offline"
                    ? "Offline"
                    : "Checking..."}
            </span>
          </div>

          <div className="divide-y divide-[#dfe4eb]">
            <div className="px-5 py-3.5 flex items-center justify-between gap-4">
              <div>
                <div className="text-xs font-semibold text-[#1a1a1c]">
                  {engineState === "online"
                    ? `Running${enginePid ? ` (pid ${enginePid})` : ""}`
                    : engineState === "auth-mismatch"
                      ? "Stale daemon holding the port"
                      : "Daemon not responding"}
                </div>
                <div className="text-[11px] text-[#525866] mt-0.5">
                  {engineState === "auth-mismatch"
                    ? "The engine is reachable but rejected this app's token. Restart replaces it with a fresh, authorized daemon."
                    : "Restart stops any orphaned daemon and starts a fresh one with this app's token."}
                </div>
              </div>
              <button
                onClick={handleRestartEngine}
                disabled={restartingEngine}
                className="px-3 py-1.5 rounded-lg border border-[#dfe4eb] bg-[#f8f9fb] hover:bg-[#eceff4] text-xs font-medium text-[#1a1a1c] flex items-center gap-1.5 cursor-pointer shrink-0 transition-colors disabled:opacity-60"
              >
                <RefreshCw className={`size-3.5 text-[#525866] ${restartingEngine ? "animate-spin" : ""}`} />
                <span>{restartingEngine ? "Restarting..." : "Restart engine"}</span>
              </button>
            </div>

            {engineLogTail.length > 0 && (
              <details className="px-5 py-3">
                <summary className="text-[11px] font-medium text-[#1677ff] cursor-pointer">
                  Engine log (last {engineLogTail.length} lines)
                </summary>
                <pre className="mt-2 max-h-40 overflow-auto rounded-lg bg-[#0a0d14] p-3 text-[10px] leading-relaxed font-mono text-[#c2c7d0] whitespace-pre-wrap">
                  {engineLogTail.join("\n")}
                </pre>
              </details>
            )}
          </div>
        </section>

        {/* Section 2c: System Startup & Cloud Connectivity */}
        <section className="bg-white rounded-xl border border-[#dfe4eb] overflow-hidden">
          <div className="px-5 py-4 border-b border-[#dfe4eb] flex items-center justify-between">
            <div>
              <h3 className="text-xs font-semibold text-[#1a1a1c] tracking-tight">
                System Startup & Cloud Connectivity
              </h3>
              <p className="text-[11px] text-[#525866] mt-0.5">
                Windows login auto-start and persistent WebSocket relay tunnel for remote AI computer use
              </p>
            </div>
            <span
              className={`text-[10px] font-mono px-2 py-0.5 rounded-md border ${
                !isAuthenticated
                  ? "bg-[#f0f2f6] text-[#525866] border-[#dfe4eb]"
                  : relayStatus?.connected
                  ? "bg-[#edfcf2] text-[#0e8345] border-[#bbf0cf]"
                  : "bg-[#fff8e6] text-[#b7791f] border-[#f5dfa8]"
              }`}
            >
              {!isAuthenticated
                ? "Local Only"
                : relayStatus?.connected
                ? "Relay Active"
                : "Standby"}
            </span>
          </div>

          <div className="divide-y divide-[#dfe4eb]">
            {/* Windows Autostart */}
            <div className="px-5 py-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <Power className="size-4 text-[#525866]" />
                  <span className="text-xs font-semibold text-[#1a1a1c]">
                    Launch Extra on Windows Startup
                  </span>
                  {autostartInfo?.enabled && (
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#edfcf2] text-[#0e8345] border border-[#bbf0cf]">
                      Enabled
                    </span>
                  )}
                </div>
                <p className="text-[11px] text-[#525866] mt-0.5">
                  Automatically launches the Extra engine daemon and interface minimized when Windows starts, keeping Cloud MCP continuously available for ChatGPT and Claude.
                </p>
                {(autostartInfo?.current_command || autostartInfo?.command) && (
                  <div className="mt-1.5 text-[10px] font-mono text-[#868c98] truncate max-w-xl">
                    HKCU\Software\Microsoft\Windows\CurrentVersion\Run\Extra
                  </div>
                )}
              </div>

              <button
                onClick={handleToggleAutostart}
                disabled={loadingAutostart || !autostartInfo}
                className={`px-3 py-1.5 rounded-lg border text-xs font-medium flex items-center gap-1.5 cursor-pointer shrink-0 transition-colors ${
                  autostartInfo?.enabled
                    ? "bg-[#fff1f2] border-[#fecdd3] text-[#e11d48] hover:bg-[#ffe4e6]"
                    : "bg-[#1677ff] border-[#1677ff] text-white hover:bg-[#125ecc]"
                } disabled:opacity-60`}
              >
                {loadingAutostart ? (
                  <>
                    <RefreshCw className="size-3.5 animate-spin" />
                    <span>Updating...</span>
                  </>
                ) : autostartInfo?.enabled ? (
                  <span>Disable Autostart</span>
                ) : (
                  <span>Enable Autostart</span>
                )}
              </button>
            </div>

            {/* Cloud Relay Tunnel */}
            <div className="px-5 py-3.5 space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <Cloud className="size-4 text-[#525866]" />
                    <span className="text-xs font-semibold text-[#1a1a1c]">
                      Cloud MCP Relay Tunnel
                    </span>
                    {isAuthenticated && relayStatus?.connected && (
                      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-[#edfcf2] text-[#0e8345] border border-[#bbf0cf]">
                        <span className="size-1.5 rounded-full bg-[#0e8345] animate-ping" />
                        Online
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-[#525866] mt-0.5">
                    Persistent outbound WebSocket tunnel to AWS Cloud Hub. Enables remote models to pilot this machine without port-forwarding or public IP exposure.
                  </p>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  {cloudPingResult && (
                    <span className="text-xs font-mono font-medium text-emerald-700 bg-[#edfcf2] border border-[#bbf0cf] px-2 py-0.5 rounded-md tabular-nums">
                      {cloudPingResult}
                    </span>
                  )}
                  {isAuthenticated && (
                    <button
                      onClick={handleTestCloudPing}
                      disabled={testingCloudPing}
                      className="px-2.5 py-1.5 rounded-lg border border-[#dfe4eb] bg-white hover:bg-[#f8f9fb] text-xs font-medium text-[#1a1a1c] flex items-center gap-1.5 cursor-pointer transition-colors"
                      title="Test live roundtrip ping to AWS Hub"
                    >
                      <Radio className={`size-3.5 ${testingCloudPing ? "animate-spin text-[#1677ff]" : "text-[#525866]"}`} />
                      <span>Ping Hub</span>
                    </button>
                  )}
                  {isAuthenticated && (
                    relayStatus?.connected ? (
                      <button
                        onClick={handleStopRelay}
                        disabled={loadingRelayAction}
                        className="px-2.5 py-1.5 rounded-lg border border-[#fecdd3] bg-[#fff1f2] hover:bg-[#ffe4e6] text-[#e11d48] text-xs font-medium flex items-center gap-1.5 cursor-pointer transition-colors"
                      >
                        <span>Disconnect</span>
                      </button>
                    ) : (
                      <button
                        onClick={handleStartRelay}
                        disabled={loadingRelayAction}
                        className="px-2.5 py-1.5 rounded-lg bg-[#1677ff] hover:bg-[#125ecc] text-white text-xs font-medium flex items-center gap-1.5 cursor-pointer transition-colors"
                      >
                        <span>Connect</span>
                      </button>
                    )
                  )}
                </div>
              </div>

              {/* URL & Endpoint Box */}
              {isAuthenticated ? (
                <div className="flex items-center justify-between gap-3 p-2.5 rounded-lg bg-[#f8f9fb] border border-[#dfe4eb]">
                  <div className="min-w-0 flex items-center gap-2">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-[#868c98] shrink-0 font-medium">
                      Cloud MCP URL:
                    </span>
                    <span className="font-mono text-xs text-[#1a1a1c] truncate select-all">
                      {relayStatus?.cloud_mcp_url || (relayToken ? `https://extra.yantraos.com/mcp?key=${relayToken}` : "https://extra.yantraos.com/sse")}
                    </span>
                  </div>
                  <button
                    onClick={handleCopyCloudMcpUrl}
                    className="px-2.5 py-1 rounded-md border border-[#dfe4eb] bg-white hover:bg-[#f0f2f6] text-[11px] font-medium text-[#1a1a1c] flex items-center gap-1.5 cursor-pointer shrink-0 transition-colors"
                  >
                    {copiedCloudMcpUrl ? (
                      <>
                        <Check className="size-3 text-emerald-600" />
                        <span className="text-emerald-700">Copied</span>
                      </>
                    ) : (
                      <>
                        <Copy className="size-3 text-[#525866]" />
                        <span>Copy URL</span>
                      </>
                    )}
                  </button>
                </div>
              ) : (
                <div className="p-3 rounded-lg bg-[#f8f9fb] border border-[#dfe4eb] flex items-center justify-between gap-3">
                  <div className="text-[11px] text-[#525866]">
                    Cloud Relay is completely dormant in Sovereign Local Mode. Sign in to connect to AWS Hub and allow ChatGPT / Claude to pilot your PC.
                  </div>
                  <button
                    onClick={openAuthModal}
                    className="px-3 py-1.5 rounded-lg bg-[#1677ff] text-white text-xs font-medium hover:bg-[#125ecc] transition-colors shrink-0 cursor-pointer"
                  >
                    Sign In
                  </button>
                </div>
              )}
            </div>
          </div>
        </section>

        {/* Section 3: Safety & Boundaries */}
        <section className="bg-white rounded-xl border border-[#dfe4eb] overflow-hidden">
          <div className="px-5 py-4 border-b border-[#dfe4eb] flex items-center justify-between">
            <div>
              <h3 className="text-xs font-semibold text-[#1a1a1c] tracking-tight">
                Safety & Sandbox Boundaries
              </h3>
              <p className="text-[11px] text-[#525866] mt-0.5">
                Hardware interlocks, emergency stops, and filesystem access controls
              </p>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-[#edfcf2] text-[#0e8345] border border-[#bbf0cf]">
              CFA Enforced
            </span>
          </div>

          <div className="divide-y divide-[#dfe4eb]">
            {/* Kill Switch */}
            <div className="px-5 py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-[#1a1a1c]">Hardware Kill Switch</span>
                  <kbd className="px-1.5 py-0.5 rounded bg-[#f0f2f6] border border-[#dfe4eb] text-[10px] font-mono text-[#525866]">
                    Ctrl + Alt + Esc
                  </kbd>
                </div>
                <p className="text-[11px] text-[#525866] mt-0.5">
                  Instantly releases all Win32 hardware hooks, aborts dispatch loops, and halts execution immediately
                </p>
              </div>

              <div>
                {!isPanicActive ? (
                  <button
                    onClick={panicStop}
                    className="px-3.5 py-1.5 rounded-lg bg-[#fff1f2] hover:bg-[#ffe4e6] text-[#e11d48] border border-[#fecdd3] text-xs font-medium transition-colors cursor-pointer shrink-0"
                  >
                    Freeze engine
                  </button>
                ) : (
                  <button
                    onClick={resumePilot}
                    className="px-3.5 py-1.5 rounded-lg bg-[#1a1a1c] hover:bg-[#2c3038] text-white text-xs font-medium transition-colors cursor-pointer shrink-0 flex items-center gap-1.5"
                  >
                    <Play className="size-3 fill-current" />
                    <span>Resume pilot</span>
                  </button>
                )}
              </div>
            </div>

            {/* Workspace Directory */}
            <div className="px-5 py-4 space-y-2">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-xs font-semibold text-[#1a1a1c]">Workspace Directory</span>
                  <p className="text-[11px] text-[#525866] mt-0.5">
                    Safe local folder isolated from Windows Defender Controlled Folder Access restrictions
                  </p>
                </div>
                <button
                  onClick={handleCopyWorkspacePath}
                  className="px-2.5 py-1 rounded-md border border-[#dfe4eb] bg-white hover:bg-[#f8f9fb] text-[11px] font-medium text-[#1a1a1c] flex items-center gap-1.5 cursor-pointer transition-colors"
                >
                  {copiedPath ? (
                    <>
                      <Check className="size-3 text-emerald-600" />
                      <span className="text-emerald-700">Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy className="size-3 text-[#525866]" />
                      <span>Copy path</span>
                    </>
                  )}
                </button>
              </div>

              <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[#f8f9fb] border border-[#dfe4eb]">
                <FolderOpen className="size-4 text-[#868c98] shrink-0" />
                <span className="font-mono text-xs text-[#1a1a1c] truncate select-all">
                  {workspacePath}
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* Section 4: Interface & Account */}
        <section className="bg-white rounded-xl border border-[#dfe4eb] overflow-hidden">
          <div className="px-5 py-4 border-b border-[#dfe4eb] flex items-center justify-between">
            <div>
              <h3 className="text-xs font-semibold text-[#1a1a1c] tracking-tight">
                Interface & Sovereign Identity
              </h3>
              <p className="text-[11px] text-[#525866] mt-0.5">
                Local telemetry and optional relay passkey for remote cloud coordination
              </p>
            </div>
            <div className="flex items-center gap-1.5 text-[11px] text-[#0e8345] font-medium">
              <span className="size-1.5 rounded-full bg-[#0e8345]" />
              <span>Sovereign Local Mode</span>
            </div>
          </div>

          <div className="px-5 py-4">
            {isAuthenticated && user ? (
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-3 rounded-lg bg-[#f8f9fb] border border-[#dfe4eb]">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-[#1a1a1c]">{user.username}</span>
                    <span className="text-[11px] text-[#525866]">{user.email}</span>
                  </div>
                  {relayToken && (
                    <div className="text-[11px] font-mono text-[#868c98] mt-1 flex flex-wrap items-center gap-2">
                      <span className="flex items-center gap-1.5">
                        <Key className="size-3.5 text-[#525866]" />
                        <span>{relayToken.slice(0, 16)}••••••••</span>
                      </span>
                      {user.token_rotated_at && (
                        <span className="text-[10px] text-[#868c98]">
                          (Rotated {new Date(user.token_rotated_at * 1000).toLocaleDateString()})
                        </span>
                      )}
                    </div>
                  )}
                </div>

                <div className="flex flex-wrap items-center gap-2 shrink-0">
                  <button
                    onClick={handleSyncCloudCredentials}
                    disabled={refreshingProfile}
                    className="px-2.5 py-1.5 rounded-lg bg-white border border-[#dfe4eb] text-xs font-medium text-[#1a1a1c] hover:bg-[#eceff4] flex items-center gap-1.5 cursor-pointer transition-colors"
                    title="Fetch latest profile and rotated keys from cloud"
                  >
                    <RefreshCw className={`size-3.5 text-[#525866] ${refreshingProfile ? "animate-spin" : ""}`} />
                    <span>{refreshingProfile ? "Syncing..." : "Sync"}</span>
                  </button>

                  {relayToken && (
                    <button
                      onClick={handleRotatePasskey}
                      disabled={rotatingKey}
                      className={`px-2.5 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 cursor-pointer transition-colors ${
                        armRotateKey
                          ? "bg-[#e11d48] text-white hover:bg-[#be123c]"
                          : "bg-white border border-[#dfe4eb] text-[#1a1a1c] hover:bg-[#eceff4]"
                      }`}
                      title="Rotate computer link passkey"
                    >
                      <RefreshCw className={`size-3.5 ${rotatingKey ? "animate-spin" : ""}`} />
                      <span>{rotatingKey ? "Rotating..." : armRotateKey ? "Confirm?" : "Rotate"}</span>
                    </button>
                  )}

                  {relayToken && (
                    <button
                      onClick={handleCopyPasskey}
                      className="px-2.5 py-1.5 rounded-lg bg-white border border-[#dfe4eb] text-xs font-medium text-[#1a1a1c] hover:bg-[#eceff4] flex items-center gap-1.5 cursor-pointer transition-colors"
                      title="Copy passkey"
                    >
                      {copiedToken ? (
                        <>
                          <Check className="size-3.5 text-emerald-600" />
                          <span>Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy className="size-3.5 text-[#525866]" />
                          <span>Copy token</span>
                        </>
                      )}
                    </button>
                  )}
                  <button
                    onClick={logout}
                    className="px-2.5 py-1.5 rounded-lg border border-[#fecdd3] bg-[#fff1f2] hover:bg-[#ffe4e6] text-[#e11d48] text-xs font-medium flex items-center gap-1.5 cursor-pointer transition-colors"
                    title="Sign out"
                  >
                    <LogOut className="size-3.5" />
                    <span>Sign out</span>
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-3 rounded-lg bg-[#f8f9fb] border border-[#dfe4eb]">
                <div className="flex items-center gap-3">
                  <div className="size-8 rounded-lg bg-white border border-[#dfe4eb] flex items-center justify-center shrink-0 text-[#0e8345]">
                    <Shield className="size-4" />
                  </div>
                  <div>
                    <div className="text-xs font-semibold text-[#1a1a1c]">
                      Air-Gapped Local Operation
                    </div>
                    <div className="text-[11px] text-[#525866] mt-0.5">
                      All telemetry and tool actuation run on local loopback. No cloud account required.
                    </div>
                  </div>
                </div>

                <button
                  onClick={() => {
                    soundEngine.playTick();
                    openAuthModal();
                  }}
                  className="flex items-center justify-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-[#1a1a1c] hover:bg-[#2c3038] text-white text-xs font-medium transition-colors cursor-pointer shrink-0"
                >
                  <Lock className="size-3.5" />
                  <span>Connect Cloud Hub</span>
                </button>
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
