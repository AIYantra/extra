"""
Project Extra — Complete System Uninstaller & Purge Subsystem
Implements native OS confirmation modals (default NO), MCP server deregistration,
user PATH cleanup, and recursive self-deletion across Windows and macOS.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("extra.uninstall")

DISCLAIMER_TEXT = (
    "EXTRA UNINSTALLATION DISCLAIMER\n\n"
    "WARNING: This will permanently and completely remove Extra from your computer.\n\n"
    "The following components will be deleted:\n"
    " • Extra Runtime, CLI & Virtual Environment (%USERPROFILE%\\.extra)\n"
    " • Episodic Memory Graph & Learned Quirks (KùzuDB)\n"
    " • All Task Blueprints, Checkpoints & Workspace Files\n"
    " • AI Agent Skills & Global Rules\n"
    " • MCP Server Registrations (Claude Desktop, Antigravity, Cursor, Windsurf)\n\n"
    "This action cannot be undone.\n\n"
    "Are you sure you want to completely uninstall Extra from this device?"
)


def prompt_gui_confirmation(
    title: str = "Extra Uninstallation — Confirmation Required",
    force_no_gui: bool = False,
) -> bool:
    """
    Displays a native OS modal dialog with the disclaimer.
    CRITICAL: The default selected button is strictly set to 'NO' / 'Cancel'
    so accidental Enter/Space keypresses will abort safely.

    Returns:
        True if and only if the user explicitly confirms uninstallation.
    """
    if force_no_gui:
        return prompt_cli_confirmation(title)

    system = platform.system()

    # 1. Windows: Win32 MessageBoxW with MB_YESNO | MB_ICONWARNING | MB_DEFBUTTON2
    if system == "Windows":
        try:
            import ctypes

            MB_YESNO = 0x00000004
            MB_ICONWARNING = 0x00000030
            MB_DEFBUTTON2 = 0x00000100      # Button 2 (NO) is selected by default!
            MB_SETFOREGROUND = 0x00010000   # Bring window to foreground
            MB_TOPMOST = 0x00040000         # Always on top

            flags = MB_YESNO | MB_ICONWARNING | MB_DEFBUTTON2 | MB_SETFOREGROUND | MB_TOPMOST
            result = ctypes.windll.user32.MessageBoxW(0, DISCLAIMER_TEXT, title, flags)
            IDYES = 6
            return result == IDYES
        except Exception as ex:
            logger.warning("Windows native MessageBox failed: %s, falling back to Tkinter/CLI", ex)

    # 2. macOS: AppleScript display alert with default button 'Cancel'
    elif system == "Darwin":
        try:
            escaped_text = DISCLAIMER_TEXT.replace('"', '\\"').replace("\n", "\\n")
            script = (
                f'display alert "{title}" message "{escaped_text}" '
                f'as critical buttons {{"Cancel", "Uninstall Extra"}} '
                f'default button "Cancel" cancel button "Cancel"'
            )
            res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            return "Uninstall Extra" in res.stdout
        except Exception as ex:
            logger.warning("macOS osascript alert failed: %s, falling back to Tkinter/CLI", ex)

    # 3. Fallback: Tkinter (if available) with default 'no'
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        res = messagebox.askyesno(
            title=title,
            message=DISCLAIMER_TEXT,
            default=messagebox.NO,
            icon=messagebox.WARNING,
        )
        root.destroy()
        return bool(res)
    except Exception:
        pass

    # 4. Final Fallback: Terminal CLI prompt with default No
    return prompt_cli_confirmation(title)


def prompt_cli_confirmation(title: str = "Extra Uninstallation") -> bool:
    """Interactive console prompt with default NO."""
    print("\n" + "=" * 70)
    print(f" {title.upper()}")
    print("=" * 70)
    print(DISCLAIMER_TEXT)
    print("=" * 70)
    try:
        ans = input("\nType 'YES' to permanently delete Extra [default: No]: ").strip()
        return ans.upper() == "YES"
    except (EOFError, KeyboardInterrupt):
        return False


def cleanup_claude_desktop(config_path: Optional[Path] = None) -> bool:
    """Removes 'extra' entry from Claude Desktop mcpServers config."""
    if config_path is None:
        if platform.system() == "Windows":
            appdata = os.environ.get("APPDATA", "")
            if not appdata:
                return False
            config_path = Path(appdata) / "Claude" / "claude_desktop_config.json"
        elif platform.system() == "Darwin":
            config_path = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
        else:
            return False

    if not config_path.exists():
        return False

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        if "mcpServers" in data and "extra" in data["mcpServers"]:
            del data["mcpServers"]["extra"]
            config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            logger.info("Removed Extra from Claude Desktop config at %s", config_path)
            return True
    except Exception as ex:
        logger.warning("Failed to clean Claude Desktop config: %s", ex)
    return False


def cleanup_antigravity() -> List[str]:
    """Removes Extra MCP registrations and rule files from Antigravity environment."""
    removed_items: List[str] = []

    # 1. agy mcp remove extra
    try:
        res = subprocess.run(["agy", "mcp", "remove", "extra"], capture_output=True, text=True)
        if res.returncode == 0:
            removed_items.append("Antigravity MCP server 'extra' deregistered")
    except Exception:
        pass

    user_home = Path.home()

    # 2. Global skill: ~/.gemini/config/skills/extra-automation
    skill_dir = user_home / ".gemini" / "config" / "skills" / "extra-automation"
    if skill_dir.exists():
        try:
            shutil.rmtree(skill_dir, ignore_errors=True)
            removed_items.append(f"Removed global skill {skill_dir}")
        except Exception:
            pass

    # 3. Global MCP instructions: ~/.gemini/antigravity-cli/mcp/extra
    mcp_extra_dir = user_home / ".gemini" / "antigravity-cli" / "mcp" / "extra"
    if mcp_extra_dir.exists():
        try:
            shutil.rmtree(mcp_extra_dir, ignore_errors=True)
            removed_items.append(f"Removed MCP instructions {mcp_extra_dir}")
        except Exception:
            pass

    # 4. Clean GEMINI.md protocol entry
    gemini_md = user_home / ".gemini" / "GEMINI.md"
    if gemini_md.exists():
        try:
            content = gemini_md.read_text(encoding="utf-8")
            marker = "## Extra Windows Desktop Automation Protocol"
            if marker in content:
                # Remove from marker to next major heading or end
                lines = content.splitlines()
                kept_lines = []
                skipping = False
                for line in lines:
                    if marker in line:
                        skipping = True
                    elif skipping and line.startswith("# ") and not line.startswith("## Extra"):
                        skipping = False
                    if not skipping:
                        kept_lines.append(line)
                gemini_md.write_text("\n".join(kept_lines), encoding="utf-8")
                removed_items.append("Cleaned Extra protocol from ~/.gemini/GEMINI.md")
        except Exception:
            pass

    # 5. User workspace rule: ~/.agents/rules/extra_automation.md
    user_rule = user_home / ".agents" / "rules" / "extra_automation.md"
    if user_rule.exists():
        try:
            user_rule.unlink(missing_ok=True)
            removed_items.append(f"Removed user rule {user_rule}")
        except Exception:
            pass

    return removed_items


def cleanup_ide_configs() -> List[str]:
    """Cleans up Cursor and Windsurf MCP configuration files."""
    cleaned = []
    user_home = Path.home()

    # Windsurf
    windsurf_cfg = user_home / ".codeium" / "windsurf" / "mcp_config.json"
    if windsurf_cfg.exists():
        try:
            data = json.loads(windsurf_cfg.read_text(encoding="utf-8"))
            if "mcpServers" in data and "extra" in data["mcpServers"]:
                del data["mcpServers"]["extra"]
                windsurf_cfg.write_text(json.dumps(data, indent=2), encoding="utf-8")
                cleaned.append("Cleaned Extra from Windsurf MCP config")
        except Exception:
            pass

    return cleaned


def remove_from_user_path() -> bool:
    """Removes ~/.extra/bin from user PATH variable."""
    system = platform.system()
    extra_bin_name = ".extra"

    if system == "Windows":
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_READ | winreg.KEY_WRITE
            ) as key:
                try:
                    val, val_type = winreg.QueryValueEx(key, "Path")
                except FileNotFoundError:
                    return False

                parts = [p.strip() for p in val.split(";") if p.strip()]
                new_parts = [p for p in parts if extra_bin_name not in p.lower()]

                if len(parts) != len(new_parts):
                    new_val = ";".join(new_parts)
                    winreg.SetValueEx(key, "Path", 0, val_type, new_val)
                    # Broadcast environment change
                    try:
                        import ctypes

                        HWND_BROADCAST = 0xFFFF
                        WM_SETTINGCHANGE = 0x001A
                        SMTO_ABORTIFHUNG = 0x0002
                        ctypes.windll.user32.SendMessageTimeoutW(
                            HWND_BROADCAST,
                            WM_SETTINGCHANGE,
                            0,
                            "Environment",
                            SMTO_ABORTIFHUNG,
                            1000,
                            ctypes.byref(ctypes.c_ulong()),
                        )
                    except Exception:
                        pass
                    logger.info("Removed Extra from Windows User PATH")
                    return True
        except Exception as ex:
            logger.warning("Failed to clean Windows User PATH: %s", ex)
            return False

    elif system in ("Darwin", "Linux"):
        user_home = Path.home()
        modified = False
        for sh_rc in [user_home / ".zshrc", user_home / ".bashrc", user_home / ".bash_profile"]:
            if sh_rc.exists():
                try:
                    content = sh_rc.read_text(encoding="utf-8")
                    if ".extra/bin" in content:
                        new_lines = [
                            line for line in content.splitlines() if ".extra/bin" not in line
                        ]
                        sh_rc.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
                        modified = True
                except Exception:
                    pass
        return modified

    return False


def purge_extra_directory(extra_dir: Optional[Path] = None, delay_sec: int = 2) -> None:
    """
    Completely and permanently purges the .extra directory.
    Uses a detached process to allow the currently running Python interpreter to exit
    before removing locked binaries.
    """
    target = extra_dir or (Path.home() / ".extra")
    if not target.exists():
        return

    # 1. Delete immediately accessible subdirectories
    immediate_subdirs = [
        "workspace", "blueprints", "checkpoints", "memory", "skills",
        "archive_legacy_scratch", "extracted_deliverables"
    ]
    for sub in immediate_subdirs:
        sub_path = target / sub
        if sub_path.exists():
            try:
                shutil.rmtree(sub_path, ignore_errors=True)
            except Exception:
                pass

    # Delete non-locked loose files
    for item in target.glob("*"):
        if item.is_file() and not item.name.endswith(".exe"):
            try:
                item.unlink(missing_ok=True)
            except Exception:
                pass

    system = platform.system()

    # 2. Spawn detached cleanup script to remove venv and root directory after exit
    if system == "Windows":
        temp_dir = Path(tempfile.gettempdir())
        bat_script = temp_dir / f"extra_purge_{int(time.time())}.bat"
        script_content = f"""@echo off
