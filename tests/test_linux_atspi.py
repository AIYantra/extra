"""
Project Extra — Linux Platform AT-SPI2 Accessibility Plane Unit Tests
Tests D-Bus connection, accessibility bus activation, role mapping normalization,
semantic UI hierarchy traversal, direct element invocation, and Set-of-Mark annotation.
"""

from __future__ import annotations

import sys
import unittest
from PIL import Image

if not sys.platform.startswith("linux"):
    raise unittest.SkipTest("Linux-specific AT-SPI2 tests skipped on non-Linux")

from extra.core.platform.base import AbstractAccessibilityPlane, UIElement
from extra.core.platform.linux.atspi_plane import (
    ATSPI_ROLE_MAP,
    INTERACTIVE_TYPES,
    LinuxAccessibilityPlane,
    SetOfMarkAnnotator,
    enable_accessibility_bus,
    get_atspi_bus_address,
)


class TestLinuxAccessibilityPlane(unittest.TestCase):
    """Exhaustive tests for Linux AT-SPI2 semantic accessibility plane."""

    def setUp(self) -> None:
        self.plane = LinuxAccessibilityPlane()
        self.annotator = SetOfMarkAnnotator()

    def tearDown(self) -> None:
        self.plane.close()

    def test_abstract_interface_conformance(self) -> None:
        """Verify LinuxAccessibilityPlane conforms to AbstractAccessibilityPlane."""
        self.assertIsInstance(self.plane, AbstractAccessibilityPlane)

    def test_enable_accessibility_bus(self) -> None:
        """Verify setting org.a11y.Status.IsEnabled succeeds or executes safely."""
        res = enable_accessibility_bus()
        self.assertIsInstance(res, bool)

    def test_atspi_bus_address_discovery(self) -> None:
        """Verify discovery of AT-SPI2 socket address."""
        addr = get_atspi_bus_address()
        # On modern Linux desktops with at-spi2-core installed, address is a unix socket
        if addr:
            self.assertTrue(addr.startswith("unix:path=") or "at-spi" in addr)

    def test_role_mapping_matrix(self) -> None:
        """Verify AT-SPI roles map to standardized Extra control types."""
        expected_mappings = {
            "push button": "Button",
            "push-button": "Button",
            "button": "Button",
            "toggle button": "Button",
            "check box": "CheckBox",
            "check-box": "CheckBox",
            "radio button": "RadioButton",
            "combo box": "ComboBox",
            "text": "Edit",
            "entry": "Edit",
            "menu item": "MenuItem",
            "page tab": "TabItem",
            "slider": "Slider",
            "spin button": "Spinner",
            "link": "Hyperlink",
            "window": "Window",
            "frame": "Window",
            "dialog": "Window",
        }
        for role, expected_type in expected_mappings.items():
            self.assertIn(role, ATSPI_ROLE_MAP)
            self.assertEqual(ATSPI_ROLE_MAP[role], expected_type)

    def test_interactive_types_classification(self) -> None:
        """Verify interactive types set contains actionable control classes."""
        self.assertIn("Button", INTERACTIVE_TYPES)
        self.assertIn("Edit", INTERACTIVE_TYPES)
        self.assertIn("CheckBox", INTERACTIVE_TYPES)
        self.assertIn("RadioButton", INTERACTIVE_TYPES)
        self.assertIn("ComboBox", INTERACTIVE_TYPES)
        self.assertIn("MenuItem", INTERACTIVE_TYPES)
        self.assertIn("TabItem", INTERACTIVE_TYPES)

    def test_inspect_window_traversal(self) -> None:
        """Test semantic hierarchy traversal on the live desktop."""
        elements = self.plane.inspect_window(interactive_only=True, max_elements=20)
        self.assertIsInstance(elements, list)
        for el in elements:
            self.assertIsInstance(el, UIElement)
            self.assertGreater(el.element_id, 0)
            self.assertIsInstance(el.name, str)
            self.assertIn(el.control_type, INTERACTIVE_TYPES)
            self.assertEqual(len(el.bounding_box), 4)
            self.assertEqual(len(el.center), 2)
            # Verify serialization
            d = el.to_dict()
            self.assertEqual(d["element_id"], el.element_id)
            self.assertEqual(d["control_type"], el.control_type)

    def test_find_element(self) -> None:
        """Test searching for accessible element by title or role."""
        elements = self.plane.inspect_window(interactive_only=True, max_elements=10)
        if elements:
            target = elements[0]
            # Exact find
            found = self.plane.find_element(target.name, exact=True)
            if found:
                self.assertEqual(found.element_id, target.element_id)
            # Substring find
            sub = target.name[:max(1, len(target.name) // 2)]
            found_sub = self.plane.find_element(sub, exact=False)
            self.assertIsNotNone(found_sub)

    def test_invoke_element_direct_or_fallback(self) -> None:
        """Test element invocation mechanism."""
        # Non-existent element returns False
        self.assertFalse(self.plane.invoke_element(999999))

        dummy = UIElement(
            element_id=888,
            name="TestMockButton",
            control_type="Button",
            bounding_box=(0, 0, 10, 10),
            center=(5, 5),
            raw_element=None,
        )
        # Fallback executes click at (5, 5) safely
        res = self.plane.invoke_element(dummy)
        self.assertTrue(res)

    def test_set_of_mark_annotator(self) -> None:
        """Verify Set-of-Mark visual annotation overlays."""
        img = Image.new("RGB", (640, 480), color=(50, 50, 50))
        elems = [
            UIElement(
                element_id=1,
                name="ButtonOne",
                control_type="Button",
                bounding_box=(50, 50, 150, 90),
                center=(100, 70),
            ),
            UIElement(
                element_id=2,
                name="InputTwo",
                control_type="Edit",
                bounding_box=(200, 50, 400, 90),
                center=(300, 70),
            ),
        ]
        annotated_img, mapping = self.annotator.annotate(img, elems)
        self.assertEqual(annotated_img.size, (640, 480))
        self.assertEqual(len(mapping), 2)
        self.assertIn(1, mapping)
        self.assertIn(2, mapping)


if __name__ == "__main__":
    unittest.main()
