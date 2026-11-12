import { useState, useEffect } from "react";
import {
  Info,
  ShieldCheck,
  FileText,
  RefreshCw,
  Monitor,
  Server,
  Globe,
  ExternalLink,
  Download,
  Sparkles,
} from "lucide-react";
import { Switch } from "../ui/switch";
import {
  APP_VERSION_LABEL,
  PRODUCT_BYLINE,
  RELAY_HOST,
} from "../../utils/appMeta";
import { openExternal } from "../../utils/openExternal";
import {
  UPDATE_RELEASES_URL,
  downloadAsset,
} from "../../services/updateService";
import { useUpdateStore } from "../../store/useUpdateStore";

type AboutTab = "about" | "privacy" | "terms" | "updates";

const TABS: { id: AboutTab; label: string; icon: typeof Info }[] = [
  { id: "about", label: "About", icon: Info },
  { id: "privacy", label: "Privacy", icon: ShieldCheck },
  { id: "terms", label: "Terms", icon: FileText },
  { id: "updates", label: "Updates", icon: RefreshCw },
];

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-xl border border-[#dfe4eb] bg-white">
      <h3 className="border-b border-[#dfe4eb] px-5 py-3 text-xs font-semibold text-[#1a1a1c]">
        {title}
      </h3>
      <div className="space-y-3 px-5 py-4 text-xs leading-relaxed text-[#525866]">
        {children}
      </div>
    </section>
  );
}

export const PRIVACY_URL = `https://${RELAY_HOST}/privacy`;
export const TERMS_URL = `https://${RELAY_HOST}/terms`;

function WebsiteLink({ href, label }: { href: string; label: string }) {
  return (
    <button
      type="button"
      onClick={() => void openExternal(href)}
      className="inline-flex cursor-pointer items-center gap-1 text-xs font-medium text-[#1677ff] transition-colors ease-[cubic-bezier(0.22,1,0.36,1)] hover:underline"
    >
      {label}
      <ExternalLink className="size-3.5" strokeWidth={1.5} />
    </button>
  );
}

function formatCheckedAt(ts: number | null): string {
  if (!ts) return "Never checked";
  return `Last checked ${new Date(ts).toLocaleString()}`;
}

