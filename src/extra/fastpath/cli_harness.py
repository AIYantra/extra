"""
Project Extra — Universal CLI Harness Runner (Plane 2 Fast-Path)
Provides deterministic execution of agent-native CLI harnesses (HKUDS/CLI-Anything ecosystem)
with JSON machine-output parsing, session locking, artifact tracking, and zero app-specific hardcoding.
"""

from __future__ import annotations

import importlib.util
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("Extra-FastPath-Harness")

_EXTRA_HOME = Path(os.environ.get("USERPROFILE") or os.environ.get("HOME") or ".") / ".extra"
_HARNESS_WORKSPACE = _EXTRA_HOME / "workspace" / "harness"
_HARNESS_WORKSPACE.mkdir(parents=True, exist_ok=True)


@dataclass
class HarnessResult:
    """
    Structured outcome of an agent-native CLI harness execution.
    """
    harness: str
    success: bool
    returncode: int
    stdout: str
    stderr: str
    data: Optional[Any] = None
    artifacts_created: List[str] = field(default_factory=list)
    latency_ms: float = 0.0
    error: Optional[str] = None
    resolved_cmd: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _extract_json_payload(text: str) -> Optional[Any]:
    """
    Resiliently extracts JSON payloads from CLI stdout, handling potential
    leading/trailing banners, log lines, or multi-line structures.
    """
    stripped = text.strip()
    if not stripped:
        return None

    # 1. Fast path: whole text is JSON
    try:
        return json.loads(stripped)
    except Exception:
        pass

    # 2. Line-by-line check (common for Click CLI JSON output)
    for line in reversed(stripped.splitlines()):
        l = line.strip()
        if (l.startswith("{") and l.endswith("}")) or (l.startswith("[") and l.endswith("]")):
            try:
                return json.loads(l)
            except Exception:
                pass

    # 3. Robust AST scan using json.JSONDecoder.raw_decode
    decoder = json.JSONDecoder()
    last_obj = None
    for i, char in enumerate(stripped):
        if char in ("{", "["):
            try:
                obj, _ = decoder.raw_decode(stripped, i)
                last_obj = obj
            except Exception:
                continue

    return last_obj


