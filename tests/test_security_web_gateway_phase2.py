"""
Unit and integration tests for Phase 2 Security Audit:
Web Platform & Cloudflare Edge Gateway Security (worker.js & Next.js frontend),
OAuth 2.0 / RFC 8414 & RFC 7636 PKCE Enforcement, Upstream Header Sanitization,
Client-Side Credential Lifecycle, and Defense-in-Depth Security Headers.
"""

import sys
import os
import re
import json
import base64
import hashlib
from urllib.parse import urlparse
from pathlib import Path
import pytest

extra_root = Path(__file__).resolve().parents[1]
website_root = extra_root.parent / "extra.yantraos.com"
worker_path = website_root / "worker.js"
auth_path = website_root / "src" / "utils" / "auth.ts"
next_config_path = website_root / "next.config.ts"


def test_rfc8414_oauth_metadata_conformance():
    """Verifies that RFC 8414 OAuth 2.0 Authorization Server and Protected Resource metadata are strictly defined."""
    assert worker_path.is_file(), f"worker.js not found at {worker_path}"
    content = worker_path.read_text(encoding="utf-8")

    # 1. Authorization Server Metadata endpoints
    assert "url.pathname === \"/.well-known/oauth-authorization-server\"" in content
    assert "url.pathname === \"/.well-known/openid-configuration\"" in content
    assert 'issuer: "https://extra.yantraos.com"' in content
    assert 'authorization_endpoint: "https://extra.yantraos.com/oauth/authorize"' in content
    assert 'token_endpoint: "https://extra.yantraos.com/oauth/token"' in content
    assert 'revocation_endpoint: "https://extra.yantraos.com/oauth/revoke"' in content
    assert 'registration_endpoint: "https://extra.yantraos.com/oauth/register"' in content
    assert 'code_challenge_methods_supported: ["S256"]' in content

    # 2. Protected Resource Metadata
    assert "url.pathname === \"/.well-known/oauth-protected-resource\"" in content
    assert 'resource: "https://extra.yantraos.com/mcp"' in content
    assert 'authorization_servers: ["https://extra.yantraos.com"]' in content


def test_rfc7636_pkce_validation_enforcement():
    """Verifies RFC 7636 PKCE S256 code challenge computation and verification logic."""
    content = worker_path.read_text(encoding="utf-8")

    # 1. Mandate code_verifier check in worker.js
    assert "Missing PKCE code_verifier" in content
    assert 'codeRecord.code_challenge_method === "S256"' in content
    assert "PKCE verification failed" in content

    # 2. Python mirror testing of RFC 7636 S256 PKCE specification
    def compute_s256_code_challenge(verifier: str) -> str:
        digest = hashlib.sha256(verifier.encode("ascii")).digest()
        return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")

    def verify_pkce(verifier: str, stored_challenge: str, method: str) -> bool:
        if not verifier or not stored_challenge:
            return False
        if method == "S256":
            return compute_s256_code_challenge(verifier) == stored_challenge
        return verifier == stored_challenge

    # Test vectors (RFC 7636 Appendix B)
    test_verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    expected_challenge = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"

    assert compute_s256_code_challenge(test_verifier) == expected_challenge
    assert verify_pkce(test_verifier, expected_challenge, "S256") is True

    # Tampered verifier must fail
    assert verify_pkce(test_verifier + "_tampered", expected_challenge, "S256") is False
    # Empty verifier must fail
    assert verify_pkce("", expected_challenge, "S256") is False


