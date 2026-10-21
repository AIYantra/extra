"""
Project Extra - Automated Tunneling Subsystem
Provides zero-configuration, secure Cloudflare Quick Tunnels for remote Model Context Protocol (MCP)
transports, enabling seamless pairing with the OpenAI ChatGPT Universal Plugin Directory (chatgpt.com/plugins).
"""

from __future__ import annotations

import logging
import os
import platform
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger("extra.fastpath.tunnel")

_CLOUDFLARED_RELEASE_BASE = "https://github.com/cloudflare/cloudflared/releases/latest/download"


def get_extra_bin_dir() -> Path:
    """Returns the persistent user-level binary directory (~/.extra/bin)."""
    bin_dir = Path.home() / ".extra" / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    return bin_dir


def find_cloudflared_binary() -> Optional[Path]:
    """
    Locates the cloudflared executable in standard system locations or ~/.extra/bin.
    """
    # 1. Check system PATH
    system_path = shutil.which("cloudflared")
    if system_path:
        return Path(system_path)

    # 2. Check ~/.extra/bin
    bin_name = "cloudflared.exe" if sys.platform == "win32" else "cloudflared"
    local_bin = get_extra_bin_dir() / bin_name
    if local_bin.exists() and os.access(local_bin, os.X_OK if sys.platform != "win32" else os.R_OK):
        return local_bin

    # 3. Check known OS-specific default install paths
    candidates = []
    if sys.platform == "win32":
        candidates.extend([
            Path("C:/Program Files/cloudflared/cloudflared.exe"),
            Path("C:/Program Files (x86)/cloudflared/cloudflared.exe"),
        ])
    elif sys.platform == "darwin":
        candidates.extend([
            Path("/opt/homebrew/bin/cloudflared"),
            Path("/usr/local/bin/cloudflared"),
        ])
    else:
        candidates.extend([
            Path("/usr/local/bin/cloudflared"),
            Path("/usr/bin/cloudflared"),
        ])

    for c in candidates:
        if c.exists():
            return c

    return None


def ensure_cloudflared_installed() -> Optional[Path]:
    """
    Verifies that cloudflared is installed, or downloads the standalone zero-dependency
    binary directly into ~/.extra/bin on the fly.
    """
    existing = find_cloudflared_binary()
    if existing:
        return existing

    bin_dir = get_extra_bin_dir()
    os_name = sys.platform
    arch = platform.machine().lower()

    target_name = "cloudflared.exe" if os_name == "win32" else "cloudflared"
    target_path = bin_dir / target_name

    logger.info("Auto-provisioning secure Cloudflare Tunnel binary to %s...", target_path)

    try:
        if os_name == "win32":
            download_url = f"{_CLOUDFLARED_RELEASE_BASE}/cloudflared-windows-amd64.exe"
        elif os_name.startswith("linux"):
            if "arm" in arch or "aarch64" in arch:
                download_url = f"{_CLOUDFLARED_RELEASE_BASE}/cloudflared-linux-arm64"
            else:
                download_url = f"{_CLOUDFLARED_RELEASE_BASE}/cloudflared-linux-amd64"
        elif os_name == "darwin":
            if "arm" in arch:
                download_url = f"{_CLOUDFLARED_RELEASE_BASE}/cloudflared-darwin-arm64.tgz"
            else:
                download_url = f"{_CLOUDFLARED_RELEASE_BASE}/cloudflared-darwin-amd64.tgz"
        else:
            logger.error("Unsupported OS for automated cloudflared download: %s", os_name)
            return None

        # Download directly
        logger.info("Downloading %s ...", download_url)
        urllib.request.urlretrieve(download_url, str(target_path))

        if os_name != "win32":
            target_path.chmod(0o755)

        logger.info("Successfully provisioned cloudflared (%s bytes)", target_path.stat().st_size)
        return target_path

    except Exception as e:
        logger.error("Failed to auto-download cloudflared: %s", e)
        return None


