"""
Extra Scout — Skill Synthesizer
Synthesizes discovered app intelligence, CLI flags, hotkeys, and fast-paths
into an agentskills.io-compliant SKILL.md and commits playbooks to KùzuDB memory.
"""

import os
import re
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from extra.core.scout.detector import detect_app_profile, AppProfile
from extra.core.scout.scraper import get_app_intelligence
from extra.core.memory.ingest import record_action_app, record_action_quirk

logger = logging.getLogger("extra.scout.synthesizer")


def _slugify(name: str) -> str:
    """Converts application name to lowercase alphanumeric slug with hyphens."""
    clean = re.sub(r'[^a-zA-Z0-9]+', '-', name.strip().lower())
    return clean.strip('-')


def format_skill_markdown(app_name: str, profile: AppProfile, intel: Dict[str, Any]) -> str:
    """Generates agentskills.io compliant SKILL.md markdown string."""
    slug = _slugify(app_name)
    title = app_name.title()

    lines = [
        "---",
        f"name: extra-{slug}",
        f"description: Autonomous automation playbook, zero-stall fast paths, hotkeys, and CLI flags for {title}.",
        "---",
        "",
        f"# {title} Desktop Automation Protocol",
        "",
        f"> **Application Profile:** UI Framework: `{profile.ui_framework}` | "
        f"Installed: `{'Yes' if profile.is_installed else 'Web / External'}` | "
        f"Scripting API: `{profile.scripting_api or 'Native Input'}`",
        "",
        f"### Overview",
        intel.get("summary", f"Specialized automation guide for {title}."),
        "",
        "## 1. Application Architecture & UI Surface",
        intel.get("ui_surface_caveat", "Standard desktop window interface."),
        "",
        "## 2. Zero-Stall Fast Paths",
    ]

    for fp in intel.get("fast_paths", []):
        lines.append(f"- {fp}")

    lines.append("")
    lines.append("## 3. High-Speed Hotkeys Cheat Sheet")
    lines.append("| Shortcut | Action | Category |")
    lines.append("| :--- | :--- | :--- |")

    hotkeys = intel.get("hotkeys", [])
    if hotkeys:
        for hk in hotkeys:
            lines.append(f"| `{hk['key']}` | {hk['action']} | {hk.get('category', 'General')} |")
    else:
        lines.append("| `Ctrl + S` | Save | File |")
        lines.append("| `Esc` | Dismiss Modal / Popup | Navigation |")

    cli_opts = intel.get("cli_options", [])
    if cli_opts or profile.cli_supported:
        lines.append("")
        lines.append("## 4. Command Line Automation & Flags")
        lines.append("| Flag | Description | Example |")
        lines.append("| :--- | :--- | :--- |")
        for opt in cli_opts:
            lines.append(f"| `{opt['flag']}` | {opt['description']} | `{opt['example']}` |")

    lines.append("")
    lines.append("## 5. Anti-Stall Guardrails & Caveats")
    for guard in intel.get("anti_stall_guardrails", []):
        lines.append(f"- {guard}")

    lines.append("")
    return "\n".join(lines)


def scout_and_generate_skill(
    app_name: str,
    force_refresh: bool = False,
    custom_notes: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Just-In-Time app scouting: inspects application profile, scrapes shortcuts & CLI,
    synthesizes a specialized SKILL.md, writes to active skills directories, and commits to memory.
    
    Args:
        app_name: Application name or executable (e.g. 'blender', 'photoshop', 'canva').
        force_refresh: Whether to regenerate the skill even if it already exists.
        custom_notes: Optional user or agent guidance to incorporate into the playbook.
    """
    clean_name = app_name.strip().lower()
    slug = _slugify(clean_name)
    skill_dir_name = f"extra-{slug}"

    # Determine output directories
    target_dirs: List[Path] = []
    user_home = Path.home()

    # 1. Local workspace .agents/skills/
    if (Path.cwd() / ".agents").exists():
        target_dirs.append(Path.cwd() / ".agents" / "skills" / skill_dir_name)
    elif (Path.cwd().parent / ".agents").exists():
        target_dirs.append(Path.cwd().parent / ".agents" / "skills" / skill_dir_name)
    else:
        target_dirs.append(user_home / ".agents" / "skills" / skill_dir_name)

    # 2. Global user config .gemini/config/skills/
    target_dirs.append(user_home / ".gemini" / "config" / "skills" / skill_dir_name)

    # 3. Extra local skills repo
    target_dirs.append(user_home / ".extra" / "skills" / skill_dir_name)


    # Check if already generated and force_refresh is False
    if not force_refresh and all((d / "SKILL.md").exists() for d in target_dirs if d.parent.exists()):
        primary_file = target_dirs[0] / "SKILL.md"
        if primary_file.exists():
            try:
                from extra.core.platform.windows.shell import register_app, APP_REGISTRY
                if clean_name not in APP_REGISTRY:
                    register_app(clean_name, target=f"{clean_name}.exe", proc=f"{clean_name}.exe", app_type="exe")
            except Exception:
                pass
            return {
                "status": "cached",
                "app_name": app_name,
                "skill_name": skill_dir_name,
                "skill_path": str(primary_file),
                "summary": f"Using existing cached skill for {app_name}.",
            }

    # 1. Detect application profile
    profile = detect_app_profile(clean_name)

    # 2. Retrieve intelligence & cheat sheets
    intel = get_app_intelligence(clean_name, profile)

    if custom_notes:
        intel.setdefault("fast_paths", []).append(f"Custom Rule: {custom_notes}")

    # 3. Generate Markdown content
    content = format_skill_markdown(app_name, profile, intel)

    # 4. Write to all target skill directories
    written_paths: List[str] = []
    for d in target_dirs:
        try:
            d.mkdir(parents=True, exist_ok=True)
            skill_file = d / "SKILL.md"
            skill_file.write_text(content, encoding="utf-8")
            written_paths.append(str(skill_file))
        except Exception as e:
            logger.warning("Could not write skill to %s: %s", d, e)

    # 5. Ingest into KùzuDB memory graph
    try:
        record_action_app(app_name=clean_name, exe_path=profile.executable_path)
        primary_workaround = intel.get("fast_paths", ["Use keyboard shortcuts."])[0]
        record_action_quirk(
            app_name=clean_name,
            issue=intel.get("ui_surface_caveat", "Complex UI surface"),
            workaround=primary_workaround,
            playbook_snippet=f"App: {clean_name} | Framework: {profile.ui_framework} | Fast-path: {primary_workaround}",
        )
    except Exception as e:
        logger.debug("Memory ingestion during scout skipped or deferred: %s", e)

    # 6. Automatic Shell Registry Integration During Scout (TASK-120)
    try:
        from extra.core.platform.windows.shell import register_app
        target_path = profile.executable_path or f"{clean_name}.exe"
        register_app(clean_name, target=target_path, proc=os.path.basename(target_path), app_type="exe")
    except Exception as e:
        logger.debug("Shell registry auto-integration during scout skipped: %s", e)

    return {
        "status": "generated",
        "app_name": app_name,
        "ui_framework": profile.ui_framework,
        "is_installed": profile.is_installed,
        "cli_supported": profile.cli_supported,
        "scripting_api": profile.scripting_api,
        "skill_name": skill_dir_name,
        "skill_paths": written_paths,
        "hotkey_count": len(intel.get("hotkeys", [])),
        "summary": f"Scouted {app_name} ({profile.ui_framework}). Generated specialized SKILL.md with {len(intel.get('hotkeys', []))} hotkeys.",
    }
