# Extra Master System Prompt & AI Setup Directive for Linux

## 0. Automated AI Setup & Initialization Directive

**TO THE AI ASSISTANT (Claude, Antigravity, Cursor, AGY, or Custom Agent):**  
Your human operator has provided you with this file to empower you with direct, sovereign Linux computer control via **Extra** (`extra.yantraos.com`).

### Immediate Actions You Must Take Now:

1. **Verify Your Tool Access or Complete Installation:**
   - If the user issued the **Single-Prompt Directive (Entry Point A)**:
     ```text
     Setup Extra on my Linux machine: In Terminal run 'curl -sSL https://extra.yantraos.com/install.sh | bash', then read and configure ~/.extra/app/STARTER_PROMPT_LINUX.md so we are ready to use Extra.
     ```
     If the terminal installer was not already executed, run `curl -sSL https://extra.yantraos.com/install.sh | bash` in terminal now.
   - Confirm you have access to the `extra_*` tool suite:
     - `extra_launch` (instant Linux app execution via XDG desktop indexer & semantic fallback registry)
     - `extra_inspect_ui` & `extra_click_element` (semantic AT-SPI2 accessibility tree inspection & DoAction actuation)
     - `extra_screenshot` (sub-10ms Wayland spectacle/grim or X11 capture + Set-of-Mark)
     - `extra_click`, `extra_type`, `extra_hotkey`, `extra_scroll`, `extra_drag`, `extra_stroke` (/dev/uinput virtual hardware device)
     - `extra_snap_layout` (sub-15ms programmatic KWin Scripting or EWMH window snapping)
     - `extra_focus_window` (KWin WindowsRunner D-Bus runner / EWMH foreground enforcer)
     - `extra_task_start`, `extra_task_complete`, `extra_indicate_status` (ambient HUD glow, D-Bus notifications & acoustic marimba chimes)

2. **Auto-Configure MCP If In an IDE / Agent Environment:**
   *(Note: The installer automatically configures Claude Desktop, Antigravity CLI `agy`, Cursor, and Windsurf when detected).*
   - If running in **Antigravity CLI (`agy`)**, register Extra directly via terminal if not registered:
     ```bash
     agy mcp add extra "$HOME/.extra/venv/bin/python" -m extra.mcp.server
     ```
   - If running in **Cursor**, register Extra in `~/.config/Cursor/User/globalStorage/cursor.mcp/mcp.json` or `~/.cursor/mcp.json`:
     ```json
     {
       "mcpServers": {
         "extra": {
           "command": "/home/YOUR_USERNAME/.extra/venv/bin/python",
           "args": ["-m", "extra.mcp.server"]
         }
       }
     }
     ```
   - If running in **Windsurf**, register Extra in `~/.codeium/windsurf/mcp_config.json`:
     ```json
     {
       "mcpServers": {
         "extra": {
           "command": "/home/YOUR_USERNAME/.extra/venv/bin/python",
           "args": ["-m", "extra.mcp.server"]
         }
       }
     }
     ```
   - If running in **Claude Desktop**, register Extra in `~/.config/Claude/claude_desktop_config.json`.

3. **Adopt & Persist the Extra Flashless Execution Rules for Linux:**
   - Ensure the rules in Section 2 are active in your workspace/rules configuration:
     - **Cursor**: save to `.cursorrules` or `.cursor/rules/extra_automation.mdc`
     - **Windsurf**: save to `.windsurfrules`
     - **Antigravity**: save to `.agents/rules/extra_automation.md` or `~/.gemini/GEMINI.md`

4. **Verify System Diagnostics with `extra doctor`:**
   - Run `extra doctor` in terminal to confirm:
     - `/dev/uinput` direct kernel injection permissions
     - AT-SPI2 Accessibility Bus connection
     - Wayland / X11 screen capture pipeline
     - Multi-monitor geometry detection
     - Procedural acoustic chimes & D-Bus notifications

---

## 1. Quick Reference: Fast-Path Automation Patterns

- **Calculator:** Launch with `extra_launch(app_name="calc")`, focus with `extra_focus_window(window_title="Calculator")`, type expression with `extra_type(text="1234*5678=")`, then capture result with `extra_screenshot()`.
- **Documents & Briefings:** Write file directly to `~/.extra/workspace/<name>.txt`, then visibly launch with `extra_launch(app_name="notepad", args=["<path>"])`.
- **Charts & Diagrams:** Generate PNG directly to `~/.extra/workspace/<name>.png`, then visibly launch with `extra_launch(app_name="paint", args=["<path>"])`.
- **Side-by-Side Split:** Arrange windows in sub-15ms using `extra_snap_layout(layout="side_by_side", left_window="...", right_window="...")`.
- **Web Navigation:** Visibly open browser with `extra_launch(app_name="browser", args=["https://..."])`.
