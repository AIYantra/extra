"""
Unit and integration tests for Phase 4 Security Hardening:
Edge Worker, Script Delivery Security, OAuth PKCE, Token Revocation, XSS Escaping,
and HTTPS Origin Enforcement (worker.js).
"""

import sys
import os
import re
import shutil
import tempfile
import subprocess
from pathlib import Path
import pytest

extra_root = Path(__file__).resolve().parents[1]
worker_path = extra_root / "worker.js"
if not worker_path.is_file():
    worker_path = extra_root.parent / "extra.yantraos.com" / "worker.js"


def test_worker_file_exists():
    assert worker_path.is_file(), f"worker.js not found at {worker_path}"


def test_worker_https_origins_enforced():
    """Verifies that all S3 and upstream script origins strictly use HTTPS and never plaintext HTTP."""
    content = worker_path.read_text(encoding="utf-8")
    
    # Assert no plaintext http:// origins exist in worker.js
    assert "http://" not in content, "Found unencrypted http:// origin in worker.js"
    assert "s3-website" not in content, "Found legacy unauthenticated s3-website origin"
    assert "https://extra.yantraos.com.s3.ap-south-1.amazonaws.com" in content


def test_worker_token_ttl_limits():
    """Verifies that OAuth access token TTL is capped at 24 hours (86400s) and refresh token at 90 days."""
    content = worker_path.read_text(encoding="utf-8")
    
    assert "const OAUTH_ACCESS_TOKEN_TTL = 86400" in content
    assert "const OAUTH_REFRESH_TOKEN_TTL = 86400 * 90" in content
    # Verify no remaining 30-day (86400 * 30) access token TTLs
    assert "86400 * 30" not in content


def test_worker_backdoor_codes_removed():
    """Verifies that hardcoded backdoor reviewer bypasses in /oauth/token are completely eradicated."""
    content = worker_path.read_text(encoding="utf-8")
    
    # Check that auth_chatgpt_reviewer is never checked as a bypass in token exchange
    assert 'code === "auth_chatgpt_reviewer"' not in content
    assert 'code.startsWith("auth_reviewer_")' not in content


def test_worker_query_parameter_sanitization():
    """Verifies that sensitive query parameters (?key=, ?token=, ?passkey=) are stripped before S3 proxying."""
    content = worker_path.read_text(encoding="utf-8")
    
    assert 'cleanSearch.delete("key")' in content
    assert 'cleanSearch.delete("token")' in content
    assert 'cleanSearch.delete("passkey")' in content
    assert 'cleanSearch.delete("relay_key")' in content


def test_worker_node_integration():
    """Executes the automated Node.js integration suite verifying PKCE, XSS escaping, and Revocation."""
    if shutil.which("node") is None:
        pytest.skip("Node.js not installed on this runner")
    if not worker_path.is_file():
        pytest.skip("worker.js not found for node execution")

    # Format path with forward slashes for ES module import on all platforms
    worker_url_path = worker_path.resolve().as_posix()

    node_script_content = f"""
import worker from "file:///{worker_url_path}";
import assert from "node:assert";

class MockKV {{
  constructor() {{
    this.store = new Map();
  }}
  async get(key) {{
    return this.store.get(key) || null;
  }}
  async put(key, val, opts) {{
    this.store.set(key, val);
  }}
  async delete(key) {{
    this.store.delete(key);
  }}
}}

async function runTests() {{
  const kv = new MockKV();
  const env = {{ TELEMETRY_KV: kv }};
  const ctx = {{ waitUntil: (p) => p }};

  // 1. Discovery
  {{
    const req = new Request("https://extra.yantraos.com/.well-known/oauth-authorization-server");
    const res = await worker.fetch(req, env, ctx);
    assert.strictEqual(res.status, 200);
    const data = await res.json();
    assert.strictEqual(data.revocation_endpoint, "https://extra.yantraos.com/oauth/revoke");
    assert.deepStrictEqual(data.code_challenge_methods_supported, ["S256"]);
  }}

  // 2. PKCE requirement
  {{
    const req = new Request("https://extra.yantraos.com/oauth/authorize?client_id=chatgpt&redirect_uri=https://chatgpt.com/api/aip/callback");
    const res = await worker.fetch(req, env, ctx);
    assert.strictEqual(res.status, 400);
    const body = await res.json();
    assert.strictEqual(body.error, "invalid_request");
    assert.match(body.error_description, /code_challenge is required/i);
  }}

  // 3. XSS escaping
  {{
    const maliciousClient = '<script>alert("xss")</script>';
    const req = new Request(`https://extra.yantraos.com/oauth/authorize?client_id=test&client_name=${{encodeURIComponent(maliciousClient)}}&code_challenge=xyz123&redirect_uri=https://chatgpt.com/api/aip/callback`);
    const res = await worker.fetch(req, env, ctx);
    assert.strictEqual(res.status, 200);
    const html = await res.text();
    assert(!html.includes('<script>alert("xss")</script>'));
  }}

  // 4. Backdoor code rejection
  {{
    const req = new Request("https://extra.yantraos.com/oauth/token", {{
      method: "POST",
      headers: {{ "Content-Type": "application/json" }},
      body: JSON.stringify({{
        grant_type: "authorization_code",
        code: "auth_chatgpt_reviewer",
        code_verifier: "xyz",
      }}),
    }});
    const res = await worker.fetch(req, env, ctx);
    assert.strictEqual(res.status, 400);
    const body = await res.json();
    assert.strictEqual(body.error, "invalid_grant");
  }}

  // 5. PKCE verifier requirement
  {{
    await kv.put("oauth_code:valid_test_code", JSON.stringify({{
      relay_key: "extra_rel_123",
      client_id: "test",
      redirect_uri: "https://chatgpt.com/api/aip/callback",
      code_challenge: "some_challenge",
      code_challenge_method: "S256",
      created_at: Date.now(),
    }}));

    const req = new Request("https://extra.yantraos.com/oauth/token", {{
      method: "POST",
      headers: {{ "Content-Type": "application/json" }},
      body: JSON.stringify({{
        grant_type: "authorization_code",
        code: "valid_test_code",
      }}),
    }});
    const res = await worker.fetch(req, env, ctx);
    assert.strictEqual(res.status, 400);
    const body = await res.json();
    assert.strictEqual(body.error, "invalid_grant");
    assert.match(body.error_description, /PKCE code_verifier/i);
  }}

  // 6. Revocation
  {{
    await kv.put("oauth_token:extra_tok_test_123", JSON.stringify({{ relay_key: "abc" }}));
    const req = new Request("https://extra.yantraos.com/oauth/revoke", {{
      method: "POST",
      headers: {{ "Content-Type": "application/json" }},
      body: JSON.stringify({{ token: "extra_tok_test_123" }}),
    }});
    const res = await worker.fetch(req, env, ctx);
    assert.strictEqual(res.status, 200);
    assert.strictEqual(await kv.get("oauth_token:extra_tok_test_123"), null);
  }}
}}

runTests().catch((err) => {{
  console.error("Test failed:", err);
  process.exit(1);
}});
"""
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False, encoding="utf-8") as f:
        f.write(node_script_content)
        temp_script = f.name

    try:
        res = subprocess.run(
            ["node", temp_script],
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert res.returncode == 0, f"Node test harness failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
    finally:
        try:
            os.remove(temp_script)
        except OSError:
            pass
