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
  - `extra_focus_window`: `call_mcp_tool(ServerName="extra", ToolName="extra_focus_window", Arguments={"window_title": "<title>", "timeout": 3.0})` or `Arguments={"hwnd": <int>}`.
  - `extra_type`: `call_mcp_tool(ServerName="extra", ToolName="extra_type", Arguments={"text": "<string>", "press_enter": false})`
    Instant Win32 `KEYEVENTF_UNICODE` (`VK_PACKET`) typing.
  - `extra_hotkey`: `call_mcp_tool(ServerName="extra", ToolName="extra_hotkey", Arguments={"keys": ["win", "left"]})`
  - `extra_screenshot`: `call_mcp_tool(ServerName="extra", ToolName="extra_screenshot", Arguments={"annotate_ui": false, "save_to_file": true})`
  - `extra_inspect_ui`: `call_mcp_tool(ServerName="extra", ToolName="extra_inspect_ui", Arguments={"window_title": "<title>", "interactive_only": true, "max_elements": 50})`
  - `extra_click_element`: `call_mcp_tool(ServerName="extra", ToolName="extra_click_element", Arguments={"element_id": <int>})`
  - `extra_click`: `call_mcp_tool(ServerName="extra", ToolName="extra_click", Arguments={"x": <int>, "y": <int>, "button": "left"})`
  - `extra_scroll`: `call_mcp_tool(ServerName="extra", ToolName="extra_scroll", Arguments={"clicks": -5, "direction": "vertical"})` or `Arguments={"delta": -500, "horizontal": false}`.
  - `extra_drag`: `call_mcp_tool(ServerName="extra", ToolName="extra_drag", Arguments={"start_x": <int>, "start_y": <int>, "end_x": <int>, "end_y": <int>})`
  - `extra_browser`: `call_mcp_tool(ServerName="extra", ToolName="extra_browser", Arguments={"action": "navigate"|"content"|"click", "url": "..."})`
  - `extra_task_start`: `call_mcp_tool(ServerName="extra", ToolName="extra_task_start", Arguments={"task_name": "<name>"})`
    Activates ambient screen edge pulse and cursor halo.
  - `extra_task_complete`: `call_mcp_tool(ServerName="extra", ToolName="extra_task_complete", Arguments={"summary": "<summary>", "success": true})`
    Signals task completion: flashes emerald green border, plays acoustic chime, and dissolves indicators.
  - `extra_indicate_status`: `call_mcp_tool(ServerName="extra", ToolName="extra_indicate_status", Arguments={"status": "active"|"complete"|"idle", "message": "..."})`
  - `extra_recall_memory`: `call_mcp_tool(ServerName="extra", ToolName="extra_recall_memory", Arguments={"query": "<query>", "app_name": "<app>", "top_k": 3})`
    Recalls past task workflows, artifacts, and known quirks via KùzuDB + FastEmbed (< 3ms).
  - `extra_scout_app`: `call_mcp_tool(ServerName="extra", ToolName="extra_scout_app", Arguments={"app_name": "<app>", "force_refresh": false})`
    Discovers UI framework (Electron/Win32/Viewport), universal hotkeys, CLI flags, and generates SKILL.md.
  - `extra_evolve_skill`: `call_mcp_tool(ServerName="extra", ToolName="extra_evolve_skill", Arguments={"app_name": "<app>", "workflow_summary": "<summary>", "instructions": "<playbook>"})`
    Crystallizes newly verified zero-stall fast paths into permanent skill playbooks.
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
  4. NEVER pass `use_clipboard=true` in Calculator (Windows Calculator rejects clipboard paste with "Invalid input").
  5. NEVER call `extra_inspect_ui` to read the result. Call `extra_screenshot()` directly once to present the result.
- **Documents & Briefings (`notepad.exe`):**
  1. Write the document file directly to disk (`Path.write_text` or `write_to_file`) to avoid slow character-by-character typing.
     - **Safe Path:** ALWAYS save to `%USERPROFILE%\.extra\workspace\<name>.txt` or the active project folder. **NEVER** write to `%USERPROFILE%\Documents` (blocked by Windows Defender Controlled Folder Access).
  2. Visibly launch Notepad with the file: `extra_launch(app_name="notepad", args=["<absolute_path>"])`.
- **Diagrams & Charts (`mspaint.exe`):**
  1. Generate the clean, professional PNG image programmatically to disk via Python (`PIL`) or .NET.
     - **Safe Path:** ALWAYS save to `%USERPROFILE%\.extra\workspace\<name>.png`. **NEVER** write to `%USERPROFILE%\Pictures` (blocked by Windows Defender Controlled Folder Access).
  2. Visibly launch Paint to display the chart: `extra_launch(app_name="mspaint", args=["<absolute_path>"])`.
