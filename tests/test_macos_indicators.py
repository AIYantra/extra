"""
Unit tests for Project Extra — macOS Ambient Awareness & Audio Feedback Engine
Tests in-memory audio synthesis, wave encoding, NSPanel overlay configuration,
and indicator lifecycle states without requiring physical macOS hardware.
"""

from __future__ import annotations

import io
import struct
import unittest
from unittest.mock import MagicMock, patch
import wave

from extra.core.platform.base import AbstractIndicatorController
from extra.core.platform.macos.indicators import (
    AudioIndicator,
    IndicatorController,
    MacIndicatorOverlay,
    get_indicator_controller,
)


class TestMacOSIndicators(unittest.TestCase):
    """Tests for macOS audio feedback and ambient awareness overlay."""

    def setUp(self):
        self.audio = AudioIndicator()

    def test_synthesize_wav_format_complete(self):
        wav_bytes = self.audio._synthesize("complete")
        self.assertGreater(len(wav_bytes), 1000)

        # Verify WAV header
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

    def test_audio_cache(self):
        b1 = self.audio._synthesize("complete")
        b2 = self.audio._synthesize("complete")
        self.assertIs(b1, b2)

    @patch("extra.core.platform.macos.indicators.NSSound")
    @patch("extra.core.platform.macos.indicators.NSData")
    def test_audio_play_nssound(self, mock_nsdata, mock_nssound):
        mock_data_obj = MagicMock()
        mock_nsdata.dataWithBytes_length_.return_value = mock_data_obj
        mock_sound_obj = MagicMock()
        mock_nssound.alloc.return_value.initWithData_.return_value = mock_sound_obj

        self.audio.play("start")
        import time

        time.sleep(0.05)  # Wait for async thread to run
        mock_nsdata.dataWithBytes_length_.assert_called()
        mock_sound_obj.play.assert_called()

    @patch("extra.core.platform.macos.indicators.NSPanel")
    @patch("extra.core.platform.macos.indicators.NSScreen")
    def test_overlay_setup_and_invisibility(self, mock_screen, mock_nspanel):
        mock_scr_instance = MagicMock()
        mock_scr_instance.frame.return_value = ((0, 0), (1920, 1080))
        mock_screen.mainScreen.return_value = mock_scr_instance

        mock_panel_instance = MagicMock()
        mock_nspanel.alloc.return_value.initWithContentRect_styleMask_backing_defer_.return_value = (
            mock_panel_instance
        )

        overlay = MacIndicatorOverlay()
        success = overlay.setup()
        self.assertTrue(success)

        # Verify critical window properties
        mock_panel_instance.setOpaque_.assert_called_with(False)
        mock_panel_instance.setIgnoresMouseEvents_.assert_called_with(True)
        # Verify NSWindowSharingNone = 0 for capture invisibility
        mock_panel_instance.setSharingType_.assert_called_with(0)

        # Test show and hide
        overlay.show_active()
        self.assertEqual(overlay.current_mode, "active")
        mock_panel_instance.orderFrontRegardless.assert_called()

        overlay.hide()
        self.assertEqual(overlay.current_mode, "idle")
        mock_panel_instance.orderOut_.assert_called()

    def test_indicator_controller_interface(self):
        ctrl = get_indicator_controller()
        self.assertIsInstance(ctrl, AbstractIndicatorController)

        # Test lifecycle methods do not throw
        ctrl.task_start("test_task")
        ctrl.task_action("move", 100, 100)
        ctrl.task_complete("done", success=True, play_chime=False)
        ctrl.task_indicate_status("active", "running")
        ctrl.task_indicate_status("complete", "finished")
        ctrl.pulse("cyan")
        ctrl.stop()


if __name__ == "__main__":
    unittest.main()
