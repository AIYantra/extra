"""
Project Extra Session Auditor.
Ingests real-world agent session transcripts (Antigravity, Claude Desktop, Cursor)
and computes exact ground-truth token consumption, turns, latency, and cost savings
across the latest frontier models (GPT-6 Astra, Claude Opus 5.5, Claude Sonnet 5.5, Gemini 4 Argon).
"""

import os
import sys
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

from extra.core.metrics.ledger import ImpactLedger, MODEL_PRICING, DEFAULT_MODEL_KEY, BASELINES

def parse_iso_time(ts_str: str) -> Optional[datetime]:
    """Parses standard ISO 8601 timestamps."""
    if not ts_str:
        return None
    ts_clean = ts_str.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(ts_clean)
    except Exception:
        return None

def find_transcript_file(path_str: str) -> Path:
    """Resolves a transcript path from a direct file path or directory."""
    path = Path(path_str).expanduser().resolve()
    if path.is_file():
        return path

    if path.is_dir():
        # Check standard locations in Antigravity or workspace logs
        candidates = [
            path / ".system_generated" / "logs" / "transcript_full.jsonl",
            path / ".system_generated" / "logs" / "transcript.jsonl",
            path / "transcript_full.jsonl",
            path / "transcript.jsonl",
        ]
        for c in candidates:
            if c.is_file():
                return c

        # Recursively search for any transcript_full.jsonl
        found = list(path.glob("**/transcript_full.jsonl"))
        if found:
            return found[0]
        found_compact = list(path.glob("**/transcript.jsonl"))
        if found_compact:
            return found_compact[0]

    raise FileNotFoundError(f"No transcript file found at or inside: {path_str}")

