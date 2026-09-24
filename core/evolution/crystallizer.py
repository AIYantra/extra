"""
Extra Evolution — Skill Crystallizer
Crystallizes discovered fast-paths, workarounds, and anti-stall guardrails
into versioned, permanent SKILL.md playbooks and updates the KùzuDB memory graph.
"""

import os
import re
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from extra.core.scout.synthesizer import _slugify, scout_and_generate_skill
from extra.core.memory.ingest import record_action_quirk, record_action_app
from extra.core.evolution.curator import get_default_skill_directories

logger = logging.getLogger("extra.evolution.crystallizer")


def _find_existing_skill(slug: str, search_roots: Optional[List[Path]] = None) -> Optional[Path]:
    """Locates existing SKILL.md in workspace or user configuration directories."""
    roots = search_roots if search_roots is not None else get_default_skill_directories()
    for base in roots:
        for candidate in [base / f"extra-{slug}" / "SKILL.md", base / slug / "SKILL.md"]:
            if candidate.exists():
                return candidate
    return None



def _patch_skill_content(
    content: str,
    workflow_summary: str,
    instructions: str,
    friction_points: Optional[List[str]] = None,
    solutions_found: Optional[List[str]] = None,
    fastpath_file: Optional[str] = None,
    is_golden_path: bool = True,
) -> str:
    """Injects newly evolved fast paths and guardrails into an existing SKILL.md with strict deduplication."""
    evolve_timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    has_changes = False

    # Format new fast-path entry ONLY if golden path
    if is_golden_path:
        if fastpath_file:
            new_fast_path = f"- **Evolved API Fast-Path ({workflow_summary}):** Run `python {fastpath_file}` — {instructions}"
        else:
            new_fast_path = f"- **Evolved Fast Path ({workflow_summary}):** {instructions}"

        # Inject into "## 2. Zero-Stall Fast Paths"
        fast_path_header = "## 2. Zero-Stall Fast Paths"
        if fast_path_header in content:
            parts = content.split(fast_path_header, 1)
            # Check if already present to avoid duplication
            if workflow_summary.strip().lower() not in parts[1].lower():
                content = f"{parts[0]}{fast_path_header}\n{new_fast_path}\n{parts[1]}"
                has_changes = True
        else:
            content += f"\n\n{fast_path_header}\n{new_fast_path}\n"
            has_changes = True

    # Inject into "## 5. Anti-Stall Guardrails & Caveats" with strict normalized deduplication
    if friction_points or solutions_found:
        guardrails_header = "## 5. Anti-Stall Guardrails & Caveats"
        existing_normalized = {
            re.sub(r"\s+", " ", line.strip().lower())
            for line in content.splitlines()
            if line.strip()
        }

        new_guards = []
        if friction_points:
            for fp in friction_points:
                clean_fp = fp.strip()
                if not clean_fp:
                    continue
                line = f"- Avoid: {clean_fp}"
                norm_line = re.sub(r"\s+", " ", line.lower())
                if norm_line not in existing_normalized:
                    new_guards.append(line)
                    existing_normalized.add(norm_line)

        if solutions_found:
            for sol in solutions_found:
                clean_sol = sol.strip()
                if not clean_sol:
                    continue
                line = f"- Verified Resolution: {clean_sol}"
                norm_line = re.sub(r"\s+", " ", line.lower())
                if norm_line not in existing_normalized:
                    new_guards.append(line)
                    existing_normalized.add(norm_line)

        if new_guards:
            has_changes = True
            guards_str = "\n".join(new_guards)
            if guardrails_header in content:
                parts = content.split(guardrails_header, 1)
                content = f"{parts[0]}{guardrails_header}\n{guards_str}\n{parts[1]}"
            else:
                content += f"\n\n{guardrails_header}\n{guards_str}\n"

    # Only append evolution metadata comment if actual new content was injected
    if has_changes:
        evolution_meta = f"\n<!-- Evolved by Extra Evolution Engine: {evolve_timestamp} | Focus: {workflow_summary} -->\n"
        content = content.rstrip() + evolution_meta

    return content


