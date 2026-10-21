"""
Project Extra — Test Harness Configuration & Partitioning Fixtures
Provides automatic test suite categorization, platform gating, and benchmark markers.
"""

import sys
import pytest


def pytest_configure(config):
    """Register custom markers dynamically if not present in pyproject.toml."""
    config.addinivalue_line("markers", "unit: Fast isolated unit tests with zero system dependencies")
    config.addinivalue_line("markers", "integration: Subsystem integration tests")
    config.addinivalue_line("markers", "windows: Tests requiring Windows Win32 / UIA subsystems")
    config.addinivalue_line("markers", "linux: Tests requiring Linux X11 / Wayland / AT-SPI2 subsystems")
    config.addinivalue_line("markers", "macos: Tests requiring macOS Quartz / Accessibility subsystems")
    config.addinivalue_line("markers", "benchmark: Performance profiling and stress benchmark suites")
    config.addinivalue_line("markers", "security: Security audit and vulnerability verification tests")


def pytest_collection_modifyitems(config, items):
    """
    Categorizes collected tests dynamically based on filename patterns and applies platform skips.
    """
    current_platform = sys.platform

    for item in items:
        file_name = item.path.name.lower()

        # 1. Benchmark Suites
        if "benchmark" in file_name or "acceleration" in file_name:
            item.add_marker(pytest.mark.benchmark)

        # 2. Security Suites
        if "security" in file_name:
            item.add_marker(pytest.mark.security)

        # 3. macOS Subsystems
        if file_name.startswith("test_macos_") or "pillar3_tcc" in file_name:
            item.add_marker(pytest.mark.macos)
            if current_platform != "darwin":
                item.add_marker(pytest.mark.skip(reason=f"Requires macOS host (current: {current_platform})"))

        # 4. Linux Subsystems
        elif file_name.startswith("test_linux_"):
            item.add_marker(pytest.mark.linux)
            if current_platform != "linux":
                item.add_marker(pytest.mark.skip(reason=f"Requires Linux host (current: {current_platform})"))

        # 5. Windows Subsystems
        elif file_name.startswith("test_windows_") or file_name in ("test_child_session.py", "test_pip_window.py"):
            item.add_marker(pytest.mark.windows)
            if current_platform != "win32":
                item.add_marker(pytest.mark.skip(reason=f"Requires Windows host (current: {current_platform})"))

        # 6. Default to unit / integration
        else:
            if "harness" in file_name or "director" in file_name or "mcp" in file_name or "distiller" in file_name:
                item.add_marker(pytest.mark.integration)
            else:
                item.add_marker(pytest.mark.unit)
