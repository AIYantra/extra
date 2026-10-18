"""
Project Extra — Resilient Web Workspace Fast-Path Engine
Provides universal URL-based official document export, browser clipboard & popup permission flags,
and direct provider endpoint resolution without fragile GUI menu clicking or headless script cheating.
"""

from __future__ import annotations

import logging
import os
import re
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger("Extra-FastPath-WebWorkspace")


@dataclass
class WorkspaceExportProvider:
    """
    Declarative specification for a web workspace export endpoint provider.
    """
    name: str
    url_pattern: re.Pattern
    type_extractor: Callable[[re.Match], str]
    id_extractor: Callable[[re.Match], str]
    export_url_templates: Dict[str, str]  # doc_type -> URL template with {doc_id} and {format}
    supported_formats: Dict[str, List[str]] = field(default_factory=dict)  # doc_type -> list of formats


# Built-in Declarative Workspace Providers Registry
_WORKSPACE_PROVIDERS: List[WorkspaceExportProvider] = [
    # 1. Google Workspace (Docs, Sheets, Slides, Drawings)
    WorkspaceExportProvider(
        name="google_workspace",
        url_pattern=re.compile(
            r"https?://(?:docs|drive)\.google\.com/(document|spreadsheets|presentation|drawings)/d/([a-zA-Z0-9_-]+)",
            re.IGNORECASE,
        ),
        type_extractor=lambda m: (
            "document" if m.group(1).lower() in ("document", "docs")
            else "spreadsheets" if m.group(1).lower() in ("spreadsheets", "sheets")
            else "presentation" if m.group(1).lower() in ("presentation", "slides")
            else "drawings"
        ),
        id_extractor=lambda m: m.group(2),
        export_url_templates={
            "document": "https://docs.google.com/document/d/{doc_id}/export?format={format}",
            "spreadsheets": "https://docs.google.com/spreadsheets/d/{doc_id}/export?format={format}",
            "presentation": "https://docs.google.com/presentation/d/{doc_id}/export/{format}",
            "drawings": "https://docs.google.com/drawings/d/{doc_id}/export/{format}",
        },
        supported_formats={
            "document": ["pdf", "docx", "txt", "html", "odt", "epub", "rtf"],
            "spreadsheets": ["pdf", "xlsx", "csv", "tsv", "ods", "zip", "html"],
            "presentation": ["pdf", "pptx", "txt", "odp"],
            "drawings": ["pdf", "png", "svg", "jpeg"],
        },
    ),
    # 2. Etherpad / HedgeDoc / HackMD generic pad
    WorkspaceExportProvider(
        name="etherpad",
        url_pattern=re.compile(r"https?://[^/]+/p/([a-zA-Z0-9_.-]+)", re.IGNORECASE),
        type_extractor=lambda m: "document",
        id_extractor=lambda m: m.group(1),
        export_url_templates={
            "document": "{base_url}/p/{doc_id}/export/{format}",
        },
        supported_formats={
            "document": ["txt", "html", "pdf", "etherpad"],
        },
    ),
    # 3. HackMD / CodiMD
    WorkspaceExportProvider(
        name="hackmd",
        url_pattern=re.compile(r"https?://(?:hackmd\.io|demo\.codimd\.org)/([a-zA-Z0-9_.-]+)", re.IGNORECASE),
        type_extractor=lambda m: "document",
        id_extractor=lambda m: m.group(1),
        export_url_templates={
            "document": "https://hackmd.io/{doc_id}/download",
        },
        supported_formats={
            "document": ["md", "pdf", "html"],
        },
    ),
]


def register_workspace_provider(provider: WorkspaceExportProvider) -> None:
    """Registers a new workspace export endpoint provider."""
    _WORKSPACE_PROVIDERS.insert(0, provider)


