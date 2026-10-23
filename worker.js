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

      // GET: Render polished YantraOS device consent & pairing UI
      const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Connect Extra to Google Gemini</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background-color: #0c0d12;
      color: #e2e8f0;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      padding: 1.5rem;
    }
    .card {
      background: #141721;
      border: 1px solid #232838;
      border-radius: 16px;
      padding: 2.5rem;
      width: 100%;
      max-width: 480px;
      box-shadow: 0 20px 40px rgba(0,0,0,0.4);
    }
    .badge {
      display: inline-block;
      background: rgba(56, 189, 248, 0.12);
      color: #38bdf8;
      font-size: 0.75rem;
      font-weight: 600;
      padding: 0.35rem 0.75rem;
      border-radius: 9999px;
      margin-bottom: 1.25rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    h1 {
      font-size: 1.5rem;
      font-weight: 700;
      color: #ffffff;
      margin-bottom: 0.75rem;
    }
    p {
      color: #94a3b8;
      font-size: 0.9rem;
      line-height: 1.5;
      margin-bottom: 1.75rem;
    }
    .form-group {
      margin-bottom: 1.5rem;
    }
    label {
      display: block;
      font-size: 0.825rem;
      font-weight: 600;
      color: #cbd5e1;
      margin-bottom: 0.5rem;
    }
    input[type="text"] {
      width: 100%;
      background: #0f111a;
      border: 1px solid #2d3348;
      border-radius: 10px;
      padding: 0.85rem 1rem;
      color: #ffffff;
      font-size: 0.95rem;
      font-family: monospace;
      outline: none;
      transition: border-color 0.15s;
    }
    input[type="text"]:focus {
      border-color: #38bdf8;
      box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.15);
    }
    .hint {
      display: block;
      font-size: 0.75rem;
      color: #64748b;
      margin-top: 0.4rem;
    }
    .permissions {
      background: rgba(15, 23, 42, 0.6);
      border: 1px solid #1e293b;
      border-radius: 10px;
      padding: 1rem;
      margin-bottom: 1.75rem;
      font-size: 0.8rem;
      color: #94a3b8;
    }
    .permissions strong { color: #f1f5f9; display: block; margin-bottom: 0.25rem; }
    button {
      width: 100%;
      background: linear-gradient(135deg, #2563eb, #1d4ed8);
      color: #ffffff;
      border: none;
      border-radius: 10px;
      padding: 0.95rem;
      font-size: 1rem;
      font-weight: 600;
      cursor: pointer;
      transition: opacity 0.15s, transform 0.05s;
    }
    button:hover { opacity: 0.95; }
    button:active { transform: scale(0.99); }
  </style>
</head>
<body>
  <div class="card">
    <span class="badge">Model Context Protocol</span>
    <h1>Connect Extra to Google Gemini</h1>
    <p>Authorize Google Gemini Web (gemini.google.com) to pilot this workstation using your secure Extra device tunnel.</p>
    <form method="POST" action="/oauth/authorize">
      <input type="hidden" name="client_id" value="${clientId}">
      <input type="hidden" name="redirect_uri" value="${redirectUri}">
      <input type="hidden" name="state" value="${state}">
      <input type="hidden" name="code_challenge" value="${codeChallenge}">
      <input type="hidden" name="code_challenge_method" value="${codeChallengeMethod}">
      <div class="form-group">
        <label for="relay_key">Desktop Setup Key</label>
        <input type="text" id="relay_key" name="relay_key" value="${savedKey}" placeholder="extra_rel_..." required autofocus>
        <span class="hint">Obtain this key by running <code>extra connect</code> in your local terminal.</span>
      </div>
      <div class="permissions">
        <strong>Granted Scope:</strong>
        Full local desktop automation (mouse clicks, Unicode typing, visual screen inspection, and batch execution).
      </div>
      <button type="submit">Authorize & Pair Device</button>
    </form>
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
      const reqHeaders = new Headers(request.headers);
      reqHeaders.set("Host", targetUrl.hostname);
      reqHeaders.set("X-Forwarded-Host", url.hostname);
      reqHeaders.set("X-Forwarded-Proto", "https");

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
