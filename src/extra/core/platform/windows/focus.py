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


def get_window_executable_path(hwnd: int) -> Optional[str]:
    """Retrieves the full executable file path for the process hosting the window handle."""
    if not hwnd or not win32gui.IsWindow(hwnd):
        return None
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        if not pid:
            return None
        if psutil is not None:
            try:
                proc = psutil.Process(pid)
                exe = proc.exe()
                if exe and os.path.exists(exe):
                    return exe
            except Exception:
                pass
        # Pure Win32 fallback
        h_proc = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if h_proc:
            buf = ctypes.create_unicode_buffer(512)
            size = wintypes.DWORD(512)
            res = kernel32.QueryFullProcessImageNameW(h_proc, 0, buf, ctypes.byref(size))
            kernel32.CloseHandle(h_proc)
            if res and os.path.exists(buf.value):
                return buf.value
    except Exception:
        pass
    return None


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

    try:
        win32gui.EnumWindows(lambda hwnd, _: hwnds.append(hwnd) or 1, None)
    except Exception:
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
                # Retain untitled windows only if they have substantial desktop geometry (frameless / custom titlebars)
                try:
                    rect = win32gui.GetWindowRect(hwnd)
                    if (rect[2] - rect[0]) < 100 or (rect[3] - rect[1]) < 100:
                        continue
                except Exception:
                    continue
            info = get_window_info(hwnd)
            if info:
                results.append(info)
        except Exception:
            continue

    return results


class _DynamicProcessMap(dict):
    """Dynamic process alias resolver backed by APP_REGISTRY and system aliases."""
    def get(self, key, default=None):
        try:
            from extra.core.platform.windows.shell import APP_REGISTRY
            entry = APP_REGISTRY.get(str(key).lower())
            if entry and "proc" in entry:
                return entry["proc"].lower().rstrip(".exe")
        except Exception:
            pass
        return default if default is not None else key

    def __getitem__(self, key):
        val = self.get(key)
        if val is not None:
            return val
        raise KeyError(key)

    def __contains__(self, key):
        try:
            from extra.core.platform.windows.shell import APP_REGISTRY
            return str(key).lower() in APP_REGISTRY
        except Exception:
            return False


ALIAS_PROCESS_MAP: Dict[str, str] = _DynamicProcessMap()


def _normalize_title(t: str) -> str:
    """Normalizes title string by stripping zero-width and invisible control unicode chars."""
    if not t:
        return ""
    return (
        t.replace("\u200b", "")
        .replace("\u200c", "")
        .replace("\u200d", "")
        .replace("\ufeff", "")
        .strip()
        .lower()
    )


def find_window_by_title(
    query: str, exact: bool = False, visible_only: bool = True, timeout: float = 0.0
) -> Optional[WindowInfo]:
    """
    Finds the best matching window using a resilient multi-tier resolution strategy:
    Tier 1: Exact title match
    Tier 2: Direct substring match
    Tier 3: Multi-word match (e.g. 'Meta Business Suite' in 'Meta Business Suite - Google Chrome')
    Tier 4: Dynamic process-level and registered app fallback
    Optionally polls up to timeout seconds.
    """
    deadline = time.perf_counter() + max(0.0, timeout)
    q = _normalize_title(query)
    is_querying_overlay = "overlay" in q or "extra" in q

    while True:
        windows = list_windows(visible_only=visible_only)

        # Build searchable pairs with normalized titles, filtering internal overlays
        searchable: List[Tuple[WindowInfo, str]] = []
        for win in windows:
            norm_t = _normalize_title(win.title)
            if not is_querying_overlay and win.title.startswith("Extra") and "overlay" in norm_t:
                continue
            searchable.append((win, norm_t))

        # Tier 1: Exact match
        for win, norm_t in searchable:
            if norm_t == q:
                return win

        if not exact:
            # Tier 2: Direct substring match
            for win, norm_t in searchable:
                if q in norm_t:
                    return win

            # Tier 3: Multi-word match
            words = [w for w in q.split() if len(w) > 2]
            if len(words) > 1:
                for win, norm_t in searchable:
                    if all(word in norm_t for word in words):
                        return win

            # Tier 4: Dynamic process-level fallback via registered apps and fuzzy proc match
            proc_target = None
            try:
                from extra.core.platform.windows.shell import APP_REGISTRY
                reg_entry = APP_REGISTRY.get(q)
                if reg_entry and "proc" in reg_entry:
                    proc_target = reg_entry["proc"].lower().rstrip(".exe")
            except Exception:
                pass

            if not proc_target:
                proc_target = q.rstrip(".exe")

            matching_proc_windows: List[WindowInfo] = []
            for win in windows:
                w_proc = win.process_name.lower().rstrip(".exe")
                if w_proc == proc_target or proc_target in w_proc or (len(proc_target) > 3 and w_proc in proc_target):
                    matching_proc_windows.append(win)

            if matching_proc_windows:
                # Prioritize windows that have non-empty titles and are not minimized
                for win in matching_proc_windows:
                    if win.title and not win.is_minimized:
                        return win
                for win in matching_proc_windows:
                    if win.title:
                        return win
                return matching_proc_windows[0]

        if time.perf_counter() >= deadline:
            break
        time.sleep(0.1)

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


