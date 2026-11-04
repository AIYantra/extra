import { useState } from "react";
import type { FormEvent } from "react";
import { Play, History, ShieldCheck } from "lucide-react";
import { RECENT_PRESETS } from "../data/dashboard";

interface ComposerCardProps {
  onRunIntent: (intent: string) => void;
  isExecuting?: boolean;
}

const GROUNDING_MODES = ["Dual-Plane", "Visual only", "Bridge only"] as const;

export function ComposerCard({ onRunIntent, isExecuting = false }: ComposerCardProps) {
  const [intent, setIntent] = useState("");
  const [mode, setMode] = useState<(typeof GROUNDING_MODES)[number]>("Dual-Plane");
  const [hitl, setHitl] = useState(true);
  const canRun = intent.trim().length > 0 && !isExecuting;

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!canRun) return;
    onRunIntent(intent.trim());
  };

  return (
    <section aria-label="Intent composer" className="card rounded-xl p-5">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <h2 className="text-[15px] font-semibold text-[#0F172A] tracking-tight">What should the agent automate?</h2>
        <div className="flex items-center gap-2" role="group" aria-label="Grounding mode">
          {GROUNDING_MODES.map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => setMode(m)}
              aria-pressed={mode === m}
              className={`tactile px-2.5 py-1.5 rounded-lg text-[11px] font-semibold border ${mode === m ? "bg-sky-50 text-[#0284C7] border-sky-200" : "bg-white text-slate-500 border-[#DFE4EB] hover:text-slate-800"}`}
            >
              {m}
            </button>
          ))}
        </div>
      </div>

      <form onSubmit={submit}>
        <label htmlFor="intent-input" className="sr-only">Describe the desktop task to automate</label>
        <div className="flex items-stretch gap-2">
          <input
            id="intent-input"
            type="text"
            value={intent}
            onChange={(e) => setIntent(e.target.value)}
            placeholder="e.g. Export the Q3 financial report from Sheets to a verified PDF…"
            autoComplete="off"
            className="focus-ring flex-1 min-w-0 h-12 bg-slate-50 border border-[#DFE4EB] hover:border-slate-300 focus:border-[#0284C7] focus:bg-white rounded-lg px-4 text-[15px] text-[#0F172A] placeholder:text-[#94A3B8] transition-colors duration-100"
          />
          <button
            type="submit"
            disabled={!canRun}
            className={`tactile shrink-0 h-12 px-5 rounded-lg font-semibold text-[13px] flex items-center gap-2 ${canRun ? "bg-[#0284C7] text-white hover:bg-[#0369A1] shadow-sm" : "bg-slate-100 text-slate-400 cursor-not-allowed"}`}
          >
            {isExecuting ? (
              <><span className="w-4 h-4 border-2 border-white/70 border-t-transparent rounded-full animate-spin" aria-hidden="true" /><span>Dispatching…</span></>
            ) : (
              <><span>Run Intent</span><Play size={16} strokeWidth={1.75} className="fill-current" /></>
            )}
          </button>
        </div>
        <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-[11px] text-[#94A3B8]">
          <span className="font-mono">Enter to run · Esc clears focus</span>
          <button
            type="button"
            role="switch"
            aria-checked={hitl}
            onClick={() => setHitl((v) => !v)}
            className="tactile flex items-center gap-2 font-medium text-slate-600"
          >
            <ShieldCheck size={16} strokeWidth={1.75} className={hitl ? "text-[#10B981]" : "text-slate-400"} />
            <span>Human-in-loop approvals {hitl ? "on" : "off"}</span>
            <span className={`relative w-8 h-[18px] rounded-full ${hitl ? "bg-[#10B981]" : "bg-slate-200"}`} aria-hidden="true">
              <span className={`absolute top-[2px] w-[14px] h-[14px] rounded-full bg-white shadow transition-all duration-100 ${hitl ? "left-[16px]" : "left-[2px]"}`} />
            </span>
          </button>
        </div>
      </form>

      {/* Real past runs — one click re-runs */}
      <div className="mt-4 pt-3 border-t border-slate-100 flex flex-wrap items-center gap-2">
        <span className="flex items-center gap-1.5 text-[11px] text-[#94A3B8] font-medium"><History size={16} strokeWidth={1.75} /> Recent</span>
        {RECENT_PRESETS.map((p) => (
          <button
            key={p.label}
            type="button"
            onClick={() => { setIntent(p.label); onRunIntent(p.label); }}
            title={`${p.runs} — click to re-run`}
            className="tactile min-w-0 max-w-full text-[12px] bg-slate-50 hover:bg-sky-50 border border-[#DFE4EB] hover:border-sky-200 text-slate-600 hover:text-[#0F172A] pl-1.5 pr-2.5 py-1.5 rounded-lg flex items-center gap-2 font-medium"
          >
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white border border-[#DFE4EB] text-slate-600 font-semibold shrink-0">{p.app}</span>
            <span className="truncate min-w-0 max-w-[300px]">{p.label}</span>
            <span className="text-[10px] font-mono text-[#94A3B8] shrink-0 hidden sm:inline">{p.runs}</span>
          </button>
        ))}
      </div>
    </section>
  );
}
