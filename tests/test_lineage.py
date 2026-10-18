"""
Tests for Project Extra — Artifact Lineage & Provenance Verifier
Ensures strict detection of workflow substitution and fake programmatic exports.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from extra.core.composer.blueprint import Milestone, MilestoneStatus
from extra.core.composer.lineage import (
    ArtifactLineageVerifier,
    ArtifactOrigin,
    LineageVerdict,
    verify_artifact_lineage,
)
from extra.core.composer.verifier import MilestoneVerifier


def _create_mock_pdf(path: Path, producer: str, creator: str = "Mozilla/5.0") -> None:
    content = (
        f"%PDF-1.4\n"
        f"1 0 obj\n<< /Producer ({producer}) /Creator ({creator}) >>\nendobj\n"
        f"trailer\n<< /Info 1 0 R >>\n%%EOF"
    ).encode("latin1")
    path.write_bytes(content)


def test_lineage_detects_google_workspace_export(tmp_path: Path):
    pdf = tmp_path / "authentic_docs.pdf"
    _create_mock_pdf(pdf, producer="Google Docs", creator="Google Docs")

    verdict = verify_artifact_lineage(pdf, expected_origin=ArtifactOrigin.OFFICIAL_WEB_EXPORT)
    assert verdict.valid is True
    assert verdict.detected_origin == ArtifactOrigin.OFFICIAL_WEB_EXPORT
    assert verdict.producer == "Google Docs"
    assert len(verdict.defects) == 0


def test_lineage_detects_and_rejects_headless_chrome_substitution(tmp_path: Path):
    pdf = tmp_path / "fake_docs_headless.pdf"
    # Exact signature produced by chrome.exe --headless --print-to-pdf
    _create_mock_pdf(pdf, producer="Skia/PDF m128", creator="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

    verdict = verify_artifact_lineage(pdf, expected_origin=ArtifactOrigin.OFFICIAL_WEB_EXPORT)
    assert verdict.valid is False
    assert verdict.detected_origin == ArtifactOrigin.PROGRAMMATIC_LOCAL
    assert any("local browser print" in d for d in verdict.defects)


def test_lineage_detects_and_rejects_reportlab_script(tmp_path: Path):
    pdf = tmp_path / "python_reportlab.pdf"
    _create_mock_pdf(pdf, producer="ReportLab PDF Library - www.reportlab.com")

    verdict = verify_artifact_lineage(pdf, expected_origin=ArtifactOrigin.OFFICIAL_WEB_EXPORT)
    assert verdict.valid is False
    assert verdict.detected_origin == ArtifactOrigin.PROGRAMMATIC_LOCAL
    assert any("ReportLab" in d for d in verdict.defects)


def test_lineage_detects_desktop_app_export(tmp_path: Path):
    pdf = tmp_path / "libreoffice_doc.pdf"
    _create_mock_pdf(pdf, producer="LibreOffice 24.2", creator="Writer")

    verdict = verify_artifact_lineage(pdf, expected_origin=ArtifactOrigin.APPLICATION_EXPORT)
    assert verdict.valid is True
    assert verdict.detected_origin == ArtifactOrigin.APPLICATION_EXPORT


def test_lineage_verified_via_browser_download_source(tmp_path: Path):
    pdf = tmp_path / "browser_download.pdf"
    _create_mock_pdf(pdf, producer="Generic PDF Producer")

    verifier = ArtifactLineageVerifier()
    # Mock browser history database match
    with patch.object(
        verifier,
        "_lookup_browser_download_source",
        return_value="https://docs.google.com/document/d/xyz123/export?format=pdf",
    ):
        verdict = verifier.verify_lineage(pdf, expected_origin=ArtifactOrigin.OFFICIAL_WEB_EXPORT)

    assert verdict.valid is True
    assert verdict.detected_origin == ArtifactOrigin.OFFICIAL_WEB_EXPORT
    assert verdict.source_url is not None
    assert "docs.google.com" in verdict.source_url


def test_milestone_verifier_blocks_fake_export(tmp_path: Path):
    fake_pdf = tmp_path / "executive_briefing.pdf"
    _create_mock_pdf(fake_pdf, producer="Skia/PDF m128", creator="Mozilla/5.0")

    milestone = Milestone(
        id="m_export",
        name="Export Executive Briefing from Google Docs",
        expected_artifacts=[str(fake_pdf)],
        acceptance_criteria={
            "expected_origin": "official_web_export",
            "min_file_size_bytes": 10,
        },
    )

    verifier = MilestoneVerifier()
    res = verifier.verify_milestone(milestone)

    assert res.passed is False
    assert any("lineage violation" in d or "local browser print" in d for d in res.defects)
