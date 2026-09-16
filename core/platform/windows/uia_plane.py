"""
Project Extra — Microsoft UI Automation (UIA) v3 Semantic Plane
Direct COM layer over UIAutomationCore.dll providing sub-15ms
element inspection, BoundingRect resolution, InvokePattern activation,
and Set-of-Mark (SoM) visual badge overlays.
"""

from __future__ import annotations

import ctypes
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from PIL import Image, ImageDraw, ImageFont

from extra.core.platform.base import AbstractAccessibilityPlane, UIElement
from extra.core.platform.windows.focus import get_foreground_window, list_windows
from extra.core.platform.windows.geometry import attach_input_desktop, ensure_dpi_aware
from extra.core.platform.windows.input_engine import mouse_click

# TreeScope Constants
TREE_SCOPE_ELEMENT = 1
TREE_SCOPE_CHILDREN = 2
TREE_SCOPE_DESCENDANTS = 4
TREE_SCOPE_SUBTREE = 7

# UI Automation Control Type IDs
UIA_BUTTON_ID = 50000
UIA_CALENDAR_ID = 50001
UIA_CHECKBOX_ID = 50002
UIA_COMBOBOX_ID = 50003
UIA_EDIT_ID = 50004
UIA_HYPERLINK_ID = 50005
UIA_IMAGE_ID = 50006
UIA_LIST_ITEM_ID = 50007
UIA_LIST_ID = 50008
UIA_MENU_ID = 50009
UIA_MENUBAR_ID = 50010
UIA_MENUITEM_ID = 50011
UIA_PROGRESSBAR_ID = 50012
UIA_RADIOBUTTON_ID = 50013
UIA_SCROLLBAR_ID = 50014
UIA_SLIDER_ID = 50015
UIA_SPINNER_ID = 50016
UIA_STATUSBAR_ID = 50017
UIA_TAB_ID = 50018
UIA_TABITEM_ID = 50019
UIA_TEXT_ID = 50020
UIA_TOOLBAR_ID = 50021
UIA_TOOLTIP_ID = 50022
UIA_TREE_ID = 50023
UIA_TREEITEM_ID = 50024
UIA_CUSTOM_ID = 50025
UIA_GROUP_ID = 50026
UIA_THUMB_ID = 50027
UIA_DATAGRID_ID = 50028
UIA_DATAITEM_ID = 50029
UIA_DOCUMENT_ID = 50030
UIA_SPLITBUTTON_ID = 50031
UIA_WINDOW_ID = 50032
UIA_PANE_ID = 50033
UIA_HEADER_ID = 50034
UIA_HEADERITEM_ID = 50035
UIA_TABLE_ID = 50036
UIA_TITLEBAR_ID = 50037
UIA_SEPARATOR_ID = 50038
UIA_SEMANTICZOOM_ID = 50039
UIA_APPBAR_ID = 50040

CONTROL_TYPE_NAMES: Dict[int, str] = {
    UIA_BUTTON_ID: "Button",
    UIA_CALENDAR_ID: "Calendar",
    UIA_CHECKBOX_ID: "CheckBox",
    UIA_COMBOBOX_ID: "ComboBox",
    UIA_EDIT_ID: "Edit",
    UIA_HYPERLINK_ID: "Hyperlink",
    UIA_IMAGE_ID: "Image",
    UIA_LIST_ITEM_ID: "ListItem",
    UIA_LIST_ID: "List",
    UIA_MENU_ID: "Menu",
    UIA_MENUBAR_ID: "MenuBar",
    UIA_MENUITEM_ID: "MenuItem",
    UIA_PROGRESSBAR_ID: "ProgressBar",
    UIA_RADIOBUTTON_ID: "RadioButton",
    UIA_SCROLLBAR_ID: "ScrollBar",
    UIA_SLIDER_ID: "Slider",
    UIA_SPINNER_ID: "Spinner",
    UIA_STATUSBAR_ID: "StatusBar",
    UIA_TAB_ID: "Tab",
    UIA_TABITEM_ID: "TabItem",
    UIA_TEXT_ID: "Text",
    UIA_TOOLBAR_ID: "ToolBar",
    UIA_TOOLTIP_ID: "ToolTip",
    UIA_TREE_ID: "Tree",
    UIA_TREEITEM_ID: "TreeItem",
    UIA_CUSTOM_ID: "Custom",
    UIA_GROUP_ID: "Group",
    UIA_THUMB_ID: "Thumb",
    UIA_DATAGRID_ID: "DataGrid",
    UIA_DATAITEM_ID: "DataItem",
    UIA_DOCUMENT_ID: "Document",
    UIA_SPLITBUTTON_ID: "SplitButton",
    UIA_WINDOW_ID: "Window",
    UIA_PANE_ID: "Pane",
    UIA_HEADER_ID: "Header",
    UIA_HEADERITEM_ID: "HeaderItem",
    UIA_TABLE_ID: "Table",
    UIA_TITLEBAR_ID: "TitleBar",
    UIA_SEPARATOR_ID: "Separator",
    UIA_SEMANTICZOOM_ID: "SemanticZoom",
    UIA_APPBAR_ID: "AppBar",
}

