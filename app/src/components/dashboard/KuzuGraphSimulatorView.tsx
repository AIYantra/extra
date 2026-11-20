import { useState, useEffect } from "react";
import { extraDataService } from "../../services/extraDataService";
import {
  type KuzuNode,
  type KuzuNodeType,
  type KuzuGraphData,
  getInitialSeedGraph,
  NODE_STYLE_MAP,
} from "./kuzu/kuzuSimulationData";
import { KuzuTopologyCanvas } from "./kuzu/KuzuTopologyCanvas";
import { KuzuQueryBar } from "./kuzu/KuzuQueryBar";
import { KuzuNodeDetailDrawer } from "./kuzu/KuzuNodeDetailDrawer";
import { Network, RefreshCw, PlusCircle } from "lucide-react";
import { soundEngine } from "../../utils/sound";
import { toast } from "sonner";

export function KuzuGraphSimulatorView() {
  const [graph, setGraph] = useState<KuzuGraphData>(getInitialSeedGraph);
  const [isLoadingLive, setIsLoadingLive] = useState<boolean>(true);
  const [selectedNode, setSelectedNode] = useState<KuzuNode | null>(null);
  const [highlightedNodeIds, setHighlightedNodeIds] = useState<Set<string> | null>(null);
  const [activeTypeFilter, setActiveTypeFilter] = useState<string>("All");
  const [activeClusterFilter, setActiveClusterFilter] = useState<string>("All");
  const [isSimulatingPhysics, setIsSimulatingPhysics] = useState<boolean>(true);
  const [isIngesting, setIsIngesting] = useState<boolean>(false);
  const [activeQueryInfo, setActiveQueryInfo] = useState<string | null>(null);

  const loadLiveGraph = async () => {
    try {
      setIsLoadingLive(true);
      const liveData = await extraDataService.fetchLiveKuzuGraph();
      if (liveData && liveData.nodes && liveData.nodes.length > 0) {
        setGraph({
          nodes: liveData.nodes.map((n, i) => ({
            ...n,
            x: n.x ?? (220 + (i % 6) * 130),
            y: n.y ?? (160 + Math.floor(i / 6) * 110),
            radius: n.radius ?? 20,
          })),
          edges: liveData.edges.map(e => ({
            ...e,
            type: e.type as any,
          })),
        });
      }
    } catch (e) {
      console.warn("[KuzuGraph] Using baseline seed graph:", e);
    } finally {
      setIsLoadingLive(false);
    }
  };

  useEffect(() => {
    loadLiveGraph();
  }, []);

  // Type Filters
  const nodeTypes: (KuzuNodeType | "All")[] = [
    "All",
    "Task",
    "App",
    "ActionStep",
    "Artifact",
    "StallEvent",
    "AppQuirk",
    "SoulDecision",
  ];

  // Apply filters to active highlights
  const handleTypeFilter = (type: string) => {
    soundEngine.playTick();
    setActiveTypeFilter(type);
    if (type === "All") {
      setHighlightedNodeIds(null);
      setActiveQueryInfo(null);
      return;
    }
    const matched = new Set(
      graph.nodes.filter((n) => n.type === type).map((n) => n.id)
    );
    setHighlightedNodeIds(matched);
    setActiveQueryInfo(`Filter: Type = ${type} (${matched.size} nodes)`);
  };

  const handleClusterFilter = (clusterId: string) => {
    soundEngine.playTick();
    setActiveClusterFilter(clusterId);
    if (clusterId === "All") {
      setHighlightedNodeIds(null);
      setActiveQueryInfo(null);
      return;
    }
    const matched = new Set(
      graph.nodes.filter((n) => n.cluster === clusterId).map((n) => n.id)
    );
    setHighlightedNodeIds(matched);
    setActiveQueryInfo(`Filter: Cluster = ${clusterId} (${matched.size} nodes)`);
  };

  const handleFilterResults = (
    matchingIds: Set<string> | null,
    description: string | null
  ) => {
    setHighlightedNodeIds(matchingIds);
    setActiveQueryInfo(description);
  };

  const handleSimulateIngestion = async () => {
    setIsIngesting(true);
    soundEngine.playTick();

    try {
      const res = await extraDataService.ingestKuzuQuirk({
        app: "Calculator",
        issue: "Rapid sequential calculations trigger UI Automation race condition.",
        workaround: "Dispatch atomic extra_batch_actions with auto_settle=True.",
        playbook: "skills/extra-calc/SKILL.md",
      });
      if (res.success) {
        soundEngine.playSuccessChime();
        toast.success(`Committed quirk '${res.id}' to on-disk KùzuDB memory!`, { duration: 4500 });
        await loadLiveGraph();
      } else {
        toast.error(`Ingestion failed: ${res.error}`);
      }
    } catch (e: any) {
      toast.error(`Could not commit to KùzuDB: ${e?.message}`);
    } finally {
      setIsIngesting(false);
    }
  };

  const handleResetGraph = async () => {
    soundEngine.playTick();
    setSelectedNode(null);
    setHighlightedNodeIds(null);
    setActiveTypeFilter("All");
    setActiveClusterFilter("All");
    setActiveQueryInfo(null);
    await loadLiveGraph();
    toast.info("Refreshed graph from on-disk KùzuDB");
  };

  return (
    <div className="space-y-2.5 pb-6 h-full flex flex-col min-h-0 animate-in fade-in duration-150">
      {/* Studio Header: Identity + Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 pb-1 select-none shrink-0">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-[#0a0d14] tracking-tight flex items-center gap-1.5">
              <Network className="size-4 text-[#1677ff]" />
              KùzuDB Memory Graph
            </h2>
            <span className="text-[11px] font-mono text-[#525866] bg-white border border-[#dfe4eb] px-2 py-0.5 rounded-full tabular-nums shadow-2xs flex items-center gap-1.5">
              {isLoadingLive && <RefreshCw className="size-3 animate-spin text-[#1677ff]" />}
              {graph.nodes.length} nodes · {graph.edges.length} edges
            </span>
            <span className="text-[11px] font-mono text-[#1677ff] bg-[#1677ff]/8 border border-[#1677ff]/20 px-2 py-0.5 rounded-full">
              FastEmbed 384-dim
            </span>
          </div>
          <p className="text-xs text-[#525866] mt-0.5">
            Relational episodic memory store simulating sub-3ms cosine vector recall and crystallized quirks
          </p>
        </div>

        {/* Global Actions */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleResetGraph}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white border border-[#dfe4eb] text-xs font-medium text-[#525866] hover:text-[#0a0d14] hover:bg-[#f8f9fb] shadow-2xs transition-colors cursor-pointer"
            title="Reset to default seed graph"
          >
            <RefreshCw className="size-3 text-[#525866]" />
            <span>Reset</span>
          </button>

          <button
            type="button"
            onClick={handleSimulateIngestion}
            disabled={isIngesting}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#1677ff] hover:bg-[#0958d9] text-white text-xs font-medium shadow-2xs transition-colors cursor-pointer disabled:opacity-50"
            title="Ingest new sample trajectory into graph"
          >
            <PlusCircle className="size-3.5 text-white" />
            <span>{isIngesting ? "Ingesting..." : "Ingest Sample Task"}</span>
          </button>
        </div>
      </div>

      {/* Unified Studio Query & Filter Deck */}
      <div className="shrink-0">
        <KuzuQueryBar
          graph={graph}
          onFilterResults={handleFilterResults}
          activeClusterFilter={activeClusterFilter}
          onClusterFilterChange={handleClusterFilter}
        />
      </div>

      {/* Node Type Category Chips Rail */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-0.5 shrink-0 select-none">
        <span className="text-[11px] font-medium text-[#868c98] mr-0.5">Filter Type:</span>
        {nodeTypes.map((t) => {
          const isAll = t === "All";
          const style = !isAll ? NODE_STYLE_MAP[t as KuzuNodeType] : null;
          const count = isAll
            ? graph.nodes.length
            : graph.nodes.filter((n) => n.type === t).length;

          return (
            <button
              key={t}
              type="button"
              onClick={() => handleTypeFilter(t)}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] transition-colors cursor-pointer border ${
                activeTypeFilter === t
                  ? "bg-[#0a0d14] text-white border-[#0a0d14] font-medium shadow-2xs"
                  : "bg-white text-[#525866] border-[#dfe4eb] hover:bg-[#f8f9fb] hover:text-[#0a0d14]"
              }`}
            >
              {style && (
                <span
                  className="size-1.5 rounded-full"
                  style={{ backgroundColor: style.fill }}
                />
              )}
              <span>{t}</span>
              <span className="text-[10px] opacity-70 tabular-nums">({count})</span>
            </button>
          );
        })}
      </div>

      {/* Active Filter Query Notification (if any) */}
      {activeQueryInfo && (
        <div className="flex items-center justify-between px-3 py-1.5 bg-[#f8f9fb] border border-[#dfe4eb] rounded-lg text-xs text-[#0a0d14] shrink-0">
          <span className="font-mono text-[11px] text-[#525866]">{activeQueryInfo}</span>
          <button
            type="button"
            onClick={() => {
              setHighlightedNodeIds(null);
              setActiveQueryInfo(null);
              setActiveTypeFilter("All");
              setActiveClusterFilter("All");
            }}
            className="text-[11px] font-mono text-[#1677ff] hover:underline cursor-pointer"
          >
            Clear Filter
          </button>
        </div>
      )}

      {/* Main Elevated Canvas + Detail Drawer Split Layout */}
      <div className="flex-1 min-h-[460px] flex relative overflow-hidden rounded-xl border border-[#dfe4eb] bg-white shadow-2xs">
        {/* Force-Directed Canvas */}
        <div className="flex-1 h-full min-h-0 relative">
          <KuzuTopologyCanvas
            graph={graph}
            selectedNodeId={selectedNode ? selectedNode.id : null}
            highlightedNodeIds={highlightedNodeIds}
            onSelectNode={setSelectedNode}
            isSimulating={isSimulatingPhysics}
            onToggleSimulating={() => setIsSimulatingPhysics((prev) => !prev)}
          />
        </div>

        {/* Detail Inspector Drawer (Slide-Over) */}
        {selectedNode && (
          <KuzuNodeDetailDrawer
            node={selectedNode}
            graph={graph}
            onClose={() => setSelectedNode(null)}
            onSelectNode={setSelectedNode}
          />
        )}
      </div>
    </div>
  );
}
