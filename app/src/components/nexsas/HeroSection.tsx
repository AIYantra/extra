import React, { useState } from "react";
import { BadgePrimary } from "@/src/components/ui/badge";
import { ButtonPrimary, ButtonSecondary } from "@/src/components/ui/button";
import {
  Activity,
  MousePointer,
  CheckCircle2,
  Lock,
  Pause,
  Layers
} from "lucide-react";

export const HeroSection: React.FC = () => {
  const [viewMode, setViewMode] = useState<"workstation" | "workflow">("workstation");
  const [isPaused, setIsPaused] = useState(false);
  const [isControlTaken, setIsControlTaken] = useState(false);

  return (
    <section className="relative isolate overflow-hidden pt-28 pb-16 md:pt-36 md:pb-24">
      {/* Static ambient radial grid background from Nexsas */}
      <div className="pointer-events-none absolute inset-0 z-0 overflow-hidden">
        <div className="absolute top-[-10%] left-1/2 -translate-x-1/2 h-[520px] w-[850px] rounded-full bg-[radial-gradient(ellipse_at_center,rgba(134,79,254,0.08)_0%,rgba(35,238,214,0.04)_40%,transparent_70%)]" />
        <div className="absolute top-[35%] left-1/2 -translate-x-1/2 h-[450px] w-[750px] rounded-full bg-[radial-gradient(ellipse_at_center,rgba(134,79,254,0.05)_0%,transparent_65%)]" />
        <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(26,26,28,0.02)_1px,transparent_1px),linear-gradient(to_bottom,rgba(26,26,28,0.02)_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_40%,#000_60%,transparent_100%)] opacity-70" />
      </div>

      <div className="main-container relative z-10 mx-auto max-w-[1200px] px-4 sm:px-6">
        <div className="space-y-7 text-center md:space-y-10">
          {/* Eyebrow Badge */}
          <div className="flex justify-center">
            <BadgePrimary>
              <span>OPEN-SOURCE COMPUTER USE & CLOUD MCP FOR WINDOWS & MAC</span>
            </BadgePrimary>
          </div>

          {/* Master Headline */}
          <div className="space-y-3.5 max-w-4xl mx-auto">
            <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold text-secondary tracking-tight leading-[1.12]">
              Your AI can answer.{" "}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary-600 to-primary-400">
                Now it can act.
              </span>
            </h1>
            <p className="text-base sm:text-lg text-secondary/70 max-w-2xl mx-auto leading-relaxed font-normal">
              Extra gives your AI sovereign hands and eyes on Windows and macOS — opening applications, clicking buttons, synthesizing brush strokes, and executing multi-step desktop workflows.
            </p>
          </div>

          {/* Agency CTA Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-4 pt-1">
            <ButtonPrimary
              onClick={() => {
                const elem = document.getElementById("cockpit");
                elem?.scrollIntoView({ behavior: "smooth" });
              }}
              className="w-full sm:w-auto shadow-lg shadow-primary-500/20 hover:shadow-primary-500/35 transition-all"
              textClassName="text-center text-nowrap px-6 py-3 font-semibold text-sm text-white"
            >
              Launch Desktop Cockpit
            </ButtonPrimary>

            <a href="#architecture" className="w-full sm:w-auto">
              <ButtonSecondary
                className="w-full sm:w-auto bg-white hover:bg-background-2 text-secondary border border-stroke-1 shadow-2xs transition-all"
                textClassName="text-center text-nowrap px-5 py-3 font-medium text-sm text-secondary"
              >
                Inspect Dual-Plane Architecture
              </ButtonSecondary>
            </a>
          </div>

          {/* Micro Trust Line */}
          <div className="flex flex-wrap items-center justify-center gap-x-3 text-xs font-medium text-secondary/60 pt-1">
            <span>Sovereign Local Execution</span>
            <span className="text-secondary/30">·</span>
            <span>Zero Cloud Telemetry Leaks</span>
            <span className="text-secondary/30">·</span>
            <span>Sub-15ms Optical Grounding</span>
            <span className="text-secondary/30">·</span>
            <span className="text-primary-600 font-semibold">Standard MCP Interface</span>
          </div>

          {/* The Nexsas Agency Hero Visual Window */}
          <div
            id="cockpit"
            className="mt-8 mx-auto max-w-5xl overflow-hidden rounded-[24px] border border-stroke-1 bg-white p-3 sm:p-5 shadow-2xl transition-all"
          >
            {/* Top Window Bar */}
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-stroke-2 pb-3 px-1 sm:px-2">
              <div className="flex items-center gap-2">
                <span className="size-3 rounded-full bg-red-400" />
                <span className="size-3 rounded-full bg-amber-400" />
                <span className="size-3 rounded-full bg-emerald-400" />
                <span className="ml-2 text-xs font-mono text-secondary/70 font-medium truncate max-w-[260px] sm:max-w-none">
                  extra-agentd · Windows 11 Desktop Sandbox · Win32 API & Plane 2
                </span>
              </div>

              {/* View Mode Toggle */}
              <div className="flex items-center gap-1 rounded-lg bg-background-4 p-1 border border-stroke-2/60 text-xs font-medium">
                <button
                  type="button"
                  onClick={() => setViewMode("workstation")}
                  className={`flex items-center gap-1.5 px-3 py-1 rounded-md transition-all cursor-pointer ${
                    viewMode === "workstation"
                      ? "bg-white text-primary-600 font-semibold shadow-2xs"
                      : "text-secondary/60 hover:text-secondary"
                  }`}
                >
                  <Activity className="size-3.5 text-primary-500" />
                  <span>Live Workstation</span>
                </button>
                <button
                  type="button"
                  onClick={() => setViewMode("workflow")}
                  className={`flex items-center gap-1.5 px-3 py-1 rounded-md transition-all cursor-pointer ${
                    viewMode === "workflow"
                      ? "bg-white text-primary-600 font-semibold shadow-2xs"
                      : "text-secondary/60 hover:text-secondary"
                  }`}
                >
                  <Layers className="size-3.5 text-primary-500" />
                  <span>Execution Radar</span>
                </button>
              </div>
            </div>

            {/* Mode 1: Live Interactive Workstation */}
            {viewMode === "workstation" && (
              <div className="mt-4 grid grid-cols-1 lg:grid-cols-12 gap-5 text-left">
                {/* Left: 16:10 Desktop Monitor */}
                <div className="lg:col-span-8 flex flex-col justify-between">
                  <div className="relative aspect-[16/10] bg-slate-900 rounded-xl overflow-hidden border border-slate-800 shadow-inner flex flex-col">
                    {/* Simulated OS titlebar */}
                    <div className="h-7 bg-slate-800/90 px-3 flex items-center justify-between text-[11px] text-slate-300 border-b border-slate-700/80 font-mono">
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                        <span className="truncate">Active Glass: Google Sheets — Q3 Revenue Model.xlsx</span>
                      </div>
                      <span className="text-[10px] text-slate-400">1920 × 1080 @ 60fps</span>
                    </div>

                    {/* Desktop Content */}
                    <div className="relative flex-1 bg-slate-950 p-4 flex flex-col justify-center items-center overflow-hidden">
                      {/* Sheet Window */}
                      <div className="w-[94%] h-[88%] bg-white rounded-lg shadow-xl border border-slate-200 p-3 flex flex-col justify-between select-none">
                        <div className="flex items-center justify-between pb-2 border-b border-slate-100 text-[10px] text-slate-500 font-mono">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-slate-900">Google Sheets</span>
                            <span>File</span>
                            <span>Edit</span>
                            <span>Format</span>
                            <span>Data</span>
                          </div>
                          <span className="text-emerald-600 font-semibold">● SOUL Attached</span>
                        </div>

                        <div className="space-y-1.5 my-auto text-[11px] font-mono">
                          <div className="flex justify-between text-slate-400 border-b border-slate-100 pb-0.5">
                            <span>Account Category</span>
                            <span>Q1 Actual</span>
                            <span>Q2 Actual</span>
                            <span className="font-bold text-slate-900">Q3 Forecast</span>
                          </div>
                          <div className="flex justify-between text-slate-600">
                            <span>Enterprise ARR</span>
                            <span>$1,420,000</span>
                            <span>$1,680,000</span>
                            <span className="text-primary-600 font-semibold">$1,940,000</span>
                          </div>
                          <div className="flex justify-between text-slate-600">
                            <span>Autonomous Pilot Seats</span>
                            <span>$240,000</span>
                            <span>$310,000</span>
                            <span className="text-primary-600 font-semibold">$485,000</span>
                          </div>
                          <div className="relative flex justify-between text-slate-900 font-bold pt-1.5 border-t border-slate-200">
                            <span>Total Operating Revenue</span>
                            <span>$1,660,000</span>
                            <span>$1,990,000</span>
                            {/* SOUL Emerald Target Grounding Box */}
                            <div className="relative px-2 py-0.5 bg-emerald-50 border border-emerald-500 rounded text-emerald-800">
                              <span>$2,425,000</span>
                              <span className="absolute -top-3.5 -right-2 bg-emerald-600 text-white text-[8px] font-mono px-1 rounded shadow-xs">
                                TARGET: D14
                              </span>
                            </div>
                          </div>
                        </div>

                        <div className="text-[9px] text-slate-400 font-mono flex justify-between border-t border-slate-100 pt-1">
                          <span>Sheet: Revenue</span>
                          <span>Formula: =SUM(D2:D13)</span>
                        </div>
                      </div>

                      {/* Optical Cursor Flight Overlay */}
                      <div
                        className="absolute pointer-events-none transition-all duration-300"
                        style={{ top: "66%", right: "24%" }}
                      >
                        <div className="flex items-center gap-1.5">
                          <MousePointer className="w-4 h-4 text-emerald-400 fill-emerald-500 filter drop-shadow" />
                          <span className="bg-slate-900/90 text-emerald-300 text-[9px] font-mono px-1.5 py-0.5 rounded border border-emerald-500/40">
                            X: 1420 Y: 780
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Bottom Status */}
                    <div className="h-6 bg-slate-900 px-3 flex items-center justify-between text-[10px] font-mono text-slate-400 border-t border-slate-800">
                      <span className="flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                        Zero-Hop Perception Active (12ms Settle)
                      </span>
                      <span>PID: 21404 (win32)</span>
                    </div>
                  </div>
                </div>

                {/* Right: Stepper Timeline & Physical Controls */}
                <div className="lg:col-span-4 flex flex-col justify-between space-y-4">
                  <div>
                    <div className="flex items-center justify-between pb-2 border-b border-stroke-1">
                      <span className="text-xs font-semibold uppercase tracking-wider text-secondary/60 font-mono">
                        Execution Pipeline
                      </span>
                      <span className="text-[11px] font-mono text-primary-600 font-medium">3 of 5 Steps</span>
                    </div>

                    <div className="mt-3 space-y-2 text-xs">
                      <div className="p-2.5 rounded-lg border border-stroke-1 bg-white opacity-80">
                        <div className="flex items-center justify-between font-mono text-[11px]">
                          <span className="font-semibold text-secondary flex items-center gap-1.5">
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                            extra_focus_window
                          </span>
                          <span className="text-secondary/40">14ms</span>
                        </div>
                        <p className="text-[11px] text-secondary/60 mt-0.5 truncate">
                          Window: "Google Sheets - Q3 Model"
                        </p>
                      </div>

                      <div className="p-2.5 rounded-lg border border-stroke-1 bg-white opacity-80">
                        <div className="flex items-center justify-between font-mono text-[11px]">
                          <span className="font-semibold text-secondary flex items-center gap-1.5">
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                            extra_click_element
                          </span>
                          <span className="text-secondary/40">26ms</span>
                        </div>
                        <p className="text-[11px] text-secondary/60 mt-0.5 truncate">
                          Target: [Sheet: "Revenue", Cell: "D14"]
                        </p>
                      </div>

                      <div className="p-2.5 rounded-lg border border-emerald-500/60 bg-emerald-50/50 border-l-4 border-l-emerald-600 shadow-2xs">
                        <div className="flex items-center justify-between font-mono text-[11px]">
                          <span className="font-semibold text-emerald-900 flex items-center gap-1.5">
                            <span className="relative flex h-2 w-2">
                              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-600"></span>
                            </span>
                            extra_type
                          </span>
                          <span className="text-emerald-700 font-semibold">Active</span>
                        </div>
                        <p className="text-[11px] text-slate-800 font-medium mt-0.5">
                          Unicode Typing: "=SUM(D2:D13)"
                        </p>
                      </div>

                      <div className="p-2.5 rounded-lg border border-stroke-1 bg-background-2/50 text-secondary/40">
                        <span className="font-mono text-[11px]">extra_verify_lineage</span>
                        <p className="text-[11px] text-secondary/40 mt-0.5">Cryptographic PDF Lineage</p>
                      </div>
                    </div>
                  </div>

                  {/* Physical Human-in-Loop Controls */}
                  <div className="pt-2 border-t border-stroke-1 space-y-2">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setIsControlTaken(!isControlTaken)}
                        className={`flex-1 py-2 px-3 rounded-lg text-xs font-semibold border transition-all cursor-pointer flex items-center justify-center gap-1.5 ${
                          isControlTaken
                            ? "bg-secondary text-white border-secondary"
                            : "bg-white text-secondary border-stroke-1 hover:bg-background-2"
                        }`}
                      >
                        <Lock className="w-3.5 h-3.5" />
                        <span>{isControlTaken ? "Release Glass" : "Take Control"}</span>
                      </button>

                      <button
                        onClick={() => setIsPaused(!isPaused)}
                        className={`py-2 px-3.5 rounded-lg text-xs font-semibold border transition-all cursor-pointer flex items-center justify-center gap-1.5 ${
                          isPaused
                            ? "bg-emerald-600 text-white border-emerald-600"
                            : "bg-secondary text-white border-secondary hover:bg-secondary/90"
                        }`}
                      >
                        <Pause className="w-3.5 h-3.5" />
                        <span>{isPaused ? "Resume" : "Pause"}</span>
                      </button>
                    </div>

                    <div className="p-2 rounded-md bg-background-2 text-[10px] font-mono text-secondary/60 flex justify-between">
                      <span>Elapsed: 00:01:42</span>
                      <span className="text-emerald-700 font-semibold">Errors: 0</span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Mode 2: Execution Radar */}
            {viewMode === "workflow" && (
              <div className="mt-4 p-6 bg-background-2 rounded-xl text-left space-y-3">
                <div className="font-semibold text-sm text-secondary">
                  Active Mission: Financial Cashflow Automation
                </div>
                <p className="text-xs text-secondary/70">
                  Dual-plane dispatcher active. Reading receipt PDF telemetry, synchronizing numbers into Google Sheets, and compiling clean PDF export without browser devtool cheats.
                </p>
                <div className="flex gap-2 pt-2">
                  <span className="px-2.5 py-1 rounded bg-white border border-stroke-1 text-xs font-mono text-secondary">
                    Win32 VK_PACKET Typing: Active
                  </span>
                  <span className="px-2.5 py-1 rounded bg-white border border-stroke-1 text-xs font-mono text-emerald-700 font-medium">
                    Lineage Verifier: Ready
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
};
