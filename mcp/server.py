"""
Project Extra — Official Anthropic Model Context Protocol (MCP) Server
Exposes high-speed perception, SendInput injection, UIA semantic tree querying,
browser fast-path, and closed-loop stall breaking over standard stdio transport.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional

# Defensive sys.path guard: ensure local 'mcp' folder never shadows the PyPI 'mcp' SDK
_shadow_paths = [
    p for p in sys.path
    if os.path.isdir(os.path.join(p, "mcp")) and "site-packages" not in p.lower()
]
for _p in _shadow_paths:
    sys.path.remove(_p)
if "mcp" in sys.modules and "site-packages" not in getattr(sys.modules["mcp"], "__file__", "").lower():
    del sys.modules["mcp"]

from mcp.server.mcpserver import MCPServer

from extra.core.capture import capture_roi, capture_screen, get_capture_engine
from extra.core.focus import (
    find_window_by_title,
    force_activate_window,
    get_foreground_window,
    list_windows,
)
from extra.core.geometry import (
    attach_input_desktop,
    denormalize_coordinates,
    ensure_dpi_aware,
    get_cursor_position,
    get_monitors_info,
    normalize_coordinates,
)
from extra.core.indicators import get_indicator_controller
from extra.core.input_engine import (
    atomic_clipboard_paste,
    instant_type,
    mouse_click,
    mouse_double_click,
    mouse_drag,
    mouse_move,
    mouse_scroll,
    send_hotkey,
)
from extra.core.stall_breaker import EmergencyAbortError, StallBreaker, StallStatus
from extra.core.uia_plane import SetOfMarkAnnotator, UIAutomationPlane
from extra.fastpath.browser import execute_browser_action
from extra.fastpath.shell import launch_app, open_uri, resolve_executable

# Configure logging to stderr so stdio JSON-RPC stream remains pure
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [Extra-MCP] [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger("extra.mcp")

# Initialize Server
server = MCPServer("Extra-Windows-Flashless")

# Singletons for supervisor plane
_uia_plane = UIAutomationPlane()
_som_annotator = SetOfMarkAnnotator()
_stall_breaker = StallBreaker(max_strikes=2)


@server.tool()
def extra_screenshot(
    monitor_index: int = 0,
    crop_box: Optional[List[int]] = None,
    annotate_ui: bool = False,
    save_to_file: bool = True,
    file_path: Optional[str] = None,
    include_base64: bool = False,
) -> Dict[str, Any]:
    """
    Captures an ultra-fast screen frame (< 30ms) from the specified monitor.
    Optionally overlays Set-of-Mark (SoM) numbered badges on all detected interactive UI elements.
    Saves screenshot to disk to avoid large Base64 payload truncation in AI clients (Fixes #4, credit: @harshbuttru3).
    
    Args:
        monitor_index: 0-based display index (0 = primary monitor).
        crop_box: Optional [left, top, right, bottom] physical pixel coordinates to crop.
        annotate_ui: If True, draws numbered badges [1], [2] on all interactive buttons and returns their positions.
        save_to_file: If True (default), writes image to disk in the safe scratch workspace (~/.extra/workspace/screenshots/).
        file_path: Optional custom file path to save screenshot.
        include_base64: If True, includes full base64 string in response (default False to prevent LLM payload truncation).
    """
    ensure_dpi_aware()
    attach_input_desktop()

    crop_tuple = tuple(crop_box) if crop_box and len(crop_box) == 4 else None
    cap = capture_screen(monitor_index=monitor_index, crop_box=crop_tuple)

    result: Dict[str, Any] = {
        "monitor_index": monitor_index,
        "width": cap.width,
        "height": cap.height,
        "duration_ms": cap.duration_ms,
        "crop_box": crop_box,
    }

    if annotate_ui:
        # Inspect interactive UI elements
        elements = _uia_plane.inspect_window(interactive_only=True, max_elements=50)
        ann_img, mark_map = _som_annotator.annotate(cap.image, elements)
        final_img = ann_img
        result["annotated"] = True
        result["elements"] = [el.to_dict() for el in elements]
    else:
        final_img = cap.image
        result["annotated"] = False

    # Save to file to prevent LLM tool payload truncation (Fixes #4, reported by @harshbuttru3)
    if save_to_file:
        from pathlib import Path
        if not file_path:
            workspace_dir = Path(os.environ.get("EXTRA_WORKSPACE", Path.home() / ".extra" / "workspace")) / "screenshots"
            workspace_dir.mkdir(parents=True, exist_ok=True)
            filename = f"screenshot_{int(time.time() * 1000)}.png"
            target_path = workspace_dir / filename
        else:
            target_path = Path(file_path)
            target_path.parent.mkdir(parents=True, exist_ok=True)

        final_img.save(str(target_path), format="PNG")
        result["file_path"] = str(target_path).replace("\\", "/")

    if include_base64:
        import io, base64
        buf = io.BytesIO()
        final_img.save(buf, format="JPEG", quality=80)
        result["screenshot_base64"] = base64.b64encode(buf.getvalue()).decode("utf-8")

    return result


@server.tool()
def extra_click(
    x: int,
    y: int,
    button: str = "left",
    clicks: int = 1,
    normalized: bool = False,
    monitor_index: int = 0,
) -> Dict[str, Any]:
    """
    Executes a hardware-level mouse click with PerMonitorV2 DPI compensation and closed-loop stall checking.
    Supports global fallback visual diffing to eliminate false-stalls when distant viewports change (Fixes #4, credit: @harshbuttru3).
    
    Args:
        x: X-coordinate (physical pixel or normalized 0-1000).
        y: Y-coordinate (physical pixel or normalized 0-1000).
        button: Mouse button ('left', 'right', 'middle'). Default: 'left'.
        clicks: Click count (1 = single click, 2 = double click). Default: 1.
        normalized: If True, treats x, y as [0, 1000] scale and converts to physical pixels.
        monitor_index: Monitor index if normalized coordinates are used.
    """
    ensure_dpi_aware()
    attach_input_desktop()
    _stall_breaker.check_safety_abort()

    if normalized:
        phys_x, phys_y = denormalize_coordinates(x, y, monitor_index=monitor_index)
    else:
        phys_x, phys_y = x, y

    # Capture state before action for closed-loop verification
    # Using full capture to slice ROI and retain global canvas for fallback diffing (Fixes #4 / @harshbuttru3)
    before_fg = get_foreground_window()
    before_hwnd = before_fg.hwnd if before_fg else None
    cap_before = capture_screen(monitor_index=monitor_index)
    roi_box = (
        max(0, phys_x - 100),
        max(0, phys_y - 100),
        min(cap_before.width, phys_x + 100),
        min(cap_before.height, phys_y + 100),
    )
    roi_before = cap_before.image.crop(roi_box)

    t0 = time.perf_counter()
    mouse_click(phys_x, phys_y, button=button, clicks=clicks, monitor_index=monitor_index)
    duration_ms = (time.perf_counter() - t0) * 1000.0

    # Settle time for UI animation/dispatch
    time.sleep(0.08)

    # Capture state after action
    after_fg = get_foreground_window()
    after_hwnd = after_fg.hwnd if after_fg else None
    cap_after = capture_screen(monitor_index=monitor_index)
    roi_after = cap_after.image.crop(roi_box)

    outcome = _stall_breaker.evaluate_action(
        roi_before,
        roi_after,
        before_hwnd=before_hwnd,
        after_hwnd=after_hwnd,
        action_name=f"click({button}, x={phys_x}, y={phys_y})",
        before_full_image=cap_before.image,
        after_full_image=cap_after.image,
    )

    return {
        "success": True,
        "phys_x": phys_x,
        "phys_y": phys_y,
        "button": button,
        "clicks": clicks,
        "duration_ms": round(duration_ms, 2),
        "stall_status": outcome.status.value,
        "strikes": outcome.strikes,
        "message": outcome.message,
    }


@server.tool()
def extra_type(
    text: str,
    press_enter: bool = False,
    use_clipboard: bool = False,
) -> Dict[str, Any]:
    """
    Injects Unicode text with sub-millisecond latency into the active focused window.
    Uses Win32 KEYEVENTF_UNICODE (VK_PACKET) with 100% fidelity across all scripts and emojis.
    
    FAST-PATH: In Calculator (calc.exe), directly type the entire mathematical formula followed by '='
    (e.g., text='45/5*2+10-11=') instead of clicking buttons individually.

    Args:
        text: Text string to type (full Unicode and emoji support).
        press_enter: If True, sends an Enter key immediately following the text.
        use_clipboard: If True (or text > 80 chars), injects via atomic clipboard paste.
    """
    ensure_dpi_aware()
    attach_input_desktop()
    _stall_breaker.check_safety_abort()

    t0 = time.perf_counter()
    # Guard: Calculator (calc.exe) strictly rejects clipboard paste containing operators or equals ("Invalid input").
    # Always use native instant_type (VK_PACKET) when Calculator is focused.
    fg = get_foreground_window()
    is_calc = fg and ("calculator" in fg.title.lower() or "calc" in fg.title.lower())

    if is_calc:
        instant_type(text, press_enter=press_enter)
        method = "vk_packet"
    elif use_clipboard or len(text) > 80:
        atomic_clipboard_paste(text)
        if press_enter:
            send_hotkey(["enter"])
        method = "clipboard"
    else:
        instant_type(text, press_enter=press_enter)
        method = "vk_packet"
    duration_ms = (time.perf_counter() - t0) * 1000.0

    return {
        "success": True,
        "length": len(text),
        "duration_ms": round(duration_ms, 2),
        "method": method,
    }


@server.tool()
def extra_hotkey(keys: List[str]) -> Dict[str, Any]:
    """
    Dispatches a synchronized keyboard shortcut sequence.
    Example: ['ctrl', 'c'], ['win', 'r'], ['ctrl', 'shift', 'esc'], ['alt', 'tab'].
    
    Args:
        keys: List of key names to press together in order and release in reverse.
    """
    ensure_dpi_aware()
    attach_input_desktop()
    _stall_breaker.check_safety_abort()

    t0 = time.perf_counter()
    send_hotkey(keys)
    duration_ms = (time.perf_counter() - t0) * 1000.0

    return {
        "success": True,
        "keys": keys,
        "duration_ms": round(duration_ms, 2),
    }


@server.tool()
def extra_inspect_ui(
    window_title: Optional[str] = None,
    hwnd: Optional[int] = None,
    interactive_only: bool = True,
    max_elements: int = 50,
) -> Dict[str, Any]:
    """
    Queries Microsoft UI Automation Core v3 to return accessible controls with exact bounding boxes.
    Allows zero-token semantic targeting without vision hallucinations.
    
    NOTE: For Calculator calculations, do NOT use this to inspect individual digit buttons;
    use extra_type to inject the entire formula directly.

    Args:
        window_title: Optional substring of window title to inspect (e.g. 'Calculator', 'Chrome').
        hwnd: Optional explicit window handle.
        interactive_only: If True, returns only interactive buttons, edits, links, tabs.
        max_elements: Maximum elements to return (default 50).
    """
    ensure_dpi_aware()
    attach_input_desktop()

    target_hwnd = hwnd
    if not target_hwnd and window_title:
        win = find_window_by_title(window_title)
        if win:
            target_hwnd = win.hwnd

    t0 = time.perf_counter()
    elements = _uia_plane.inspect_window(
        hwnd=target_hwnd, interactive_only=interactive_only, max_elements=max_elements
    )
    duration_ms = (time.perf_counter() - t0) * 1000.0

    return {
        "success": True,
        "count": len(elements),
        "duration_ms": round(duration_ms, 2),
        "elements": [el.to_dict() for el in elements],
    }


@server.tool()
def extra_click_element(element_id: int) -> Dict[str, Any]:
    """
    Activates an element previously discovered via extra_inspect_ui or extra_screenshot Set-of-Mark.
    Tries direct COM InvokePattern in < 1ms first, falling back to physical center hardware click.
    
    NOTE: Never use this in a loop to click individual number or operator buttons in Calculator;
    use extra_type instead to inject the formula in one step.

    Args:
        element_id: The integer ID of the element (e.g. 1, 2, 5).
    """
    ensure_dpi_aware()
    attach_input_desktop()
    _stall_breaker.check_safety_abort()

    t0 = time.perf_counter()
    success = _uia_plane.invoke_element(element_id)
    duration_ms = (time.perf_counter() - t0) * 1000.0

    return {
        "success": success,
        "element_id": element_id,
        "duration_ms": round(duration_ms, 2),
    }


@server.tool()
def extra_launch(app_name: str, args: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Deterministically launches standard Windows applications and tools.
    Supported shortcuts: 'calc', 'notepad', 'explorer', 'settings', 'cmd', 'terminal', 'edge', 'chrome', 'brave'.
    
    Args:
        app_name: Tool name or executable (e.g. 'calc', 'notepad', 'explorer', 'settings').
        args: Optional list of command-line arguments.
    """
    ensure_dpi_aware()
    attach_input_desktop()

    res = launch_app(app_name=app_name, args=args, wait_for_window=True)
    return res.to_dict()


@server.tool()
def extra_browser(
    action: str,
    url: Optional[str] = None,
    selector: Optional[str] = None,
    value: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executes web automation via Microsoft Edge / Playwright without vision overhead.
    
    Actions:
        - 'navigate': Opens url.
        - 'content': Extracts clean semantic markdown text.
        - 'click': Clicks CSS/XPath selector.
        - 'fill': Types text into selector.
        - 'eval': Evaluates JavaScript string in value.
        - 'screenshot': Returns page base64 screenshot.
        - 'close': Closes browser.
    """
    return execute_browser_action(action=action, url=url, selector=selector, value=value)


@server.tool()
def extra_focus_window(
    window_title: Optional[str] = None,
    hwnd: Optional[int] = None,
    timeout: float = 3.0,
) -> Dict[str, Any]:
    """
    Forces a target application window to the foreground, bypassing Windows lock restrictions.
    Supports polling retry to handle asynchronously initializing windows (Fixes #4, credit: @harshbuttru3).
    
    Args:
        window_title: Window title query substring.
        hwnd: Direct window handle.
        timeout: Maximum seconds to poll for the window if not immediately found (default: 3.0s).
    """
    ensure_dpi_aware()
    attach_input_desktop()

    target_hwnd = hwnd
    if not target_hwnd and window_title:
        win = find_window_by_title(window_title, timeout=timeout)
        if win:
            target_hwnd = win.hwnd

    if not target_hwnd:
        return {"success": False, "error": f"Window '{window_title}' not found (timed out after {timeout:.1f}s)."}

    ok = force_activate_window(target_hwnd)
    return {"success": ok, "hwnd": target_hwnd}


@server.tool()
def extra_scroll(delta: int, horizontal: bool = False) -> Dict[str, Any]:
    """
    Scrolls the mouse wheel vertically or horizontally.
    Positive delta scrolls up/right, negative scrolls down/left.
    """
    ensure_dpi_aware()
    attach_input_desktop()
    mouse_scroll(delta, horizontal=horizontal)
    return {"success": True, "delta": delta, "horizontal": horizontal}


@server.tool()
def extra_drag(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    button: str = "left",
    normalized: bool = False,
    monitor_index: int = 0,
) -> Dict[str, Any]:
    """Performs a smooth click-and-drag from start to end coordinates."""
    ensure_dpi_aware()
    attach_input_desktop()

    if normalized:
        sx, sy = denormalize_coordinates(start_x, start_y, monitor_index)
        ex, ey = denormalize_coordinates(end_x, end_y, monitor_index)
    else:
        sx, sy = start_x, start_y
        ex, ey = end_x, end_y

    mouse_drag(sx, sy, ex, ey, button=button, monitor_index=monitor_index)
    return {"success": True, "start": [sx, sy], "end": [ex, ey]}


@server.tool()
def extra_task_start(
    task_name: Optional[str] = None,
    monitor_index: int = 0,
) -> Dict[str, Any]:
    """
    Signals the start of an autonomous computer use task.
    Activates the ambient screen edge pulse (visible to human peripheral vision)
    and attaches the interactive cursor halo.
    
    NOTE: Both overlays are automatically excluded from screenshots via SetWindowDisplayAffinity.
    
    Args:
        task_name: Human-readable description of the task (e.g. 'Generate Q3 Report in Excel').
        monitor_index: 0-based monitor index to illuminate.
    """
    ensure_dpi_aware()
    attach_input_desktop()
    ctrl = get_indicator_controller()
    ctrl.task_start(task_name=task_name, monitor_index=monitor_index)
    return {"success": True, "task_name": task_name, "status": "active"}


@server.tool()
def extra_task_complete(
    summary: Optional[str] = None,
    success: bool = True,
    play_chime: bool = True,
) -> Dict[str, Any]:
    """
    Signals that the autonomous computer use task is completed.
    Triggers:
    1. The ambient screen edge flashes soft emerald green for ~1.5s, then dissolves.
    2. A pleasant multi-harmonic audio chime plays, informing the user immediately even if away from the screen.
    3. The cursor beacon dismisses cleanly.
    
    Args:
        summary: Optional completion summary (e.g. 'Spreadsheet saved to Desktop and email sent').
        success: Whether the task succeeded (plays positive chime) or needs attention (plays alert). Default True.
        play_chime: If True, plays the synthesized acoustic chime. Default True.
    """
    ensure_dpi_aware()
    attach_input_desktop()
    ctrl = get_indicator_controller()
    ctrl.task_complete(summary=summary, success=success, play_chime=play_chime)
    return {
        "success": True,
        "summary": summary,
        "status": "completed" if success else "failed",
    }


@server.tool()
def extra_indicate_status(
    status: str = "active",
    message: Optional[str] = None,
    play_sound: bool = False,
) -> Dict[str, Any]:
    """
    Controls human-agent awareness indicators on the Windows desktop.
    
    Args:
        status: One of 'active' (pulsing border + cursor halo), 'complete' (green flash + chime), or 'idle'/'stop' (hide indicators).
        message: Optional status or summary note.
        play_sound: Whether to play a chime.
    """
    ensure_dpi_aware()
    attach_input_desktop()
    ctrl = get_indicator_controller()
    st = status.lower().strip()
    if st in ("active", "running", "busy"):
        ctrl.task_start(task_name=message)
    elif st in ("complete", "completed", "done", "success"):
        ctrl.task_complete(summary=message, success=True, play_chime=play_sound)
    elif st in ("fail", "failed", "error", "abort"):
        ctrl.task_complete(summary=message, success=False, play_chime=play_sound)
    else:
        ctrl.task_stop()
    return {"success": True, "status": st, "message": message}


def main() -> None:
    """Starts the Extra MCP server over stdio transport."""
    ensure_dpi_aware()
    attach_input_desktop()
    logger.info("Extra Flashless MCP Server initializing on stdio transport...")
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
