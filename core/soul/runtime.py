"""
Project Extra — Project SOUL
Hardware execution provider manager and ONNX Runtime session lifecycle.
Provides zero-bloat, cross-platform hardware acceleration (DirectML on Windows, CoreML on macOS, CPU universal).
"""

from __future__ import annotations

import logging
import os
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Extra-SOUL-Runtime")

# Safe home directory complying with Windows Defender Controlled Folder Access
_EXTRA_HOME = Path(os.environ.get("USERPROFILE") or os.environ.get("HOME") or ".") / ".extra"
SOUL_MODEL_DIR = _EXTRA_HOME / "models" / "soul"


class SoulRuntimeManager:
    """
    Manages lazy-loaded, thread-safe ONNX Runtime sessions for SOUL models.
    Automatically discovers and prioritizes hardware acceleration providers.
    """

    _instance: Optional[SoulRuntimeManager] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._sessions: Dict[str, Any] = {}
        self._providers: Optional[List[str]] = None
        self._session_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> SoulRuntimeManager:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def get_execution_providers(self) -> List[str]:
        """
        Detects and returns prioritized ONNX Execution Providers for the current OS.
        Windows -> DirectML (DmlExecutionProvider) > CPU
        macOS -> CoreML (CoreMLExecutionProvider) > CPU
        """
        if self._providers is not None:
            return self._providers

        providers = ["CPUExecutionProvider"]
        try:
            import onnxruntime as ort
            available = ort.get_available_providers()
            logger.debug("Available ONNX providers on system: %s", available)

            prioritized: List[str] = []
            if sys.platform == "win32":
                if "DmlExecutionProvider" in available:
                    prioritized.append("DmlExecutionProvider")
            elif sys.platform == "darwin":
                if "CoreMLExecutionProvider" in available:
                    prioritized.append("CoreMLExecutionProvider")

            for p in prioritized:
                if p in available and p not in providers:
                    providers.insert(0, p)
        except Exception as ex:
            logger.warning("Could not probe ONNX execution providers: %s", ex)

        self._providers = providers
        logger.info("Active SOUL Execution Providers: %s", self._providers)
        return self._providers

    def get_session(self, model_name: str, model_path: Optional[Path] = None) -> Optional[Any]:
        """
        Retrieves or initializes a cached ONNX InferenceSession for a model.
        Returns None if model file does not exist.
        """
        with self._session_lock:
            if model_name in self._sessions:
                return self._sessions[model_name]

            target_path = model_path or (SOUL_MODEL_DIR / f"{model_name}.onnx")
            if not target_path.exists():
                logger.debug("SOUL model file not found at %s. Fast-path fallback active.", target_path)
                return None

            try:
                import onnxruntime as ort
                sess_options = ort.SessionOptions()
                sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                sess_options.intra_op_num_threads = max(1, os.cpu_count() or 2)

                providers = self.get_execution_providers()
                session = ort.InferenceSession(str(target_path), sess_options, providers=providers)
                self._sessions[model_name] = session
                logger.info("Loaded SOUL ONNX session '%s' with provider: %s", model_name, session.get_providers()[0])
                return session
            except Exception as ex:
                logger.error("Failed to initialize ONNX session for '%s': %s", model_name, ex)
                return None

    def is_gpu_accelerated(self) -> bool:
        providers = self.get_execution_providers()
        return any(p in providers for p in ("DmlExecutionProvider", "CoreMLExecutionProvider", "CUDAExecutionProvider"))


# Convenience singleton accessor
def get_soul_runtime() -> SoulRuntimeManager:
    return SoulRuntimeManager.get_instance()
