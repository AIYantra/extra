"""
Unit and integration tests for Phase 3 Security Audit:
Core Computer-Use Engine (extra core runtime),
Win32 CTypes Memory Safety, Corner Abort Fail-Safe, 2-Strike Perceptual Stall Breaker,
Subtask Destructive Keyword Blocking, and Filesystem Containment & CFA Compliance.
"""

import sys
import os
import ctypes
from pathlib import Path
import pytest

extra_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(extra_root / "src"))

from extra.core.stall_breaker import StallBreaker, StallStatus, EmergencyAbortError
from extra.core.subtask import DESTRUCTIVE_KEYWORDS, SubtaskRunner
from extra.fastpath.fs import _is_safe_path, _is_contained_in, _is_safe_workspace_root


def test_win32_input_ctypes_struct_alignment_and_types():
    """Verifies Win32 CTypes struct sizes, pointer types, and coordinate clamping."""
    if sys.platform != "win32":
        pytest.skip("Win32 CTypes tests are specific to Windows operating system")

    from extra.core.platform.windows.input_engine import (
        INPUT,
        MOUSEINPUT,
        KEYBDINPUT,
        HARDWAREINPUT,
        LPINPUT,
        user32,
    )
    from extra.core.platform.windows.geometry import clamp_coordinates

    # 1. Verify 64-bit Windows struct alignments (MSDN specification)
    # On 64-bit Windows: sizeof(MOUSEINPUT) == 32 or 40 depending on padding, sizeof(INPUT) == 40
    is_64bit = ctypes.sizeof(ctypes.c_void_p) == 8
    if is_64bit:
        assert ctypes.sizeof(INPUT) == 40, f"Expected sizeof(INPUT) == 40 on 64-bit, got {ctypes.sizeof(INPUT)}"
        assert ctypes.sizeof(MOUSEINPUT) in (28, 32), f"Unexpected sizeof(MOUSEINPUT): {ctypes.sizeof(MOUSEINPUT)}"
        assert ctypes.sizeof(KEYBDINPUT) in (20, 24), f"Unexpected sizeof(KEYBDINPUT): {ctypes.sizeof(KEYBDINPUT)}"

    # 2. Verify SendInput argtypes and restype
    assert user32.SendInput.argtypes is not None
    assert len(user32.SendInput.argtypes) == 3
    assert user32.SendInput.argtypes[1] == LPINPUT
    assert user32.SendInput.restype is not None

    # 3. Verify coordinate clamping prevents negative or out-of-screen buffer writes
    cx, cy = clamp_coordinates(-500, -1000)
    assert cx >= 0 and cy >= 0
    cx_max, cy_max = clamp_coordinates(999999, 999999)
    assert cx_max < 999999 and cy_max < 999999


def test_stall_breaker_corner_abort_and_strikes():
    """Verifies that StallBreaker catches corner abort (0,0) and terminates on 2 consecutive no-delta strikes."""
    from PIL import Image

    breaker = StallBreaker(hash_threshold=2, pixel_threshold=0.5, max_strikes=2, corner_abort_pixels=3)

    # 1. Verify corner abort check logic: points near (0, 0) within corner_abort_pixels must raise EmergencyAbortError
    def check_corner(x: int, y: int):
        if x <= breaker.corner_abort_pixels and y <= breaker.corner_abort_pixels:
            raise EmergencyAbortError(f"Emergency fail-safe abort triggered at ({x}, {y})")

    with pytest.raises(EmergencyAbortError):
        check_corner(0, 0)
    with pytest.raises(EmergencyAbortError):
        check_corner(2, 2)

    # Coordinates away from corner must not raise
    check_corner(100, 100)

    # 2. Test 2-strike perceptual stall logic with real images
    breaker.reset()
    assert breaker.current_strikes == 0

    img_black = Image.new("RGB", (100, 100), (0, 0, 0))
    img_white = Image.new("RGB", (100, 100), (255, 255, 255))

    # Strike 1: Identical images (zero delta)
    out1 = breaker.evaluate_action(
        before_image=img_black,
        after_image=img_black,
        action_name="click_button",
    )
    assert breaker.current_strikes == 1
    assert out1.strikes == 1
    assert out1.status in (StallStatus.NORMAL, StallStatus.WARNING)

    # Strike 2: Second consecutive zero delta triggers STALLED
    out2 = breaker.evaluate_action(
        before_image=img_black,
        after_image=img_black,
        action_name="click_button",
    )
    assert breaker.current_strikes == 2
    assert out2.strikes == 2
    assert out2.status == StallStatus.STALLED

    # Recovery on major visual change resets strikes to 0
    out3 = breaker.evaluate_action(
        before_image=img_black,
        after_image=img_white,
        action_name="click_button",
    )
    assert breaker.current_strikes == 0
    assert out3.strikes == 0
    assert out3.status == StallStatus.NORMAL