def start_tunnel(
    local_port: int,
    host: str = "127.0.0.1",
    timeout_sec: float = 30.0,
) -> Tuple[Optional[subprocess.Popen], Optional[str]]:
    """
    Spawns a Cloudflare Quick Tunnel forwarding traffic to http://{host}:{local_port}.
    Returns a tuple of (process_handle, public_https_url).
    """
    bin_path = ensure_cloudflared_installed()
    if not bin_path:
        raise RuntimeError(
            "Could not find or install 'cloudflared'. Please install cloudflared manually: "
            "https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/"
        )

    cmd = [
        str(bin_path),
        "tunnel",
        "--url",
        f"http://{host}:{local_port}",
        "--no-autoupdate",
    ]

    logger.info("Spawning tunnel: %s", " ".join(cmd))

    # Cloudflare outputs progress and tunnel URL on stderr
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    tunnel_url: Optional[str] = None
    url_pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

    # Read output with timeout
    start_time = time.time()
    while time.time() - start_time < timeout_sec:
        if proc.poll() is not None:
            # Subprocess terminated prematurely
            err = proc.stderr.read() if proc.stderr else ""
            raise RuntimeError(f"cloudflared tunnel process exited unexpectedly with code {proc.returncode}: {err}")

        line = proc.stderr.readline() if proc.stderr else ""
        if not line:
            time.sleep(0.05)
            continue

        match = url_pattern.search(line)
        if match:
            tunnel_url = match.group(0)
            break

    if not tunnel_url:
        proc.terminate()
        try:
            proc.wait(timeout=3.0)
        except subprocess.TimeoutExpired:
            proc.kill()
        raise TimeoutError(f"Timed out after {timeout_sec}s waiting for Cloudflare Tunnel URL.")

    # Continue draining stderr in background thread to prevent pipe blocking
    def _drain_stderr():
        try:
            if proc.stderr:
                for _ in proc.stderr:
                    pass
        except Exception:
            pass

    t = threading.Thread(target=_drain_stderr, daemon=True)
    t.start()

    return proc, tunnel_url


def stop_tunnel(proc: Optional[subprocess.Popen]) -> None:
    """Cleanly terminates a running tunnel subprocess."""
    if not proc or proc.poll() is not None:
        return

    logger.info("Stopping Cloudflare Tunnel (PID: %s)...", proc.pid)
    try:
        proc.terminate()
        proc.wait(timeout=3.0)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def generate_secure_token() -> str:
    """Generates a secure 32-character hexadecimal Bearer authorization token."""
    return secrets.token_hex(16)


def format_chatgpt_banner(
    public_url: str,
    auth_token: Optional[str] = None,
    local_port: int = 8000,
) -> str:
    """Formats a step-by-step terminal connection guide for ChatGPT."""
    auth_display = auth_token if auth_token else "None (No authentication)"
    auth_step = f"Paste Bearer Token: {auth_token}" if auth_token else "Set Authentication to 'No authentication'"
    banner = f"""
==================================================================
  [EXTRA] Flashless MCP Server - Live ChatGPT Bridge Active
==================================================================

  [*] Server URL (Copy & Paste this into ChatGPT):
      {public_url}/mcp

  [*] Compatible Fallbacks: {public_url}/sse  or  {public_url}
  [*] Plugin Manifest:     {public_url}/.well-known/ai-plugin.json
  [*] Authentication:      {auth_display}
  [*] Local Port:          http://127.0.0.1:{local_port}

------------------------------------------------------------------
  >> IN CHATGPT (https://chatgpt.com/plugins or Connected Apps):
  1. Connection: Keep 'Server URL' selected
  2. In the URL box, paste:
     {public_url}/mcp
     (or {public_url}/sse)
  3. Authentication:
     {auth_step}
  4. Click 'Add' or 'Save'!
==================================================================
"""
    return banner
