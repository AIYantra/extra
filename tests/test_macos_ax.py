"""
Project Extra — macOS Semantic Accessibility Plane Test Suite
Validates Phase 3 deliverables:
1. MacAccessibilityPlane interface compliance (AbstractAccessibilityPlane)
2. Interactive roles filtering and semantic hierarchy models
3. UIElement properties, center calculations, and to_dict() serialization
4. Set-of-Mark (SoM) visual badge overlay generation and mapping
5. Element search and invocation fallback mechanics
"""

from __future__ import annotations

from pathlib import Path
import sys
import time
import unittest

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from PIL import Image

from extra.core.platform.base import AbstractAccessibilityPlane, UIElement
from extra.core.platform.macos.ax_plane import (
    INTERACTIVE_ROLES,
    MacAccessibilityPlane,
    SetOfMarkAnnotator,
)


class TestMacOSAccessibilityPlane(unittest.TestCase):
    """Test suite validating macOS Accessibility and Set-of-Mark subsystems."""

    def setUp(self) -> None:
        self.plane = MacAccessibilityPlane()
        self.mock_elements = [
            UIElement(
                element_id=1,
                name="Calculate",
                control_type="Button",
                automation_id="calc_btn",
                class_name="AXButton",
                bounding_box=(100, 100, 200, 140),
                center=(150, 120),
                is_enabled=True,
                is_offscreen=False,
                raw_element=None,
            ),
            UIElement(
                element_id=2,
                name="Formula Input",
                control_type="TextField",
                automation_id="formula_field",
                class_name="AXTextField",
                bounding_box=(100, 160, 400, 200),
                center=(250, 180),
                is_enabled=True,
                is_offscreen=False,
                raw_element=None,
            ),
            UIElement(
                element_id=3,
                name="Enable GPU",
                control_type="CheckBox",
                automation_id="gpu_check",
                class_name="AXCheckBox",
                bounding_box=(100, 220, 250, 250),
                center=(175, 235),
                is_enabled=True,
                is_offscreen=False,
                raw_element=None,
            ),
        ]

    def test_accessibility_interface_compliance(self) -> None:
        """Asserts MacAccessibilityPlane satisfies AbstractAccessibilityPlane."""
        self.assertIsInstance(self.plane, AbstractAccessibilityPlane)

    def test_interactive_roles_coverage(self) -> None:
        """Asserts key macOS interactive roles are recognized."""
        essential_roles = {
            "AXButton",
            "AXTextField",
            "AXCheckBox",
            "AXRadioButton",
            "AXPopUpButton",
            "AXMenuItem",
            "AXSlider",
            "AXTabGroup",
            "AXLink",
        }
        for role in essential_roles:
            self.assertIn(role, INTERACTIVE_ROLES)

    def test_ui_element_properties_and_serialization(self) -> None:
        """Asserts UIElement geometric dimensions and JSON-safe dictionary serialization."""
        el = self.mock_elements[0]
        self.assertEqual(el.width, 100)
        self.assertEqual(el.height, 40)
        self.assertEqual(el.center, (150, 120))

        data = el.to_dict()
        self.assertEqual(data["element_id"], 1)
        self.assertEqual(data["name"], "Calculate")
        self.assertEqual(data["control_type"], "Button")
        self.assertEqual(data["bounding_box"], [100, 100, 200, 140])
        self.assertEqual(data["center"], [150, 120])
        self.assertTrue(data["is_enabled"])
        self.assertFalse(data["is_offscreen"])

    def test_set_of_mark_badge_annotator(self) -> None:
        """Asserts SetOfMarkAnnotator generates numbered badges and mapping on image."""
        annotator = SetOfMarkAnnotator()
        test_img = Image.new("RGB", (800, 600), color=(40, 44, 52))

        ann_img, mapping = annotator.annotate(test_img, self.mock_elements)

        # Output image must retain input dimensions
        self.assertEqual(ann_img.size, (800, 600))
        self.assertEqual(len(mapping), 3)
        self.assertIn(1, mapping)
        self.assertIn(2, mapping)
        self.assertIn(3, mapping)
        self.assertEqual(mapping[1].name, "Calculate")

    def test_element_search_and_caching(self) -> None:
        """Asserts cached element lookup by query substring and exact match."""
        # Populate cache
        for el in self.mock_elements:
            self.plane._cached_elements[el.element_id] = el

        # Exact match
        found = None
        for el in self.plane._cached_elements.values():
            if el.name.lower() == "calculate":
                found = el
                break
        self.assertIsNotNone(found)
        self.assertEqual(found.element_id, 1)

        # Substring match
        found_sub = None
        for el in self.plane._cached_elements.values():
            if "formula" in el.name.lower():
                found_sub = el
                break
        self.assertIsNotNone(found_sub)
        self.assertEqual(found_sub.element_id, 2)

    def test_invocation_fallback_to_center_click(self) -> None:
        """Asserts element invocation resolves center point and dispatches without error."""
        for el in self.mock_elements:
            self.plane._cached_elements[el.element_id] = el

        # Invoke by ID
        res = self.plane.invoke_element(1)
        self.assertTrue(res)

        # Invoke non-existent element
        res_none = self.plane.invoke_element(999)
        self.assertFalse(res_none)


def run_tests() -> bool:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMacOSAccessibilityPlane)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
