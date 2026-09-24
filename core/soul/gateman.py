"""
Project Extra — Project SOUL (System One Ultra-fast Layer)
SOUL-Gateman: Temporal Settle & Mode Transition Gatekeeper.
Monitors UI frame buffers at 20-60Hz to detect exact visual stabilization and prevent
premature action dispatch without burning cloud LLM tokens.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional, Tuple
from PIL import Image
import imagehash

from extra.core.capture import capture_screen

logger = logging.getLogger("Extra-SOUL-Gateman")


class SoulGateman:
    """
    Sub-15ms visual settle and state transition detector.
    Ensures windows, WebGL canvases, and modals have completely rendered
    before subsequent physical actions are dispatched.
    """

    def __init__(self, monitor_index: int = 0) -> None:
        self.monitor_index = monitor_index
        # Warmup hash pipeline to eliminate first-frame cold start latency
        try:
            dummy = Image.new("L", (16, 16), color=128)
            imagehash.dhash(dummy)
            imagehash.phash(dummy)
        except Exception:
            pass

    def wait_until_settled(
        self,
        timeout_sec: float = 4.0,
        settle_frames: int = 2,
        check_interval_ms: int = 60,
        hash_diff_threshold: int = 1,
    ) -> Dict[str, Any]:
        """
        Polls screen frames until visual changes cease (perceptual stability).
        Returns a dict with settled (bool), duration_ms, and frames_inspected.
        """
        t0 = time.perf_counter()
        consecutive_stable = 0
        last_hash: Optional[imagehash.ImageHash] = None
        frames = 0

        while (time.perf_counter() - t0) < timeout_sec:
            frames += 1
            try:
                cap = capture_screen(self.monitor_index)
                thumb = cap.image.resize((64, 64), Image.Resampling.NEAREST)
                curr_hash = imagehash.dhash(thumb)
            except Exception as ex:
                logger.debug("[SOUL-Gateman] Frame capture error: %s", ex)
                time.sleep(check_interval_ms / 1000.0)
                continue

            if last_hash is not None:
                diff = curr_hash - last_hash
                if diff <= hash_diff_threshold:
                    consecutive_stable += 1
                    if consecutive_stable >= settle_frames:
                        duration_ms = (time.perf_counter() - t0) * 1000.0
                        logger.debug("[SOUL-Gateman] Settled after %.1fms (%d frames)", duration_ms, frames)
                        return {
                            "settled": True,
                            "duration_ms": duration_ms,
                            "frames_inspected": frames,
                            "final_hash": str(curr_hash),
                        }
                else:
                    consecutive_stable = 0

            last_hash = curr_hash
            time.sleep(check_interval_ms / 1000.0)

        duration_ms = (time.perf_counter() - t0) * 1000.0
        logger.warning("[SOUL-Gateman] Settle timed out after %.1fms (%d frames)", duration_ms, frames)
        return {
            "settled": False,
            "duration_ms": duration_ms,
            "frames_inspected": frames,
            "final_hash": str(last_hash) if last_hash else "",
        }

    def wait_for_change(
        self,
        timeout_sec: float = 3.0,
        check_interval_ms: int = 50,
        min_diff: int = 3,
    ) -> Dict[str, Any]:
        """
        Waits until a visual change occurs (e.g. after a button click or launch).
        """
        t0 = time.perf_counter()
        try:
            cap0 = capture_screen(self.monitor_index)
            thumb0 = cap0.image.resize((64, 64), Image.Resampling.NEAREST)
            h0 = imagehash.dhash(thumb0)
        except Exception:
            h0 = None
        frames = 1

        while (time.perf_counter() - t0) < timeout_sec:
            frames += 1
            time.sleep(check_interval_ms / 1000.0)
            try:
                cap = capture_screen(self.monitor_index)
                thumb = cap.image.resize((64, 64), Image.Resampling.NEAREST)
                curr_h = imagehash.dhash(thumb)
            except Exception:
                continue

            if h0 is not None and (curr_h - h0) >= min_diff:
                duration_ms = (time.perf_counter() - t0) * 1000.0
                return {
                    "changed": True,
                    "duration_ms": duration_ms,
                    "frames_inspected": frames,
                    "diff": curr_h - h0,
                }

        duration_ms = (time.perf_counter() - t0) * 1000.0
        return {
            "changed": False,
            "duration_ms": duration_ms,
            "frames_inspected": frames,
            "diff": 0,
        }


# Singleton
_default_gateman = SoulGateman()


def wait_until_settled(
    timeout_sec: float = 4.0,
    settle_frames: int = 2,
    check_interval_ms: int = 60,
    hash_diff_threshold: int = 1,
) -> Dict[str, Any]:
    return _default_gateman.wait_until_settled(
        timeout_sec=timeout_sec,
        settle_frames=settle_frames,
        check_interval_ms=check_interval_ms,
        hash_diff_threshold=hash_diff_threshold,
    )
