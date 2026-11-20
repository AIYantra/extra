import { useEffect, useRef, useState, useCallback } from "react";
import {
  type KuzuNode,
  type KuzuEdge,
  type KuzuGraphData,
  NODE_STYLE_MAP,
} from "./kuzuSimulationData";
import { ZoomIn, ZoomOut, RotateCcw, Maximize2 } from "lucide-react";
import { soundEngine } from "../../../utils/sound";

interface KuzuTopologyCanvasProps {
  graph: KuzuGraphData;
  selectedNodeId: string | null;
  highlightedNodeIds: Set<string> | null;
  onSelectNode: (node: KuzuNode | null) => void;
  isSimulating: boolean;
  onToggleSimulating: () => void;
  onResetView?: () => void;
}

// Studio color lightening utility for 3D tactile node gradients
function lightenHex(hex: string, percent: number): string {
  try {
    const clean = hex.replace("#", "");
    const num = parseInt(clean, 16);
    const amt = Math.round(2.55 * percent);
    const R = Math.min(255, (num >> 16) + amt);
    const G = Math.min(255, ((num >> 8) & 0x00ff) + amt);
    const B = Math.min(255, (num & 0x0000ff) + amt);
    return `rgb(${R},${G},${B})`;
  } catch {
    return hex;
  }
}

