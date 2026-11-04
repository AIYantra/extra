import { useState, useEffect } from "react";
import { AlertTriangle, Play } from "lucide-react";
import { DashboardSidebar } from "./DashboardSidebar";
import { DashboardTopBar } from "./DashboardTopBar";
import { DashboardOverview } from "./DashboardOverview";
import { McpToolsView } from "./McpToolsView";
import { TaskSessionsView } from "./TaskSessionsView";
import { ConnectedAppsView } from "./ConnectedAppsView";
import { PluginConnectorsSetupView } from "./PluginConnectorsSetupView";
import { SkillsCatalogView } from "./SkillsCatalogView";
import { ApiKeysAndRelayView } from "./ApiKeysAndRelayView";
import { ReportsAndDoctorView } from "./ReportsAndDoctorView";
import { SettingsView } from "./SettingsView";
import { LivePilotGlass } from "./LivePilotGlass";
import { LineageVaultCard } from "./LineageVaultCard";
import { BrowsersView } from "./BrowsersView";
import { DualPlaneView } from "./DualPlaneView";
import { OpticalRadarView } from "./OpticalRadarView";
import { TerminalView } from "./TerminalView";
import { ProfileView } from "./ProfileView";
import { AboutView } from "./AboutView";
import { CommandPaletteModal } from "../CommandPaletteModal";
import { PanicSafetyModal } from "./PanicSafetyModal";
import { toast } from "sonner";
import { useEngineStore } from "../../store/useEngineStore";
import { soundEngine } from "../../utils/sound";

