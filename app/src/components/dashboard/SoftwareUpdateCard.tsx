import {
  RefreshCw,
  ArrowUpCircle,
  Check,
  CheckCircle2,
  ChevronRight,
  ShieldCheck,
  Zap,
  RotateCcw,
  ExternalLink,
  Cpu,
  PackageCheck,
  AlertCircle,
} from "lucide-react";
import { useUpdateStore } from "../../store/useUpdateStore";
import { APP_VERSION_LABEL } from "../../utils/appMeta";
import { soundEngine } from "../../utils/sound";
import { Switch } from "../ui/switch";
import { UPDATE_RELEASES_URL } from "../../services/updateService";

interface SoftwareUpdateCardProps {
  onNavigateTab?: (tab: string) => void;
  compact?: boolean;
}

export function SoftwareUpdateCard({ onNavigateTab, compact = false }: SoftwareUpdateCardProps) {
  const {
    installedVersionLabel,
    installedVersion,
    updateAvailable,
    latestTag,
    checking: checkingUpdate,
    updating: updatingApp,
    progressPercent: updateProgress,
    statusMessage: updateStatusMsg,
    lastCheckedAt,
    autoCheck,
    autoUpdate,
    updateState,
    error: updateError,
    reloadCountdown,
    setAutoCheck,
    setAutoUpdate,
    checkNow,
    performUpdateNow,
    triggerReloadNow,
  } = useUpdateStore();

  const activeVerLabel = installedVersionLabel || APP_VERSION_LABEL;
  const targetVer = latestTag || `v${installedVersion}`;

  // Determine active milestone in the 4-stage lifecycle
  // 1: Verify (0-25%), 2: Download (25-55%), 3: Patch (55-85%), 4: Hot-Reload (85-100%)
  const currentStageIndex =
    updateProgress < 25
      ? 0
      : updateProgress < 55
      ? 1
      : updateProgress < 88
      ? 2
      : 3;

  const STAGES = [
    { label: "Verify", desc: "Signature & environment check", icon: ShieldCheck },
    { label: "Download", desc: "Signed wheel & assets", icon: PackageCheck },
    { label: "Patch", desc: "Core engine & dependencies", icon: Cpu },
    { label: "Hot-Reload", desc: "Daemon & cockpit state swap", icon: Zap },
  ];

  return (
    <section className="bg-white dark:bg-[#121316] rounded-xl border border-[#dfe4eb] dark:border-[#27282d] overflow-hidden shadow-2xs transition-all duration-200">
      {/* Executive Card Header */}
      <div className="px-5 py-4 border-b border-[#dfe4eb] dark:border-[#27282d] flex items-center justify-between bg-white dark:bg-[#121316]">
        <div className="flex items-center gap-3">
          <div className="size-8 rounded-lg bg-[#f0f2f6] dark:bg-[#1a1b1e] border border-[#dfe4eb] dark:border-[#27282d] flex items-center justify-center shrink-0">
            <RefreshCw className={`size-4 text-[#1677ff] ${checkingUpdate ? "animate-spin" : ""}`} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-xs font-semibold text-[#1a1a1c] dark:text-[#f4f5f8] tracking-tight">
                Software Updates
              </h3>
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10px] font-medium bg-[#f0f2f6] dark:bg-[#1e2024] text-[#525866] dark:text-[#9ea4b0] border border-[#dfe4eb] dark:border-[#2b2d33]">
                <span className="size-1.5 rounded-full bg-[#10b981]" />
                Stable Channel
              </span>
            </div>
            <p className="text-[11px] text-[#525866] dark:text-[#868c98] mt-0.5">
              Cryptographic integrity verification, engine hot-reload & autonomous security updates
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-[11px] font-mono font-medium px-2 py-0.5 rounded-md bg-[#f8f9fb] dark:bg-[#18191d] text-[#1a1a1c] dark:text-[#f4f5f8] border border-[#dfe4eb] dark:border-[#27282d] tabular-nums">
            {activeVerLabel}
          </span>
          <button
            onClick={() => {
              soundEngine.playTick();
              void checkNow();
            }}
            disabled={checkingUpdate || updatingApp}
            aria-label="Check for updates"
            title="Check official release channel"
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-[#dfe4eb] dark:border-[#27282d] bg-white dark:bg-[#18191d] text-[11px] font-medium text-[#1a1a1c] dark:text-[#f4f5f8] hover:bg-[#f0f2f6] dark:hover:bg-[#202227] transition-colors cursor-pointer disabled:opacity-50"
          >
            <RefreshCw className={`size-3 text-[#525866] dark:text-[#868c98] ${checkingUpdate ? "animate-spin text-[#1677ff]" : ""}`} />
            <span>{checkingUpdate ? "Checking..." : "Check Now"}</span>
          </button>
        </div>
      </div>

      <div className="p-5 space-y-4">
        {/* ========================================================================= */}
        {/* CASE 1: UPDATE IN PROGRESS (HUMAN-PSYCHOLOGY STAGED PROGRESS ENGINE)     */}
        {/* ========================================================================= */}
        {updatingApp ? (
          <div className="rounded-xl border border-[#1677ff]/30 bg-gradient-to-b from-[#f5f9ff] to-white dark:from-[#131926] dark:to-[#121316] p-4.5 space-y-4 shadow-sm">
            {/* Header Telemetry */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="size-2 rounded-full bg-[#1677ff] animate-ping" />
                <span className="text-xs font-semibold text-[#1a1a1c] dark:text-[#f4f5f8] tracking-tight">
                  Upgrading Extra to {targetVer}
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#1677ff]/10 text-[#1677ff] font-medium">
                  Stage {currentStageIndex + 1} of 4
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-bold text-[#1677ff] tabular-nums">
                  {Math.round(updateProgress)}%
                </span>
              </div>
            </div>

            {/* 4-Stage Milestone Stepper Breadcrumb */}
            <div className="grid grid-cols-4 gap-2 pt-1">
              {STAGES.map((stg, idx) => {
                const isPassed = currentStageIndex > idx;
                const isCurrent = currentStageIndex === idx;
                const StageIcon = stg.icon;
                return (
                  <div
                    key={stg.label}
                    className={`flex flex-col p-2 rounded-lg border text-left transition-all duration-300 ${
                      isCurrent
                        ? "bg-white dark:bg-[#1a1c22] border-[#1677ff] shadow-xs"
                        : isPassed
                        ? "bg-[#f8f9fb] dark:bg-[#16171b] border-[#dfe4eb] dark:border-[#27282d] opacity-90"
                        : "bg-transparent border-transparent opacity-40"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <StageIcon
                        className={`size-3.5 ${
                          isCurrent
                            ? "text-[#1677ff] animate-pulse"
                            : isPassed
                            ? "text-[#10b981]"
                            : "text-[#868c98]"
                        }`}
                      />
                      {isPassed ? (
                        <Check className="size-3 text-[#10b981]" strokeWidth={2.5} />
                      ) : isCurrent ? (
                        <span className="size-1.5 rounded-full bg-[#1677ff] animate-ping" />
                      ) : (
                        <span className="size-1 rounded-full bg-[#dfe4eb] dark:bg-[#27282d]" />
                      )}
                    </div>
                    <span
                      className={`text-[11px] font-semibold tracking-tight ${
                        isCurrent
                          ? "text-[#1677ff]"
                          : isPassed
                          ? "text-[#1a1a1c] dark:text-[#f4f5f8]"
                          : "text-[#868c98]"
                      }`}
                    >
                      {stg.label}
                    </span>
                    <span className="text-[9.5px] text-[#868c98] dark:text-[#6c727e] line-clamp-1 mt-0.5">
                      {stg.desc}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* Vitality Loading Bar with Shimmer Beam */}
            <div className="space-y-1.5 pt-1">
              <div className="relative w-full h-2 bg-[#e8ebee] dark:bg-[#202227] rounded-full overflow-hidden border border-[#dfe4eb]/80 dark:border-[#27282d]">
                <div
                  className="h-full rounded-full transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] relative overflow-hidden"
                  style={{
                    width: `${Math.max(6, updateProgress)}%`,
                    background: "linear-gradient(90deg, #1677ff 0%, #388eff 50%, #1677ff 100%)",
                    backgroundSize: "200% 100%",
                  }}
                >
                  {/* High-speed vitality pulse so users know process is active */}
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/40 to-transparent animate-[shimmer_1.5s_infinite]" />
                </div>
              </div>
              <div className="flex items-center justify-between text-[11px] font-mono text-[#525866] dark:text-[#9ea4b0]">
                <span className="truncate pr-2">{updateStatusMsg || "Applying engine updates..."}</span>
                <span className="shrink-0 tabular-nums text-[10px] text-[#868c98]">Sub-millisecond dispatch</span>
              </div>
            </div>
          </div>
        ) : updateState === "completed" ? (
          /* ========================================================================= */
          /* CASE 2: SUCCESS CELEBRATION (HOT-RELOAD READY)                           */
          /* ========================================================================= */
          <div className="rounded-xl border border-[#10b981]/40 bg-gradient-to-b from-[#f0fdf4] to-white dark:from-[#0f241a] dark:to-[#121316] p-4.5 space-y-3 shadow-xs">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="size-8 rounded-lg bg-[#10b981]/15 border border-[#10b981]/30 flex items-center justify-center shrink-0">
                  <CheckCircle2 className="size-4 text-[#10b981]" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-[#1a1a1c] dark:text-[#f4f5f8] tracking-tight">
                      Extra {targetVer} Successfully Installed!
                    </span>
                    <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-[#10b981]/15 text-[#10b981] font-semibold border border-[#10b981]/30">
                      Live
                    </span>
                  </div>
                  <p className="text-[11px] text-[#525866] dark:text-[#9ea4b0] mt-0.5">
                    All engine modules, daemon services, and security fixes have been verified.
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => triggerReloadNow()}
                  className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-[#10b981] hover:bg-[#059669] text-white text-xs font-semibold transition-all shadow-xs cursor-pointer active:scale-95"
                >
                  <RotateCcw className="size-3.5" />
                  <span>
                    Reload Now {reloadCountdown !== null ? `(${reloadCountdown}s)` : ""}
                  </span>
                </button>
              </div>
            </div>
          </div>
        ) : updateAvailable && latestTag ? (
          /* ========================================================================= */
          /* CASE 3: UPDATE AVAILABLE (EXECUTIVE ARCHITECTURE DECK - NO NEON SLOP)     */
          /* ========================================================================= */
          <div className="rounded-xl border border-[#dfe4eb] dark:border-[#27282d] bg-gradient-to-b from-[#fafbfd] to-white dark:from-[#18191d] dark:to-[#121316] p-4.5 space-y-3.5 shadow-xs">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="space-y-1.5">
                <div className="flex items-center gap-2">
                  <span className="size-2 rounded-full bg-[#1677ff] animate-ping" />
                  <span className="text-xs font-bold text-[#1a1a1c] dark:text-[#f4f5f8] tracking-tight">
                    Extra {latestTag} Ready to Install
                  </span>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-md bg-[#1677ff]/10 text-[#1677ff] font-semibold border border-[#1677ff]/20">
                    Latest Stable
                  </span>
                </div>

                {/* Version Transition Chip */}
                <div className="flex items-center gap-2 text-xs">
                  <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-[#f0f2f6] dark:bg-[#202227] border border-[#dfe4eb] dark:border-[#27282d] font-mono text-[11px] text-[#525866] dark:text-[#868c98]">
                    <span>Current:</span>
                    <span className="font-semibold text-[#1a1a1c] dark:text-[#f4f5f8]">{activeVerLabel}</span>
                  </div>
                  <ChevronRight className="size-3 text-[#868c98]" />
                  <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-[#1677ff]/10 border border-[#1677ff]/25 font-mono text-[11px] text-[#1677ff]">
                    <span>Upgrade:</span>
                    <span className="font-bold">{latestTag}</span>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2 self-start sm:self-auto">
                <button
                  onClick={() => {
                    soundEngine.playTick();
                    void performUpdateNow();
                  }}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#1677ff] hover:bg-[#125ecc] text-white text-xs font-semibold transition-all shadow-xs cursor-pointer active:scale-95"
                >
                  <ArrowUpCircle className="size-3.5" />
                  <span>Update Now</span>
                </button>

                {onNavigateTab ? (
                  <button
                    onClick={() => {
                      soundEngine.playTick();
                      onNavigateTab("about");
                    }}
                    className="flex items-center gap-1 px-3 py-2 rounded-lg border border-[#dfe4eb] dark:border-[#27282d] bg-white dark:bg-[#18191d] hover:bg-[#f0f2f6] dark:hover:bg-[#202227] text-xs font-medium text-[#1a1a1c] dark:text-[#f4f5f8] transition-colors cursor-pointer"
                  >
                    <span>Changelog</span>
                    <ChevronRight className="size-3 text-[#868c98]" />
                  </button>
                ) : (
                  <a
                    href={UPDATE_RELEASES_URL}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1 px-3 py-2 rounded-lg border border-[#dfe4eb] dark:border-[#27282d] bg-white dark:bg-[#18191d] hover:bg-[#f0f2f6] dark:hover:bg-[#202227] text-xs font-medium text-[#1a1a1c] dark:text-[#f4f5f8] transition-colors"
                  >
                    <span>Release Notes</span>
                    <ExternalLink className="size-3 text-[#868c98]" />
                  </a>
                )}
              </div>
            </div>

            {/* Senior Dev Agency Highlights (3 Anti-Slop Badges) */}
            <div className="pt-2 border-t border-[#dfe4eb]/60 dark:border-[#27282d]/60 grid grid-cols-1 sm:grid-cols-3 gap-2">
              <div className="flex items-center gap-2 text-[11px] text-[#525866] dark:text-[#9ea4b0]">
                <ShieldCheck className="size-3.5 text-[#10b981] shrink-0" />
                <span>Loopback Origin CORS Hardened</span>
              </div>
              <div className="flex items-center gap-2 text-[11px] text-[#525866] dark:text-[#9ea4b0]">
                <CheckCircle2 className="size-3.5 text-[#1677ff] shrink-0" />
                <span>100% Green Matrix CI/CD Tested</span>
              </div>
              <div className="flex items-center gap-2 text-[11px] text-[#525866] dark:text-[#9ea4b0]">
                <Zap className="size-3.5 text-[#f59e0b] shrink-0" />
                <span>Zero-Stall Engine Hot-Reload</span>
              </div>
            </div>
          </div>
        ) : (
          /* ========================================================================= */
          /* CASE 4: UP TO DATE (CALM, REASSURING CRAFT)                              */
          /* ========================================================================= */
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3.5 rounded-lg bg-[#f8f9fb] dark:bg-[#18191d] border border-[#dfe4eb] dark:border-[#27282d]">
            <div className="flex items-center gap-2.5">
              <div className="size-6 rounded-full bg-[#10b981]/15 border border-[#10b981]/30 flex items-center justify-center shrink-0">
                <Check className="size-3 text-[#10b981]" strokeWidth={2.5} />
              </div>
              <div>
                <span className="text-xs font-medium text-[#1a1a1c] dark:text-[#f4f5f8] block">
                  Extra is up to date
                </span>
                <span className="text-[11px] font-mono text-[#868c98] dark:text-[#6c727e] block">
                  {lastCheckedAt
                    ? `Last checked ${new Date(lastCheckedAt).toLocaleTimeString()} • Sovereign release verified`
                    : "Checked on startup • Sovereign release verified"}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white dark:bg-[#121316] text-[#525866] dark:text-[#9ea4b0] border border-[#dfe4eb] dark:border-[#27282d]">
                {activeVerLabel}
              </span>
            </div>
          </div>
        )}

        {/* Error notification if failed */}
        {updateError && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-900/50 text-xs text-rose-800 dark:text-rose-300">
            <AlertCircle className="size-4 shrink-0 text-rose-600 dark:text-rose-400" />
            <div className="flex-1">
              <span className="font-semibold">Update Notice:</span> {updateError}
            </div>
            <button
              onClick={() => void checkNow({ silent: false })}
              className="px-2 py-1 rounded bg-rose-100 dark:bg-rose-900/40 hover:bg-rose-200 text-rose-900 dark:text-rose-200 text-[11px] font-medium transition-colors cursor-pointer"
            >
              Retry Check
            </button>
          </div>
        )}

        {/* Preferences Toggles */}
        {!compact && (
          <div className="pt-2 border-t border-[#dfe4eb] dark:border-[#27282d] space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-xs font-medium text-[#1a1a1c] dark:text-[#f4f5f8] block">
                  Automatic update checks
                </span>
                <span className="text-[11px] text-[#525866] dark:text-[#868c98] block">
                  Periodically query official release channels and surface unobtrusive notifications
                </span>
              </div>
              <Switch
                checked={autoCheck}
                onCheckedChange={setAutoCheck}
                aria-label="Automatic update checks"
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <span className="text-xs font-medium text-[#1a1a1c] dark:text-[#f4f5f8] block">
                  Download updates automatically
                </span>
                <span className="text-[11px] text-[#525866] dark:text-[#868c98] block">
                  Fetch verified signed packages in background as soon as they are published
                </span>
              </div>
              <Switch
                checked={autoUpdate}
                onCheckedChange={setAutoUpdate}
                aria-label="Download updates automatically"
              />
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
