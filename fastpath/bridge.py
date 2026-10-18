"""
Project Extra — Universal Execution Bridge Subsystem
Provides sandboxed, deterministic programmatic execution across diverse runtimes
(Python, PowerShell, Blender bpy, Node, CLI) without hardcoding app logic into the core engine.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger("Extra-FastPath-Bridge")

_EXTRA_HOME = Path(os.environ.get("USERPROFILE") or os.environ.get("HOME") or ".") / ".extra"
_BRIDGE_WORKSPACE = _EXTRA_HOME / "workspace" / "bridge"
_BRIDGE_WORKSPACE.mkdir(parents=True, exist_ok=True)


@dataclass
class BridgeResult:
    """
    Structured outcome of an execution bridge dispatch.
    """
    runtime: str
    success: bool
    returncode: int
    stdout: str
    stderr: str
    artifacts_created: List[str] = field(default_factory=list)
    latency_ms: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class UniversalBridgeRegistry:
    """
    Dynamic, extensible registry of execution runtimes.
    Maintains zero app-specific hardcoding: runtimes are defined as command templates.
    """

    def __init__(self) -> None:
        self._runtimes: Dict[str, Dict[str, Any]] = {
            "python": {
                "executable": sys.executable,
                "args": ["{script}"],
                "file_extension": ".py",
            },
            "powershell": {
                "executable": "powershell.exe" if sys.platform == "win32" else "pwsh",
                "args": ["-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", "{script}"],
                "file_extension": ".ps1",
            },
            "cmd": {
                "executable": "cmd.exe",
                "args": ["/c", "{script}"],
                "file_extension": ".bat",
            },
            "bash": {
                "executable": "bash",
                "args": ["-c", "{script}"],
                "file_extension": ".sh",
            },
            "harness": {
                "executable": "cli-anything",
                "args": [],
                "file_extension": "",
            },
        }
        self._auto_discover_external_runtimes()

    def _auto_discover_external_runtimes(self) -> None:
        """Autodiscovers standard external creative engines on system PATH or default directories."""
        # 1. Blender bpy runner
        blender_path = shutil.which("blender")
        if not blender_path and sys.platform == "win32":
            # Check standard Program Files paths
            for pf in [os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")]:
                if pf:
                    found = list(Path(pf).glob("Blender Foundation/Blender */blender.exe"))
                    if found:
                        blender_path = str(found[0])
                        break

        if blender_path:
            self.register_runtime(
                "blender_bpy",
                executable=blender_path,
                args=["-b", "--python", "{script}"],
                file_extension=".py",
            )

        # 2. Node / UXP runner
        node_path = shutil.which("node")
        if node_path:
            self.register_runtime(
                "node",
                executable=node_path,
                args=["{script}"],
                file_extension=".js",
            )

    def register_runtime(
        self,
        name: str,
        executable: str,
        args: List[str],
        file_extension: str = ".txt",
        env_vars: Optional[Dict[str, str]] = None,
    ) -> None:
        """Dynamically registers a new execution runtime template."""
        self._runtimes[name.lower()] = {
            "executable": executable,
            "args": args,
            "file_extension": file_extension,
            "env_vars": env_vars or {},
        }
        logger.info("[Bridge] Registered runtime '%s' -> %s", name, executable)

    def get_runtime(self, name: str) -> Optional[Dict[str, Any]]:
        return self._runtimes.get(name.lower())

    def list_runtimes(self) -> List[str]:
        return list(self._runtimes.keys())


# Singleton Registry
_registry = UniversalBridgeRegistry()


# Forbidden screen-scraping / capture patterns in bridge execution
# extra_execute_bridge is designated for deterministic computation, data processing, and CLI workflows,
# NOT for real-time screen perception loops. Screen perception MUST use native extra_screenshot or extra_inspect_ui.
FORBIDDEN_BRIDGE_PERCEPTION_PATTERNS = [
    r"\bimport\s+mss\b",
    r"\bfrom\s+mss\b",
    r"\bmss\.mss\b",
    r"\bImageGrab\b",
    r"\bpyscreenshot\b",
    r"\bpyautogui\.screenshot\b",
    r"\bwin32gui\.GetDC\b",
    r"\buser32\.GetDC\b",
    r"\bgdi32\.BitBlt\b",
    r"\bXGetImage\b",
    r"\bCGWindowListCreateImage\b",
]


def check_bridge_payload_safety(payload: str, runtime: str) -> Optional[str]:
    """
    Validates that a bridge payload does not attempt to circumvent native desktop perception
    by importing unauthorized screen capture or window scraping libraries.
    """
    if runtime.lower() in ("python", "blender_bpy", "node"):
        import re
        text_to_check = payload
        candidate = Path(payload.strip().strip('"').strip("'"))
        if candidate.exists() and candidate.is_file():
            try:
                text_to_check = candidate.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                pass

        for pat in FORBIDDEN_BRIDGE_PERCEPTION_PATTERNS:
            if re.search(pat, text_to_check, re.IGNORECASE):
                return (
                    f"BRIDGE ARCHITECTURE VIOLATION: Execution of screen-scraping/capture module "
                    f"(pattern '{pat}') is strictly prohibited inside extra_execute_bridge. "
                    f"extra_execute_bridge is designated for deterministic computation, data processing, "
                    f"and CLI workflows, NOT for real-time screen perception loops. "
                    f"Use native extra_screenshot(crop_box=[left, top, right, bottom]) or extra_inspect_ui instead."
                )
    return None


def execute_bridge(
    runtime: str,
    payload: str,
    args: Optional[List[str]] = None,
    working_dir: Optional[str] = None,
    expected_artifacts: Optional[List[str]] = None,
    timeout_sec: float = 60.0,
    env: Optional[Dict[str, str]] = None,
) -> BridgeResult:
    """
    Executes a script or command payload via the specified runtime.
    Handles temporary file lifecycle, process execution, artifact verification,
    and returns a structured BridgeResult in under 5ms execution overhead.
    """
    t0 = time.perf_counter()
    rt_info = _registry.get_runtime(runtime)

    if not rt_info:
        return BridgeResult(
            runtime=runtime,
            success=False,
            returncode=-1,
            stdout="",
            stderr="",
            error=f"Unsupported runtime '{runtime}'. Available: {_registry.list_runtimes()}",
            latency_ms=(time.perf_counter() - t0) * 1000.0,
        )

    # Safety Check: Block unauthorized screen-scraping in execution bridge
    safety_violation = check_bridge_payload_safety(payload, runtime)
    if safety_violation:
        return BridgeResult(
            runtime=runtime,
            success=False,
            returncode=-4,
            stdout="",
            stderr=safety_violation,
            error=safety_violation,
            latency_ms=(time.perf_counter() - t0) * 1000.0,
            metadata={"security_blocked": True},
        )

    # Special handling for agent-native CLI harnesses
    if runtime.lower() in ("harness", "cli_harness"):
        from extra.fastpath.cli_harness import execute_harness
        h_res = execute_harness(
            harness=payload,
            args=args or [],
            working_dir=working_dir,
            timeout_sec=timeout_sec,
            env=env,
        )
        return BridgeResult(
            runtime="harness",
            success=h_res.success,
            returncode=h_res.returncode,
            stdout=h_res.stdout,
            stderr=h_res.stderr,
            artifacts_created=h_res.artifacts_created,
            latency_ms=h_res.latency_ms,
            error=h_res.error,
            metadata={"data": h_res.data, "resolved_cmd": h_res.resolved_cmd, **h_res.metadata},
        )

    exe = rt_info["executable"]
    ext = rt_info.get("file_extension", ".txt")
    cwd = working_dir or str(_BRIDGE_WORKSPACE)

    # Determine if payload is an existing script file or raw code
    is_file = False
    candidate_path = Path(payload.strip().strip('"').strip("'"))
    if candidate_path.exists() and candidate_path.is_file():
        script_file = candidate_path
        is_file = True
    else:
        # Materialize payload to a temporary file in safe workspace
        temp_name = f"exec_{runtime}_{int(time.time()*1000)}{ext}"
        script_file = _BRIDGE_WORKSPACE / temp_name
        script_file.write_text(payload, encoding="utf-8")

    # Build command arguments
    cmd: List[str] = [exe]
    for arg_template in rt_info.get("args", []):
        if "{script}" in arg_template:
            cmd.append(arg_template.replace("{script}", str(script_file)))
        else:
            cmd.append(arg_template)

    if args:
        cmd.extend(args)

    # Setup environment: scrub ambient sensitive tokens unless explicitly provided in env
    BASELINE_SYSTEM_VARS = {
        "SYSTEMROOT", "PATH", "TEMP", "TMP", "COMSPEC", "PATHEXT",
        "WINDIR", "USERPROFILE", "HOMEPATH", "HOMEDRIVE", "ALLUSERSPROFILE",
        "APPDATA", "LOCALAPPDATA", "PROGRAMDATA", "PROGRAMFILES", "PROGRAMFILES(X86)",
        "NUMBER_OF_PROCESSORS", "PROCESSOR_ARCHITECTURE", "PROCESSOR_IDENTIFIER",
        "OS", "TERM", "LANG", "LC_ALL", "SHELL", "HOME", "USER", "LOGNAME",
    }
    SENSITIVE_KEY_PATTERNS = (
        "KEY", "SECRET", "TOKEN", "PASSWORD", "AUTH", "CREDENTIAL", "PRIVATE",
        "PAT", "ACCESS_KEY", "WEBHOOK", "SIG", "API_KEY"
    )

    exec_env = {}
    for k, v in os.environ.items():
        k_upper = k.upper()
        if k_upper in BASELINE_SYSTEM_VARS:
            exec_env[k] = v
        elif any(pattern in k_upper for pattern in SENSITIVE_KEY_PATTERNS):
            continue
        else:
            exec_env[k] = v

    if rt_info.get("env_vars"):
        exec_env.update(rt_info["env_vars"])
    if env:
        # Explicit caller-supplied env overrides everything
        exec_env.update(env)

    # Snapshot artifacts before execution to detect newly created ones
    expected = expected_artifacts or []
    pre_stat = {}
    for art in expected:
        p = Path(os.path.expandvars(art))
        if p.exists():
            pre_stat[str(p)] = p.stat().st_mtime

    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            env=exec_env,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            encoding="utf-8",
            errors="replace",
        )
        returncode = proc.returncode
        stdout = proc.stdout
        stderr = proc.stderr
        success = (returncode == 0)
    except subprocess.TimeoutExpired as tex:
        returncode = -2
        stdout = tex.stdout or "" if hasattr(tex, "stdout") else ""
        stderr = f"Execution timed out after {timeout_sec} seconds"
        success = False
    except Exception as ex:
        returncode = -3
        stdout = ""
        stderr = str(ex)
        success = False

    # Check for newly created or updated artifacts
    found_artifacts = []
    for art in expected:
        p = Path(os.path.expandvars(art))
        if p.exists():
            mtime = p.stat().st_mtime
            if str(p) not in pre_stat or mtime > pre_stat[str(p)]:
                found_artifacts.append(str(p))

    # Cleanup ephemeral script files to avoid workspace bloat
    if not is_file and script_file.exists():
        try:
            script_file.unlink()
        except Exception:
            pass

    latency_ms = (time.perf_counter() - t0) * 1000.0

    return BridgeResult(
        runtime=runtime,
        success=success,
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        artifacts_created=found_artifacts,
        latency_ms=latency_ms,
        error=None if success else (stderr or f"Exited with code {returncode}"),
        metadata={"cmd": cmd, "is_script_file": is_file},
    )
