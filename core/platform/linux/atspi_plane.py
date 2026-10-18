"""
Project Extra — Linux Semantic Accessibility Plane (AT-SPI2 D-Bus)
Direct D-Bus client connecting to AT-SPI2 registry and application buses.
Provides sub-15ms semantic UI hierarchy inspection, bounding box resolution,
direct < 1ms DoAction invocation, and Set-of-Mark (SoM) visual badge overlays.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from PIL import Image, ImageDraw, ImageFont

from extra.core.platform.base import AbstractAccessibilityPlane, UIElement
from extra.core.platform.linux.geometry import ensure_dpi_aware
from extra.core.platform.linux.input_engine import mouse_click

logger = logging.getLogger("extra.atspi.linux")

# ── Jeepney D-Bus Setup ────────────────────────────────────────────────────────

try:
    from jeepney import DBusAddress, new_method_call
    from jeepney.io.blocking import DBusConnection, open_dbus_connection
    _JEEPNEY_AVAILABLE = True
except ImportError:
    DBusAddress = None
    new_method_call = None
    DBusConnection = None
    open_dbus_connection = None
    _JEEPNEY_AVAILABLE = False

# ── AT-SPI2 Role Mapping & Interactive Classification ──────────────────────────

ATSPI_ROLE_MAP: Dict[str, str] = {
    # Buttons
    "push button": "Button",
    "push-button": "Button",
    "button": "Button",
    "toggle button": "Button",
    "toggle-button": "Button",
    # Checks & Radios
    "check box": "CheckBox",
    "check-box": "CheckBox",
    "check menu item": "CheckBox",
    "check-menu-item": "CheckBox",
    "radio button": "RadioButton",
    "radio-button": "RadioButton",
    "radio menu item": "RadioButton",
    "radio-menu-item": "RadioButton",
    # Combos & Lists
    "combo box": "ComboBox",
    "combo-box": "ComboBox",
    "list item": "ListItem",
    "list-item": "ListItem",
    "list": "List",
    "list box": "List",
    "list-box": "List",
    # Text & Entries
    "text": "Edit",
    "entry": "Edit",
    "password text": "Edit",
    "password-text": "Edit",
    "editbar": "Edit",
    # Menus
    "menu item": "MenuItem",
    "menu-item": "MenuItem",
    "tearoff menu item": "MenuItem",
    "tearoff-menu-item": "MenuItem",
    "menu": "Menu",
    "menu bar": "MenuBar",
    "menu-bar": "MenuBar",
    # Tabs
    "page tab": "TabItem",
    "page-tab": "TabItem",
    "page tab list": "Tab",
    "page-tab-list": "Tab",
    # Trees
    "tree item": "TreeItem",
    "tree-item": "TreeItem",
    "tree": "Tree",
    "tree table": "Tree",
    "tree-table": "Tree",
    # Controls
    "slider": "Slider",
    "spin button": "Spinner",
    "spin-button": "Spinner",
    "link": "Hyperlink",
    "progress bar": "ProgressBar",
    "progress-bar": "ProgressBar",
    "level bar": "ProgressBar",
    "level-bar": "ProgressBar",
    "scroll bar": "ScrollBar",
    "scroll-bar": "ScrollBar",
    # Content & Windows
    "label": "Text",
    "heading": "Text",
    "paragraph": "Text",
    "caption": "Text",
    "image": "Image",
    "icon": "Image",
    "window": "Window",
    "frame": "Window",
    "dialog": "Window",
    "internal frame": "Window",
    "internal-frame": "Window",
    "panel": "Pane",
    "page": "Pane",
    "section": "Pane",
    "tool bar": "ToolBar",
    "tool-bar": "ToolBar",
    "status bar": "StatusBar",
    "status-bar": "StatusBar",
    "tool tip": "ToolTip",
    "tool-tip": "ToolTip",
    "table": "Table",
    "table cell": "TableCell",
    "table-cell": "TableCell",
    "header": "Header",
    "footer": "Footer",
    "terminal": "Terminal",
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
    "TreeItem",
    "Slider",
    "Spinner",
}

# ATSPI Coordination Constants
ATSPI_COORD_TYPE_SCREEN = 0
ATSPI_COORD_TYPE_WINDOW = 1

# ATSPI State Bitmasks
STATE_ENABLED = 1 << 1
STATE_SENSITIVE = 1 << 2
STATE_ACTIVE = 1 << 3
STATE_FOCUSABLE = 1 << 10
STATE_FOCUSED = 1 << 11
STATE_SHOWING = 1 << 23
STATE_VISIBLE = 1 << 24
STATE_DEFUNCT = 1 << 25


def get_atspi_bus_address() -> Optional[str]:
    """
    Discovers the active AT-SPI2 accessibility D-Bus socket address.
    1. Checks $AT_SPI_BUS_ADDRESS environment variable.
    2. Checks standard user socket at /run/user/<uid>/at-spi/bus_0.
    3. Queries org.a11y.Bus /org/a11y/bus org.a11y.Bus.GetAddress via user session bus.
    """
    env_addr = os.environ.get("AT_SPI_BUS_ADDRESS")
    if env_addr:
        return env_addr

    uid = os.getuid()
    sock_path = f"/run/user/{uid}/at-spi/bus_0"
    if os.path.exists(sock_path):
        return f"unix:path={sock_path}"

    if shutil.which("busctl"):
        try:
            out = subprocess.check_output(
                ["busctl", "--user", "call", "org.a11y.Bus", "/org/a11y/bus", "org.a11y.Bus", "GetAddress"],
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=0.5,
            )
            for token in out.split():
                if token.startswith('"unix:') and token.endswith('"'):
                    return token.strip('"')
                elif token.startswith('unix:'):
                    return token.strip('"\n\r')
        except Exception:
            pass

    return None


def enable_accessibility_bus() -> bool:
    """
    Activates Chromium, Electron, Qt, and GTK accessibility tree publication
    by setting org.a11y.Status.IsEnabled = true on the user session bus.
    """
    os.environ["ACCESSIBILITY_ENABLED"] = "1"
    os.environ["GNOME_ACCESSIBILITY"] = "1"
    os.environ["QT_ACCESSIBILITY"] = "1"

    if shutil.which("busctl"):
        try:
            res = subprocess.run(
                [
                    "busctl",
                    "--user",
                    "set-property",
                    "org.a11y.Bus",
                    "/org/a11y/bus",
                    "org.a11y.Status",
                    "IsEnabled",
                    "b",
                    "true",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=0.5,
            )
            return res.returncode == 0
        except Exception:
            pass
    return False


# ── LinuxAccessibilityPlane Implementation ─────────────────────────────────────

class LinuxAccessibilityPlane(AbstractAccessibilityPlane):
    """
    Linux implementation of AbstractAccessibilityPlane using AT-SPI2 D-Bus.
    Provides sub-15ms UI hierarchy inspection, bounding box resolution,
    and direct < 1ms DoAction invocation without hardware mouse clicks.
    """

    def __init__(self) -> None:
        ensure_dpi_aware()
        self._cached_elements: Dict[int, UIElement] = {}
        self._element_counter: int = 1
        self._bus_conn: Optional[Any] = None
        self._bus_address: Optional[str] = None
        enable_accessibility_bus()

    def _get_connection(self) -> Optional[Any]:
        """Retrieves or establishes a resilient D-Bus connection to the AT-SPI bus."""
        if not _JEEPNEY_AVAILABLE:
            return None

        if self._bus_conn is not None:
            return self._bus_conn

        self._bus_address = get_atspi_bus_address()
        if not self._bus_address:
            logger.debug("AT-SPI bus address not discovered.")
            return None

        try:
            conn = open_dbus_connection(self._bus_address)
            if hasattr(conn, "sock") and conn.sock:
                conn.sock.settimeout(0.35)
            self._bus_conn = conn
            return self._bus_conn
        except Exception as ex:
            logger.debug("Failed connecting to AT-SPI bus (%s): %s", self._bus_address, ex)
            self._bus_conn = None
            return None

    def _close_connection(self) -> None:
        """Closes the active D-Bus connection."""
        if self._bus_conn is not None:
            try:
                self._bus_conn.close()
            except Exception:
                pass
            self._bus_conn = None

    def close(self) -> None:
        """Explicitly releases accessibility resources and closes D-Bus connection."""
        self._close_connection()

    def __del__(self) -> None:
        self.close()

    def _next_element_id(self) -> int:
        """Generates a monotonically increasing element ID."""
        eid = self._element_counter
        self._element_counter += 1
        return eid

    def inspect_window(
        self,
        hwnd: Optional[int] = None,
        interactive_only: bool = True,
        max_elements: int = 50,
    ) -> List[UIElement]:
        """
        Inspects interactive controls of the target window or active application.
        Queries the AT-SPI2 registry over D-Bus and traverses widget extents.
        """
        conn = self._get_connection()
        if conn is None:
            return []

        # Find target process ID from focus manager if hwnd or active foreground
        target_pid: Optional[int] = None
        try:
            from extra.core.platform.linux.focus import get_foreground_window, get_window_info
            if hwnd:
                win_info = get_window_info(hwnd)
                if win_info and win_info.process_id > 0:
                    target_pid = win_info.process_id
            else:
                fg = get_foreground_window()
                if fg and fg.process_id > 0:
                    target_pid = fg.process_id
        except Exception:
            pass

        elements: List[UIElement] = []
        self._cached_elements.clear()

        try:
            # Query top-level application roots from Registry
            reg_addr = DBusAddress(
                "/org/a11y/atspi/accessible/root",
                bus_name="org.a11y.atspi.Registry",
                interface="org.a11y.atspi.Accessible",
            )
            msg = new_method_call(reg_addr, "GetChildren", "", ())
            reply = conn.send_and_get_reply(msg)
            if not reply.body or not reply.body[0]:
                return []

            app_children: List[Tuple[str, str]] = reply.body[0]

            # Filter or order applications by target_pid if known
            target_apps: List[Tuple[str, str]] = []
            other_apps: List[Tuple[str, str]] = []

            for srv, path in app_children:
                if target_pid:
                    try:
                        pid_msg = new_method_call(
                            DBusAddress(
                                "/org/freedesktop/DBus",
                                bus_name="org.freedesktop.DBus",
                                interface="org.freedesktop.DBus",
                            ),
                            "GetConnectionUnixProcessID",
                            "s",
                            (srv,),
                        )
                        pid_rep = conn.send_and_get_reply(pid_msg)
                        if pid_rep.body and pid_rep.body[0] == target_pid:
                            target_apps.append((srv, path))
                            continue
                    except Exception:
                        pass
                other_apps.append((srv, path))

            candidate_apps = target_apps if target_apps else other_apps

            # Traverse candidate application subtrees
            visited: Set[Tuple[str, str]] = set()
            queue: List[Tuple[str, str, int]] = [(srv, path, 0) for srv, path in candidate_apps]

            while queue and len(elements) < max_elements:
                curr_srv, curr_path, depth = queue.pop(0)
                if (curr_srv, curr_path) in visited or depth > 8:
                    continue
                visited.add((curr_srv, curr_path))

                # 1. Enqueue children first to explore containers fully
                try:
                    c_msg = new_method_call(
                        DBusAddress(curr_path, bus_name=curr_srv, interface="org.a11y.atspi.Accessible"),
                        "GetChildren",
                        "",
                        (),
                    )
                    c_rep = conn.send_and_get_reply(c_msg)
                    if c_rep.body and c_rep.body[0]:
                        for child_srv, child_path in c_rep.body[0]:
                            if (child_srv, child_path) not in visited:
                                queue.append((child_srv, child_path, depth + 1))
                except Exception:
                    pass

                # 2. Check if this node is an interactive or semantic control
                try:
                    role_msg = new_method_call(
                        DBusAddress(curr_path, bus_name=curr_srv, interface="org.a11y.atspi.Accessible"),
                        "GetRoleName",
                        "",
                        (),
                    )
                    role_rep = conn.send_and_get_reply(role_msg)
                    raw_role = str(role_rep.body[0]).lower().replace("_", " ").strip() if role_rep.body else "unknown"
                    ctrl_type = ATSPI_ROLE_MAP.get(raw_role) or ATSPI_ROLE_MAP.get(raw_role.replace("-", " ")) or "Custom"

                    # Check Component extents
                    has_valid_extents = False
                    bbox = (0, 0, 0, 0)
                    center = (0, 0)

                    ext_msg = new_method_call(
                        DBusAddress(curr_path, bus_name=curr_srv, interface="org.a11y.atspi.Component"),
                        "GetExtents",
                        "u",
                        (ATSPI_COORD_TYPE_SCREEN,),
                    )
                    ext_rep = conn.send_and_get_reply(ext_msg)
                    if ext_rep.body and len(ext_rep.body[0]) >= 4:
                        ex, ey, ew, eh = ext_rep.body[0][:4]
                        if ew > 0 and eh > 0:
                            bbox = (ex, ey, ex + ew, ey + eh)
                            center = (ex + ew // 2, ey + eh // 2)
                            has_valid_extents = True

                    # Extract name
                    name = ""
                    try:
                        name_msg = new_method_call(
                            DBusAddress(curr_path, bus_name=curr_srv, interface="org.freedesktop.DBus.Properties"),
                            "Get",
                            "ss",
                            ("org.a11y.atspi.Accessible", "Name"),
                        )
                        name_rep = conn.send_and_get_reply(name_msg)
                        if name_rep.body and name_rep.body[0]:
                            val = name_rep.body[0]
                            name = str(val[1] if isinstance(val, (tuple, list)) and len(val) >= 2 else val).strip()
                    except Exception:
                        pass

                    # Extract states
                    is_enabled = True
                    is_showing = True
                    try:
                        state_msg = new_method_call(
                            DBusAddress(curr_path, bus_name=curr_srv, interface="org.a11y.atspi.Accessible"),
                            "GetState",
                            "",
                            (),
                        )
                        state_rep = conn.send_and_get_reply(state_msg)
                        if state_rep.body and state_rep.body[0]:
                            s0 = state_rep.body[0][0]
                            is_enabled = bool(s0 & (STATE_ENABLED | STATE_SENSITIVE))
                            is_showing = bool(s0 & STATE_SHOWING)
                    except Exception:
                        pass

                    # Query interfaces
                    ifaces: List[str] = []
                    try:
                        iface_msg = new_method_call(
                            DBusAddress(curr_path, bus_name=curr_srv, interface="org.a11y.atspi.Accessible"),
                            "GetInterfaces",
                            "",
                            (),
                        )
                        iface_rep = conn.send_and_get_reply(iface_msg)
                        if iface_rep.body and iface_rep.body[0]:
                            ifaces = list(iface_rep.body[0])
                    except Exception:
                        pass

                    # Determine eligibility
                    is_candidate = has_valid_extents
                    if interactive_only:
                        is_candidate = is_candidate and (ctrl_type in INTERACTIVE_TYPES)

                    if is_candidate and (name or ctrl_type in ("Button", "Edit", "MenuItem", "TabItem", "CheckBox")):
                        elem_id = self._next_element_id()
                        elem = UIElement(
                            element_id=elem_id,
                            name=name or f"<{ctrl_type}>",
                            control_type=ctrl_type,
                            automation_id=f"{curr_srv}:{curr_path}",
                            class_name=raw_role,
                            bounding_box=bbox,
                            center=center,
                            is_enabled=is_enabled,
                            is_offscreen=not is_showing,
                            raw_element={
                                "srv": curr_srv,
                                "path": curr_path,
                                "interfaces": ifaces,
                            },
                        )
                        elements.append(elem)
                        self._cached_elements[elem_id] = elem

                except Exception as err:
                    logger.debug("Error processing node (%s, %s): %s", curr_srv, curr_path, err)
                    continue

        except Exception as e:
            logger.debug("Failed AT-SPI tree traversal: %s", e)
            self._close_connection()

        return elements

    def find_element(
        self, query: str, exact: bool = False, interactive_only: bool = True
    ) -> Optional[UIElement]:
        """
        Finds element matching name or text query.
        Searches cached elements or triggers an active window inspection.
        """
        q = query.strip().lower()
        if not self._cached_elements:
            self.inspect_window(interactive_only=interactive_only)

        for elem in self._cached_elements.values():
            e_name = elem.name.strip().lower()
            if exact and e_name == q:
                return elem
            elif not exact and q in e_name:
                return elem
        return None

    def invoke_element(self, element_or_id: Union[UIElement, int]) -> bool:
        """
        Activates the target UI element.
        Tries direct AT-SPI DoAction(0) invocation in < 1ms first.
        Falls back to physical hardware center mouse click if unsupported.
        """
        elem: Optional[UIElement] = None
        if isinstance(element_or_id, int):
            elem = self._cached_elements.get(element_or_id)
        else:
            elem = element_or_id

        if elem is None:
            return False

        # Attempt 1: Direct D-Bus DoAction(0)
        conn = self._get_connection()
        if conn is not None and elem.raw_element:
            raw = elem.raw_element
            srv = raw.get("srv")
            path = raw.get("path")
            ifaces = raw.get("interfaces", [])

            if srv and path and "org.a11y.atspi.Action" in ifaces:
                try:
                    act_msg = new_method_call(
                        DBusAddress(path, bus_name=srv, interface="org.a11y.atspi.Action"),
                        "DoAction",
                        "i",
                        (0,),
                    )
                    reply = conn.send_and_get_reply(act_msg)
                    if reply.body and bool(reply.body[0]):
                        return True
                except Exception as ex:
                    logger.debug("Direct AT-SPI DoAction failed: %s", ex)

        # Attempt 2: Hardware Center Click fallback
        cx, cy = elem.center
        if cx > 0 or cy > 0:
            mouse_click(cx, cy)
            return True

        return False


# ── Set-of-Mark (SoM) Visual Annotator ─────────────────────────────────────────

class SetOfMarkAnnotator:
    """
    Set-of-Mark (SoM) visual annotator.
    Renders high-visibility numbered badges on top of detected interactive elements.
    Allows AI models to ground exact click targets by number without coordinate hallucinations.
    """

    def __init__(self) -> None:
        self._font = None
        font_candidates = [
            "/usr/share/fonts/noto/NotoSans-Regular.ttf",
            "/usr/share/fonts/TTF/DejaVuSans.ttf",
            "/usr/share/fonts/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        for font_path in font_candidates:
            if os.path.exists(font_path):
                try:
                    self._font = ImageFont.truetype(font_path, 11)
                    break
                except Exception:
                    pass

        if self._font is None:
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
            if x2 <= x1 or y2 <= y1:
                continue

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


AccessibilityPlane = LinuxAccessibilityPlane
UIAutomationPlane = LinuxAccessibilityPlane
