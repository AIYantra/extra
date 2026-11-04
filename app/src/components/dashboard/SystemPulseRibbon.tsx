import { Terminal, Zap, OctagonAlert, Play } from "lucide-react";
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";
import { useEngineStore } from "../../store/useEngineStore";

export function SystemPulseRibbon() {
  const telemetry = useEngineStore((state) => state.telemetry);
  const isServerOnline = useEngineStore((state) => state.isServerOnline);
  const isPanicActive = useEngineStore((state) => state.isPanicActive);
  const panicStop = useEngineStore((state) => state.panicStop);
  const resumePilot = useEngineStore((state) => state.resumePilot);

  const settleLatency = telemetry.latency_ms > 0 ? telemetry.latency_ms.toFixed(1) + "ms" : "<15ms";
  const targetProc = telemetry.target_proc || (isServerOnline ? "Extra MCP" : "Desktop");
  const targetPid = telemetry.target_pid ? `PID ${telemetry.target_pid}` : "Ready";

  return (
    <div className="flex items-center justify-between px-3.5 py-2 rounded-lg border border-station-border bg-station-well/80 text-xs font-mono select-none shadow-xs">
      {/* Left: Calm Engine Status & Process */}
      <div className="flex items-center gap-2.5 min-w-0">
        <Tooltip>
          <TooltipTrigger asChild>
            <div className="flex items-center gap-1.5 cursor-help">
              <span
                className={`size-2 rounded-full shrink-0 ${
                  isPanicActive
                    ? "bg-rose-500 animate-pulse"
                    : isServerOnline
                    ? "bg-emerald-500"
                    : "bg-emerald-500/80"
                }`}
              />
              <span className="font-medium text-station-text-primary text-[11px] tracking-tight">
                {isPanicActive ? "HARDWARE FROZEN" : isServerOnline ? "ENGINE ACTIVE" : "PILOT ACTIVE"}
              </span>
            </div>
          </TooltipTrigger>
          <TooltipContent side="bottom" className="text-xs font-sans">
            {isPanicActive
              ? "Emergency Hardware Stop Active. All OS inputs blocked."
              : isServerOnline
              ? "Loopback MCP RPC server active on 127.0.0.1:8000"
              : "Direct Win32 Hardware Actuator Active"}
          </TooltipContent>
        </Tooltip>

        <span className="text-station-border">·</span>

        <span className="text-station-text-muted text-[11px] truncate flex items-center gap-1">
          <Terminal className="size-3 text-station-text-dim shrink-0" />
          <span>{targetProc}</span>
          <span className="text-station-text-dim">/</span>
          <span className="text-station-text-muted">{targetPid}</span>
        </span>

        <span className="text-station-border hidden sm:inline">·</span>

        <span className="hidden sm:inline-flex items-center gap-1 text-[11px] text-station-text-muted">
          <Zap className="size-3 text-cyan-500 shrink-0" />
          <span>{settleLatency} settle</span>
        </span>
      </div>

      {/* Right: Panic Stop / Resume Pill */}
      <div className="flex items-center gap-2 shrink-0">
        {isPanicActive ? (
          <button
            onClick={resumePilot}
            className="flex items-center gap-1 h-5.5 px-2 rounded-md bg-emerald-600 hover:bg-emerald-500 text-white text-[10px] font-medium transition-colors cursor-pointer shadow-xs"
          >
            <Play className="size-2.5 fill-current" />
            <span>Resume Pilot</span>
          </button>
        ) : (
          <button
            onClick={panicStop}
            className="flex items-center gap-1 h-5.5 px-2 rounded-md text-[10px] text-rose-500 hover:text-white bg-rose-500/10 hover:bg-rose-600 border border-rose-500/20 transition-all cursor-pointer shadow-xs"
            title="Emergency Hardware Stop (Ctrl+Alt+Esc)"
          >
            <OctagonAlert className="size-2.5" />
            <span>Panic Stop</span>
          </button>
        )}
      </div>
    </div>
  );
}
