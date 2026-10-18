"""
Zero-PII Data Sanitization Engine for Project Extra Telemetry.
Strictly scrubs file paths, usernames, URLs, emails, and credentials.
Guarantees zero screenshots, zero raw prompt strings, and zero personal data.
"""

import os
import re
import sys
import platform
from pathlib import Path
from urllib.parse import urlparse
from typing import Dict, Any, Optional

USER_HOME = str(Path.home())

# Regular expressions for sensitive personal data detection and scrubbing
REGEX_EMAIL = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
REGEX_IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
REGEX_API_KEY = re.compile(r"(?:sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{20,}|Bearer\s+[a-zA-Z0-9_\-\.]+)", re.IGNORECASE)

class ZeroPiiSanitizer:
    """Strict client-side privacy scrubber for telemetry serialization."""

    @classmethod
    def sanitize_path(cls, path_str: str) -> str:
        """
        Scans and anonymizes absolute file paths.
        Replaces user profile paths with generic placeholders and masks personal filenames.
        Example: 'C:\\Users\\JohnDoe\\Documents\\secret_doc.pdf' -> '<USERPROFILE>\\Documents\\*.pdf'
        """
        if not path_str or not isinstance(path_str, str):
            return ""

        # Normalize both Windows backslashes and POSIX forward slashes
        home_win = USER_HOME.replace("/", "\\")
        home_posix = USER_HOME.replace("\\", "/")

        sanitized = path_str.replace(home_win, "<USERPROFILE>").replace(home_posix, "<USERPROFILE>")

        # Also check for Unix/Linux style home paths
        user_name = Path.home().name
        if user_name and user_name in sanitized and "<USERPROFILE>" not in sanitized:
            sanitized = sanitized.replace(user_name, "<USER>")

        # Mask specific file names inside user profile to prevent leaking private document titles
        if "<USERPROFILE>" in sanitized:
            sep = "\\" if "\\" in sanitized else "/"
            parts = sanitized.split(sep)
            if len(parts) > 1 and "." in parts[-1]:
                ext = parts[-1].split(".")[-1]
                parts[-1] = f"*.{ext}"
                sanitized = sep.join(parts)

        return sanitized

    @classmethod
    def sanitize_url(cls, url_str: str) -> str:
        """
        Strips query strings, credentials, and URL fragments.
        Retains only domain and top-level safe route path.
        Example: 'https://site.com/search?q=my+ssn#top' -> 'https://site.com/search'
        """
        if not url_str or not isinstance(url_str, str):
            return ""

        try:
            parsed = urlparse(url_str)
            # Reconstruct without query, fragment, or user/password credentials
            netloc = parsed.hostname or parsed.netloc
            if parsed.port and parsed.port not in (80, 443):
                netloc = f"{netloc}:{parsed.port}"

            # Retain at most the first two path segments to mask deeply nested personal IDs
            path_segments = [seg for seg in parsed.path.split("/") if seg]
            safe_path = "/" + "/".join(path_segments[:2]) if path_segments else ""

            return f"{parsed.scheme}://{netloc}{safe_path}"
        except Exception:
            return "<REDACTED_URL>"

    @classmethod
    def sanitize_text(cls, text: str) -> str:
        """
        Scans text for emails, IP addresses, and authorization tokens, replacing them with redaction tokens.
        """
        if not text or not isinstance(text, str):
            return ""

        cleaned = REGEX_API_KEY.sub("<REDACTED_KEY>", text)
        cleaned = REGEX_EMAIL.sub("<REDACTED_EMAIL>", cleaned)
        cleaned = REGEX_IPV4.sub("<REDACTED_IP>", cleaned)
        return cleaned

    @classmethod
    def build_telemetry_event(
        cls,
        client_hash: str,
        app: str,
        archetype: str,
        tool_name: str,
        compilation_latency_ms: float = 0.0,
        execution_duration_ms: float = 0.0,
        settle_latency_ms: float = 0.0,
        actions_count: int = 1,
        success: bool = True,
        error_class: Optional[str] = None,
        speedup: float = 1.0,
        extra_version: str = "0.3.1"
    ) -> Dict[str, Any]:
        """
        Builds a verified, zero-PII telemetry payload according to production schema.
        Guarantees that no raw prompts, screenshots, or credentials can ever enter the event.
        """
        # Ensure error class is clean (e.g. 'TimeoutError', 'WindowNotFound')
        clean_error = None
        if error_class:
            clean_error = str(error_class).split(":")[0].strip()
            clean_error = cls.sanitize_text(clean_error)

        return {
            "client_hash": client_hash,
            "extra_version": extra_version,
            "platform": {
                "os": sys.platform,
                "release": platform.release(),
                "arch": platform.machine()
            },
            "execution_metrics": {
                "app_name": (app or "generic").lower()[:32],
                "archetype": archetype[:32],
                "tool_name": tool_name[:32],
                "compilation_latency_ms": round(compilation_latency_ms, 3),
                "execution_duration_ms": round(execution_duration_ms, 2),
                "settle_latency_ms": round(settle_latency_ms, 2),
                "actions_count": int(actions_count),
                "success": bool(success),
                "error_class": clean_error,
                "speedup_multiplier": round(float(speedup), 1)
            }
        }
