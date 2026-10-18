"""
Unit test suite for Project Extra First-Run Activation Ping and Privacy Telemetry.
Verifies one-time triggering, zero-PII payload integrity, DO_NOT_TRACK overrides,
and fail-open air-gapped resiliency.
"""

import json
import os
import pytest
from unittest.mock import patch, MagicMock

from extra.core.metrics.config import (
    CONFIG_PATH,
    EXTRA_HOME,
    load_config,
    save_config,
    is_first_run_pending,
    mark_first_run_complete,
    is_first_run_telemetry_allowed,
)
from extra.core.metrics.telemetry import (
    DEFAULT_TELEMETRY_ENDPOINT,
    TelemetryClient,
    emit_first_run_activation,
)


@pytest.fixture
def clean_config(tmp_path, monkeypatch):
    """Sets up an isolated configuration environment for each test."""
    fake_config = tmp_path / "config.json"
    fake_metrics = tmp_path / "metrics"
    monkeypatch.setattr("extra.core.metrics.config.CONFIG_PATH", fake_config)
    monkeypatch.setattr("extra.core.metrics.config.EXTRA_HOME", tmp_path)
    monkeypatch.setattr("extra.core.metrics.config.METRICS_DIR", fake_metrics)
    monkeypatch.delenv("DO_NOT_TRACK", raising=False)
    monkeypatch.delenv("EXTRA_TELEMETRY", raising=False)
    monkeypatch.delenv("EXTRA_TELEMETRY_ENDPOINT", raising=False)
    return fake_config


def test_first_run_pending_state(clean_config):
    """Verifies that a fresh installation starts with first_run_pending=True."""
    assert is_first_run_pending() is True
    mark_first_run_complete()
    assert is_first_run_pending() is False


def test_first_run_activation_triggers_once(clean_config):
    """Verifies that first-run activation fires once, posts valid payload, and never fires again."""
    sent_requests = []

    class MockResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    def mock_urlopen(req, timeout=2.0):
        sent_requests.append(req)
        return MockResponse()

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        # 1. First invocation must trigger and send request
        res1 = emit_first_run_activation(entrypoint="mcp_test", sync=True)
        assert res1 is True
        assert len(sent_requests) == 1

        req = sent_requests[0]
        data = json.loads(req.data.decode("utf-8"))
        assert "events" in data
        event = data["events"][0]
        assert event["event"] == "activation_first_run"
        assert event["entrypoint"] == "mcp_test"
        assert len(event["client_hash"]) == 64
        assert event["os"] in ("windows", "darwin", "linux")
        assert "extra_version" in event

        # 2. Config must now be marked as recorded
        assert is_first_run_pending() is False
        cfg = load_config()
        assert cfg.get("first_run_recorded") is True

        # 3. Second invocation must immediately return False and send NO requests
        res2 = emit_first_run_activation(entrypoint="mcp_test", sync=True)
        assert res2 is False
        assert len(sent_requests) == 1


def test_first_run_activation_do_not_track(clean_config, monkeypatch):
    """Verifies that DO_NOT_TRACK=1 strictly blocks network dispatch but marks first_run complete."""
    monkeypatch.setenv("DO_NOT_TRACK", "1")
    assert is_first_run_telemetry_allowed() is False

    with patch("urllib.request.urlopen") as mock_urlopen:
        res = emit_first_run_activation(entrypoint="cli_test", sync=True)
        assert res is False
        mock_urlopen.assert_not_called()

    # Must be marked recorded so it never retries or prompts
    assert is_first_run_pending() is False


def test_first_run_activation_extra_telemetry_disabled(clean_config, monkeypatch):
    """Verifies that EXTRA_TELEMETRY=0 strictly blocks network dispatch."""
    monkeypatch.setenv("EXTRA_TELEMETRY", "0")
    assert is_first_run_telemetry_allowed() is False

    with patch("urllib.request.urlopen") as mock_urlopen:
        res = emit_first_run_activation(entrypoint="cli_test", sync=True)
        assert res is False
        mock_urlopen.assert_not_called()

    assert is_first_run_pending() is False


def test_first_run_activation_offline_resiliency(clean_config):
    """Verifies that network failures fail silently without throwing exceptions."""
    def mock_urlopen_fail(req, timeout=2.0):
        raise OSError("Network is completely unreachable (air-gapped)")

    with patch("urllib.request.urlopen", side_effect=mock_urlopen_fail):
        # Even on network crash, emit_first_run_activation must not raise
        res = emit_first_run_activation(entrypoint="mcp_offline", sync=True)
        assert res is False

    # Still marks recorded so it does not loop on every startup in offline mode
    assert is_first_run_pending() is False


def test_telemetry_client_singleton():
    """Verifies TelemetryClient singleton and initialization."""
    client1 = TelemetryClient.get_instance()
    client2 = TelemetryClient.get_instance()
    assert client1 is client2
    assert "extra.yantraos.com" in client1.endpoint_url or "telemetry" in client1.endpoint_url


def test_mcp_server_main_triggers_first_run(clean_config):
    """Verifies that extra.mcp.server.main invokes emit_first_run_activation."""
    with patch("extra.mcp.server.server.run"), \
         patch("extra.mcp.server.ensure_dpi_aware"), \
         patch("extra.mcp.server.attach_input_desktop"), \
         patch("extra.mcp.server.ensure_startup_migration", return_value={"status": "noop"}), \
         patch("extra.core.metrics.telemetry.emit_first_run_activation") as mock_emit:
        from extra.mcp.server import main as mcp_main
        mcp_main()
        mock_emit.assert_called_once_with(entrypoint="mcp")


def test_cli_main_triggers_first_run(clean_config, monkeypatch):
    """Verifies that cli.main invokes emit_first_run_activation with command entrypoint."""
    monkeypatch.setattr("sys.argv", ["extra", "doctor"])
    with patch("extra.cli.cmd_doctor", return_value=0), \
         patch("extra.cli.check_first_run_consent"), \
         patch("extra.core.metrics.telemetry.emit_first_run_activation") as mock_emit, \
         pytest.raises(SystemExit) as exc_info:
        from extra.cli import main as cli_main
        cli_main()
    assert exc_info.value.code == 0
    mock_emit.assert_called_once_with(entrypoint="cli_doctor")

