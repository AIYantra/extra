import { useState } from "react";
import {
  Globe,
  ShieldCheck,
  Laptop,
  RefreshCw,
  Search,
  ExternalLink,
  Plus,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useEngineStore } from "../../store/useEngineStore";
import { StationPageHeader } from "./StationPageHeader";

export function BrowsersView() {
  const windows = useEngineStore((state) => state.windows);
  const fetchWindows = useEngineStore((state) => state.fetchWindows);
  const dispatchIntent = useEngineStore((state) => state.dispatchIntent);

  const [targetUrl, setTargetUrl] = useState("");
  const [isNavigating, setIsNavigating] = useState(false);
  const [navMsg, setNavMsg] = useState<string | null>(null);

  const browserWindows = windows.filter((w) => w.is_browser);

  const handleNavigate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetUrl.trim() || isNavigating) return;

    setIsNavigating(true);
    const url = targetUrl.startsWith("http") ? targetUrl : `https://${targetUrl}`;

    try {
      const res = await dispatchIntent(`launch browser at ${url}`);
      setNavMsg(res?.message || `Browser launched at ${url}`);
      setTargetUrl("");
      await fetchWindows();
    } catch (err: any) {
      setNavMsg(`Failed to launch browser: ${err?.message || "Daemon offline"}`);
      setTargetUrl("");
    } finally {
      setIsNavigating(false);
      setTimeout(() => setNavMsg(null), 4000);
    }
  };

  return (
    <div className="space-y-4 sm:space-y-5 pb-8">
      {/* Unified Agency Header */}
      <StationPageHeader
        icon={Globe}
        iconColor="text-cyan-500"
        title="Browser Cockpit & Anti-Bot Stealth"
        badge={`${browserWindows.length} Active Windows`}
        description="Real-time telemetry and management of running browser windows, Chromium instances, and isolated profiles with anti-bot stealth."
        actions={
          <Button
            variant="secondary"
            size="sm"
            onClick={() => fetchWindows()}
            className="gap-1.5 text-xs font-mono bg-station-surface hover:bg-station-surface/80 border-station-border text-station-text-primary rounded-md cursor-pointer active:scale-95"
          >
            <RefreshCw className="size-3.5" />
            <span>Scan Windows</span>
          </Button>
        }
      />

      {/* URL Quick-Launch Bar */}
      <form
        onSubmit={handleNavigate}
        className="rounded-xl border border-station-border specular-card bg-station-well p-2.5 sm:p-3 shadow-xs flex items-center gap-2.5 focus-within:ring-2 focus-within:ring-primary/20 focus-within:border-primary transition-all"
      >
        <Search className="size-4 text-station-text-muted shrink-0 ml-1.5" />
        <input
          type="text"
          value={targetUrl}
          onChange={(e) => setTargetUrl(e.target.value)}
          placeholder="Launch URL in isolated profile (e.g. 'docs.google.com' or 'youtube.com')..."
          className="flex-1 bg-transparent text-xs sm:text-sm text-station-text-primary placeholder:text-station-text-dim outline-none font-mono"
        />
        <Button
          type="submit"
          variant="primary"
          size="sm"
          disabled={!targetUrl.trim() || isNavigating}
          className="h-7 px-3 gap-1.5 shrink-0 text-xs font-medium rounded-md focus-visible:ring-2 focus-visible:ring-primary/50 cursor-pointer active:scale-95"
        >
          {isNavigating ? (
            <RefreshCw className="size-3 animate-spin" />
          ) : (
            <Plus className="size-3" />
          )}
          <span>Open Session</span>
        </Button>
      </form>

      {/* Navigation Feedback Toast */}
      {navMsg && (
        <div className="p-3 rounded-lg border border-emerald-500/20 bg-emerald-500/10 text-xs text-emerald-600 dark:text-emerald-300 font-mono flex items-center justify-between gap-3 animate-in fade-in duration-150">
          <span>{navMsg}</span>
          <span className="text-[10px] text-station-text-muted">Session Initialized</span>
        </div>
      )}

      {/* Active Browser Instances Grid */}
      <div className="space-y-3">
        <div className="flex items-center justify-between text-xs text-station-text-muted font-mono px-1">
          <span>Active Desktop Windows ({browserWindows.length})</span>
          <span>Win32 EnumWindows Grounding</span>
        </div>

        {browserWindows.length === 0 ? (
          <div className="p-8 rounded-xl border border-station-border specular-card bg-station-well text-center space-y-2">
            <Globe className="size-8 text-station-text-dim mx-auto" />
            <h4 className="text-sm font-medium text-station-text-primary">No Browser Windows Detected</h4>
            <p className="text-xs text-station-text-muted max-w-sm mx-auto">
              Launch a browser session above or open Edge/Chrome on your desktop to inspect interactive sessions.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
            {browserWindows.map((win) => (
              <div
                key={win.hwnd}
                className="p-4 rounded-xl border border-station-border specular-card bg-station-well hover:border-station-border-active hover:bg-station-elevated/40 transition-all duration-150 flex flex-col justify-between space-y-3 shadow-xs group"
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 min-w-0">
                      <div className="size-7 rounded-md bg-station-surface border border-station-border flex items-center justify-center text-cyan-500 shrink-0">
                        <Laptop className="size-3.5" />
                      </div>
                      <Badge variant="mono" className="text-[9px] bg-station-surface/80 border-station-border text-station-text-muted tabular-nums">
                        PID {win.pid}
                      </Badge>
                    </div>

                    <span className="text-[10px] font-mono text-station-text-dim tabular-nums">
                      HWND: {win.hwnd}
                    </span>
                  </div>

                  <div>
                    <h4 className="text-xs sm:text-[13px] font-medium text-station-text-primary tracking-tight truncate group-hover:text-primary transition-colors" title={win.title}>
                      {win.title}
                    </h4>
                    <p className="text-[11px] font-mono text-station-text-muted mt-0.5 truncate">
                      {win.proc_name}
                    </p>
                  </div>
                </div>

                <div className="pt-2.5 border-t border-station-border flex items-center justify-between text-xs">
                  <span className="inline-flex items-center gap-1 text-[10px] font-mono text-emerald-600 dark:text-emerald-400 font-medium">
                    <ShieldCheck className="size-3" />
                    Stealth Active
                  </span>

                  <button
                    onClick={() => dispatchIntent(`focus window "${win.title}"`)}
                    className="text-[11px] font-mono text-station-text-muted hover:text-station-text-primary px-2 py-0.5 rounded border border-station-border bg-station-surface hover:bg-station-surface/80 transition-colors cursor-pointer inline-flex items-center gap-1 active:scale-95"
                  >
                    <span>Focus</span>
                    <ExternalLink className="size-3" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}