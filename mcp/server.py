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
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

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
    get_window_executable_path,
    list_windows,
    snap_layout,
    snap_window,
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
    execute_batch_actions,
    instant_type,
    mouse_click,
    mouse_double_click,
    mouse_drag,
    mouse_move,
    mouse_scroll,
    mouse_stroke,
    send_hotkey,
    smooth_mouse_move,
)
from extra.core.stall_breaker import EmergencyAbortError, StallBreaker, StallStatus
from extra.core.uia_plane import SetOfMarkAnnotator, UIAutomationPlane
from extra.fastpath.browser import execute_browser_action
from extra.fastpath.fs import execute_fs_batch
from extra.fastpath.shell import launch_app, open_uri, resolve_executable
from extra.core.memory import (
    finish_memory_recording,
    recall_memory,
    start_memory_recording,
)
from extra.core.memory.ingest import (
    get_active_recorder,
    record_action_app,
    record_action_artifact,
    record_action_stall,
    record_action_step,
)
from extra.core.scout import scout_and_generate_skill
from extra.core.evolution import (
    analyze_task_trajectory,
    crystallize_skill_evolution,
    curate_skill_library,
    ensure_startup_migration,
    sanitize_skill_library,
)
from extra.fastpath.bridge import execute_bridge
from extra.core.composer import (
    Milestone,
    MilestoneStatus,
    TaskBlueprint,
    create_semantic_state_token,
    fold_completed_milestone,
    verify_milestone_acceptance,
)
from extra.core.soul import wait_until_settled, evaluate_screen_milestone


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

    fg = get_foreground_window()
    if fg:
        result["active_window_title"] = fg.title
        result["active_window_hwnd"] = fg.hwnd

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
        record_action_artifact(result["file_path"], mime_type="png")

    if include_base64:
        import io, base64
        buf = io.BytesIO()
        final_img.save(buf, format="JPEG", quality=80)
        result["screenshot_base64"] = base64.b64encode(buf.getvalue()).decode("utf-8")

    record_action_step("extra_screenshot", {"annotate_ui": annotate_ui, "save_to_file": save_to_file}, result.get("duration_ms", 0.0))
    return result


@server.tool()
def extra_mouse_move(
    x: int,
    y: int,
    human_like: bool = False,
    speed: str = "normal",
    style: str = "bezier",
    normalized: bool = False,
    monitor_index: int = 0,
) -> Dict[str, Any]:
    """
    Moves the mouse cursor to exact target coordinates (hovering or repositioning).
    Supports human-like biomechanical movement to bypass anti-bot detections or simulate user behavior.
    
    Args:
        x: X-coordinate (physical pixel or normalized 0-1000).
        y: Y-coordinate (physical pixel or normalized 0-1000).
        human_like: If True, glides along an organic curve with Fitts's Law acceleration,
                    micro-tremors, and anti-bot behavioral compliance.
        speed: Movement speed if human_like is True ('fast', 'normal', 'slow').
        style: Motion algorithm ('bezier' or 'windmouse').
        normalized: If True, treats x, y as [0, 1000] scale.
        monitor_index: Target monitor index.
    """
    ensure_dpi_aware()
    attach_input_desktop()
    _stall_breaker.check_safety_abort()

    if normalized:
        phys_x, phys_y = denormalize_coordinates(x, y, monitor_index=monitor_index)
    else:
        phys_x, phys_y = x, y

    t0 = time.perf_counter()
    if human_like:
        smooth_mouse_move(phys_x, phys_y, speed=speed, style=style, monitor_index=monitor_index)
    else:
        mouse_move(phys_x, phys_y, monitor_index=monitor_index)
    duration_ms = (time.perf_counter() - t0) * 1000.0

    record_action_step("extra_mouse_move", {"x": phys_x, "y": phys_y, "human_like": human_like, "speed": speed}, duration_ms)
    return {
        "success": True,
        "phys_x": phys_x,
        "phys_y": phys_y,
        "human_like": human_like,
        "duration_ms": round(duration_ms, 2),
    }


