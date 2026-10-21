"""
Project Extra — Autonomous Subtask Engine
Executes compound desktop micro-routines locally in closed loops without roundtripping
to the host LLM for each individual click and keystroke.
Provides fast-path intent compilation, closed-loop settle verification, and semantic state folding.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import re
import time
import urllib.parse
from typing import Any, Dict, List, Optional

from extra.core.focus import get_foreground_window
from extra.core.input_engine import execute_batch_actions
from extra.core.soul.compressor import compress_milestone_state

logger = logging.getLogger("Extra-SubtaskRunner")

# Prohibited destructive keywords requiring explicit manual user authorization
DESTRUCTIVE_KEYWORDS = {
    "format c:",
    "rmdir /s",
    "del /f /s /q",
    "drop database",
    "delete all",
    "erase disk",
    "clean all",
}


@dataclass
class SubtaskResult:
    """Structured result of an autonomous local micro-subtask."""
    success: bool
    intent: str
    steps_executed: int
    duration_ms: float
    result_value: Optional[str] = None
    final_state_token: str = ""
    active_window: str = ""
    distilled_ui: Optional[str] = None
    executed_actions: List[Dict[str, Any]] = field(default_factory=list)
    critic_verdict: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serializes result for MCP response dispatch."""
        res: Dict[str, Any] = {
            "success": self.success,
            "intent": self.intent,
            "steps_executed": self.steps_executed,
            "duration_ms": round(self.duration_ms, 2),
            "result_value": self.result_value,
            "final_state_token": self.final_state_token,
            "active_window": self.active_window,
            "executed_actions": self.executed_actions,
            "error": self.error,
        }
        if self.distilled_ui:
            res["distilled_ui"] = self.distilled_ui
        if self.critic_verdict:
            res["critic_verdict"] = self.critic_verdict
        return res


