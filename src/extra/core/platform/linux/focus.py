"""
Project Extra — Linux Window Focus & Snapping Engine
Window discovery, enumeration, active window focus enforcement,
and sub-15ms programmatic snap layouts across Wayland (KWin) and X11 (EWMH).
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union

try:
    from jeepney import DBusAddress, new_method_call
    from jeepney.io.blocking import open_dbus_connection
    HAVE_JEEPNEY = True
except ImportError:
    HAVE_JEEPNEY = False

from extra.core.platform.base import AbstractFocusManager, WindowInfo
from extra.core.platform.linux.geometry import (
    clamp_coordinates,
    get_monitors_info,
    get_primary_monitor,
)
from extra.core.platform.linux.permissions import is_wayland

logger = logging.getLogger("extra.focus.linux")

_focus_manager_instance: Optional[LinuxFocusManager] = None

# Internal bidirectional mapping between integer hwnd and KWin string runner IDs
_hwnd_to_kwin: Dict[int, str] = {}
_kwin_to_hwnd: Dict[str, int] = {}
_next_synthetic_hwnd: int = 10000


def _get_or_create_hwnd(kwin_id: str) -> int:
    """Returns a consistent, positive integer handle for a KWin window ID."""
    global _next_synthetic_hwnd
    if kwin_id in _kwin_to_hwnd:
        return _kwin_to_hwnd[kwin_id]
    h = _next_synthetic_hwnd
    _next_synthetic_hwnd += 1
    _hwnd_to_kwin[h] = kwin_id
    _kwin_to_hwnd[kwin_id] = h
    return h


def get_work_area(monitor_index: int = 0) -> Tuple[int, int, int, int]:
    """Returns (left, top, right, bottom) of display work area."""
    monitors = get_monitors_info()
    mon = monitors[monitor_index] if 0 <= monitor_index < len(monitors) else monitors[0]
    return (mon.left, mon.top, mon.right, mon.bottom)


def get_window_info(hwnd: int) -> Optional[WindowInfo]:
    """Retrieves window metadata for a specific window ID."""
    return get_focus_manager().get_window_info(hwnd)


def get_foreground_window() -> Optional[WindowInfo]:
    """Returns current active foreground window info."""
    return get_focus_manager().get_foreground_window()


def list_windows(visible_only: bool = True) -> List[WindowInfo]:
    """Enumerates active top-level native windows."""
    return get_focus_manager().list_windows(visible_only=visible_only)


def find_window_by_title(
    query: str, exact: bool = False, visible_only: bool = True, timeout: float = 0.0
) -> Optional[WindowInfo]:
    """Finds window matching title substring or exact string with optional timeout."""
    return get_focus_manager().find_window_by_title(
        query=query, exact=exact, visible_only=visible_only, timeout=timeout
    )


def find_windows_by_process(
    process_name: str, visible_only: bool = True
) -> List[WindowInfo]:
    """Finds windows belonging to a process name."""
    return get_focus_manager().find_windows_by_process(
        process_name=process_name, visible_only=visible_only
    )


def force_activate_window(hwnd: int) -> bool:
    """Forces window to foreground and focuses it."""
    return get_focus_manager().force_activate_window(hwnd)


def get_window_executable_path(hwnd: int) -> Optional[str]:
    """Returns full filesystem path to window's backing executable via procfs."""
    win = get_window_info(hwnd)
    if not win or not win.process_id:
        return None
    exe_link = f"/proc/{win.process_id}/exe"
    try:
        if os.path.exists(exe_link):
            return os.path.realpath(exe_link)
    except Exception:
        pass
    return None


