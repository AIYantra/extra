"""
Project Extra — CLI-Hub Registry & Package Manager Integration
Provides autonomous discovery, inspection, and installation of 40+ agent-native CLI harnesses
backed by HKUDS/CLI-Anything registries.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Extra-FastPath-CLIHub")

_EXTRA_HOME = Path(os.environ.get("USERPROFILE") or os.environ.get("HOME") or ".") / ".extra"
_CLI_HUB_DIR = _EXTRA_HOME / "cli_hub"
_CLI_HUB_DIR.mkdir(parents=True, exist_ok=True)
_CACHE_FILE = _CLI_HUB_DIR / "registry_cache.json"
_PUBLIC_CACHE_FILE = _CLI_HUB_DIR / "public_registry_cache.json"
_CACHE_TTL = 3600 * 6  # 6 hours cache TTL

REGISTRY_URL = "https://hkuds.github.io/CLI-Anything/registry.json"
PUBLIC_REGISTRY_URL = "https://hkuds.github.io/CLI-Anything/public_registry.json"


class CliHubManager:
    """
    Registry client and installer for CLI-Anything harnesses.
    Maintains zero application-specific hardcoding.
    """

    def __init__(self, workspace_root: Optional[Path] = None) -> None:
        self.workspace_root = workspace_root or Path("D:/yantra_workspace/CLI-Anything")
        self._cached_all: Optional[List[Dict[str, Any]]] = None

    def _get_local_registry_file(self) -> Optional[Path]:
        """Locates registry.json in local workspace if available."""
        candidates = [
            Path(os.environ.get("CLI_HUB_REGISTRY", "")),
            self.workspace_root / "registry.json",
            Path(__file__).parents[3] / "CLI-Anything" / "registry.json",
            Path(__file__).parents[2] / "CLI-Anything" / "registry.json",
        ]
        for c in candidates:
            if c and c.is_file():
                return c
        return None

    def _get_local_public_registry_file(self) -> Optional[Path]:
        """Locates public_registry.json in local workspace if available."""
        candidates = [
            self.workspace_root / "public_registry.json",
            Path(__file__).parents[3] / "CLI-Anything" / "public_registry.json",
            Path(__file__).parents[2] / "CLI-Anything" / "public_registry.json",
        ]
        for c in candidates:
            if c and c.is_file():
                return c
        return None

    def fetch_registry(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Fetches primary harness registry from local file, cache, or remote HTTP."""
        local_file = self._get_local_registry_file()
        if local_file and not force_refresh:
            try:
                data = json.loads(local_file.read_text(encoding="utf-8"))
                return data
            except Exception as ex:
                logger.warning("[CLIHub] Failed reading local registry %s: %s", local_file, ex)

        # Check local cache
        if not force_refresh and _CACHE_FILE.exists():
            try:
                cached = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
                if time.time() - cached.get("_cached_at", 0) < _CACHE_TTL:
                    return cached.get("data", {})
            except Exception:
                pass

        # Remote fetch fallback
        try:
            import urllib.request
            req = urllib.request.Request(REGISTRY_URL, headers={"User-Agent": "Project-Extra/0.4.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                _CACHE_FILE.write_text(json.dumps({"_cached_at": time.time(), "data": data}, indent=2), encoding="utf-8")
                return data
        except Exception as ex:
            logger.warning("[CLIHub] Remote fetch failed: %s", ex)
            if _CACHE_FILE.exists():
                try:
                    return json.loads(_CACHE_FILE.read_text(encoding="utf-8")).get("data", {})
                except Exception:
                    pass

        return {"clis": []}

    def fetch_public_registry(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """Fetches public registry if available."""
        local_file = self._get_local_public_registry_file()
        if local_file and not force_refresh:
            try:
                return json.loads(local_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        if not force_refresh and _PUBLIC_CACHE_FILE.exists():
            try:
                cached = json.loads(_PUBLIC_CACHE_FILE.read_text(encoding="utf-8"))
                if time.time() - cached.get("_cached_at", 0) < _CACHE_TTL:
                    return cached.get("data")
            except Exception:
                pass

        try:
            import urllib.request
            req = urllib.request.Request(PUBLIC_REGISTRY_URL, headers={"User-Agent": "Project-Extra/0.4.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                _PUBLIC_CACHE_FILE.write_text(json.dumps({"_cached_at": time.time(), "data": data}, indent=2), encoding="utf-8")
                return data
        except Exception:
            return None

    def fetch_all_clis(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Fetches and merges primary and public CLI registries."""
        if self._cached_all and not force_refresh:
            return self._cached_all

        all_clis = []
        primary = self.fetch_registry(force_refresh)
        for cli in primary.get("clis", []):
            entry = dict(cli)
            entry["_source"] = "harness"
            all_clis.append(entry)

        public = self.fetch_public_registry(force_refresh)
        if public:
            for cli in public.get("clis", []):
                entry = dict(cli)
                entry["_source"] = "public"
                all_clis.append(entry)

        self._cached_all = all_clis
        return all_clis

    def list_harnesses(self, category: Optional[str] = None, installed_only: bool = False) -> List[Dict[str, Any]]:
        """Lists available harnesses with optional category and installed filter."""
        from extra.fastpath.cli_harness import is_harness_available

        clis = self.fetch_all_clis()
        results = []
        for item in clis:
            cat = item.get("category", "")
            if category and cat.lower() != category.lower():
                continue
            is_installed = is_harness_available(item.get("name", ""))
            if installed_only and not is_installed:
                continue

            entry = dict(item)
            entry["is_installed"] = is_installed
            results.append(entry)

        return results

    def search_harnesses(self, query: str) -> List[Dict[str, Any]]:
        """Searches harnesses by name, display name, category, or description keywords."""
        from extra.fastpath.cli_harness import is_harness_available

        q = query.strip().lower()
        clis = self.fetch_all_clis()
        matched = []

        for item in clis:
            name = item.get("name", "").lower()
            display_name = item.get("display_name", "").lower()
            desc = item.get("description", "").lower()
            cat = item.get("category", "").lower()

            if q in name or q in display_name or q in desc or q in cat:
                entry = dict(item)
                entry["is_installed"] = is_harness_available(name)
                matched.append(entry)

        return matched

    def get_harness_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Returns metadata for a specific harness by name."""
        from extra.fastpath.cli_harness import is_harness_available

        clean = name.strip().lower()
        if clean.startswith("cli-anything-"):
            clean = clean[len("cli-anything-"):]

        for item in self.fetch_all_clis():
            if item.get("name", "").lower() == clean:
                info = dict(item)
                info["is_installed"] = is_harness_available(clean)
                return info
        return None

    def is_harness_installed(self, name: str) -> bool:
        """Checks if a harness is installed and executable."""
        from extra.fastpath.cli_harness import is_harness_available
        return is_harness_available(name)

    def install_harness(
        self,
        name: str,
        force_reinstall: bool = False,
        timeout_sec: float = 180.0,
    ) -> Dict[str, Any]:
        """
        Installs a CLI harness into the active Python environment.
        Prioritizes:
        1. Local editable install if CLI-Anything monorepo contains the agent-harness
        2. cli-hub CLI binary if installed
        3. Registry install_cmd (e.g. pip install git+...)
        4. Standard pip package (pip install cli-anything-<name>)
        """
        from extra.fastpath.cli_harness import is_harness_available

        clean = name.strip().lower()
        if clean.startswith("cli-anything-"):
            clean = clean[len("cli-anything-"):]

        if not force_reinstall and is_harness_available(clean):
            return {
                "success": True,
                "name": clean,
                "already_installed": True,
                "message": f"Harness 'cli-anything-{clean}' is already installed and available.",
            }

        # 1. Local Monorepo Editable Install Check
        info = self.get_harness_info(clean)
        local_harness_dir = None
        repo_roots = [
            self.workspace_root,
            Path("D:/yantra_workspace/CLI-Anything"),
            Path(__file__).parents[3] / "CLI-Anything",
            Path(__file__).parents[2] / "CLI-Anything",
        ]
        for r_root in repo_roots:
            if r_root and r_root.exists():
                cand = r_root / clean / "agent-harness"
                if cand.exists() and (cand / "setup.py").exists():
                    local_harness_dir = cand
                    break

        if local_harness_dir:
            logger.info("[CLIHub] Found local harness at %s, installing via pip -e", local_harness_dir)
            cmd = [sys.executable, "-m", "pip", "install", "-e", str(local_harness_dir)]
        elif shutil.which("cli-hub"):
            logger.info("[CLIHub] Found cli-hub CLI in PATH, invoking 'cli-hub install %s'", clean)
            cmd = ["cli-hub", "install", clean]
        elif info and info.get("install_cmd"):
            install_cmd_str = info["install_cmd"]
            parts = install_cmd_str.split()
            # Enforce pip installation strictly; reject arbitrary shell commands or untrusted remote URLs
            if parts and parts[0] == "pip" and "install" in parts:
                safe_args = []
                for p in parts[1:]:
                    if p.startswith(("-e", "git+", "http://", "https://", "--extra-index-url", "--find-links")):
                        continue
                    safe_args.append(p)
                cmd = [sys.executable, "-m", "pip"] + (safe_args if safe_args else ["install", f"cli-anything-{clean}"])
            else:
                logger.warning("[CLIHub] Blocked non-pip install_cmd from registry for '%s': %s", clean, install_cmd_str)
                cmd = [sys.executable, "-m", "pip", "install", f"cli-anything-{clean}"]
        else:
            # Fallback to standard pip package
            cmd = [sys.executable, "-m", "pip", "install", f"cli-anything-{clean}"]

        logger.info("[CLIHub] Running install command: %s", " ".join(cmd))
        t0 = time.perf_counter()
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
            duration_s = round(time.perf_counter() - t0, 2)
            try:
                from extra.fastpath.cli_harness import _default_runner
                _default_runner.clear_resolution_cache()
            except Exception:
                pass
            success = (proc.returncode == 0) and is_harness_available(clean)

            return {
                "success": success,
                "name": clean,
                "returncode": proc.returncode,
                "stdout": proc.stdout[-1000:] if proc.stdout else "",
                "stderr": proc.stderr[-1000:] if proc.stderr else "",
                "duration_seconds": duration_s,
                "message": "Installed successfully" if success else "Installation failed or command not verified in PATH",
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "name": clean,
                "returncode": -1,
                "error": f"Installation timed out after {timeout_sec}s",
            }
        except Exception as ex:
            return {
                "success": False,
                "name": clean,
                "returncode": -2,
                "error": str(ex),
            }

    def uninstall_harness(self, name: str) -> Dict[str, Any]:
        """Uninstalls a CLI harness from the environment."""
        clean = name.strip().lower()
        if clean.startswith("cli-anything-"):
            clean = clean[len("cli-anything-"):]

        cmd = [sys.executable, "-m", "pip", "uninstall", "-y", f"cli-anything-{clean}"]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60.0)
            try:
                from extra.fastpath.cli_harness import _default_runner
                _default_runner.clear_resolution_cache()
            except Exception:
                pass
            return {
                "success": proc.returncode == 0,
                "name": clean,
                "message": "Uninstalled successfully" if proc.returncode == 0 else proc.stderr,
            }
        except Exception as ex:
            return {"success": False, "name": clean, "error": str(ex)}


# Global singleton manager
_default_hub = CliHubManager()


def get_cli_hub() -> CliHubManager:
    return _default_hub
