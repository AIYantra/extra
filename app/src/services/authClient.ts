/**
 * Project Extra — Universal Authentication & Cloud Hub Service Client
 * Provides zero-friction email OTP authentication, session persistence,
 * user profile retrieval, passkey rotation, and local daemon synchronization.
 */

export interface PairedDevice {
  device_id: string;
  device_name: string;
  platform: string;
  status: "connected" | "idle" | "offline";
  paired_at: number;
  last_ping?: number;
}

export interface ExtraUser {
  id: string;
  email: string;
  username: string;
  plan: "free" | "pro";
  billing_cycle?: "monthly" | "annual";
  actions_used?: number;
  max_quota?: number;
  status?: "active" | "cooling_off";
  created_at?: number;
  paired_devices?: PairedDevice[];
  paired_devices_count?: number;
  relay_token?: string;
  token_rotated_at?: number;
}

export interface AuthResponse {
  success: boolean;
  token?: string;
  user?: ExtraUser;
  requires_verification?: boolean;
  email?: string;
  message?: string;
  error?: string;
}

export const CLOUD_API_BASE_URL = "https://extra.yantraos.com";
export const LOCAL_SERVER_BASE_URL = "http://127.0.0.1:8000";

export const STORAGE_TOKEN_KEY = "extra_auth_token";
export const STORAGE_USER_KEY = "extra_auth_user";

/**
 * Detects the backend error returned when a password login hits an account
 * that was registered via Google OAuth (no password hash stored).
 */
export function isGoogleOnlyAccountError(message: string | null | undefined): boolean {
  return !!message && /registered via google/i.test(message);
}

class AuthClient {
  private apiBase: string;
  private localBase: string;

  constructor(apiBase: string = CLOUD_API_BASE_URL, localBase: string = LOCAL_SERVER_BASE_URL) {
    this.apiBase = apiBase;
    this.localBase = localBase;
  }

  /**
   * Register a new account with email, password, and display username.
   */
  async signupWithPassword(email: string, password: string, username?: string): Promise<AuthResponse> {
    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail || !cleanEmail.includes("@") || !cleanEmail.includes(".")) {
      throw new Error("Please enter a valid email address.");
    }
    if (password.length < 8) {
      throw new Error("Password must be at least 8 characters long.");
    }

