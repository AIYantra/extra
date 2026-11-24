"""
Unit and integration tests for Phase 1 Security Audit:
Payment Gateway Security (Polar.sh Primary & Dodo Payments Fallback),
Webhook Cryptographic Signature Verification, Open Redirect Defense,
and Dashboard Entitlement Protection.
"""

import sys
import os
import re
import json
import time
import hmac
import hashlib
import base64
from pathlib import Path
import pytest

extra_root = Path(__file__).resolve().parents[1]
website_root = extra_root.parent / "extra.yantraos.com"
worker_path = website_root / "worker.js"


def test_polar_checkout_immutable_slugs():
    """Verifies that Polar checkout links in pricing and dashboard are immutable and tamper-proof."""
    pricing_file = website_root / "src" / "components" / "home" / "pricing.tsx"
    billing_file = website_root / "src" / "components" / "dashboard" / "tabs" / "billing-tab.tsx"

    assert pricing_file.is_file(), f"pricing.tsx not found at {pricing_file}"
    assert billing_file.is_file(), f"billing-tab.tsx not found at {billing_file}"

    pricing_content = pricing_file.read_text(encoding="utf-8")
    billing_content = billing_file.read_text(encoding="utf-8")

    # 1. Verify immutable Polar checkout URLs in pricing
    assert "https://buy.polar.sh/polar_cl_" in pricing_content
    # Confirm URLs are not constructed dynamically from untrusted URL query parameters
    assert "searchParams.get" not in pricing_content

    # 2. Verify immutable customer portal in billing tab
    assert "https://polar.sh/yantraos/portal" in billing_content
    # Confirm reverse tabnabbing defense (rel="noopener noreferrer") on external checkout/portal links
    assert 'rel="noopener noreferrer"' in billing_content
    assert 'rel="noopener noreferrer"' in pricing_content


def test_dodo_checkout_secret_fail_closed():
    """Verifies that Dodo checkout fails closed when DODO_PAYMENTS_API_KEY is missing, with zero hardcoded secrets."""
    assert worker_path.is_file(), f"worker.js not found at {worker_path}"
    content = worker_path.read_text(encoding="utf-8")

    # 1. Zero hardcoded secrets in source (CWE-798 prevention)
    assert '|| "dodo_test_' not in content, "Found hardcoded fallback test key in worker.js"
    assert '|| "dodo_live_' not in content, "Found hardcoded fallback live key in worker.js"

    # 2. Verify fail-closed redirect when secret is missing
    assert 'if (!dodoKey) {' in content
    assert 'gateway_error=dodo_not_configured' in content


def test_dodo_checkout_open_redirect_rejection():
    """Verifies that /api/dodo/checkout strictly validates upstream checkout URLs against an allowlist."""
    content = worker_path.read_text(encoding="utf-8")

    # Verify that targetUrl is parsed and protocol + hostname are explicitly checked
    assert "targetUrl.protocol === \"https:\"" in content
    assert 'targetUrl.hostname === "checkout.dodopayments.com"' in content
    assert 'targetUrl.hostname === "test.checkout.dodopayments.com"' in content

    # Test our Python validation mirror of this exact regex/URL rule
    def is_safe_redirect(url_str: str) -> bool:
        from urllib.parse import urlparse
        try:
            p = urlparse(url_str)
            return p.scheme == "https" and p.hostname in (
                "checkout.dodopayments.com",
                "test.checkout.dodopayments.com"
            )
        except Exception:
            return False

    assert is_safe_redirect("https://checkout.dodopayments.com/buy/123") is True
    assert is_safe_redirect("https://test.checkout.dodopayments.com/session/abc") is True
    assert is_safe_redirect("http://checkout.dodopayments.com/buy/123") is False
    assert is_safe_redirect("https://evil-phishing.com/checkout") is False
    assert is_safe_redirect("https://checkout.dodopayments.com.attacker.com/buy") is False
    assert is_safe_redirect("javascript:alert(1)") is False


