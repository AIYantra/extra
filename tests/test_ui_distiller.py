"""
Project Extra — Screen UI Distiller Test Suite
Validates the token-optimized semantic UI translation engine:
1. Pruning and deduplication of noisy container nodes.
2. Spatial sorting (top-to-bottom, left-to-right row banding).
3. Markdown, Compact, and JSON serialization modes.
4. Token estimation and savings metrics (> 85% savings vs screenshots).
5. Live desktop window distillation and MCP server exposure.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import List, Optional

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from extra.core.distiller import (
    DistillationResult,
    UIDistiller,
    distill_screen,
)
from extra.core.platform.base import AbstractAccessibilityPlane, UIElement


class MockAccessibilityPlane(AbstractAccessibilityPlane):
    """Mock accessibility plane returning predefined UIElement hierarchy."""

    def __init__(self, elements: List[UIElement]) -> None:
        self._mock_elements = elements

    def inspect_window(
        self,
        hwnd: Optional[int] = None,
        interactive_only: bool = False,
        max_elements: int = 50,
    ) -> List[UIElement]:
        return self._mock_elements

    def find_element(
        self, query: str, exact: bool = False, interactive_only: bool = True
    ) -> Optional[UIElement]:
        for el in self._mock_elements:
            if exact and el.name == query:
                return el
            elif not exact and query.lower() in el.name.lower():
                return el
        return None

    def invoke_element(self, element_or_id: Union[UIElement, int]) -> bool:
        return True

    def find_elements(
        self,
        name: Optional[str] = None,
        control_type: Optional[str] = None,
        automation_id: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> List[UIElement]:
        return self._mock_elements


def test_pruning_and_deduplication() -> None:
    print("[Test 1] Pruning, filtering, and deduplication...", end=" ")

    mock_elements = [
        # Valid button
        UIElement(
            element_id=1,
            name="Submit",
            control_type="Button",
            bounding_box=(100, 200, 180, 240),
            center=(140, 220),
        ),
        # Duplicate button wrapper with same center and name
        UIElement(
            element_id=2,
            name="Submit",
            control_type="Pane",
            bounding_box=(100, 200, 180, 240),
            center=(140, 220),
        ),
        # Degenerate zero-size element (should be dropped)
        UIElement(
            element_id=3,
            name="Invisible",
            control_type="Text",
            bounding_box=(10, 10, 10, 10),
            center=(10, 10),
        ),
        # Offscreen element (should be dropped)
        UIElement(
            element_id=4,
            name="Offscreen",
            control_type="Button",
            bounding_box=(-500, -500, -400, -450),
            center=(-450, -475),
            is_offscreen=True,
        ),
        # Unnamed container pane with no ID (should be dropped)
        UIElement(
            element_id=5,
            name="",
            control_type="Pane",
            bounding_box=(0, 0, 800, 600),
            center=(400, 300),
        ),
        # Valid text label
        UIElement(
            element_id=6,
            name="Result: 42",
            control_type="Text",
            bounding_box=(100, 50, 300, 80),
            center=(200, 65),
        ),
        # Valid input field
        UIElement(
            element_id=7,
            name="Username",
            control_type="Edit",
            bounding_box=(100, 120, 300, 150),
            center=(200, 135),
        ),
    ]

    distiller = UIDistiller(plane=MockAccessibilityPlane(mock_elements))
    pruned = distiller._prune_and_filter(mock_elements, interactive_only=False)

    # Expected retained: Submit (1), Result: 42 (6), Username (7) -> 3 elements
    assert len(pruned) == 3, f"Expected 3 retained elements, got {len(pruned)}"
    names = [el.name for el in pruned]
    assert "Submit" in names
    assert "Result: 42" in names
    assert "Username" in names
    print("PASSED")


def test_spatial_sorting() -> None:
    print("[Test 2] Spatial sorting (Top-to-Bottom, Left-to-Right row banding)...", end=" ")

    # Row 1: y ~ 100 (x=200, x=50)
    # Row 2: y ~ 250 (x=150, x=50)
    mock_elements = [
        UIElement(element_id=1, name="Row1_Right", control_type="Button", center=(200, 102), bounding_box=(180, 90, 220, 114)),
        UIElement(element_id=2, name="Row2_Right", control_type="Button", center=(150, 252), bounding_box=(130, 240, 170, 264)),
        UIElement(element_id=3, name="Row1_Left", control_type="Button", center=(50, 100), bounding_box=(30, 90, 70, 110)),
        UIElement(element_id=4, name="Row2_Left", control_type="Button", center=(50, 250), bounding_box=(30, 240, 70, 260)),
    ]

    distiller = UIDistiller(plane=MockAccessibilityPlane(mock_elements))
    sorted_els = distiller._spatial_sort(mock_elements)

    expected_order = ["Row1_Left", "Row1_Right", "Row2_Left", "Row2_Right"]
    actual_order = [el.name for el in sorted_els]
    assert actual_order == expected_order, f"Expected {expected_order}, got {actual_order}"
    print("PASSED")


def test_markdown_and_compact_formatting() -> None:
    print("[Test 3] Markdown and Compact formatting & Token metrics...", end=" ")

    mock_elements = [
        UIElement(element_id=1, name="Display: 120", control_type="Text", center=(150, 50), bounding_box=(50, 40, 250, 60)),
        UIElement(element_id=2, name="Search Query", control_type="Edit", center=(150, 100), bounding_box=(50, 90, 250, 110)),
        UIElement(element_id=3, name="OK", control_type="Button", center=(100, 200), bounding_box=(70, 185, 130, 215)),
        UIElement(element_id=4, name="Cancel", control_type="Button", center=(180, 200), bounding_box=(150, 185, 210, 215)),
    ]

    distiller = UIDistiller(plane=MockAccessibilityPlane(mock_elements))
    res_md = distiller.distill_window(hwnd=12345, format="markdown", include_coordinates=True)

    assert "### Window:" in res_md.content
    assert "Display: 120" in res_md.content
    assert "Search Query" in res_md.content
    assert "OK" in res_md.content
    assert "Cancel" in res_md.content
    assert res_md.element_count == 4
    assert res_md.interactive_count == 3  # Edit + 2 Buttons
    assert res_md.approx_tokens < 150
    assert res_md.token_savings_pct > 85.0

    # Compact format test
    res_compact = distiller.distill_window(hwnd=12345, format="compact", include_coordinates=True)
    assert "[WIN:" in res_compact.content
    assert "INFO:" in res_compact.content
    assert "ACTIONS:" in res_compact.content
    assert res_compact.approx_tokens < 100
    assert res_compact.token_savings_pct > 90.0

    # JSON format test
    res_json = distiller.distill_window(hwnd=12345, format="json", include_coordinates=True)
    parsed = json.loads(res_json.content)
    assert "window" in parsed
    assert len(parsed["controls"]) == 4

    print("PASSED")


def test_live_window_distillation() -> None:
    print("[Test 4] Live desktop distillation via default plane...", end=" ")

    res = distill_screen(format="markdown", max_elements=25)
    assert res.success if hasattr(res, "success") else True
    assert isinstance(res.content, str)
    assert len(res.content) > 0
    assert res.approx_tokens < 500
    assert res.token_savings_pct >= 65.0
    print(f"PASSED (Window: '{res.window_title}', Tokens: ~{res.approx_tokens}, Savings: {res.token_savings_pct}%)")


def test_mcp_tool_integration() -> None:
    print("[Test 5] MCP Server extra_translate_screen tool invocation...", end=" ")

    from extra.mcp.server import extra_translate_screen

    tool_res = extra_translate_screen(format="markdown", max_elements=20)
    assert tool_res["success"] is True
    assert "content" in tool_res
    assert "approx_tokens" in tool_res
    assert "token_savings_pct" in tool_res
    assert "elements" in tool_res
    print(f"PASSED (MCP Returned {tool_res['element_count']} controls, ~{tool_res['approx_tokens']} tokens)")


def test_zero_hop_perception_mcp() -> None:
    print("[Test 6] Zero-Hop Perception auto-distill in extra_screenshot, extra_type, extra_batch_actions...", end=" ")
    from extra.mcp.server import extra_screenshot, extra_type, extra_batch_actions

    # 1. Test screenshot auto_distill
    sc_res = extra_screenshot(save_to_file=False, auto_distill=True)
    assert "distilled_ui" in sc_res, "distilled_ui must be present in extra_screenshot response"
    assert isinstance(sc_res["distilled_ui"], str)

    # 2. Test type auto_distill
    type_res = extra_type(text="", auto_distill=True)
    assert type_res["success"] is True
    assert "distilled_ui" in type_res

    # 3. Test batch_actions auto_distill
    batch_res = extra_batch_actions(actions=[{"action": "sleep", "ms": 10}], auto_distill=True)
    assert batch_res["success"] is True
    assert "distilled_ui" in batch_res

    print("PASSED")


def run_all() -> None:
    print("=" * 65)
    print("  EXTRA PHASE 1: SCREEN UI DISTILLER VALIDATION SUITE")
    print("=" * 65)
    t0 = time.perf_counter()

    test_pruning_and_deduplication()
    test_spatial_sorting()
    test_markdown_and_compact_formatting()
    test_live_window_distillation()
    test_mcp_tool_integration()
    test_zero_hop_perception_mcp()

    elapsed = (time.perf_counter() - t0) * 1000.0
    print("=" * 65)
    print(f"  ALL 6 TESTS PASSED SUCCESSFULLY in {elapsed:.2f}ms")
    print("=" * 65)


if __name__ == "__main__":
    run_all()

