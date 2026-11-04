import { useState, useEffect, useRef } from "react";
import {
  ArrowLeft,
  ArrowRight,
  PanelLeft,
  Minus,
  Square,
  X,
  ExternalLink,
  Keyboard,
  ShieldAlert,
  Info,
  Layers,
  FileCheck2,
  Monitor,
  Plus,
} from "lucide-react";
import { checkIsTauri } from "../../services/ipc";

interface NativeTitleBarProps {
  sidebarCollapsed: boolean;
  onToggleSidebar: () => void;
  canGoBack?: boolean;
  canGoForward?: boolean;
  onNavigateBack?: () => void;
  onNavigateForward?: () => void;
  onSelectTab: (tab: string) => void;
  onNewChat: () => void;
  onOpenShortcuts?: () => void;
  onOpenCommandPalette?: () => void;
}

type MenuKey = "file" | "edit" | "view" | "help" | null;

export function NativeTitleBar({
  sidebarCollapsed,
  onToggleSidebar,
  canGoBack = false,
  canGoForward = false,
  onNavigateBack,
  onNavigateForward,
  onSelectTab,
  onNewChat,
  onOpenShortcuts,
  onOpenCommandPalette,
}: NativeTitleBarProps) {
  const [activeMenu, setActiveMenu] = useState<MenuKey>(null);
  const [isTauriApp, setIsTauriApp] = useState(false);
  const menuContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setIsTauriApp(checkIsTauri());
  }, []);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        menuContainerRef.current &&
        !menuContainerRef.current.contains(e.target as Node)
      ) {
        setActiveMenu(null);
      }
    };
    if (activeMenu) {
      window.addEventListener("mousedown", handleClickOutside);
    }
    return () => window.removeEventListener("mousedown", handleClickOutside);
  }, [activeMenu]);

  // Window Controls
  const handleMinimize = async () => {
    if (isTauriApp) {
      try {
        const { getCurrentWindow } = await import("@tauri-apps/api/window");
        await getCurrentWindow().minimize();
      } catch (err) {
        console.warn("[TitleBar] Minimize failed:", err);
      }
    }
  };

  const handleToggleMaximize = async () => {
    if (isTauriApp) {
      try {
        const { getCurrentWindow } = await import("@tauri-apps/api/window");
        await getCurrentWindow().toggleMaximize();
      } catch (err) {
        console.warn("[TitleBar] Toggle maximize failed:", err);
      }
    }
  };

  const handleClose = async () => {
    if (isTauriApp) {
      try {
        const { getCurrentWindow } = await import("@tauri-apps/api/window");
        await getCurrentWindow().close();
      } catch (err) {
        console.warn("[TitleBar] Close failed:", err);
      }
    }
  };

  const toggleMenu = (key: MenuKey) => {
    setActiveMenu((prev) => (prev === key ? null : key));
  };

  const handleMenuHover = (key: MenuKey) => {
    if (activeMenu !== null) {
      setActiveMenu(key);
    }
  };

  return (
    <header
      data-tauri-drag-region
      className="h-9 bg-[#171717] border-b border-white/[0.08] flex items-center justify-between px-2 text-[#ECECEC] text-xs select-none sticky top-0 z-50 shrink-0 font-sans"
    >
      {/* Left: Navigation history, Sidebar collapse toggle & Application menus */}
      <div className="flex items-center gap-1 min-w-0" ref={menuContainerRef}>
        {/* Navigation Buttons */}
        <div className="flex items-center gap-0.5 mr-1" data-tauri-drag-region="false">
          <button
            onClick={onNavigateBack}
            disabled={!canGoBack}
            title="Back (Alt+Left)"
            aria-label="Back"
            className="w-7 h-7 flex items-center justify-center rounded text-[#8E8E8E] hover:text-[#ECECEC] hover:bg-white/[0.08] disabled:opacity-30 disabled:hover:bg-transparent disabled:hover:text-[#8E8E8E] transition-colors cursor-pointer disabled:cursor-not-allowed"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={onNavigateForward}
            disabled={!canGoForward}
            title="Forward (Alt+Right)"
            aria-label="Forward"
            className="w-7 h-7 flex items-center justify-center rounded text-[#8E8E8E] hover:text-[#ECECEC] hover:bg-white/[0.08] disabled:opacity-30 disabled:hover:bg-transparent disabled:hover:text-[#8E8E8E] transition-colors cursor-pointer disabled:cursor-not-allowed"
          >
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={onToggleSidebar}
            title={sidebarCollapsed ? "Open sidebar (Ctrl+Shift+S)" : "Close sidebar (Ctrl+Shift+S)"}
            aria-label="Toggle sidebar"
            className={`w-7 h-7 flex items-center justify-center rounded transition-colors cursor-pointer ${
              sidebarCollapsed
                ? "text-[#8E8E8E] hover:text-[#ECECEC] hover:bg-white/[0.08]"
                : "text-[#ECECEC] bg-white/[0.06] hover:bg-white/[0.1]"
            }`}
          >
            <PanelLeft className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Desktop App Menu Items */}
        <div className="flex items-center space-x-0.5 relative text-xs" data-tauri-drag-region="false">
          {/* File Menu */}
          <div className="relative">
            <button
              onClick={() => toggleMenu("file")}
              onMouseEnter={() => handleMenuHover("file")}
              className={`px-2 py-1 rounded text-[11.5px] font-medium transition-colors cursor-pointer ${
                activeMenu === "file"
                  ? "bg-white/[0.12] text-[#ECECEC]"
                  : "text-[#B4B4B4] hover:text-[#ECECEC] hover:bg-white/[0.06]"
              }`}
            >
              File
            </button>
            {activeMenu === "file" && (
              <div className="absolute left-0 top-full mt-1 w-56 bg-[#252525] border border-white/[0.1] rounded-lg shadow-2xl py-1 z-50 text-xs">
                <button
                  onClick={() => {
                    onNewChat();
                    setActiveMenu(null);
                  }}
                  className="w-full px-3 py-1.5 flex items-center justify-between text-[#ECECEC] hover:bg-[#2F2F2F] transition-colors text-left"
                >
                  <span className="flex items-center gap-2">
                    <Plus className="w-3.5 h-3.5 text-purple-400" />
                    New chat
                  </span>
                  <span className="text-[10px] text-[#8E8E8E]">Ctrl+Shift+O</span>
                </button>
                <button
                  onClick={() => {
                    if (onOpenCommandPalette) onOpenCommandPalette();
                    setActiveMenu(null);
                  }}
                  className="w-full px-3 py-1.5 flex items-center justify-between text-[#ECECEC] hover:bg-[#2F2F2F] transition-colors text-left"
                >
                  <span>Quick Search / Run</span>
                  <span className="text-[10px] text-[#8E8E8E]">Ctrl+K</span>
                </button>
                <div className="my-1 border-t border-white/[0.08]" />
                <button
                  onClick={() => {
                    onSelectTab("lineage");
                    setActiveMenu(null);
                  }}
                  className="w-full px-3 py-1.5 flex items-center justify-between text-[#ECECEC] hover:bg-[#2F2F2F] transition-colors text-left"
                >
                  <span className="flex items-center gap-2">
                    <FileCheck2 className="w-3.5 h-3.5 text-emerald-400" />
                    Export Run Deliverables
                  </span>
                </button>
                <div className="my-1 border-t border-white/[0.08]" />
                <button
                  onClick={handleClose}
                  className="w-full px-3 py-1.5 flex items-center justify-between text-rose-300 hover:bg-rose-900/30 transition-colors text-left"
                >
                  <span>Exit Extra</span>
                  <span className="text-[10px] text-[#8E8E8E]">Alt+F4</span>
                </button>
              </div>
            )}
          </div>

          {/* Edit Menu */}
          <div className="relative">
            <button
              onClick={() => toggleMenu("edit")}
              onMouseEnter={() => handleMenuHover("edit")}
              className={`px-2 py-1 rounded text-[11.5px] font-medium transition-colors cursor-pointer ${
                activeMenu === "edit"
                  ? "bg-white/[0.12] text-[#ECECEC]"
                  : "text-[#B4B4B4] hover:text-[#ECECEC] hover:bg-white/[0.06]"
              }`}
            >
              Edit
            </button>
            {activeMenu === "edit" && (
              <div className="absolute left-0 top-full mt-1 w-52 bg-[#252525] border border-white/[0.1] rounded-lg shadow-2xl py-1 z-50 text-xs">
                <button
                  onClick={() => {
                    document.execCommand("undo");
                    setActiveMenu(null);
                  }}
                  className="w-full px-3 py-1.5 flex items-center justify-between text-[#ECECEC] hover:bg-[#2F2F2F] transition-colors text-left"
                >
                  <span>Undo</span>
                  <span className="text-[10px] text-[#8E8E8E]">Ctrl+Z</span>
                </button>
                <button
                  onClick={() => {
                    document.execCommand("redo");
                    setActiveMenu(null);
                  }}
                  className="w-full px-3 py-1.5 flex items-center justify-between text-[#ECECEC] hover:bg-[#2F2F2F] transition-colors text-left"
                >
                  <span>Redo</span>
                  <span className="text-[10px] text-[#8E8E8E]">Ctrl+Y</span>
                </button>
                <div className="my-1 border-t border-white/[0.08]" />
                <button
                  onClick={() => {
                    document.execCommand("cut");
                    setActiveMenu(null);
                  }}
                  className="w-full px-3 py-1.5 flex items-center justify-between text-[#ECECEC] hover:bg-[#2F2F2F] transition-colors text-left"
                >
                  <span>Cut</span>
                  <span className="text-[10px] text-[#8E8E8E]">Ctrl+X</span>
                </button>
                <button
                  onClick={() => {
                    document.execCommand("copy");
                    setActiveMenu(null);
                  }}
                  className="w-full px-3 py-1.5 flex items-center justify-between text-[#ECECEC] hover:bg-[#2F2F2F] transition-colors text-left"
                >
                  <span>Copy</span>
                  <span className="text-[10px] text-[#8E8E8E]">Ctrl+C</span>
                </button>
                <button
                  onClick={() => {
                    document.execCommand("paste");
                    setActiveMenu(null);
                  }}
                  className="w-full px-3 py-1.5 flex items-center justify-between text-[#ECECEC] hover:bg-[#2F2F2F] transition-colors text-left"
                >
                  <span>Paste</span>
                  <span className="text-[10px] text-[#8E8E8E]">Ctrl+V</span>
                </button>
              </div>
            )}
          </div>

          {/* View Menu */}
          <div className="relative">
            <button
              onClick={() => toggleMenu("view")}
              onMouseEnter={() => handleMenuHover("view")}
              className={`px-2 py-1 rounded text-[11.5px] font-medium transition-colors cursor-pointer ${
                activeMenu === "view"
                  ? "bg-white/[0.12] text-[#ECECEC]"
                  : "text-[#B4B4B4] hover:text-[#ECECEC] hover:bg-white/[0.06]"
              }`}
            >
              View
            </button>
            {activeMenu === "view" && (
              <div className="absolute left-0 top-full mt-1 w-56 bg-[#252525] border border-white/[0.1] rounded-lg shadow-2xl py-1 z-50 text-xs">
                <button
                  onClick={() => {
                    onToggleSidebar();
                    setActiveMenu(null);
                  }}
                  className="w-full px-3 py-1.5 flex items-center justify-between text-[#ECECEC] hover:bg-[#2F2F2F] transition-colors text-left"
                >
                  <span>Toggle Sidebar</span>
                  <span className="text-[10px] text-[#8E8E8E]">Ctrl+Shift+S</span>
                </button>
                <button
                  onClick={() => {
                    handleToggleMaximize();
                    setActiveMenu(null);
                  }}
                  className="w-full px-3 py-1.5 flex items-center justify-between text-[#ECECEC] hover:bg-[#2F2F2F] transition-colors text-left"
                >
                  <span>Toggle Fullscreen</span>
                  <span className="text-[10px] text-[#8E8E8E]">F11</span>
                </button>
                <div className="my-1 border-t border-white/[0.08]" />
                <button
                  onClick={() => {
                    onSelectTab("chat");
                    setActiveMenu(null);
                  }}
                  className="w-full px-3 py-1.5 flex items-center justify-between text-[#ECECEC] hover:bg-[#2F2F2F] transition-colors text-left"
                >
                  <span>Chat Conversation</span>
                  <span className="text-[10px] text-[#8E8E8E]">1</span>
                </button>
                <button
                  onClick={() => {
                    onSelectTab("pilot");
                    setActiveMenu(null);
                  }}
                  className="w-full px-3 py-1.5 flex items-center justify-between text-[#ECECEC] hover:bg-[#2F2F2F] transition-colors text-left"
                >
                  <span className="flex items-center gap-2">
                    <Monitor className="w-3.5 h-3.5 text-indigo-400" />
                    Live Desktop Pilot
                  </span>
                  <span className="text-[10px] text-[#8E8E8E]">2</span>
                </button>
                <button
                  onClick={() => {
                    onSelectTab("automations");
                    setActiveMenu(null);
                  }}
                  className="w-full px-3 py-1.5 flex items-center justify-between text-[#ECECEC] hover:bg-[#2F2F2F] transition-colors text-left"
                >
                  <span className="flex items-center gap-2">
                    <Layers className="w-3.5 h-3.5 text-amber-400" />
                    Automations & Recipes
                  </span>
                  <span className="text-[10px] text-[#8E8E8E]">3</span>
                </button>
                <button
                  onClick={() => {
                    onSelectTab("dualplane");
                    setActiveMenu(null);
                  }}
                  className="w-full px-3 py-1.5 flex items-center justify-between text-[#ECECEC] hover:bg-[#2F2F2F] transition-colors text-left"
                >
                  <span>Dual-Plane Screen</span>
                  <span className="text-[10px] text-[#8E8E8E]">5</span>
                </button>
                <button
                  onClick={() => {
                    onSelectTab("lineage");
                    setActiveMenu(null);
                  }}
                  className="w-full px-3 py-1.5 flex items-center justify-between text-[#ECECEC] hover:bg-[#2F2F2F] transition-colors text-left"
                >
                  <span>Lineage Vault</span>
                  <span className="text-[10px] text-[#8E8E8E]">8</span>
                </button>
              </div>
            )}
          </div>

          {/* Help Menu */}
          <div className="relative">
            <button
              onClick={() => toggleMenu("help")}
              onMouseEnter={() => handleMenuHover("help")}
              className={`px-2 py-1 rounded text-[11.5px] font-medium transition-colors cursor-pointer ${
                activeMenu === "help"
                  ? "bg-white/[0.12] text-[#ECECEC]"
                  : "text-[#B4B4B4] hover:text-[#ECECEC] hover:bg-white/[0.06]"
              }`}
            >
              Help
            </button>
            {activeMenu === "help" && (
              <div className="absolute left-0 top-full mt-1 w-60 bg-[#252525] border border-white/[0.1] rounded-lg shadow-2xl py-1 z-50 text-xs">
                <a
                  href="https://github.com"
                  target="_blank"
                  rel="noreferrer"
                  className="w-full px-3 py-1.5 flex items-center justify-between text-[#ECECEC] hover:bg-[#2F2F2F] transition-colors text-left"
                  onClick={() => setActiveMenu(null)}
                >
                  <span className="flex items-center gap-2">
                    <Info className="w-3.5 h-3.5 text-blue-400" />
                    Documentation
                  </span>
                  <ExternalLink className="w-3 h-3 text-[#8E8E8E]" />
                </a>
                <button
                  onClick={() => {
                    if (onOpenShortcuts) onOpenShortcuts();
                    setActiveMenu(null);
                  }}
                  className="w-full px-3 py-1.5 flex items-center justify-between text-[#ECECEC] hover:bg-[#2F2F2F] transition-colors text-left"
                >
                  <span className="flex items-center gap-2">
                    <Keyboard className="w-3.5 h-3.5 text-purple-400" />
                    Keyboard Shortcuts
                  </span>
                  <span className="text-[10px] text-[#8E8E8E]">Ctrl+/</span>
                </button>
                <div className="my-1 border-t border-white/[0.08]" />
                <div className="px-3 py-1.5 text-[11px] text-[#8E8E8E] flex items-center justify-between">
                  <span className="flex items-center gap-1.5">
                    <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
                    Panic Stop:
                  </span>
                  <span className="font-mono text-rose-300 text-[10px]">Ctrl+Alt+Esc</span>
                </div>
                <div className="my-1 border-t border-white/[0.08]" />
                <div className="px-3 py-1.5 text-[11px] text-[#8E8E8E]">
                  Extra v2.4 (ChatGPT Desktop Edition)
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Middle: Draggable window space */}
      <div className="flex-1 h-full cursor-move" data-tauri-drag-region />

      {/* Right: Windows Native Window Controls */}
      <div className="flex items-center gap-0.5 -mr-1" data-tauri-drag-region="false">
        <button
          onClick={handleMinimize}
          aria-label="Minimize Window"
          title="Minimize"
          className="w-8 h-7 flex items-center justify-center text-[#8E8E8E] hover:text-[#ECECEC] hover:bg-white/[0.06] transition-colors cursor-pointer rounded-sm"
        >
          <Minus className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={handleToggleMaximize}
          aria-label="Maximize Window"
          title="Maximize"
          className="w-8 h-7 flex items-center justify-center text-[#8E8E8E] hover:text-[#ECECEC] hover:bg-white/[0.06] transition-colors cursor-pointer rounded-sm"
        >
          <Square className="w-3 h-3" />
        </button>
        <button
          onClick={handleClose}
          aria-label="Close Window"
          title="Close"
          className="w-8 h-7 flex items-center justify-center text-[#8E8E8E] hover:text-white hover:bg-rose-600 transition-colors cursor-pointer rounded-sm"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </header>
  );
}
