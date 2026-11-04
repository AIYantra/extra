import { useState } from "react";
import { Check, X, Brain, Trash2, Pencil, Cpu, HardDrive, Globe, Gauge } from "lucide-react";
import type { RiskLevel } from "../data/dashboard";
import { INITIAL_APPROVALS, INITIAL_MEMORIES } from "../data/dashboard";

const RISK_STYLE: Record<RiskLevel, string> = {
  High: "bg-rose-50 text-rose-700 border-rose-200",
  Medium: "bg-amber-50 text-amber-800 border-amber-200",
  Low: "bg-slate-100 text-slate-600 border-slate-200",
};

function Sparkline({ points, stroke }: { points: string; stroke: string }) {
  return (
    <svg className="w-16 h-7 shrink-0" viewBox="0 0 64 28" preserveAspectRatio="none" aria-hidden="true">
      <polyline points={points} fill="none" stroke={stroke} strokeWidth="1.75" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}

export function AttentionRail() {
  const [approvals, setApprovals] = useState(INITIAL_APPROVALS);
  const [memories, setMemories] = useState(INITIAL_MEMORIES);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [lastDecision, setLastDecision] = useState<string | null>(null);

  const decide = (id: string, verb: "Approved" | "Rejected") => {
    const item = approvals.find((a) => a.id === id);
    setApprovals((prev) => prev.filter((a) => a.id !== id));
    if (item) setLastDecision(`${verb}: ${item.title}`);
  };

  const startEdit = (id: string, fact: string) => { setEditingId(id); setDraft(fact); };
  const saveEdit = (id: string) => {
    if (!draft.trim()) return;
    setMemories((prev) => prev.map((m) => (m.id === id ? { ...m, fact: draft.trim() } : m)));
    setEditingId(null);
  };

  return (
    <div className="space-y-4">
      {/* Pending human approvals */}
      <section aria-label="Pending approvals" className="card rounded-xl p-4">
        <div className="flex items-center justify-between pb-2 mb-3 border-b border-slate-100">
          <h3 className="flex items-center gap-2 text-[13px] font-semibold text-[#0F172A]">
            <span className={`w-2 h-2 rounded-full ${approvals.length ? "bg-amber-500 animate-pulse" : "bg-[#10B981]"}`} aria-hidden="true" />
            Needs your approval
          </h3>
          <span className="text-[10px] font-mono bg-amber-50 text-amber-800 border border-amber-200 px-1.5 py-0.5 rounded font-semibold tabular-nums">{approvals.length} pending</span>
        </div>

        {lastDecision && approvals.length < INITIAL_APPROVALS.length && (
          <p className="mb-3 text-[11px] font-mono text-emerald-700 bg-emerald-50 border border-emerald-200/70 rounded-lg px-2.5 py-2" role="status">{lastDecision}</p>
        )}

        {approvals.length === 0 ? (
          <p className="py-3 text-center text-xs text-[#94A3B8] flex items-center justify-center gap-1.5">
            <Check size={16} strokeWidth={1.75} className="text-[#10B981]" /> Queue clear — no action needs you.
          </p>
        ) : (
          <div className="space-y-3">
            {approvals.map((a) => (
              <article key={a.id} className="p-3 rounded-lg border border-amber-200/80 bg-amber-50/40">
                <div className="flex items-start justify-between gap-2">
                  <h4 className="font-semibold text-[13px] text-[#0F172A] leading-snug">{a.title}</h4>
                  <span className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded border shrink-0 font-semibold ${RISK_STYLE[a.risk]}`}>{a.risk} risk</span>
                </div>
                <p className="text-[11px] text-slate-600 mt-1.5 font-mono leading-relaxed break-all">{a.detail}</p>
                <p className="text-[10px] font-mono text-[#94A3B8] mt-1">{a.app} · requested {a.requestedAgo}</p>
                <div className="flex items-center justify-end gap-2 mt-3 pt-2.5 border-t border-amber-100">
                  <button type="button" onClick={() => decide(a.id, "Rejected")} className="tactile h-8 px-3 rounded-lg text-[12px] font-semibold text-slate-600 bg-white hover:bg-slate-50 border border-[#DFE4EB] flex items-center gap-1">
                    <X size={16} strokeWidth={1.75} /> Reject
                  </button>
                  <button type="button" onClick={() => decide(a.id, "Approved")} className="tactile h-8 px-3.5 rounded-lg text-[12px] font-semibold bg-[#0284C7] hover:bg-[#0369A1] text-white flex items-center gap-1 shadow-sm">
                    <Check size={16} strokeWidth={1.75} /> Approve
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      {/* Inspectable memory ledger — editable / deletable */}
      <section aria-label="Memory ledger" className="card rounded-xl p-4">
        <div className="flex items-center justify-between pb-2 mb-3 border-b border-slate-100">
          <h3 className="flex items-center gap-2 text-[13px] font-semibold text-[#0F172A]"><Brain size={16} strokeWidth={1.75} className="text-[#10B981]" /> SOUL memory ledger</h3>
          <span className="text-[10px] font-mono text-[#94A3B8]">KùzuDB · {memories.length} facts</span>
        </div>
        <ul className="space-y-2">
          {memories.map((m) => (
            <li key={m.id} className="p-2.5 rounded-lg border border-slate-100 bg-slate-50/60 text-xs group">
              {editingId === m.id ? (
                <div>
                  <label htmlFor={`edit-${m.id}`} className="sr-only">Edit memory fact</label>
                  <textarea
                    id={`edit-${m.id}`}
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    rows={3}
                    autoFocus
                    className="focus-ring w-full rounded-md border border-[#0284C7] bg-white px-2 py-1.5 text-[12px] text-slate-800 resize-none"
                  />
                  <div className="flex justify-end gap-2 mt-2">
                    <button type="button" onClick={() => setEditingId(null)} className="tactile h-7 px-2.5 rounded-md text-[11px] font-semibold text-slate-600 bg-white border border-[#DFE4EB]">Cancel</button>
                    <button type="button" onClick={() => saveEdit(m.id)} className="tactile h-7 px-2.5 rounded-md text-[11px] font-semibold bg-[#0284C7] text-white">Save fact</button>
                  </div>
                </div>
              ) : (
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-slate-800 text-[12px] leading-snug font-medium">{m.fact}</p>
                    <p className="mt-1.5 flex items-center gap-1.5 text-[10px] font-mono text-[#94A3B8]">
                      <span className="inline-flex items-center gap-1 text-emerald-700 bg-emerald-50 border border-emerald-200/70 px-1.5 py-px rounded font-semibold"><Check size={12} strokeWidth={2} />{m.source}</span>
                      <span>{m.verifiedAt}</span>
                    </p>
                  </div>
                  <span className="flex shrink-0 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity duration-100">
                    <button type="button" onClick={() => startEdit(m.id, m.fact)} aria-label={`Edit memory: ${m.fact}`} className="tactile p-1.5 text-slate-400 hover:text-[#0284C7] rounded-md"><Pencil size={16} strokeWidth={1.75} /></button>
                    <button type="button" onClick={() => setMemories((prev) => prev.filter((x) => x.id !== m.id))} aria-label={`Forget memory: ${m.fact}`} className="tactile p-1.5 text-slate-400 hover:text-rose-600 rounded-md"><Trash2 size={16} strokeWidth={1.75} /></button>
                  </span>
                </div>
              )}
            </li>
          ))}
        </ul>
        {memories.length === 0 && <p className="text-xs text-[#94A3B8] text-center py-2">Ledger empty — verified facts will appear here.</p>}
      </section>

      {/* System health sparklines */}
      <section aria-label="System health" className="card rounded-xl p-4">
        <div className="flex items-center justify-between pb-2 mb-3 border-b border-slate-100">
          <h3 className="text-[13px] font-semibold text-[#0F172A]">System health</h3>
          <span className="text-[10px] font-mono text-emerald-600 font-semibold flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-[#10B981]" />100% operational</span>
        </div>
        <dl className="space-y-3 text-xs">
          <div className="flex items-center justify-between gap-3">
            <dt className="flex items-center gap-2 text-slate-600"><Cpu size={16} strokeWidth={1.75} className="text-slate-400" />CPU load</dt>
            <dd className="flex items-center gap-3"><Sparkline points="0,20 12,10 24,16 36,6 48,13 64,8" stroke="#0284C7" /><span className="font-mono font-semibold text-slate-800 tabular-nums w-12 text-right">8.4%</span></dd>
          </div>
          <div className="flex items-center justify-between gap-3">
            <dt className="flex items-center gap-2 text-slate-600"><HardDrive size={16} strokeWidth={1.75} className="text-slate-400" />Memory</dt>
            <dd className="flex items-center gap-3"><Sparkline points="0,14 14,18 28,8 42,15 56,10 64,12" stroke="#10B981" /><span className="font-mono font-semibold text-slate-800 tabular-nums w-12 text-right">3.8 GB</span></dd>
          </div>
          <div className="flex items-center justify-between gap-3">
            <dt className="flex items-center gap-2 text-slate-600"><Gauge size={16} strokeWidth={1.75} className="text-slate-400" />Grounding p95</dt>
            <dd className="flex items-center gap-3"><Sparkline points="0,10 14,12 28,7 42,10 56,6 64,8" stroke="#0284C7" /><span className="font-mono font-semibold text-slate-800 tabular-nums w-12 text-right">12ms</span></dd>
          </div>
          <div className="flex items-center justify-between gap-3 pt-2 border-t border-slate-100">
            <dt className="flex items-center gap-2 text-slate-600"><Globe size={16} strokeWidth={1.75} className="text-slate-400" />Chrome sessions</dt>
            <dd className="font-mono font-semibold text-slate-800 tabular-nums">2 active · 0 crashed</dd>
          </div>
        </dl>
      </section>
    </div>
  );
}
