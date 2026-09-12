"""
Project Extra — Fast-Path Accelerators
Direct application launch and Playwright DOM extraction without visual overhead.
"""

from extra.fastpath.browser import (
    BrowserFastPath,
    execute_browser_action,
    get_browser_fastpath,
)
from extra.fastpath.shell import (
    LaunchResult,
    launch_app,
    open_uri,
    resolve_executable,
)

__all__ = [
    "LaunchResult",
    "launch_app",
    "resolve_executable",
    "open_uri",
    "BrowserFastPath",
    "get_browser_fastpath",
    "execute_browser_action",
]
