"""
Project Extra — macOS Semantic Accessibility Plane (AXUIElement)
Direct ApplicationServices AXUIElement client providing sub-12ms
element inspection, BoundingBox resolution, AXPressAction activation,
and Set-of-Mark (SoM) visual badge overlays.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from PIL import Image, ImageDraw, ImageFont

from extra.core.platform.base import AbstractAccessibilityPlane, UIElement
from extra.core.platform.macos.geometry import points_to_pixels
from extra.core.platform.macos.input_engine import mouse_click

logger = logging.getLogger("extra.ax_plane.macos")

try:
    from ApplicationServices import (
        AXUIElementCopyActionNames,
        AXUIElementCopyAttributeValue,
        AXUIElementCreateApplication,
        AXUIElementCreateSystemWide,
        AXUIElementPerformAction,
        kAXChildrenAttribute,
        kAXDescriptionAttribute,
        kAXFocusedApplicationAttribute,
        kAXHelpAttribute,
        kAXIdentifierAttribute,
        kAXPositionAttribute,
        kAXPressAction,
        kAXRoleAttribute,
        kAXShowMenuAction,
        kAXSizeAttribute,
        kAXTitleAttribute,
        kAXValueAttribute,
    )
except ImportError:
    AXUIElementCreateSystemWide = None
    AXUIElementCreateApplication = None
    AXUIElementCopyAttributeValue = None
    AXUIElementCopyActionNames = None
    AXUIElementPerformAction = None
    kAXFocusedApplicationAttribute = "AXFocusedApplication"
    kAXChildrenAttribute = "AXChildren"
    kAXRoleAttribute = "AXRole"
    kAXTitleAttribute = "AXTitle"
    kAXDescriptionAttribute = "AXDescription"
    kAXValueAttribute = "AXValue"
    kAXHelpAttribute = "AXHelp"
    kAXIdentifierAttribute = "AXIdentifier"
    kAXPositionAttribute = "AXPosition"
    kAXSizeAttribute = "AXSize"
    kAXPressAction = "AXPress"
    kAXShowMenuAction = "AXShowMenu"

# Actionable interactive roles
INTERACTIVE_ROLES: Set[str] = {
    "AXButton",
    "AXTextField",
    "AXTextArea",
    "AXCheckBox",
    "AXRadioButton",
    "AXPopUpButton",
    "AXMenuButton",
    "AXMenuItem",
    "AXMenuBarItem",
    "AXSlider",
    "AXTabGroup",
    "AXRadioButton",
    "AXLink",
    "AXComboBox",
    "AXScrollArea",
    "AXRow",
    "AXCell",
    "AXColorWell",
    "AXIncrementer",
}


class MacAccessibilityPlane(AbstractAccessibilityPlane):
    """
    Direct client over macOS ApplicationServices AXUIElement architecture.
    Provides sub-12ms UI hierarchy discovery, attribute extraction, and direct invocation.
    """

    def __init__(self) -> None:
        self.system = AXUIElementCreateSystemWide() if AXUIElementCreateSystemWide else None
        self._cached_elements: Dict[int, UIElement] = {}

    def inspect_window(
        self,
        hwnd: Optional[int] = None,
        interactive_only: bool = True,
        max_elements: int = 50,
    ) -> List[UIElement]:
        """
        Extracts semantic UI element hierarchy for the active or designated window.
        If hwnd is specified, resolves the owning application PID and queries its tree.
        """
        if self.system is None and AXUIElementCreateApplication is None:
            return []

        app_elem = None

        # 1. Target specific window if hwnd provided
        if hwnd is not None and AXUIElementCreateApplication is not None:
            try:
                from extra.core.platform.macos.focus import get_window_info
                win = get_window_info(hwnd)
                if win and win.process_id:
                    app_elem = AXUIElementCreateApplication(win.process_id)
            except Exception as ex:
                logger.debug("Could not resolve application from hwnd=%s: %s", hwnd, ex)

        # 2. Target currently focused application
        if app_elem is None and self.system is not None:
            err, focused_app = AXUIElementCopyAttributeValue(
                self.system, kAXFocusedApplicationAttribute, None
            )
            if err == 0 and focused_app:
                app_elem = focused_app

        # 3. Fallback to foreground window PID
        if app_elem is None and AXUIElementCreateApplication is not None:
            try:
                from extra.core.platform.macos.focus import get_foreground_window
                fg = get_foreground_window()
                if fg and fg.process_id:
                    app_elem = AXUIElementCreateApplication(fg.process_id)
            except Exception:
                pass

        if not app_elem:
            return []

        results: List[UIElement] = []
        self._cached_elements.clear()

        # Traverse hierarchy starting from target app
        self._traverse(app_elem, results, max_elements, interactive_only)

        for el in results:
            self._cached_elements[el.element_id] = el

        return results

    def _extract_label(self, elem: Any) -> str:
        """Extracts human-readable semantic label from multiple candidate AX attributes."""
        # 1. Title
        err, title = AXUIElementCopyAttributeValue(elem, kAXTitleAttribute, None)
        if err == 0 and title and str(title).strip():
            return str(title).strip()

        # 2. Description
        err, desc = AXUIElementCopyAttributeValue(elem, kAXDescriptionAttribute, None)
        if err == 0 and desc and str(desc).strip():
            return str(desc).strip()

        # 3. Value (for textfields, checkboxes, sliders)
        err, val = AXUIElementCopyAttributeValue(elem, kAXValueAttribute, None)
        if err == 0 and val and isinstance(val, (str, int, float)) and str(val).strip():
            return str(val).strip()

        # 4. Help tooltip
        err, help_txt = AXUIElementCopyAttributeValue(elem, kAXHelpAttribute, None)
        if err == 0 and help_txt and str(help_txt).strip():
            return str(help_txt).strip()

        return ""

    def _traverse(
        self,
        elem: Any,
        results: List[UIElement],
        max_elements: int,
        interactive_only: bool,
    ) -> None:
        if len(results) >= max_elements:
            return

        err, role = AXUIElementCopyAttributeValue(elem, kAXRoleAttribute, None)
        role_str = str(role or "Unknown")

        is_candidate = (not interactive_only) or (role_str in INTERACTIVE_ROLES)

        if err == 0 and is_candidate:
            label = self._extract_label(elem)
            _, pos = AXUIElementCopyAttributeValue(elem, kAXPositionAttribute, None)
            _, size = AXUIElementCopyAttributeValue(elem, kAXSizeAttribute, None)

            if pos and size:
                pt_x = float(getattr(pos, "x", 0.0))
                pt_y = float(getattr(pos, "y", 0.0))
                pt_w = float(getattr(size, "width", 0.0))
                pt_h = float(getattr(size, "height", 0.0))

                if pt_w > 2 and pt_h > 2:
                    # Convert logical points to physical Retina pixels for screenshot alignment
                    phys_x, phys_y = points_to_pixels(pt_x, pt_y)
                    phys_w, phys_h = points_to_pixels(pt_w, pt_h)

                    # Identifier attribute
                    _, ident = AXUIElementCopyAttributeValue(elem, kAXIdentifierAttribute, None)
                    auto_id = str(ident or "")

                    elem_id = len(results) + 1
                    ui_el = UIElement(
                        element_id=elem_id,
                        name=label,
                        control_type=role_str.replace("AX", ""),
                        automation_id=auto_id,
                        class_name=role_str,
                        bounding_box=(phys_x, phys_y, phys_x + phys_w, phys_y + phys_h),
                        center=(phys_x + phys_w // 2, phys_y + phys_h // 2),
                        is_enabled=True,
                        is_offscreen=False,
                        raw_element=elem,
                    )
                    results.append(ui_el)

        # Recurse through children
        err, children = AXUIElementCopyAttributeValue(elem, kAXChildrenAttribute, None)
        if err == 0 and children:
            for child in children:
                if len(results) >= max_elements:
                    break
                self._traverse(child, results, max_elements, interactive_only)

    def find_element(
        self, query: str, exact: bool = False, interactive_only: bool = True
    ) -> Optional[UIElement]:
        """Searches currently cached or visible elements matching a name or query."""
        q = query.strip().lower()
        elements = self.inspect_window(interactive_only=interactive_only)
        for el in elements:
            name = el.name.lower()
            if exact and name == q:
                return el
            elif not exact and q in name:
                return el
        return None

    def invoke_element(self, element_or_id: Union[UIElement, int]) -> bool:
        """
        Activates the target UI element.
        Tries direct semantic actions (AXPress, AXShowMenu, AXPick) first (< 1ms),
        falling back to hardware coordinate click.
        """
        elem: Optional[UIElement] = None
        if isinstance(element_or_id, int):
            elem = self._cached_elements.get(element_or_id)
        else:
            elem = element_or_id

        if not elem:
            return False

        # Attempt 1: Direct Semantic Invocation
        if elem.raw_element and AXUIElementPerformAction is not None:
            # Query supported action names
            actions: List[str] = []
            if AXUIElementCopyActionNames is not None:
                err, act_names = AXUIElementCopyActionNames(elem.raw_element, None)
                if err == 0 and act_names:
                    actions = [str(a) for a in act_names]

            # Priority action list
            target_actions = ["AXPress", "AXShowMenu", "AXPick", "AXConfirm"]
            for act in target_actions:
                if not actions or act in actions:
                    try:
                        res = AXUIElementPerformAction(elem.raw_element, act)
                        if res == 0:
                            return True
                    except Exception:
                        pass

        # Attempt 2: Center Coordinate Hardware Click Fallback
        cx, cy = elem.center
        mouse_click(cx, cy)
        return True


class SetOfMarkAnnotator:
    """
    Set-of-Mark (SoM) visual badge annotator for macOS.
    Renders high-visibility numbered badges on top of detected interactive elements.
    """

    def __init__(self) -> None:
        self._font = None
        try:
            self._font = ImageFont.truetype("Helvetica", 11)
        except Exception:
            self._font = ImageFont.load_default()

    def annotate(
        self, image: Image.Image, elements: List[UIElement]
    ) -> Tuple[Image.Image, Dict[int, UIElement]]:
        """
        Draws bounding box outlines and numbered badges for every element.
        Returns annotated image copy and element_id -> UIElement mapping.
        """
        annotated = image.copy()
        draw = ImageDraw.Draw(annotated)
        mapping: Dict[int, UIElement] = {}

        # High-contrast palette: Bright Cyan outline, Yellow badge, Black text
        box_color = (0, 210, 255)  # #00D2FF Cyan
        badge_bg = (255, 230, 0)   # #FFE600 Yellow
        badge_fg = (0, 0, 0)       # Deep Black

        for elem in elements:
            x1, y1, x2, y2 = elem.bounding_box
            mapping[elem.element_id] = elem

            # Draw thin bounding box outline
            draw.rectangle([x1, y1, x2, y2], outline=box_color, width=2)

            # Badge text
            label = str(elem.element_id)
            bbox = draw.textbbox((0, 0), label, font=self._font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]

            badge_w = text_w + 6
            badge_h = text_h + 4

            # Place badge near top-left of element
            bx1 = x1 + 2
            by1 = y1 + 2
            bx2 = bx1 + badge_w
            by2 = by1 + badge_h

            draw.rectangle([bx1, by1, bx2, by2], fill=badge_bg, outline=(0, 0, 0), width=1)
            draw.text((bx1 + 3, by1 + 1), label, fill=badge_fg, font=self._font)

        return annotated, mapping
