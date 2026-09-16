---
trigger: always_on
description: Mandatory high-speed macOS desktop automation protocol whenever using Extra MCP tools (extra_*) or executing computer use on macOS.
---

## Extra macOS Desktop Automation Protocol

Whenever automating macOS desktop applications or executing computer use:

### 0. Zero-Schema-Lookup Direct Invocations (Speed Optimization)
- **DO NOT waste roundtrips reading tool schemas (`view_file` or `list_dir` on `mcp/extra/*.json`).**
- You already have the complete, verified argument schema for all `extra` MCP tools right here:
  - `extra_launch`: `call_mcp_tool(ServerName="extra", ToolName="extra_launch", Arguments={"app_name": "<name>", "args": [...]})`
    Common apps: `"calc"`, `"notepad"` / `"textedit"`, `"paint"` / `"preview"`, `"explorer"` / `"finder"`, `"terminal"`, `"safari"`, `"chrome"`, `"edge"`, or macOS URIs.
  - `extra_focus_window`: `call_mcp_tool(ServerName="extra", ToolName="extra_focus_window", Arguments={"window_title": "<title>", "timeout": 3.0})` or `Arguments={"hwnd": <int>}`.
  - `extra_type`: `call_mcp_tool(ServerName="extra", ToolName="extra_type", Arguments={"text": "<string>", "press_enter": false})`
    Instant UTF-16 Unicode injection via CoreGraphics event taps.
  - `extra_hotkey`: `call_mcp_tool(ServerName="extra", ToolName="extra_hotkey", Arguments={"keys": ["cmd", "c"]})`
  - `extra_screenshot`: `call_mcp_tool(ServerName="extra", ToolName="extra_screenshot", Arguments={"annotate_ui": false, "save_to_file": true})`
  - `extra_inspect_ui`: `call_mcp_tool(ServerName="extra", ToolName="extra_inspect_ui", Arguments={"interactive_only": true, "max_elements": 50})`
  - `extra_click_element`: `call_mcp_tool(ServerName="extra", ToolName="extra_click_element", Arguments={"element_id": <int>})`
  - `extra_click`: `call_mcp_tool(ServerName="extra", ToolName="extra_click", Arguments={"x": <int>, "y": <int>, "button": "left"})`
  - `extra_scroll`: `call_mcp_tool(ServerName="extra", ToolName="extra_scroll", Arguments={"clicks": -5, "direction": "vertical"})`
  - `extra_drag`: `call_mcp_tool(ServerName="extra", ToolName="extra_drag", Arguments={"start_x": <int>, "start_y": <int>, "end_x": <int>, "end_y": <int>})`
  - `extra_browser`: `call_mcp_tool(ServerName="extra", ToolName="extra_browser", Arguments={"action": "navigate"|"content"|"click", "url": "..."})`
  - `extra_task_start`: `call_mcp_tool(ServerName="extra", ToolName="extra_task_start", Arguments={"task_name": "<name>"})`
    Activates ambient screen edge pulse and cursor halo.
  - `extra_task_complete`: `call_mcp_tool(ServerName="extra", ToolName="extra_task_complete", Arguments={"summary": "<summary>", "success": true})`
    Signals task completion: flashes emerald green border, plays acoustic chime, and dissolves indicators.
  - `extra_indicate_status`: `call_mcp_tool(ServerName="extra", ToolName="extra_indicate_status", Arguments={"status": "active"|"complete"|"idle", "message": "..."})`
- **Execute Immediately:** On Turn 1, jump directly to calling `call_mcp_tool(ServerName="extra", ...)` without calling `list_dir` or `view_file` on `mcp/extra/`.

### 1. The Live Computer Use Mandate (NO Headless/Silent Execution)
- **Computer use MUST happen LIVE on the macOS desktop.**
- **DO NOT** encapsulate the desktop UI workflow into a headless background Python runner script that executes invisibly or closes apps.
- **DO USE Extra MCP tools directly** for all desktop interactions:
  - `extra_launch(app_name="...", args=[...])` to open apps visibly in the foreground.
  - `extra_focus_window(window_title="...")` to bring windows to the front.
  - `extra_type(text="...")` to enter formulas into Calculator or text into documents.
  - `extra_hotkey(keys=[...])` to send keyboard shortcuts.
  - `extra_screenshot()` to visually verify and display the final desktop state.
- **Every application opened for the user MUST REMAIN OPEN AND VISIBLE.** NEVER call `.terminate()`, `kill`, or `pkill` on apps that were requested to be opened.

### 2. High-Speed Hybrid Fast Paths (Zero-Stall Content Creation)
To prevent human-slow typing or awkward UI manipulation while keeping apps 100% visible:
- **Calculator (`Calculator.app`):**
  1. `extra_launch(app_name="calc")`
  2. `extra_focus_window(window_title="Calculator")`
  3. `extra_type(text="<formula>=")` (e.g. `extra_type(text="245.12/383.29=")`) — calculations compute instantly on screen.
  4. NEVER call `extra_inspect_ui` to read the result. Call `extra_screenshot()` directly once to present the result.
- **Documents & Briefings (`TextEdit.app`):**
  1. Write the document file directly to disk (`Path.write_text` or `write_to_file`) to avoid slow character-by-character typing.
  2. Visibly launch TextEdit with the file: `extra_launch(app_name="textedit", args=["<absolute_path>"])`.
- **Diagrams & Charts (`Preview.app`):**
  1. Generate the clean, professional PNG image programmatically to disk via Python (`PIL`) or matplotlib.
  2. Visibly launch Preview to display the chart: `extra_launch(app_name="preview", args=["<absolute_path>"])`.
- **Finder & Desktop Folders:**
  1. Create folders (`mkdir`) and move files on disk using filesystem commands (`shutil.move`).
  2. Visibly open the folder in Finder: `extra_launch(app_name="finder", args=["<folder_path>"])`.
- **Web Navigation & Financial Quotes (`safari` or `chrome`):**
  1. Visibly open browser to URL: `extra_launch(app_name="safari", args=["https://www.google.com/finance/quote/NVDA:NASDAQ"])`.
  2. Use the live market numbers directly without reverse-engineering APIs.

### 3. Keyboard Shortcuts & Modifiers (macOS Specific)
- Always use `cmd` instead of `ctrl` for standard shortcuts:
  - Copy: `extra_hotkey(keys=["cmd", "c"])`
  - Paste: `extra_hotkey(keys=["cmd", "v"])`
  - Select All: `extra_hotkey(keys=["cmd", "a"])`
  - Save: `extra_hotkey(keys=["cmd", "s"])`
  - Close Window: `extra_hotkey(keys=["cmd", "w"])`
  - Quit App: `extra_hotkey(keys=["cmd", "q"])`

### 4. Strict Anti-Stall Guardrails (ZERO Rabbit Holes, ZERO Test Scripts)
- **ZERO Modular Test Scripts:** NEVER write exploratory test scripts. Perform actions directly.
- **ZERO Vision Pixel-Hunting:** Do NOT attempt 30–50 fragile vision-mouse clicks to find small buttons. Use semantic targeting (`extra_inspect_ui` / `extra_click_element`), keyboard shortcuts (`extra_hotkey`), or text injection (`extra_type`).
- **Verification:** Call `extra_screenshot()` ONCE at the end to confirm the visual arrangement, then conclude immediately.