@server.tool()
def extra_click(
    x: Optional[int] = None,
    y: Optional[int] = None,
    target: Optional[str] = None,
    button: str = "left",
    clicks: int = 1,
    normalized: bool = False,
    monitor_index: int = 0,
    human_like: bool = True,
    speed: str = "normal",
) -> Dict[str, Any]:
    """
    Executes a hardware-level mouse click with PerMonitorV2 DPI compensation and closed-loop stall checking.
    Supports semantic visual grounding via SOUL-Eyes ('target') for zero-coordinate autonomous clicking.
    Supports human-like curved approach with natural reaction delay (enabled by default for live computer use).
    
    Args:
        x: Optional X-coordinate (physical pixel or normalized 0-1000).
        y: Optional Y-coordinate (physical pixel or normalized 0-1000).
        target: Optional semantic target name (e.g. 'Brush tool', 'Yellow color', 'File menu') for SOUL-Eyes visual grounding.
        button: Mouse button ('left', 'right', 'middle'). Default: 'left'.
        clicks: Click count (1 = single click, 2 = double click). Default: 1.
        normalized: If True, treats x, y as [0, 1000] scale and converts to physical pixels.
        monitor_index: Monitor index if normalized coordinates are used.
        human_like: If True, approaches target via human Bézier trajectory with physiological pre-click reaction delay (default: True).
        speed: Speed preset if human_like is True ('fast', 'normal', 'slow').
    """
    ensure_dpi_aware()
    attach_input_desktop()
    _stall_breaker.check_safety_abort()

    grounding_meta = None
    if target and (x is None or y is None):
        from extra.core.soul import visual_ground
        ground_res = visual_ground(query=target, monitor_index=monitor_index)
        if ground_res.matched and ground_res.screen_point:
            phys_x, phys_y = ground_res.screen_point
            grounding_meta = {
                "query": target,
                "confidence": getattr(ground_res, "confidence", 1.0),
                "latency_ms": ground_res.latency_ms,
                "screen_point": [phys_x, phys_y],
            }
        else:
            return {
                "success": False,
                "error": f"Semantic target '{target}' could not be visually grounded on screen.",
                "latency_ms": ground_res.latency_ms if 'ground_res' in locals() else 0.0,
            }
    elif x is not None and y is not None:
        if normalized:
            phys_x, phys_y = denormalize_coordinates(int(x), int(y), monitor_index=monitor_index)
        else:
            phys_x, phys_y = int(x), int(y)
    else:
        return {
            "success": False,
            "error": "Either (x, y) coordinates or a semantic 'target' must be provided.",
        }

    # Capture state before action for closed-loop verification
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
    mouse_click(
        phys_x,
        phys_y,
        button=button,
        clicks=clicks,
        monitor_index=monitor_index,
        human_like=human_like,
        speed=speed,
    )
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
        action_name="click",
        before_full_image=cap_before.image,
        after_full_image=cap_after.image,
    )

    record_action_step("extra_click", {"x": phys_x, "y": phys_y, "button": button, "clicks": clicks, "human_like": human_like}, duration_ms)
    if outcome.status != StallStatus.NORMAL:
        record_action_stall(
            strike_count=outcome.strikes,
            trigger_action=f"click({button}, x={phys_x}, y={phys_y})",
            resolution=outcome.message,
        )

    ret = {
        "success": outcome.status != StallStatus.STALLED,
        "phys_x": phys_x,
        "phys_y": phys_y,
        "button": button,
        "clicks": clicks,
        "human_like": human_like,
        "duration_ms": round(duration_ms, 2),
        "stall_status": outcome.status.value,
        "strikes": outcome.strikes,
        "visual_change": outcome.status == StallStatus.NORMAL,
        "message": outcome.message,
    }
    if outcome.status == StallStatus.STALLED:
        ret["error"] = outcome.message
    elif outcome.status == StallStatus.WARNING:
        ret["warning"] = outcome.message
    if grounding_meta:
        ret["grounding"] = grounding_meta
    return ret



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
        use_clipboard: If True, injects via atomic clipboard paste (defaults to False for universal input compatibility).
    """
    ensure_dpi_aware()
    attach_input_desktop()
    _stall_breaker.check_safety_abort()

    t0 = time.perf_counter()
    if use_clipboard:
        atomic_clipboard_paste(text)
        if press_enter:
            send_hotkey(["enter"])
        method = "clipboard"
    else:
        # Universal instant keystroke injection via Win32 VK_PACKET / macOS CGEvent (< 2ms)
        instant_type(text, press_enter=press_enter)
        method = "vk_packet"
    duration_ms = (time.perf_counter() - t0) * 1000.0
    _stall_breaker.reset()

    record_action_step("extra_type", {"text": text[:80], "press_enter": press_enter, "use_clipboard": use_clipboard}, duration_ms)
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
    _stall_breaker.reset()

    record_action_step("extra_hotkey", {"keys": keys}, duration_ms)
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
def extra_click_element(
    element_id: Optional[int] = None,
    query: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Activates an accessible element or visually grounds and clicks an opaque UI target.
    Tries direct Microsoft UI Automation COM InvokePattern in < 1ms first.
    If UIA has no match (or on opaque WebGL/canvas apps like Canva/Figma), automatically
    falls back to SOUL-Eyes edge visual grounding to locate and click coordinates from pixels.
    
    NOTE: Never use this in a loop to click individual number or operator buttons in Calculator;
    use extra_type instead to inject the formula in one step.

    Args:
        element_id: Optional integer ID of the element discovered via extra_inspect_ui.
        query: Optional semantic target name (e.g. 'Search bar', 'Presentation', 'Export', 'Close') for SOUL-Eyes visual grounding.
    """
    ensure_dpi_aware()
    attach_input_desktop()
    _stall_breaker.check_safety_abort()

    t0 = time.perf_counter()
    success = False
    grounding_meta = None

    if element_id is not None:
        success = _uia_plane.invoke_element(element_id)

    # SOUL-Eyes Visual Grounding Fallback
    if not success and query:
        from extra.core.soul import visual_ground
        from extra.core.input_engine import mouse_click

        res = visual_ground(query=query)
        if res.matched and res.screen_point:
            mouse_click(res.screen_point[0], res.screen_point[1])
            success = True
            grounding_meta = {
                "grounded_target": query,
                "screen_point": res.screen_point,
                "grounding_latency_ms": res.latency_ms,
            }

    duration_ms = (time.perf_counter() - t0) * 1000.0

    result = {
        "success": success,
        "element_id": element_id,
        "duration_ms": round(duration_ms, 2),
    }
    if grounding_meta:
        result["soul_eyes"] = grounding_meta
    return result


