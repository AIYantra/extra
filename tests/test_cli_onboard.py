"""
Automated unit tests for Extra universal interactive onboarding and client auto-wiring.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from extra.core.onboard import (
    ClientInfo,
    _check_json_mcp_config,
    _update_json_mcp_config,
    configure_all_clients,
    configure_client,
    detect_installed_clients,
    get_default_python_executable,
    run_sensory_handshake,
)


def test_get_default_python_executable():
    py = get_default_python_executable()
    assert py is not None
    assert len(py) > 0


def test_check_json_mcp_config(tmp_path: Path):
    config_file = tmp_path / "mcp.json"

    # Non-existent file
    exists, is_cfg = _check_json_mcp_config(config_file)
    assert not exists
    assert not is_cfg

    # File without extra
    config_file.write_text(json.dumps({"mcpServers": {"other": {"command": "test"}}}), encoding="utf-8")
    exists, is_cfg = _check_json_mcp_config(config_file)
    assert exists
    assert not is_cfg

    # File with extra
    config_file.write_text(
        json.dumps({"mcpServers": {"extra": {"command": "python", "args": ["-m", "extra.mcp.server"]}}}),
        encoding="utf-8",
    )
    exists, is_cfg = _check_json_mcp_config(config_file)
    assert exists
    assert is_cfg


def test_update_json_mcp_config(tmp_path: Path):
    config_file = tmp_path / "nested" / "mcp.json"
    python_exe = sys.executable

    # Creates file from scratch
    ok = _update_json_mcp_config(config_file, python_exe)
    assert ok
    assert config_file.exists()

    data = json.loads(config_file.read_text(encoding="utf-8"))
    assert "mcpServers" in data
    assert "extra" in data["mcpServers"]
    assert data["mcpServers"]["extra"]["command"] == python_exe
    assert data["mcpServers"]["extra"]["args"] == ["-m", "extra.mcp.server"]

    # Idempotent re-write preserves other servers
    data["mcpServers"]["other_server"] = {"command": "node"}
    config_file.write_text(json.dumps(data), encoding="utf-8")

    ok2 = _update_json_mcp_config(config_file, python_exe)
    assert ok2
    updated_data = json.loads(config_file.read_text(encoding="utf-8"))
    assert "other_server" in updated_data["mcpServers"]
    assert updated_data["mcpServers"]["extra"]["command"] == python_exe


def test_detect_installed_clients(tmp_path: Path):
    # Create mock user home
    mock_cursor = tmp_path / ".cursor" / "mcp.json"
    mock_cursor.parent.mkdir(parents=True, exist_ok=True)
    mock_cursor.write_text("{}", encoding="utf-8")

    clients = detect_installed_clients(user_home=tmp_path)
    cursor_client = next((c for c in clients if c.client_id == "cursor"), None)

    assert cursor_client is not None
    assert cursor_client.is_installed is True
    assert cursor_client.is_configured is False


def test_configure_client_and_all(tmp_path: Path):
    cursor_cfg = tmp_path / ".cursor" / "mcp.json"
    cursor_cfg.parent.mkdir(parents=True, exist_ok=True)
    cursor_cfg.write_text("{}", encoding="utf-8")

    client = ClientInfo(
        client_id="cursor",
        name="Cursor IDE",
        config_path=cursor_cfg,
        is_installed=True,
        is_configured=False,
    )

    ok = configure_client(client, python_exe=sys.executable)
    assert ok

    data = json.loads(cursor_cfg.read_text(encoding="utf-8"))
    assert "extra" in data.get("mcpServers", {})

    # Bulk configure
    results = configure_all_clients([client], python_exe=sys.executable)
    assert results["cursor"] is True


def test_run_sensory_handshake_skip():
    res = run_sensory_handshake(skip_handshake=True)
    assert res["status"] == "skipped"
    assert res["visual"] is False


def test_cli_onboard_command():
    from extra.cli import cmd_onboard
    import argparse

    args = argparse.Namespace(yes=True, skip_handshake=True)
    code = cmd_onboard(args)
    assert code == 0


def test_cli_station_command(monkeypatch):
    from extra.cli import cmd_station
    import argparse

    opened_urls = []
    monkeypatch.setattr("webbrowser.open", lambda u: opened_urls.append(u))

    args = argparse.Namespace(web=True, url="http://localhost:5173")
    code = cmd_station(args)
    assert code == 0
    assert "http://localhost:5173" in opened_urls
