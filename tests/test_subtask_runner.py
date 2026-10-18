"""
Project Extra — Autonomous Subtask Runner Test Suite
Validates System 1 closed-loop execution and in-engine dynamic branching:
1. Intent pattern compilation (math calculations, quick notes, modal dismissal).
2. Safety Gate blocking destructive commands (format, rmdir, delete all).
3. Dynamic in-engine control flow (eval, assert, wait_until_settled, read_clipboard).
4. Live autonomous subtask execution (launch -> calculate -> copy result in 1 turn).
5. MCP Server extra_subtask_run tool integration.
"""

from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from extra.core.input_engine import execute_batch_actions
from extra.core.subtask import (
    SubtaskResult,
    SubtaskRunner,
    run_subtask,
)


def test_intent_compilation() -> None:
    print("[Test 1] Fast-path intent compilation patterns...", end=" ")
    runner = SubtaskRunner()

    # 1. Math calculation pattern
    calc_actions = runner.compile_intent("calculate 145 * 28 in calc")
    assert len(calc_actions) == 8, f"Expected 8 actions, got {len(calc_actions)}"
    assert calc_actions[0]["action"] == "launch"
    assert calc_actions[0]["app_name"] == "calc"
    assert calc_actions[3]["action"] == "hotkey"
    assert calc_actions[4]["action"] == "type"
    assert calc_actions[4]["text"] == "145*28="
    assert calc_actions[7]["action"] == "read_clipboard"

    # 2. Notepad note pattern
    note_actions = runner.compile_intent("open notepad and type Hello World")
    assert len(note_actions) == 4, f"Expected 4 actions, got {len(note_actions)}"
    assert note_actions[0]["action"] == "launch"
    assert note_actions[0]["app_name"] == "notepad"
    assert note_actions[3]["action"] == "type"
    assert note_actions[3]["text"] == "Hello World\n"

    # 3. Modal dismiss pattern
    dismiss_actions = runner.compile_intent("dismiss modal")
    assert len(dismiss_actions) == 1
    assert dismiss_actions[0]["action"] == "decide"
    assert "modal" in dismiss_actions[0]["condition"]
    assert dismiss_actions[0]["on_true"][0]["action"] == "hotkey"
    assert dismiss_actions[0]["on_true"][0]["keys"] == ["esc"]

    # 4. Window snapping patterns
    snap_actions = runner.compile_intent("snap calc and notepad side by side")
    assert len(snap_actions) == 2
    assert snap_actions[0]["action"] == "snap_layout"
    assert snap_actions[0]["layout"] == "side_by_side"
    assert snap_actions[0]["left_window"] == "calc"
    assert snap_actions[0]["right_window"] == "notepad"

    max_actions = runner.compile_intent("maximize notepad")
    assert len(max_actions) == 2
    assert max_actions[0]["action"] == "snap_layout"
    assert max_actions[0]["layout"] == "maximize"
    assert max_actions[0]["window"] == "notepad"

    center_actions = runner.compile_intent("center calc")
    assert len(center_actions) == 2
    assert center_actions[0]["action"] == "snap_layout"
    assert center_actions[0]["layout"] == "center"

    # 5. Browser URL navigation pattern
    nav_actions = runner.compile_intent("navigate to https://github.com")
    assert len(nav_actions) == 3
    assert nav_actions[0]["action"] == "launch"
    assert nav_actions[0]["app_name"] == "browser"
    assert nav_actions[0]["args"] == ["https://github.com"]

    # 6. Browser web search pattern
    search_actions = runner.compile_intent("search for AI news in browser")
    assert len(search_actions) == 3
    assert search_actions[0]["action"] == "launch"
    assert search_actions[0]["app_name"] == "browser"
    assert "google.com/search?q=AI+news" in search_actions[0]["args"][0]

    yt_actions = runner.compile_intent("search classical piano on youtube")
    assert len(yt_actions) == 3
    assert "youtube.com/results?search_query=classical+piano" in yt_actions[0]["args"][0]

    # 7. Select all and copy pattern
    copy_actions = runner.compile_intent("select all and copy from notepad")
    assert len(copy_actions) >= 5
    assert copy_actions[0]["action"] == "focus"
    assert copy_actions[0]["window_title"] == "notepad"
    assert any(a["action"] == "read_clipboard" for a in copy_actions)

    # 8. General app launch and input pattern (Shell apps must be blocked, non-shell apps allowed)
    blocked_shell_actions = runner.compile_intent("launch cmd and type dir")
    assert len(blocked_shell_actions) == 0, "Shell macros must be blocked for security"

    app_actions = runner.compile_intent("launch editor and type hello")
    assert len(app_actions) == 5
    assert app_actions[0]["action"] == "launch"
    assert app_actions[0]["app_name"] == "editor"
    assert app_actions[3]["action"] == "type"
    assert app_actions[3]["text"] == "hello\n"

    # 9. Focus window pattern
    focus_actions = runner.compile_intent("switch to Calculator")
    assert len(focus_actions) == 2
    assert focus_actions[0]["action"] == "focus"
    assert focus_actions[0]["window_title"] == "Calculator"

    # 10. Canvas reset and clearing pattern (with selection dismissal and brush re-selection)
    clear_actions = runner.compile_intent("clear canvas in paint")
    assert len(clear_actions) == 9
    assert clear_actions[0]["action"] == "focus"
    assert clear_actions[0]["window_title"] == "paint"
    assert clear_actions[1]["action"] == "click"
    assert clear_actions[1]["x"] == 500 and clear_actions[1]["y"] == 400
    assert clear_actions[2]["action"] == "hotkey" and clear_actions[2]["keys"] == ["ctrl", "a"]
    assert clear_actions[4]["action"] == "hotkey" and clear_actions[4]["keys"] == ["delete"]
    assert clear_actions[5]["action"] == "hotkey" and clear_actions[5]["keys"] == ["esc"]
    assert clear_actions[6]["action"] == "hotkey" and clear_actions[6]["keys"] == ["b"]
    assert clear_actions[7]["action"] == "click" and clear_actions[7]["x"] == 500 and clear_actions[7]["y"] == 400

    blank_actions = runner.compile_intent("start over with a blank canvas")
    assert len(blank_actions) == 8
    assert blank_actions[0]["action"] == "click"
    assert blank_actions[1]["action"] == "hotkey" and blank_actions[1]["keys"] == ["ctrl", "a"]
    assert blank_actions[3]["action"] == "hotkey" and blank_actions[3]["keys"] == ["delete"]
    assert blank_actions[4]["action"] == "hotkey" and blank_actions[4]["keys"] == ["esc"]
    assert blank_actions[5]["action"] == "hotkey" and blank_actions[5]["keys"] == ["b"]
    assert blank_actions[6]["action"] == "click" and blank_actions[6]["x"] == 500 and blank_actions[6]["y"] == 400

    print("PASSED")


