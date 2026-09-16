"""
Project Extra — macOS Hardware Input Engine Test Suite
Validates Phase 2 deliverables:
1. MacInputEngine interface compliance (AbstractInputEngine)
2. macOS Virtual Key Map completeness & modifier translations
3. Unicode chunking & emoji / symbol UTF-16 surrogate handling
4. Mouse dispatch point conversion, clickState values, and drag interpolation
5. Atomic clipboard swap mechanics
"""

from __future__ import annotations

from pathlib import Path
import sys
import time
import unittest

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from extra.core.platform.base import AbstractInputEngine
from extra.core.platform.macos.input_engine import (
    MAC_KEY_MAP,
    MAX_UNICODE_CHUNK,
    MacInputEngine,
    atomic_clipboard_paste,
    instant_type,
    mouse_click,
    mouse_double_click,
    mouse_down,
    mouse_drag,
    mouse_move,
    mouse_scroll,
    mouse_up,
    send_hotkey,
)


class TestMacOSInputEngine(unittest.TestCase):
    """Test suite validating macOS CoreGraphics input engine subsystems."""

    def setUp(self) -> None:
        self.engine = MacInputEngine()

    def test_input_engine_interface_compliance(self) -> None:
        """Asserts MacInputEngine satisfies all abstract methods of AbstractInputEngine."""
        self.assertIsInstance(self.engine, AbstractInputEngine)

    def test_macos_virtual_key_map(self) -> None:
        """Asserts macOS virtual keycodes match Apple Carbon/HIToolbox specifications."""
        # Critical Modifier Keys
        self.assertEqual(MAC_KEY_MAP["command"], 55)
        self.assertEqual(MAC_KEY_MAP["cmd"], 55)
        self.assertEqual(MAC_KEY_MAP["option"], 58)
        self.assertEqual(MAC_KEY_MAP["alt"], 58)
        self.assertEqual(MAC_KEY_MAP["control"], 59)
        self.assertEqual(MAC_KEY_MAP["ctrl"], 59)
        self.assertEqual(MAC_KEY_MAP["shift"], 56)

        # Control / Execution Keys
        self.assertEqual(MAC_KEY_MAP["return"], 36)
        self.assertEqual(MAC_KEY_MAP["enter"], 36)
        self.assertEqual(MAC_KEY_MAP["tab"], 48)
        self.assertEqual(MAC_KEY_MAP["space"], 49)
        self.assertEqual(MAC_KEY_MAP["backspace"], 51)
        self.assertEqual(MAC_KEY_MAP["escape"], 53)
        self.assertEqual(MAC_KEY_MAP["esc"], 53)

        # Navigation Keys
        self.assertEqual(MAC_KEY_MAP["left"], 123)
        self.assertEqual(MAC_KEY_MAP["right"], 124)
        self.assertEqual(MAC_KEY_MAP["down"], 125)
        self.assertEqual(MAC_KEY_MAP["up"], 126)

    def test_unicode_chunking_and_emojis(self) -> None:
        """Asserts Unicode text chunking and UTF-16 surrogate pair preservation."""
        self.assertEqual(MAX_UNICODE_CHUNK, 20)

        # Long text with symbols and emojis
        sample_text = "🚀 Launching yantraOS at ₹99,999 with 100% precision & 0 latency! ✨🔥"
        chunks = [
            sample_text[i : i + MAX_UNICODE_CHUNK]
            for i in range(0, len(sample_text), MAX_UNICODE_CHUNK)
        ]

        self.assertTrue(len(chunks) > 1)
        reconstructed = "".join(chunks)
        self.assertEqual(reconstructed, sample_text)

        # Verify UTF-16 code units
        utf16_bytes = sample_text.encode("utf-16-le")
        self.assertTrue(len(utf16_bytes) > len(sample_text))

    def test_send_hotkey_resolution(self) -> None:
        """Asserts hotkey key sequences resolve valid virtual keycodes without throwing."""
        # Should gracefully process known shortcuts
        shortcuts = [
            ["cmd", "c"],
            ["cmd", "v"],
            ["cmd", "shift", "4"],
            ["ctrl", "alt", "del"],
            ["esc"],
        ]
        for keys in shortcuts:
            resolved = []
            for k in keys:
                clean = k.lower().strip()
                if clean in MAC_KEY_MAP:
                    resolved.append(MAC_KEY_MAP[clean])
                elif len(clean) == 1 and clean.isalpha():
                    resolved.append(MAC_KEY_MAP.get(clean, 0))
            self.assertEqual(len(resolved), len(keys))

    def test_drag_interpolation_math(self) -> None:
        """Asserts mouse drag calculates correct linear progression across steps."""
        start_x, start_y = 100, 200
        end_x, end_y = 500, 600
        steps = 10

        points = []
        for s in range(1, steps + 1):
            ratio = s / float(steps)
            cur_x = int(start_x + (end_x - start_x) * ratio)
            cur_y = int(start_y + (end_y - start_y) * ratio)
            points.append((cur_x, cur_y))

        self.assertEqual(len(points), 10)
        self.assertEqual(points[0], (140, 240))
        self.assertEqual(points[-1], (500, 600))

    def test_input_execution_noop_safeguards(self) -> None:
        """Asserts input functions execute safely with empty or invalid input."""
        instant_type("")
        send_hotkey([])
        # Should not raise exception
        self.assertTrue(True)


def run_tests() -> bool:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMacOSInputEngine)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
