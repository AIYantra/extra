import { useState, useEffect } from "react";
import {
  AlertTriangle,
  Play,
  ChevronDown,
  ChevronUp,
  Activity,
} from "lucide-react";
import { toast } from "sonner";
import { useEngineStore } from "../../store/useEngineStore";
import { soundEngine } from "../../utils/sound";
import { Keycap } from "../minimal/Keycap";

export function ActiveFlightDeck() {
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);
  const [elapsedSec, setElapsedSec] = useState(0);

  const isExecuting = useEngineStore((state) => state.isExecuting);
  const activeMission = useEngineStore((state) => state.activeMission);
  const activeStep = useEngineStore((state) => state.activeStep);
  const executionStartTime = useEngineStore((state) => state.executionStartTime);
  const isPanicActive = useEngineStore((state) => state.isPanicActive);
  const telemetry = useEngineStore((state) => state.telemetry);
  const activeTool = useEngineStore((state) => state.activeTool);
  const lastAction = useEngineStore((state) => state.lastAction);
  const panicStop = useEngineStore((state) => state.panicStop);
  const resumePilot = useEngineStore((state) => state.resumePilot);

  // Timer tick during active execution
  useEffect(() => {
    if (!isExecuting) {
      setElapsedSec(0);
      return;
    }

    const interval = setInterval(() => {
      if (executionStartTime) {
        setElapsedSec((Date.now() - executionStartTime) / 1000);
      } else {
        setElapsedSec((prev) => prev + 0.1);
      }
    }, 100);

    return () => clearInterval(interval);
  }, [isExecuting, executionStartTime]);

  const handlePanic = async () => {
    soundEngine.playPanicAlert();
    toast.error("Emergency Mission Abort — Extra Paused", { duration: 4000 });
    await panicStop();
  };

  const handleResume = async () => {
    soundEngine.playTick();
    toast.success("Resuming Desktop Automation");
    await resumePilot();
  };

  const formatTimer = (sec: number) => {
    const mins = Math.floor(sec / 60);
    const s = (sec % 60).toFixed(1);
    return `${mins.toString().padStart(2, "0")}:${s.padStart(4, "0")}`;
  };

  const displayIntent =
    activeMission ||
    lastAction?.intent ||
    (isExecuting ? "Executing computer action..." : "Ready for instructions");

  // If completely idle and no panic, consume ZERO vertical height
  if (!isExecuting && !isPanicActive) {
    return null;
  }

  return (
    <div
      className={`rounded-2xl border transition-all duration-150 overflow-hidden shadow-xs ${
        isPanicActive
          ? "border-rose-500/30 bg-rose-50/50 dark:bg-rose-950/20"
          : "border-emerald-500/25 bg-emerald-50/50 dark:bg-emerald-950/20"
      }`}
    >
      <div className="p-3.5 sm:p-4 flex flex-col gap-2.5">
        {/* Dynamic Island Style Main Bar */}
        <div className="flex items-center justify-between gap-3">
          {/* Left: Status Pill + Intent */}
          <div className="flex items-center gap-2.5 min-w-0">
            <span className="relative flex size-2.5 shrink-0">
              <span
                className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                  isPanicActive ? "bg-rose-400" : "bg-emerald-400"
                }`}
              />
              <span
                className={`relative inline-flex rounded-full size-2.5 ${
                  isPanicActive ? "bg-rose-500" : "bg-emerald-500"
                }`}
              />
            </span>

            <div className="flex items-center gap-2 min-w-0">
              <span
                className={`text-xs font-semibold tracking-tight shrink-0 ${
                  isPanicActive
                    ? "text-rose-700 dark:text-rose-400"
                    : "text-emerald-700 dark:text-emerald-400"
                }`}
              >
                {isPanicActive ? "Paused" : "In Flight"}
              </span>

              {isExecuting && (
                <span className="text-[11px] font-mono font-medium text-emerald-800 dark:text-emerald-300 bg-emerald-500/10 px-1.5 py-0.5 rounded tabular-nums shrink-0">
                  T+ {formatTimer(elapsedSec)}
                </span>
              )}

              <span className="text-xs font-medium text-slate-800 dark:text-zinc-200 truncate">
                {displayIntent}
              </span>
            </div>
          </div>

          {/* Right: Pause / Resume Button + Diagnostics Trigger */}
          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
              className="text-[11px] font-mono text-slate-500 hover:text-slate-800 dark:text-zinc-400 dark:hover:text-zinc-200 px-2 py-1 rounded-md hover:bg-black/[0.04] dark:hover:bg-white/[0.04] transition-colors flex items-center gap-1 cursor-pointer"
            >
              <span>{showTechnicalDetails ? "Less" : "Diagnostics"}</span>
              {showTechnicalDetails ? <ChevronUp className="size-3" /> : <ChevronDown className="size-3" />}
            </button>

            {isExecuting && (
              <button
                onClick={handlePanic}
                title="Pause Extra (Press Esc)"
                className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-600 dark:text-rose-400 border border-rose-500/20 transition-all cursor-pointer active:scale-95"
              >
                <AlertTriangle className="size-3 text-rose-500" />
                <span>Pause</span>
                <Keycap size="sm" className="text-rose-500 border-rose-500/30">
                  Esc
                </Keycap>
              </button>
            )}

            {isPanicActive && (
              <button
                onClick={handleResume}
                className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white transition-all shadow-xs cursor-pointer active:scale-95"
              >
                <Play className="size-3 fill-current" />
                <span>Resume</span>
              </button>
            )}
          </div>
        </div>

        {/* Step subtitle if actively dispatching */}
        {activeStep && (
          <p className="text-[11px] text-slate-500 dark:text-zinc-400 flex items-center gap-1.5 pl-5">
            <Activity className="size-3 text-emerald-500 shrink-0" />
            <span className="truncate">{activeStep}</span>
          </p>
        )}

        {/* Expanded Diagnostics Panel (Only when requested) */}
        {showTechnicalDetails && (
          <div className="pt-2 mt-1 border-t border-black/[0.05] dark:border-white/[0.06] grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] font-mono">
            <div className="p-2 rounded-lg bg-white/60 dark:bg-zinc-900/60 border border-black/[0.04] dark:border-white/[0.05]">
              <span className="text-slate-400 dark:text-zinc-500 block text-[10px] uppercase">Window</span>
              <span className="text-slate-800 dark:text-zinc-200 truncate font-medium block">
                {telemetry.target_window || "Desktop"}
              </span>
            </div>
            <div className="p-2 rounded-lg bg-white/60 dark:bg-zinc-900/60 border border-black/[0.04] dark:border-white/[0.05]">
              <span className="text-slate-400 dark:text-zinc-500 block text-[10px] uppercase">Process</span>
              <span className="text-slate-800 dark:text-zinc-200 truncate font-medium block">
                {telemetry.target_proc || "System"} (PID: {telemetry.target_pid || 0})
              </span>
            </div>
            <div className="p-2 rounded-lg bg-white/60 dark:bg-zinc-900/60 border border-black/[0.04] dark:border-white/[0.05]">
              <span className="text-slate-400 dark:text-zinc-500 block text-[10px] uppercase">Tool</span>
              <span className="text-slate-800 dark:text-zinc-200 truncate font-medium block">
                {activeTool !== "Standing by" ? activeTool : "Ready"}
              </span>
            </div>
            <div className="p-2 rounded-lg bg-white/60 dark:bg-zinc-900/60 border border-black/[0.04] dark:border-white/[0.05]">
              <span className="text-slate-400 dark:text-zinc-500 block text-[10px] uppercase">Settle Latency</span>
              <span className="text-emerald-600 dark:text-emerald-400 font-medium block">
                {telemetry.latency_ms > 0 ? `${telemetry.latency_ms.toFixed(1)}ms` : "< 15ms"}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
