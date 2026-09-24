"""
Extra Scout — Session & Auth Vault
Safely extracts active session cookies, CSRF tokens, and authorization headers
from live Edge/Chrome browser contexts without requiring OAuth apps or API keys.
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

from extra.core.scout.cdp_sniffer import CapturedRequest

logger = logging.getLogger("extra.scout.session_vault")

# Sensitive header names to track
AUTH_HEADER_KEYS = {
    "authorization",
    "x-csrftoken",
    "x-csrf-token",
    "x-fb-lsd",
    "x-asbd-id",
    "x-ig-app-id",
    "x-twitter-auth-tags",
    "x-client-data",
    "cookie",
}


@dataclass
class ServiceSession:
    """Represents an active, authenticated web session ready for API fast-paths."""
    domain: str
    cookies: Dict[str, str] = field(default_factory=dict)
    auth_headers: Dict[str, str] = field(default_factory=dict)
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    origin: Optional[str] = None

    def get_cookie_header(self) -> str:
        """Formats cookies into standard 'Cookie: key=value; ...' header."""
        return "; ".join([f"{k}={v}" for k, v in self.cookies.items()])

    def get_request_headers(self) -> Dict[str, str]:
        """Combines headers, cookies, and user agent into a ready-to-use request header dict."""
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json, text/plain, */*",
        }
        if self.origin:
            headers["Origin"] = self.origin
            headers["Referer"] = f"{self.origin}/"

        if self.cookies:
            headers["Cookie"] = self.get_cookie_header()

        headers.update(self.auth_headers)
        return headers

    def to_redacted_dict(self) -> Dict[str, Any]:
        """Returns safe representation for logs and display without leaking raw secrets."""
        redacted_cookies = {k: ("***" if len(v) < 8 else f"{v[:3]}...{v[-3:]}") for k, v in self.cookies.items()}
        redacted_headers = {}
        for k, v in self.auth_headers.items():
            if any(s in k.lower() for s in ["auth", "token", "lsd", "secret", "key"]):
                redacted_headers[k] = "***REDACTED***"
            else:
                redacted_headers[k] = v

        return {
            "domain": self.domain,
            "cookies_count": len(self.cookies),
            "cookies_sample": redacted_cookies,
            "auth_headers": redacted_headers,
            "origin": self.origin,
        }


class SessionVault:
    """Extracts, isolates, and manages authenticated browser sessions."""

    @staticmethod
    def extract_from_context(context: Any, target_url: Optional[str] = None) -> ServiceSession:
        """
        Extracts cookies and session metadata from a Playwright BrowserContext.
        """
        domain = "localhost"
        origin = None
        if target_url:
            parsed = urlparse(target_url)
            domain = parsed.netloc
            origin = f"{parsed.scheme}://{parsed.netloc}"

        cookies_dict: Dict[str, str] = {}
        try:
            raw_cookies = context.cookies(urls=[target_url] if target_url else None)
            for c in raw_cookies:
                cookies_dict[c["name"]] = c["value"]
        except Exception as e:
            logger.warning(f"Could not extract cookies from browser context: {e}")

        return ServiceSession(
            domain=domain,
            cookies=cookies_dict,
            origin=origin,
        )

    @staticmethod
    def extract_auth_from_requests(captured_requests: List[CapturedRequest], target_domain: Optional[str] = None) -> Dict[str, str]:
        """
        Identifies and extracts custom authorization and CSRF headers from captured requests.
        """
        auth_headers: Dict[str, str] = {}

        for req in captured_requests:
            if target_domain and target_domain not in req.url:
                continue

            for header_name, header_val in req.headers.items():
                norm_name = header_name.lower()
                if norm_name in AUTH_HEADER_KEYS and norm_name != "cookie":
                    auth_headers[header_name] = header_val

        return auth_headers

    @classmethod
    def assemble_session(
        cls,
        context: Optional[Any],
        captured_requests: List[CapturedRequest],
        target_url: str,
    ) -> ServiceSession:
        """Assembles a complete ServiceSession from both browser context and network traces."""
        parsed = urlparse(target_url)
        domain = parsed.netloc

        session = cls.extract_from_context(context, target_url) if context else ServiceSession(domain=domain)
        session.domain = domain
        session.origin = f"{parsed.scheme}://{parsed.netloc}"

        # Merge headers captured over the wire
        wire_headers = cls.extract_auth_from_requests(captured_requests, domain)
        session.auth_headers.update(wire_headers)

        return session
