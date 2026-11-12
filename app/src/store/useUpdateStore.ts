import { create } from "zustand";
import { persist } from "zustand/middleware";
import { toast } from "sonner";
import {
  checkForUpdates,
  fetchInstalledVersion,
  performAppUpdate,
  type UpdateCheckResult,
} from "../services/updateService";
import { getAppVersion, getAppVersionLabel, setAppVersion } from "../utils/appMeta";

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
        set({ updating: true, error: null });
        toast.info("Starting Extra update...", {
          description: "Running background installer. Extra will refresh automatically once updated.",
        });

        try {
          const res = await performAppUpdate();
          if (res.success) {
            toast.success("Update initiated successfully!", {
              description: "Downloading and applying latest signed runtime...",
            });

            // Poll for version upgrade in background
            let pollCount = 0;
            const poller = setInterval(async () => {
              pollCount++;
              const newVer = await fetchInstalledVersion();
              if (newVer && newVer !== get().installedVersion) {
                clearInterval(poller);
                set({
                  updating: false,
                  installedVersion: newVer,
                  installedVersionLabel: `v${newVer}`,
                  updateAvailable: false,
                });
                toast.success(`Updated to Extra v${newVer}!`, {
                  description: "Newest features and SAC security fixes active.",
                });
                setTimeout(() => window.location.reload(), 1500);
              } else if (pollCount > 25) {
                clearInterval(poller);
                set({ updating: false });
              }
            }, 3000);

            return true;
          } else {
            set({ updating: false, error: res.error || "Failed to trigger update" });
            toast.error("Update failed to trigger", {
              description: res.error || "Check terminal permissions or run 'irm https://extra.yantraos.com/install.ps1 | iex'",
            });
            return false;
          }
        } catch (err: any) {
          set({ updating: false, error: err.message });
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