def test_safety_gate_blocking() -> None:
    print("[Test 2] System 1 Safety Gate blocking destructive commands...", end=" ")
    runner = SubtaskRunner()

    res_format = runner.run_subtask(intent="format C: immediately")
    assert res_format.success is False
    assert res_format.steps_executed == 0
    assert "Destructive operation blocked" in str(res_format.error)

    res_rmdir = runner.run_subtask(intent="run rmdir /s on folder")
    assert res_rmdir.success is False
    assert "Destructive operation blocked" in str(res_rmdir.error)

    print("PASSED")


def test_dynamic_in_engine_branching() -> None:
    print("[Test 3] Dynamic in-engine eval, assert, and wait_until_settled...", end=" ")

    # Batch with eval condition and wait_until_settled
    actions = [
        {"action": "sleep", "ms": 20},
        {
            "action": "eval",
            "condition": "Is desktop active?",
            "context": {"window_title": "Desktop Explorer"},
            "if_true": [
                {"action": "sleep", "ms": 10},
            ],
            "if_false": [
                {"action": "sleep", "ms": 50},
            ],
        },
        {
            "action": "assert",
            "condition": "Is system running normally?",
            "context": {"status": "normal"},
            "on_fail": "continue",
        },
        {"action": "wait_until_settled", "timeout_sec": 0.5},
    ]

    res = execute_batch_actions(actions)
    assert res["success"] is True
    assert res["executed_count"] >= 3

    # Verify executed action logs
    executed_types = [step["action"] for step in res["executed"]]
    assert "eval" in executed_types
    assert "assert" in executed_types
    assert "wait_until_settled" in executed_types
    print("PASSED")


def test_live_autonomous_subtask() -> None:
    print("[Test 4] Live autonomous subtask execution (Calc 25*40= -> copy)...", end=" ")

    # Execute end-to-end math subtask
    res = run_subtask(intent="calculate 25 * 40 in calc")
    assert res.success is True
    assert res.steps_executed >= 4
    assert res.duration_ms < 6000.0  # Finished within timeout
    assert "STATE: SUBTASK_PASS" in res.final_state_token
    # Result value should be 1000 if clipboard captured
    if res.result_value:
        assert "1000" in res.result_value.replace(",", ""), f"Expected 1000, got '{res.result_value}'"

    print(f"PASSED (Executed {res.steps_executed} steps in {res.duration_ms:.2f}ms | Result: '{res.result_value}')")


def test_mcp_extra_subtask_run() -> None:
    print("[Test 5] MCP Server extra_subtask_run tool invocation...", end=" ")
    from extra.mcp.server import extra_subtask_run

    # Test running with explicit actions
    tool_res = extra_subtask_run(
        actions=[
            {"action": "sleep", "ms": 30},
            {"action": "wait_until_settled", "timeout_sec": 0.4},
        ]
    )
    assert tool_res["success"] is True
    assert tool_res["steps_executed"] == 2
    assert "final_state_token" in tool_res
    print(f"PASSED (MCP subtask finished in {tool_res['duration_ms']:.2f}ms)")


