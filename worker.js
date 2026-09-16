/**
 * Cloudflare Worker Edge Router for extra.yantraos.com
 * Handles adaptive OS script delivery for universal curl/irm one-liners
 */

const GITHUB_RAW_BASE = "https://raw.githubusercontent.com/AIYantra/extra/main";

const SCRIPT_MAP = {
  "/install.sh": `${GITHUB_RAW_BASE}/install.sh`,
  "/install.ps1": `${GITHUB_RAW_BASE}/install.ps1`,
  "/extra_automation_macos.md": `${GITHUB_RAW_BASE}/rules/extra_automation_macos.md`,
  "/extra_automation.md": `${GITHUB_RAW_BASE}/rules/extra_automation.md`,
  "/STARTER_PROMPT_MACOS.md": `${GITHUB_RAW_BASE}/STARTER_PROMPT_MACOS.md`,
  "/STARTER_PROMPT.md": `${GITHUB_RAW_BASE}/STARTER_PROMPT.md`,
};

function isMacOrUnixUserAgent(userAgent) {
  const ua = (userAgent || "").toLowerCase();
  return (
    ua.includes("curl") ||
    ua.includes("wget") ||
    ua.includes("darwin") ||
    ua.includes("macintosh") ||
    ua.includes("mac os") ||
    ua.includes("linux") ||
    ua.includes("bsd")
  );
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const userAgent = (request.headers.get("user-agent") || "").toLowerCase();

    // Route 1 & 2: Direct script & rule requests
    if (SCRIPT_MAP[url.pathname]) {
      const upstreamRes = await fetch(SCRIPT_MAP[url.pathname]);
      const headers = new Headers(upstreamRes.headers);
      headers.set("Content-Type", "text/plain; charset=utf-8");
      headers.set("Cache-Control", "public, max-age=60, s-maxage=300");
      headers.set("X-Content-Type-Options", "nosniff");
      return new Response(upstreamRes.body, {
        status: upstreamRes.status,
        headers,
      });
    }

    // Route 3: Universal CLI one-liner: curl -sSL https://extra.yantraos.com/install | bash
    if (url.pathname === "/install") {
      const targetScript = isMacOrUnixUserAgent(userAgent) ? "/install.sh" : "/install.ps1";
      const upstreamRes = await fetch(SCRIPT_MAP[targetScript]);
      const headers = new Headers(upstreamRes.headers);
      headers.set("Content-Type", "text/plain; charset=utf-8");
      headers.set("Cache-Control", "public, max-age=60, s-maxage=300");
      headers.set("X-Content-Type-Options", "nosniff");
      return new Response(upstreamRes.body, {
        status: upstreamRes.status,
        headers,
      });
    }

    // Route 4: Web Browser UI / Assets fallback to origin
    return fetch(request);
  },
};
