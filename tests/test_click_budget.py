"""
Project Extra — Fast Click-Path Budget Tests (EXTRA_FORM_FILL_SPEED_RFC Step 6).

Asserts the fast profile on mocked capture/UIA planes only: jump move
instead of the human glide, zeroed reaction delays, capped fast distill,
and batch transcript marking. Never wall-clock asserts on live input.
"""

from __future__ import annotations

import time
import unittest
from typing import List, Optional
from unittest.mock import MagicMock, patch

from extra.core.distiller import UIDistiller
from extra.core.platform.base import AbstractAccessibilityPlane, UIElement
from extra.core.stall_breaker import StallStatus


def _rich_elements() -> List[UIElement]:
    elems = []
    for i, name in enumerate(("Save", "Cancel", "Name", "Email", "Notes")):
        ctype = "Button" if i < 2 else ("Edit" if i < 4 else "Text")
        elems.append(
            UIElement(
                element_id=100 + i,
                name=name,
                control_type=ctype,
                bounding_box=(10, 10 + i * 40, 210, 40 + i * 40),
                center=(110, 25 + i * 40),
            )
        )
    return elems


class RecordingPlane(AbstractAccessibilityPlane):
    """Mock plane that records inspect_window budgets and forbids vision fallback."""

    def __init__(self, elements: List[UIElement]) -> None:
        self._elements = elements
        self.inspect_calls: list[dict] = []

    def inspect_window(self, hwnd=None, interactive_only: bool = True, max_elements: int = 50):
        self.inspect_calls.append({"hwnd": hwnd, "interactive_only": interactive_only, "max_elements": max_elements})
        return self._elements

    def find_element(self, query, exact=False, interactive_only=True):
        return None

    def invoke_element(self, element_or_id) -> bool:
        return False


def _mocked_click_env(srv):
    """Enters mocked desktop planes for one extra_click call; returns controls."""
    mouse = patch.object(srv, "mouse_click")
    cap_image = MagicMock()
    cap_image.crop.return_value = MagicMock()
    cap = MagicMock()
    cap.width = 1366
    cap.height = 768
    cap.image = cap_image
    capture = patch.object(srv, "capture_screen", return_value=cap)
    fg = MagicMock()
    fg.hwnd = 4242
    fg.title = "Form Window"
    foreground = patch.object(srv, "get_foreground_window", return_value=fg)
    distill = patch.object(srv, "distill_screen", return_value=MagicMock(content="compact-ui"))
    outcome = MagicMock()
    outcome.status = StallStatus.NORMAL
    outcome.strikes = 0
    outcome.message = "changed"
    outcome.recommended_action = None
    breaker = MagicMock()
    breaker.evaluate_action.return_value = outcome
    stall = patch.object(srv, "_stall_breaker", breaker)
    sleeps: list[float] = []
    sleep = patch("time.sleep", side_effect=lambda s: sleeps.append(s))
    return mouse, capture, foreground, distill, stall, sleep, sleeps


class TestExtraClickFastProfile(unittest.TestCase):
    def test_fast_profile_uses_jump_and_capped_distill(self) -> None:
        from extra.mcp import server as srv

        mouse, capture, foreground, distill, stall, sleep, sleeps = _mocked_click_env(srv)
        with mouse as m, capture, foreground, distill as d, stall, sleep:
            t0 = time.perf_counter()
            res = srv.extra_click(x=500, y=300, profile="fast")
            dur_ms = (time.perf_counter() - t0) * 1000.0
        self.assertTrue(res["success"])
        self.assertEqual(res["profile"], "fast")
        self.assertFalse(m.call_args.kwargs.get("human_like", True))
        d.assert_called_once_with(format="compact", max_elements=25, interactive_only=True, fast=True)
        self.assertNotIn(0.08, sleeps)
        self.assertLess(dur_ms, 600.0, "mocked fast click must stay under the 600ms budget")

    def test_normal_profile_preserves_human_behavior(self) -> None:
        from extra.mcp import server as srv

        mouse, capture, foreground, distill, stall, sleep, sleeps = _mocked_click_env(srv)
        with mouse as m, capture, foreground, distill as d, stall, sleep:
            res = srv.extra_click(x=500, y=300)
        self.assertTrue(res["success"])
        self.assertEqual(res.get("profile"), "normal")
        self.assertTrue(m.call_args.kwargs.get("human_like", False))
        _, kwargs = d.call_args
        self.assertNotIn("fast", kwargs)
        self.assertIn(0.08, sleeps)