def crystallize_skill_evolution(
    app_name: str,
    workflow_summary: str,
    instructions: str,
    friction_points: Optional[List[str]] = None,
    solutions_found: Optional[List[str]] = None,
    skill_name: Optional[str] = None,
    fastpath_file: Optional[str] = None,
    is_golden_path: bool = True,
    target_dirs: Optional[List[Path]] = None,
) -> Dict[str, Any]:
    """
    Crystallizes a verified workflow into a permanent skill.
    If the skill already exists, patches it with the newly learned fast path.
    If the skill does not exist, scaffolds it via Extra Scout first, then patches it.
    
    Args:
        app_name: Name of the application (e.g. 'canva', 'blender', 'photoshop').
        workflow_summary: Short summary of what was accomplished (e.g. 'Instagram Poster Direct Injection').
        instructions: Precise step-by-step instructions or fast-path playbook.
        friction_points: Optional list of pitfalls or errors encountered.
        solutions_found: Optional list of resolutions discovered.
        skill_name: Optional explicit skill name override.
        fastpath_file: Optional synthesized python fastpath script file path.
        is_golden_path: If True, injects into Zero-Stall Fast Paths. If False, only records guardrails.
        target_dirs: Optional explicit list of target directories to write the skill to.
    """
    clean_name = app_name.strip().lower()
    slug = _slugify(clean_name)
    target_skill_name = skill_name or f"extra-{slug}"

    # Target output directories
    if target_dirs is None:
        target_dirs = [d / target_skill_name for d in get_default_skill_directories()]

    existing_skill_file = _find_existing_skill(slug)
    if not is_golden_path:
        patch_type = "guardrails_only"
    else:
        patch_type = "updated" if existing_skill_file else "created"

    if existing_skill_file:
        base_content = existing_skill_file.read_text(encoding="utf-8")
    else:
        # Scaffold new skill via Scout
        scout_res = scout_and_generate_skill(clean_name, force_refresh=True)
        if scout_res.get("skill_paths"):
            base_content = Path(scout_res["skill_paths"][0]).read_text(encoding="utf-8")
        else:
            base_content = f"---\nname: {target_skill_name}\ndescription: Automation playbook for {clean_name}.\n---\n# {clean_name.capitalize()} Automation Protocol\n\n## 2. Zero-Stall Fast Paths\n"

    # Patch with evolved intelligence
    updated_content = _patch_skill_content(
        content=base_content,
        workflow_summary=workflow_summary,
        instructions=instructions,
        friction_points=friction_points,
        solutions_found=solutions_found,
        fastpath_file=fastpath_file,
        is_golden_path=is_golden_path,
    )

    # Save to all target skill directories
    written_paths: List[str] = []
    for d in target_dirs:
        try:
            d.mkdir(parents=True, exist_ok=True)
            skill_file = d / "SKILL.md"
            skill_file.write_text(updated_content, encoding="utf-8")
            written_paths.append(str(skill_file))
        except Exception as e:
            logger.warning("Could not write evolved skill to %s: %s", d, e)

    # Record in KùzuDB memory (skip for test/mock apps)
    if not clean_name.startswith("mock") and not clean_name.startswith("test"):
        try:
            record_action_app(app_name=clean_name)
            primary_issue = friction_points[0] if friction_points else "Execution friction in workflow"
            primary_sol = solutions_found[0] if solutions_found else instructions
            record_action_quirk(
                app_name=clean_name,
                issue=primary_issue,
                workaround=primary_sol,
                playbook=f"Task: {workflow_summary} | Evolved Playbook: {instructions}",
            )
        except Exception as e:
            logger.debug("Memory ingestion during evolution skipped or deferred: %s", e)


    return {
        "status": "evolved",
        "app_name": app_name,
        "skill_name": target_skill_name,
        "patch_type": patch_type,
        "workflow_summary": workflow_summary,
        "skill_paths": written_paths,
        "summary": f"Evolved {target_skill_name} ({patch_type}). Injected zero-stall fast path for '{workflow_summary}'.",
    }


def crystallize_soul_fastpath(
    app_name: str,
    trigger_condition: str,
    resolved_action: str,
    confidence: float = 0.95,
    friction_points: Optional[List[str]] = None,
    solutions_found: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Crystallizes a recurring SOUL micro-decision into a permanent fast-path rule
    within the application's SKILL.md and memory graph.
    """
    clean_app = app_name.strip().lower()
    fastpath_instruction = f"If condition '{trigger_condition}' evaluates True: execute {resolved_action} (confidence: {confidence:.2f})"

    return crystallize_skill_evolution(
        app_name=clean_app,
        workflow_summary=f"SOUL Fast-Path: {trigger_condition}",
        instructions=fastpath_instruction,
        friction_points=friction_points or [f"Intermittent trigger: {trigger_condition}"],
        solutions_found=solutions_found or [f"Auto-resolved with {resolved_action}"],
    )

