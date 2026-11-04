import { useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  Bell,
  Search,
  SquarePen,
  Pin,
  Folder,
  FolderOpen,
  MessageSquare,
  MoreHorizontal,
  Check,
  Zap,
  Shield,
  Gauge,
} from "lucide-react";
import { useEngineStore } from "../../store/useEngineStore";
import type { SpeedMode } from "../../services/ipc";
import { SPEED_MODE_META } from "../../utils/speedModes";

interface ChatGPTSidebarProps {
  collapsed: boolean;
  onToggleCollapsed: () => void;
  onNewChat: () => void;
  onSelectChat: (chatId: string, title?: string) => void;
  activeChatId?: string;
  onOpenCommandPalette: () => void;
  onSelectTab: (tab: string) => void;
}

export function ChatGPTSidebar({
  collapsed,
  onNewChat,
  onSelectChat,
  activeChatId = "new",
  onOpenCommandPalette,
  onSelectTab,
}: ChatGPTSidebarProps) {
  const speedMode = useEngineStore((state) => state.speedMode);
  const setSpeedMode = useEngineStore((state) => state.setSpeedMode);
  const runs = useEngineStore((state) => state.runs);

  const [modeDropdownOpen, setModeDropdownOpen] = useState(false);
  const [pinnedOpen, setPinnedOpen] = useState(true);
  const [projectsOpen, setProjectsOpen] = useState(true);
  const [openFolders, setOpenFolders] = useState<Record<string, boolean>>({
    playground: true,
    workflows: false,
    petgrooming: false,
  });

  // Mock pinned and project items
  const pinnedItems = [
    { id: "pin-1", title: "YantraOS Overview", icon: MessageSquare, type: "chat" },
    { id: "pin-2", title: "Extra Engine Repo", icon: Folder, type: "project" },
    { id: "pin-3", title: "yantraOS Sovereign OS", icon: Folder, type: "project" },
  ];

  const projects = [
    {
      id: "playground",
      name: "Playground",
      items: [
        { id: "pg-1", title: "Calculate and type in Calc" },
        { id: "pg-2", title: "Notepad draft generator" },
      ],
    },
    {
      id: "workflows",
      name: "Workflows",
      items: [
        { id: "wf-1", title: "Market Data Extraction" },
        { id: "wf-2", title: "Q3 Ledger Reconciliation" },
      ],
    },
    {
      id: "petgrooming",
      name: "PetGroomingPalace",
      items: [{ id: "pgp-1", title: "Client intake spreadsheet" }],
    },
  ];

  // Recents from store runs or defaults
  const recentItems =
    runs.length > 0
      ? runs.slice(0, 10).map((r) => ({
          id: r.id,
          title: r.title || `Mission ${r.id.slice(0, 8)}`,
          status: r.status,
        }))
      : [
          { id: "rec-1", title: "Calculate 245.12/383.29 in Calc", status: "completed" },
          { id: "rec-2", title: "Reconcile Q3 Balance Sheets", status: "completed" },
          { id: "rec-3", title: "Generate Paint System Architecture", status: "completed" },
          { id: "rec-4", title: "Automate Chrome Browser Research", status: "completed" },
        ];

  const toggleFolder = (folderId: string) => {
    setOpenFolders((prev) => ({
      ...prev,
      [folderId]: !prev[folderId],
    }));
  };

  const handleSpeedModeChange = (mode: SpeedMode) => {
    setSpeedMode(mode);
    setModeDropdownOpen(false);
  };

  return (
    <aside
      aria-label="Navigation Drawer"
      className={`bg-[#171717] border-r border-white/[0.08] flex flex-col justify-between select-none h-full transition-[width,opacity] duration-200 ease-in-out shrink-0 font-sans z-30 ${
        collapsed ? "w-0 opacity-0 overflow-hidden border-r-0 pointer-events-none" : "w-[260px] opacity-100"
      }`}
    >
      <div className="flex flex-col min-w-0 flex-1 overflow-hidden">
        {/* Top Header: Extra v2.4 Dropdown + Bell + Search */}
        <div className="h-12 px-3 flex items-center justify-between border-b border-white/[0.06] shrink-0">
          {/* Engine & Speed Mode Dropdown */}
          <div className="relative">
            <button
              onClick={() => setModeDropdownOpen(!modeDropdownOpen)}
              className="flex items-center gap-1.5 px-2 py-1 rounded-md hover:bg-white/[0.06] text-[#ECECEC] transition-colors cursor-pointer group"
            >
              <span className="font-semibold text-xs tracking-tight">Extra v2.4</span>
              <span
                className={`text-[9px] px-1 py-0.2 rounded font-medium ${
                  speedMode === "turbo"
                    ? "bg-purple-900/50 text-purple-300 border border-purple-500/30"
                    : speedMode === "smart"
                    ? "bg-emerald-900/50 text-emerald-300 border border-emerald-500/30"
                    : "bg-white/[0.06] text-[#B4B4B4]"
                }`}
              >
                {SPEED_MODE_META[speedMode].label.toUpperCase()}
              </span>
              <ChevronDown className="w-3 h-3 text-[#8E8E8E] group-hover:text-[#ECECEC] transition-transform" />
            </button>

            {/* Mode Selector Dropdown */}
            {modeDropdownOpen && (
              <div className="absolute left-0 top-full mt-1 w-52 bg-[#252525] border border-white/[0.1] rounded-lg shadow-2xl p-1 z-50 text-xs">
                <div className="px-2 py-1 text-[10px] text-[#8E8E8E] uppercase tracking-wider font-mono">
                  Execution Mode
                </div>
                <button
                  onClick={() => handleSpeedModeChange("turbo")}
                  className="w-full px-2.5 py-1.5 rounded flex items-center justify-between hover:bg-[#2F2F2F] text-[#ECECEC] cursor-pointer"
                >
                  <div className="flex items-center gap-2">
                    <Zap className="w-3.5 h-3.5 text-purple-400" />
                    <div>
                      <div className="font-medium text-xs">{SPEED_MODE_META.turbo.label}</div>
                      <div className="text-[10px] text-[#8E8E8E]">{SPEED_MODE_META.turbo.shortDesc}</div>
                    </div>
                  </div>
                  {speedMode === "turbo" && <Check className="w-3.5 h-3.5 text-purple-400" />}
                </button>
                <button
                  onClick={() => handleSpeedModeChange("balanced")}
                  className="w-full px-2.5 py-1.5 rounded flex items-center justify-between hover:bg-[#2F2F2F] text-[#ECECEC] cursor-pointer"
                >
                  <div className="flex items-center gap-2">
                    <Gauge className="w-3.5 h-3.5 text-blue-400" />
                    <div>
                      <div className="font-medium text-xs">{SPEED_MODE_META.balanced.label}</div>
                      <div className="text-[10px] text-[#8E8E8E]">{SPEED_MODE_META.balanced.shortDesc}</div>
                    </div>
                  </div>
                  {speedMode === "balanced" && <Check className="w-3.5 h-3.5 text-blue-400" />}
                </button>
                <button
                  onClick={() => handleSpeedModeChange("smart")}
                  className="w-full px-2.5 py-1.5 rounded flex items-center justify-between hover:bg-[#2F2F2F] text-[#ECECEC] cursor-pointer"
                >
                  <div className="flex items-center gap-2">
                    <Shield className="w-3.5 h-3.5 text-emerald-400" />
                    <div>
                      <div className="font-medium text-xs">{SPEED_MODE_META.smart.label}</div>
                      <div className="text-[10px] text-[#8E8E8E]">{SPEED_MODE_META.smart.shortDesc}</div>
                    </div>
                  </div>
                  {speedMode === "smart" && <Check className="w-3.5 h-3.5 text-emerald-400" />}
                </button>
              </div>
            )}
          </div>

          {/* Header Quick Actions */}
          <div className="flex items-center gap-0.5">
            <button
              onClick={() => onSelectTab("overview")}
              title="Notifications"
              className="w-7 h-7 flex items-center justify-center rounded-md text-[#8E8E8E] hover:text-[#ECECEC] hover:bg-white/[0.06] transition-colors cursor-pointer"
            >
              <Bell className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={onOpenCommandPalette}
              title="Quick Search (Ctrl+K)"
              className="w-7 h-7 flex items-center justify-center rounded-md text-[#8E8E8E] hover:text-[#ECECEC] hover:bg-white/[0.06] transition-colors cursor-pointer"
            >
              <Search className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Primary Action: New Chat Button */}
        <div className="p-3 pb-2 shrink-0">
          <button
            onClick={onNewChat}
            className="w-full h-9 px-3 rounded-lg bg-[#212121] hover:bg-[#2A2A2A] border border-white/[0.08] hover:border-white/[0.14] text-[#ECECEC] flex items-center justify-between transition-all cursor-pointer shadow-sm group"
          >
            <div className="flex items-center gap-2 font-medium text-xs">
              <SquarePen className="w-4 h-4 text-purple-400 group-hover:text-purple-300 transition-colors" />
              <span>New chat</span>
            </div>
            <span className="text-[10px] text-[#8E8E8E] font-mono group-hover:text-[#B4B4B4]">
              Ctrl+Shift+O
            </span>
          </button>
        </div>

        {/* Scrollable Navigation Tree */}
        <div className="flex-1 overflow-y-auto px-2 space-y-4 py-1">
          {/* PINNED SECTION */}
          <div>
            <button
              onClick={() => setPinnedOpen(!pinnedOpen)}
              className="w-full flex items-center justify-between px-2 py-1 text-[10px] font-mono uppercase tracking-wider text-[#8E8E8E] hover:text-[#ECECEC] transition-colors cursor-pointer"
            >
              <span className="flex items-center gap-1.5 font-semibold">
                <Pin className="w-3 h-3 text-[#8E8E8E]" />
                PINNED
              </span>
              {pinnedOpen ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            </button>

            {pinnedOpen && (
              <div className="mt-1 space-y-0.5">
                {pinnedItems.map((item) => {
                  const Icon = item.icon;
                  return (
                    <button
                      key={item.id}
                      onClick={() => onSelectChat(item.id, item.title)}
                      className="w-full h-7.5 px-2 rounded-md flex items-center gap-2 text-xs text-[#B4B4B4] hover:text-[#ECECEC] hover:bg-[#2A2A2A] transition-colors text-left truncate cursor-pointer group"
                    >
                      <Icon className="w-3.5 h-3.5 text-[#8E8E8E] group-hover:text-[#ECECEC] shrink-0" />
                      <span className="truncate flex-1">{item.title}</span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* PROJECTS SECTION */}
          <div>
            <button
              onClick={() => setProjectsOpen(!projectsOpen)}
              className="w-full flex items-center justify-between px-2 py-1 text-[10px] font-mono uppercase tracking-wider text-[#8E8E8E] hover:text-[#ECECEC] transition-colors cursor-pointer"
            >
              <span className="flex items-center gap-1.5 font-semibold">
                <Folder className="w-3 h-3 text-[#8E8E8E]" />
                PROJECTS
              </span>
              {projectsOpen ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            </button>

            {projectsOpen && (
              <div className="mt-1 space-y-1">
                {projects.map((proj) => {
                  const isOpen = openFolders[proj.id];
                  return (
                    <div key={proj.id} className="space-y-0.5">
                      <button
                        onClick={() => toggleFolder(proj.id)}
                        className="w-full h-7 px-2 rounded-md flex items-center justify-between text-xs font-medium text-[#ECECEC] hover:bg-[#2A2A2A] transition-colors text-left cursor-pointer"
                      >
                        <div className="flex items-center gap-2 truncate">
                          {isOpen ? (
                            <FolderOpen className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                          ) : (
                            <Folder className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                          )}
                          <span className="truncate">{proj.name}</span>
                        </div>
                        {isOpen ? (
                          <ChevronDown className="w-3 h-3 text-[#8E8E8E]" />
                        ) : (
                          <ChevronRight className="w-3 h-3 text-[#8E8E8E]" />
                        )}
                      </button>

                      {isOpen && (
                        <div className="pl-4 space-y-0.5 border-l border-white/[0.06] ml-3.5">
                          {proj.items.map((subItem) => (
                            <button
                              key={subItem.id}
                              onClick={() => onSelectChat(subItem.id, subItem.title)}
                              className="w-full h-7 px-2 rounded-md flex items-center gap-2 text-[11.5px] text-[#B4B4B4] hover:text-[#ECECEC] hover:bg-[#2A2A2A] transition-colors text-left truncate cursor-pointer"
                            >
                              <span className="w-1 h-1 rounded-full bg-[#8E8E8E] shrink-0" />
                              <span className="truncate">{subItem.title}</span>
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* RECENTS SECTION */}
          <div>
            <div className="px-2 py-1 text-[10px] font-mono font-semibold uppercase tracking-wider text-[#8E8E8E]">
              RECENTS
            </div>
            <div className="mt-1 space-y-0.5">
              {recentItems.map((item) => {
                const isActive = activeChatId === item.id;
                return (
                  <div
                    key={item.id}
                    className={`group w-full h-7.5 px-2 rounded-md flex items-center justify-between text-xs transition-colors cursor-pointer ${
                      isActive
                        ? "bg-[#2F2F2F] text-[#ECECEC] font-medium"
                        : "text-[#B4B4B4] hover:text-[#ECECEC] hover:bg-[#2A2A2A]"
                    }`}
                  >
                    <button
                      onClick={() => onSelectChat(item.id, item.title)}
                      className="flex-1 min-w-0 text-left truncate flex items-center gap-1.5"
                    >
                      <MessageSquare className="w-3 h-3 text-[#8E8E8E] group-hover:text-[#ECECEC] shrink-0" />
                      <span className="truncate">{item.title}</span>
                    </button>

                    <button
                      title="More actions"
                      onClick={(e) => {
                        e.stopPropagation();
                      }}
                      className="opacity-0 group-hover:opacity-100 p-1 text-[#8E8E8E] hover:text-[#ECECEC] transition-opacity cursor-pointer rounded"
                    >
                      <MoreHorizontal className="w-3 h-3" />
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