function UpdatesTab() {
  const {
    installedVersionLabel,
    autoCheck,
    autoUpdate,
    lastCheckedAt,
    latestTag,
    updateAvailable,
    checking,
    updating,
    error,
    lastResult,
    setAutoCheck,
    setAutoUpdate,
    syncInstalledVersion,
    checkNow,
    performUpdateNow,
  } = useUpdateStore();

  useEffect(() => {
    void syncInstalledVersion();
  }, [syncInstalledVersion]);

  const activeLabel = installedVersionLabel || APP_VERSION_LABEL;

  return (
    <div className="space-y-4">
      <Section title="Installed">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <span className="font-medium text-[#1a1a1c]">
              Extra {PRODUCT_BYLINE}
            </span>
            <span className="font-mono text-[11px] tabular-nums text-[#525866]">
              {activeLabel} local
            </span>
          </div>
          <button
            type="button"
            onClick={() => void checkNow()}
            disabled={checking || updating}
            className="flex h-9 cursor-pointer items-center gap-2 rounded-[10px] bg-[#1677ff] px-4 text-xs font-medium text-white transition-colors ease-[cubic-bezier(0.22,1,0.36,1)] hover:bg-[#0958d9] disabled:opacity-50"
          >
            {checking ? (
              <>
                <RefreshCw
                  className="size-4 animate-spin"
                  strokeWidth={1.5}
                />
                Checking
              </>
            ) : (
              <>
                <RefreshCw className="size-4" strokeWidth={1.5} />
                Check for updates
              </>
            )}
          </button>
        </div>
        <p className="font-mono text-[11px] tabular-nums text-[#868c98]">
          {formatCheckedAt(lastCheckedAt)}
        </p>
        {error && <p className="text-xs text-[#e11d48]">{error}</p>}
        {!error && lastCheckedAt && !updateAvailable && (
          <p className="text-xs text-[#525866]">
            You&apos;re up to date on {activeLabel}.
          </p>
        )}
      </Section>

      {updateAvailable && latestTag && (
        <section className="rounded-xl border border-[#bbf0cf] bg-[#edfcf2]">
          <h3 className="border-b border-[#bbf0cf] px-5 py-3 text-xs font-semibold text-[#0e8345]">
            Update available
          </h3>
          <div className="space-y-3 px-5 py-4 text-xs leading-relaxed text-[#0e8345]">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p>
                <span className="font-mono font-medium tabular-nums">
                  {latestTag}
                </span>{" "}
                is out. Installed {activeLabel}.
              </p>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => void performUpdateNow()}
                  disabled={updating}
                  className="flex h-9 cursor-pointer items-center gap-2 rounded-[10px] bg-[#0e8345] px-4 text-xs font-medium text-white transition-colors ease-[cubic-bezier(0.22,1,0.36,1)] hover:bg-[#0b6b37] disabled:opacity-50"
                >
                  {updating ? (
                    <>
                      <RefreshCw className="size-4 animate-spin" strokeWidth={1.5} />
                      Updating...
                    </>
                  ) : (
                    <>
                      <Sparkles className="size-4" strokeWidth={1.5} />
                      Update Now
                    </>
                  )}
                </button>
                {lastResult?.downloadUrl && lastResult.assetName && (
                  <button
                    type="button"
                    onClick={() =>
                      downloadAsset(
                        lastResult.downloadUrl as string,
                        lastResult.assetName as string,
                      )
                    }
                    className="flex h-9 cursor-pointer items-center gap-2 rounded-[10px] border border-[#bbf0cf] bg-white px-3 text-xs font-medium text-[#0e8345] transition-colors ease-[cubic-bezier(0.22,1,0.36,1)] hover:bg-[#f4f5f8]"
                  >
                    <Download className="size-3.5" strokeWidth={1.5} />
                    Download
                  </button>
                )}
                {lastResult && (
                  <button
                    type="button"
                    onClick={() => void openExternal(lastResult.releaseUrl)}
                    className="flex h-9 cursor-pointer items-center gap-2 rounded-[10px] border border-[#bbf0cf] bg-white px-3 text-xs font-medium text-[#0e8345] transition-colors ease-[cubic-bezier(0.22,1,0.36,1)] hover:bg-[#f4f5f8]"
                  >
                    View release
                    <ExternalLink className="size-3.5" strokeWidth={1.5} />
                  </button>
                )}
              </div>
            </div>
            {lastResult?.publishedAt && (
              <p className="font-mono text-[11px] tabular-nums">
                Published{" "}
                {new Date(lastResult.publishedAt).toLocaleDateString()}
              </p>
            )}
          </div>
        </section>
      )}

      <Section title="Automatic updates">
        <div className="flex items-center justify-between gap-3 py-1">
          <div>
            <p className="font-medium text-[#1a1a1c]">Check automatically</p>
            <p className="mt-0.5 text-[11px] text-[#525866]">
              Look for new releases every few hours and notify you.
            </p>
          </div>
          <Switch
            checked={autoCheck}
            onCheckedChange={setAutoCheck}
            aria-label="Check for updates automatically"
          />
        </div>
        <div className="flex items-center justify-between gap-3 border-t border-[#dfe4eb] py-1 pt-3">
          <div>
            <p className="font-medium text-[#1a1a1c]">
              Download updates automatically
            </p>
            <p className="mt-0.5 text-[11px] text-[#525866]">
              Fetch the installer as soon as one is available.
            </p>
          </div>
          <Switch
            checked={autoUpdate}
            onCheckedChange={setAutoUpdate}
            aria-label="Download updates automatically"
          />
        </div>
      </Section>

      <Section title="Release history">
        <div className="space-y-4">
          <div>
            <div className="flex items-center justify-between gap-3">
              <p className="font-medium text-[#1a1a1c]">v0.3.6</p>
              <p className="font-mono text-[11px] tabular-nums text-[#868c98]">
                2026-11-12
              </p>
            </div>
            <p className="mt-1">
              Dynamic App Versioning, In-App Self-Updating Engine, Windows 11 Smart App Control (SAC) Signed Runtime &amp; macOS Gatekeeper Quarantine Stripping.
            </p>
            <div className="mt-2 flex flex-wrap items-center gap-4">
              <WebsiteLink
                href="https://github.com/AIYantra/extra/compare/v0.3.5...v0.3.6"
                label="Full changelog"
              />
              <WebsiteLink href={UPDATE_RELEASES_URL} label="All releases" />
            </div>
          </div>
          <div className="border-t border-[#dfe4eb] pt-3">
            <div className="flex items-center justify-between gap-3">
              <p className="font-medium text-[#1a1a1c]">v0.3.5</p>
              <p className="font-mono text-[11px] tabular-nums text-[#868c98]">
                2026-11-07
              </p>
            </div>
            <p className="mt-1">
              Cloudflare Worker MCP Stream Fix, OpenAI DestructiveHint Compliance &amp; 1-Turn Live-Browser Form Fill.
            </p>
          </div>
        </div>
      </Section>
    </div>
  );
}