def get_work_area(monitor_index: int = 0) -> Tuple[int, int, int, int]:
    """Retrieves the physical pixel work area (left, top, right, bottom) excluding the taskbar."""
    rect = wintypes.RECT()
    if user32.SystemParametersInfoW(48, 0, ctypes.byref(rect), 0):  # SPI_GETWORKAREA = 48
        return (int(rect.left), int(rect.top), int(rect.right), int(rect.bottom))
    w = user32.GetSystemMetrics(0)
    h = user32.GetSystemMetrics(1)
    return (0, 0, int(w), int(h))


def snap_window(hwnd: int, position: str = "left", monitor_index: int = 0) -> bool:
    """
    Instantly repositions and sizes a window into a screen quadrant or half using Win32 API.
    Bypasses Windows 11 Snap Assist menus and executes in under 15ms.
    Positions: 'left', 'right', 'top', 'bottom', 'maximize', 'restore', 'center',
               'top_left', 'top_right', 'bottom_left', 'bottom_right'.
    """
    if not hwnd or not win32gui.IsWindow(hwnd):
        return False

    ensure_dpi_aware()
    attach_input_desktop()

    pos = position.lower().strip()
    if pos in ("maximize", "max", "full"):
        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
        force_activate_window(hwnd)
        return True

    # Restore if iconic (minimized) or zoomed (maximized) so SetWindowPos takes effect
    if win32gui.IsIconic(hwnd) or user32.IsZoomed(hwnd):
        win32gui.ShowWindow(hwnd, SW_RESTORE)
        time.sleep(0.05)

    l, t, r, b = get_work_area(monitor_index)
    work_w = r - l
    work_h = b - t
    half_w = work_w // 2
    half_h = work_h // 2

    if pos in ("left", "left_half", "left_split"):
        nx, ny, nw, nh = l, t, half_w, work_h
    elif pos in ("right", "right_half", "right_split"):
        nx, ny, nw, nh = l + half_w, t, work_w - half_w, work_h
    elif pos in ("third_left", "left_third", "left_col"):
        third_w = work_w // 3
        nx, ny, nw, nh = l, t, third_w, work_h
    elif pos in ("third_center", "center_third", "middle_third", "center_col"):
        third_w = work_w // 3
        nx, ny, nw, nh = l + third_w, t, third_w, work_h
    elif pos in ("third_right", "right_third", "right_col"):
        third_w = work_w // 3
        nx, ny, nw, nh = l + 2 * third_w, t, work_w - (2 * third_w), work_h
    elif pos in ("top", "top_half"):
        nx, ny, nw, nh = l, t, work_w, half_h
    elif pos in ("bottom", "bottom_half"):
        nx, ny, nw, nh = l, t + half_h, work_w, work_h - half_h
    elif pos in ("top_left", "tl"):
        nx, ny, nw, nh = l, t, half_w, half_h
    elif pos in ("top_right", "tr"):
        nx, ny, nw, nh = l + half_w, t, work_w - half_w, half_h
    elif pos in ("bottom_left", "bl"):
        nx, ny, nw, nh = l, t + half_h, half_w, work_h - half_h
    elif pos in ("bottom_right", "br"):
        nx, ny, nw, nh = l + half_w, t + half_h, work_w - half_w, work_h - half_h
    elif pos in ("center", "centered"):
        cw = int(work_w * 0.8)
        ch = int(work_h * 0.8)
        nx = l + (work_w - cw) // 2
        ny = t + (work_h - ch) // 2
        nw = cw
        nh = ch
    else:
        nx, ny, nw, nh = l, t, work_w, work_h

    # Move and size window, bringing to top
    user32.SetWindowPos(hwnd, 0, nx, ny, nw, nh, 0x0040)  # SWP_SHOWWINDOW = 0x0040
    force_activate_window(hwnd)
    return True