class UniversalHarnessRunner:
    """
    Dynamic, extensible runner for agent-native CLI harnesses.
    Follows the Universal Engine Invariant: ZERO hardcoded application logic.
    """

    def __init__(self, workspace_dir: Optional[Path] = None) -> None:
        self.workspace_dir = workspace_dir or _HARNESS_WORKSPACE
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self._resolution_cache: Dict[str, Optional[List[str]]] = {}

    def clear_resolution_cache(self) -> None:
        """Clears the cached harness command resolutions."""
        self._resolution_cache.clear()

    @staticmethod
    def normalize_harness_name(name: str) -> str:
        """Normalizes names like 'cli-anything-blender', 'blender', 'GIMP' to slug."""
        clean = name.strip().lower()
        if clean.startswith("cli-anything-"):
            clean = clean[len("cli-anything-"):]
        elif clean.startswith("cli_anything-"):
            clean = clean[len("cli_anything-"):]
        elif clean.startswith("cli_anything_"):
            clean = clean[len("cli_anything_"):]
        return clean.replace("_", "-")

    def resolve_harness(self, harness: str, force_refresh: bool = False) -> Optional[List[str]]:
        """
        Resolves the executable command for the given harness.
        Checks:
        1. Direct command in PATH (e.g. 'cli-anything-gimp')
        2. Virtualenv / Python Scripts directory (e.g. sys.prefix/Scripts/cli-anything-gimp.exe)
        3. Python module invocation (python -m cli_anything.<name>.<name>_cli)
        4. Local repository agent-harness path (if CLI-Anything repo is present)
        """
        slug = self.normalize_harness_name(harness)
        if not force_refresh and slug in self._resolution_cache:
            return self._resolution_cache[slug]

        cmd_candidates = [
            f"extra-{slug}",
            f"cli-anything-{slug}",
            f"cli-anything-{slug.replace('-', '')}",
            f"cli-{slug}",
            slug,
        ]

        res = self._resolve_uncached(slug, cmd_candidates)
        self._resolution_cache[slug] = res
        return res

    def _resolve_uncached(self, slug: str, cmd_candidates: List[str]) -> Optional[List[str]]:
        # 1. System PATH
        for cand in cmd_candidates:
            which_res = shutil.which(cand)
            if which_res:
                return [which_res]
            if sys.platform == "win32":
                for ext in [".exe", ".cmd", ".bat"]:
                    which_ext = shutil.which(f"{cand}{ext}")
                    if which_ext:
                        return [which_ext]

        # 2. sys.prefix Scripts / bin directory and Extra home bin
        prefix_path = Path(sys.prefix)
        script_dirs = [
            _EXTRA_HOME / "bin",
            _EXTRA_HOME / "venv" / "Scripts",
            prefix_path / "Scripts",
            prefix_path / "bin",
            Path.home() / ".local" / "bin",
        ]
        for s_dir in script_dirs:
            if s_dir.exists():
                for cand in cmd_candidates:
                    p = s_dir / cand
                    if p.exists() and os.access(p, os.X_OK):
                        return [str(p)]
                    if sys.platform == "win32":
                        for ext in [".exe", ".cmd", ".bat"]:
                            p_ext = s_dir / f"{cand}{ext}"
                            if p_ext.exists():
                                return [str(p_ext)]

        # 3. Python module discovery
        py_modules = [
            f"cli_anything.{slug.replace('-', '_')}.{slug.replace('-', '_')}_cli",
            f"extra_{slug.replace('-', '_')}.{slug.replace('-', '_')}_cli",
            f"extra_{slug.replace('-', '_')}.paint_cli",
        ]
        for py_mod in py_modules:
            try:
                if importlib.util.find_spec(py_mod) is not None:
                    return [sys.executable, "-m", py_mod]
            except Exception:
                pass

        # 4. Monorepo / Workspace fallback
        repo_roots = [
            Path(os.environ.get("CLI_ANYTHING_ROOT", "")),
            Path("D:/yantra_workspace/CLI-Anything"),
            Path(__file__).parents[3] / "CLI-Anything",
            Path(__file__).parents[2] / "CLI-Anything",
        ]
        for r_root in repo_roots:
            if r_root and r_root.exists():
                candidate_paths = [
                    r_root / slug / "agent-harness" / "cli_anything" / slug.replace("-", "_") / f"{slug.replace('-', '_')}_cli.py",
                    r_root / slug.replace("-", "") / "agent-harness" / "cli_anything" / slug.replace("-", "_") / f"{slug.replace('-', '_')}_cli.py",
                ]
                for c_path in candidate_paths:
                    if c_path.exists():
                        return [sys.executable, str(c_path)]

        return None

    def is_harness_available(self, harness: str) -> bool:
        """Returns True if the harness can be resolved locally."""
        return self.resolve_harness(harness) is not None

    def execute(
        self,
        harness: str,
        args: List[str],
        json_output: bool = True,
        auto_visualize: bool = False,
        working_dir: Optional[str] = None,
        timeout_sec: float = 60.0,
        env: Optional[Dict[str, str]] = None,
        strict_exit: bool = False,
    ) -> HarnessResult:
        """
        Executes a command using the specified agent-native CLI harness.
        """
        t0 = time.perf_counter()
        slug = self.normalize_harness_name(harness)
        cmd_base = self.resolve_harness(slug)

        if not cmd_base:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            return HarnessResult(
                harness=slug,
                success=False,
                returncode=-1,
                stdout="",
                stderr="",
                error=f"Harness 'cli-anything-{slug}' not found on system PATH or python environment. "
                      f"Use extra_hub_manage(action='install', harness_name='{slug}') to install it.",
                latency_ms=latency_ms,
            )

        # Prepare arguments & JSON flag injection
        full_args = list(args)
        if json_output and "--json" not in full_args:
            # Check where to insert --json (typically right after base command or at top level)
            full_args.insert(0, "--json")

        cwd = Path(working_dir) if working_dir else self.workspace_dir
        cwd.mkdir(parents=True, exist_ok=True)

        # Snapshot files in cwd to detect newly created artifacts
        def _get_files(p: Path) -> Set[Path]:
            try:
                return {f for f in p.glob("*") if f.is_file()}
            except Exception:
                return set()

        files_before = _get_files(cwd)

        # Prepare environment
        run_env = os.environ.copy()
        if env:
            run_env.update(env)

        # If running Python script directly from monorepo, ensure parent agent-harness is in PYTHONPATH
        if len(cmd_base) == 2 and cmd_base[0] == sys.executable and cmd_base[1].endswith(".py"):
            script_path = Path(cmd_base[1])
            parent_harness = str(script_path.parents[2])
            existing_pp = run_env.get("PYTHONPATH", "")
            run_env["PYTHONPATH"] = f"{parent_harness}{os.pathsep}{existing_pp}" if existing_pp else parent_harness

        full_cmd = cmd_base + full_args
        logger.info("[Harness] Executing: %s in %s", " ".join(full_cmd), cwd)

        try:
            proc = subprocess.run(
                full_cmd,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                env=run_env,
            )
            latency_ms = (time.perf_counter() - t0) * 1000.0

            # Detect created artifacts
            files_after = _get_files(cwd)
            new_files = sorted(str(f.resolve()) for f in (files_after - files_before))

            # Parse JSON data if requested
            parsed_data = None
            if json_output:
                parsed_data = _extract_json_payload(proc.stdout)

            success = (proc.returncode == 0)
            error_msg = None if success else (proc.stderr.strip() or f"Process exited with code {proc.returncode}")

            if strict_exit and not success:
                raise RuntimeError(f"Harness '{slug}' failed with exit code {proc.returncode}: {error_msg}")

            metadata: Dict[str, Any] = {"working_dir": str(cwd), "json_parsed": parsed_data is not None}

            # Dual-Plane Visualizer: Bring output live onto physical display
            if auto_visualize and success:
                try:
                    from extra.fastpath.visualizer import visualize_harness_outcome
                    vis_res = visualize_harness_outcome(
                        harness=slug,
                        artifacts_created=new_files,
                        data=parsed_data,
                        args=args,
                    )
                    metadata["visualization"] = vis_res
                except Exception as v_ex:
                    logger.warning("[Harness] Auto-visualization skipped: %s", v_ex)
                    metadata["visualization"] = {"visualized": False, "error": str(v_ex)}

            return HarnessResult(
                harness=slug,
                success=success,
                returncode=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                data=parsed_data,
                artifacts_created=new_files,
                latency_ms=latency_ms,
                error=error_msg,
                resolved_cmd=full_cmd,
                metadata=metadata,
            )

        except subprocess.TimeoutExpired as ex:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            logger.warning("[Harness] Timed out after %s seconds: %s", timeout_sec, full_cmd)
            return HarnessResult(
                harness=slug,
                success=False,
                returncode=-2,
                stdout="",
                stderr="",
                error=f"Harness execution timed out after {timeout_sec}s",
                latency_ms=latency_ms,
                resolved_cmd=full_cmd,
            )
        except Exception as ex:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            logger.exception("[Harness] Execution error: %s", ex)
            return HarnessResult(
                harness=slug,
                success=False,
                returncode=-3,
                stdout="",
                stderr="",
                error=str(ex),
                latency_ms=latency_ms,
                resolved_cmd=full_cmd,
            )


# Global singleton runner
_default_runner = UniversalHarnessRunner()


def execute_harness(
    harness: str,
    args: List[str],
    json_output: bool = True,
    auto_visualize: bool = False,
    working_dir: Optional[str] = None,
    timeout_sec: float = 60.0,
    env: Optional[Dict[str, str]] = None,
) -> HarnessResult:
    """Convenience helper to execute a CLI harness."""
    return _default_runner.execute(
        harness=harness,
        args=args,
        json_output=json_output,
        auto_visualize=auto_visualize,
        working_dir=working_dir,
        timeout_sec=timeout_sec,
        env=env,
    )


def resolve_harness(harness: str) -> Optional[List[str]]:
    """Convenience helper to resolve a harness binary."""
    return _default_runner.resolve_harness(harness)


def is_harness_available(harness: str) -> bool:
    """Convenience helper to check harness availability."""
    return _default_runner.is_harness_available(harness)
