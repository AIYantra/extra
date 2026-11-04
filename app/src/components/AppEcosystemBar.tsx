import type { LucideIcon } from "lucide-react";
import { Table2, PenTool, Box, Paintbrush, NotebookText, Globe, ArrowRight } from "lucide-react";
import { HARNESS_APPS } from "../data/dashboard";

const APP_ICON: Record<string, LucideIcon> = {
  sheets: Table2,
  canva: PenTool,
  blender: Box,
  paint: Paintbrush,
  obsidian: NotebookText,
  chrome: Globe,
};

interface AppEcosystemBarProps {
  onLaunchApp: (app: string) => void;
}

export function AppEcosystemBar({ onLaunchApp }: AppEcosystemBarProps) {
  return (
    <section aria-label="Verified application harnesses" className="card rounded-xl p-4">
      <div className="flex items-center justify-between pb-2 mb-3 border-b border-slate-100">
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-500">Verified application harnesses</h3>
          <p className="text-xs text-slate-500 mt-0.5">Deterministic playbooks — click to focus and pre-fill an intent</p>
        </div>
        <span className="text-[11px] font-mono text-[#94A3B8] tabular-nums">6 connected</span>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
        {HARNESS_APPS.map((a) => {
          const Icon = APP_ICON[a.id] ?? Globe;
          return (
            <button
              key={a.id}
              type="button"
              onClick={() => onLaunchApp(a.name)}
              className="tactile p-3 rounded-lg border border-[#DFE4EB] hover:border-sky-300 hover:bg-sky-50/40 text-left group bg-white"
            >
              <span className="flex items-center justify-between mb-2">
                <span className="w-8 h-8 rounded-lg bg-slate-50 border border-slate-100 flex items-center justify-center text-slate-500 group-hover:text-[#0284C7] group-hover:border-sky-200 transition-colors duration-100">
                  <Icon size={16} strokeWidth={1.75} />
                </span>
                <span className="flex items-center gap-1 text-[10px] font-mono font-semibold text-emerald-700">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#10B981]" aria-hidden="true" />{a.status}
                </span>
              </span>
              <span className="block font-semibold text-[13px] text-[#0F172A] group-hover:text-[#0284C7] transition-colors duration-100">{a.name}</span>
              <span className="mt-2 pt-2 border-t border-slate-100 flex items-center justify-between text-[10px] font-mono text-[#94A3B8]">
                <span>{a.plane} · <span className="tabular-nums">{a.latency}</span></span>
                <ArrowRight size={16} strokeWidth={1.75} className="text-slate-300 group-hover:text-[#0284C7] group-hover:translate-x-0.5 transition-all duration-100" />
              </span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