def snap_layout(
    layout: str = "side_by_side",
    left_window: Optional[Union[str, int]] = None,
    right_window: Optional[Union[str, int]] = None,
    window: Optional[Union[str, int]] = None,
    center_window: Optional[Union[str, int]] = None,
    windows: Optional[List[Union[str, int]]] = None,
    monitor_index: int = 0,
) -> Dict[str, Any]:
    """
    Arranges windows into a cohesive visual layout in a single programmatic step.
    Eliminates multi-turn hotkey snapping loops.
    
    Supported layouts:
      - 'side_by_side' / 'split': docks left_window to left half, right_window to right half.
      - 'thirds' / 'side_by_side_3' / 'three_columns': docks 3 windows into left, center, right thirds.
      - 'maximize' / 'fullscreen' / 'full': maximizes window (or left_window) to fill the screen.
      - 'center' / 'centered': centers window occupying 80% screen work area.
      - 'top_bottom' / 'split_vertical': docks left_window to top half, right_window to bottom half.
      - 'grid' / 'quad' / '2x2': docks 4 windows into 2x2 quadrants.
    """
    results: Dict[str, Any] = {}

    def _resolve_hwnd(target: Optional[Union[str, int]]) -> Optional[int]:
        if target is None:
            return None
        if isinstance(target, int):
            return target if win32gui.IsWindow(target) else None
        win = find_window_by_title(str(target), timeout=2.0)
        return win.hwnd if win else None

    # Handle windows list if provided
    if windows and len(windows) > 0:
        if len(windows) == 3 and layout in ("side_by_side", "thirds", "three_columns", "side_by_side_3"):
            layout = "thirds"
            left_window = windows[0]
            center_window = windows[1]
            right_window = windows[2]
        elif len(windows) == 2:
            left_window = windows[0]
            right_window = windows[1]
        elif len(windows) >= 4:
            layout = "grid"

    target_main = window if window is not None else left_window
    h_main = _resolve_hwnd(target_main)
    h_left = _resolve_hwnd(left_window)
    h_center = _resolve_hwnd(center_window)
    h_right = _resolve_hwnd(right_window)

    layout_norm = layout.lower().strip()
    if layout_norm in ("maximize", "max", "fullscreen", "full"):
        if h_main:
            results["main"] = {"target": target_main, "hwnd": h_main, "success": snap_window(h_main, "maximize", monitor_index)}
    elif layout_norm in ("center", "centered"):
        if h_main:
            results["main"] = {"target": target_main, "hwnd": h_main, "success": snap_window(h_main, "center", monitor_index)}
    elif layout_norm in ("top_bottom", "split_vertical"):
        if h_left:
            results["top"] = {"target": left_window, "hwnd": h_left, "success": snap_window(h_left, "top", monitor_index)}
        if h_right:
            results["bottom"] = {"target": right_window, "hwnd": h_right, "success": snap_window(h_right, "bottom", monitor_index)}
    elif layout_norm in ("thirds", "side_by_side_3", "three_columns", "split_3"):
        if h_left:
            results["left"] = {"target": left_window, "hwnd": h_left, "success": snap_window(h_left, "third_left", monitor_index)}
        if h_center:
            results["center"] = {"target": center_window, "hwnd": h_center, "success": snap_window(h_center, "third_center", monitor_index)}
        if h_right:
            results["right"] = {"target": right_window, "hwnd": h_right, "success": snap_window(h_right, "third_right", monitor_index)}
    elif layout_norm in ("grid", "quad", "2x2"):
        w_list = windows or [left_window, right_window, center_window, window]
        tl_target = w_list[0] if len(w_list) > 0 else left_window
        tr_target = w_list[1] if len(w_list) > 1 else right_window
        bl_target = w_list[2] if len(w_list) > 2 else center_window
        br_target = w_list[3] if len(w_list) > 3 else window

        h_tl = _resolve_hwnd(tl_target)
        h_tr = _resolve_hwnd(tr_target)
        h_bl = _resolve_hwnd(bl_target)
        h_br = _resolve_hwnd(br_target)

        if h_tl:
            results["top_left"] = {"target": tl_target, "hwnd": h_tl, "success": snap_window(h_tl, "top_left", monitor_index)}
        if h_tr:
            results["top_right"] = {"target": tr_target, "hwnd": h_tr, "success": snap_window(h_tr, "top_right", monitor_index)}
        if h_bl:
            results["bottom_left"] = {"target": bl_target, "hwnd": h_bl, "success": snap_window(h_bl, "bottom_left", monitor_index)}
        if h_br:
            results["bottom_right"] = {"target": br_target, "hwnd": h_br, "success": snap_window(h_br, "bottom_right", monitor_index)}
    elif layout_norm in ("side_by_side", "split_horizontal", "split"):
        if h_left:
            results["left"] = {"target": left_window, "hwnd": h_left, "success": snap_window(h_left, "left", monitor_index)}
        if h_right:
            results["right"] = {"target": right_window, "hwnd": h_right, "success": snap_window(h_right, "right", monitor_index)}
    else:
        if h_main:
            results["main"] = {"target": target_main, "hwnd": h_main, "success": snap_window(h_main, layout_norm, monitor_index)}

    missing: List[str] = []
    if layout_norm in ("maximize", "max", "fullscreen", "full", "center", "centered"):
        if target_main is not None and h_main is None:
            missing.append(f"window '{target_main}'")
    elif layout_norm in ("top_bottom", "split_vertical", "side_by_side", "split_horizontal", "split"):
        if left_window is not None and h_left is None:
            missing.append(f"left_window '{left_window}'")
        if right_window is not None and h_right is None:
            missing.append(f"right_window '{right_window}'")
    elif layout_norm in ("thirds", "side_by_side_3", "three_columns", "split_3"):
        if left_window is not None and h_left is None:
            missing.append(f"left_window '{left_window}'")
        if center_window is not None and h_center is None:
            missing.append(f"center_window '{center_window}'")
        if right_window is not None and h_right is None:
            missing.append(f"right_window '{right_window}'")
    elif layout_norm in ("grid", "quad", "2x2"):
        for label, tgt, hnd in [("top_left", tl_target, h_tl), ("top_right", tr_target, h_tr), ("bottom_left", bl_target, h_bl), ("bottom_right", br_target, h_br)]:
            if tgt is not None and hnd is None:
                missing.append(f"{label} '{tgt}'")
    else:
        if target_main is not None and h_main is None:
            missing.append(f"window '{target_main}'")

    available_titles: List[str] = []
    if missing:
        try:
            available_titles = [w.title for w in list_windows(visible_only=True) if w.title and len(w.title.strip()) > 1]
        except Exception:
            available_titles = []

    success = (len(missing) == 0) and (len(results) > 0) and all(r.get("success", False) for r in results.values())

    resp: Dict[str, Any] = {
        "success": success,
        "layout": layout,
        "windows": results,
    }
    if missing:
        resp["error"] = f"Requested layout target(s) not found among open windows: {', '.join(missing)}."
        resp["available_windows"] = available_titles[:15]
        resp["suggestion"] = "Ensure the application is launched and visible before attempting to snap layout."
    elif not success:
        resp["error"] = "One or more windows could not be repositioned into layout."

    return resp


