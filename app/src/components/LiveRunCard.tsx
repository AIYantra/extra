import { useEffect, useState } from "react";
import { Pause, Play, Square, MousePointer2, CheckCircle2, Clock, Maximize2, Lock, LockOpen } from "lucide-react";
import { EXECUTION_STEPS, formatDuration } from "../data/dashboard";

interface LiveRunCardProps {
  isPaused: boolean;
  onTogglePause: () => void;
  onStop: () => void;
  activeIntent: string;
}

const WAYPOINTS = [
  { x: 1420, y: 780 },
  { x: 984, y: 412 },
  { x: 762, y: 638 },
  { x: 1296, y: 704 },
];

export function LiveRunCard({ isPaused, onTogglePause, onStop, activeIntent }: LiveRunCardProps) {
  const [takeControl, setTakeControl] = useState(false);
  const [elapsed, setElapsed] = useState(102);
  const [wp, setWp] = useState(0);

  useEffect(() => {
    if (isPaused || takeControl) return;
    const t = window.setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => window.clearInterval(t);
  }, [isPaused, takeControl]);

  useEffect(() => {
    if (isPaused || takeControl) return;
    const t = window.setInterval(() => setWp((i) => (i + 1) % WAYPOINTS.length), 3000);
    return () => window.clearInterval(t);
  }, [isPaused, takeControl]);

  const coord = WAYPOINTS[wp];
  const doneCount = EXECUTION_STEPS.filter((s) => s.status === "done").length;

  return (
    <section aria-label="Live run cockpit" className="card rounded-xl p-5">
      {/* Header + permanently anchored controls (Fitts) */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-100">
        <div className="flex items-center gap-3 min-w-0">
          <span className="relative flex h-2.5 w-2.5 shrink-0" aria-hidden="true">
            <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-60 ${isPaused || takeControl ? "bg-amber-400" : "bg-emerald-400"}`} />
            <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${isPaused || takeControl ? "bg-amber-500" : "bg-[#10B981]"}`} />
          </span>
          <div className="min-w-0">
            <h2 className="font-semibold text-[#0F172A] text-sm tracking-tight truncate">
              {takeControl ? "Operator controlling — pilot holding" : isPaused ? "Session paused by operator" : "Live desktop pilot in progress"}
            </h2>
            <p className="text-[11px] text-slate-500 truncate max-w-[420px]">{activeIntent}</p>
          </div>
          <span className="hidden md:inline text-[11px] font-mono text-slate-500 bg-slate-100 px-2 py-1 rounded shrink-0">Task #run-8924</span>
        </div>
        <div className="flex items-center gap-2">
          <button type="button" onClick={() => setTakeControl((v) => !v)} aria-pressed={takeControl} className={`tactile h-9 px-3 rounded-lg text-xs font-semibold border flex items-center gap-1.5 ${takeControl ? "bg-[#0F172A] text-white border-[#0F172A]" : "bg-white text-slate-700 border-[#DFE4EB] hover:bg-slate-50"}`}>
            {takeControl ? <LockOpen size={16} strokeWidth={1.75} /> : <Lock size={16} strokeWidth={1.75} />}
            {takeControl ? "Release" : "Take Control"}
          </button>
          <button type="button" onClick={onTogglePause} className={`tactile h-9 px-4 rounded-lg text-xs font-semibold flex items-center gap-1.5 ${isPaused ? "bg-[#10B981] text-white hover:bg-emerald-600" : "bg-[#0F172A] text-white hover:bg-slate-800"}`}>
            {isPaused ? <Play size={16} strokeWidth={1.75} className="fill-current" /> : <Pause size={16} strokeWidth={1.75} />}
            {isPaused ? "Resume Pilot" : "Pause"}
          </button>
          <button type="button" onClick={onStop} title="Abort run and release OS hooks" className="tactile h-9 px-3 rounded-lg text-xs font-semibold text-rose-600 border border-rose-200 hover:bg-rose-50 flex items-center gap-1.5 ml-3">
            <Square size={16} strokeWidth={1.75} className="fill-current" /> Abort
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-5 mt-4">
        {/* Simulated screen monitor 16:10 */}
        <div className="xl:col-span-7">
          <div className="relative aspect-[16/10] bg-slate-900 rounded-lg overflow-hidden border border-slate-800 flex flex-col">
            <div className="h-8 bg-slate-800 px-3 flex items-center justify-between text-[11px] text-slate-300 border-b border-slate-700 shrink-0">
              <span className="flex items-center gap-2 font-mono truncate">
                <span className="flex gap-1.5 shrink-0" aria-hidden="true">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#FF5F57]" /><span className="w-2.5 h-2.5 rounded-full bg-[#FEBC2E]" /><span className="w-2.5 h-2.5 rounded-full bg-[#28C840]" />
                </span>
                <span className="truncate">Sheets — Q3 Financials.xlsx</span>
              </span>
              <span className="flex items-center gap-2 shrink-0">
                <span className="text-[10px] text-slate-400 font-mono tabular-nums hidden lg:inline">1920 × 1080 · 60 fps</span>
                <button type="button" aria-label="Expand monitor" className="tactile text-slate-400 hover:text-white p-0.5"><Maximize2 size={16} strokeWidth={1.75} /></button>
              </span>
            </div>

            <div className="relative flex-1 bg-slate-950 p-4 flex items-center justify-center overflow-hidden">
              {/* Simulated Sheets window */}
              <div className="relative w-[94%] bg-white rounded-md shadow-xl border border-slate-200 p-3 select-none">
                <div className="flex items-center justify-between pb-2 border-b border-slate-100 text-[10px] text-slate-500 font-mono">
                  <span className="flex items-center gap-2 relative">
                    <span className="font-bold text-slate-800 text-[11px]">Sheets</span>
                    <span className="relative px-1 rounded border border-sky-400 bg-sky-50 text-sky-700">File
                      <span className="absolute -top-4 left-0 bg-sky-600 text-white text-[8px] px-1 rounded whitespace-nowrap">MENU · 98.2%</span>
                    </span>
                    <span>Edit</span><span>Insert</span><span>Data</span>
                  </span>
                  <span className="text-emerald-600 font-semibold flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-[#10B981]" />Connected</span>
                </div>
                <div className="text-[11px] font-mono mt-2 space-y-1.5">
                  <div className="grid grid-cols-[1.4fr_1fr_1fr_1.1fr] gap-2 text-slate-400 border-b border-slate-100 pb-1 text-right"><span className="text-left">Account item</span><span>Q1</span><span>Q2</span><span className="font-bold text-slate-800">Q3 forecast</span></div>
                  <div className="grid grid-cols-[1.4fr_1fr_1fr_1.1fr] gap-2 text-slate-600 text-right"><span className="text-left truncate">Subscription ARR</span><span className="tabular-nums">$1,420,000</span><span className="tabular-nums">$1,680,000</span><span className="text-[#0284C7] font-semibold tabular-nums">$1,940,000</span></div>
                  <div className="grid grid-cols-[1.4fr_1fr_1fr_1.1fr] gap-2 text-slate-600 text-right"><span className="text-left">Pilot seats</span><span className="tabular-nums">$240,000</span><span className="tabular-nums">$310,000</span><span className="text-[#0284C7] font-semibold tabular-nums">$485,000</span></div>
                  <div className="grid grid-cols-[1.4fr_1fr_1fr_1.1fr] gap-2 items-center text-slate-900 font-bold pt-1.5 border-t border-slate-200 text-right">
                    <span className="text-left">Total net revenue</span><span className="tabular-nums">$1,660,000</span><span className="tabular-nums">$1,990,000</span>
                    <span className="relative justify-self-end px-2 py-0.5 bg-emerald-50 border-[1.5px] border-[#10B981] rounded text-emerald-800 tabular-nums">$2,425,000
                      <span className="absolute -top-4 -right-1 bg-emerald-600 text-white text-[8px] px-1 rounded whitespace-nowrap">TARGET D14 · 99.8%</span>
                    </span>
                  </div>
                </div>
                <div className="text-[9px] text-slate-400 font-mono flex justify-between border-t border-slate-100 pt-1.5 mt-2"><span>Revenue · D14 selected</span><span>=SUM(D2:D13)</span></div>

                {/* Optical cursor flight */}
                <div className={`absolute pointer-events-none ${takeControl || isPaused ? "" : "cursor-flight"}`} style={{ top: "72%", right: "38%" }} aria-hidden="true">
                  <span className="flex items-center gap-1.5">
                    <MousePointer2 size={16} strokeWidth={1.75} className="text-emerald-500 fill-emerald-400 drop-shadow" />
                    <span className="bg-slate-900 text-emerald-300 text-[9px] font-mono px-1.5 py-0.5 rounded border border-emerald-500/40 tabular-nums">X:{coord.x} Y:{coord.y}</span>
                  </span>
                </div>
              </div>

              {takeControl && (
                <div className="absolute top-3 left-1/2 -translate-x-1/2 bg-amber-400 text-amber-950 text-[11px] font-bold px-3 py-1.5 rounded-full shadow">OPERATOR CONTROL — pilot inputs held</div>
              )}
            </div>

            <div className="h-7 bg-slate-900 px-3 flex items-center justify-between text-[10px] font-mono text-slate-400 border-t border-slate-800 shrink-0">
              <span className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-[#10B981]" />SOUL grounding · sub-15ms</span>
              <span className="tabular-nums">PID 14088 · win32 · X:{coord.x} Y:{coord.y}</span>
            </div>
          </div>
          <div className="mt-2 flex justify-between text-[11px] font-mono text-[#94A3B8]">
            <span>Elapsed <span className="text-slate-700 font-semibold tabular-nums">{formatDuration(elapsed)}</span></span>
            <span>Actions <span className="text-slate-700 font-semibold tabular-nums">12</span> · Errors <span className="text-emerald-600 font-semibold tabular-nums">0</span></span>
          </div>
        </div>

        {/* Vertical execution timeline */}
        <div className="xl:col-span-5 flex flex-col">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-500">Execution steps</h3>
            <span className="text-[11px] font-mono text-[#94A3B8] tabular-nums">Step {doneCount + 1} of {EXECUTION_STEPS.length}</span>
          </div>
          <div className="h-1.5 bg-slate-100 rounded-full mt-3 overflow-hidden" role="progressbar" aria-valuenow={60} aria-valuemin={0} aria-valuemax={100} aria-label="Run progress 60 percent">
            <div className="h-full bg-[#10B981] rounded-full transition-all duration-500" style={{ width: "60%" }} />
          </div>
          <ol className="mt-3 space-y-0 relative">
            {EXECUTION_STEPS.map((s, i) => (
              <li key={s.id} className="relative flex gap-3 pb-3 last:pb-0">
                {i < EXECUTION_STEPS.length - 1 && <span className={`absolute left-[7px] top-5 bottom-0 w-px ${s.status === "done" ? "bg-emerald-200" : "bg-slate-200"}`} aria-hidden="true" />}
                <span className="relative shrink-0 mt-0.5">
                  {s.status === "done" && <CheckCircle2 size={16} strokeWidth={1.75} className="text-[#10B981] bg-white" />}
                  {s.status === "doing" && <span className="relative flex h-4 w-4"><span className="animate-ping absolute h-full w-full rounded-full bg-emerald-400 opacity-60" /><span className="relative rounded-full h-4 w-4 bg-[#10B981] border-[3px] border-white shadow" /></span>}
                  {s.status === "queued" && <Clock size={16} strokeWidth={1.75} className="text-slate-300 bg-white" />}
                </span>
                <div className={`flex-1 min-w-0 p-2.5 rounded-lg border ${s.status === "doing" ? "border-emerald-300 bg-emerald-50/60" : s.status === "done" ? "border-[#DFE4EB] bg-white" : "border-slate-100 bg-slate-50/60"}`}>
                  <div className="flex items-center justify-between gap-2">
                    <span className={`font-mono text-[11px] font-semibold truncate ${s.status === "queued" ? "text-slate-400" : "text-slate-800"}`}>{s.tool}</span>
                    {s.durationMs !== undefined && <span className="font-mono text-[10px] text-[#94A3B8] tabular-nums shrink-0">{s.durationMs}ms{s.grounding ? ` · ${s.grounding}` : ""}</span>}
                  </div>
                  <p className={`mt-0.5 text-[11px] truncate ${s.status === "queued" ? "text-slate-400" : "text-slate-500"}`}>{s.target}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}
