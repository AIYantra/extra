"""
Unit and integration test suite for Project Extra Impact Ledger and Config Engine.
Verifies calculations, persistence, atomic file operations, and privacy defaults.
"""

import os
import json
import pytest
from pathlib import Path
from unittest.mock import patch

from extra.core.metrics.config import (
    load_config,
    save_config,
    is_telemetry_enabled,
    set_telemetry_enabled,
    get_anonymous_machine_id
)
from extra.core.metrics.ledger import ImpactLedger, BASELINES

def test_config_privacy_defaults(tmp_path, monkeypatch):
    """Verifies that telemetry defaults to False and respects privacy overrides."""
    fake_config = tmp_path / "config.json"
    monkeypatch.setattr("extra.core.metrics.config.CONFIG_PATH", fake_config)
    monkeypatch.setattr("extra.core.metrics.config.EXTRA_HOME", tmp_path)

    # 1. By default, telemetry is OFF
    assert is_telemetry_enabled() is False

    # 2. Enabling via set_telemetry_enabled
    set_telemetry_enabled(True)
    assert is_telemetry_enabled() is True

    # 3. DO_NOT_TRACK universal override strictly disables it
    monkeypatch.setenv("DO_NOT_TRACK", "1")
    assert is_telemetry_enabled() is False

    monkeypatch.delenv("DO_NOT_TRACK")
    assert is_telemetry_enabled() is True

    # 4. EXTRA_TELEMETRY=0 explicit override
    monkeypatch.setenv("EXTRA_TELEMETRY", "0")
    assert is_telemetry_enabled() is False

    # 5. EXTRA_TELEMETRY=1 explicit override
    monkeypatch.setenv("EXTRA_TELEMETRY", "1")
    assert is_telemetry_enabled() is True

def test_anonymous_machine_id_generation(tmp_path, monkeypatch):
    """Verifies that anonymous machine ID is a 64-char sha256 hex string."""
    fake_config = tmp_path / "config.json"
    monkeypatch.setattr("extra.core.metrics.config.CONFIG_PATH", fake_config)
    monkeypatch.setattr("extra.core.metrics.config.EXTRA_HOME", tmp_path)

    mach_id = get_anonymous_machine_id()
    assert len(mach_id) == 64
    assert all(c in "0123456789abcdef" for c in mach_id)

def test_ledger_archetype_resolution():
    """Verifies that common apps and intents map to correct empirical archetypes."""
    assert ImpactLedger.resolve_archetype(app="calc") == "math_calculation"
    assert ImpactLedger.resolve_archetype(intent="calculate 450 * 12=") == "math_calculation"
    assert ImpactLedger.resolve_archetype(tool_name="extra_snap_layout") == "window_snapping"
    assert ImpactLedger.resolve_archetype(app="notepad") == "document_creation"
    assert ImpactLedger.resolve_archetype(app="edge") == "web_research"
    assert ImpactLedger.resolve_archetype(app="mspaint") == "canvas_inking"
    assert ImpactLedger.resolve_archetype(app="unknown_tool_xyz") == "generic_automation"

def test_ledger_savings_calculation():
    """Verifies math calculation savings match empirical Batch 1 results."""
    # Run Calculator task in 14.0s (vs 296s baseline)
    savings = ImpactLedger.calculate_savings(
        archetype="math_calculation",
        actual_duration_sec=14.0,
        actual_turns=3,
        actual_prompt_tokens=66131,
        actual_completion_tokens=2500
    )

    assert savings["archetype"] == "math_calculation"
    assert savings["time_saved_sec"] == 282.0
    assert savings["speedup_multiplier"] >= 21.0
    assert savings["turns_saved"] == 48
    assert savings["prompt_tokens_saved"] == (516493 - 66131)
    assert savings["completion_tokens_saved"] == (24184 - 2500)
    assert savings["total_tokens_saved"] == (516493 - 66131) + (24184 - 2500)
    assert savings["estimated_cost_saved_usd"] > 0.05

