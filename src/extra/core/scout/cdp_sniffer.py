"""
Extra Scout — CDP Network Sniffer & API Mutation Interceptor
Intercepts live network traffic (Fetch, XHR, GraphQL, REST) from Edge/Chrome
via Chrome DevTools Protocol or Playwright request listeners, isolating
reproducible mutation contracts to bypass visual UI token waste.
"""

from __future__ import annotations

import json
import re
import time
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Union
from urllib.parse import urlparse

logger = logging.getLogger("extra.scout.cdp_sniffer")

# File extensions and resource types to filter out
STATIC_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico",
    ".css", ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".mp3", ".mp4", ".wav", ".avi", ".webm",
    ".map", ".js"
}

# Third-party trackers and telemetry domains to ignore
IGNORED_DOMAINS = {
    "google-analytics.com",
    "doubleclick.net",
    "datadoghq.com",
    "sentry.io",
    "hotjar.com",
    "mixpanel.com",
    "segment.io",
    "facebook.com/tr",
    "analytics.twitter.com",
}


@dataclass
class CapturedRequest:
    """Represents an intercepted HTTP/GraphQL network call."""
    url: str
    method: str
    headers: Dict[str, str] = field(default_factory=dict)
    post_data: Optional[Union[str, Dict[str, Any]]] = None
    response_status: Optional[int] = None
    response_headers: Dict[str, str] = field(default_factory=dict)
    response_body: Optional[str] = None
    content_type: str = ""
    timestamp: float = field(default_factory=time.time)
    duration_ms: float = 0.0

    @property
    def is_api(self) -> bool:
        """Determines if the request is an API/JSON/GraphQL call rather than a static asset."""
        parsed = urlparse(self.url)
        path = parsed.path.lower()

        # Reject static file extensions
        if any(path.endswith(ext) for ext in STATIC_EXTENSIONS):
            return False

        # Reject tracking domains
        if any(ign in parsed.netloc.lower() or ign in self.url.lower() for ign in IGNORED_DOMAINS):
            return False

        # Check content-type or URL patterns
        ct = self.content_type.lower()
        if any(t in ct for t in ["application/json", "application/graphql", "text/plain"]):
            return True

        if any(marker in path for marker in ["/api/", "/graphql", "/v1/", "/v2/", "/v3/", "/rpc", "/query", "/mutation"]):
            return True

        # If it has POST JSON data, it's an API call
        if self.method.upper() in ("POST", "PUT", "PATCH", "DELETE") and self.post_data:
            return True

        return False

    @property
    def is_mutation(self) -> bool:
        """Checks if request modifies state (POST/PUT/PATCH/DELETE or GraphQL mutation)."""
        if self.method.upper() in ("POST", "PUT", "PATCH", "DELETE"):
            return True

        # Check for GraphQL mutation in query string or post_data
        body_str = str(self.post_data or "")
        if "mutation" in body_str.lower() or "mutation" in self.url.lower():
            return True

        return False

    def to_dict(self) -> Dict[str, Any]:
        """Serializes captured request to dictionary."""
        data = asdict(self)
        data["is_api"] = self.is_api
        data["is_mutation"] = self.is_mutation
        return data


class NetworkSniffer:
    """
    Attaches to a browser Page or Context to intercept, record, and filter
    actionable API requests.
    """

    def __init__(self) -> None:
        self.captured_requests: List[CapturedRequest] = []
        self._is_active: bool = False
        self._page = None
        self._pending_requests: Dict[str, CapturedRequest] = {}

    @property
    def is_active(self) -> bool:
        return self._is_active

    def attach_to_page(self, page: Any) -> None:
        """Attaches request and response event listeners to a Playwright page."""
        self._page = page
        self._is_active = True
        self.captured_requests.clear()
        self._pending_requests.clear()

        try:
            page.on("request", self._on_request)
            page.on("response", self._on_response)
            logger.info("NetworkSniffer attached to page.")
        except Exception as e:
            logger.warning(f"Failed to attach listeners to page: {e}")

    def detach(self) -> List[CapturedRequest]:
        """Stops sniffing and detaches listeners, returning captured requests."""
        if self._page and self._is_active:
            try:
                self._page.remove_listener("request", self._on_request)
                self._page.remove_listener("response", self._on_response)
            except Exception as e:
                logger.debug(f"Error removing page listeners: {e}")

        self._is_active = False
        logger.info(f"NetworkSniffer detached. Captured {len(self.captured_requests)} requests.")
        return list(self.captured_requests)

    def _on_request(self, request: Any) -> None:
        """Handler for Playwright 'request' event."""
        try:
            req_id = f"{request.method}_{request.url}_{time.time()}"
            post_data = None
            try:
                post_data = request.post_data
                if post_data:
                    try:
                        post_data = json.loads(post_data)
                    except Exception:
                        pass
            except Exception:
                pass

            headers = {}
            try:
                headers = request.headers
            except Exception:
                pass

            captured = CapturedRequest(
                url=request.url,
                method=request.method,
                headers=headers,
                post_data=post_data,
                timestamp=time.time(),
            )
            # Store in pending
            self._pending_requests[request.url] = captured
        except Exception as e:
            logger.debug(f"Error handling request event: {e}")

    def _on_response(self, response: Any) -> None:
        """Handler for Playwright 'response' event."""
        try:
            url = response.url
            captured = self._pending_requests.pop(url, None)
            if captured is None:
                captured = CapturedRequest(
                    url=url,
                    method=response.request.method if hasattr(response, "request") else "GET",
                    headers=response.request.headers if hasattr(response, "request") else {},
                    timestamp=time.time(),
                )

            captured.response_status = response.status
            captured.duration_ms = (time.time() - captured.timestamp) * 1000.0

            try:
                captured.response_headers = response.headers
                captured.content_type = response.headers.get("content-type", "")
            except Exception:
                pass

            # Only read body for API endpoints to avoid memory spikes
            if captured.is_api:
                try:
                    # Limit body preview to 4000 characters
                    body_text = response.text()
                    captured.response_body = body_text[:4000] if body_text else None
                except Exception:
                    pass

                self.captured_requests.append(captured)

        except Exception as e:
            logger.debug(f"Error handling response event: {e}")

    def get_api_mutations(self) -> List[CapturedRequest]:
        """Returns only the captured mutating API requests."""
        return [r for r in self.captured_requests if r.is_api and r.is_mutation]

    def export_summary(self) -> Dict[str, Any]:
        """Exports a clean summary of captured endpoints for LLM and synthesis."""
        mutations = self.get_api_mutations()
        return {
            "total_captured": len(self.captured_requests),
            "mutations_count": len(mutations),
            "mutations": [m.to_dict() for m in mutations[:15]],
        }