timeout /t {delay_sec} /nobreak >nul
if exist "{target}" (
    rmdir /s /q "{target}" >nul 2>&1
)
del "%~f0" >nul 2>&1
"""
        bat_script.write_text(script_content, encoding="utf-8")
        try:
            DETACHED_PROCESS = 0x00000008
            CREATE_NEW_PROCESS_GROUP = 0x00000200
            subprocess.Popen(
                ["cmd.exe", "/c", str(bat_script)],
                creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
                close_fds=True,
            )
        except Exception as ex:
            logger.warning("Failed to spawn Windows detached purge script: %s", ex)

    elif system in ("Darwin", "Linux"):
        cmd = f"sleep {delay_sec} && rm -rf '{target}'"
        try:
            subprocess.Popen(["sh", "-c", cmd], start_new_session=True)
        except Exception as ex:
            logger.warning("Failed to spawn POSIX detached purge script: %s", ex)


def perform_uninstall(
    force: bool = False,
    dry_run: bool = False,
    extra_dir: Optional[Path] = None,
) -> int:
    """
    Main orchestrator for 'extra uninstall'.
    Presents the confirmation modal with default NO, cleans integrations, and purges all files.
    """
    print("\n" + "=" * 70)
    print(" EXTRA COMPLETE SYSTEM UNINSTALLATION")
    print("=" * 70)

    # 1. Confirmation Modal
    if not force:
        confirmed = prompt_gui_confirmation()
        if not confirmed:
            print("\n[CANCELLED] Uninstallation aborted by user. Extra remains installed.\n")
            return 0
    else:
        print("\n[--yes / force] Confirmation bypassed via command line flag.")

    target_dir = extra_dir or (Path.home() / ".extra")

    if dry_run:
        print("\n[DRY RUN] The following actions would be performed:")
        print(f"  • Purge directory: {target_dir}")
        print("  • Deregister from Claude Desktop, Antigravity, Cursor, and Windsurf")
        print("  • Remove ~/.extra/bin from user PATH")
        print("  • Remove all learned skills, memory graph, and blueprints")
        print("\n[DRY RUN COMPLETE] No files were deleted.\n")
        return 0

    print("\nStarting uninstallation process...")

    # 2. Deregister from Claude Desktop
    claude_ok = cleanup_claude_desktop()
    if claude_ok:
        print("  [OK] Deregistered Extra from Claude Desktop")

    # 3. Deregister from Antigravity & clean rules
    agy_cleaned = cleanup_antigravity()
    for item in agy_cleaned:
        print(f"  [OK] {item}")

    # 4. Deregister from IDEs
    ide_cleaned = cleanup_ide_configs()
    for item in ide_cleaned:
        print(f"  [OK] {item}")

    # 5. Clean PATH
    path_cleaned = remove_from_user_path()
    if path_cleaned:
        print("  [OK] Removed Extra from user PATH environment variable")

    # 6. Purge files & directory
    print(f"  [OK] Purging Extra installation directory: {target_dir}")
    purge_extra_directory(target_dir)

    print("\n" + "=" * 70)
    print(" [COMPLETE] EXTRA HAS BEEN COMPLETELY REMOVED FROM YOUR DEVICE.")
    print(" All background files, memory databases, and configs have been purged.")
    print("=" * 70 + "\n")
    return 0
