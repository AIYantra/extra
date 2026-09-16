"""
Project Extra — macOS TCC Privacy & Security Permissions Subsystem
Implements Pillar 3 of the Extra for macOS Universal Launch Plan:
1. Accessibility check (AXUIElement / AXIsProcessTrusted)
2. Screen Recording check (ScreenCaptureKit / CGPreflightScreenCaptureAccess)
3. 1-Click deep-link openers to System Settings panes
4. Interactive terminal guidance card
5. TCC recovery and reset commands (tccutil)
"""

from __future__ import annotations

import logging
import platform
import subprocess
from typing import Dict, Optional, Tuple

logger = logging.getLogger("extra.permissions.macos")

# Official macOS TCC System Settings URL schemes
URL_ACCESSIBILITY = "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
URL_SCREEN_CAPTURE = "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture"

# Standard client bundle identifiers for tccutil management
CLIENT_BUNDLE_MAP: Dict[str, str] = {
    "terminal": "com.apple.Terminal",
    "iterm": "com.googlecode.iterm2",
    "iterm2": "com.googlecode.iterm2",
    "claude": "com.anthropic.claudedesktop",
    "claudedesktop": "com.anthropic.claudedesktop",
    "cursor": "com.todesktop.230313mzl4w4u92",
    "windsurf": "com.codeium.windsurf",
}


def check_accessibility() -> bool:
    """
    Verifies whether the current process or terminal host has been granted
    macOS Accessibility permissions (AXUIElement / CGEventTap).
    """
    if platform.system() != "Darwin":
        return True

    try:
        import ApplicationServices as AX
        if hasattr(AX, "AXIsProcessTrusted"):
            return bool(AX.AXIsProcessTrusted())
    except Exception as e:
        logger.debug(f"Accessibility check exception: {e}")

    return False


def check_screen_recording() -> bool:
    """
    Verifies whether the current process or terminal host has been granted
    macOS Screen Recording permissions (ScreenCaptureKit / Quartz).
    """
    if platform.system() != "Darwin":
        return True

    try:
        import Quartz.CoreGraphics as CG
        if hasattr(CG, "CGPreflightScreenCaptureAccess"):
            return bool(CG.CGPreflightScreenCaptureAccess())
    except Exception as e:
        logger.debug(f"Screen Recording check exception: {e}")

    return False


def verify_all_permissions() -> Tuple[bool, bool]:
    """
    Checks both required permissions on macOS.
    Returns (has_accessibility, has_screen_recording).
    """
    return check_accessibility(), check_screen_recording()


def open_accessibility_settings() -> bool:
    """Deep-links directly to the macOS Accessibility System Settings pane."""
    if platform.system() != "Darwin":
        return False
    try:
        subprocess.run(["open", URL_ACCESSIBILITY], check=True)
        return True
    except Exception as e:
        logger.warning(f"Failed to open Accessibility settings: {e}")
        return False


def open_screen_recording_settings() -> bool:
    """Deep-links directly to the macOS Screen Recording System Settings pane."""
    if platform.system() != "Darwin":
        return False
    try:
        subprocess.run(["open", URL_SCREEN_CAPTURE], check=True)
        return True
    except Exception as e:
        logger.warning(f"Failed to open Screen Recording settings: {e}")
        return False


def open_all_permissions_settings() -> bool:
    """Opens both Accessibility and Screen Recording System Settings panes."""
    ok1 = open_accessibility_settings()
    ok2 = open_screen_recording_settings()
    return ok1 or ok2


def reset_permissions(client: str = "Terminal") -> Tuple[bool, str]:
    """
    Resets TCC permissions for a given client application using tccutil.
    Helps resolve corrupted or stuck permission states.
    """
    if platform.system() != "Darwin":
        return False, "tccutil is only available on macOS."

    client_key = client.lower().strip()
    bundle_id = CLIENT_BUNDLE_MAP.get(client_key, client)

    logs = []
    success = True
    for service in ["Accessibility", "ScreenCapture"]:
        cmd = ["tccutil", "reset", service, bundle_id]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                logs.append(f"Reset {service} for {bundle_id}: [OK]")
            else:
                logs.append(f"Reset {service} for {bundle_id}: {res.stderr.strip()}")
                success = False
        except Exception as e:
            logs.append(f"Reset {service} for {bundle_id} failed: {e}")
            success = False

    return success, "\n".join(logs)


def get_guidance_card() -> str:
    """
    Renders the formatted interactive terminal guidance card
    for macOS accessibility and screen capture permissions.
    """
    return """\
┌────────────────────────────────────────────────────────────────────────┐
│               ACTION REQUIRED: MACOS SECURITY PERMISSIONS              │
├────────────────────────────────────────────────────────────────────────┤
│ Extra requires two standard permissions to automate your Mac:          │
│                                                                        │
│ 1. Accessibility:                                                      │
│    Run: open "x-apple.systempreferences:com.apple.preference.security? │
│               Privacy_Accessibility"                                   │
│    -> Toggle ON: Terminal / iTerm2 / Claude Desktop                    │
│                                                                        │
│ 2. Screen Recording:                                                   │
│    Run: open "x-apple.systempreferences:com.apple.preference.security? │
│               Privacy_ScreenCapture"                                   │
│    -> Toggle ON: Terminal / iTerm2 / Claude Desktop                    │
│                                                                        │
│ Once enabled, run 'extra doctor' to verify all checks pass [OK].       │
└────────────────────────────────────────────────────────────────────────┘"""


def print_guidance_card() -> None:
    """Prints the formatted terminal guidance card."""
    print("\n" + get_guidance_card() + "\n")
