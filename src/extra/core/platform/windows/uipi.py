"""
Project Extra — Win32 User Interface Privilege Isolation (UIPI) & Elevation Guard
Provides zero-overhead process token inspection and UIPI barrier detection.
Detects when a target window is running at High Integrity (Elevated) while Extra is at Medium Integrity,
preventing silent SendInput drops and providing deterministic diagnostic telemetry.
"""

from __future__ import annotations
import sys
import os
import logging
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger("extra.platform.windows.uipi")

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes
    import win32gui
    import win32process

    advapi32 = ctypes.windll.advapi32
    kernel32 = ctypes.windll.kernel32
    user32 = ctypes.windll.user32

    TOKEN_QUERY = 0x0008
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    TokenElevation = 20
    GA_ROOT = 2

    class TOKEN_ELEVATION(ctypes.Structure):
        _fields_ = [("TokenIsElevated", wintypes.DWORD)]

    class POINT(ctypes.Structure):
        _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

    # Explicit 64-bit Win32 prototypes to prevent pointer truncation / overflow
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    advapi32.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    advapi32.OpenProcessToken.restype = wintypes.BOOL
    advapi32.GetTokenInformation.argtypes = [
        wintypes.HANDLE,
        ctypes.c_uint,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    advapi32.GetTokenInformation.restype = wintypes.BOOL

    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.IsWindow.argtypes = [wintypes.HWND]
    user32.IsWindow.restype = wintypes.BOOL
    user32.WindowFromPoint.argtypes = [POINT]
    user32.WindowFromPoint.restype = wintypes.HWND
    user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetAncestor.restype = wintypes.HWND
    user32.GetForegroundWindow.restype = wintypes.HWND
else:
    ctypes = None
    wintypes = None
    win32gui = None
    win32process = None
    advapi32 = None
    kernel32 = None
    user32 = None


def is_current_process_elevated() -> bool:
    """Returns True if the current Extra process is running with Administrator elevation (High Integrity)."""
    if sys.platform != "win32" or advapi32 is None or kernel32 is None:
        return False

    h_token = wintypes.HANDLE()
    if not advapi32.OpenProcessToken(kernel32.GetCurrentProcess(), TOKEN_QUERY, ctypes.byref(h_token)):
        return False
    try:
        elevation = TOKEN_ELEVATION()
        cb_size = wintypes.DWORD(ctypes.sizeof(elevation))
        res = advapi32.GetTokenInformation(
            h_token,
            TokenElevation,
            ctypes.byref(elevation),
            cb_size,
            ctypes.byref(cb_size),
        )
        return bool(res and elevation.TokenIsElevated)
    except Exception as e:
        logger.debug("Failed to inspect current process token elevation: %s", e)
        return False
    finally:
        kernel32.CloseHandle(h_token)


def is_window_elevated(hwnd: int) -> bool:
    """Returns True if the process owning the window is running with Administrator elevation (High Integrity)."""
    if sys.platform != "win32" or advapi32 is None or kernel32 is None or user32 is None:
        return False

    if not hwnd or not user32.IsWindow(hwnd):
        return False

    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value:
        return False

    h_proc = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if not h_proc:
        return False

    try:
        h_token = wintypes.HANDLE()
        if not advapi32.OpenProcessToken(h_proc, TOKEN_QUERY, ctypes.byref(h_token)):
            return False
        try:
            elevation = TOKEN_ELEVATION()
            cb_size = wintypes.DWORD(ctypes.sizeof(elevation))
            res = advapi32.GetTokenInformation(
                h_token,
                TokenElevation,
                ctypes.byref(elevation),
                cb_size,
                ctypes.byref(cb_size),
            )
            return bool(res and elevation.TokenIsElevated)
        except Exception as e:
            logger.debug("Failed to inspect window PID %s token elevation: %s", pid.value, e)
            return False
        finally:
            kernel32.CloseHandle(h_token)
    finally:
        kernel32.CloseHandle(h_proc)


def get_root_window_at_point(x: int, y: int) -> Optional[int]:
    """Retrieves the top-level root window handle positioned at the physical screen coordinates (x, y)."""
    if sys.platform != "win32" or user32 is None:
        return None
    try:
        pt = POINT(int(x), int(y))
        child_hwnd = user32.WindowFromPoint(pt)
        if not child_hwnd:
            return None
        root_hwnd = user32.GetAncestor(child_hwnd, GA_ROOT)
        return root_hwnd if root_hwnd else child_hwnd
    except Exception as e:
        logger.debug("Failed to get root window at point (%s, %s): %s", x, y, e)
        return None


def check_uipi_barrier(hwnd: Optional[int] = None, coords: Optional[Tuple[int, int]] = None, window_title: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Detects if Windows User Interface Privilege Isolation (UIPI) will block synthetic inputs.
    Returns a structured advisory dict if a UIPI barrier is detected, or None if safe.
    """
    if sys.platform != "win32":
        return None

    # If Extra is already elevated to High Integrity, UIPI will never block inputs
    if is_current_process_elevated():
        return None

    target_hwnd = hwnd
    if (not target_hwnd or not user32.IsWindow(target_hwnd)) and coords:
        target_hwnd = get_root_window_at_point(coords[0], coords[1])

    if not target_hwnd or not user32.IsWindow(target_hwnd):
        # Fall back to active foreground window
        target_hwnd = user32.GetForegroundWindow()

    if not target_hwnd or not user32.IsWindow(target_hwnd):
        return None

    if is_window_elevated(target_hwnd):
        title = window_title
        if not title and win32gui is not None:
            try:
                title = win32gui.GetWindowText(target_hwnd).strip()
            except Exception:
                title = None
        target_name = f"'{title}'" if title else "Target window"

        return {
            "uipi_barrier": True,
            "target_elevated": True,
            "extra_elevated": False,
            "target_hwnd": target_hwnd,
            "target_title": title or "Unknown",
            "advisory": (
                f"Windows UIPI Barrier Detected: {target_name} is running with Administrator elevation (High Integrity), "
                "but Extra is running as a standard user. Windows kernel silently blocks synthetic mouse clicks and keystrokes. "
                "To automate this application, start Extra from an Administrator terminal (e.g. 'extra connect --elevate')."
            )
        }

    return None