export function AboutView() {
  const [tab, setTab] = useState<AboutTab>("about");
  const installedVersionLabel = useUpdateStore((s) => s.installedVersionLabel) || APP_VERSION_LABEL;

  return (
    <div className="max-w-4xl space-y-6 pb-16 animate-in fade-in duration-150">
      <div className="flex flex-col gap-3 border-b border-[#dfe4eb] pb-4 sm:flex-row sm:items-center sm:justify-between select-none">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-[#1a1a1c]">
              About Extra
            </h2>
            <span className="rounded-md border border-[#dfe4eb] bg-[#f0f2f6] px-1.5 py-0.5 font-mono text-[10px] text-[#525866]">
              {installedVersionLabel} local
            </span>
          </div>
          <p className="mt-0.5 text-xs text-[#525866]">
            Extra {PRODUCT_BYLINE}. What it is, how it handles your data, and
            what changed.
          </p>
        </div>
        <div className="flex flex-wrap gap-1 rounded-xl border border-[#dfe4eb] bg-[#f0f2f6] p-1">
          {TABS.map(({ id, label }) => (
            <button
              key={id}
              type="button"
              onClick={() => setTab(id)}
              className={`h-8 cursor-pointer rounded-lg px-3 text-xs font-medium transition-colors ease-[cubic-bezier(0.22,1,0.36,1)] ${
                tab === id
                  ? "bg-white text-[#1a1a1c] shadow-xs"
                  : "text-[#525866] hover:text-[#1a1a1c]"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {tab === "about" && (
        <div className="space-y-4">
          <Section title="What Extra does">
            <p>
              Extra is a desktop station that operates your computer&apos;s
              apps for you. A local engine on this machine
              <span className="font-mono text-[11px] text-[#1a1a1c]">
                {" "}
                127.0.0.1:8000
              </span>{" "}
              carries out each step, and an optional cloud relay at
              <span className="font-mono text-[11px] text-[#1a1a1c]">
                {" "}
                {RELAY_HOST}
              </span>{" "}
              links this computer to your account when you sign in.
            </p>
            <p>
              You can also skip sign-in entirely. In local mode everything
              runs on this computer and no account is needed.
            </p>
          </Section>

          <Section title="This installation">
            <div className="divide-y divide-[#dfe4eb]">
              {[
                {
                  icon: Monitor,
                  name: "App",
                  value: `${APP_VERSION_LABEL} local`,
                },
                {
                  icon: Server,
                  name: "Engine",
                  value: "Local loopback · 127.0.0.1:8000",
                },
                { icon: Globe, name: "Relay", value: RELAY_HOST },
              ].map(({ icon: Icon, name, value }) => (
                <div
                  key={name}
                  className="flex items-center justify-between gap-3 py-2.5 first:pt-0 last:pb-0"
                >
                  <span className="flex items-center gap-2 font-medium text-[#1a1a1c]">
                    <Icon
                      className="size-4 text-[#525866]"
                      strokeWidth={1.5}
                    />
                    {name}
                  </span>
                  <span className="font-mono text-[11px] tabular-nums text-[#525866]">
                    {value}
                  </span>
                </div>
              ))}
            </div>
          </Section>
        </div>
      )}

      {tab === "privacy" && (
        <div className="space-y-4">
          <Section title="Stays on this computer">
            <p>
              Your sign-in credential is stored encrypted with Windows
              encryption on this machine. In local mode there is no account,
              so there is nothing to send anywhere.
            </p>
          </Section>
          <Section title="Only when you sign in">
            <p>
              Signing in links this computer to your Extra Cloud account so
              it appears in your device fleet. That link, and the relay
              passkey shown after sign-in, exist only for signed-in
              computers.
            </p>
          </Section>
          <Section title="Built to work offline">
            <p>
              Local mode runs the full station with no network needed. Cloud
              features such as browser sign-in and relay sync are used only
              when you choose them.
            </p>
            <WebsiteLink
              href={PRIVACY_URL}
              label="Read the full policy on extra.yantraos.com"
            />
          </Section>
        </div>
      )}

      {tab === "terms" && (
        <div className="space-y-4">
          <Section title="Terms of use">
            <p>
              Extra operates apps on your own computer at your direction.
              Review each action before you approve it. You are responsible
              for what you ask Extra to do on your machine.
            </p>
            <p>
              Local mode needs the local engine running on this computer.
              Signed-in features need an internet connection and an Extra
              Cloud account.
            </p>
            <p>
              We may update these terms alongside app updates. The version
              history lives under Updates on this page.
            </p>
            <WebsiteLink
              href={TERMS_URL}
              label="Read the full terms on extra.yantraos.com"
            />
          </Section>
        </div>
      )}

      {tab === "updates" && <UpdatesTab />}
    </div>
  );
}
