"""
Project Extra — Artifact Lineage & Provenance Verifier
Guarantees authentic deliverable origin and enforces strict anti-shortcut compliance.
Detects fraudulent workflow substitution (e.g. headless Chrome printing local HTML
instead of mandated Google Docs / Slides export).
"""

from __future__ import annotations

import configparser
import logging
import os
import re
import sqlite3
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger("Extra-Composer-Lineage")


class ArtifactOrigin(str, Enum):
    """
    Classified physical origin of a deliverable artifact.
    """
    OFFICIAL_WEB_EXPORT = "official_web_export"  # Server-rendered download from official web service
    APPLICATION_EXPORT = "application_export"    # Exported from desktop GUI software (LibreOffice, Blender, Paint)
    CLI_HARNESS = "cli_harness"                  # Produced deterministically via Plane 2 CLI harness
    PROGRAMMATIC_LOCAL = "programmatic_local"    # Ad-hoc local script (headless Chrome print, reportlab, python)
    UNKNOWN = "unknown"


@dataclass
class LineageVerdict:
    """
    Detailed verdict of artifact provenance inspection.
    """
    valid: bool
    detected_origin: ArtifactOrigin
    expected_origin: Optional[ArtifactOrigin] = None
    confidence: float = 1.0
    producer: Optional[str] = None
    creator: Optional[str] = None
    source_url: Optional[str] = None
    defects: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "detected_origin": self.detected_origin.value,
            "expected_origin": self.expected_origin.value if self.expected_origin else None,
            "confidence": self.confidence,
            "producer": self.producer,
            "creator": self.creator,
            "source_url": self.source_url,
            "defects": self.defects,
            "metadata": self.metadata,
        }


