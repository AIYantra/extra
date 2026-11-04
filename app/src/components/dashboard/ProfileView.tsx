import { useEffect, useState } from "react";
import {
  KeyRound,
  Copy,
  Check,
  Eye,
  EyeOff,
  RefreshCw,
  ShieldCheck,
  MonitorSmartphone,
  LogOut,
  Fingerprint,
} from "lucide-react";
import { toast } from "sonner";
import { ExtraAvatar } from "../ExtraAvatar";
import { authClient } from "../../services/authClient";
import { useAuthStore } from "../../store/useAuthStore";
import { soundEngine } from "../../utils/sound";

function planLabel(plan?: string | null) {
  if (plan === "pro") return "Pro Unlimited";
  if (plan === "team") return "Team";
  return "Free Cloud";
}

export function ProfileView() {
  const { user, relayToken, logout, openAuthModal, refreshProfile } = useAuthStore();
  const [showRelay, setShowRelay] = useState(false);
  const [copied, setCopied] = useState(false);
  const [rotating, setRotating] = useState(false);
  const [armRotate, setArmRotate] = useState(false);
  const [currentPw, setCurrentPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [pwBusy, setPwBusy] = useState(false);
  const [pwMsg, setPwMsg] = useState<string | null>(null);
  const [pwErr, setPwErr] = useState<string | null>(null);

  useEffect(() => {
    if (!armRotate) return;
    const t = setTimeout(() => setArmRotate(false), 6000);
    return () => clearTimeout(t);
  }, [armRotate]);

  if (!user) {
    return (
      <div className="p-6">
        <div className="max-w-[560px] mx-auto bg-white border border-[#dfe4eb] rounded-2xl p-8 text-center shadow-2xs">
          <div className="mx-auto size-12 rounded-full bg-[#f0f2f6] flex items-center justify-center mb-4">
            <Fingerprint className="size-5 text-[#868c98]" />
          </div>
          <h2 className="text-base font-semibold text-[#1a1a1c]">Sign in to view your profile</h2>
          <p className="text-xs text-[#868c98] mt-1.5 leading-relaxed">
            Your avatar, relay passkey, paired devices and security settings live here once you connect.
          </p>
          <button
            onClick={() => {
              soundEngine.playTick();
              openAuthModal();
            }}
            className="mt-5 px-5 py-2 rounded-lg bg-[#1677ff] text-white text-xs font-semibold hover:bg-[#0f64d8] transition-colors cursor-pointer"
          >
            Sign In & Connect Cloud
          </button>
        </div>
      </div>
    );
  }

  const passkey = relayToken || user?.relay_token || "";
  const masked = passkey ? "•".repeat(Math.min(passkey.length, 24)) : "—";

  const handleCopy = async () => {
    if (!passkey) return;
    try {
      await navigator.clipboard.writeText(passkey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      toast.success("Passkey copied to clipboard");
    } catch {
      toast.error("Could not copy passkey");
    }
  };

  const handleRotate = async () => {
    if (!armRotate) {
      setArmRotate(true);
      return;
    }
    setArmRotate(false);
    setRotating(true);
    try {
      await authClient.rotateRelayPasskey();
      await refreshProfile();
      soundEngine.playSuccessChime();
      toast.success("New passkey generated and saved. Old keys stop working now.");
    } catch (err: any) {
      toast.error(err?.message || "Could not rotate passkey");
    } finally {
      setRotating(false);
    }
  };

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    setPwMsg(null);
    setPwErr(null);
    if (newPw !== confirmPw) {
      setPwErr("New passwords do not match.");
      return;
    }
    setPwBusy(true);
    try {
      await authClient.changeUserPassword(currentPw, newPw);
      setPwMsg("Password updated successfully.");
      setCurrentPw("");
      setNewPw("");
      setConfirmPw("");
      soundEngine.playSuccessChime();
    } catch (err: any) {
      setPwErr(err?.message || "Failed to update password.");
    } finally {
      setPwBusy(false);
    }
  };

  const devices = (user?.paired_devices || []) as Array<{
    device_name?: string;
    device_id?: string;
    platform?: string;
    os?: string;
    status?: string;
  }>;

  return (
    <div className="p-6">
      <div className="max-w-[720px] mx-auto space-y-4">
        <div>
          <h1 className="text-xl font-semibold text-[#1a1a1c] tracking-tight">Profile</h1>
          <p className="text-xs text-[#868c98] mt-1">
            Your identity, relay credentials, devices and security.
          </p>
        </div>

        {/* Identity */}
        <div className="bg-white border border-[#dfe4eb] rounded-2xl p-5 shadow-2xs">
          <div className="flex items-center gap-4">
            <ExtraAvatar seed={user.email} size={72} />
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="text-base font-semibold text-[#1a1a1c] truncate">
                  {user.username || user.email}
                </h2>
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-[#e8f3ff] text-[#1677ff]">
                  {planLabel(user.plan)}
                </span>
              </div>
              <p className="text-xs text-[#868c98] truncate mt-0.5">{user.email}</p>
              <p className="text-[11px] text-[#868c98] font-mono mt-1 truncate" title={user.id}>
                id: {user.id}
              </p>
            </div>
          </div>
          <p className="text-[11px] text-[#868c98] mt-4 leading-relaxed">
            Your avatar is generated from your account and looks the same on the web dashboard.
            No profile photo is ever uploaded.
          </p>
        </div>

        {/* Relay passkey */}
        <div className="bg-white border border-[#dfe4eb] rounded-2xl p-5 shadow-2xs">
          <div className="flex items-center gap-2">
            <KeyRound className="size-4 text-[#868c98]" />
            <h3 className="text-sm font-semibold text-[#1a1a1c]">Cloud Relay Passkey</h3>
          </div>
          <div className="flex items-center gap-2 mt-3">
            <div className="relative flex-1">
              <input
                type={showRelay ? "text" : "password"}
                readOnly
                value={showRelay ? passkey : masked}
                className="w-full py-2 pl-3 pr-9 rounded-lg border border-[#dfe4eb] bg-[#f8f9fb] text-xs font-mono text-[#1a1a1c] outline-none"
              />
              <button
                onClick={() => setShowRelay((v) => !v)}
                className="absolute right-2 top-2 text-[#868c98] hover:text-[#1a1a1c] cursor-pointer"
                title={showRelay ? "Hide" : "Reveal"}
              >
                {showRelay ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
              </button>
            </div>
            <button
              onClick={handleCopy}
              className="px-3 py-2 rounded-lg border border-[#dfe4eb] text-xs font-medium text-[#1a1a1c] hover:bg-[#f8f9fb] transition-colors cursor-pointer flex items-center gap-1.5"
            >
              {copied ? <Check className="size-3.5 text-[#0e8345]" /> : <Copy className="size-3.5" />}
              {copied ? "Copied" : "Copy"}
            </button>
            <button
              onClick={handleRotate}
              disabled={rotating}
              className={`px-3 py-2 rounded-lg text-xs font-medium transition-colors cursor-pointer flex items-center gap-1.5 ${
                armRotate
                  ? "bg-[#e11d48] text-white hover:bg-[#be123c]"
                  : "border border-[#dfe4eb] text-[#1a1a1c] hover:bg-[#f8f9fb]"
              }`}
            >
              <RefreshCw className={`size-3.5 ${rotating ? "animate-spin" : ""}`} />
              {rotating ? "Rotating" : armRotate ? "Confirm rotate?" : "Rotate"}
            </button>
          </div>
          <p className="text-[11px] text-[#868c98] mt-2.5 leading-relaxed">
            Rotating mints a fresh key and saves it to this machine. Old keys stop working immediately.
          </p>
        </div>

        {/* Paired devices */}
        <div className="bg-white border border-[#dfe4eb] rounded-2xl p-5 shadow-2xs">
          <div className="flex items-center gap-2">
            <MonitorSmartphone className="size-4 text-[#868c98]" />
            <h3 className="text-sm font-semibold text-[#1a1a1c]">
              Paired Devices {devices.length > 0 && <span className="text-[#868c98] font-normal">({devices.length})</span>}
            </h3>
          </div>
          {devices.length === 0 ? (
            <p className="text-xs text-[#868c98] mt-3 leading-relaxed">
              No devices paired yet. This machine pairs automatically the next time it syncs.
            </p>
          ) : (
            <div className="mt-3 space-y-2">
              {devices.map((d, i) => (
                <div
                  key={d.device_id || i}
                  className="flex items-center gap-3 px-3 py-2.5 rounded-xl border border-[#dfe4eb] bg-[#f8f9fb]"
                >
                  <MonitorSmartphone className="size-4 text-[#868c98] shrink-0" />
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-medium text-[#1a1a1c] truncate">
                      {d.device_name || d.device_id || "Unknown device"}
                    </p>
                    <p className="text-[11px] text-[#868c98] truncate">
                      {[d.platform, d.os].filter(Boolean).join(" · ") || "—"}
                    </p>
                  </div>
                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-[#e9f9f0] text-[#0e8345] shrink-0">
                    {d.status || "linked"}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Security */}
        <div className="bg-white border border-[#dfe4eb] rounded-2xl p-5 shadow-2xs">
          <div className="flex items-center gap-2">
            <ShieldCheck className="size-4 text-[#868c98]" />
            <h3 className="text-sm font-semibold text-[#1a1a1c]">Change Password</h3>
          </div>
          <form onSubmit={handlePasswordChange} className="mt-3 space-y-2.5 max-w-[420px]">
            <input
              type="password"
              value={currentPw}
              onChange={(e) => setCurrentPw(e.target.value)}
              placeholder="Current password"
              autoComplete="current-password"
              className="w-full py-2 px-3 rounded-lg border border-[#dfe4eb] bg-white text-xs text-[#1a1a1c] outline-none focus:border-[#1677ff] transition-colors"
            />
            <input
              type="password"
              value={newPw}
              onChange={(e) => setNewPw(e.target.value)}
              placeholder="New password (min 8 characters)"
              autoComplete="new-password"
              className="w-full py-2 px-3 rounded-lg border border-[#dfe4eb] bg-white text-xs text-[#1a1a1c] outline-none focus:border-[#1677ff] transition-colors"
            />
            <input
              type="password"
              value={confirmPw}
              onChange={(e) => setConfirmPw(e.target.value)}
              placeholder="Confirm new password"
              autoComplete="new-password"
              className="w-full py-2 px-3 rounded-lg border border-[#dfe4eb] bg-white text-xs text-[#1a1a1c] outline-none focus:border-[#1677ff] transition-colors"
            />
            {pwErr && <p className="text-xs text-[#e11d48]">{pwErr}</p>}
            {pwMsg && <p className="text-xs text-[#0e8345]">{pwMsg}</p>}
            <button
              type="submit"
              disabled={pwBusy || !currentPw || !newPw || !confirmPw}
              className="px-4 py-2 rounded-lg bg-[#1677ff] text-white text-xs font-semibold hover:bg-[#0f64d8] transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {pwBusy ? "Updating…" : "Update Password"}
            </button>
          </form>
        </div>

        {/* Sign out */}
        <div className="bg-white border border-[#dfe4eb] rounded-2xl p-5 shadow-2xs">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold text-[#1a1a1c]">Sign Out</h3>
              <p className="text-[11px] text-[#868c98] mt-0.5">
                Clears this machine's session and relay credentials.
              </p>
            </div>
            <button
              onClick={() => {
                soundEngine.playTick();
                logout();
              }}
              className="px-4 py-2 rounded-lg border border-[#ffb9a2] text-[#e11d48] text-xs font-semibold hover:bg-[#fff1f2] transition-colors cursor-pointer flex items-center gap-1.5 shrink-0"
            >
              <LogOut className="size-3.5" />
              Sign Out
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
