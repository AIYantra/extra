import { useState, useRef, useEffect } from "react";
import {
  Terminal as TerminalIcon,
  RotateCw,
  Trash2,
  Copy,
  Check,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useEngineStore } from "../../store/useEngineStore";

interface TerminalLine {
  id: string;
  type: "input" | "output" | "error" | "system";
  text: string;
  timestamp: string;
}

const getInitialLines = (): TerminalLine[] => {
  const time = new Date().toLocaleTimeString();
  return [
    {
      id: "init-1",
      type: "system",
      text: "Extra Sovereign OS Shell v2.4 [Win32 Native Environment]",
      timestamp: time,
    },
    {
      id: "init-2",
      type: "system",
      text: "Connected to Extra MCP Loopback on 127.0.0.1:8000 (FastMCP Streamable / SSE)",
      timestamp: time,
    },
    {
      id: "init-3",
      type: "output",
      text: "Type 'help', 'status', 'health', or any Win32 / Extra intent command.",
      timestamp: time,
    },
  ];
};

export function TerminalView() {
  const [lines, setLines] = useState<TerminalLine[]>(getInitialLines);
  const [inputVal, setInputVal] = useState("");
  const [isExecuting, setIsExecuting] = useState(false);
  const [copied, setCopied] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const telemetry = useEngineStore((state) => state.telemetry);
  const dispatchIntent = useEngineStore((state) => state.dispatchIntent);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [lines]);

  const addLine = (type: TerminalLine["type"], text: string) => {
    const time = new Date().toLocaleTimeString();
    setLines((prev) => [...prev, { id: `${Date.now()}-${Math.random()}`, type, text, timestamp: time }]);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cmd = inputVal.trim();
    if (!cmd || isExecuting) return;

    addLine("input", `$ ${cmd}`);
    setInputVal("");
    setIsExecuting(true);

    if (cmd.toLowerCase() === "clear") {
      setLines([]);
      setIsExecuting(false);
      return;
    }

    if (cmd.toLowerCase() === "help") {
      addLine("system", "Extra Available CLI Commands:");
      addLine("output", "  status       - Show engine metrics, active window, and RSS memory");
      addLine("output", "  health       - Ping MCP loopback server at 127.0.0.1:8000");
      addLine("output", "  clear        - Clear the terminal console buffer");
      addLine("output", "  <intent>     - Compile and execute any macro or desktop subtask");
      setIsExecuting(false);
      return;
    }

    if (cmd.toLowerCase() === "status") {
      addLine("output", `Active Pilot: ${telemetry.active_pilot || "Extra Engine"}`);
      addLine("output", `Target Window: ${telemetry.target_window} (PID: ${telemetry.target_pid || "System"})`);
      addLine("output", `Process: ${telemetry.target_proc || "Desktop"} | Memory: ${telemetry.memory_mb.toFixed(0)}MB RSS`);
      addLine("output", `Latency: ${telemetry.latency_ms.toFixed(1)}ms | Tasks Completed: ${telemetry.tasks_completed}`);
      setIsExecuting(false);
      return;
    }

    if (cmd.toLowerCase() === "health") {
      try {
        const t0 = performance.now();
        const res = await fetch("http://127.0.0.1:8000/health");
        const ms = Math.round(performance.now() - t0);
        if (res.ok) {
          addLine("output", `HTTP 200 OK — Extra MCP daemon alive (${ms}ms)`);
        } else {
          addLine("error", `HTTP ${res.status} — Unhealthy daemon response`);
        }
      } catch (err: any) {
        addLine("error", `Connection failed: ${err.message}`);
      }
      setIsExecuting(false);
      return;
    }

    try {
      const res = await dispatchIntent(cmd);
      if (res && res.result) {
        addLine("output", res.result.summary || JSON.stringify(res.result));
      } else {
        addLine("output", res?.message || "Subtask executed successfully via on-device SOUL.");
      }
    } catch (err: any) {
      addLine("error", `Execution failed: ${err.message}`);
    } finally {
      setIsExecuting(false);
    }
  };

  const copyLog = () => {
    const text = lines.map((l) => `[${l.timestamp}] [${l.type.toUpperCase()}] ${l.text}`).join("\n");
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-4 pb-8">
      {/* Header Banner */}
      <div className="rounded-xl border border-station-border bg-station-well p-4 sm:p-5 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-station-surface border border-station-border text-station-text-primary flex items-center justify-center">
              <TerminalIcon className="w-4 h-4 text-emerald-500" />
            </div>
            <h2 className="text-base sm:text-lg font-medium text-station-text-primary tracking-tight">
              Agent Shell & Telemetry Terminal
            </h2>
            <Badge variant="mono" className="text-[10px] bg-station-surface border-station-border text-station-text-muted">
              Win32 Shell
            </Badge>
          </div>
          <p className="text-xs text-station-text-muted mt-1 max-w-2xl leading-relaxed">
            Direct stdout/stderr telemetry pipe connecting Extra cockpit to the FastMCP daemon.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={copyLog}
            className="gap-1.5 text-xs font-mono bg-station-surface hover:bg-station-surface/80 border-station-border text-station-text-primary"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
            <span>Copy Log</span>
          </Button>

          <Button
            variant="ghost"
            size="sm"
            onClick={() => setLines([])}
            className="gap-1.5 text-xs text-station-text-muted hover:text-station-text-primary hover:bg-station-surface/50"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Clear</span>
          </Button>
        </div>
      </div>

      {/* Terminal Display Container */}
      <div className="rounded-xl border border-station-border bg-station-well shadow-sm overflow-hidden font-mono text-xs flex flex-col h-[520px]">
        {/* Terminal Titlebar */}
        <div className="h-8 px-4 border-b border-station-border bg-station-elevated flex items-center justify-between text-station-text-muted select-none text-[11px]">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block animate-pulse" />
            <span className="text-station-text-primary font-medium">Extra MCP Terminal (127.0.0.1:8000)</span>
          </div>

          <div className="flex items-center gap-3 text-[10px] text-station-text-dim">
            <span>UTF-8</span>
            <span>·</span>
            <span>{lines.length} lines</span>
          </div>
        </div>

        {/* Output Stream */}
        <div ref={scrollRef} className="flex-1 p-4 overflow-y-auto space-y-1.5 bg-station-canvas">
          {lines.map((line) => (
            <div key={line.id} className="flex items-start gap-2 leading-relaxed">
              <span className="text-station-text-dim text-[10px] select-none shrink-0 tabular-nums">
                [{line.timestamp}]
              </span>

              {line.type === "input" && (
                <span className="text-indigo-600 dark:text-cyan-300 font-semibold">{line.text}</span>
              )}
              {line.type === "output" && (
                <span className="text-station-text-primary">{line.text}</span>
              )}
              {line.type === "error" && (
                <span className="text-rose-600 dark:text-rose-400 font-medium">{line.text}</span>
              )}
              {line.type === "system" && (
                <span className="text-emerald-600 dark:text-emerald-400 font-medium">{line.text}</span>
              )}
            </div>
          ))}

          {isExecuting && (
            <div className="flex items-center gap-2 text-station-text-muted py-1">
              <RotateCw className="w-3 h-3 animate-spin text-emerald-500" />
              <span>Compiling intent via SOUL-Critic...</span>
            </div>
          )}
        </div>

        {/* Input Bar */}
        <form onSubmit={handleSubmit} className="border-t border-station-border bg-station-elevated p-2 flex items-center gap-2">
          <span className="text-emerald-500 font-bold ml-2 select-none">$</span>
          <input
            type="text"
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            placeholder="Type a command (e.g. 'status', 'health', 'calculate 245.12/383.29=')..."
            className="flex-1 bg-transparent text-xs text-station-text-primary placeholder:text-station-text-dim outline-none font-mono"
            autoFocus
          />
          <Button
            type="submit"
            variant="primary"
            size="sm"
            disabled={!inputVal.trim() || isExecuting}
            className="h-7 px-3 text-xs font-mono font-medium"
          >
            Send ↵
          </Button>
        </form>
      </div>
    </div>
  );
}