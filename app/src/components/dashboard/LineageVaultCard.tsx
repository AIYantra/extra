import { useState, useMemo } from "react";
import {
  FileText,
  Archive,
  Image as ImageIcon,
  Code,
  Clock,
  ShieldCheck,
  FolderOpen,
  Copy,
  Check,
  FileSpreadsheet,
  ExternalLink,
  Search,
} from "lucide-react";
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";
import { toast } from "sonner";
import { useEngineStore } from "../../store/useEngineStore";
import { telemetryClient } from "../../services/telemetryClient";

export function LineageVaultCard() {
  const deliverables = useEngineStore((state) => state.deliverables);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [revealingId, setRevealingId] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");

  const getFileCategory = (name: string) => {
    const ext = name.split(".").pop()?.toLowerCase() || "";
    if (["xlsx", "xls", "csv"].includes(ext)) return "sheets";
    if (["pdf", "docx", "doc", "txt", "md"].includes(ext)) return "docs";
    if (["png", "jpg", "jpeg", "webp", "svg"].includes(ext)) return "images";
    if (["zip", "tar", "gz", "rar", "7z"].includes(ext)) return "archives";
    if (["py", "json", "js", "ts", "html", "css"].includes(ext)) return "code";
    return "other";
  };

  const getFileIcon = (name: string) => {
    const cat = getFileCategory(name);
    switch (cat) {
      case "sheets":
        return { icon: FileSpreadsheet, color: "text-emerald-500 bg-emerald-500/10" };
      case "docs":
        return { icon: FileText, color: "text-rose-500 bg-rose-500/10" };
      case "images":
        return { icon: ImageIcon, color: "text-cyan-500 bg-cyan-500/10" };
      case "archives":
        return { icon: Archive, color: "text-amber-500 bg-amber-500/10" };
      case "code":
        return { icon: Code, color: "text-purple-500 bg-purple-500/10" };
      default:
        return { icon: FileText, color: "text-slate-500 bg-black/[0.04] dark:bg-white/[0.04]" };
    }
  };

  const filteredDeliverables = useMemo(() => {
    return deliverables.filter((d) => {
      const matchesSearch =
        d.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        d.origin.toLowerCase().includes(searchQuery.toLowerCase());
      if (!matchesSearch) return false;
      if (filterType === "all") return true;
      return getFileCategory(d.name) === filterType;
    });
  }, [deliverables, searchQuery, filterType]);

  const handleCopyHash = (id: string, hash: string, e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(hash.replace("sha256:", "").replace("...", ""));
    setCopiedId(id);
    toast.success("SHA-256 checksum copied to clipboard");
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleReveal = async (id: string, path: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setRevealingId(id);
    toast.info("Revealing artifact in Windows Explorer...");
    try {
      await telemetryClient.revealFile(path);
    } finally {
      setTimeout(() => setRevealingId(null), 600);
    }
  };

  const handleOpenRootWorkspace = async () => {
    if (deliverables.length > 0) {
      await telemetryClient.revealFile(deliverables[0].path);
    } else {
      toast.info("Opening ~/.extra/workspace...");
    }
  };

  return (
    <div className="w-full space-y-4 animate-in fade-in duration-150">
      {/* Top Header & Workspace Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-black/[0.06] dark:border-white/[0.08]">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
              <ShieldCheck className="size-4" />
            </span>
            <h2 className="text-base font-bold text-slate-900 dark:text-white tracking-tight">
              Created Files & Artifacts
            </h2>
            <span className="text-xs font-mono font-medium text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-md tabular-nums">
              {deliverables.length} Verified
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-zinc-400 mt-1">
            Every document, diagram, and spreadsheet created by Extra is saved on your local device.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={handleOpenRootWorkspace}
            className="px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-100 hover:bg-slate-200/80 dark:bg-zinc-800 dark:hover:bg-zinc-700 text-slate-700 dark:text-zinc-200 border border-black/[0.04] dark:border-white/[0.06] flex items-center gap-1.5 cursor-pointer transition-all active:scale-95"
          >
            <FolderOpen className="size-3.5 text-amber-500" />
            <span>Open Workspace</span>
          </button>
        </div>
      </div>

      {/* Filter Chips & Search Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
        <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar select-none">
          {[
            { id: "all", label: "All Files" },
            { id: "sheets", label: "Spreadsheets" },
            { id: "docs", label: "Documents" },
            { id: "images", label: "Graphics" },
            { id: "code", label: "Code" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setFilterType(tab.id)}
              className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors cursor-pointer whitespace-nowrap ${
                filterType === tab.id
                  ? "bg-slate-900 dark:bg-white text-white dark:text-slate-900"
                  : "bg-black/[0.03] dark:bg-white/[0.04] text-slate-600 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-white"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Compact Search Input */}
        <div className="relative w-full sm:w-56">
          <Search className="size-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search deliverables..."
            className="w-full h-8 pl-8 pr-3 rounded-lg text-xs bg-black/[0.03] dark:bg-white/[0.04] border border-black/[0.06] dark:border-white/[0.06] text-slate-900 dark:text-white placeholder:text-slate-400 outline-none focus:border-indigo-500 transition-colors"
          />
        </div>
      </div>

      {/* Finder-Style Deliverables Table */}
      <div className="rounded-xl border border-black/[0.06] dark:border-white/[0.08] bg-white dark:bg-[#121417] divide-y divide-black/[0.04] dark:divide-white/[0.05] overflow-hidden shadow-xs">
        {filteredDeliverables.length === 0 ? (
          <div className="py-12 text-center select-none space-y-2">
            <div className="size-9 rounded-full bg-slate-100 dark:bg-zinc-800 flex items-center justify-center mx-auto text-slate-400 dark:text-zinc-500">
              <Clock className="size-4" />
            </div>
            <p className="text-xs font-semibold text-slate-900 dark:text-white">No files found</p>
            <p className="text-[11px] text-slate-500 dark:text-zinc-400 max-w-xs mx-auto">
              Any file Extra creates will automatically appear with its cryptographic hash.
            </p>
          </div>
        ) : (
          filteredDeliverables.map((d) => {
            const { icon: Icon, color } = getFileIcon(d.name);
            const isCopied = copiedId === d.id;
            const isRevealing = revealingId === d.id;

            return (
              <div
                key={d.id}
                onClick={(e) => handleReveal(d.id, d.path, e)}
                className="p-3 sm:px-4 sm:py-3 hover:bg-black/[0.015] dark:hover:bg-white/[0.02] transition-colors flex items-center justify-between gap-3 cursor-pointer group select-none"
              >
                {/* File Info */}
                <div className="flex items-center gap-3 min-w-0">
                  <div
                    className={`size-8 rounded-lg flex items-center justify-center shrink-0 ${color}`}
                  >
                    <Icon className="size-4" />
                  </div>

                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <p
                        className="text-xs sm:text-sm font-semibold text-slate-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors truncate max-w-[180px] sm:max-w-md"
                        title={d.name}
                      >
                        {d.name}
                      </p>
                      <span className="text-[10px] font-mono text-slate-500 dark:text-zinc-400 bg-slate-100 dark:bg-zinc-800 px-1.5 py-0.5 rounded tabular-nums shrink-0">
                        {d.size}
                      </span>
                    </div>

                    <div className="flex items-center gap-2 text-[11px] font-mono text-slate-400 dark:text-zinc-500 mt-0.5 tabular-nums">
                      <span className="truncate max-w-[130px] sm:max-w-[200px]">{d.origin}</span>
                      <span>•</span>
                      <span className="truncate max-w-[120px]">{d.hash}</span>
                    </div>
                  </div>
                </div>

                {/* Actions Rail */}
                <div className="flex items-center gap-1.5 shrink-0">
                  <span className="text-[11px] font-mono text-slate-400 dark:text-zinc-500 tabular-nums hidden md:inline mr-2">
                    {d.verifiedAt}
                  </span>

                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button
                        onClick={(e) => handleCopyHash(d.id, d.hash, e)}
                        className="p-1.5 rounded-lg border border-black/[0.06] dark:border-white/[0.08] bg-slate-50 hover:bg-slate-100 dark:bg-zinc-800/80 dark:hover:bg-zinc-700 text-slate-500 hover:text-slate-900 dark:text-zinc-400 dark:hover:text-white transition-colors cursor-pointer active:scale-95"
                      >
                        {isCopied ? (
                          <Check className="size-3.5 text-emerald-500" />
                        ) : (
                          <Copy className="size-3.5" />
                        )}
                      </button>
                    </TooltipTrigger>
                    <TooltipContent>Copy SHA-256 Checksum</TooltipContent>
                  </Tooltip>

                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button
                        onClick={(e) => handleReveal(d.id, d.path, e)}
                        className="p-1.5 rounded-lg border border-black/[0.06] dark:border-white/[0.08] bg-slate-50 hover:bg-slate-100 dark:bg-zinc-800/80 dark:hover:bg-zinc-700 text-slate-500 hover:text-slate-900 dark:text-zinc-400 dark:hover:text-white transition-colors cursor-pointer active:scale-95"
                      >
                        <ExternalLink
                          className={`size-3.5 ${isRevealing ? "text-emerald-500 animate-spin" : ""}`}
                        />
                      </button>
                    </TooltipTrigger>
                    <TooltipContent>Reveal in Windows Explorer</TooltipContent>
                  </Tooltip>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
