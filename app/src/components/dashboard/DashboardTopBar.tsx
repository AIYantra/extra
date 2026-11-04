import { useState, useEffect, useRef } from "react";
import {
  Search,
  OctagonAlert,
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
  Sparkles,
} from "lucide-react";
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";
import { DesktopWindowControls } from "./DesktopWindowControls";
import { ExtraAvatar } from "../ExtraAvatar";
import { useEngineStore } from "../../store/useEngineStore";
import { useAuthStore } from "../../store/useAuthStore";
import { useOnboardingStore } from "../../store/useOnboardingStore";
import { soundEngine } from "../../utils/sound";
import { toast } from "sonner";
import { telemetryClient } from "../../services/telemetryClient";

interface DashboardTopBarProps {
  currentTab?: string;
  onOpenCommandPalette: () => void;
  onLaunchNewPilot?: () => void;
  onNavigateTab?: (tab: string) => void;
}

const TAB_TITLES: Record<string, string> = {
  overview: "Dashboard",
  tools: "MCP Tools",
  sessions: "Task Sessions",
  apps: "Connected Apps",
  skills: "Skills & Memory Graph",
  keys: "API Keys & Relay",
  telemetry: "Reports & Doctor",
  settings: "Settings",
  about: "About",
};

export function DashboardTopBar({
  currentTab = "overview",
  onOpenCommandPalette,
  onNavigateTab,
}: DashboardTopBarProps) {
  const isServerOnline = useEngineStore((state) => state.isServerOnline);
  const isPanicActive = useEngineStore((state) => state.isPanicActive);
  const panicStop = useEngineStore((state) => state.panicStop);
  const resumePilot = useEngineStore((state) => state.resumePilot);

  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const isLocalOfflineMode = useAuthStore((state) => state.isLocalOfflineMode);
  const user = useAuthStore((state) => state.user);
  const relayToken = useAuthStore((state) => state.relayToken);
  const openAuthModal = useAuthStore((state) => state.openAuthModal);
  const logout = useAuthStore((state) => state.logout);
  const setLocalOffline = useAuthStore((state) => state.setLocalOffline);

  const [isMac, setIsMac] = useState(false);
  const [isAccountDropdownOpen, setIsAccountDropdownOpen] = useState(false);
  const [copiedRelay, setCopiedRelay] = useState(false);
  const [restartingEngine, setRestartingEngine] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

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

        {/* Engine Daemon Health Status — Offline pill restarts the daemon */}
        <Tooltip>
          <TooltipTrigger asChild>
            {isServerOnline ? (
              <div className="hidden sm:inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-[#f8f9fb] border border-[#dfe4eb] hover:border-[#ccd2dc] transition-colors duration-150 cursor-help">
                <span className="size-1.5 rounded-full shrink-0 bg-[#0e8345]" />
                <span className="text-[11px] font-mono text-[#525866] tabular-nums">
                  Port 8000
                </span>
              </div>
            ) : (
              <button
                onClick={handleRestartEngine}
                disabled={restartingEngine}
                className="hidden sm:inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-[#fff8e6] border border-[#f5dfa8] hover:border-[#e3b008] transition-colors duration-150 cursor-pointer disabled:opacity-60"
              >
                <span className="size-1.5 rounded-full shrink-0 bg-amber-500" />
                <span className="text-[11px] font-mono text-[#525866] tabular-nums">
                  {restartingEngine ? "Restarting..." : "Offline — Restart"}
                </span>
                <RefreshCw
                  className={`size-3 text-[#b7791f] ${restartingEngine ? "animate-spin" : ""}`}
                />
              </button>
            )}
          </TooltipTrigger>
          <TooltipContent side="bottom" className="text-xs">
            {isServerOnline
              ? "Extra Sovereign Engine Daemon active at http://127.0.0.1:8000"
              : "Engine daemon unreachable — click to restart it with this app's token"}
          </TooltipContent>
        </Tooltip>
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
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#f8f9fb] text-[#525866] border border-[#dfe4eb]">
                {user.plan || "Free"}
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
                    <span className="inline-flex items-center gap-1 font-medium text-[#0e8345]">
                      <span className="size-1.5 rounded-full bg-[#0e8345]" />
                      Active (ap-south-1)
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-[#868c98]">Paired Workstation</span>
                    <span className="font-mono text-[#1a1a1c] text-[10px] truncate max-w-[130px]">
                      Windows 11
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

                  <button
                    onClick={() => {
                      soundEngine.playTick();
                      setLocalOffline(true);
                      setIsAccountDropdownOpen(false);
                      toast.info("Operating in Sovereign Offline Mode (~/.extra)");
                    }}
                    className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-md hover:bg-[#f8f9fb] text-xs text-[#525866] hover:text-[#1a1a1c] transition-colors cursor-pointer"
                  >
                    <Laptop className="size-3.5 text-[#868c98]" />
                    <span>Switch to Offline Mode</span>
                  </button>

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

        {/* First Flight Onboarding Setup Trigger */}
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              onClick={() => {
                soundEngine.playTick();
                useOnboardingStore.getState().openOnboarding("welcome");
              }}
              className="h-8 px-2.5 rounded-lg border border-[#1677ff]/30 bg-[#1677ff]/5 hover:bg-[#1677ff]/10 text-[#1677ff] transition-colors duration-150 flex items-center gap-1.5 text-xs font-semibold cursor-pointer shadow-2xs"
            >
              <Sparkles className="size-3.5 text-[#1677ff]" />
              <span className="hidden sm:inline">First Flight</span>
            </button>
          </TooltipTrigger>
          <TooltipContent side="bottom" className="text-xs">
            Open the 1-click AI Connect &amp; Magic Test Setup Wizard
          </TooltipContent>
        </Tooltip>

        {/* Emergency Panic Pause / Resume Indicator (Unslopped & Deduplicated) */}
        {!isPanicActive ? (
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                onClick={() => {
                  soundEngine.playPanicAlert();
                  panicStop();
                }}
                className="h-8 px-2.5 rounded-lg border border-[#dfe4eb] bg-white hover:bg-[#f8f9fb] hover:border-[#ccd2dc] text-[#525866] hover:text-[#1a1a1c] transition-colors duration-150 flex items-center gap-1.5 text-xs font-medium cursor-pointer shadow-2xs"
              >
                <OctagonAlert className="size-3.5 text-[#868c98] shrink-0" />
                <span className="hidden sm:inline font-medium text-xs">Pause</span>
                <kbd className="hidden md:inline-flex items-center px-1.5 py-0.5 rounded border border-[#dfe4eb] bg-[#f8f9fb] text-[10px] font-mono text-[#868c98]">
                  Esc
                </kbd>
              </button>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="text-xs">
              Emergency Stop: Instantly freezes desktop automation (Press Esc)
            </TooltipContent>
          </Tooltip>
        ) : (
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                onClick={() => {
                  soundEngine.playSuccessChime();
                  resumePilot();
                }}
                className="h-8 px-2.5 rounded-lg border border-[#f5d99b] dark:border-amber-800/60 bg-[#fffbf0] hover:bg-[#fef3c7] dark:bg-[#1a1714] dark:hover:bg-[#251d16] text-[#78350f] dark:text-amber-200 transition-colors duration-150 flex items-center gap-1.5 text-xs font-medium cursor-pointer shadow-2xs"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-[#d97706] animate-pulse" />
                <span className="font-medium text-xs">Paused</span>
                <kbd className="hidden sm:inline-flex items-center px-1 py-0.2 rounded border border-[#f5d99b] dark:border-amber-800/60 bg-white dark:bg-zinc-800 text-[10px] font-mono text-[#b45309] dark:text-amber-300">
                  Esc
                </kbd>
              </button>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="text-xs">
              Paused: Click or press Esc to resume pilot
            </TooltipContent>
          </Tooltip>
        )}

        {/* Frameless Tauri Desktop Window Controls (hidden in normal window mode) */}
        <DesktopWindowControls />
      </div>
    </header>
  );
}
