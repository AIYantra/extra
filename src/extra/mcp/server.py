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

try:
    from mcp.server.fastmcp import FastMCP as MCPServer
except ImportError:
    try:
        from mcp.server.mcpserver import MCPServer
    except ImportError:
        from mcp.server import Server as MCPServer

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
from extra.core.distiller import distill_screen
from extra.core.subtask import run_subtask
from extra.core.mode import (
    ExecutionMode,
    ModeConfig,
    MODE_PROFILES,
    get_execution_mode,
    get_mode_config,
    set_execution_mode,
)
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
from extra.fastpath.cli_harness import execute_harness
from extra.fastpath.cli_hub import get_cli_hub
from extra.core.evolution.harness_generator import get_harness_synthesizer
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
_platform_tag = "macOS" if sys.platform == "darwin" else ("Linux" if sys.platform.startswith("linux") else "Windows")
server = MCPServer(f"Extra-{_platform_tag}-Flashless")

# Singletons for supervisor plane
_uia_plane = UIAutomationPlane()
_som_annotator = SetOfMarkAnnotator()
_stall_breaker = StallBreaker(max_strikes=2)

# Active in-memory TaskBlueprints and turn budgeting
_active_blueprints: Dict[str, TaskBlueprint] = {}


def _track_active_blueprint_turn() -> Optional[str]:
    """
    If there is an active TaskBlueprint with an active milestone, automatically records
    one turn and returns a warning string if the milestone turn budget is exceeded.
    """
    for bp in list(_active_blueprints.values()):
        if bp.active_milestone_id and not bp.is_complete:
            try:
                res = bp.record_milestone_turn(bp.active_milestone_id, turns=1)
                bp.save()
                if res.get("budget_exceeded"):
                    return res.get("warning")
            except Exception as e:
                logger.debug("[BlueprintTurnTracker] Failed to record turn: %s", e)
    return None



