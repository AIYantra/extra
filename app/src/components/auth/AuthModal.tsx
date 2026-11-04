import React, { useState, useEffect, useRef } from "react";
import {
  Mail,
  Lock,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  Copy,
  Check,
  X,
  Laptop,
  KeyRound,
  Eye,
  EyeOff,
  Globe,
  RefreshCw,
} from "lucide-react";
import { ExtraLogoIcon } from "../ExtraLogo";
import { useAuthStore } from "../../store/useAuthStore";
import { authClient, isGoogleOnlyAccountError } from "../../services/authClient";
import { soundEngine } from "../../utils/sound";

interface AuthModalProps {
  forceOpen?: boolean;
  onClose?: () => void;
}

type AuthMode = "login" | "signup";
type AuthStep = "credentials" | "verify_otp" | "waiting_browser";

export function AuthModal({ forceOpen = false, onClose }: AuthModalProps) {
  const {
    isAuthenticated,
    isLocalOfflineMode,
    isOnboardingDismissed,
    isAuthModalOpen,
    closeAuthModal,
    user,
    setAuth,
    setLocalOffline,
    dismissOnboarding,
  } = useAuthStore();

  const [mode, setMode] = useState<AuthMode>("login");
  const [step, setStep] = useState<AuthStep>("credentials");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [otpCode, setOtpCode] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [infoMessage, setInfoMessage] = useState<string | null>(null);
  const [successApiKey, setSuccessApiKey] = useState<string | null>(null);
  const [copiedKey, setCopiedKey] = useState(false);
  const [showGoogleAlt, setShowGoogleAlt] = useState(false);

  const pollIntervalRef = useRef<any>(null);
  // Token already in secure storage when a browser SSO starts. The loopback
  // poll only accepts a *different* token so stale creds can't fake success.
  const preBrowserTokenRef = useRef<string | null>(null);

  // Modal open condition: opens whenever isAuthModalOpen is true, or during fresh onboarding
  const isOpen = isAuthModalOpen || forceOpen || (!isAuthenticated && !isLocalOfflineMode && !isOnboardingDismissed);

  // Close on Escape -> defaults to local mode
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        handleSkip();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen]);

  // Polling for loopback credentials when waiting for browser login
  useEffect(() => {
    if (step === "waiting_browser") {
      pollIntervalRef.current = setInterval(async () => {
        try {
          const creds = await authClient.loadStoredCredentials();
          if (creds && creds.token && creds.user && creds.token !== preBrowserTokenRef.current) {
            clearInterval(pollIntervalRef.current);
            setAuth(creds.token, creds.user);
            setSuccessApiKey(creds.user.relay_token || creds.token);
            setStep("credentials");
            soundEngine.playSuccessChime();
          }
        } catch {}
      }, 1500);
    } else {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    }

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, [step, setAuth]);

  if (!isOpen) return null;

  const handleSkip = () => {
    soundEngine.playTick();
    closeAuthModal();
    setLocalOffline(true);
    dismissOnboarding();
    if (onClose) onClose();
  };

  const handleCredentialsSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setInfoMessage(null);
    setShowGoogleAlt(false);

    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail || !cleanEmail.includes("@") || !cleanEmail.includes(".")) {
      setErrorMessage("Please enter a valid email address.");
      soundEngine.playPanicAlert();
      return;
    }

    if (password.length < 8) {
      setErrorMessage("Password must be at least 8 characters long.");
      soundEngine.playPanicAlert();
      return;
    }

    setLoading(true);
    soundEngine.playTick();

    try {
      if (mode === "login") {
        const res = await authClient.loginWithPassword(cleanEmail, password);
        if (res.requires_verification) {
          // Password login never emails a code itself, so trigger a fresh
          // one before showing the OTP screen.
          try {
            await authClient.resendVerificationCode(cleanEmail);
            setInfoMessage(`We sent a fresh 6-digit code to ${cleanEmail}. Enter it below to finish signing in.`);
          } catch {
            setInfoMessage(`Enter the 6-digit code sent to ${cleanEmail}, or tap Resend Code for a fresh one.`);
          }
          setStep("verify_otp");
          soundEngine.playTick();
          return;
        }

        if (res.token && res.user) {
          setAuth(res.token, res.user);
          setSuccessApiKey(res.user.relay_token || res.token);
          soundEngine.playSuccessChime();
        }
      } else {
        // Sign Up
        const res = await authClient.signupWithPassword(cleanEmail, password, fullName);
        if (res.requires_verification) {
          setStep("verify_otp");
          setInfoMessage(`We sent a 6-digit verification code to ${cleanEmail}. Enter it below to activate your account.`);
          soundEngine.playTick();
          return;
        }

        if (res.token && res.user) {
          setAuth(res.token, res.user);
          setSuccessApiKey(res.user.relay_token || res.token);
          soundEngine.playSuccessChime();
        }
      }
    } catch (err: any) {
      const message = err?.message || "Failed to authenticate. Please check your credentials.";
      setErrorMessage(message);
      // Google-registered accounts have no password: offer one-click SSO
      // instead of leaving the user at a dead-end error.
      if (mode === "login" && isGoogleOnlyAccountError(message)) {
        setShowGoogleAlt(true);
      }
      soundEngine.playPanicAlert();
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtpSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    const cleanCode = otpCode.trim();
    if (!cleanCode || cleanCode.length < 6) {
      setErrorMessage("Please enter the complete 6-digit code.");
      soundEngine.playPanicAlert();
      return;
    }

    setLoading(true);
    soundEngine.playTick();

    try {
      const res = await authClient.verifyOtp(email, cleanCode);
      if (res.token && res.user) {
        setAuth(res.token, res.user);
        setSuccessApiKey(res.user.relay_token || res.token);
        setStep("credentials");
        soundEngine.playSuccessChime();
      }
    } catch (err: any) {
      setErrorMessage(err?.message || "Invalid or expired code. Please try again.");
      soundEngine.playPanicAlert();
    } finally {
      setLoading(false);
    }
  };

  const handleResendCode = async () => {
    setErrorMessage(null);
    setIsResending(true);
    soundEngine.playTick();
    try {
      await authClient.resendVerificationCode(email);
      setInfoMessage(`New verification code sent to ${email.trim()}.`);
    } catch (err: any) {
      setErrorMessage(err?.message || "Failed to resend code. Please wait a moment.");
    } finally {
      setIsResending(false);
    }
  };

  const handleGoogleBrowserLogin = async () => {
    setErrorMessage(null);
    setInfoMessage(null);
    setShowGoogleAlt(false);
    soundEngine.playTick();

    // Snapshot any pre-existing stored token so the loopback poll below
    // only accepts the fresh token from this browser round-trip.
    try {
      const existing = await authClient.loadStoredCredentials();
      preBrowserTokenRef.current = existing?.token || null;
    } catch {
      preBrowserTokenRef.current = null;
    }

    const callbackPort = typeof window !== "undefined" && window.location.port ? window.location.port : "5173";
    const callbackUrl = `http://127.0.0.1:${callbackPort}/api/auth/callback`;
    const authUrl = `https://extra.yantraos.com/login?desktop_callback=${encodeURIComponent(callbackUrl)}`;

    try {
      // 1. Attempt to launch system default browser with active profile cleanly via local daemon
      const res = await fetch("/api/extra/open-browser", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: authUrl }),
      }).catch(() => null);

      // Only fallback to window.open if local daemon is completely unreachable
      if (!res || !res.ok) {
        if (typeof window !== "undefined" && !window.location.port) {
          window.open(authUrl, "_blank");
        }
      }

      setStep("waiting_browser");
    } catch (e: any) {
      setErrorMessage("Could not open system browser. Please use email & password sign-in.");
    }
  };

  const handleCopyKey = () => {
    if (!successApiKey) return;
    navigator.clipboard.writeText(successApiKey);
    setCopiedKey(true);
    soundEngine.playTick();
    setTimeout(() => setCopiedKey(false), 2000);
  };

  const handleFinishLogin = () => {
    closeAuthModal();
    dismissOnboarding();
    if (onClose) onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#1a1a1c]/40 p-4 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-[460px] overflow-hidden rounded-2xl border border-[#dfe4eb] bg-white shadow-2xl">
        {/* Modal Close / Skip Icon */}
        <button
          onClick={handleSkip}
          className="absolute right-4 top-4 cursor-pointer rounded-full p-2 text-[#868c98] transition-colors ease-[cubic-bezier(0.22,1,0.36,1)] hover:bg-[#f4f5f8] hover:text-[#1a1a1c]"
          title="Continue in local mode"
        >
          <X className="size-4" strokeWidth={1.5} />
        </button>

        <div className="p-6">
          {successApiKey ? (
            /* Post-Login Success & API Key Revelation */
            <div className="space-y-6 text-center animate-in fade-in duration-200">
              <div className="mx-auto flex size-12 items-center justify-center rounded-xl border border-[#bbf0cf] bg-[#edfcf2] text-[#0e8345]">
                <CheckCircle2 className="size-5" strokeWidth={1.5} />
              </div>

              <div className="space-y-2">
                <h3 className="text-xl font-semibold text-[#1a1a1c]">
                  Station connected
                </h3>
                <p className="text-sm text-[#525866]">
                  Signed in as {user?.username || "Pilot"}. This computer is linked to Extra Cloud.
                </p>
              </div>

              {/* API Key Box */}
              <div className="rounded-xl border border-[#dfe4eb] bg-[#f0f2f6] p-4 text-left">
                <div className="mb-2 flex items-center justify-between">
                  <span className="flex items-center gap-2 text-xs font-medium text-[#525866]">
                    <KeyRound className="size-4 text-[#525866]" strokeWidth={1.5} />
                    Cloud relay passkey
                  </span>
                  <span className="font-mono text-[11px] tabular-nums text-[#868c98]">
                    {user?.plan === "pro" ? "Pro" : "Free"}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span className="break-all font-mono text-xs font-medium tabular-nums text-[#1a1a1c] select-all">
                    {successApiKey}
                  </span>
                  <button
                    onClick={handleCopyKey}
                    className="flex h-8 shrink-0 cursor-pointer items-center gap-2 rounded-lg border border-[#dfe4eb] bg-white px-3 text-xs font-medium text-[#1a1a1c] transition-colors ease-[cubic-bezier(0.22,1,0.36,1)] hover:bg-[#f4f5f8]"
                  >
                    {copiedKey ? (
                      <>
                        <Check className="size-4 text-[#0e8345]" strokeWidth={1.5} />
                        Copied
                      </>
                    ) : (
                      <>
                        <Copy className="size-4 text-[#525866]" strokeWidth={1.5} />
                        Copy
                      </>
                    )}
                  </button>
                </div>
              </div>

              <div className="space-y-2 rounded-xl border border-[#dfe4eb] bg-white p-4 text-left text-xs text-[#525866]">
                <p className="flex items-center gap-2 font-medium text-[#1a1a1c]">
                  <ShieldCheck className="size-4 text-[#525866]" strokeWidth={1.5} />
                  Sync on
                </p>
                <p>This computer is registered in your fleet on extra.yantraos.com</p>
                <p>Credentials are stored with Windows encryption on this computer</p>
              </div>

              <button
                onClick={handleFinishLogin}
                className="flex h-10 w-full cursor-pointer items-center justify-center gap-2 rounded-[10px] bg-[#1677ff] px-4 text-xs font-medium text-white transition-colors ease-[cubic-bezier(0.22,1,0.36,1)] hover:bg-[#0958d9]"
              >
                Go to Mission Control
                <ArrowRight className="size-4" strokeWidth={1.5} />
              </button>
            </div>
          ) : step === "verify_otp" ? (
            /* OTP Verification Screen */
            <div className="space-y-6 animate-in fade-in duration-200">
              <div className="space-y-2 text-center">
                <div className="mx-auto flex size-12 items-center justify-center rounded-xl border border-[#dfe4eb] bg-[#f4f5f8] text-[#525866]">
                  <Mail className="size-5" strokeWidth={1.5} />
                </div>
                <h2 className="text-xl font-semibold text-[#1a1a1c]">
                  Check your email
                </h2>
                <p className="mx-auto max-w-xs text-xs text-[#525866]">
                  {infoMessage || `Enter the 6-digit code sent to ${email}`}
                </p>
              </div>

              {errorMessage && (
                <div className="flex items-center gap-2 rounded-xl border border-[#ffb9a2] bg-[#fff1f2] p-3 text-xs text-[#e11d48]">
                  <X className="size-4 shrink-0" strokeWidth={1.5} />
                  {errorMessage}
                </div>
              )}

              <form onSubmit={handleVerifyOtpSubmit} className="space-y-4">
                <div>
                  <label htmlFor="auth-otp" className="mb-2 block text-center text-xs font-medium text-[#1a1a1c]">
                    Verification code
                  </label>
                  <input
                    id="auth-otp"
                    autoComplete="one-time-code"
                    type="text"
                    inputMode="numeric"
                    pattern="[0-9]*"
                    maxLength={6}
                    value={otpCode}
                    onChange={(e) => setOtpCode(e.target.value.replace(/[^0-9]/g, "").slice(0, 6))}
                    placeholder="123456"
                    autoFocus
                    required
                    className="h-12 w-full rounded-[10px] border border-[#dfe4eb] bg-white px-4 py-3 text-center font-mono text-xl tabular-nums tracking-[0.3em] text-[#1a1a1c] transition-colors ease-[cubic-bezier(0.22,1,0.36,1)] placeholder:text-[#868c98] focus:border-[#1677ff] focus:outline-none focus:ring-1 focus:ring-[#1677ff]"
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading || otpCode.length < 6}
                  className="flex h-10 w-full cursor-pointer items-center justify-center gap-2 rounded-[10px] bg-[#1677ff] px-4 text-xs font-medium text-white transition-colors ease-[cubic-bezier(0.22,1,0.36,1)] hover:bg-[#0958d9] disabled:opacity-50"
                >
                  {loading ? (
                    <div className="size-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  ) : (
                    <>
                      Verify
                      <ArrowRight className="size-4" strokeWidth={1.5} />
                    </>
                  )}
                </button>
              </form>

              <div className="flex items-center justify-between border-t border-[#dfe4eb] pt-4 text-xs">
                <button
                  type="button"
                  onClick={() => {
                    setStep("credentials");
                    setErrorMessage(null);
                  }}
                  className="cursor-pointer text-[#525866] transition-colors ease-[cubic-bezier(0.22,1,0.36,1)] hover:text-[#1a1a1c]"
                >
                  Back
                </button>
                <button
                  type="button"
                  onClick={handleResendCode}
                  disabled={isResending}
                  className="cursor-pointer font-medium text-[#1677ff] transition-colors ease-[cubic-bezier(0.22,1,0.36,1)] hover:underline disabled:opacity-50"
                >
                  {isResending ? "Sending" : "Resend code"}
                </button>
              </div>
            </div>
          ) : step === "waiting_browser" ? (
            /* Waiting for Browser SSO Loopback */
            <div className="space-y-6 text-center animate-in fade-in duration-200">
              <div className="mx-auto flex size-12 items-center justify-center rounded-xl border border-[#dfe4eb] bg-[#f4f5f8] text-[#525866]">
                <Globe className="size-5" strokeWidth={1.5} />
              </div>

              <div className="space-y-2">
                <h3 className="text-lg font-semibold text-[#1a1a1c]">
                  Continue in your browser
                </h3>
                <p className="mx-auto max-w-xs text-xs text-[#525866]">
                  We opened <span className="font-mono text-[#1a1a1c]">extra.yantraos.com</span> in your browser. Finish sign-in there.
                </p>
              </div>

              <div className="flex items-center justify-center gap-2 rounded-xl border border-[#dfe4eb] bg-[#f8f9fb] p-4 text-xs text-[#525866]">
                <RefreshCw className="size-4 animate-spin text-[#525866]" strokeWidth={1.5} />
                <span>Waiting for browser sign-in</span>
              </div>

              <div className="space-y-2">
                <button
                  type="button"
                  onClick={handleGoogleBrowserLogin}
                  className="h-10 w-full cursor-pointer rounded-[10px] border border-[#dfe4eb] bg-white px-4 text-xs font-medium text-[#1a1a1c] transition-colors ease-[cubic-bezier(0.22,1,0.36,1)] hover:bg-[#f4f5f8]"
                >
                  Reopen browser
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setStep("credentials");
                    setErrorMessage(null);
                  }}
                  className="w-full cursor-pointer py-2 text-xs text-[#525866] transition-colors ease-[cubic-bezier(0.22,1,0.36,1)] hover:text-[#1a1a1c]"
                >
                  Use email instead
                </button>
              </div>
            </div>
          ) : (
            /* Login & Sign Up Form */
            <div className="space-y-6">
              {/* Header */}
              <div className="space-y-2 text-center">
                <ExtraLogoIcon className="mx-auto mb-1 size-10 text-[#1a1a1c]" color="#1A1A1C" />
                <h2 className="text-2xl font-semibold text-[#1a1a1c]">
                  {mode === "login" ? "Sign in to Extra" : "Create your account"}
                </h2>
                <p className="text-xs text-[#525866]">
                  Link this computer to Extra Cloud.
                </p>
              </div>

              {/* Mode Toggle Tabs */}
              <div className="flex rounded-xl border border-[#dfe4eb] bg-[#f0f2f6] p-1">
                <button
                  type="button"
                  onClick={() => {
                    setMode("login");
                    setErrorMessage(null);
                    setInfoMessage(null);
                    setShowGoogleAlt(false);
                  }}
                  className={`h-8 flex-1 cursor-pointer rounded-lg text-xs font-medium transition-colors ease-[cubic-bezier(0.22,1,0.36,1)] ${
                    mode === "login"
                      ? "bg-white text-[#1a1a1c] shadow-xs"
                      : "text-[#525866] hover:text-[#1a1a1c]"
                  }`}
                >
                  Sign in
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setMode("signup");
                    setErrorMessage(null);
                    setInfoMessage(null);
                    setShowGoogleAlt(false);
                  }}
                  className={`h-8 flex-1 cursor-pointer rounded-lg text-xs font-medium transition-colors ease-[cubic-bezier(0.22,1,0.36,1)] ${
                    mode === "signup"
                      ? "bg-white text-[#1a1a1c] shadow-xs"
                      : "text-[#525866] hover:text-[#1a1a1c]"
                  }`}
                >
                  Create account
                </button>
              </div>

              {errorMessage && (
                <div className="rounded-xl border border-[#ffb9a2] bg-[#fff1f2] p-3 text-xs text-[#e11d48]">
                  <div className="flex items-center gap-2">
                    <X className="size-4 shrink-0" strokeWidth={1.5} />
                    <span>{errorMessage}</span>
                  </div>
                  {showGoogleAlt && (
                    <button
                      type="button"
                      onClick={handleGoogleBrowserLogin}
                      className="mt-3 h-9 w-full cursor-pointer rounded-lg border border-[#ffb9a2] bg-white px-3 text-xs font-medium text-[#1a1a1c] transition-colors ease-[cubic-bezier(0.22,1,0.36,1)] hover:bg-[#fff7f7]"
                    >
                      Continue with Google instead
                    </button>
                  )}
                </div>
              )}

              {infoMessage && (
                <div className="flex items-center gap-2 rounded-xl border border-[#bbf0cf] bg-[#edfcf2] p-3 text-xs text-[#0e8345]">
                  <ShieldCheck className="size-4 shrink-0 text-[#0e8345]" strokeWidth={1.5} />
                  {infoMessage}
                </div>
              )}

              {/* Input Form */}
              <form onSubmit={handleCredentialsSubmit} className="space-y-4">
                {mode === "signup" && (
                  <div>
                    <label htmlFor="auth-fullname" className="mb-2 block text-xs font-medium text-[#1a1a1c]">
                      Full name
                    </label>
                    <input
                      id="auth-fullname"
                      autoComplete="name"
                      type="text"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      placeholder="Ada Lovelace"
                      className="h-10 w-full rounded-[10px] border border-[#dfe4eb] bg-white px-3 text-xs text-[#1a1a1c] transition-colors ease-[cubic-bezier(0.22,1,0.36,1)] placeholder:text-[#868c98] focus:border-[#1677ff] focus:outline-none focus:ring-1 focus:ring-[#1677ff]"
                    />
                  </div>
                )}

                <div>
                  <label htmlFor="auth-email" className="mb-2 block text-xs font-medium text-[#1a1a1c]">
                    Email address
                  </label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-3 size-4 text-[#868c98]" strokeWidth={1.5} />
                    <input
                      id="auth-email"
                      autoComplete="email"
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="operator@company.com"
                      required
                      className="h-10 w-full rounded-[10px] border border-[#dfe4eb] bg-white pl-10 pr-3 text-xs text-[#1a1a1c] transition-colors ease-[cubic-bezier(0.22,1,0.36,1)] placeholder:text-[#868c98] focus:border-[#1677ff] focus:outline-none focus:ring-1 focus:ring-[#1677ff]"
                    />
                  </div>
                </div>

                <div>
                  <label htmlFor="auth-password" className="mb-2 block text-xs font-medium text-[#1a1a1c]">
                    Password
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-3 size-4 text-[#868c98]" strokeWidth={1.5} />
                    <input
                      id="auth-password"
                      autoComplete={mode === "login" ? "current-password" : "new-password"}
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="At least 8 characters"
                      required
                      minLength={8}
                      className="h-10 w-full rounded-[10px] border border-[#dfe4eb] bg-white pl-10 pr-10 text-xs text-[#1a1a1c] transition-colors ease-[cubic-bezier(0.22,1,0.36,1)] placeholder:text-[#868c98] focus:border-[#1677ff] focus:outline-none focus:ring-1 focus:ring-[#1677ff]"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-3 text-[#868c98] transition-colors ease-[cubic-bezier(0.22,1,0.36,1)] hover:text-[#1a1a1c]"
                    >
                      {showPassword ? <EyeOff className="size-4" strokeWidth={1.5} /> : <Eye className="size-4" strokeWidth={1.5} />}
                    </button>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="flex h-10 w-full cursor-pointer items-center justify-center gap-2 rounded-[10px] bg-[#1677ff] px-4 text-xs font-medium text-white transition-colors ease-[cubic-bezier(0.22,1,0.36,1)] hover:bg-[#0958d9] disabled:opacity-50"
                >
                  {loading ? (
                    <div className="size-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  ) : (
                    <>
                      {mode === "login" ? "Sign in" : "Create account"}
                      <ArrowRight className="size-4" strokeWidth={1.5} />
                    </>
                  )}
                </button>
              </form>

              {/* Social Login Divider */}
              <div className="flex items-center gap-3">
                <div className="h-px w-full bg-[#dfe4eb]" />
                <span className="shrink-0 text-xs text-[#868c98]">
                  or continue with browser
                </span>
                <div className="h-px w-full bg-[#dfe4eb]" />
              </div>

              {/* 1-Click Google & Browser SSO Button */}
              <button
                type="button"
                onClick={handleGoogleBrowserLogin}
                className="flex h-10 w-full cursor-pointer items-center justify-center gap-2 rounded-[10px] border border-[#dfe4eb] bg-white px-4 text-xs font-medium text-[#1a1a1c] transition-colors ease-[cubic-bezier(0.22,1,0.36,1)] hover:bg-[#f4f5f8]"
              >
                <svg className="size-4" viewBox="0 0 24 24">
                  <path
                    fill="#4285F4"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                  />
                </svg>
                Continue with Google
              </button>

              {/* Crucial Mandatory Skip Link */}
              <div className="space-y-2 border-t border-[#dfe4eb] pt-4 text-center">
                <button
                  type="button"
                  onClick={handleSkip}
                  className="inline-flex cursor-pointer items-center gap-2 py-1 text-center text-xs font-medium text-[#525866] transition-colors ease-[cubic-bezier(0.22,1,0.36,1)] hover:text-[#1a1a1c]"
                >
                  <Laptop className="size-4 shrink-0" strokeWidth={1.5} />
                  Continue in local mode
                  <kbd className="rounded border border-[#dfe4eb] bg-[#f4f5f8] px-1.5 py-0.5 font-mono text-[11px] tabular-nums text-[#868c98]">
                    Esc
                  </kbd>
                </button>
                <p className="font-mono text-[11px] tabular-nums text-[#868c98]">
                  relay · extra.yantraos.com
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
