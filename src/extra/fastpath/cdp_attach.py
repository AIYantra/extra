"""
Project Extra — Live-Browser CDP Attach Fast-Path (EXTRA_FORM_FILL_SPEED_RFC Step 1).

Generic attach path to the user's running Edge/Chrome via Playwright
``connect_over_cdp``. No app-specific branches: this module only speaks the
generic DevTools protocol (target list, page pick, selector fill) and works
with any Chromium-based browser or any web page.

Two operating modes (decided by the highest-risk spike, 2026-11-07):
  1. Daily-driver attach — only possible when the browser was started with
     ``--remote-debugging-port`` (probed read-only, never clicked/typed).
     Stock daily Chrome/Edge has NO CDP endpoint, so this mode usually
     answers "closed" and the caller must surface the guided error.
  2. Automation-profile attach (default recommendation) — Edge/Chrome
     relaunched under a NEW Extra profile with remote debugging; the daily
     profile is never touched.

Security: binds/probes 127.0.0.1 only. Never opens a debugging port on a
profile without telling the user; never attaches to file:// secrets.
"""

from __future__ import annotations

import json
import time
import urllib.request
from typing import Any, Dict, List, Mapping, Optional

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # Optional dependency; attach path errors clearly when missing.
    sync_playwright = None


DEFAULT_CDP_PORT = 9222
DEFAULT_CDP_HOST = "127.0.0.1"

EXTRA_AUTOMATION_PROFILE_DIR = "%USERPROFILE%\\.extra-browser-profile"

_GUIDED_RELAUNCH_COMMANDS = (
    "Relaunch the browser under a NEW Extra automation profile (your daily "
    "profile stays untouched), then retry. Close ALL windows of that browser first."
    "\nMicrosoft Edge:\n"
    '  msedge.exe --remote-debugging-port=9222 --user-data-dir="%USERPROFILE%\\.extra-browser-profile"'
    "\nGoogle Chrome:\n"
    '  chrome.exe --remote-debugging-port=9222 --user-data-dir="%USERPROFILE%\\.extra-browser-profile"'
    "\nThen log in to the site once inside that window — the session persists in the Extra profile."
)


def guided_attach_error(
    host: str = DEFAULT_CDP_HOST,
    port: int = DEFAULT_CDP_PORT,
    channel: Optional[str] = None,
) -> Dict[str, Any]:
    """Standard guided error returned when no live-browser CDP endpoint answers."""
    browser = (channel or "Edge/Chrome").strip() or "Edge/Chrome"
    return {
        "success": False,
        "attached": False,
        "error": (
            f"No live-browser CDP endpoint answered at {host}:{port} "
            f"(probed read-only). Extra refuses to blind-click the live browser. {_GUIDED_RELAUNCH_COMMANDS}"
        ),
        "browser_hint": browser,
        "endpoint": f"http://{host}:{port}",
        "remediation": _GUIDED_RELAUNCH_COMMANDS,
    }


def endpoint_url(host: str = DEFAULT_CDP_HOST, port: int = DEFAULT_CDP_PORT) -> str:
    """Builds the CDP HTTP endpoint URL for a loopback debugging port."""
    return f"http://{host}:{port}"


def probe_cdp_endpoint(
    host: str = DEFAULT_CDP_HOST,
    port: int = DEFAULT_CDP_PORT,
    timeout_sec: float = 3.0,
) -> Dict[str, Any]:
    """
    Read-only probe of ``GET /json/list`` on a loopback debugging port.

    Never clicks, types, or mutates anything. Returns
    ``{"open": bool, "targets": [...], "endpoint": url}``.
    """
    url = endpoint_url(host, port)
    try:
        req = urllib.request.Request(f"{url}/json/list", method="GET")
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            payload = resp.read().decode("utf-8", errors="replace")
        targets = json.loads(payload)
        if not isinstance(targets, list):
            targets = []
        return {"open": True, "targets": targets, "endpoint": url}
    except Exception as ex:
        return {"open": False, "targets": [], "endpoint": url, "error": str(ex)[:200]}


