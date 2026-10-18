"""
Unit tests for Project Extra — Linux Ambient Awareness & Audio Feedback Subsystem
Tests procedural acoustic glass synthesis, D-Bus notification dispatch,
overlay state transitions, and indicator lifecycle states.
"""

from __future__ import annotations

import io
import time
import unittest
from unittest.mock import MagicMock, patch
import wave

from extra.core.platform.base import AbstractIndicatorController
from extra.core.platform.linux.indicators import (
    AudioIndicator,
    IndicatorController,
    LinuxIndicatorController,
    LinuxIndicatorOverlay,
    LinuxNotificationNotifier,
    get_indicator_controller,
)


class TestLinuxIndicators(unittest.TestCase):
    """Tests for Linux audio feedback, D-Bus notifications, and ambient awareness overlay."""

    def setUp(self):
        self.audio = AudioIndicator()

    def test_abstract_interface_compliance(self):
        controller = get_indicator_controller()
        self.assertIsInstance(controller, AbstractIndicatorController)
        self.assertIsInstance(controller, LinuxIndicatorController)
        self.assertIs(IndicatorController, LinuxIndicatorController)

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

    def test_synthesize_wav_format_alert(self):
        wav_bytes = self.audio._synthesize("alert")
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

    @patch("extra.core.platform.linux.indicators.subprocess.Popen")
    @patch("extra.core.platform.linux.indicators.shutil.which")
    def test_audio_play_pwplay_async(self, mock_which, mock_popen):
        mock_which.side_effect = lambda cmd: "/usr/bin/pw-play" if cmd == "pw-play" else None
        mock_proc = MagicMock()
        mock_popen.return_value = mock_proc

        self.audio.play("start")
        time.sleep(0.05)  # Wait for async thread

        mock_popen.assert_called_once()
        args, kwargs = mock_popen.call_args
        self.assertEqual(args[0], ["pw-play", "-"])
        mock_proc.communicate.assert_called_once()

    def test_notification_notifier_dbus(self):
        try:
            import jeepney
        except ImportError:
            self.skipTest("jeepney is not installed on this system")
        notifier = LinuxNotificationNotifier()
        with patch("jeepney.io.blocking.open_dbus_connection") as mock_conn_fn:
            mock_conn = MagicMock()
            mock_reply = MagicMock()
            mock_reply.body = (42,)
            mock_conn.send_and_get_reply.return_value = mock_reply
            mock_conn_fn.return_value = mock_conn

            nid = notifier.notify(
                summary="Test Summary",
                body="Test Body",
                icon="dialog-information",
                urgency=1,
            )
            self.assertEqual(nid, 42)
            mock_conn.send_and_get_reply.assert_called_once()
            mock_conn.close.assert_called_once()

    def test_notification_notifier_notify_send_fallback(self):
        notifier = LinuxNotificationNotifier()
        # Mock jeepney failure to test notify-send fallback
        with patch.dict("sys.modules", {"jeepney": None}):
            with patch("extra.core.platform.linux.indicators.shutil.which", return_value="/usr/bin/notify-send"):
                with patch("extra.core.platform.linux.indicators.subprocess.Popen") as mock_popen:
                    nid = notifier.notify("Fallback Summary", "Fallback Body")
                    self.assertEqual(nid, 1)
                    mock_popen.assert_called_once()
                    args = mock_popen.call_args[0][0]
                    self.assertEqual(args[0], "notify-send")
                    self.assertIn("Fallback Summary", args)

    def test_overlay_state_machine(self):
        overlay = LinuxIndicatorOverlay()
        self.assertTrue(overlay.setup())

        # Active
        overlay.show_active()
        self.assertEqual(overlay.current_mode, "active")
        self.assertTrue(overlay.is_visible)

        # Complete
        overlay.show_complete()
        self.assertEqual(overlay.current_mode, "complete")
        self.assertTrue(overlay.is_visible)

        # Alert
        overlay.show_alert()
        self.assertEqual(overlay.current_mode, "alert")
        self.assertTrue(overlay.is_visible)

        # Hide
        overlay.hide()
        self.assertEqual(overlay.current_mode, "idle")
        self.assertFalse(overlay.is_visible)

    def test_indicator_controller_task_lifecycle(self):
        controller = LinuxIndicatorController()
        with patch.object(controller.audio, "play") as mock_audio:
            with patch.object(controller.notifier, "notify") as mock_notify:
                # 1. Start
                controller.task_start(task_name="Autonomous Task")
                self.assertEqual(controller.overlay.current_mode, "active")
                self.assertTrue(controller.overlay.is_visible)
                mock_audio.assert_called_with("start")
                mock_notify.assert_called_once()

                # 2. Action
                controller.task_action("click", x=100, y=200)

                # 3. Complete
                controller.task_complete(summary="Task finished", success=True)
                self.assertEqual(controller.overlay.current_mode, "complete")
                mock_audio.assert_called_with("complete")

                # Auto-hide wait
                time.sleep(0.7)
                self.assertEqual(controller.overlay.current_mode, "idle")
                self.assertFalse(controller.overlay.is_visible)

    def test_indicator_controller_indicate_status_dispatch(self):
        controller = LinuxIndicatorController()
        with patch.object(controller, "task_start") as mock_start:
            with patch.object(controller, "task_complete") as mock_complete:
                with patch.object(controller, "stop") as mock_stop:
                    controller.task_indicate_status("active", "Running step")
                    mock_start.assert_called_with(task_name="Running step")

                    controller.task_indicate_status("complete", "Done step")
                    mock_complete.assert_called_with(summary="Done step", success=True, play_chime=True)

                    controller.task_indicate_status("error", "Error step")
                    mock_complete.assert_called_with(summary="Error step", success=False, play_chime=True)

                    controller.task_indicate_status("idle")
                    mock_stop.assert_called_once()

    def test_pulse_momentary_glow(self):
        controller = LinuxIndicatorController()
        controller.pulse("cyan")
        self.assertEqual(controller.overlay.current_mode, "active")
        self.assertTrue(controller.overlay.is_visible)

        time.sleep(0.5)
        self.assertEqual(controller.overlay.current_mode, "idle")
        self.assertFalse(controller.overlay.is_visible)


if __name__ == "__main__":
    unittest.main()
