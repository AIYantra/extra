import { create } from "zustand";
import { persist } from "zustand/middleware";
import { toast } from "sonner";
import {
  checkForUpdates,
  downloadAsset,
  type UpdateCheckResult,
} from "../services/updateService";
import { openExternal } from "../utils/openExternal";

const CHECK_INTERVAL_MS = 6 * 60 * 60 * 1000;

interface UpdateStoreState {
  autoCheck: boolean;
  autoUpdate: boolean;
  lastCheckedAt: number | null;
  latestTag: string | null;
  updateAvailable: boolean;
  /** Release tag the user was already notified about. */
  notifiedTag: string | null;
  checking: boolean;
  error: string | null;
  lastResult: UpdateCheckResult | null;

  setAutoCheck: (enabled: boolean) => void;
  setAutoUpdate: (enabled: boolean) => void;
  checkNow: (opts?: { silent?: boolean }) => Promise<UpdateCheckResult | null>;
  autoCheckIfDue: () => Promise<void>;
}

export const useUpdateStore = create<UpdateStoreState>()(
  persist(
    (set, get) => ({
      autoCheck: true,
      autoUpdate: false,
      lastCheckedAt: null,
      latestTag: null,
      updateAvailable: false,
      notifiedTag: null,
      checking: false,
      error: null,
      lastResult: null,

      setAutoCheck: (enabled: boolean) => {
        set({ autoCheck: enabled });
      },

      setAutoUpdate: (enabled: boolean) => {
        set({ autoUpdate: enabled });
      },

      checkNow: async (opts) => {
        const silent = opts?.silent ?? false;
        if (get().checking) return get().lastResult;
        set({ checking: true, error: null });
        try {
          const result = await checkForUpdates();
          const alreadyNotified = get().notifiedTag === result.latestTag;
          set({
            checking: false,
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
            if (get().autoUpdate && result.installable && result.downloadUrl && result.assetName) {
              downloadAsset(result.downloadUrl, result.assetName);
              toast.success(`Update ${result.latestTag} downloading`, {
                description: `${result.assetName} — run it when the download finishes.`,
              });
            } else {
              toast.success(`Update available: ${result.latestTag}`, {
                description: `Installed ${result.current} — see About › Updates.`,
              });
            }
          } else if (!silent && !result.available) {
            if (result.offline) {
              toast.info(`Extra ${result.latestTag} (Installed)`, {
                description: "Cannot reach update server. You are running the verified local release.",
              });
            } else {
              toast.success("You're up to date", {
                description: `Installed ${result.current} is the latest release.`,
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

export function viewRelease(url: string): void {
  void openExternal(url);
}
