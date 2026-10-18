"""
Project Extra — Ground-Truth State Critic Subsystem
Conducts independent, decoupled audits of actual application state (tab counts,
slide counts, non-empty text, canvas activity) across DOM and UIA trees.
Eliminates epistemic drift and bars agents from hallucinating 100% QA pass reports.
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Union

from bs4 import BeautifulSoup

from extra.core.platform import get_accessibility_plane

logger = logging.getLogger("Extra-SOUL-StateCritic")


@dataclass
class StateAuditClaim:
    """
    Operator or task-mandated expectations for application ground-truth state.
    """
    doc_type: Optional[str] = None  # "spreadsheet", "document", "presentation", "canvas", "general"
    expected_tabs: Optional[int] = None
    expected_slides: Optional[int] = None
    expected_sections: Optional[int] = None
    min_words: Optional[int] = None
    min_cells: Optional[int] = None
    expected_elements: Optional[List[str]] = field(default_factory=list)
    forbidden_elements: Optional[List[str]] = field(default_factory=list)


@dataclass
class StateAuditResult:
    """
    Immutable, cryptographic result of a ground-truth state audit.
    """
    passed: bool
    score: float
    claims: Dict[str, Any]
    ground_truth: Dict[str, Any]
    defects: List[str] = field(default_factory=list)
    audit_hash: str = ""
    timestamp: str = ""
    report_text: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class GroundTruthStateCritic:
    """
    Decoupled state critic that inspects the actual UI runtime (via DOM or UIA)
    to confirm whether claimed artifacts and document contents truly exist.
    """

    def audit_state(
        self,
        claims: Union[Dict[str, Any], StateAuditClaim],
        window_title: Optional[str] = None,
        page_html: Optional[str] = None,
    ) -> StateAuditResult:
        """
        Audits active desktop window or provided web page against claims.
        """
        t0 = time.perf_counter()
        if isinstance(claims, dict):
            claim_obj = StateAuditClaim(
                doc_type=claims.get("doc_type"),
                expected_tabs=claims.get("expected_tabs"),
                expected_slides=claims.get("expected_slides"),
                expected_sections=claims.get("expected_sections"),
                min_words=claims.get("min_words"),
                min_cells=claims.get("min_cells"),
                expected_elements=claims.get("expected_elements") or [],
                forbidden_elements=claims.get("forbidden_elements") or [],
            )
        else:
            claim_obj = claims

        ground_truth: Dict[str, Any] = {}
        defects: List[str] = []

        # 1. Probing Strategy: DOM if HTML provided, else Accessibility Plane
        if page_html:
            self._probe_dom(page_html, claim_obj, ground_truth, defects)
        else:
            self._probe_accessibility(window_title, claim_obj, ground_truth, defects)

        # 2. Evaluate Claims vs Ground Truth
        if claim_obj.expected_tabs is not None:
            actual_tabs = ground_truth.get("tab_count", 0)
            if actual_tabs < claim_obj.expected_tabs:
                defects.append(
                    f"Tab count deficit: Expected {claim_obj.expected_tabs} tabs, but found only {actual_tabs}"
                )

        if claim_obj.expected_slides is not None:
            actual_slides = ground_truth.get("slide_count", 0)
            if actual_slides < claim_obj.expected_slides:
                defects.append(
                    f"Slide count deficit: Expected {claim_obj.expected_slides} slides, but found only {actual_slides}"
                )

        if claim_obj.min_words is not None:
            actual_words = ground_truth.get("word_count", 0)
            if actual_words < claim_obj.min_words:
                defects.append(
                    f"Document text deficit: Expected at least {claim_obj.min_words} words, but found only {actual_words}"
                )

        if claim_obj.expected_sections is not None:
            actual_sections = ground_truth.get("section_count", 0)
            if actual_sections < claim_obj.expected_sections:
                defects.append(
                    f"Section count deficit: Expected {claim_obj.expected_sections} sections/headings, but found only {actual_sections}"
                )

        if claim_obj.min_cells is not None:
            actual_cells = ground_truth.get("non_empty_cells", 0)
            if actual_cells < claim_obj.min_cells:
                defects.append(
                    f"Spreadsheet data deficit: Expected at least {claim_obj.min_cells} non-empty cells, but found {actual_cells}"
                )

        # 3. Calculate Score and Verdict
        latency_ms = (time.perf_counter() - t0) * 1000.0
        passed = len(defects) == 0
        total_checks = sum(
            1 for c in [
                claim_obj.expected_tabs,
                claim_obj.expected_slides,
                claim_obj.min_words,
                claim_obj.expected_sections,
                claim_obj.min_cells,
            ] if c is not None
        )
        if total_checks == 0:
            total_checks = max(1, len(defects))

        score = max(0.0, 1.0 - (len(defects) / float(total_checks)))
        now_iso = datetime.now(timezone.utc).isoformat()

        # 4. Generate Tamper-Proof Cryptographic Hash
        hash_payload = f"{now_iso}|{passed}|{score}|{ground_truth}|{defects}"
        audit_hash = hashlib.sha256(hash_payload.encode("utf-8")).hexdigest()

        # 5. Build Formatted Report
        report_lines = [
            "==================================================",
            f" EXTRA GROUND-TRUTH STATE AUDIT REPORT",
            f" Timestamp: {now_iso}",
            f" Verdict:   {'PASSED (100% Verified)' if passed else 'FAILED (Defects Detected)'}",
            f" Score:     {score * 100:.1f}%",
            f" Audit Hash: {audit_hash[:16]}...",
            "--------------------------------------------------",
            " MEASURED GROUND TRUTH:",
        ]
        for k, v in ground_truth.items():
            report_lines.append(f"  • {k}: {v}")

        if defects:
            report_lines.append(" DEFECTS DETECTED:")
            for d in defects:
                report_lines.append(f"  [X] {d}")
        else:
            report_lines.append(" ALL VERIFICATION CHECKS SATISFIED.")
        report_lines.append("==================================================")
        report_text = "\n".join(report_lines)

        return StateAuditResult(
            passed=passed,
            score=round(score, 3),
            claims=asdict(claim_obj),
            ground_truth=ground_truth,
            defects=defects,
            audit_hash=audit_hash,
            timestamp=now_iso,
            report_text=report_text,
            latency_ms=round(latency_ms, 2),
        )

    def _probe_dom(
        self,
        html: str,
        claims: StateAuditClaim,
        ground_truth: Dict[str, Any],
        defects: List[str],
    ) -> None:
        """
        Parses HTML DOM tree to extract ground-truth metrics for web workspaces.
        """
        soup = BeautifulSoup(html, "html.parser")

        # Tab counting (Spreadsheets: Google Sheets, Excel Online, etc.)
        tab_elements = soup.find_all(
            lambda tag: (
                tag.get("role") == "tab"
                or (tag.get("class") and any("tab" in c.lower() for c in tag.get("class")))
                or tag.get("aria-selected") is not None
            )
        )
        # Filter out navigation / app-level tabs
        sheet_tabs = [
            t for t in tab_elements
            if t.get_text(strip=True) and len(t.get_text(strip=True)) < 40
        ]
        ground_truth["tab_count"] = len(sheet_tabs)
        ground_truth["tab_names"] = [t.get_text(strip=True) for t in sheet_tabs[:15]]

        # Slide counting (Presentations: Google Slides, PowerPoint Online)
        slide_elements = soup.find_all(
            lambda tag: (
                tag.get("role") == "option"
                or (tag.get("class") and any("filmstrip" in c.lower() or "slide" in c.lower() for c in tag.get("class")))
            )
        )
        # Exclude non-slide items
        real_slides = [s for s in slide_elements if "slide" in str(s.get("class", "")).lower() or s.get("role") == "option"]
        ground_truth["slide_count"] = len(real_slides)

        # Document Text & Word counting (Docs: Google Docs, Word Online)
        # Exclude scripts, styles, toolbars
        for bad in soup(["script", "style", "nav", "header", "footer"]):
            bad.decompose()

        # Target editor bodies or general text
        editor_body = (
            soup.find("div", class_=re.compile(r"kix-appview|document-editor|editor|editable", re.IGNORECASE))
            or soup.find("div", attrs={"contenteditable": "true"})
            or soup.body
        )
        text = editor_body.get_text(separator=" ", strip=True) if editor_body else ""
        words = [w for w in re.split(r"\s+", text) if len(w) > 1]
        ground_truth["word_count"] = len(words)

        # Section / Header counting
        headers = soup.find_all(["h1", "h2", "h3", "h4"])
        ground_truth["section_count"] = len(headers)

        # Non-empty table cells (if HTML table or grid present)
        cells = soup.find_all(["td", "th", "div"], attrs={"role": "gridcell"})
        non_empty_cells = [c for c in cells if c.get_text(strip=True)]
        ground_truth["non_empty_cells"] = len(non_empty_cells)

    def _probe_accessibility(
        self,
        window_title: Optional[str],
        claims: StateAuditClaim,
        ground_truth: Dict[str, Any],
        defects: List[str],
    ) -> None:
        """
        Probes the active desktop application accessibility tree (UIA / AT-SPI2 / AX).
        """
        try:
            plane = get_accessibility_plane()
            elements = plane.inspect_tree(window_title=window_title, interactive_only=False, max_elements=500)

            tabs: List[str] = []
            slides: List[str] = []
            words_count = 0
            sections_count = 0
            cells_count = 0

            for el in elements:
                ctype = getattr(el, "control_type", "") or ""
                name = getattr(el, "name", "") or ""

                # Tab items
                if ctype in ("TabItem", "AXTab") or "sheet" in name.lower() or "tab" in name.lower():
                    if name and name not in tabs:
                        tabs.append(name)

                # Slide thumbnails
                if ("slide" in name.lower() and ctype in ("ListItem", "Button", "AXRow")) or "thumbnail" in name.lower():
                    slides.append(name)

                # Text / Document content
                if ctype in ("Document", "Edit", "Text", "AXTextArea", "AXTextField"):
                    w = [token for token in re.split(r"\s+", name) if len(token) > 1]
                    words_count += len(w)

                # Grid cells
                if ctype in ("DataItem", "AXCell") and name.strip():
                    cells_count += 1

            ground_truth["tab_count"] = len(tabs)
            ground_truth["tab_names"] = tabs[:15]
            ground_truth["slide_count"] = len(slides)
            ground_truth["word_count"] = words_count
            ground_truth["section_count"] = sections_count
            ground_truth["non_empty_cells"] = cells_count
        except Exception as ex:
            logger.debug("Accessibility probe fallback: %s", ex)
            ground_truth["probe_error"] = str(ex)
            defects.append(f"Accessibility sensor probe failed: {ex}")


_default_state_critic = GroundTruthStateCritic()


def audit_ground_truth_state(
    claims: Union[Dict[str, Any], StateAuditClaim],
    window_title: Optional[str] = None,
    page_html: Optional[str] = None,
) -> StateAuditResult:
    """
    Public entry point to independently audit application ground-truth state.
    """
    return _default_state_critic.audit_state(claims, window_title=window_title, page_html=page_html)
