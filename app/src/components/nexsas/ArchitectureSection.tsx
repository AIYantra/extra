import React, { useState } from "react";
import { BadgePrimary } from "@/src/components/ui/badge";
import {
  Eye,
  Zap,
  FolderCheck,
  FileSpreadsheet,
  Plane,
  Music,
  CheckCircle2
} from "lucide-react";

export const ArchitectureSection: React.FC = () => {
  const magicPrompts = [
    {
      id: "downloads",
      prompt: "Clean up my Downloads folder.",
      app: "Finder / Explorer",
      actionText: "Scanned 42 loose files · Organized into /Q3-Taxes, /Decks, and /Archive",
      icon: FolderCheck,
      badge: "Files Organized",
      badgeColor: "bg-primary-50 text-primary-700 border-primary-200",
      detail: "No duplicate names, PDFs categorized, screenshots triaged in 1.4s.",
    },
    {
      id: "excel",
      prompt: "Open Excel and total these invoices.",
      app: "Microsoft Excel",
      actionText: "Opened invoices.xlsx · Calculated SUM(B2:B48) · Output $4,820.50",
      icon: FileSpreadsheet,
      badge: "Formulas Verified",
      badgeColor: "bg-emerald-50 text-emerald-700 border-emerald-300",
      detail: "Extracted 48 receipt totals, calculated tax deductions, formatted table.",
    },
    {
      id: "flights",
      prompt: "Find these flights and put the details in a note.",
      app: "Browser & Notes",
      actionText: "Navigated Google Flights · Extracted JFK ➔ SFO · Saved to Apple Notes",
      icon: Plane,
      badge: "Itinerary Saved",
      badgeColor: "bg-blue-50 text-blue-700 border-blue-300",
      detail: "Found nonstop $348 fares, copied departure times, created clean note.",
    },
    {
      id: "spotify",
      prompt: "Open Spotify and play some focus music.",
      app: "Spotify",
      actionText: "Launched Spotify · Searched 'Deep Focus' · Started seamless playback",
      icon: Music,
      badge: "Playing Now",
      badgeColor: "bg-purple-50 text-purple-700 border-purple-300",
      detail: "Brought Spotify window up, selected playlist, pressed play instantly.",
    },
  ];

  const [activePromptId, setActivePromptId] = useState("downloads");
  const activePrompt = magicPrompts.find((p) => p.id === activePromptId) || magicPrompts[0];
  const Icon = activePrompt.icon;

  return (
    <section id="architecture" className="py-20 md:py-28 bg-background-2/60 border-y border-stroke-1">
      <div className="main-container mx-auto max-w-[1200px] px-4 sm:px-6">
        <div className="text-center space-y-4 mb-14">
          <div className="flex justify-center">
            <BadgePrimary>
              <span>DUAL-PLANE ARCHITECTURAL MODEL</span>
            </BadgePrimary>
          </div>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold text-secondary tracking-tight">
            Two distinct execution planes. Zero guesswork.
          </h2>
          <p className="text-secondary/70 max-w-2xl mx-auto text-base sm:text-lg">
            Unlike brittle screenshot-only bots, Extra blends continuous optical perception with deterministic local code bridges.
          </p>
        </div>

        {/* Interactive Prompt Pills */}
        <div className="flex flex-wrap items-center justify-center gap-2 sm:gap-3 mb-10">
          {magicPrompts.map((p) => (
            <button
              key={p.id}
              onClick={() => setActivePromptId(p.id)}
              className={`px-4 py-2 rounded-full text-xs sm:text-sm font-medium border transition-all cursor-pointer ${
                activePromptId === p.id
                  ? "bg-secondary text-white border-secondary shadow-md"
                  : "bg-white text-secondary/70 border-stroke-1 hover:border-stroke-3 hover:text-secondary"
              }`}
            >
              <span>"{p.prompt}"</span>
            </button>
          ))}
        </div>

        {/* Active Prompt Preview Bar */}
        <div className="mb-8 p-4 rounded-2xl bg-white border border-stroke-1 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-background-3 flex items-center justify-center text-primary-600 shrink-0">
              <Icon className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-semibold text-secondary text-sm">{activePrompt.app}</span>
                <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${activePrompt.badgeColor}`}>
                  {activePrompt.badge}
                </span>
              </div>
              <p className="text-xs text-secondary/70 mt-0.5 font-mono">{activePrompt.actionText}</p>
            </div>
          </div>
          <span className="text-xs text-secondary/50 font-medium italic">{activePrompt.detail}</span>
        </div>

        {/* Dual-Plane Comparison Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Plane 1: Optical Grounding */}
          <div className="p-6 sm:p-8 rounded-[20px] bg-white border border-stroke-1 shadow-sm hover:shadow-md transition-all space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center">
                  <Eye className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="font-bold text-secondary text-base">Plane 1: Optical Perception</h3>
                  <span className="text-[11px] font-mono text-emerald-700">Project SOUL Grounding</span>
                </div>
              </div>
              <span className="text-xs font-mono font-semibold px-2 py-1 rounded bg-emerald-50 text-emerald-800 border border-emerald-200">
                12ms Latency
              </span>
            </div>

            <p className="text-xs sm:text-sm text-secondary/70 leading-relaxed">
              When UI controls are custom, web-based, or lack accessibility trees (e.g. Canva canvas or Google Sheets grid), SOUL scans the glass using OCR grounding and Set-of-Marks, calculating pixel coordinates without blind guessing.
            </p>

            <ul className="space-y-2 text-xs text-secondary/80 font-mono pt-2 border-t border-stroke-2">
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                Sub-15ms visual settle detection via SOUL-Gateman
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                Zero-Hop Perception Protocol (distilled UI included)
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                Natural continuous Bezier splines on creative canvas
              </li>
            </ul>
          </div>

          {/* Plane 2: Deterministic Code Bridge */}
          <div className="p-6 sm:p-8 rounded-[20px] bg-white border border-stroke-1 shadow-sm hover:shadow-md transition-all space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-primary-50 text-primary-700 flex items-center justify-center">
                  <Zap className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="font-bold text-secondary text-base">Plane 2: Deterministic Bridge</h3>
                  <span className="text-[11px] font-mono text-primary-700">extra_execute_bridge</span>
                </div>
              </div>
              <span className="text-xs font-mono font-semibold px-2 py-1 rounded bg-primary-50 text-primary-800 border border-primary-200">
                Sub-Millisecond
              </span>
            </div>

            <p className="text-xs sm:text-sm text-secondary/70 leading-relaxed">
              When high-speed deterministic execution is available, Extra bypasses fragile GUI hunting completely. It executes native Win32/macOS system calls, Blender BPY scripts, and batch file system primitives atomically in 1 turn.
            </p>

            <ul className="space-y-2 text-xs text-secondary/80 font-mono pt-2 border-t border-stroke-2">
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-primary-600" />
                Instant Win32 KEYEVENTF_UNICODE typing (VK_PACKET)
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-primary-600" />
                extra_fs_batch: Controlled Folder Access compliant
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-primary-600" />
                Cryptographic provenance & physical file lineage verification
              </li>
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
};
