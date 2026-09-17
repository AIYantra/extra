"""
Unit tests for Extra Scout subsystem (detector, scraper, synthesizer).
"""

import os
import shutil
import unittest
from pathlib import Path

from extra.core.scout.detector import detect_app_profile, AppProfile
from extra.core.scout.scraper import get_app_intelligence
from extra.core.scout.synthesizer import scout_and_generate_skill, format_skill_markdown


class TestExtraScout(unittest.TestCase):
    def test_detect_known_profiles(self):
        """Tests application profile detection for pro tools and canvas apps."""
        blender_prof = detect_app_profile("blender")
        self.assertEqual(blender_prof.ui_framework, "directx_opengl_viewport")
        self.assertIn("bpy", (blender_prof.scripting_api or "").lower())

        canva_prof = detect_app_profile("canva")
        self.assertEqual(canva_prof.ui_framework, "electron_web_canvas")

        calc_prof = detect_app_profile("calc")
        self.assertIsNotNone(calc_prof.scripting_api)

    def test_get_app_intelligence_curated(self):
        """Tests retrieval of curated hotkeys and zero-stall fast paths."""
        blender_prof = detect_app_profile("blender")
        intel = get_app_intelligence("blender", blender_prof)

        self.assertIn("fast_paths", intel)
        self.assertIn("hotkeys", intel)
        self.assertIn("anti_stall_guardrails", intel)

        # Check key shortcuts
        hotkey_keys = [hk["key"] for hk in intel["hotkeys"]]
        self.assertIn("Tab", hotkey_keys)
        self.assertIn("Shift + A", hotkey_keys)
        self.assertIn("F12", hotkey_keys)

        # Check fast-paths
        fast_path_text = " ".join(intel["fast_paths"])
        self.assertIn("-b", fast_path_text)
        self.assertIn("bpy", fast_path_text)

    def test_format_skill_markdown(self):
        """Tests that generated markdown conforms to agentskills.io format."""
        profile = AppProfile(
            app_name="testapp",
            ui_framework="win32",
            is_installed=True,
            scripting_api="CLI",
        )
        intel = {
            "summary": "Test application overview.",
            "ui_surface_caveat": "Standard win32 window.",
            "fast_paths": ["Use CLI flag --test"],
            "hotkeys": [{"key": "Ctrl + T", "action": "New Tab", "category": "General"}],
            "cli_options": [{"flag": "--test", "description": "Run test", "example": "testapp --test"}],
            "anti_stall_guardrails": ["Do not click blindly."],
        }

        md = format_skill_markdown("testapp", profile, intel)
        self.assertTrue(md.startswith("---\nname: extra-testapp\n"))
        self.assertIn("description:", md)
        self.assertIn("# Testapp Desktop Automation Protocol", md)
        self.assertIn("`Ctrl + T`", md)
        self.assertIn("`--test`", md)

    def test_scout_and_generate_skill_execution(self):
        """Tests end-to-end skill scouting and generation."""
        res = scout_and_generate_skill("blender", force_refresh=True)
        self.assertEqual(res["status"], "generated")
        self.assertEqual(res["ui_framework"], "directx_opengl_viewport")
        self.assertGreater(res["hotkey_count"], 5)
        self.assertTrue(len(res["skill_paths"]) > 0)

        # Verify generated file exists and has frontmatter
        skill_file = Path(res["skill_paths"][0])
        self.assertTrue(skill_file.exists())
        content = skill_file.read_text(encoding="utf-8")
        self.assertIn("name: extra-blender", content)
        self.assertIn("blender.exe -b", content)


if __name__ == "__main__":
    unittest.main()
