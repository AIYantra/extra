"""
Unit tests for Project Extra — Windows Ambient Awareness & Audio Feedback Subsystem
Tests in-memory procedural audio synthesis, WAV encoding, Win32 transparent layered window lifecycle,
GDI resource leak prevention, and state transitions.
"""

from __future__ import annotations

import ctypes
import io
import time
import unittest
from unittest.mock import MagicMock, patch
import wave

from extra.core.platform.base import AbstractIndicatorController
from extra.core.platform.windows.indicators import (
    AudioIndicator,
    IndicatorController,
    IndicatorWorkerThread,
    get_indicator_controller,
)


class TestWindowsAudioIndicator(unittest.TestCase):
    """Tests for Windows procedural audio feedback synthesis and caching."""

    def setUp(self):
        self.audio = AudioIndicator()

    def test_synthesize_wav_format_complete(self):
        wav_bytes = self.audio._synthesize("complete")
        self.assertGreater(len(wav_bytes), 1000)

        with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
            self.assertEqual(wf.getnchannels(), 1)
            self.assertEqual(wf.getsampwidth(), 2)  # 16-bit
            self.assertEqual(wf.getframerate(), 44100)
            self.assertGreater(wf.getnframes(), 0)

    def test_synthesize_wav_format_start(self):
        wav_bytes = self.audio._synthesize("start")
        self.assertGreater(len(wav_bytes), 1000)

        with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
            self.assertEqual(wf.getnchannels(), 1)
            self.assertEqual(wf.getsampwidth(), 2)
            self.assertEqual(wf.getframerate(), 44100)
            self.assertGreater(wf.getnframes(), 0)

    def test_synthesize_wav_format_alert_and_error(self):
        for profile in ("alert", "error"):
            wav_bytes = self.audio._synthesize(profile)
            self.assertGreater(len(wav_bytes), 1000)
            with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
                self.assertEqual(wf.getnchannels(), 1)
                self.assertEqual(wf.getsampwidth(), 2)
                self.assertEqual(wf.getframerate(), 44100)
                self.assertGreater(wf.getnframes(), 0)

    def test_synthesize_wav_format_attention(self):
        wav_bytes = self.audio._synthesize("attention")
        self.assertGreater(len(wav_bytes), 1000)

        with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
            self.assertEqual(wf.getnchannels(), 1)
            self.assertEqual(wf.getsampwidth(), 2)
            self.assertEqual(wf.getframerate(), 44100)
            self.assertGreater(wf.getnframes(), 0)

    def test_audio_cache(self):
        b1 = self.audio._synthesize("complete")
        b2 = self.audio._synthesize("complete")
        self.assertIs(b1, b2)

    @patch("winsound.PlaySound")
    def test_audio_play_async(self, mock_play):
        self.audio.play("start")
        time.sleep(0.05)  # Allow daemon thread to run
        mock_play.assert_called_once()
        args, kwargs = mock_play.call_args
        self.assertIsInstance(args[0], bytes)


class TestWindowsIndicatorController(unittest.TestCase):
    """Tests for Windows indicator controller, lifecycle, GDI hygiene, and window visibility."""

    def test_abstract_interface_compliance(self):
        ctrl = get_indicator_controller()
        self.assertIsInstance(ctrl, AbstractIndicatorController)
        self.assertIsInstance(ctrl, IndicatorController)

    def test_singleton_instance(self):
        c1 = get_indicator_controller()
        c2 = IndicatorController.get_instance()
        self.assertIs(c1, c2)

    def test_task_indicate_status_routing(self):
        ctrl = get_indicator_controller()
        with patch.object(ctrl, "task_start") as mock_start, \
             patch.object(ctrl, "task_complete") as mock_complete, \
             patch.object(ctrl, "task_stop") as mock_stop:

            ctrl.task_indicate_status("active", "Testing Active", play_sound=False)
            mock_start.assert_called_once_with(task_name="Testing Active", play_chime=False)

            ctrl.task_indicate_status("done", "Testing Done", play_sound=True)
            mock_complete.assert_called_with(summary="Testing Done", success=True, play_chime=True)

            ctrl.task_indicate_status("error", "Testing Error", play_sound=True)
            mock_complete.assert_called_with(summary="Testing Error", success=False, play_chime=True)

            ctrl.task_indicate_status("idle")
            mock_stop.assert_called_once()

    def test_gdi_resource_zero_leak(self):
        """Verifies that rendering 200 reticle and bloom frames does not leak GDI handles."""
        u32 = ctypes.windll.user32
        k32 = ctypes.windll.kernel32
        u32.GetGuiResources.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        u32.GetGuiResources.restype = ctypes.c_uint
        k32.GetCurrentProcess.restype = ctypes.c_void_p
        h_proc = k32.GetCurrentProcess()

        ctrl = get_indicator_controller()
        worker = ctrl._worker
        self.assertIsNotNone(worker)

        # Warm up
        worker._draw_tactical_reticle(shockwave_radius=20, shockwave_alpha_ratio=0.8, flash_center=True)
        worker._draw_edge_bloom(worker.ACTIVE_BLOOM_BANDS)

        initial_gdi = u32.GetGuiResources(h_proc, 0)
        for _ in range(100):
            worker._draw_tactical_reticle(shockwave_radius=25, shockwave_alpha_ratio=0.5, flash_center=True)
            worker._draw_edge_bloom(worker.ACTIVE_BLOOM_BANDS)
        final_gdi = u32.GetGuiResources(h_proc, 0)

        leaked = final_gdi - initial_gdi
        self.assertEqual(leaked, 0, f"Detected GDI handle leak: {leaked} handles leaked!")

    def test_completion_visibility_from_idle(self):
        """Verifies that task_complete from IDLE state ensures hwnd_edge is made visible."""
        import win32gui
        ctrl = get_indicator_controller()
        worker = ctrl._worker
        self.assertIsNotNone(worker)

        # Force state to IDLE
        ctrl.task_stop()
        time.sleep(0.1)
        self.assertEqual(worker.state, "IDLE")

        # Now trigger completion
        ctrl.task_complete("Task Completed from Idle", success=True, play_chime=False)
        time.sleep(0.1)

        # State must be COMPLETING and hwnd_edge MUST be visible
        self.assertEqual(worker.state, "COMPLETING")
        is_visible = win32gui.IsWindowVisible(worker.hwnd_edge)
        self.assertTrue(is_visible, "hwnd_edge must be visible during COMPLETING state even when triggered from IDLE!")

        # Stop afterwards
        ctrl.task_stop()


if __name__ == "__main__":
    unittest.main()
