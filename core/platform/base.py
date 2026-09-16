"""
Project Extra — Platform Abstraction Layer (PAL) Base Interfaces
Standardized abstract base classes and dataclasses across Windows and macOS.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import base64
from dataclasses import dataclass
import io
from typing import Any, Dict, List, Optional, Tuple, Union
from PIL import Image


# ── Shared Common Dataclasses ──────────────────────────────────────────────────

@dataclass
class CaptureResult:
    """Encapsulates captured screen image with performance metadata."""
    image: Image.Image
    duration_ms: float
    monitor_index: int
    width: int
    height: int
    crop_box: Optional[Tuple[int, int, int, int]] = None

    def to_base64(self, format: str = "JPEG", quality: int = 85) -> str:
        """Encodes captured PIL Image into base64 string."""
        return image_to_base64(self.image, format=format, quality=quality)


@dataclass(frozen=True)
class MonitorInfo:
    """Represents physical display hardware metrics and DPI scaling."""
    index: int
    left: int
    top: int
    right: int
    bottom: int
    width: int
    height: int
    is_primary: bool
    device_name: str
    dpi_x: int
    dpi_y: int
    scale_factor: float


@dataclass(frozen=True)
class WindowInfo:
    """Represents an active top-level native window."""
    hwnd: int  # Native window handle or ID
    title: str
    class_name: str
    process_id: int
    process_name: str
    rect: Tuple[int, int, int, int]
    is_visible: bool
    is_minimized: bool

    @property
    def width(self) -> int:
        return self.rect[2] - self.rect[0]

    @property
    def height(self) -> int:
        return self.rect[3] - self.rect[1]

    @property
    def center(self) -> Tuple[int, int]:
        return ((self.rect[0] + self.rect[2]) // 2, (self.rect[1] + self.rect[3]) // 2)


@dataclass
class UIElement:
    """Represents an accessible UI element queried from native accessibility trees."""
    element_id: int
    name: str
    control_type: str
    automation_id: str = ""
    class_name: str = ""
    bounding_box: Tuple[int, int, int, int] = (0, 0, 0, 0)  # (left, top, right, bottom)
    center: Tuple[int, int] = (0, 0)
    is_enabled: bool = True
    is_offscreen: bool = False
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


@dataclass
class LaunchResult:
    """Encapsulates the result of a deterministic application launch."""
    success: bool
    app_name: str
    target_executed: str
    hwnd: Optional[int] = None
    window_title: Optional[str] = None
    pid: Optional[int] = None
    duration_ms: float = 0.0
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "app_name": self.app_name,
            "target_executed": self.target_executed,
            "hwnd": self.hwnd,
            "window_title": self.window_title,
            "pid": self.pid,
            "duration_ms": self.duration_ms,
            "message": self.message,
        }


# ── Shared Helper Functions ────────────────────────────────────────────────────

def image_to_base64(image: Image.Image, format: str = "JPEG", quality: int = 85) -> str:
    """Converts a PIL Image to a base64 encoded string."""
    buffer = io.BytesIO()
    if format.upper() == "JPEG":
        if image.mode != "RGB":
            image = image.convert("RGB")
        image.save(buffer, format="JPEG", quality=quality, optimize=True)
    else:
        image.save(buffer, format=format)

    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return encoded


def get_bbox_center(bbox: Tuple[int, int, int, int]) -> Tuple[int, int]:
    """Computes the geometric center point (x, y) of a bounding box."""
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) // 2, (y1 + y2) // 2)


# ── Abstract Base Classes (ABCs) ───────────────────────────────────────────────

class AbstractCaptureEngine(ABC):
    """Abstract interface for native high-speed screen perception."""

    @abstractmethod
    def capture(
        self,
        monitor_index: int = 0,
        crop_box: Optional[Tuple[int, int, int, int]] = None,
    ) -> CaptureResult:
        """Captures a screen frame from the specified monitor."""
        pass

    def close(self) -> None:
        """Releases capture resources."""
        pass

    def __enter__(self) -> "AbstractCaptureEngine":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()


class AbstractGeometry(ABC):
    """Abstract interface for hardware geometry and coordinate mapping."""

    @abstractmethod
    def ensure_dpi_aware(self) -> bool:
        """Initializes native DPI and coordinate awareness."""
        pass

    @abstractmethod
    def attach_input_desktop(self) -> bool:
        """Attaches caller to active desktop session if applicable."""
        pass

    @abstractmethod
    def get_monitors_info(self) -> List[MonitorInfo]:
        """Discovers all displays with dimensions and DPI scaling factors."""
        pass

    @abstractmethod
    def get_primary_monitor(self) -> MonitorInfo:
        """Returns the primary display's information."""
        pass

    @abstractmethod
    def get_virtual_screen_bounds(self) -> Tuple[int, int, int, int]:
        """Returns virtual desktop bounding rectangle (left, top, width, height)."""
        pass

    @abstractmethod
    def get_cursor_position(self) -> Tuple[int, int]:
        """Returns current mouse cursor physical coordinates (x, y)."""
        pass

    @abstractmethod
    def normalize_coordinates(
        self, phys_x: int, phys_y: int, monitor_index: int = 0
    ) -> Tuple[int, int]:
        """Converts physical pixel coordinates into normalized [0, 1000] space."""
        pass

    @abstractmethod
    def denormalize_coordinates(
        self, norm_x: Union[int, float], norm_y: Union[int, float], monitor_index: int = 0
    ) -> Tuple[int, int]:
        """Converts normalized coordinates back to exact physical display pixels."""
        pass

    @abstractmethod
    def normalize_bbox(
        self, rect: Tuple[int, int, int, int], monitor_index: int = 0
    ) -> Tuple[int, int, int, int]:
        """Converts physical bounding box to normalized [0, 1000] bounding box."""
        pass

    @abstractmethod
    def denormalize_bbox(
        self,
        bbox: Tuple[Union[int, float], Union[int, float], Union[int, float], Union[int, float]],
        monitor_index: int = 0,
    ) -> Tuple[int, int, int, int]:
        """Converts normalized bounding box back to physical bounding box."""
        pass

    @abstractmethod
    def clamp_coordinates(
        self, phys_x: int, phys_y: int, monitor_index: int = 0
    ) -> Tuple[int, int]:
        """Clamps physical coordinates to stay within monitor bounds."""
        pass


