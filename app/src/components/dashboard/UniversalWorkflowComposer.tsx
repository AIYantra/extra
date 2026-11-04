import { useState, useRef } from "react";
import {
  Sparkles,
  Loader2,
  Zap,
  Calculator,
  FolderOpen,
  Music,
  Columns,
} from "lucide-react";
import { toast } from "sonner";
import { useEngineStore } from "../../store/useEngineStore";
import { soundEngine } from "../../utils/sound";
import type { SpeedMode } from "../../services/ipc";
import { SPEED_MODE_META } from "../../utils/speedModes";
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";

interface UniversalWorkflowComposerProps {
  onDispatchSuccess?: (intent: string) => void;
}

export function UniversalWorkflowComposer({
  onDispatchSuccess,
}: UniversalWorkflowComposerProps) {
  const [intent, setIntent] = useState("");
  const [isFocused, setIsFocused] = useState(false);
  const [isDispatching, setIsDispatching] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const dispatchIntent = useEngineStore((state) => state.dispatchIntent);
  const speedMode = useEngineStore((state) => state.speedMode);
  const setSpeedMode = useEngineStore((state) => state.setSpeedMode);

  // Curated, elegant prompt suggestions with monochrome glyphs
  const suggestions = [
    { label: "Calculate 245 ÷ 4", prompt: "calculate 245.12 / 4 in Calculator", icon: Calculator },
    { label: "Organize Downloads", prompt: "organize loose files in Downloads folder", icon: FolderOpen },
    { label: "Play Lo-Fi Music", prompt: "search YouTube for lofi hip hop relax music", icon: Music },
    { label: "Snap Windows", prompt: "snap active windows side by side", icon: Columns },
  ];

  // Auto-detect target app icon for subtle visual grounding
  const getInferredApp = (text: string) => {
    const lower = text.toLowerCase();
    if (lower.includes("calc") || lower.includes("calculate") || /[\d+\-*/=]/.test(lower)) return "calc";
    if (lower.includes("paint") || lower.includes("draw") || lower.includes("sketch")) return "mspaint";
    if (lower.includes("notepad") || lower.includes("write") || lower.includes("text")) return "notepad";
    if (lower.includes("youtube") || lower.includes("browse") || lower.includes("search") || lower.includes("web")) return "edge";
    if (lower.includes("sheet") || lower.includes("excel")) return "sheets";
    return null;
  };

  const inferredApp = getInferredApp(intent);

  const cycleSpeedMode = () => {
    soundEngine.playTick();
    const modes: SpeedMode[] = ["turbo", "balanced", "smart"];
    const next = modes[(modes.indexOf(speedMode) + 1) % modes.length];
    setSpeedMode(next);
    toast.info(`Speed mode: ${SPEED_MODE_META[next].label}`);
  };

  const handleDispatch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const query = intent.trim();
    if (!query || isDispatching) return;

    setIsDispatching(true);
    soundEngine.playTick();
    toast.info(`Dispatching: ${query.slice(0, 42)}...`);

    try {
      const res = await dispatchIntent(query);
      const summary = res?.result?.summary || res?.message || "Macro executed successfully";
      toast.success(summary);
      soundEngine.playSuccessChime();
      setIntent("");
      if (onDispatchSuccess) onDispatchSuccess(query);
    } catch (err: any) {
      const msg = err?.message || "Dispatch failed";
      toast.error(msg);
    } finally {
      setIsDispatching(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleDispatch();
    }
  };

  return (
    <div className="w-full space-y-3">
      {/* Raycast-Grade Hero Command Capsule */}
      <form
        onSubmit={handleDispatch}
        onClick={() => inputRef.current?.focus()}
        className={`group relative flex items-center h-13 px-4 rounded-2xl border transition-all duration-120 cursor-text shadow-xs ${
          isFocused
            ? "border-indigo-500/50 ring-3 ring-indigo-500/15 bg-white dark:bg-[#14161b]"
            : "border-black/[0.08] dark:border-white/[0.08] bg-white dark:bg-[#121417] hover:border-black/[0.12] dark:hover:border-white/[0.12]"
        }`}
      >
        {/* Left Icon: Clean Command Glyph */}
        <div className="flex items-center justify-center size-7 rounded-lg bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 shrink-0 mr-3 transition-colors">
          {isDispatching ? (
            <Loader2 className="size-4 animate-spin text-indigo-600 dark:text-indigo-400" />
          ) : (
            <Sparkles className="size-4 text-indigo-600 dark:text-indigo-400" />
          )}
        </div>

        {/* Tactile Native Input */}
        <input
          ref={inputRef}
          type="text"
          value={intent}
          onChange={(e) => setIntent(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          onKeyDown={handleKeyDown}
          placeholder="Tell Extra what to do on your computer..."
          className="w-full h-full bg-transparent border-0 outline-none text-slate-900 dark:text-white placeholder:text-slate-400 dark:placeholder:text-zinc-500 text-sm font-sans font-medium selection:bg-indigo-500/20 focus-visible:outline-none"
        />

        {/* Right Rail: Subtle Inferred App + Speed Mode + Return Keycap */}
        <div className="flex items-center gap-2 shrink-0 ml-3 select-none">
          {/* Inferred Target App Pill */}
          {inferredApp && (
            <span className="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-mono font-medium text-slate-600 dark:text-zinc-300 bg-slate-100 dark:bg-zinc-800 border border-black/[0.05] dark:border-white/[0.05] animate-in fade-in duration-150">
              <span className="size-1.5 rounded-full bg-emerald-500" />
              {inferredApp}
            </span>
          )}

          {/* Quick Speed Mode Cycle Pill */}
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  cycleSpeedMode();
                }}
                className="hidden md:inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-mono font-semibold uppercase tracking-wider text-slate-600 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-white bg-slate-100/70 hover:bg-slate-100 dark:bg-zinc-800/60 dark:hover:bg-zinc-800 border border-black/[0.05] dark:border-white/[0.06] transition-colors cursor-pointer focus-visible:outline-none"
              >
                <Zap className="size-2.5 text-amber-500" />
                <span>{SPEED_MODE_META[speedMode].label}</span>
              </button>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="text-xs font-mono">
              Switch speed: Turbo, Balanced, Smart IT
            </TooltipContent>
          </Tooltip>

          {/* Return Keycap / Dispatch Button */}
          <button
            type="submit"
            disabled={!intent.trim() || isDispatching}
            className={`flex items-center justify-center size-7 rounded-lg transition-all duration-120 cursor-pointer focus-visible:outline-none ${
              intent.trim()
                ? "bg-indigo-600 hover:bg-indigo-500 text-white shadow-xs active:scale-95"
                : "bg-slate-100 dark:bg-zinc-800 text-slate-400 dark:text-zinc-600 border border-black/[0.04] dark:border-white/[0.06] opacity-70"
            }`}
            title="Press Enter to dispatch"
          >
            {isDispatching ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : (
              <span className="text-xs font-mono font-bold leading-none">↵</span>
            )}
          </button>
        </div>
      </form>

      {/* Quiet, Minimal Prompt Suggestions (Inline chips) */}
      <div className="flex items-center gap-2 px-1 text-xs select-none overflow-x-auto no-scrollbar">
        <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 dark:text-zinc-500 shrink-0">
          Try:
        </span>
        <div className="flex items-center gap-1.5 flex-wrap">
          {suggestions.map((s) => {
            const Icon = s.icon;
            return (
              <button
                key={s.label}
                type="button"
                onClick={() => {
                  soundEngine.playTick();
                  setIntent(s.prompt);
                  inputRef.current?.focus();
                }}
                className="inline-flex items-center gap-1.5 text-[11px] font-medium text-slate-600 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-white px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200/70 dark:bg-[#181a20] dark:hover:bg-[#20232a] border border-black/[0.04] dark:border-white/[0.05] transition-all cursor-pointer whitespace-nowrap active:scale-95"
              >
                <Icon className="size-3 text-slate-400 dark:text-zinc-500" />
                <span>{s.label}</span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
