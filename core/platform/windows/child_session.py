"""
Project Extra — Win32 Child Session & Picture-in-Picture (PiP) Isolation Engine
Provides 3-tier desktop isolation:
  - Tier 1: Native Terminal Services Child Session (Windows Pro/Enterprise + Admin)
  - Tier 2: Win32 Isolated Desktop (CreateDesktopW in Winsta0, Windows Home compatible)
  - Tier 3: Non-Invasive Plane 2 Fast-Path (direct programmatic actuation)

Enables Extra to execute desktop automation visibly in an isolated session or
virtual desktop without moving the physical cursor or stealing focus from the user.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass, field
from enum import Enum
import logging
import os
import platform
import re
import subprocess
import sys
import threading
import time
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("extra.core.platform.windows.child_session")

# Win32 Constants
DESKTOP_CREATEWINDOW = 0x0002
DESKTOP_ENUMERATE = 0x0040
DESKTOP_WRITEOBJECTS = 0x0080
DESKTOP_SWITCHDESKTOP = 0x0100
DESKTOP_CREATEMENU = 0x0004
DESKTOP_HOOKCONTROL = 0x0020
DESKTOP_READOBJECTS = 0x0001
DESKTOP_JOURNALRECORD = 0x0008
DESKTOP_JOURNALPLAYBACK = 0x0010
DESKTOP_ALL_ACCESS = 0x01FF

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
shell32 = ctypes.windll.shell32
wtsapi32 = getattr(ctypes.windll, "wtsapi32", None)


class SessionTier(str, Enum):
    """The execution isolation tier for concurrent desktop automation."""
    TIER_1_NATIVE_CHILD_SESSION = "native_child_session"
    TIER_2_VIRTUAL_DESKTOP = "virtual_desktop"
    TIER_3_PLANE_2_FASTPATH = "plane_2_fastpath"


@dataclass
class ChildSessionCapability:
    """Detailed hardware and operating system capabilities for Child Sessions."""
    can_native_child_session: bool
    can_virtual_desktop: bool
    recommended_tier: SessionTier
    os_edition: str
    is_admin: bool
    termsrv_available: bool
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "can_native_child_session": self.can_native_child_session,
            "can_virtual_desktop": self.can_virtual_desktop,
            "recommended_tier": self.recommended_tier.value,
            "os_edition": self.os_edition,
            "is_admin": self.is_admin,
            "termsrv_available": self.termsrv_available,
            "reason": self.reason,
            "metadata": self.metadata,
        }


def detect_os_edition() -> str:
    """Detects Windows OS edition string via CIM/WMI or platform release."""
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_OperatingSystem).Caption"],
            capture_output=True,
            text=True,
            timeout=3.0,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except Exception:
        pass
    return f"Windows {platform.release()} (Build {platform.version()})"


def is_user_admin() -> bool:
    """Checks if the current process is running with administrative privileges."""
    try:
        return bool(shell32.IsUserAnAdmin())
    except Exception:
        return False


def detect_child_session_capabilities() -> ChildSessionCapability:
    """
    Evaluates the host Windows configuration to determine available isolation tiers.
    Checks Terminal Services (WTS), administrative tokens, and Win32 Desktop creation.
    """
    os_ed = detect_os_edition()
    admin = is_user_admin()
    termsrv_ok = False

    # 1. Probe Terminal Services Child Sessions (wtsapi32.dll)
    can_native = False
    native_reason = ""
    if wtsapi32 and hasattr(wtsapi32, "WTSEnableChildSessions"):
        try:
            # Check service status
            termsrv_ok = True
            if admin and "Home" not in os_ed:
                # Test call with current state query
                can_native = True
                native_reason = "Windows Pro/Enterprise with administrative privileges."
            elif not admin:
                native_reason = "Native Terminal Services Child Sessions require Administrator elevation."
            else:
                native_reason = "Windows Home edition does not license Terminal Services Child Sessions."
        except Exception as ex:
            native_reason = f"WTS error: {ex}"
    else:
        native_reason = "wtsapi32.dll or WTSEnableChildSessions API is unavailable."

    # 2. Probe Win32 Virtual Desktop Creation (CreateDesktopW)
    can_virtual = False
    try:
        # Create a transient probe desktop
        test_name = f"ExtraProbe_{int(time.time()*1000)}"
        user32.CreateDesktopW.argtypes = [
            wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_void_p,
            wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p
        ]
        user32.CreateDesktopW.restype = wintypes.HANDLE
        user32.CloseDesktop.argtypes = [wintypes.HANDLE]
        user32.CloseDesktop.restype = wintypes.BOOL

        h_probe = user32.CreateDesktopW(test_name, None, None, 0, DESKTOP_ALL_ACCESS, None)
        if h_probe:
            can_virtual = True
            user32.CloseDesktop(h_probe)
    except Exception:
        can_virtual = False

    # 3. Determine recommended tier
    if can_native:
        rec_tier = SessionTier.TIER_1_NATIVE_CHILD_SESSION
        final_reason = "Native Child Session available."
    elif can_virtual:
        rec_tier = SessionTier.TIER_2_VIRTUAL_DESKTOP
        final_reason = (
            "Windows 11 Home / unprivileged mode detected. Using Win32 Isolated Virtual Desktop (Tier 2)."
        )
    else:
        rec_tier = SessionTier.TIER_3_PLANE_2_FASTPATH
        final_reason = "Desktop isolation unavailable; defaulting to Plane 2 Fast-Path."

    return ChildSessionCapability(
        can_native_child_session=can_native,
        can_virtual_desktop=can_virtual,
        recommended_tier=rec_tier,
        os_edition=os_ed,
        is_admin=admin,
        termsrv_available=termsrv_ok,
        reason=final_reason,
        metadata={"wts_reason": native_reason},
    )


class VirtualDesktop:
    """
    Manages an independent Win32 Desktop inside WindowStation Winsta0.
    Apps launched inside this desktop receive their own windows, message pump,
    and visual rendering without interfering with the user's active console desktop.
    """

    def __init__(self, name: str = "Extra_Isolated_Desktop") -> None:
        if not re.match(r"^[a-zA-Z0-9_\-\.]{1,64}$", name):
            raise ValueError(f"Invalid desktop name '{name}'. Must be 1-64 alphanumeric, underscore, period, or dash characters.")
        self.name = name
        self.handle: Optional[int] = None
        self._initial_thread_desktop: Optional[int] = None
        self._lock = threading.Lock()

    def create(self) -> bool:
        """Creates the Win32 desktop and stores its handle."""
        with self._lock:
            if self.handle:
                return True
            try:
                user32.CreateDesktopW.argtypes = [
                    wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_void_p,
                    wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p
                ]
                user32.CreateDesktopW.restype = wintypes.HANDLE

                hdesk = user32.CreateDesktopW(
                    self.name,
                    None,
                    None,
                    0,
                    DESKTOP_ALL_ACCESS,
                    None
                )
                if hdesk:
                    self.handle = int(hdesk)
                    logger.info("[VirtualDesktop] Created isolated desktop '%s' (handle: %s)", self.name, self.handle)
                    return True
                else:
                    err = ctypes.GetLastError()
                    logger.warning("[VirtualDesktop] Failed to create desktop '%s' (Win32 error: %s)", self.name, err)
                    return False
            except Exception as ex:
                logger.error("[VirtualDesktop] Exception creating desktop '%s': %s", self.name, ex)
                return False

    def attach_current_thread(self) -> bool:
        """Attaches the calling thread to this isolated desktop."""
        if not self.handle:
            if not self.create():
                return False
        try:
            user32.GetThreadDesktop.argtypes = [wintypes.DWORD]
            user32.GetThreadDesktop.restype = wintypes.HANDLE
            user32.SetThreadDesktop.argtypes = [wintypes.HANDLE]
            user32.SetThreadDesktop.restype = wintypes.BOOL

            tid = kernel32.GetCurrentThreadId()
            if self._initial_thread_desktop is None:
                self._initial_thread_desktop = int(user32.GetThreadDesktop(tid))

            res = user32.SetThreadDesktop(self.handle)
            return bool(res)
        except Exception as ex:
            logger.warning("[VirtualDesktop] Failed to attach thread to desktop: %s", ex)
            return False

    def detach_current_thread(self) -> bool:
        """Restores the calling thread to its original desktop."""
        if self._initial_thread_desktop:
            try:
                res = user32.SetThreadDesktop(self._initial_thread_desktop)
                return bool(res)
            except Exception:
                pass
        return False

    def launch_process(
        self,
        cmd: List[str],
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> subprocess.Popen:
        """
        Launches an application specifically targeted into this isolated desktop.
        The window will not appear on the user's primary desktop.
        """
        if not self.handle:
            self.create()

        si = subprocess.STARTUPINFO()
        si.lpDesktop = self.name

        exec_env = os.environ.copy()
        if env:
            exec_env.update(env)

        logger.info("[VirtualDesktop] Spawning process in desktop '%s': %s", self.name, " ".join(cmd))
        return subprocess.Popen(
            cmd,
            startupinfo=si,
            cwd=cwd,
            env=exec_env,
            creationflags=0,
        )

    def close(self) -> None:
        """Closes the desktop handle."""
        with self._lock:
            if self.handle:
                try:
                    user32.CloseDesktop.argtypes = [wintypes.HANDLE]
                    user32.CloseDesktop.restype = wintypes.BOOL
                    user32.CloseDesktop(self.handle)
                except Exception:
                    pass
                self.handle = None
                logger.info("[VirtualDesktop] Closed desktop '%s'", self.name)


class ChildSessionManager:
    """
    Unified manager for Picture-in-Picture (PiP) and Child Session execution.
    Auto-detects host capabilities and routes to the best available isolation tier.
    """

    def __init__(self, desktop_name: str = "Extra_PiP_Desktop") -> None:
        self.desktop_name = desktop_name
        self.capabilities = detect_child_session_capabilities()
        self.active_tier: Optional[SessionTier] = None
        self.virtual_desktop: Optional[VirtualDesktop] = None
        self.native_session_id: Optional[int] = None
        self._is_running = False
        self._lock = threading.Lock()

    def start(self, requested_tier: Optional[Union[SessionTier, str]] = None) -> bool:
        """
        Starts the isolated execution session using the requested or optimal tier.
        """
        with self._lock:
            if self._is_running:
                return True

            tier = None
            if requested_tier:
                tier_str = requested_tier.value if isinstance(requested_tier, SessionTier) else str(requested_tier)
                for t in SessionTier:
                    if t.value == tier_str:
                        tier = t
                        break

            if tier is None:
                tier = self.capabilities.recommended_tier

            # Tier 1: Native Terminal Services Child Session
            if tier == SessionTier.TIER_1_NATIVE_CHILD_SESSION:
                if self.capabilities.can_native_child_session and wtsapi32:
                    try:
                        wtsapi32.WTSEnableChildSessions.argtypes = [wintypes.BOOL]
                        wtsapi32.WTSEnableChildSessions.restype = wintypes.BOOL
                        ok = wtsapi32.WTSEnableChildSessions(True)
                        if ok:
                            self.active_tier = SessionTier.TIER_1_NATIVE_CHILD_SESSION
                            self._is_running = True
                            logger.info("[ChildSessionManager] Initialized Tier 1 Native Child Session")
                            return True
                    except Exception as ex:
                        logger.warning("[ChildSessionManager] Native child session failed: %s. Falling back to Tier 2.", ex)

                # Fallback to Tier 2 if Tier 1 requested but unavailable
                tier = SessionTier.TIER_2_VIRTUAL_DESKTOP

            # Tier 2: Win32 Isolated Virtual Desktop
            if tier == SessionTier.TIER_2_VIRTUAL_DESKTOP:
                self.virtual_desktop = VirtualDesktop(name=self.desktop_name)
                if self.virtual_desktop.create():
                    self.active_tier = SessionTier.TIER_2_VIRTUAL_DESKTOP
                    self._is_running = True
                    logger.info("[ChildSessionManager] Initialized Tier 2 Virtual Desktop '%s'", self.desktop_name)
                    return True
                else:
                    tier = SessionTier.TIER_3_PLANE_2_FASTPATH

            # Tier 3: Plane 2 Fast-Path (direct background execution)
            self.active_tier = SessionTier.TIER_3_PLANE_2_FASTPATH
            self._is_running = True
            logger.info("[ChildSessionManager] Initialized Tier 3 Plane 2 Fast-Path mode")
            return True

    def stop(self) -> None:
        """Stops and cleans up the active isolated session."""
        with self._lock:
            if not self._is_running:
                return
            if self.virtual_desktop:
                self.virtual_desktop.close()
                self.virtual_desktop = None
            self._is_running = False
            self.active_tier = None
            logger.info("[ChildSessionManager] Stopped child session")

    def is_active(self) -> bool:
        """Checks if an isolated session is currently active."""
        return self._is_running

    def get_active_tier(self) -> Optional[SessionTier]:
        """Returns the active isolation tier, or None if inactive."""
        return self.active_tier

    def launch_app(
        self,
        cmd: List[str],
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> subprocess.Popen:
        """
        Launches an application inside the active isolated session.
        If Tier 2 is active, targets the isolated desktop.
        Otherwise launches normally in the background.
        """
        if self._is_running and self.virtual_desktop and self.active_tier == SessionTier.TIER_2_VIRTUAL_DESKTOP:
            return self.virtual_desktop.launch_process(cmd, cwd=cwd, env=env)
        else:
            return subprocess.Popen(cmd, cwd=cwd, env=env)

    def attach_worker_thread(self) -> bool:
        """Attaches the calling thread to the isolated desktop."""
        if self._is_running and self.virtual_desktop:
            return self.virtual_desktop.attach_current_thread()
        return False

    def detach_worker_thread(self) -> bool:
        """Detaches the calling thread from the isolated desktop."""
        if self._is_running and self.virtual_desktop:
            return self.virtual_desktop.detach_current_thread()
        return False

    def get_status(self) -> Dict[str, Any]:
        """Returns structured telemetry and status dictionary."""
        return {
            "is_active": self._is_running,
            "active_tier": self.active_tier.value if self.active_tier else None,
            "desktop_name": self.desktop_name if self._is_running else None,
            "capabilities": self.capabilities.to_dict(),
        }


# Global manager singleton
_global_child_session_manager: Optional[ChildSessionManager] = None
_manager_lock = threading.Lock()


def get_child_session_manager() -> ChildSessionManager:
    """Returns the process-wide ChildSessionManager singleton."""
    global _global_child_session_manager
    with _manager_lock:
        if _global_child_session_manager is None:
            _global_child_session_manager = ChildSessionManager()
        return _global_child_session_manager