class AbstractInputEngine(ABC):
    """Abstract interface for hardware mouse and keyboard input injection."""

    @abstractmethod
    def mouse_move(self, x: int, y: int, monitor_index: int = 0) -> None:
        """Dispatches mouse cursor movement."""
        pass

    @abstractmethod
    def mouse_down(self, button: str = "left") -> None:
        """Depresses a mouse button."""
        pass

    @abstractmethod
    def mouse_up(self, button: str = "left") -> None:
        """Releases a mouse button."""
        pass

    @abstractmethod
    def mouse_click(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        button: str = "left",
        clicks: int = 1,
        interval: float = 0.05,
        monitor_index: int = 0,
    ) -> None:
        """Executes one or more mouse clicks at specified target coordinates."""
        pass

    @abstractmethod
    def mouse_double_click(
        self, x: Optional[int] = None, y: Optional[int] = None, monitor_index: int = 0
    ) -> None:
        """Executes a double click at target coordinates."""
        pass

    @abstractmethod
    def mouse_drag(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        button: str = "left",
        steps: int = 15,
        duration: float = 0.2,
        monitor_index: int = 0,
    ) -> None:
        """Performs smooth click-and-drag between coordinates."""
        pass

    @abstractmethod
    def mouse_scroll(self, delta: int, horizontal: bool = False) -> None:
        """Scrolls mouse wheel vertically or horizontally."""
        pass

    @abstractmethod
    def instant_type(self, text: str, press_enter: bool = False) -> None:
        """Injects text directly via native system Unicode events."""
        pass

    @abstractmethod
    def send_hotkey(self, keys: List[str]) -> None:
        """Dispatches synchronized key combinations (e.g. ['ctrl', 'c'])."""
        pass

    @abstractmethod
    def atomic_clipboard_paste(self, text: str) -> None:
        """Performs atomic virtual clipboard swap and paste."""
        pass


