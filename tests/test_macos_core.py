"""
Project Extra — End-to-End macOS Integration Test Suite
Simulates full autonomous computer use workflows on macOS:
1. Ambient Awareness Start (Pulse & Chime)
2. High-Speed Retina Perception (Capture & Normalization)
3. Semantic UI Inspection & Set-of-Mark Annotation
4. Hardware / Semantic Control Execution (Click, Type, Hotkey)
5. Window Focus Enforcement & Shell Fast-Path
6. Closed-Loop Safety & 2-Strike Stall Breaker Verification
7. Task Completion & Dissolve
"""

from __future__ import annotations

import io
import unittest
from unittest.mock import MagicMock, patch

from PIL import Image

from extra.core.platform.base import CaptureResult, UIElement, WindowInfo
from extra.core.platform.macos.ax_plane import MacAccessibilityPlane, SetOfMarkAnnotator
from extra.core.platform.macos.capture import ScreenCaptureEngine
from extra.core.platform.macos.focus import MacFocusManager
from extra.core.platform.macos.geometry import MacGeometry
from extra.core.platform.macos.indicators import IndicatorController
from extra.core.platform.macos.input_engine import MacInputEngine
from extra.core.platform.macos.shell import MacShellLauncher
from extra.core.stall_breaker import StallBreaker, StallStatus


class TestMacOSEndToEndIntegration(unittest.TestCase):
    """End-to-end integration testing for all Extra macOS submodules."""

    def setUp(self):
        self.geometry = MacGeometry()
        self.capture_engine = ScreenCaptureEngine()
        self.input_engine = MacInputEngine()
        self.ax_plane = MacAccessibilityPlane()
        self.focus_mgr = MacFocusManager()
        self.shell = MacShellLauncher()
        self.indicators = IndicatorController()
        self.stall_breaker = StallBreaker()

    def test_full_autonomous_loop_simulation(self):
        # ── Step 1: Ambient Awareness Start ──────────────────────────────────
        with patch.object(self.indicators.audio, "play") as mock_audio_play, patch.object(
            self.indicators.overlay, "show_active"
        ) as mock_overlay_show:
            self.indicators.task_start("Calculate compound interest")
            mock_audio_play.assert_called_with("start")
            mock_overlay_show.assert_called_once()

        # ── Step 2: Application Fast-Path Launch ─────────────────────────────
        with patch("extra.core.platform.macos.shell.subprocess.Popen") as mock_popen, patch(
            "extra.core.platform.macos.shell.list_windows"
        ) as mock_list_win:
            mock_list_win.return_value = [
                WindowInfo(
                    hwnd=901,
                    title="Calculator",
                    class_name="NSWindow",
                    process_id=3000,
                    process_name="Calculator",
                    rect=(100, 100, 400, 600),
                    is_visible=True,
                    is_minimized=False,
                )
            ]
            launch_res = self.shell.launch_app("calc", wait_for_window=True, timeout=0.5)
            self.assertTrue(launch_res.success)
            self.assertEqual(launch_res.hwnd, 901)
            mock_popen.assert_called_once_with(["open", "-a", "Calculator"])

        # ── Step 3: Screen Perception & Retina Normalization ─────────────────
        dummy_img = Image.new("RGB", (3456, 2234), color=(30, 30, 30))
        self.capture_engine.prefer_sck = True
        with patch("extra.core.platform.macos.capture.CG") as mock_cap_cg, patch.object(
            self.capture_engine, "_capture_screencapturekit", return_value=dummy_img
        ):
            mock_cap_cg.CGMainDisplayID.return_value = 1
            cap = self.capture_engine.capture(monitor_index=0)
            self.assertEqual(cap.width, 3456)
            self.assertEqual(cap.height, 2234)

            # Check Retina normalizer
            with patch("extra.core.platform.macos.geometry.get_monitors_info") as mock_mon_list:
                from extra.core.platform.base import MonitorInfo

                retina_mon = MonitorInfo(
                    index=0,
                    left=0,
                    top=0,
                    right=3456,
                    bottom=2234,
                    width=3456,
                    height=2234,
                    is_primary=True,
                    device_name="Built-in Retina Display",
                    dpi_x=144,
                    dpi_y=144,
                    scale_factor=2.0,
                )
                mock_mon_list.return_value = [retina_mon]
                norm_x, norm_y = self.geometry.normalize_coordinates(1728, 1117)
                self.assertEqual((norm_x, norm_y), (500, 500))

        # ── Step 4: Semantic UI Inspection & Set-of-Mark Annotation ──────────
        dummy_elements = [
            UIElement(
                element_id=1,
                name="7",
                control_type="AXButton",
                bounding_box=(200, 300, 260, 360),
                center=(230, 330),
            ),
            UIElement(
                element_id=2,
                name="*",
                control_type="AXButton",
                bounding_box=(280, 300, 340, 360),
                center=(310, 330),
            ),
            UIElement(
                element_id=3,
                name="9",
                control_type="AXButton",
                bounding_box=(200, 380, 260, 440),
                center=(230, 410),
            ),
        ]
        with patch.object(self.ax_plane, "inspect_active_window", return_value=dummy_elements):
            elems = self.ax_plane.inspect_active_window()
            self.assertEqual(len(elems), 3)
            self.assertEqual(elems[0].name, "7")

            # Annotate with Set-of-Mark badges
            annotator = SetOfMarkAnnotator()
            annotated_img, mark_map = annotator.annotate(cap.image, elems)
            self.assertEqual(len(mark_map), 3)
            self.assertEqual(mark_map[1].name, "7")

        # ── Step 5: Hardware & Unicode Input Injection ───────────────────────
        with patch("extra.core.platform.macos.input_engine.CG") as mock_input_cg:
            mock_input_cg.kCGHIDEventTap = 0
            mock_input_cg.kCGEventLeftMouseDown = 1
            mock_input_cg.kCGEventLeftMouseUp = 2
            mock_input_cg.kCGMouseEventClickState = 1

            # Click on button "7"
            self.input_engine.mouse_click(x=230, y=330)
            mock_input_cg.CGEventCreateMouseEvent.assert_called()
            mock_input_cg.CGEventPost.assert_called()

            # Instant type calculation
            self.input_engine.instant_type("42*8=")
            mock_input_cg.CGEventKeyboardSetUnicodeString.assert_called()

        # ── Step 6: Closed-Loop Stall Breaker Evaluation ─────────────────────
        after_img = Image.new("RGB", (3456, 2234), color=(50, 50, 50))
        with patch("extra.core.stall_breaker.get_cursor_position", return_value=(500, 500)):
            outcome = self.stall_breaker.evaluate_action(
                before_image=dummy_img,
                after_image=after_img,
                action_name="type calculation",
            )
            self.assertEqual(outcome.status, StallStatus.NORMAL)
            self.assertEqual(outcome.strikes, 0)
            self.assertGreater(outcome.pixel_diff, 0.0)

        # ── Step 7: Task Complete & Dissolve ─────────────────────────────────
        with patch.object(self.indicators.audio, "play") as mock_audio_play, patch.object(
            self.indicators.overlay, "show_complete"
        ) as mock_overlay_complete:
            self.indicators.task_complete("Calculation finished: 336", success=True, play_chime=True)
            mock_audio_play.assert_called_with("complete")
            mock_overlay_complete.assert_called_once()


if __name__ == "__main__":
    unittest.main()
