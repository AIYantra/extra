"""
Extra Evolution — Skill Library Curator
Scans, validates frontmatter, detects duplicate skills, and catalogs active skills.
"""

import os
import re
from pathlib import Path
from typing import Dict, Any, List


def _parse_skill_frontmatter(file_path: Path) -> Dict[str, str]:
    """Extracts YAML frontmatter name and description from a SKILL.md file."""
    try:
        content = file_path.read_text(encoding="utf-8")
        match = re.search(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        if not match:
            return {}
        fm_text = match.group(1)
        res = {}
        for line in fm_text.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                res[k.strip().lower()] = v.strip().strip('"\'')
        return res
    except Exception:
        return {}


def curate_skill_library() -> Dict[str, Any]:
    """
    Curates and audits the skill libraries across workspace and global paths.
    Validates frontmatter, tracks locations, and indexes all discovered playbooks.
    """
    search_dirs = [
        Path("D:/yantra_workspace/.agents/skills"),
        Path(os.path.expandvars(r"%USERPROFILE%\.gemini\config\skills")),
        Path(os.path.expandvars(r"%USERPROFILE%\.extra\skills")),
    ]

    catalog: Dict[str, Dict[str, Any]] = {}
    corrupted_count = 0

    for base_dir in search_dirs:
        if not base_dir.exists():
            continue

        for skill_md in base_dir.glob("*/SKILL.md"):
            folder_name = skill_md.parent.name
            fm = _parse_skill_frontmatter(skill_md)
            skill_name = fm.get("name", folder_name)
            desc = fm.get("description", "No description provided.")

            if not fm.get("name") or not fm.get("description"):
                corrupted_count += 1

            if skill_name not in catalog:
                catalog[skill_name] = {
                    "name": skill_name,
                    "description": desc,
                    "locations": [str(skill_md)],
                    "is_valid": bool(fm.get("name") and fm.get("description")),
                }
            else:
                if str(skill_md) not in catalog[skill_name]["locations"]:
                    catalog[skill_name]["locations"].append(str(skill_md))

    return {
        "status": "healthy" if corrupted_count == 0 else "needs_attention",
        "total_unique_skills": len(catalog),
        "corrupted_count": corrupted_count,
        "skills": list(catalog.values()),
    }
