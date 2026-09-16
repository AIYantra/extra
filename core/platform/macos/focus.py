"""
Project Extra — macOS Window Focus & NSWorkspace Management
Enumerates top-level macOS application windows via CGWindowListCopyWindowInfo and
forces foreground activation using NSRunningApplication, AXUIElement, and AppleScript.
"""

from __future__ import annotations

import subprocess
import time
from typing import List, Optional

from extra.core.platform.base import AbstractFocusManager, WindowInfo

try:
    import Quartz.CoreGraphics as CG
    from AppKit import (
        NSApplicationActivateIgnoringOtherApps,
        NSRunningApplication,
        NSWorkspace,
    )
except ImportError:
    CG = None
    NSWorkspace = None
    NSRunningApplication = None
    NSApplicationActivateIgnoringOtherApps = 2

try:
    import ApplicationServices as AX
except ImportError:
    AX = None


def list_windows(visible_only: bool = True) -> List[WindowInfo]:
    """Enumerates top-level application windows on macOS."""
    if CG is None:
        return []

    opts = CG.kCGWindowListOptionOnScreenOnly if visible_only else CG.kCGWindowListOptionAll
    opts |= CG.kCGWindowListExcludeDesktopElements
    window_list = CG.CGWindowListCopyWindowInfo(opts, CG.kCGNullWindowID)
    if not window_list:
        return []

    results: List[WindowInfo] = []
    for win in window_list:
        layer = win.get("kCGWindowLayer", 0)
        # Standard user app windows live on layer 0
        if layer != 0:
            continue

        hwnd = int(win.get("kCGWindowNumber", 0))
        title = str(win.get("kCGWindowName") or "").strip()
        owner = str(win.get("kCGWindowOwnerName") or "").strip()
        pid = int(win.get("kCGWindowOwnerPID", 0))
        bounds = win.get("kCGWindowBounds", {})
        is_onscreen = bool(win.get("kCGWindowIsOnscreen", True))

        x = int(bounds.get("X", 0))
        y = int(bounds.get("Y", 0))
        w = int(bounds.get("Width", 0))
        h = int(bounds.get("Height", 0))

        if visible_only and (w <= 10 or h <= 10 or not is_onscreen):
            continue

        display_title = title if title else owner
        results.append(
            WindowInfo(
                hwnd=hwnd,
                title=display_title,
                class_name="NSWindow",
                process_id=pid,
                process_name=owner,
                rect=(x, y, x + w, y + h),
                is_visible=is_onscreen,
                is_minimized=not is_onscreen,
            )
        )

    return results


def get_foreground_window() -> Optional[WindowInfo]:
    """Returns the frontmost application window on macOS."""
    if NSWorkspace is None:
        return None

    try:
        active_app = NSWorkspace.sharedWorkspace().frontmostApplication()
        if not active_app:
            return None
        pid = int(active_app.processIdentifier())
    except Exception:
        return None

    windows = list_windows(visible_only=True)
    for win in windows:
        if win.process_id == pid:
            return win

    # If no window on layer 0 is visible yet, return basic window info
    app_name = str(active_app.localizedName() or "Unknown")
    return WindowInfo(
        hwnd=0,
        title=app_name,
        class_name="NSApplication",
        process_id=pid,
        process_name=app_name,
        rect=(0, 0, 0, 0),
        is_visible=True,
        is_minimized=False,
    )


def get_window_info(hwnd: int) -> Optional[WindowInfo]:
    """Retrieves detailed WindowInfo for a specific window ID (hwnd)."""
    windows = list_windows(visible_only=False)
    for win in windows:
        if win.hwnd == hwnd:
            return win
    return None


def find_window_by_title(
    query: str, exact: bool = False, visible_only: bool = True, timeout: float = 0.0
) -> Optional[WindowInfo]:
    """Finds the first window matching query in title or process name, optionally polling up to timeout seconds."""
    deadline = time.perf_counter() + max(0.0, timeout)
    q = query.strip().lower()

    while True:
        for win in list_windows(visible_only=visible_only):
            title = win.title.lower()
            proc = win.process_name.lower()
            if exact:
                if title == q or proc == q:
                    return win
            else:
                if q in title or q in proc:
                    return win

        if time.perf_counter() >= deadline:
            break
        time.sleep(0.1)

    return None


def find_windows_by_process(
    process_name: str, visible_only: bool = True
) -> List[WindowInfo]:
    """Finds all windows belonging to an owner app name."""
    p = process_name.lower().rstrip(".app")
    results: List[WindowInfo] = []
    for w in list_windows(visible_only=visible_only):
        w_proc = w.process_name.lower().rstrip(".app")
        if w_proc == p or p in w_proc:
            results.append(w)
    return results


def force_activate_window(hwnd: int) -> bool:
    """
    Activates the application owning the given window number with high-priority focus.
    Uses NSRunningApplication activateWithOptions, with AXUIElement window raise
    and AppleScript activation fallback.
    """
    win = get_window_info(hwnd)
    if not win:
        return False

    success = False

    # 1. Primary: NSRunningApplication
    if NSRunningApplication is not None and win.process_id > 0:
        try:
            app = NSRunningApplication.runningApplicationWithProcessIdentifier_(win.process_id)
            if app:
                success = bool(app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps))
        except Exception:
            success = False

    # 2. Secondary: Raise specific window via Accessibility API if available
    if AX is not None and win.process_id > 0:
        try:
            app_elem = AX.AXUIElementCreateApplication(win.process_id)
            err, windows = AX.AXUIElementCopyAttributeValue(app_elem, "AXWindows", None)
            if err == 0 and windows:
                for w in windows:
                    AX.AXUIElementPerformAction(w, "AXRaise")
                    AX.AXUIElementSetAttributeValue(w, "AXMain", True)
                    success = True
                    break
        except Exception:
            pass

    # 3. Fallback: AppleScript tell application to activate
    if not success and win.process_name:
        try:
            script = f'tell application "{win.process_name}" to activate'
            res = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=1.5,
            )
            if res.returncode == 0:
                success = True
        except Exception:
            pass

    return success


class MacFocusManager(AbstractFocusManager):
    """macOS implementation of the AbstractFocusManager interface."""

    def get_window_info(self, hwnd: int) -> Optional[WindowInfo]:
        return get_window_info(hwnd)

    def get_foreground_window(self) -> Optional[WindowInfo]:
        return get_foreground_window()

    def list_windows(self, visible_only: bool = True) -> List[WindowInfo]:
        return list_windows(visible_only=visible_only)

    def find_window_by_title(
        self, query: str, exact: bool = False, visible_only: bool = True, timeout: float = 0.0
    ) -> Optional[WindowInfo]:
        return find_window_by_title(query, exact, visible_only, timeout=timeout)

    def find_windows_by_process(
        self, process_name: str, visible_only: bool = True
    ) -> List[WindowInfo]:
        return find_windows_by_process(process_name, visible_only)

    def force_activate_window(self, hwnd: int) -> bool:
        return force_activate_window(hwnd)
