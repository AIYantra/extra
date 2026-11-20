import { useState, useEffect, useRef } from "react";
import {
  Search,
  Laptop,
  KeyRound,
  ChevronRight,
  ChevronDown,
  ExternalLink,
  LogOut,
  Copy,
  Check,
  Globe,
  User,
  RefreshCw,
} from "lucide-react";
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";
import { DesktopWindowControls } from "./DesktopWindowControls";
import { ExtraAvatar } from "../ExtraAvatar";
import { useEngineStore } from "../../store/useEngineStore";
import { useAuthStore } from "../../store/useAuthStore";
import { useUpdateStore } from "../../store/useUpdateStore";
import { soundEngine } from "../../utils/sound";
import { toast } from "sonner";
import { telemetryClient } from "../../services/telemetryClient";
import { extraDataService, type LiveRelayStatus } from "../../services/extraDataService";

interface DashboardTopBarProps {
  currentTab?: string;
  onOpenCommandPalette: () => void;
  onLaunchNewPilot?: () => void;
  onNavigateTab?: (tab: string) => void;
}

const TAB_TITLES: Record<string, string> = {
  overview: "Dashboard",
  tools: "Tools & Skills",
  sessions: "Execution History",
  integrations: "AI Integrations",
  settings: "Settings & Health",
  profile: "Profile",
  about: "About",
};

