"""
Project Extra — Microsoft UI Automation (UIA) v3 Semantic Plane
Direct COM layer over UIAutomationCore.dll providing sub-15ms
element inspection, BoundingRect resolution, InvokePattern activation,
and Set-of-Mark (SoM) visual badge overlays.
"""

from __future__ import annotations

import ctypes
from dataclasses import dataclass
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from PIL import Image, ImageDraw, ImageFont

from extra.core.focus import get_foreground_window, list_windows
from extra.core.geometry import attach_input_desktop, ensure_dpi_aware
from extra.core.input_engine import mouse_click

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

# Interactive controls that agents typically want to interact with
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

# UIA Pattern IDs
UIA_INVOKE_PATTERN_ID = 10000
UIA_TOGGLE_PATTERN_ID = 10015
UIA_VALUE_PATTERN_ID = 10002


@dataclass
class UIElement:
    """Represents an accessible UI element queried from UIAutomationCore.dll."""
    element_id: int
    name: str
    control_type: str
    automation_id: str
    class_name: str
    bounding_box: Tuple[int, int, int, int]  # (left, top, right, bottom)
    center: Tuple[int, int]
    is_enabled: bool
    is_offscreen: bool
    raw_element: Any = None

    @property
    def width(self) -> int:
        return self.bounding_box[2] - self.bounding_box[0]

    @property
    def height(self) -> int:
        return self.bounding_box[3] - self.bounding_box[1]

    def to_dict(self) -> Dict[str, Any]:
        """Serializes to JSON-safe dictionary for MCP agents."""
        return {
            "element_id": self.element_id,
            "name": self.name,
            "control_type": self.control_type,
            "automation_id": self.automation_id,
            "class_name": self.class_name,
            "bounding_box": list(self.bounding_box),
            "center": list(self.center),
            "is_enabled": self.is_enabled,
            "is_offscreen": self.is_offscreen,
        }


class UIAutomationPlane:
    """
    Direct COM wrapper over Microsoft UIAutomationCore.dll.
    Provides semantic UI inspection and direct invocation with sub-15ms speed.
    """

    def __init__(self) -> None:
        ensure_dpi_aware()
        attach_input_desktop()
        self._mod = None
        self._uia = None
        self._cond_true = None
        self._cached_elements: Dict[int, UIElement] = {}

    def _init_uia(self) -> None:
        if self._uia is None:
            import comtypes.client
            self._mod = comtypes.client.GetModule("UIAutomationCore.dll")
            self._uia = comtypes.client.CreateObject(self._mod.CUIAutomation)
            self._cond_true = self._uia.CreateTrueCondition()

    def inspect_window(
        self,
        hwnd: Optional[int] = None,
        max_depth: int = 4,
        interactive_only: bool = True,
        max_elements: int = 150,
    ) -> List[UIElement]:
        """
        Queries the UI Automation tree of a target window (or the active window / top windows).
        Uses native UIAutomation FindAll for sub-15ms batch retrieval.
        
        Args:
            hwnd: Optional window handle. If None, targets foreground window or all active windows.
            interactive_only: If True, filters for clickable/actionable elements.
            max_elements: Maximum number of elements to return.
            
        Returns:
            List of UIElement items with exact physical bounding boxes.
        """
        ensure_dpi_aware()
        attach_input_desktop()
        self._init_uia()

        target_roots = []
        if hwnd:
            try:
                elem = self._uia.ElementFromHandle(hwnd)
                if elem:
                    target_roots.append(elem)
            except Exception:
                pass
        else:
            try:
                root = self._uia.GetRootElement()
                top_children = root.FindAll(TREE_SCOPE_CHILDREN, self._cond_true)
                for i in range(top_children.Length):
                    target_roots.append(top_children.GetElement(i))
            except Exception:
                pass

        elements: List[UIElement] = []
        self._cached_elements.clear()

        for root_elem in target_roots:
            if len(elements) >= max_elements:
                break

            try:
                # Batch query all descendants in this root via single COM call
                raw_list = root_elem.FindAll(TREE_SCOPE_DESCENDANTS, self._cond_true)
                for i in range(raw_list.Length):
                    if len(elements) >= max_elements:
                        break

                    node = raw_list.GetElement(i)
                    try:
                        c_type_id = int(node.CurrentControlType)
                        c_type_name = CONTROL_TYPE_NAMES.get(c_type_id, "Unknown")
                        name = str(node.CurrentName or "").strip()
                        auto_id = str(node.CurrentAutomationId or "").strip()
                        class_name = str(node.CurrentClassName or "").strip()
                        rect = node.CurrentBoundingRectangle
                        is_enabled = bool(node.CurrentIsEnabled)
                        is_offscreen = bool(node.CurrentIsOffscreen)

                        left, top, right, bottom = int(rect.left), int(rect.top), int(rect.right), int(rect.bottom)
                        width = right - left
                        height = bottom - top

                        if width > 4 and height > 4 and not is_offscreen:
                            keep = True
                            if interactive_only:
                                keep = (c_type_name in INTERACTIVE_TYPES) or (bool(name) and c_type_name not in {"Pane", "Group", "Window"})

                            if keep:
                                elem_id = len(elements) + 1
                                center_x = (left + right) // 2
                                center_y = (top + bottom) // 2
                                ui_elem = UIElement(
                                    element_id=elem_id,
                                    name=name,
                                    control_type=c_type_name,
                                    automation_id=auto_id,
                                    class_name=class_name,
                                    bounding_box=(left, top, right, bottom),
                                    center=(center_x, center_y),
                                    is_enabled=is_enabled,
                                    is_offscreen=is_offscreen,
                                    raw_element=node,
                                )
                                elements.append(ui_elem)
                                self._cached_elements[elem_id] = ui_elem
                    except Exception:
                        continue
            except Exception:
                continue

        return elements

    def find_element_by_name(
        self, name_query: str, hwnd: Optional[int] = None, exact: bool = False
    ) -> Optional[UIElement]:
        """Finds an element matching a name query."""
        q = name_query.strip().lower()
        elements = self.inspect_window(hwnd=hwnd, interactive_only=False)
        for elem in elements:
            e_name = elem.name.lower()
            if exact and e_name == q:
                return elem
            elif not exact and q in e_name:
                return elem
        return None

    def invoke_element(self, element_or_id: UIElement | int) -> bool:
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
