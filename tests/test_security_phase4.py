"""
Unit and integration tests for Phase 4 Security Hardening:
Edge Worker, Script Delivery Security, OAuth PKCE, Token Revocation, XSS Escaping,
and HTTPS Origin Enforcement (extra.yantraos.com/worker.js).
"""

import sys
import os
import re
import subprocess
from pathlib import Path
import pytest

extra_root = Path(__file__).resolve().parents[1]
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
    test_script = extra_root.parent / "Artifacts" / "extra" / "test_worker_node.js"
    assert test_script.is_file(), f"test_worker_node.js not found at {test_script}"
    
    res = subprocess.run(
        ["node", str(test_script)],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert res.returncode == 0, f"Node test harness failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
    assert "All Node.js worker security tests passed successfully!" in res.stdout
