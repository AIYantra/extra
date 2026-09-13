"""
Project Extra — Command-Line Interface (CLI) & System Diagnostic Runner
Provides `extra doctor`, `extra test`, `extra run`, `extra inspect`, and `extra snap`.
"""

from __future__ import annotations

import argparse
import os
import platform
import sys
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from extra import __version__
except Exception:
    __version__ = "0.1.1"

from extra.core.capture import capture_screen
from extra.core.focus import (
    find_window_by_title,
    get_foreground_window,
    list_windows,
)
from extra.core.geometry import (
    attach_input_desktop,
    ensure_dpi_aware,
    get_cursor_position,
    get_monitors_info,
)
from extra.core.uia_plane import SetOfMarkAnnotator, UIAutomationPlane
from extra.fastpath.shell import resolve_executable


def cmd_doctor() -> int:
    """Runs a complete system health and capability diagnostic."""
    ensure_dpi_aware()
    attach_input_desktop()

    print("=" * 65)
    print(" EXTRA SYSTEM HEALTH & HARDWARE DIAGNOSTIC (DOCTOR)")
    print("=" * 65)

    # 1. OS & Architecture
    print("\n[Operating System & Architecture]")
    os_name = platform.system()
    os_release = platform.release()
    os_version = platform.version()
    machine = platform.machine()
    py_ver = sys.version.split()[0]
    print(f"  Extra Version: {__version__}")
    print(f"  OS:            {os_name} {os_release} (Build {os_version})")
    print(f"  Architecture:  {machine}")
    print(f"  Python:        {py_ver} ({'64-bit' if sys.maxsize > 2**32 else '32-bit'})")

    if os_name != "Windows":
        print("  [FAIL] Extra requires Windows 10 or Windows 11.")
        return 1
    else:
        print("  [OK] Supported Windows host.")

    # 2. DPI & Security Desktop Attachment
    print("\n[DPI Geometry & Thread Desktop]")
    dpi_ok = ensure_dpi_aware()
    desk_ok = attach_input_desktop()
    print(f"  DPI Awareness: {'PerMonitorV2 (Active)' if dpi_ok else 'Fallback'}")
    print(f"  Input Desktop: {'Attached (Default)' if desk_ok else 'Standard'}")

    cursor = get_cursor_position()
    print(f"  Mouse Cursor:  Physical pixel {cursor}")

    # 3. Displays & Hardware Metrics
    print("\n[Displays & Multi-Monitor Metrics]")
    monitors = get_monitors_info()
    print(f"  Monitors:      {len(monitors)} connected display(s)")
    for m in monitors:
        print(f"    - Display {m.index}: {m.width}x{m.height} @ ({m.left}, {m.top}) | DPI: {m.dpi_x}x{m.dpi_y} ({m.scale_factor}x scale) | Primary={m.is_primary}")

    # 4. Perception Engine Latency Benchmark
    print("\n[Screen Capture Benchmark]")
    latencies = []
    for _ in range(3):
        cap = capture_screen(0)
        latencies.append(cap.duration_ms)
    avg_latency = sum(latencies) / len(latencies)
    print(f"  Capture Runs:  {latencies[0]:.1f}ms, {latencies[1]:.1f}ms, {latencies[2]:.1f}ms (Average: {avg_latency:.1f}ms)")
    if avg_latency < 100:
        print(f"  [OK] High-speed screen capture verified ({avg_latency:.1f}ms).")
    else:
        print("  [WARN] Screen capture took longer than expected.")

    # 5. Semantic UI Automation v3 Plane
    print("\n[Microsoft UI Automation Core COM Layer]")
    try:
        uia = UIAutomationPlane()
        t0 = time.perf_counter()
        elems = uia.inspect_window(interactive_only=True, max_elements=20)
        t_uia = (time.perf_counter() - t0) * 1000.0
        print(f"  UIA Status:    Active & Operational ({len(elems)} elements inspected in {t_uia:.1f}ms)")
        print("  [OK] UIAutomationCore.dll COM interface functional.")
    except Exception as e:
        print(f"  [FAIL] UIA Plane Error: {e}")

    # 6. Microsoft Edge & Playwright Fast-Path
    print("\n[Browser Fast-Path (Microsoft Edge / Playwright)]")
    edge_path = resolve_executable("edge")
    if edge_path and os.path.exists(edge_path):
        print(f"  Edge Binary:   {edge_path}")
        print("  [OK] Microsoft Edge available for zero-download web fast-path.")
    else:
        print("  [WARN] Microsoft Edge not found at standard path.")

    # 7. Active Windows
    print("\n[Active Desktop Windows]")
    fg = get_foreground_window()
    print(f"  Foreground:    {repr(fg.title) if fg else 'None'} ({fg.process_name if fg else ''})")
    wins = list_windows(visible_only=True)
    print(f"  Total Windows: {len(wins)} visible top-level windows")

    print("\n" + "=" * 65)
    print(" DOCTOR DIAGNOSTIC COMPLETE: SYSTEM IS READY FOR EXTRA")
    print("=" * 65)
    return 0


