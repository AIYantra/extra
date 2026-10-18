"""
Project Extra — Linux Host Permissions & Environment Diagnostics
Verifies display server protocols (Wayland vs. X11), desktop environments,
kernel /dev/uinput input subsystem access, and AT-SPI2 accessibility bus.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from typing import Dict, Tuple


def get_session_type() -> str:
    """Returns 'wayland', 'x11', or 'unknown' based on active environment."""
    st = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if st:
        return st
    if os.environ.get("WAYLAND_DISPLAY"):
        return "wayland"
    if os.environ.get("DISPLAY"):
        return "x11"
    return "unknown"


def is_wayland() -> bool:
    """Returns True if running in a Wayland session."""
    return get_session_type() == "wayland"


def is_x11() -> bool:
    """Returns True if running in a native X11 session."""
    return get_session_type() == "x11"


def get_current_desktop() -> str:
    """Returns the desktop environment name (e.g. 'KDE', 'GNOME', 'XFCE', 'sway')."""
    d = os.environ.get("XDG_CURRENT_DESKTOP", "")
    if not d:
        d = os.environ.get("DESKTOP_SESSION", "")
    return d.strip()


def check_uinput_access() -> bool:
    """
    Verifies read/write access to /dev/uinput for kernel-level hardware event injection.
    Returns True if the current process can open /dev/uinput.
    """
    uinput_path = "/dev/uinput"
    if not os.path.exists(uinput_path):
        return False
    return os.access(uinput_path, os.R_OK | os.W_OK)


def check_atspi_bus() -> bool:
    """
    Checks if the AT-SPI2 accessibility D-Bus daemon is available.
    Verifies either the socket path at /run/user/<uid>/at-spi/bus_0 or org.a11y.Bus.
    """
    uid = os.getuid()
    socket_path = f"/run/user/{uid}/at-spi/bus_0"
    if os.path.exists(socket_path):
        return True

    # Fallback check via busctl or gdbus
    if shutil.which("busctl"):
        res = subprocess.run(
            ["busctl", "--user", "status", "org.a11y.Bus"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=1.0,
        )
        if res.returncode == 0:
            return True
    return False


def check_capture_backend() -> Tuple[bool, str]:
    """
    Detects the best available screen perception backend on the host.
    Returns (available: bool, backend_name: str).
    """
    if is_wayland():
        desktop = get_current_desktop().upper()
        if "KDE" in desktop and shutil.which("spectacle"):
            return True, "spectacle (KDE Wayland)"
        if shutil.which("grim"):
            return True, "grim (wlroots Wayland)"
        # Check portal
        if shutil.which("busctl"):
            res = subprocess.run(
                ["busctl", "--user", "status", "org.freedesktop.portal.Desktop"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=1.0,
            )
            if res.returncode == 0:
                return True, "XDG Portal ScreenCast (Wayland)"
        return False, "No Wayland capture tool found (install spectacle or grim)"
    else:
        # X11
        if shutil.which("scrot") or shutil.which("xwd"):
            return True, "X11 (MIT-SHM mss / scrot)"
        return True, "X11 (mss / XShm)"


def get_environment_summary() -> Dict[str, str]:
    """Returns a dictionary summarizing all Linux desktop environment attributes."""
    session = get_session_type()
    desktop = get_current_desktop() or "Generic / None"
    uinput_ok = check_uinput_access()
    atspi_ok = check_atspi_bus()
    cap_ok, cap_name = check_capture_backend()

    return {
        "session_type": session,
        "desktop": desktop,
        "uinput_accessible": "Yes" if uinput_ok else "No (requires 'input' group or udev rule)",
        "atspi_bus": "Active" if atspi_ok else "Inactive",
        "capture_backend": cap_name if cap_ok else "Unavailable",
    }


def print_guidance_card() -> None:
    """Prints terminal setup guidance for any missing permissions."""
    print("=" * 65)
    print(" EXTRA LINUX HARDWARE & ACCESS GUIDANCE")
    print("=" * 65)
    if not check_uinput_access():
        print("  [ACTION NEEDED] /dev/uinput access required for hardware input.")
        print("  Add your user to the 'input' group:")
        print("    sudo usermod -aG input $USER")
        print("  Or add a udev rule:")
        print("    echo 'KERNEL==\"uinput\", GROUP=\"input\", MODE=\"0660\"' | sudo tee /etc/udev/rules.d/99-uinput.rules")
        print("    sudo udevadm control --reload-rules && sudo udevadm trigger")
        print("  (Note: Log out and log back in for group changes to take effect)")
    if not check_atspi_bus():
        print("  [WARN] AT-SPI2 Accessibility bus not detected.")
        print("  Enable accessibility for semantic UI navigation:")
        print("    gsettings set org.gnome.desktop.interface toolkit-accessibility true")
        print("    or ensure 'at-spi2-core' is installed.")
    print("=" * 65)
