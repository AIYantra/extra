"""
Project Extra — Playwright / Edge CDP Browser Fast-Path Engine
Direct semantic DOM extraction and web interaction bypassing visual token waste.
Uses Microsoft Edge (pre-installed on Windows 10/11) via Playwright.
"""

from __future__ import annotations

import base64
import time
from typing import Any, Dict, Optional

from bs4 import BeautifulSoup
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright


class BrowserFastPath:
    """
    Playwright-powered browser fast-path manager.
    Maintains a reusable browser session using Windows 10/11 native Microsoft Edge.
    """

    def __init__(self, headless: bool = True) -> None:
        self.headless = headless
        self._pw = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    def _ensure_page(self) -> Page:
        """Initializes browser and returns active page."""
        if self._page is None or self._page.is_closed():
            if self._pw is None:
                self._pw = sync_playwright().start()

            # Attempt 1: Native Windows Microsoft Edge (pre-installed, 0 download)
            try:
                self._browser = self._pw.chromium.launch(
                    channel="msedge", headless=self.headless
                )
            except Exception:
                # Attempt 2: Standard Chromium
                self._browser = self._pw.chromium.launch(headless=self.headless)

            self._context = self._browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            )
            self._page = self._context.new_page()

        return self._page

    def navigate(self, url: str, wait_until: str = "domcontentloaded") -> Dict[str, Any]:
        """Navigates to a destination URL and returns page metadata."""
        if not url.startswith(("http://", "https://", "file://")):
            url = f"https://{url}"

        t0 = time.perf_counter()
        page = self._ensure_page()
        response = page.goto(url, wait_until=wait_until, timeout=30000)
        duration_ms = (time.perf_counter() - t0) * 1000.0

        status = response.status if response else 200
        title = page.title()

        return {
            "success": True,
            "url": page.url,
            "title": title,
            "status": status,
            "duration_ms": round(duration_ms, 2),
        }

    def get_content(
        self, selector: Optional[str] = None, as_markdown: bool = True, max_length: int = 8000
    ) -> str:
        """
        Extracts clean, readable semantic content from the page.
        Strips script, style, and advert noise using BeautifulSoup.
        """
        page = self._ensure_page()

        if selector:
            element = page.query_selector(selector)
            html = element.inner_html() if element else ""
        else:
            html = page.content()

        if not html:
            return ""

        soup = BeautifulSoup(html, "html.parser")

        # Strip uninformative elements
        for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
            tag.decompose()

        if as_markdown:
            # Extract structured text with headings and links
            lines = []
            for el in soup.find_all(["h1", "h2", "h3", "h4", "p", "li", "a", "button"]):
                text = el.get_text(strip=True)
                if not text:
                    continue

                if el.name == "h1":
                    lines.append(f"\n# {text}\n")
                elif el.name == "h2":
                    lines.append(f"\n## {text}\n")
                elif el.name == "h3":
                    lines.append(f"\n### {text}\n")
                elif el.name == "li":
                    lines.append(f"- {text}")
                elif el.name == "a" and el.get("href"):
                    href = el.get("href")
                    if href.startswith("http"):
                        lines.append(f"[{text}]({href})")
                else:
                    lines.append(text)

            content = "\n".join(lines)
        else:
            content = soup.get_text(separator="\n", strip=True)

        if len(content) > max_length:
            content = content[:max_length] + f"\n\n... [Truncated: {len(content) - max_length} additional characters]"

        return content

    def click(self, selector: str) -> Dict[str, Any]:
        """Clicks an element matching CSS or XPath selector."""
        page = self._ensure_page()
        t0 = time.perf_counter()
        page.click(selector, timeout=10000)
        duration_ms = (time.perf_counter() - t0) * 1000.0

        return {
            "success": True,
            "selector": selector,
            "duration_ms": round(duration_ms, 2),
            "current_url": page.url,
        }

    def fill(self, selector: str, value: str) -> Dict[str, Any]:
        """Fills an input, textarea, or contenteditable field."""
        page = self._ensure_page()
        t0 = time.perf_counter()
        page.fill(selector, value, timeout=10000)
        duration_ms = (time.perf_counter() - t0) * 1000.0

        return {
            "success": True,
            "selector": selector,
            "value_length": len(value),
            "duration_ms": round(duration_ms, 2),
        }

    def evaluate(self, script: str) -> Any:
        """Executes custom JavaScript inside page context."""
        page = self._ensure_page()
        return page.evaluate(script)

    def screenshot_base64(self) -> str:
        """Captures page screenshot and returns base64 encoded JPEG."""
        page = self._ensure_page()
        png_bytes = page.screenshot(type="jpeg", quality=80)
        return base64.b64encode(png_bytes).decode("utf-8")

    def close(self) -> None:
        """Closes browser session and Playwright driver."""
        if self._browser:
            try:
                self._browser.close()
            except Exception:
                pass
            self._browser = None
            self._context = None
            self._page = None

        if self._pw:
            try:
                self._pw.stop()
            except Exception:
                pass
            self._pw = None


# Shared singleton browser instance
_default_browser: Optional[BrowserFastPath] = None


def get_browser_fastpath(headless: bool = True) -> BrowserFastPath:
    """Returns or initializes the shared BrowserFastPath instance."""
    global _default_browser
    if _default_browser is None:
        _default_browser = BrowserFastPath(headless=headless)
    return _default_browser


def execute_browser_action(
    action: str,
    url: Optional[str] = None,
    selector: Optional[str] = None,
    value: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Unified high-level dispatcher for browser fast-path MCP operations.
    
    Supported actions:
        - 'navigate': Opens url.
        - 'content': Extracts semantic DOM text/markdown.
        - 'click': Clicks selector.
        - 'fill': Fills selector with value.
        - 'eval': Evaluates JavaScript value.
        - 'screenshot': Returns base64 screenshot.
        - 'close': Closes browser.
    """
    browser = get_browser_fastpath()
    act = action.strip().lower()

    if act == "navigate":
        if not url:
            return {"error": "Missing 'url' parameter for navigate action."}
        return browser.navigate(url)

    elif act in ("content", "read", "extract"):
        content = browser.get_content(selector=selector, as_markdown=True)
        return {"content": content, "url": browser._page.url if browser._page else ""}

    elif act == "click":
        if not selector:
            return {"error": "Missing 'selector' parameter for click action."}
        return browser.click(selector)

    elif act in ("fill", "type"):
        if not selector:
            return {"error": "Missing 'selector' parameter for fill action."}
        return browser.fill(selector, value or "")

    elif act in ("eval", "evaluate"):
        if not value:
            return {"error": "Missing 'value' (script) parameter for eval action."}
        res = browser.evaluate(value)
        return {"result": res}

    elif act == "screenshot":
        b64 = browser.screenshot_base64()
        return {"screenshot_base64": b64}

    elif act == "close":
        browser.close()
        return {"closed": True}

    else:
        return {"error": f"Unknown browser action: '{action}'. Supported: navigate, content, click, fill, eval, screenshot, close."}
