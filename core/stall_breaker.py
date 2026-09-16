"""
Project Extra — Closed-Loop Stall Breaker & Safety System
Heritage: Ported from yantraOS computer_use_bridge.py (EXIT_STALLED = 4).
Closed-loop perceptual hash diffing, 2-strike runaway loop breaker,
emergency corner abort (0, 0), and cross-platform global kill-switch trap:
- Windows: Ctrl + Alt + Shift + Q
- macOS: Cmd + Option + Shift + Q
"""

from __future__ import annotations

import ctypes
from dataclasses import dataclass
from enum import Enum
import sys
from typing import Optional, Tuple

import imagehash
import numpy as np
from PIL import Image

from extra.core.geometry import attach_input_desktop, ensure_dpi_aware, get_cursor_position

user32 = getattr(ctypes, "windll", None)
if user32 is not None:
    user32 = getattr(user32, "user32", None)

try:
    import Quartz.CoreGraphics as CG
except ImportError:
    CG = None

# Win32 Virtual Key Codes for Emergency Kill Switch
VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt
VK_SHIFT = 0x10
VK_Q = 0x51


class StallStatus(str, Enum):
    NORMAL = "normal"
    WARNING = "warning"
    STALLED = "stalled"


class EmergencyAbortError(Exception):
    """Raised immediately when emergency fail-safe corner (0,0) or kill hotkey is triggered."""
    pass


@dataclass
class ActionOutcome:
    """Evaluated result of an action verifying visual progression."""
    status: StallStatus
    strikes: int
    phash_diff: int
    pixel_diff: float
    window_changed: bool
    message: str


