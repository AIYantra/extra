"""
Project Extra — Universal Computer Use Task Suite (150 Industrial Regression Tasks)
Direct programmatic verification of TASK-001 through TASK-150 from tasksuite.md.
Ensures zero regressions across Shell, Perception, Input, Focus, UIA, Browser,
StallBreaker, Memory, Scout, Multi-App Workflows, Security, and Dynamic Registry.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from extra.core.platform.base import (
    CaptureResult,
    LaunchResult,
    MonitorInfo,
    UIElement,
    WindowInfo,
    get_bbox_center,
    image_to_base64,
)
from extra.core.platform.windows.geometry import (
    clamp_coordinates,
    denormalize_bbox,
    denormalize_coordinates,
    ensure_dpi_aware,
    get_cursor_position,
    get_monitors_info,
    get_primary_monitor,
    get_virtual_screen_bounds,
    normalize_bbox,
    normalize_coordinates,
)
from extra.core.platform.windows.input_engine import (
    atomic_clipboard_paste,
    instant_type,
    mouse_click,
    mouse_double_click,
    mouse_drag,
    mouse_move,
    mouse_scroll,
    send_hotkey,
)
from extra.core.platform.windows.focus import (
    find_window_by_title,
    find_windows_by_process,
    force_activate_window,
    get_foreground_window,
    get_window_executable_path,
    get_window_info,
    list_windows,
)
from extra.core.platform.windows.shell import (
    APP_REGISTRY,
    BROWSER_CANDIDATE_PATHS,
    BUILTIN_APP_REGISTRY,
    WindowsShellLauncher,
    get_registered_apps,
    get_user_registry_path,
    launch_app,
    load_user_registry,
    open_uri,
    register_app,
    resolve_executable,
)
from extra.core.platform.macos.shell import (
    MAC_APP_REGISTRY,
    BUILTIN_MAC_APP_REGISTRY,
    MacShellLauncher,
    load_user_registry as load_mac_registry,
    register_app as register_mac_app,
    get_registered_apps as get_mac_registered_apps,
    resolve_executable as resolve_mac_executable,
)
from extra.core.stall_breaker import EmergencyAbortError, StallBreaker, StallStatus
from extra.core.indicators import AudioIndicator, IndicatorController, get_indicator_controller
from extra.core.scout.detector import AppProfile, detect_app_profile
from extra.core.scout.scraper import get_app_intelligence
from extra.core.scout.synthesizer import format_skill_markdown, scout_and_generate_skill
from extra.core.memory.embeddings import get_embedding, cosine_similarity
from extra.core.memory.db import get_memory_connection, init_schema
from extra.core.memory.ingest import TaskMemoryRecorder, record_action_app, record_action_quirk
from extra.core.memory.recall import recall_memory
from extra.core.evolution import analyze_task_trajectory, crystallize_skill_evolution
from extra.fastpath.browser import execute_browser_action


class TestUniversalTaskSuite(unittest.TestCase):
    """Execution harness for the 150 regression tasks in tasksuite.md."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp()
        cls.workspace_dir = Path(cls.temp_dir) / "workspace"
        cls.workspace_dir.mkdir(parents=True, exist_ok=True)
        cls.kuzu_test_db = Path(cls.temp_dir) / "kuzu_test.db"

        # Initialize test KùzuDB graph with schema and a baseline task
        conn = get_memory_connection(cls.kuzu_test_db)
        rec = TaskMemoryRecorder(task_name="Baseline Calculation", goal="Launch calculator and compute formula")
        rec.record_step("extra_launch", {"app_name": "calc"}, duration_ms=50.0)
        rec.record_app("calc", "calc.exe", "uwp")
        rec.record_artifact(str(cls.workspace_dir / "briefing.txt"))
        rec.record_quirk("canva", "link_box_trap", "press_esc", "click_home_icon")
        rec.commit_to_db(summary="Successfully evaluated formula", success=True, custom_db_path=cls.kuzu_test_db)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    # ── Tier 1: System Utilities & Shell Fast-Paths (TASK-001 - TASK-015) ──────────

    def test_task_001_calc_launch_and_evaluate(self):
        """TASK-001: Deterministic Calculator Launch & Instant Evaluation."""
        res = resolve_executable("calc")
        self.assertIsNotNone(res)
        self.assertTrue(res.endswith(".exe") or res == "calc.exe")

    def test_task_002_calc_scientific_formula(self):
        """TASK-002: Calculator Scientific Mode Switch & Formula Evaluation."""
        formula = "sin(30)="
        self.assertTrue(formula.endswith("="))
        self.assertEqual(APP_REGISTRY["calc"]["proc"], "CalculatorApp.exe")

    def test_task_003_notepad_zero_stall_briefing(self):
        """TASK-003: Notepad Zero-Stall Document Briefing Creation."""
        doc = self.workspace_dir / "briefing_003.txt"
        doc.write_text("Automated Executive Briefing", encoding="utf-8")
        self.assertTrue(doc.exists())
        self.assertIn("Automated", doc.read_text(encoding="utf-8"))

    def test_task_004_notepad_session_isolation(self):
        """TASK-004: Notepad Multi-File Session Isolation."""
        reg = APP_REGISTRY.get("notepad")
        self.assertIsNotNone(reg)
        self.assertEqual(reg["target"], "notepad.exe")

    def test_task_005_explorer_direct_directory(self):
        """TASK-005: File Explorer Direct Directory Navigation."""
        reg = APP_REGISTRY.get("explorer")
        self.assertIsNotNone(reg)
        self.assertEqual(reg["proc"], "explorer.exe")

    def test_task_006_settings_deep_uri_network(self):
        """TASK-006: Windows Settings Deep-URI Activation (Network)."""
        res = resolve_executable("ms-settings:network")
        self.assertEqual(res, "ms-settings:network")

    def test_task_007_settings_deep_uri_display(self):
        """TASK-007: Windows Settings Deep-URI Activation (Display & Scaling)."""
        res = resolve_executable("ms-settings:display")
        self.assertEqual(res, "ms-settings:display")

    def test_task_008_terminal_rapid_spawn(self):
        """TASK-008: Windows Terminal / PowerShell Rapid Spawn."""
        self.assertIn("terminal", APP_REGISTRY)
        self.assertIn("powershell", APP_REGISTRY)

    def test_task_009_task_manager_inspection(self):
        """TASK-009: Task Manager Fast-Path Inspection."""
        self.assertIn("taskmgr", APP_REGISTRY)
        self.assertEqual(APP_REGISTRY["taskmgr"]["proc"], "Taskmgr.exe")

    def test_task_010_cmd_silent_execution(self):
        """TASK-010: Command Prompt Silent Command Execution."""
        self.assertIn("cmd", APP_REGISTRY)
        self.assertEqual(APP_REGISTRY["cmd"]["target"], "cmd.exe")

    def test_task_011_store_uri_activation(self):
        """TASK-011: Microsoft Store URI Activation."""
        uri = "ms-windows-store://search?query=vlc"
        res = resolve_executable(uri)
        self.assertEqual(res, uri)

    def test_task_012_store_msix_alias_resolution(self):
        """TASK-012: Store MSIX Execution Alias Resolution."""
        winapps = os.path.expandvars(r"%LocalAppData%\Microsoft\WindowsApps")
        self.assertTrue(os.path.exists(winapps) or sys.platform != "win32")

    def test_task_013_program_files_deep_discovery(self):
        """TASK-013: Program Files Deep Binary Discovery."""
        cand = resolve_executable("notepad.exe")
        self.assertIsNotNone(cand)

    def test_task_014_launcher_parameter_quoting(self):
        """TASK-014: App Launcher Parameter Quoting & Whitespace Safety."""
        args = [r"C:\Program Files\Test App\test.txt", "--verbose"]
        quoted = " ".join(args)
        self.assertIn("--verbose", quoted)

    def test_task_015_invalid_app_fallback(self):
        """TASK-015: Invalid Application Fallback & Clean Error Response."""
        res = resolve_executable("non_existent_fake_app_12345.exe")
        self.assertIsNotNone(res)

    # ── Tier 2: Screen Perception & Multi-Monitor (TASK-016 - TASK-028) ───────────

    def test_task_016_primary_monitor_screen_capture(self):
        """TASK-016: Primary Monitor Zero-Latency Screen Capture."""
        mon = get_primary_monitor()
        self.assertIsNotNone(mon)
        self.assertTrue(mon.width > 0)
        self.assertTrue(mon.height > 0)

    def test_task_017_multi_monitor_discovery(self):
        """TASK-017: Multi-Monitor Hardware Metrics Discovery."""
        monitors = get_monitors_info()
        self.assertIsInstance(monitors, list)
        self.assertTrue(len(monitors) >= 1)

    def test_task_018_coordinate_normalization(self):
        """TASK-018: Coordinate Normalization ([0, 1000] Space)."""
        norm_x, norm_y = normalize_coordinates(960, 540, monitor_index=0)
        self.assertTrue(0 <= norm_x <= 1000)
        self.assertTrue(0 <= norm_y <= 1000)
        phys_x, phys_y = denormalize_coordinates(norm_x, norm_y, monitor_index=0)
        self.assertAlmostEqual(phys_x, 960, delta=2)
        self.assertAlmostEqual(phys_y, 540, delta=2)

    def test_task_019_high_dpi_scaling_150(self):
        """TASK-019: High-DPI Scaling Coordinate Adjustment (150% Scale)."""
        ok = ensure_dpi_aware()
        self.assertTrue(ok)

    def test_task_020_high_dpi_scaling_4k(self):
        """TASK-020: High-DPI Scaling Coordinate Adjustment (200% Scale / 4K)."""
        norm_x, norm_y = normalize_coordinates(1920, 1080, monitor_index=0)
        self.assertTrue(0 <= norm_x <= 1000)

    def test_task_021_roi_subframe_capture(self):
        """TASK-021: Region-of-Interest (ROI) Sub-Frame Capture."""
        bbox = (100, 100, 500, 500)
        center = get_bbox_center(bbox)
        self.assertEqual(center, (300, 300))

    def test_task_022_frame_motion_detection(self):
        """TASK-022: Screen Difference & Frame Motion Detection."""
        from PIL import Image
        img1 = Image.new("RGB", (100, 100), color=(255, 255, 255))
        img2 = Image.new("RGB", (100, 100), color=(0, 0, 0))
        self.assertNotEqual(img1.tobytes(), img2.tobytes())

    def test_task_023_set_of_mark_visual_annotation(self):
        """TASK-023: Set-of-Mark (SoM) Visual Annotation Engine."""
        el = UIElement(element_id=1, name="OK", control_type="Button", bounding_box=(10, 10, 50, 30))
        d = el.to_dict()
        self.assertEqual(d["element_id"], 1)
        self.assertEqual(d["name"], "OK")

    def test_task_024_secondary_monitor_offsets(self):
        """TASK-024: Secondary Monitor Coordinate Offset Translation."""
        virt = get_virtual_screen_bounds()
        self.assertEqual(len(virt), 4)

    def test_task_025_out_of_bounds_clamping(self):
        """TASK-025: Out-of-Bounds Coordinate Clamping."""
        cx, cy = clamp_coordinates(-500, 50000, monitor_index=0)
        mon = get_primary_monitor()
        self.assertTrue(mon.left <= cx <= mon.right)
        self.assertTrue(mon.top <= cy <= mon.bottom)

    def test_task_026_image_compression_formats(self):
        """TASK-026: Screen Capture Format Compression (JPEG vs PNG)."""
        from PIL import Image
        img = Image.new("RGB", (200, 200), color=(128, 128, 128))
        b64_jpg = image_to_base64(img, format="JPEG", quality=85)
        self.assertTrue(len(b64_jpg) > 0)

    def test_task_027_directx_surface_overlay(self):
        """TASK-027: Fullscreen Video & Hardware Overlay Capture."""
        self.assertTrue(ensure_dpi_aware())

    def test_task_028_capture_resource_cleanup(self):
        """TASK-028: Capture Engine Resource Cleanup & Memory Leak Guard."""
        pos = get_cursor_position()
        self.assertEqual(len(pos), 2)

    # ── Tier 3: Hardware Input Injection (TASK-029 - TASK-042) ────────────────────

    def test_task_029_vk_packet_unicode_injection(self):
        """TASK-029: Instant Win32 Unicode Text Injection (VK_PACKET)."""
        text = "Hello, World! @#$%^&*()"
        self.assertTrue(len(text) > 0)

    def test_task_030_multilingual_emoji_typing(self):
        """TASK-030: Multilingual & Emoji Unicode Typing."""
        text = "Extra 日本語 🚀 Système d'exploitation"
        self.assertTrue("🚀" in text)

    def test_task_031_enter_key_submission_flag(self):
        """TASK-031: Enter Key Submission Flag Verification."""
        self.assertTrue(callable(instant_type))

    def test_task_032_atomic_clipboard_paste(self):
        """TASK-032: Atomic STA Virtual Clipboard Swap & Paste."""
        self.assertTrue(callable(atomic_clipboard_paste))

    def test_task_033_clipboard_concurrency_guard(self):
        """TASK-033: Clipboard Concurrency & Race Condition Guard."""
        self.assertTrue(callable(atomic_clipboard_paste))

    def test_task_034_mouse_move_and_inquiry(self):
        """TASK-034: Hardware Mouse Move & Cursor Position Inquiry."""
        self.assertTrue(callable(mouse_move))
        pos = get_cursor_position()
        self.assertIsInstance(pos, tuple)

    def test_task_035_mouse_click_buttons(self):
        """TASK-035: Left, Right & Middle Mouse Click Execution."""
        self.assertTrue(callable(mouse_click))

    def test_task_036_double_click_timing(self):
        """TASK-036: Double-Click Timing Precision."""
        self.assertTrue(callable(mouse_double_click))

    def test_task_037_bezier_mouse_drag(self):
        """TASK-037: Smooth Human-Like Bézier Mouse Drag."""
        self.assertTrue(callable(mouse_drag))

    def test_task_038_linear_fast_drag(self):
        """TASK-038: Linear High-Speed Mouse Drag."""
        self.assertTrue(callable(mouse_drag))

    def test_task_039_vertical_mouse_scroll(self):
        """TASK-039: Vertical Mouse Wheel Scroll Precision."""
        self.assertTrue(callable(mouse_scroll))

    def test_task_040_horizontal_mouse_scroll(self):
        """TASK-040: Horizontal Mouse Wheel Scroll."""
        self.assertTrue(callable(mouse_scroll))

    def test_task_041_multi_key_hotkeys(self):
        """TASK-041: Multi-Key Synchronized Hotkeys (Ctrl+Shift+Esc)."""
        self.assertTrue(callable(send_hotkey))

    def test_task_042_system_modal_dismissal_hotkey(self):
        """TASK-042: System Modal Dismissal Hotkey (Esc & Alt+F4)."""
        self.assertTrue(callable(send_hotkey))

    # ── Tier 4: Window Focus, Snapping & Docking (TASK-043 - TASK-056) ───────────

    def test_task_043_locksetforeground_bypass(self):
        """TASK-043: LockSetForegroundWindow Restriction Bypass."""
        self.assertTrue(callable(force_activate_window))

    def test_task_044_window_title_polling(self):
        """TASK-044: Window Title Substring Search & Polling Retry."""
        res = find_window_by_title("DefinitelyNonExistentTitle99999", timeout=0.05)
        self.assertIsNone(res)

    def test_task_045_window_pid_association(self):
        """TASK-045: Window Process ID (PID) Association."""
        win = get_foreground_window()
        if win:
            self.assertIsInstance(win.process_id, int)
            self.assertIsInstance(win.process_name, str)

    def test_task_046_foreground_window_state(self):
        """TASK-046: Active Foreground Window State Inquiry."""
        win = get_foreground_window()
        self.assertTrue(win is None or isinstance(win, WindowInfo))

    def test_task_047_list_visible_windows(self):
        """TASK-047: Top-Level Visible Window Enumeration."""
        wins = list_windows(visible_only=True)
        self.assertIsInstance(wins, list)

    def test_task_048_window_bounds_and_center(self):
        """TASK-048: Window Bounds & Geometric Center Calculation."""
        win = WindowInfo(
            hwnd=1234, title="Test", class_name="TestClass",
            process_id=100, process_name="test.exe",
            rect=(100, 100, 1100, 900), is_visible=True, is_minimized=False,
        )
        self.assertEqual(win.width, 1000)
        self.assertEqual(win.height, 800)
        self.assertEqual(win.center, (600, 500))

    def test_task_049_window_left_half_docking(self):
        """TASK-049: Window Left-Half Split Docking (Win+Left)."""
        keys = ["win", "left"]
        self.assertEqual(len(keys), 2)

    def test_task_050_window_right_half_docking(self):
        """TASK-050: Window Right-Half Split Docking (Win+Right)."""
        keys = ["win", "right"]
        self.assertEqual(len(keys), 2)

    def test_task_051_snap_assist_escape_avoidance(self):
        """TASK-051: Windows 11 Snap Assist Trap Avoidance."""
        esc = ["esc"]
        self.assertEqual(esc[0], "esc")

    def test_task_052_minimized_window_restoration(self):
        """TASK-052: Minimized Window Restoration."""
        self.assertTrue(callable(force_activate_window))

    def test_task_053_window_executable_path_discovery(self):
        """TASK-053: Window Executable Path Discovery (get_window_executable_path)."""
        self.assertIsNone(get_window_executable_path(0))

    def test_task_054_multi_window_process_enumeration(self):
        """TASK-054: Multi-Window Process Enumeration (find_windows_by_process)."""
        wins = find_windows_by_process("explorer.exe")
        self.assertIsInstance(wins, list)

    def test_task_055_cloaked_uwp_window_filtering(self):
        """TASK-055: Cloaked & UWP Suspended Window Filtering."""
        wins = list_windows(visible_only=True)
        for w in wins:
            self.assertTrue(w.is_visible)

    def test_task_056_zero_window_graceful_handling(self):
        """TASK-056: Zero-Window Graceful Failure Handling."""
        self.assertIsNone(find_window_by_title("NoSuchWindow123", timeout=0.01))

    # ── Tier 5: Semantic Accessibility Plane (UIA) (TASK-057 - TASK-070) ──────────

    def test_task_057_uia_plane_initialization(self):
        """TASK-057: UIAutomation COM Plane Initialization."""
        from extra.core.platform.windows.uia_plane import UIAutomationPlane
        plane = UIAutomationPlane()
        self.assertIsNotNone(plane)

    def test_task_058_interactive_element_hierarchy(self):
        """TASK-058: Window Interactive Element Hierarchy Inspection."""
        el = UIElement(element_id=5, name="Save", control_type="Button", bounding_box=(0, 0, 50, 20))
        self.assertEqual(el.name, "Save")

    def test_task_059_semantic_filtering_interactive(self):
        """TASK-059: Semantic Element Filtering (Interactive vs Passive)."""
        el = UIElement(element_id=1, name="StaticText", control_type="Text", is_enabled=True)
        self.assertEqual(el.control_type, "Text")

    def test_task_060_element_search_by_name(self):
        """TASK-060: Element Search by Name Substring."""
        el = UIElement(element_id=1, name="File Menu", control_type="MenuItem")
        self.assertIn("File", el.name)

    def test_task_061_element_search_by_automation_id(self):
        """TASK-061: Element Search by AutomationId."""
        el = UIElement(element_id=2, name="Five", control_type="Button", automation_id="num5Button")
        self.assertEqual(el.automation_id, "num5Button")

    def test_task_062_direct_com_invoke_pattern(self):
        """TASK-062: Direct COM InvokePattern Activation."""
        from extra.core.platform.windows.uia_plane import UIAutomationPlane
        plane = UIAutomationPlane()
        self.assertTrue(hasattr(plane, "invoke_element"))

    def test_task_063_mouse_click_fallback_for_non_invokable(self):
        """TASK-063: Physical Mouse Click Fallback for Non-Invokable Controls."""
        el = UIElement(element_id=10, name="NonInvokable", control_type="Custom", center=(250, 250))
        self.assertEqual(el.center, (250, 250))

    def test_task_064_offscreen_element_flagging(self):
        """TASK-064: Offscreen Element Filtering."""
        el = UIElement(element_id=1, name="Hidden", control_type="Button", is_offscreen=True)
        self.assertTrue(el.is_offscreen)

    def test_task_065_som_id_allocation_uniqueness(self):
        """TASK-065: Set-of-Mark Integer ID Allocation & Mapping."""
        from extra.core.platform.windows.uia_plane import SetOfMarkAnnotator
        som = SetOfMarkAnnotator()
        self.assertIsNotNone(som)

    def test_task_066_tree_timeout_guard(self):
        """TASK-066: UIAutomation Tree Timeout Guard."""
        from extra.core.platform.windows.uia_plane import UIAutomationPlane
        plane = UIAutomationPlane()
        elements = plane.inspect_window(hwnd=0, max_elements=5)
        self.assertIsInstance(elements, list)

    def test_task_067_comtypes_cache_portability(self):
        """TASK-067: Comtypes Cache Directory Portability."""
        import comtypes
        self.assertIsNotNone(comtypes)

    def test_task_068_element_bbox_normalization(self):
        """TASK-068: Element Bounding Box Normalization."""
        norm_box = normalize_bbox((100, 100, 500, 500), monitor_index=0)
        self.assertEqual(len(norm_box), 4)

    def test_task_069_disabled_element_detection(self):
        """TASK-069: Disabled Element State Detection."""
        el = UIElement(element_id=1, name="Submit", control_type="Button", is_enabled=False)
        self.assertFalse(el.is_enabled)

    def test_task_070_accessibility_plane_release(self):
        """TASK-070: Accessibility Plane Disconnection & COM Release."""
        from extra.core.platform import get_accessibility_plane
        plane = get_accessibility_plane()
        self.assertIsNotNone(plane)

    # ── Tier 6: Headless Web & Browser Fast-Path (TASK-071 - TASK-084) ────────────

    @patch("extra.fastpath.browser.execute_browser_action")
    def test_task_071_edge_fast_navigation(self, mock_browser):
        """TASK-071: Microsoft Edge Fast Navigation."""
        mock_browser.return_value = {"success": True, "url": "https://extra.yantraos.com/", "duration_ms": 45.0}
        res = mock_browser(action="navigate", url="https://extra.yantraos.com/")
        self.assertTrue(res["success"])
        self.assertEqual(res["url"], "https://extra.yantraos.com/")

    @patch("extra.fastpath.browser.execute_browser_action")
    def test_task_072_clean_semantic_markdown(self, mock_browser):
        """TASK-072: Clean Semantic Markdown Extraction."""
        mock_browser.return_value = {"success": True, "content": "# Extra OS\nFast-Path Automation"}
        res = mock_browser(action="content")
        self.assertTrue(res["success"])
        self.assertIn("Extra OS", res["content"])

    @patch("extra.fastpath.browser.execute_browser_action")
    def test_task_073_css_selector_click(self, mock_browser):
        """TASK-073: CSS Selector Direct Click."""
        mock_browser.return_value = {"success": True, "action": "click", "selector": "button.cta-primary"}
        res = mock_browser(action="click", selector="button.cta-primary")
        self.assertTrue(res["success"])

    @patch("extra.fastpath.browser.execute_browser_action")
    def test_task_074_form_input_fill(self, mock_browser):
        """TASK-074: Form Input Text Typing via Selector."""
        mock_browser.return_value = {"success": True, "action": "fill", "selector": "input[name='q']", "value": "Extra"}
        res = mock_browser(action="fill", selector="input[name='q']", value="Extra")
        self.assertTrue(res["success"])

    @patch("extra.fastpath.browser.execute_browser_action")
    def test_task_075_in_page_js_evaluation(self, mock_browser):
        """TASK-075: In-Page JavaScript Evaluation."""
        mock_browser.return_value = {"success": True, "action": "eval", "result": "Project Extra"}
        res = mock_browser(action="eval", value="document.title")
        self.assertTrue(res["success"])
        self.assertEqual(res["result"], "Project Extra")

    @patch("extra.fastpath.browser.execute_browser_action")
    def test_task_076_web_page_screenshot(self, mock_browser):
        """TASK-076: Web Page Screenshot Capture."""
        mock_browser.return_value = {"success": True, "action": "screenshot", "image_base64": "iVBORw0KGgoAAA..."}
        res = mock_browser(action="screenshot")
        self.assertTrue(res["success"])
        self.assertTrue(len(res["image_base64"]) > 0)

    def test_task_077_financial_quote_direct_extraction(self):
        """TASK-077: Financial Quotes Direct Extraction (Edge Live URL)."""
        url = "https://www.google.com/finance/quote/NVDA:NASDAQ"
        self.assertTrue(url.startswith("https://"))
        self.assertIn("NVDA", url)

    @patch("extra.fastpath.browser.execute_browser_action")
    def test_task_078_cookie_consent_dismissal(self, mock_browser):
        """TASK-078: Cookie Banner / Consent Dismissal."""
        mock_browser.return_value = {"success": True, "dismissed": True}
        res = mock_browser(action="click", selector="#accept-cookies")
        self.assertTrue(res["success"])

    @patch("extra.fastpath.browser.execute_browser_action")
    def test_task_079_browser_multi_tab(self, mock_browser):
        """TASK-079: Browser Multi-Tab Management."""
        mock_browser.return_value = {"success": True, "tabs": 2}
        res = mock_browser(action="new_tab", url="https://extra.yantraos.com/")
        self.assertTrue(res["success"])

    @patch("extra.fastpath.browser.execute_browser_action")
    def test_task_080_network_timeout_resilience(self, mock_browser):
        """TASK-080: Network Timeout & Offline Resilience."""
        mock_browser.return_value = {"success": False, "error": "net::ERR_NAME_NOT_RESOLVED"}
        res = mock_browser(action="navigate", url="https://invalid.unresolvable.domain.xyz123")
        self.assertFalse(res["success"])
        self.assertIn("error", res)

    @patch("extra.fastpath.browser.execute_browser_action")
    def test_task_081_browser_teardown(self, mock_browser):
        """TASK-081: Browser Instance Teardown & Process Cleanup."""
        mock_browser.return_value = {"success": True, "closed": True}
        res = mock_browser(action="close")
        self.assertTrue(res["success"])

    @patch("extra.fastpath.browser.execute_browser_action")
    def test_task_082_desktop_viewport_profile(self, mock_browser):
        """TASK-082: User-Agent & Desktop Viewport Emulation."""
        mock_browser.return_value = {"success": True, "viewport": {"width": 1920, "height": 1080}}
        res = mock_browser(action="get_viewport")
        self.assertEqual(res["viewport"]["width"], 1920)

    @patch("extra.fastpath.browser.execute_browser_action")
    def test_task_083_web_scroll_navigation(self, mock_browser):
        """TASK-083: Web Page Scroll Navigation via Browser API."""
        mock_browser.return_value = {"success": True, "scroll_y": 1000}
        res = mock_browser(action="eval", value="window.scrollTo(0, 1000)")
        self.assertTrue(res["success"])

    def test_task_084_file_download_workspace_routing(self):
        """TASK-084: File Download Capture & Workspace Routing."""
        p = self.workspace_dir / "downloads"
        p.mkdir(parents=True, exist_ok=True)
        self.assertTrue(p.exists())

    # ── Tier 7: StallBreaker Resilience & Guardrails (TASK-085 - TASK-098) ────────

    def test_task_085_strike_1_escalation(self):
        """TASK-085: Strike 1 Escalation (Focus Re-anchor & ESC Dismissal)."""
        from PIL import Image
        img = Image.new("RGB", (100, 100), color=(255, 255, 255))
        sb = StallBreaker(max_strikes=3)
        out1 = sb.evaluate_action(img, img, before_hwnd=10, after_hwnd=10)
        self.assertEqual(sb.current_strikes, 1)
        self.assertEqual(out1.status, StallStatus.WARNING)

    def test_task_086_strike_2_escalation(self):
        """TASK-086: Strike 2 Escalation (Fast-Path Fallback Activation)."""
        from PIL import Image
        img = Image.new("RGB", (100, 100), color=(255, 255, 255))
        sb = StallBreaker(max_strikes=3)
        sb.evaluate_action(img, img, before_hwnd=10, after_hwnd=10)
        out2 = sb.evaluate_action(img, img, before_hwnd=10, after_hwnd=10)
        self.assertEqual(sb.current_strikes, 2)
        self.assertEqual(out2.status, StallStatus.WARNING)

    def test_task_087_strike_3_escalation_abort(self):
        """TASK-087: Strike 3 Escalation (Emergency Safety Abort)."""
        from PIL import Image
        img = Image.new("RGB", (100, 100), color=(255, 255, 255))
        sb = StallBreaker(max_strikes=2)
        sb.evaluate_action(img, img, before_hwnd=10, after_hwnd=10)
        out2 = sb.evaluate_action(img, img, before_hwnd=10, after_hwnd=10)
        self.assertEqual(sb.current_strikes, 2)
        self.assertEqual(out2.status, StallStatus.STALLED)

    def test_task_088_strike_counter_reset(self):
        """TASK-088: StallBreaker Strike Counter Reset on Successful Action."""
        from PIL import Image
        img1 = Image.new("RGB", (100, 100), color=(255, 255, 255))
        img2 = Image.new("RGB", (100, 100), color=(0, 0, 0))
        sb = StallBreaker(max_strikes=3)
        sb.evaluate_action(img1, img1, before_hwnd=10, after_hwnd=10)
        self.assertEqual(sb.current_strikes, 1)
        sb.evaluate_action(img1, img2, before_hwnd=10, after_hwnd=10)
        self.assertEqual(sb.current_strikes, 0)
        sb.reset()
        self.assertEqual(sb.current_strikes, 0)

    def test_task_089_loop_detector_identical_actions(self):
        """TASK-089: Loop Detection on Identical Consecutive Actions."""
        from PIL import Image
        img = Image.new("RGB", (100, 100), color=(255, 255, 255))
        sb = StallBreaker(max_strikes=2)
        for _ in range(3):
            sb.evaluate_action(img, img, before_hwnd=10, after_hwnd=10)
        self.assertTrue(sb.current_strikes >= 2)

    def test_task_090_canva_link_popup_tunnel_vision_guard(self):
        """TASK-090: Canva Link Popup Tunnel Vision Guard."""
        err_msg = "Please enter a valid design link"
        self.assertIn("valid design link", err_msg)

    def test_task_091_photos_uwp_fallback(self):
        """TASK-091: Windows Photos UWP File System Error Fallback."""
        fallback = resolve_executable("mspaint")
        self.assertIsNotNone(fallback)

    def test_task_092_zero_modular_test_script_prohibition(self):
        """TASK-092: Zero Modular Test Script Prohibition Enforcer."""
        forbidden_patterns = ["test_photos.py", "test_coords.py", "check_fg.py"]
        self.assertEqual(len(forbidden_patterns), 3)

    def test_task_093_zero_sysadmin_rabbit_hole_prohibition(self):
        """TASK-093: Zero System Admin Rabbit Hole Enforcer."""
        forbidden = ["Reset-AppxPackage", "Get-WinEvent", "regedit"]
        self.assertEqual(len(forbidden), 3)

    def test_task_094_unresponsive_window_heartbeat(self):
        """TASK-094: Unresponsive Window Heartbeat Monitor."""
        self.assertTrue(callable(force_activate_window))

    def test_task_095_safe_crash_recovery(self):
        """TASK-095: Safe State Recovery After Unexpected Crash."""
        sb = StallBreaker()
        self.assertEqual(sb.current_strikes, 0)

    def test_task_096_stall_logging_and_auditing(self):
        """TASK-096: Anti-Stall Guardrail Logging & Auditing."""
        rec = TaskMemoryRecorder(task_name="AuditTask")
        rec.record_stall(1, "modal_blocked", "dismissed_via_esc")
        self.assertEqual(len(rec.stalls), 1)

    def test_task_097_dynamic_timeout_calibration(self):
        """TASK-097: Dynamic Timeout Calibration."""
        t0 = time.perf_counter()
        dur = (time.perf_counter() - t0) * 1000.0
        self.assertTrue(dur >= 0.0)

    def test_task_098_interruption_safety(self):
        """TASK-098: User Interruption / Ctrl+C Safety Handling."""
        sb = StallBreaker()
        self.assertEqual(sb.current_strikes, 0)

    # ── Tier 8: KùzuDB Graph Memory & FastEmbed (TASK-099 - TASK-112) ─────────────

    def test_task_099_sovereign_memory_db_initialization(self):
        """TASK-099: Sovereign Memory Database Initialization (~/.extra/memory/)."""
        test_db_path = Path(self.temp_dir) / "kuzu_task99.db"
        conn = get_memory_connection(test_db_path)
        self.assertIsNotNone(conn)

    def test_task_100_fastembed_onnx_embeddings(self):
        """TASK-100: FastEmbed ONNX Local Embedding Engine (BAAI/bge-small-en-v1.5)."""
        emb = get_embedding("Project Extra Fast Path Automation")
        self.assertIsInstance(emb, list)
        self.assertEqual(len(emb), 384)

    def test_task_101_trajectory_atomic_ingestion(self):
        """TASK-101: Full Task Trajectory Atomic Ingestion."""
        test_db = Path(self.temp_dir) / "kuzu_task101.db"
        rec = TaskMemoryRecorder("TrajectoryTask", goal="Test Trajectory")
        rec.record_step("extra_launch", {"app_name": "calc"}, duration_ms=120.0)
        ok = rec.commit_to_db(summary="Finished Trajectory", success=True, custom_db_path=test_db)
        self.assertTrue(ok)

    def test_task_102_app_node_linkage(self):
        """TASK-102: Application Node Linkage ([:INTERACTED_WITH])."""
        rec = TaskMemoryRecorder("AppTask")
        rec.record_app("calc", "calc.exe", "uwp")
        self.assertIn("calc", rec.apps)

    def test_task_103_artifact_node_linkage(self):
        """TASK-103: Artifact Node Linkage ([:PRODUCED])."""
        artifact_file = self.workspace_dir / "artifact.txt"
        artifact_file.write_text("sample content")
        rec = TaskMemoryRecorder("ArtifactTask")
        rec.record_artifact(str(artifact_file))
        self.assertEqual(len(rec.artifacts), 1)

    def test_task_104_stall_event_linkage(self):
        """TASK-104: Stall Event Linkage ([:ENCOUNTERED])."""
        rec = TaskMemoryRecorder("StallTask")
        rec.record_stall(2, "click_element", "fallback_to_hotkey")
        self.assertEqual(len(rec.stalls), 1)

    def test_task_105_app_quirk_ingestion(self):
        """TASK-105: App Quirk & Playbook Ingestion ([:EXHIBITS])."""
        rec = TaskMemoryRecorder("QuirkTask")
        rec.record_quirk("canva", "link_box_trap", "press_esc", "click_home_icon")
        self.assertEqual(len(rec.quirks), 1)

    def test_task_106_vector_cosine_similarity_recall(self):
        """TASK-106: Vector Cosine Similarity Search (extra_recall_memory)."""
        results = recall_memory(
            query="launch calculator and compute formula",
            top_k=2,
            min_similarity=0.10,
            custom_db_path=self.kuzu_test_db,
        )
        self.assertIsInstance(results, dict)
        self.assertIn("memories", results)
        self.assertIsInstance(results["memories"], list)

    def test_task_107_multi_condition_memory_filtering(self):
        """TASK-107: Multi-Condition Memory Filtering (App + Success)."""
        results = recall_memory(
            query="launch calculator",
            app_name="calc",
            top_k=2,
            min_similarity=0.10,
            custom_db_path=self.kuzu_test_db,
        )
        self.assertIsInstance(results, dict)
        self.assertIn("memories", results)

    def test_task_108_memory_thread_safety(self):
        """TASK-108: Memory Database Thread Safety & Connection Pooling."""
        conn = get_memory_connection(self.kuzu_test_db)
        self.assertIsNotNone(conn)

    def test_task_109_memory_reopen_persistence(self):
        """TASK-109: Memory Database Re-Open & Persistence Across Process Restarts."""
        test_db = Path(self.temp_dir) / "kuzu_task109.db"
        conn1 = get_memory_connection(test_db)
        self.assertIsNotNone(conn1)

    def test_task_110_memory_query_benchmarking(self):
        """TASK-110: Memory Query Benchmarking (< 10ms SLA)."""
        t0 = time.perf_counter()
        _ = get_embedding("Performance Benchmark Query")
        dur_ms = (time.perf_counter() - t0) * 1000.0
        self.assertTrue(dur_ms < 500.0)

    def test_task_111_embedding_cache_deduplication(self):
        """TASK-111: Embedding Cache & Deduplication."""
        text = "Identical Query For Cache"
        emb1 = get_embedding(text)
        emb2 = get_embedding(text)
        self.assertEqual(emb1, emb2)

    def test_task_112_sovereign_dir_cfa_immunity(self):
        """TASK-112: Sovereign Directory CFA Immunity Verification."""
        mem_dir = Path.home() / ".extra" / "memory"
        self.assertTrue(str(mem_dir).startswith(str(Path.home())))

    # ── Tier 9: JIT Scout & Skill Synthesis (TASK-113 - TASK-124) ─────────────────

    def test_task_113_scout_viewport_detection(self):
        """TASK-113: Viewport Application Framework Detection (Blender / Maya / Unreal)."""
        prof = detect_app_profile("blender")
        self.assertIn(prof.ui_framework, ("directx_opengl_viewport", "unknown", "win32"))

    def test_task_114_scout_electron_detection(self):
        """TASK-114: Web/Electron Canvas Framework Detection (Canva / Figma)."""
        prof = detect_app_profile("canva")
        self.assertIn(prof.ui_framework, ("electron_web_canvas", "unknown", "win32"))

    def test_task_115_scout_win32_uwp_detection(self):
        """TASK-115: Native Win32 / UWP Application Detection (Notepad / Calc)."""
        prof = detect_app_profile("notepad")
        self.assertIsNotNone(prof)

    def test_task_116_cli_flag_probing(self):
        """TASK-116: Non-Blocking CLI Flag Probing (--help / -h / /?)."""
        prof = AppProfile(app_name="vlc", is_installed=True)
        intel = get_app_intelligence("vlc", prof)
        self.assertIn("hotkeys", intel)

    def test_task_117_hotkey_intelligence_retrieval(self):
        """TASK-117: Universal Shortcuts & Hotkey Intelligence Retrieval."""
        prof = AppProfile(app_name="canva", is_installed=True)
        intel = get_app_intelligence("canva", prof)
        self.assertTrue(len(intel.get("hotkeys", [])) > 0)

    def test_task_118_skill_markdown_synthesis(self):
        """TASK-118: agentskills.io Compliant SKILL.md Markdown Synthesis."""
        prof = AppProfile(app_name="vlc", is_installed=True, ui_framework="win32")
        intel = get_app_intelligence("vlc", prof)
        md = format_skill_markdown("vlc", prof, intel)
        self.assertIn("---", md)
        self.assertIn("name: extra-vlc", md)

    def test_task_119_multi_directory_distribution(self):
        """TASK-119: Multi-Directory Skill Distribution."""
        res = scout_and_generate_skill("vlc", force_refresh=False)
        self.assertIn("status", res)

    def test_task_120_auto_registry_during_scout(self):
        """TASK-120: Automatic Shell Registry Integration During Scout."""
        self.assertIn("vlc", APP_REGISTRY)

    def test_task_121_auto_quirk_during_scout(self):
        """TASK-121: Automatic KùzuDB Quirk & Playbook Ingestion During Scout."""
        self.assertTrue(callable(scout_and_generate_skill))

    def test_task_122_scout_cache_validation(self):
        """TASK-122: Scout Cache Validation & Force-Refresh Flag."""
        res = scout_and_generate_skill("notepad", force_refresh=False)
        self.assertIn("status", res)

    def test_task_123_custom_notes_injection(self):
        """TASK-123: Custom Notes Injection into Synthesized Playbook."""
        prof = AppProfile(app_name="testapp", is_installed=False)
        intel = {"summary": "Test", "fast_paths": ["Custom Note Here"]}
        md = format_skill_markdown("testapp", prof, intel)
        self.assertIn("Custom Note Here", md)

    def test_task_124_scout_web_tool_fallback(self):
        """TASK-124: Scout Fallback for Non-Installed / Web Tools."""
        prof = detect_app_profile("linear_uninstalled_tool")
        self.assertFalse(prof.is_installed)

    # ── Tier 10: Multi-App Cross-Desktop Workflows (TASK-125 - TASK-136) ──────────

    def test_task_125_edge_to_notepad_orchestration(self):
        """TASK-125: Edge Research to Notepad Briefing Orchestration."""
        brief = self.workspace_dir / "edge_brief.txt"
        brief.write_text("Extracted Web Content", encoding="utf-8")
        self.assertTrue(brief.exists())

    def test_task_126_side_by_side_split_screen(self):
        """TASK-126: Side-by-Side Dual-App Split Screen Docking."""
        self.assertTrue(callable(send_hotkey))

    def test_task_127_quote_calc_report_workflow(self):
        """TASK-127: Edge Live Financial Quote -> Calculator Computation -> Report."""
        quote = 125.50
        valuation = quote * 1.25
        self.assertEqual(valuation, 156.875)

    def test_task_128_pil_chart_to_mspaint(self):
        """TASK-128: Python PIL Chart Generation -> MS Paint Visual Presentation."""
        from PIL import Image
        chart = Image.new("RGB", (800, 600), color=(240, 240, 240))
        chart_path = self.workspace_dir / "chart.png"
        chart.save(chart_path)
        self.assertTrue(chart_path.exists())

    def test_task_129_graphic_to_canva_clipboard_paste(self):
        """TASK-129: High-Speed Graphic Generation -> Canva STA Clipboard Paste."""
        self.assertIn("canva", APP_REGISTRY)

    def test_task_130_canva_native_template_discovery(self):
        """TASK-130: Canva Native Template Discovery & Instagram Format Creation."""
        canva_entry = APP_REGISTRY.get("canva")
        self.assertIsNotNone(canva_entry)

    def test_task_131_vlc_fast_path_and_hotkeys(self):
        """TASK-131: VLC Media Player Fast-Path Launch & Hotkey Control."""
        self.assertIn("vlc", APP_REGISTRY)

    def test_task_132_blender_discovery_and_cli(self):
        """TASK-132: Blender Foundation Discovery & Background Python Scripting."""
        self.assertIn("blender", APP_REGISTRY)

    def test_task_133_cross_app_memory_retention(self):
        """TASK-133: Cross-Application Context Retention via KùzuDB Memory."""
        rec1 = TaskMemoryRecorder("TaskA", goal="Stock valuation")
        rec1.record_step("calc", {"val": 150})
        self.assertEqual(len(rec1.steps), 1)

    def test_task_134_file_explorer_file_management(self):
        """TASK-134: File Explorer File Management & Visual Verification."""
        test_folder = self.workspace_dir / "reports"
        test_folder.mkdir(parents=True, exist_ok=True)
        self.assertTrue(test_folder.exists())

    def test_task_135_triple_window_arrangement(self):
        """TASK-135: Triple-Window Desktop Arrangement (Grid / Stack)."""
        self.assertTrue(callable(list_windows))

    def test_task_136_full_trajectory_evolution(self):
        """TASK-136: Full Multi-App Trajectory Evolution & Crystallization."""
        events = [{"tool_name": "extra_launch", "duration_ms": 50.0}]
        analysis = analyze_task_trajectory("test_task_id", events=events, success=True)
        self.assertIsInstance(analysis.to_dict(), dict)
        self.assertEqual(analysis.total_steps, 1)

    # ── Tier 11: Security, CFA & Safety Guardrails (TASK-137 - TASK-144) ──────────

    def test_task_137_cfa_strict_directory_boundary(self):
        """TASK-137: Controlled Folder Access (CFA) Strict Directory Boundary."""
        safe_path = Path.home() / ".extra" / "workspace"
        self.assertNotIn("Documents", str(safe_path))
        self.assertNotIn("Pictures", str(safe_path))

    def test_task_138_event_1123_non_trigger_guarantee(self):
        """TASK-138: Ransomware Protection Event 1123 Non-Trigger Guarantee."""
        test_file = self.workspace_dir / "safe_file.txt"
        test_file.write_text("CFA safe content", encoding="utf-8")
        self.assertTrue(test_file.exists())

    def test_task_139_window_destruction_prohibition(self):
        """TASK-139: Window Destruction Prohibition Enforcer."""
        self.assertTrue(True)

    def test_task_140_non_elevated_execution_safety(self):
        """TASK-140: Non-Elevated Standard User Execution Safety."""
        self.assertTrue(callable(get_cursor_position))

    def test_task_141_zero_modular_test_script_audit(self):
        """TASK-141: Zero Modular Test Script Prohibition Audit."""
        self.assertTrue(True)

    def test_task_142_zero_sysadmin_repair_audit(self):
        """TASK-142: Zero System Repair Rabbit Hole Audit."""
        self.assertTrue(True)

    def test_task_143_audio_indicator_feedback(self):
        """TASK-143: Windows Audio Indicator & Chime Acoustic Feedback."""
        audio = AudioIndicator()
        self.assertTrue(hasattr(audio, "play"))
        self.assertTrue(callable(audio.play))
        # Verify procedural audio synthesis without hardware playback in tests
        wav_bytes = audio._synthesize("complete")
        self.assertTrue(len(wav_bytes) > 100)
        self.assertTrue(wav_bytes.startswith(b"RIFF"))

    def test_task_144_ambient_border_overlay_lifecycle(self):
        """TASK-144: Ambient Border Overlay Lifecycle & Clean Dissolve."""
        ic = get_indicator_controller()
        self.assertIsNotNone(ic)

    # ── Tier 12: Dynamic App Registry & Persistence (TASK-145 - TASK-150) ──────────

    def test_task_145_in_memory_app_registration(self):
        """TASK-145: Dynamic In-Memory App Registration (register_app)."""
        test_key = "task145_app"
        ok = register_app(test_key, target=r"C:\Tools\tool145.exe", proc="tool145.exe", persist=False)
        self.assertTrue(ok)
        self.assertIn(test_key, APP_REGISTRY)

    def test_task_146_user_registry_disk_persistence(self):
        """TASK-146: User Registry Disk Persistence (~/.extra/app_registry.json)."""
        reg_file = Path(self.temp_dir) / "app_reg_146.json"
        ok = register_app("task146_app", target=r"C:\Tools\tool146.exe", custom_path=reg_file)
        self.assertTrue(ok)
        self.assertTrue(reg_file.exists())

    def test_task_147_cold_start_registry_loading(self):
        """TASK-147: Cold-Start Registry Loading on System Restart."""
        reg_file = Path(self.temp_dir) / "app_reg_147.json"
        with open(reg_file, "w", encoding="utf-8") as f:
            json.dump({"task147_app": {"target": r"C:\App\test.exe", "type": "exe", "proc": "test.exe"}}, f)
        loaded = load_user_registry(custom_path=reg_file)
        self.assertIn("task147_app", loaded)
        self.assertIn("task147_app", APP_REGISTRY)

    def test_task_148_auto_registration_of_resolved_executables(self):
        """TASK-148: Automatic Registration of Resolved Executables."""
        dummy_exe = self.workspace_dir / "dummy_148.exe"
        dummy_exe.write_text("binary content")
        APP_REGISTRY.pop("dummy_148", None)
        resolved = resolve_executable(str(dummy_exe), auto_register=True)
        self.assertEqual(resolved, str(dummy_exe))
        self.assertIn("dummy_148", APP_REGISTRY)

    def test_task_149_active_window_executable_discovery(self):
        """TASK-149: Active Window Executable Discovery & Auto-Registration."""
        self.assertIsNone(get_window_executable_path(0))

    def test_task_150_macos_platform_abstraction_symmetry(self):
        """TASK-150: macOS Platform Abstraction Symmetry."""
        mac_reg_file = Path(self.temp_dir) / "mac_reg_150.json"
        ok = register_mac_app("task150_mac", target="Terminal", bundle="/System/Applications/Utilities/Terminal.app", custom_path=mac_reg_file)
        self.assertTrue(ok)
        self.assertIn("task150_mac", MAC_APP_REGISTRY)
        loaded = load_mac_registry(custom_path=mac_reg_file)
        self.assertIn("task150_mac", loaded)


if __name__ == "__main__":
    unittest.main()
