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

logger = logging.getLogger("extra.evolution.crystallizer")


def _find_existing_skill(slug: str) -> Optional[Path]:
    """Locates existing SKILL.md in workspace or user configuration directories."""
    candidate_paths = [
        Path("D:/yantra_workspace/.agents/skills") / f"extra-{slug}" / "SKILL.md",
        Path("D:/yantra_workspace/.agents/skills") / slug / "SKILL.md",
        Path(os.path.expandvars(r"%USERPROFILE%\.gemini\config\skills")) / f"extra-{slug}" / "SKILL.md",
        Path(os.path.expandvars(r"%USERPROFILE%\.extra\skills")) / f"extra-{slug}" / "SKILL.md",
    ]
    for p in candidate_paths:
        if p.exists():
            return p
    return None


def _patch_skill_content(
    content: str,
    workflow_summary: str,
    instructions: str,
    friction_points: Optional[List[str]] = None,
    solutions_found: Optional[List[str]] = None,
) -> str:
    """Injects newly evolved fast paths and guardrails into an existing SKILL.md."""
    evolve_timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    # Format new fast-path entry
    new_fast_path = f"- **Evolved Fast Path ({workflow_summary}):** {instructions}"

    # Inject into "## 2. Zero-Stall Fast Paths"
    fast_path_header = "## 2. Zero-Stall Fast Paths"
    if fast_path_header in content:
        parts = content.split(fast_path_header, 1)
        # Check if already present to avoid duplication
        if workflow_summary not in parts[1]:
            content = f"{parts[0]}{fast_path_header}\n{new_fast_path}\n{parts[1]}"
    else:
        content += f"\n\n{fast_path_header}\n{new_fast_path}\n"

    # Inject into "## 5. Anti-Stall Guardrails & Caveats"
    if friction_points or solutions_found:
        guardrails_header = "## 5. Anti-Stall Guardrails & Caveats"
        new_guards = []
        if friction_points:
            for fp in friction_points:
                new_guards.append(f"- Avoid: {fp}")
        if solutions_found:
            for sol in solutions_found:
                new_guards.append(f"- Verified Resolution: {sol}")

        if guardrails_header in content:
            parts = content.split(guardrails_header, 1)
            guards_str = "\n".join(new_guards)
            content = f"{parts[0]}{guardrails_header}\n{guards_str}\n{parts[1]}"
        else:
            content += f"\n\n{guardrails_header}\n" + "\n".join(new_guards) + "\n"

    # Append evolution metadata comment
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
    """
    clean_name = app_name.strip().lower()
    slug = _slugify(clean_name)
    target_skill_name = skill_name or f"extra-{slug}"

    # Target output directories
    target_dirs = [
        Path("D:/yantra_workspace/.agents/skills") / target_skill_name,
        Path(os.path.expandvars(r"%USERPROFILE%\.gemini\config\skills")) / target_skill_name,
        Path(os.path.expandvars(r"%USERPROFILE%\.extra\skills")) / target_skill_name,
    ]

    existing_skill_file = _find_existing_skill(slug)
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

    # Record in KùzuDB memory
    try:
        record_action_app(app_name=clean_name)
        primary_issue = friction_points[0] if friction_points else "Execution friction in workflow"
        primary_sol = solutions_found[0] if solutions_found else instructions
        record_action_quirk(
            app_name=clean_name,
            issue=primary_issue,
            workaround=primary_sol,
            playbook_snippet=f"Task: {workflow_summary} | Evolved Playbook: {instructions}",
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