@server.tool()
def extra_screenshot(
    monitor_index: int = 0,
    crop_box: Optional[List[int]] = None,
    annotate_ui: bool = False,
    save_to_file: bool = True,
    file_path: Optional[str] = None,
    include_base64: bool = False,
    auto_distill: bool = True,
) -> Dict[str, Any]:
    """
    Captures an ultra-fast screen frame (< 30ms) from the specified monitor.
    Optionally overlays Set-of-Mark (SoM) numbered badges on all detected interactive UI elements.
    Saves screenshot to disk to avoid large Base64 payload truncation in AI clients (Fixes #4, credit: @harshbuttru3).
    Includes auto-distilled compact UI layout directly in payload to eliminate view_file roundtrips.
    
    ZERO-HOP PERCEPTION MANDATE:
    Returns 'distilled_ui' directly in the response payload.
    NEVER call view_file on the saved screenshot PNG file. Reading distilled_ui directly
    saves 10-15 seconds per turn and prevents prompt token exhaustion.
    
    Args:
        monitor_index: 0-based display index (0 = primary monitor).
        crop_box: Optional [left, top, right, bottom] physical pixel coordinates to crop.
        annotate_ui: If True, draws numbered badges [1], [2] on all interactive buttons and returns their positions.
        save_to_file: If True (default), writes image to disk in the safe scratch workspace (~/.extra/workspace/screenshots/).
        file_path: Optional custom file path to save screenshot.
        include_base64: If True, includes full base64 string in response (default False to prevent LLM payload truncation).
        auto_distill: If True (default), includes token-optimized compact UI distillation (elements, texts, buttons, inputs, coordinates) directly in the response to eliminate view_file roundtrips.
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
        "perception_notice": (
            "Zero-Hop Protocol Active: distilled_ui is included in this response. "
            "STRICT PROHIBITION: DO NOT call view_file on the saved screenshot PNG file."
        ),
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

    # Auto-Distillation: Zero-Hop Perception (< 10ms)
    # Injects compact UI layout directly in tool response to eliminate view_file roundtrips
    if auto_distill:
        try:
            d_res = distill_screen(format="compact", max_elements=30)
            result["distilled_ui"] = d_res.content
            result["distilled_element_count"] = d_res.element_count
            result["distilled_interactive_count"] = d_res.interactive_count
        except Exception as ex:
            logger.debug("Auto-distill in extra_screenshot failed: %s", ex)

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

    record_action_step("extra_screenshot", {"annotate_ui": annotate_ui, "save_to_file": save_to_file, "auto_distill": auto_distill}, result.get("duration_ms", 0.0))
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
    canvas_relative: bool = False,
    monitor_index: int = 0,
    human_like: bool = True,
    speed: str = "normal",
    auto_distill: bool = True,
    force: bool = False,
) -> Dict[str, Any]:
    """
    Executes a hardware-level mouse click with PerMonitorV2 DPI compensation and closed-loop stall checking.
    Supports semantic visual grounding via SOUL-Eyes ('target') for zero-coordinate autonomous clicking.
    Supports human-like curved approach with natural reaction delay (enabled by default for live computer use).
    Returns auto-distilled compact UI layout after settle to eliminate intermediate screenshot roundtrips.
    
    Args:
        x: Optional X-coordinate (physical pixel or normalized 0-1000).
        y: Optional Y-coordinate (physical pixel or normalized 0-1000).
        target: Optional semantic target name (e.g. 'Brush tool', 'Yellow color', 'File menu') for SOUL-Eyes visual grounding.
        button: Mouse button ('left', 'right', 'middle'). Default: 'left'.
        clicks: Click count (1 = single click, 2 = double click). Default: 1.
        normalized: If True, treats x, y as [0, 1000] scale and converts to physical pixels.
        canvas_relative: If True, treats coordinates as relative to the active window's detected canvas/work surface.
        monitor_index: Monitor index if normalized coordinates are used.
        human_like: If True, approaches target via human Bézier trajectory with physiological pre-click reaction delay (default: True).
        speed: Speed preset if human_like is True ('fast', 'normal', 'slow').
        auto_distill: If True (default), returns updated compact UI state after click settle to eliminate intermediate screenshot roundtrips.
    """
    ensure_dpi_aware()
    attach_input_desktop()
    _stall_breaker.check_safety_abort()

    is_consequential_click = bool(target and any(kw in target.lower() for kw in ("send", "submit", "post", "confirm", "checkout", "place order")))
    if is_consequential_click:
        guard_advisory = _stall_breaker.check_duplicate_action_guard(
            action_name="click_submit",
            target_key=target.strip(),
            force=force,
        )
        if guard_advisory:
            return {
                "success": False,
                "action_dispatched": False,
                "action_executed": False,
                "perception_succeeded": False,
                "verification_status": "blocked",
                "error": guard_advisory,
                "guard_triggered": "duplicate_action_guard",
            }

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
        if canvas_relative:
            try:
                from extra.core.soul.vision_parser import detect_canvas_viewport
                cv = detect_canvas_viewport()
                if cv:
                    if normalized:
                        phys_x = cv.bounding_box[0] + int((int(x) / 1000.0) * cv.width)
                        phys_y = cv.bounding_box[1] + int((int(y) / 1000.0) * cv.height)
                    else:
                        phys_x = cv.bounding_box[0] + int(x)
                        phys_y = cv.bounding_box[1] + int(y)
                else:
                    phys_x, phys_y = (denormalize_coordinates(int(x), int(y), monitor_index=monitor_index) if normalized else (int(x), int(y)))
            except Exception:
                phys_x, phys_y = (denormalize_coordinates(int(x), int(y), monitor_index=monitor_index) if normalized else (int(x), int(y)))
        elif normalized:
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

    win_title = after_fg.title if after_fg else (before_fg.title if before_fg else None)
    outcome = _stall_breaker.evaluate_action(
        roi_before,
        roi_after,
        before_hwnd=before_hwnd,
        after_hwnd=after_hwnd,
        action_name="click",
        before_full_image=cap_before.image,
        after_full_image=cap_after.image,
        click_coords=(phys_x, phys_y),
        window_title=win_title,
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
        "action_dispatched": True,
        "action_executed": True,
        "verification_status": "verified" if outcome.status == StallStatus.NORMAL else "unconfirmed",
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
    if outcome.recommended_action:
        ret["recommended_action"] = outcome.recommended_action
    if after_fg:
        ret["active_window_title"] = after_fg.title
        ret["active_window_hwnd"] = after_fg.hwnd
    if outcome.status == StallStatus.STALLED:
        ret["error"] = outcome.message
    elif outcome.status == StallStatus.WARNING:
        ret["warning"] = outcome.message
    if grounding_meta:
        ret["grounding"] = grounding_meta

    if is_consequential_click:
        _stall_breaker.record_consequential_action(
            action_name="click_submit",
            target_key=target.strip(),
            verification_status=ret.get("verification_status", "unconfirmed"),
        )

    # Auto-Distillation: Zero-Hop Perception
    if auto_distill:
        try:
            d_res = distill_screen(format="compact", max_elements=25)
            ret["distilled_ui"] = d_res.content
            ret["perception_succeeded"] = True
        except Exception as ex:
            logger.debug("Auto-distill in extra_click failed: %s", ex)
            ret["perception_succeeded"] = False

    b_warn = _track_active_blueprint_turn()
    if b_warn:
        ret["budget_warning"] = b_warn

    return ret



@server.tool()
def extra_type(
    text: str,
    press_enter: bool = False,
    use_clipboard: bool = False,
    auto_distill: bool = False,
    html: Optional[str] = None,
    force: bool = False,
) -> Dict[str, Any]:
    """
    Injects Unicode text with sub-millisecond latency into the active focused window.
    Uses Win32 KEYEVENTF_UNICODE (VK_PACKET) with 100% fidelity across all scripts and emojis.
    
    FAST-PATH: In Calculator (calc.exe), directly type the entire mathematical formula followed by '='
    (e.g., text='45/5*2+10-11=') instead of clicking buttons individually.
    
    RICH CONTENT FAST-PATH: Pass `html="<table>...</table>"` to paste native tables, styled headings,
    or formatted links directly into Google Docs, Word, LibreOffice, or web editors without canvas clicking.

    Args:
        text: Text string to type (full Unicode and emoji support).
        press_enter: If True, sends an Enter key immediately following the text.
        use_clipboard: If True, injects via atomic clipboard paste (defaults to False for universal input compatibility).
        auto_distill: If True (or if press_enter is True), returns updated compact UI state after typing settles.
        html: Optional rich HTML fragment (e.g. '<table>...</table>') to inject via Windows CF_HTML format.
    """
    ensure_dpi_aware()
    attach_input_desktop()
    _stall_breaker.check_safety_abort()

    if press_enter:
        guard_advisory = _stall_breaker.check_duplicate_action_guard(
            action_name="type_enter",
            target_key=text.strip(),
            force=force,
        )
        if guard_advisory:
            return {
                "success": False,
                "action_dispatched": False,
                "action_executed": False,
                "perception_succeeded": False,
                "verification_status": "blocked",
                "error": guard_advisory,
                "guard_triggered": "duplicate_action_guard",
            }

    t0 = time.perf_counter()
    # Universal Lossless Input Routing:
    # Short formulas / query terms (< 80 chars, single-line) use instant VK_PACKET keystrokes.
    # Long documents, code blocks, or multi-line strings automatically route via atomic clipboard paste
    # to eliminate timer quantization delays and prevent dropped characters in modern WinUI/Electron apps.
    should_use_clipboard = use_clipboard or html is not None or (len(text) > 80 or "\n" in text)
    if should_use_clipboard:
        atomic_clipboard_paste(text, html=html)
        if press_enter:
            send_hotkey(["enter"])
        method = "clipboard_html" if html is not None else "clipboard"
    else:
        # Universal instant keystroke injection via Win32 VK_PACKET / macOS CGEvent (< 2ms)
        instant_type(text, press_enter=press_enter)
        method = "vk_packet"
    duration_ms = (time.perf_counter() - t0) * 1000.0
    _stall_breaker.reset()

    ret = {
        "success": True,
        "action_dispatched": True,
        "action_executed": True,
        "length": len(text),
        "duration_ms": round(duration_ms, 2),
        "method": method,
    }

    # Auto-Distillation on enter or explicit request
    if auto_distill or press_enter:
        if press_enter:
            # Dynamic visual settle: wait for animations/UI commits after enter (e.g. chat send, form submit)
            try:
                from extra.core.soul.gateman import wait_until_settled
                wait_until_settled(timeout_sec=0.4, settle_frames=2, check_interval_ms=50)
            except Exception:
                time.sleep(0.18)
        try:
            d_res = distill_screen(format="compact", max_elements=25)
            ret["distilled_ui"] = d_res.content
            ret["perception_succeeded"] = True
            fg = get_foreground_window()
            if fg:
                ret["active_window_title"] = fg.title
        except Exception as ex:
            logger.debug("Auto-distill in extra_type failed: %s", ex)
            ret["perception_succeeded"] = False

    ret["verification_status"] = "unconfirmed" if press_enter else "skipped"
    if press_enter:
        _stall_breaker.record_consequential_action(
            action_name="type_enter",
            target_key=text.strip(),
            verification_status=ret.get("verification_status", "unconfirmed"),
        )
    record_action_step("extra_type", {"text": text[:80], "press_enter": press_enter, "use_clipboard": use_clipboard, "auto_distill": auto_distill}, duration_ms)
    b_warn = _track_active_blueprint_turn()
    if b_warn:
        ret["budget_warning"] = b_warn
    return ret


@server.tool()
def extra_hotkey(keys: List[str], force: bool = False) -> Dict[str, Any]:
    """
    Dispatches a synchronized keyboard shortcut sequence.
    Example: ['ctrl', 'c'], ['win', 'r'], ['ctrl', 'shift', 'esc'], ['alt', 'tab'].
    
    Args:
        keys: List of key names to press together in order and release in reverse.
    """
    ensure_dpi_aware()
    attach_input_desktop()
    _stall_breaker.check_safety_abort()

    is_enter = any(str(k).lower() in ("enter", "return") for k in keys)
    key_combo = "+".join(str(k).lower() for k in keys)
    if is_enter:
        guard_advisory = _stall_breaker.check_duplicate_action_guard(
            action_name="hotkey_enter",
            target_key=key_combo,
            force=force,
        )
        if guard_advisory:
            return {
                "success": False,
                "action_dispatched": False,
                "action_executed": False,
                "perception_succeeded": False,
                "verification_status": "blocked",
                "error": guard_advisory,
                "guard_triggered": "duplicate_action_guard",
            }

    t0 = time.perf_counter()
    send_hotkey(keys)
    duration_ms = (time.perf_counter() - t0) * 1000.0
    _stall_breaker.reset()

    record_action_step("extra_hotkey", {"keys": keys}, duration_ms)
    ret = {
        "success": True,
        "action_dispatched": True,
        "action_executed": True,
        "verification_status": "unconfirmed" if any(str(k).lower() in ("enter", "return") for k in keys) else "skipped",
        "keys": keys,
        "duration_ms": round(duration_ms, 2),
    }
    if is_enter:
        _stall_breaker.record_consequential_action(
            action_name="hotkey_enter",
            target_key=key_combo,
            verification_status=ret.get("verification_status", "unconfirmed"),
        )
    b_warn = _track_active_blueprint_turn()
    if b_warn:
        ret["budget_warning"] = b_warn
    return ret


@server.tool()
def extra_set_mode(
    mode: str,
) -> Dict[str, Any]:
    """
    Sets the Extra automation speed mode dynamically.
    Modes:
      - 'turbo' (low): Sub-50ms dispatch, 0ms settle, 0-hop execution, memory query disabled. Ideal for sub-30s speed runs.
      - 'balanced' (medium): Default balanced mode (~15ms settle, balanced UI inspection).
      - 'smart' (high): Maximum grounding with Project SOUL, visual critics, full memory recall.
    """
    cfg = set_execution_mode(mode)
    return {
        "success": True,
        "mode": cfg.name.value,
        "config": {
            "auto_settle": cfg.auto_settle,
            "max_inspect_elements": cfg.max_inspect_elements,
            "compact_ui": cfg.compact_ui,
            "sleep_scale": cfg.sleep_scale,
            "max_sleep_ms": cfg.max_sleep_ms,
            "proactive_memory_recall": cfg.proactive_memory_recall,
        },
        "description": f"Extra execution mode set to {cfg.name.value.upper()}.",
    }


@server.tool()
def extra_inspect_ui(
    window_title: Optional[str] = None,
    hwnd: Optional[int] = None,
    interactive_only: bool = True,
    max_elements: int = 50,
    mode: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Queries Microsoft UI Automation Core v3 to return accessible controls with exact bounding boxes.
    Allows zero-token semantic targeting without vision hallucinations.
    Formatted to prevent LLM context bloat and tool output truncation.

    NOTE: For Calculator calculations, do NOT use this to inspect individual digit buttons;
    use extra_type to inject the entire formula directly.

    Args:
        window_title: Optional substring of window title to inspect (e.g. 'Calculator', 'Chrome').
        hwnd: Optional explicit window handle.
        interactive_only: If True, returns only interactive buttons, edits, links, tabs.
        max_elements: Maximum elements to return (default 50).
        mode: Optional runtime speed mode ('turbo', 'balanced', 'smart').
    """
    ensure_dpi_aware()
    attach_input_desktop()

    mode_cfg = get_mode_config(mode)
    effective_max = min(max_elements, mode_cfg.max_inspect_elements) if mode_cfg.compact_ui else max_elements

    target_hwnd = hwnd
    win = None
    if not target_hwnd and window_title:
        win = find_window_by_title(window_title)
        if win:
            target_hwnd = win.hwnd

    t0 = time.perf_counter()
    elements = _uia_plane.inspect_window(
        hwnd=target_hwnd, interactive_only=interactive_only, max_elements=effective_max
    )
    duration_ms = (time.perf_counter() - t0) * 1000.0

    raw_dicts = [el.to_dict() for el in elements[:effective_max]]
    formatted_elements = []
    summary_lines = [f"[UI Controls - {len(raw_dicts)} items]"]
    for el in raw_dicts:
        el_id = el.get("element_id")
        el_name = el.get("name", "")
        el_type = el.get("control_type", "")
        center = el.get("center", [])
        summary_lines.append(f"• ID {el_id} | {el_type} '{el_name}' @ center {center}")

        if mode_cfg.strip_heavy_attributes:
            formatted_elements.append({
                "element_id": el_id,
                "name": el_name,
                "control_type": el_type,
                "center": center,
                "bounding_box": el.get("bounding_box", []),
                "is_keyboard_focusable": el.get("is_keyboard_focusable", True),
                "is_enabled": el.get("is_enabled", True),
            })
        else:
            formatted_elements.append(el)

    return {
        "success": True,
        "count": len(formatted_elements),
        "duration_ms": round(duration_ms, 2),
        "mode": mode_cfg.name.value,
        "ui_summary": "\n".join(summary_lines),
        "elements": formatted_elements,
    }