def pick_target(
    targets: List[Dict[str, Any]],
    url_match: Optional[str] = None,
    title_match: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Picks the best DevTools target: ``type == "page"`` entries first,
    filtered by URL/title substring when given. Returns None when empty.
    """
    pages = [t for t in targets if isinstance(t, dict) and t.get("type") == "page"]
    pool = pages or [t for t in targets if isinstance(t, dict)]
    if url_match:
        needle = url_match.lower()
        matched = [t for t in pool if needle in str(t.get("url", "")).lower()]
        if matched:
            pool = matched
    if title_match:
        needle = title_match.lower()
        matched = [t for t in pool if needle in str(t.get("title", "")).lower()]
        if matched:
            pool = matched
    return pool[0] if pool else None


class LiveBrowserSession:
    """
    Attached live-browser session over an existing CDP endpoint.

    Owns only the Playwright CDP *connection* — ``close()`` disconnects the
    client and never closes the user's browser windows.
    """

    def __init__(self) -> None:
        self._pw = None
        self._cdp = None
        self._page = None
        self.endpoint: Optional[str] = None

    # -- lifecycle ------------------------------------------------------
    @classmethod
    def attach(
        cls,
        endpoint: Optional[str] = None,
        host: str = DEFAULT_CDP_HOST,
        port: int = DEFAULT_CDP_PORT,
        url_match: Optional[str] = None,
        title_match: Optional[str] = None,
    ) -> "LiveBrowserSession":
        """Attaches to a live browser; raises RuntimeError with guidance on failure."""
        if sync_playwright is None:
            raise RuntimeError(
                "Playwright is not installed, so live-browser attach is unavailable. "
                "Install it with: pip install playwright  (no browser download needed for attach). "
                + _GUIDED_RELAUNCH_COMMANDS
            )
        sess = cls()
        sess.endpoint = endpoint or endpoint_url(host, port)
        try:
            sess._pw = sync_playwright().start()
            sess._cdp = sess._pw.chromium.connect_over_cdp(sess.endpoint)
        except Exception as ex:
            sess.close()
            raise RuntimeError(
                f"Could not attach to live browser at {sess.endpoint}: {ex}. "
                + _GUIDED_RELAUNCH_COMMANDS
            ) from ex
        contexts = sess._cdp.contexts
        ctx = contexts[0] if contexts else sess._cdp.new_context()
        page = None
        if url_match or title_match:
            for cand in ctx.pages:
                try:
                    curl = (cand.url or "").lower()
                    ctitle = (cand.title() or "").lower()
                except Exception:
                    continue
                ok = True
                if url_match and url_match.lower() not in curl:
                    ok = False
                if title_match and title_match.lower() not in ctitle:
                    ok = False
                if ok:
                    page = cand
                    break
        if page is None:
            try:
                page = ctx.pages[0] if ctx.pages else ctx.new_page()
            except Exception as ex:
                sess.close()
                raise RuntimeError(f"Live browser has no usable page: {ex}") from ex
        try:
            page.bring_to_front()
        except Exception:
            pass
        sess._page = page
        return sess

    @property
    def page(self):  # type: ignore[no-untyped-def]
        """Returns the attached Playwright page (raises if detached)."""
        if self._page is None:
            raise RuntimeError("Live browser session is not attached.")
        return self._page

    def close(self) -> None:
        """Disconnects the CDP client session. The user's browser stays open."""
        if self._cdp is not None:
            try:
                self._cdp.close()
            except Exception:
                pass
            self._cdp = None
        if self._pw is not None:
            try:
                self._pw.stop()
            except Exception:
                pass
            self._pw = None
        self._page = None

    # -- page primitives ------------------------------------------------
    def snapshot_forms(self) -> Dict[str, Any]:
        """Lists fillable fields on the live page: selector, label, type."""
        fields = self.page.eval_on_selector_all(
            "input, textarea, select",
            """els => els.map(e => {
                const lbl = (e.getAttribute('aria-label') || e.name || e.id || e.placeholder || e.type || e.tagName);
                return {selector: (e.id ? '#' + e.id : (e.name ? `[name="${e.name}"]` : e.tagName.toLowerCase())),
                        tag: e.tagName.toLowerCase(), type: (e.type || ''),
                        name: (e.name || ''), id: (e.id || ''),
                        label: (lbl || '').slice(0, 80),
                        placeholder: (e.placeholder || '').slice(0, 80)};
            })""",
        )
        return {"success": True, "url": self.page.url, "fields": fields or []}

    def fill_many(
        self,
        fields: Mapping[str, str],
        submit: bool = False,
        submit_selector: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        One-turn selector→value fill. Uses native Playwright fill/select/check
        so ``input``/``change`` events fire exactly like real typing.
        Never submits unless ``submit=True`` (default False).
        """
        if not fields:
            return {"success": False, "error": "No fields provided: pass {selector: value}."}
        t0 = time.perf_counter()
        filled: List[str] = []
        failed: List[Dict[str, str]] = []
        for selector, value in fields.items():
            try:
                kind = self.page.eval_on_selector(
                    selector,
                    "e => ({tag: e.tagName.toLowerCase(), type: (e.type || '').toLowerCase()})",
                )
                tag = (kind or {}).get("tag", "")
                itype = (kind or {}).get("type", "")
                if tag == "select":
                    self.page.select_option(selector, str(value), timeout=5000)
                elif itype in ("checkbox", "radio"):
                    want = str(value).strip().lower() in ("1", "true", "yes", "on", "checked")
                    if want:
                        self.page.check(selector, timeout=5000)
                    else:
                        self.page.uncheck(selector, timeout=5000)
                else:
                    self.page.fill(selector, str(value), timeout=10000)
                filled.append(selector)
            except Exception as ex:
                failed.append({"selector": selector, "error": str(ex)[:200]})
        submitted = False
        if submit and not failed:
            try:
                if submit_selector:
                    self.page.click(submit_selector, timeout=5000)
                else:
                    clicked = self.page.eval_on_selector_all(
                        "form button[type=submit], form input[type=submit], button[type=submit]",
                        "els => { if (els.length) { els[0].click(); return true; } return false; }",
                    )
                    if not clicked:
                        self.page.keyboard.press("Enter")
                submitted = True
            except Exception as ex:
                failed.append({"selector": submit_selector or "<submit>", "error": str(ex)[:200]})
        duration_ms = (time.perf_counter() - t0) * 1000.0
        return {
            "success": len(failed) == 0,
            "filled": filled,
            "failed": failed,
            "submitted": submitted,
            "duration_ms": round(duration_ms, 2),
            "url": self.page.url,
        }

    def click_selector(self, selector: str) -> Dict[str, Any]:
        """Clicks a selector on the live page."""
        t0 = time.perf_counter()
        self.page.click(selector, timeout=10000)
        return {
            "success": True,
            "selector": selector,
            "duration_ms": round((time.perf_counter() - t0) * 1000.0, 2),
            "url": self.page.url,
        }

    def eval_js(self, script: str) -> Any:
        """Evaluates JavaScript in the live page context."""
        return self.page.evaluate(script)


def fill_form(
    fields: Mapping[str, str],
    submit: bool = False,
    submit_selector: Optional[str] = None,
    url_match: Optional[str] = None,
    title_match: Optional[str] = None,
    host: str = DEFAULT_CDP_HOST,
    port: int = DEFAULT_CDP_PORT,
) -> Dict[str, Any]:
    """
    One-turn live-browser form fill: probe → attach → fill → detach.

    Returns the guided relaunch error (never blind clicks) when no CDP
    endpoint answers. Detaches afterwards; the browser stays open.
    """
    probe = probe_cdp_endpoint(host=host, port=port)
    if not probe["open"]:
        return guided_attach_error(host=host, port=port)
    sess: Optional[LiveBrowserSession] = None
    try:
        sess = LiveBrowserSession.attach(
            endpoint=probe["endpoint"], url_match=url_match, title_match=title_match
        )
        res = sess.fill_many(fields, submit=submit, submit_selector=submit_selector)
        res["attached"] = True
        return res
    except RuntimeError as ex:
        return {"success": False, "attached": False, "error": str(ex)[:600]}
    finally:
        if sess is not None:
            sess.close()


def execute_browser_fill_action(act) -> dict:
    """
    Batch-dispatcher entry point for ``{"action": "browser_fill"}``.

    Platform-independent (pure CDP + stdlib): probe, attach, fill, detach.
    Every ``execute_batch_actions`` backend routes here; without a CDP
    endpoint the result is the guided relaunch error, never blind clicks.
    """
    raw_fields = act.get("fields") or {}
    fields = {str(k): ("" if v is None else str(v)) for k, v in dict(raw_fields).items()}
    host = str(act.get("host", DEFAULT_CDP_HOST))
    try:
        port = int(act.get("port", DEFAULT_CDP_PORT))
    except (TypeError, ValueError):
        port = DEFAULT_CDP_PORT
    url_match = act.get("url_match")
    title_match = act.get("title_match") or act.get("window_title")
    submit = bool(act.get("submit", False))
    item = {
        "action": "browser_fill",
        "success": False,
        "attached": False,
        "fields": fields,
        "submit_requested": submit,
    }
    probe = probe_cdp_endpoint(host=host, port=port)
    if not probe["open"]:
        item["error"] = guided_attach_error(host=host, port=port)["error"]
        item["remediation"] = _GUIDED_RELAUNCH_COMMANDS
        return item
    sess = None
    try:
        sess = LiveBrowserSession.attach(
            endpoint=probe["endpoint"], url_match=url_match, title_match=title_match
        )
        item["attached"] = True
        if not fields:
            snap = sess.snapshot_forms()
            item["success"] = True
            item["snapshot_only"] = True
            item["available_fields"] = snap.get("fields", [])
            item["url"] = snap.get("url", "")
            return item
        res = sess.fill_many(
            fields, submit=submit, submit_selector=act.get("submit_selector")
        )
        item["success"] = bool(res.get("success"))
        item["filled"] = res.get("filled", [])
        item["submitted"] = res.get("submitted", False)
        item["url"] = res.get("url", "")
        if not res.get("success"):
            item["error"] = "; ".join(
                f"{f.get('selector')}: {f.get('error')}" for f in res.get("failed", [])
            )[:600]
        return item
    except RuntimeError as ex:
        item["error"] = str(ex)[:600]
        return item
    finally:
        if sess is not None:
            sess.close()