def test_closed_loop_batch_actions() -> None:
    print("[Test 6] Closed-Loop Batch Actions with active window, final settle, and auto-distill...", end=" ")
    from extra.core.input_engine import execute_batch_actions

    res = execute_batch_actions(
        actions=[
            {"action": "sleep", "ms": 20},
        ],
        auto_settle=True,
        auto_distill=True,
    )
    assert res["success"] is True
    assert res["executed_count"] == 1
    assert "final_settled" in res
    assert "active_window" in res
    assert "distilled_ui" in res
    assert "screen_state" in res
    print(f"PASSED (Batch observed active window '{res.get('active_window', {}).get('title', '')}', state tokens present)")


def test_soul_decider_and_critic_integration() -> None:
    print("[Test 7] SOUL-Decider dynamic branching & SOUL-Critic milestone verification...", end=" ")

    # 1. Test 'decide' reflex action branching
    res_decide = execute_batch_actions([
        {
            "action": "decide",
            "condition": "Is 'Recycle Bin' visible?",
            "context": {"text": "Desktop with Recycle Bin and Explorer active"},
            "on_true": [{"action": "sleep", "ms": 10}],
            "on_false": [{"action": "sleep", "ms": 100}],
        }
    ])
    assert res_decide["success"] is True
    decide_step = res_decide["executed"][0]
    assert decide_step["action"] == "decide"
    assert decide_step["branch"] == "on_true"

    # 2. Test 'critic' action passing when unwanted element is absent
    res_critic = execute_batch_actions([
        {
            "action": "critic",
            "milestone": "system_health_check",
            "unwanted": ["NonExistentCrashErrorXYZ9999"],
            "on_fail": "continue",
        }
    ])
    assert res_critic["success"] is True
    critic_step = res_critic["executed"][0]
    assert critic_step["action"] == "critic"
    assert "passed" in critic_step
    assert "latency_ms" in critic_step

    # 3. Test run_subtask with passing critic check
    res_subtask = run_subtask(
        actions=[{"action": "sleep", "ms": 10}],
        unwanted_elements=["NonExistentCrashModalXYZ9999"],
    )
    assert res_subtask.success is True
    assert res_subtask.critic_verdict is not None
    assert res_subtask.critic_verdict["passed"] is True
    assert "Critic: PASS" in res_subtask.final_state_token

    # 4. Test run_subtask with failing critic check on non-existent expected element
    res_subtask_fail = run_subtask(
        actions=[{"action": "sleep", "ms": 10}],
        expected_elements=["UltraSpecificNonExistentElementXYZ99999"],
    )
    assert res_subtask_fail.success is False
    assert res_subtask_fail.critic_verdict is not None
    assert res_subtask_fail.critic_verdict["passed"] is False
    assert len(res_subtask_fail.critic_verdict["defects"]) > 0
    assert "Critic: REJECT" in res_subtask_fail.final_state_token
    assert "SOUL-Critic rejected milestone" in str(res_subtask_fail.error)

    print("PASSED")


def test_macro_pipeline_execution() -> None:
    print("[Test 8] Universal Macro Intent Pipelines & Snap Execution...", end=" ")
    runner = SubtaskRunner()

    # 1. Test Snapping execution in batch
    res_snap = execute_batch_actions([
        {"action": "snap_layout", "layout": "side_by_side", "left_window": "Calculator", "right_window": "Notepad"},
        {"action": "sleep", "ms": 10},
    ])
    assert res_snap["success"] is True
    assert any(s["action"] == "snap_layout" for s in res_snap["executed"])

    # 2. Test Select All & Copy macro execution
    res_copy = runner.run_subtask(intent="select all and copy")
    assert res_copy.success is True
    assert res_copy.steps_executed >= 4
    assert any(s["action"] == "read_clipboard" for s in res_copy.executed_actions)

    print("PASSED")


class TestSubtaskRunner(unittest.TestCase):
    def test_01_intent_compilation(self):
        test_intent_compilation()

    def test_02_safety_gate_blocking(self):
        test_safety_gate_blocking()

    def test_03_dynamic_in_engine_branching(self):
        test_dynamic_in_engine_branching()

    def test_04_live_autonomous_subtask(self):
        test_live_autonomous_subtask()

    def test_05_mcp_extra_subtask_run(self):
        test_mcp_extra_subtask_run()

    def test_06_closed_loop_batch_actions(self):
        test_closed_loop_batch_actions()

    def test_07_soul_decider_and_critic_integration(self):
        test_soul_decider_and_critic_integration()

    def test_08_macro_pipeline_execution(self):
        test_macro_pipeline_execution()


def run_all() -> None:
    print("=" * 65)
    print("  EXTRA PHASE 2, 3 & 4: AUTONOMOUS SUBTASK ENGINE TEST SUITE")
    print("=" * 65)
    t0 = time.perf_counter()

    test_intent_compilation()
    test_safety_gate_blocking()
    test_dynamic_in_engine_branching()
    test_live_autonomous_subtask()
    test_mcp_extra_subtask_run()
    test_closed_loop_batch_actions()
    test_soul_decider_and_critic_integration()
    test_macro_pipeline_execution()

    elapsed = (time.perf_counter() - t0) * 1000.0
    print("=" * 65)
    print(f"  ALL 8 TESTS PASSED in {elapsed:.2f}ms")
    print("=" * 65)


if __name__ == "__main__":
    run_all()