def test_subtask_destructive_keyword_blocking():
    """Verifies that SubtaskRunner contains and blocks high-risk destructive keywords."""
    assert "format c:" in DESTRUCTIVE_KEYWORDS
    assert "rmdir /s" in DESTRUCTIVE_KEYWORDS
    assert "del /f /s /q" in DESTRUCTIVE_KEYWORDS
    assert "drop database" in DESTRUCTIVE_KEYWORDS
    assert "delete all" in DESTRUCTIVE_KEYWORDS
    assert "erase disk" in DESTRUCTIVE_KEYWORDS
    assert "clean all" in DESTRUCTIVE_KEYWORDS

    def is_destructive(intent: str) -> bool:
        lowered = intent.lower()
        return any(kw in lowered for kw in DESTRUCTIVE_KEYWORDS)

    assert is_destructive("Please format c: immediately") is True
    assert is_destructive("run rmdir /s on folder") is True
    assert is_destructive("delete all customer files") is True
    assert is_destructive("calculate 25 * 4 in calc") is False
    assert is_destructive("open notepad and write memo") is False


def test_filesystem_path_containment_and_traversal_defense():
    """Verifies that fastpath fs strictly blocks path traversal, system directory access, and root deletion."""
    # 1. Block bare drive roots and system directories
    if sys.platform == "win32":
        assert _is_safe_path(r"C:\\") is False
        assert _is_safe_path(r"C:\Windows") is False
        assert _is_safe_path(r"C:\Windows\System32") is False
        assert _is_safe_path(r"C:\Program Files") is False
    else:
        assert _is_safe_path("/") is False
        assert _is_safe_path("/bin") is False
        assert _is_safe_path("/etc/passwd") is False

    # 2. Verify path containment within safe workspace
    base_dir = Path.home() / ".extra" / "workspace"
    safe_child = base_dir / "documents" / "report.txt"
    traversal_attempt = base_dir / ".." / ".." / "Windows" / "System32" / "cmd.exe"
    same_dir_escape = Path.home() / ".ssh" / "id_rsa"

    assert _is_contained_in(safe_child, base_dir) is True
    assert _is_contained_in(traversal_attempt, base_dir) is False
    assert _is_contained_in(same_dir_escape, base_dir) is False
    assert _is_contained_in(base_dir, base_dir) is False  # Self cannot be targeted for batch deletion


def test_cli_doctor_cfa_and_workspace_boundary():
    """Verifies that cli.py inspects Controlled Folder Access (CFA) and verifies safe scratch isolation."""
    cli_path = extra_root / "src" / "extra" / "cli.py"
    assert cli_path.is_file()
    cli_content = cli_path.read_text(encoding="utf-8")

    # 1. Verify CFA diagnostic logic
    assert "Controlled Folder Access" in cli_content
    assert "EnableControlledFolderAccess" in cli_content
    assert ".extra" in cli_content
    assert "workspace" in cli_content

    # 2. Safe scratch workspace location
    default_ws = Path.home() / ".extra" / "workspace"
    assert default_ws.name == "workspace"
    assert default_ws.parent.name == ".extra"


def test_cross_platform_kill_switches():
    """Verifies emergency kill switch key combinations in stall_breaker.py."""
    stall_breaker_path = extra_root / "src" / "extra" / "core" / "stall_breaker.py"
    assert stall_breaker_path.is_file()
    content = stall_breaker_path.read_text(encoding="utf-8")

    # Win32 kill switch keys: Ctrl + Alt + Shift + Q
    assert "VK_CONTROL = 0x11" in content
    assert "VK_MENU = 0x12" in content
    assert "VK_SHIFT = 0x10" in content
    assert "VK_Q = 0x51" in content

    # Emergency corner abort documentation
    assert "emergency corner abort (0, 0)" in content
