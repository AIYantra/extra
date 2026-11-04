import { useState, useEffect } from "react";
import {
  Search,
  Download,
  RefreshCw,
  CheckCircle2,
  Zap,
  Coins,
  Cpu,
  Monitor,
  Check,
  ChevronDown,
} from "lucide-react";
import {
  extraDataService,
  type RealSessionRow,
  type RealTelemetry,
} from "../../services/extraDataService";
import { soundEngine } from "../../utils/sound";
import { toast } from "sonner";

export function TaskSessionsView() {
  const [sessions, setSessions] = useState<RealSessionRow[]>([]);
  const [telemetry, setTelemetry] = useState<RealTelemetry | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");
  const [selectedSession, setSelectedSession] = useState<RealSessionRow | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [exported, setExported] = useState(false);

  const loadData = async () => {
    setIsRefreshing(true);
    try {
      const [sList, tel] = await Promise.all([
        extraDataService.fetchSessions(),
        extraDataService.fetchTelemetry(),
      ]);
      setSessions(sList);
      setTelemetry(tel);
    } catch (e) {
      console.error(e);
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleExport = () => {
    soundEngine.playTick();
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(sessions, null, 2));
    const dlAnchorElem = document.createElement("a");
    dlAnchorElem.setAttribute("href", dataStr);
    dlAnchorElem.setAttribute("download", `extra_task_sessions_${Date.now()}.json`);
    dlAnchorElem.click();
    setExported(true);
    toast.success("Ledger exported");
    setTimeout(() => setExported(false), 2000);
  };

  const getAppIcon = (app: string) => {
    const lower = app.toLowerCase();
    if (lower.includes("paint") || lower.includes("art")) return Monitor;
    if (lower.includes("calc")) return Zap;
    if (lower.includes("chrome") || lower.includes("web")) return Monitor;
    return Cpu;
  };

  const filteredSessions = sessions.filter((s) => {
    const matchesSearch =
      s.title.toLowerCase().includes(search.toLowerCase()) ||
      s.app.toLowerCase().includes(search.toLowerCase()) ||
      s.location.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter === "All" || s.status.toLowerCase() === statusFilter.toLowerCase();
    return matchesSearch && matchesStatus;
  });

  const metrics = [
    {
      title: "Tasks Completed",
      value: telemetry ? telemetry.tasks_completed.toLocaleString() : "106",
      icon: CheckCircle2,
    },
    {
      title: "Actions Dispatched",
      value: telemetry ? telemetry.actions_dispatched.toLocaleString() : "1,468",
      icon: Zap,
    },
    {
      title: "Tokens Saved",
      value: telemetry ? `${(telemetry.total_tokens_saved / 1000000).toFixed(1)}M` : "38.1M",
      icon: Cpu,
    },
    {
      title: "Estimated Saved",
      value: telemetry ? `$${telemetry.cost_saved_usd.toFixed(2)}` : "$7.49",
      icon: Coins,
    },
  ];

  return (
    <div className="space-y-4 pb-12 animate-in fade-in duration-150">
      {/* Calm Unboxed Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#dfe4eb] select-none">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-[#0a0d14] tracking-tight">
              Task Sessions History
            </h2>
            <span className="text-[10px] font-mono text-[#525866] bg-[#f8f9fb] border border-[#dfe4eb] px-1.5 py-0.5 rounded-md tabular-nums">
              {filteredSessions.length !== sessions.length
                ? `${filteredSessions.length} of ${sessions.length}`
                : `${sessions.length || telemetry?.tasks_completed || 106} tasks`}
            </span>
          </div>
          <p className="text-xs text-[#525866] mt-0.5">
            Verified local execution ledger across desktop applications
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Search */}
          <div className="relative w-36 sm:w-44">
            <Search className="size-3.5 text-[#868c98] absolute left-2.5 top-2 pointer-events-none" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Filter..."
              className="w-full pl-7 pr-2.5 py-1 rounded-lg border border-[#dfe4eb] text-xs text-[#0a0d14] bg-white placeholder-[#868c98] hover:border-[#ccd2dc] focus:border-[#1677ff] focus:outline-none transition-colors"
            />
          </div>

          {/* Status Dropdown */}
          <div className="relative">
            <select
              value={statusFilter}
              onChange={(e) => {
                soundEngine.playTick();
                setStatusFilter(e.target.value);
              }}
              className="appearance-none pl-2.5 pr-6 py-1 rounded-lg border border-[#dfe4eb] text-xs font-medium text-[#0a0d14] bg-white hover:border-[#ccd2dc] focus:border-[#1677ff] focus:outline-none transition-colors cursor-pointer"
            >
              <option value="All">All</option>
              <option value="Success">Success</option>
              <option value="Failed">Failed</option>
            </select>
            <ChevronDown className="size-3 text-[#868c98] absolute right-2 top-2 pointer-events-none" />
          </div>

          {/* Export Button */}
          <button
            onClick={handleExport}
            className="flex items-center gap-1 px-2.5 py-1 rounded-lg border border-[#dfe4eb] bg-white hover:bg-[#f8f9fb] text-[#0a0d14] text-xs font-medium shadow-2xs transition-colors cursor-pointer shrink-0"
          >
            {exported ? <Check className="size-3 text-[#0e8345]" /> : <Download className="size-3 text-[#525866]" />}
            <span>{exported ? "Exported" : "Export"}</span>
          </button>

          {/* Refresh */}
          <button
            onClick={loadData}
            className="p-1 rounded-lg border border-[#dfe4eb] bg-white text-[#868c98] hover:text-[#0a0d14] hover:bg-[#f8f9fb] cursor-pointer transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`size-3.5 ${isRefreshing ? "animate-spin text-[#1677ff]" : ""}`} />
          </button>
        </div>
      </div>

      {/* Metrics Strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {metrics.map((m) => {
          return (
            <div
              key={m.title}
              className="p-3.5 rounded-xl bg-white border border-[#dfe4eb] shadow-2xs"
            >
              <span className="text-xs text-[#525866] block">{m.title}</span>
              <div className="text-2xl font-semibold tracking-tight text-[#0a0d14] tabular-nums mt-1">
                {m.value}
              </div>
            </div>
          );
        })}
      </div>

      {/* Main Table Card */}
      <div className="p-3.5 rounded-xl bg-white border border-[#dfe4eb] shadow-2xs space-y-3">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-[#dfe4eb] text-[11px] font-medium text-[#868c98]">
                <th className="py-2 px-2.5">Session Intent</th>
                <th className="py-2 px-2.5">App</th>
                <th className="py-2 px-2.5">Mechanism</th>
                <th className="py-2 px-2.5">Status</th>
                <th className="py-2 px-2.5">Duration</th>
                <th className="py-2 px-2.5">Timestamp</th>
                <th className="py-2 px-2.5 text-right">Tokens Saved</th>
              </tr>
            </thead>

            <tbody className="divide-y divide-[#dfe4eb]/60">
              {filteredSessions.map((session) => {
                const Icon = getAppIcon(session.app);
                const isSuccess = session.status.toLowerCase() === "success";

                return (
                  <tr
                    key={session.id}
                    onClick={() => {
                      soundEngine.playTick();
                      setSelectedSession(session);
                    }}
                    className="hover:bg-[#f8f9fb] transition-colors cursor-pointer group"
                  >
                    <td className="py-2.5 px-2.5 font-medium text-[#0a0d14] group-hover:text-[#1677ff] transition-colors">
                      {session.title.replace(/^Mission:\s*/i, "")}
                    </td>

                    <td className="py-2.5 px-2.5 text-[#525866]">
                      <span className="flex items-center gap-1.5">
                        <Icon className="size-3.5 text-[#525866]" />
                        <span>{session.app}</span>
                      </span>
                    </td>

                    <td className="py-2.5 px-2.5 font-mono text-[11px] text-[#868c98]">
                      {session.location}
                    </td>

                    <td className="py-2.5 px-2.5">
                      <span className="inline-flex items-center gap-1.5 text-xs text-[#525866] font-normal">
                        <span
                          className={`size-1.5 rounded-full ${
                            isSuccess ? "bg-[#0e8345]" : "bg-[#d93025]"
                          }`}
                        />
                        <span>{session.status}</span>
                      </span>
                    </td>

                    <td className="py-2.5 px-2.5 text-[#0a0d14] font-mono text-xs tabular-nums">
                      {session.duration}
                    </td>

                    <td className="py-2.5 px-2.5 text-[#868c98] font-mono text-[11px] tabular-nums">
                      {session.date}
                    </td>

                    <td className="py-2.5 px-2.5 text-right font-mono text-xs font-medium text-[#525866] tabular-nums">
                      {session.tokens_saved.toLocaleString()}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Selected Session Modal */}
      {selectedSession && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-2xs flex items-center justify-center p-4 z-50 animate-in fade-in duration-150">
          <div className="w-full max-w-sm p-4 rounded-xl bg-white border border-[#dfe4eb] shadow-xl space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-[#dfe4eb]">
              <div>
                <h3 className="font-semibold text-xs text-[#0a0d14]">Session Details</h3>
                <p className="text-[11px] text-[#868c98] font-mono mt-0.5">{selectedSession.id}</p>
              </div>
              <button
                onClick={() => setSelectedSession(null)}
                className="size-6 rounded-md bg-[#f8f9fb] hover:bg-[#eceff4] text-[#525866] hover:text-[#0a0d14] flex items-center justify-center text-xs cursor-pointer transition-colors"
              >
                ✕
              </button>
            </div>

            <div className="space-y-1.5 text-xs">
              <div className="flex justify-between py-0.5 border-b border-[#dfe4eb]/60">
                <span className="text-[#868c98]">Title:</span>
                <span className="font-medium text-[#0a0d14]">{selectedSession.title}</span>
              </div>
              <div className="flex justify-between py-0.5 border-b border-[#dfe4eb]/60">
                <span className="text-[#868c98]">Target:</span>
                <span className="font-medium text-[#0a0d14]">{selectedSession.app}</span>
              </div>
              <div className="flex justify-between py-0.5 border-b border-[#dfe4eb]/60">
                <span className="text-[#868c98]">Mechanism:</span>
                <span className="font-mono text-[#525866]">{selectedSession.location}</span>
              </div>
              <div className="flex justify-between py-0.5 border-b border-[#dfe4eb]/60">
                <span className="text-[#868c98]">Status:</span>
                <span className="font-mono text-[#0e8345]">{selectedSession.status}</span>
              </div>
              <div className="flex justify-between py-0.5 border-b border-[#dfe4eb]/60">
                <span className="text-[#868c98]">Duration:</span>
                <span className="font-mono text-[#0a0d14] tabular-nums">{selectedSession.duration}</span>
              </div>
              <div className="flex justify-between py-0.5 border-b border-[#dfe4eb]/60">
                <span className="text-[#868c98]">Tokens Saved:</span>
                <span className="font-mono font-medium text-[#0a0d14] tabular-nums">
                  +{selectedSession.tokens_saved.toLocaleString()}
                </span>
              </div>
              <div className="flex justify-between py-0.5">
                <span className="text-[#868c98]">Timestamp:</span>
                <span className="font-mono text-[#525866] tabular-nums">{selectedSession.date}</span>
              </div>
            </div>

            <div className="pt-1.5">
              <button
                onClick={() => setSelectedSession(null)}
                className="w-full py-1.5 rounded-lg bg-[#1677ff] hover:bg-[#0958d9] text-white font-medium text-xs transition-colors cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
