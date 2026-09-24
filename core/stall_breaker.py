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
from typing import Any, Dict, List, Optional, Tuple, Union

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
    cognitive_state: str = "NORMAL_PROGRESS"
    recommended_action: Optional[str] = None
    is_spinner_detected: bool = False
    is_modal_blocked: bool = False


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
        self._last_action: Optional[str] = None
        self._recent_diffs: List[int] = []
        self._last_cognitive_state: str = "NORMAL_PROGRESS"

    @property
    def current_strikes(self) -> int:
        return self._current_strikes

    def classify_cognitive_state(
        self,
        hwnd: Optional[int] = None,
        window_title: Optional[str] = None,
        context_text: Optional[str] = None,
        phash_diff: int = 0,
        pixel_diff: float = 0.0,
    ) -> Tuple[str, Optional[str]]:
        """
        Queries SOUL (System One Ultra-fast Layer) to categorize the active application state:
        - 'APP_CRASHED': Unresponsive message loop (Win32 IsHungAppWindow).
        - 'MODAL_BLOCKED': Active modal or confirmation dialog intercepting input.
        - 'SPINNER_BLOCKED': Ongoing loading spinner or indeterminate progress animation.
        - 'ZERO_CHANGE': Purely static unchanged state.
        - 'NORMAL_PROGRESS': Active and responding.
        """
        # 1. Hardware-level hung window check (Win32 IsHungAppWindow in 0.01ms)
        if hwnd and user32 is not None and hasattr(user32, "IsHungAppWindow"):
            try:
                if bool(user32.IsHungAppWindow(hwnd)):
                    return "APP_CRASHED", "Target application is not responding (hung message loop). Kill or restart process."
            except Exception:
                pass

        # 2. Gather desktop context
        title = window_title or ""
        if not title:
            try:
                from extra.core.focus import get_foreground_window
                fg = get_foreground_window()
                if fg:
                    title = fg.title
            except Exception:
                pass

        ctx_dict: Dict[str, Any] = {
            "window_title": title,
            "phash_diff": phash_diff,
            "pixel_diff": round(pixel_diff, 2),
        }
        if context_text:
            ctx_dict["context"] = context_text

        # 3. SOUL Reflexive Evaluation
        try:
            from extra.core.soul import get_soul_decider
            decider = get_soul_decider()

            candidates = [
                "NORMAL_PROGRESS",
                "SPINNER_BLOCKED",
                "MODAL_BLOCKED",
                "ZERO_CHANGE",
            ]
            query = f"Classify state of window '{title}'. Visual diff: phash={phash_diff}, pixel={pixel_diff:.2f}."
            decision = decider.decide_choice(query, candidates, context=ctx_dict)
            state = str(decision.result)

            recommendation: Optional[str] = None
            if state == "SPINNER_BLOCKED":
                recommendation = "Application is in a loading/spinner state. Avoid repeating clicks; wait for completion or send Escape."
            elif state == "MODAL_BLOCKED":
                recommendation = f"A modal dialog ('{title}') is blocking interaction. Dismiss with Escape or target dialog controls."
            elif state == "ZERO_CHANGE":
                recommendation = "Action produced no visible effect. Try alternative shortcuts, scrolling, or different coordinates."

            return state, recommendation
        except Exception:
            return "ZERO_CHANGE", "Action produced no visible change."

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
        self._recent_diffs.append(phash_diff)
        self._recent_diffs = self._recent_diffs[-5:]

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

        # 5. SOUL Cognitive Stall Analysis (Detects Spinner Loops, Modal Traps, & Crashes)
        is_potential_spinner = (
            not window_changed
            and 0 < phash_diff <= 8
            and pixel_diff <= 3.0
            and len(self._recent_diffs) >= 2
            and all(0 < d <= 8 for d in self._recent_diffs[-2:])
        )

        cognitive_state = "NORMAL_PROGRESS"
        recommended_action: Optional[str] = None
        is_spinner = False
        is_modal = False

        if not has_visual_delta or is_potential_spinner or self._current_strikes >= 1:
            cog_state, cog_rec = self.classify_cognitive_state(
                hwnd=after_hwnd or before_hwnd,
                phash_diff=phash_diff,
                pixel_diff=full_pixel_diff if global_changed else pixel_diff,
            )
            cognitive_state = cog_state
            recommended_action = cog_rec
            self._last_cognitive_state = cog_state

            if cog_state == "SPINNER_BLOCKED":
                is_spinner = True
                has_state_change = False  # Override: spinner churning is NOT true progression!
            elif cog_state == "MODAL_BLOCKED":
                is_modal = True
            elif cog_state == "APP_CRASHED":
                has_state_change = False

        if has_state_change:
            # Action had visible effect: reset strikes
            self._current_strikes = 0
            self._last_hash = h_after
            self._last_hwnd = after_hwnd
            self._last_action = action_name
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
                cognitive_state=cognitive_state,
                recommended_action=recommended_action,
                is_spinner_detected=is_spinner,
                is_modal_blocked=is_modal,
            )
        else:
            # Action produced NO visual or window change
            # If target changed from previous action, start a new strike count rather than compounding
            if self._last_action and self._last_action != action_name:
                self._current_strikes = 1
            else:
                self._current_strikes += 1

            self._last_action = action_name

            if cognitive_state == "APP_CRASHED":
                status = StallStatus.STALLED
                message = f"APPLICATION CRASH DETECTED: Window '{after_hwnd or before_hwnd}' is hung and unresponsive. {recommended_action}"
            elif is_spinner:
                status = StallStatus.STALLED if self._current_strikes >= self.max_strikes else StallStatus.WARNING
                message = (
                    f"SPINNER LOOP DETECTED (Strike {self._current_strikes}/{self.max_strikes}): Application is stuck in an active loading animation. "
                    f"{recommended_action}"
                )
            elif is_modal:
                status = StallStatus.STALLED if self._current_strikes >= self.max_strikes else StallStatus.WARNING
                message = (
                    f"MODAL TRAP DETECTED (Strike {self._current_strikes}/{self.max_strikes}): Action produced no effect because a dialog is intercepting input. "
                    f"{recommended_action}"
                )
            elif self._current_strikes >= self.max_strikes:
                status = StallStatus.STALLED
                message = (
                    f"STALL DETECTED: {self._current_strikes} consecutive attempts on '{action_name}' produced zero screen or window changes. "
                    f"Consider scrolling, using keyboard shortcuts, or targeting a different UI element."
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
                cognitive_state=cognitive_state,
                recommended_action=recommended_action,
                is_spinner_detected=is_spinner,
                is_modal_blocked=is_modal,
            )

    def reset(self) -> None:
        """Resets the strike counter to zero."""
        self._current_strikes = 0
        self._last_hash = None
        self._last_hwnd = None
        self._last_action = None
        self._recent_diffs.clear()
        self._last_cognitive_state = "NORMAL_PROGRESS"