class TestBatchClickFastProfile(unittest.TestCase):
    def test_batch_fast_click_skips_glide_and_settle(self) -> None:
        from extra.core.platform.windows import input_engine as win

        with patch.object(win, "mouse_click") as m, patch(
            "extra.core.soul.gateman.wait_until_settled",
            return_value={"settled": True, "duration_ms": 1.0},
        ) as settle:
            from extra.core.input_engine import execute_batch_actions

            res = execute_batch_actions(
                [{"action": "click", "x": 10, "y": 20, "profile": "fast"}],
                auto_distill=False,
            )
        self.assertTrue(res["success"])
        item = res["executed"][0]
        self.assertEqual(item["profile"], "fast")
        # Jump path: else-branch relies on the False default, never the glide.
        self.assertFalse(m.call_args.kwargs.get("human_like", False))
        self.assertNotIn("settled", item)
        settle.assert_not_called()

    def test_batch_normal_click_keeps_settle(self) -> None:
        from extra.core.platform.windows import input_engine as win

        with patch.object(win, "mouse_click"), patch(
            "extra.core.soul.gateman.wait_until_settled",
            return_value={"settled": True, "duration_ms": 1.0},
        ) as settle:
            from extra.core.input_engine import execute_batch_actions

            res = execute_batch_actions([{"action": "click", "x": 10, "y": 20}], auto_distill=False)
        item = res["executed"][0]
        self.assertEqual(item.get("profile"), "normal")
        self.assertIn("settled", item)
        settle.assert_called()


class TestDistillerFastFlag(unittest.TestCase):
    def test_fast_caps_fetch_and_skips_vision(self) -> None:
        plane = RecordingPlane(_rich_elements())
        distiller = UIDistiller(plane=plane)
        win = MagicMock()
        win.title = "Form Window"
        win.process_name = "chrome.exe"
        win.hwnd = 777
        win.rect = None
        fg = MagicMock()
        fg.hwnd = 777
        with patch("extra.core.distiller.get_window_info", return_value=win), patch(
            "extra.core.distiller.get_foreground_window", return_value=fg
        ), patch("extra.core.soul.vision_parser.EdgeVisionParser") as vision:
            res = distiller.distill_window(hwnd=777, format="compact", max_elements=25, interactive_only=True, fast=True)
        self.assertEqual(plane.inspect_calls[-1]["max_elements"], 60)
        vision.assert_not_called()
        self.assertGreater(res.interactive_count, 0)

    def test_normal_keeps_full_fetch(self) -> None:
        plane = RecordingPlane(_rich_elements())
        distiller = UIDistiller(plane=plane)
        win = MagicMock()
        win.title = "Form Window"
        win.process_name = "chrome.exe"
        win.hwnd = 777
        win.rect = None
        fg = MagicMock()
        fg.hwnd = 777
        with patch("extra.core.distiller.get_window_info", return_value=win), patch(
            "extra.core.distiller.get_foreground_window", return_value=fg
        ), patch("extra.core.soul.vision_parser.EdgeVisionParser") as vision:
            distiller.distill_window(hwnd=777, format="compact", max_elements=25)
        self.assertEqual(plane.inspect_calls[-1]["max_elements"], 150)
        vision.assert_called()  # normal profile still runs work-surface detection


if __name__ == "__main__":
    unittest.main()
