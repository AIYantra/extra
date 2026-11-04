import { useState } from "react";
import { Search, Command, Bell, RefreshCw, MonitorSmartphone, Pause, Play } from "lucide-react";

interface TopBarProps {
  onOpenCommandPalette: () => void;
  isPaused: boolean;
  onTogglePause: () => void;
}

export function TopBar({ onOpenCommandPalette, isPaused, onTogglePause }: TopBarProps) {
  const [spinning, setSpinning] = useState(false);

  const refresh = () => {
    setSpinning(true);
    window.setTimeout(() => setSpinning(false), 600);
  };

  return (
    <header className="h-14 shrink-0 border-b border-[#DFE4EB] bg-white px-4 lg:px-6 flex items-center justify-between gap-4 sticky top-0 z-20">
      {/* Command palette trigger */}
      <button
        type="button"
        onClick={onOpenCommandPalette}
        aria-label="Open command palette"
        className="tactile flex-1 min-w-0 max-w-md flex items-center justify-between gap-3 px-3 py-2 rounded-lg border border-[#DFE4EB] bg-slate-50 hover:bg-white hover:border-slate-300 text-[13px] text-slate-500 text-left"
      >
        <span className="flex items-center gap-2 truncate">
          <Search size={16} strokeWidth={1.75} className="text-slate-400 shrink-0" />
          <span className="truncate">Search actions, apps, skills, runs…</span>
        </span>
        <kbd className="hidden sm:inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-mono font-medium text-slate-500 bg-white border border-[#DFE4EB] rounded shrink-0">
          <Command size={12} strokeWidth={1.75} /> K
        </kbd>
      </button>

      <div className="flex items-center gap-2.5">
        {/* Environment pill: OS · host · port */}
        <div className="hidden xl:flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-slate-50 border border-[#DFE4EB] text-[11px] text-slate-600 font-mono whitespace-nowrap" title="Connected desktop environment">
          <MonitorSmartphone size={16} strokeWidth={1.75} className="text-slate-400" />
          <span>Windows 11 · DESKTOP-7F2A · :1420</span>
          <span className="w-1.5 h-1.5 rounded-full bg-[#10B981]" aria-label="Connected" />
        </div>

        {/* Physical pause / intervention switch — permanently anchored (Fitts) */}
        <button
          type="button"
          role="switch"
          aria-checked={isPaused}
          onClick={onTogglePause}
          className={`tactile flex items-center gap-2 pl-3 pr-2 py-1.5 rounded-lg text-xs font-semibold border ${isPaused ? "bg-amber-50 text-amber-800 border-amber-300" : "bg-white text-slate-700 border-[#DFE4EB] hover:border-slate-300"}`}
        >
          {isPaused ? <Play size={16} strokeWidth={1.75} /> : <Pause size={16} strokeWidth={1.75} />}
          <span className="hidden md:inline">{isPaused ? "Intervention — Paused" : "Live Pilot"}</span>
          <span className={`relative w-8 h-[18px] rounded-full transition-colors duration-100 ${isPaused ? "bg-amber-400" : "bg-slate-200"}`} aria-hidden="true">
            <span className={`absolute top-[2px] w-[14px] h-[14px] rounded-full bg-white shadow transition-all duration-100 ${isPaused ? "left-[16px]" : "left-[2px]"}`} />
          </span>
        </button>

        <button type="button" onClick={refresh} aria-label="Refresh telemetry" className="tactile hidden md:block p-2 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg">
          <RefreshCw size={16} strokeWidth={1.75} className={spinning ? "animate-spin" : ""} />
        </button>

        <button type="button" aria-label="Notifications, 2 unread" className="tactile relative p-2 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg">
          <Bell size={16} strokeWidth={1.75} />
          <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-[#0284C7]" aria-hidden="true" />
        </button>

        <button type="button" aria-label="Operator profile" className="tactile w-8 h-8 rounded-full bg-slate-100 border border-[#DFE4EB] flex items-center justify-center text-[11px] font-bold text-slate-700 ml-1">
          OP
        </button>
      </div>
    </header>
  );
}
