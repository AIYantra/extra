import { useState } from "react";
import {
  MessageSquare,
  Layers,
  Clock,
  FolderKanban,
  Cpu,
  MoreHorizontal,
  Settings,
  Shield,
  FileCheck2,
  Terminal,
} from "lucide-react";
import { useEngineStore } from "../../store/useEngineStore";

interface ActivityDockProps {
  currentTab: string;
  onSelectTab: (tab: string) => void;
  onOpenSettings?: () => void;
  onOpenCommandPalette?: () => void;
}

export function ActivityDock({
  currentTab,
  onSelectTab,
  onOpenSettings,
  onOpenCommandPalette,
}: ActivityDockProps) {
  const [showMoreMenu, setShowMoreMenu] = useState(false);
  const [showProfileCard, setShowProfileCard] = useState(false);

  const isServerOnline = useEngineStore((state) => state.isServerOnline);
  const isPanicActive = useEngineStore((state) => state.isPanicActive);
  const telemetry = useEngineStore((state) => state.telemetry);

  const dockItems = [
    {
      id: "chat",
      label: "Chat & Missions",
      icon: MessageSquare,
      shortcut: "1",
    },
    {
      id: "automations",
      label: "Automations & Recipes",
      icon: Layers,
      shortcut: "3",
    },
    {
      id: "history",
      label: "Execution History",
      icon: Clock,
      shortcut: "2",
    },
    {
      id: "projects",
      label: "Projects & Workspaces",
      icon: FolderKanban,
      shortcut: "4",
    },
    {
      id: "dualplane",
      label: "Dual-Plane Bridge (P1+P2)",
      icon: Cpu,
      shortcut: "5",
    },
  ];

  return (
    <aside
      aria-label="Activity Dock"
      className="w-12 bg-[#171717] border-r border-white/[0.08] flex flex-col justify-between items-center py-2 select-none h-full z-40 shrink-0 font-sans"
    >
      {/* Top Application Context Icons */}
      <div className="flex flex-col items-center gap-1.5 w-full">
        {dockItems.map((item) => {
          const Icon = item.icon;
          const isActive =
            currentTab === item.id ||
            (item.id === "chat" && (currentTab === "overview" || currentTab === "chat")) ||
            (item.id === "history" && currentTab === "pilot");

          return (
            <div key={item.id} className="relative group flex items-center justify-center">
              <button
                onClick={() => onSelectTab(item.id === "history" ? "pilot" : item.id)}
                title={`${item.label} (${item.shortcut})`}
                aria-label={item.label}
                className={`w-9 h-9 rounded-lg flex items-center justify-center transition-all cursor-pointer relative ${
                  isActive
                    ? "bg-[#2F2F2F] text-[#ECECEC] shadow-sm"
                    : "text-[#8E8E8E] hover:text-[#ECECEC] hover:bg-white/[0.06]"
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? "text-[#ECECEC]" : "text-[#8E8E8E]"}`} />

                {/* Left Active Indicator Bar */}
                {isActive && (
                  <span className="absolute left-0 top-2 bottom-2 w-0.5 bg-purple-500 rounded-r-full" />
                )}
              </button>

              {/* Hover Tooltip */}
              <div className="absolute left-full ml-2 px-2 py-1 bg-[#252525] border border-white/[0.1] rounded-md text-[11px] text-[#ECECEC] whitespace-nowrap opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity z-50 shadow-xl flex items-center gap-1.5">
                <span>{item.label}</span>
                <span className="text-[9px] text-[#8E8E8E] font-mono px-1 py-0.2 rounded bg-white/[0.08]">
                  {item.shortcut}
                </span>
              </div>
            </div>
          );
        })}

        {/* More Actions Menu Button */}
        <div className="relative">
          <button
            onClick={() => setShowMoreMenu(!showMoreMenu)}
            title="More Options"
            aria-label="More"
            className={`w-9 h-9 rounded-lg flex items-center justify-center transition-all cursor-pointer ${
              showMoreMenu
                ? "bg-[#2F2F2F] text-[#ECECEC]"
                : "text-[#8E8E8E] hover:text-[#ECECEC] hover:bg-white/[0.06]"
            }`}
          >
            <MoreHorizontal className="w-4 h-4" />
          </button>

          {showMoreMenu && (
            <div className="absolute left-full top-0 ml-2 w-48 bg-[#252525] border border-white/[0.1] rounded-lg shadow-2xl py-1 z-50 text-xs">
              <button
                onClick={() => {
                  if (onOpenCommandPalette) onOpenCommandPalette();
                  setShowMoreMenu(false);
                }}
                className="w-full px-3 py-1.5 flex items-center justify-between text-[#ECECEC] hover:bg-[#2F2F2F] text-left transition-colors"
              >
                <span>Quick Search / Run</span>
                <span className="text-[10px] text-[#8E8E8E] font-mono">Ctrl+K</span>
              </button>
              <div className="my-1 border-t border-white/[0.08]" />
              <button
                onClick={() => {
                  onSelectTab("radar");
                  setShowMoreMenu(false);
                }}
                className="w-full px-3 py-1.5 flex items-center gap-2 text-[#ECECEC] hover:bg-[#2F2F2F] text-left transition-colors"
              >
                <Shield className="w-3.5 h-3.5 text-blue-400" />
                <span>Optical Radar</span>
              </button>
              <button
                onClick={() => {
                  onSelectTab("lineage");
                  setShowMoreMenu(false);
                }}
                className="w-full px-3 py-1.5 flex items-center gap-2 text-[#ECECEC] hover:bg-[#2F2F2F] text-left transition-colors"
              >
                <FileCheck2 className="w-3.5 h-3.5 text-emerald-400" />
                <span>Lineage Vault</span>
              </button>
              <button
                onClick={() => {
                  onSelectTab("terminal");
                  setShowMoreMenu(false);
                }}
                className="w-full px-3 py-1.5 flex items-center gap-2 text-[#ECECEC] hover:bg-[#2F2F2F] text-left transition-colors"
              >
                <Terminal className="w-3.5 h-3.5 text-amber-400" />
                <span>Agent Shell</span>
              </button>
              <div className="my-1 border-t border-white/[0.08]" />
              <button
                onClick={() => {
                  if (onOpenSettings) onOpenSettings();
                  else onSelectTab("settings");
                  setShowMoreMenu(false);
                }}
                className="w-full px-3 py-1.5 flex items-center gap-2 text-[#ECECEC] hover:bg-[#2F2F2F] text-left transition-colors"
              >
                <Settings className="w-3.5 h-3.5 text-[#B4B4B4]" />
                <span>Settings</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Bottom Profile & Sovereign Identity */}
      <div className="flex flex-col items-center gap-2 w-full pt-2 border-t border-white/[0.06]">
        {/* User Profile Avatar Pill (C) */}
        <div className="relative group">
          <button
            onClick={() => setShowProfileCard(!showProfileCard)}
            title="Surya Narayan (Operator)"
            aria-label="User Profile"
            className="w-7 h-7 rounded-full bg-gradient-to-tr from-purple-600 to-indigo-500 text-white font-bold text-xs flex items-center justify-center hover:ring-2 hover:ring-purple-400/50 transition-all cursor-pointer shadow-sm"
          >
            C
          </button>

          {/* Profile Popover */}
          {showProfileCard && (
            <div className="absolute left-full bottom-0 ml-2 w-56 bg-[#252525] border border-white/[0.1] rounded-lg shadow-2xl p-3 z-50 text-xs text-[#ECECEC]">
              <div className="flex items-center gap-2.5 pb-2 border-b border-white/[0.08]">
                <div className="w-8 h-8 rounded-full bg-purple-600 text-white font-bold flex items-center justify-center text-sm">
                  C
                </div>
                <div>
                  <div className="font-semibold text-white">Surya Narayan</div>
                  <div className="text-[10px] text-[#8E8E8E]">Sovereign Operator</div>
                </div>
              </div>
              <div className="pt-2 space-y-1 text-[11px] text-[#B4B4B4]">
                <div className="flex justify-between">
                  <span>Engine:</span>
                  <span className="font-mono text-[#ECECEC]">Extra v2.4</span>
                </div>
                <div className="flex justify-between">
                  <span>Active Speed:</span>
                  <span className="text-emerald-400 font-medium">Turbo</span>
                </div>
                <div className="flex justify-between">
                  <span>Target Process:</span>
                  <span className="font-mono text-[#ECECEC] truncate max-w-[100px]">
                    {telemetry.target_proc || "Desktop"}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Sovereign Emblem (Wolf/Fox 🐺) with Live Status Dot */}
        <div className="relative group">
          <button
            onClick={() => onSelectTab("overview")}
            title={
              isPanicActive
                ? "Panic Stopped"
                : isServerOnline
                ? "Engine Connected"
                : "Engine Standby"
            }
            aria-label="Sovereign Extra Status"
            className="w-7 h-7 rounded-lg bg-[#252525] hover:bg-[#2F2F2F] text-sm flex items-center justify-center relative transition-colors cursor-pointer border border-white/[0.06]"
          >
            <span>🐺</span>
            {/* Live Indicator Dot */}
            <span
              className={`absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full border border-[#171717] ${
                isPanicActive
                  ? "bg-rose-500 animate-pulse"
                  : isServerOnline
                  ? "bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.8)]"
                  : "bg-amber-400"
              }`}
            />
          </button>

          <div className="absolute left-full ml-2 px-2 py-1 bg-[#252525] border border-white/[0.1] rounded-md text-[11px] text-[#ECECEC] whitespace-nowrap opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity z-50 shadow-xl">
            {isPanicActive
              ? "Emergency Frozen (Ctrl+Alt+Esc)"
              : isServerOnline
              ? "Sovereign Engine Online"
              : "Standing By"}
          </div>
        </div>
      </div>
    </aside>
  );
}
