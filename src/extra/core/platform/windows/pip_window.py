"""
Project Extra — Win32 Native Picture-in-Picture (PiP) Floating Preview Window
Provides a hardware-accelerated, always-on-top, draggable floating preview window
using pure Win32 API and GDI (zero external GUI framework overhead, sub-millisecond blit).
Renders real-time captures of the isolated Child Session or Virtual Desktop.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import logging
import queue
import threading
import time
from typing import Any, Dict, Optional, Tuple

from PIL import Image

logger = logging.getLogger("extra.core.platform.windows.pip_window")

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32

# Win32 Window Styles
WS_POPUP = 0x80000000
WS_VISIBLE = 0x10000000
WS_THICKFRAME = 0x00040000
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080

# Win32 Messages
WM_DESTROY = 0x0002
WM_PAINT = 0x000F
WM_CLOSE = 0x0010
WM_ERASEBKGND = 0x0014
WM_NCHITTEST = 0x0084
WM_USER = 0x0400
WM_PIP_UPDATE = WM_USER + 101

# Hit test constants
HTCAPTION = 2

# GDI constants
DIB_RGB_COLORS = 0
SRCCOPY = 0x00CC0020
BI_RGB = 0

WNDPROCTYPE = ctypes.WINFUNCTYPE(wintypes.LPARAM, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

# Explicit 64-bit Win32 prototypes
user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.DefWindowProcW.restype = wintypes.LPARAM
user32.DestroyWindow.argtypes = [wintypes.HWND]
user32.DestroyWindow.restype = wintypes.BOOL
user32.PostQuitMessage.argtypes = [ctypes.c_int]
user32.PostQuitMessage.restype = None
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostMessageW.restype = wintypes.BOOL
user32.BeginPaint.argtypes = [wintypes.HWND, ctypes.c_void_p]
user32.BeginPaint.restype = wintypes.HDC
user32.EndPaint.argtypes = [wintypes.HWND, ctypes.c_void_p]
user32.EndPaint.restype = wintypes.BOOL
user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.c_void_p]
user32.GetClientRect.restype = wintypes.BOOL
user32.InvalidateRect.argtypes = [wintypes.HWND, ctypes.c_void_p, wintypes.BOOL]
user32.InvalidateRect.restype = wintypes.BOOL
user32.GetMessageW.argtypes = [ctypes.c_void_p, wintypes.HWND, wintypes.UINT, wintypes.UINT]
user32.GetMessageW.restype = wintypes.BOOL
user32.TranslateMessage.argtypes = [ctypes.c_void_p]
user32.TranslateMessage.restype = wintypes.BOOL
user32.DispatchMessageW.argtypes = [ctypes.c_void_p]
user32.DispatchMessageW.restype = wintypes.LPARAM
user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.GetSystemMetrics.restype = ctypes.c_int
user32.RegisterClassW.argtypes = [ctypes.c_void_p]
user32.RegisterClassW.restype = wintypes.ATOM
user32.CreateWindowExW.argtypes = [
    wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, ctypes.c_void_p
]
user32.CreateWindowExW.restype = wintypes.HWND

gdi32.SetStretchBltMode.argtypes = [wintypes.HDC, ctypes.c_int]
gdi32.SetStretchBltMode.restype = ctypes.c_int
gdi32.StretchDIBits.argtypes = [
    wintypes.HDC,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT, wintypes.DWORD
]
gdi32.StretchDIBits.restype = ctypes.c_int


class PAINTSTRUCT(ctypes.Structure):
    _fields_ = [
        ("hdc", wintypes.HDC),
        ("fErase", wintypes.BOOL),
        ("rcPaint", wintypes.RECT),
        ("fRestore", wintypes.BOOL),
        ("fIncUpdate", wintypes.BOOL),
        ("rgbReserved", wintypes.BYTE * 32),
    ]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ("bmiHeader", BITMAPINFOHEADER),
        ("bmiColors", wintypes.DWORD * 3),
    ]


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROCTYPE),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HANDLE),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HANDLE),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


# Module-level window registry and class initialization
_ACTIVE_PIP_WINDOWS: Dict[int, Any] = {}
_PIP_CLASS_NAME = "Extra_PiP_Native_Window_Class"
_PIP_CLASS_BUF = ctypes.create_unicode_buffer(_PIP_CLASS_NAME)
_GLOBAL_WCLS: Optional[WNDCLASSW] = None
_CLASS_LOCK = threading.Lock()
_CLASS_REGISTERED = False


@WNDPROCTYPE
def _global_pip_wnd_proc(hwnd: int, msg: int, wparam: int, lparam: int) -> int:
    """Permanent module-level WndProc ensuring zero callback garbage collection."""
    win = _ACTIVE_PIP_WINDOWS.get(hwnd)
    if msg == WM_NCHITTEST:
        return HTCAPTION
    elif msg == WM_PIP_UPDATE and win:
        win._handle_frame_update()
        return 0
    elif msg == WM_PAINT and win:
        win._handle_paint()
        return 0
    elif msg == WM_ERASEBKGND:
        return 1
    elif msg == WM_CLOSE:
        user32.DestroyWindow(hwnd)
        return 0
    elif msg == WM_DESTROY:
        _ACTIVE_PIP_WINDOWS.pop(hwnd, None)
        user32.PostQuitMessage(0)
        return 0
    return user32.DefWindowProcW(hwnd, msg, wparam, lparam)


def _ensure_class_registered() -> None:
    global _CLASS_REGISTERED, _GLOBAL_WCLS
    with _CLASS_LOCK:
        if _CLASS_REGISTERED:
            return
        hinst = kernel32.GetModuleHandleW(None)
        _GLOBAL_WCLS = WNDCLASSW()
        _GLOBAL_WCLS.style = 0x0008  # CS_DBLCLKS
        _GLOBAL_WCLS.lpfnWndProc = _global_pip_wnd_proc
        _GLOBAL_WCLS.hInstance = hinst
        _GLOBAL_WCLS.lpszClassName = ctypes.cast(_PIP_CLASS_BUF, wintypes.LPCWSTR)
        user32.RegisterClassW(ctypes.byref(_GLOBAL_WCLS))
        _CLASS_REGISTERED = True


class PiPPreviewWindow:
    """
    Pure Win32 hardware-accelerated Picture-in-Picture floating preview window.
    Features:
      - Always-on-top (`WS_EX_TOPMOST`)
      - Smooth title-bar-free dragging across the screen
      - Direct DIB-to-device GDI blitting (< 1ms per frame)
      - Independent UI message loop thread (zero impact on automation speed)
    """

    def __init__(
        self,
        title: str = "Extra Picture-in-Picture",
        width: int = 480,
        height: int = 270,
        fps: int = 30,
    ) -> None:
        self.title = title
        self.width = width
        self.height = height
        self.fps = fps
        self._frame_interval = 1.0 / fps

        self.hwnd: Optional[int] = None
        self._thread: Optional[threading.Thread] = None
        self._frame_queue: queue.Queue = queue.Queue(maxsize=2)
        self._latest_bmp_bytes: Optional[bytes] = None
        self._latest_bmp_size: Tuple[int, int] = (0, 0)
        self._stop_event = threading.Event()
        self._ready_event = threading.Event()
        self._is_visible = False
        self._lock = threading.Lock()

    def start(self) -> bool:
        """Starts the native Win32 PiP window on a dedicated message-loop thread."""
        with self._lock:
            if self._thread and self._thread.is_alive():
                return True

            self._stop_event.clear()
            self._ready_event.clear()

            self._thread = threading.Thread(
                target=self._win32_ui_worker,
                daemon=True,
                name="ExtraNativePiPThread",
            )
            self._thread.start()

            # Wait for window handle creation
            ok = self._ready_event.wait(timeout=3.0)
            if ok and self.hwnd:
                self._is_visible = True
                logger.info("[PiPViewer] Native Win32 PiP window started (HWND: %s, %dx%d)", self.hwnd, self.width, self.height)
                return True
            logger.warning("[PiPViewer] Failed to initialize native Win32 PiP window")
            return False

    def stop(self) -> None:
        """Destroys the window and stops the UI message loop."""
        with self._lock:
            self._stop_event.set()
            if self.hwnd:
                try:
                    user32.PostMessageW(self.hwnd, WM_CLOSE, 0, 0)
                except Exception:
                    pass
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=1.5)
            self._thread = None
            self.hwnd = None
            self._is_visible = False
            logger.info("[PiPViewer] Native Win32 PiP window stopped")

    def update_frame(self, image: Image.Image) -> None:
        """
        Pushes a new captured PIL image frame to the preview window.
        Converts to BGR DIB format and invalidates the client area for instant blitting.
        """
        if not self._is_visible or not self.hwnd or self._stop_event.is_set():
            return
        try:
            # Drain queue if full to show newest frame
            if self._frame_queue.full():
                try:
                    self._frame_queue.get_nowait()
                except queue.Empty:
                    pass
            self._frame_queue.put_nowait(image)

            # Notify window to repaint
            user32.PostMessageW(self.hwnd, WM_PIP_UPDATE, 0, 0)
        except Exception:
            pass

    def is_visible(self) -> bool:
        """Returns True if the PiP window is visible."""
        return self._is_visible and bool(self.hwnd)

    def _handle_frame_update(self) -> None:
        """Processes the next frame from queue into BGRA 32-bit DIB format."""
        try:
            img = self._frame_queue.get_nowait()
            w, h = img.size
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            r, g, b, a = img.split()
            bgra_img = Image.merge("RGBA", (b, g, r, a))
            flipped = bgra_img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            self._latest_bmp_bytes = flipped.tobytes()
            self._latest_bmp_size = (w, h)

            if self.hwnd:
                user32.InvalidateRect(self.hwnd, None, False)
        except Exception:
            pass

    def _handle_paint(self) -> None:
        """Renders the latest DIB frame via GDI StretchDIBits."""
        if not self.hwnd:
            return
        ps = PAINTSTRUCT()
        hdc = user32.BeginPaint(self.hwnd, ctypes.byref(ps))
        if hdc:
            try:
                if self._latest_bmp_bytes and self._latest_bmp_size[0] > 0:
                    w, h = self._latest_bmp_size
                    bmi = BITMAPINFO()
                    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
                    bmi.bmiHeader.biWidth = w
                    bmi.bmiHeader.biHeight = h
                    bmi.bmiHeader.biPlanes = 1
                    bmi.bmiHeader.biBitCount = 32
                    bmi.bmiHeader.biCompression = BI_RGB

                    rect = wintypes.RECT()
                    user32.GetClientRect(self.hwnd, ctypes.byref(rect))
                    client_w = rect.right - rect.left
                    client_h = rect.bottom - rect.top

                    gdi32.SetStretchBltMode(hdc, 3)  # COLORONCOLOR
                    gdi32.StretchDIBits(
                        hdc,
                        0, 0, client_w, client_h,
                        0, 0, w, h,
                        self._latest_bmp_bytes,
                        ctypes.byref(bmi),
                        DIB_RGB_COLORS,
                        SRCCOPY,
                    )
            finally:
                user32.EndPaint(self.hwnd, ctypes.byref(ps))

    def _win32_ui_worker(self) -> None:
        """Dedicated message-pump worker thread for the Win32 window."""
        _ensure_class_registered()
        hinst = kernel32.GetModuleHandleW(None)

        screen_w = user32.GetSystemMetrics(0)
        screen_h = user32.GetSystemMetrics(1)
        pos_x = screen_w - self.width - 24
        pos_y = screen_h - self.height - 60

        self.hwnd = user32.CreateWindowExW(
            WS_EX_TOPMOST | WS_EX_TOOLWINDOW,
            _PIP_CLASS_BUF,
            self.title,
            WS_POPUP | WS_VISIBLE | WS_THICKFRAME,
            pos_x, pos_y, self.width, self.height,
            None, None, hinst, None,
        )

        if self.hwnd:
            _ACTIVE_PIP_WINDOWS[self.hwnd] = self

        self._ready_event.set()

        # Win32 Message Pump
        msg = (wintypes.MSG)()
        while not self._stop_event.is_set():
            ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if ret <= 0:
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        self._is_visible = False


# Global singleton instance
_global_pip_window: Optional[PiPPreviewWindow] = None
_pip_lock = threading.Lock()


def get_pip_window() -> PiPPreviewWindow:
    """Returns the process-wide PiPPreviewWindow singleton."""
    global _global_pip_window
    with _pip_lock:
        if _global_pip_window is None:
            _global_pip_window = PiPPreviewWindow()
        return _global_pip_window
