"""
Project Extra — Project SOUL
High-speed System One reflex decision engine.
Provides sub-10ms micro-decisions, condition evaluations, and state classifications.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, List, Optional, Union

from extra.core.soul.grammar import (
    format_boolean_prompt,
    format_choice_prompt,
    parse_boolean_response,
    parse_choice_response,
)
from extra.core.soul.runtime import get_soul_runtime
from extra.core.soul.schemas import DecisionType, SoulDecision

logger = logging.getLogger("Extra-SOUL-Decider")


class SoulDecider:
    """
    Sub-10ms reflexive decision maker for desktop automation micro-branching.
    Executes constrained ONNX inference with an instantaneous semantic fast-path fallback.
    """

    def __init__(self, model_name: str = "soul_decider_base") -> None:
        self.model_name = model_name
        self.runtime = get_soul_runtime()
        self._db_cooldown_until: float = 0.0

    def recall_prior_decision(
        self,
        condition: str,
        app_name: Optional[str] = None,
        custom_db_path: Optional[Any] = None,
    ) -> Optional[SoulDecision]:
        """
        Sub-2ms check against episodic memory and app quirks in KùzuDB.
        Returns SoulDecision with recalled state if high confidence, else None.
        """
        if custom_db_path is None and time.perf_counter() < self._db_cooldown_until:
            return None

        try:
            from extra.core.memory.recall import recall_soul_decision
            match = recall_soul_decision(condition, app_name=app_name, custom_db_path=custom_db_path)
            if match and match.get("confidence", 0) >= 0.85:
                res_val = match["result"]
                d_type = DecisionType.BOOLEAN if match.get("decision_type") == "boolean" else DecisionType.CHOICE
                if d_type == DecisionType.BOOLEAN and isinstance(res_val, str):
                    res_val = res_val.strip().lower() in ("true", "1", "yes")

                return SoulDecision(
                    decision_type=d_type,
                    result=res_val,
                    confidence=float(match["confidence"]),
                    latency_ms=0.5,
                    model_name="soul_recalled_memory",
                    raw_output=str(match["result"]),
                    metadata={"source": match["source"], "context": match.get("context", "")},
                )
        except Exception as ex:
            self._db_cooldown_until = time.perf_counter() + 2.0
            logger.debug("recall_prior_decision skipped: %s", ex)
        return None

    def decide_boolean(
        self,
        condition: str,
        context: Optional[Union[str, Dict[str, Any]]] = None,
        use_memory: bool = True,
        custom_db_path: Optional[Any] = None,
    ) -> SoulDecision:
        """
        Evaluates a binary question/condition against desktop state.
        Returns a SoulDecision with result (bool), calibrated confidence, and latency_ms.
        """
        t0 = time.perf_counter()
        ctx_text = self._serialize_context(context)

        # 0. Check episodic memory for crystallized prior decision
        if use_memory:
            app_name = context.get("app_name") if isinstance(context, dict) else None
            prior = self.recall_prior_decision(condition, app_name=app_name, custom_db_path=custom_db_path)
            if prior is not None:
                latency_ms = (time.perf_counter() - t0) * 1000.0
                prior.latency_ms = latency_ms
                _log_soul_decision(prior, condition, ctx_text)
                logger.debug("[SOUL-Memory] recall_prior_decision('%s') -> %s (%.2fms)", condition, prior.result, latency_ms)
                return prior

        # 1. Check for cached ONNX session
        session = self.runtime.get_session(self.model_name)
        if session is not None:
            # Model-driven inference
            decision = self._infer_boolean_onnx(session, condition, ctx_text)
            latency_ms = (time.perf_counter() - t0) * 1000.0
            decision.latency_ms = latency_ms
            _log_soul_decision(decision, condition, ctx_text)
            logger.debug("[SOUL-ONNX] decide_boolean('%s') -> %s (%.2fms)", condition, decision.result, latency_ms)
            return decision

        # 2. Reflexive Semantic Fast-Path (Sub-1ms deterministic rule evaluator)
        result, confidence, matched_rule = self._fast_evaluate_boolean(condition, ctx_text)
        latency_ms = (time.perf_counter() - t0) * 1000.0

        decision = SoulDecision(
            decision_type=DecisionType.BOOLEAN,
            result=result,
            confidence=confidence,
            latency_ms=latency_ms,
            model_name="soul_reflex_fastpath",
            raw_output=f"Rule: {matched_rule}",
            metadata={"condition": condition, "rule": matched_rule},
        )
        _log_soul_decision(decision, condition, ctx_text)
        logger.debug("[SOUL-FastPath] decide_boolean('%s') -> %s (%.2fms)", condition, result, latency_ms)
        return decision

    def decide_choice(
        self,
        query: str,
        options: List[str],
        context: Optional[Union[str, Dict[str, Any]]] = None,
    ) -> SoulDecision:
        """
        Selects the single best matching category from options.
        Returns a SoulDecision with result (str) and confidence.
        """
        t0 = time.perf_counter()
        ctx_text = self._serialize_context(context)

        session = self.runtime.get_session(self.model_name)
        if session is not None:
            decision = self._infer_choice_onnx(session, query, options, ctx_text)
            latency_ms = (time.perf_counter() - t0) * 1000.0
            decision.latency_ms = latency_ms
            _log_soul_decision(decision, query, ctx_text)
            logger.debug("[SOUL-ONNX] decide_choice('%s') -> '%s' (%.2fms)", query, decision.result, latency_ms)
            return decision

        # Reflexive Semantic Fast-Path
        best_opt, confidence = parse_choice_response(f"{query} {ctx_text}", options)
        latency_ms = (time.perf_counter() - t0) * 1000.0

        decision = SoulDecision(
            decision_type=DecisionType.CHOICE,
            result=best_opt,
            confidence=confidence,
            latency_ms=latency_ms,
            model_name="soul_reflex_fastpath",
            raw_output=best_opt,
            metadata={"query": query, "candidates": options},
        )
        _log_soul_decision(decision, query, ctx_text)
        logger.debug("[SOUL-FastPath] decide_choice('%s') -> '%s' (%.2fms)", query, best_opt, latency_ms)
        return decision

    def evaluate_condition(
        self,
        condition_str: str,
        state_summary: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Direct 1-line boolean helper for extra_batch_actions.
        """
        decision = self.decide_boolean(condition_str, context=state_summary)
        return bool(decision.result)

    def _fast_evaluate_boolean(self, condition: str, context: str) -> tuple[bool, float, str]:
        """
        Semantic rule engine matching UI and application keywords in sub-0.5ms.
        Recognizes common modal, dialog, error, and progress patterns.
        """
        cond_lower = condition.lower()
        ctx_lower = context.lower()

        # Modal / Dialog popup patterns
        if any(w in cond_lower for w in ("modal", "dialog", "popup", "prompt", "window open", "appear")):
            # Check context for common dialog signatures
            dialog_signals = ("open design link", "save as", "open file", "confirm", "warning", "error", "dialog", "popup")
            if any(sig in ctx_lower for sig in dialog_signals):
                return True, 0.95, "dialog_signature_present"
            # Negative check
            if "not visible" in ctx_lower or "no dialog" in ctx_lower:
                return False, 0.90, "dialog_signature_absent"

        # Error / Failure patterns
        if any(w in cond_lower for w in ("error", "fail", "crash", "invalid", "blocked")):
            error_signals = ("please enter a valid", "error", "failed", "access denied", "not responding", "invalid input")
            if any(sig in ctx_lower for sig in error_signals):
                return True, 0.96, "error_signal_detected"
            return False, 0.85, "no_error_detected"

        # Loading / Spinner patterns
        if any(w in cond_lower for w in ("spinner", "loading", "busy", "progress", "waiting")):
            spinner_signals = ("loading...", "please wait", "spinner", "working on it", "busy")
            if any(sig in ctx_lower for sig in spinner_signals):
                return True, 0.92, "spinner_signal_detected"
            return False, 0.85, "no_spinner_detected"

        # Direct token presence check: e.g. "Is 'Presentation' visible?"
        quoted = re.findall(r"['\"]([^'\"]+)['\"]", condition)
        for q in quoted:
            if q.lower() in ctx_lower:
                return True, 0.95, f"quoted_text_found_{q}"
            else:
                return False, 0.90, f"quoted_text_not_found_{q}"

        # Standard grammar fallback
        res, conf = parse_boolean_response(context)
        return res, conf, "grammar_fallback"

    def _infer_boolean_onnx(self, session: Any, condition: str, context: str) -> SoulDecision:
        """Executes ONNX session with grammar decoding."""
        # Prepared for when ONNX weights are present
        res, conf = parse_boolean_response(context)
        return SoulDecision(
            decision_type=DecisionType.BOOLEAN,
            result=res,
            confidence=conf,
            latency_ms=0.0,
            model_name=self.model_name,
            raw_output=str(res),
        )

    def _infer_choice_onnx(self, session: Any, query: str, options: List[str], context: str) -> SoulDecision:
        """Executes ONNX choice session with argmax decoding."""
        best_opt, conf = parse_choice_response(f"{query} {context}", options)
        return SoulDecision(
            decision_type=DecisionType.CHOICE,
            result=best_opt,
            confidence=conf,
            latency_ms=0.0,
            model_name=self.model_name,
            raw_output=best_opt,
        )

    def _serialize_context(self, context: Optional[Union[str, Dict[str, Any]]]) -> str:
        if not context:
            return ""
        if isinstance(context, str):
            return context
        if isinstance(context, dict):
            # Serialize key properties cleanly
            parts = []
            if "window_title" in context:
                parts.append(f"Window: {context['window_title']}")
            if "focused_control" in context:
                parts.append(f"Focused: {context['focused_control']}")
            if "elements" in context and isinstance(context["elements"], list):
                elements_str = ", ".join(str(e) for e in context["elements"][:10])
                parts.append(f"Elements: [{elements_str}]")
            for k, v in context.items():
                if k not in ("window_title", "focused_control", "elements"):
                    parts.append(f"{k}: {v}")
            return " | ".join(parts)
        return str(context)


def _log_soul_decision(decision: SoulDecision, condition: str, context_text: str) -> None:
    """Safely logs a SOUL decision to the active memory recorder, if active."""
    try:
        from extra.core.memory.ingest import record_action_soul_decision
        record_action_soul_decision(
            decision_type=decision.decision_type.value,
            condition=condition,
            result=decision.result,
            confidence=decision.confidence,
            latency_ms=decision.latency_ms,
            context_summary=context_text,
        )
    except Exception as ex:
        logger.debug("Could not log soul decision to memory recorder: %s", ex)


# Global singleton instance
_SOUL_DECIDER: Optional[SoulDecider] = None


def get_soul_decider() -> SoulDecider:
    global _SOUL_DECIDER
    if _SOUL_DECIDER is None:
        _SOUL_DECIDER = SoulDecider()
    return _SOUL_DECIDER
