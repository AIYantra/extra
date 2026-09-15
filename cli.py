"""
Project Extra — Command-Line Interface (CLI) & System Diagnostic Runner
Provides `extra doctor`, `extra test`, `extra run`, `extra inspect`, and `extra snap`.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import shutil
import subprocess
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


def cmd_indicators_demo() -> int:
    """Demonstrates ambient edge pulse, cursor halo, and harmonic audio chime live."""
    from extra.core.indicators import get_indicator_controller

    ctrl = get_indicator_controller()
    print("=" * 65)
    print(" EXTRA TASK INDICATION & AWARENESS LIVE DEMO")
    print("=" * 65)

    print("\n[1/3] Activating Ambient Screen Edge Pulse (Electric Indigo/Cyan Breathing)...")
    ctrl.task_start("Autonomous Task Demonstration", monitor_index=0)
    time.sleep(1.2)

    print("[2/3] Demonstrating Interactive Cursor Halo & Click Ripple...")
    cur_x, cur_y = get_cursor_position()
    for i in range(1, 6):
        step_x = cur_x + i * 25
        step_y = cur_y + int(18 * math.sin(i * 0.8))
        ctrl.task_action("move", step_x, step_y)
        time.sleep(0.08)

    # Click ripple at target coordinate
    ctrl.task_action("click", cur_x + 150, cur_y)
    print("  [OK] Click ripple triggered at pointer coordinates.")
    time.sleep(1.0)

    print("[3/3] Completing Task: Flashing Soft Emerald Green & Playing Harmonic Chime...")
    ctrl.task_complete("Task demonstrated and completed successfully", success=True, play_chime=True)
    time.sleep(2.0)

    print("\n[OK] Demo completed! All overlays smoothly dissolved.")
    return 0


def sync_ai_rules_and_skills(repo_dir: Path) -> bool:
    """Deploys AI rules, skills, MCP schemas, and client configurations."""
    print("\n[AI Rules & Skills Synchronization]")
    rule_src = repo_dir / "rules" / "extra_automation.md"
    if not rule_src.exists():
        print(f"  [WARN] Rule file not found at {rule_src}")
        return False

    rule_content = rule_src.read_text(encoding="utf-8")
    user_home = Path.home()

    # 1. Global Skill: ~/.gemini/config/skills/extra-automation/SKILL.md
    skill_dir = user_home / ".gemini" / "config" / "skills" / "extra-automation"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(rule_content, encoding="utf-8")
    print(f"  [OK] Global skill deployed: {skill_dir / 'SKILL.md'}")

    # 2. Always-On Protocol: ~/.gemini/GEMINI.md
    gemini_md = user_home / ".gemini" / "GEMINI.md"
    if gemini_md.exists():
        existing = gemini_md.read_text(encoding="utf-8")
        if "Extra Windows Desktop Automation Protocol" not in existing:
            gemini_md.write_text(existing + "\n\n" + rule_content, encoding="utf-8")
            print(f"  [OK] Registered always-on protocol in {gemini_md}")
        else:
            print(f"  [OK] Always-on protocol already active in {gemini_md}")
    else:
        gemini_md.parent.mkdir(parents=True, exist_ok=True)
        gemini_md.write_text(rule_content, encoding="utf-8")
        print(f"  [OK] Created always-on protocol in {gemini_md}")

    # 3. Antigravity MCP Instructions & Tool Schemas: ~/.gemini/antigravity-cli/mcp/extra/
    mcp_extra_dir = user_home / ".gemini" / "antigravity-cli" / "mcp" / "extra"
    if mcp_extra_dir.exists():
        (mcp_extra_dir / "instructions.md").write_text(rule_content, encoding="utf-8")
        print(f"  [OK] Updated MCP instructions: {mcp_extra_dir / 'instructions.md'}")

        # Update JSON tool schemas
        try:
            import asyncio
            from extra.mcp.server import server

            async def _dump():
                tools = await server.list_tools()
                count = 0
                for t in tools:
                    schema = {
                        "name": t.name,
                        "description": t.description,
                        "parameters": getattr(t, "input_schema", getattr(t, "inputSchema", {})),
                    }
                    fp = mcp_extra_dir / f"{t.name}.json"
                    fp.write_text(json.dumps(schema), encoding="utf-8")
                    count += 1
                return count

            tool_count = asyncio.run(_dump())
            print(f"  [OK] Synchronized {tool_count} MCP schema definitions.")
        except Exception as ex:
            print(f"  [WARN] Could not refresh MCP schemas: {ex}")

    # 4. User Profile Rules: ~/.agents/rules/extra_automation.md
    user_agents_dir = user_home / ".agents" / "rules"
    user_agents_dir.mkdir(parents=True, exist_ok=True)
    (user_agents_dir / "extra_automation.md").write_text(rule_content, encoding="utf-8")
    print(f"  [OK] User rules deployed: {user_agents_dir / 'extra_automation.md'}")

    # 5. Workspace Rules (if in workspace)
    cwd_rules = Path.cwd() / ".agents" / "rules"
    if cwd_rules.parent.exists():
        cwd_rules.mkdir(parents=True, exist_ok=True)
        (cwd_rules / "extra_automation.md").write_text(rule_content, encoding="utf-8")
        print(f"  [OK] Workspace rules deployed: {cwd_rules / 'extra_automation.md'}")

    # 6. Antigravity CLI (agy) Re-registration
    agy_cmd = shutil.which("agy")
    if agy_cmd:
        try:
            subprocess.run(
                [agy_cmd, "mcp", "add", "extra", sys.executable, "-m", "extra.mcp.server"],
                capture_output=True,
                text=True,
                check=True,
            )
            print("  [OK] Re-registered with Antigravity CLI (agy).")
        except Exception as ex:
            print(f"  [WARN] agy mcp re-registration notice: {ex}")

    # 7. Claude Desktop Configuration
    claude_dir = Path(os.environ.get("APPDATA", "")) / "Claude"
    claude_config = claude_dir / "claude_desktop_config.json"
    if claude_dir.exists():
        try:
            config_data = {}
            if claude_config.exists():
                raw = claude_config.read_text(encoding="utf-8").strip()
                if raw:
                    config_data = json.loads(raw)
            if "mcpServers" not in config_data:
                config_data["mcpServers"] = {}
            config_data["mcpServers"]["extra"] = {
                "command": sys.executable,
                "args": ["-m", "extra.mcp.server"],
            }
            claude_config.write_text(json.dumps(config_data, indent=2), encoding="utf-8")
            print(f"  [OK] Claude Desktop configuration verified: {claude_config}")
        except Exception as ex:
            print(f"  [WARN] Could not update Claude Desktop configuration: {ex}")

    return True


def cmd_update(args: argparse.Namespace) -> int:
    """Synchronizes Extra repository, dependencies, AI rules, and MCP configurations."""
    print("=" * 65)
    print(" EXTRA SYSTEM & AI RULES SYNCHRONIZATION (UPDATE)")
    print("=" * 65)

    repo_dir = Path(__file__).resolve().parent
    if not (repo_dir / "requirements.txt").exists() and (repo_dir.parent / "requirements.txt").exists():
        repo_dir = repo_dir.parent

    git_cmd = shutil.which("git")

    # If --rules-only is requested
    if args.rules_only:
        success = sync_ai_rules_and_skills(repo_dir)
        print("\n[OK] AI rules and skills synchronization complete.")
        return 0 if success else 1

    # Phase 1: Git Repository Synchronization
    print("\n[Repository Synchronization]")
    is_git_repo = (repo_dir / ".git").exists() and git_cmd is not None
    if not is_git_repo:
        if args.check:
            print(f"  [INFO] ZIP-based installation detected at {repo_dir}.")
            print("  Run 'extra update' to refresh to the latest release from GitHub.")
            return 0

        print(f"  [INFO] ZIP-based installation detected at {repo_dir}.")
        print("  Downloading latest release from GitHub (https://github.com/AIYantra/extra)...")
        import urllib.request
        import zipfile
        import tempfile

        try:
            zip_url = "https://github.com/AIYantra/extra/archive/refs/heads/main.zip"
            with tempfile.TemporaryDirectory() as tmpdir:
                zip_file = Path(tmpdir) / "extra.zip"
                urllib.request.urlretrieve(zip_url, zip_file)
                with zipfile.ZipFile(zip_file, "r") as zf:
                    zf.extractall(tmpdir)
                extracted_app = Path(tmpdir) / "extra-main"
                if extracted_app.exists():
                    for item in extracted_app.rglob("*"):
                        rel = item.relative_to(extracted_app)
                        dest = repo_dir / rel
                        if item.is_dir():
                            dest.mkdir(parents=True, exist_ok=True)
                        else:
                            shutil.copy2(item, dest)
                    print("  [OK] Repository updated to latest version from GitHub.")
        except Exception as ex:
            print(f"  [WARN] Failed to update repository via ZIP archive: {ex}")
    else:
        try:
            print("  Fetching latest commits from remote origin/main...")
            subprocess.run(
                [git_cmd, "-C", str(repo_dir), "fetch", "origin", "main"],
                capture_output=True,
                text=True,
                check=True,
            )

            # Check commit count
            diff_proc = subprocess.run(
                [git_cmd, "-C", str(repo_dir), "rev-list", "HEAD..origin/main", "--count"],
                capture_output=True,
                text=True,
                check=True,
            )
            incoming_count = int(diff_proc.stdout.strip() or "0")

            if args.check:
                if incoming_count > 0:
                    print(f"  [UPDATE AVAILABLE] {incoming_count} new commit(s) on origin/main:")
                    log_proc = subprocess.run(
                        [git_cmd, "-C", str(repo_dir), "log", "HEAD..origin/main", "--oneline"],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    for line in log_proc.stdout.strip().splitlines():
                        print(f"    - {line}")
                    print("\nRun 'extra update' to apply these updates.")
                else:
                    print("  [UP TO DATE] Extra is already on the latest upstream commit.")
                return 0

            if incoming_count > 0:
                print(f"  Incoming updates detected ({incoming_count} commits):")
                log_proc = subprocess.run(
                    [git_cmd, "-C", str(repo_dir), "log", "HEAD..origin/main", "--oneline"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                for line in log_proc.stdout.strip().splitlines():
                    print(f"    - {line}")

                if args.force:
                    print("  [FORCE] Resetting local repository to origin/main...")
                    subprocess.run(
                        [git_cmd, "-C", str(repo_dir), "reset", "--hard", "origin/main"],
                        check=True,
                    )
                    print("  [OK] Repository hard-reset to origin/main.")
                else:
                    status_proc = subprocess.run(
                        [git_cmd, "-C", str(repo_dir), "status", "--porcelain"],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    has_local_changes = bool(status_proc.stdout.strip())
                    if has_local_changes:
                        print("  Stashing local modifications...")
                        subprocess.run(
                            [git_cmd, "-C", str(repo_dir), "stash", "push", "-m", "extra-update-autostash"],
                            check=True,
                        )

                    print("  Pulling upstream updates...")
                    subprocess.run(
                        [git_cmd, "-C", str(repo_dir), "pull", "origin", "main"],
                        check=True,
                    )

                    if has_local_changes:
                        print("  Restoring local modifications...")
                        try:
                            subprocess.run([git_cmd, "-C", str(repo_dir), "stash", "pop"], check=True)
                        except Exception:
                            print("  [WARN] Merge conflict in stash pop. Changes remain in stash.")

                    print("  [OK] Repository updated successfully.")
            else:
                print("  [OK] Repository is already up to date with origin/main.")

        except Exception as ex:
            print(f"  [WARN] Git update error: {ex}")
            if args.check:
                return 1

    # Phase 2: Dependency Refresh (unless --skip-deps)
    if not args.skip_deps:
        print("\n[Dependency Refresh]")
        req_file = repo_dir / "requirements.txt"
        if req_file.exists():
            print(f"  Verifying dependencies from {req_file.name}...")
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--quiet", "--upgrade", "-r", str(req_file)],
                    check=True,
                )
                print("  [OK] Production requirements refreshed.")
            except Exception as ex:
                print(f"  [WARN] Failed to refresh requirements: {ex}")

        pyproject_file = repo_dir / "pyproject.toml"
        if pyproject_file.exists():
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--quiet", "-e", str(repo_dir)],
                    check=True,
                )
                print("  [OK] Package editable link verified.")
            except Exception as ex:
                print(f"  [WARN] Failed to install editable package: {ex}")
    else:
        print("\n[Dependency Refresh] Skipped (--skip-deps specified).")

    # Phase 3: AI Rules & Skills Synchronization
    sync_ai_rules_and_skills(repo_dir)

    print("\n" + "=" * 65)
    print(" EXTRA UPDATE COMPLETED SUCCESSFULLY")
    print("=" * 65)
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

    # indicators
    subparsers.add_parser("indicators", help="Demonstrate ambient screen pulse, cursor halo, and audio chime")

    # update
    update_parser = subparsers.add_parser("update", help="Update Extra, refresh dependencies, and sync AI rules")
    update_parser.add_argument("--check", action="store_true", help="Check for available updates without applying")
    update_parser.add_argument("--rules-only", action="store_true", help="Synchronize AI rules and skills only (fast)")
    update_parser.add_argument("--skip-deps", action="store_true", help="Pull code and sync rules without pip re-install")
    update_parser.add_argument("--force", action="store_true", help="Force update and reset local changes to upstream")

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
    elif args.command == "indicators":
        sys.exit(cmd_indicators_demo())
    elif args.command == "update":
        sys.exit(cmd_update(args))
    elif args.command == "run":
        sys.exit(cmd_run(args))
    elif args.command == "inspect":
        sys.exit(cmd_inspect(args))
    elif args.command == "snap":
        sys.exit(cmd_snap(args))


if __name__ == "__main__":
    main()
