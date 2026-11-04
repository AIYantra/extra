import { APP_VERSION, RELAY_HOST } from "../utils/appMeta";

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
  const installer = assets.find((a) => /\.(exe|msi)$/i.test(a.name));
  return installer ?? assets[0];
}

/**
 * Asks GitHub for the latest Extra release and compares it with the
 * installed version. Throws a plain-language error when offline.
 */
export async function checkForUpdates(
  current: string = APP_VERSION,
): Promise<UpdateCheckResult> {
  let data: {
    tag_name: string;
    html_url: string;
    published_at: string | null;
    body: string | null;
    assets: ReleaseAsset[];
  };
  try {
    const res = await fetch(
      `https://api.github.com/repos/${UPDATE_OWNER}/${UPDATE_REPO}/releases/latest`,
      { headers: { Accept: "application/vnd.github+json" } },
    );
    if (!res.ok) {
      throw new Error(`GitHub answered ${res.status}`);
    }
    data = await res.json();
  } catch {
    throw new Error(
      `Couldn't reach the update server. Check your connection and try again. Relay host: ${RELAY_HOST}.`,
    );
  }

  const latestTag: string = data.tag_name || "";
  const latest = latestTag.replace(/^[vV]/, "");
  const asset = pickAsset(data.assets || []);
  const installable = asset ? /\.(exe|msi)$/i.test(asset.name) : false;

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
