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

    // Route 0: CORS Preflight
    if (request.method === "OPTIONS" && url.pathname.startsWith("/api/")) {
      return new Response(null, { status: 204, headers: CORS_HEADERS });
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
          version: "0.3.1",
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
          version: url.searchParams.get("version") || "0.3.1",
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
        version: body.version || "0.3.1",
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
    reqHeaders.set("Host", "extra.yantraos.com");

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
        "script-src 'self' 'unsafe-inline' https://player.vimeo.com https://static.cloudflareinsights.com https://www.googletagmanager.com https://www.clarity.ms https://*.clarity.ms",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: blob: https: https://www.googletagmanager.com https://*.google-analytics.com https://*.clarity.ms https://c.bing.com",
        "font-src 'self' data:",
        "frame-src 'self' https://player.vimeo.com",
        "media-src 'self' blob: data: https:",
        "connect-src 'self' https://cloudflareinsights.com https://*.vimeo.com https://*.vimeocdn.com https://*.google-analytics.com https://*.analytics.google.com https://*.googletagmanager.com https://*.clarity.ms https://c.bing.com",
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
      resHeaders.set("Cache-Control", "public, max-age=0, s-maxage=3600, must-revalidate");
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