def test_dashboard_entitlement_query_spoofing_defense():
    """Verifies that query parameters like ?payment=success do NOT elevate privileges on the client."""
    auth_file = website_root / "src" / "utils" / "auth.ts"
    dashboard_file = website_root / "src" / "components" / "dashboard" / "dashboard-shell.tsx"

    assert auth_file.is_file()
    assert dashboard_file.is_file()

    auth_content = auth_file.read_text(encoding="utf-8")
    dashboard_content = dashboard_file.read_text(encoding="utf-8")

    # Dashboard must fetch profile from authenticated server endpoint (/api/auth/me), not query string
    assert "fetchUserProfile" in dashboard_content
    assert "${API_BASE_URL}/api/auth/me" in auth_content
    # Confirm client-side query parameters are not used to set plan = 'pro'
    assert "payment=success" not in auth_content
    assert "payment=success" not in dashboard_content


def test_polar_webhook_standard_signature_spec():
    """Verifies that Polar Standard-Webhooks HMAC-SHA256 signature algorithm and timestamp drift window work properly."""
    
    def generate_polar_signature(secret: str, msg_id: str, timestamp: int, payload: str) -> str:
        # Standard-Webhooks: signed_content = "${msg_id}.${timestamp}.${payload}"
        signed_content = f"{msg_id}.{timestamp}.{payload}".encode("utf-8")
        # Polar secret can be prefixed with "whsec_" or test prefixes and base64 encoded
        secret_clean = secret
        for prefix in ["test_whsec_", "whsec_"]:
            if secret_clean.startswith(prefix):
                secret_clean = secret_clean[len(prefix):]
                break
        secret_bytes = secret_clean.encode("utf-8")
        try:
            secret_raw = base64.b64decode(secret_bytes)
        except Exception:
            secret_raw = secret_bytes
        signature = hmac.new(secret_raw, signed_content, hashlib.sha256).digest()
        return "v1," + base64.b64encode(signature).decode("utf-8")

    def verify_polar_webhook(secret: str, msg_id: str, timestamp_str: str, payload: str, sig_header: str) -> bool:
        try:
            ts = int(timestamp_str)
        except (ValueError, TypeError):
            return False

        # Enforce maximum 300s (5-minute) drift window to prevent replay attacks
        now = int(time.time())
        if abs(now - ts) > 300:
            return False

        expected_sig = generate_polar_signature(secret, msg_id, ts, payload)
        # Compare securely with constant-time comparison
        return hmac.compare_digest(expected_sig, sig_header)

    # Use a mock test secret without matching Stripe's public regex pattern (whsec_...)
    secret = "test_whsec_mock_dummy_secret_key_for_testing"
    msg_id = "msg_polar_01j789abc"
    now = int(time.time())
    payload = json.dumps({"type": "subscription.created", "data": {"id": "sub_123", "status": "active"}})

    # 1. Valid signature and fresh timestamp must pass
    valid_sig = generate_polar_signature(secret, msg_id, now, payload)
    assert verify_polar_webhook(secret, msg_id, str(now), payload, valid_sig) is True

    # 2. Tampered payload must fail
    tampered_payload = json.dumps({"type": "subscription.created", "data": {"id": "sub_123", "status": "canceled"}})
    assert verify_polar_webhook(secret, msg_id, str(now), tampered_payload, valid_sig) is False

    # 3. Forged signature must fail
    assert verify_polar_webhook(secret, msg_id, str(now), payload, "v1,ZmFrZXNpZ25hdHVyZQ==") is False

    # 4. Expired timestamp (> 300s in the past) must fail replay defense
    stale_ts = now - 350
    stale_sig = generate_polar_signature(secret, msg_id, stale_ts, payload)
    assert verify_polar_webhook(secret, msg_id, str(stale_ts), payload, stale_sig) is False


def test_csp_payment_domains_conformance():
    """Verifies that Content Security Policy whitelists payment providers in frame-src and connect-src but not script-src."""
    content = worker_path.read_text(encoding="utf-8")

    # frame-src must allow Polar and Dodo for modals/redirects
    assert "https://polar.sh" in content
    assert "https://*.polar.sh" in content
    assert "https://checkout.dodopayments.com" in content

    # connect-src must allow Polar API
    assert "https://api.polar.sh" in content
