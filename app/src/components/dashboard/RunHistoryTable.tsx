import { useState } from "react";
import {
  formatDuration,
  type RunStatus,
  type MissionRun,
} from "../../data/dashboard";
import { useEngineStore } from "../../store/useEngineStore";
import {
  FileSpreadsheet,
  Palette,
  Box,
  Brush,
  BookOpen,
  Globe,
  ArrowUpRight,
  ShieldCheck,
  Clock,
  Calculator,
  MoreHorizontal,
  Copy,
  Check,
  RotateCcw,
  Eye,
} from "lucide-react";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";
import { toast } from "sonner";
import { RunDetailDrawer } from "./RunDetailDrawer";

export function RunHistoryTable() {
  const runs = useEngineStore((state) => state.runs);
  const [filter, setFilter] = useState<string>("all");
  const [selectedRun, setSelectedRun] = useState<MissionRun | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [copiedHashId, setCopiedHashId] = useState<string | null>(null);

  const getAppIcon = (app: string) => {
    switch (app.toLowerCase()) {
      case "sheets":
        return <FileSpreadsheet className="size-3.5 text-emerald-500" />;
      case "canva":
        return <Palette className="size-3.5 text-indigo-500" />;
      case "blender":
        return <Box className="size-3.5 text-amber-500" />;
      case "paint":
        return <Brush className="size-3.5 text-rose-500" />;
      case "obsidian":
        return <BookOpen className="size-3.5 text-purple-500" />;
      case "calculator":
      case "calc":
        return <Calculator className="size-3.5 text-cyan-500" />;
      default:
        return <Globe className="size-3.5 text-station-text-muted" />;
    }
  };

  const getStatusBadge = (status: RunStatus) => {
    switch (status) {
      case "running":
        return (
          <Badge variant="warning" size="sm" dot pulse>
            Running
          </Badge>
        );
      case "completed":
        return (
          <Badge variant="success" size="sm" dot>
            Verified
          </Badge>
        );
      case "failed":
        return (
          <Badge variant="destructive" size="sm" dot>
            Failed
          </Badge>
        );
      default:
        return (
          <Badge variant="outline" size="sm">
            Queued
          </Badge>
        );
    }
  };

  const filteredRuns = runs.filter((run) => {
    if (filter === "active") return run.status === "running";
    if (filter === "completed") return run.status === "completed";
    if (filter === "verified") return run.lineage && run.lineage !== "—";
    return true;
  });

  const completedCount = runs.filter((r) => r.status === "completed").length;
  const activeCount = runs.filter((r) => r.status === "running").length;
  const verifiedCount = runs.filter((r) => r.lineage && r.lineage !== "—").length;

  const handleInspect = (run: MissionRun) => {
    setSelectedRun(run);
    setIsDrawerOpen(true);
  };

  const handleCopyHash = (e: React.MouseEvent, runId: string, hash: string) => {
    e.stopPropagation();
    if (hash === "—") return;
    navigator.clipboard.writeText(hash);
    setCopiedHashId(runId);
    toast.success("Lineage SHA-256 copied to clipboard");
    setTimeout(() => setCopiedHashId(null), 2000);
  };

  return (
    <>
      <div className="rounded-xl border border-station-border bg-station-well shadow-xs overflow-hidden transition-all duration-200">
        {/* Header and Filter Tabs */}
        <div className="p-4 border-b border-station-border bg-station-elevated flex flex-wrap items-center justify-between gap-3 select-none">
          <div>
            <h3 className="text-xs sm:text-sm font-semibold text-station-text-primary tracking-tight">
              Execution Ledger & Mission Queue
            </h3>
            <p className="text-[11px] text-station-text-muted font-sans mt-0.5">
              Cryptographic audit trail of autonomous subtask dispatches and verified SHA-256 receipts
            </p>
          </div>

          <Tabs value={filter} onValueChange={setFilter}>
            <TabsList className="h-7.5 bg-station-well border border-station-border p-0.5 rounded-lg">
              <TabsTrigger
                value="all"
                className="gap-1.5 text-xs h-6 px-2.5 data-[state=active]:bg-station-surface data-[state=active]:text-station-text-primary data-[state=active]:shadow-xs"
              >
                <span>All Runs</span>
                <span className="text-[10px] font-mono px-1 rounded bg-station-surface text-station-text-muted">
                  {runs.length}
                </span>
              </TabsTrigger>
              <TabsTrigger
                value="active"
                className="gap-1.5 text-xs h-6 px-2.5 data-[state=active]:bg-station-surface data-[state=active]:text-station-text-primary data-[state=active]:shadow-xs"
              >
                <span>Active</span>
                {activeCount > 0 && (
                  <span className="text-[10px] font-mono px-1 rounded bg-amber-500/10 text-amber-600 dark:text-amber-400 font-semibold">
                    {activeCount}
                  </span>
                )}
              </TabsTrigger>
              <TabsTrigger
                value="completed"
                className="gap-1.5 text-xs h-6 px-2.5 data-[state=active]:bg-station-surface data-[state=active]:text-station-text-primary data-[state=active]:shadow-xs"
              >
                <span>Completed</span>
                <span className="text-[10px] font-mono px-1 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-semibold">
                  {completedCount}
                </span>
              </TabsTrigger>
              <TabsTrigger
                value="verified"
                className="gap-1.5 text-xs h-6 px-2.5 data-[state=active]:bg-station-surface data-[state=active]:text-station-text-primary data-[state=active]:shadow-xs"
              >
                <span>Verified</span>
                <span className="text-[10px] font-mono px-1 rounded bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 font-semibold">
                  {verifiedCount}
                </span>
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </div>

        {/* Table Content */}
        {runs.length === 0 ? (
          <div className="py-12 text-center space-y-3 bg-station-canvas">
            <div className="w-10 h-10 rounded-full bg-station-surface border border-station-border flex items-center justify-center mx-auto text-station-text-muted">
              <Clock className="size-5" />
            </div>
            <div className="space-y-1">
              <h4 className="text-sm font-medium text-station-text-primary">No Runs Recorded Yet</h4>
              <p className="text-xs text-station-text-muted max-w-sm mx-auto font-sans">
                Dispatched macros and pilots will appear here with cryptographic SHA-256 lineage and token savings.
              </p>
            </div>
          </div>
        ) : (
          <Table className="bg-station-canvas">
            <TableHeader>
              <TableRow>
                <TableHead>Run ID / Task Intent</TableHead>
                <TableHead>Target App</TableHead>
                <TableHead>Plane</TableHead>
                <TableHead>Steps</TableHead>
                <TableHead>Duration</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Lineage Hash</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredRuns.map((run) => (
                <TableRow
                  key={run.id}
                  onClick={() => handleInspect(run)}
                  className="cursor-pointer group"
                >
                  {/* ID & Task */}
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Badge variant="mono" size="sm" className="shrink-0 text-[10px] bg-station-surface border-station-border text-station-text-muted">
                        {run.id}
                      </Badge>
                      <span className="font-medium text-station-text-primary truncate max-w-[260px] text-xs transition-colors">
                        {run.title}
                      </span>
                    </div>
                  </TableCell>

                  {/* Target App */}
                  <TableCell>
                    <div className="flex items-center gap-1.5 text-station-text-muted text-xs">
                      <div className="size-5 rounded bg-station-surface border border-station-border flex items-center justify-center shrink-0">
                        {getAppIcon(run.app)}
                      </div>
                      <span className="text-station-text-primary font-medium">{run.app}</span>
                    </div>
                  </TableCell>

                  {/* Plane */}
                  <TableCell>
                    <Badge variant="mono" size="sm" className="bg-station-surface border-station-border text-station-text-muted">
                      {run.app === "Blender"
                        ? "P2 Bridge"
                        : run.app === "Paint"
                        ? "P1 Ink"
                        : "P1 SOUL"}
                    </Badge>
                  </TableCell>

                  {/* Steps */}
                  <TableCell className="font-mono text-station-text-muted font-medium tabular-nums text-xs">
                    {run.steps}
                  </TableCell>

                  {/* Duration */}
                  <TableCell className="font-mono text-station-text-muted font-medium tabular-nums text-xs">
                    {formatDuration(run.durationSec)}
                  </TableCell>

                  {/* Status */}
                  <TableCell>{getStatusBadge(run.status)}</TableCell>

                  {/* Lineage */}
                  <TableCell>
                    {run.lineage !== "—" ? (
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <button
                            onClick={(e) => handleCopyHash(e, run.id, run.lineage || "")}
                            className="flex items-center gap-1 font-mono text-[11px] text-station-text-muted font-medium hover:text-station-text-primary transition-colors cursor-pointer"
                          >
                            <ShieldCheck className="size-3.5 text-emerald-500 shrink-0" />
                            <span className="truncate max-w-[110px]">{run.lineage}</span>
                            {copiedHashId === run.id ? (
                              <Check className="size-3 text-emerald-500 ml-1" />
                            ) : (
                              <Copy className="size-3 text-station-text-dim ml-1 opacity-0 group-hover:opacity-100" />
                            )}
                          </button>
                        </TooltipTrigger>
                        <TooltipContent side="top">
                          Click to copy full SHA-256 cryptographic provenance hash
                        </TooltipContent>
                      </Tooltip>
                    ) : (
                      <span className="text-station-text-dim font-mono text-[11px]">—</span>
                    )}
                  </TableCell>

                  {/* Action Menu */}
                  <TableCell className="text-right" onClick={(e) => e.stopPropagation()}>
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        variant="secondary"
                        size="xs"
                        onClick={() => handleInspect(run)}
                        className="h-6 px-2 text-[11px] gap-1 font-mono bg-station-surface hover:bg-station-surface/80 border border-station-border text-station-text-primary"
                      >
                        <span>Inspect</span>
                        <ArrowUpRight className="size-3 text-station-text-muted" />
                      </Button>

                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon-xs"
                            className="size-6 text-station-text-muted hover:text-station-text-primary"
                            aria-label="Row actions"
                          >
                            <MoreHorizontal className="size-3.5" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="bg-station-elevated border-station-border">
                          <DropdownMenuItem onClick={() => handleInspect(run)}>
                            <Eye className="size-3.5 mr-2" />
                            Inspect Breakdown
                          </DropdownMenuItem>
                          {run.lineage !== "—" && (
                            <DropdownMenuItem onClick={(e) => handleCopyHash(e, run.id, run.lineage || "")}>
                              <Copy className="size-3.5 mr-2" />
                              Copy SHA-256 Hash
                            </DropdownMenuItem>
                          )}
                          <DropdownMenuSeparator className="bg-station-border" />
                          <DropdownMenuItem onClick={() => console.log("Re-dispatching run:", run.id)}>
                            <RotateCcw className="size-3.5 mr-2" />
                            Re-run on Desktop
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>

      {/* Slide-over Inspect Drawer */}
      <RunDetailDrawer
        run={selectedRun}
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
      />
    </>
  );
}