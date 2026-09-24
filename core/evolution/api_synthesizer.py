"""
Extra Evolution — API & CLI Synthesizer
Automatically generates production-grade, typed Python clients, CLIs, and FastMCP
tool definitions from intercepted browser network traces.
"""

from __future__ import annotations

import json
import os
import re
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse, parse_qs

from extra.core.scout.cdp_sniffer import CapturedRequest
from extra.core.scout.session_vault import ServiceSession

logger = logging.getLogger("extra.evolution.api_synthesizer")


def _sanitize_identifier(name: str) -> str:
    """Converts arbitrary strings into valid Python identifiers."""
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", name).lower()
    if cleaned and cleaned[0].isdigit():
        cleaned = f"fn_{cleaned}"
    return cleaned or "action"


class ApiSynthesizer:
    """Synthesizes Python scripts, CLIs, and MCP tools from network traces."""

    @staticmethod
    def synthesize_fastpath_module(
        service_name: str,
        action_name: str,
        captured_request: CapturedRequest,
        session: Optional[ServiceSession] = None,
    ) -> str:
        """
        Generates complete Python source code for an autonomous API fast-path.
        """
        fn_name = _sanitize_identifier(action_name)
        module_slug = _sanitize_identifier(service_name)
        url = captured_request.url
        method = captured_request.method.upper()

        # Parse query params
        parsed_url = urlparse(url)
        base_endpoint = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
        query_params = {k: v[0] if len(v) == 1 else v for k, v in parse_qs(parsed_url.query).items()}

        # Headers extraction
        headers = {}
        if session:
            headers = session.get_request_headers()
        else:
            # Use captured headers, filtering host and content-length
            for k, v in captured_request.headers.items():
                if k.lower() not in ("host", "content-length", "connection", "accept-encoding"):
                    headers[k] = v

        # Payload handling
        body_data = captured_request.post_data
        is_json = isinstance(body_data, dict) or (isinstance(body_data, str) and body_data.startswith("{"))
        
        # Format payload as code
        if is_json:
            if isinstance(body_data, str):
                try:
                    payload_repr = json.dumps(json.loads(body_data), indent=4)
                except Exception:
                    payload_repr = repr(body_data)
            else:
                payload_repr = json.dumps(body_data, indent=4)
        else:
            payload_repr = repr(body_data)

        headers_repr = json.dumps(headers, indent=4)
        params_repr = json.dumps(query_params, indent=4) if query_params else "{}"

        # Generate module template
        code = f'''"""
Autonomous Fast-Path Client for {service_name.capitalize()}
Synthesized automatically by Extra MCP Evolution Engine.
Direct programmatic execution bypassing UI token waste.
"""

from __future__ import annotations

import sys
import json
import logging
from typing import Dict, Any, Optional
import httpx

logger = logging.getLogger("extra.fastpath.{module_slug}")

ENDPOINT = "{base_endpoint}"
DEFAULT_HEADERS = {headers_repr}
DEFAULT_PARAMS = {params_repr}


def {fn_name}(
    payload_override: Optional[Dict[str, Any]] = None,
    params_override: Optional[Dict[str, Any]] = None,
    headers_override: Optional[Dict[str, str]] = None,
    timeout: float = 30.0,
) -> Dict[str, Any]:
    """
    Executes the synthesized '{action_name}' mutation.
    """
    headers = dict(DEFAULT_HEADERS)
    if headers_override:
        headers.update(headers_override)

    params = dict(DEFAULT_PARAMS)
    if params_override:
        params.update(params_override)

    data = {payload_repr}
    if payload_override and isinstance(data, dict):
        data.update(payload_override)

    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        try:
            if "{method}" in ("POST", "PUT", "PATCH"):
                if isinstance(data, dict):
                    response = client.request("{method}", ENDPOINT, headers=headers, params=params, json=data)
                else:
                    response = client.request("{method}", ENDPOINT, headers=headers, params=params, content=data)
            else:
                response = client.request("{method}", ENDPOINT, headers=headers, params=params)

            response.raise_for_status()
            try:
                return {{"success": True, "status": response.status_code, "data": response.json()}}
            except Exception:
                return {{"success": True, "status": response.status_code, "text": response.text[:1000]}}

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error executing {action_name}: {{e}}")
            return {{"success": False, "status": e.response.status_code, "error": str(e)}}
        except Exception as e:
            logger.error(f"Unexpected error executing {action_name}: {{e}}")
            return {{"success": False, "error": str(e)}}


# CLI Entrypoint
if __name__ == "__main__":
    print(f"Executing fast-path {fn_name}...")
    result = {fn_name}()
    print(json.dumps(result, indent=2))
'''
        return code

    @classmethod
    def save_fastpath_file(
        cls,
        code: str,
        service_name: str,
        target_dir: Optional[Path] = None,
    ) -> Path:
        """Saves generated code into extra/fastpath/web/<service_name>.py."""
        slug = _sanitize_identifier(service_name)
        if target_dir is None:
            target_dir = Path(__file__).resolve().parent.parent.parent / "fastpath" / "web"

        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / f"{slug}.py"

        file_path.write_text(code, encoding="utf-8")
        logger.info(f"Synthesized fast-path saved to {file_path}")
        return file_path
