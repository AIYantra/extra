import { useMemo, useState } from "react";
import { ArrowUpRight, RotateCcw, Copy, Check } from "lucide-react";
import type { RunStatus } from "../data/dashboard";
import { MISSION_RUNS, formatDuration } from "../data/dashboard";

type Filter = "all" | RunStatus;

const FILTERS: { id: Filter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "running", label: "Running" },
  { id: "completed", label: "Completed" },
  { id: "failed", label: "Failed" },
  { id: "queued", label: "Queued" },
];

const STATUS_META: Record<RunStatus, { dot: string; text: string; label: string }> = {
  running: { dot: "bg-[#10B981] animate-pulse", text: "text-emerald-700", label: "Running" },
  completed: { dot: "bg-slate-400", text: "text-slate-600", label: "Completed" },
  failed: { dot: "bg-rose-500", text: "text-rose-600", label: "Failed" },
  queued: { dot: "bg-slate-300", text: "text-slate-400", label: "Queued" },
};

export function RunQueueTable() {
  const [filter, setFilter] = useState<Filter>("all");
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [retried, setRetried] = useState<ReadonlySet<string>>(new Set());

  const maxDuration = useMemo(() => Math.max(...MISSION_RUNS.map((r) => r.durationSec), 1), []);
  const counts = useMemo(() => {
    const c: Record<Filter, number> = { all: MISSION_RUNS.length, running: 0, completed: 0, failed: 0, queued: 0 };
    for (const r of MISSION_RUNS) c[r.status] += 1;
    return c;
  }, []);

  const visible = MISSION_RUNS.filter((r) => filter === "all" || r.status === filter);

  const copyLineage = async (id: string, lineage: string) => {
    try { await navigator.clipboard.writeText(lineage); } catch { /* clipboard unavailable in some webviews */ }
    setCopiedId(id);
    window.setTimeout(() => setCopiedId((c) => (c === id ? null : c)), 1600);
  };

  return (
    <section aria-label="Execution audit table" className="card rounded-xl overflow-hidden">
      <div className="p-4 border-b border-slate-100 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-500">Execution audit &amp; lineage</h2>
          <p className="text-xs text-slate-500 mt-0.5">Every run is reproducible — steps, duration, and cryptographic lineage</p>
        </div>
        <div className="flex items-center gap-1 bg-slate-50 border border-[#DFE4EB] rounded-lg p-1 max-w-full overflow-x-auto" role="tablist" aria-label="Filter runs by status">
          {FILTERS.map((f) => (
            <button
              key={f.id}
              type="button"
              role="tab"
              aria-selected={filter === f.id}
              onClick={() => setFilter(f.id)}
              className={`tactile px-2.5 py-1.5 rounded-md text-[11px] font-semibold ${filter === f.id ? "bg-white text-[#0284C7] shadow-sm border border-[#DFE4EB]" : "text-slate-500 hover:text-slate-800 border border-transparent"}`}
            >
              {f.label} <span className="font-mono tabular-nums text-[#94A3B8]">{counts[f.id]}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs min-w-[920px]">
          <thead>
            <tr className="border-b border-slate-100 bg-slate-50/80 text-slate-500 font-mono text-[10px] uppercase tracking-wider">
              <th scope="col" className="py-2.5 px-5 font-semibold">Run · Intent</th>
              <th scope="col" className="py-2.5 px-3 font-semibold">App</th>
              <th scope="col" className="py-2.5 px-3 font-semibold">Status</th>
              <th scope="col" className="py-2.5 px-3 font-semibold">Started</th>
              <th scope="col" className="py-2.5 px-3 font-semibold w-44">Duration</th>
              <th scope="col" className="py-2.5 px-3 font-semibold">Steps</th>
              <th scope="col" className="py-2.5 px-3 font-semibold">Lineage</th>
              <th scope="col" className="py-2.5 px-5 font-semibold text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {visible.map((run) => {
              const status: RunStatus = retried.has(run.id) ? "queued" : run.status;
              const meta = STATUS_META[status];
              return (
                <tr key={run.id} className="hover:bg-slate-50/80 transition-colors duration-100 h-[52px]">
                  <td className="py-2.5 px-5 max-w-[340px]">
                    <span className="font-mono text-[10px] text-[#94A3B8] tabular-nums block">#{run.id}</span>
                    <span className="font-semibold text-[13px] text-[#0F172A] block truncate">{retried.has(run.id) ? `${run.title} (re-queued)` : run.title}</span>
                    {run.errorReason && status === "failed" && <span className="text-[11px] text-rose-600 font-mono block truncate mt-0.5">{run.errorReason}</span>}
                  </td>
                  <td className="py-2.5 px-3"><span className="px-2 py-1 rounded bg-slate-100 text-slate-700 font-mono text-[10px] font-semibold">{run.app}</span></td>
                  <td className="py-2.5 px-3 whitespace-nowrap">
                    <span className={`inline-flex items-center gap-1.5 font-semibold ${meta.text}`}><span className={`w-1.5 h-1.5 rounded-full ${meta.dot}`} aria-hidden="true" />{meta.label}</span>
                  </td>
                  <td className="py-2.5 px-3 font-mono text-slate-500 tabular-nums whitespace-nowrap">{run.started}</td>
                  <td className="py-2.5 px-3">
                    <span className="flex items-center gap-2">
                      <span className="w-16 h-1.5 bg-slate-100 rounded-full overflow-hidden shrink-0" aria-hidden="true">
                        <span className={`block h-full rounded-full ${status === "failed" ? "bg-rose-400" : status === "running" ? "bg-[#10B981]" : "bg-[#0284C7]"}`} style={{ width: `${Math.max(4, (run.durationSec / maxDuration) * 100)}%` }} />
                      </span>
                      <span className="font-mono text-slate-700 tabular-nums">{formatDuration(run.durationSec)}</span>
                    </span>
                  </td>
                  <td className="py-2.5 px-3 font-mono text-slate-500 tabular-nums whitespace-nowrap">{run.steps}</td>
                  <td className="py-2.5 px-3">
                    <span className="flex items-center gap-1.5">
                      <span className="font-mono text-[11px] text-slate-600 tabular-nums">{run.lineage}</span>
                      {run.lineage !== "—" && (
                        <button type="button" onClick={() => copyLineage(run.id, run.lineage)} aria-label={`Copy lineage hash for ${run.id}`} className="tactile p-1 text-slate-400 hover:text-[#0284C7] rounded">
                          {copiedId === run.id ? <Check size={16} strokeWidth={1.75} className="text-[#10B981]" /> : <Copy size={16} strokeWidth={1.75} />}
                        </button>
                      )}
                    </span>
                    <span className="text-[11px] text-slate-500 block truncate max-w-[220px]">{run.result}</span>
                  </td>
                  <td className="py-2.5 px-5 text-right whitespace-nowrap">
                    {status === "failed" ? (
                      <button type="button" onClick={() => setRetried((prev) => new Set(prev).add(run.id))} className="tactile h-8 px-3 rounded-lg text-[11px] font-semibold text-rose-700 hover:bg-rose-50 border border-rose-200 inline-flex items-center gap-1.5">
                        <RotateCcw size={16} strokeWidth={1.75} /> Retry
                      </button>
                    ) : (
                      <button type="button" aria-label={`Inspect run ${run.id}`} className="tactile p-2 text-slate-400 hover:text-[#0284C7] hover:bg-sky-50 rounded-lg"><ArrowUpRight size={16} strokeWidth={1.75} /></button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {visible.length === 0 && <p className="py-8 text-center text-xs text-[#94A3B8]">No runs with this status yet.</p>}
      </div>
    </section>
  );
}