def test_ledger_event_recording_and_persistence(tmp_path, monkeypatch):
    """Verifies atomic recording and summary updates in impact_ledger.json."""
    fake_ledger = tmp_path / "impact_ledger.json"
    fake_metrics = tmp_path
    monkeypatch.setattr("extra.core.metrics.ledger.get_ledger_path", lambda: fake_ledger)
    monkeypatch.setattr("extra.core.metrics.config.get_ledger_path", lambda: fake_ledger)

    # Record first event
    res1 = ImpactLedger.record_event(
        archetype="math_calculation",
        app="calc",
        duration_sec=14.0,
        turns=3,
        actions_count=2,
        prompt_tokens=66131,
        completion_tokens=2500,
        success=True
    )
    assert res1["time_saved_sec"] == 282.0

    # Record second event (Notepad)
    res2 = ImpactLedger.record_event(
        archetype="document_creation",
        app="notepad",
        duration_sec=8.0,
        turns=2,
        actions_count=3,
        prompt_tokens=25000,
        completion_tokens=1500,
        success=True
    )
    assert res2["time_saved_sec"] == 172.0

    summary = ImpactLedger.get_summary()
    assert summary["tasks_completed"] == 2
    assert summary["actions_dispatched"] == 5
    assert summary["wall_clock_time_saved_seconds"] == (282.0 + 172.0)
    assert summary["model_turns_saved"] == (48 + 26)
    assert "calc" in summary["top_apps"]
    assert "notepad" in summary["top_apps"]

    # Verify ASCII card formatting
    card = ImpactLedger.format_ascii_card()
    assert "PROJECT EXTRA: IMPACT SHIELD" in card
    assert "TIME SAVED" in card
    assert "TOKENS SAVED" in card

    # Verify receipt formatting
    receipt = ImpactLedger.get_impact_receipt(duration_sec=0.45, archetype="math_calculation")
    assert "speedup" in receipt
    assert "time_saved" in receipt
    assert "tokens_saved" in receipt

def test_sanitizer_path_masking():
    """Verifies that personal home paths and filenames are scrubbed."""
    from extra.core.metrics.sanitizer import ZeroPiiSanitizer
    home_dir = str(Path.home())
    test_path = os.path.join(home_dir, "Documents", "financial_records.pdf")
    sanitized = ZeroPiiSanitizer.sanitize_path(test_path)
    assert home_dir not in sanitized
    assert "<USERPROFILE>" in sanitized
    assert "financial_records" not in sanitized
    assert "*.pdf" in sanitized

def test_sanitizer_url_scrubbing():
    """Verifies that query parameters, auth tokens, and fragments are stripped from URLs."""
    from extra.core.metrics.sanitizer import ZeroPiiSanitizer
    dirty_url = "https://example.com/api/v1/auth?token=secret123&session=abc#details"
    clean_url = ZeroPiiSanitizer.sanitize_url(dirty_url)
    assert "secret123" not in clean_url
    assert "session" not in clean_url
    assert "#details" not in clean_url
    assert clean_url == "https://example.com/api/v1"

def test_sanitizer_text_redaction():
    """Verifies that API keys, emails, and IPv4 addresses are redacted."""
    from extra.core.metrics.sanitizer import ZeroPiiSanitizer
    dirty_text = "Contact user@secret.corp or 192.168.1.100 using sk-abcdef123456789012345678"
    clean_text = ZeroPiiSanitizer.sanitize_text(dirty_text)
    assert "user@secret.corp" not in clean_text
    assert "<REDACTED_EMAIL>" in clean_text
    assert "192.168.1.100" not in clean_text
    assert "<REDACTED_IP>" in clean_text
    assert "sk-abcdef123456789012345678" not in clean_text
    assert "<REDACTED_KEY>" in clean_text

def test_sanitizer_build_telemetry_event():
    """Verifies that telemetry payload schema contains only anonymous metrics."""
    from extra.core.metrics.sanitizer import ZeroPiiSanitizer
    event = ZeroPiiSanitizer.build_telemetry_event(
        client_hash="abc123hash",
        app="calc",
        archetype="math_calculation",
        tool_name="extra_subtask_run",
        compilation_latency_ms=0.007,
        execution_duration_ms=450.2,
        settle_latency_ms=14.5,
        actions_count=8,
        success=True,
        speedup=21.1
    )
    assert event["client_hash"] == "abc123hash"
    assert "platform" in event
    assert event["execution_metrics"]["app_name"] == "calc"
    assert event["execution_metrics"]["archetype"] == "math_calculation"
    assert event["execution_metrics"]["speedup_multiplier"] == 21.1
    assert "prompt" not in event
    assert "screenshot" not in event

def test_telemetry_client_disabled_by_default(monkeypatch):
    """Verifies that TelemetryClient emits nothing when telemetry is disabled."""
    from extra.core.metrics.telemetry import TelemetryClient
    monkeypatch.setenv("DO_NOT_TRACK", "1")

    client = TelemetryClient()
    emitted = client.emit_event(
        app="calc",
        archetype="math_calculation",
        tool_name="extra_subtask_run"
    )
    assert emitted is False
    assert len(client.queue) == 0