def cmd_test() -> int:
    """Runs the full integration test suite."""
    from extra.test_core_engine import run_tests
    try:
        run_tests()
        return 0
    except Exception as e:
        print(f"\n[FAIL] Test suite failed: {e}")
        return 1


def cmd_run(args: argparse.Namespace) -> int:
    """Starts the Model Context Protocol (MCP) server."""
    from extra.mcp.server import main
    main()
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    """Quickly inspects UI Automation controls on the desktop."""
    ensure_dpi_aware()
    attach_input_desktop()

    uia = UIAutomationPlane()
    print(f"Inspecting UI elements (window='{args.window}', max={args.limit})...")
    hwnd = None
    if args.window:
        win = find_window_by_title(args.window)
        if win:
            hwnd = win.hwnd
            print(f"Targeting window [{hwnd}] '{win.title}'")

    elems = uia.inspect_window(hwnd=hwnd, interactive_only=not args.all, max_elements=args.limit)
    print(f"\nDiscovered {len(elems)} elements:")
    for el in elems:
        safe_name = el.name.encode("ascii", "replace").decode("ascii")
        print(f"  [{el.element_id:2d}] {el.control_type:<12} center={el.center} bbox={el.bounding_box} '{safe_name}'")
    return 0


def cmd_snap(args: argparse.Namespace) -> int:
    """Captures a screenshot and optionally overlays Set-of-Mark badges."""
    ensure_dpi_aware()
    attach_input_desktop()

    cap = capture_screen(monitor_index=args.monitor)
    output_path = Path(args.output)

    if args.som:
        uia = UIAutomationPlane()
        elems = uia.inspect_window(interactive_only=True, max_elements=50)
        annotator = SetOfMarkAnnotator()
        ann_img, mark_map = annotator.annotate(cap.image, elems)
        ann_img.save(output_path)
        print(f"Saved Set-of-Mark annotated screenshot ({len(mark_map)} badges) to {output_path.resolve()}")
    else:
        cap.image.save(output_path)
        print(f"Saved screenshot ({cap.width}x{cap.height}, {cap.duration_ms}ms) to {output_path.resolve()}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="extra",
        description="Extra — Flashless Windows 10/11 Computer-Use Engine & MCP Server",
    )
    parser.add_argument(
        "--version", "-v", action="version", version=f"extra {__version__}"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # doctor
    subparsers.add_parser("doctor", help="Run system health and capability diagnostics")

    # test
    subparsers.add_parser("test", help="Run integration test suite")

    # run
    run_parser = subparsers.add_parser("run", help="Start the MCP Server on stdio")
    run_parser.add_argument("--transport", default="stdio", choices=["stdio"], help="Transport mode")

    # inspect
    inspect_parser = subparsers.add_parser("inspect", help="Inspect Windows UI Automation tree")
    inspect_parser.add_argument("--window", "-w", default=None, help="Filter by window title")
    inspect_parser.add_argument("--limit", "-n", type=int, default=30, help="Max elements to display")
    inspect_parser.add_argument("--all", "-a", action="store_true", help="Include non-interactive containers")

    # snap
    snap_parser = subparsers.add_parser("snap", help="Capture a desktop screenshot")
    snap_parser.add_argument("--output", "-o", default="screenshot.png", help="Output file path")
    snap_parser.add_argument("--monitor", "-m", type=int, default=0, help="Monitor index")
    snap_parser.add_argument("--som", action="store_true", help="Overlay Set-of-Mark numbered badges")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "doctor":
        sys.exit(cmd_doctor())
    elif args.command == "test":
        sys.exit(cmd_test())
    elif args.command == "run":
        sys.exit(cmd_run(args))
    elif args.command == "inspect":
        sys.exit(cmd_inspect(args))
    elif args.command == "snap":
        sys.exit(cmd_snap(args))


if __name__ == "__main__":
    main()