export function DashboardLayout() {
  const [currentTab, setCurrentTab] = useState<string>("overview");
  const [collapsed, setCollapsed] = useState<boolean>(false);
  const [isCommandOpen, setIsCommandOpen] = useState<boolean>(false);
  const [isPanicModalOpen, setIsPanicModalOpen] = useState<boolean>(false);

  const isPanicActive = useEngineStore((state) => state.isPanicActive);
  const panicStop = useEngineStore((state) => state.panicStop);
  const resumePilot = useEngineStore((state) => state.resumePilot);

  // Initialize Tauri IPC event listener on mount
  useEffect(() => {
    let unlistenFn: (() => void) | undefined;
    useEngineStore.getState().init().then((fn) => {
      unlistenFn = fn;
    });

    return () => {
      if (unlistenFn) {
        unlistenFn();
      }
    };
  }, []);

  // Global keyboard shortcuts:
  // 1. Ctrl+K / Cmd+K to open Command Palette
  // 2. Ctrl+Alt+Esc for Emergency Hardware Panic Stop
  // 3. 1-9 Numeric Navigation (when not typing in inputs)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // 1a. Ctrl+Alt+Esc Emergency Hardware Panic Stop Hook
      if (e.ctrlKey && e.altKey && (e.key === "Escape" || e.code === "Escape")) {
        e.preventDefault();
        soundEngine.playPanicAlert();
        toast.error("Emergency Hardware Panic Stop Active — Actuators Severed", { duration: 5000 });
        panicStop();
        return;
      }

      // 1b. Contextual Escape Key: If mission is executing, immediate 1-key abort
      if ((e.key === "Escape" || e.code === "Escape") && !e.ctrlKey && !e.altKey && !e.metaKey) {
        const state = useEngineStore.getState();
        if (state.isExecuting) {
          e.preventDefault();
          soundEngine.playPanicAlert();
          toast.error("Mission Aborted via Escape — Actuators Severed", { duration: 4000 });
          panicStop();
          return;
        }
      }

      // Ctrl+K / Cmd+K Command Palette Hook
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        soundEngine.playTick();
        setIsCommandOpen((prev) => !prev);
        return;
      }

      // 1-9 Numeric Navigation Keys (when not typing inside inputs)
      const target = e.target as HTMLElement;
      const isInput =
        target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.isContentEditable);

      if (!isInput && !e.ctrlKey && !e.metaKey && !e.altKey && !isCommandOpen) {
        const tabMap: Record<string, string> = {
          "1": "overview",
          "2": "tools",
          "3": "sessions",
          "4": "apps",
          "5": "skills",
          "6": "keys",
          "7": "telemetry",
          "8": "settings",
          "9": "about",
        };
        if (tabMap[e.key]) {
          e.preventDefault();
          setCurrentTab(tabMap[e.key]);
          soundEngine.playTick();
        }
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [panicStop, isCommandOpen]);

  const renderActiveView = () => {
    switch (currentTab) {
      case "tools":
        return <McpToolsView />;
      case "sessions":
      case "automations":
        return <TaskSessionsView />;
      case "apps":
        return <ConnectedAppsView onNavigateTab={setCurrentTab} />;
      case "connectors":
      case "plugins":
        return <PluginConnectorsSetupView />;
      case "skills":
        return <SkillsCatalogView />;
      case "keys":
        return <ApiKeysAndRelayView />;
      case "telemetry":
        return <ReportsAndDoctorView />;
      case "settings":
        return <SettingsView />;
      case "pilot":
        return <LivePilotGlass />;
      case "browsers":
        return <BrowsersView />;
      case "dualplane":
        return <DualPlaneView />;
      case "radar":
        return <OpticalRadarView />;
      case "terminal":
        return <TerminalView />;
      case "lineage":
        return <LineageVaultCard />;
      case "profile":
        return <ProfileView />;
      case "about":
        return <AboutView />;
      case "overview":
      default:
        return <DashboardOverview onNavigateTab={setCurrentTab} />;
    }
  };

  return (
    <div className="fixed inset-0 h-screen w-screen max-h-screen max-w-screen overflow-hidden bg-station-canvas text-station-text-primary flex flex-row font-sans antialiased selection:bg-primary/20 selection:text-station-text-primary transition-colors duration-150">
      {/* App Sidebar */}
      <DashboardSidebar
        currentTab={currentTab}
        onSelectTab={setCurrentTab}
        collapsed={collapsed}
        onToggleCollapsed={() => setCollapsed(!collapsed)}
      />

      {/* Main Content Area */}
      <div className="flex-1 h-full flex flex-col min-w-0 overflow-hidden bg-station-canvas transition-colors duration-150">
        {/* Emergency Pause Active Banner (Unslopped & Crafted) */}
        {isPanicActive && (
          <div className="shrink-0 bg-[#fffbf0] dark:bg-[#1a1714] border-b border-[#f3d99e] dark:border-[#382b1d] px-4 sm:px-6 py-2.5 flex items-center justify-between gap-3 text-xs z-40 transition-colors duration-150 shadow-2xs">
            <div className="flex items-center gap-2.5 min-w-0">
              <span className="p-1 rounded-md bg-[#fef3c7] dark:bg-amber-950/60 text-[#b45309] dark:text-amber-400 border border-[#fde68a] dark:border-amber-800/40 shrink-0">
                <AlertTriangle className="w-3.5 h-3.5" />
              </span>
              <div className="min-w-0 flex items-center gap-1.5">
                <span className="font-semibold text-[#78350f] dark:text-amber-100 tracking-tight">
                  Extra is paused
                </span>
                <kbd className="inline-flex items-center px-1.5 py-0.5 rounded border border-[#f5d99b] dark:border-amber-800/60 bg-white dark:bg-zinc-800 text-[10px] font-mono text-[#b45309] dark:text-amber-300 shadow-2xs">
                  Esc
                </kbd>
                <span className="text-[#92400e]/80 dark:text-amber-300/70 hidden md:inline font-normal ml-1">
                  — All desktop actions are paused. You are in sovereign control.
                </span>
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <button
                type="button"
                onClick={() => setIsPanicModalOpen(true)}
                className="h-7 px-2.5 text-xs font-medium text-[#78350f] dark:text-amber-200 bg-white/80 dark:bg-zinc-900/80 hover:bg-white dark:hover:bg-zinc-800 border border-[#f5d99b] dark:border-amber-800/50 rounded-md transition-colors duration-150 cursor-pointer shadow-2xs"
              >
                Inspect State
              </button>
              <button
                type="button"
                onClick={() => {
                  soundEngine.playSuccessChime();
                  resumePilot();
                }}
                className="h-7 px-3 text-xs font-medium bg-[#0e8345] hover:bg-[#0b6b37] text-white rounded-md transition-colors duration-150 flex items-center gap-1.5 cursor-pointer shadow-2xs"
              >
                <Play className="w-3 h-3 fill-current" />
                <span>Resume</span>
              </button>
            </div>
          </div>
        )}

        <div className="shrink-0 z-20">
          <DashboardTopBar
            currentTab={currentTab}
            onOpenCommandPalette={() => setIsCommandOpen(true)}
            onNavigateTab={setCurrentTab}
          />
        </div>

        <main className="flex-1 min-h-0 overflow-y-auto w-full">
          <div className="p-4 sm:p-6 lg:p-8 max-w-[1380px] w-full mx-auto">
            {renderActiveView()}
          </div>
        </main>
      </div>

      {/* Hardware Panic Safety Modal */}
      <PanicSafetyModal
        isOpen={isPanicModalOpen}
        onClose={() => setIsPanicModalOpen(false)}
      />

      {/* Command Palette Modal */}
      <CommandPaletteModal
        isOpen={isCommandOpen}
        onClose={() => setIsCommandOpen(false)}
        onRunAction={(action) => {
          console.log("Action triggered:", action);
          if (action.includes("pilot")) setCurrentTab("pilot");
          else if (action.includes("connectors") || action.includes("plugin") || action.includes("chatgpt") || action.includes("claude")) setCurrentTab("connectors");
          else if (action.includes("settings")) setCurrentTab("settings");
          else if (action.includes("lineage")) setCurrentTab("lineage");
          else if (action.includes("macro") || action.includes("automation")) setCurrentTab("automations");
        }}
      />
    </div>
  );
}
