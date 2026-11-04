import { Activity, ShieldCheck, Sparkles, Layers, Terminal, Cpu } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";
import { useEngineStore } from "../../store/useEngineStore";

export function TelemetryRadarCard() {
  const telemetry = useEngineStore((state) => state.telemetry);
  const isServerOnline = useEngineStore((state) => state.isServerOnline);

  return (
    <Card className="rounded-xl border border-station-border bg-station-well shadow-xs overflow-hidden transition-all duration-200">
      {/* Header */}
      <CardHeader className="p-3.5 sm:p-4 border-b border-station-border bg-station-elevated flex flex-row items-center justify-between gap-3 select-none">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-7 h-7 rounded-md bg-station-surface border border-station-border flex items-center justify-center text-cyan-500 shadow-xs shrink-0">
            <Activity className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <CardTitle className="text-xs sm:text-sm font-medium text-station-text-primary tracking-tight">
              Engine Telemetry & Guardrails
            </CardTitle>
            <CardDescription className="text-[11px] text-station-text-muted font-sans mt-0.5 truncate">
              Live OS Event Actuation & Perception Telemetry
            </CardDescription>
          </div>
        </div>

        <Tooltip>
          <TooltipTrigger asChild>
            <span className="inline-flex">
              <Badge
                variant={isServerOnline ? "success" : "outline"}
                dot={isServerOnline}
                pulse={isServerOnline}
                className="text-[10px] py-0.5 px-2 font-mono shrink-0"
              >
                {isServerOnline ? "127.0.0.1:8000 Live" : "Standby"}
              </Badge>
            </span>
          </TooltipTrigger>
          <TooltipContent>FastAPI / MCP local telemetry socket connection state</TooltipContent>
        </Tooltip>
      </CardHeader>

      <CardContent className="p-4 sm:p-5 space-y-4 bg-station-canvas">
        {/* Dual Plane Distribution Meter */}
        <div className="space-y-1.5 select-none">
          <div className="flex items-center justify-between text-xs text-station-text-primary">
            <span className="flex items-center gap-1.5 font-medium">
              <Layers className="w-3.5 h-3.5 text-indigo-500" />
              <span>Dual-Plane Workload Distribution</span>
            </span>
            <span className="font-mono text-[11px] text-station-text-muted">
              {telemetry.actions_dispatched ? `${telemetry.actions_dispatched.toLocaleString()} Actions` : "Dual-Plane Active"}
            </span>
          </div>

          {/* Segmented Dual-Plane Progress Bar */}
          <div className="w-full bg-station-surface h-2 rounded-full overflow-hidden flex border border-station-border p-[1px]">
            <Tooltip>
              <TooltipTrigger asChild>
                <div
                  className="bg-indigo-500 hover:bg-indigo-400 h-full rounded-l-full transition-all cursor-help"
                  style={{ width: "50%" }}
                />
              </TooltipTrigger>
              <TooltipContent>Plane 1: Optical Grounding & Zero-Coordinate Actuation</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <div
                  className="bg-emerald-500 hover:bg-emerald-400 h-full rounded-r-full transition-all cursor-help"
                  style={{ width: "50%" }}
                />
              </TooltipTrigger>
              <TooltipContent>Plane 2: Native Bridge Code & Batch OS Operations</TooltipContent>
            </Tooltip>
          </div>

          <div className="flex justify-between text-[10px] font-mono text-station-text-dim pt-0.5">
            <span className="text-indigo-600 dark:text-indigo-400 font-medium">Plane 1: Optical Grounding (&lt;15ms)</span>
            <span className="text-emerald-600 dark:text-emerald-400 font-medium">Plane 2: Native Bridge Code</span>
          </div>
        </div>

        {/* Metric Tiles 2x2 with Tooltips */}
        <div className="grid grid-cols-2 gap-2.5 text-xs pt-1 select-none">
          {/* Tile 1: SOUL-Gateman */}
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="p-2.5 rounded-lg border border-station-border bg-station-well hover:bg-station-surface transition-colors space-y-1 shadow-xs cursor-help">
                <div className="flex items-center gap-1.5 text-[10px] font-mono text-station-text-muted font-medium">
                  <Sparkles className="w-3 h-3 text-emerald-500" />
                  <span>SOUL-Gateman</span>
                </div>
                <p className="font-mono font-medium text-station-text-primary text-xs tabular-nums">
                  {telemetry.latency_ms > 0 ? `${telemetry.latency_ms.toFixed(1)}ms Visual Settle` : "<15ms Visual Settle"}
                </p>
              </div>
            </TooltipTrigger>
            <TooltipContent>Tier 1 optical settle detection ensures visual rendering matches actual state before next step.</TooltipContent>
          </Tooltip>

          {/* Tile 2: CFA Guardrail */}
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="p-2.5 rounded-lg border border-station-border bg-station-well hover:bg-station-surface transition-colors space-y-1 shadow-xs cursor-help">
                <div className="flex items-center gap-1.5 text-[10px] font-mono text-station-text-muted font-medium">
                  <ShieldCheck className="w-3 h-3 text-emerald-500" />
                  <span>CFA Guardrail</span>
                </div>
                <p className="font-mono font-medium text-station-text-primary text-xs">
                  100% Controlled Folder Safe
                </p>
              </div>
            </TooltipTrigger>
            <TooltipContent>Windows Defender Controlled Folder Access compliant. Operations restricted to safe workspaces.</TooltipContent>
          </Tooltip>

          {/* Tile 3: Actuator Plane */}
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="p-2.5 rounded-lg border border-station-border bg-station-well hover:bg-station-surface transition-colors space-y-1 shadow-xs cursor-help">
                <div className="flex items-center gap-1.5 text-[10px] font-mono text-station-text-muted font-medium">
                  <Terminal className="w-3 h-3 text-indigo-500" />
                  <span>Actuator Plane</span>
                </div>
                <p className="font-mono font-medium text-station-text-primary text-xs truncate">
                  {telemetry.target_proc || "Desktop"} ({telemetry.target_pid ? `PID ${telemetry.target_pid}` : "Ready"})
                </p>
              </div>
            </TooltipTrigger>
            <TooltipContent>Direct Win32 HWND targeting and AT-SPI2 accessibility bridge connection.</TooltipContent>
          </Tooltip>

          {/* Tile 4: Process RSS Memory */}
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="p-2.5 rounded-lg border border-station-border bg-station-well hover:bg-station-surface transition-colors space-y-1 shadow-xs cursor-help">
                <div className="flex items-center gap-1.5 text-[10px] font-mono text-station-text-muted font-medium">
                  <Cpu className="w-3 h-3 text-cyan-500" />
                  <span>Engine RSS Memory</span>
                </div>
                <p className="font-mono font-medium text-station-text-primary text-xs tabular-nums">
                  {telemetry.memory_mb > 0 ? `${telemetry.memory_mb.toFixed(0)} MB RSS` : "Active RSS"}
                </p>
              </div>
            </TooltipTrigger>
            <TooltipContent>Physical RAM occupied by Extra daemon process and PyWebView host.</TooltipContent>
          </Tooltip>
        </div>
      </CardContent>
    </Card>
  );
}