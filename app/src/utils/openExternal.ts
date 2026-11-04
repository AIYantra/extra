/**
 * Opens a URL in the user's system browser.
 * Prefers the local daemon (same mechanism as sign-in) so links leave
 * the app window; falls back to a new browser tab otherwise.
 */
export async function openExternal(url: string): Promise<void> {
  try {
    const res = await fetch("/api/extra/open-browser", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    }).catch(() => null);
    if (res && res.ok) return;
  } catch {
    /* fall through to window.open */
  }
  window.open(url, "_blank", "noopener,noreferrer");
}