class AbstractAccessibilityPlane(ABC):
    """Abstract interface for semantic accessibility hierarchy inspection and invocation."""

    @abstractmethod
    def inspect_window(
        self, hwnd: Optional[int] = None, interactive_only: bool = True, max_elements: int = 50
    ) -> List[UIElement]:
        """Inspects interactive elements of the target window."""
        pass

    def inspect_active_window(self, max_elements: int = 50) -> List[UIElement]:
        """Inspects the currently active foreground window."""
        return self.inspect_window(hwnd=None, interactive_only=True, max_elements=max_elements)

    @abstractmethod
    def find_element(
        self, query: str, exact: bool = False, interactive_only: bool = True
    ) -> Optional[UIElement]:
        """Finds element matching name or text query."""
        pass

    @abstractmethod
    def invoke_element(self, element_or_id: Union[UIElement, int]) -> bool:
        """Invokes or activates the target UI element."""
        pass


class AbstractFocusManager(ABC):
    """Abstract interface for window discovery, enumeration, and foreground focus."""

    @abstractmethod
    def get_window_info(self, hwnd: int) -> Optional[WindowInfo]:
        """Retrieves details for a specific window handle."""
        pass

    @abstractmethod
    def get_foreground_window(self) -> Optional[WindowInfo]:
        """Returns the active foreground window."""
        pass

    @abstractmethod
    def list_windows(self, visible_only: bool = True) -> List[WindowInfo]:
        """Enumerates visible top-level windows."""
        pass

    @abstractmethod
    def find_window_by_title(
        self, query: str, exact: bool = False, visible_only: bool = True, timeout: float = 0.0
    ) -> Optional[WindowInfo]:
        """Finds window matching title substring or exact string, with optional polling timeout."""
        pass

    @abstractmethod
    def find_windows_by_process(
        self, process_name: str, visible_only: bool = True
    ) -> List[WindowInfo]:
        """Finds windows belonging to a process name."""
        pass

    @abstractmethod
    def force_activate_window(self, hwnd: int) -> bool:
        """Forces window to foreground and focuses it."""
        pass


class AbstractShellLauncher(ABC):
    """Abstract interface for application launching and URI routing."""

    @abstractmethod
    def launch_app(
        self,
        app_name: str,
        args: Optional[List[str]] = None,
        wait_for_window: bool = True,
        timeout: float = 5.0,
    ) -> LaunchResult:
        """Deterministically launches application by alias or path."""
        pass

    @abstractmethod
    def open_uri(self, uri: str) -> bool:
        """Opens URL or URI protocol handler."""
        pass

    @abstractmethod
    def resolve_executable(self, app_name: str) -> Optional[Tuple[str, str]]:
        """Resolves app alias to executable target and type."""
        pass


class AbstractIndicatorController(ABC):
    """Abstract interface for visual overlays and auditory notifications."""

    @abstractmethod
    def task_start(self, task_name: str, monitor_index: int = 0) -> None:
        """Activates ambient edge glow and cursor indicators."""
        pass

    @abstractmethod
    def task_action(
        self, action_type: str, x: int = 0, y: int = 0, monitor_index: int = 0
    ) -> None:
        """Triggers dynamic cursor reticle or click ripple."""
        pass

    @abstractmethod
    def task_complete(
        self, summary: str = "", success: bool = True, play_chime: bool = True
    ) -> None:
        """Fires completion visual bloom and plays chime."""
        pass

    @abstractmethod
    def task_indicate_status(self, status: str, message: str = "") -> None:
        """Updates ambient status indicators."""
        pass

    @abstractmethod
    def pulse(self, color: str = "cyan") -> None:
        """Fires a momentary ambient pulse."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Dismisses and cleans up overlay indicators."""
        pass
