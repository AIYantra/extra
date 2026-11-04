import { useState } from "react";
import { ArrowRight, Zap, FolderSync, Calculator, FileSpreadsheet, Music } from "lucide-react";
import { Card } from "../minimal/Card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useEngineStore } from "../../store/useEngineStore";
import { toast } from "sonner";

export function MacroCompilerCard() {
  const [intent, setIntent] = useState("");
  const [isDispatching, setIsDispatching] = useState(false);
  const dispatchIntent = useEngineStore((state) => state.dispatchIntent);

  const presets = [
    {
      label: "Reconcile Q3 Sheets",
      icon: FileSpreadsheet,
      query: "Open Google Sheets and write formula =SUM(D2:D13) into cell D14",
    },
    {
      label: "Clean Downloads",
      icon: FolderSync,
      query: "Organize loose files in Downloads into /Taxes, /Decks, and /Archive via extra_fs_batch",
    },
    {
      label: "Calculate ARR Growth",
      icon: Calculator,
      query: "calculate 245.12/383.29=",
    },
    {
      label: "Spotify Focus Mix",
      icon: Music,
      query: "Search youtube for lofi hip hop focus mix and play",
    },
  ];

  const handleDispatch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!intent.trim() || isDispatching) return;
    setIsDispatching(true);
    try {
      const res = await dispatchIntent(intent.trim());
      toast.success(res?.result?.summary || "Workflow dispatched successfully");
      setIntent("");
    } catch (err: any) {
      toast.error(`Dispatch failed: ${err?.message || "Daemon offline"}`);
    } finally {
      setIsDispatching(false);
    }
  };

  return (
    <Card className="p-4 sm:p-5 space-y-3.5 bg-station-well border-station-border shadow-xs">
      <div className="flex items-center justify-between border-b border-station-border pb-2.5">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-station-surface border border-station-border flex items-center justify-center text-station-text-primary">
            <Zap className="w-3.5 h-3.5 text-emerald-500" />
          </div>
          <h3 className="text-xs font-semibold text-station-text-primary">
            Universal Workflow Dispatcher
          </h3>
        </div>

        <Badge variant="mono" className="bg-station-surface border-station-border text-station-text-muted">&lt;50ms dispatch</Badge>
      </div>

      {/* Preset Workflow Chips */}
      <div className="flex flex-wrap gap-1.5">
        {presets.map((p) => {
          const Icon = p.icon;
          return (
            <button
              key={p.label}
              onClick={() => setIntent(p.query)}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-station-border bg-station-surface hover:bg-station-surface/80 text-station-text-muted hover:text-station-text-primary text-xs transition-colors cursor-pointer text-left"
            >
              <Icon className="w-3 h-3 text-station-text-dim shrink-0" />
              <span>{p.label}</span>
            </button>
          );
        })}
      </div>

      {/* Intent Command Form */}
      <form onSubmit={handleDispatch} className="space-y-2 pt-1">
        <div className="relative">
          <input
            type="text"
            value={intent}
            onChange={(e) => setIntent(e.target.value)}
            placeholder="Type a workflow intent (e.g. 'calculate 450 * 1.18 in calc')..."
            className="w-full px-3 py-2 rounded-lg border border-station-border text-xs text-station-text-primary placeholder:text-station-text-dim focus:outline-none focus:border-primary transition-all font-sans bg-station-canvas shadow-xs"
          />
        </div>

        <div className="flex items-center justify-between gap-2 pt-1">
          <span className="text-[11px] font-mono text-station-text-dim">
            Target: <span className="text-station-text-muted font-medium">Active Windows Sandbox</span>
          </span>

          <Button
            type="submit"
            variant="primary"
            size="sm"
            disabled={!intent.trim() || isDispatching}
            className="gap-1.5 font-medium"
          >
            {isDispatching ? (
              <span>Dispatching...</span>
            ) : (
              <>
                <span>Compile & Run</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </>
            )}
          </Button>
        </div>
      </form>
    </Card>
  );
}