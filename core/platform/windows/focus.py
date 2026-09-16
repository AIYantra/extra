"""
Project Extra — Win32 Window Focus & Foreground Enforcer
Bypasses Windows LockSetForegroundWindow restrictions using AttachThreadInput,
providing guaranteed window activation, enumeration, and title/PID search.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
import time
from typing import List, Optional, Tuple

try:
    import psutil
except ImportError:
    psutil = None

import win32con
import win32gui
import win32process

from extra.core.platform.base import AbstractFocusManager, WindowInfo
from extra.core.platform.windows.geometry import attach_input_desktop, ensure_dpi_aware

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

SW_RESTORE = 9
SW_SHOW = 5
SPI_SETFOREGROUNDLOCKTIMEOUT = 0x2001
SPIF_SENDCHANGE = 0x0002
LSFW_UNLOCK = 2


def get_window_info(hwnd: int) -> Optional[WindowInfo]:
    """Retrieves detailed WindowInfo for a specific window handle."""
    if not hwnd or not win32gui.IsWindow(hwnd):
        return None

    title = win32gui.GetWindowText(hwnd).strip()
    class_name = win32gui.GetClassName(hwnd)
    _, pid = win32process.GetWindowThreadProcessId(hwnd)

    proc_name = "unknown"
    if psutil is not None:
        try:
            proc = psutil.Process(pid)
            proc_name = proc.name()
        except Exception:
            pass

    if proc_name == "unknown" and pid:
        # Fallback to pure Win32 QueryFullProcessImageNameW
        try:
            h_proc = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
            if h_proc:
                buf = ctypes.create_unicode_buffer(512)
                size = wintypes.DWORD(512)
                if kernel32.QueryFullProcessImageNameW(h_proc, 0, buf, ctypes.byref(size)):
                    proc_name = os.path.basename(buf.value)
                kernel32.CloseHandle(h_proc)
        except Exception:
            pass

    try:
        rect = win32gui.GetWindowRect(hwnd)
    except Exception:
        rect = (0, 0, 0, 0)

    is_visible = bool(win32gui.IsWindowVisible(hwnd))
    is_minimized = bool(win32gui.IsIconic(hwnd))

    return WindowInfo(
        hwnd=hwnd,
        title=title,
        class_name=class_name,
        process_id=pid,
        process_name=proc_name,
        rect=rect,
        is_visible=is_visible,
        is_minimized=is_minimized,
    )


def get_foreground_window() -> Optional[WindowInfo]:
    """Returns the WindowInfo for the currently focused foreground window."""
    ensure_dpi_aware()
    attach_input_desktop()
    hwnd = win32gui.GetForegroundWindow()
    return get_window_info(hwnd)


def list_windows(visible_only: bool = True) -> List[WindowInfo]:
    """Enumerates all top-level desktop windows."""
    ensure_dpi_aware()
    attach_input_desktop()
    results: List[WindowInfo] = []
    hwnds: List[int] = []

    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def _enum_callback(hwnd: int, lparam: int) -> bool:
        hwnds.append(hwnd)
        return True

    proc = WNDENUMPROC(_enum_callback)
    try:
        user32.EnumWindows(proc, 0)
    except Exception:
        pass

    for hwnd in hwnds:
        try:
            if visible_only and not win32gui.IsWindowVisible(hwnd):
                continue
            title = win32gui.GetWindowText(hwnd).strip()
            if visible_only and not title:
                continue
            info = get_window_info(hwnd)
            if info:
                results.append(info)
        except Exception:
            continue

    return results


def find_window_by_title(
    query: str, exact: bool = False, visible_only: bool = True
) -> Optional[WindowInfo]:
    """Finds the first window matching title substring or exact string."""
    q = query.strip().lower()
    windows = list_windows(visible_only=visible_only)

    for win in windows:
        w_title = win.title.lower()
        if exact:
            if w_title == q:
                return win
        else:
            if q in w_title:
                return win
    return None


def find_windows_by_process(
    process_name: str, visible_only: bool = True
) -> List[WindowInfo]:
    """Finds all windows belonging to a given process executable name."""
    p_query = process_name.lower().rstrip(".exe")
    windows = list_windows(visible_only=visible_only)
    return [
        w
        for w in windows
        if w.process_name.lower().rstrip(".exe") == p_query
    ]


def force_activate_window(hwnd: int) -> bool:
    """
    Bypasses Windows LockSetForegroundWindow restrictions to forcefully
    activate, restore, and focus the target window using AttachThreadInput.
    """
    if not hwnd or not win32gui.IsWindow(hwnd):
        return False

    ensure_dpi_aware()
    attach_input_desktop()

    # 1. Restore if minimized
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, SW_RESTORE)
        time.sleep(0.05)

    cur_thread = kernel32.GetCurrentThreadId()
    fg_hwnd = user32.GetForegroundWindow()
    fg_thread = user32.GetWindowThreadProcessId(fg_hwnd, None) if fg_hwnd else 0

    attached = False
    if fg_thread and cur_thread != fg_thread:
        attached = bool(user32.AttachThreadInput(cur_thread, fg_thread, True))

    try:
        # Unlock foreground lock timeout
        user32.SystemParametersInfoW(
            SPI_SETFOREGROUNDLOCKTIMEOUT, 0, 0, SPIF_SENDCHANGE
        )

        # Set foreground window
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        user32.SetFocus(hwnd)
        time.sleep(0.02)
    finally:
        if attached:
            user32.AttachThreadInput(cur_thread, fg_thread, False)

    # Check if successfully foregrounded
    return user32.GetForegroundWindow() == hwnd


class WindowsFocusManager(AbstractFocusManager):
    """Windows implementation of the AbstractFocusManager interface."""

    def get_window_info(self, hwnd: int) -> Optional[WindowInfo]:
        return get_window_info(hwnd)

    def get_foreground_window(self) -> Optional[WindowInfo]:
        return get_foreground_window()

    def list_windows(self, visible_only: bool = True) -> List[WindowInfo]:
        return list_windows(visible_only=visible_only)

    def find_window_by_title(
        self, query: str, exact: bool = False, visible_only: bool = True
    ) -> Optional[WindowInfo]:
        return find_window_by_title(query=query, exact=exact, visible_only=visible_only)

    def find_windows_by_process(
        self, process_name: str, visible_only: bool = True
    ) -> List[WindowInfo]:
        return find_windows_by_process(process_name=process_name, visible_only=visible_only)

    def force_activate_window(self, hwnd: int) -> bool:
        return force_activate_window(hwnd=hwnd)
