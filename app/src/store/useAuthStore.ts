import { create } from "zustand";
import { persist } from "zustand/middleware";
import {
  authClient,
  type ExtraUser,
} from "../services/authClient";
import { extraDataService } from "../services/extraDataService";

interface AuthStoreState {
  user: ExtraUser | null;
  token: string | null;
  relayToken: string | null;
  isAuthenticated: boolean;
  isLocalOfflineMode: boolean;
  isOnboardingDismissed: boolean;
  isAuthModalOpen: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  setAuth: (token: string, user: ExtraUser) => void;
  setLocalOffline: (enabled: boolean) => Promise<void>;
  dismissOnboarding: () => void;
  reopenOnboarding: () => void;
  openAuthModal: () => void;
  closeAuthModal: () => void;
  updatePasskey: (newPasskey: string, tokenRotatedAt?: number) => void;
  rotatePasskey: () => Promise<string>;
  refreshProfile: () => Promise<void>;
  logout: () => void;
  setError: (error: string | null) => void;
  initFromSecureStorage: () => Promise<void>;
}

export const useAuthStore = create<AuthStoreState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      relayToken: null,
      isAuthenticated: false,
      isLocalOfflineMode: true,
      isOnboardingDismissed: true,
      isAuthModalOpen: false,
      isLoading: false,
      error: null,

      setAuth: (token: string, user: ExtraUser) => {
        authClient.saveSessionLocally(token, user);
        authClient.syncToLocalDaemon(token, user).catch(() => {});
        authClient.pairDevice(token, "Extra (Windows 11)").catch(() => {});
        set({
          token,
          user,
          relayToken: user.relay_token || null,
          isAuthenticated: true,
          isLocalOfflineMode: false,
          isOnboardingDismissed: true,
          // Leave the modal open so the caller lands on the post-login
          // success screen; it closes via "Go to Mission Control".
          error: null,
        });
      },

      setLocalOffline: async (enabled: boolean) => {
        const currentToken = get().token || authClient.getLocalToken() || "";
        const currentUser = get().user || authClient.getLocalCachedUser();
        const currentRelayToken = get().relayToken || currentUser?.relay_token || "";

        if (enabled) {
          // Sever outbound WebSocket tunnel immediately
          await extraDataService.stopRelay().catch(() => {});
          if (currentUser) {
            authClient.syncToLocalDaemon(currentToken, currentUser, true).catch(() => {});
          }
        } else {
          // Reconnect outbound WebSocket tunnel
          await extraDataService.startRelay(currentRelayToken || undefined).catch(() => {});
          if (currentUser) {
            authClient.syncToLocalDaemon(currentToken, currentUser, false).catch(() => {});
          }
        }

        set({
          isLocalOfflineMode: enabled,
          isOnboardingDismissed: true,
          isAuthModalOpen: false,
        });
      },

      dismissOnboarding: () => {
        set({ isOnboardingDismissed: true, isAuthModalOpen: false });
      },

      openAuthModal: () => {
        set({ isAuthModalOpen: true, isOnboardingDismissed: false });
      },

      closeAuthModal: () => {
        set({ isAuthModalOpen: false });
      },

      reopenOnboarding: () => {
        set({ isAuthModalOpen: true, isOnboardingDismissed: false });
      },

      updatePasskey: (newPasskey: string, tokenRotatedAt?: number) => {
        const currentUser = get().user;
        const currentToken = get().token;
        if (currentUser && currentToken) {
          const updatedUser: ExtraUser = {
            ...currentUser,
            relay_token: newPasskey,
            token_rotated_at: tokenRotatedAt || Math.floor(Date.now() / 1000),
          };
          authClient.saveSessionLocally(currentToken, updatedUser);
          authClient.syncToLocalDaemon(currentToken, updatedUser).catch(() => {});
          extraDataService.startRelay(newPasskey).catch(() => {});
          set({
            user: updatedUser,
            relayToken: newPasskey,
          });
        }
      },

      rotatePasskey: async (): Promise<string> => {
        const currentToken = get().token;
        if (!currentToken) {
          throw new Error("Not authenticated. Please sign in first.");
        }
        set({ isLoading: true, error: null });
        try {
          const res = await authClient.rotateRelayPasskey(currentToken);
          get().updatePasskey(res.relay_token, res.token_rotated_at);
          set({ isLoading: false });
          return res.relay_token;
        } catch (err: any) {
          set({ isLoading: false, error: err.message || "Failed to rotate passkey" });
          throw err;
        }
      },

      refreshProfile: async () => {
        const token = get().token;
        if (!token) return;
        set({ isLoading: true });
        try {
          const user = await authClient.fetchProfile(token);
          if (user) {
            authClient.saveSessionLocally(token, user);
            authClient.syncToLocalDaemon(token, user).catch(() => {});

            const oldRelayToken = get().relayToken;
            const newRelayToken = user.relay_token || null;
            if (newRelayToken && newRelayToken !== oldRelayToken) {
              console.log("[useAuthStore] Detected updated relay passkey from cloud:", newRelayToken.slice(0, 14) + "...");
              extraDataService.startRelay(newRelayToken).catch(() => {});
            }

            set({
              user,
              relayToken: newRelayToken,
              isAuthenticated: true,
              isLoading: false,
            });
          } else {
            // Token expired or invalid
            set({
              user: null,
              token: null,
              relayToken: null,
              isAuthenticated: false,
              isLoading: false,
            });
          }
        } catch (err: any) {
          set({
            error: err.message || "Failed to update profile",
            isLoading: false,
          });
        }
      },

      logout: () => {
        authClient.clearSessionLocally();
        extraDataService.stopRelay().catch(() => {});
        authClient.syncToLocalDaemon("", { id: "", email: "", plan: "community", is_local_mode: true } as any).catch(() => {});
        set({
          user: null,
          token: null,
          relayToken: null,
          isAuthenticated: false,
          isLocalOfflineMode: false,
          isOnboardingDismissed: false,
          error: null,
        });
      },

      setError: (error: string | null) => {
        set({ error });
      },

      initFromSecureStorage: async () => {
        try {
          let creds = await authClient.loadStoredCredentials();
          // Fallback to cached session in localStorage if loopback DPAPI daemon is booting
          if (!creds || !creds.user) {
            const cachedUser = authClient.getLocalCachedUser();
            const cachedToken = authClient.getLocalToken();
            if (cachedUser && cachedToken) {
              creds = {
                token: cachedToken,
                user: cachedUser,
                relay_token: cachedUser.relay_token,
              };
            }
          }
          if (creds && (creds.token || creds.user)) {
            const user = creds.user;
            const rToken = creds.relay_token || user?.relay_token || null;
            set({
              token: creds.token || null,
              user: user || null,
              relayToken: rToken,
              isAuthenticated: true,
              isLocalOfflineMode: false,
            });
            // Automatically refresh profile from cloud in background to reconcile any keys rotated on web!
            get().refreshProfile().catch(() => {});
          }
        } catch (e) {
          console.warn("[useAuthStore] Secure credential hydration error:", e);
        }
      },
    }),
    {
      name: "extra_consumer_auth",
      partialize: (state) => ({
        // Sensitive secrets (token, relayToken, credentials) are stored securely via DPAPI;
        // only UI flags and offline state are persisted in unencrypted web storage.
        isAuthenticated: state.isAuthenticated,
        isLocalOfflineMode: state.isLocalOfflineMode,
        isOnboardingDismissed: state.isOnboardingDismissed,
      }),
    }
  )
);
