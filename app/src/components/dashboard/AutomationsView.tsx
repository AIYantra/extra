import { useState } from "react";
import {
  Layers,
  Play,
  CheckCircle2,
  Clock,
  Calculator,
  FileSpreadsheet,
  FolderSync,
  Palette,
  Terminal,
  Zap,
  RotateCw,
  Sliders,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { StationPageHeader } from "./StationPageHeader";
import { useEngineStore } from "../../store/useEngineStore";

interface AutomationRecipe {
  id: string;
  name: string;
  category: "Productivity" | "Creative" | "System" | "Developer";
  icon: typeof Calculator;
  description: string;
  intent: string;
  estimatedMs: number;
  tags: string[];
}

const RECIPES: AutomationRecipe[] = [
  {
    id: "calc-growth",
    name: "ARR Growth Formula",
    category: "Productivity",
    icon: Calculator,
    description: "Computes financial quotient instantly in Windows Calculator (zero-turn fast path).",
    intent: "calculate 245.12/383.29=",
    estimatedMs: 38,
    tags: ["calc.exe", "1-turn macro", "Tier 1"],
  },
  {
    id: "sheets-formula",
    name: "Google Sheets Reconcile",
    category: "Productivity",
    icon: FileSpreadsheet,
    description: "Inserts =SUM(D2:D13) formula into active cell and verifies recalculation.",
    intent: "Open Google Sheets and enter formula =SUM(D2:D13) into active cell",
    estimatedMs: 420,
    tags: ["Sheets", "Fast Path", "Shift+F11"],
  },
  {
    id: "fs-organize",
    name: "Organize Loose Downloads",
    category: "System",
    icon: FolderSync,
    description: "Batches untracked files into /Taxes, /Decks, and /Archive without multi-turn shell loops.",
    intent: "Organize loose files in Downloads into categorized folders via extra_fs_batch",
    estimatedMs: 85,
    tags: ["CFA Compliant", "extra_fs_batch"],
  },
  {
    id: "paint-chart",
    name: "Architecture Diagram in Paint",
    category: "Creative",
    icon: Palette,
    description: "Synthesizes system block diagram on MS Paint canvas using vector brush splines.",
    intent: "Draw system architecture block diagram in MS Paint",
    estimatedMs: 1200,
    tags: ["mspaint.exe", "Bezier Splines", "SOUL-Ink"],
  },
  {
    id: "window-snap",
    name: "Side-by-Side Dual Cockpit",
    category: "System",
    icon: Sliders,
    description: "Arranges active editor and terminal into perfect 50/50 side-by-side layout in 15ms.",
    intent: "Snap active windows side by side via extra_snap_layout",
    estimatedMs: 14,
    tags: ["SetWindowPos", "Sub-15ms"],
  },
  {
    id: "cli-harness",
    name: "CLI Agent Harness Audit",
    category: "Developer",
    icon: Terminal,
    description: "Synthesizes 7-phase CLI agent harness SOP, tests, and dual-plane wrapper.",
    intent: "Run extra_harness_run for active workspace",
    estimatedMs: 340,
    tags: ["Dual-Plane", "Phase 1-7"],
  },
];

export function AutomationsView() {
  const [selectedCategory, setSelectedCategory] = useState<string>("All");
  const [customIntent, setCustomIntent] = useState("");
  const [isExecuting, setIsExecuting] = useState(false);
  const [activeRecipeId, setActiveRecipeId] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<{ id: string; success: boolean; message: string; ms: number } | null>(null);

  const isServerOnline = useEngineStore((state) => state.isServerOnline);
  const isPanicActive = useEngineStore((state) => state.isPanicActive);
  const dispatchIntent = useEngineStore((state) => state.dispatchIntent);

  const categories = ["All", "Productivity", "System", "Creative", "Developer"];

  const filtered = selectedCategory === "All"
    ? RECIPES
    : RECIPES.filter((r) => r.category === selectedCategory);

  const handleRunRecipe = async (recipe: AutomationRecipe) => {
    if (isExecuting || isPanicActive) return;
    setIsExecuting(true);
    setActiveRecipeId(recipe.id);
    const t0 = performance.now();

    try {
      const data = await dispatchIntent(recipe.intent);
      const elapsed = Math.round(performance.now() - t0);
      setLastResult({
        id: recipe.id,
        success: data?.status === "ok",
        message: data?.message || `Dispatched "${recipe.name}" in ${elapsed}ms`,
        ms: elapsed,
      });
    } catch (err: any) {
      const elapsed = Math.round(performance.now() - t0);
      setLastResult({
        id: recipe.id,
        success: false,
        message: `Failed to dispatch "${recipe.name}": ${err?.message || "Daemon offline"}`,
        ms: elapsed,
      });
    } finally {
      setIsExecuting(false);
      setActiveRecipeId(null);
      setTimeout(() => setLastResult(null), 5000);
    }
  };

  const handleCustomDispatch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!customIntent.trim() || isExecuting || isPanicActive) return;

    setIsExecuting(true);
    setActiveRecipeId("custom");
    const t0 = performance.now();

    try {
      const data = await dispatchIntent(customIntent);
      const elapsed = Math.round(performance.now() - t0);
      setLastResult({
        id: "custom",
        success: data?.status === "ok",
        message: data?.message || `Dispatched intent in ${elapsed}ms`,
        ms: elapsed,
      });
      setCustomIntent("");
    } catch (err: any) {
      const elapsed = Math.round(performance.now() - t0);
      setLastResult({
        id: "custom",
        success: false,
        message: `Failed to dispatch "${customIntent}": ${err?.message || "Daemon offline"}`,
        ms: elapsed,
      });
      setCustomIntent("");
    } finally {
      setIsExecuting(false);
      setActiveRecipeId(null);
      setTimeout(() => setLastResult(null), 5000);
    }
  };

  return (
    <div className="space-y-4 sm:space-y-5 pb-8">
      {/* Unified Agency Header */}
      <StationPageHeader
        icon={Layers}
        iconColor="text-indigo-500"
        title="Autonomous Micro-Routines & Recipes"
        badge="14 Active Recipes"
        description="Single-turn macro execution via the Universal Intent Compiler. Dispatches compound hardware actions with sub-millisecond latency and on-device SOUL-Critic validation."
        actions={
          <Badge variant="outline" className="gap-1.5 font-mono text-[11px] text-station-text-muted border-station-border">
            <span className={`size-1.5 rounded-full ${isServerOnline ? "bg-emerald-500 animate-pulse" : "bg-amber-500"}`} />
            {isServerOnline ? "Engine Ready" : "Loopback Standby"}
          </Badge>
        }
      />

      {/* Custom Command Dispatch Bar */}
      <form onSubmit={handleCustomDispatch} className="rounded-xl border border-station-border specular-card bg-station-well p-2.5 sm:p-3 shadow-xs flex items-center gap-2.5 focus-within:ring-2 focus-within:ring-primary/20 focus-within:border-primary transition-all">
        <Zap className="size-4 text-emerald-500 shrink-0 ml-1.5" />
        <input
          type="text"
          value={customIntent}
          onChange={(e) => setCustomIntent(e.target.value)}
          placeholder="Type an intent (e.g. 'calculate 245.12/383.29=' or 'snap notepad and calculator side by side')..."
          className="flex-1 bg-transparent text-xs sm:text-sm text-station-text-primary placeholder:text-station-text-dim outline-none font-mono"
        />
        <Button
          type="submit"
          variant="primary"
          size="sm"
          disabled={!customIntent.trim() || isExecuting}
          className="h-7 px-3 gap-1.5 shrink-0 text-xs font-medium rounded-md focus-visible:ring-2 focus-visible:ring-primary/50 cursor-pointer active:scale-95"
        >
          {isExecuting && activeRecipeId === "custom" ? (
            <RotateCw className="size-3 animate-spin" />
          ) : (
            <Play className="size-3 fill-current" />
          )}
          <span>Execute</span>
        </Button>
      </form>

      {/* Execution Result Banner */}
      {lastResult && (
        <div className={`p-3 rounded-lg border text-xs font-mono flex items-center justify-between gap-3 animate-in fade-in duration-150 ${
          lastResult.success
            ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-600 dark:text-emerald-300"
            : "bg-rose-500/10 border-rose-500/20 text-rose-600 dark:text-rose-300"
        }`}>
          <div className="flex items-center gap-2">
            <CheckCircle2 className="size-4 text-emerald-500 shrink-0" />
            <span>{lastResult.message}</span>
          </div>
          <span className="text-[10px] text-station-text-muted shrink-0 tabular-nums">{lastResult.ms}ms total</span>
        </div>
      )}

      {/* Segmented Filter Control */}
      <div className="p-1 rounded-lg bg-station-surface/50 border border-station-border inline-flex items-center gap-1 select-none">
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setSelectedCategory(cat)}
            className={`px-3 py-1 rounded-md text-xs font-medium transition-all duration-150 cursor-pointer ${
              selectedCategory === cat
                ? "bg-station-well text-station-text-primary shadow-xs font-semibold"
                : "text-station-text-muted hover:text-station-text-primary hover:bg-station-elevated/40"
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Recipes Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
        {filtered.map((recipe) => {
          const Icon = recipe.icon;
          const isThisActive = isExecuting && activeRecipeId === recipe.id;
          return (
            <div
              key={recipe.id}
              className="rounded-xl border border-station-border specular-card bg-station-well p-4 hover:border-station-border-active hover:bg-station-elevated/40 transition-all duration-150 flex flex-col justify-between space-y-3.5 shadow-xs group"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="size-7 rounded-md bg-station-surface border border-station-border flex items-center justify-center text-station-text-primary">
                    <Icon className="size-3.5 text-station-text-muted group-hover:text-primary transition-colors" />
                  </div>
                  <Badge variant="mono" className="text-[9px] bg-station-surface/80 border-station-border text-station-text-muted tabular-nums">
                    <Clock className="size-2.5 mr-1 text-station-text-dim" />
                    ~{recipe.estimatedMs}ms
                  </Badge>
                </div>
                <div>
                  <h3 className="text-xs sm:text-sm font-medium text-station-text-primary tracking-tight">{recipe.name}</h3>
                  <p className="text-xs text-station-text-muted mt-0.5 line-clamp-2 leading-relaxed">{recipe.description}</p>
                </div>
              </div>

              <div className="space-y-2.5 pt-2 border-t border-station-border">
                <div className="flex flex-wrap gap-1">
                  {recipe.tags.map((tag) => (
                    <span
                      key={tag}
                      className="text-[9px] font-mono px-1.5 py-0.5 rounded-sm bg-station-surface text-station-text-muted"
                    >
                      {tag}
                    </span>
                  ))}
                </div>

                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => handleRunRecipe(recipe)}
                  disabled={isExecuting || isPanicActive}
                  className="w-full h-7.5 text-xs font-medium gap-1.5 justify-center cursor-pointer rounded-md bg-station-surface hover:bg-station-surface/80 border-station-border text-station-text-primary active:scale-95 transition-all"
                >
                  {isThisActive ? (
                    <>
                      <RotateCw className="size-3 animate-spin" />
                      <span>Actuating Live...</span>
                    </>
                  ) : (
                    <>
                      <Play className="size-3 fill-current" />
                      <span>Execute Recipe</span>
                    </>
                  )}
                </Button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}