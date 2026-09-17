"""
Project Extra — Cross-Platform Shell Fast-Path Engine
Deterministic, zero-latency application and system utility launcher,
bypassing visual desktop searching on Windows and macOS.
"""

from __future__ import annotations

import sys
from typing import Dict, List, Optional, Tuple

from extra.core.platform import (
    LaunchResult,
    launch_app,
    open_uri,
    resolve_executable,
)

if sys.platform == "darwin":
    from extra.core.platform.macos.shell import (
        MAC_APP_REGISTRY as APP_REGISTRY,
        BUILTIN_MAC_APP_REGISTRY as BUILTIN_APP_REGISTRY,
        get_registered_apps,
        get_user_registry_path,
        load_user_registry,
        register_app,
    )
    BROWSER_CANDIDATE_PATHS = {}
else:
    from extra.core.platform.windows.shell import (
        APP_REGISTRY,
        BROWSER_CANDIDATE_PATHS,
        BUILTIN_APP_REGISTRY,
        get_registered_apps,
        get_user_registry_path,
        load_user_registry,
        register_app,
    )

__all__ = [
    "APP_REGISTRY",
    "BUILTIN_APP_REGISTRY",
    "BROWSER_CANDIDATE_PATHS",
    "LaunchResult",
    "launch_app",
    "open_uri",
    "resolve_executable",
    "register_app",
    "load_user_registry",
    "get_registered_apps",
    "get_user_registry_path",
]