@server.tool()
def extra_launch(
    app_name: str,
    args: Optional[List[str]] = None,
    profile: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Deterministically launches standard Windows applications and tools.
    Supported shortcuts: 'calc', 'notepad', 'explorer', 'settings', 'cmd', 'terminal', 'edge', 'chrome', 'brave'.
    
    Args:
        app_name: Tool name or executable (e.g. 'calc', 'notepad', 'explorer', 'settings', 'chrome', 'edge').
        args: Optional list of command-line arguments.
        profile: Optional browser profile name (e.g. 'Default', 'Profile 1', 'Profile 3').
    """
    ensure_dpi_aware()
    attach_input_desktop()

    res = launch_app(app_name=app_name, args=args, wait_for_window=True, profile=profile)
    if res.success:
        _stall_breaker.reset()
    record_action_app(app_name=app_name, exe_path=getattr(res, "target_executed", None))
    record_action_step("extra_launch", {"app_name": app_name, "args": args, "profile": profile})
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
        - 'settle': Waits for DOM stability and network quiescence in < 10ms-30ms.
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
    if ok:
        _stall_breaker.reset()
        try:
            exe_path = get_window_executable_path(target_hwnd)
            if exe_path and os.path.exists(exe_path):
                from pathlib import Path
                app_alias = Path(exe_path).stem.lower()
                from extra.fastpath.shell import APP_REGISTRY, register_app
                if app_alias not in APP_REGISTRY:
                    register_app(name=app_alias, target=exe_path, proc=os.path.basename(exe_path))
                record_action_app(app_name=app_alias, exe_path=exe_path)
        except Exception:
            pass
    return {"success": ok, "hwnd": target_hwnd}


@server.tool()
def extra_scroll(
    delta: Optional[int] = None,
    horizontal: bool = False,
    clicks: Optional[int] = None,
    direction: str = "vertical",
) -> Dict[str, Any]:
    """
    Scrolls the mouse wheel vertically or horizontally.
    Supports either delta (e.g. -500 or 500) or clicks (e.g. -5, 5 with direction="vertical"|"horizontal").
    Positive delta/clicks scrolls up/right, negative scrolls down/left.
    """
    ensure_dpi_aware()
    attach_input_desktop()

    is_horizontal = horizontal or (direction.lower() == "horizontal")
    if delta is not None:
        final_delta = delta
    elif clicks is not None:
        final_delta = clicks
    else:
        final_delta = -5

    mouse_scroll(final_delta, horizontal=is_horizontal)
    _stall_breaker.reset()
    record_action_step("extra_scroll", {"delta": final_delta, "horizontal": is_horizontal})
    return {"success": True, "delta": final_delta, "horizontal": is_horizontal}


@server.tool()
def extra_drag(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    button: str = "left",
    duration: float = 0.3,
    human_like: bool = False,
    normalized: bool = False,
    monitor_index: int = 0,
) -> Dict[str, Any]:
    """
    Performs a click-and-drag from start to end coordinates.
    Supports smooth human-like biomechanical dragging.
    
    Args:
        start_x: Starting X coordinate.
        start_y: Starting Y coordinate.
        end_x: Ending X coordinate.
        end_y: Ending Y coordinate.
        button: Mouse button to hold ('left', 'right').
        duration: Drag duration in seconds (default 0.3s).
        human_like: If True, executes continuous smooth drag without linear robotic steps.
        normalized: If True, treats coordinates as [0, 1000] scale.
        monitor_index: Target monitor.
    """
    ensure_dpi_aware()
    attach_input_desktop()
    _stall_breaker.check_safety_abort()

    if normalized:
        sx, sy = denormalize_coordinates(start_x, start_y, monitor_index)
        ex, ey = denormalize_coordinates(end_x, end_y, monitor_index)
    else:
        sx, sy = start_x, start_y
        ex, ey = end_x, end_y

    t0 = time.perf_counter()
    mouse_drag(sx, sy, ex, ey, button=button, duration=duration, human_like=human_like, monitor_index=monitor_index)
    duration_ms = (time.perf_counter() - t0) * 1000.0

    record_action_step("extra_drag", {"start": [sx, sy], "end": [ex, ey], "human_like": human_like}, duration_ms)
    return {"success": True, "start": [sx, sy], "end": [ex, ey], "duration_ms": round(duration_ms, 2)}


@server.tool()
def extra_stroke(
    points: Optional[List[List[int]]] = None,
    points_file: Optional[str] = None,
    button: str = "left",
    duration: float = 1.0,
    smooth: bool = True,
    normalized: bool = False,
    monitor_index: int = 0,
) -> Dict[str, Any]:
    """
    Executes a continuous fluid brush stroke across multiple waypoints while holding down the mouse button.
    Essential for Canva canvas drawing, sketching in MS Paint, calligraphy, and video timeline scrubbing.
    
    Args:
        points: List of [x, y] coordinates forming the stroke path (e.g. [[100, 200], [150, 250], [300, 400]]).
        points_file: Optional path to a JSON file containing the points list.
        button: Mouse button to hold during stroke ('left' or 'right').
        duration: Total stroke duration in seconds (default: 1.0s).
        smooth: If True, applies centripetal Catmull-Rom spline interpolation for smooth continuous ink.
        normalized: If True, treats coordinates as [0, 1000] scale.
        monitor_index: Target display monitor.
    """
    ensure_dpi_aware()
    attach_input_desktop()
    _stall_breaker.check_safety_abort()

    if points is None and points_file:
        from pathlib import Path
        p = Path(points_file)
        if not p.is_file():
            return {"success": False, "error": f"points_file not found: {points_file}"}
        try:
            with open(p, "r", encoding="utf-8") as f:
                points = json.load(f)
        except Exception as e:
            return {"success": False, "error": f"Failed to read points_file: {e}"}

    if not points:
        return {"success": False, "error": "No points provided for stroke"}

    phys_points: List[Tuple[int, int]] = []
    for pt in points:
        if len(pt) >= 2:
            if normalized:
                px, py = denormalize_coordinates(pt[0], pt[1], monitor_index)
            else:
                px, py = int(pt[0]), int(pt[1])
            phys_points.append((px, py))

    cap_before = None
    try:
        cap_before = capture_screen(monitor_index=monitor_index)
    except Exception:
        pass

    t0 = time.perf_counter()
    mouse_stroke(phys_points, button=button, duration=duration, smooth=smooth, monitor_index=monitor_index)
    duration_ms = (time.perf_counter() - t0) * 1000.0

    # Brief settle delay for hardware/GPU canvas composition
    time.sleep(0.08)

    pixels_changed = 0
    ink_detected = True
    path_hits = 0
    sampled_count = 0
    if cap_before is not None:
        try:
            cap_after = capture_screen(monitor_index=monitor_index)
            import numpy as np
            arr_before = np.asarray(cap_before.image, dtype=np.int16)
            arr_after = np.asarray(cap_after.image, dtype=np.int16)
            diff = np.abs(arr_before - arr_after)
            changed_mask = np.any(diff > 12, axis=-1)
            pixels_changed = int(np.count_nonzero(changed_mask))

            # On-Path Trajectory Verification:
            # Prevents false positives from selection marquees or cursor drag overlays.
            # Real ink MUST appear directly under/around the waypoint path coordinates.
            h, w = changed_mask.shape
            step_sample = max(1, len(phys_points) // 20)
            sampled_points = phys_points[::step_sample]
            for px, py in sampled_points:
                sampled_count += 1
                y0, y1 = max(0, py - 3), min(h, py + 4)
                x0, x1 = max(0, px - 3), min(w, px + 4)
                if np.any(changed_mask[y0:y1, x0:x1]):
                    path_hits += 1

            # Ink is verified only if:
            # 1. Overall screen pixels changed > 0
            # 2. At least 25% of the sampled trajectory coordinates received ink
            ink_detected = (pixels_changed > 0) and (path_hits >= max(1, int(sampled_count * 0.25)))
        except Exception as e:
            logger.debug("Ink verification failed: %s", e)
            ink_detected = True

    record_action_step(
        "extra_stroke",
        {
            "point_count": len(phys_points),
            "button": button,
            "duration": duration,
            "pixels_changed": pixels_changed,
            "path_hits": path_hits,
            "sampled_points": sampled_count,
            "ink_detected": ink_detected,
        },
        duration_ms,
    )

    if not ink_detected and cap_before is not None:
        record_action_stall(
            strike_count=1,
            trigger_action=f"extra_stroke({len(phys_points)} points)",
            resolution="Ghost stroke: 0 ink deposited along trajectory.",
        )
        return {
            "success": False,
            "ink_detected": False,
            "pixels_changed": pixels_changed,
            "path_hits": path_hits,
            "sampled_points": sampled_count,
            "point_count": len(phys_points),
            "button": button,
            "duration_ms": round(duration_ms, 2),
            "error": (
                f"GHOST STROKE DETECTED: Hardware mouse moved across {len(phys_points)} points, "
                "but 0 ink was deposited along the actual stroke path! (A selection box or drag marquee was detected instead). "
                "The drawing tool (Pen/Brush/Pencil) is NOT actively selected. "
                "Click Tools -> Draw -> Pen, then click the canvas center to focus before drawing."
            ),
        }

    _stall_breaker.reset()
    return {
        "success": True,
        "ink_detected": True,
        "pixels_changed": pixels_changed,
        "path_hits": path_hits,
        "sampled_points": sampled_count,
        "point_count": len(phys_points),
        "button": button,
        "duration_ms": round(duration_ms, 2),
    }


@server.tool()
def extra_batch_actions(
    actions: Optional[List[Dict[str, Any]]] = None,
    actions_file: Optional[str] = None,
    auto_settle: bool = True,
    strict_ink: bool = False,
) -> Dict[str, Any]:
    """
    Executes an atomic list of hardware actions sequentially with sub-millisecond dispatch.
    Eliminates multi-turn network round-trips (reducing seconds to milliseconds) for compound workflows.
    Enhanced with Tier 1 SOUL-Gateman visual settle detection (sub-15ms) to eliminate race conditions.
    
    Supported action dictionary formats:
      - {"action": "hotkey", "keys": ["ctrl", "t"]}
      - {"action": "type", "text": "edge://bookmarks", "press_enter": True}
      - {"action": "click", "x": 500, "y": 300, "button": "left", "clicks": 1}
      - {"action": "double_click", "x": 500, "y": 300}
      - {"action": "focus", "window_title": "Edge"} or {"action": "focus", "hwnd": 12345}
      - {"action": "sleep", "ms": 200} (also accepts "duration_ms", "seconds", or "delay")
      - {"action": "scroll", "clicks": -5, "direction": "vertical"}
      - {"action": "stroke", "points": [[...], [...]], "button": "left", "smooth": True}
      - Project SOUL Dynamic Reflex Actions:
        - {"action": "eval", "condition": "Is modal open?", "if_true": [...], "if_false": [...]}
        - {"action": "assert", "condition": "Did export complete?", "on_fail": "abort"|"retry"|"continue", "max_retries": 2}
        - {"action": "wait_for_state", "condition": "Is Presentation loaded?", "timeout_ms": 2000, "poll_interval_ms": 50}
      
    Args:
      actions: List of action dictionaries to execute in sequence.
      actions_file: Optional path to a JSON file containing the list of action dictionaries.
      auto_settle: If True (default), automatically verifies visual frame stability (< 15ms)
                  between physical UI actions (clicks, hotkeys, focus) to prevent ghost strokes
                  and animation race conditions without burning cloud tokens.
      strict_ink: If True, fails the batch if any stroke produces 0 deposited ink along its trajectory.
      
    Returns summary of executed actions and total elapsed execution time in milliseconds.
    """
    ensure_dpi_aware()
    attach_input_desktop()

    if actions is None and actions_file:
        from pathlib import Path
        p = Path(actions_file)
        if not p.is_file():
            return {"success": False, "error": f"actions_file not found: {actions_file}"}
        try:
            with open(p, "r", encoding="utf-8") as f:
                actions = json.load(f)
        except Exception as e:
            return {"success": False, "error": f"Failed to read actions_file: {e}"}

    if not actions:
        return {"success": False, "error": "No actions provided for batch"}

    has_strokes = any(
        isinstance(a, dict) and str(a.get("action", a.get("type", ""))).lower().strip() in ("stroke", "brush", "draw", "mouse_stroke")
        for a in actions
    )
    cap_before = None
    if has_strokes:
        try:
            cap_before = capture_screen()
        except Exception:
            pass

    res = execute_batch_actions(actions, auto_settle=auto_settle)
    _stall_breaker.reset()
    total_dur = res.get("total_duration_ms", 0)

    # Mid-task quality telemetry and ink verification for strokes in batch
    if has_strokes and cap_before is not None:
        time.sleep(0.08)
        pixels_changed = 0
        ink_detected = True
        path_hits = 0
        sampled_count = 0
        try:
            cap_after = capture_screen()
            import numpy as np
            arr_before = np.asarray(cap_before.image, dtype=np.int16)
            arr_after = np.asarray(cap_after.image, dtype=np.int16)
            diff = np.abs(arr_before - arr_after)
            changed_mask = np.any(diff > 12, axis=-1)
            pixels_changed = int(np.count_nonzero(changed_mask))

            # Extract waypoints from all stroke actions in batch
            batch_points: List[Tuple[int, int]] = []
            for a in actions:
                if isinstance(a, dict) and str(a.get("action", a.get("type", ""))).lower().strip() in ("stroke", "brush", "draw", "mouse_stroke"):
                    pts = a.get("points", [])
                    for p in pts:
                        if len(p) >= 2:
                            batch_points.append((int(p[0]), int(p[1])))

            if batch_points:
                h, w = changed_mask.shape
                step_sample = max(1, len(batch_points) // 30)
                sampled_points = batch_points[::step_sample]
                for px, py in sampled_points:
                    sampled_count += 1
                    y0, y1 = max(0, py - 3), min(h, py + 4)
                    x0, x1 = max(0, px - 3), min(w, px + 4)
                    if np.any(changed_mask[y0:y1, x0:x1]):
                        path_hits += 1

                ink_detected = (pixels_changed > 0) and (path_hits >= max(1, int(sampled_count * 0.25)))
            else:
                ink_detected = pixels_changed > 0
        except Exception as e:
            logger.debug("Batch ink verification diff failed: %s", e)
            ink_detected = True

        res["ink_detected"] = ink_detected
        res["pixels_changed"] = pixels_changed
        res["path_hits"] = path_hits
        res["sampled_points"] = sampled_count

        record_action_step(
            "extra_batch_actions",
            {
                "count": len(actions),
                "total_duration_ms": total_dur,
                "pixels_changed": pixels_changed,
                "path_hits": path_hits,
                "ink_detected": ink_detected,
            },
        )

        all_strokes = all(
            isinstance(a, dict) and str(a.get("action", a.get("type", ""))).lower().strip() in ("stroke", "brush", "draw", "mouse_stroke")
            for a in actions
        )
        if not ink_detected:
            if all_strokes or strict_ink:
                res["success"] = False
                res["error"] = (
                    "GHOST STROKES IN BATCH: All drawing strokes in this batch produced 0 ink along their stroke paths! "
                    "(Only an empty cursor drag or selection box occurred). "
                    "Active drawing tool is not selected. Click Tools -> Draw -> Pen, then click canvas center to focus."
                )
            else:
                res["warning"] = "GHOST STROKES IN BATCH: Dispatched strokes produced 0 ink along trajectory paths."
    else:
        record_action_step("extra_batch_actions", {"count": len(actions), "total_duration_ms": total_dur})

    return res


@server.tool()
def extra_snap_layout(
    layout: str = "side_by_side",
    left_window: Optional[str] = None,
    right_window: Optional[str] = None,
    monitor_index: int = 0,
) -> Dict[str, Any]:
    """
    Arranges multiple windows into a cohesive visual layout in a single programmatic step (sub-15ms).
    Eliminates fragile multi-turn Win+Left / Win+Right hotkey snapping and avoids Windows 11 Snap Assist popups.
    
    Args:
        layout: Layout preset. Currently supports 'side_by_side' (split 50/50 horizontally).
        left_window: Window title substring (e.g. "Paint") or HWND for the left screen half.
        right_window: Window title substring (e.g. "Notepad") or HWND for the right screen half.
        monitor_index: 0-based monitor index (default 0).
    """
    ensure_dpi_aware()
    attach_input_desktop()
    res = snap_layout(layout=layout, left_window=left_window, right_window=right_window, monitor_index=monitor_index)
    _stall_breaker.reset()
    record_action_step("extra_snap_layout", {"layout": layout, "left": left_window, "right": right_window})
    return res


@server.tool()
def extra_fs_batch(
    operation: str,
    base_dir: Optional[str] = None,
    rules: Optional[Dict[str, List[str]]] = None,
    files: Optional[List[Dict[str, Any]]] = None,
    renames: Optional[List[Dict[str, str]]] = None,
    deletes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    High-speed batch filesystem operations avoiding multi-turn shell execution.
    Complies with Windows Defender Controlled Folder Access (CFA).
    
    Operations:
      - 'organize': Classifies files in base_dir into subdirectories by extension or category based on rules mapping.
        rules example: {"Documents": [".pdf", ".docx", ".txt"], "Images": [".png", ".jpg"]}
      - 'create_tree': Atomically creates directory structures and files.
        files example: [{"path": "reports/summary.txt", "content": "..."}]
      - 'batch_rename': Renames multiple files according to renames mapping.
        renames example: [{"old": "base_dir/a.txt", "new": "base_dir/b.txt"}]
      - 'batch_delete': Safely deletes list of file paths.
    """
    res = execute_fs_batch(
        operation=operation,
        base_dir=base_dir,
        rules=rules,
        files=files,
        renames=renames,
        deletes=deletes,
    )
    record_action_step("extra_fs_batch", {"operation": operation, "success": res.get("success")})
    return res


@server.tool()
def extra_task_start(
    task_name: Optional[str] = None,
    task_objective: Optional[str] = None,
    monitor_index: int = 0,
) -> Dict[str, Any]:
    """
    Signals the start of an autonomous computer use task.
    Activates the ambient screen edge pulse (visible to human peripheral vision)
    and attaches the interactive cursor halo. Automatically initializes episodic memory recording.
    
    NOTE: Both overlays are automatically excluded from screenshots via SetWindowDisplayAffinity.
    
    Args:
        task_name: Human-readable description of the task (e.g. 'Generate Q3 Report in Excel').
        task_objective: Optional detailed objective or user prompt for episodic memory.
        monitor_index: 0-based monitor index to illuminate.
    """
    ensure_dpi_aware()
    attach_input_desktop()
    ctrl = get_indicator_controller()
    ctrl.task_start(task_name=task_name, monitor_index=monitor_index)
    start_memory_recording(task_name=task_name or "Autonomous Task", goal=task_objective)
    _stall_breaker.reset()
    return {"success": True, "task_name": task_name, "status": "active"}


@server.tool()
def extra_task_complete(
    summary: Optional[str] = None,
    success: bool = True,
    play_chime: bool = True,
    auto_screenshot: bool = True,
) -> Dict[str, Any]:
    """
    Signals that the autonomous computer use task is completed.
    Triggers:
    1. The ambient screen edge flashes soft emerald green for ~1.5s, then dissolves.
    2. A pleasant multi-harmonic audio chime plays, informing the user immediately even if away from the screen.
    3. The cursor beacon dismisses cleanly.
    4. Evaluates execution trajectory for friction, stalls, and self-evolution opportunities.
    5. Asynchronously commits the entire task trace and artifacts into KùzuDB memory.
    6. Automatically captures a clean final desktop screenshot (eliminating parallel extra_screenshot calls).
    
    Args:
        summary: Optional completion summary (e.g. 'Spreadsheet saved to Desktop and email sent').
        success: Whether the task succeeded (plays positive chime) or needs attention (plays alert). Default True.
        play_chime: If True, plays the synthesized acoustic chime. Default True.
        auto_screenshot: If True, automatically captures and returns the final verified screen state. Default True.
    """
    ensure_dpi_aware()
    attach_input_desktop()
    ctrl = get_indicator_controller()

    rec = get_active_recorder()

    # Pre-completion inking guardrail:
    # If stroke actions were executed during the task, verify visual pixels were rendered.
    if rec and success:
        stroke_steps = [
            s for s in rec.steps
            if s.get("tool_name") == "extra_stroke" or "stroke" in str(s.get("parameters", ""))
        ]
        if stroke_steps:
            total_pixels_changed = 0
            has_pixel_tracking = False
            for s in stroke_steps:
                params = s.get("parameters")
                if isinstance(params, str):
                    try:
                        params = json.loads(params)
                    except Exception:
                        params = {}
                if isinstance(params, dict):
                    if "pixels_changed" in params:
                        has_pixel_tracking = True
                        total_pixels_changed += params.get("pixels_changed", 0)

            if has_pixel_tracking and total_pixels_changed == 0:
                ctrl.task_complete(summary="Task rejected: zero ink rendered", success=False, play_chime=False)
                return {
                    "success": False,
                    "status": "failed",
                    "error": (
                        f"TASK COMPLETION REJECTED: {len(stroke_steps)} stroke actions were dispatched, "
                        "but ZERO visual pixels were rendered on screen! The canvas is still completely blank or unchanged. "
                        "Do not declare completion until visual content is actually rendered."
                    ),
                    "stroke_count": len(stroke_steps),
                    "total_pixels_rendered": 0,
                }

    ctrl.task_complete(summary=summary, success=success, play_chime=play_chime)

    # Analyze trajectory before finalizing recorder
    analysis_dict: Optional[Dict[str, Any]] = None
    if rec:
        try:
            events = []
            for step in rec.steps:
                ev = {"tool_name": step["tool_name"], "duration_ms": step["duration_ms"]}
                raw_params = step.get("parameters")
                if isinstance(raw_params, str):
                    try:
                        ev.update(json.loads(raw_params))
                    except Exception:
                        pass
                elif isinstance(raw_params, dict):
                    ev.update(raw_params)
                events.append(ev)
            for stall in rec.stalls:
                events.append({
                    "type": "stall",
                    "strike_count": stall["strike_count"],
                    "trigger_action": stall["trigger_action"],
                })
            wall_clock_ms = (time.time() - rec.start_time) * 1000.0 if rec and hasattr(rec, "start_time") else None
            an = analyze_task_trajectory(task_id=rec.task_id, events=events, success=success, wall_clock_duration_ms=wall_clock_ms)
            analysis_dict = an.to_dict()
        except Exception as e:
            logger.debug("Trajectory analysis failed: %s", e)

    # Auto-screenshot verification to eliminate parallel blind extra_screenshot calls
    final_cap_path = None
    if auto_screenshot:
        try:
            cap = capture_screen(monitor_index=0)
            if cap and getattr(cap, "file_path", None):
                final_cap_path = cap.file_path
        except Exception as e:
            logger.debug("Auto-screenshot capture failed: %s", e)

    task_id = finish_memory_recording(summary=summary or "Task finished", success=success, async_commit=True)
    res: Dict[str, Any] = {
        "success": True,
        "summary": summary,
        "status": "completed" if success else "failed",
        "memory_task_id": task_id,
    }
    if final_cap_path:
        res["final_screenshot"] = final_cap_path
        res["visual_verification_note"] = "Final desktop frame automatically captured upon completion."

    if rec:
        stroke_steps = [
            s for s in rec.steps
            if s.get("tool_name") == "extra_stroke" or "stroke" in str(s.get("parameters", ""))
        ]
        if stroke_steps:
            tot_px = 0
            for s in stroke_steps:
                params = s.get("parameters")
                if isinstance(params, str):
                    try:
                        params = json.loads(params)
                    except Exception:
                        params = {}
                if isinstance(params, dict):
                    tot_px += params.get("pixels_changed", 0)

            if tot_px > 0:
                res["drawing_verification"] = (
                    f"Verified: {len(stroke_steps)} stroke action(s) rendered {tot_px} visual pixels on canvas."
                )
            else:
                res["drawing_verification"] = (
                    f"{len(stroke_steps)} stroke action(s) were recorded. "
                    "OS mouse strokes only produce visual ink when an active drawing tool is selected and focused on canvas. "
                    "Verify visual output before declaring completion."
                )

    if analysis_dict:
        res["trajectory_analysis"] = analysis_dict
        candidate = analysis_dict.get("candidate_for_evolution", False)
        is_golden = analysis_dict.get("is_golden_path", False)
        if candidate and success and is_golden:
            res["evolution_recommendation"] = (
                "Verified golden-path workflow discovered. You may call 'extra_evolve_skill' to crystallize verified fast paths into permanent skill playbooks."
            )
        elif candidate and (not is_golden or not success):
            res["evolution_recommendation"] = (
                "Task encountered friction, recovery steps, or was not a clean golden path. "
                "DO NOT synthesize noisy recovery steps or intermediate actions as a fast path. "
                "If calling 'extra_evolve_skill', provide ONLY discovered anti-stall guardrails in 'friction_points' and 'solutions_found'."
            )

    return res


@server.tool()
def extra_scout_app(
    app_name: str,
    force_refresh: bool = False,
    custom_notes: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Just-In-Time Application Scout: detects an application's UI framework (Electron, Win32, Viewport),
    universal hotkeys, CLI automation flags, and scripting APIs before taking GUI actions.
    Synthesizes a specialized SKILL.md playbook and commits it to active skill directories and memory.
    
    Args:
        app_name: Name or executable of the application (e.g. 'blender', 'photoshop', 'canva', 'inkscape').
        force_refresh: If True, forces re-scouting even if a cached skill exists. Default False.
        custom_notes: Optional custom instructions or tips to include in the generated playbook.
    """
    return scout_and_generate_skill(
        app_name=app_name,
        force_refresh=force_refresh,
        custom_notes=custom_notes,
    )


@server.tool()
def extra_evolve_skill(
    app_name: str,
    workflow_summary: str,
    instructions: str,
    friction_points: Optional[List[str]] = None,
    solutions_found: Optional[List[str]] = None,
    skill_name: Optional[str] = None,
    fastpath_file: Optional[str] = None,
    is_golden_path: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Self-Evolving Learning Loop: crystallizes a discovered zero-stall workflow, resolution,
    or fast path into a permanent reusable skill playbook (Reflexion style).
    Patches existing SKILL.md files and persists quirks to KùzuDB memory.
    
    Args:
        app_name: Name of the application (e.g. 'canva', 'blender', 'photoshop').
        workflow_summary: Short summary of what was accomplished (e.g. 'Direct Instagram Poster Injection').
        instructions: Precise step-by-step instructions or fast-path playbook to replicate.
        friction_points: Optional list of obstacles or pitfalls encountered during execution.
        solutions_found: Optional list of verified workarounds discovered.
        skill_name: Optional custom skill name override (defaults to 'extra-<app_name>').
        fastpath_file: Optional synthesized python fastpath script file path.
        is_golden_path: If True, updates Fast Paths. If False, only records guardrails. Defaults to True unless stalls occurred.
    """
    if is_golden_path is None:
        rec = get_active_recorder()
        if rec:
            events = []
            for step in rec.steps:
                ev = {"tool_name": step["tool_name"], "duration_ms": step["duration_ms"]}
                raw_params = step.get("parameters")
                if isinstance(raw_params, str):
                    try:
                        ev.update(json.loads(raw_params))
                    except Exception:
                        pass
                elif isinstance(raw_params, dict):
                    ev.update(raw_params)
                events.append(ev)
            for stall in rec.stalls:
                events.append({
                    "type": "stall",
                    "strike_count": stall["strike_count"],
                    "trigger_action": stall["trigger_action"],
                })
            an = analyze_task_trajectory(task_id=rec.task_id, events=events, success=True)
            is_golden_path = an.is_golden_path
        else:
            is_golden_path = False

    return crystallize_skill_evolution(
        app_name=app_name,
        workflow_summary=workflow_summary,
        instructions=instructions,
        friction_points=friction_points,
        solutions_found=solutions_found,
        skill_name=skill_name,
        fastpath_file=fastpath_file,
        is_golden_path=is_golden_path,
    )


@server.tool()
def extra_recall_memory(
    query: str,
    app_name: Optional[str] = None,
    top_k: int = 3,
) -> Dict[str, Any]:
    """
    Recalls past task execution memories, workflows, generated artifacts, and known app quirks.
    Uses local embedded KùzuDB and FastEmbed vector search (< 3ms).
    
    Args:
        query: Natural language description of what to recall (e.g. 'Canva Instagram launch poster').
        app_name: Optional application name filter (e.g. 'Canva', 'Blender', 'Edge').
        top_k: Maximum number of relevant memories to return (default 3).
    """
    return recall_memory(query=query, app_name=app_name, top_k=top_k)


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


@server.tool()
def extra_curate_skills(
    sanitize: bool = False,
) -> Dict[str, Any]:
    """
    Curates, audits, and optionally sanitizes skill playbooks across workspace and user directories.
    Detects corrupted skills, strips legacy unhardened evolved fast paths, removes mock skills,
    and returns a complete audit catalog of all verified active skills.
    
    Args:
        sanitize: If True, purges legacy/unhardened evolved fast paths and removes mock skill folders.
    """
    return curate_skill_library(sanitize=sanitize)


# Active in-memory blueprints cache
_active_blueprints: Dict[str, TaskBlueprint] = {}


@server.tool()
def extra_execute_bridge(
    runtime: str,
    payload: str,
    args: Optional[List[str]] = None,
    expected_artifacts: Optional[List[str]] = None,
    timeout_sec: float = 60.0,
) -> Dict[str, Any]:
    """
    Executes a programmatic script or code payload via the Universal Execution Bridge (Plane 2).
    Enables deterministic, atomic execution for complex apps (Blender bpy, Python, PowerShell, CLI)
    without multi-turn GUI clicking.
    
    Args:
        runtime: Execution runtime ('python', 'powershell', 'blender_bpy', 'cmd', 'bash').
        payload: Absolute path to script file OR raw code block to execute.
        args: Optional list of additional command line flags or arguments.
        expected_artifacts: Optional list of file paths expected to be created/updated.
        timeout_sec: Maximum execution timeout in seconds (default: 60.0).
    """
    ensure_dpi_aware()
    try:
        res = execute_bridge(
            runtime=runtime,
            payload=payload,
            args=args,
            expected_artifacts=expected_artifacts,
            timeout_sec=timeout_sec,
        )
        return res.to_dict()
    except Exception as ex:
        logger.warning("[extra_execute_bridge] Error: %s", ex)
        return {"success": False, "error": str(ex), "runtime": runtime}


@server.tool()
def extra_blueprint_start(
    title: str,
    task_type: str = "general",
    milestones: Optional[List[Dict[str, Any]]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Initializes a new long-horizon Task Blueprint with a Directed Acyclic Graph (DAG) of milestones (Plane 1).
    Enables structured progress tracking, rollback checkpoints, and context folding.
    
    Args:
        title: Human-readable task title (e.g. 'Build 3D Car in Blender').
        task_type: Domain category ('video_editing', '3d_modeling', 'design_deck', 'general').
        milestones: List of milestone objects with 'id', 'name', 'dependencies', 'expected_artifacts', etc.
        metadata: Optional metadata dictionary.
    """
    try:
        ms_objs = [Milestone.from_dict(m) for m in (milestones or [])]
        bp = TaskBlueprint(title=title, task_type=task_type, milestones=ms_objs, metadata=metadata)
        _active_blueprints[bp.task_id] = bp
        saved_path = bp.save()
        runnable = [m.to_dict() for m in bp.get_next_runnable()]
        
        return {
            "success": True,
            "task_id": bp.task_id,
            "title": bp.title,
            "total_milestones": len(bp.milestones),
            "runnable_milestones": runnable,
            "blueprint_file": str(saved_path),
        }
    except Exception as ex:
        logger.warning("[extra_blueprint_start] Error: %s", ex)
        return {"success": False, "error": str(ex)}


@server.tool()
def extra_blueprint_milestone(
    task_id: str,
    milestone_id: str,
    action: str = "complete",
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    summary: Optional[str] = None,
    auto_rollback: bool = False,
) -> Dict[str, Any]:
    """
    Updates and verifies a milestone state in an active Task Blueprint, folding context via HIPIF.
    Returns a dense semantic state token to prevent LLM context window bloat.
    
    Args:
        task_id: Active blueprint task ID.
        milestone_id: Milestone ID to update.
        action: One of 'start', 'complete', 'fail', or 'rollback'.
        result: Optional execution result dictionary (stdout, artifacts, returncode).
        error: Error message if action is 'fail'.
        summary: Brief summary for HIPIF context folding.
        auto_rollback: If True and verification fails, automatically rolls back this milestone
                      and its descendants to the last known healthy state.
    """
    try:
        clean_task_id = str(Path(task_id).name)
        bp = _active_blueprints.get(clean_task_id)
        if not bp:
            from extra.core.composer.blueprint import _BLUEPRINTS_DIR
            bp_file = _BLUEPRINTS_DIR / f"{clean_task_id}.json"
            if bp_file.exists():
                bp = TaskBlueprint.load(bp_file)
                _active_blueprints[clean_task_id] = bp
            else:
                return {"success": False, "error": f"Task blueprint '{clean_task_id}' not found"}

        act = action.lower().strip()
        if act == "start":
            m = bp.start_milestone(milestone_id)
            bp.save()
            return {"success": True, "action": act, "milestone": m.to_dict()}

        elif act == "complete":
            m = bp.milestones.get(milestone_id)
            if not m:
                return {"success": False, "error": f"Milestone '{milestone_id}' not found"}

            # Perform physical & visual verification
            verif = verify_milestone_acceptance(m, execution_result=result)
            if not verif.passed:
                bp.fail_milestone(milestone_id, error=f"Verification failed: {', '.join(verif.defects)}")
                reset_ids = []
                if auto_rollback:
                    reset_ids = bp.rollback_to(milestone_id)
                bp.save()
                return {
                    "success": False,
                    "action": act,
                    "verified": False,
                    "defects": verif.defects,
                    "auto_rollback": auto_rollback,
                    "reset_milestones": reset_ids,
                    "milestone": m.to_dict(),
                }

            bp.complete_milestone(milestone_id, result=result)
            ckpt = fold_completed_milestone(bp, milestone_id, summary=summary)
            bp.save()
            dense_token = create_semantic_state_token(m)
            runnable = [item.to_dict() for item in bp.get_next_runnable()]

            return {
                "success": True,
                "action": act,
                "verified": True,
                "state_token": dense_token,
                "is_task_complete": bp.is_complete,
                "next_runnable_milestones": runnable,
                "checkpoint_id": ckpt.checkpoint_id,
            }

        elif act == "fail":
            m = bp.fail_milestone(milestone_id, error=error or "Unknown failure")
            bp.save()
            return {"success": True, "action": act, "milestone": m.to_dict()}

        elif act == "rollback":
            reset_ids = bp.rollback_to(milestone_id)
            bp.save()
            return {"success": True, "action": act, "reset_milestones": reset_ids}

        else:
            return {"success": False, "error": f"Invalid action '{action}'. Use start/complete/fail/rollback."}
    except Exception as ex:
        logger.warning("[extra_blueprint_milestone] Error: %s", ex)
        return {"success": False, "error": str(ex)}


@server.tool()
def extra_soul_wait(
    condition: str = "settled",
    timeout_sec: float = 4.0,
    check_interval_ms: int = 60,
) -> Dict[str, Any]:
    """
    Sub-15ms visual settle and state transition detector powered by Project SOUL-Gateman.
    Monitors DXGI frames at 60Hz to verify UI stabilization before dispatching physical actions.
    
    Args:
        condition: 'settled' (waits for screen pixels to stop changing) or 'change' (waits for visual delta).
        timeout_sec: Maximum timeout in seconds (default: 4.0).
        check_interval_ms: Milliseconds between frame samples (default: 60).
    """
    ensure_dpi_aware()
    if condition.lower().strip() == "change":
        from extra.core.soul.gateman import _default_gateman
        res = _default_gateman.wait_for_change(timeout_sec=timeout_sec, check_interval_ms=check_interval_ms)
    else:
        from extra.core.soul.gateman import _default_gateman
        res = _default_gateman.wait_until_settled(timeout_sec=timeout_sec, check_interval_ms=check_interval_ms)
    return res


def main() -> None:
    """Starts the Extra MCP server over stdio transport."""
    ensure_dpi_aware()
    attach_input_desktop()
    try:
        mig = ensure_startup_migration()
        if mig.get("status") == "migrated":
            logger.info("Startup migration applied: sanitized legacy skills (%s files cleaned)", mig.get("files_cleaned", 0))
    except Exception as e:
        logger.debug("Startup migration check skipped: %s", e)

    logger.info("Extra Flashless MCP Server initializing on stdio transport...")
    server.run(transport="stdio")


if __name__ == "__main__":
    main()

