/**
 * Cloudflare Worker Edge Router for extra.yantraos.com
 * Handles:
 * 1. Adaptive OS script delivery for universal curl/irm one-liners (Linux, macOS, Windows)
 * 2. Anonymous installation success beacon ingestion (/api/install-success)
 * 3. Privacy-preserving fleet telemetry & first-run activation (/api/telemetry)
 * 4. Health & diagnostic API (/api/health)
 */

const GITHUB_RAW_BASE = "https://raw.githubusercontent.com/AIYantra/extra/main";

const SCRIPT_MAP = {
  "/install.sh": `${GITHUB_RAW_BASE}/install.sh`,
  "/install.ps1": `${GITHUB_RAW_BASE}/install.ps1`,
  "/extra_automation_linux.md": `${GITHUB_RAW_BASE}/rules/extra_automation_linux.md`,
  "/extra_automation_macos.md": `${GITHUB_RAW_BASE}/rules/extra_automation_macos.md`,
  "/extra_automation.md": `${GITHUB_RAW_BASE}/rules/extra_automation.md`,
  "/STARTER_PROMPT_LINUX.md": `${GITHUB_RAW_BASE}/STARTER_PROMPT_LINUX.md`,
  "/STARTER_PROMPT_MACOS.md": `${GITHUB_RAW_BASE}/STARTER_PROMPT_MACOS.md`,
  "/STARTER_PROMPT.md": `${GITHUB_RAW_BASE}/STARTER_PROMPT.md`,
};

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, User-Agent, Authorization",
  "Access-Control-Max-Age": "86400",
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

    const AWS_MCP_HUB_ORIGIN = env && env.AWS_MCP_HUB_ORIGIN ? env.AWS_MCP_HUB_ORIGIN : "https://nfmcn307n7.execute-api.ap-south-1.amazonaws.com";

    // Route OpenAI Domain Verification Challenge
    if (url.pathname === "/.well-known/openai-apps-challenge") {
      return new Response("F58MIaoD5s33CTGsLkyWNSdZf0KVl-UY1h4JPyWrt8o", {
        status: 200,
        headers: {
          "Content-Type": "text/plain; charset=utf-8",
          "Access-Control-Allow-Origin": "*",
          "Cache-Control": "public, max-age=0, must-revalidate",
        },
      });
    }

    // Route RFC 8414 & OpenID Connect Discovery (for ChatGPT Custom MCP Server OAuth Discovery)
    if (
      url.pathname === "/.well-known/oauth-authorization-server" ||
      url.pathname === "/.well-known/openid-configuration"
    ) {
      const oauthMetadata = {
        issuer: "https://extra.yantraos.com",
        authorization_endpoint: "https://extra.yantraos.com/oauth/authorize",
        token_endpoint: "https://extra.yantraos.com/oauth/token",
        registration_endpoint: "https://extra.yantraos.com/oauth/register",
        token_endpoint_auth_methods_supported: ["client_secret_post", "client_secret_basic", "none"],
        response_types_supported: ["code"],
        grant_types_supported: ["authorization_code", "refresh_token"],
        code_challenge_methods_supported: ["S256", "plain"],
        scopes_supported: ["mcp", "offline_access"]
      };
      return new Response(JSON.stringify(oauthMetadata), {
        status: 200,
        headers: {
          "Content-Type": "application/json; charset=utf-8",
          ...CORS_HEADERS,
          "Cache-Control": "public, max-age=3600",
        },
      });
    }

    if (url.pathname === "/.well-known/oauth-protected-resource") {
      return new Response(JSON.stringify({
        resource: "https://extra.yantraos.com/mcp",
        authorization_servers: ["https://extra.yantraos.com"],
        scopes_supported: ["mcp"]
      }), {
        status: 200,
        headers: {
          "Content-Type": "application/json; charset=utf-8",
          ...CORS_HEADERS,
          "Cache-Control": "public, max-age=3600",
        },
      });
    }

    // Route RFC 7591 Dynamic Client Registration (for Google Gemini & OAuth 2.1 Clients)
    if (url.pathname === "/oauth/register") {
      if (request.method === "POST") {
        let clientMeta = {};
        try {
          clientMeta = await request.json();
        } catch (_) {
          clientMeta = {};
        }

        const clientId = "gemini_" + crypto.randomUUID().replace(/-/g, "").substring(0, 16);
        const clientSecret = "sec_" + crypto.randomUUID().replace(/-/g, "");
        const issuedAt = Math.floor(Date.now() / 1000);

        const redirectUris = Array.isArray(clientMeta.redirect_uris) && clientMeta.redirect_uris.length > 0
          ? clientMeta.redirect_uris
          : ["https://vertexaisearch.cloud.google.com/oauth-redirect"];

        const regRecord = {
          client_id: clientId,
          client_secret: clientSecret,
          client_id_issued_at: issuedAt,
          client_secret_expires_at: 0,
          client_name: clientMeta.client_name || "Google Gemini Connector",
          redirect_uris: redirectUris,
          grant_types: clientMeta.grant_types || ["authorization_code", "refresh_token"],
          response_types: clientMeta.response_types || ["code"],
          token_endpoint_auth_method: clientMeta.token_endpoint_auth_method || "client_secret_post",
          scope: "mcp offline_access"
        };

        if (env && env.TELEMETRY_KV) {
          try {
            await env.TELEMETRY_KV.put(`oauth_client:${clientId}`, JSON.stringify(regRecord), { expirationTtl: 86400 * 90 });
          } catch (_) {}
        }

        return new Response(JSON.stringify(regRecord), {
          status: 201,
          headers: {
            "Content-Type": "application/json; charset=utf-8",
            ...CORS_HEADERS,
            "Cache-Control": "no-store",
            "Pragma": "no-cache",
          },
        });
      }

      if (request.method === "GET") {
        return new Response(JSON.stringify({
          status: "ready",
          service: "OAuth 2.0 Dynamic Client Registration",
          spec: "RFC 7591",
        }), {
          status: 200,
          headers: {
            "Content-Type": "application/json; charset=utf-8",
            ...CORS_HEADERS,
          },
        });
      }
    }

    // Route RFC 6749 OAuth 2.0 Authorization Endpoint (for Google Gemini & Web MCP Connectors)
    if (url.pathname === "/oauth/authorize") {
      const clientId = url.searchParams.get("client_id") || "";
      const redirectUri = url.searchParams.get("redirect_uri") || "";
      const state = url.searchParams.get("state") || "";
      const codeChallenge = url.searchParams.get("code_challenge") || "";
      const codeChallengeMethod = url.searchParams.get("code_challenge_method") || "S256";

      const cookieHeader = request.headers.get("Cookie") || "";
      const cookieMatch = cookieHeader.match(/extra_device_key=([^;]+)/);
      const savedKey = cookieMatch ? decodeURIComponent(cookieMatch[1]) : "";
      const queryKey = (url.searchParams.get("key") || url.searchParams.get("relay_key") || "").trim();

      // POST: Form submission from the pairing UI
      if (request.method === "POST") {
        let submittedKey = "";
        let postClientId = clientId;
        let postRedirectUri = redirectUri;
        let postState = state;
        let postCodeChallenge = codeChallenge;
        let postCodeChallengeMethod = codeChallengeMethod;

        try {
          const contentType = request.headers.get("content-type") || "";
          if (contentType.includes("application/x-www-form-urlencoded") || contentType.includes("multipart/form-data")) {
            const formData = await request.formData();
            submittedKey = (formData.get("relay_key") || "").trim();
            postClientId = formData.get("client_id") || clientId;
            postRedirectUri = formData.get("redirect_uri") || redirectUri;
            postState = formData.get("state") || state;
            postCodeChallenge = formData.get("code_challenge") || codeChallenge;
            postCodeChallengeMethod = formData.get("code_challenge_method") || codeChallengeMethod;
          } else if (contentType.includes("application/json")) {
            const jsonBody = await request.json();
            submittedKey = (jsonBody.relay_key || "").trim();
            postClientId = jsonBody.client_id || clientId;
            postRedirectUri = jsonBody.redirect_uri || redirectUri;
            postState = jsonBody.state || state;
            postCodeChallenge = jsonBody.code_challenge || codeChallenge;
            postCodeChallengeMethod = jsonBody.code_challenge_method || codeChallengeMethod;
          }
        } catch (_) {}

        if (!submittedKey) {
          return new Response("Missing device setup key. Please enter a valid Extra relay key.", { status: 400 });
        }

        const authCode = "auth_" + crypto.randomUUID().replace(/-/g, "");
        const codeRecord = {
          relay_key: submittedKey,
          client_id: postClientId,
          redirect_uri: postRedirectUri,
          code_challenge: postCodeChallenge,
          code_challenge_method: postCodeChallengeMethod,
          created_at: Date.now(),
        };

        if (env && env.TELEMETRY_KV) {
          try {
            await env.TELEMETRY_KV.put(`oauth_code:${authCode}`, JSON.stringify(codeRecord), { expirationTtl: 600 });
          } catch (_) {}
        }

        const target = new URL(postRedirectUri || "https://vertexaisearch.cloud.google.com/oauth-redirect");
        target.searchParams.set("code", authCode);
        if (postState) target.searchParams.set("state", postState);

        return new Response(null, {
          status: 302,
          headers: {
            "Location": target.toString(),
            "Set-Cookie": `extra_device_key=${encodeURIComponent(submittedKey)}; Path=/; Max-Age=2592000; Secure; SameSite=Lax`,
          },
        });
      }

      // GET: Instant auto-approve if key is present in query string
      if (queryKey && redirectUri) {
        const authCode = "auth_" + crypto.randomUUID().replace(/-/g, "");
        const codeRecord = {
          relay_key: queryKey,
          client_id: clientId,
          redirect_uri: redirectUri,
          code_challenge: codeChallenge,
          code_challenge_method: codeChallengeMethod,
          created_at: Date.now(),
        };

        if (env && env.TELEMETRY_KV) {
          try {
            await env.TELEMETRY_KV.put(`oauth_code:${authCode}`, JSON.stringify(codeRecord), { expirationTtl: 600 });
          } catch (_) {}
        }

        const target = new URL(redirectUri);
        target.searchParams.set("code", authCode);
        if (state) target.searchParams.set("state", state);

        return new Response(null, {
          status: 302,
          headers: {
            "Location": target.toString(),
            "Set-Cookie": `extra_device_key=${encodeURIComponent(queryKey)}; Path=/; Max-Age=2592000; Secure; SameSite=Lax`,
          },
        });
      }

      // GET: Render clean, luminous consent & pairing UI matching extra.yantraos.com
      const cancelHref = redirectUri
        ? `${redirectUri}${redirectUri.includes('?') ? '&' : '?'}error=access_denied&error_description=User+cancelled+authorization${state ? '&state=' + encodeURIComponent(state) : ''}`
        : '#';

      const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Connect Extra to Google Gemini</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" href="/icon.png" type="image/png">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Inter+Tight:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-canvas: #f8fafc;
      --card-bg: rgba(255, 255, 255, 0.94);
      --card-border: rgba(223, 228, 235, 0.95);
      --text-main: #0f172a;
      --text-muted: #5e6573;
      --text-subtle: #8a92a3;
      --brand-blue: #0284c7;
      --stroke-light: #e2e8f0;
      --btn-dark: #0f172a;
      --btn-dark-hover: #1e293b;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: 'Inter Tight', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background-color: var(--bg-canvas);
      background-image: 
        radial-gradient(at 50% 0%, #e0edfd 0px, transparent 65%),
        radial-gradient(at 100% 100%, #f0f7ff 0px, transparent 55%),
        linear-gradient(to right, rgba(2, 132, 199, 0.04) 1px, transparent 1px),
        linear-gradient(to bottom, rgba(2, 132, 199, 0.04) 1px, transparent 1px);
      background-size: 100% 100%, 100% 100%, 32px 32px, 32px 32px;
      color: var(--text-main);
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      padding: 1.5rem;
      -webkit-font-smoothing: antialiased;
    }

    .card {
      background: var(--card-bg);
      backdrop-filter: blur(24px);
      -webkit-backdrop-filter: blur(24px);
      border: 1px solid var(--card-border);
      border-radius: 24px;
      padding: 2.25rem;
      width: 100%;
      max-width: 460px;
      box-shadow: 0 24px 50px -12px rgba(15, 23, 42, 0.09), 0 1px 3px rgba(15, 23, 42, 0.04);
    }

    .pair-row {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 1rem;
      margin-bottom: 1.25rem;
    }

    .avatar-box {
      width: 52px;
      height: 52px;
      border-radius: 14px;
      background: #ffffff;
      border: 1px solid var(--stroke-light);
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 4px 12px rgba(15, 23, 42, 0.04);
      padding: 8px;
    }

    .avatar-box img {
      width: 100%;
      height: 100%;
      object-fit: contain;
    }

    .bridge-connector {
      display: flex;
      align-items: center;
      position: relative;
      width: 54px;
      justify-content: center;
    }

    .bridge-line {
      position: absolute;
      top: 50%;
      left: 0;
      right: 0;
      height: 2px;
      background: #e2e8f0;
      transform: translateY(-50%);
    }

    .bridge-pill {
      position: relative;
      background: #f0f7ff;
      border: 1px solid #bae0ff;
      color: #0284c7;
      font-size: 0.6875rem;
      font-weight: 700;
      padding: 0.15rem 0.45rem;
      border-radius: 9999px;
      letter-spacing: 0.04em;
    }

    .title {
      font-size: 1.35rem;
      font-weight: 700;
      color: var(--text-main);
      text-align: center;
      margin-bottom: 0.35rem;
      letter-spacing: -0.02em;
    }

    .subtitle {
      color: var(--text-muted);
      font-size: 0.875rem;
      line-height: 1.5;
      text-align: center;
      margin-bottom: 1.75rem;
    }

    .form-group {
      margin-bottom: 1.25rem;
    }

    .field-label {
      display: block;
      font-size: 0.8125rem;
      font-weight: 600;
      color: #334155;
      margin-bottom: 0.45rem;
    }

    .input-wrapper {
      position: relative;
    }

    input[type="text"] {
      width: 100%;
      background: #f8fafc;
      border: 1.5px solid #d7dde5;
      border-radius: 12px;
      padding: 0.8rem 1rem;
      color: #0f172a;
      font-family: 'IBM Plex Mono', Menlo, Consolas, monospace;
      font-size: 0.875rem;
      outline: none;
      transition: all 0.15s ease;
    }

    input[type="text"]:focus {
      background: #ffffff;
      border-color: var(--brand-blue);
      box-shadow: 0 0 0 3px rgba(2, 132, 199, 0.15);
    }

    .hint {
      display: block;
      font-size: 0.75rem;
      color: var(--text-subtle);
      margin-top: 0.45rem;
    }

    .code-chip {
      background: #f1f5f9;
      border: 1px solid #e2e8f0;
      color: #0f172a;
      font-family: 'IBM Plex Mono', monospace;
      padding: 0.12rem 0.35rem;
      border-radius: 5px;
      font-size: 0.72rem;
    }

    .scope-box {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 14px;
      padding: 1rem 1.15rem;
      margin-bottom: 1.5rem;
    }

    .scope-title {
      font-size: 0.75rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #64748b;
      margin-bottom: 0.65rem;
      display: flex;
      align-items: center;
      gap: 0.4rem;
    }

    .scope-list {
      list-style: none;
      display: flex;
      flex-direction: column;
      gap: 0.45rem;
    }

    .scope-item {
      display: flex;
      align-items: flex-start;
      gap: 0.5rem;
      font-size: 0.8125rem;
      color: #334155;
      line-height: 1.4;
    }

    .check-icon {
      flex-shrink: 0;
      width: 16px;
      height: 16px;
      color: #0284c7;
      margin-top: 1px;
    }

    .security-note {
      font-size: 0.72rem;
      color: #64748b;
      margin-top: 0.75rem;
      padding-top: 0.65rem;
      border-top: 1px solid #edf2f7;
    }

    .btn-submit {
      width: 100%;
      background: var(--btn-dark);
      color: #ffffff;
      border: none;
      border-radius: 12px;
      padding: 0.85rem;
      font-size: 0.9375rem;
      font-weight: 600;
      cursor: pointer;
      box-shadow: 0 4px 12px rgba(15, 23, 42, 0.12);
      transition: all 0.15s ease;
    }

    .btn-submit:hover {
      background: var(--btn-dark-hover);
      box-shadow: 0 6px 16px rgba(15, 23, 42, 0.18);
      transform: translateY(-1px);
    }

    .btn-submit:active {
      transform: translateY(0);
    }

    .cancel-row {
      text-align: center;
      margin-top: 0.85rem;
    }

    .cancel-link {
      color: var(--text-subtle);
      font-size: 0.8125rem;
      text-decoration: none;
      transition: color 0.15s ease;
    }

    .cancel-link:hover {
      color: #334155;
      text-decoration: underline;
    }

    .card-footer {
      text-align: center;
      margin-top: 1.5rem;
      padding-top: 1.25rem;
      border-top: 1px solid #f1f5f9;
      font-size: 0.72rem;
      color: var(--text-subtle);
    }
  </style>
</head>
<body>
  <div class="card">
    <div class="pair-row">
      <div class="avatar-box" title="Extra Computer Use Protocol">
        <img src="/icon.png" alt="Extra">
      </div>
      <div class="bridge-connector">
        <div class="bridge-line"></div>
        <span class="bridge-pill">MCP</span>
      </div>
      <div class="avatar-box" title="Google Gemini">
        <img src="/logos/gemini.svg" alt="Gemini">
      </div>
    </div>

    <h1 class="title">Connect to Google Gemini</h1>
    <p class="subtitle">Pair your desktop workstation with Gemini Web to inspect windows, click buttons, and run local tools.</p>

    <form method="POST" action="/oauth/authorize">
      <input type="hidden" name="client_id" value="${clientId}">
      <input type="hidden" name="redirect_uri" value="${redirectUri}">
      <input type="hidden" name="state" value="${state}">
      <input type="hidden" name="code_challenge" value="${codeChallenge}">
      <input type="hidden" name="code_challenge_method" value="${codeChallengeMethod}">

      <div class="form-group">
        <label for="relay_key" class="field-label">Workstation Setup Key</label>
        <div class="input-wrapper">
          <input type="text" id="relay_key" name="relay_key" value="${savedKey}" placeholder="extra_rel_..." required autofocus spellcheck="false" autocomplete="off">
        </div>
        <span class="hint">Find your key by running <code class="code-chip">extra connect</code> in your terminal.</span>
      </div>

      <div class="scope-box">
        <div class="scope-title">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
          Workstation Permissions
        </div>
        <ul class="scope-list">
          <li class="scope-item">
            <svg class="check-icon" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/></svg>
            <span><strong>Desktop control:</strong> Mouse clicks, keyboard typing, and window navigation</span>
          </li>
          <li class="scope-item">
            <svg class="check-icon" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/></svg>
            <span><strong>Screen inspection:</strong> Window titles, focused controls, and frames</span>
          </li>
          <li class="scope-item">
            <svg class="check-icon" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/></svg>
            <span><strong>Local execution:</strong> Run tools configured in your Extra engine</span>
          </li>
        </ul>
        <div class="security-note">
          Local-first execution. Actions run only on your machine through your authenticated key.
        </div>
      </div>

      <button type="submit" class="btn-submit">Allow Connection</button>
      
      <div class="cancel-row">
        <a href="${cancelHref}" class="cancel-link">Cancel</a>
      </div>
    </form>

    <div class="card-footer">
      Extra • Sovereign Computer Use Protocol
    </div>
  </div>
</body>
</html>`;

      return new Response(html, {
        status: 200,
        headers: {
          "Content-Type": "text/html; charset=utf-8",
          ...CORS_HEADERS,
        },
      });
    }

    // Route RFC 6749 & RFC 7636 OAuth 2.0 Token Endpoint (for Google Gemini & Web MCP Connectors)
    if (url.pathname === "/oauth/token") {
      if (request.method === "POST") {
        let grantType = "";
        let code = "";
        let redirectUri = "";
        let clientId = "";
        let clientSecret = "";
        let codeVerifier = "";
        let refreshToken = "";

        const contentType = request.headers.get("content-type") || "";
        if (contentType.includes("application/x-www-form-urlencoded") || contentType.includes("multipart/form-data")) {
          const formData = await request.formData();
          grantType = formData.get("grant_type") || "";
          code = formData.get("code") || "";
          redirectUri = formData.get("redirect_uri") || "";
          clientId = formData.get("client_id") || "";
          clientSecret = formData.get("client_secret") || "";
          codeVerifier = formData.get("code_verifier") || "";
          refreshToken = formData.get("refresh_token") || "";
        } else if (contentType.includes("application/json")) {
          try {
            const jsonBody = await request.json();
            grantType = jsonBody.grant_type || "";
            code = jsonBody.code || "";
            redirectUri = jsonBody.redirect_uri || "";
            clientId = jsonBody.client_id || "";
            clientSecret = jsonBody.client_secret || "";
            codeVerifier = jsonBody.code_verifier || "";
            refreshToken = jsonBody.refresh_token || "";
          } catch (_) {}
        }

        const authHeader = request.headers.get("authorization") || "";
        if (authHeader.startsWith("Basic ")) {
          try {
            const creds = atob(authHeader.substring(6)).split(":");
            if (creds.length >= 2) {
              clientId = clientId || creds[0];
              clientSecret = clientSecret || creds[1];
            }
          } catch (_) {}
        }

        // Grant Type 1: authorization_code
        if (grantType === "authorization_code") {
          if (!code) {
            return new Response(JSON.stringify({ error: "invalid_request", error_description: "Missing authorization code" }), {
              status: 400,
              headers: { "Content-Type": "application/json; charset=utf-8", ...CORS_HEADERS },
            });
          }

          let codeRecord = null;
          if (env && env.TELEMETRY_KV) {
            try {
              const raw = await env.TELEMETRY_KV.get(`oauth_code:${code}`);
              if (raw) {
                codeRecord = JSON.parse(raw);
                // Consume code immediately to ensure one-time use
                await env.TELEMETRY_KV.delete(`oauth_code:${code}`);
              }
            } catch (_) {}
          }

          if (!codeRecord) {
            return new Response(JSON.stringify({ error: "invalid_grant", error_description: "Authorization code is invalid or expired" }), {
              status: 400,
              headers: { "Content-Type": "application/json; charset=utf-8", ...CORS_HEADERS },
            });
          }

          // PKCE S256 verification if challenge was set
          if (codeRecord.code_challenge) {
            if (!codeVerifier) {
              return new Response(JSON.stringify({ error: "invalid_grant", error_description: "Missing PKCE code_verifier" }), {
                status: 400,
                headers: { "Content-Type": "application/json; charset=utf-8", ...CORS_HEADERS },
              });
            }

            if (codeRecord.code_challenge_method === "S256") {
              const encoder = new TextEncoder();
              const digest = await crypto.subtle.digest("SHA-256", encoder.encode(codeVerifier));
              const computedChallenge = btoa(String.fromCharCode(...new Uint8Array(digest)))
                .replace(/\+/g, "-")
                .replace(/\//g, "_")
                .replace(/=+$/, "");

              if (computedChallenge !== codeRecord.code_challenge) {
                return new Response(JSON.stringify({ error: "invalid_grant", error_description: "PKCE verification failed" }), {
                  status: 400,
                  headers: { "Content-Type": "application/json; charset=utf-8", ...CORS_HEADERS },
                });
              }
            } else if (codeVerifier !== codeRecord.code_challenge) {
              return new Response(JSON.stringify({ error: "invalid_grant", error_description: "PKCE plain verification failed" }), {
                status: 400,
                headers: { "Content-Type": "application/json; charset=utf-8", ...CORS_HEADERS },
              });
            }
          }

          // Issue access token and refresh token
          const accessToken = "extra_tok_" + crypto.randomUUID().replace(/-/g, "");
          const newRefreshToken = "extra_ref_" + crypto.randomUUID().replace(/-/g, "");

          const tokenRecord = {
            relay_key: codeRecord.relay_key,
            client_id: codeRecord.client_id || clientId,
            created_at: Date.now(),
          };

          if (env && env.TELEMETRY_KV) {
            try {
              // 30 days access token
              await env.TELEMETRY_KV.put(`oauth_token:${accessToken}`, JSON.stringify(tokenRecord), { expirationTtl: 86400 * 30 });
              // 90 days refresh token
              await env.TELEMETRY_KV.put(`oauth_refresh:${newRefreshToken}`, JSON.stringify(tokenRecord), { expirationTtl: 86400 * 90 });
            } catch (_) {}
          }

          return new Response(JSON.stringify({
            access_token: accessToken,
            token_type: "Bearer",
            expires_in: 86400 * 30,
            refresh_token: newRefreshToken,
            scope: "mcp offline_access",
          }), {
            status: 200,
            headers: {
              "Content-Type": "application/json; charset=utf-8",
              ...CORS_HEADERS,
              "Cache-Control": "no-store",
              "Pragma": "no-cache",
            },
          });
        }

        // Grant Type 2: refresh_token
        if (grantType === "refresh_token") {
          if (!refreshToken) {
            return new Response(JSON.stringify({ error: "invalid_request", error_description: "Missing refresh token" }), {
              status: 400,
              headers: { "Content-Type": "application/json; charset=utf-8", ...CORS_HEADERS },
            });
          }

          let refreshRecord = null;
          if (env && env.TELEMETRY_KV) {
            try {
              const raw = await env.TELEMETRY_KV.get(`oauth_refresh:${refreshToken}`);
              if (raw) refreshRecord = JSON.parse(raw);
            } catch (_) {}
          }

          if (!refreshRecord) {
            return new Response(JSON.stringify({ error: "invalid_grant", error_description: "Refresh token is invalid or expired" }), {
              status: 400,
              headers: { "Content-Type": "application/json; charset=utf-8", ...CORS_HEADERS },
            });
          }

          const newAccessToken = "extra_tok_" + crypto.randomUUID().replace(/-/g, "");
          if (env && env.TELEMETRY_KV) {
            try {
              await env.TELEMETRY_KV.put(`oauth_token:${newAccessToken}`, JSON.stringify(refreshRecord), { expirationTtl: 86400 * 30 });
            } catch (_) {}
          }

          return new Response(JSON.stringify({
            access_token: newAccessToken,
            token_type: "Bearer",
            expires_in: 86400 * 30,
            refresh_token: refreshToken,
            scope: "mcp offline_access",
          }), {
            status: 200,
            headers: {
              "Content-Type": "application/json; charset=utf-8",
              ...CORS_HEADERS,
              "Cache-Control": "no-store",
              "Pragma": "no-cache",
            },
          });
        }

        return new Response(JSON.stringify({ error: "unsupported_grant_type", error_description: `Grant type '${grantType}' not supported` }), {
          status: 400,
          headers: { "Content-Type": "application/json; charset=utf-8", ...CORS_HEADERS },
        });
      }

      if (request.method === "GET") {
        return new Response(JSON.stringify({
          status: "ready",
          service: "OAuth 2.0 Token Endpoint",
          spec: "RFC 6749 / RFC 7636",
        }), {
          status: 200,
          headers: {
            "Content-Type": "application/json; charset=utf-8",
            ...CORS_HEADERS,
          },
        });
      }
    }

    // Route 0: Universal CORS Preflight
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: {
          ...CORS_HEADERS,
          "Access-Control-Allow-Headers": "Content-Type, User-Agent, Authorization, Accept, X-Requested-With",
        },
      });
    }

    // Route MCP: Model Context Protocol & OpenAI ChatGPT Plugin Gateway
    if (
      url.pathname === "/mcp" ||
      url.pathname === "/sse" ||
      url.pathname.startsWith("/messages") ||
      url.pathname.startsWith("/oauth/") ||
      url.pathname.startsWith("/api/auth/") ||
      url.pathname.startsWith("/api/paypal/") ||
      url.pathname.startsWith("/api/action/") ||
      url.pathname === "/openapi.json" ||
      url.pathname === "/openapi.yaml" ||
      url.pathname === "/.well-known/ai-plugin.json" ||
      url.pathname === "/plugin.json" ||
      url.pathname === "/health"
    ) {
      const targetUrl = new URL(url.pathname + url.search, AWS_MCP_HUB_ORIGIN);

      // Resolve OAuth Bearer access token to user's paired desktop relay key
      const authHeader = request.headers.get("Authorization") || "";
      let isBearerAuth = false;
      let effectiveRelayKey = null;

      if (authHeader.startsWith("Bearer ")) {
        isBearerAuth = true;
        const token = authHeader.substring(7).trim();

        if (token.startsWith("extra_rel_") || token.startsWith("extra_usr_")) {
          // Direct relay key or user token passed as Bearer
          effectiveRelayKey = token;
          targetUrl.searchParams.set("key", token);
        } else if (token.startsWith("extra_tok_")) {
          // OAuth 2.0 dynamic access token issued to Google Gemini or ChatGPT
          if (env && env.TELEMETRY_KV) {
            try {
              const rawTokenData = await env.TELEMETRY_KV.get(`oauth_token:${token}`);
              if (rawTokenData) {
                const tokenRecord = JSON.parse(rawTokenData);
                if (tokenRecord && tokenRecord.relay_key) {
                  effectiveRelayKey = tokenRecord.relay_key;
                  targetUrl.searchParams.set("key", tokenRecord.relay_key);
                }
              }
            } catch (_) {}
          }
        } else if (token) {
          // Other tokens (e.g. JWT or custom credentials), check KV first
          if (env && env.TELEMETRY_KV) {
            try {
              const rawTokenData = await env.TELEMETRY_KV.get(`oauth_token:${token}`);
              if (rawTokenData) {
                const tokenRecord = JSON.parse(rawTokenData);
                if (tokenRecord && tokenRecord.relay_key) {
                  effectiveRelayKey = tokenRecord.relay_key;
                  targetUrl.searchParams.set("key", tokenRecord.relay_key);
                }
              }
            } catch (_) {}
          }
        }
      }

      // If client attempted Bearer auth but token could not be resolved and no query key is present, reject with 401
      if (isBearerAuth && !targetUrl.searchParams.has("key") && (url.pathname === "/mcp" || url.pathname === "/sse")) {
        return new Response(JSON.stringify({
          jsonrpc: "2.0",
          error: {
            code: -32000,
            message: "Unauthorized: Invalid or expired Bearer access token. Please re-authenticate."
          },
          id: null
        }), {
          status: 401,
          headers: {
            "Content-Type": "application/json; charset=utf-8",
            "WWW-Authenticate": 'Bearer error="invalid_token", error_description="The access token expired or is invalid"',
            ...CORS_HEADERS,
          },
        });
      }

      const reqHeaders = new Headers(request.headers);
      reqHeaders.set("Host", targetUrl.hostname);
      reqHeaders.set("X-Forwarded-Host", url.hostname);
      reqHeaders.set("X-Forwarded-Proto", "https");

      // CRITICAL: Rewrite the forwarded Authorization header to the resolved relay key!
      // Upstream AWS Lambda prioritizes Authorization: Bearer <key> over the ?key= query param.
      // If we leave the external extra_tok_... in the Authorization header, Lambda uses extra_tok_...
      // as the lookup key and fails to find the user's active extra_rel_... connection!
      if (effectiveRelayKey) {
        reqHeaders.set("Authorization", `Bearer ${effectiveRelayKey}`);
      }

      const backendRes = await fetch(targetUrl.toString(), {
        method: request.method,
        headers: reqHeaders,
        body: request.method !== "GET" && request.method !== "HEAD" ? request.body : undefined,
        redirect: "manual",
      });

      const resHeaders = new Headers(backendRes.headers);
      resHeaders.set("Access-Control-Allow-Origin", "*");
      resHeaders.set("Access-Control-Allow-Methods", "GET, POST, OPTIONS, HEAD");
      resHeaders.set("Access-Control-Allow-Headers", "Content-Type, Authorization, Accept, X-Requested-With");

      return new Response(backendRes.body, {
        status: backendRes.status,
        headers: resHeaders,
      });
    }

    // Route 1: Health Diagnostic Check
    if (url.pathname === "/api/health") {
      const geo = request.cf ? {
        country: request.cf.country || "XX",
        city: request.cf.city || "Unknown",
        colo: request.cf.colo || "Unknown",
      } : {};
      return new Response(
        JSON.stringify({
          status: "healthy",
          service: "extra-edge-router",
          version: "0.3.3",
          edge: geo,
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json", ...CORS_HEADERS },
        }
      );
    }

    // Route 2: Anonymous Installation Success Beacon
    if (url.pathname === "/api/install-success" && request.method === "POST") {
      const contentLength = parseInt(request.headers.get("content-length") || "0", 10);
      if (contentLength > 16384) {
        return new Response(JSON.stringify({ error: "Payload too large. Max 16KB allowed." }), {
          status: 413,
          headers: { "Content-Type": "application/json", ...CORS_HEADERS },
        });
      }

      let body = {};
      try {
        body = await request.json();
      } catch (_) {
        body = {
          os: url.searchParams.get("os") || "unknown",
          arch: url.searchParams.get("arch") || "unknown",
          version: url.searchParams.get("version") || "0.3.3",
          method: url.searchParams.get("method") || "script",
        };
      }

      const geo = request.cf ? {
        country: request.cf.country || "XX",
        city: request.cf.city || "Unknown",
        colo: request.cf.colo || "Unknown",
      } : {};

      const eventRecord = {
        event: "install_success",
        os: body.os || "unknown",
        arch: body.arch || "unknown",
        version: body.version || "0.3.3",
        method: body.method || "script",
        geo,
        timestamp: Date.now(),
      };

      // Persist in Cloudflare KV if configured
      if (env && env.TELEMETRY_KV) {
        try {
          const dateStr = new Date().toISOString().slice(0, 10);
          const key = `install:${dateStr}:${body.os || "unknown"}:${Date.now()}`;
          await env.TELEMETRY_KV.put(key, JSON.stringify(eventRecord), { expirationTtl: 86400 * 90 });
        } catch (_) {}
      }

      if (ctx && ctx.waitUntil && env && env.WEBHOOK_URL) {
        ctx.waitUntil(fetch(env.WEBHOOK_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(eventRecord),
        }).catch(() => {}));
      }

      return new Response(JSON.stringify({ status: "ok", tracked: true }), {
        status: 200,
        headers: { "Content-Type": "application/json", ...CORS_HEADERS },
      });
    }

    // Route 3: Fleet Telemetry & First-Run Activation Ingestion
    if (url.pathname === "/api/telemetry" && request.method === "POST") {
      const contentLength = parseInt(request.headers.get("content-length") || "0", 10);
      if (contentLength > 16384) {
        return new Response(JSON.stringify({ error: "Payload too large. Max 16KB allowed." }), {
          status: 413,
          headers: { "Content-Type": "application/json", ...CORS_HEADERS },
        });
      }

      let payload = {};
      try {
        payload = await request.json();
      } catch (_) {
        return new Response(JSON.stringify({ error: "Invalid JSON" }), {
          status: 400,
          headers: { "Content-Type": "application/json", ...CORS_HEADERS },
        });
      }

      const geo = request.cf ? {
        country: request.cf.country || "XX",
        colo: request.cf.colo || "Unknown",
      } : {};

      const rawEvents = Array.isArray(payload.events) ? payload.events : [payload];
      // Bound array processing to max 25 events per request to prevent KV write exhaustion
      const events = rawEvents.slice(0, 25);

      // Persist in Cloudflare KV if configured
      if (env && env.TELEMETRY_KV) {
        try {
          const dateStr = new Date().toISOString().slice(0, 10);
          for (const ev of events) {
            const key = `telemetry:${dateStr}:${ev.event || "event"}:${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
            await env.TELEMETRY_KV.put(key, JSON.stringify({ ...ev, geo }), { expirationTtl: 86400 * 90 });
          }
        } catch (_) {}
      }

      // Async dispatch to external PostHog if configured
      if (ctx && ctx.waitUntil && env && env.POSTHOG_HOST && env.POSTHOG_API_KEY) {
        ctx.waitUntil((async () => {
          try {
            if (env && env.POSTHOG_HOST && env.POSTHOG_API_KEY) {
              const posthogEvents = events.map(ev => ({
                event: ev.event || "extra_event",
                properties: {
                  ...ev,
                  $geoip_country_code: geo.country,
                },
                distinct_id: ev.client_hash || "anonymous",
              }));
              await fetch(`https://${env.POSTHOG_HOST}/batch/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  api_key: env.POSTHOG_API_KEY,
                  batch: posthogEvents,
                }),
              });
            }
          } catch (_) {}
        })());
      }

      return new Response(JSON.stringify({ status: "ok", received: events.length }), {
        status: 200,
        headers: { "Content-Type": "application/json", ...CORS_HEADERS },
      });
    }

    // Route 4: Direct script & rule requests
    if (SCRIPT_MAP[url.pathname]) {
      // Optional: record script download count
      if (ctx && ctx.waitUntil && env && env.TELEMETRY_KV) {
        ctx.waitUntil((async () => {
          try {
            const dateStr = new Date().toISOString().slice(0, 10);
            const key = `download:${dateStr}:${url.pathname}:${Date.now()}`;
            await env.TELEMETRY_KV.put(key, JSON.stringify({ script: url.pathname, time: Date.now() }), { expirationTtl: 86400 * 30 });
          } catch (_) {}
        })());
      }

      const upstreamRes = await fetch(SCRIPT_MAP[url.pathname]);
      const headers = new Headers(upstreamRes.headers);
      headers.set("Content-Type", "text/plain; charset=utf-8");
      headers.set("Cache-Control", "public, max-age=60, s-maxage=300");
      headers.set("X-Content-Type-Options", "nosniff");
      headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
      headers.set("Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload");
      return new Response(upstreamRes.body, {
        status: upstreamRes.status,
        headers,
      });
    }

    // Route 5: Universal CLI one-liner: curl -sSL https://extra.yantraos.com/install | bash
    if (url.pathname === "/install") {
      const targetScript = isMacOrUnixUserAgent(userAgent) ? "/install.sh" : "/install.ps1";
      const upstreamRes = await fetch(SCRIPT_MAP[targetScript]);
      const headers = new Headers(upstreamRes.headers);
      headers.set("Content-Type", "text/plain; charset=utf-8");
      headers.set("Cache-Control", "public, max-age=60, s-maxage=300");
      headers.set("X-Content-Type-Options", "nosniff");
      headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
      headers.set("Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload");
      return new Response(upstreamRes.body, {
        status: upstreamRes.status,
        headers,
      });
    }

    // Route 6: Web Browser UI / Assets fallback to S3 Origin with Edge Caching
    const cache = caches.default;
    const cacheKey = new Request(url.toString(), request);
    
    // Attempt edge cache lookup for GET / HEAD
    if (request.method === "GET" || request.method === "HEAD") {
      const cachedRes = await cache.match(cacheKey);
      if (cachedRes) {
        const headers = new Headers(cachedRes.headers);
        headers.set("CF-Cache-Status", "HIT");
        headers.set("X-Edge-Cache", "HIT");
        return new Response(cachedRes.body, {
          status: cachedRes.status,
          headers,
        });
      }
    }

    const S3_ORIGIN = "http://extra.yantraos.com.s3-website.ap-south-1.amazonaws.com";
    const targetUrl = new URL(url.pathname + url.search, S3_ORIGIN);

    const reqHeaders = new Headers(request.headers);
    reqHeaders.delete("host");
    reqHeaders.set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36");

    const originRes = await fetch(targetUrl.toString(), {
      method: request.method,
      headers: reqHeaders,
    });

    const resHeaders = new Headers(originRes.headers);
    resHeaders.set("X-Content-Type-Options", "nosniff");
    resHeaders.set("X-Frame-Options", "DENY");
    resHeaders.set("Referrer-Policy", "strict-origin-when-cross-origin");
    resHeaders.set("Permissions-Policy", "camera=(), microphone=(), geolocation=(), browsing-topics=()");
    resHeaders.set("Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload");
    resHeaders.set("X-Served-By", "extra-edge-router");
    resHeaders.set(
      "Content-Security-Policy",
      [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline' https://player.vimeo.com https://static.cloudflareinsights.com https://www.googletagmanager.com https://www.clarity.ms https://*.clarity.ms https://www.paypal.com https://*.paypalobjects.com",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: blob: https: https://www.googletagmanager.com https://*.google-analytics.com https://*.clarity.ms https://c.bing.com",
        "font-src 'self' data:",
        "frame-src 'self' https://player.vimeo.com https://*.paypal.com",
        "media-src 'self' blob: data: https:",
        "connect-src 'self' https://cloudflareinsights.com https://*.vimeo.com https://*.vimeocdn.com https://*.google-analytics.com https://*.analytics.google.com https://*.googletagmanager.com https://*.clarity.ms https://c.bing.com https://*.paypal.com",
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "form-action 'self'",
      ].join("; ")
    );

    if (resHeaders.has("location")) {
      const loc = resHeaders.get("location");
      resHeaders.set("location", loc.replace(/^http:\/\//i, "https://"));
    }

    if (url.pathname.startsWith("/_next/static/")) {
      resHeaders.set("Cache-Control", "public, max-age=31536000, immutable");
      resHeaders.set("s-maxage", "31536000");
    } else {
      resHeaders.set("Cache-Control", "public, max-age=0, s-maxage=0, must-revalidate");
    }

    const finalRes = new Response(originRes.body, {
      status: originRes.status,
      headers: resHeaders,
    });

    if ((request.method === "GET" || request.method === "HEAD") && originRes.status === 200 && ctx && ctx.waitUntil) {
      ctx.waitUntil(cache.put(cacheKey, finalRes.clone()));
    }

    return finalRes;
  },
};
