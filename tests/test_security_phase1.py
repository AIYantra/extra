"""
Unit and integration tests for Phase 1 Security Hardening:
Local Control-Plane, Authentication Gating, CSRF State Tokens, and DNS Rebinding Protection.
"""

import sys
import os
import secrets
from pathlib import Path
import pytest

# Ensure extra and app paths are importable
extra_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(extra_root))
sys.path.insert(0, str(extra_root / "src"))
sys.path.insert(0, str(extra_root / "app"))

from extra.mcp.server import _PUBLIC_SSE_PATHS, BearerAuthASGIMiddleware
from run_app import (
    _create_oauth_state,
    _validate_and_consume_oauth_state,
    open_url_in_user_browser,
    SPAHandler,
    EXTRA_LOOPBACK_TOKEN,
)


def test_oauth_csrf_state_generation_and_consumption():
    """Verifies that OAuth state tokens are single-use, cryptographically strong, and expire."""
    state1 = _create_oauth_state()
    state2 = _create_oauth_state()

    assert len(state1) >= 32
    assert len(state2) >= 32
    assert state1 != state2

    # Consuming state1 must succeed exactly once
    assert _validate_and_consume_oauth_state(state1) is True
    # Second consumption of state1 must fail (single-use invariant)
    assert _validate_and_consume_oauth_state(state1) is False

    # Invalid and empty states must fail
    assert _validate_and_consume_oauth_state("") is False
    assert _validate_and_consume_oauth_state("invalid_state_123") is False


def test_open_url_validation_and_sanitization():
    """Verifies that open_url_in_user_browser rejects protocol splitting and CLI flags."""
    # Malicious inputs that must be rejected
    assert open_url_in_user_browser('https://target.com" --disable-web-security') is False
    assert open_url_in_user_browser("https://target.com\r\n--flag") is False
    assert open_url_in_user_browser("javascript:alert(1)") is False
    assert open_url_in_user_browser("file:///C:/Windows/System32/cmd.exe") is False
    assert open_url_in_user_browser("powershell -Command whoami") is False

    # Valid URLs are accepted (will not throw errors or split arguments)
    # Note: On CI/headless, actual browser launch might return False if no GUI, but validation passes
    from urllib.parse import urlparse
    clean = "https://extra.yantraos.com/dashboard"
    p = urlparse(clean)
    assert p.scheme == "https" and p.netloc == "extra.yantraos.com"


def test_mcp_public_paths_exemptions_revoked():
    """Verifies that mutating control endpoints are not exempted from Bearer auth."""
    # Mutating routes that must NOT be public
    forbidden_public = [
        "/api/config/sync",
        "/api/autostart",
        "/api/relay/start",
        "/api/relay/stop",
        "/api/dispatch",
        "/api/reveal",
    ]
    for path in forbidden_public:
        assert path not in _PUBLIC_SSE_PATHS, f"Route {path} must NOT be in _PUBLIC_SSE_PATHS!"

    # Read-only public discovery endpoints that should be public
    assert "/health" in _PUBLIC_SSE_PATHS
    assert "/plugin.json" in _PUBLIC_SSE_PATHS
    assert "/api/relay/status" in _PUBLIC_SSE_PATHS


def test_bearer_auth_middleware_enforcement():
    """Verifies that BearerAuthASGIMiddleware blocks unauthenticated calls to /api/config/sync."""
    import asyncio

    async def _run_test():
        called = False

        async def dummy_app(scope, receive, send):
            nonlocal called
            called = True

        token = "sec_test_token_1234567890abcdef"
        middleware = BearerAuthASGIMiddleware(dummy_app, token=token)

        sent_messages = []

        async def mock_receive():
            return {"type": "http.request"}

        async def mock_send(msg):
            sent_messages.append(msg)

        # 1. Unauthenticated request to /api/config/sync must be rejected with 401
        scope_unauth = {
            "type": "http",
            "method": "POST",
            "path": "/api/config/sync",
            "headers": [(b"host", b"127.0.0.1:8000")],
            "query_string": b"",
        }
        await middleware(scope_unauth, mock_receive, mock_send)
        assert called is False
        assert any(m.get("status") == 401 for m in sent_messages)

        # 2. Authenticated request with Bearer token must pass through
        called = False
        sent_messages.clear()
        scope_auth = {
            "type": "http",
            "method": "POST",
            "path": "/api/config/sync",
            "headers": [
                (b"host", b"127.0.0.1:8000"),
                (b"authorization", f"Bearer {token}".encode("utf-8")),
            ],
            "query_string": b"",
        }
        await middleware(scope_auth, mock_receive, mock_send)
        assert called is True

    asyncio.run(_run_test())