- **Canvas & Design Apps (Canva, Figma, Web-in-App / Electron):**
  1. **UI Architecture Understanding:**
     - Canva and Figma desktop applications are built on Electron.
     - Top navigation bars, search inputs, home screen category icons, and sidebars ARE standard web elements that CAN be interacted with via clicks, hotkeys, and searches.
     - Only the inner drawing canvas area (where individual shapes, vectors, and text layers sit) renders in an opaque HTML5/WebGL canvas that does not expose Win32 UIA accessibility nodes.
  2. **How to Create & Open Designs in Canva:**
     - **Primary (Most Reliable): Use Home Screen Category Icons or Search Bar:**
       - On the Canva home screen, click the visible category icons directly (e.g. "Presentation", "Instagram Post", "Doc", "Whiteboard") or click the prominent search box: *"What would you like to create?"* at the top of the home screen, type the desired format (e.g. "Instagram Post" or "Presentation"), and press Enter.
       - **CRITICAL CAVEAT ON `Ctrl + N`:** In Canva desktop, pressing `Ctrl + N` often defaults keyboard focus to the **"Open a design link:"** box at the bottom of the popup! DO NOT blindly type design names after pressing `Ctrl + N`. If you see "Please enter a valid design link", press `extra_hotkey(keys=["esc"])` once to dismiss the popup, and click the category icon or search box on the main home screen!
  3. **Honoring User Intent (Templates vs Custom Graphics):**
     - **When the user requests to use Canva templates:**
       - Search for the template in Canva's search bar or click "Templates" on the left navigation bar.
       - Select a template and use Canva's native tools. Do NOT fight the user's explicit request to use Canva templates.
     - **When generating custom graphics or high-speed posters (Fast-Path):**
       - You can generate high-resolution PNG assets programmatically to disk via Python (`PIL`) inside `%USERPROFILE%\.extra\workspace\<name>.png`.
       - Copy directly to the Windows Clipboard using PowerShell STA:
         `powershell -STA -Command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Clipboard]::SetImage([System.Drawing.Image]::FromFile('<safe_png_path>'))"`
       - Bring Canva to foreground (`extra_focus_window(window_title="Canva")`), click the canvas, and paste: `extra_hotkey(keys=["ctrl", "v"])`.
  4. Snap windows side-by-side (`win+left`, `win+right`).

- **File Explorer & Desktop Folders:**
  1. Create folders (`mkdir`) and move files on disk using filesystem commands (`shutil.move`) inside `%USERPROFILE%\.extra\workspace\` or the project root.
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
- **ZERO Modular Test Scripts:** NEVER write exploratory scripts (`test_photos.py`, `test_coords.py`, `check_fg.py`, `press_up.py`, `canvas_click.py`). Testing code across multiple files or trying to write `ctypes` mouse drivers wastes 4+ minutes. Perform actions directly with Extra MCP tools (`extra_click`, `extra_type`, `extra_hotkey`).
- **ZERO Panic Scripting & Error Looping:** If an application shows a validation error (such as "Please enter a valid design link" in Canva), NEVER get stuck in a tunnel-vision loop trying to type into the wrong box. Press `extra_hotkey(keys=["esc"])` once to dismiss the dialog, and check the web (`search_web`) or look at the main UI screen to find the correct button.
- **ZERO System Admin Rabbit Holes:**
  - If Windows Photos shows an error dialog (e.g. UWP file system error): send `extra_hotkey(keys=["esc"])` once to dismiss.
  - If Photos fails to display the image within 1 second, **FALL BACK IMMEDIATELY** to MS Paint: `extra_launch(app_name="mspaint", args=["<image_path>"])`.
  - **STRICT PROHIBITION:** NEVER run `Reset-AppxPackage`, never crawl Event Viewer logs (`Get-WinEvent`), never search the Windows Registry, and never attempt system-level UWP repairs.
- **ZERO Vision Pixel-Hunting:** Do NOT attempt 30–50 fragile vision-mouse clicks to find small buttons. Use keyboard shortcuts (`extra_hotkey`), text injection (`extra_type`), or direct launcher parameters.
- **Verification:** Call `extra_screenshot()` ONCE at the end to confirm the visual arrangement, then conclude immediately.

### 5. Windows Defender & Controlled Folder Access (CFA) Compliance
- **STRICT DIRECTORY BOUNDARY:** NEVER create files or directories directly in Windows protected user folders:
  - DO NOT write to `%USERPROFILE%\Documents`, `%USERPROFILE%\Pictures`, `%USERPROFILE%\Desktop`, `%USERPROFILE%\Videos`.
  - Windows Defender Controlled Folder Access (Ransomware Protection) strictly blocks `python.exe` and `cmd.exe` from modifying these folders (Event 1123) and triggers alarming security toast popups for the user.
- **MANDATORY SAFE WORKSPACE:** Always perform file creation, data extraction, reports, and diagram exports in:
  - `%USERPROFILE%\.extra\workspace\` (or the active project repository).
  - This folder is 100% exempt from CFA restrictions, guaranteeing zero Defender warnings, zero permission errors, and flawless visual presentation in Notepad, Paint, and Explorer.
