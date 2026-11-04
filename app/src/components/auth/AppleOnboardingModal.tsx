import React, { useState, useRef, useEffect } from "react";
import {
  Mail,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  Copy,
  Check,
  RefreshCw,
  X,
  Laptop,
} from "lucide-react";
import { ExtraLogoIcon } from "../ExtraLogo";
import { useAuthStore } from "../../store/useAuthStore";
import { authClient, type ExtraUser } from "../../services/authClient";
import { soundEngine } from "../../utils/sound";

interface AppleOnboardingModalProps {
  forceOpen?: boolean;
  onClose?: () => void;
}

type Step = "welcome" | "otp" | "success";

export function AppleOnboardingModal({ forceOpen = false, onClose }: AppleOnboardingModalProps) {
  const {
    isAuthenticated,
    isLocalOfflineMode,
    isOnboardingDismissed,
    user,
    setAuth,
    setLocalOffline,
    dismissOnboarding,
  } = useAuthStore();

  const [step, setStep] = useState<Step>("welcome");
  const [email, setEmail] = useState("");
  const [otpDigits, setOtpDigits] = useState<string[]>(["", "", "", "", "", ""]);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [resendCooldown, setResendCooldown] = useState(0);
  const [copiedKey, setCopiedKey] = useState(false);
  const [provisionedUser, setProvisionedUser] = useState<ExtraUser | null>(user);

  const otpInputRefs = useRef<(HTMLInputElement | null)[]>([]);

  // Determine if modal should be shown
  const isOpen = forceOpen || (!isAuthenticated && !isLocalOfflineMode && !isOnboardingDismissed);

  // Resend cooldown countdown effect
  useEffect(() => {
    if (resendCooldown <= 0) return;
    const timer = setInterval(() => {
      setResendCooldown((prev) => Math.max(0, prev - 1));
    }, 1000);
    return () => clearInterval(timer);
  }, [resendCooldown]);

  // Focus first OTP box when entering OTP step
  useEffect(() => {
    if (step === "otp" && otpInputRefs.current[0]) {
      setTimeout(() => {
        otpInputRefs.current[0]?.focus();
      }, 100);
    }
  }, [step]);

  // Dismiss modal on Escape key
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setLocalOffline(true);
        dismissOnboarding();
        if (onClose) onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose, dismissOnboarding, setLocalOffline]);

  if (!isOpen) return null;

  // Handle email submit -> request OTP
  const handleRequestOtp = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setErrorMessage(null);

    const cleanEmail = email.trim();
    if (!cleanEmail || !cleanEmail.includes("@")) {
      setErrorMessage("Please enter a valid email address.");
      soundEngine.playPanicAlert();
      return;
    }

    setLoading(true);
    soundEngine.playTick();

    try {
      await authClient.requestOtp(cleanEmail);
      setStep("otp");
      setResendCooldown(30);
      setOtpDigits(["", "", "", "", "", ""]);
      soundEngine.playSuccessChime();
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to send verification code.");
      soundEngine.playPanicAlert();
    } finally {
      setLoading(false);
    }
  };

  // Handle OTP digit changes with auto-focus advancing
  const handleOtpChange = (index: number, value: string) => {
    const digit = value.replace(/[^0-9]/g, "").slice(-1);
    const newDigits = [...otpDigits];
    newDigits[index] = digit;
    setOtpDigits(newDigits);
    setErrorMessage(null);

    if (digit && index < 5) {
      otpInputRefs.current[index + 1]?.focus();
    }

    const fullCode = newDigits.join("");
    if (fullCode.length === 6 && !newDigits.some((d) => d === "")) {
      handleVerifyOtp(fullCode);
    }
  };

  // Handle backspace navigation across OTP boxes
  const handleOtpKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Backspace") {
      if (!otpDigits[index] && index > 0) {
        const newDigits = [...otpDigits];
        newDigits[index - 1] = "";
        setOtpDigits(newDigits);
        otpInputRefs.current[index - 1]?.focus();
      }
    }
  };

  // Handle paste of 6-digit code
  const handleOtpPaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData("text").trim().replace(/[^0-9]/g, "");
    if (pastedData.length >= 6) {
      const chars = pastedData.slice(0, 6).split("");
      setOtpDigits(chars);
      otpInputRefs.current[5]?.focus();
      handleVerifyOtp(pastedData.slice(0, 6));
    }
  };

  // Verify OTP with backend
  const handleVerifyOtp = async (codeOverride?: string) => {
    const code = codeOverride || otpDigits.join("");
    if (code.length < 6) {
      setErrorMessage("Please enter all 6 digits.");
      soundEngine.playPanicAlert();
      return;
    }

    setLoading(true);
    setErrorMessage(null);
    soundEngine.playTick();

    try {
      const res = await authClient.verifyOtp(email, code);
      if (res.success && res.token && res.user) {
        setAuth(res.token, res.user);
        setProvisionedUser(res.user);
        setStep("success");
        soundEngine.playSuccessChime();
      } else {
        throw new Error(res.error || "Verification failed.");
      }
    } catch (err: any) {
      setErrorMessage(err.message || "Invalid verification code.");
      soundEngine.playPanicAlert();
    } finally {
      setLoading(false);
    }
  };

  // Resend OTP code
  const handleResend = async () => {
    if (resendCooldown > 0 || loading) return;
    setLoading(true);
    setErrorMessage(null);
    try {
      await authClient.requestOtp(email);
      setResendCooldown(30);
      soundEngine.playTick();
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to resend code.");
    } finally {
      setLoading(false);
    }
  };

  // Sovereign Local Offline Mode Bypass
  const handleSkipLocalOffline = () => {
    soundEngine.playTick();
    setLocalOffline(true);
    dismissOnboarding();
    if (onClose) onClose();
  };

  const handleFinish = () => {
    soundEngine.playTick();
    dismissOnboarding();
    if (onClose) onClose();
  };

  const handleCopyPasskey = (passkey: string) => {
    navigator.clipboard.writeText(passkey);
    setCopiedKey(true);
    soundEngine.playTick();
    setTimeout(() => setCopiedKey(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40 backdrop-blur-sm transition-all p-4">
      {/* Apple-grade Modal Container with Concentric Radiuses */}
      <div
        className="relative w-full max-w-md overflow-hidden rounded-2xl bg-white dark:bg-[#121417] p-7 shadow-2xl border border-black/[0.08] dark:border-white/[0.08] transition-all duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Optional Dismiss button */}
        {(isOnboardingDismissed || isAuthenticated || isLocalOfflineMode) && (
          <button
            onClick={() => {
              if (onClose) onClose();
              dismissOnboarding();
            }}
            className="absolute top-4 right-4 p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-zinc-200 hover:bg-black/[0.03] dark:hover:bg-white/[0.05] transition-colors cursor-pointer"
          >
            <X className="size-4" />
          </button>
        )}

        {/* ================= STEP 1: WELCOME & EMAIL ================= */}
        {step === "welcome" && (
          <div className="flex flex-col items-center text-center">
            {/* Official Extra Dotted-X Brand Mark */}
            <div className="mb-4 drop-shadow-xs">
              <ExtraLogoIcon className="size-13 text-[#1a1a1c]" color="#1A1A1C" />
            </div>

            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
              Welcome to Extra
            </h2>
            <p className="mt-1.5 text-xs text-slate-500 dark:text-zinc-400 max-w-[280px] leading-relaxed">
              Your sovereign personal desktop assistant. Connect your tools in seconds.
            </p>

            {/* Email Form */}
            <form onSubmit={handleRequestOtp} className="w-full mt-6 space-y-3.5">
              <div className="relative text-left">
                <label className="block text-xs font-medium text-slate-700 dark:text-zinc-300 mb-1 ml-0.5">
                  Email Address
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400 dark:text-zinc-500">
                    <Mail className="size-4" />
                  </div>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    autoFocus
                    required
                    disabled={loading}
                    className="w-full pl-9 pr-3.5 py-2.5 rounded-xl bg-slate-50 dark:bg-zinc-900 border border-black/[0.08] dark:border-white/[0.08] text-slate-900 dark:text-white placeholder:text-slate-400 text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all font-medium"
                  />
                </div>
              </div>

              {errorMessage && (
                <div className="p-2.5 rounded-xl bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-900/40 text-xs text-rose-600 dark:text-rose-400 font-medium text-left leading-relaxed">
                  {errorMessage}
                </div>
              )}

              {/* Primary Continue Button */}
              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 px-4 rounded-xl bg-slate-900 hover:bg-slate-800 dark:bg-white dark:hover:bg-zinc-100 text-white dark:text-slate-900 text-xs sm:text-sm font-semibold shadow-xs transition-all flex items-center justify-center gap-2 disabled:opacity-50 active:scale-95 cursor-pointer"
              >
                {loading ? (
                  <>
                    <RefreshCw className="size-3.5 animate-spin" />
                    <span>Sending code...</span>
                  </>
                ) : (
                  <>
                    <span>Continue with Email</span>
                    <ArrowRight className="size-3.5" />
                  </>
                )}
              </button>
            </form>

            {/* Sovereign Local Mode Bypass */}
            <div className="mt-5 pt-4 border-t border-black/[0.06] dark:border-white/[0.06] w-full">
              <button
                type="button"
                onClick={handleSkipLocalOffline}
                className="text-xs font-medium text-slate-500 hover:text-slate-800 dark:text-zinc-400 dark:hover:text-zinc-200 transition-colors flex items-center justify-center gap-1.5 mx-auto py-0.5 cursor-pointer"
              >
                <Laptop className="size-3.5 text-slate-400" />
                <span>Use Offline without an Account</span>
                <span className="text-slate-400 dark:text-zinc-600">→</span>
              </button>
              <p className="text-[11px] text-slate-400 dark:text-zinc-500 mt-1">
                100% private, operates strictly on your machine
              </p>
            </div>
          </div>
        )}

        {/* ================= STEP 2: 6-DIGIT OTP ================= */}
        {step === "otp" && (
          <div className="flex flex-col items-center text-center">
            {/* Header */}
            <div className="size-12 rounded-2xl bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-100 dark:border-indigo-900/40 flex items-center justify-center mb-3.5 text-indigo-600 dark:text-indigo-400 shadow-xs">
              <Mail className="size-5" />
            </div>

            <h2 className="text-lg font-bold tracking-tight text-slate-900 dark:text-white">
              Check your email
            </h2>
            <p className="mt-1 text-xs text-slate-500 dark:text-zinc-400 max-w-[280px]">
              We sent a 6-digit code to{" "}
              <span className="font-semibold text-slate-800 dark:text-zinc-200">{email}</span>
            </p>
            <button
              onClick={() => {
                setStep("welcome");
                setErrorMessage(null);
              }}
              className="mt-1 text-xs text-indigo-600 dark:text-indigo-400 hover:underline font-medium cursor-pointer"
            >
              Change email
            </button>

            {/* 6-Box Segmented OTP Inputs */}
            <div className="flex items-center justify-center gap-1.5 sm:gap-2 mt-5 mb-3" onPaste={handleOtpPaste}>
              {otpDigits.map((digit, idx) => (
                <input
                  key={idx}
                  ref={(el) => {
                    otpInputRefs.current[idx] = el;
                  }}
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  maxLength={1}
                  value={digit}
                  disabled={loading}
                  onChange={(e) => handleOtpChange(idx, e.target.value)}
                  onKeyDown={(e) => handleOtpKeyDown(idx, e)}
                  className="size-11 sm:size-12 text-center text-lg font-bold font-mono rounded-xl bg-slate-50 dark:bg-zinc-900 border border-black/[0.08] dark:border-white/[0.08] text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all select-none tabular-nums"
                />
              ))}
            </div>

            {errorMessage && (
              <div className="w-full p-2.5 rounded-xl bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-900/40 text-xs text-rose-600 dark:text-rose-400 font-medium leading-relaxed mb-3">
                {errorMessage}
              </div>
            )}

            {/* Verify CTA */}
            <button
              onClick={() => handleVerifyOtp()}
              disabled={loading || otpDigits.some((d) => !d)}
              className="w-full py-2.5 px-4 rounded-xl bg-slate-900 hover:bg-slate-800 dark:bg-white dark:hover:bg-zinc-100 text-white dark:text-slate-900 text-xs sm:text-sm font-semibold shadow-xs transition-all flex items-center justify-center gap-2 disabled:opacity-40 active:scale-95 cursor-pointer mt-2"
            >
              {loading ? (
                <>
                  <RefreshCw className="size-3.5 animate-spin" />
                  <span>Verifying...</span>
                </>
              ) : (
                <span>Verify & Connect</span>
              )}
            </button>

            {/* Resend Timer */}
            <div className="mt-4 text-xs text-slate-500 dark:text-zinc-400">
              {resendCooldown > 0 ? (
                <span className="tabular-nums">Didn't receive it? Resend in {resendCooldown}s</span>
              ) : (
                <button
                  onClick={handleResend}
                  disabled={loading}
                  className="text-indigo-600 dark:text-indigo-400 font-semibold hover:underline cursor-pointer"
                >
                  Resend code
                </button>
              )}
            </div>
          </div>
        )}

        {/* ================= STEP 3: PROVISIONING SUCCESS ================= */}
        {step === "success" && (
          <div className="flex flex-col items-center text-center">
            {/* Emerald Checkmark Badge */}
            <div className="size-13 rounded-2xl bg-emerald-500/10 border border-emerald-500/25 flex items-center justify-center text-emerald-600 dark:text-emerald-400 mb-4 shadow-xs">
              <CheckCircle2 className="size-6" />
            </div>

            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
              You're all set!
            </h2>
            <p className="mt-1 text-xs text-slate-500 dark:text-zinc-400">
              Logged in as <span className="font-semibold text-slate-800 dark:text-zinc-200">{provisionedUser?.email || email}</span>
            </p>

            {/* Passkey Provisioned Card */}
            <div className="w-full mt-5 p-3.5 rounded-xl bg-slate-50 dark:bg-zinc-900 border border-black/[0.06] dark:border-white/[0.08] text-left">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="size-3.5 text-emerald-500" />
                  <span className="text-xs font-semibold text-slate-800 dark:text-zinc-200">
                    Your Extra Passkey
                  </span>
                </div>
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                  {provisionedUser?.plan || "Free"} Plan
                </span>
              </div>

              <div className="flex items-center justify-between gap-2 p-2 rounded-lg bg-white dark:bg-[#121417] border border-black/[0.04] dark:border-white/[0.05]">
                <span className="font-mono text-xs text-slate-600 dark:text-zinc-300 truncate">
                  {provisionedUser?.relay_token
                    ? `${provisionedUser.relay_token.slice(0, 14)}••••••••••••`
                    : "extra_rel_••••••••••••••••"}
                </span>
                {provisionedUser?.relay_token && (
                  <button
                    onClick={() => handleCopyPasskey(provisionedUser.relay_token!)}
                    className="p-1 rounded-md text-slate-400 hover:text-slate-700 dark:hover:text-zinc-200 transition-colors cursor-pointer"
                    title="Copy Passkey"
                  >
                    {copiedKey ? <Check className="size-3 text-emerald-500" /> : <Copy className="size-3" />}
                  </button>
                )}
              </div>

              <p className="text-[11px] text-slate-500 dark:text-zinc-400 mt-2 leading-relaxed">
                Your AI tools (Claude, Cursor, ChatGPT) can now connect in one click.
              </p>
            </div>

            {/* Finish CTA */}
            <button
              onClick={handleFinish}
              className="w-full mt-5 py-2.5 px-4 rounded-xl bg-slate-900 hover:bg-slate-800 dark:bg-white dark:hover:bg-zinc-100 text-white dark:text-slate-900 text-xs sm:text-sm font-semibold shadow-xs transition-all flex items-center justify-center gap-2 active:scale-95 cursor-pointer"
            >
              <span>Open Extra</span>
              <ArrowRight className="size-3.5" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
