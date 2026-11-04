import {
  Monitor,
  Activity,
  ShieldCheck,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { useEngineStore } from "../../store/useEngineStore";
import { StationPageHeader } from "./StationPageHeader";

export function DualPlaneView() {
  const telemetry = useEngineStore((state) => state.telemetry);

  return (
    <div className="space-y-4 sm:space-y-5 pb-8">
      {/* Unified Agency Header */}
      <StationPageHeader
        icon={Monitor}
        iconColor="text-emerald-500"
        title="Dual-Plane Execution Architecture"
        badge="P1 Physical + P2 Deterministic"
        description="Extra bifurcates computer-use into two complementary execution planes: visible hardware actuation on the glass (P1) and deterministic sub-millisecond code bridges (P2) to completely eliminate exploratory GUI loops."
        actions={
          <Badge variant="outline" className="gap-1.5 font-mono text-[11px] text-station-text-muted border-station-border">
            <Activity className="size-3.5 text-emerald-500" />
            <span>{telemetry.actions_dispatched ? `${telemetry.actions_dispatched.toLocaleString()} Dispatched Actions` : "Dual-Plane Active"}</span>
          </Badge>
        }
      />

      {/* Plane Comparison Deck */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Plane 1 Card */}
        <div className="rounded-xl border border-station-border specular-card bg-station-well p-5 space-y-4 shadow-xs">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="size-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-600 dark:text-emerald-400 font-bold text-xs font-mono">
                P1
              </div>
              <div>
                <h3 className="text-sm font-medium text-station-text-primary">Plane 1: Physical OS Glass Actuator</h3>
                <p className="text-[11px] font-mono text-station-text-muted">Low-level Win32 / Cocoa / X11 primitives</p>
              </div>
            </div>
            <Badge variant="success" dot className="text-[10px]">Live</Badge>
          </div>

          <p className="text-xs text-station-text-muted leading-relaxed">
            Interacts visibly with native application windows like a human operator. Dispatches smooth Bezier curves,
            hardware keystrokes via <code className="font-mono text-[11px] bg-station-surface border border-station-border text-station-text-primary px-1 py-0.5 rounded">VK_PACKET</code>, and validates screen settle in sub-15ms.
          </p>

          <div className="space-y-2 pt-2 border-t border-station-border font-mono text-xs">
            <div className="flex items-center justify-between py-1 border-b border-station-border/50">
              <span className="text-station-text-muted">Actuation Latency</span>
              <span className="text-emerald-600 dark:text-emerald-400 font-medium tabular-nums">1.2ms (Zero IPC Overhead)</span>
            </div>
            <div className="flex items-center justify-between py-1 border-b border-station-border/50">
              <span className="text-station-text-muted">Visual Settle Verification</span>
              <span className="text-station-text-primary font-medium">SOUL-Gateman Tier 1 (&lt;15ms)</span>
            </div>
            <div className="flex items-center justify-between py-1 border-b border-station-border/50">
              <span className="text-station-text-muted">Accessibility Invariant</span>
              <span className="text-station-text-primary font-medium">AT-SPI2 / UIAutomation Native</span>
            </div>
            <div className="flex items-center justify-between py-1">
              <span className="text-station-text-muted">Primary Primitives</span>
              <span className="text-station-text-primary text-[11px]">extra_click, extra_type, extra_stroke</span>
            </div>
          </div>
        </div>

        {/* Plane 2 Card */}
        <div className="rounded-xl border border-station-border specular-card bg-station-well p-5 space-y-4 shadow-xs">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="size-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-600 dark:text-indigo-400 font-bold text-xs font-mono">
                P2
              </div>
              <div>
                <h3 className="text-sm font-medium text-station-text-primary">Plane 2: Deterministic Code Bridge</h3>
                <p className="text-[11px] font-mono text-station-text-muted">Direct in-process API execution</p>
              </div>
            </div>
            <Badge variant="accent" dot className="text-[10px]">Deterministic</Badge>
          </div>

          <p className="text-xs text-station-text-muted leading-relaxed">
            Eliminates multi-turn GUI guesswork by executing deterministic scripts directly into runtime engines:
            Python bridges, Blender BPY headless runners, and local batch filesystem primitives.
          </p>

          <div className="space-y-2 pt-2 border-t border-station-border font-mono text-xs">
            <div className="flex items-center justify-between py-1 border-b border-station-border/50">
              <span className="text-station-text-muted">Bridge Execution Time</span>
              <span className="text-indigo-600 dark:text-indigo-400 font-medium tabular-nums">Sub-50ms Micro-Routines</span>
            </div>
            <div className="flex items-center justify-between py-1 border-b border-station-border/50">
              <span className="text-station-text-muted">Filesystem Compliance</span>
              <span className="text-station-text-primary font-medium">100% CFA Defender Compliant</span>
            </div>
            <div className="flex items-center justify-between py-1 border-b border-station-border/50">
              <span className="text-station-text-muted">Lineage Proof</span>
              <span className="text-emerald-600 dark:text-emerald-400 font-medium">SHA-256 Checksum Verified</span>
            </div>
            <div className="flex items-center justify-between py-1">
              <span className="text-station-text-muted">Primary Primitives</span>
              <span className="text-station-text-primary text-[11px]">extra_execute_bridge, extra_fs_batch</span>
            </div>
          </div>
        </div>
      </div>

      {/* Dual-Plane Policy Notice */}
      <div className="p-4 rounded-xl border border-station-border specular-card bg-station-well flex items-start gap-3 shadow-xs">
        <ShieldCheck className="size-5 text-emerald-500 shrink-0 mt-0.5" />
        <div className="space-y-1 text-xs">
          <h4 className="font-medium text-station-text-primary">The Live Desktop Pilot Invariant</h4>
          <p className="text-station-text-muted leading-relaxed">
            Computer use occurs live on the physical Windows desktop as a visible pilot. Extra strictly bans background
            headless scripting bots that hide actions from the user. When creative artwork, notes, or calculations are requested,
            windows launch visibly in the foreground and remain open.
          </p>
        </div>
      </div>
    </div>
  );
}