def test_oauth_redirect_uri_security():
    """Verifies that redirect URIs are strictly validated against allowlists, rejecting open redirects and dangerous protocols."""
    content = worker_path.read_text(encoding="utf-8")

    # Ensure worker has redirect URI check function
    assert "function isValidRedirectUri(uri, clientRecord)" in content
    assert 'parsed.protocol !== "https:" && parsed.protocol !== "http:"' in content
    assert 'parsed.protocol === "http:" && parsed.hostname !== "localhost" && parsed.hostname !== "127.0.0.1"' in content

    # Python mirror test of isValidRedirectUri logic
    def is_valid_redirect_uri(uri: str, client_uris: list[str] = None) -> bool:
        if not uri:
            return False
        try:
            parsed = urlparse(uri)
            if parsed.scheme not in ("https", "http"):
                return False
            if parsed.scheme == "http" and parsed.hostname not in ("localhost", "127.0.0.1"):
                return False

            allowed_exact = [
                "https://chatgpt.com/api/aip/callback",
                "https://chat.openai.com/api/aip/callback",
                "https://chatgpt.com/auth/callback",
                "https://chat.openai.com/auth/callback",
                "https://chatgpt.com/aip/test/oauth/callback",
                "https://claude.ai/api/connectors/callback",
                "https://vertexaisearch.cloud.google.com/oauth-redirect",
                "https://vertexaisearch.cloud.google.com/callback",
            ]
            if uri in allowed_exact:
                return True

            if client_uris and uri in client_uris:
                return True

            if parsed.hostname in ("localhost", "127.0.0.1") and (
                parsed.path == "/api/auth/callback" or parsed.path.startswith("/api/auth/callback/")
            ):
                return True

            return False
        except Exception:
            return False

    # Valid targets
    assert is_valid_redirect_uri("https://chatgpt.com/auth/callback") is True
    assert is_valid_redirect_uri("https://claude.ai/api/connectors/callback") is True
    assert is_valid_redirect_uri("https://vertexaisearch.cloud.google.com/oauth-redirect") is True
    assert is_valid_redirect_uri("http://localhost/api/auth/callback") is True
    assert is_valid_redirect_uri("http://127.0.0.1/api/auth/callback/custom") is True
    assert is_valid_redirect_uri("https://partner.com/cb", client_uris=["https://partner.com/cb"]) is True

    # Malicious / Invalid targets
    assert is_valid_redirect_uri("javascript:alert(1)") is False
    assert is_valid_redirect_uri("data:text/html,<script>alert(1)</script>") is False
    assert is_valid_redirect_uri("http://attacker.com/oauth/callback") is False
    assert is_valid_redirect_uri("https://attacker.com/steal-code") is False
    assert is_valid_redirect_uri("https://chatgpt.com.attacker.com/auth/callback") is False


def test_bearer_token_resolution_and_proxy_headers():
    """Verifies that worker.js authenticates Bearer tokens and rewrites Authorization headers securely for upstream AWS Lambda."""
    content = worker_path.read_text(encoding="utf-8")

    # 1. Bearer token resolution logic
    assert "token.startsWith(\"extra_tok_\")" in content
    assert "oauth_token:" in content

    # 2. Rejection of unauthenticated or expired Bearer tokens with 401
    assert "Unauthorized: Invalid or expired Bearer access token" in content
    assert 'WWW-Authenticate": \'Bearer error="invalid_token"' in content

    # 3. Secure header rewriting before forwarding to upstream AWS Lambda
    assert 'reqHeaders.set("Host", targetUrl.hostname);' in content
    assert 'reqHeaders.set("X-Forwarded-Host", url.hostname);' in content
    assert 'reqHeaders.set("X-Forwarded-Proto", "https");' in content
    assert 'reqHeaders.set("Authorization", `Bearer ${effectiveRelayKey}`);' in content


def test_client_storage_and_cookie_attributes():
    """Verifies that src/utils/auth.ts enforces SameSite=Lax, Secure cookies and cleans credentials on 401."""
    assert auth_path.is_file(), f"auth.ts not found at {auth_path}"
    content = auth_path.read_text(encoding="utf-8")

    # 1. Cookie security attributes
    assert "SameSite=Lax" in content
    assert "secure" in content.lower()

    # 2. Clear authentication on 401 Unauthorized
    assert "if (res.status === 401)" in content
    assert "clearAuth()" in content

    # 3. clearAuth removes localStorage and sets cookie max-age=0
    assert "localStorage.removeItem(TOKEN_KEY)" in content
    assert "localStorage.removeItem(USER_KEY)" in content
    assert "max-age=0" in content


def test_edge_and_frontend_security_headers():
    """Verifies defense-in-depth security headers (HSTS, CSP, XFO, nosniff, Permissions-Policy) in worker.js and next.config.ts."""
    assert next_config_path.is_file(), f"next.config.ts not found at {next_config_path}"
    worker_content = worker_path.read_text(encoding="utf-8")
    next_content = next_config_path.read_text(encoding="utf-8")

    # Verify headers in worker.js (Edge level)
    assert 'resHeaders.set("X-Content-Type-Options", "nosniff")' in worker_content
    assert 'resHeaders.set("X-Frame-Options", "DENY")' in worker_content
    assert 'resHeaders.set("Referrer-Policy", "strict-origin-when-cross-origin")' in worker_content
    assert 'resHeaders.set("Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload")' in worker_content
    assert 'resHeaders.set("Permissions-Policy", "camera=(), microphone=(), geolocation=(), browsing-topics=()")' in worker_content

    # Verify CSP directives
    assert "frame-ancestors 'none'" in worker_content
    assert "base-uri 'self'" in worker_content
    assert "form-action 'self'" in worker_content

    # Verify defense-in-depth headers in next.config.ts (Build/Export level)
    assert 'key: "X-Frame-Options"' in next_content
    assert 'value: "DENY"' in next_content
    assert 'key: "X-Content-Type-Options"' in next_content
    assert 'value: "nosniff"' in next_content
    assert 'max-age=63072000; includeSubDomains; preload' in next_content