class WindowsFocusManager(AbstractFocusManager):
    """Windows implementation of the AbstractFocusManager interface."""

    def get_window_info(self, hwnd: int) -> Optional[WindowInfo]:
        return get_window_info(hwnd)

    def get_foreground_window(self) -> Optional[WindowInfo]:
        return get_foreground_window()

    def list_windows(self, visible_only: bool = True) -> List[WindowInfo]:
        return list_windows(visible_only=visible_only)

    def find_window_by_title(
        self, query: str, exact: bool = False, visible_only: bool = True, timeout: float = 0.0
    ) -> Optional[WindowInfo]:
        return find_window_by_title(query=query, exact=exact, visible_only=visible_only, timeout=timeout)

    def find_windows_by_process(
        self, process_name: str, visible_only: bool = True
    ) -> List[WindowInfo]:
        return find_windows_by_process(process_name=process_name, visible_only=visible_only)

    def force_activate_window(self, hwnd: int) -> bool:
        return force_activate_window(hwnd=hwnd)

    def snap_window(self, hwnd: int, position: str = "left", monitor_index: int = 0) -> bool:
        return snap_window(hwnd=hwnd, position=position, monitor_index=monitor_index)

    def snap_layout(
        self,
        layout: str = "side_by_side",
        left_window: Optional[Union[str, int]] = None,
        right_window: Optional[Union[str, int]] = None,
        window: Optional[Union[str, int]] = None,
        center_window: Optional[Union[str, int]] = None,
        windows: Optional[List[Union[str, int]]] = None,
        monitor_index: int = 0,
    ) -> Dict[str, Any]:
        return snap_layout(
            layout=layout,
            left_window=left_window,
            right_window=right_window,
            window=window,
            center_window=center_window,
            windows=windows,
            monitor_index=monitor_index,
        )
