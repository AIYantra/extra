import { useState } from "react";
import {
  Monitor,
  X,
  Play,
  Pause,
  RotateCw,
} from "lucide-react";
import { LivePilotGlass } from "../dashboard/LivePilotGlass";
import { RunHistoryTable } from "../dashboard/RunHistoryTable";
import { LineageVaultCard } from "../dashboard/LineageVaultCard";
import { DualPlaneView } from "../dashboard/DualPlaneView";
import { OpticalRadarView } from "../dashboard/OpticalRadarView";
import { SkillsCatalogView } from "../dashboard/SkillsCatalogView";
import { useEngineStore } from "../../store/useEngineStore";
import { soundEngine } from "../../utils/sound";

interface WorkCockpitViewProps {
  onClose?: () => void;
  isSplitView?: boolean;
}

type WorkSubTab = "cockpit" | "dualplane" | "radar" | "skills" | "lineage";

export function WorkCockpitView({ onClose, isSplitView = false }: WorkCockpitViewProps) {
  const [subTab, setSubTab] = useState<WorkSubTab>("cockpit");
  const [isRefreshing, setIsRefreshing] = useState(false);

  const telemetry = useEngineStore((state) => state.telemetry);
  const isServerOnline = useEngineStore((state) => state.isServerOnline);
  const isPanicActive = useEngineStore((state) => state.isPanicActive);
  const speedMode = useEngineStore((state) => state.speedMode);
  const refreshTelemetry = useEngineStore((state) => state.refreshTelemetry);
  const panicStop = useEngineStore((state) => state.panicStop);
  const resumePilot = useEngineStore((state) => state.resumePilot);

  const handleSubTabChange = (tab: WorkSubTab) => {
    soundEngine.playTick();
    setSubTab(tab);
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    soundEngine.playTick();
    await refreshTelemetry();
    setTimeout(() => setIsRefreshing(false), 500);
  };

  const renderSubView = () => {
    switch (subTab) {
      case "dualplane":
        return <DualPlaneView />;
      case "radar":
        return <OpticalRadarView />;
      case "skills":
        return <SkillsCatalogView />;
      case "lineage":
        return (
          <div className="space-y-4">
            <LineageVaultCard />
            <RunHistoryTable />
          </div>
        );
      case "cockpit":
      default:
        return (
          <div className="space-y-4 sm:space-y-5 animate-in fade-in duration-150">
            {/* Live Visual Optical Glass */}
            <LivePilotGlass />

            {/* Run Ledger & Deliverable Lineage Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <RunHistoryTable />
              <LineageVaultCard />
            </div>
          </div>
        );
    }
  };

  return (
    <div className="w-full flex flex-col space-y-4 font-sans select-none">
      {/* Top Workstation Header HUD */}
      <div className="p-3 rounded-2xl bg-[#1A1A1A] border border-white/[0.08] shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        {/* Left: Mode Title + Telemetry Status */}
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center shrink-0">
            <Monitor className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-xs text-[#ECECEC] tracking-tight">
                Workstation Cockpit
              </span>
              <span
                className={`text-[9px] font-mono px-1.5 py-0.2 rounded font-medium ${
                  isServerOnline
                    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                    : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                }`}
              >
                {isServerOnline ? "Engine Connected" : "Standby"}
              </span>
              <span className="text-[9px] font-mono px-1 py-0.2 rounded bg-purple-900/40 text-purple-300 border border-purple-500/30">
                {speedMode.toUpperCase()}
              </span>
            </div>
            <div className="flex items-center gap-2 text-[10px] font-mono text-[#8E8E8E] mt-0.5 truncate">
              <span>Target: <strong className="text-[#ECECEC] font-normal">{telemetry.target_proc || "Desktop"}</strong></span>
              {telemetry.target_pid > 0 && <span>• PID {telemetry.target_pid}</span>}
              <span>• Latency: <strong className="text-emerald-400 font-normal">{telemetry.latency_ms.toFixed(1)}ms</strong></span>
            </div>
          </div>
        </div>

        {/* Center: Sub-view Segmented Tabs */}
        <div className="flex items-center bg-[#141414] p-1 rounded-xl border border-white/[0.06] text-xs self-start sm:self-auto overflow-x-auto max-w-full">
          <button
            onClick={() => handleSubTabChange("cockpit")}
            className={`px-3 py-1 rounded-lg transition-colors cursor-pointer whitespace-nowrap ${
              subTab === "cockpit"
                ? "bg-[#2A2A2A] text-[#ECECEC] font-medium shadow-sm"
                : "text-[#8E8E8E] hover:text-[#ECECEC]"
            }`}
          >
            Cockpit
          </button>
          <button
            onClick={() => handleSubTabChange("dualplane")}
            className={`px-3 py-1 rounded-lg transition-colors cursor-pointer whitespace-nowrap ${
              subTab === "dualplane"
                ? "bg-[#2A2A2A] text-[#ECECEC] font-medium shadow-sm"
                : "text-[#8E8E8E] hover:text-[#ECECEC]"
            }`}
          >
            Dual-Plane
          </button>
          <button
            onClick={() => handleSubTabChange("radar")}
            className={`px-3 py-1 rounded-lg transition-colors cursor-pointer whitespace-nowrap ${
              subTab === "radar"
                ? "bg-[#2A2A2A] text-[#ECECEC] font-medium shadow-sm"
                : "text-[#8E8E8E] hover:text-[#ECECEC]"
            }`}
          >
            Optical Radar
          </button>
          <button
            onClick={() => handleSubTabChange("skills")}
            className={`px-3 py-1 rounded-lg transition-colors cursor-pointer whitespace-nowrap ${
              subTab === "skills"
                ? "bg-[#2A2A2A] text-[#ECECEC] font-medium shadow-sm"
                : "text-[#8E8E8E] hover:text-[#ECECEC]"
            }`}
          >
            Skills Catalog
          </button>
          <button
            onClick={() => handleSubTabChange("lineage")}
            className={`px-3 py-1 rounded-lg transition-colors cursor-pointer whitespace-nowrap ${
              subTab === "lineage"
                ? "bg-[#2A2A2A] text-[#ECECEC] font-medium shadow-sm"
                : "text-[#8E8E8E] hover:text-[#ECECEC]"
            }`}
          >
            Lineage Vault
          </button>
        </div>

        {/* Right: Panic Control + Refresh + Close */}
        <div className="flex items-center gap-1.5 shrink-0">
          <button
            onClick={isPanicActive ? resumePilot : panicStop}
            className={`px-2.5 py-1 rounded-lg text-xs font-medium flex items-center gap-1.5 cursor-pointer transition-colors shadow-sm ${
              isPanicActive
                ? "bg-emerald-600 hover:bg-emerald-500 text-white"
                : "bg-rose-950/60 hover:bg-rose-900/80 text-rose-300 border border-rose-500/30"
            }`}
            title="Emergency Panic Kill Switch (Ctrl+Alt+Esc)"
          >
            {isPanicActive ? (
              <>
                <Play className="w-3 h-3 fill-current" />
                <span>Resume</span>
              </>
            ) : (
              <>
                <Pause className="w-3 h-3" />
                <span>Panic Freeze</span>
              </>
            )}
          </button>

          <button
            onClick={handleRefresh}
            className="w-7 h-7 rounded-lg flex items-center justify-center text-[#8E8E8E] hover:text-[#ECECEC] hover:bg-white/[0.06] transition-colors cursor-pointer"
            title="Refresh State"
          >
            <RotateCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin text-purple-400" : ""}`} />
          </button>

          {isSplitView && onClose && (
            <button
              onClick={() => {
                soundEngine.playTick();
                onClose();
              }}
              className="w-7 h-7 rounded-lg flex items-center justify-center text-[#8E8E8E] hover:text-white hover:bg-white/[0.08] transition-colors cursor-pointer ml-1"
              title="Close Split Canvas"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Main Subview Container */}
      <div className="flex-1 min-w-0">
        {renderSubView()}
      </div>
    </div>
  );
}
