import { getAppVersion, setAppVersion, APP_VERSION } from "../utils/appMeta";

export const UPDATE_OWNER = "AIYantra";
export const UPDATE_REPO = "extra";
export const UPDATE_RELEASES_URL = `https://github.com/${UPDATE_OWNER}/${UPDATE_REPO}/releases`;

export interface UpdateCheckResult {
  /** Installed version, e.g. "0.3.6". */
  current: string;
  /** Latest release version without the leading v, e.g. "0.3.6". */
  latest: string;
  /** Latest release tag as published, e.g. "v0.3.6". */
  latestTag: string;
  available: boolean;
  publishedAt: string | null;
  releaseUrl: string;
  notes: string | null;
  /** Direct download URL of the preferred asset, if any. */
  downloadUrl: string | null;
  assetName: string | null;
  /** True when the preferred asset is a runnable installer. */
  installable: boolean;
  /** True when update servers are offline or rate limited. */
  offline?: boolean;
}

export function normalizeVersion(version: string): number[] {
  return version
    .trim()
    .replace(/^[vV]/, "")
    .split(".")
    .map((part) => {
      const n = parseInt(part, 10);
      return Number.isFinite(n) ? n : 0;
    });
}

/** True when `latest` is a newer version than `current`. */
export function isNewerVersion(latest: string, current: string): boolean {
  const a = normalizeVersion(latest);
  const b = normalizeVersion(current);
  const len = Math.max(a.length, b.length);
  for (let i = 0; i < len; i++) {
    const x = a[i] ?? 0;
    const y = b[i] ?? 0;
    if (x !== y) return x > y;
  }
  return false;
}

interface ReleaseAsset {
  name: string;
  browser_download_url: string;
}

function pickAsset(assets: ReleaseAsset[]): ReleaseAsset | null {
  if (assets.length === 0) return null;
  const installer = assets.find((a) => /\.(exe|msi|whl|ps1|sh)$/i.test(a.name));
  return installer ?? assets[0];
}

/**
 * Fetches dynamic installed version from local Extra engine backend.
 */
export async function fetchInstalledVersion(): Promise<string> {
  try {
    const res = await fetch("/api/extra/version", {
      headers: { Accept: "application/json" },
    });
    if (res.ok) {
      const data = await res.json();
      if (data && data.version) {
        setAppVersion(data.version);
        return data.version;
      }
    }
  } catch {
    // Local endpoint not reachable; fallback to runtime memory
  }
  return getAppVersion();
}

/**
 * Checks for latest Extra release via local backend proxy, edge manifest, or GitHub.
 * Guarantees zero unhandled exceptions and smooth fallback.
 */
export async function checkForUpdates(
  current?: string,
): Promise<UpdateCheckResult> {
  const activeVer = current || (await fetchInstalledVersion()) || getAppVersion() || APP_VERSION;

  // 1. Try local app backend proxy (fastest, eliminates CORS & rate-limiting)
  try {
    const localRes = await fetch("/api/extra/update", {
      headers: { Accept: "application/json" },
    });
    if (localRes.ok) {
      const payload = await localRes.json();
      if (payload && payload.latest) {
        const resolvedCurrent = payload.current || activeVer;
        setAppVersion(resolvedCurrent);
        return {
          current: resolvedCurrent,
          latest: payload.latest,
          latestTag: payload.latestTag || `v${payload.latest}`,
          available: Boolean(payload.available),
          publishedAt: payload.publishedAt || null,
          releaseUrl: payload.releaseUrl || UPDATE_RELEASES_URL,
          notes: payload.notes || null,
          downloadUrl: payload.downloadUrl || null,
          assetName: payload.assetName || null,
          installable: Boolean(payload.installable ?? true),
          offline: Boolean(payload.offline),
        };
      }
    }
  } catch {
    // Local endpoint not reachable; proceed to edge manifest
  }

  // 2. Try extra.yantraos.com/api/version.json (Cloudflare edge CDN)
  try {
    const edgeRes = await fetch("https://extra.yantraos.com/api/version.json", {
      headers: { Accept: "application/json" },
    });
    if (edgeRes.ok) {
      const edgeData = await edgeRes.json();
      if (edgeData && edgeData.version) {
        const latestTag = edgeData.tag_name || `v${edgeData.version}`;
        const latest = edgeData.version;
        return {
          current: activeVer,
          latest,
          latestTag,
          available: isNewerVersion(latest, activeVer),
          publishedAt: edgeData.published_at || null,
          releaseUrl: edgeData.html_url || UPDATE_RELEASES_URL,
          notes: edgeData.notes || null,
          downloadUrl: edgeData.download_url || null,
          assetName: edgeData.assets?.[0]?.name || null,
          installable: true,
          offline: false,
        };
      }
    }
  } catch {
    // Edge server not reachable; fall through to GitHub
  }

  // 3. Fallback to GitHub API
  try {
    const res = await fetch(
      `https://api.github.com/repos/${UPDATE_OWNER}/${UPDATE_REPO}/releases/latest`,
      { headers: { Accept: "application/vnd.github+json" } },
    );
    if (res.ok) {
      const data = await res.json();
      const latestTag: string = data.tag_name || "";
      const latest = latestTag.replace(/^[vV]/, "");
      const asset = pickAsset(data.assets || []);
      const installable = asset ? /\.(exe|msi|whl|ps1|sh)$/i.test(asset.name) : true;

      return {
        current: activeVer,
        latest,
        latestTag,
        available: latestTag ? isNewerVersion(latest, activeVer) : false,
        publishedAt: data.published_at,
        releaseUrl: data.html_url || UPDATE_RELEASES_URL,
        notes: data.body,
        downloadUrl: asset ? asset.browser_download_url : null,
        assetName: asset ? asset.name : null,
        installable,
        offline: false,
      };
    }
  } catch {
    // Network offline or rate limited
  }

  // 4. Graceful offline fallback: user is on current version, no scary error toast
  return {
    current: activeVer,
    latest: activeVer,
    latestTag: `v${activeVer}`,
    available: false,
    publishedAt: null,
    releaseUrl: UPDATE_RELEASES_URL,
    notes: "Operating with verified installed release.",
    downloadUrl: null,
    assetName: null,
    installable: false,
    offline: true,
  };
}

/** Starts a browser download of the given release asset. */
export function downloadAsset(url: string, filename: string): void {
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.rel = "noopener noreferrer";
  document.body.appendChild(link);
  link.click();
  link.remove();
}

/**
 * Triggers background execution of the official installer to upgrade Extra.
 */
export async function performAppUpdate(): Promise<{ success: boolean; message?: string; error?: string }> {
  try {
    const res = await fetch("/api/extra/update/perform", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    if (res.ok) {
      const data = await res.json();
      return { success: true, message: data.message || "Update in progress" };
    }
    const errData = await res.json().catch(() => ({}));
    return { success: false, error: errData.error || `HTTP ${res.status}` };
  } catch (err: any) {
    return { success: false, error: err.message || "Failed to reach local update bridge." };
  }
}