def audit_transcript(
    transcript_path: Path,
    model_key: str = DEFAULT_MODEL_KEY,
    record_to_ledger: bool = False
) -> Dict[str, Any]:
    """
    Parses a session transcript and calculates exact metrics and savings against empirical baselines.
    """
    steps: List[Dict[str, Any]] = []
    with open(transcript_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    steps.append(json.loads(line))
                except Exception:
                    continue

    if not steps:
        raise ValueError(f"Transcript at {transcript_path} contains no valid JSON steps.")

    first_time: Optional[datetime] = None
    last_time: Optional[datetime] = None
    model_turns = 0
    tool_calls_count: Dict[str, int] = {}
    extra_tools_count = 0
    shell_commands_count = 0
    scratch_files_count = 0

    exact_input_tokens = 0
    exact_cache_read_tokens = 0
    exact_output_tokens = 0

    prompt_summary = ""
    app_detected = "generic"

    for step in steps:
        st_time = parse_iso_time(step.get("created_at", ""))
        if st_time:
            if first_time is None or st_time < first_time:
                first_time = st_time
            if last_time is None or st_time > last_time:
                last_time = st_time

        st_type = step.get("type", "")
        st_source = step.get("source", "")
        content = step.get("content", "") or ""

        if st_type == "USER_INPUT" and not prompt_summary:
            prompt_summary = content[:120].strip()

        # Extract exact token metrics if recorded by host
        if "input_tokens" in step:
            exact_input_tokens += step.get("input_tokens", 0)
        if "cache_read_tokens" in step:
            exact_cache_read_tokens += step.get("cache_read_tokens", 0)
        if "output_tokens" in step:
            exact_output_tokens += step.get("output_tokens", 0)

        if st_source == "MODEL" and st_type == "PLANNER_RESPONSE":
            model_turns += 1

            for tc in step.get("tool_calls", []):
                t_name = tc.get("tool_name", "") or tc.get("name", "")
                tool_calls_count[t_name] = tool_calls_count.get(t_name, 0) + 1

                if t_name.startswith("extra_") or t_name.startswith("mcp_extra_"):
                    extra_tools_count += 1
                elif t_name in ("run_command", "bash", "execute_command"):
                    shell_commands_count += 1
                elif t_name in ("write_to_file", "create_file", "edit_file"):
                    scratch_files_count += 1

                # Detect target app from args
                args = tc.get("args") or tc.get("arguments") or {}
                if isinstance(args, dict):
                    app_arg = args.get("app") or args.get("app_name") or args.get("window_title")
                    if app_arg and isinstance(app_arg, str) and app_detected == "generic":
                        app_detected = app_arg.lower()

    # Determine duration
    if first_time and last_time:
        duration_sec = max(0.5, (last_time - first_time).total_seconds())
    else:
        duration_sec = 1.0

    is_extra_run = extra_tools_count > 0 or shell_commands_count == 0
    archetype = ImpactLedger.resolve_archetype(app=app_detected, intent=prompt_summary)
    base = BASELINES.get(archetype, BASELINES["generic_automation"])

    total_tokens = exact_input_tokens + exact_output_tokens

    # Calculate savings against baseline
    savings = ImpactLedger.calculate_savings(
        archetype=archetype,
        actual_duration_sec=duration_sec,
        actual_turns=model_turns,
        actual_prompt_tokens=exact_input_tokens,
        actual_completion_tokens=exact_output_tokens,
        model_key=model_key,
        screenshots_avoided=max(0, base["turns"] - model_turns)
    )

    result = {
        "transcript_file": str(transcript_path),
        "user_prompt_summary": prompt_summary,
        "is_extra_run": is_extra_run,
        "archetype": archetype,
        "app_detected": app_detected,
        "duration_sec": round(duration_sec, 2),
        "model_turns": model_turns,
        "tokens": {
            "input_tokens": exact_input_tokens,
            "cache_read_tokens": exact_cache_read_tokens,
            "output_tokens": exact_output_tokens,
            "total_tokens": total_tokens
        },
        "tool_breakdown": {
            "extra_tools": extra_tools_count,
            "shell_commands": shell_commands_count,
            "scratch_files": scratch_files_count,
            "all_tools": tool_calls_count
        },
        "savings": savings,
        "pricing_model_used": model_key
    }

    if record_to_ledger and is_extra_run:
        ImpactLedger.record_event(
            archetype=archetype,
            app=app_detected,
            duration_sec=duration_sec,
            turns=model_turns,
            actions_count=max(1, extra_tools_count),
            prompt_tokens=exact_input_tokens,
            completion_tokens=exact_output_tokens,
            success=True,
            model_key=model_key
        )
        result["recorded_to_ledger"] = True

    return result

def format_audit_receipt(audit: Dict[str, Any]) -> str:
    """Formats the audit analysis into a clean ASCII receipt card."""
    tok = audit["tokens"]
    sav = audit["savings"]
    tools = audit["tool_breakdown"]
    model_name = MODEL_PRICING.get(audit["pricing_model_used"], {}).get("name", audit["pricing_model_used"])

    dur_str = f"{audit['duration_sec']:.1f}s"
    if audit['duration_sec'] >= 60:
        dur_str = f"{int(audit['duration_sec'] // 60)}m {int(audit['duration_sec'] % 60)}s"

    inp_str = f"{tok['input_tokens']:,}"
    out_str = f"{tok['output_tokens']:,}"
    turns_str = str(audit['model_turns'])
    lat_str = f"+{sav['time_saved_sec']:.1f}s saved ({sav['speedup_multiplier']}× faster)"
    turns_saved_str = f"+{sav['turns_saved']} turns eliminated"
    tok_saved_str = f"+{sav['total_tokens_saved']:,} tokens preserved"
    tool_summary = f"{tools['extra_tools']} Extra actions | {tools['shell_commands']} Shell cmds | {tools['scratch_files']} Scratch files"

    lines = [
        "╔═════════════════════════════════════════════════════════════════════════════════╗",
        "║                     🔬 PROJECT EXTRA: SESSION AUDIT 🔬                          ║",
        "║                   Empirical Ground-Truth Verification Card                      ║",
        "╠═════════════════════════════════════════════════════════════════════════════════╣",
        f"║  Session Archetype:    {audit['archetype'].upper():<48} ║",
        f"║  Target Application:   {audit['app_detected'].title():<48} ║",
        f"║  Wall-Clock Duration:  {dur_str:<48} ║",
        f"║  Agent Model Turns:    {turns_str:<48} ║",
        f"║  Input Tokens (API):   {inp_str:<48} ║",
        f"║  Output Tokens (API):  {out_str:<48} ║",
        "╠═════════════════════════════════════════════════════════════════════════════════╣",
        "║  SAVINGS VS EMPIRICAL BASELINE (WITHOUT EXTRA):                                 ║",
        f"║  ⏱️  Wall-Clock Latency:  {lat_str:<47} ║",
        f"║  🔄  Model Turns Saved:   {turns_saved_str:<47} ║",
        f"║  🪙  Token Reduction:     {tok_saved_str:<47} ║",
        "╠═════════════════════════════════════════════════════════════════════════════════╣",
        f"║  FRONTIER MODEL COST SAVINGS MATRIX (Across 2026 Models):                       ║",
    ]

    c_by_m = sav.get("cost_by_model", {})
    showcase_models = [
        ("gpt-6-astra", "GPT-6 Astra ($10/$50)"),
        ("claude-opus-5-5", "Claude Opus 5.5 ($4/$20)"),
        ("claude-sonnet-5-5", "Claude Sonnet 5.5 ($2/$10)"),
        ("gemini-4-argon", "Gemini 4 Argon ($2/$10)"),
        ("deepseek-v3", "DeepSeek-V3 ($0.14/$0.28)"),
    ]

    for m_id, label in showcase_models:
        cost = c_by_m.get(m_id, 0.0)
        c_line = f"+${cost:.4f} USD"
        lines.append(f"║    • {label:<32}: {c_line:<30} ║")

    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    full_text = "\n".join(lines)
    try:
        encoding = getattr(sys.stdout, "encoding", "utf-8") or "utf-8"
        full_text.encode(encoding)
        return full_text
    except (UnicodeEncodeError, LookupError):
        ascii_lines = []
        for line in lines:
            l = line.replace("╔", "+").replace("╗", "+").replace("╚", "+").replace("╝", "+")
            l = l.replace("╠", "+").replace("╣", "+").replace("═", "-").replace("║", "|")
            l = l.replace("🔬", "").replace("⏱️", "").replace("🔄", "").replace("🪙", "").replace("•", "*").replace("×", "x")
            ascii_lines.append(l)
        return "\n".join(ascii_lines)
