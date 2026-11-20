import { useState } from "react";
import {
  Info,
  RefreshCw,
  Monitor,
  Server,
  Globe,
  ExternalLink,
} from "lucide-react";
import {
  APP_VERSION_LABEL,
  PRODUCT_BYLINE,
  RELAY_HOST,
} from "../../utils/appMeta";
import { openExternal } from "../../utils/openExternal";
import {
  UPDATE_RELEASES_URL,
} from "../../services/updateService";
import { useUpdateStore } from "../../store/useUpdateStore";
import { SoftwareUpdateCard } from "./SoftwareUpdateCard";

type AboutTab = "about" | "updates";

const TABS: { id: AboutTab; label: string; icon: typeof Info }[] = [
  { id: "about", label: "Overview", icon: Info },
  { id: "updates", label: "Software Updates", icon: RefreshCw },
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

function UpdatesTab() {
  return (
    <div className="space-y-4">
      <SoftwareUpdateCard />

      <Section title="Release history">
        <div className="space-y-4">
          <div>
            <div className="flex items-center justify-between gap-3">
              <p className="font-medium text-[#1a1a1c]">v0.3.7</p>
              <p className="font-mono text-[11px] tabular-nums text-[#868c98]">
                2026-11-20
              </p>
            </div>
            <p className="mt-1">
              Multi-Phase Security Hardening, Strict Cloud Relay Air-Gap Isolation, Workspace Filesystem Containment &amp; RFC 7636 PKCE Edge OAuth Defense.
            </p>
            <div className="mt-2 flex flex-wrap items-center gap-4">
              <WebsiteLink
                href="https://github.com/AIYantra/extra/compare/v0.3.6...v0.3.7"
                label="Full changelog"
              />
              <WebsiteLink href={UPDATE_RELEASES_URL} label="All releases" />
            </div>
          </div>
          <div className="border-t border-[#dfe4eb] pt-3">
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

interface AboutViewProps {
  defaultTab?: AboutTab;
}

export function AboutView({ defaultTab = "about" }: AboutViewProps = {}) {
  const [tab, setTab] = useState<AboutTab>(defaultTab);
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

          <Section title="Data Sovereignty & Local Processing">
            <p>
              Extra operates 100% locally on your machine. Screen captures, hardware keyboard keystrokes, and mission execution traces never leave your device unless you explicitly connect Cloud Relay. All telemetry is sovereign to <code className="font-mono text-[11px] bg-[#f0f2f6] px-1 py-0.5 rounded text-[#1a1a1c]">~/.extra</code>.
            </p>
            <div className="flex flex-wrap items-center gap-4 pt-2 border-t border-[#dfe4eb]">
              <WebsiteLink
                href={PRIVACY_URL}
                label="Privacy Policy"
              />
              <WebsiteLink
                href={TERMS_URL}
                label="Terms of Service"
              />
            </div>
          </Section>
        </div>
      )}

      {tab === "updates" && <UpdatesTab />}
    </div>
  );
}
