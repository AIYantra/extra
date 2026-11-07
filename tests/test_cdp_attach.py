"""
Project Extra — CDP Attach Core Tests (EXTRA_FORM_FILL_SPEED_RFC Step 6).

Validates the live-browser attach path without touching the user's daily
browser: endpoint probe + target pick run against a local stub HTTP server,
fill mapping runs against a fake page object, and one live test attaches to
a throwaway automation-profile browser (skipped when no browser binary is
available). No wall-clock asserts anywhere.
"""

from __future__ import annotations

import json
import socket
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from extra.fastpath.cdp_attach import (
    LiveBrowserSession,
    execute_browser_fill_action,
    fill_form,
    guided_attach_error,
    pick_target,
    probe_cdp_endpoint,
)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class _StubCDPHandler(BaseHTTPRequestHandler):
    targets = [
        {
            "id": "page-1",
            "type": "page",
            "title": "Example Form",
            "url": "https://example.com/form",
            "webSocketDebuggerUrl": "ws://127.0.0.1:9/devtools/page/1",
        },
        {
            "id": "other-1",
            "type": "service_worker",
            "title": "",
            "url": "https://example.com/sw.js",
            "webSocketDebuggerUrl": "ws://127.0.0.1:9/devtools/sw/1",
        },
    ]

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/json/list":
            body = json.dumps(self.targets).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args: object) -> None:
        pass


class FakeKeyboard:
    def __init__(self) -> None:
        self.pressed: list[str] = []

    def press(self, key: str) -> None:
        self.pressed.append(key)


class FakePage:
    """Minimal stand-in for a Playwright page: records selector ops, no I/O."""

    def __init__(self, kinds: dict[str, tuple[str, str]]) -> None:
        # selector -> (tag, type)
        self.kinds = kinds
        self.filled: dict[str, str] = {}
        self.selected: dict[str, str] = {}
        self.checked: set[str] = set()
        self.unchecked: set[str] = set()
        self.clicked: list[str] = []
        self.url = "https://example.com/form"
        self.keyboard = FakeKeyboard()

    def eval_on_selector(self, selector: str, _js: str) -> dict[str, str]:
        tag, itype = self.kinds[selector]
        return {"tag": tag, "type": itype}

    def fill(self, selector: str, value: str, timeout: int = 10000) -> None:
        self.filled[selector] = value

    def select_option(self, selector: str, value: str, timeout: int = 5000) -> None:
        self.selected[selector] = value

    def check(self, selector: str, timeout: int = 5000) -> None:
        self.checked.add(selector)

    def uncheck(self, selector: str, timeout: int = 5000) -> None:
        self.unchecked.add(selector)

    def click(self, selector: str, timeout: int = 5000) -> None:
        self.clicked.append(selector)