INTERACTIVE_TYPES: Set[str] = {
    "Button",
    "Edit",
    "Hyperlink",
    "CheckBox",
    "RadioButton",
    "ComboBox",
    "MenuItem",
    "TabItem",
    "ListItem",
    "SplitButton",
    "TreeItem",
    "Slider",
}

UIA_INVOKE_PATTERN_ID = 10000
UIA_TOGGLE_PATTERN_ID = 10015
UIA_VALUE_PATTERN_ID = 10002


class UIAutomationPlane(AbstractAccessibilityPlane):
    """
    Direct COM wrapper over Microsoft UIAutomationCore.dll.
    Provides semantic UI inspection and direct invocation with sub-15ms speed.
    """

    def __init__(self) -> None:
        ensure_dpi_aware()
        attach_input_desktop()
        self._automation = None
        self._condition_factory = None
        self._tree_walker = None
        self._cached_elements: Dict[int, UIElement] = {}
        self._init_com()

    def _init_com(self) -> None:
        """Initializes the CUIAutomation8 / CUIAutomation COM interface via comtypes."""
        try:
            import comtypes.client
            # Generate or load Microsoft UIAutomation TypeLib
            self._mod = comtypes.client.GetModule("UIAutomationCore.dll")
            try:
                # Prefer CUIAutomation8 (Windows 8+)
                self._automation = comtypes.client.CreateObject(
                    self._mod.CUIAutomation8, interface=self._mod.IUIAutomation
                )
            except Exception:
                # Fallback to CUIAutomation
                self._automation = comtypes.client.CreateObject(
                    self._mod.CUIAutomation, interface=self._mod.IUIAutomation
                )

            self._tree_walker = self._automation.ControlViewWalker
        except Exception as e:
            self._automation = None

    def inspect_window(
        self,
        hwnd: Optional[int] = None,
        interactive_only: bool = True,
        max_elements: int = 50,
    ) -> List[UIElement]:
        """
        Extracts semantic UI element hierarchy for the designated window.
        If hwnd is omitted, targets the currently active foreground window.
        """
        if self._automation is None:
            return []

        ensure_dpi_aware()
        attach_input_desktop()

        target_hwnd = hwnd
        if target_hwnd is None:
            fg = get_foreground_window()
            target_hwnd = fg.hwnd if fg else 0

        if not target_hwnd:
            return []

        elements: List[UIElement] = []
        self._cached_elements.clear()

        try:
            root_elem = self._automation.ElementFromHandle(target_hwnd)
            if not root_elem:
                return []

            # Create TrueCondition to walk descendants
            true_cond = self._automation.CreateTrueCondition()
            elem_array = root_elem.FindAll(TREE_SCOPE_DESCENDANTS, true_cond)

            if not elem_array:
                return []

            count = elem_array.Length
            curr_id = 1

            for i in range(count):
                if len(elements) >= max_elements:
                    break

                try:
                    elem = elem_array.GetElement(i)
                    c_type_id = elem.CurrentControlType
                    c_type_name = CONTROL_TYPE_NAMES.get(c_type_id, "Unknown")

                    if interactive_only and c_type_name not in INTERACTIVE_TYPES:
                        continue

                    # Check offscreen
                    if elem.CurrentIsOffscreen:
                        continue

                    # Bounding rectangle: (left, top, right, bottom)
                    rect = elem.CurrentBoundingRectangle
                    left = int(rect.left)
                    top = int(rect.top)
                    right = int(rect.right)
                    bottom = int(rect.bottom)
                    w = right - left
                    h = bottom - top

                    # Filter out degenerate or invisible rectangles
                    if w <= 2 or h <= 2:
                        continue

                    name = str(elem.CurrentName or "").strip()
                    auto_id = str(elem.CurrentAutomationId or "").strip()
                    class_name = str(elem.CurrentClassName or "").strip()
                    is_enabled = bool(elem.CurrentIsEnabled)

                    center = ((left + right) // 2, (top + bottom) // 2)

                    ui_el = UIElement(
                        element_id=curr_id,
                        name=name,
                        control_type=c_type_name,
                        automation_id=auto_id,
                        class_name=class_name,
                        bounding_box=(left, top, right, bottom),
                        center=center,
                        is_enabled=is_enabled,
                        is_offscreen=False,
                        raw_element=elem,
                    )
                    elements.append(ui_el)
                    self._cached_elements[curr_id] = ui_el
                    curr_id += 1
                except Exception:
                    continue

        except Exception:
            pass

        return elements

    def find_element(
        self, query: str, exact: bool = False, interactive_only: bool = True
    ) -> Optional[UIElement]:
        """Searches currently cached or visible elements matching a name or query."""
        q = query.strip().lower()
        elements = self.inspect_window(interactive_only=interactive_only)

        for elem in elements:
            e_name = elem.name.lower()
            if exact and e_name == q:
                return elem
            elif not exact and q in e_name:
                return elem
        return None

    def invoke_element(self, element_or_id: Union[UIElement, int]) -> bool:
        """
        Activates the target UI element.
        Tries direct COM InvokePattern first (< 1ms), falling back to physical mouse click.
        """
        elem: Optional[UIElement] = None
        if isinstance(element_or_id, int):
            elem = self._cached_elements.get(element_or_id)
        else:
            elem = element_or_id

        if elem is None:
            return False

        # Attempt 1: COM InvokePattern
        if elem.raw_element:
            try:
                pattern_ptr = elem.raw_element.GetCurrentPattern(UIA_INVOKE_PATTERN_ID)
                if pattern_ptr:
                    invoke_pat = pattern_ptr.QueryInterface(self._mod.IUIAutomationInvokePattern)
                    invoke_pat.Invoke()
                    return True
            except Exception:
                pass

            # Attempt 2: COM TogglePattern (for CheckBoxes/RadioButtons)
            try:
                pattern_ptr = elem.raw_element.GetCurrentPattern(UIA_TOGGLE_PATTERN_ID)
                if pattern_ptr:
                    toggle_pat = pattern_ptr.QueryInterface(self._mod.IUIAutomationTogglePattern)
                    toggle_pat.Toggle()
                    return True
            except Exception:
                pass

        # Attempt 3: Hardware Center Click fallback
        cx, cy = elem.center
        mouse_click(cx, cy)
        return True


class SetOfMarkAnnotator:
    """
    Set-of-Mark (SoM) visual annotator.
    Renders high-visibility numbered badges on top of detected interactive elements.
    """

    def __init__(self) -> None:
        self._font = None
        try:
            self._font = ImageFont.truetype("arial.ttf", 11)
        except Exception:
            self._font = ImageFont.load_default()

    def annotate(
        self, image: Image.Image, elements: List[UIElement]
    ) -> Tuple[Image.Image, Dict[int, UIElement]]:
        """
        Draws bounding box outlines and numbered badges for every element.
        Returns a copy of the annotated image and mapping of element_id -> UIElement.
        """
        annotated = image.copy()
        draw = ImageDraw.Draw(annotated)
        mapping: Dict[int, UIElement] = {}

        # Distinct high-contrast palette
        box_color = (0, 210, 255)  # Bright Cyan
        badge_bg = (255, 230, 0)   # High-vis Yellow
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
