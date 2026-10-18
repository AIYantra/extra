---
trigger: always_on
description: Mandatory high-speed Linux desktop automation protocol whenever using Extra MCP tools (extra_*) or executing computer use on Linux.
---

## Extra Linux Desktop Automation Protocol

Whenever automating Linux desktop applications or executing computer use across Wayland (KDE KWin, GNOME Mutter, wlroots) or X11:

### 0. Zero-Schema-Lookup Direct Invocations (Speed Optimization)
- **DO NOT waste roundtrips reading tool schemas (`view_file` or `list_dir` on `mcp/extra/*.json`).**
- You already have the complete, verified argument schema for all `extra` MCP tools right here:
  - `extra_launch`: `call_mcp_tool(ServerName="extra", ToolName="extra_launch", Arguments={"app_name": "<name>", "args": [...]})`
    Common apps: `"calc"`, `"notepad"`, `"files"` / `"explorer"`, `"terminal"`, `"browser"` / `"chrome"` / `"chromium"`, `"paint"`, `"settings"`, or Linux URI handlers.
  - `extra_focus_window`: `call_mcp_tool(ServerName="extra", ToolName="extra_focus_window", Arguments={"window_title": "<title>", "timeout": 3.0})` or `Arguments={"hwnd": <int>}`.
    Sub-3ms window activation via KWin D-Bus runner / EWMH.
  - `extra_type`: `call_mcp_tool(ServerName="extra", ToolName="extra_type", Arguments={"text": "<string>", "press_enter": false})`
    Instant hardware event injection via `/dev/uinput` with terminal-aware atomic clipboard pasting (`Ctrl+Shift+V` for terminals vs `Ctrl+V` for GUI).
  - `extra_hotkey`: `call_mcp_tool(ServerName="extra", ToolName="extra_hotkey", Arguments={"keys": ["ctrl", "c"]})`
  - `extra_screenshot`: `call_mcp_tool(ServerName="extra", ToolName="extra_screenshot", Arguments={"annotate_ui": false, "save_to_file": true})`
    Multi-tier capture (`spectacle` for KDE Wayland, `grim` for wlroots, `mss` XShm for X11) with active window metadata.
  - `extra_snap_layout`: `call_mcp_tool(ServerName="extra", ToolName="extra_snap_layout", Arguments={"layout": "side_by_side", "left_window": "<title>", "right_window": "<title>"})`
    Sub-15ms programmatic window snapping via KWin Scripting on Wayland or xdotool/wmctrl on X11.
  - `extra_inspect_ui`: `call_mcp_tool(ServerName="extra", ToolName="extra_inspect_ui", Arguments={"window_title": "<title>", "interactive_only": true, "max_elements": 25})`
    Pure-Python AT-SPI2 accessibility tree inspection over Session D-Bus (< 15ms).
  - `extra_click_element`: `call_mcp_tool(ServerName="extra", ToolName="extra_click_element", Arguments={"element_id": <int>})`
    Sub-millisecond AT-SPI2 `DoAction(0)` semantic actuation with physical click fallback.
  - `extra_click`: `call_mcp_tool(ServerName="extra", ToolName="extra_click", Arguments={"x": <int>, "y": <int>, "button": "left"})`
  - `extra_stroke`: `call_mcp_tool(ServerName="extra", ToolName="extra_stroke", Arguments={"points": [[x1, y1], [x2, y2], ...], "duration": 0.5})`
  - `extra_scroll`: `call_mcp_tool(ServerName="extra", ToolName="extra_scroll", Arguments={"clicks": -5, "direction": "vertical"})`
  - `extra_drag`: `call_mcp_tool(ServerName="extra", ToolName="extra_drag", Arguments={"start_x": <int>, "start_y": <int>, "end_x": <int>, "end_y": <int>})`
  - `extra_browser`: `call_mcp_tool(ServerName="extra", ToolName="extra_browser", Arguments={"action": "navigate"|"content"|"click", "url": "..."})`
  - `extra_task_start`: `call_mcp_tool(ServerName="extra", ToolName="extra_task_start", Arguments={"task_name": "<name>"})`
    Activates ambient edge glow and plays synthesized acoustic chime.
  - `extra_task_complete`: `call_mcp_tool(ServerName="extra", ToolName="extra_task_complete", Arguments={"summary": "<summary>", "success": true})`
    Flashes emerald green border, plays multi-harmonic glass marimba chord, and sends desktop notification.
  - `extra_indicate_status`: `call_mcp_tool(ServerName="extra", ToolName="extra_indicate_status", Arguments={"status": "active"|"complete"|"idle", "message": "..."})`
- **Execute Immediately:** On Turn 1, jump directly to calling `call_mcp_tool(ServerName="extra", ...)` without calling `list_dir` or `view_file` on `mcp/extra/`.

### 1. The Live Desktop Pilot Mandate (ZERO Background Scripting)
- **Computer use MUST happen LIVE on the Linux desktop as a visible pilot.**
- **STRICT PROHIBITION:**
  - **NEVER** use `run_command` to execute background Python scripts (`pyautogui`, `xdotool`, `pynput`, `comtypes`) to automate GUI clicks or hunt for buttons invisibly.
  - Automate directly through the Extra MCP tools (`extra_launch`, `extra_click`, `extra_type`, `extra_hotkey`, `extra_snap_layout`).
- **Every application opened for the user MUST REMAIN OPEN AND VISIBLE.** NEVER call `.terminate()`, `kill`, or `killall` on apps requested to be opened.

### 2. High-Speed Hybrid Fast Paths (Zero-Stall Content Creation)
To prevent human-slow character typing while keeping apps 100% visible:
- **Calculator (`kcalc`, `gnome-calculator`, `galculator`):**
  1. `extra_launch(app_name="calc")`
  2. `extra_focus_window(window_title="Calculator")`
  3. `extra_type(text="<formula>=")` (e.g. `extra_type(text="245.12/383.29=")`)
  4. Call `extra_screenshot()` to visually present the calculation result.
- **Documents & Briefings (`kate`, `gedit`, `mousepad`):**
  1. Write the document file directly to disk in `~/.extra/workspace/<name>.txt` or the project directory.
  2. Visibly launch the editor: `extra_launch(app_name="notepad", args=["<absolute_path>"])`.
- **Diagrams & Charts (`kolourpaint`, `drawing`):**
  1. Generate clean PNG image programmatically to `~/.extra/workspace/<name>.png`.
  2. Visibly launch image viewer/editor: `extra_launch(app_name="paint", args=["<absolute_path>"])`.
- **File Manager (`dolphin`, `nautilus`, `thunar`):**
  1. Create folders or organize files on disk using filesystem operations.
  2. Visibly open folder: `extra_launch(app_name="files", args=["<folder_path>"])`.
- **Web Navigation (`browser`, `chromium`, `chrome`, `firefox`):**
  1. Visibly open URL: `extra_launch(app_name="browser", args=["https://..."])`.
  2. Chromium crash restore bubbles are automatically suppressed.
- **Side-by-Side Presentation:**
  1. Snap two windows side-by-side in one tool turn:
     `extra_snap_layout(layout="side_by_side", left_window="<left_app>", right_window="<right_app>")`
