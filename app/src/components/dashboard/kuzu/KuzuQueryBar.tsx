import { useState } from "react";
import { Search, Terminal, X, Sparkles, Filter } from "lucide-react";
import {
  type KuzuGraphData,
} from "./kuzuSimulationData";
import { soundEngine } from "../../../utils/sound";
import { extraDataService } from "../../../services/extraDataService";

interface KuzuQueryBarProps {
  graph: KuzuGraphData;
  onFilterResults: (
    matchingNodeIds: Set<string> | null,
    queryDescription: string | null
  ) => void;
  activeClusterFilter?: string;
  onClusterFilterChange?: (cluster: string) => void;
}

export function KuzuQueryBar({
  graph,
  onFilterResults,
  activeClusterFilter = "All",
  onClusterFilterChange,
}: KuzuQueryBarProps) {
  const [mode, setMode] = useState<"recall" | "cypher">("recall");
  const [queryString, setQueryString] = useState<string>("");
  const [activePreset, setActivePreset] = useState<string | null>(null);
  const [execTelemetry, setExecTelemetry] = useState<{
    latencyMs: number;
    matchCount: number;
  } | null>(null);

  // Suggested Natural Language Recall Queries
  const RECALL_SUGGESTIONS = [
    { label: "Calc paste quirk", query: "calculator clipboard paste failure" },
    { label: "Sheets openpyxl", query: "google sheets openpyxl chart" },
    { label: "FreeCAD 3D export", query: "freecad motor mount export" },
    { label: "Paint spline settle", query: "ms paint bezier spline settle" },
  ];

  // Cypher Presets
  const CYPHER_PRESETS = [
    {
      label: "Tasks & Target Apps",
      cypher: "MATCH (t:Task)-[:TARGETED]->(a:App) RETURN t, a",
      types: ["Task", "App"],
      edgeType: "TARGETED",
    },
    {
      label: "Apps & Quirks",
      cypher: "MATCH (a:App)-[:EXHIBITS]->(q:AppQuirk) RETURN a, q",
      types: ["App", "AppQuirk"],
      edgeType: "EXHIBITS",
    },
    {
      label: "Stalls & Resolutions",
      cypher: "MATCH (s:StallEvent)-[:REFINED_BY]->(q:AppQuirk) RETURN s, q",
      types: ["StallEvent", "AppQuirk"],
      edgeType: "REFINED_BY",
    },
    {
      label: "Produced Artifacts",
      cypher: "MATCH (t:Task)-[:PRODUCED]->(art:Artifact) RETURN t, art",
      types: ["Task", "Artifact"],
      edgeType: "PRODUCED",
    },
  ];

  // Clusters
  const clusters = [
    { id: "All", label: "All Apps" },
    { id: "calc", label: "Calc" },
    { id: "sheets", label: "Sheets" },
    { id: "paint", label: "Paint" },
    { id: "freecad", label: "FreeCAD" },
    { id: "notepad", label: "Notepad" },
    { id: "canva", label: "Canva" },
  ];

  // Run Real Semantic Vector Recall against KùzuDB backend
  const handleRunRecall = async (query: string) => {
    soundEngine.playTick();
    setQueryString(query);
    setActivePreset(null);

    if (!query.trim()) {
      onFilterResults(null, null);
      setExecTelemetry(null);
      return;
    }

    try {
      const res = await extraDataService.queryKuzuGraph("recall", query);
      const matchedNodeIds = new Set<string>();
      if (res.matches && res.matches.length > 0) {
        for (const m of res.matches) {
          matchedNodeIds.add(m.node_id);
          for (const edge of graph.edges) {
            if (edge.source === m.node_id) matchedNodeIds.add(edge.target);
            if (edge.target === m.node_id) matchedNodeIds.add(edge.source);
          }
        }
      }
      setExecTelemetry({ latencyMs: res.latency_ms, matchCount: res.count });
      onFilterResults(
        matchedNodeIds.size > 0 ? matchedNodeIds : null,
        `Semantic Recall: "${query}" (${res.count} results in ${res.latency_ms}ms)`
      );
    } catch (e: any) {
      console.warn("Recall error:", e);
    }
  };

  // Run Real Cypher Preset against KùzuDB backend
  const handleRunCypherPreset = async (preset: (typeof CYPHER_PRESETS)[0]) => {
    soundEngine.playTick();
    setQueryString(preset.cypher);
    setActivePreset(preset.label);

    try {
      const res = await extraDataService.queryKuzuGraph("cypher", preset.cypher);
      const resultIds = new Set<string>();
      for (const edge of graph.edges) {
        if (edge.type === preset.edgeType) {
          resultIds.add(edge.source);
          resultIds.add(edge.target);
        }
      }
      setExecTelemetry({ latencyMs: res.latency_ms, matchCount: res.count });
      onFilterResults(resultIds, `Cypher: ${preset.label} (${res.count} rows in ${res.latency_ms}ms)`);
    } catch (e: any) {
      console.warn("Cypher error:", e);
    }
  };

  const handleClear = () => {
    soundEngine.playTick();
    setQueryString("");
    setActivePreset(null);
    setExecTelemetry(null);
    onFilterResults(null, null);
  };

  return (
    <div className="bg-white border border-[#dfe4eb] rounded-xl p-2.5 shadow-2xs space-y-2">
      {/* Primary Input & Mode Row */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
        {/* Mode Selector Segmented Pill */}
        <div className="flex items-center gap-0.5 p-0.5 rounded-lg bg-[#f4f5f8] border border-[#dfe4eb] shrink-0">
          <button
            type="button"
            onClick={() => {
              soundEngine.playTick();
              setMode("recall");
              handleClear();
            }}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors cursor-pointer ${
              mode === "recall"
                ? "bg-white text-[#0a0d14] shadow-2xs border border-[#dfe4eb]"
                : "text-[#525866] hover:text-[#0a0d14]"
            }`}
          >
            <Search className="size-3.5 text-[#1677ff]" />
            <span>Semantic Recall</span>
          </button>

          <button
            type="button"
            onClick={() => {
              soundEngine.playTick();
              setMode("cypher");
              handleClear();
            }}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors cursor-pointer ${
              mode === "cypher"
                ? "bg-white text-[#0a0d14] shadow-2xs border border-[#dfe4eb]"
                : "text-[#525866] hover:text-[#0a0d14]"
            }`}
          >
            <Terminal className="size-3.5 text-[#525866]" />
            <span>Cypher Query</span>
          </button>
        </div>

        {/* Input Field */}
        <div className="relative flex-1 min-w-[220px]">
          <div className="absolute left-3 top-2.5 text-[#868c98] pointer-events-none">
            {mode === "recall" ? (
              <Sparkles className="size-3.5 text-[#1677ff]" />
            ) : (
              <Terminal className="size-3.5 text-[#525866]" />
            )}
          </div>

          <input
            type="text"
            value={queryString}
            onChange={(e) => {
              const val = e.target.value;
              setQueryString(val);
              if (mode === "recall") handleRunRecall(val);
            }}
            placeholder={
              mode === "recall"
                ? "Search graph by natural language intent (e.g. 'calculator paste quirk')..."
                : "MATCH (t:Task)-[:TARGETED]->(a:App) RETURN t, a"
            }
            className="w-full pl-8 pr-8 py-1.5 rounded-lg bg-[#fcfdfe] border border-[#dfe4eb] text-xs text-[#0a0d14] placeholder:text-[#868c98] focus:outline-none focus:border-[#1677ff] focus:bg-white shadow-2xs font-mono transition-colors"
          />

          {queryString && (
            <button
              type="button"
              onClick={handleClear}
              className="absolute right-2 top-2 text-[#868c98] hover:text-[#0a0d14] p-0.5 rounded cursor-pointer"
              title="Clear search"
            >
              <X className="size-3.5" />
            </button>
          )}
        </div>

        {/* Telemetry Indicator */}
        {execTelemetry && (
          <div className="hidden md:flex items-center gap-1.5 text-[11px] font-mono text-[#525866] px-2.5 py-1.5 bg-[#f8f9fb] border border-[#dfe4eb] rounded-lg shrink-0 tabular-nums">
            <span className="text-[#0a0d14] font-medium">
              {execTelemetry.matchCount} nodes
            </span>
            <span>·</span>
            <span>{execTelemetry.latencyMs}ms</span>
          </div>
        )}
      </div>

      {/* Preset & Cluster Filter Rail */}
      <div className="flex items-center justify-between gap-2 pt-1 border-t border-[#f4f5f8] flex-wrap text-[11px]">
        {/* Presets */}
        <div className="flex items-center gap-1 flex-wrap">
          <span className="text-[#868c98] font-medium mr-0.5">Presets:</span>
          {mode === "recall"
            ? RECALL_SUGGESTIONS.map((s, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleRunRecall(s.query)}
                  className={`px-2 py-0.5 rounded-md border transition-colors cursor-pointer text-[11px] ${
                    queryString === s.query
                      ? "bg-[#0a0d14] text-white border-[#0a0d14] font-medium"
                      : "bg-[#f8f9fb] text-[#525866] border-[#dfe4eb] hover:bg-[#f4f5f8] hover:text-[#0a0d14]"
                  }`}
                >
                  {s.label}
                </button>
              ))
            : CYPHER_PRESETS.map((p, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleRunCypherPreset(p)}
                  className={`px-2 py-0.5 rounded-md border transition-colors cursor-pointer text-[11px] ${
                    activePreset === p.label
                      ? "bg-[#0a0d14] text-white border-[#0a0d14] font-medium"
                      : "bg-[#f8f9fb] text-[#525866] border-[#dfe4eb] hover:bg-[#f4f5f8] hover:text-[#0a0d14]"
                  }`}
                >
                  {p.label}
                </button>
              ))}
        </div>

        {/* App Clusters Filter (if callback provided) */}
        {onClusterFilterChange && (
          <div className="flex items-center gap-1">
            <span className="text-[#868c98] font-medium mr-0.5 flex items-center gap-1">
              <Filter className="size-3" />
              App:
            </span>
            {clusters.map((c) => (
              <button
                key={c.id}
                type="button"
                onClick={() => onClusterFilterChange(c.id)}
                className={`px-1.5 py-0.5 rounded text-[11px] border transition-colors cursor-pointer ${
                  activeClusterFilter === c.id
                    ? "bg-[#0a0d14] text-white border-[#0a0d14] font-medium"
                    : "bg-[#f8f9fb] text-[#525866] border-[#dfe4eb] hover:bg-[#f4f5f8] hover:text-[#0a0d14]"
                }`}
              >
                {c.label}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
