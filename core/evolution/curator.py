"""
Extra Evolution — Skill Library Curator & Sanitizer
Scans, audits, sanitizes, detects duplicate skills, and catalogs active skills.
Automates healing of legacy unhardened evolved fast paths and mock skills across releases.
"""

import os
import re
import shutil
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger("extra.evolution.curator")


def get_default_skill_directories() -> List[Path]:
    """Returns discovered active skill directories across workspace and global configurations."""
    user_home = Path.home()
    candidates: List[Path] = [
        Path.cwd() / ".agents" / "skills",
        Path.cwd().parent / ".agents" / "skills",
        user_home / ".agents" / "skills",
        user_home / ".gemini" / "config" / "skills",
        user_home / ".extra" / "skills",
    ]
    env_path = os.environ.get("EXTRA_SKILLS_PATH")
    if env_path:
        candidates.append(Path(env_path))

    seen = set()
    result = []
    for d in candidates:
        try:
            resolved = d.resolve()
            if resolved not in seen:
                seen.add(resolved)
                result.append(d)
        except Exception:
            if str(d) not in seen:
                seen.add(str(d))
                result.append(d)
    return result


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


def clean_skill_content(content: str, strip_evolved: bool = True) -> str:
    """
    Cleans and normalizes SKILL.md content.
    If strip_evolved is True, removes legacy/unhardened evolved fast paths and evolution metadata comments.
    Normalizes consecutive empty lines and trailing whitespace.
    """
    lines = content.splitlines()
    cleaned_lines: List[str] = []
    skip_evolved_block = False

    for line in lines:
        stripped = line.strip()

        # Check for evolution metadata comments
        if re.search(r"<!--\s*Evolved by Extra Evolution Engine:.*?-->", line):
            continue

        if strip_evolved:
            # Check for evolved fast path entries
            if re.match(r"^-\s*\*\*Evolved\s+(?:API\s+)?Fast[ -]Path.*?:\*\*", stripped, re.IGNORECASE):
                # Skip this bullet and any non-bullet continuation lines
                skip_evolved_block = True
                continue
            if skip_evolved_block:
                if stripped.startswith("- ") or stripped.startswith("#") or stripped == "":
                    skip_evolved_block = False
                    if stripped.startswith("- ") or stripped.startswith("#"):
                        cleaned_lines.append(line)
                else:
                    continue
            else:
                cleaned_lines.append(line)
        else:
            cleaned_lines.append(line)

    result = "\n".join(cleaned_lines)
    # Normalize excess blank lines (max 2 consecutive newlines)
    result = re.sub(r"\n{3,}", "\n\n", result).rstrip() + "\n"
    return result


def sanitize_skill_library(
    strip_legacy_evolved: bool = True,
    remove_mock_skills: bool = True,
    target_dirs: Optional[List[Path]] = None,
) -> Dict[str, Any]:
    """
    Sanitizes all skill directories:
    1. Removes temporary/mock skill folders (e.g. extra-mock-*, mock-*).
    2. Strips legacy unhardened evolved lines and evolution comments from SKILL.md.
    3. Validates and repairs corrupted skill formatting.
    """
    search_dirs = target_dirs if target_dirs is not None else get_default_skill_directories()
    mock_names = {"extra-mock-app", "extra-mock-service", "extra-mock_service", "mock-app", "mock-service"}

    files_inspected = 0
    files_cleaned = 0
    mocks_removed = []
    cleaned_skills = []

    for base_dir in search_dirs:
        if not base_dir.exists():
            continue

        # 1. Remove mock directories
        if remove_mock_skills:
            try:
                for item in list(base_dir.iterdir()):
                    item_low = item.name.lower()
                    if item.is_dir() and (
                        item_low in mock_names
                        or item_low.startswith(("extra-mock", "mock-", "mock_"))
                    ):
                        try:
                            shutil.rmtree(item, ignore_errors=True)
                            mocks_removed.append(str(item))
                            logger.info("Removed mock skill folder: %s", item)
                        except Exception as e:
                            logger.warning("Could not remove mock skill folder %s: %s", item, e)
            except Exception as e:
                logger.warning("Error reading directory %s: %s", base_dir, e)

        # 2. Inspect and sanitize SKILL.md files
        for skill_md in base_dir.glob("*/SKILL.md"):
            files_inspected += 1
            try:
                folder_name = skill_md.parent.name
                original_text = skill_md.read_text(encoding="utf-8")
                cleaned_text = clean_skill_content(original_text, strip_evolved=strip_legacy_evolved)
                # Ensure frontmatter contains name
                fm = _parse_skill_frontmatter(skill_md)
                if not fm.get("name") and re.match(r"^---\s*\n", cleaned_text):
                    cleaned_text = re.sub(r"^---\s*\n", f"---\nname: {folder_name}\n", cleaned_text, count=1)
                if cleaned_text != original_text:
                    skill_md.write_text(cleaned_text, encoding="utf-8")
                    files_cleaned += 1
                    cleaned_skills.append(str(skill_md))
                    logger.info("Sanitized skill playbook: %s", skill_md)
            except Exception as e:
                logger.warning("Failed to sanitize %s: %s", skill_md, e)


    return {
        "status": "success",
        "files_inspected": files_inspected,
        "files_cleaned": files_cleaned,
        "mocks_removed": mocks_removed,
        "cleaned_skills": cleaned_skills,
    }


def ensure_startup_migration() -> Dict[str, Any]:
    """
    Ensures that existing users' environments and skills are sanitized upon upgrading
    to v0.3.0+. Strips legacy unhardened evolved lines and mock test skills automatically.
    Uses a versioned migration marker so it only runs once per release.
    """
    marker_file = Path.home() / ".extra" / ".v0_3_0_migration_done"
    if marker_file.exists():
        return {"status": "already_migrated"}

    try:
        report = sanitize_skill_library(strip_legacy_evolved=True, remove_mock_skills=True)
        marker_file.parent.mkdir(parents=True, exist_ok=True)
        marker_file.write_text(
            f"migrated_at={time.time()}\nstatus=migrated\nfiles_cleaned={report.get('files_cleaned', 0)}\n",
            encoding="utf-8",
        )
        report["status"] = "migrated"
        logger.info("Extra v0.3.0 startup migration completed: %s files cleaned.", report.get("files_cleaned", 0))
        return report
    except Exception as e:
        logger.warning("Startup migration notice: %s", e)
        return {"status": "error", "error": str(e)}


def curate_skill_library(sanitize: bool = False) -> Dict[str, Any]:
    """
    Curates and audits the skill libraries across workspace and global paths.
    Validates frontmatter, tracks locations, and indexes all discovered playbooks.
    Optionally sanitizes skills before cataloging.
    """
    if sanitize:
        sanitize_skill_library(strip_legacy_evolved=True, remove_mock_skills=True)

    search_dirs = get_default_skill_directories()
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

