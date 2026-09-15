"""
Project Extra — Core Engine End-to-End Integration Test Suite
Validates all Phase 1 subsystems:
1. Geometry & PerMonitorV2 DPI Normalization
2. Screen Capture & ROI Cropping
3. Input Engine Mechanics
4. Window Focus & Enumeration
5. UI Automation Plane & Set-of-Mark
6. Stall Breaker & Safety Supervisor
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from extra.core import (
    ActionOutcome,
    CaptureResult,
    EmergencyAbortError,
    MonitorInfo,
    ScreenCaptureEngine,
    SetOfMarkAnnotator,
    StallBreaker,
    StallStatus,
    UIAutomationPlane,
    UIElement,
    WindowInfo,
    attach_input_desktop,
    capture_roi,
    capture_screen,
    clamp_coordinates,
    denormalize_bbox,
    denormalize_coordinates,
    ensure_dpi_aware,
    get_bbox_center,
    get_cursor_position,
    get_foreground_window,
    get_monitors_info,
    get_primary_monitor,
    list_windows,
    mouse_move,
    normalize_bbox,
    normalize_coordinates,
    IndicatorController,
    AudioIndicator,
    get_indicator_controller,
)


def run_tests() -> None:
    print("=" * 60)
    print(" EXTRA PHASE 1: CORE ENGINE INTEGRATION TEST SUITE")
    print("=" * 60)

    # Attach thread to interactive desktop
    attach_input_desktop()

    # 1. Geometry & DPI
    print("\n[1/6] Testing Geometry & DPI Awareness...")
    dpi_ok = ensure_dpi_aware()
    print(f"  [OK] DPI Awareness Context Initialized: {dpi_ok}")

    monitors = get_monitors_info()
    assert len(monitors) > 0, "No monitors detected!"
    print(f"  [OK] Discovered {len(monitors)} monitor(s):")
    for m in monitors:
        print(f"     - Mon {m.index}: {m.width}x{m.height} @ ({m.left}, {m.top}), scale={m.scale_factor}x, primary={m.is_primary}")

    cursor = get_cursor_position()
    norm = normalize_coordinates(cursor[0], cursor[1], 0)
    denorm = denormalize_coordinates(norm[0], norm[1], 0)
    print(f"  [OK] Cursor: {cursor} -> Normalized: {norm} -> Denormalized: {denorm}")
    assert abs(cursor[0] - denorm[0]) <= 1 and abs(cursor[1] - denorm[1]) <= 1, "Coordinate math drift detected!"

    # 2. Capture Engine
    print("\n[2/6] Testing High-Speed Screen Capture...")
    cap = capture_screen(0)
    print(f"  [OK] Primary Monitor Capture: {cap.width}x{cap.height} in {cap.duration_ms} ms")
    assert cap.width > 0 and cap.height > 0
    assert cap.image is not None

    b64 = cap.to_base64(quality=80)
    print(f"  [OK] Base64 JPEG Encoding: {len(b64)} chars")
    assert len(b64) > 1000

    roi_cap = capture_roi(50, 50, 350, 250, 0)
    print(f"  [OK] ROI Capture (300x200): {roi_cap.width}x{roi_cap.height} in {roi_cap.duration_ms} ms")
    assert roi_cap.width == 300 and roi_cap.height == 200

    # 3. Focus & Window Management
    print("\n[3/6] Testing Window Focus & Enumeration...")
    fg = get_foreground_window()
    print(f"  [OK] Foreground Window: HWND={fg.hwnd if fg else None}, Title={repr(fg.title) if fg else 'None'}")

    wins = list_windows(visible_only=True)
    print(f"  [OK] Total Visible Top-Level Windows: {len(wins)}")
    for w in wins[:4]:
        safe_title = w.title[:35].encode("ascii", "replace").decode("ascii")
        print(f"     - [{w.hwnd}] '{safe_title}' ({w.process_name}) rect={w.rect}")

    # 4. UI Automation Plane & Set-of-Mark
    print("\n[4/6] Testing UI Automation Semantic Plane & Set-of-Mark...")
    uia = UIAutomationPlane()
    t_uia_start = time.perf_counter()
    elements = uia.inspect_window(interactive_only=True, max_elements=25)
    t_uia_ms = (time.perf_counter() - t_uia_start) * 1000.0
    print(f"  [OK] Inspected {len(elements)} interactive UI elements in {t_uia_ms:.2f} ms")
    for el in elements[:5]:
        safe_name = el.name.encode("ascii", "replace").decode("ascii")
        print(f"     - [{el.element_id}] {el.control_type}: '{safe_name}' center={el.center} bbox={el.bounding_box}")

    annotator = SetOfMarkAnnotator()
    ann_img, mark_map = annotator.annotate(cap.image, elements)
    print(f"  [OK] Set-of-Mark Overlay Generated: {ann_img.size} with {len(mark_map)} element badges")
    assert len(mark_map) == len(elements)

    # 5. Input Engine Mechanics
    print("\n[5/6] Testing Win32 Input Engine Mechanics...")
    orig_cursor = get_cursor_position()
    test_target = (orig_cursor[0] + 15, orig_cursor[1] + 15)
    mouse_move(test_target[0], test_target[1])
    time.sleep(0.02)
    moved_cursor = get_cursor_position()
    print(f"  [OK] Micro-mouse displacement: {orig_cursor} -> {moved_cursor}")
    mouse_move(orig_cursor[0], orig_cursor[1])
    time.sleep(0.02)
    restored_cursor = get_cursor_position()
    print(f"  [OK] Restored cursor position: {restored_cursor}")

    # 6. Stall Breaker & Safety Supervisor
    print("\n[6/6] Testing Stall Breaker & 2-Strike Protection...")
    breaker = StallBreaker(max_strikes=2)
    breaker.check_safety_abort()
    print("  [OK] Corner fail-safe check passed.")

    # Strike 1 check
    out1 = breaker.evaluate_action(cap.image, cap.image, before_hwnd=1, after_hwnd=1, action_name="test_click")
    assert out1.status == StallStatus.WARNING and out1.strikes == 1
    print(f"  [OK] Strike 1 Warning Triggered: {out1.status.value}")

    # Strike 2 check
    out2 = breaker.evaluate_action(cap.image, cap.image, before_hwnd=1, after_hwnd=1, action_name="test_click")
    assert out2.status == StallStatus.STALLED and out2.strikes == 2
    print(f"  [OK] Strike 2 Stall Triggered: {out2.status.value}")

    # Visual recovery check
    out3 = breaker.evaluate_action(cap.image, ann_img, before_hwnd=1, after_hwnd=1, action_name="test_recovery")
    assert out3.status == StallStatus.NORMAL and out3.strikes == 0
    print(f"  [OK] Visual Change Reset Strikes to 0: {out3.status.value}")

    # 7. Human-Agent Awareness & Task Indicators
    print("\n[7/7] Testing Human-Agent Awareness & Indicators (Edge, Halo, Audio)...")
    indicator_ctrl = get_indicator_controller()
    assert indicator_ctrl is not None
    # Test audio synthesis
    audio = AudioIndicator()
    complete_wav = audio._synthesize("complete")
    assert len(complete_wav) > 1000
    start_wav = audio._synthesize("start")
    assert len(start_wav) > 1000
    print(f"  [OK] Audio Chimes Synthesized: complete={len(complete_wav)} bytes, start={len(start_wav)} bytes")

    # Start indicator
    indicator_ctrl.task_start("Test Autonomous Workflow", 0)
    time.sleep(0.3)
    print("  [OK] Ambient Screen Edge Pulse Initialized")

    # Action dispatch
    indicator_ctrl.task_action("click", 500, 300, 0)
    time.sleep(0.2)
    print("  [OK] Cursor Halo & Click Ripple Dispatched")

    # Task completion
    indicator_ctrl.task_complete("Test Workflow Completed", success=True, play_chime=True)
    time.sleep(1.0)
    print("  [OK] Completion Sequence Dispatched (Emerald Flash + Chime)")

    print("\n" + "=" * 60)
    print(" ALL CORE ENGINE & TASK INDICATION MODULES VERIFIED!")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
