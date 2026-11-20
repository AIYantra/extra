import { create } from "zustand";
import { persist } from "zustand/middleware";
import { toast } from "sonner";
import {
  checkForUpdates,
  fetchInstalledVersion,
  performAppUpdate,
  fetchUpdateProgress,
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

  setAutoCheck: (enabled: boolean) => void;
  setAutoUpdate: (enabled: boolean) => void;
  syncInstalledVersion: () => Promise<string>;
  checkNow: (opts?: { silent?: boolean }) => Promise<UpdateCheckResult | null>;
  performUpdateNow: () => Promise<boolean>;
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
            set({
              installedVersion: ver,
              installedVersionLabel: `v${ver}`,
            });
            return ver;
          }
        } catch {
          // ignore
        }
        return get().installedVersion;
      },

      checkNow: async (opts) => {
        const silent = opts?.silent ?? false;
        if (get().checking) return get().lastResult;
        set({ checking: true, error: null });
        try {
          // Sync live local version first
          const activeVer = await get().syncInstalledVersion();
          const result = await checkForUpdates(activeVer);
          const alreadyNotified = get().notifiedTag === result.latestTag;

          if (result.current) {
            setAppVersion(result.current);
          }

          set({
            checking: false,
            installedVersion: result.current,
            installedVersionLabel: `v${result.current}`,
            lastCheckedAt: Date.now(),
            latestTag: result.latestTag,
            updateAvailable: result.available,
            lastResult: result,
            notifiedTag:
              result.available && !alreadyNotified
                ? result.latestTag
                : get().notifiedTag,
          });

          if (result.available && !alreadyNotified) {
            if (get().autoUpdate) {
              await get().performUpdateNow();
            } else {
              toast.success(`Update available: ${result.latestTag}`, {
                description: `Installed v${result.current} — click 'Update Now' in About › Updates.`,
              });
            }
          } else if (!silent && !result.available) {
            if (result.offline) {
              toast.info(`Extra v${result.current} (Installed)`, {
                description: "Cannot reach update server. You are running the verified local release.",
              });
            } else {
              toast.success("You're up to date", {
                description: `Installed v${result.current} is the latest release.`,
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
                  const newVer = await fetchInstalledVersion();
                  set({
                    updating: false,
                    installedVersion: newVer || targetTag || get().installedVersion,
                    installedVersionLabel: `v${newVer || targetTag || get().installedVersion}`,
                    updateAvailable: false,
                    updateState: "completed",
                    progressPercent: 100,
                  });
                  soundEngine.playSuccessChime();
                  toast.success(`Updated to Extra v${newVer || targetTag}!`, {
                    description: "All engine modules and security fixes are active.",
                  });
                  setTimeout(() => window.location.reload(), 1800);
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
              if (newVer && newVer !== get().installedVersion) {
                clearInterval(poller);
                set({
                  updating: false,
                  installedVersion: newVer,
                  installedVersionLabel: `v${newVer}`,
                  updateAvailable: false,
                  updateState: "completed",
                  progressPercent: 100,
                });
                soundEngine.playSuccessChime();
                toast.success(`Updated to Extra v${newVer}!`);
                setTimeout(() => window.location.reload(), 1500);
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
        latestTag: state.latestTag,
        updateAvailable: state.updateAvailable,
        notifiedTag: state.notifiedTag,
      }),
    },
  ),
);