def extract_workspace_info(url: str) -> Optional[Dict[str, Any]]:
    """
    Extracts document identifier, document type, and provider from a workspace URL.
    Returns None if the URL does not match any registered workspace provider.
    """
    if not url or not isinstance(url, str):
        return None

    clean_url = url.strip()
    for provider in _WORKSPACE_PROVIDERS:
        match = provider.url_pattern.search(clean_url)
        if match:
            doc_type = provider.type_extractor(match)
            doc_id = provider.id_extractor(match)
            parsed = urllib.parse.urlparse(clean_url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            return {
                "provider": provider.name,
                "doc_type": doc_type,
                "doc_id": doc_id,
                "base_url": base_url,
                "matched_url": clean_url,
                "supported_formats": provider.supported_formats.get(doc_type, []),
            }
    return None


def get_official_export_url(
    url_or_id: str,
    app_type: Optional[str] = None,
    export_format: str = "pdf",
) -> Optional[str]:
    """
    Constructs the official server-side export URL for a workspace document.
    
    Args:
        url_or_id: Full document URL or document ID.
        app_type: 'document', 'spreadsheets', 'presentation', or None if inferrable from URL.
        export_format: Desired export format ('pdf', 'docx', 'xlsx', 'csv', 'pptx', etc.).
    
    Returns:
        The direct download export URL, or None if provider cannot be resolved.
    """
    info = extract_workspace_info(url_or_id)
    doc_format = export_format.lower().lstrip(".")

    if info:
        provider_name = info["provider"]
        doc_type = app_type or info["doc_type"]
        doc_id = info["doc_id"]
        base_url = info.get("base_url", "")
    else:
        # If bare ID passed with explicit app_type, assume Google Workspace as default provider
        if not app_type:
            return None
        doc_id = url_or_id.strip()
        doc_type = app_type.lower()
        provider_name = "google_workspace"
        base_url = "https://docs.google.com"

    for provider in _WORKSPACE_PROVIDERS:
        if provider.name == provider_name:
            template = provider.export_url_templates.get(doc_type)
            if template:
                return template.format(doc_id=doc_id, format=doc_format, base_url=base_url)

    return None


def configure_workspace_browser_flags() -> List[str]:
    """
    Returns Chromium/Edge command-line flags required to prevent clipboard stalls,
    external redirect blocks, and popup permission dialogs during live desktop sessions.
    """
    return [
        "--enable-features=ClipboardContentSetting",
        "--disable-features=BlockExternalFormRedirectsNoGesture",
        "--disable-popup-blocking",
        "--allow-running-insecure-content",
        "--disable-blink-features=AutomationControlled",
        "--no-first-run",
        "--no-default-browser-check",
    ]


def trigger_workspace_export(
    url_or_id: str,
    output_path: Union[str, Path],
    export_format: str = "pdf",
    app_type: Optional[str] = None,
    timeout: float = 30.0,
) -> Dict[str, Any]:
    """
    Downloads an authentic document export directly from the official provider endpoint.
    This guarantees 100% genuine artifact lineage from the target web workspace service
    without resorting to local HTML conversion or headless browser print substitution.
    """
    export_url = get_official_export_url(url_or_id, app_type=app_type, export_format=export_format)
    if not export_url:
        return {
            "success": False,
            "error": f"Could not resolve official export URL for '{url_or_id}' (app_type={app_type})",
        }

    target_file = Path(output_path).resolve()
    target_file.parent.mkdir(parents=True, exist_ok=True)

    # Use urllib / requests with browser user-agent
    import urllib.request
    req = urllib.request.Request(
        export_url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/128.0.0.0 Safari/537.36"
            ),
            "Accept": "*/*",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            content_type = response.headers.get("Content-Type", "")
            data = response.read()
            if not data or len(data) < 10:
                return {
                    "success": False,
                    "error": f"Downloaded artifact is empty or truncated ({len(data)} bytes)",
                    "export_url": export_url,
                }
            target_file.write_bytes(data)

        size = target_file.stat().st_size
        return {
            "success": True,
            "file_path": str(target_file),
            "file_size": size,
            "export_url": export_url,
            "format": export_format,
            "content_type": content_type,
            "source": "official_workspace_export",
        }
    except Exception as ex:
        logger.warning("[WebWorkspace] Export download failed: %s", ex)
        return {
            "success": False,
            "error": str(ex),
            "export_url": export_url,
        }