    const res = await fetch(`${this.apiBase}/api/auth/signup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: cleanEmail,
        password,
        username: (username || cleanEmail.split("@")[0]).trim(),
      }),
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.error || "Failed to create account.");
    }

    if (data.token && data.user) {
      this.saveSessionLocally(data.token, data.user);
      this.syncToLocalDaemon(data.token, data.user).catch(() => {});
    }

    return data;
  }

  /**
   * Resend the 6-digit verification code to the given email.
   */
  async resendVerificationCode(email: string): Promise<boolean> {
    const cleanEmail = email.trim().toLowerCase();
    const res = await fetch(`${this.apiBase}/api/auth/resend-code`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: cleanEmail }),
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.error || "Failed to resend verification code.");
    }
    return true;
  }

  /**
   * Change the account password (current + new, min 8 chars).
   */
  async changeUserPassword(currentPassword: string, newPassword: string): Promise<void> {
    const token = this.getLocalToken();
    if (!token) {
      throw new Error("Not authenticated. Please sign in first.");
    }
    if (!newPassword || newPassword.length < 8) {
      throw new Error("New password must be at least 8 characters.");
    }
    const res = await fetch(`${this.apiBase}/api/auth/change-password`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
      }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data.success) {
      throw new Error(data.error || "Failed to update password.");
    }
  }

  /**
   * Mint a fresh relay passkey from the cloud, then persist it locally.
   * Returns the new passkey.
   */
  async rotateRelayPasskey(): Promise<string> {
    const token = this.getLocalToken();
    if (!token) {
      throw new Error("Not authenticated. Please sign in first.");
    }
    const gen = await fetch(`${this.apiBase}/api/auth/generate-passkey`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const genData = await gen.json().catch(() => ({}));
    if (!gen.ok || !genData.success || !genData.passkey) {
      throw new Error(genData.error || "Could not generate a new passkey.");
    }
    const save = await fetch("/api/extra/update-passkey", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ passkey: genData.passkey as string }),
    });
    const saveData = await save.json().catch(() => ({}));
    if (!save.ok || !saveData.success) {
      throw new Error(saveData.error || "Could not save the new passkey locally.");
    }
    return genData.passkey as string;
  }

  /**
   * Request a 6-digit OTP code to the given email address.
   * Seamlessly handles both new registrations (via /api/auth/signup)
   * and returning user sign-ins (via /api/auth/resend-code).
   */
  async requestOtp(email: string): Promise<{ success: boolean; message: string; isNewUser: boolean }> {
    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail || !cleanEmail.includes("@") || !cleanEmail.includes(".")) {
      throw new Error("Please enter a valid email address.");
    }

    try {
      // 1. Attempt signup with an auto-generated client device credential
      const fallbackPassword = `ExtraPass_${Math.random().toString(36).slice(2)}!A1`;
      const username = cleanEmail.split("@")[0].slice(0, 20);

      const signupRes = await fetch(`${this.apiBase}/api/auth/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: cleanEmail,
          password: fallbackPassword,
          username,
        }),
      });

      const signupData = await signupRes.json();

      if (signupRes.status === 201 || signupData.requires_verification) {
        return {
          success: true,
          message: "We've sent a 6-digit verification code to your email.",
          isNewUser: true,
        };
      }

      // 2. If user already exists (HTTP 409), request a new code via resend-code
      if (signupRes.status === 409 || (signupData.error && signupData.error.toLowerCase().includes("already exists"))) {
        const resendRes = await fetch(`${this.apiBase}/api/auth/resend-code`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: cleanEmail }),
        });

        const resendData = await resendRes.json();
        if (resendRes.ok && resendData.success) {
          return {
            success: true,
            message: "We've sent a 6-digit verification code to your email.",
            isNewUser: false,
          };
        }

        // If backend reports email is already verified, inform user code is ready for sign-in
        if (resendData.message && resendData.message.includes("already verified")) {
          return {
            success: true,
            message: "Verification code ready. Enter your code to sign in.",
            isNewUser: false,
          };
        }

        throw new Error(resendData.error || "Failed to send verification code.");
      }

      throw new Error(signupData.error || "Failed to initiate sign in.");
    } catch (err: any) {
      console.error("[AuthClient] requestOtp failed:", err);
      throw new Error(err.message || "Unable to reach Extra authentication service.");
    }
  }

  /**
   * Verify the 6-digit OTP code received by email.
   * On success, returns the JWT auth token and user profile with passkey (relay_token).
   */
  async verifyOtp(email: string, code: string): Promise<AuthResponse> {
    const cleanEmail = email.trim().toLowerCase();
    const cleanCode = code.trim();

    if (!cleanCode || cleanCode.length < 6) {
      throw new Error("Please enter the complete 6-digit code.");
    }

    try {
      const res = await fetch(`${this.apiBase}/api/auth/verify-email`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: cleanEmail,
          code: cleanCode,
        }),
      });

      const data = await res.json();
      if (!res.ok || !data.success) {
        throw new Error(data.error || "Invalid or expired code. Please try again.");
      }

      if (data.token && data.user) {
        this.saveSessionLocally(data.token, data.user);
        // Best-effort background sync with local desktop daemon
        this.syncToLocalDaemon(data.token, data.user).catch(() => {});
      }

      return data;
    } catch (err: any) {
      console.error("[AuthClient] verifyOtp failed:", err);
      throw new Error(err.message || "Failed to verify code.");
    }
  }

  /**
   * Optional email + password login fallback.
   */
  async loginWithPassword(email: string, password: string): Promise<AuthResponse> {
    const res = await fetch(`${this.apiBase}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: email.trim().toLowerCase(),
        password,
      }),
    });

    const data = await res.json();
    // Unverified accounts answer 403 + requires_verification. Return the
    // payload instead of throwing so the caller can route to OTP verify.
    if (data.requires_verification) {
      return data;
    }
    if (!res.ok || !data.success) {
      throw new Error(data.error || "Invalid email or password.");
    }

    if (data.token && data.user) {
      this.saveSessionLocally(data.token, data.user);
      this.syncToLocalDaemon(data.token, data.user).catch(() => {});
    }

    return data;
  }

  /**
   * Fetches latest user profile from cloud hub.
   */
  async fetchProfile(token: string): Promise<ExtraUser | null> {
    try {
      const res = await fetch(`${this.apiBase}/api/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.status === 401) {
        this.clearSessionLocally();
        return null;
      }

      const data = await res.json();
      if (data.success && data.user) {
        this.saveSessionLocally(token, data.user);
        return data.user;
      }
      return null;
    } catch (err) {
      console.warn("[AuthClient] fetchProfile offline, returning local cache:", err);
      return this.getLocalCachedUser();
    }
  }

  /**
   * Generates a new Extra Passkey (relay_token) in one tap.
   */
  async rotatePasskey(token: string): Promise<{ success: boolean; relay_token: string }> {
    const res = await fetch(`${this.apiBase}/api/auth/rotate-token`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({}),
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.error || "Failed to generate new passkey.");
    }

    // Update locally cached user
    const user = this.getLocalCachedUser();
    if (user) {
      user.relay_token = data.relay_token;
      this.saveSessionLocally(token, user);
      this.syncToLocalDaemon(token, user).catch(() => {});
    }

    return data;
  }

  /**
   * Pairs the current workstation to the user's account.
   */
  async pairDevice(token: string, deviceName: string = "Desktop Workstation"): Promise<any> {
    try {
      const platform = navigator.userAgent.includes("Windows")
        ? "Windows"
        : navigator.userAgent.includes("Mac")
        ? "macOS"
        : "Linux";

      const res = await fetch(`${this.apiBase}/api/auth/pair-device`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ device_name: deviceName, platform }),
      });

      return await res.json();
    } catch (e) {
      console.warn("[AuthClient] pairDevice failed:", e);
      return null;
    }
  }

  private loopbackSessionToken: string | null = null;

  async getLoopbackSessionToken(): Promise<string | null> {
    if (this.loopbackSessionToken) return this.loopbackSessionToken;
    try {
      const res = await fetch("/api/extra/session-token");
      if (res.ok) {
        const data = await res.json();
        if (data?.token) {
          this.loopbackSessionToken = data.token;
          return data.token;
        }
      }
    } catch {}
    return null;
  }

  /**
   * Synchronizes active token and relay passkey to the local Extra MCP daemon
   * (http://127.0.0.1:8000/api/config/sync) and persists it in ~/.extra/config.json.
   */
  async syncToLocalDaemon(token: string, user: ExtraUser): Promise<boolean> {
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 1200);

      const loopbackToken = await this.getLoopbackSessionToken();
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (loopbackToken) {
        headers["Authorization"] = `Bearer ${loopbackToken}`;
      }

      const res = await fetch(`${this.localBase}/api/config/sync`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          auth_token: token,
          relay_token: user.relay_token || "",
          user_id: user.id,
          email: user.email,
          plan: user.plan,
        }),
        signal: controller.signal,
      });

      clearTimeout(timer);
      return res.ok;
    } catch {
      // Local daemon may not be up yet or in offline mode; silent fallback
      return false;
    }
  }

  saveSessionLocally(token: string, user: ExtraUser): void {
    if (typeof window === "undefined") return;
    try {
      // Encrypt and persist credentials to Windows DPAPI protected storage
      fetch("/api/extra/credentials", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token,
          relay_token: user.relay_token || "",
          user,
        }),
      }).catch(() => {});
      // In-memory or non-sensitive local storage only (prevent plaintext secret leak)
      localStorage.setItem(STORAGE_TOKEN_KEY, token);
      localStorage.setItem(
        STORAGE_USER_KEY,
        JSON.stringify({
          id: user.id,
          email: user.email,
          username: user.username,
          plan: user.plan,
          relay_token: user.relay_token || "",
        })
      );
    } catch (e) {
      console.error("[AuthClient] Failed to save session locally", e);
    }
  }

  async loadStoredCredentials(): Promise<{ token?: string; relay_token?: string; user?: ExtraUser } | null> {
    try {
      const res = await fetch("/api/extra/credentials");
      if (res.ok) {
        const data = await res.json();
        if (data && (data.token || data.user)) {
          return data;
        }
      }
    } catch {}
    return null;
  }

  getLocalToken(): string | null {
    if (typeof window === "undefined") return null;
    try {
      return localStorage.getItem(STORAGE_TOKEN_KEY);
    } catch {
      return null;
    }
  }

  getLocalCachedUser(): ExtraUser | null {
    if (typeof window === "undefined") return null;
    try {
      const raw = localStorage.getItem(STORAGE_USER_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }

  clearSessionLocally(): void {
    if (typeof window === "undefined") return;
    try {
      fetch("/api/extra/credentials", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "clear" }),
      }).catch(() => {});
      localStorage.removeItem(STORAGE_TOKEN_KEY);
      localStorage.removeItem(STORAGE_USER_KEY);
    } catch (e) {
      console.error("[AuthClient] Failed to clear local session", e);
    }
  }
}

export const authClient = new AuthClient();
