import { useState } from "react";
import { MessageSquare, Monitor, RotateCw, Maximize2, Minimize2 } from "lucide-react";
import { useEngineStore } from "../../store/useEngineStore";
import { soundEngine } from "../../utils/sound";

interface ModeSwitcherProps {
  onToggleExpand?: () => void;
  isExpanded?: boolean;
}

export function ModeSwitcher({ onToggleExpand, isExpanded = false }: ModeSwitcherProps) {
  const activeMode = useEngineStore((state) => state.activeMode);
  const setActiveMode = useEngineStore((state) => state.setActiveMode);
  const refreshTelemetry = useEngineStore((state) => state.refreshTelemetry);
  const fetchRuns = useEngineStore((state) => state.fetchRuns);
  const fetchLineage = useEngineStore((state) => state.fetchLineage);
  const telemetry = useEngineStore((state) => state.telemetry);
  const isServerOnline = useEngineStore((state) => state.isServerOnline);

  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleSelectMode = (mode: "chat" | "work") => {
    if (activeMode !== mode) {
      soundEngine.playTick();
      setActiveMode(mode);
    }
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    soundEngine.playTick();
    try {
      await Promise.allSettled([
        refreshTelemetry(),
        fetchRuns(),
        fetchLineage(),
      ]);
    } finally {
      setTimeout(() => setIsRefreshing(false), 500);
    }
  };

  return (
    <div className="w-full flex items-center justify-between px-4 py-2 border-b border-white/[0.06] bg-[#212121]/90 backdrop-blur-md sticky top-0 z-30 select-none font-sans">
      {/* Left: Active Pilot / Live target window subtitle badge */}
      <div className="flex items-center gap-2 min-w-0">
        <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/[0.04] border border-white/[0.06] text-xs text-[#B4B4B4]">
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              isServerOnline ? "bg-emerald-400" : "bg-amber-400"
            }`}
          />
          <span className="font-mono text-[11px] text-[#ECECEC] truncate max-w-[140px]">
            {telemetry.target_proc || "Desktop"}
          </span>
          {telemetry.latency_ms > 0 && (
            <span className="text-[10px] text-[#8E8E8E] font-mono tabular-nums">
              ({telemetry.latency_ms.toFixed(0)}ms)
            </span>
          )}
        </div>
      </div>

      {/* Center: Segmented Floating Capsule [ Chat | Work ] */}
      <div className="flex items-center bg-[#171717] p-1 rounded-full border border-white/[0.08] shadow-inner">
        <button
          onClick={() => handleSelectMode("chat")}
          className={`flex items-center gap-2 px-4 py-1 rounded-full text-xs font-medium transition-all duration-150 cursor-pointer ${
            activeMode === "chat"
              ? "bg-[#2F2F2F] text-[#ECECEC] shadow-sm font-semibold"
              : "text-[#8E8E8E] hover:text-[#ECECEC] hover:bg-white/[0.04]"
          }`}
          title="Chat Assistant Mode (Ctrl+1)"
        >
          <MessageSquare className={`w-3.5 h-3.5 ${activeMode === "chat" ? "text-purple-400" : "text-[#8E8E8E]"}`} />
          <span>Chat</span>
        </button>

        <button
          onClick={() => handleSelectMode("work")}
          className={`flex items-center gap-2 px-4 py-1 rounded-full text-xs font-medium transition-all duration-150 cursor-pointer ${
            activeMode === "work"
              ? "bg-[#2F2F2F] text-[#ECECEC] shadow-sm font-semibold"
              : "text-[#8E8E8E] hover:text-[#ECECEC] hover:bg-white/[0.04]"
          }`}
          title="Workstation Live Pilot Mode (Ctrl+2)"
        >
          <Monitor className={`w-3.5 h-3.5 ${activeMode === "work" ? "text-indigo-400" : "text-[#8E8E8E]"}`} />
          <span>Work</span>
          {telemetry.is_paused ? (
            <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse" />
          ) : isServerOnline ? (
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
          ) : null}
        </button>
      </div>

      {/* Right: Quick Canvas Actions (Expand ⊞ and Refresh ↻) */}
      <div className="flex items-center gap-1 min-w-0">
        <button
          onClick={handleRefresh}
          disabled={isRefreshing}
          className="w-7 h-7 rounded-md flex items-center justify-center text-[#8E8E8E] hover:text-[#ECECEC] hover:bg-white/[0.06] transition-colors cursor-pointer"
          title="Refresh Engine State (↻)"
        >
          <RotateCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin text-purple-400" : ""}`} />
        </button>

        <button
          onClick={onToggleExpand}
          className="w-7 h-7 rounded-md flex items-center justify-center text-[#8E8E8E] hover:text-[#ECECEC] hover:bg-white/[0.06] transition-colors cursor-pointer"
          title={isExpanded ? "Collapse View (⊞)" : "Expand View (⊞)"}
        >
          {isExpanded ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
        </button>
      </div>
    </div>
  );
}