class TestCdpProbeAndPick(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.port = _free_port()
        cls.server = HTTPServer(("127.0.0.1", cls.port), _StubCDPHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, kwargs={"poll_interval": 0.05})
        cls.thread.daemon = True
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.thread.join(timeout=5)

    def test_probe_open_lists_targets(self) -> None:
        res = probe_cdp_endpoint(port=self.port)
        self.assertTrue(res["open"])
        self.assertEqual(len(res["targets"]), 2)
        self.assertEqual(res["endpoint"], f"http://127.0.0.1:{self.port}")

    def test_probe_closed_port(self) -> None:
        res = probe_cdp_endpoint(port=_free_port())
        self.assertFalse(res["open"])
        self.assertEqual(res["targets"], [])

    def test_pick_target_prefers_pages(self) -> None:
        targets = _StubCDPHandler.targets
        self.assertEqual(pick_target(targets)["id"], "page-1")
        self.assertEqual(pick_target(targets, url_match="sw.js")["id"], "page-1")
        # url_match narrows within pages; falls back to full pool when no page matches
        picked = pick_target(targets, title_match="example form")
        self.assertEqual(picked["id"], "page-1")
        self.assertIsNone(pick_target([]))

    def test_guided_error_names_relaunch(self) -> None:
        err = guided_attach_error(port=19222, channel="chrome")
        self.assertFalse(err["success"])
        self.assertFalse(err["attached"])
        self.assertIn("--remote-debugging-port", err["remediation"])
        self.assertIn("Extra", err["remediation"])
        self.assertIn("chrome", err["browser_hint"])

    def test_fill_form_no_endpoint_never_clicks(self) -> None:
        res = fill_form({"#a": "x"}, port=_free_port())
        self.assertFalse(res["success"])
        self.assertFalse(res.get("attached", False))
        self.assertIn("remediation", res)

    def test_execute_browser_fill_action_no_endpoint(self) -> None:
        item = execute_browser_fill_action({"action": "browser_fill", "fields": {"#a": "x"}, "port": _free_port()})
        self.assertEqual(item["action"], "browser_fill")
        self.assertFalse(item["success"])
        self.assertIn("remediation", item)


class TestFillManyFakePage(unittest.TestCase):
    def _session(self) -> tuple[LiveBrowserSession, FakePage]:
        sess = LiveBrowserSession()
        page = FakePage({"#name": ("input", "text"), "#topic": ("select", "select-one"), "#news": ("input", "checkbox")})
        sess._page = page  # type: ignore[attr-defined]
        return sess, page

    def test_fill_mapping_dispatches_by_tag(self) -> None:
        sess, page = self._session()
        res = sess.fill_many({"#name": "Ada", "#topic": "bug", "#news": "yes"})
        self.assertTrue(res["success"])
        self.assertEqual(page.filled, {"#name": "Ada"})
        self.assertEqual(page.selected, {"#topic": "bug"})
        self.assertIn("#news", page.checked)
        self.assertFalse(res["submitted"])

    def test_no_submit_by_default(self) -> None:
        sess, page = self._session()
        res = sess.fill_many({"#name": "Ada"}, submit=False)
        self.assertTrue(res["success"])
        self.assertFalse(res["submitted"])
        self.assertEqual(page.keyboard.pressed, [])
        self.assertEqual(page.clicked, [])

    def test_submit_clicks_selector(self) -> None:
        sess, page = self._session()
        res = sess.fill_many({"#name": "Ada"}, submit=True, submit_selector="#go")
        self.assertTrue(res["submitted"])
        self.assertEqual(page.clicked, ["#go"])

    def test_unknown_selector_reports_failure(self) -> None:
        sess, _ = self._session()
        res = sess.fill_many({"#missing": "x"})
        self.assertFalse(res["success"])
        self.assertEqual(len(res["failed"]), 1)

    def test_empty_fields_rejected(self) -> None:
        sess, _ = self._session()
        res = sess.fill_many({})
        self.assertFalse(res["success"])


class TestLiveAttachFixture(unittest.TestCase):
    """Real attach against a throwaway automation-profile browser (never the daily profile).

    Chrome is launched as a plain subprocess with remote debugging (mirroring
    real-world usage where the browser is already running), so the test holds
    only one Playwright instance: the attach under test.
    """

    CHROME_CANDIDATES = (
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    )

    def test_attach_fill_readback(self) -> None:
        import subprocess
        import time as _time

        chrome = next((p for p in self.CHROME_CANDIDATES if Path(p).is_file()), None)
        if chrome is None:
            self.skipTest("no Chrome binary found")
        port = _free_port()
        profile_dir = Path(tempfile.mkdtemp(prefix="extra-cdp-test-"))
        fixture = profile_dir / "form.html"
        fixture.write_text(
            "<html><head><title>Fixture</title></head><body>"
            '<input id="a"><input id="b" type="email">'
            '<select id="c"><option value="x">x</option><option value="y">y</option></select>'
            '<textarea id="d"></textarea></body></html>',
            encoding="utf-8",
        )
        proc = subprocess.Popen(
            [
                chrome,
                "--headless=new",
                "--disable-gpu",
                "--no-first-run",
                "--no-default-browser-check",
                f"--remote-debugging-port={port}",
                f"--user-data-dir={profile_dir / 'profile'}",
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            probe: dict = {"open": False}
            for _ in range(100):
                probe = probe_cdp_endpoint(port=port)
                if probe["open"]:
                    break
                _time.sleep(0.1)
            self.assertTrue(probe["open"], f"CDP endpoint did not open: {probe}")
            sess = LiveBrowserSession.attach(endpoint=f"http://127.0.0.1:{port}")
            try:
                sess.page.goto(fixture.as_uri())
                res = sess.fill_many({"#a": "Ada", "#b": "a@x.io", "#c": "y", "#d": "hi"})
                self.assertTrue(res["success"], res)
                vals = sess.page.eval_on_selector_all(
                    "input, select, textarea", "els => els.map(e => e.value)"
                )
                self.assertEqual(vals, ["Ada", "a@x.io", "y", "hi"])
            finally:
                sess.close()
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except Exception:
                proc.kill()


if __name__ == "__main__":
    unittest.main()
