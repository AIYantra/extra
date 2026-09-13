---
trigger: always_on
description: Mandatory high-speed Windows desktop automation protocol whenever using Extra MCP tools (extra_*) or executing computer use on Windows.
---

## Extra Windows Desktop Automation Protocol

Whenever automating Windows desktop applications or executing computer use:

### 0. Zero-Schema-Lookup Direct Invocations (Speed Optimization)
- **DO NOT waste roundtrips reading tool schemas (`view_file` or `list_dir` on `mcp/extra/*.json`).**
- You already have the complete, verified argument schema for all `extra` MCP tools right here:
  - `extra_launch`: `call_mcp_tool(ServerName="extra", ToolName="extra_launch", Arguments={"app_name": "<name>", "args": [...]})`
    Common apps: `"calc"`, `"notepad"`, `"mspaint"`, `"explorer"`, `"edge"`, or Windows URIs like `"ms-settings:"`.
  - `extra_focus_window`: `call_mcp_tool(ServerName="extra", ToolName="extra_focus_window", Arguments={"window_title": "<title>"})` or `Arguments={"hwnd": <int>}`.
  - `extra_type`: `call_mcp_tool(ServerName="extra", ToolName="extra_type", Arguments={"text": "<string>", "press_enter": false})`
    Instant Win32 `KEYEVENTF_UNICODE` (`VK_PACKET`) typing.
  - `extra_hotkey`: `call_mcp_tool(ServerName="extra", ToolName="extra_hotkey", Arguments={"keys": ["win", "left"]})`
  - `extra_screenshot`: `call_mcp_tool(ServerName="extra", ToolName="extra_screenshot", Arguments={"annotate_ui": false})`
  - `extra_inspect_ui`: `call_mcp_tool(ServerName="extra", ToolName="extra_inspect_ui", Arguments={"window_title": "<title>", "interactive_only": true, "max_elements": 50})`
  - `extra_click_element`: `call_mcp_tool(ServerName="extra", ToolName="extra_click_element", Arguments={"element_id": <int>})`
  - `extra_click`: `call_mcp_tool(ServerName="extra", ToolName="extra_click", Arguments={"x": <int>, "y": <int>, "button": "left"})`
  - `extra_scroll`: `call_mcp_tool(ServerName="extra", ToolName="extra_scroll", Arguments={"clicks": -5, "direction": "vertical"})`
  - `extra_drag`: `call_mcp_tool(ServerName="extra", ToolName="extra_drag", Arguments={"start_x": <int>, "start_y": <int>, "end_x": <int>, "end_y": <int>})`
  - `extra_browser`: `call_mcp_tool(ServerName="extra", ToolName="extra_browser", Arguments={"action": "navigate"|"content"|"click", "url": "..."})`
- **Execute Immediately:** On Turn 1, jump directly to calling `call_mcp_tool(ServerName="extra", ...)` without calling `list_dir` or `view_file` on `mcp/extra/`.

### 1. The Live Computer Use Mandate (NO Headless/Silent Execution)
- **Computer use MUST happen LIVE on the Windows desktop.**
- **DO NOT** encapsulate the desktop UI workflow into a headless background Python runner script that executes invisibly or closes apps.
- **DO USE Extra MCP tools directly** for all desktop interactions:
  - `extra_launch(app_name="...", args=[...])` to open apps visibly in the foreground.
  - `extra_focus_window(window_title="...")` to bring windows to the front.
  - `extra_type(text="...")` to enter formulas into Calculator or text into documents.
  - `extra_hotkey(keys=[...])` to snap windows and send keyboard shortcuts.
  - `extra_screenshot()` to visually verify and display the final desktop state.
- **Every application opened for the user MUST REMAIN OPEN AND VISIBLE.** NEVER call `.terminate()`, `kill`, or `taskkill` on apps that were requested to be opened.

### 2. High-Speed Hybrid Fast Paths (Zero-Stall Content Creation)
To prevent human-slow typing or sloppy freehand drawing while keeping the UI 100% visible:
- **Calculator (`calc.exe`):**
  1. `extra_launch(app_name="calc")`
  2. `extra_focus_window(window_title="Calculator")`
  3. `extra_type(text="<formula>=")` (e.g. `extra_type(text="245.12/383.29=")`) — calculations compute instantly on screen.
- **Documents & Briefings (`notepad.exe`):**
  1. Write the document file directly to disk (`Path.write_text` or `write_to_file`) to avoid slow character-by-character typing.
  2. Visibly launch Notepad with the file: `extra_launch(app_name="notepad", args=["<absolute_path>"])`.
- **Diagrams & Charts (`mspaint.exe`):**
  1. Generate the clean, professional PNG image programmatically to disk via Python (`PIL`) or .NET.
  2. Visibly launch Paint to display the chart: `extra_launch(app_name="mspaint", args=["<absolute_path>"])`.
- **File Explorer & Desktop Folders:**
  1. Create folders (`mkdir`) and move files on disk using filesystem commands (`shutil.move`).
  2. Visibly open the folder in Explorer: `extra_launch(app_name="explorer", args=["<folder_path>"])`.
- **Web Navigation & Financial Quotes (`edge`):**
  1. Visibly open Microsoft Edge to the quote URL: `extra_launch(app_name="edge", args=["https://www.google.com/finance/quote/NVDA:NASDAQ"])`.
  2. Use the live market numbers directly without reverse-engineering APIs.

### 3. Bulletproof Window Snapping (Side-by-Side Presentation)
- **NEVER** drag window title bars with mouse coordinates.
- In Windows 11, apps have tabs (Notepad tabs retain prior names). Never search for exact document file names in titles.
- **Snap Windows Using Native Hotkeys:**
  - **Left Half:**
    1. `extra_focus_window(window_title="Paint")` (or image viewer)
    2. `extra_hotkey(keys=["win", "left"])`
    3. `extra_hotkey(keys=["esc"])` (dismisses Windows 11 Snap Assist menu)
  - **Right Half:**
    1. `extra_focus_window(window_title="Notepad")`
    2. `extra_hotkey(keys=["win", "right"])`
    3. `extra_hotkey(keys=["esc"])` (dismisses Windows 11 Snap Assist menu)

### 4. Strict Anti-Stall Guardrails (ZERO Rabbit Holes, ZERO Test Scripts)
- **ZERO Modular Test Scripts:** NEVER write exploratory scripts (`test_photos.py`, `test_coords.py`, `test_quotes.py`, `check_modules.py`). Testing code across multiple files wastes 4+ minutes. Perform actions directly.
- **ZERO System Admin Rabbit Holes:**
  - If Windows Photos shows an error dialog (e.g. UWP file system error): send `extra_hotkey(keys=["esc"])` once to dismiss.
  - If Photos fails to display the image within 1 second, **FALL BACK IMMEDIATELY** to MS Paint: `extra_launch(app_name="mspaint", args=["<image_path>"])`.
  - **STRICT PROHIBITION:** NEVER run `Reset-AppxPackage`, never crawl Event Viewer logs (`Get-WinEvent`), never search the Windows Registry, and never attempt system-level UWP repairs.
- **ZERO Vision Pixel-Hunting:** Do NOT attempt 30–50 fragile vision-mouse clicks to find small buttons. Use keyboard shortcuts (`extra_hotkey`), text injection (`extra_type`), or direct launcher parameters.
- **Verification:** Call `extra_screenshot()` ONCE at the end to confirm the visual arrangement, then conclude immediately.