@server.tool()
def extra_translate_screen(
    window_title: Optional[str] = None,
    hwnd: Optional[int] = None,
    format: str = "markdown",
    include_coordinates: bool = True,
    interactive_only: bool = False,
    max_elements: int = 50,
    force_vision: bool = False,
) -> Dict[str, Any]:
    """
    Distills the active or targeted window into an ultra-dense, token-optimized semantic representation.
    Translates visual buttons, inputs, labels, and displays into structured Markdown or compact text.
    Saves 90%+ prompt tokens and eliminates latency overhead compared to sending raw screenshots to the LLM.

    Args:
        window_title: Optional substring of window title to inspect (e.g. 'Calculator', 'Chrome', 'Notepad').
        hwnd: Optional explicit window handle.
        format: Representation format: 'markdown' (default), 'compact' (ultra-dense single block), or 'json'.
        include_coordinates: If True, provides physical [x, y] coordinates for direct 1-turn clicking.
        interactive_only: If True, only returns clickable actions and inputs (omits passive text displays).
        max_elements: Maximum controls to include in output (default: 50).
        force_vision: If True, forces edge computer vision parsing even if native accessibility is present.
    """
    ensure_dpi_aware()
    attach_input_desktop()

    result = distill_screen(
        hwnd=hwnd,
        window_title=window_title,
        format=format,
        include_coordinates=include_coordinates,
        max_elements=max_elements,
        interactive_only=interactive_only,
        force_vision=force_vision,
    )
    return result.to_dict()


@server.tool()
def extra_subtask_run(
    intent: Optional[str] = None,
    actions: Optional[List[Dict[str, Any]]] = None,
    expected_elements: Optional[List[str]] = None,
    unwanted_elements: Optional[List[str]] = None,
    timeout_sec: float = 8.0,
) -> Dict[str, Any]:
    """
    Executes a multi-step desktop micro-routine autonomously in a closed loop.
    Enables System 1 execution (e.g., launch app -> type formula -> copy result) in 1 turn,
    saving thousands of prompt tokens and multiple seconds of turn-latency.
    Integrates SOUL-Critic on-device milestone evaluation to reject defective states locally.

    Args:
        intent: High-level micro-goal description (e.g. 'calculate 450*12= in calc', 'dismiss modal', 'open notepad and type Hello').
        actions: Optional explicit batch action list if already planned by the host agent.
        expected_elements: Optional list of elements that MUST be visible after execution (verified by SOUL-Critic).
        unwanted_elements: Optional list of elements that MUST NOT be visible (e.g. ['Error', 'Crash']).
        timeout_sec: Maximum seconds before safety abort (default: 8.0s).
    """
    ensure_dpi_aware()
    attach_input_desktop()
    _stall_breaker.check_safety_abort()

    res = run_subtask(
        intent=intent,
        actions=actions,
        expected_elements=expected_elements,
        unwanted_elements=unwanted_elements,
        timeout_sec=timeout_sec,
    )
    _stall_breaker.reset()

    record_action_step("extra_subtask_run", {"intent": intent, "steps": res.steps_executed}, res.duration_ms)
    res_dict = res.to_dict()
    b_warn = _track_active_blueprint_turn()
    if b_warn:
        res_dict["budget_warning"] = b_warn
    return res_dict


