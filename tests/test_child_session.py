"""
Project Extra — Win32 Child Session & Picture-in-Picture (PiP) Test Suite
Verifies capability detection, Virtual Desktop creation/lifecycle,
and Picture-in-Picture preview window rendering.
"""

import os
import sys
import time
import unittest
from pathlib import Path

if sys.platform != "win32":
    raise unittest.SkipTest("Windows-only PiP and Child Session test suite")

import pytest
from PIL import Image

# Ensure extra project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extra.core.platform.windows.child_session import (
    ChildSessionCapability,
    ChildSessionManager,
    SessionTier,
    VirtualDesktop,
    detect_child_session_capabilities,
    get_child_session_manager,
)
from extra.core.platform.windows.pip_window import PiPPreviewWindow, get_pip_window


def test_child_session_capabilities_detection():
    """Verifies that OS edition, privileges, and isolation tiers are accurately detected."""
    caps = detect_child_session_capabilities()
    assert isinstance(caps, ChildSessionCapability)
    assert caps.os_edition != "", "OS edition must not be empty"
    assert caps.recommended_tier in (
        SessionTier.TIER_1_NATIVE_CHILD_SESSION,
        SessionTier.TIER_2_VIRTUAL_DESKTOP,
        SessionTier.TIER_3_PLANE_2_FASTPATH,
    )
    assert isinstance(caps.can_virtual_desktop, bool)
    assert isinstance(caps.can_native_child_session, bool)
    assert isinstance(caps.is_admin, bool)

    data = caps.to_dict()
    assert "recommended_tier" in data
    assert "os_edition" in data


def test_virtual_desktop_lifecycle():
    """Verifies creating, attaching to, and closing an isolated Win32 Desktop."""
    desktop_name = f"Extra_TestDesk_{int(time.time()*1000)}"
    desk = VirtualDesktop(name=desktop_name)

    created = desk.create()
    assert created is True, "Failed to create Win32 Virtual Desktop"
    assert desk.handle is not None and desk.handle > 0, "Invalid desktop handle"

    # Test thread attachment on a clean worker thread (Win32 requires thread to have 0 windows)
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        attached = pool.submit(desk.attach_current_thread).result(timeout=2.0)
        assert attached is True, "Failed to attach clean worker thread to virtual desktop"

        detached = pool.submit(desk.detach_current_thread).result(timeout=2.0)
        assert detached is True, "Failed to detach worker thread from virtual desktop"

    # Test clean teardown
    desk.close()
    assert desk.handle is None, "Desktop handle should be None after close"


def test_virtual_desktop_name_validation():
    """Verifies that invalid or dangerous desktop names are rejected."""
    with pytest.raises(ValueError, match="Invalid desktop name"):
        VirtualDesktop(name="../../traversal")
    with pytest.raises(ValueError, match="Invalid desktop name"):
        VirtualDesktop(name="Bad Name With Spaces")
    with pytest.raises(ValueError, match="Invalid desktop name"):
        VirtualDesktop(name="Bad;Name&Pipe")
    with pytest.raises(ValueError, match="Invalid desktop name"):
        VirtualDesktop(name="A" * 65)  # Exceeds max length


def test_child_session_manager_auto_routing():
    """Verifies that ChildSessionManager auto-selects and starts the optimal isolation tier."""
    mgr = ChildSessionManager(desktop_name=f"Extra_MgrDesk_{int(time.time()*1000)}")
    assert mgr.is_active() is False

    started = mgr.start()
    assert started is True, "Failed to start ChildSessionManager"
    assert mgr.is_active() is True
    assert mgr.get_active_tier() is not None

    status = mgr.get_status()
    assert status["is_active"] is True
    assert status["active_tier"] == mgr.get_active_tier().value

    mgr.stop()
    assert mgr.is_active() is False
    assert mgr.get_active_tier() is None


def test_pip_preview_window_lifecycle():
    """Verifies starting, updating frames, and stopping the native PiP preview window."""
    pip = PiPPreviewWindow(title="Extra Unit Test PiP", width=320, height=180)
    started = pip.start()
    assert started is True, "Failed to start native PiP window"
    assert pip.is_visible() is True
    assert pip.hwnd is not None

    # Push a test frame
    test_img = Image.new("RGB", (320, 180), color=(30, 90, 180))
    pip.update_frame(test_img)

    time.sleep(0.2)
    pip.stop()
    assert pip.is_visible() is False


def test_child_session_mcp_tools():
    """Verifies that MCP tools correctly expose child session status and PiP control."""
    from extra.mcp.server import extra_child_session_status, extra_pip_control

    status_res = extra_child_session_status()
    assert status_res["success"] is True
    assert status_res["supported"] is True
    assert "capabilities" in status_res

    # Test PiP control query
    pip_query = extra_pip_control("status")
    assert pip_query["success"] is True
    assert pip_query["is_visible"] is False

    # Test PiP control start
    start_res = extra_pip_control("start")
    assert start_res["success"] is True
    assert start_res["is_visible"] is True
    assert start_res["hwnd"] is not None

    # Test PiP control stop
    stop_res = extra_pip_control("stop")
    assert stop_res["success"] is True
    assert stop_res["is_visible"] is False

