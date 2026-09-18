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
  - `extra_batch_actions`: `call_mcp_tool(ServerName="extra", ToolName="extra_batch_actions", Arguments={"actions": [{"action": "click"|"type"|"hotkey"|"sleep"|"focus"|"scroll", ...}]})`
    Executes an atomic list of hardware actions sequentially with sub-millisecond dispatch in a single turn.
  - `extra_snap_layout`: `call_mcp_tool(ServerName="extra", ToolName="extra_snap_layout", Arguments={"layout": "side_by_side", "left_window": "<title>", "right_window": "<title>"})`
    Instantly arranges and sizes windows into side-by-side or split layouts in 15ms via Win32 `SetWindowPos`, eliminating multi-turn hotkey loops.
  - `extra_fs_batch`: `call_mcp_tool(ServerName="extra", ToolName="extra_fs_batch", Arguments={"operation": "organize"|"create_tree"|"batch_rename"|"batch_delete", ...})`
    Atomic, high-speed batch filesystem operations avoiding multi-turn shell commands while remaining 100% compliant with Windows Defender Controlled Folder Access.
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
  - `extra_batch_actions(actions=[...])` to execute compound hardware actions in a single turn.
  - `extra_snap_layout(...)` to snap and arrange windows cleanly in sub-15ms.
  - `extra_type(text="...")` to enter formulas into Calculator or text into documents.
  - `extra_hotkey(keys=[...])` to send keyboard shortcuts.
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
  4. Snap windows side-by-side using `extra_snap_layout(layout="side_by_side", ...)`.

- **File Explorer & Desktop Folders:**
  1. Use `extra_fs_batch` or filesystem commands (`shutil.move`) inside `%USERPROFILE%\.extra\workspace\` or the project root.
  2. Visibly open the folder in Explorer: `extra_launch(app_name="explorer", args=["<folder_path>"])`.
- **Web Navigation & Browser Workflows (`edge`):**
  1. Visibly open Microsoft Edge to URLs: `extra_launch(app_name="edge", args=["https://..."])`.
  2. Use live market numbers directly without reverse-engineering APIs.
  3. **Multi-Tab Launch & Bookmarking Fast Path:**
     - Open multiple tabs in a single launcher call: `extra_launch(app_name="edge", args=["<url1>", "<url2>", "<url3>"])`.
     - **Browser Initialization Settle Delay:** Browsers spawn multiple renderer and GPU processes. Always include an initial settle sleep of at least 1500–2000ms before sending window/dialog keystrokes.
     - **Bookmark All Open Tabs into a Folder:**
       Execute via `extra_batch_actions`:
       ```json
       [
         {"action": "focus", "window_title": "Edge"},
         {"action": "sleep", "ms": 1500},
         {"action": "hotkey", "keys": ["ctrl", "shift", "d"]},
         {"action": "sleep", "ms": 800},
         {"action": "type", "text": "<FolderName>", "press_enter": true},
         {"action": "sleep", "ms": 500}
       ]
       ```
     - **NEVER Mix `Ctrl+D` with `Ctrl+Shift+D`:** `Ctrl+D` bookmarks ONLY the single active foreground tab, creating loose, duplicate bookmark entries on the root Favorites bar. `Ctrl+Shift+D` bookmarks all open tabs into a dedicated folder.
  4. **Managing & Reverting Bookmarks / Favorites:**
     - **UI Fast Path (Mandatory for Running Browsers):**
       - Press `extra_hotkey(keys=["ctrl", "shift", "o"])` to open Edge's Favorites flyout, type the folder/bookmark name to select it, and send `extra_hotkey(keys=["delete"])`. Or right-click and click "Delete" via `extra_batch_actions`.
       - Alternatively, navigate to `edge://favorites`.
     - **CRITICAL: In-Memory Browser Lock:** Modern browsers (Edge, Chrome) keep bookmarks in memory while running. NEVER write to `AppData\...\Bookmarks` JSON files on disk while `msedge.exe` is running; the browser will silently overwrite the disk file on exit/sync and restore the bookmarks!
     - **Disk Cleanup Path:** If deleting browser data on disk, you MUST terminate all browser processes first (`powershell -Command "Stop-Process -Name msedge -Force"`), modify the file, and then verify.

### 3. Bulletproof Window Snapping (Side-by-Side Presentation)
- **NEVER** drag window title bars with mouse coordinates.
- In Windows 11, apps have tabs (Notepad tabs retain prior names). Never search for exact document file names in titles.
- **Primary & Fastest (15ms, 1 Tool Turn): Programmatic Snap Layout**
  - `extra_snap_layout(layout="side_by_side", left_window="Paint", right_window="Notepad")`
  - Win32 `SetWindowPos` directly resizes and docks both windows with sub-millisecond precision, completely eliminating the Windows 11 Snap Assist menu.
- **Fallback (Hotkeys):**
  - **Left Half:**
    1. `extra_focus_window(window_title="Paint")`
    2. `extra_hotkey(keys=["win", "left"])`
    3. `extra_hotkey(keys=["esc"])` (dismisses Windows 11 Snap Assist menu)
  - **Right Half:**
    1. `extra_focus_window(window_title="Notepad")`
    2. `extra_hotkey(keys=["win", "right"])`
    3. `extra_hotkey(keys=["esc"])` (dismisses Windows 11 Snap Assist menu)

### 4. Strict Anti-Stall Guardrails (ZERO Rabbit Holes, ZERO Test Scripts)
- **ZERO Double-Hop Vision (10s Latency Tax Prohibition):**
  - When calling `extra_screenshot()`, the image is captured and written to disk.
  - **NEVER** follow `extra_screenshot()` with `view_file` on the resulting PNG file path.
  - Calling `view_file` burns 8–12 seconds loading binary image data into context and forces a redundant LLM turn.
  - Call `extra_screenshot()` ONCE at the conclusion of your task to provide visual verification for the user, then conclude your turn immediately.