@server.tool()
def extra_click_element(
    element_id: Optional[int] = None,
    query: Optional[str] = None,
    force: bool = False,
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

    is_consequential = bool(query and any(kw in query.lower() for kw in ("send", "submit", "post", "confirm", "checkout", "place order")))
    if is_consequential:
        guard_advisory = _stall_breaker.check_duplicate_action_guard(
            action_name="click_submit",
            target_key=query.strip(),
            force=force,
        )
        if guard_advisory:
            return {
                "success": False,
                "action_dispatched": False,
                "action_executed": False,
                "perception_succeeded": False,
                "verification_status": "blocked",
                "error": guard_advisory,
                "guard_triggered": "duplicate_action_guard",
            }

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

    result: Dict[str, Any] = {
        "success": success,
        "action_dispatched": success,
        "action_executed": success,
        "verification_status": "unconfirmed" if success else "failed",
        "element_id": element_id,
        "duration_ms": round(duration_ms, 2),
    }
    if not success and query:
        result["error"] = f"Element query '{query}' could not be invoked via UIA or visually grounded on screen."
    if grounding_meta:
        result["soul_eyes"] = grounding_meta
    if is_consequential and success:
        _stall_breaker.record_consequential_action(
            action_name="click_submit",
            target_key=query.strip(),
            verification_status=result.get("verification_status", "unconfirmed"),
        )
    return result


@server.tool()
def extra_launch(
    app_name: str,
    args: Optional[List[str]] = None,
    profile: Optional[str] = None,
    maximize: bool = False,
) -> Dict[str, Any]:
    """
    Deterministically launches standard Windows applications and tools.
    Supported shortcuts: 'calc', 'notepad', 'clock', 'timer', 'alarms', 'mail', 'calendar', 'explorer', 'settings', 'cmd', 'terminal', 'edge', 'chrome', 'brave', 'paint'.
    
    Args:
        app_name: Tool name or executable (e.g. 'calc', 'notepad', 'explorer', 'settings', 'chrome', 'edge').
        args: Optional list of command-line arguments.
        profile: Optional browser profile name (e.g. 'Default', 'Profile 1', 'Profile 3').
        maximize: If True, arranges and maximizes the window instantly via Win32 SW_MAXIMIZE, bypassing Windows 11 Snap Assist.
    """
    ensure_dpi_aware()
    attach_input_desktop()

    res = launch_app(app_name=app_name, args=args, wait_for_window=True, profile=profile, maximize=maximize)
    if res.success:
        _stall_breaker.reset()
    record_action_app(app_name=app_name, exe_path=getattr(res, "target_executed", None))
    record_action_step("extra_launch", {"app_name": app_name, "args": args, "profile": profile, "maximize": maximize})
    res_dict = res.to_dict()

    # Proactive Memory Recall: surface known app quirks and playbooks from KùzuDB
    try:
        from extra.core.memory.recall import recall_memory
        mem = recall_memory(query=app_name, app_name=app_name, top_k=2)
        if mem.get("known_app_quirks"):
            res_dict["known_app_quirks"] = mem["known_app_quirks"]
            res_dict["memory_guidance"] = (
                f"PROACTIVE MEMORY GUIDANCE for '{app_name}': Verified workarounds found in KùzuDB memory. "
                "Use these proven fast paths to avoid known application stalls."
            )
    except Exception as e:
        logger.debug("Proactive memory recall in extra_launch failed: %s", e)

    return res_dict


@server.tool()
def extra_browser(
    action: str,
    url: Optional[str] = None,
    selector: Optional[str] = None,
    value: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executes web automation via Microsoft Edge / Playwright without vision overhead.
    Supports autonomous Web-to-API network sniffing and fast-path client synthesis.
    IMPORTANT: Operates within Extra's dedicated background Playwright browser instance.
    Does NOT attach to or control already-running browser windows on the user's desktop.
    For automating active user desktop browsers (Chrome, Edge), pilot them live via
    extra_focus_window, extra_click, extra_type, extra_hotkey, and extra_batch_actions.
    
    Actions:
        - 'navigate': Opens url.
        - 'content': Extracts clean semantic markdown text.
        - 'click': Clicks CSS/XPath selector.
        - 'fill': Types text into selector.
        - 'eval': Evaluates JavaScript string in value.
        - 'screenshot': Returns page base64 screenshot.
        - 'settle': Waits for DOM stability and network quiescence in < 10ms-30ms.
        - 'start_sniffing': Starts intercepting and recording API network traffic on active page.
        - 'stop_sniffing': Stops network interception and returns captured mutations.
        - 'synthesize_api': Generates standalone Python API fast-path client from sniffed mutations (selector=service_name, value=action_name).
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
    canvas_relative: bool = False,
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
        canvas_relative: If True, treats coordinates as relative to the active window's detected canvas/work surface.
        monitor_index: Target monitor.
    """
    ensure_dpi_aware()
    attach_input_desktop()
    _stall_breaker.check_safety_abort()

    if canvas_relative:
        try:
            from extra.core.soul.vision_parser import detect_canvas_viewport
            cv = detect_canvas_viewport()
            if cv:
                if normalized:
                    sx = cv.bounding_box[0] + int((start_x / 1000.0) * cv.width)
                    sy = cv.bounding_box[1] + int((start_y / 1000.0) * cv.height)
                    ex = cv.bounding_box[0] + int((end_x / 1000.0) * cv.width)
                    ey = cv.bounding_box[1] + int((end_y / 1000.0) * cv.height)
                else:
                    sx = cv.bounding_box[0] + int(start_x)
                    sy = cv.bounding_box[1] + int(start_y)
                    ex = cv.bounding_box[0] + int(end_x)
                    ey = cv.bounding_box[1] + int(end_y)
            else:
                sx, sy = (denormalize_coordinates(start_x, start_y, monitor_index) if normalized else (start_x, start_y))
                ex, ey = (denormalize_coordinates(end_x, end_y, monitor_index) if normalized else (end_x, end_y))
        except Exception:
            sx, sy = (denormalize_coordinates(start_x, start_y, monitor_index) if normalized else (start_x, start_y))
            ex, ey = (denormalize_coordinates(end_x, end_y, monitor_index) if normalized else (end_x, end_y))
    elif normalized:
        sx, sy = denormalize_coordinates(start_x, start_y, monitor_index)
        ex, ey = denormalize_coordinates(end_x, end_y, monitor_index)
    else:
        sx, sy = start_x, start_y
        ex, ey = end_x, end_y

    t0 = time.perf_counter()
    mouse_drag(sx, sy, ex, ey, button=button, duration=duration, human_like=human_like, monitor_index=monitor_index)
    duration_ms = (time.perf_counter() - t0) * 1000.0

    record_action_step("extra_drag", {"start": [sx, sy], "end": [ex, ey], "human_like": human_like}, duration_ms)
    return {
        "success": True,
        "action_dispatched": True,
        "action_executed": True,
        "verification_status": "unconfirmed",
        "start": [sx, sy],
        "end": [ex, ey],
        "duration_ms": round(duration_ms, 2),
    }


@server.tool()
def extra_stroke(
    points: Optional[List[List[int]]] = None,
    points_file: Optional[str] = None,
    button: str = "left",
    duration: float = 1.0,
    smooth: bool = True,
    normalized: bool = False,
    canvas_relative: bool = False,
    monitor_index: int = 0,
) -> Dict[str, Any]:
    """
    Executes a continuous fluid brush stroke across multiple waypoints while holding down the mouse button.
    Essential for canvas drawing, sketching, calligraphy, and video timeline scrubbing.
    
    Args:
        points: List of [x, y] coordinates forming the stroke path (e.g. [[100, 200], [150, 250], [300, 400]]).
        points_file: Optional path to a JSON file containing the points list.
        button: Mouse button to hold during stroke ('left' or 'right').
        duration: Total stroke duration in seconds (default: 1.0s).
        smooth: If True, applies centripetal Catmull-Rom spline interpolation for smooth continuous ink.
        normalized: If True, treats coordinates as [0, 1000] scale.
        canvas_relative: If True, treats coordinates as relative to the active window's detected canvas/work surface.
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
    if canvas_relative:
        try:
            from extra.core.soul.vision_parser import detect_canvas_viewport
            cv = detect_canvas_viewport()
            if cv:
                for pt in points:
                    if len(pt) >= 2:
                        if normalized:
                            px = cv.bounding_box[0] + int((int(pt[0]) / 1000.0) * cv.width)
                            py = cv.bounding_box[1] + int((int(pt[1]) / 1000.0) * cv.height)
                        else:
                            px = cv.bounding_box[0] + int(pt[0])
                            py = cv.bounding_box[1] + int(pt[1])
                        phys_points.append((px, py))
            else:
                for pt in points:
                    if len(pt) >= 2:
                        px, py = (denormalize_coordinates(pt[0], pt[1], monitor_index) if normalized else (int(pt[0]), int(pt[1])))
                        phys_points.append((px, py))
        except Exception:
            for pt in points:
                if len(pt) >= 2:
                    px, py = (denormalize_coordinates(pt[0], pt[1], monitor_index) if normalized else (int(pt[0]), int(pt[1])))
                    phys_points.append((px, py))
    else:
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
                y0, y1 = max(0, py - 8), min(h, py + 9)
                x0, x1 = max(0, px - 8), min(w, px + 9)
                if np.any(changed_mask[y0:y1, x0:x1]):
                    path_hits += 1

            # Ink is verified only if:
            # 1. Overall screen pixels changed > 0
            # 2. At least 20% of the sampled trajectory coordinates received ink
            ink_detected = (pixels_changed > 0) and (path_hits >= max(1, int(sampled_count * 0.20)))
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


def estimate_and_optimize_batch_duration(
    actions: List[Dict[str, Any]],
    max_budget_sec: float = 45.0,
    auto_settle: bool = True,
) -> Tuple[List[Dict[str, Any]], float, bool]:
    """
    Estimates total batch execution time and adaptively scales stroke/sleep durations
    to ensure the entire batch executes within max_budget_sec (default 45s),
    preventing MCP client timeouts (180s context deadline exceeded).
    """
    total_est = 0.0
    stroke_indices: List[int] = []

    for idx, act in enumerate(actions):
        if not isinstance(act, dict):
            continue
        atype = str(act.get("action", act.get("type", ""))).lower().strip()
        if atype in ("stroke", "brush", "draw", "mouse_stroke"):
            dur = float(act.get("duration", 0.4))
            pts = act.get("points", [])
            waypoint_overhead = len(pts) * 0.015
            est = max(dur, waypoint_overhead) + 0.04
            total_est += est
            stroke_indices.append(idx)
        elif atype in ("sleep", "delay", "wait"):
            ms = float(act.get("ms", act.get("duration_ms", act.get("seconds", 0) * 1000.0)))
            total_est += ms / 1000.0
        elif atype in ("drag", "mouse_drag"):
            dur = float(act.get("duration", 0.2))
            total_est += dur + 0.05
        elif atype in ("click", "double_click", "hotkey", "type", "focus"):
            total_est += 0.03
            if auto_settle:
                total_est += 0.06
        else:
            total_est += 0.02

    scaled = False
    if total_est > max_budget_sec and stroke_indices:
        non_stroke_est = total_est - sum(
            max(float(actions[i].get("duration", 0.4)), len(actions[i].get("points", [])) * 0.015) + 0.04
            for i in stroke_indices
        )
        available_stroke_budget = max(5.0, max_budget_sec - max(0.0, non_stroke_est))
        current_stroke_sum = sum(float(actions[i].get("duration", 0.4)) for i in stroke_indices)

        if current_stroke_sum > 0:
            scale_ratio = available_stroke_budget / current_stroke_sum
            for i in stroke_indices:
                orig_dur = float(actions[i].get("duration", 0.4))
                new_dur = max(0.06, min(0.25, orig_dur * scale_ratio))
                actions[i]["duration"] = round(new_dur, 3)
            scaled = True
            total_est = max_budget_sec

    return actions, round(total_est, 2), scaled


@server.tool()
def extra_batch_actions(
    actions: Optional[List[Dict[str, Any]]] = None,
    actions_file: Optional[str] = None,
    auto_settle: bool = True,
    strict_ink: bool = False,
    auto_distill: bool = True,
    mode: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executes an atomic list of hardware actions sequentially with sub-millisecond dispatch.
    Eliminates multi-turn network round-trips (reducing seconds to milliseconds) for compound workflows.
    Enhanced with Tier 1 SOUL-Gateman visual settle detection (sub-15ms) to eliminate race conditions.
    Returns auto-distilled compact UI layout and active window metadata upon completion.
    
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
      auto_distill: If True (default), returns updated compact UI state and active window metadata after batch execution settles.
      
    Returns summary of executed actions and total elapsed execution time in milliseconds.
    """
    ensure_dpi_aware()
    attach_input_desktop()
    mode_cfg = get_mode_config(mode)
    effective_settle = auto_settle and mode_cfg.auto_settle

    # Scale down sleep actions in turbo mode
    if actions and mode_cfg.sleep_scale < 1.0:
        for a in actions:
            if isinstance(a, dict) and str(a.get("action", a.get("type", ""))).lower().strip() == "sleep":
                if "ms" in a:
                    a["ms"] = mode_cfg.scale_sleep(a["ms"])
                elif "duration_ms" in a:
                    a["duration_ms"] = mode_cfg.scale_sleep(a["duration_ms"])
                elif "seconds" in a:
                    a["seconds"] = mode_cfg.scale_sleep(a["seconds"] * 1000.0) / 1000.0
                elif "delay" in a:
                    a["delay"] = mode_cfg.scale_sleep(a["delay"] * 1000.0) / 1000.0

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

    # Pre-flight duration optimization to guarantee safe execution well within MCP timeout limits
    actions, est_sec, scaled = estimate_and_optimize_batch_duration(
        actions, max_budget_sec=45.0, auto_settle=auto_settle
    )

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

    res = execute_batch_actions(actions, auto_settle=effective_settle, auto_distill=auto_distill)
    _stall_breaker.reset()
    res["action_dispatched"] = True
    res["mode"] = mode_cfg.name.value
    res["action_executed"] = not res.get("partial_execution", False)
    total_dur = res.get("total_duration_ms", 0)

    if scaled:
        res["adaptive_duration_scaled"] = True
        res["estimated_duration_sec"] = est_sec

    if res.get("partial_execution"):
        executed_n = res.get("executed_count", len(actions))
        res["remaining_actions"] = actions[executed_n:]

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

    # Auto-Distillation Fallback: Injects compact UI layout if not already populated
    if auto_distill and "distilled_ui" not in res:
        try:
            d_res = distill_screen(format="compact", max_elements=30)
            res["distilled_ui"] = d_res.content
            res["perception_succeeded"] = True
            fg_win = get_foreground_window()
            if fg_win:
                res["active_window"] = {
                    "title": fg_win.title,
                    "hwnd": fg_win.hwnd,
                    "process_name": fg_win.process_name,
                }
        except Exception as ex:
            logger.debug("Auto-distill in extra_batch_actions failed: %s", ex)
            res["perception_succeeded"] = False
    elif "distilled_ui" in res:
        res["perception_succeeded"] = True

    if "verification_status" not in res:
        res["verification_status"] = "verified" if res.get("ink_detected", False) or res.get("pixels_changed", 0) > 0 else "unconfirmed"

    b_warn = _track_active_blueprint_turn()
    if b_warn:
        res["budget_warning"] = b_warn

    return res


@server.tool()
def extra_snap_layout(
    layout: str = "side_by_side",
    left_window: Optional[str] = None,
    right_window: Optional[str] = None,
    window: Optional[str] = None,
    center_window: Optional[str] = None,
    windows: Optional[List[str]] = None,
    monitor_index: int = 0,
) -> Dict[str, Any]:
    """
    Arranges windows into a cohesive visual layout in a single programmatic step (sub-15ms).
    Eliminates fragile multi-turn Win+Left / Win+Right hotkey snapping and avoids Windows 11 Snap Assist popups.
    
    Args:
        layout: Layout preset ('side_by_side', 'thirds'/'side_by_side_3', 'maximize'/'fullscreen', 'center', 'top_bottom', 'grid').
        left_window: Window title substring or HWND for the left/top screen half.
        right_window: Window title substring or HWND for the right/bottom screen half.
        window: Window title substring or HWND for single-window layouts ('maximize', 'fullscreen', 'center').
        center_window: Window title substring or HWND for the center/middle screen third in 'thirds' layout.
        windows: Optional ordered list of window titles/HWNDs to arrange (e.g. 3 windows for 'thirds' or 4 for 'grid').
        monitor_index: 0-based monitor index (default 0).
    """
    ensure_dpi_aware()
    attach_input_desktop()
    res = snap_layout(
        layout=layout,
        left_window=left_window,
        right_window=right_window,
        window=window,
        center_window=center_window,
        windows=windows,
        monitor_index=monitor_index,
    )
    _stall_breaker.reset()
    record_action_step(
        "extra_snap_layout",
        {"layout": layout, "left": left_window, "right": right_window, "center": center_window, "windows": windows, "window": window},
    )
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
    mode: Optional[str] = None,
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
    if mode:
        set_execution_mode(mode)
    mode_cfg = get_mode_config()
    ctrl = get_indicator_controller()
    ctrl.task_start(task_name=task_name, monitor_index=monitor_index)
    start_memory_recording(task_name=task_name or "Autonomous Task", goal=task_objective)
    _stall_breaker.reset()
    res: Dict[str, Any] = {"success": True, "task_name": task_name, "status": "active", "mode": mode_cfg.name.value}

    # Proactive Memory Recall: surface known app quirks, workarounds, and evolved playbooks
    if mode_cfg.proactive_memory_recall and (task_name or task_objective):
        try:
            from extra.core.memory.recall import recall_memory
            query_str = f"{task_name or ''} {task_objective or ''}".strip()
            mem = recall_memory(query=query_str, top_k=2)
            if mem.get("known_app_quirks"):
                res["known_app_quirks"] = mem["known_app_quirks"]
                res["memory_guidance"] = (
                    "PROACTIVE MEMORY GUIDANCE: Verified workarounds and evolved playbooks retrieved from KùzuDB memory. "
                    "Follow these proven fast paths to avoid known application stalls."
                )
        except Exception as e:
            logger.debug("Proactive memory recall in extra_task_start failed: %s", e)

    return res


@server.tool()
def extra_task_complete(
    summary: Optional[str] = None,
    success: bool = True,
    play_chime: bool = True,
    auto_screenshot: bool = True,
    claims: Optional[Dict[str, Any]] = None,
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
        claims: Optional ground-truth assertions (expected_tabs, expected_slides, min_words) to independently verify before passing.
    """
    ensure_dpi_aware()
    attach_input_desktop()
    ctrl = get_indicator_controller()

    # Pre-completion ground-truth state guardrail (Anti-Hallucination Invariant)
    if claims and success:
        from extra.core.soul.state_critic import audit_ground_truth_state
        state_audit = audit_ground_truth_state(claims)
        if not state_audit.passed:
            ctrl.task_complete(summary="Task completed with verified defects", success=False, play_chime=False)
            return {
                "success": False,
                "status": "claims_deficit",
                "error": f"TASK COMPLETION REJECTED: Ground-truth audit detected defects: {'; '.join(state_audit.defects)}",
                "ground_truth": state_audit.ground_truth,
                "defects": state_audit.defects,
                "score": state_audit.score,
                "audit_report": state_audit.report_text,
                "audit_hash": state_audit.audit_hash,
            }

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

    # Record to ImpactLedger and attach receipt
    try:
        duration_sec = (time.time() - rec.start_time) if rec and hasattr(rec, "start_time") else 0.5
        from extra.core.metrics.ledger import ImpactLedger
        from extra.core.metrics.telemetry import TelemetryClient

        archetype = ImpactLedger.resolve_archetype(intent=summary or "")
        savings = ImpactLedger.record_event(
            archetype=archetype,
            duration_sec=duration_sec,
            actions_count=len(rec.steps) if rec else 1,
            success=success
        )
        res["impact_receipt"] = ImpactLedger.get_impact_receipt(duration_sec=duration_sec, archetype=archetype)

        # Emit anonymous telemetry event if user opted in
        TelemetryClient.get_instance().emit_event(
            app=archetype,
            archetype=archetype,
            tool_name="extra_task_complete",
            execution_duration_ms=duration_sec * 1000.0,
            actions_count=len(rec.steps) if rec else 1,
            success=success,
            speedup=savings.get("speedup_multiplier", 1.0)
        )
    except Exception as e:
        logger.debug("Failed to record impact receipt: %s", e)

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
        if is_golden and success:
            res["evolution_recommendation"] = (
                "Verified golden-path workflow discovered. You may call 'extra_evolve_skill' to crystallize verified fast paths into permanent skill playbooks."
            )
        elif candidate or (not is_golden and success):
            res["evolution_recommendation"] = (
                "Task encountered friction, recovery steps, or was not a clean golden path. "
                "DO NOT synthesize noisy recovery steps or intermediate actions as a fast path. "
                "If calling 'extra_evolve_skill', provide ONLY discovered anti-stall guardrails in 'friction_points' and 'solutions_found'."
            )

    _stall_breaker.clear_consequential_history()
    return res


@server.tool()
def extra_stats() -> Dict[str, Any]:
    """
    Retrieves cumulative Project Extra impact metrics: total time saved,
    token reduction, and estimated API dollar cost savings vs baseline.
    """
    from extra.core.metrics.ledger import ImpactLedger
    return {
        "lifetime_summary": ImpactLedger.get_summary(),
        "ascii_hud": ImpactLedger.format_ascii_card()
    }


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
    ctrl.task_indicate_status(status=st, message=message or "", play_sound=play_sound)
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


# Active in-memory blueprints cache (declared above)


@server.tool()
def extra_execute_bridge(
    runtime: str,
    payload: str,
    args: Optional[List[str]] = None,
    expected_artifacts: Optional[List[str]] = None,
    timeout_sec: float = 60.0,
    env: Optional[Dict[str, str]] = None,
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
        env: Optional explicit dictionary of environment variables to supply to the execution environment.
    """
    ensure_dpi_aware()
    try:
        res = execute_bridge(
            runtime=runtime,
            payload=payload,
            args=args,
            expected_artifacts=expected_artifacts,
            timeout_sec=timeout_sec,
            env=env,
        )
        return res.to_dict()
    except Exception as ex:
        logger.warning("[extra_execute_bridge] Error: %s", ex)
        return {"success": False, "error": str(ex), "runtime": runtime}


@server.tool()
def extra_harness_run(
    harness: str,
    command: List[str],
    json_output: bool = True,
    auto_visualize: bool = True,
    working_dir: Optional[str] = None,
    timeout_sec: float = 60.0,
) -> Dict[str, Any]:
    """
    Executes an agent-native CLI harness (HKUDS/CLI-Anything) for complex desktop software
    (e.g. 'blender', 'gimp', 'freecad', 'libreoffice', 'inkscape', 'krita', 'audacity', 'shotcut', 'obsidian', 'godot', 'qgis').
    Dispatches deterministic subcommands with automatic --json structured machine output
    in under 50ms, eliminating visual token waste and UI coordinate guessing.
    Optionally auto-visualizes the resulting project/artifact live on the user's physical screen
    with SOUL-Gateman visual settle verification and ambient indicators.

    Args:
        harness: Name or slug of the harness (e.g. 'blender', 'cli-anything-blender', 'gimp', 'freecad').
        command: List of CLI arguments and options (e.g. ['mesh', 'add-cube', '--size', '2.0']).
        json_output: If True (default), injects and parses --json for structured output.
        auto_visualize: If True (default), brings created project/artifact live onto the desktop display.
        working_dir: Optional working directory for the command.
        timeout_sec: Maximum timeout in seconds (default 60.0).
    """
    try:
        res = execute_harness(
            harness=harness,
            args=command,
            json_output=json_output,
            auto_visualize=auto_visualize,
            working_dir=working_dir,
            timeout_sec=timeout_sec,
        )
        return res.to_dict()
    except Exception as ex:
        logger.warning("[extra_harness_run] Error: %s", ex)
        return {"success": False, "error": str(ex), "harness": harness}


@server.tool()
def extra_hub_manage(
    action: str,
    harness_name: Optional[str] = None,
    query: Optional[str] = None,
    category: Optional[str] = None,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """
    Discovers, inspects, and installs agent-native CLI harnesses via the CLI-Hub registry
    (40+ applications covering 3D, CAD, Image, Video, Audio, Office, Database, DevOps, OSINT).

    Args:
        action: Management operation: 'list' (list available CLIs), 'search' (search by query/category),
                'info' (inspect details for harness_name), 'install' (install harness into environment),
                'status' (check if harness_name is installed).
        harness_name: Target harness name for 'info', 'install', or 'status' (e.g. 'freecad', 'gimp').
        query: Search term for 'search' action.
        category: Optional category filter for 'list' or 'search' (e.g. '3d', 'image', 'video', 'office').
        force_refresh: Whether to bypass cache and re-fetch the registry.
    """
    try:
        hub = get_cli_hub()
        act = action.strip().lower()

        if act == "list":
            clis = hub.list_harnesses(category=category)
            return {"success": True, "count": len(clis), "clis": clis}

        elif act == "search":
            results = hub.search_harnesses(query=query or "")
            if category:
                results = [r for r in results if r.get("category", "").lower() == category.lower()]
            return {"success": True, "count": len(results), "query": query, "results": results}

        elif act == "info":
            if not harness_name:
                return {"success": False, "error": "harness_name is required for 'info' action"}
            info = hub.get_harness_info(harness_name)
            if info:
                return {"success": True, "harness": harness_name, "info": info}
            return {"success": False, "error": f"Harness '{harness_name}' not found in CLI-Hub registry"}

        elif act == "status":
            if not harness_name:
                return {"success": False, "error": "harness_name is required for 'status' action"}
            installed = hub.is_harness_installed(harness_name)
            return {"success": True, "harness": harness_name, "is_installed": installed}

        elif act == "install":
            if not harness_name:
                return {"success": False, "error": "harness_name is required for 'install' action"}
            res = hub.install_harness(harness_name, force_reinstall=force_refresh)
            return res

        elif act == "uninstall":
            if not harness_name:
                return {"success": False, "error": "harness_name is required for 'uninstall' action"}
            res = hub.uninstall_harness(harness_name)
            return res

        else:
            return {
                "success": False,
                "error": f"Unknown action '{action}'. Valid actions: 'list', 'search', 'info', 'install', 'status', 'uninstall'",
            }
    except Exception as ex:
        logger.warning("[extra_hub_manage] Error: %s", ex)
        return {"success": False, "error": str(ex), "action": action}


@server.tool()
def extra_harness_synthesize(
    software_path_or_repo: str,
    phase_target: str = "all",
    custom_guidance: Optional[str] = None,
    output_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Autonomous GUI-to-CLI Harness Synthesizer (CLI-Anything 7-Phase Generator).
    Synthesizes a production-grade, stateful, tested Click CLI harness and declarative skill
    for any desktop app codebase or git repository.
    
    Args:
        software_path_or_repo: Local path to source code or git URL (e.g. 'https://github.com/...').
        phase_target: Target phase ('analyze' | 'design' | 'scaffold' | 'skill' | 'all').
        custom_guidance: Optional domain instructions, specific operations, or backend notes.
        output_dir: Optional output directory for the generated harness.
    """
    try:
        synth = get_harness_synthesizer()
        res = synth.synthesize(
            software_path_or_repo=software_path_or_repo,
            phase_target=phase_target,
            custom_guidance=custom_guidance,
            output_dir=output_dir,
        )
        return res
    except Exception as ex:
        logger.warning("[extra_harness_synthesize] Error: %s", ex)
        return {"success": False, "error": str(ex), "target": software_path_or_repo}


@server.tool()
def extra_blueprint_start(
    title: str,
    task_type: str = "general",
    milestones: Optional[List[Dict[str, Any]]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Initializes a new long-horizon Task Blueprint with a Directed Acyclic Graph (DAG) of milestones (Plane 1).
    Enables structured progress tracking, rollback checkpoints, turn budgeting, and context folding.
    
    Args:
        title: Human-readable task title (e.g. 'Build 3D Car in Blender').
        task_type: Domain category ('video_editing', '3d_modeling', 'design_deck', 'general').
        milestones: List of milestone objects with 'id', 'name', 'dependencies', 'max_turns', etc.
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
            "budget_status": bp.get_budget_status(),
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
    Enforces turn budgets per milestone to prevent long-horizon stall loops and task starvation.
    Returns a dense semantic state token to prevent LLM context window bloat.
    
    Args:
        task_id: Active blueprint task ID.
        milestone_id: Milestone ID to update.
        action: One of 'start', 'complete', 'fail', 'rollback', 'record_turn', or 'status'.
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
            return {
                "success": True,
                "action": act,
                "milestone": m.to_dict(),
                "max_turns": m.max_turns,
                "turns_consumed": m.turns_consumed,
                "remaining_turns": m.remaining_turns,
            }

        elif act in ("record_turn", "turn", "progress"):
            turn_res = bp.record_milestone_turn(milestone_id)
            bp.save()
            return {"success": True, "action": act, **turn_res}

        elif act in ("status", "budget"):
            budget_res = bp.get_budget_status()
            return {"success": True, "action": act, **budget_res}

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
                    "turns_consumed": m.turns_consumed,
                    "max_turns": m.max_turns,
                    "budget_exceeded": m.is_budget_exceeded,
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
                "turns_consumed": m.turns_consumed,
                "max_turns": m.max_turns,
                "budget_exceeded": m.is_budget_exceeded,
                "budget_warning": (
                    f"Milestone '{m.id}' completed after consuming {m.turns_consumed}/{m.max_turns} turns (budget exceeded)."
                    if m.is_budget_exceeded else None
                ),
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
            return {"success": False, "error": f"Invalid action '{action}'. Use start/complete/fail/rollback/record_turn/status."}
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
    Sub-15ms per-frame visual settle and state transition detector powered by Project SOUL-Gateman.
    Monitors frame buffers at 20-60Hz to verify UI stabilization before dispatching subsequent physical actions.
    Typical end-to-end settle duration is ~120ms (2 consecutive stable frames sampled at 60ms intervals).
    
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


@server.tool()
def extra_workspace_export(
    url_or_id: Optional[str] = None,
    output_path: Optional[str] = None,
    export_format: str = "pdf",
    app_type: Optional[str] = None,
    workspace_dir: Optional[str] = None,
    archive_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Official server-side workspace and deliverable export engine.
    Supports authentic web document exports (Google Docs, Sheets, Slides) as well as
    local project workspace packaging (creating compliant archive bundles).
    
    Args:
        url_or_id: Full document URL or document ID (for web workspaces) or local directory path.
        output_path: Absolute destination path for the exported file or archive.
        export_format: 'pdf', 'docx', 'xlsx', 'csv', 'pptx', 'zip', etc. Default 'pdf'.
        app_type: Optional document type ('document', 'spreadsheets', 'presentation', 'local').
        workspace_dir: Optional local workspace directory to package as zip archive.
        archive_name: Optional archive file name when exporting local workspace directory (e.g. 'mission.zip').
    """
    import os
    import zipfile
    from pathlib import Path

    # Check if local workspace directory export
    target_dir = workspace_dir or (url_or_id if url_or_id and os.path.isdir(url_or_id) else None)
    if target_dir:
        src = Path(target_dir).resolve()
        if not src.exists():
            return {"success": False, "error": f"Workspace directory does not exist: {target_dir}"}

        dest = output_path
        if not dest:
            name = archive_name or f"{src.name}_export.zip"
            if not name.endswith(".zip"):
                name += ".zip"
            dest = str(src / "exports" / name if (src / "exports").exists() else src / name)

        dest_p = Path(dest).resolve()
        dest_p.parent.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(dest_p, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(src):
                for f in files:
                    fp = Path(root) / f
                    if fp.resolve() == dest_p:
                        continue
                    arcname = fp.relative_to(src)
                    zf.write(fp, arcname)

        return {
            "success": True,
            "export_format": "zip",
            "output_path": str(dest_p),
            "size_bytes": dest_p.stat().st_size,
            "source": "official_workspace_export",
            "message": f"Successfully exported local workspace {src} to {dest_p}.",
        }

    if not url_or_id:
        return {"success": False, "error": "Either url_or_id or workspace_dir must be provided."}
    if not output_path:
        return {"success": False, "error": "output_path is required for web workspace export."}

    from extra.fastpath.web_workspace import trigger_workspace_export
    return trigger_workspace_export(
        url_or_id=url_or_id,
        output_path=output_path,
        export_format=export_format,
        app_type=app_type,
    )


@server.tool()
def extra_verify_lineage(
    file_path: Optional[str] = None,
    workspace_path: Optional[str] = None,
    expected_origin: str = "official_web_export",
) -> Dict[str, Any]:
    """
    Verifies the physical lineage and authentic provenance of a deliverable artifact.
    Rejects fraudulent workflow substitutions (e.g. headless Chrome printing local HTML
    instead of genuine Google Workspace or application export).
    
    Args:
        file_path: Path to the artifact to verify (file or archive).
        workspace_path: Optional path to project directory to verify exported lineage manifest.
        expected_origin: 'official_web_export', 'application_export', or 'cli_harness'. Default 'official_web_export'.
    """
    target = file_path or workspace_path
    if not target:
        return {"valid": False, "defects": ["Either file_path or workspace_path must be provided."]}

    from pathlib import Path
    target_p = Path(target)
    if target_p.is_dir():
        manifest = target_p / "exports" / "lineage_manifest.json"
        if manifest.exists():
            return {
                "valid": True,
                "detected_origin": "manifest_verified",
                "file_path": str(manifest),
                "message": f"Verified lineage manifest for workspace at {manifest}.",
            }
        exports = list((target_p / "exports").glob("*")) if (target_p / "exports").exists() else []
        if exports:
            target = str(exports[0])
        else:
            return {
                "valid": True,
                "detected_origin": "workspace_directory",
                "file_path": str(target_p),
                "message": f"Workspace directory {target_p} lineage tracked.",
            }

    from extra.core.composer.lineage import verify_artifact_lineage
    verdict = verify_artifact_lineage(target, expected_origin=expected_origin)
    return verdict.to_dict()


@server.tool()
def extra_verify_state(
    window_title: Optional[str] = None,
    expected_tabs: Optional[int] = None,
    expected_slides: Optional[int] = None,
    min_words: Optional[int] = None,
    expected_sections: Optional[int] = None,
    min_cells: Optional[int] = None,
    doc_type: Optional[str] = None,
    claims: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Decoupled ground-truth state auditor powered by GroundTruthStateCritic.
    Directly measures application runtime reality (counts actual tabs, slides, words, sections)
    across DOM and accessibility trees to prevent epistemic drift and false QA reporting.
    
    Args:
        window_title: Optional active window title to inspect via accessibility plane.
        expected_tabs: Required tab count (for spreadsheets).
        expected_slides: Required slide count (for presentations).
        min_words: Minimum required words (for text documents).
        expected_sections: Required section / heading count.
        min_cells: Minimum required non-empty table cells.
        doc_type: Optional document type classification ('spreadsheet', 'document', 'presentation').
        claims: Optional dictionary containing compound claim assertions.
    """
    ensure_dpi_aware()
    from extra.core.soul.state_critic import audit_ground_truth_state
    c_dict = claims.copy() if claims else {}
    if expected_tabs is not None:
        c_dict["expected_tabs"] = expected_tabs
    if expected_slides is not None:
        c_dict["expected_slides"] = expected_slides
    if min_words is not None:
        c_dict["min_words"] = min_words
    if expected_sections is not None:
        c_dict["expected_sections"] = expected_sections
    if min_cells is not None:
        c_dict["min_cells"] = min_cells
    if doc_type:
        c_dict["doc_type"] = doc_type

    res = audit_ground_truth_state(c_dict, window_title=window_title)
    return {
        "success": True,
        "passed": res.passed,
        "score": res.score,
        "ground_truth": res.ground_truth,
        "defects": res.defects,
        "audit_hash": res.audit_hash,
        "report": res.report_text,
        "latency_ms": res.latency_ms,
    }


@server.tool()
def extra_child_session_status() -> Dict[str, Any]:
    """
    Returns the real-time status and hardware isolation capabilities of the desktop session.
    Probes Windows Terminal Services (WTS) Child Sessions (Tier 1),
    Win32 Isolated Virtual Desktops (Tier 2), and Plane 2 Fast-Path execution (Tier 3).
    """
    ensure_dpi_aware()
    if sys.platform != "win32":
        return {
            "success": True,
            "supported": False,
            "platform": sys.platform,
            "message": "Child session isolation is currently available on Windows.",
        }
    try:
        from extra.core.platform.windows.child_session import get_child_session_manager
        mgr = get_child_session_manager()
        status = mgr.get_status()
        status["success"] = True
        status["supported"] = True
        return status
    except Exception as e:
        return {"success": False, "error": str(e)}


@server.tool()
def extra_pip_control(action: str = "status") -> Dict[str, Any]:
    """
    Controls the hardware-accelerated Picture-in-Picture (PiP) floating preview window.
    Actions:
      - 'start': Launches the always-on-top, draggable floating preview window on the screen.
      - 'stop': Closes and destroys the preview window.
      - 'status': Returns the current visibility and HWND handle.
    """
    ensure_dpi_aware()
    if sys.platform != "win32":
        return {
            "success": False,
            "error": "Picture-in-Picture window is currently supported on Windows.",
        }
    try:
        from extra.core.platform.windows.pip_window import get_pip_window
        pip = get_pip_window()
        clean_action = action.strip().lower()
        if clean_action == "start":
            ok = pip.start()
            return {"success": ok, "is_visible": pip.is_visible(), "hwnd": pip.hwnd}
        elif clean_action == "stop":
            pip.stop()
            return {"success": True, "is_visible": False, "hwnd": None}
        elif clean_action == "status":
            return {"success": True, "is_visible": pip.is_visible(), "hwnd": pip.hwnd}
        else:
            return {"success": False, "error": f"Unknown PiP action '{action}'. Use start, stop, or status."}
    except Exception as e:
        return {"success": False, "error": str(e)}


# Custom discovery & HTTP routes for ChatGPT Plugin and health monitoring
@server.custom_route("/", methods=["GET"])
async def _root_endpoint(request: Any) -> Any:
    from starlette.responses import JSONResponse
    return JSONResponse({
        "name": "Extra Desktop Operator",
        "status": "online",
        "version": "0.3.2",
        "platform": _platform_tag,
        "mcp_endpoint": "/sse",
        "documentation": "https://extra.yantraos.com",
    })


@server.custom_route("/health", methods=["GET"])
async def _health_endpoint(request: Any) -> Any:
    from starlette.responses import JSONResponse
    return JSONResponse({"status": "healthy", "version": "0.3.2", "platform": _platform_tag})


@server.custom_route("/plugin.json", methods=["GET"])
@server.custom_route("/.well-known/ai-plugin.json", methods=["GET"])
async def _plugin_manifest_endpoint(request: Any) -> Any:
    from starlette.responses import JSONResponse
    host_header = request.headers.get("host", "localhost:8000")
    scheme = "https" if request.headers.get("x-forwarded-proto") == "https" or "trycloudflare.com" in host_header else "http"
    base_url = f"{scheme}://{host_header}"

    manifest = {
        "schema_version": "v1",
        "name_for_human": "Extra Desktop Operator",
        "name_for_model": "extra_desktop",
        "description_for_human": "Sovereign desktop automation and computer-use engine that can see your screen, click UI elements, launch apps, and automate tasks.",
        "description_for_model": "Universal computer-use engine and MCP server. Allows the model to inspect desktop displays via screenshots, launch native desktop applications, click UI elements with visual grounding, type text, send hotkeys, and arrange window layouts across Linux, Windows, and macOS.",
        "auth": {
            "type": "service_http",
            "authorization_type": "bearer",
            "verification_tokens": {
                "openai": os.environ.get("EXTRA_OPENAI_VERIFICATION_TOKEN", "extra_openai_token")
            }
        },
        "logo_url": "https://raw.githubusercontent.com/AIYantra/extra/main/assets/extra_banner.png",
        "contact_email": "support@yantraos.com",
        "legal_info_url": "https://github.com/AIYantra/extra/blob/main/LICENSE",
        "extensions": {
            "com.openai": {
                "mcp_server": {
                    "transport": "sse",
                    "url": f"{base_url}/sse"
                },
                "capabilities": [
                    "computer_use",
                    "screen_perception",
                    "os_automation"
                ],
                "tools": [
                    "extra_screenshot",
                    "extra_launch",
                    "extra_click",
                    "extra_type",
                    "extra_hotkey",
                    "extra_snap_layout",
                    "extra_batch_actions",
                    "extra_task_complete"
                ]
            }
        }
    }
    return JSONResponse(manifest)


_PUBLIC_SSE_PATHS = {
    "/",
    "/health",
    "/plugin.json",
    "/.well-known/ai-plugin.json",
}


class BearerAuthASGIMiddleware:
    """
    High-performance zero-copy ASGI middleware enforcing Bearer authentication for MCP endpoints.
    Protects local screen perception and actuation against unauthorized remote invocations.
    """
    def __init__(self, app: Any, token: str) -> None:
        self.app = app
        self.token = token.strip()

    async def __call__(self, scope: Dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") == "http":
            path = scope.get("path", "")
            # Exempt public discovery routes, manifest lookups, and CORS preflight OPTIONS
            if path in _PUBLIC_SSE_PATHS or path.startswith("/.well-known") or scope.get("method") == "OPTIONS":
                await self.app(scope, receive, send)
                return

            headers = dict(scope.get("headers", []))
            auth_header = headers.get(b"authorization", b"").decode("utf-8", errors="ignore").strip()
            query_string = scope.get("query_string", b"").decode("utf-8", errors="ignore")

            is_authed = False
            if auth_header.lower().startswith("bearer "):
                client_token = auth_header[7:].strip()
                if client_token == self.token:
                    is_authed = True

            if not is_authed and query_string:
                from urllib.parse import parse_qs
                params = parse_qs(query_string)
                for qk in ("token", "auth", "api_key", "key"):
                    if params.get(qk, [None])[0] == self.token:
                        is_authed = True
                        break

            if not is_authed:
                body = json.dumps({
                    "error": "unauthorized",
                    "detail": "Invalid or missing Bearer authorization token."
                }).encode("utf-8")
                await send({
                    "type": "http.response.start",
                    "status": 401,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"www-authenticate", b"Bearer"),
                        (b"content-length", str(len(body)).encode("utf-8")),
                    ],
                })
                await send({
                    "type": "http.response.body",
                    "body": body,
                })
                return

        await self.app(scope, receive, send)


def create_unified_mcp_app() -> Any:
    """
    Constructs a unified ASGI Starlette application supporting:
    1. Streamable HTTP (MCP spec default /mcp, and POST fallbacks on /sse and /) for ChatGPT and modern MCP clients.
    2. SSE Transport (GET /sse EventSource and POST /messages) for legacy MCP SSE clients.
    3. Custom discovery routes (GET /, /health, /plugin.json, /.well-known/ai-plugin.json).
    """
    import contextlib
    from starlette.applications import Starlette
    from starlette.routing import Route
    try:
        from mcp.server.fastmcp.server import StreamableHTTPASGIApp
    except ImportError:
        try:
            from mcp.server.mcpserver import StreamableHTTPASGIApp
        except ImportError:
            StreamableHTTPASGIApp = None

    allowed = list(server.settings.transport_security.allowed_hosts or [])
    for h in ("testserver", "testserver:*", "127.0.0.1:*", "localhost:*", "[::1]:*"):
        if h not in allowed:
            allowed.append(h)
    server.settings.transport_security.allowed_hosts = allowed

    sse_app = server.sse_app()
    _ = server.streamable_http_app()
    if hasattr(server, "_session_manager") and server._session_manager is not None:
        server._session_manager.security_settings = server.settings.transport_security
    if StreamableHTTPASGIApp is not None and hasattr(server, "session_manager"):
        streamable_asgi = StreamableHTTPASGIApp(server.session_manager)
    else:
        streamable_asgi = server.streamable_http_app()

    sse_route = None
    for r in sse_app.routes:
        if getattr(r, "path", None) == "/sse":
            sse_route = r
            break

    class UnifiedSSEEndpoint:
        """
        Unified handler for /sse:
        - GET: Streams server events (SSE EventSource)
        - POST: Processes JSON-RPC requests via Streamable HTTP session manager
        """
        async def __call__(self, scope: Dict[str, Any], receive: Any, send: Any) -> None:
            if scope.get("type") == "http" and scope.get("method") == "POST":
                await streamable_asgi(scope, receive, send)
            elif sse_route:
                await sse_route.app(scope, receive, send)
            else:
                from starlette.responses import Response
                res = Response(status_code=404)
                await res(scope, receive, send)

    @contextlib.asynccontextmanager
    async def lifespan(app: Any):
        async with server.session_manager.run():
            yield

    routes = [
        Route("/mcp", endpoint=streamable_asgi, methods=["GET", "POST"]),
        Route("/sse", endpoint=UnifiedSSEEndpoint(), methods=["GET", "POST"]),
        Route("/", endpoint=streamable_asgi, methods=["POST"]),
    ]

    for r in sse_app.routes:
        if getattr(r, "path", None) not in ("/sse",):
            routes.append(r)

    return Starlette(
        debug=server.settings.debug,
        routes=routes,
        lifespan=lifespan,
    )


def run_sse_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    auth_token: Optional[str] = None,
    allowed_hosts: Optional[List[str]] = None,
    tunnel: bool = False,
) -> None:
    """Starts the Extra MCP server over SSE & Streamable HTTP transport."""
    import uvicorn
    from mcp.server.fastmcp.server import TransportSecuritySettings

    tunnel_proc = None
    public_url = None

    if tunnel:
        from extra.relay.tunnel import start_tunnel
        try:
            tunnel_proc, public_url = start_tunnel(local_port=port, host=host)
            if public_url:
                tunnel_host = public_url.replace("https://", "").replace("http://", "")
                if not allowed_hosts:
                    allowed_hosts = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
                allowed_hosts.extend([tunnel_host, f"{tunnel_host}:*", "*.trycloudflare.com"])
        except Exception as e:
            logger.error("Failed to start Cloudflare Tunnel: %s", e)
            print(f"[FAIL] Cloudflare Tunnel failed to start: {e}")

    effective_hosts = allowed_hosts or ["127.0.0.1:*", "localhost:*", "[::1]:*"]
    disable_dns = bool(auth_token) or host == "0.0.0.0" or tunnel

    server.settings.transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=not disable_dns,
        allowed_hosts=effective_hosts,
    )
    server.settings.host = host
    server.settings.port = port
    if hasattr(server, "_session_manager") and server._session_manager is not None:
        server._session_manager.security_settings = server.settings.transport_security

    starlette_app = create_unified_mcp_app()
    app = starlette_app
    if auth_token:
        app = BearerAuthASGIMiddleware(starlette_app, token=auth_token)

    if tunnel and public_url:
        from extra.relay.tunnel import format_chatgpt_banner
        banner = format_chatgpt_banner(public_url=public_url, auth_token=auth_token, local_port=port)
        logger.info("%s", banner)
        print(banner, flush=True)
    else:
        logger.info("=" * 66)
        logger.info("🚀 Extra Flashless MCP SSE Server Active")
        logger.info("   Local Endpoint:   http://%s:%s/sse", host, port)
        logger.info("   Plugin Manifest:  http://%s:%s/.well-known/ai-plugin.json", host, port)
        logger.info("   Health Check:     http://%s:%s/health", host, port)
        if auth_token:
            masked = f"{auth_token[:4]}***" if len(auth_token) > 4 else "***"
            logger.info("   Authentication:   Bearer token protected (token: %s)", masked)
        else:
            logger.warning("   Authentication:   NONE (Open access - only use on private loopback!)")
        logger.info("=" * 66)

    import anyio
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level=server.settings.log_level.lower(),
    )
    uvicorn_server = uvicorn.Server(config)
    try:
        anyio.run(uvicorn_server.serve)
    finally:
        if tunnel_proc:
            from extra.relay.tunnel import stop_tunnel
            stop_tunnel(tunnel_proc)


def main(
    transport: str = "stdio",
    host: str = "127.0.0.1",
    port: int = 8000,
    auth_token: Optional[str] = None,
    allowed_hosts: Optional[List[str]] = None,
    tunnel: bool = False,
) -> None:
    """Starts the Extra MCP server over stdio or SSE transport."""
    ensure_dpi_aware()
    attach_input_desktop()

    if tunnel:
        transport = "sse"

    # Environment variable overrides/fallbacks
    env_token = os.environ.get("EXTRA_AUTH_TOKEN")
    if not auth_token and env_token:
        auth_token = env_token

    env_transport = os.environ.get("EXTRA_MCP_TRANSPORT", transport).lower()
    transport = env_transport

    env_port = os.environ.get("EXTRA_MCP_PORT")
    if env_port and env_port.isdigit():
        port = int(env_port)

    env_host = os.environ.get("EXTRA_MCP_HOST")
    if env_host:
        host = env_host

    # Check for isolated child session environment variable
    if os.environ.get("EXTRA_ISOLATED_DESKTOP") == "1" and sys.platform == "win32":
        try:
            from extra.core.platform.windows.child_session import get_child_session_manager
            mgr = get_child_session_manager()
            mgr.start()
            logger.info("[MCP] Isolated child session active (Tier: %s)", mgr.get_active_tier())
        except Exception as e:
            logger.warning("[MCP] Failed to initialize child session: %s", e)

    # Check for live PiP preview window environment variable
    if os.environ.get("EXTRA_PIP_PREVIEW") == "1" and sys.platform == "win32":
        try:
            from extra.core.platform.windows.pip_window import get_pip_window
            pip = get_pip_window()
            pip.start()
            logger.info("[MCP] Picture-in-Picture floating preview window active (HWND: %s)", pip.hwnd)
        except Exception as e:
            logger.warning("[MCP] Failed to initialize PiP window: %s", e)

    try:
        mig = ensure_startup_migration()
        if mig.get("status") == "migrated":
            logger.info("Startup migration applied: sanitized legacy skills (%s files cleaned)", mig.get("files_cleaned", 0))
    except Exception as e:
        logger.debug("Startup migration check skipped: %s", e)

    try:
        from extra.core.metrics.telemetry import emit_first_run_activation
        entrypoint_tag = "mcp" if transport == "stdio" else f"mcp-{transport}"
        emit_first_run_activation(entrypoint=entrypoint_tag)
    except Exception as e:
        logger.debug("First-run activation check skipped: %s", e)

    if transport in ("sse", "http"):
        run_sse_server(host=host, port=port, auth_token=auth_token, allowed_hosts=allowed_hosts, tunnel=tunnel)
    elif transport == "streamable-http":
        logger.info("Extra Flashless MCP Server initializing on streamable-http (http://%s:%s/mcp)...", host, port)
        server.settings.host = host
        server.settings.port = port
        server.run(transport="streamable-http")
    else:
        logger.info("Extra Flashless MCP Server initializing on stdio transport...")
        server.run(transport="stdio")


if __name__ == "__main__":
    main()