class SubtaskRunner:
    """
    Autonomous System 1 execution engine for compound desktop actions.
    Compiles high-level micro-goals into optimized batch action pipelines.
    """

    def compile_intent(self, intent: str) -> List[Dict[str, Any]]:
        """
        Synthesizes standard desktop micro-patterns into verified action pipelines.
        Returns a list of batch actions if recognized, or empty list if custom.
        """
        clean_intent = intent.strip()

        # 1. Modal / Popup Dismissal Pattern:
        # e.g. "dismiss modal", "close popup", "cancel dialog"
        if any(w in clean_intent.lower() for w in ("dismiss modal", "close popup", "cancel dialog", "close dialog", "dismiss prompt")):
            return [
                {
                    "action": "decide",
                    "condition": "is modal or dialog visible",
                    "on_true": [
                        {"action": "hotkey", "keys": ["esc"]},
                        {"action": "wait_until_settled", "timeout_sec": 0.8},
                    ],
                }
            ]

        # 2. Calculator Computation Pattern:
        # e.g. "calculate 145 * 28", "compute 250+80 in calc", "calc 500/20", "245.12 / 383.29="
        calc_match = re.search(
            r"(?:calculate|compute|calc|math)\s+([0-9\.\+\-\*\/\^\(\)\s]+)", clean_intent, flags=re.IGNORECASE
        ) or (re.match(r"^[0-9\.\+\-\*\/\^\(\)\s]+=$", clean_intent) and re.search(r"([0-9\.\+\-\*\/\^\(\)\s]+)", clean_intent))
        if calc_match:
            formula = calc_match.group(1).strip()
            # Clean formula characters
            formula = re.sub(r"[^\d\+\-\*\/\.\(\)]", "", formula)
            if formula:
                if not formula.endswith("="):
                    formula += "="
                return [
                    {"action": "launch", "app_name": "calc"},
                    {"action": "focus", "window_title": "Calculator"},
                    {"action": "wait_until_settled", "timeout_sec": 1.5},
                    {"action": "hotkey", "keys": ["esc"]},
                    {"action": "type", "text": formula},
                    {"action": "sleep", "ms": 250},
                    {"action": "hotkey", "keys": ["ctrl", "c"]},
                    {"action": "read_clipboard"},
                ]

        # 3. Window Layout Setup & Snapping Patterns:
        # e.g. "snap calc and notepad side by side", "snap calc to left and notepad to right"
        side_by_side_match = re.search(
            r"(?:snap|split|arrange|dock)\s+([a-zA-Z0-9_\-\.]+)\s+(?:to\s+left\s+and\s+|and\s+)([a-zA-Z0-9_\-\.]+)(?:\s+(?:to\s+right|side\s*by\s*side|split|horizontally))?",
            clean_intent,
            flags=re.IGNORECASE,
        ) or re.search(
            r"(?:side\s*by\s*side|split\s*screen)\s+([a-zA-Z0-9_\-\.]+)\s+and\s+([a-zA-Z0-9_\-\.]+)",
            clean_intent,
            flags=re.IGNORECASE,
        )
        if side_by_side_match:
            app1 = side_by_side_match.group(1).strip()
            app2 = side_by_side_match.group(2).strip()
            return [
                {"action": "snap_layout", "layout": "side_by_side", "left_window": app1, "right_window": app2},
                {"action": "wait_until_settled", "timeout_sec": 0.5},
            ]

        maximize_match = re.search(
            r"(?:maximize|fullscreen)\s+([a-zA-Z0-9_\-\.]+)", clean_intent, flags=re.IGNORECASE
        ) or re.search(
            r"snap\s+([a-zA-Z0-9_\-\.]+)\s+(?:to\s+)?maximize", clean_intent, flags=re.IGNORECASE
        )
        if maximize_match:
            app = maximize_match.group(1).strip()
            return [
                {"action": "snap_layout", "layout": "maximize", "window": app},
                {"action": "wait_until_settled", "timeout_sec": 0.5},
            ]

        center_match = re.search(
            r"(?:center|center\s+window)\s+([a-zA-Z0-9_\-\.]+)", clean_intent, flags=re.IGNORECASE
        )
        if center_match:
            app = center_match.group(1).strip()
            return [
                {"action": "snap_layout", "layout": "center", "window": app},
                {"action": "wait_until_settled", "timeout_sec": 0.5},
            ]

        # 4. Select All & Copy / Clipboard Extraction Pattern:
        # e.g. "select all and copy from notepad", "copy all text", "copy all"
        copy_all_match = re.search(
            r"(?:copy\s+all\s+text|select\s+all\s+and\s+copy|copy\s+all)(?:\s+from\s+([a-zA-Z0-9_\-\.]+))?",
            clean_intent,
            flags=re.IGNORECASE,
        )
        if copy_all_match:
            target_app = copy_all_match.group(1)
            actions = []
            if target_app:
                actions.extend([
                    {"action": "focus", "window_title": target_app.strip()},
                    {"action": "wait_until_settled", "timeout_sec": 0.5},
                ])
            actions.extend([
                {"action": "hotkey", "keys": ["ctrl", "a"]},
                {"action": "sleep", "ms": 50},
                {"action": "hotkey", "keys": ["ctrl", "c"]},
                {"action": "read_clipboard"},
            ])
            return actions

        # 5. Browser Navigation & Web Search Patterns:
        # Case A: Direct URL Navigation: e.g. "navigate to https://github.com", "open www.python.org in browser"
        url_match = re.search(
            r"(?:navigate|browse|go|open)\s+(?:to\s+)?(https?:\/\/[^\s]+|www\.[^\s]+|[a-zA-Z0-9\.\-]+\.(?:com|org|net|io|ai|gov|edu|dev)(?:\/[^\s]*)?)(?:\s+in\s+browser)?",
            clean_intent,
            flags=re.IGNORECASE,
        )
        if url_match:
            target_url = url_match.group(1).strip()
            if not target_url.startswith(("http://", "https://")):
                target_url = "https://" + target_url
            return [
                {"action": "launch", "app_name": "browser", "args": [target_url]},
                {"action": "focus", "window_title": "browser"},
                {"action": "wait_until_settled", "timeout_sec": 2.0},
            ]

        # Case B: Web Search: e.g. "search for AI news in browser", "search AI news on youtube"
        search_match = re.search(
            r"(?:search|query|lookup|google)\s+(?:for\s+)?['\"]?([^'\"].+?)['\"]?\s+(?:on|in)\s+(?:the\s+web|browser|google|bing|youtube|duckduckgo)",
            clean_intent,
            flags=re.IGNORECASE,
        ) or re.search(
            r"(?:search|query|lookup)\s+(?:the\s+web|browser|google|youtube|bing|duckduckgo)\s+for\s+['\"]?([^'\"]+)['\"]?",
            clean_intent,
            flags=re.IGNORECASE,
        )
        if search_match:
            search_term = search_match.group(1).strip()
            encoded = urllib.parse.quote_plus(search_term)
            lower_intent = clean_intent.lower()
            if "youtube" in lower_intent:
                s_url = f"https://www.youtube.com/results?search_query={encoded}"
            elif "bing" in lower_intent:
                s_url = f"https://www.bing.com/search?q={encoded}"
            elif "duckduckgo" in lower_intent:
                s_url = f"https://duckduckgo.com/?q={encoded}"
            else:
                s_url = f"https://www.google.com/search?q={encoded}"
            return [
                {"action": "launch", "app_name": "browser", "args": [s_url]},
                {"action": "focus", "window_title": "browser"},
                {"action": "wait_until_settled", "timeout_sec": 2.0},
            ]

        # 6. Quick Note in Notepad Pattern (Kept for backwards compatibility):
        note_match = re.search(
            r"(?:open|launch)\s+notepad\s+(?:and\s+)?(?:type|write)\s+(.+)", clean_intent, flags=re.IGNORECASE
        )
        if note_match:
            text = note_match.group(1).strip()
            return [
                {"action": "launch", "app_name": "notepad"},
                {"action": "focus", "window_title": "Notepad"},
                {"action": "wait_until_settled", "timeout_sec": 1.5},
                {"action": "type", "text": text + "\n"},
            ]

        # 7. General App Launch & Direct Input / Run Pattern:
        # e.g. "open notepad and type hello", "launch texteditor and write notes"
        app_type_match = re.search(
            r"(?:open|launch)\s+([a-zA-Z0-9_\-\.]+)\s+(?:and\s+)?(?:type|write|input|enter|run)\s+(.+)",
            clean_intent,
            flags=re.IGNORECASE,
        )
        if app_type_match:
            app_name = app_type_match.group(1).strip()
            # Security Gating: Block shell executables from natural language GUI typing macros
            # Programmatic terminal execution must be routed through Plane 2 (extra_execute_bridge) for safety.
            SHELL_APPS = {
                "cmd", "cmd.exe", "powershell", "powershell.exe", "pwsh", "pwsh.exe",
                "terminal", "wt", "wt.exe", "bash", "bash.exe", "zsh", "sh", "wsl", "wsl.exe"
            }
            if app_name.lower() in SHELL_APPS:
                logger.warning(
                    "[Subtask] Blocked shell application '%s' from natural language GUI typing macro. Use extra_execute_bridge instead.",
                    app_name
                )
                return []

            text_to_type = app_type_match.group(2).strip()
            if not text_to_type.endswith("\n"):
                text_to_type += "\n"
            return [
                {"action": "launch", "app_name": app_name},
                {"action": "focus", "window_title": app_name},
                {"action": "wait_until_settled", "timeout_sec": 1.5},
                {"action": "type", "text": text_to_type},
                {"action": "wait_until_settled", "timeout_sec": 0.5},
            ]

        # 8. Focus / Switch Window Pattern:
        # e.g. "focus notepad", "switch to Calculator", "bring chrome to front"
        focus_match = re.search(
            r"(?:focus|switch\s+to|bring\s+to\s+front)\s+([a-zA-Z0-9_\-\.\s]+)",
            clean_intent,
            flags=re.IGNORECASE,
        )
        if focus_match:
            target_win = focus_match.group(1).strip()
            return [
                {"action": "focus", "window_title": target_win},
                {"action": "wait_until_settled", "timeout_sec": 0.8},
            ]

        # 9. Canvas Reset & Viewport Clearing Pattern:
        # e.g. "clear canvas", "reset canvas in paint", "blank canvas in mspaint", "clear canvas in photoshop"
        canvas_clear_match = re.search(
            r"(?:clear|reset|blank)\s+(?:the\s+)?canvas(?:\s+(?:in|on|for)\s+([a-zA-Z0-9_\-\.]+))?",
            clean_intent,
            flags=re.IGNORECASE,
        ) or re.search(
            r"(?:start\s+over\s+with\s+(?:a\s+)?blank\s+canvas|new\s+canvas)(?:\s+(?:in|on|for)\s+([a-zA-Z0-9_\-\.]+))?",
            clean_intent,
            flags=re.IGNORECASE,
        )
        if canvas_clear_match:
            app_target = canvas_clear_match.group(1)
            actions: List[Dict[str, Any]] = []
            if app_target:
                actions.append({"action": "focus", "window_title": app_target.strip()})
            # Canvas viewport focus click (bypasses Ribbon / Titlebar keyboard capture)
            actions.append({"action": "click", "x": 500, "y": 400})
            actions.append({"action": "hotkey", "keys": ["ctrl", "a"]})
            actions.append({"action": "sleep", "ms": 50})
            actions.append({"action": "hotkey", "keys": ["delete"]})
            actions.append({"action": "hotkey", "keys": ["esc"]})  # Dismiss marquee selection box
            actions.append({"action": "hotkey", "keys": ["b"]})    # Re-select Brush tool
            actions.append({"action": "click", "x": 500, "y": 400}) # Re-focus drawing canvas
            actions.append({"action": "wait_until_settled", "timeout_sec": 0.5})
            return actions

        return []

    def run_subtask(
        self,
        intent: Optional[str] = None,
        actions: Optional[List[Dict[str, Any]]] = None,
        expected_elements: Optional[List[str]] = None,
        unwanted_elements: Optional[List[str]] = None,
        timeout_sec: float = 8.0,
    ) -> SubtaskResult:
        """
        Executes an autonomous micro-subtask pipeline.
        
        Args:
            intent: High-level micro-goal description.
            actions: Optional explicit batch actions list.
            expected_elements: Optional elements that must be visible on screen post-execution.
            unwanted_elements: Optional elements that must NOT be visible on screen post-execution.
            timeout_sec: Safety timeout.
        """
        t0 = time.perf_counter()
        goal_desc = intent or "custom_micro_plan"

        # 1. Safety Guard against Destructive Commands
        for d_key in DESTRUCTIVE_KEYWORDS:
            if d_key in goal_desc.lower():
                duration_ms = (time.perf_counter() - t0) * 1000.0
                return SubtaskResult(
                    success=False,
                    intent=goal_desc,
                    steps_executed=0,
                    duration_ms=duration_ms,
                    error=f"Destructive operation blocked by System 1 Safety Gate: '{d_key}'. Manual user confirmation required.",
                )

        # 2. Determine Action Pipeline
        final_actions = actions
        if not final_actions and intent:
            final_actions = self.compile_intent(intent)

        if not final_actions:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            return SubtaskResult(
                success=False,
                intent=goal_desc,
                steps_executed=0,
                duration_ms=duration_ms,
                error=f"Could not compile intent '{intent}' into autonomous actions, and no explicit actions list was provided.",
            )

        # 3. Execute Closed-Loop Batch Actions
        batch_res = execute_batch_actions(final_actions, auto_distill=True)
        duration_ms = (time.perf_counter() - t0) * 1000.0
        success = bool(batch_res.get("success", False))

        # 4. Extract Output Result Value
        result_value = None
        executed_steps = batch_res.get("executed", batch_res.get("actions", []))

        # Check if any step captured clipboard or result
        for step in executed_steps:
            if step.get("action") in ("read_clipboard", "copy") and "value" in step:
                result_value = str(step["value"]).strip()
                break
        if not result_value and "clipboard" in batch_res:
            result_value = str(batch_res["clipboard"]).strip()

        # 5. Extract Active Window Context & Screen State
        active_title = ""
        if "active_window" in batch_res and isinstance(batch_res["active_window"], dict):
            active_title = batch_res["active_window"].get("title", "")
        if not active_title:
            try:
                fg = get_foreground_window()
                if fg:
                    active_title = fg.title
            except Exception:
                pass

        distilled_ui = batch_res.get("distilled_ui")

        # 6. Post-Execution SOUL-Critic Verification Gate
        critic_verdict_dict = None
        if success and (expected_elements or unwanted_elements):
            try:
                from extra.core.soul import SoulCritic
                critic = SoulCritic()
                exp_list = expected_elements if isinstance(expected_elements, list) else ([expected_elements] if expected_elements else None)
                unw_list = unwanted_elements if isinstance(unwanted_elements, list) else ([unwanted_elements] if unwanted_elements else None)
                verdict = critic.evaluate_screen_milestone(
                    milestone_name=goal_desc,
                    expected_elements=exp_list,
                    unwanted_elements=unw_list,
                )
                critic_verdict_dict = {
                    "passed": verdict.passed,
                    "confidence": round(verdict.confidence, 2),
                    "defects": verdict.defects,
                    "latency_ms": round(verdict.latency_ms, 2),
                }
                if not verdict.passed:
                    success = False
                    critic_err = f"SOUL-Critic rejected milestone '{goal_desc}': {'; '.join(verdict.defects)}"
                    curr_err = batch_res.get("error")
                    batch_error_str = f"{curr_err}; {critic_err}" if curr_err else critic_err
                else:
                    batch_error_str = batch_res.get("error")
            except Exception as e:
                logger.warning("SOUL-Critic evaluation error: %s", e)
                batch_error_str = batch_res.get("error")
        else:
            batch_error_str = batch_res.get("error")

        # 7. Generate Compact Semantic State Token
        status_tag = "PASS" if success else "FAIL"
        val_str = f" | Value: {result_value}" if result_value else ""
        critic_tag = " | Critic: PASS" if (critic_verdict_dict and critic_verdict_dict.get("passed")) else (" | Critic: REJECT" if critic_verdict_dict else "")
        state_token = f"[STATE: SUBTASK_{status_tag}{critic_tag} | Intent: '{goal_desc[:30]}' | Steps: {len(executed_steps)}{val_str} | Latency: {int(duration_ms)}ms]"

        return SubtaskResult(
            success=success,
            intent=goal_desc,
            steps_executed=len(executed_steps),
            duration_ms=duration_ms,
            result_value=result_value,
            final_state_token=state_token,
            active_window=active_title,
            distilled_ui=distilled_ui,
            executed_actions=executed_steps,
            critic_verdict=critic_verdict_dict,
            error=batch_error_str,
        )


_default_runner = SubtaskRunner()


def run_subtask(
    intent: Optional[str] = None,
    actions: Optional[List[Dict[str, Any]]] = None,
    expected_elements: Optional[List[str]] = None,
    unwanted_elements: Optional[List[str]] = None,
    timeout_sec: float = 8.0,
) -> SubtaskResult:
    """Convenience top-level function for autonomous subtask execution."""
    return _default_runner.run_subtask(
        intent=intent,
        actions=actions,
        expected_elements=expected_elements,
        unwanted_elements=unwanted_elements,
        timeout_sec=timeout_sec,
    )
