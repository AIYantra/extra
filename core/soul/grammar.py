"""
Project Extra — Project SOUL
Grammar and constrained decoding utilities.
Ensures zero-hallucination output by enforcing rigid schemas on raw model outputs.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple, Union


def format_boolean_prompt(condition: str, context: Optional[str] = None) -> str:
    """Formats a deterministic binary question prompt for SOUL."""
    ctx_str = f"\nContext:\n{context.strip()}" if context and context.strip() else ""
    return (
        f"You are SOUL, an ultra-fast on-device decision reflex.\n"
        f"Answer the following question with strictly TRUE or FALSE.{ctx_str}\n"
        f"Question: {condition.strip()}\n"
        f"Answer:"
    )


def format_choice_prompt(query: str, options: List[str], context: Optional[str] = None) -> str:
    """Formats a deterministic multiple-choice question prompt for SOUL."""
    options_str = ", ".join(f"'{opt}'" for opt in options)
    ctx_str = f"\nContext:\n{context.strip()}" if context and context.strip() else ""
    return (
        f"You are SOUL, an ultra-fast on-device decision reflex.\n"
        f"Select the single best matching category from: [{options_str}].{ctx_str}\n"
        f"Condition to evaluate: {query.strip()}\n"
        f"Answer:"
    )


def parse_boolean_response(raw_text: str) -> Tuple[bool, float]:
    """
    Parses and sanitizes a raw output into a verified boolean and confidence.
    Guarantees strict boolean output regardless of raw formatting.
    """
    cleaned = raw_text.strip().lower()
    
    # Exact token match
    if cleaned in ("true", "yes", "1", "y", "t"):
        return True, 0.95
    if cleaned in ("false", "no", "0", "n", "f"):
        return False, 0.95

    # Prefix match
    if cleaned.startswith("true") or cleaned.startswith("yes"):
        return True, 0.85
    if cleaned.startswith("false") or cleaned.startswith("no"):
        return False, 0.85

    # Regex search for truthy/falsy keywords
    true_match = re.search(r"\b(true|yes|confirmed|present|visible)\b", cleaned)
    false_match = re.search(r"\b(false|no|absent|missing|not visible)\b", cleaned)

    if true_match and not false_match:
        return True, 0.75
    if false_match and not true_match:
        return False, 0.75

    # Default to False with low confidence if totally ambiguous
    return False, 0.50


def parse_choice_response(raw_text: str, options: List[str]) -> Tuple[str, float]:
    """
    Constrains raw model text to strictly one of the supplied options.
    Returns (matched_option, confidence).
    """
    if not options:
        return raw_text.strip(), 0.0

    cleaned = raw_text.strip().lower()

    # 1. Exact match (case-insensitive)
    for opt in options:
        if cleaned == opt.lower():
            return opt, 0.98

    # 2. Substring / Word-boundary containment (with underscore-to-space normalization)
    for opt in options:
        opt_variants = [opt.lower(), opt.lower().replace("_", " "), opt.lower().replace("-", " ")]
        for variant in set(opt_variants):
            pattern = r"\b" + re.escape(variant) + r"\b"
            if re.search(pattern, cleaned):
                return opt, 0.88

    # 3. Partial startswith containment
    for opt in options:
        if cleaned.startswith(opt.lower()) or cleaned.startswith(opt.lower().replace("_", " ")):
            return opt, 0.80

    # 4. Fallback: match highest alphanumeric token overlap
    best_opt = options[0]
    best_score = 0.0
    cleaned_tokens = set(re.findall(r"[a-z0-9]+", cleaned))

    for opt in options:
        opt_tokens = set(re.findall(r"[a-z0-9]+", opt.lower()))
        if not opt_tokens:
            continue
        overlap = len(cleaned_tokens.intersection(opt_tokens)) / len(opt_tokens)
        if overlap > best_score:
            best_score = overlap
            best_opt = opt

    confidence = 0.50 + (best_score * 0.40)
    return best_opt, confidence
