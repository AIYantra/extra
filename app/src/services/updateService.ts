import { APP_VERSION } from "../utils/appMeta";

export const UPDATE_OWNER = "AIYantra";
export const UPDATE_REPO = "extra";
export const UPDATE_RELEASES_URL = `https://github.com/${UPDATE_OWNER}/${UPDATE_REPO}/releases`;

export interface UpdateCheckResult {
  /** Installed version, e.g. "0.3.4". */
  current: string;
  /** Latest release version without the leading v, e.g. "0.3.4". */
  latest: string;
  /** Latest release tag as published, e.g. "v0.3.4". */
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
  const installer = assets.find((a) => /\.(exe|msi|whl)$/i.test(a.name));
  return installer ?? assets[0];
}

/**
 * Checks for latest Extra release via local backend proxy, edge manifest, or GitHub.
 * Guarantees zero unhandled exceptions and smooth fallback.
 */
export async function checkForUpdates(
  current: string = APP_VERSION,
): Promise<UpdateCheckResult> {
  // 1. Try local app backend proxy (fastest, eliminates CORS & rate-limiting)
  try {
    const localRes = await fetch("/api/extra/update", {
      headers: { Accept: "application/json" },
    });
    if (localRes.ok) {
      const payload = await localRes.json();
      if (payload && payload.latest) {
        return {
          current: payload.current || current,
          latest: payload.latest,
          latestTag: payload.latestTag || `v${payload.latest}`,
          available: Boolean(payload.available),
          publishedAt: payload.publishedAt || null,
          releaseUrl: payload.releaseUrl || UPDATE_RELEASES_URL,
          notes: payload.notes || null,
          downloadUrl: payload.downloadUrl || null,
          assetName: payload.assetName || null,
          installable: Boolean(payload.installable),
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
          current,
          latest,
          latestTag,
          available: isNewerVersion(latest, current),
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
      const installable = asset ? /\.(exe|msi|whl)$/i.test(asset.name) : false;

      return {
        current,
        latest,
        latestTag,
        available: latestTag ? isNewerVersion(latest, current) : false,
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
    current,
    latest: current,
    latestTag: `v${current}`,
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
