"""
Tests for Project Extra — Resilient Web Workspace Fast-Path Engine
"""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from extra.fastpath.web_workspace import (
    WorkspaceExportProvider,
    configure_workspace_browser_flags,
    extract_workspace_info,
    get_official_export_url,
    register_workspace_provider,
    trigger_workspace_export,
)


def test_extract_workspace_info_google_docs():
    url = "https://docs.google.com/document/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit?tab=t.0"
    info = extract_workspace_info(url)
    assert info is not None
    assert info["provider"] == "google_workspace"
    assert info["doc_type"] == "document"
    assert info["doc_id"] == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
    assert "pdf" in info["supported_formats"]
    assert "docx" in info["supported_formats"]


def test_extract_workspace_info_google_sheets():
    url = "https://docs.google.com/spreadsheets/d/1X5abc12345XYZ/edit#gid=0"
    info = extract_workspace_info(url)
    assert info is not None
    assert info["provider"] == "google_workspace"
    assert info["doc_type"] == "spreadsheets"
    assert info["doc_id"] == "1X5abc12345XYZ"
    assert "xlsx" in info["supported_formats"]
    assert "csv" in info["supported_formats"]


def test_extract_workspace_info_google_slides():
    url = "https://docs.google.com/presentation/d/2Y6def67890ABC/edit#slide=id.p"
    info = extract_workspace_info(url)
    assert info is not None
    assert info["provider"] == "google_workspace"
    assert info["doc_type"] == "presentation"
    assert info["doc_id"] == "2Y6def67890ABC"
    assert "pptx" in info["supported_formats"]


def test_get_official_export_url_docs():
    url = "https://docs.google.com/document/d/my-test-doc-id/edit"
    export_pdf = get_official_export_url(url, export_format="pdf")
    assert export_pdf == "https://docs.google.com/document/d/my-test-doc-id/export?format=pdf"

    export_docx = get_official_export_url(url, export_format="docx")
    assert export_docx == "https://docs.google.com/document/d/my-test-doc-id/export?format=docx"


def test_get_official_export_url_sheets():
    url = "https://docs.google.com/spreadsheets/d/sheet-12345/edit#gid=100"
    export_pdf = get_official_export_url(url, export_format="pdf")
    assert export_pdf == "https://docs.google.com/spreadsheets/d/sheet-12345/export?format=pdf"

    export_xlsx = get_official_export_url(url, export_format="xlsx")
    assert export_xlsx == "https://docs.google.com/spreadsheets/d/sheet-12345/export?format=xlsx"


def test_get_official_export_url_slides():
    url = "https://docs.google.com/presentation/d/deck-999/edit#slide=id.p1"
    export_pdf = get_official_export_url(url, export_format="pdf")
    assert export_pdf == "https://docs.google.com/presentation/d/deck-999/export/pdf"

    export_pptx = get_official_export_url(url, export_format="pptx")
    assert export_pptx == "https://docs.google.com/presentation/d/deck-999/export/pptx"


def test_get_official_export_url_bare_id_with_type():
    export_url = get_official_export_url("raw_doc_id_99", app_type="document", export_format="pdf")
    assert export_url == "https://docs.google.com/document/d/raw_doc_id_99/export?format=pdf"


def test_custom_workspace_provider_registration():
    provider = WorkspaceExportProvider(
        name="custom_cloud",
        url_pattern=re.compile(r"https?://customcloud\.io/files/([a-zA-Z0-9]+)", re.IGNORECASE),
        type_extractor=lambda m: "document",
        id_extractor=lambda m: m.group(1),
        export_url_templates={"document": "https://customcloud.io/api/export/{doc_id}?type={format}"},
        supported_formats={"document": ["pdf", "txt"]},
    )
    register_workspace_provider(provider)

    info = extract_workspace_info("https://customcloud.io/files/doc1234")
    assert info is not None
    assert info["provider"] == "custom_cloud"
    assert info["doc_id"] == "doc1234"

    exp_url = get_official_export_url("https://customcloud.io/files/doc1234", export_format="pdf")
    assert exp_url == "https://customcloud.io/api/export/doc1234?type=pdf"


def test_browser_workspace_flags():
    flags = configure_workspace_browser_flags()
    assert "--enable-features=ClipboardContentSetting" in flags
    assert "--disable-popup-blocking" in flags
    assert any("Clipboard" in f for f in flags)


def test_trigger_workspace_export_mocked(tmp_path: Path):
    target_pdf = tmp_path / "downloaded_test.pdf"
    dummy_pdf_content = b"%PDF-1.4 Mock Authentic PDF Content for testing"

    mock_resp = MagicMock()
    mock_resp.headers = {"Content-Type": "application/pdf"}
    mock_resp.read.return_value = dummy_pdf_content
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = trigger_workspace_export(
            "https://docs.google.com/document/d/test-doc/edit",
            output_path=target_pdf,
            export_format="pdf",
        )

    assert res["success"] is True
    assert res["file_size"] == len(dummy_pdf_content)
    assert target_pdf.exists()
    assert target_pdf.read_bytes() == dummy_pdf_content
    assert res["source"] == "official_workspace_export"
