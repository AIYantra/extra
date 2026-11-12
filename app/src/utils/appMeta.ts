/**
 * Single source of truth for product identity strings.
 * Version is dynamically synchronized with the local Extra engine runtime.
 */
export const DEFAULT_APP_VERSION = "0.3.6";
export const DEFAULT_APP_VERSION_LABEL = `v${DEFAULT_APP_VERSION}`;

let _runtimeVersion = DEFAULT_APP_VERSION;

export function getAppVersion(): string {
  return _runtimeVersion;
}

export function getAppVersionLabel(): string {
  return `v${_runtimeVersion}`;
}

export function setAppVersion(newVersion: string): void {
  if (!newVersion) return;
  _runtimeVersion = newVersion.trim().replace(/^[vV]/, "");
}

export const APP_VERSION = DEFAULT_APP_VERSION;
export const APP_VERSION_LABEL = DEFAULT_APP_VERSION_LABEL;
export const PRODUCT_NAME = "Extra";
export const PRODUCT_BYLINE = "by YantraOS";
export const RELAY_HOST = "extra.yantraos.com";