class ArtifactLineageVerifier:
    """
    Inspects physical artifact binary structure, metadata headers, and OS/browser
    download history to verify authentic deliverable provenance.
    """

    def inspect_artifact(self, file_path: Union[str, Path]) -> LineageVerdict:
        """
        Inspects an artifact file and determines its physical lineage.
        """
        path = Path(file_path).resolve()
        if not path.exists():
            return LineageVerdict(
                valid=False,
                detected_origin=ArtifactOrigin.UNKNOWN,
                confidence=0.0,
                defects=[f"Artifact file does not exist: {path}"],
            )

        suffix = path.suffix.lower()
        if suffix == ".pdf":
            return self._inspect_pdf(path)
        else:
            return self._inspect_generic_file(path)

    def _inspect_pdf(self, path: Path) -> LineageVerdict:
        """
        Examines PDF trailer metadata, Producer/Creator tags, and browser download lineage.
        """
        producer, creator = self._extract_pdf_metadata(path)
        source_url = self._lookup_browser_download_source(path)

        defects: List[str] = []
        origin = ArtifactOrigin.UNKNOWN
        confidence = 0.85
        metadata = {"file_size": path.stat().st_size, "path": str(path)}

        prod_lower = (producer or "").lower()
        creat_lower = (creator or "").lower()

        # 1. Check for official web download records
        if source_url and ("docs.google.com" in source_url or "drive.google.com" in source_url):
            origin = ArtifactOrigin.OFFICIAL_WEB_EXPORT
            confidence = 0.98
        elif "google" in prod_lower or "google" in creat_lower:
            origin = ArtifactOrigin.OFFICIAL_WEB_EXPORT
            confidence = 0.95
        # 2. Check for official desktop office applications
        elif "libreoffice" in prod_lower or "openoffice" in prod_lower:
            origin = ArtifactOrigin.APPLICATION_EXPORT
            confidence = 0.95
        # 3. Check for Programmatic Local Generation (Headless Chrome / ReportLab / Skia)
        elif "reportlab" in prod_lower or "pymupdf" in prod_lower:
            origin = ArtifactOrigin.PROGRAMMATIC_LOCAL
            confidence = 0.99
            defects.append(
                f"Artifact produced by local Python library ('{producer}'), not target application"
            )
        elif "skia/pdf" in prod_lower or "mozilla" in creat_lower or "headlesschrome" in creat_lower:
            # Check if this Skia PDF came from an authentic web download or local headless print
            if source_url and ("http://" in source_url or "https://" in source_url) and not source_url.startswith("file://"):
                origin = ArtifactOrigin.OFFICIAL_WEB_EXPORT
                confidence = 0.90
            else:
                origin = ArtifactOrigin.PROGRAMMATIC_LOCAL
                confidence = 0.92
                defects.append(
                    "Artifact generated via local browser print (Skia/PDF on local source), "
                    "indicating workflow substitution instead of genuine web workspace export"
                )
        else:
            if source_url:
                origin = ArtifactOrigin.OFFICIAL_WEB_EXPORT
            else:
                origin = ArtifactOrigin.APPLICATION_EXPORT
                confidence = 0.60

        return LineageVerdict(
            valid=len(defects) == 0,
            detected_origin=origin,
            confidence=confidence,
            producer=producer,
            creator=creator,
            source_url=source_url,
            defects=defects,
            metadata=metadata,
        )

    def _inspect_generic_file(self, path: Path) -> LineageVerdict:
        """
        Generic file inspection via browser download history and Windows Zone.Identifier.
        """
        source_url = self._lookup_browser_download_source(path)
        metadata = {"file_size": path.stat().st_size, "path": str(path)}
        if source_url:
            return LineageVerdict(
                valid=True,
                detected_origin=ArtifactOrigin.OFFICIAL_WEB_EXPORT,
                confidence=0.90,
                source_url=source_url,
                metadata=metadata,
            )
        return LineageVerdict(
            valid=True,
            detected_origin=ArtifactOrigin.UNKNOWN,
            confidence=0.50,
            metadata=metadata,
        )

    def _extract_pdf_metadata(self, path: Path) -> tuple[Optional[str], Optional[str]]:
        """
        Reads raw binary trailer / Info dictionary in PDF without requiring external heavy dependencies.
        """
        try:
            # Read beginning and tail of file where metadata typically resides
            size = path.stat().st_size
            sample_size = min(size, 65536)
            with open(path, "rb") as f:
                tail = b""
                if size > sample_size:
                    f.seek(size - sample_size)
                    tail = f.read(sample_size)
                f.seek(0)
                head = f.read(sample_size)

            content = head + tail
            text = content.decode("latin1", errors="ignore")

            producer = None
            creator = None

            # Pattern 1: /Producer (value)
            prod_match = re.search(r"/Producer\s*\(([^)]+)\)", text)
            if prod_match:
                producer = prod_match.group(1).strip()
            else:
                # Pattern 2: /Producer <hex>
                prod_hex = re.search(r"/Producer\s*<([0-9a-fA-F]+)>", text)
                if prod_hex:
                    try:
                        producer = bytes.fromhex(prod_hex.group(1)).decode("utf-16be", errors="ignore")
                    except Exception:
                        pass

            # Pattern 1: /Creator (value)
            creat_match = re.search(r"/Creator\s*\(([^)]+)\)", text)
            if creat_match:
                creator = creat_match.group(1).strip()
            else:
                creat_hex = re.search(r"/Creator\s*<([0-9a-fA-F]+)>", text)
                if creat_hex:
                    try:
                        creator = bytes.fromhex(creat_hex.group(1)).decode("utf-16be", errors="ignore")
                    except Exception:
                        pass

            return producer, creator
        except Exception as ex:
            logger.debug("Failed to extract PDF metadata: %s", ex)
            return None, None

    def _lookup_browser_download_source(self, path: Path) -> Optional[str]:
        """
        Checks NTFS Zone.Identifier ADS and browser history database for download origin URL.
        """
        # 1. Windows NTFS Zone.Identifier stream
        if sys.platform == "win32":
            zone_path = path.parent / f"{path.name}:Zone.Identifier"
            try:
                if zone_path.exists():
                    ini_text = zone_path.read_text(encoding="utf-8", errors="ignore")
                    cp = configparser.ConfigParser()
                    cp.read_string(ini_text)
                    if cp.has_option("ZoneTransfer", "HostUrl"):
                        return cp.get("ZoneTransfer", "HostUrl")
                    if cp.has_option("ZoneTransfer", "ReferrerUrl"):
                        return cp.get("ZoneTransfer", "ReferrerUrl")
            except Exception:
                pass

        # 2. Chrome / Edge History database check
        download_url = self._query_browser_history_downloads(path)
        if download_url:
            return download_url

        return None

    def _query_browser_history_downloads(self, path: Path) -> Optional[str]:
        """
        Queries Chromium/Edge history database for download entries matching the file path.
        """
        abs_target = str(path.resolve()).replace("/", "\\")
        home = Path(os.environ.get("USERPROFILE") or os.environ.get("HOME") or ".")
        possible_history_paths = [
            home / "AppData/Local/Google/Chrome/User Data/Default/History",
            home / "AppData/Local/Microsoft/Edge/User Data/Default/History",
            home / ".config/google-chrome/Default/History",
            home / ".config/chromium/Default/History",
        ]

        for hist_path in possible_history_paths:
            if not hist_path.exists():
                continue
            try:
                # Open read-only via URI to avoid locking active browser database
                conn_uri = f"file:{hist_path.resolve().as_posix()}?mode=ro&immutable=1"
                conn = sqlite3.connect(conn_uri, uri=True, timeout=1.0)
                cur = conn.cursor()
                cur.execute(
                    "SELECT tab_url, referrer FROM downloads WHERE target_path LIKE ? ORDER BY start_time DESC LIMIT 1",
                    (f"%{path.name}%",),
                )
                row = cur.fetchone()
                conn.close()
                if row:
                    tab_url, referrer = row
                    return tab_url or referrer
            except Exception:
                continue

        return None

    def verify_lineage(
        self,
        file_path: Union[str, Path],
        expected_origin: Union[str, ArtifactOrigin],
        forbidden_origins: Optional[List[Union[str, ArtifactOrigin]]] = None,
    ) -> LineageVerdict:
        """
        Strictly verifies that an artifact matches the expected provenance origin
        and has not been substituted via a forbidden programmatic shortcut.
        """
        exp_origin = (
            ArtifactOrigin(expected_origin)
            if isinstance(expected_origin, str)
            else expected_origin
        )
        forb_origins = [
            ArtifactOrigin(fo) if isinstance(fo, str) else fo
            for fo in (forbidden_origins or [ArtifactOrigin.PROGRAMMATIC_LOCAL])
        ]

        verdict = self.inspect_artifact(file_path)
        verdict.expected_origin = exp_origin

        # Reject if origin is in forbidden list
        if verdict.detected_origin in forb_origins:
            verdict.valid = False
            msg = (
                f"Artifact lineage violation: Detected origin is '{verdict.detected_origin.value}', "
                f"which is explicitly forbidden (expected '{exp_origin.value}')"
            )
            if msg not in verdict.defects:
                verdict.defects.append(msg)
            return verdict

        # Verify matching expected origin if strict
        if exp_origin != ArtifactOrigin.UNKNOWN and verdict.detected_origin != exp_origin:
            # Allow OFFICIAL_WEB_EXPORT when APPLICATION_EXPORT is expected (or vice versa) if high confidence
            is_compatible = (
                {verdict.detected_origin, exp_origin} <= {ArtifactOrigin.OFFICIAL_WEB_EXPORT, ArtifactOrigin.APPLICATION_EXPORT}
            )
            if not is_compatible:
                verdict.valid = False
                verdict.defects.append(
                    f"Lineage mismatch: Expected origin '{exp_origin.value}', "
                    f"but detected origin was '{verdict.detected_origin.value}'"
                )

        verdict.valid = len(verdict.defects) == 0
        return verdict


_default_lineage_verifier = ArtifactLineageVerifier()


def verify_artifact_lineage(
    file_path: Union[str, Path],
    expected_origin: Union[str, ArtifactOrigin] = ArtifactOrigin.OFFICIAL_WEB_EXPORT,
    forbidden_origins: Optional[List[Union[str, ArtifactOrigin]]] = None,
) -> LineageVerdict:
    """
    Public entry point to verify deliverable artifact provenance.
    """
    return _default_lineage_verifier.verify_lineage(
        file_path,
        expected_origin=expected_origin,
        forbidden_origins=forbidden_origins,
    )