def snap_window(hwnd: int, position: str = "left", monitor_index: int = 0) -> bool:
    """
    Programmatically repositions and sizes a window into a screen half or quadrant in sub-15ms.
    Positions: 'left', 'right', 'top', 'bottom', 'maximize', 'restore', 'center'.
    Uses KWin Scripting on Wayland or xdotool/wmctrl on X11.
    """
    l, t, r, b = get_work_area(monitor_index)
    work_w = r - l
    work_h = b - t
    half_w = work_w // 2
    half_h = work_h // 2

    pos = position.lower().strip()
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
    elif pos in ("center", "centered"):
        cw, ch = int(work_w * 0.8), int(work_h * 0.8)
        nx = l + (work_w - cw) // 2
        ny = t + (work_h - ch) // 2
        nw, nh = cw, ch
    elif pos in ("maximize", "max", "full"):
        nx, ny, nw, nh = l, t, work_w, work_h
    else:
        nx, ny, nw, nh = l, t, work_w, work_h

    # Tier 1: KDE KWin Wayland Scripting
    kwin_id = _hwnd_to_kwin.get(hwnd)
    win_info = get_window_info(hwnd)
    target_match = kwin_id or (win_info.title if win_info else None) or str(hwnd)

    if shutil.which("busctl"):
        kwin_script = f"""
        var getWindows = function() {{
            return (typeof workspace.windowList === 'function') ? workspace.windowList() : workspace.clientList();
        }};
        var wins = getWindows();
        var target = "{target_match}";
        for (var i = 0; i < wins.length; i++) {{
            var w = wins[i];
            var match = (w.internalId && w.internalId.toString().indexOf(target) !== -1) ||
                        (w.caption && w.caption.indexOf(target) !== -1);
            if (match) {{
                w.minimized = false;
                workspace.activeWindow = w;
                w.frameGeometry = {{x: {nx}, y: {ny}, width: {nw}, height: {nh}}};
                break;
            }}
        }}
        """
        tmp_script = f"/tmp/extra_snap_{int(time.time() * 1000)}.js"
        try:
            with open(tmp_script, "w", encoding="utf-8") as f:
                f.write(kwin_script)
            out = subprocess.check_output(
                [
                    "busctl", "--user", "call",
                    "org.kde.KWin", "/Scripting",
                    "org.kde.kwin.Scripting", "loadScript",
                    "ss", tmp_script, f"snap_{hwnd}",
                ],
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=0.5,
            )
            sid = int(out.strip().split()[-1])
            subprocess.run(
                ["busctl", "--user", "call", "org.kde.KWin", f"/Scripting/Script{sid}", "org.kde.kwin.Script", "run"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=0.5,
            )
            subprocess.run(
                ["busctl", "--user", "call", "org.kde.KWin", "/Scripting", "org.kde.kwin.Scripting", "unloadScript", "s", f"snap_{hwnd}"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=0.5,
            )
            return True
        except Exception:
            pass
        finally:
            if os.path.exists(tmp_script):
                try:
                    os.remove(tmp_script)
                except Exception:
                    pass

    # Tier 2: X11 / XWayland (xdotool / wmctrl)
    if shutil.which("xdotool"):
        try:
            subprocess.run(["xdotool", "windowsize", str(hwnd), str(nw), str(nh)], timeout=0.5)
            subprocess.run(["xdotool", "windowmove", str(hwnd), str(nx), str(ny)], timeout=0.5)
            force_activate_window(hwnd)
            return True
        except Exception:
            pass

    if shutil.which("wmctrl"):
        try:
            subprocess.run(
                ["wmctrl", "-i", "-r", hex(hwnd), "-e", f"0,{nx},{ny},{nw},{nh}"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=0.5,
            )
            force_activate_window(hwnd)
            return True
        except Exception:
            pass

    return False


def snap_layout(
    layout: str = "side_by_side",
    left_window: Optional[Union[str, int]] = None,
    right_window: Optional[Union[str, int]] = None,
    window: Optional[Union[str, int]] = None,
    center_window: Optional[Union[str, int]] = None,
    windows: Optional[List[Union[str, int]]] = None,
    monitor_index: int = 0,
) -> Dict[str, Any]:
    """Arranges windows into side-by-side, thirds, or split layout in one tool turn."""
    results: Dict[str, Any] = {}

    def _resolve_hwnd(target: Optional[Union[str, int]]) -> Optional[int]:
        if target is None:
            return None
        if isinstance(target, int):
            return target
        win = find_window_by_title(str(target), timeout=1.0)
        return win.hwnd if win else None

    if windows and len(windows) > 0:
        if len(windows) == 3 and layout in ("side_by_side", "thirds", "three_columns", "side_by_side_3"):
            layout = "thirds"
            left_window = windows[0]
            center_window = windows[1]
            right_window = windows[2]
        elif len(windows) == 2:
            left_window = windows[0]
            right_window = windows[1]

    h_left = _resolve_hwnd(left_window)
    h_center = _resolve_hwnd(center_window)
    h_right = _resolve_hwnd(right_window)

    layout_norm = layout.lower().strip()
    if layout_norm in ("side_by_side", "split_horizontal", "split"):
        if h_left:
            results["left"] = {
                "target": left_window,
                "hwnd": h_left,
                "success": snap_window(h_left, "left", monitor_index),
            }
        if h_right:
            results["right"] = {
                "target": right_window,
                "hwnd": h_right,
                "success": snap_window(h_right, "right", monitor_index),
            }
    elif layout_norm in ("thirds", "side_by_side_3", "three_columns", "split_3"):
        if h_left:
            results["left"] = {
                "target": left_window,
                "hwnd": h_left,
                "success": snap_window(h_left, "third_left", monitor_index),
            }
        if h_center:
            results["center"] = {
                "target": center_window,
                "hwnd": h_center,
                "success": snap_window(h_center, "third_center", monitor_index),
            }
        if h_right:
            results["right"] = {
                "target": right_window,
                "hwnd": h_right,
                "success": snap_window(h_right, "third_right", monitor_index),
            }

    missing: List[str] = []
    if layout_norm in ("thirds", "side_by_side_3", "three_columns", "split_3"):
        if left_window is not None and h_left is None:
            missing.append(f"left_window '{left_window}'")
        if center_window is not None and h_center is None:
            missing.append(f"center_window '{center_window}'")
        if right_window is not None and h_right is None:
            missing.append(f"right_window '{right_window}'")
    else:
        if left_window is not None and h_left is None:
            missing.append(f"left_window '{left_window}'")
        if right_window is not None and h_right is None:
            missing.append(f"right_window '{right_window}'")

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
        "results": results,
    }
    if missing:
        resp["error"] = f"Requested layout target(s) not found among open windows: {', '.join(missing)}."
        resp["available_windows"] = available_titles[:15]
        resp["suggestion"] = "Ensure the application is launched and visible before attempting to snap layout."
    elif not success:
        resp["error"] = "One or more windows could not be repositioned into layout."

    return resp


# ── LinuxFocusManager Implementation ───────────────────────────────────────────

class LinuxFocusManager(AbstractFocusManager):
    """
    Linux implementation of AbstractFocusManager supporting KWin D-Bus and X11 EWMH.
    """

    def __init__(self) -> None:
        self._cached_windows: List[WindowInfo] = []

    def get_window_info(self, hwnd: int) -> Optional[WindowInfo]:
        for w in self.list_windows(visible_only=False):
            if w.hwnd == hwnd:
                return w
        return None

    def get_foreground_window(self) -> Optional[WindowInfo]:
        wins = self.list_windows(visible_only=True)
        if wins:
            # First window in KWin list or first active
            return wins[0]

        # Fallback via xdotool
        if shutil.which("xdotool"):
            try:
                res = subprocess.check_output(
                    ["xdotool", "getactivewindow"], text=True, stderr=subprocess.DEVNULL, timeout=0.3
                ).strip()
                if res.isdigit():
                    wid = int(res)
                    title = ""
                    try:
                        title = subprocess.check_output(
                            ["xdotool", "getwindowname", str(wid)], text=True, stderr=subprocess.DEVNULL, timeout=0.3
                        ).strip()
                    except Exception:
                        pass
                    return WindowInfo(
                        hwnd=wid,
                        title=title,
                        class_name="NativeWindow",
                        process_id=0,
                        process_name="",
                        rect=(0, 0, 1920, 1080),
                        is_visible=True,
                        is_minimized=False,
                    )
            except Exception:
                pass

        mon = get_primary_monitor()
        return WindowInfo(
            hwnd=0,
            title="Desktop",
            class_name="Desktop",
            process_id=0,
            process_name="",
            rect=(mon.left, mon.top, mon.right, mon.bottom),
            is_visible=True,
            is_minimized=False,
        )

    def list_windows(self, visible_only: bool = True) -> List[WindowInfo]:
        windows: List[WindowInfo] = []
        seen_titles: Set[str] = set()

        # Tier 1: KWin WindowsRunner D-Bus Query via Jeepney (pure Python < 3ms)
        if HAVE_JEEPNEY:
            try:
                conn = open_dbus_connection(bus="SESSION")
                try:
                    addr = DBusAddress("/WindowsRunner", bus_name="org.kde.KWin", interface="org.kde.krunner1")
                    msg = new_method_call(addr, "Match", "s", ("",))
                    reply = conn.send_and_get_reply(msg, timeout=0.5)
                    if reply.body and len(reply.body) > 0 and isinstance(reply.body[0], list):
                        for match in reply.body[0]:
                            if len(match) >= 3:
                                tok_id, tok_title, tok_class = match[0], match[1], match[2]
                                if tok_title and tok_title not in seen_titles:
                                    seen_titles.add(tok_title)
                                    h = _get_or_create_hwnd(tok_id)
                                    windows.append(
                                        WindowInfo(
                                            hwnd=h,
                                            title=tok_title,
                                            class_name=tok_class or "KWinClient",
                                            process_id=0,
                                            process_name=tok_class,
                                            rect=(0, 0, 1920, 1080),
                                            is_visible=True,
                                            is_minimized=False,
                                        )
                                    )
                        if windows:
                            self._cached_windows = windows
                            return windows
                finally:
                    conn.close()
            except Exception as e:
                logger.debug(f"Jeepney KWin WindowsRunner query failed: {e}")

        # Tier 1b: KWin WindowsRunner D-Bus Query via busctl regex
        if shutil.which("busctl"):
            try:
                out = subprocess.check_output(
                    [
                        "busctl", "--user", "call",
                        "org.kde.KWin", "/WindowsRunner",
                        "org.kde.krunner1", "Match",
                        "s", "",
                    ],
                    text=True,
                    stderr=subprocess.DEVNULL,
                    timeout=0.6,
                )
                pattern = re.compile(r'\"([^\"]+)\"\s+\"([^\"]+)\"\s+\"([^\"]+)\"\s+\d+')
                for m in pattern.findall(out):
                    tok_id, tok_title, tok_class = m[0], m[1], m[2]
                    if tok_title and tok_title not in seen_titles:
                        seen_titles.add(tok_title)
                        h = _get_or_create_hwnd(tok_id)
                        windows.append(
                            WindowInfo(
                                hwnd=h,
                                title=tok_title,
                                class_name=tok_class or "KWinClient",
                                process_id=0,
                                process_name=tok_class,
                                rect=(0, 0, 1920, 1080),
                                is_visible=True,
                                is_minimized=False,
                            )
                        )
                if windows:
                    self._cached_windows = windows
                    return windows
            except Exception:
                pass

        # Tier 2: wmctrl (X11 / XWayland)
        if shutil.which("wmctrl"):
            try:
                output = subprocess.check_output(
                    ["wmctrl", "-l", "-p", "-G"], text=True, stderr=subprocess.DEVNULL, timeout=0.6
                )
                for line in output.splitlines():
                    parts = line.split(maxsplit=8)
                    if len(parts) >= 8:
                        wid_hex, desk, pid_str, x_str, y_str, w_str, h_str, host = parts[:8]
                        title = parts[8] if len(parts) > 8 else ""
                        wid = int(wid_hex, 16)
                        pid = int(pid_str) if pid_str.isdigit() else 0
                        x, y, w, h = int(x_str), int(y_str), int(w_str), int(h_str)

                        pname = ""
                        if pid > 0:
                            comm_path = f"/proc/{pid}/comm"
                            if os.path.exists(comm_path):
                                try:
                                    with open(comm_path, "r", encoding="utf-8") as f:
                                        pname = f.read().strip()
                                except Exception:
                                    pass

                        windows.append(
                            WindowInfo(
                                hwnd=wid,
                                title=title,
                                class_name=pname or "X11Client",
                                process_id=pid,
                                process_name=pname,
                                rect=(x, y, x + w, y + h),
                                is_visible=(desk != "-1"),
                                is_minimized=(desk == "-1"),
                            )
                        )
                if windows:
                    self._cached_windows = windows
                    return [w for w in windows if not visible_only or w.is_visible]
            except Exception:
                pass

        return windows

    def find_window_by_title(
        self, query: str, exact: bool = False, visible_only: bool = True, timeout: float = 0.0
    ) -> Optional[WindowInfo]:
        t0 = time.time()
        q = query.lower().strip()

        while True:
            for w in self.list_windows(visible_only=visible_only):
                title_lower = w.title.lower().strip()
                if exact and title_lower == q:
                    return w
                if not exact and (
                    q in title_lower
                    or (w.class_name and q in w.class_name.lower())
                    or (w.process_name and q in w.process_name.lower())
                ):
                    return w
            if time.time() - t0 >= timeout:
                break
            time.sleep(0.1)

        return None

    def find_windows_by_process(
        self, process_name: str, visible_only: bool = True
    ) -> List[WindowInfo]:
        q = process_name.lower().strip()
        return [
            w for w in self.list_windows(visible_only=visible_only)
            if q in w.process_name.lower() or q in w.class_name.lower()
        ]

    def force_activate_window(self, hwnd: int) -> bool:
        kwin_id = _hwnd_to_kwin.get(hwnd)
        if kwin_id:
            # Tier 1: KWin WindowsRunner D-Bus Activation via Jeepney
            if HAVE_JEEPNEY:
                try:
                    conn = open_dbus_connection(bus="SESSION")
                    try:
                        addr = DBusAddress("/WindowsRunner", bus_name="org.kde.KWin", interface="org.kde.krunner1")
                        run_msg = new_method_call(addr, "Run", "ss", (kwin_id, ""))
                        conn.send_message(run_msg)
                        return True
                    finally:
                        conn.close()
                except Exception as e:
                    logger.debug(f"Jeepney KWin Run failed: {e}")

            # Tier 1b: KWin WindowsRunner D-Bus Activation via busctl
            if shutil.which("busctl"):
                try:
                    subprocess.run(
                        [
                            "busctl", "--user", "call",
                            "org.kde.KWin", "/WindowsRunner",
                            "org.kde.krunner1", "Run",
                            "ss", kwin_id, "",
                        ],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=0.5,
                    )
                    return True
                except Exception:
                    pass

        # Tier 2: xdotool windowactivate
        if shutil.which("xdotool"):
            try:
                subprocess.run(
                    ["xdotool", "windowactivate", str(hwnd)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=0.5,
                )
                return True
            except Exception:
                pass

        # Tier 3: wmctrl -i -a
        if shutil.which("wmctrl"):
            try:
                subprocess.run(
                    ["wmctrl", "-i", "-a", hex(hwnd)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=0.5,
                )
                return True
            except Exception:
                pass

        return False


def get_focus_manager() -> LinuxFocusManager:
    global _focus_manager_instance
    if _focus_manager_instance is None:
        _focus_manager_instance = LinuxFocusManager()
    return _focus_manager_instance


FocusManager = LinuxFocusManager