- **ZERO Ad-Hoc Vision Scripts (PIL / NumPy Pixel-Hunting Prohibition):**
  - **STRICT PROHIBITION:** NEVER write Python scripts using `PIL`, `numpy`, or `cv2` to crop screenshot sub-images, calculate RGB pixel differences, do brightness thresholding, or search for button text in image matrices.
  - Writing 10+ vision scripts and calling `view_file` on image crops (`fav_bar.png`, `button.png`, `delete_opt.png`) creates an unacceptable 15-minute stall loop.
  - Find controls using native hotkeys (`Ctrl+Shift+O`, `Ctrl+F`, `Tab`), direct URL navigation (`edge://favorites`), or semantic accessibility inspection (`extra_inspect_ui`).
- **ZERO False-Positive Disk Verifications:**
  - When undoing or changing state in an application (browser bookmarks, document edits, app preferences), NEVER claim the task is complete merely because a disk file was edited if the application is still running in memory. Verify the live application window or verify with the application closed.
- **ZERO Unconstrained Directory Crawls:**
  - NEVER run recursive `os.walk` or unconstrained grep across entire `AppData\Local\` or browser `User Data` directories. These directories contain gigabytes of binary cache and database files that will hang background tasks. Target exact known file paths only.
- **MANDATORY Compound Batch Actions:**
  - When performing multiple sequential actions (e.g. focusing an app, clicking a search bar, typing text, pressing enter, and sleeping), ALWAYS bundle them into `extra_batch_actions` instead of serial single-action turns.
- **ZERO Modular Test Scripts:** NEVER write exploratory scripts (`test_photos.py`, `test_coords.py`, `check_fg.py`, `press_up.py`, `canvas_click.py`). Testing code across multiple files or trying to write `ctypes` mouse drivers wastes 4+ minutes. Perform actions directly with Extra MCP tools (`extra_click`, `extra_type`, `extra_hotkey`, `extra_batch_actions`).
- **ZERO Panic Scripting & Error Looping:** If an application shows a validation error (such as "Please enter a valid design link" in Canva), NEVER get stuck in a tunnel-vision loop trying to type into the wrong box. Press `extra_hotkey(keys=["esc"])` once to dismiss the dialog, and check the web (`search_web`) or look at the main UI screen to find the correct button.
- **ZERO System Admin Rabbit Holes:**
  - If Windows Photos shows an error dialog (e.g. UWP file system error): send `extra_hotkey(keys=["esc"])` once to dismiss.
  - If Photos fails to display the image within 1 second, **FALL BACK IMMEDIATELY** to MS Paint: `extra_launch(app_name="mspaint", args=["<image_path>"])`.
  - **STRICT PROHIBITION:** NEVER run `Reset-AppxPackage`, never crawl Event Viewer logs (`Get-WinEvent`), never search the Windows Registry, and never attempt system-level UWP repairs.
- **ZERO Accessibility Dump Paging:**
  - When `extra_inspect_ui` outputs a large response saved to an artifact file (`.system_generated/.../output.txt`), **NEVER** call `view_file` repeatedly across multiple slices to page through hundreds of lines of accessibility tree text.
  - Paging through UI tree dumps burns 30–60 seconds and bloats context. Target controls using native application shortcuts (`Ctrl+Shift+D`, `Ctrl+Shift+O`, `Ctrl+T`, `Tab`, `Enter`), direct URLs, or limit `max_elements=15`.
- **ZERO Window HWND Hunting Scripts:**
  - NEVER run PowerShell / C# P/Invoke scripts (`GetForegroundWindow`, `EnumWindows`, `GetWindowText`, `Get-Process`) to search for window handles.
  - Re-focus cleanly using `extra_focus_window(window_title="<AppName>")` or click the window directly.
- **STRICT ANTI-BLIND COMPLETION MANDATE (Sequential Verification):**
  - **NEVER call `extra_task_complete` in the same tool turn as `extra_screenshot`.**
  - Calling `extra_screenshot` and `extra_task_complete` simultaneously forces the model to claim completion blindly without ever receiving or inspecting the verification visual state.
  - **Mandatory 2-Step Verification Sequence:**
    1. Turn N: Execute your final UI action and call `extra_screenshot()` (or inspect via `extra_inspect_ui`). Conclude your tool calls for that turn.
    2. Turn N+1: Receive the screenshot / inspection output, visually verify that the expected UI elements and content actually exist. Only then call `extra_task_complete(summary="...", success=true)` and present your response to the user.
    3. If the verification reveals missing elements (e.g. bookmarks dialog didn't take, text didn't paste), take corrective action—DO NOT claim completion!

### 5. Windows Defender & Controlled Folder Access (CFA) Compliance
- **STRICT DIRECTORY BOUNDARY:** NEVER create files or directories directly in Windows protected user folders:
  - DO NOT write to `%USERPROFILE%\Documents`, `%USERPROFILE%\Pictures`, `%USERPROFILE%\Desktop`, `%USERPROFILE%\Videos`.
  - Windows Defender Controlled Folder Access (Ransomware Protection) strictly blocks `python.exe` and `cmd.exe` from modifying these folders (Event 1123) and triggers alarming security toast popups for the user.
- **MANDATORY SAFE WORKSPACE:** Always perform file creation, data extraction, reports, and diagram exports in:
  - `%USERPROFILE%\.extra\workspace\` (or the active project repository).
  - This folder is 100% exempt from CFA restrictions, guaranteeing zero Defender warnings, zero permission errors, and flawless visual presentation in Notepad, Paint, and Explorer.
