import React from "react";
import { BadgePrimary } from "@/src/components/ui/badge";
import { Check, X } from "lucide-react";

export const BenchmarkSection: React.FC = () => {
  const metrics = [
    {
      feature: "Calculator Math & Formula Run",
      extra: "1 turn (< 50ms via extra_subtask_run)",
      generic: "4 turns (~18,000ms blind screenshot loop)",
    },
    {
      feature: "Document Creation & Briefing",
      extra: "1 turn (Direct write to disk + Notepad launch)",
      generic: "12 turns (Character-by-character typing)",
    },
    {
      feature: "Visual Settle & Change Detection",
      extra: "12ms (SOUL-Gateman hardware hash)",
      generic: "3,000ms (Arbitrary sleep delay per action)",
    },
    {
      feature: "Perception & Grounding Latency",
      extra: "Zero-Hop Protocol (distilled_ui included)",
      generic: "Separate tool call + 10s base64 image parsing",
    },
    {
      feature: "Window Snapping & Tile Arranging",
      extra: "15ms (extra_snap_layout via Win32 SetWindowPos)",
      generic: "Multi-turn Win+Arrow hotkey loops with errors",
    },
    {
      feature: "Deliverable Provenance Verification",
      extra: "Cryptographic lineage check (SHA-256 + metadata)",
      generic: "Unverified hallucinated success claims",
    },
  ];

  return (
    <section id="benchmarks" className="py-20 md:py-28 bg-background-2/70 border-t border-stroke-1">
      <div className="main-container mx-auto max-w-[1200px] px-4 sm:px-6">
        <div className="text-center space-y-4 mb-16">
          <div className="flex justify-center">
            <BadgePrimary>
              <span>BENCHMARK DATA & SPEED ADVANTAGE</span>
            </BadgePrimary>
          </div>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold text-secondary tracking-tight">
            Extra vs Generic Computer-Use Bots
          </h2>
          <p className="text-secondary/70 max-w-2xl mx-auto text-base sm:text-lg">
            Built from first principles for sub-millisecond dispatch, action chunking, and deterministic execution.
          </p>
        </div>

        {/* 3 Metric Hero Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          <div className="p-6 rounded-2xl bg-white border border-stroke-1 shadow-sm text-center">
            <span className="text-3xl sm:text-4xl font-bold text-secondary font-mono tracking-tight">
              12ms
            </span>
            <h4 className="font-semibold text-secondary text-sm mt-1">Optical Settle Detection</h4>
            <p className="text-xs text-secondary/60 mt-1">SOUL-Gateman Tier 1 perception</p>
          </div>

          <div className="p-6 rounded-2xl bg-white border border-stroke-1 shadow-sm text-center">
            <span className="text-3xl sm:text-4xl font-bold text-primary-600 font-mono tracking-tight">
              1 Turn
            </span>
            <h4 className="font-semibold text-secondary text-sm mt-1">Macro Action Chunking</h4>
            <p className="text-xs text-secondary/60 mt-1">Zero single-action turn waste</p>
          </div>

          <div className="p-6 rounded-2xl bg-white border border-stroke-1 shadow-sm text-center">
            <span className="text-3xl sm:text-4xl font-bold text-emerald-600 font-mono tracking-tight">
              100%
            </span>
            <h4 className="font-semibold text-secondary text-sm mt-1">Ground-Truth Lineage</h4>
            <p className="text-xs text-secondary/60 mt-1">Zero fake export substitutions</p>
          </div>
        </div>

        {/* Comparison Table */}
        <div className="rounded-2xl border border-stroke-1 bg-white overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs sm:text-sm">
              <thead>
                <tr className="border-b border-stroke-1 bg-background-3/80 font-mono text-[11px] text-secondary/60">
                  <th className="py-3.5 px-6 font-semibold">Workflow Operation</th>
                  <th className="py-3.5 px-6 font-semibold text-primary-700 bg-primary-50/50">
                    Extra Engine (v2.4)
                  </th>
                  <th className="py-3.5 px-6 font-semibold">Generic Computer-Use</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stroke-2 font-mono text-xs">
                {metrics.map((m, i) => (
                  <tr key={i} className="hover:bg-background-2/60 transition-colors">
                    <td className="py-3.5 px-6 font-medium text-secondary">{m.feature}</td>
                    <td className="py-3.5 px-6 font-semibold text-emerald-800 bg-emerald-50/30 flex items-center gap-2">
                      <Check className="w-4 h-4 text-emerald-600 shrink-0" />
                      <span>{m.extra}</span>
                    </td>
                    <td className="py-3.5 px-6 text-secondary/60">
                      <div className="flex items-center gap-2">
                        <X className="w-4 h-4 text-rose-500 shrink-0" />
                        <span>{m.generic}</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  );
};
