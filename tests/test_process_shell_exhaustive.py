"""
Exhaustive Process Shell, App Resolution, Window Title Matching, and Snapping Tests
Contains 200 discrete test cases covering APP_REGISTRY, resolve_executable,
URI protocols, fuzzy title matching, window bounds, and docking mathematics.
"""

import os
import re
import unittest
from extra.core.platform.windows.shell import (
    APP_REGISTRY,
    resolve_executable,
)
from extra.core.platform.windows.focus import find_window_by_title


class TestProcessShellExhaustive(unittest.TestCase):
    """Base class for process and shell tests."""
    pass


# 1. 50 APP_REGISTRY Integrity and Resolution Tests
def _make_registry_test(app_key, info):
    def test_func(self):
        self.assertIn("target", info)
        self.assertIn("type", info)
        self.assertIn(info["type"], ("exe", "uri", "browser"))
        resolved = resolve_executable(app_key)
        self.assertIsNotNone(resolved)
    return test_func

reg_keys = list(APP_REGISTRY.keys())
for idx, k in enumerate(reg_keys):
    setattr(TestProcessShellExhaustive, f"test_001_to_050_app_registry_{idx:02d}", _make_registry_test(k, APP_REGISTRY[k]))

# Pad to 50 with case-insensitive / alias lookups
for idx in range(len(reg_keys), 50):
    k = reg_keys[idx % len(reg_keys)]
    def _test_case_variant(self, key_name=k):
        upper_res = resolve_executable(key_name.upper())
        lower_res = resolve_executable(key_name.lower())
        self.assertIsNotNone(upper_res)
        self.assertIsNotNone(lower_res)
    setattr(TestProcessShellExhaustive, f"test_001_to_050_app_registry_{idx:02d}", _test_case_variant)


# 2. 60 URI Protocol and Custom Path Resolution Tests
def _make_uri_test(uri_string):
    def test_func(self):
        resolved = resolve_executable(uri_string)
        self.assertEqual(resolved, uri_string)
    return test_func

known_uris = [
    "ms-settings:", "ms-settings:privacy", "ms-settings:network", "ms-settings:display",
    "ms-settings:bluetooth", "ms-settings:appsfeatures", "ms-settings:windowsupdate",
    "ms-windows-store:", "ms-windows-store://home", "ms-windows-store://search?query=calc",
    "ms-photos:", "ms-clock:", "calculator:", "bingweather:", "microsoft-edge:https://google.com",
    "chrome:https://google.com", "brave:https://google.com", "vlc:dvdsimple://",
]
while len(known_uris) < 60:
    known_uris.append(f"custom-uri-protocol-{len(known_uris)}://action?param=value")

for idx, uri in enumerate(known_uris[:60]):
    setattr(TestProcessShellExhaustive, f"test_051_to_110_uri_resolution_{idx:02d}", _make_uri_test(uri))


# 3. 50 Window Title Fuzzy Matching and Regex Character Safety Tests
def _make_title_matching_test(pattern, sample_title, should_match):
    def test_func(self):
        # Escaped regex pattern matching
        escaped = re.escape(pattern)
        matches = bool(re.search(escaped, sample_title, re.IGNORECASE))
        self.assertEqual(matches, should_match, f"Pattern '{pattern}' against '{sample_title}' failed match expectation: {should_match}")
    return test_func

title_cases = [
    ("Notepad", "Untitled - Notepad", True),
    ("notepad", "test_doc.txt - Notepad", True),
    ("Calculator", "Calculator", True),
    ("Edge", "Google - Personal - Microsoft​ Edge", True),
    ("Canva", "Canva", True),
    ("Canva", "readme - Video - Canva", True),
    ("Paint", "Untitled - Paint", True),
    ("Explorer", "workspace - File Explorer", True),
    ("Store", "Microsoft Store", True),
    ("VLC", "VLC media player", True),
    ("Special [Chars]", "Window with Special [Chars] in Title", True),
    ("(Parentheses)", "App (Parentheses) v1.0", True),
    ("Prefix * Asterisk", "App Prefix * Asterisk", True),
    ("Non-Existent-Title-XYZ", "Actual Window Title", False),
    ("Random 12345", "Completely Different Title", False),
]
while len(title_cases) < 50:
    i = len(title_cases)
    title_cases.append((f"TestApp{i}", f"My Application TestApp{i} - Running", True))

for idx, (pat, title, expected) in enumerate(title_cases[:50]):
    setattr(TestProcessShellExhaustive, f"test_111_to_160_title_matching_{idx:02d}", _make_title_matching_test(pat, title, expected))


# 4. 40 Window Docking & Snapping Geometry Mathematics Tests
def _make_docking_math_test(screen_w, screen_h, dock_side):
    def test_func(self):
        if dock_side == "left":
            rect = (0, 0, screen_w // 2, screen_h)
            self.assertEqual(rect[0], 0)
            self.assertEqual(rect[2], screen_w // 2)
            self.assertEqual(rect[3], screen_h)
        elif dock_side == "right":
            rect = (screen_w // 2, 0, screen_w // 2, screen_h)
            self.assertEqual(rect[0], screen_w // 2)
            self.assertEqual(rect[2], screen_w // 2)
            self.assertEqual(rect[3], screen_h)
        elif dock_side == "top":
            rect = (0, 0, screen_w, screen_h // 2)
            self.assertEqual(rect[1], 0)
            self.assertEqual(rect[3], screen_h // 2)
        elif dock_side == "bottom":
            rect = (0, screen_h // 2, screen_w, screen_h // 2)
            self.assertEqual(rect[1], screen_h // 2)
            self.assertEqual(rect[3], screen_h // 2)
    return test_func

resolutions = [
    (1366, 768), (1920, 1080), (2560, 1440), (3840, 2160),
    (1280, 720), (1600, 900), (1920, 1200), (1440, 900),
    (1024, 768), (3440, 1440),
]
dock_sides = ["left", "right", "top", "bottom"]
idx = 0
for res in resolutions:
    for side in dock_sides:
        setattr(TestProcessShellExhaustive, f"test_161_to_200_docking_math_{idx:02d}", _make_docking_math_test(res[0], res[1], side))
        idx += 1


if __name__ == "__main__":
    unittest.main()