export function DashboardTopBar({
  currentTab = "overview",
  onOpenCommandPalette,
  onNavigateTab,
}: DashboardTopBarProps) {
  const isServerOnline = useEngineStore((state) => state.isServerOnline);
  const isPanicActive = useEngineStore((state) => state.isPanicActive);
  const resumePilot = useEngineStore((state) => state.resumePilot);

  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const isLocalOfflineMode = useAuthStore((state) => state.isLocalOfflineMode);
  const user = useAuthStore((state) => state.user);
  const relayToken = useAuthStore((state) => state.relayToken);
  const openAuthModal = useAuthStore((state) => state.openAuthModal);
  const logout = useAuthStore((state) => state.logout);
  const setLocalOffline = useAuthStore((state) => state.setLocalOffline);

  const updateAvailable = useUpdateStore((state) => state.updateAvailable);
  const latestTag = useUpdateStore((state) => state.latestTag);
  const installedVersionLabel = useUpdateStore((state) => state.installedVersionLabel);

  const [isMac, setIsMac] = useState(false);
  const [isAccountDropdownOpen, setIsAccountDropdownOpen] = useState(false);
  const [copiedRelay, setCopiedRelay] = useState(false);
  const [restartingEngine, setRestartingEngine] = useState(false);
  const [relayStatus, setRelayStatus] = useState<LiveRelayStatus | null>(null);
  const [togglingOffline, setTogglingOffline] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let mounted = true;
    const updateRelay = async () => {
      try {
        const stat = await extraDataService.fetchRelayStatus();
        if (mounted) setRelayStatus(stat);
      } catch {}
    };
    updateRelay();
    const interval = setInterval(updateRelay, 4000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  const handleRestartEngine = async () => {
    if (restartingEngine) return;
    setRestartingEngine(true);
    soundEngine.playTick();
    const result = await telemetryClient.restartEngine();
    setRestartingEngine(false);
    if (result.ok) {
      soundEngine.playSuccessChime();
      toast.success(result.message);
    } else {
      toast.error(result.message, { duration: 5000 });
    }
  };

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsAccountDropdownOpen(false);
      }
    }
    if (isAccountDropdownOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isAccountDropdownOpen]);

  useEffect(() => {
    if (typeof navigator !== "undefined") {
      setIsMac(navigator.platform?.toUpperCase().includes("MAC") || false);
    }
  }, []);

  const activeTitle = TAB_TITLES[currentTab] || "Dashboard";
  const shortcutLabel = isMac ? "⌘K" : "Ctrl+K";

  return (
    <header
      data-tauri-drag-region
      className="h-14 shrink-0 border-b border-[#dfe4eb] bg-white px-4 sm:px-5 flex items-center justify-between gap-4 select-none shadow-[0_1px_2px_0_rgba(0,0,0,0.02)]"
    >
      {/* Left: Clean Breadcrumb & Engine Port Status (Unslop Pass 1 & 4) */}
      <div className="flex items-center gap-3 min-w-0" data-tauri-drag-region>
        <div className="flex items-center gap-1.5 text-xs">
          <span className="text-[#868c98] font-normal hover:text-[#1a1a1c] transition-colors duration-150 cursor-default">
            Extra
          </span>
          <ChevronRight className="size-3 text-[#c2c7d0] shrink-0" />
          <span className="text-[#1a1a1c] font-medium tracking-tight truncate max-w-[150px] sm:max-w-none">
            {activeTitle}
          </span>
        </div>

        {/* Engine Daemon Health Status — Only shown when offline or reconnecting */}
        {!isServerOnline && (
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                onClick={handleRestartEngine}
                disabled={restartingEngine}
                className="hidden sm:inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-[#fff8e6] border border-[#f5dfa8] hover:border-[#e3b008] transition-colors duration-150 cursor-pointer disabled:opacity-60"
              >
                <span className="size-1.5 rounded-full shrink-0 bg-amber-500" />
                <span className="text-[11px] font-mono text-[#525866] tabular-nums">
                  {restartingEngine ? "Restarting..." : "Engine Offline — Restart"}
                </span>
                <RefreshCw
                  className={`size-3 text-[#b7791f] ${restartingEngine ? "animate-spin" : ""}`}
                />
              </button>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="text-xs">
              Engine daemon unreachable — click to restart it with this app's token
            </TooltipContent>
          </Tooltip>
        )}
      </div>

      {/* Center: Command Palette Trigger with Platform-Aware Keycap (Unslop Pass 4 & 7) */}
      <div className="flex-1 max-w-xs sm:max-w-sm md:max-w-md">
        <button
          onClick={() => {
            soundEngine.playTick();
            onOpenCommandPalette();
          }}
          className="w-full h-8.5 flex items-center justify-between gap-2 px-2.5 rounded-lg border border-[#dfe4eb] bg-[#f8f9fb] hover:bg-white hover:border-[#ccd2dc] transition-colors duration-150 text-left text-xs cursor-pointer group shadow-2xs"
        >
          <div className="flex items-center gap-2 min-w-0">
            <Search className="size-3.5 text-[#868c98] group-hover:text-[#1677ff] transition-colors duration-150 shrink-0" />
            <span className="truncate text-[#868c98] group-hover:text-[#1a1a1c] font-normal text-xs">
              Search commands...
            </span>
          </div>
          <kbd className="inline-flex items-center px-1.5 py-0.5 rounded border border-[#dfe4eb] bg-white text-[10px] font-mono text-[#868c98] shadow-2xs group-hover:border-[#ccd2dc] group-hover:text-[#1a1a1c] transition-colors duration-150 shrink-0">
            {shortcutLabel}
          </kbd>
        </button>
      </div>

      {/* Right: Account Status, Theme Switcher & Calm Emergency Pause */}
      <div className="flex items-center gap-2 shrink-0">
        {/* Subtle Update Available Pill */}
        {updateAvailable && (
          <button
            onClick={() => {
              soundEngine.playTick();
              onNavigateTab?.("about");
            }}
            className="hidden sm:inline-flex items-center gap-1.5 h-8 px-2.5 rounded-lg bg-[#edfcf2] hover:bg-[#dcfce7] border border-[#bbf0cf] text-[#0e8345] text-xs font-medium transition-colors cursor-pointer shadow-2xs"
            title="A newer version of Extra is available — click to view release notes"
          >
            <span className="size-1.5 rounded-full bg-[#0e8345] animate-pulse" />
            <span>Update Available</span>
            {latestTag && (
              <span className="font-mono text-[10px] tabular-nums font-semibold px-1 py-0.2 rounded bg-white text-[#0e8345] border border-[#bbf0cf]">
                {latestTag}
              </span>
            )}
          </button>
        )}

        {/* Account / Cloud Status */}
        {isAuthenticated && user ? (
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => {
                soundEngine.playTick();
                setIsAccountDropdownOpen((prev) => !prev);
              }}
              className="h-8 px-2.5 rounded-lg border border-[#dfe4eb] bg-white hover:bg-[#f8f9fb] transition-colors duration-150 flex items-center gap-2 text-xs text-[#1a1a1c] cursor-pointer shadow-2xs"
            >
              <ExtraAvatar seed={user.email} size={22} showBorder={false} />
              <span className="font-medium text-xs max-w-[100px] truncate">
                {user.username || user.email.split("@")[0]}
              </span>
              <span
                className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${
                  isLocalOfflineMode || (!relayStatus?.connected && relayStatus?.status === "stopped")
                    ? "bg-zinc-100 text-zinc-600 border-zinc-200"
                    : "bg-[#f8f9fb] text-[#525866] border-[#dfe4eb]"
                }`}
              >
                {isLocalOfflineMode ? "offline" : (user.plan || "Free")}
              </span>
              <ChevronDown className="size-3 text-[#868c98]" />
            </button>

            {/* Account Dropdown Card */}
            {isAccountDropdownOpen && (
              <div className="absolute right-0 top-10 w-72 rounded-xl bg-white border border-[#dfe4eb] shadow-[0_12px_32px_rgba(0,0,0,0.08)] z-50 p-3 select-none text-left animate-in fade-in zoom-in-95 duration-100">
                {/* User Identity Header */}
                <div className="flex items-center gap-2.5 pb-2.5 border-b border-[#dfe4eb]">
                  <ExtraAvatar seed={user.email} size={32} />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-1">
                      <span className="font-semibold text-xs text-[#0a0d14] truncate">
                        {user.username || user.email.split("@")[0]}
                      </span>
                      <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-[#1677ff]/10 text-[#1677ff] border border-[#1677ff]/20 font-medium shrink-0">
                        {user.plan || "Free"}
                      </span>
                    </div>
                    <span className="text-[11px] text-[#525866] truncate block">
                      {user.email}
                    </span>
                  </div>
                </div>

                {/* Cloud & Device Status Pill */}
                <div className="my-2 p-2 rounded-lg bg-[#f8f9fb] border border-[#dfe4eb] text-[11px] space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-[#868c98]">Cloud Relay</span>
                    {relayStatus?.connected && !isLocalOfflineMode ? (
                      <span className="inline-flex items-center gap-1 font-medium text-[#0e8345]">
                        <span className="size-1.5 rounded-full bg-[#0e8345] animate-pulse" />
                        Active (ap-south-1)
                      </span>
                    ) : relayStatus?.status === "connecting" && !isLocalOfflineMode ? (
                      <span className="inline-flex items-center gap-1 font-medium text-amber-600">
                        <span className="size-1.5 rounded-full bg-amber-500 animate-pulse" />
                        Connecting...
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 font-medium text-[#525866]">
                        <span className="size-1.5 rounded-full bg-[#868c98]" />
                        Sovereign Offline
                      </span>
                    )}
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-[#868c98]">Workstation</span>
                    <span className="font-mono text-[#1a1a1c] text-[10px] truncate max-w-[140px]" title={relayStatus?.device_name || "Windows PC"}>
                      {relayStatus?.device_name || "Windows PC"}
                    </span>
                  </div>
                </div>

                {/* Dropdown Menu Items */}
                <div className="space-y-1">
                  <button
                    onClick={() => {
                      soundEngine.playTick();
                      setIsAccountDropdownOpen(false);
                      onNavigateTab?.("profile");
                    }}
                    className="w-full flex items-center justify-between px-2.5 py-1.5 rounded-md hover:bg-[#f8f9fb] text-xs text-[#1a1a1c] transition-colors cursor-pointer"
                  >
                    <span className="flex items-center gap-2">
                      <User className="size-3.5 text-[#868c98]" />
                      <span>View Profile</span>
                    </span>
                    <ChevronRight className="size-3 text-[#868c98]" />
                  </button>
                  <button
                    onClick={() => {
                      soundEngine.playTick();
                      setIsAccountDropdownOpen(false);
                      onNavigateTab?.("about");
                    }}
                    className="w-full flex items-center justify-between px-2.5 py-1.5 rounded-md hover:bg-[#f8f9fb] text-xs text-[#1a1a1c] transition-colors cursor-pointer"
                  >
                    <span className="flex items-center gap-2">
                      <RefreshCw className="size-3.5 text-[#868c98]" />
                      <span>Software Updates</span>
                    </span>
                    <span className="text-[10px] font-mono text-[#868c98]">
                      {installedVersionLabel || "v0.3.6"}
                    </span>
                  </button>
                  <button
                    onClick={() => {
                      soundEngine.playTick();
                      setIsAccountDropdownOpen(false);
                      fetch("/api/extra/open-browser", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ url: "https://extra.yantraos.com/dashboard" }),
                      }).catch(() => {
                        window.open("https://extra.yantraos.com/dashboard", "_blank");
                      });
                    }}
                    className="w-full flex items-center justify-between px-2.5 py-1.5 rounded-md hover:bg-[#f8f9fb] text-xs text-[#1a1a1c] transition-colors cursor-pointer"
                  >
                    <span className="flex items-center gap-2">
                      <Globe className="size-3.5 text-[#868c98]" />
                      <span>Cloud Fleet Dashboard</span>
                    </span>
                    <ExternalLink className="size-3 text-[#868c98]" />
                  </button>

                  <button
                    onClick={() => {
                      const tokenToCopy = relayToken || user.relay_token || "";
                      if (!tokenToCopy) {
                        toast.error("No active Cloud Relay token");
                        return;
                      }
                      soundEngine.playTick();
                      navigator.clipboard.writeText(tokenToCopy);
                      setCopiedRelay(true);
                      toast.success("Cloud Relay passkey copied to clipboard");
                      setTimeout(() => setCopiedRelay(false), 2000);
                    }}
                    className="w-full flex items-center justify-between px-2.5 py-1.5 rounded-md hover:bg-[#f8f9fb] text-xs text-[#1a1a1c] transition-colors cursor-pointer"
                  >
                    <span className="flex items-center gap-2">
                      {copiedRelay ? (
                        <Check className="size-3.5 text-[#0e8345]" />
                      ) : (
                        <Copy className="size-3.5 text-[#868c98]" />
                      )}
                      <span>Copy Relay Passkey</span>
                    </span>
                    <span className="text-[10px] font-mono text-[#868c98]">
                      {copiedRelay ? "Copied" : "ext_live_..."}
                    </span>
                  </button>

                  {isLocalOfflineMode || (!relayStatus?.connected && relayStatus?.status === "stopped") ? (
                    <button
                      disabled={togglingOffline}
                      onClick={async () => {
                        setTogglingOffline(true);
                        soundEngine.playTick();
                        setRelayStatus((prev) => prev ? { ...prev, running: true, status: "connecting", connected: false } : null);
                        try {
                          await setLocalOffline(false);
                          let finalStat: LiveRelayStatus | null = null;
                          for (let i = 0; i < 10; i++) {
                            await new Promise((r) => setTimeout(r, 400));
                            finalStat = await extraDataService.fetchRelayStatus();
                            setRelayStatus(finalStat);
                            if (finalStat.connected) break;
                          }
                          soundEngine.playSuccessChime();
                          if (finalStat?.connected) {
                            toast.success("Cloud Relay connected. Live agent commands enabled.");
                          } else {
                            toast.info("Cloud Relay is reconnecting in the background...");
                          }
                        } catch {
                          toast.error("Failed to connect Cloud Relay");
                        } finally {
                          setTogglingOffline(false);
                          setIsAccountDropdownOpen(false);
                        }
                      }}
                      className="w-full flex items-center justify-between px-2.5 py-1.5 rounded-md hover:bg-[#f8f9fb] text-xs text-[#1677ff] font-medium transition-colors cursor-pointer"
                    >
                      <span className="flex items-center gap-2">
                        <Globe className={`size-3.5 text-[#1677ff] ${togglingOffline ? "animate-spin" : ""}`} />
                        <span>{togglingOffline ? "Connecting Cloud Relay..." : "Switch to Online (Cloud Relay)"}</span>
                      </span>
                      <ChevronRight className="size-3 text-[#1677ff]" />
                    </button>
                  ) : (
                    <button
                      disabled={togglingOffline}
                      onClick={async () => {
                        setTogglingOffline(true);
                        soundEngine.playTick();
                        try {
                          await setLocalOffline(true);
                          const updated = await extraDataService.fetchRelayStatus();
                          setRelayStatus(updated);
                          soundEngine.playSuccessChime();
                          toast.info("Operating in Sovereign Offline Mode. Cloud Relay tunnel closed.");
                        } catch {
                          toast.error("Failed to disconnect Cloud Relay");
                        } finally {
                          setTogglingOffline(false);
                          setIsAccountDropdownOpen(false);
                        }
                      }}
                      className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-md hover:bg-[#f8f9fb] text-xs text-[#525866] hover:text-[#1a1a1c] transition-colors cursor-pointer"
                    >
                      <Laptop className="size-3.5 text-[#868c98]" />
                      <span>{togglingOffline ? "Disconnecting..." : "Switch to Offline Mode"}</span>
                    </button>
                  )}

                  <div className="pt-1 border-t border-[#dfe4eb]">
                    <button
                      onClick={() => {
                        soundEngine.playTick();
                        logout();
                        setIsAccountDropdownOpen(false);
                        toast.success("Disconnected from Extra Cloud");
                      }}
                      className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-md hover:bg-rose-50 text-xs text-rose-600 transition-colors cursor-pointer"
                    >
                      <LogOut className="size-3.5 text-rose-500" />
                      <span>Sign Out</span>
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        ) : isLocalOfflineMode ? (
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                onClick={() => {
                  soundEngine.playTick();
                  openAuthModal();
                }}
                className="h-8 px-2.5 rounded-lg border border-[#dfe4eb] bg-white hover:bg-[#f8f9fb] hover:border-[#ccd2dc] transition-colors duration-150 flex items-center gap-1.5 text-xs text-[#525866] hover:text-[#1a1a1c] cursor-pointer shadow-2xs"
              >
                <Laptop className="size-3.5 text-[#868c98]" />
                <span className="text-xs font-medium">Local Engine</span>
              </button>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="text-xs">
              Operating 100% on-device (~/.extra) • Click to link with Cloud Relay
            </TooltipContent>
          </Tooltip>
        ) : (
          <button
            onClick={() => {
              soundEngine.playTick();
              openAuthModal();
            }}
            className="h-8 px-3 rounded-lg border border-[#1677ff]/30 bg-[#1677ff]/10 text-[#1677ff] hover:bg-[#1677ff] hover:text-white transition-colors duration-150 text-xs font-medium flex items-center gap-1.5 shadow-2xs cursor-pointer"
          >
            <KeyRound className="size-3.5" />
            <span>Connect Cloud</span>
          </button>
        )}

        {/* Emergency Panic Pause: Quiet and only visible when pilot is actually paused */}
        {isPanicActive && (
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                onClick={() => {
                  soundEngine.playSuccessChime();
                  resumePilot();
                }}
                className="h-8 px-2.5 rounded-lg border border-[#f5d99b] bg-[#fffbf0] hover:bg-[#fef3c7] text-[#78350f] transition-colors duration-150 flex items-center gap-1.5 text-xs font-medium cursor-pointer shadow-2xs"
              >
                <span className="size-2 rounded-full bg-[#d97706] animate-pulse" />
                <span className="font-medium text-xs">Pilot Paused</span>
                <kbd className="hidden sm:inline-flex items-center px-1.5 py-0.5 rounded border border-[#f5d99b] bg-white text-[10px] font-mono text-[#b45309]">
                  Esc
                </kbd>
              </button>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="text-xs">
              Pilot Paused: Click or press Esc to resume
            </TooltipContent>
          </Tooltip>
        )}

        {/* Frameless Tauri Desktop Window Controls (hidden in normal window mode) */}
        <DesktopWindowControls />
      </div>
    </header>
  );
}
