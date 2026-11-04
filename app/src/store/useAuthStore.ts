import { create } from "zustand";
import { persist } from "zustand/middleware";
import {
  authClient,
  type ExtraUser,
} from "../services/authClient";

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
  setLocalOffline: (enabled: boolean) => void;
  dismissOnboarding: () => void;
  reopenOnboarding: () => void;
  openAuthModal: () => void;
  closeAuthModal: () => void;
  updatePasskey: (newPasskey: string) => void;
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

      setLocalOffline: (enabled: boolean) => {
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

      updatePasskey: (newPasskey: string) => {
        const currentUser = get().user;
        const currentToken = get().token;
        if (currentUser && currentToken) {
          const updatedUser: ExtraUser = {
            ...currentUser,
            relay_token: newPasskey,
            token_rotated_at: Math.floor(Date.now() / 1000),
          };
          authClient.saveSessionLocally(currentToken, updatedUser);
          authClient.syncToLocalDaemon(currentToken, updatedUser).catch(() => {});
          set({
            user: updatedUser,
            relayToken: newPasskey,
          });
        }
      },

      refreshProfile: async () => {
        const token = get().token;
        if (!token) return;
        set({ isLoading: true });
        try {
          const user = await authClient.fetchProfile(token);
          if (user) {
            set({
              user,
              relayToken: user.relay_token || null,
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
          const creds = await authClient.loadStoredCredentials();
          if (creds && creds.token && creds.user) {
            set({
              token: creds.token,
              user: creds.user,
              relayToken: creds.user.relay_token || creds.relay_token || null,
              isAuthenticated: true,
              isLocalOfflineMode: false,
            });
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
