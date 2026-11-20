import { create } from "zustand";
import { persist } from "zustand/middleware";
import { toast } from "sonner";
import {
  checkForUpdates,
  fetchInstalledVersion,
  performAppUpdate,
  fetchUpdateProgress,
  isNewerVersion,
  type UpdateCheckResult,
} from "../services/updateService";
import { getAppVersion, getAppVersionLabel, setAppVersion } from "../utils/appMeta";
import { soundEngine } from "../utils/sound";

const CHECK_INTERVAL_MS = 6 * 60 * 60 * 1000;

interface UpdateStoreState {
  installedVersion: string;
  installedVersionLabel: string;
  autoCheck: boolean;
  autoUpdate: boolean;
  lastCheckedAt: number | null;
  latestTag: string | null;
  updateAvailable: boolean;
  /** Release tag the user was already notified about. */
  notifiedTag: string | null;
  checking: boolean;
  updating: boolean;
  progressPercent: number;
  statusMessage: string;
  updateState: "idle" | "checking" | "downloading" | "installing" | "restarting" | "completed" | "failed";
  error: string | null;
  lastResult: UpdateCheckResult | null;
  reloadCountdown: number | null;

  setAutoCheck: (enabled: boolean) => void;
  setAutoUpdate: (enabled: boolean) => void;
  initUpdateChecker: () => Promise<void>;
  syncInstalledVersion: () => Promise<string>;
  checkNow: (opts?: { silent?: boolean; force?: boolean }) => Promise<UpdateCheckResult | null>;
  performUpdateNow: () => Promise<boolean>;
  triggerReloadNow: () => void;
  autoCheckIfDue: () => Promise<void>;
}