export function KuzuTopologyCanvas({
  graph,
  selectedNodeId,
  highlightedNodeIds,
  onSelectNode,
  isSimulating,
  onToggleSimulating,
}: KuzuTopologyCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Viewport Transform (Pan & Zoom)
  const [zoom, setZoom] = useState<number>(1.0);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);

  // Dragging State
  const isPanningRef = useRef<boolean>(false);
  const panStartRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const draggedNodeRef = useRef<KuzuNode | null>(null);
  const dragMovedRef = useRef<boolean>(false);

  // Internal Nodes & Edges references for physics loop
  const nodesRef = useRef<KuzuNode[]>(graph.nodes);
  const edgesRef = useRef<KuzuEdge[]>(graph.edges);

  // Keep internal references synchronized when graph changes
  useEffect(() => {
    // Preserve existing positions if node already existed
    const existingMap = new Map<string, KuzuNode>(
      nodesRef.current.map((n) => [n.id, n])
    );
    nodesRef.current = graph.nodes.map((n) => {
      const existing = existingMap.get(n.id);
      if (existing) {
        return {
          ...n,
          x: existing.x,
          y: existing.y,
          vx: existing.vx,
          vy: existing.vy,
          fx: existing.fx,
          fy: existing.fy,
        };
      }
      return { ...n };
    });
    edgesRef.current = graph.edges;
  }, [graph]);

  // Screen to World Coordinate Conversion
  const screenToWorld = useCallback(
    (screenX: number, screenY: number, width: number, height: number) => {
      const cx = width / 2;
      const cy = height / 2;
      const worldX = (screenX - cx - pan.x) / zoom;
      const worldY = (screenY - cy - pan.y) / zoom;
      return { worldX, worldY };
    },
    [pan, zoom]
  );

  // Reset Camera View to Center
  const handleResetView = () => {
    soundEngine.playTick();
    setZoom(1.0);
    setPan({ x: 0, y: 0 });
  };

  // Camera Fit to View - Centers and Scales all Nodes Smoothly
  const handleFitToView = () => {
    soundEngine.playTick();
    const nodes = nodesRef.current;
    if (nodes.length === 0) return;
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    for (const n of nodes) {
      if (n.x < minX) minX = n.x;
      if (n.x > maxX) maxX = n.x;
      if (n.y < minY) minY = n.y;
      if (n.y > maxY) maxY = n.y;
    }
    const canvas = canvasRef.current;
    if (!canvas) return;
    const padding = 100;
    const graphWidth = Math.max(100, maxX - minX + padding * 2);
    const graphHeight = Math.max(100, maxY - minY + padding * 2);
    const targetZoom = Math.min(
      1.6,
      Math.max(0.4, Math.min(canvas.clientWidth / graphWidth, canvas.clientHeight / graphHeight))
    );
    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;
    setZoom(Number(targetZoom.toFixed(2)));
    setPan({ x: -centerX * targetZoom, y: -centerY * targetZoom });
  };

  const handleZoom = (delta: number) => {
    soundEngine.playTick();
    setZoom((prev) => Math.min(2.5, Math.max(0.35, prev + delta)));
  };

  // ---------------------------------------------------------------------------
  // PHYSICS SIMULATION ENGINE (Force-Directed 60fps Tick)
  // ---------------------------------------------------------------------------
  useEffect(() => {
    let animId: number;

    const tick = () => {
      if (isSimulating) {
        const nodes = nodesRef.current;
        const edges = edgesRef.current;
        const nodeMap = new Map<string, KuzuNode>(nodes.map((n) => [n.id, n]));

        // 1. Repulsion between all node pairs
        const kRepulsion = 1200;
        for (let i = 0; i < nodes.length; i++) {
          const a = nodes[i];
          for (let j = i + 1; j < nodes.length; j++) {
            const b = nodes[j];
            const dx = b.x - a.x;
            const dy = b.y - a.y;
            const distSq = dx * dx + dy * dy || 1;
            const dist = Math.sqrt(distSq);

            if (dist < 350) {
              const force = kRepulsion / distSq;
              const fx = (dx / dist) * force;
              const fy = (dy / dist) * force;

              if (a.fx === undefined || a.fx === null) {
                a.vx = (a.vx || 0) - fx;
                a.vy = (a.vy || 0) - fy;
              }
              if (b.fx === undefined || b.fx === null) {
                b.vx = (b.vx || 0) + fx;
                b.vy = (b.vy || 0) + fy;
              }
            }
          }
        }

        // 2. Spring attraction along edges
        const kSpring = 0.035;
        const targetLen = 95;
        for (const edge of edges) {
          const src = nodeMap.get(edge.source);
          const tgt = nodeMap.get(edge.target);
          if (src && tgt) {
            const dx = tgt.x - src.x;
            const dy = tgt.y - src.y;
            const dist = Math.sqrt(dx * dx + dy * dy) || 1;
            const displacement = dist - targetLen;
            const force = displacement * kSpring;
            const fx = (dx / dist) * force;
            const fy = (dy / dist) * force;

            if (src.fx === undefined || src.fx === null) {
              src.vx = (src.vx || 0) + fx;
              src.vy = (src.vy || 0) + fy;
            }
            if (tgt.fx === undefined || tgt.fx === null) {
              tgt.vx = (tgt.vx || 0) - fx;
              tgt.vy = (tgt.vy || 0) - fy;
            }
          }
        }

        // 3. Center Gravity & Position Integration
        const kGravity = 0.015;
        const damping = 0.88;
        for (const n of nodes) {
          if (n.fx !== undefined && n.fx !== null && n.fy !== undefined && n.fy !== null) {
            n.x = n.fx;
            n.y = n.fy;
            n.vx = 0;
            n.vy = 0;
            continue;
          }

          // Gravity pull to (0,0)
          n.vx = ((n.vx || 0) - n.x * kGravity) * damping;
          n.vy = ((n.vy || 0) - n.y * kGravity) * damping;

          n.x += n.vx;
          n.y += n.vy;
        }
      }

      // Draw Canvas Frame
      draw();
      animId = requestAnimationFrame(tick);
    };

    // -------------------------------------------------------------------------
    // CANVAS RENDERER (High-DPI Retina Buffer)
    // -------------------------------------------------------------------------
    const draw = () => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      const dpr = window.devicePixelRatio || 1;
      const width = canvas.clientWidth;
      const height = canvas.clientHeight;

      if (canvas.width !== width * dpr || canvas.height !== height * dpr) {
        canvas.width = width * dpr;
        canvas.height = height * dpr;
      }

      ctx.save();
      ctx.scale(dpr, dpr);
      ctx.clearRect(0, 0, width, height);

      const cx = width / 2 + pan.x;
      const cy = height / 2 + pan.y;

      // Transform Viewport
      ctx.translate(cx, cy);
      ctx.scale(zoom, zoom);

      const nodes = nodesRef.current;
      const edges = edgesRef.current;
      const nodeMap = new Map<string, KuzuNode>(nodes.map((n) => [n.id, n]));
      const draggedNode = draggedNodeRef.current;

      // 1. Draw Edges
      for (const edge of edges) {
        const src = nodeMap.get(edge.source);
        const tgt = nodeMap.get(edge.target);
        if (!src || !tgt) continue;

        const isConnectedToDragged =
          draggedNode && (draggedNode.id === src.id || draggedNode.id === tgt.id);

        const isRelated =
          selectedNodeId === src.id ||
          selectedNodeId === tgt.id ||
          hoveredNodeId === src.id ||
          hoveredNodeId === tgt.id;

        const isHighlighted =
          !highlightedNodeIds ||
          (highlightedNodeIds.has(src.id) && highlightedNodeIds.has(tgt.id));

        const isDimmed =
          (draggedNode && !isConnectedToDragged) ||
          (!draggedNode && selectedNodeId && !isRelated) ||
          (highlightedNodeIds && !isHighlighted);

        ctx.beginPath();
        ctx.moveTo(src.x, src.y);
        ctx.lineTo(tgt.x, tgt.y);

        if (isConnectedToDragged) {
          ctx.strokeStyle = "#1677ff";
          ctx.lineWidth = 2.8;
          ctx.globalAlpha = 1.0;
        } else if (isRelated || (highlightedNodeIds && isHighlighted)) {
          ctx.strokeStyle = "#1677ff";
          ctx.lineWidth = 2.2;
          ctx.globalAlpha = 1.0;
        } else if (isDimmed) {
          ctx.strokeStyle = "#cbd5e1";
          ctx.lineWidth = 1.0;
          ctx.globalAlpha = 0.18;
        } else {
          ctx.strokeStyle = "#94a3b8";
          ctx.lineWidth = 1.2;
          ctx.globalAlpha = 0.55;
        }
        ctx.stroke();

        // Edge Directional Arrow
        const dx = tgt.x - src.x;
        const dy = tgt.y - src.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const tgtStyle = NODE_STYLE_MAP[tgt.type] || NODE_STYLE_MAP.Task;
        const arrowDist = dist - tgtStyle.radius - 4;
        const arrowX = src.x + (dx / dist) * arrowDist;
        const arrowY = src.y + (dy / dist) * arrowDist;
        const angle = Math.atan2(dy, dx);

        ctx.save();
        ctx.translate(arrowX, arrowY);
        ctx.rotate(angle);
        ctx.beginPath();
        ctx.moveTo(0, 0);
        ctx.lineTo(-6, -3.5);
        ctx.lineTo(-6, 3.5);
        ctx.closePath();
        ctx.fillStyle = ctx.strokeStyle;
        ctx.fill();
        ctx.restore();

        // Edge Label (Only when zoomed in or related)
        if (zoom >= 0.85 && (isRelated || isConnectedToDragged || !isDimmed)) {
          const midX = (src.x + tgt.x) / 2;
          const midY = (src.y + tgt.y) / 2;
          ctx.font = "8px 'JetBrains Mono', monospace";
          ctx.fillStyle = isConnectedToDragged || isRelated ? "#1677ff" : "#64748b";
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillText(edge.type, midX, midY - 6);
        }
      }
      ctx.globalAlpha = 1.0;

      // 2. Draw Nodes
      for (const node of nodes) {
        const style = NODE_STYLE_MAP[node.type] || NODE_STYLE_MAP.Task;
        const isSelected = selectedNodeId === node.id;
        const isHovered = hoveredNodeId === node.id;
        const isDragged = draggedNode && draggedNode.id === node.id;
        const isConnectedToDragged =
          draggedNode &&
          edges.some(
            (e) =>
              (e.source === draggedNode.id && e.target === node.id) ||
              (e.target === draggedNode.id && e.source === node.id)
          );

        const isMatch = !highlightedNodeIds || highlightedNodeIds.has(node.id);
        const isDimmed =
          (draggedNode && !isDragged && !isConnectedToDragged) ||
          (!draggedNode && highlightedNodeIds && !isMatch) ||
          (!draggedNode && selectedNodeId && !isSelected && !isHovered && !isMatch);

        ctx.save();
        ctx.globalAlpha = isDimmed ? 0.22 : 1.0;

        // Kinetic Active Grab / Selection / Hover Halo Ring
        if (isDragged) {
          ctx.beginPath();
          ctx.arc(node.x, node.y, style.radius + 8, 0, Math.PI * 2);
          ctx.fillStyle = "rgba(22, 119, 255, 0.14)";
          ctx.fill();
          ctx.strokeStyle = "#1677ff";
          ctx.lineWidth = 2;
          ctx.setLineDash([4, 3]);
          ctx.stroke();
          ctx.setLineDash([]);
        } else if (isSelected || isHovered) {
          ctx.beginPath();
          ctx.arc(node.x, node.y, style.radius + (isSelected ? 7 : 4), 0, Math.PI * 2);
          ctx.fillStyle = isSelected ? "rgba(22, 119, 255, 0.16)" : "rgba(100, 116, 139, 0.12)";
          ctx.fill();
          ctx.strokeStyle = isSelected ? "#1677ff" : "#94a3b8";
          ctx.lineWidth = 1.5;
          ctx.stroke();
        }

        // Tactile Elevation Drop Shadow when Dragged or Selected
        if (isDragged || isSelected) {
          ctx.shadowColor = "rgba(10, 13, 20, 0.24)";
          ctx.shadowBlur = isDragged ? 20 : 12;
          ctx.shadowOffsetY = isDragged ? 6 : 3;
        }

        // Main Node Body with 3D Spherical Radial Gradient
        ctx.beginPath();
        const displayRadius = isDragged ? style.radius + 2 : style.radius;
        ctx.arc(node.x, node.y, displayRadius, 0, Math.PI * 2);

        const grad = ctx.createRadialGradient(
          node.x - displayRadius * 0.35,
          node.y - displayRadius * 0.35,
          displayRadius * 0.1,
          node.x,
          node.y,
          displayRadius
        );
        grad.addColorStop(0, lightenHex(style.fill, 28));
        grad.addColorStop(1, style.fill);
        ctx.fillStyle = grad;
        ctx.fill();

        ctx.strokeStyle = isSelected || isDragged ? "#0958d9" : style.stroke;
        ctx.lineWidth = isSelected || isDragged ? 2.5 : 1.5;
        ctx.stroke();

        // Clear shadow before drawing glyph & label
        ctx.shadowColor = "transparent";

        // Node Inner Glyph
        ctx.fillStyle = style.text;
        ctx.font = "600 10px 'Inter Tight', sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        const iconChar =
          node.type === "Task"
            ? "T"
            : node.type === "App"
            ? "A"
            : node.type === "AppQuirk"
            ? "Q"
            : node.type === "Artifact"
            ? "R"
            : node.type === "StallEvent"
            ? "!"
            : "•";
        ctx.fillText(iconChar, node.x, node.y);

        // Node Label Underneath (Frosted Glass Pill)
        ctx.font = "500 10.5px 'Inter Tight', -apple-system, sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "top";

        const textMetrics = ctx.measureText(node.label);
        const textWidth = textMetrics.width;
        const textX = node.x - textWidth / 2 - 4;
        const textY = node.y + displayRadius + 5;

        ctx.fillStyle = "rgba(255, 255, 255, 0.95)";
        ctx.beginPath();
        ctx.roundRect(textX, textY - 1, textWidth + 8, 15, 4);
        ctx.fill();
        ctx.strokeStyle = isSelected || isDragged ? "#1677ff" : "rgba(223, 228, 235, 0.85)";
        ctx.lineWidth = 1;
        ctx.stroke();

        ctx.fillStyle = isSelected || isDragged ? "#1677ff" : "#0f172a";
        ctx.fillText(node.label, node.x, textY);

        ctx.restore();
      }

      ctx.restore();
    };

    animId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animId);
  }, [pan, zoom, selectedNodeId, hoveredNodeId, highlightedNodeIds, isSimulating]);

  // ---------------------------------------------------------------------------
  // MOUSE & GESTURE INTERACTION HANDLERS
  // ---------------------------------------------------------------------------
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const screenX = e.clientX - rect.left;
    const screenY = e.clientY - rect.top;
    const { worldX, worldY } = screenToWorld(
      screenX,
      screenY,
      canvas.clientWidth,
      canvas.clientHeight
    );

    // Find clicked node
    const clicked = nodesRef.current.find((n) => {
      const style = NODE_STYLE_MAP[n.type] || NODE_STYLE_MAP.Task;
      const dx = n.x - worldX;
      const dy = n.y - worldY;
      return dx * dx + dy * dy <= style.radius * style.radius;
    });

    if (clicked) {
      draggedNodeRef.current = clicked;
      dragMovedRef.current = false;
      clicked.fx = clicked.x;
      clicked.fy = clicked.y;
    } else {
      isPanningRef.current = true;
      panStartRef.current = { x: e.clientX - pan.x, y: e.clientY - pan.y };
    }
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const screenX = e.clientX - rect.left;
    const screenY = e.clientY - rect.top;

    if (draggedNodeRef.current) {
      dragMovedRef.current = true;
      const { worldX, worldY } = screenToWorld(
        screenX,
        screenY,
        canvas.clientWidth,
        canvas.clientHeight
      );
      draggedNodeRef.current.fx = worldX;
      draggedNodeRef.current.fy = worldY;
      draggedNodeRef.current.x = worldX;
      draggedNodeRef.current.y = worldY;
      return;
    }

    if (isPanningRef.current) {
      setPan({
        x: e.clientX - panStartRef.current.x,
        y: e.clientY - panStartRef.current.y,
      });
      return;
    }

    // Hover Detection
    const { worldX, worldY } = screenToWorld(
      screenX,
      screenY,
      canvas.clientWidth,
      canvas.clientHeight
    );
    const hovered = nodesRef.current.find((n) => {
      const style = NODE_STYLE_MAP[n.type] || NODE_STYLE_MAP.Task;
      const dx = n.x - worldX;
      const dy = n.y - worldY;
      return dx * dx + dy * dy <= style.radius * style.radius;
    });

    setHoveredNodeId(hovered ? hovered.id : null);
  };

  const handleMouseUp = () => {
    if (draggedNodeRef.current) {
      if (!dragMovedRef.current) {
        // Simple click without drag -> select node
        soundEngine.playTick();
        onSelectNode(draggedNodeRef.current);
      }
      // Release pin after drag to let physics naturally settle, or keep pinned
      draggedNodeRef.current.fx = null;
      draggedNodeRef.current.fy = null;
      draggedNodeRef.current = null;
      dragMovedRef.current = false;
    } else if (isPanningRef.current) {
      isPanningRef.current = false;
    } else {
      // Clicked background -> clear selection
      onSelectNode(null);
    }
  };

  const handleWheel = (e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    const delta = e.deltaY < 0 ? 0.08 : -0.08;
    setZoom((prev) => Math.min(2.5, Math.max(0.35, prev + delta)));
  };

  return (
    <div
      ref={containerRef}
      className="relative w-full h-full min-h-[460px] rounded-xl overflow-hidden select-none"
      style={{
        backgroundImage: "radial-gradient(#dfe4eb 1.2px, transparent 1.2px)",
        backgroundSize: "24px 24px",
        backgroundColor: "#fcfdfe",
      }}
    >
      <canvas
        ref={canvasRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onWheel={handleWheel}
        className={`w-full h-full block ${
          draggedNodeRef.current
            ? "cursor-grabbing"
            : hoveredNodeId
            ? "cursor-pointer"
            : isPanningRef.current
            ? "cursor-grabbing"
            : "cursor-grab"
        }`}
      />

      {/* Floating Studio Glass HUD */}
      <div className="absolute bottom-4 left-4 flex items-center gap-1.5 p-1.5 bg-white/95 backdrop-blur-md border border-[#dfe4eb] rounded-full shadow-md z-10 select-none">
        <button
          onClick={() => handleZoom(-0.15)}
          className="p-1.5 rounded-full hover:bg-[#f4f5f8] text-[#525866] hover:text-[#0a0d14] transition-colors cursor-pointer"
          title="Zoom Out"
        >
          <ZoomOut className="size-3.5" />
        </button>
        <button
          onClick={handleResetView}
          className="text-[11px] font-mono text-[#525866] hover:text-[#0a0d14] tabular-nums px-2 py-0.5 rounded-md hover:bg-[#f4f5f8] transition-colors cursor-pointer"
          title="Click to reset zoom to 100%"
        >
          {Math.round(zoom * 100)}%
        </button>
        <button
          onClick={() => handleZoom(0.15)}
          className="p-1.5 rounded-full hover:bg-[#f4f5f8] text-[#525866] hover:text-[#0a0d14] transition-colors cursor-pointer"
          title="Zoom In"
        >
          <ZoomIn className="size-3.5" />
        </button>
        <div className="w-px h-3.5 bg-[#dfe4eb] mx-0.5" />
        <button
          onClick={handleFitToView}
          className="p-1.5 rounded-full hover:bg-[#f4f5f8] text-[#525866] hover:text-[#0a0d14] transition-colors cursor-pointer"
          title="Fit graph to view"
        >
          <Maximize2 className="size-3.5" />
        </button>
        <button
          onClick={handleResetView}
          className="p-1.5 rounded-full hover:bg-[#f4f5f8] text-[#525866] hover:text-[#0a0d14] transition-colors cursor-pointer"
          title="Reset pan & zoom"
        >
          <RotateCcw className="size-3.5" />
        </button>
        <div className="w-px h-3.5 bg-[#dfe4eb] mx-0.5" />
        <button
          onClick={() => {
            soundEngine.playTick();
            onToggleSimulating();
          }}
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-colors cursor-pointer ${
            isSimulating
              ? "bg-[#1677ff]/10 text-[#1677ff] hover:bg-[#1677ff]/18"
              : "bg-[#f4f5f8] text-[#525866] hover:text-[#0a0d14]"
          }`}
          title={isSimulating ? "Pause physics simulation" : "Resume physics simulation"}
        >
          <span
            className={`size-1.5 rounded-full ${
              isSimulating ? "bg-[#1677ff] animate-pulse" : "bg-[#868c98]"
            }`}
          />
          <span className="text-[11px] font-mono tabular-nums">{isSimulating ? "Live Physics" : "Paused"}</span>
        </button>
      </div>
    </div>
  );
}