def test_telemetry_client_queuing_when_enabled(monkeypatch):
    """Verifies that TelemetryClient queues sanitized event when telemetry is enabled."""
    from extra.core.metrics.telemetry import TelemetryClient
    monkeypatch.delenv("DO_NOT_TRACK", raising=False)
    monkeypatch.setenv("EXTRA_TELEMETRY", "1")

    client = TelemetryClient()
    emitted = client.emit_event(
        app="calc",
        archetype="math_calculation",
        tool_name="extra_subtask_run",
        speedup=21.1
    )
    assert emitted is True
    # Event should be queued or flushed
    assert isinstance(client.queue, list)

def test_dashboard_generation(tmp_path):
    """Verifies that the HTML impact dashboard generates clean HTML."""
    from extra.core.metrics.dashboard import generate_html_dashboard
    target_file = tmp_path / "dashboard.html"
    generated_path = generate_html_dashboard(target_path=target_file)
    assert generated_path.is_file()
    content = generated_path.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content
    assert "Extra Impact Shield" in content
    assert "Cumulative Time Saved" in content
    assert "Token Context Saved" in content

def test_cli_stats_command(capsys):
    """Verifies that cmd_stats prints ASCII or JSON metrics."""
    from extra.cli import cmd_stats
    import argparse
    # Test text card
    exit_code = cmd_stats(argparse.Namespace(json=False))
    assert exit_code == 0
    captured = capsys.readouterr().out
    assert "PROJECT EXTRA: IMPACT SHIELD" in captured

    # Test JSON mode
    exit_code_json = cmd_stats(argparse.Namespace(json=True))
    assert exit_code_json == 0
    captured_json = capsys.readouterr().out
    data = json.loads(captured_json)
    assert "tasks_completed" in data

def test_cli_telemetry_commands(capsys, monkeypatch, tmp_path):
    """Verifies that cmd_telemetry manages on/off/status correctly."""
    from extra.cli import cmd_telemetry
    import argparse
    fake_config = tmp_path / "config.json"
    monkeypatch.setattr("extra.core.metrics.config.CONFIG_PATH", fake_config)

    # 1. Status
    res_status = cmd_telemetry(argparse.Namespace(action="status"))
    assert res_status == 0
    out_status = capsys.readouterr().out
    assert "PRIVACY & TELEMETRY STATUS" in out_status

    # 2. Toggle On
    res_on = cmd_telemetry(argparse.Namespace(action="on"))
    assert res_on == 0
    out_on = capsys.readouterr().out
    assert "Community telemetry ENABLED" in out_on

    # 3. Toggle Off
    res_off = cmd_telemetry(argparse.Namespace(action="off"))
    assert res_off == 0
    out_off = capsys.readouterr().out
    assert "Telemetry DISABLED" in out_off

def test_mcp_extra_stats_tool():
    """Verifies that the extra_stats MCP tool returns valid summary and ASCII HUD."""
    from extra.mcp.server import extra_stats
    res = extra_stats()
    assert "lifetime_summary" in res
    assert "ascii_hud" in res
    assert "tasks_completed" in res["lifetime_summary"]
    assert "PROJECT EXTRA: IMPACT SHIELD" in res["ascii_hud"]

def test_mcp_task_complete_receipt(tmp_path, monkeypatch):
    """Verifies that extra_task_complete attaches an impact_receipt to its response."""
    from extra.mcp.server import extra_task_complete
    fake_ledger = tmp_path / "impact_ledger.json"
    monkeypatch.setattr("extra.core.metrics.ledger.get_ledger_path", lambda: fake_ledger)
    monkeypatch.setattr("extra.core.metrics.config.get_ledger_path", lambda: fake_ledger)

    res = extra_task_complete(
        summary="Calculated compound formula in Calculator",
        success=True,
        play_chime=False,
        auto_screenshot=False
    )
    assert res["success"] is True
    assert "impact_receipt" in res
    receipt = res["impact_receipt"]
    assert "speedup" in receipt
    assert "time_saved" in receipt
    assert "tokens_saved" in receipt

