import { useState, useEffect } from "react";
import {
  Zap,
  Box,
  Wrench,
  Database,
  Terminal,
  Calculator,
  Globe,
  FolderOpen,
  Laptop,
  RefreshCw,
  ChevronRight,
} from "lucide-react";
import {
  extraDataService,
  type RealTelemetry,
  type ConnectedClient,
  type RealSessionRow,
} from "../../services/extraDataService";
import { soundEngine } from "../../utils/sound";
import { getClientLogo } from "../../utils/clientLogos";
import { useAuthStore } from "../../store/useAuthStore";

interface ReferenceDashboardViewProps {
  onNavigateTab?: (tab: string) => void;
}

export function ReferenceDashboardView({ onNavigateTab }: ReferenceDashboardViewProps) {
  const { isAuthenticated, relayToken } = useAuthStore();
  const [telemetry, setTelemetry] = useState<RealTelemetry | null>(null);
  const [clients, setClients] = useState<ConnectedClient[]>([]);
  const [sessions, setSessions] = useState<RealSessionRow[]>([]);
  const [chartViewMode, setChartViewMode] = useState<"weekly" | "monthly">("weekly");
  const [hoveredBarIndex, setHoveredBarIndex] = useState<number | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Load real data from PC engine on mount & background poll
  useEffect(() => {
    let isMounted = true;

    // Ensure relay is automatically running for logged in users unless explicitly paused
    if (isAuthenticated && localStorage.getItem("extra_relay_user_stopped") !== "true") {
      extraDataService.startRelay(relayToken || undefined).catch(() => {});
    }

    async function loadData() {
      try {
        const [tel, clis, sess] = await Promise.all([
          extraDataService.fetchTelemetry(),
          extraDataService.fetchClients(),
          extraDataService.fetchSessions(),
        ]);
        if (isMounted) {
          setTelemetry(tel);
          setClients(Array.isArray(clis) ? clis : (clis as any)?.clients || []);
          setSessions(Array.isArray(sess) ? sess : (sess as any)?.sessions || []);
        }
      } catch (err) {
        console.error("Failed to load real extra data:", err);
      }
    }

    loadData();
    const interval = setInterval(loadData, 3500);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [isAuthenticated, relayToken]);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    soundEngine.playTick();
    try {
      const [tel, clis, sess] = await Promise.all([
        extraDataService.fetchTelemetry(),
        extraDataService.fetchClients(),
        extraDataService.fetchSessions(),
      ]);
      setTelemetry(tel);
      setClients(Array.isArray(clis) ? clis : (clis as any)?.clients || []);
      setSessions(Array.isArray(sess) ? sess : (sess as any)?.sessions || []);
      soundEngine.playSuccessChime();
    } finally {
      setIsRefreshing(false);
    }
  };

  // Primary Telemetry Strip — 4 High-Density Engineering Metrics (Unslop Pass 1, 5, 6)
  const primaryStats = [
    {
      id: "latency",
      value: telemetry ? `${telemetry.capture_latency_ms.toFixed(1)}ms` : "—",
      title: "Optical Settle Latency",
      caption: "DXGI Desktop Duplication",
      icon: Zap,
      tab: "telemetry",
    },
    {
      id: "actions",
      value: telemetry ? telemetry.actions_dispatched.toLocaleString() : "—",
      title: "Hardware Dispatches",
      caption: telemetry ? `${telemetry.tasks_completed} completed missions` : "Connecting to engine...",
      icon: Terminal,
      tab: "sessions",
    },
    {
      id: "tools",
      value: telemetry ? `${telemetry.native_tools_count}` : "40",
      title: "Native MCP Tools",
      caption: telemetry ? `${telemetry.active_skills_count} hardened playbooks` : "MCP playbooks",
      icon: Wrench,
      tab: "tools",
    },
    {
      id: "memory",
      value: telemetry ? telemetry.kuzu_facts_count.toLocaleString() : "—",
      title: "Memory Graph Nodes",
      caption: "KùzuDB vector topology",
      icon: Database,
      tab: "memory",
    },
  ];

  // Active chart items based on weekly vs monthly selection (100% dynamically binned from recent_events)
  const activeChartData = (chartViewMode === "weekly"
    ? telemetry?.activity_chart?.weekly
    : telemetry?.activity_chart?.monthly) || [];

  const getClientIcon = (name: string) => {
    if (name.includes("Cursor")) return Laptop;
    if (name.includes("Claude")) return Terminal;
    if (name.includes("Antigravity")) return Zap;
    return Globe;
  };

  const getAppIcon = (app: string) => {
    const lower = app.toLowerCase();
    if (lower.includes("calc")) return Calculator;
    if (lower.includes("paint")) return Box;
    if (lower.includes("chrome") || lower.includes("web")) return Globe;
    if (lower.includes("folder") || lower.includes("file") || lower.includes("download")) return FolderOpen;
    return Laptop;
  };

  return (
    <div className="space-y-6 pb-12 animate-in fade-in duration-150">
      {/* =========================================================================
          ROW 1: PRIMARY TELEMETRY STRIP (4 HIGH-DENSITY INSTRUMENTS)
          Unslop Pass 1 (Spacing), Pass 3 (Icons), Pass 5 (Type), Pass 6 (Layout)
          ========================================================================= */}
      <section className="space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <div className="flex items-center gap-2.5">
              <h2 className="text-base font-semibold text-[#1a1a1c] tracking-tight">
                Operational Telemetry
              </h2>
              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-[#f8f9fb] border border-[#dfe4eb] text-[11px] font-mono text-[#525866]">
                <span className="size-1.5 rounded-full bg-[#0e8345]" />
                <span>Nominal · 100% Health</span>
              </span>
            </div>
            <p className="text-xs text-[#525866] mt-0.5">
              Real-time hardware dispatch and autonomous computer-use metrics
            </p>
          </div>

          <button
            onClick={handleRefresh}
            className="self-start sm:self-auto flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#dfe4eb] bg-white text-xs font-medium text-[#1a1a1c] hover:bg-[#f8f9fb] hover:border-[#ccd2dc] transition-colors duration-150 cursor-pointer shadow-2xs"
            title="Resync telemetry"
          >
            <RefreshCw className={`size-3.5 ${isRefreshing ? "animate-spin text-[#1677ff]" : "text-[#868c98]"}`} />
            <span>Sync</span>
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
          {primaryStats.map((stat) => {
            const Icon = stat.icon;
            return (
              <div
                key={stat.id}
                onClick={() => {
                  if (onNavigateTab && stat.tab) {
                    soundEngine.playTick();
                    onNavigateTab(stat.tab);
                  }
                }}
                className="group relative flex flex-col justify-between p-4.5 rounded-xl bg-white border border-[#dfe4eb] shadow-2xs hover:border-[#1677ff]/60 hover:shadow-xs transition-[border-color,box-shadow] duration-150 cursor-pointer text-left min-h-[120px]"
              >
                {/* Header: Label + Quiet Line Icon */}
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-[#525866] tracking-tight">
                    {stat.title}
                  </span>
                  <Icon className="size-4 text-[#868c98] group-hover:text-[#1677ff] transition-colors duration-150" />
                </div>

                {/* Primary Metric: Tabular Monospace Hero */}
                <div className="mt-2 space-y-1">
                  <div className="text-2xl sm:text-[26px] font-bold font-mono tracking-tight text-[#1a1a1c] tabular-nums">
                    {stat.value}
                  </div>
                  <div className="text-[11px] text-[#868c98] font-normal truncate">
                    {stat.caption}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* =========================================================================
          ROW 2: STATISTICS BAR CHART (60%) + CONNECTED AI CLIENTS (40%)
          Unslop Pass 2 (Color), Pass 6 (Layout), Pass 7 (Details), Pass 8 (Visuals)
          ========================================================================= */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left Card: Hardware Dispatch Activity Chart */}
        <div className="lg:col-span-7 rounded-2xl bg-white border border-[#dfe4eb] p-5 shadow-2xs flex flex-col justify-between">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-5">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-semibold text-[#1a1a1c] tracking-tight">
                  Activity & Hardware Dispatch
                </h3>
                <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[10px] font-mono font-medium bg-[#f8f9fb] text-[#0e8345] border border-[#dfe4eb]">
                  <span className="size-1.5 rounded-full bg-[#0e8345]" />
                  Live
                </span>
              </div>
              <p className="text-[11px] text-[#525866] font-mono mt-0.5">
                Total {telemetry ? telemetry.actions_dispatched.toLocaleString() : "—"} Actions Executed
              </p>
            </div>

            <div className="flex items-center gap-3">
              {/* Weekly / Monthly Toggle Pill */}
              <div className="flex items-center p-0.5 bg-[#f0f2f6] rounded-lg border border-[#dfe4eb]">
                <button
                  type="button"
                  onClick={() => {
                    soundEngine.playTick();
                    setChartViewMode("weekly");
                    setHoveredBarIndex(null);
                  }}
                  className={`px-2.5 py-1 text-[11px] font-medium rounded-md transition-colors cursor-pointer ${
                    chartViewMode === "weekly"
                      ? "bg-white text-[#1a1a1c] shadow-2xs font-semibold"
                      : "text-[#525866] hover:text-[#1a1a1c]"
                  }`}
                >
                  Weekly
                </button>
                <button
                  type="button"
                  onClick={() => {
                    soundEngine.playTick();
                    setChartViewMode("monthly");
                    setHoveredBarIndex(null);
                  }}
                  className={`px-2.5 py-1 text-[11px] font-medium rounded-md transition-colors cursor-pointer ${
                    chartViewMode === "monthly"
                      ? "bg-white text-[#1a1a1c] shadow-2xs font-semibold"
                      : "text-[#525866] hover:text-[#1a1a1c]"
                  }`}
                >
                  Monthly
                </button>
              </div>

              {/* Legend */}
              <div className="flex items-center gap-3 text-xs font-medium pl-1">
                <span className="flex items-center gap-1.5 text-[#1a1a1c]">
                  <span className="size-2 rounded-xs bg-[#1a1a1c]" />
                  Actions
                </span>
                <span className="flex items-center gap-1.5 text-[#868c98]">
                  <span className="size-2 rounded-xs bg-[#dfe4eb]" />
                  Perceptions
                </span>
              </div>
            </div>
          </div>

          {/* Bar Chart Visualization with Crisp Top Radii */}
          <div className="relative pt-6 pb-1">
            {/* Active Period Tooltip Callout */}
            {hoveredBarIndex !== null && activeChartData[hoveredBarIndex] && (
              <div
                className="absolute top-0 -translate-x-1/2 flex flex-col items-center pointer-events-none transition-[left] duration-150 z-10"
                style={{
                  left: `${((hoveredBarIndex + 0.5) / activeChartData.length) * 100}%`,
                }}
              >
                <div className="bg-[#1a1a1c] text-white text-[11px] font-mono px-2.5 py-1 rounded-md shadow-md whitespace-nowrap flex items-center gap-1.5">
                  <span className="font-semibold">{activeChartData[hoveredBarIndex].period || activeChartData[hoveredBarIndex].label}:</span>
                  <span className="text-[#69b1ff] font-bold">{activeChartData[hoveredBarIndex].actions.toLocaleString()}</span>
                  <span className="text-[#868c98]">actions ·</span>
                  <span className="text-[#bae0ff]">{activeChartData[hoveredBarIndex].perceptions.toLocaleString()}</span>
                  <span className="text-[#868c98]">perceptions</span>
                </div>
              </div>
            )}

            {/* Bars Container */}
            <div className="h-44 flex items-end justify-between gap-3 border-b border-[#eceff4] pb-2 px-2">
              {activeChartData.map((d, idx) => {
                const isHovered = hoveredBarIndex === idx;
                const barWidthClass = chartViewMode === "monthly" ? "w-6 md:w-8" : "w-3 md:w-4.5";
                return (
                  <div
                    key={d.id || d.label}
                    onMouseEnter={() => setHoveredBarIndex(idx)}
                    onMouseLeave={() => setHoveredBarIndex(null)}
                    className="flex-1 flex flex-col items-center justify-end h-full cursor-pointer group"
                  >
                    <div className="flex items-end justify-center gap-1 w-full h-full">
                      {/* Actions Bar (Dark Accent) */}
                      <div
                        className={`${barWidthClass} rounded-t-[2px] transition-all duration-150 ${
                          isHovered ? "bg-[#1677ff]" : d.isCurrent ? "bg-[#1a1a1c]" : "bg-[#2d3139]"
                        }`}
                        style={{ height: `${d.actionsPct}%` }}
                      />
                      {/* Perceptions Bar (Subtle Neutral) */}
                      <div
                        className={`${barWidthClass} rounded-t-[2px] transition-all duration-150 ${
                          isHovered ? "bg-[#bae0ff]" : "bg-[#dfe4eb]"
                        }`}
                        style={{ height: `${d.perceptionsPct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>

            {/* X-Axis Labels */}
            <div className="flex items-center justify-between text-[11px] text-[#868c98] font-mono pt-2 px-2">
              {activeChartData.map((d, idx) => (
                <span
                  key={d.id || d.label}
                  className={`flex-1 text-center truncate ${
                    d.isCurrent
                      ? "font-semibold text-[#1677ff]"
                      : hoveredBarIndex === idx
                      ? "text-[#1a1a1c]"
                      : ""
                  }`}
                >
                  {d.label}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Right Card: Connected AI Environments with Real Logos */}
        <div className="lg:col-span-5 rounded-2xl bg-white border border-[#dfe4eb] p-5 shadow-2xs flex flex-col justify-between">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-[#1a1a1c] tracking-tight">
                Connected AI Environments
              </h3>
              <p className="text-[11px] text-[#525866] mt-0.5">
                Local loopback handshake status
              </p>
            </div>
            <button
              onClick={() => onNavigateTab && onNavigateTab("apps")}
              className="flex items-center gap-1 text-[11px] font-medium text-[#1677ff] hover:text-[#0958d9] transition-colors duration-150 cursor-pointer"
              title="Manage all environments"
            >
              <span>Manage</span>
              <ChevronRight className="size-3" />
            </button>
          </div>

          <div className="space-y-2.5">
            {clients.map((client) => {
              const logoUrl = getClientLogo(client.name);
              const Icon = getClientIcon(client.name);
              const isConnected = client.status === "Connected";

              return (
                <div
                  key={client.name}
                  className="flex items-center justify-between p-2.5 rounded-xl border border-transparent hover:border-[#dfe4eb] hover:bg-[#f8f9fb] transition-colors duration-150"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    {/* Real Logo in Crisp White Container */}
                    <div className="size-9 rounded-lg bg-white border border-[#dfe4eb] shadow-2xs flex items-center justify-center p-1.5 shrink-0">
                      {logoUrl ? (
                        <img
                          src={logoUrl}
                          alt={client.name}
                          className="size-5 object-contain"
                        />
                      ) : (
                        <Icon className="size-4.5 text-[#525866]" />
                      )}
                    </div>

                    <div className="min-w-0">
                      <p className="text-xs font-semibold text-[#1a1a1c] truncate">
                        {client.name}
                      </p>
                      <p className="text-[11px] text-[#868c98] font-mono truncate">
                        {client.subtext}
                      </p>
                    </div>
                  </div>

                  <span className="inline-flex items-center gap-1.5 text-xs text-[#525866] font-normal shrink-0">
                    <span
                      className={`size-1.5 rounded-full ${
                        isConnected ? "bg-[#0e8345]" : "bg-[#868c98]"
                      }`}
                    />
                    <span>{client.status}</span>
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* =========================================================================
          ROW 3: RECENT ACTIVITY SNAPSHOT
          Unslop: High-impact snapshot with direct link to full History ledger
          ========================================================================= */}
      <section className="rounded-2xl bg-white border border-[#dfe4eb] p-5 shadow-2xs space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-[#1a1a1c] tracking-tight">
              Recent Desktop Activity
            </h3>
            <p className="text-xs text-[#525866]">
              Latest autonomous computer-use missions executed locally
            </p>
          </div>

          <button
            onClick={() => onNavigateTab?.("sessions")}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#dfe4eb] bg-white hover:bg-[#f8f9fb] text-xs font-medium text-[#1677ff] hover:text-[#0958d9] transition-colors duration-150 cursor-pointer shadow-2xs"
          >
            <span>View Full Ledger ({sessions.length || telemetry?.tasks_completed || 0})</span>
            <ChevronRight className="size-3.5" />
          </button>
        </div>

        <div className="divide-y divide-[#eceff4] border border-[#eceff4] rounded-xl overflow-hidden">
          {sessions.slice(0, 4).map((row) => {
            const Icon = getAppIcon(row.app);
            const isSuccess = row.status === "Success";
            return (
              <div
                key={row.id}
                onClick={() => onNavigateTab?.("sessions")}
                className="flex items-center justify-between p-3.5 hover:bg-[#f8f9fb] transition-colors duration-150 cursor-pointer group"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="size-8 rounded-lg bg-[#f0f2f6] border border-[#dfe4eb] flex items-center justify-center shrink-0">
                    <Icon className="size-4 text-[#525866]" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-semibold text-[#1a1a1c] group-hover:text-[#1677ff] transition-colors truncate">
                      {row.title.replace(/^Mission:\s*/i, "")}
                    </p>
                    <p className="text-[11px] text-[#868c98] font-mono truncate mt-0.5">
                      {row.app} · {row.location}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-4 shrink-0 text-xs">
                  <span className="font-mono text-[11px] text-[#868c98] tabular-nums hidden sm:inline">
                    {row.date}
                  </span>
                  <span className="font-mono text-xs text-[#1a1a1c] tabular-nums font-medium">
                    {row.duration}
                  </span>
                  <span className="inline-flex items-center gap-1.5 text-xs text-[#525866]">
                    <span className={`size-1.5 rounded-full ${isSuccess ? "bg-[#0e8345]" : "bg-[#d93025]"}`} />
                    <span>{row.status}</span>
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
