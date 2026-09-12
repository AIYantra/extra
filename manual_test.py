"""
Project Extra — Interactive Manual Testing Playground
Run directly to manually test each subsystem on your live Windows desktop:
    & "D:\yantra_workspace\extra\.venv\Scripts\python.exe" D:\yantra_workspace\extra\manual_test.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# Force UTF-8 terminal encoding
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure extra is in path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from extra.core.capture import capture_screen
from extra.core.focus import force_activate_window, get_foreground_window, list_windows
from extra.core.geometry import attach_input_desktop, ensure_dpi_aware, get_cursor_position
from extra.core.input_engine import instant_type, mouse_click, send_hotkey
from extra.core.uia_plane import SetOfMarkAnnotator, UIAutomationPlane
from extra.fastpath.browser import execute_browser_action
from extra.fastpath.shell import launch_app


def banner() -> None:
    print("\n" + "=" * 65)
    print(" ⚡ EXTRA: INTERACTIVE MANUAL TESTING PLAYGROUND")
    print("=" * 65)
    print(" [1] Capture Screenshot & Generate Set-of-Mark Badges (Opens Image)")
    print(" [2] Test Instant Typing (3-second countdown to switch to any app)")
    print(" [3] Inspect Foreground Window UI Automation Tree")
    print(" [4] Test Semantic Click by UI Element ID")
    print(" [5] Test App Launcher Fast-Path (calc, notepad, explorer, settings)")
    print(" [6] Test Browser Fast-Path (Zero-download Edge DOM extraction)")
    print(" [7] Run Full 6-Module Core Engine Test Suite")
    print(" [8] Run System Doctor Diagnostic")
    print(" [0] Exit")
    print("=" * 65)


def test_screenshot_som() -> None:
    print("\n--> Capturing desktop frame and overlaying Set-of-Mark badges...")
    ensure_dpi_aware()
    attach_input_desktop()

    t0 = time.perf_counter()
    cap = capture_screen(0)
    t_cap = (time.perf_counter() - t0) * 1000.0

    uia = UIAutomationPlane()
    elements = uia.inspect_window(interactive_only=True, max_elements=50)
    annotator = SetOfMarkAnnotator()
    ann_img, marks = annotator.annotate(cap.image, elements)

    out_file = Path("extra_som_preview.png").resolve()
    ann_img.save(str(out_file))
    print(f" [OK] Captured {cap.width}x{cap.height} in {t_cap:.1f}ms with {len(marks)} UI badges.")
    print(f" [OK] Saved to: {out_file}")
    try:
        os.startfile(str(out_file))
        print(" [OK] Opened preview image in Windows default photo viewer.")
    except Exception as e:
        print(f" (Note: could not auto-open image: {e})")


def test_instant_typing() -> None:
    print("\n--> Instant Typing Test")
    sample_text = input("Enter text to type (press Enter for default sample): ").strip()
    if not sample_text:
        sample_text = "⚡ Tested via Project Extra on Windows 11! [Win32 KEYEVENTF_UNICODE sub-millisecond injection]"

    print("\n>>> SWITCH TO YOUR TARGET WINDOW NOW (Notepad, Browser, Chat, etc.) <<<")
    for i in range(3, 0, -1):
        print(f"    Typing begins in {i}...", flush=True)
        time.sleep(1)

    t0 = time.perf_counter()
    instant_type(sample_text, press_enter=True)
    t_ms = (time.perf_counter() - t0) * 1000.0
    print(f" [OK] Injected {len(sample_text)} characters in {t_ms:.2f} ms ({len(sample_text)/(t_ms/1000.0):.0f} chars/sec)!")


def test_inspect_foreground() -> None:
    print("\n>>> SWITCH TO YOUR TARGET WINDOW (waiting 3 seconds)... <<<")
    time.sleep(3)

    ensure_dpi_aware()
    attach_input_desktop()

    fg = get_foreground_window()
    if not fg:
        print(" [FAIL] Could not detect foreground window.")
        return

    print(f"\nTarget Window: HWND={fg.hwnd} Title='{fg.title}' Process={fg.process_name} Rect={fg.rect}")
    uia = UIAutomationPlane()
    elements = uia.inspect_window(hwnd=fg.hwnd, interactive_only=True, max_elements=30)
    print(f"Discovered {len(elements)} interactive UI elements:")
    for el in elements:
        safe_name = el.name.encode("ascii", "replace").decode("ascii")
        print(f"  [{el.element_id:2d}] {el.control_type:<12} center={el.center} bbox={el.bounding_box} '{safe_name}'")


def test_semantic_click() -> None:
    el_str = input("\nEnter UI Element ID to click (from option 3): ").strip()
    if not el_str.isdigit():
        print("Invalid ID.")
        return
    el_id = int(el_str)
    uia = UIAutomationPlane()
    print(f"--> Invoking Element [{el_id}] via UI Automation COM...")
    ok = uia.invoke_element(el_id)
    print(f" [Result] Invoke status: {ok}")


def test_app_launcher() -> None:
    target = input("\nEnter app to launch ('calc', 'notepad', 'explorer', 'settings', 'cmd'): ").strip().lower()
    if not target:
        target = "calc"
    print(f"--> Launching '{target}'...")
    res = launch_app(target, wait_for_window=True)
    print(f" [OK] Result: success={res.success}, pid={res.pid}, hwnd={res.hwnd}, window='{res.window_title}'")


def test_browser_fastpath() -> None:
    url = input("\nEnter URL (press Enter for 'https://news.ycombinator.com'): ").strip()
    if not url:
        url = "https://news.ycombinator.com"
    print(f"--> Navigating to {url} via Edge Playwright...")
    res = execute_browser_action("navigate", url=url)
    print(f" [OK] Navigated: status={res.get('status')} title='{res.get('title')}' in {res.get('duration_ms')}ms")
    content = execute_browser_action("content")
    text = content.get("content", "")
    print(f"\n[Extracted Content Preview ({len(text)} chars)]:")
    print("-" * 50)
    print(text[:400] + ("..." if len(text) > 400 else ""))
    print("-" * 50)
    execute_browser_action("close")


def main() -> None:
    ensure_dpi_aware()
    attach_input_desktop()

    while True:
        banner()
        choice = input("Select an option (0-8): ").strip()
        if choice == "1":
            test_screenshot_som()
        elif choice == "2":
            test_instant_typing()
        elif choice == "3":
            test_inspect_foreground()
        elif choice == "4":
            test_semantic_click()
        elif choice == "5":
            test_app_launcher()
        elif choice == "6":
            test_browser_fastpath()
        elif choice == "7":
            from extra.test_core_engine import run_tests
            run_tests()
        elif choice == "8":
            from extra.cli import cmd_doctor
            cmd_doctor()
        elif choice == "0":
            print("\nExiting. Happy automating!\n")
            break
        else:
            print("\n[!] Invalid selection, please try again.")


if __name__ == "__main__":
    main()