class StallBreaker:
    """
    Closed-loop perceptual diffing and safety supervisor.
    Detects when model actions produce zero visible change or loop endlessly.
    """

    def __init__(
        self,
        hash_threshold: int = 2,
        pixel_threshold: float = 0.5,
        max_strikes: int = 2,
        corner_abort_pixels: int = 3,
    ) -> None:
        self.hash_threshold = hash_threshold
        self.pixel_threshold = pixel_threshold
        self.max_strikes = max_strikes
        self.corner_abort_pixels = corner_abort_pixels
        self._current_strikes = 0
        self._last_hash: Optional[imagehash.ImageHash] = None
        self._last_hwnd: Optional[int] = None

    @property
    def current_strikes(self) -> int:
        return self._current_strikes

    def check_safety_abort(self) -> None:
        """
        Guarantees user safety:
        1. Corner Fail-Safe: Moving physical mouse to top-left corner (0, 0).
        2. Emergency Hotkey:
           - Windows: Ctrl + Alt + Shift + Q
           - macOS: Cmd + Option + Shift + Q
        """
        ensure_dpi_aware()
        attach_input_desktop()

        # 1. Corner fail-safe check
        cx, cy = get_cursor_position()
        if cx <= self.corner_abort_pixels and cy <= self.corner_abort_pixels:
            raise EmergencyAbortError(
                f"Fail-Safe Triggered: Mouse pointer detected at emergency abort corner ({cx}, {cy})."
            )

        # 2. Emergency hotkey check:
        # Windows (Ctrl + Alt + Shift + Q)
        if user32 is not None and hasattr(user32, "GetAsyncKeyState"):
            try:
                ctrl_down = bool(user32.GetAsyncKeyState(VK_CONTROL) & 0x8000)
                alt_down = bool(user32.GetAsyncKeyState(VK_MENU) & 0x8000)
                shift_down = bool(user32.GetAsyncKeyState(VK_SHIFT) & 0x8000)
                q_down = bool(user32.GetAsyncKeyState(VK_Q) & 0x8000)

                if ctrl_down and alt_down and shift_down and q_down:
                    raise EmergencyAbortError(
                        "Fail-Safe Triggered: Emergency kill hotkey (Ctrl+Alt+Shift+Q) pressed."
                    )
            except Exception as e:
                if isinstance(e, EmergencyAbortError):
                    raise

        # macOS (Cmd + Option + Shift + Q)
        if sys.platform == "darwin" and CG is not None:
            try:
                flags = CG.CGEventSourceFlagsState(CG.kCGEventSourceStateCombinedSessionState)
                cmd_down = bool(flags & getattr(CG, "kCGEventFlagMaskCommand", 0x00100000))
                opt_down = bool(flags & getattr(CG, "kCGEventFlagMaskAlternate", 0x00080000))
                shift_down = bool(flags & getattr(CG, "kCGEventFlagMaskShift", 0x00020000))
                q_down = bool(CG.CGEventSourceKeyState(CG.kCGEventSourceStateCombinedSessionState, 12))

                if cmd_down and opt_down and shift_down and q_down:
                    raise EmergencyAbortError(
                        "Fail-Safe Triggered: Emergency kill hotkey (Cmd+Opt+Shift+Q) pressed on macOS."
                    )
            except Exception as e:
                if isinstance(e, EmergencyAbortError):
                    raise

    def evaluate_action(
        self,
        before_image: Image.Image,
        after_image: Image.Image,
        before_hwnd: Optional[int] = None,
        after_hwnd: Optional[int] = None,
        action_name: str = "action",
        before_full_image: Optional[Image.Image] = None,
        after_full_image: Optional[Image.Image] = None,
    ) -> ActionOutcome:
        """
        Compares screen state before and after an action using perceptual hashing
        and numpy pixel difference. Applies the 2-strike loop breaker rule.
        Supports global fallback diffing when local ROI delta is zero (Fixes #4, credit: @harshbuttru3).
        """
        self.check_safety_abort()

        # 1. Check window state transition
        window_changed = (
            before_hwnd is not None
            and after_hwnd is not None
            and before_hwnd != after_hwnd
        )

        # 2. Compute perceptual hash delta on ROI
        h_before = imagehash.phash(before_image)
        h_after = imagehash.phash(after_image)
        phash_diff = abs(h_before - h_after)

        # 3. Compute structural pixel delta on ROI
        arr_before = np.asarray(before_image, dtype=np.int16)
        arr_after = np.asarray(after_image, dtype=np.int16)
        pixel_diff = float(np.mean(np.abs(arr_before - arr_after)))

        # Determine whether visible change occurred locally
        has_visual_delta = (phash_diff > self.hash_threshold) or (pixel_diff > self.pixel_threshold)

        # 4. Global Fallback Check (Fixes #4, credit: @harshbuttru3)
        # If local ROI produced zero delta, check if distant screen regions (e.g. 3D viewports, canvas) changed
        global_changed = False
        full_pixel_diff = 0.0
        if not has_visual_delta and not window_changed and before_full_image is not None and after_full_image is not None:
            try:
                # High-speed downsampled diff (sub-2ms via Nearest Neighbor + numpy mean)
                small_before = before_full_image.resize((160, 90), Image.Resampling.NEAREST)
                small_after = after_full_image.resize((160, 90), Image.Resampling.NEAREST)
                full_arr_before = np.asarray(small_before, dtype=np.int16)
                full_arr_after = np.asarray(small_after, dtype=np.int16)
                full_pixel_diff = float(np.mean(np.abs(full_arr_before - full_arr_after)))
                if full_pixel_diff > self.pixel_threshold:
                    global_changed = True
                    has_visual_delta = True
            except Exception:
                pass

        has_state_change = has_visual_delta or window_changed

        if has_state_change:
            # Action had visible effect: reset strikes
            self._current_strikes = 0
            self._last_hash = h_after
            self._last_hwnd = after_hwnd
            msg = (
                f"Action '{action_name}' succeeded with remote visual change (global pixel_diff={full_pixel_diff:.2f})."
                if global_changed
                else f"Action '{action_name}' succeeded with visible change (phash_diff={phash_diff}, pixel_diff={pixel_diff:.2f})."
            )
            return ActionOutcome(
                status=StallStatus.NORMAL,
                strikes=0,
                phash_diff=phash_diff,
                pixel_diff=round(full_pixel_diff if global_changed else pixel_diff, 3),
                window_changed=window_changed,
                message=msg,
            )
        else:
            # Action produced NO visual or window change
            self._current_strikes += 1
            if self._current_strikes >= self.max_strikes:
                status = StallStatus.STALLED
                message = (
                    f"STALL DETECTED: 2 consecutive actions produced zero screen or window changes. "
                    f"Action '{action_name}' failed to progress. Aborting loop to protect token burn."
                )
            else:
                status = StallStatus.WARNING
                message = (
                    f"Warning (Strike {self._current_strikes}/{self.max_strikes}): Action '{action_name}' "
                    f"produced no visible change. Consider scrolling, waiting, or targeting alternative element."
                )

            return ActionOutcome(
                status=status,
                strikes=self._current_strikes,
                phash_diff=phash_diff,
                pixel_diff=round(pixel_diff, 3),
                window_changed=window_changed,
                message=message,
            )

    def reset(self) -> None:
        """Resets the strike counter to zero."""
        self._current_strikes = 0
        self._last_hash = None
        self._last_hwnd = None
