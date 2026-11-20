import { useState, useEffect } from "react";
import {
  type KuzuNode,
  type KuzuGraphData,
  NODE_STYLE_MAP,
} from "./kuzuSimulationData";
import {
  X,
  Copy,
  Check,
  ExternalLink,
  ArrowRight,
  ArrowLeft,
  Database,
  Terminal,
} from "lucide-react";
import { soundEngine } from "../../../utils/sound";
import { toast } from "sonner";

interface KuzuNodeDetailDrawerProps {
  node: KuzuNode | null;
  graph: KuzuGraphData;
  onClose: () => void;
  onSelectNode: (node: KuzuNode | null) => void;
}

export function KuzuNodeDetailDrawer({
  node,
  graph,
  onClose,
  onSelectNode,
}: KuzuNodeDetailDrawerProps) {
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [hoveredDim, setHoveredDim] = useState<{ idx: number; val: number } | null>(null);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        soundEngine.playTick();
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  if (!node) return null;

  const style = NODE_STYLE_MAP[node.type] || NODE_STYLE_MAP.Task;

  // Find Inbound & Outbound Connected Edges
  const outboundEdges = graph.edges.filter((e) => e.source === node.id);
  const inboundEdges = graph.edges.filter((e) => e.target === node.id);

  const nodeMap = new Map<string, KuzuNode>(graph.nodes.map((n) => [n.id, n]));

  // Generated Cypher Query for this Node
  const cypherQuery =
    node.type === "App"
      ? `MATCH (a:App {name: '${node.properties.name || node.label}'}) RETURN a;`
      : `MATCH (n:${node.type} {id: '${node.id}'}) RETURN n;`;

  const handleCopyText = (text: string, key: string) => {
    soundEngine.playTick();
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    toast.success(`Copied to clipboard`);
    setTimeout(() => setCopiedKey(null), 1800);
  };

  return (
    <div className="w-80 md:w-96 shrink-0 h-full flex flex-col bg-white border-l border-[#dfe4eb] shadow-xl animate-in slide-in-from-right duration-200 z-20 overflow-hidden select-none">
      {/* Studio Drawer Header */}
      <div className="p-3.5 border-b border-[#dfe4eb] flex items-center justify-between bg-[#fbfcfe]">
        <div className="flex items-center gap-2 min-w-0">
          <span
            className="px-2 py-0.5 rounded text-[11px] font-medium shrink-0"
            style={{ backgroundColor: style.badgeBg, color: style.badgeText }}
          >
            {node.type}
          </span>
          <h3 className="font-semibold text-xs text-[#0a0d14] truncate">
            {node.label}
          </h3>
        </div>

        <div className="flex items-center gap-1.5">
          <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] font-mono text-[#868c98] bg-[#f4f5f8] border border-[#dfe4eb] rounded">
            Esc
          </kbd>
          <button
            type="button"
            onClick={() => {
              soundEngine.playTick();
              onClose();
            }}
            className="p-1 rounded-md text-[#868c98] hover:text-[#0a0d14] hover:bg-[#eceff4] transition-colors cursor-pointer"
            title="Close details"
          >
            <X className="size-4" />
          </button>
        </div>
      </div>

      {/* Drawer Body */}
      <div className="flex-1 overflow-y-auto p-3.5 space-y-4">
        {/* Node Identifier */}
        <div className="p-2.5 rounded-lg bg-[#f8f9fb] border border-[#dfe4eb] flex items-center justify-between">
          <div className="min-w-0">
            <span className="text-[10px] text-[#868c98] font-medium block">
              Primary key
            </span>
            <span className="text-xs font-mono text-[#0a0d14] font-medium truncate block mt-0.5 tabular-nums">
              {node.id}
            </span>
          </div>
          <button
            type="button"
            onClick={() => handleCopyText(node.id, "id")}
            className="p-1.5 rounded text-[#868c98] hover:text-[#0a0d14] hover:bg-white transition-colors cursor-pointer"
            title="Copy ID"
          >
            {copiedKey === "id" ? (
              <Check className="size-3.5 text-[#0e8345]" />
            ) : (
              <Copy className="size-3.5" />
            )}
          </button>
        </div>

        {/* 384-dimensional FastEmbed Vector Sparkline (If Task) */}
        {node.embedding && (
          <div className="p-3 rounded-lg bg-[#f8f9fb] border border-[#dfe4eb] space-y-2">
            <div className="flex items-center justify-between text-[11px]">
              <span className="font-medium text-[#0a0d14] flex items-center gap-1.5">
                <Database className="size-3 text-[#1677ff]" />
                FastEmbed 384-dim vector
              </span>
              <span className="font-mono text-[#525866] tabular-nums">
                {hoveredDim
                  ? `dim[${hoveredDim.idx}]: ${hoveredDim.val.toFixed(3)}`
                  : "Norm: 1.000"}
              </span>
            </div>

            {/* Interactive Vector Sparkline */}
            <div className="h-10 w-full bg-white rounded border border-[#dfe4eb] p-1 flex items-end gap-0.5 overflow-hidden">
              {node.embedding.slice(0, 48).map((val, idx) => {
                const heightPct = Math.max(10, Math.min(100, Math.abs(val) * 200));
                const isHovered = hoveredDim?.idx === idx;
                return (
                  <div
                    key={idx}
                    onMouseEnter={() => setHoveredDim({ idx, val })}
                    onMouseLeave={() => setHoveredDim(null)}
                    className="flex-1 rounded-t-2xs transition-all duration-100 cursor-pointer"
                    style={{
                      height: `${heightPct}%`,
                      backgroundColor: isHovered
                        ? "#0a0d14"
                        : val >= 0
                        ? "#1677ff"
                        : "#94a3b8",
                    }}
                    title={`Dim ${idx}: ${val}`}
                  />
                );
              })}
            </div>
            <p className="text-[10px] text-[#868c98] leading-tight">
              Hover bars to inspect scalar embedding coordinates
            </p>
          </div>
        )}

        {/* Entity Attributes Table */}
        <div className="space-y-1.5">
          <span className="text-[11px] font-medium text-[#0a0d14] tracking-tight block">
            Entity properties
          </span>
          <div className="divide-y divide-[#eceff4] border border-[#dfe4eb] rounded-lg bg-white overflow-hidden">
            {Object.entries(node.properties).map(([k, v]) => (
              <div key={k} className="p-2 flex items-center justify-between gap-2 text-xs">
                <span className="text-[11px] font-mono text-[#525866] truncate">
                  {k.replace(/_/g, " ")}
                </span>
                <span className="font-mono text-[#0a0d14] text-[11px] text-right truncate">
                  {typeof v === "boolean" ? (
                    v ? (
                      <span className="text-[#0e8345] font-medium">true</span>
                    ) : (
                      <span className="text-[#d97706] font-medium">false</span>
                    )
                  ) : typeof v === "object" ? (
                    JSON.stringify(v)
                  ) : (
                    String(v)
                  )}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Connected Graph Relationships (1-Hop Traversal) */}
        <div className="space-y-2">
          <span className="text-[11px] font-medium text-[#0a0d14] tracking-tight block">
            Graph relationships ({outboundEdges.length + inboundEdges.length})
          </span>

          {outboundEdges.length > 0 && (
            <div className="space-y-1.5">
              <span className="text-[11px] font-mono text-[#525866] flex items-center gap-1">
                <ArrowRight className="size-3 text-[#1677ff]" />
                Outbound ({outboundEdges.length})
              </span>
              <div className="space-y-1">
                {outboundEdges.map((edge) => {
                  const targetNode = nodeMap.get(edge.target);
                  if (!targetNode) return null;
                  const tStyle = NODE_STYLE_MAP[targetNode.type] || NODE_STYLE_MAP.Task;
                  return (
                    <button
                      key={edge.id}
                      type="button"
                      onClick={() => {
                        soundEngine.playTick();
                        onSelectNode(targetNode);
                      }}
                      className="w-full flex items-center justify-between p-2 rounded-lg bg-[#f8f9fb] hover:bg-[#eceff4] border border-[#dfe4eb] text-left transition-colors cursor-pointer group"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <span
                          className="size-2 rounded-full shrink-0"
                          style={{ backgroundColor: tStyle.fill }}
                        />
                        <span className="text-[11px] font-mono text-[#1677ff]">
                          {edge.type}
                        </span>
                        <span className="text-xs text-[#0a0d14] font-medium truncate">
                          {targetNode.label}
                        </span>
                      </div>
                      <ExternalLink className="size-3 text-[#868c98] group-hover:text-[#0a0d14] shrink-0" />
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {inboundEdges.length > 0 && (
            <div className="space-y-1.5 pt-1">
              <span className="text-[11px] font-mono text-[#525866] flex items-center gap-1">
                <ArrowLeft className="size-3 text-[#525866]" />
                Inbound ({inboundEdges.length})
              </span>
              <div className="space-y-1">
                {inboundEdges.map((edge) => {
                  const sourceNode = nodeMap.get(edge.source);
                  if (!sourceNode) return null;
                  const sStyle = NODE_STYLE_MAP[sourceNode.type] || NODE_STYLE_MAP.Task;
                  return (
                    <button
                      key={edge.id}
                      type="button"
                      onClick={() => {
                        soundEngine.playTick();
                        onSelectNode(sourceNode);
                      }}
                      className="w-full flex items-center justify-between p-2 rounded-lg bg-[#f8f9fb] hover:bg-[#eceff4] border border-[#dfe4eb] text-left transition-colors cursor-pointer group"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <span
                          className="size-2 rounded-full shrink-0"
                          style={{ backgroundColor: sStyle.fill }}
                        />
                        <span className="text-[11px] font-mono text-[#525866]">
                          {edge.type}
                        </span>
                        <span className="text-xs text-[#0a0d14] font-medium truncate">
                          {sourceNode.label}
                        </span>
                      </div>
                      <ExternalLink className="size-3 text-[#868c98] group-hover:text-[#0a0d14] shrink-0" />
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* KùzuDB Cypher Snippet Generator */}
        <div className="p-3 rounded-lg bg-[#0a0d14] text-white border border-[#27272a] space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono text-[#a1a1aa] flex items-center gap-1.5">
              <Terminal className="size-3 text-[#1677ff]" />
              Cypher query
            </span>
            <button
              type="button"
              onClick={() => handleCopyText(cypherQuery, "cypher")}
              className="text-[10px] text-[#a1a1aa] hover:text-white flex items-center gap-1 transition-colors cursor-pointer"
            >
              {copiedKey === "cypher" ? (
                <>
                  <Check className="size-3 text-[#0e8345]" />
                  <span>Copied</span>
                </>
              ) : (
                <>
                  <Copy className="size-3" />
                  <span>Copy</span>
                </>
              )}
            </button>
          </div>
          <code className="block text-[11px] font-mono text-[#e4e4e7] break-all leading-relaxed">
            {cypherQuery}
          </code>
        </div>
      </div>
    </div>
  );
}
