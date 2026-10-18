"""
Project Extra — Fast-Path Accelerators
Direct application launch and Playwright DOM extraction without visual overhead.
"""

from extra.fastpath.browser import (
    BrowserFastPath,
    execute_browser_action,
    get_browser_fastpath,
)
from extra.fastpath.cli_harness import (
    HarnessResult,
    UniversalHarnessRunner,
    execute_harness,
    is_harness_available,
    resolve_harness,
)
from extra.fastpath.cli_hub import (
    CliHubManager,
    get_cli_hub,
)
from extra.fastpath.fs import execute_fs_batch
from extra.fastpath.shell import (
    LaunchResult,
    launch_app,
    open_uri,
    resolve_executable,
)

from extra.fastpath.visualizer import (
    DualPlaneVisualizer,
    visualize_harness_outcome,
)
from extra.fastpath.web_workspace import (
    WorkspaceExportProvider,
    configure_workspace_browser_flags,
    extract_workspace_info,
    get_official_export_url,
    register_workspace_provider,
    trigger_workspace_export,
)
from extra.fastpath.vectorizer import (
    extract_vector_strokes,
    generate_vectorizer_preview,
)

__all__ = [
    "LaunchResult",
    "launch_app",
    "resolve_executable",
    "open_uri",
    "BrowserFastPath",
    "get_browser_fastpath",
    "execute_browser_action",
    "execute_fs_batch",
    "HarnessResult",
    "UniversalHarnessRunner",
    "execute_harness",
    "resolve_harness",
    "is_harness_available",
    "CliHubManager",
    "get_cli_hub",
    "DualPlaneVisualizer",
    "visualize_harness_outcome",
    "WorkspaceExportProvider",
    "register_workspace_provider",
    "extract_workspace_info",
    "get_official_export_url",
    "configure_workspace_browser_flags",
    "trigger_workspace_export",
    "extract_vector_strokes",
    "generate_vectorizer_preview",
]