export const useUpdateStore = create<UpdateStoreState>()(
  persist(
    (set, get) => ({
      installedVersion: getAppVersion(),
      installedVersionLabel: getAppVersionLabel(),
      autoCheck: true,
      autoUpdate: false,
      lastCheckedAt: null,
      latestTag: null,
      updateAvailable: false,
      notifiedTag: null,
      checking: false,
      updating: false,
      progressPercent: 0,
      statusMessage: "Up to date",
      updateState: "idle",
      error: null,
      lastResult: null,
      reloadCountdown: null,

      triggerReloadNow: () => {
        window.location.href = window.location.pathname + "?_t=" + Date.now();
      },

      setAutoCheck: (enabled: boolean) => {
        set({ autoCheck: enabled });
      },

      setAutoUpdate: (enabled: boolean) => {
        set({ autoUpdate: enabled });
      },

      syncInstalledVersion: async () => {
        try {
          const ver = await fetchInstalledVersion();
          if (ver) {
            setAppVersion(ver);
            const latest = get().latestTag?.replace(/^[vV]/, "");
            const hasUpdate = Boolean(latest && isNewerVersion(latest, ver));
            set({
              installedVersion: ver,
              installedVersionLabel: `v${ver}`,
              updateAvailable: hasUpdate,
            });
            return ver;
          }
        } catch {
          // ignore
        }
        return get().installedVersion;
      },

      initUpdateChecker: async () => {
        try {
          await get().syncInstalledVersion();
          // Always perform a silent check on cockpit initialization
          await get().checkNow({ silent: true, force: true });
        } catch {
          // fallback gracefully
        }
      },

      checkNow: async (opts) => {
        const silent = opts?.silent ?? false;
        if (get().checking) return get().lastResult;
        set({ checking: true, error: null });
        try {
          // 1. Sync live local version from backend first
          const activeVer = await get().syncInstalledVersion();
          const result = await checkForUpdates(activeVer);
          const alreadyNotified = get().notifiedTag === result.latestTag;

          if (result.current) {
            setAppVersion(result.current);
          }

          // Strict ground truth: only available if latest is genuinely newer than current installed version
          const isAvailable = Boolean(result.available && isNewerVersion(result.latest, result.current));

          set({
            checking: false,
            installedVersion: result.current,
            installedVersionLabel: `v${result.current}`,
            lastCheckedAt: Date.now(),
            latestTag: result.latestTag,
            updateAvailable: isAvailable,
            lastResult: result,
            notifiedTag:
              isAvailable && !alreadyNotified
                ? result.latestTag
                : get().notifiedTag,
          });

          if (isAvailable && !alreadyNotified) {
            if (get().autoUpdate) {
              await get().performUpdateNow();
            } else {
              toast.success(`Update available: ${result.latestTag}`, {
                description: `Installed v${result.current} — click 'Update Now' in Settings & Health.`,
              });
            }
          } else if (!silent && !isAvailable) {
            if (result.offline) {
              toast.info(`Extra v${result.current} (Installed)`, {
                description: "Cannot reach update server. You are running the verified local release.",
              });
            } else {
              toast.success("You're up to date", {
                description: `Installed v${result.current} is the latest verified release.`,
              });
            }
          }
          return result;
        } catch (err: any) {
          const message = err?.message || "Couldn't reach update server.";
          set({ checking: false, error: message });
          if (!silent) {
            toast.info("Update check deferred", { description: message });
          }
          return null;
        }
      },

      performUpdateNow: async () => {
        if (get().updating) return false;
        const targetTag = get().latestTag?.replace(/^[vV]/, "") || "";
        set({
          updating: true,
          error: null,
          progressPercent: 5,
          updateState: "checking",
          statusMessage: "Contacting update worker...",
        });

        soundEngine.playTick();
        toast.info("Starting Extra update...", {
          description: "Applying verified updates. Extra will refresh automatically once updated.",
        });

        try {
          const res = await performAppUpdate(targetTag);
          if (res.success) {
            // Poll for background worker progress
            let pollCount = 0;
            const poller = setInterval(async () => {
              pollCount++;
              const progress = await fetchUpdateProgress();
              if (progress) {
                set({
                  progressPercent: progress.progress_percent,
                  statusMessage: progress.status_text,
                  updateState: progress.state,
                });

                if (progress.state === "completed") {
                  clearInterval(poller);
                  const freshVer = await fetchInstalledVersion();
                  const effectiveVer = (freshVer && isNewerVersion(freshVer, get().installedVersion))
                    ? freshVer
                    : (targetTag || freshVer || get().installedVersion);

                  setAppVersion(effectiveVer);
                  set({
                    updating: false,
                    installedVersion: effectiveVer,
                    installedVersionLabel: `v${effectiveVer}`,
                    updateAvailable: false,
                    updateState: "completed",
                    progressPercent: 100,
                    statusMessage: `Extra v${effectiveVer} is installed and active!`,
                    reloadCountdown: 3,
                  });
                  soundEngine.playSuccessChime();
                  toast.success(`Updated to Extra v${effectiveVer}!`, {
                    description: "All engine modules, daemon services, and security fixes are verified.",
                  });

                  let countdown = 3;
                  const timer = setInterval(() => {
                    countdown--;
                    if (countdown <= 0) {
                      clearInterval(timer);
                      window.location.href = window.location.pathname + "?_t=" + Date.now();
                    } else {
                      set({ reloadCountdown: countdown });
                    }
                  }, 1000);
                  return;
                }

                if (progress.state === "failed") {
                  clearInterval(poller);
                  set({
                    updating: false,
                    updateState: "failed",
                    error: progress.error || "Update worker reported an error",
                  });
                  toast.error("Update failed", {
                    description: progress.error || "Review local logs in ~/.extra/logs",
                  });
                  return;
                }
              }

              // Fallback version polling in case progress endpoint is transient
              const newVer = await fetchInstalledVersion();
              if (newVer && isNewerVersion(newVer, get().installedVersion)) {
                clearInterval(poller);
                setAppVersion(newVer);
                set({
                  updating: false,
                  installedVersion: newVer,
                  installedVersionLabel: `v${newVer}`,
                  updateAvailable: false,
                  updateState: "completed",
                  progressPercent: 100,
                  statusMessage: `Extra v${newVer} is installed and active!`,
                  reloadCountdown: 2,
                });
                soundEngine.playSuccessChime();
                toast.success(`Updated to Extra v${newVer}!`);
                setTimeout(() => {
                  window.location.href = window.location.pathname + "?_t=" + Date.now();
                }, 1500);
                return;
              }

              if (pollCount > 60) {
                // Timeout after ~60s
                clearInterval(poller);
                set({ updating: false, updateState: "idle" });
              }
            }, 1000);

            return true;
          } else {
            set({
              updating: false,
              updateState: "failed",
              error: res.error || "Failed to trigger update",
            });
            toast.error("Update failed to trigger", {
              description: res.error || "Check terminal permissions or run 'extra update'",
            });
            return false;
          }
        } catch (err: any) {
          set({ updating: false, updateState: "failed", error: err.message });
          toast.error("Update error", { description: err.message });
          return false;
        }
      },

      autoCheckIfDue: async () => {
        if (!get().autoCheck) return;
        const last = get().lastCheckedAt;
        if (last && Date.now() - last < CHECK_INTERVAL_MS) return;
        await get().checkNow({ silent: true });
      },
    }),
    {
      name: "extra_update_prefs",
      partialize: (state) => ({
        autoCheck: state.autoCheck,
        autoUpdate: state.autoUpdate,
        lastCheckedAt: state.lastCheckedAt,
        notifiedTag: state.notifiedTag,
      }),
    },
  ),
);
