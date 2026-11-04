import { useState } from "react";
import {
  Clock,
  ArrowRight,
  FileSpreadsheet,
  Palette,
  Box,
  Brush,
  BookOpen,
  Globe,
  Calculator,
  ChevronRight,
  Terminal,
} from "lucide-react";
import { useEngineStore } from "../../store/useEngineStore";
import { formatDuration, type MissionRun, type RunStatus } from "../../data/dashboard";
import { RunDetailDrawer } from "./RunDetailDrawer";

interface RecentActivityStreamProps {
  onNavigateTab?: (tab: string) => void;
}

export function RecentActivityStream({ onNavigateTab }: RecentActivityStreamProps) {
  const runs = useEngineStore((state) => state.runs);
  const [selectedRun, setSelectedRun] = useState<MissionRun | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const recentRuns = runs.slice(0, 4);

  const getAppIcon = (app: string) => {
    switch (app.toLowerCase()) {
      case "sheets":
        return <FileSpreadsheet className="size-3.5 text-emerald-500" />;
      case "canva":
        return <Palette className="size-3.5 text-indigo-500" />;
      case "blender":
        return <Box className="size-3.5 text-amber-500" />;
      case "paint":
      case "mspaint":
        return <Brush className="size-3.5 text-rose-500" />;
      case "obsidian":
        return <BookOpen className="size-3.5 text-purple-500" />;
      case "calculator":
      case "calc":
        return <Calculator className="size-3.5 text-cyan-500" />;
      case "terminal":
      case "cmd":
      case "powershell":
        return <Terminal className="size-3.5 text-amber-500" />;
      default:
        return <Globe className="size-3.5 text-slate-400" />;
    }
  };

  const getStatusBadge = (status: RunStatus) => {
    switch (status) {
      case "running":
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-mono font-medium text-amber-700 dark:text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-md">
            <span className="size-1.5 rounded-full bg-amber-500 animate-pulse" />
            Running
          </span>
        );
      case "completed":
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-mono font-medium text-emerald-700 dark:text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-md">
            <span className="size-1.5 rounded-full bg-emerald-500" />
            Verified
          </span>
        );
      case "failed":
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-mono font-medium text-rose-700 dark:text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded-md">
            <span className="size-1.5 rounded-full bg-rose-500" />
            Failed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-mono font-medium text-slate-500 dark:text-zinc-400 bg-slate-100 dark:bg-zinc-800 px-2 py-0.5 rounded-md">
            Queued
          </span>
        );
    }
  };

  const handleRowClick = (run: MissionRun) => {
    setSelectedRun(run);
    setIsDrawerOpen(true);
  };

  return (
    <div className="space-y-2.5">
      {/* Header with quiet typography */}
      <div className="flex items-center justify-between px-0.5 select-none">
        <div className="flex items-center gap-2">
          <Clock className="size-3.5 text-slate-400 dark:text-zinc-500" />
          <h3 className="text-xs font-mono uppercase tracking-wider text-slate-500 dark:text-zinc-400 font-semibold">
            Recent Activity
          </h3>
          {runs.length > 0 && (
            <span className="text-[10px] font-mono text-slate-400 dark:text-zinc-500 px-1.5 py-0.5 rounded bg-slate-100 dark:bg-zinc-800 border border-black/[0.04] dark:border-white/[0.05] tabular-nums">
              {runs.length} recorded
            </span>
          )}
        </div>

        {onNavigateTab && (
          <button
            onClick={() => onNavigateTab("pilot")}
            className="text-xs text-slate-500 hover:text-slate-900 dark:text-zinc-400 dark:hover:text-white transition-colors flex items-center gap-1 cursor-pointer font-sans font-medium group"
          >
            <span>Full Ledger</span>
            <ArrowRight className="size-3 transition-transform group-hover:translate-x-0.5" />
          </button>
        )}
      </div>

      {/* Stream Rows or Calm Empty State */}
      {recentRuns.length > 0 ? (
        <div className="rounded-xl border border-black/[0.06] dark:border-white/[0.08] bg-white dark:bg-[#121417] divide-y divide-black/[0.04] dark:divide-white/[0.05] overflow-hidden shadow-xs">
          {recentRuns.map((run) => (
            <div
              key={run.id}
              onClick={() => handleRowClick(run)}
              className="px-4 py-3 flex items-center justify-between gap-3 hover:bg-black/[0.015] dark:hover:bg-white/[0.02] transition-colors cursor-pointer group"
            >
              <div className="flex items-center gap-3 min-w-0">
                <div className="size-7 rounded-lg bg-slate-100 dark:bg-zinc-800/80 border border-black/[0.04] dark:border-white/[0.05] flex items-center justify-center shrink-0">
                  {getAppIcon(run.app)}
                </div>

                <div className="min-w-0 flex flex-col">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-slate-900 dark:text-zinc-100 truncate group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                      {run.title}
                    </span>
                    <span className="hidden sm:inline-flex text-[10px] font-mono text-slate-400 dark:text-zinc-500 tabular-nums">
                      {run.id}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-[11px] text-slate-500 dark:text-zinc-400 font-mono mt-0.5 tabular-nums">
                    <span>{run.app}</span>
                    <span className="text-slate-300 dark:text-zinc-600">•</span>
                    <span>{run.steps}</span>
                    <span className="text-slate-300 dark:text-zinc-600">•</span>
                    <span>{formatDuration(run.durationSec)}</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2.5 shrink-0">
                {getStatusBadge(run.status)}
                <ChevronRight className="size-3.5 text-slate-300 dark:text-zinc-600 group-hover:text-slate-600 dark:group-hover:text-zinc-300 transition-colors" />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="rounded-xl border border-dashed border-black/[0.08] dark:border-white/[0.08] bg-white/40 dark:bg-zinc-900/30 p-8 text-center">
          <p className="text-xs text-slate-500 dark:text-zinc-400 font-sans">
            Ready for your first instruction. Type a command above or click one of the suggested actions.
          </p>
        </div>
      )}

      {/* Slide-Over Contextual Drawer for Deep Audit */}
      <RunDetailDrawer
        run={selectedRun}
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
      />
    </div>
  );
}