def test_model_pricing_matrix():
    """Verifies that 2026 frontier models are configured with correct relative pricing."""
    from extra.core.metrics.ledger import MODEL_PRICING, ImpactLedger

    assert "gpt-6-astra" in MODEL_PRICING
    assert "claude-opus-5-5" in MODEL_PRICING
    assert "claude-sonnet-5-5" in MODEL_PRICING
    assert "gemini-4-argon" in MODEL_PRICING

    # GPT-6 Astra is frontier high tier ($10/$50)
    assert MODEL_PRICING["gpt-6-astra"]["prompt_per_m"] == 10.00
    assert MODEL_PRICING["gpt-6-astra"]["completion_per_m"] == 50.00

    # Claude Opus 5.5 ($4/$20)
    assert MODEL_PRICING["claude-opus-5-5"]["prompt_per_m"] == 4.00
    assert MODEL_PRICING["claude-opus-5-5"]["completion_per_m"] == 20.00

    # Verify dynamic cost calculation
    cost_astra = ImpactLedger.calculate_cost_for_model(1_000_000, 100_000, "gpt-6-astra")
    assert cost_astra == round(10.00 + 5.00, 5)

    cost_sonnet = ImpactLedger.calculate_cost_for_model(1_000_000, 100_000, "claude-sonnet-5-5")
    assert cost_sonnet == round(2.00 + 1.00, 5)

def test_compounding_context_calculation():
    """Verifies that quadratic compounding context grows super-linearly with turn count."""
    from extra.core.metrics.ledger import ImpactLedger

    # 1 turn: 10,000 tokens
    c1 = ImpactLedger.calculate_compounding_context(1, base_system_tokens=10000, avg_turn_delta=2000)
    assert c1 == 10000

    # 10 turns: 10*10k + (10*9/2)*2k = 100k + 90k = 190,000
    c10 = ImpactLedger.calculate_compounding_context(10, base_system_tokens=10000, avg_turn_delta=2000)
    assert c10 == 190000

    # 50 turns: 50*10k + (50*49/2)*2k = 500k + 2.45M = 2,950,000 tokens
    c50 = ImpactLedger.calculate_compounding_context(50, base_system_tokens=10000, avg_turn_delta=2000)
    assert c50 == 2950000

    # Compounding factor for 50 turns vs 10 turns is much greater than 5x
    assert (c50 / c10) > 15.0

def test_auditor_transcript_parsing(tmp_path):
    """Verifies that auditor correctly extracts ground-truth metrics from session JSONL."""
    from extra.core.metrics.auditor import audit_transcript, format_audit_receipt

    fake_transcript = tmp_path / "transcript_full.jsonl"
    lines = [
        json.dumps({
            "step_index": 1,
            "source": "USER_EXPLICIT",
            "type": "USER_INPUT",
            "created_at": "2026-10-04T12:00:00Z",
            "content": "Calculate 450 * 12 in Windows Calculator"
        }),
        json.dumps({
            "step_index": 2,
            "source": "MODEL",
            "type": "PLANNER_RESPONSE",
            "created_at": "2026-10-04T12:00:05Z",
            "input_tokens": 15000,
            "output_tokens": 800,
            "tool_calls": [{"tool_name": "extra_subtask_run", "args": {"intent": "calculate 450 * 12="}}]
        }),
        json.dumps({
            "step_index": 3,
            "source": "SYSTEM",
            "type": "TOOL_RESPONSE",
            "created_at": "2026-10-04T12:00:10Z",
            "content": "Result is 5400"
        })
    ]
    fake_transcript.write_text("\n".join(lines), encoding="utf-8")

    audit = audit_transcript(fake_transcript, model_key="gpt-6-astra")
    assert audit["archetype"] == "math_calculation"
    assert audit["model_turns"] == 1
    assert audit["tokens"]["input_tokens"] == 15000
    assert audit["tokens"]["output_tokens"] == 800
    assert audit["tool_breakdown"]["extra_tools"] == 1
    assert audit["is_extra_run"] is True

    receipt_text = format_audit_receipt(audit)
    assert "PROJECT EXTRA: SESSION AUDIT" in receipt_text
    assert "GPT-6 Astra" in receipt_text

def test_cli_audit_command(tmp_path, capsys):
    """Verifies CLI extra audit command outputs receipt card."""
    from extra.cli import cmd_audit
    import argparse

    fake_transcript = tmp_path / "transcript_full.jsonl"
    fake_transcript.write_text(json.dumps({
        "source": "MODEL",
        "type": "PLANNER_RESPONSE",
        "created_at": "2026-10-04T12:00:00Z",
        "input_tokens": 5000,
        "output_tokens": 200,
        "tool_calls": [{"tool_name": "extra_type", "args": {"text": "hello"}}]
    }), encoding="utf-8")

    res = cmd_audit(argparse.Namespace(
        path=str(fake_transcript),
        model="claude-opus-5-5",
        record=False,
        json=False
    ))
    assert res == 0
    captured = capsys.readouterr().out
    assert "PROJECT EXTRA: SESSION AUDIT" in captured
    assert "Claude Opus 5.5" in captured




