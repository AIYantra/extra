---
name: extra-automation
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
  - `extra_batch_actions`: `call_mcp_tool(ServerName="extra", ToolName="extra_batch_actions", Arguments={"actions": [{"action": "click"|"type"|"hotkey"|"sleep"|"focus"|"scroll"|"stroke"|"drag", ...}], "auto_settle": true, "strict_ink": false})`
    Executes an atomic list of hardware actions sequentially with sub-millisecond dispatch and Tier 1 visual settle in a single turn. Now natively supports 'drag' (start_x, start_y, end_x, end_y) and canvas_relative=True.
  - `extra_subtask_run`: `call_mcp_tool(ServerName="extra", ToolName="extra_subtask_run", Arguments={"intent": "<intent_description>", "expected_elements": [...]})`
    Executes closed-loop micro-routines (e.g. calculation, app launching, web search, window snapping, clipboard copying) with on-device SOUL-Critic validation in 1 turn (< 50ms).
  - `extra_snap_layout`: `call_mcp_tool(ServerName="extra", ToolName="extra_snap_layout", Arguments={"layout": "side_by_side"|"thirds"|"grid", "left_window": "<title>", "right_window": "<title>", "center_window": "<title>", "windows": [...]})`
    Instantly arranges and sizes windows into side-by-side, thirds (3 columns), or 2x2 grid layouts in 15ms via Win32 `SetWindowPos`, eliminating multi-turn hotkey loops.
  - `extra_fs_batch`: `call_mcp_tool(ServerName="extra", ToolName="extra_fs_batch", Arguments={"operation": "organize"|"create_tree"|"batch_rename"|"batch_delete", ...})`
    Atomic, high-speed batch filesystem operations avoiding multi-turn shell commands while remaining 100% compliant with Windows Defender Controlled Folder Access.
  - `extra_inspect_ui`: `call_mcp_tool(ServerName="extra", ToolName="extra_inspect_ui", Arguments={"window_title": "<title>", "interactive_only": true, "max_elements": 15})`
  - `extra_click_element`: `call_mcp_tool(ServerName="extra", ToolName="extra_click_element", Arguments={"query": "<target_label>"})` (SOUL-Eyes grounding) or `Arguments={"element_id": <int>}`.
  - `extra_click`: `call_mcp_tool(ServerName="extra", ToolName="extra_click", Arguments={"target": "<semantic_name>", "button": "left"})` (Zero-Coordinate SOUL-Eyes Visual Grounding) or `Arguments={"x": <int>, "y": <int>, "button": "left", "canvas_relative": false}`.
  - `extra_soul_wait`: `call_mcp_tool(ServerName="extra", ToolName="extra_soul_wait", Arguments={"condition": "settled"|"change", "timeout_sec": 4.0})`
    Sub-15ms visual settle detection via SOUL-Gateman. ALWAYS prefer this over blind arbitrary `sleep` ms delays!
  - `extra_scroll`: `call_mcp_tool(ServerName="extra", ToolName="extra_scroll", Arguments={"clicks": -5, "direction": "vertical"})` or `Arguments={"delta": -500, "horizontal": false}`.
  - `extra_drag`: `call_mcp_tool(ServerName="extra", ToolName="extra_drag", Arguments={"start_x": <int>, "start_y": <int>, "end_x": <int>, "end_y": <int>, "canvas_relative": false})`
  - `extra_browser`: `call_mcp_tool(ServerName="extra", ToolName="extra_browser", Arguments={"action": "navigate"|"content"|"click"|"settle", "url": "..."})`
  - `extra_task_start`: `call_mcp_tool(ServerName="extra", ToolName="extra_task_start", Arguments={"task_name": "<name>"})`
    Activates ambient screen edge pulse and cursor halo.
  - `extra_task_complete`: `call_mcp_tool(ServerName="extra", ToolName="extra_task_complete", Arguments={"summary": "<summary>", "success": true})`
    Signals task completion: flashes emerald green border, plays acoustic chime, and dissolves indicators.
  - `extra_indicate_status`: `call_mcp_tool(ServerName="extra", ToolName="extra_indicate_status", Arguments={"status": "active"|"complete"|"idle", "message": "..."})`
  - `extra_recall_memory`: `call_mcp_tool(ServerName="extra", ToolName="extra_recall_memory", Arguments={"query": "<query>", "app_name": "<app>", "top_k": 3})`
    Recalls past task workflows, artifacts, and known quirks via KùzuDB + FastEmbed (< 3ms).
  - `extra_mouse_move`: `call_mcp_tool(ServerName="extra", ToolName="extra_mouse_move", Arguments={"x": <int>, "y": <int>, "duration": 0.5, "human_like": true})`
    Dispatches standalone, human-like Bezier cursor flight across the screen without clicking.
  - `extra_stroke`: `call_mcp_tool(ServerName="extra", ToolName="extra_stroke", Arguments={"points": [[x1, y1], [x2, y2], ...], "duration": 0.8, "brush_size": 2, "smooth": true, "canvas_relative": false})`
    Renders continuous vector brush/ink strokes live on canvas with automatic SOUL ink-detection. Supports canvas_relative=True.

  - `extra_blueprint_start`: `call_mcp_tool(ServerName="extra", ToolName="extra_blueprint_start", Arguments={"title": "<title>", "task_type": "general", "milestones": [{"id": "m1", "name": "...", "dependencies": []}]})`
    Initializes long-horizon Task Blueprint with DAG milestones and HIPIF context folding.
  - `extra_blueprint_milestone`: `call_mcp_tool(ServerName="extra", ToolName="extra_blueprint_milestone", Arguments={"task_id": "<id>", "milestone_id": "<id>", "action": "complete", "summary": "...", "result": {...}})`
    Updates milestone state and folds execution context into dense semantic state tokens.
  - `extra_execute_bridge`: `call_mcp_tool(ServerName="extra", ToolName="extra_execute_bridge", Arguments={"runtime": "python"|"powershell"|"blender_bpy", "payload": "<code>", "timeout_sec": 60.0})`
    Deterministic local code execution (Plane 2) avoiding multi-turn GUI guesswork.
  - `extra_curate_skills`: `call_mcp_tool(ServerName="extra", ToolName="extra_curate_skills", Arguments={"sanitize": false})`
    Audits active skills catalog and strips legacy or unhardened mock playbooks.
  - `extra_scout_app`: `call_mcp_tool(ServerName="extra", ToolName="extra_scout_app", Arguments={"app_name": "<app>", "force_refresh": false})`
    Discovers UI framework (Electron/Win32/Viewport), universal hotkeys, CLI flags, and generates SKILL.md.
  - `extra_evolve_skill`: `call_mcp_tool(ServerName="extra", ToolName="extra_evolve_skill", Arguments={"app_name": "<app>", "workflow_summary": "<summary>", "instructions": "<playbook>"})`
    Crystallizes newly verified zero-stall fast paths into permanent skill playbooks.
  - `extra_harness_synthesize`: `call_mcp_tool(ServerName="extra", ToolName="extra_harness_synthesize", Arguments={"software_path_or_repo": "<path_or_repo>", "output_dir": "<path>", "phase_target": "all"})`
    Synthesizes compliant 7-phase CLI agent harness SOP, tests, and CLI wrappers.
  - `extra_harness_run`: `call_mcp_tool(ServerName="extra", ToolName="extra_harness_run", Arguments={"harness": "<name>", "command": ["<subcommand>", "..."], "json_output": true, "auto_visualize": true})`
    Executes CLI harness commands with automatic dual-plane visualization and JSON structured output.
  - `extra_hub_manage`: `call_mcp_tool(ServerName="extra", ToolName="extra_hub_manage", Arguments={"action": "list"|"info"|"register", "harness_name": "<name>"})`
    Manages active CLI harnesses across the ecosystem.
  - `extra_workspace_export`: `call_mcp_tool(ServerName="extra", ToolName="extra_workspace_export", Arguments={"workspace_dir": "<path>", "archive_name": "<name.zip>"})` or `Arguments={"url_or_id": "<url_or_id>", "output_path": "<path>", "export_format": "pdf"}`
    Exports authenticated web documents (Docs/Sheets/Slides) or packages local workspace directory into zip archives.
  - `extra_verify_lineage`: `call_mcp_tool(ServerName="extra", ToolName="extra_verify_lineage", Arguments={"file_path": "<path>"|"workspace_path": "<dir>", "expected_origin": "official_web_export"|"application_export"|"cli_harness"})`
    Verifies cryptographic provenance and physical lineage of deliverables.
  - `extra_verify_state`: `call_mcp_tool(ServerName="extra", ToolName="extra_verify_state", Arguments={"window_title": "<title>", "claims": {...}, "expected_tabs": <int>, "expected_slides": <int>, "min_words": <int>})`
    Decoupled ground-truth state auditor directly inspecting DOM and accessibility trees to prevent epistemic drift.
  - `extra_child_session_status`: `call_mcp_tool(ServerName="extra", ToolName="extra_child_session_status", Arguments={"action": "list"|"status", "session_id": "..."})`
    Monitors background child worker sessions and health telemetry.
  - `extra_pip_control`: `call_mcp_tool(ServerName="extra", ToolName="extra_pip_control", Arguments={"action": "show"|"hide"|"status"})`
    Controls desktop picture-in-picture viewport.
  - `extra_translate_screen`: `call_mcp_tool(ServerName="extra", ToolName="extra_translate_screen", Arguments={"x": <int>, "y": <int>})`
    Translates visual screen coordinates across DPI virtual desk scaling.
- **Execute Immediately:** On Turn 1, jump directly to calling `call_mcp_tool(ServerName="extra", ...)` without calling `list_dir` or `view_file` on `mcp/extra/`.

### 0.1 Mandatory Action Chunking Protocol (Zero-Single-Action Turns)
- **STRICT PROHIBITION: NEVER dispatch single-action turns when a deterministic sequence of 2+ actions is known.**
  - Splitting trivial actions across separate turns (Turn 1: `extra_launch`, Turn 2: `extra_focus_window`, Turn 3: `extra_type`, Turn 4: `extra_screenshot`) wastes 15–30 seconds of user waiting time and burns hundreds of prompt tokens.
  - **MANDATORY**: Whenever executing predictable sequences, batch them into a **SINGLE tool call** using:
    1. `extra_subtask_run(intent="...")` — Uses the Universal Macro Intent Compiler to autonomously execute micro-routines (e.g. calculation, app launching, web search, window snapping, clipboard copying) with on-device SOUL-Critic validation in 1 turn (< 50ms).
    2. `extra_batch_actions(actions=[...], auto_settle=True)` — Executes an atomic list of hardware actions sequentially with sub-millisecond dispatch and automatic visual settle observation.
- **ZERO REDUNDANT SCREENSHOT PROHIBITION:**
  - **NEVER call `extra_screenshot` immediately after actions that already return `distilled_ui`** (e.g. `extra_screenshot`, `extra_click`, `extra_type`, `extra_batch_actions`, or `extra_subtask_run`).
  - `distilled_ui` already provides active window title, focused control, and interactive elements. Calling `extra_screenshot()` just to "verify" what was already returned in `distilled_ui` is a prohibited turn waste.
- **COMMON 1-TURN MACRO FAST PATHS:**
  - **Math / Calculations:**
    `call_mcp_tool(ServerName="extra", ToolName="extra_subtask_run", Arguments={"intent": "calculate 245.12/383.29="})`
    Or `extra_batch_actions(actions=[{"action": "launch", "app": "calc"}, {"action": "focus", "window_title": "Calculator"}, {"action": "type", "text": "245.12/383.29="}])` — Exactly 1 turn!
  - **Notes / Briefings in Notepad:**
    Write file to `%USERPROFILE%\.extra\workspace\<filename>.txt` first via file tools, then call `extra_launch(app_name="notepad", args=["<path>"])`. Exactly 1 turn!
  - **Window Snapping & Layouts:**
    `call_mcp_tool(ServerName="extra", ToolName="extra_snap_layout", Arguments={"layout": "side_by_side", "left_window": "Calculator", "right_window": "Notepad"})` — Exactly 1 turn (< 15ms)!
  - **Web Search & Navigation:**
    `call_mcp_tool(ServerName="extra", ToolName="extra_subtask_run", Arguments={"intent": "search youtube for lofi hip hop"})`
    Or `extra_browser(action="navigate", url=...)`. Exactly 1 turn!
  - **Select All & Copy:**
    `call_mcp_tool(ServerName="extra", ToolName="extra_subtask_run", Arguments={"intent": "copy all text in active window"})` — Exactly 1 turn with clipboard captured!

### 0.2 Zero-Hop Perception Protocol (Strict Prohibition of Redundant `view_file` Calls)
- **STRICT PROHIBITION: NEVER call `view_file` on `screenshot_*.png` after calling `extra_screenshot`, `extra_click`, `extra_type`, or `extra_batch_actions`.**
  - Calling `view_file` on screenshot images wastes 8 to 12 seconds per turn and inflates turn counts by over 50%.
  - `extra_screenshot`, `extra_click`, and `extra_batch_actions` automatically return `distilled_ui` directly in their JSON response payload.
  - `distilled_ui` contains the full active window title, focused elements, buttons, text inputs, and exact interactive coordinates in an ultra-dense, token-optimized textual format (< 10ms).
  - **Read the UI directly from `distilled_ui` in the tool response.**
  - **ONLY** call `view_file` on a screenshot if pixel-level color verification, freehand brush stroke inspection, or creative visual layout debugging is explicitly required by the user's task.

### 0.5 The Universal Engine Mandate (Zero App-Specific Engine Hacks)
- **Autonomous Universal Engine Principle:** Extra is an autonomous computer-use engine built to pilot ANY software on macOS and Windows—including apps it has never encountered before.
- **STRICT PROHIBITION:** **NEVER write application-specific code branches** (`if app == "canva":`, `if "photoshop" in title:`) in the core engine, MCP server tools, or evolution subsystems.
- **THE 4-STEP ROOT CAUSE GENERALIZATION PROTOCOL:** When an issue occurs in any app (e.g. Canva, Blender, Premiere, Excel):
  1. **Analyze the root cause:** Identify the exact technical failure mechanism.
  2. **Abstract to UI framework & OS failure class:** Categorize the bug into a universal class (custom title-bar focus isolation, actuator vs. perception divergence, unverified mode transitions, stale accessibility tree nodes, or blind evolution poisoning).
  3. **Implement a universal architectural fix:** Solve the whole class of problems at the engine or protocol level for ALL applications universally.
  4. **Confine app details to declarative skills:** App-specific tips, coordinates, and hotkeys belong strictly in declarative skill files (`skills/extra-<app>/SKILL.md`) or episodic memory (`memory/graph.kuzu`), NEVER in core engine code.

### 1. The Live Desktop Pilot Mandate (ZERO Background Scripts, ZERO Clipboard Cheats)
- **Computer use MUST happen LIVE on the Windows desktop as a visible pilot.**
- **THE STRICT NO-SCRIPTING PROHIBITION:**
  - **NEVER** use `run_command` or shell commands to execute background Python scripts (`python -c "import win32..."`, `PIL`, `comtypes`, `pywinauto`, `ctypes`) to automate UI interactions, hunt for buttons, or control applications.
  - Doing so transforms the engine into a headless scripting bot and traps the agent in 10-minute exploratory loops.
  - **COM / UI AUTOMATION SAFETY:** Extra already possesses a hardened, high-speed UI Automation plane (`UIAutomationPlane`) exposed via `extra_inspect_ui`. NEVER write ad-hoc `comtypes` scripts (`CreateObject('...IUIAutomation')`); doing so crashes with ungenerated TypeLib errors.
  - **ZERO DEVTOOLS CONSOLE / JAVASCRIPT INJECTION PROHIBITION:**
    - **STRICT PROHIBITION:** NEVER open browser Developer Tools (`F12`, `Ctrl+Shift+I`) to run JavaScript snippets, inject elements, trigger clicks via `document.querySelector(...)`, or monkey-patch `window.open` / event listeners in the DevTools console.
    - Doing so violates the live desktop pilot paradigm, degrades into headless web scraping, triggers browser CSP/permission blocks, and traps the agent in 50+ turn scripting loops.
    - Automate browser windows cleanly via visible OS inputs (`extra_click`, `extra_type`, `extra_hotkey`, `extra_batch_actions`) or use `extra_browser` for headless Playwright execution.
  - **MATHEMATICAL STROKE SYNTHESIS FAST-PATH:** If generating vector waypoints or decomposing an image for brush painting, NEVER run 30+ iterative PowerShell/Python commands. Use `extra_execute_bridge(runtime="python", payload="...")` in a SINGLE atomic turn to compute waypoints, or dispatch native splines directly.
  - **ALL desktop interactions MUST be dispatched directly via Extra MCP tools:**
    - `extra_launch(app_name="...", args=[...])` to open apps visibly in the foreground.
    - `extra_focus_window(window_title="...")` to bring windows to the front.
    - `extra_click(target="...", x=..., y=...)` with semantic visual grounding and visible human-like Bezier curves.
    - `extra_stroke(points=[...], duration=...)` for fluid, continuous brush and pen sketching.
    - `extra_batch_actions(actions=[...])` to execute compound hardware actions in a single turn.
    - `extra_snap_layout(...)` to snap and arrange windows cleanly in sub-15ms.
    - `extra_type(text="...")` to enter text or formulas live.
    - `extra_hotkey(keys=[...])` to send keyboard shortcuts.
    - `extra_task_complete(summary="...")` automatically captures and returns the final verified screenshot (`auto_screenshot=True`). NEVER call `extra_screenshot()` in the same tool turn as `extra_task_complete()`.
- **ZERO CLIPBOARD "CHEATS" IN CREATIVE / DRAWING TASKS:**
  - When the user asks to paint, sketch, or draw in MS Paint, Canva, or Photoshop, **NEVER** copy an upscaled reference image into the Windows Clipboard via PowerShell and `Ctrl + V` paste it onto the canvas.
  - Creative tasks must be drawn live on the glass using actual brush strokes, vector splines, tool selections, and color swatches.
- **LIVE HUMAN-OBSERVABLE FLIGHT:**
  - `extra_click` and `extra_stroke` default to `human_like=True`. The user must see the cursor glide across the glass with the ambient glow, observing the live execution as it happens.
- **Every application opened for the user MUST REMAIN OPEN AND VISIBLE.** NEVER call `.terminate()`, `kill`, or `taskkill` on apps that were requested to be opened.

### 1.1 Strict Prohibition on Workflow Substitution & Fake Exports (Ground-Truth Invariant)
- **THE STRICT WORKFLOW SUBSTITUTION PROHIBITION:**
  - When the user request or benchmark mandates operating a specific target application (e.g., Google Docs, Google Slides, Google Sheets, Canva, Figma, LibreOffice, FreeCAD, Blender):
    - **You MUST genuinely create and edit the content INSIDE that application.**
    - **NEVER substitute local programmatic workarounds (e.g. generating local HTML/CSS files, running headless Chrome to print PDFs, or generating local mockups) as a replacement for requested GUI application workflows.**
    - If a benchmark asks to create a presentation in Google Slides, you MUST create the slides in Google Slides. Creating a local HTML slide deck and exporting it to PDF is a STRICTLY PROHIBITED CHEAT.
    - If a benchmark asks to export a PDF from Google Docs or Slides, the PDF must originate from the actual document (via in-browser download or official `/export?format=pdf` URL endpoint), NEVER from a locally fabricated HTML file.
### 1.2 Long-Horizon Pacing & Milestone Turn Budgeting (Max 30 Turns Per Subtask)
- **STRICT PROHIBITION: NEVER spend more than 30 turns on any single subtask or application in multi-step workflows.**
- In long-horizon or multi-application benchmarks (e.g. creating graphics in Paint, building financial models in Sheets, drafting documents in Docs, generating presentation slides):
  - **Budget Cap:** Each subtask has a hard budget of **30 turns maximum**.
  - **Pacing Rule:** If a subtask reaches 25 turns without completion:
    1. Immediately freeze and package the essential core deliverable.
    2. Transition to the next milestone immediately to prevent starving downstream applications.
    3. NEVER get trapped in endless micro-adjusting, coordinate-nudging, or undo/redo loops that burn hundreds of turns on one application while leaving the rest of the benchmark unexecuted.

### 2. High-Speed Hybrid Fast Paths (Zero-Stall Content Creation)
To prevent human-slow typing or sloppy freehand drawing while keeping the UI 100% visible:
- **Google Sheets & Web Spreadsheets:**
  1. Bottom sheet tabs and cell grids render in an opaque HTML5 canvas where screenshot captures dismiss open context menus.
  2. **Add Sheet Tab Fast-Path:** Use `extra_hotkey(keys=["shift", "f11"])` to instantly insert a new sheet tab in 1 turn without clicking the bottom `+` button.
  3. **Universal Action Search:** Use `extra_hotkey(keys=["alt", "/"])` (Windows/Linux) or `extra_hotkey(keys=["alt", "q"])` to open the "Search the menus" box and execute any sheet command (e.g. "Rename sheet", "Insert chart", "Freeze panes") in 1 turn.
  4. NEVER spend multiple turns pixel-hunting microscopic bottom tab context menus.
- **Calculator (`calc.exe`):**
  1. Execute in ONE turn:
     `call_mcp_tool(ServerName="extra", ToolName="extra_subtask_run", Arguments={"intent": "calculate <formula>="})`
     OR `call_mcp_tool(ServerName="extra", ToolName="extra_batch_actions", Arguments={"actions": [{"action": "launch", "app": "calc"}, {"action": "focus", "window_title": "Calculator"}, {"action": "type", "text": "<formula>="}], "auto_settle": true})`
  2. Calculations compute instantly on screen and the result is returned immediately in `distilled_ui` in the same turn.
  3. NEVER pass `use_clipboard=true` in Calculator (Windows Calculator rejects clipboard paste with "Invalid input").
  4. NEVER call `extra_screenshot()` or `extra_inspect_ui()` in a separate turn — the result is already in the tool response!
- **Documents & Briefings (`notepad.exe`):**
  1. Write the document file directly to disk (`Path.write_text` or `write_to_file`) to avoid slow character-by-character typing.
     - **Safe Path:** ALWAYS save to `%USERPROFILE%\.extra\workspace\<name>.txt` or the active project folder. **NEVER** write to `%USERPROFILE%\Documents` (blocked by Windows Defender Controlled Folder Access).
  2. Visibly launch Notepad with the file: `extra_launch(app_name="notepad", args=["<absolute_path>"])`.
- **Technical Charts & Architecture Diagrams (`mspaint.exe`):**
  1. ONLY when the user explicitly requests generating a programmatic statistical graph, chart, or data visualization (e.g. matplotlib bar chart or system architecture diagram), you may generate the clean PNG image programmatically to disk via Python (`PIL`) or .NET.
     - **Safe Path:** ALWAYS save to `%USERPROFILE%\.extra\workspace\<name>.png`. **NEVER** write to `%USERPROFILE%\Pictures` (blocked by Windows Defender Controlled Folder Access).
  2. Visibly launch Paint to display the chart: `extra_launch(app_name="mspaint", args=["<absolute_path>"])`.
- **Live Creative Art & Freehand Painting Tasks (`mspaint.exe`):**
  - **STRICT PROHIBITION ON WORKFLOW SUBSTITUTION / CHEATING:** Whenever asked to paint, draw, or create an artistic scene (e.g. "paint a horse", "paint the solar system", "paint this image"), you MUST genuinely draw the artwork live on canvas using vector strokes (`action="stroke"`) and color palette selections. Generating an image via PIL and opening it via `extra_launch` is a **strictly prohibited cheat**.
  1. **Win32 Canvas Focus Invariant:** In modern MS Paint, keyboard focus defaults to the Ribbon. Global canvas shortcuts (`Ctrl+A`, `Delete`, `Ctrl+E`) will **silently fail** unless the mouse clicks inside the drawing canvas first! Always click `(x=500, y=400)` before sending canvas shortcuts.
  2. **Blank Canvas Reset Protocol:**
     `extra_subtask_run(intent="reset canvas in paint")`
     OR: `extra_batch_actions(actions=[{"action": "focus", "window_title": "Paint"}, {"action": "click", "x": 500, "y": 400}, {"action": "hotkey", "keys": ["ctrl", "a"]}, {"action": "sleep", "ms": 50}, {"action": "hotkey", "keys": ["delete"]}, {"action": "hotkey", "keys": ["esc"]}, {"action": "hotkey", "keys": ["b"]}, {"action": "click", "x": 500, "y": 400}])`. Note: `esc` dismisses marquee selection, `b` activates the Brush tool, and `click(500, 400)` re-anchors canvas focus. If `Ctrl+N` triggers a "Save changes?" dialog, immediately press `n` (`hotkey: ["n"]`) to choose "Don't Save", then click `(500, 400)` on the fresh canvas.
  3. **The 5-Stage Stroke Pipeline (Anti-Scribble Mandate):**
     - **STRICT PROHIBITION: NEVER SLICE AN IMAGE INTO ZIG-ZAG RASTER SCANLINES.** An AI painting pilot is NOT an inkjet printer. Slicing color masks into horizontal or diagonal zig-zag hatch marks produces digital noise, jagged scribbles, and wastes 100+ turns.
     - Decompose the image into **4 to 10 coarse anchor points** per curve (spine, neck, legs, silhouette) and use `extra_stroke(points=[...], smooth=True)` or `action="stroke"` (which automatically generates fluid Catmull-Rom splines with Viviani's 2/3 power law curvature slowdown).
     - Follow the 5-Stage sequence: (1) Canvas Setup -> (2) Silhouettes -> (3) Color Washes -> (4) Anatomy Refinement -> (5) Expressive Motion Streaks.
  4. **Zero-REPL Bridge Synthesis:** When calculating waypoints or doing image math in `extra_execute_bridge`, compute all waypoints and return the final action JSON in **1 single turn**. Do NOT save intermediate crop images and call `view_file` across 50 turns. Consult `skills/extra-paint/SKILL.md` for verified palette coordinates instead of exploratory vision loops.
- **Canvas & Design Apps (Canva, Figma, Web-in-App / Electron):**
  1. **UI Architecture Understanding:**
     - Canva and Figma desktop applications are built on Electron.
     - Top navigation bars, search inputs, home screen category icons, and sidebars ARE standard web elements that CAN be interacted with via clicks, hotkeys, and searches.
     - Only the inner drawing canvas area (where individual shapes, vectors, and text layers sit) renders in an opaque HTML5/WebGL canvas that does not expose Win32 UIA accessibility nodes.
  2. **How to Create & Open Designs in Canva:**
     - **Primary (Most Reliable): Use Home Screen Category Icons or Search Bar:**
       - On the Canva home screen, click the visible category icons directly (e.g. "Presentation", "Instagram Post", "Doc", "Whiteboard") or click the prominent search box: *"What would you like to create?"* at the top of the home screen, type the desired format (e.g. "Instagram Post" or "Presentation"), and press Enter.
       - **CRITICAL CAVEAT ON `Ctrl + N`:** In Canva desktop, pressing `Ctrl + N` often defaults keyboard focus to the **"Open a design link:"** box at the bottom of the popup! DO NOT blindly type design names after pressing `Ctrl + N`. If you see "Please enter a valid design link", press `extra_hotkey(keys=["esc"])` once to dismiss the popup, and click the category icon or search box on the main home screen!
     - **CANVA WEB BROWSER POP-UP BLOCKER TRAP & RECOVERY:**
       - In web browsers (Chrome/Edge), clicking "Create a design" or "Custom size" opens a popup window (`window.open`). Modern browsers silently BLOCK this popup by default, leaving the home page unchanged with a "Pop-up blocked" icon in the address bar.
       - **NEVER** attempt to fix this by opening DevTools and typing JavaScript.
       - **Recovery Options:**
         1. Click the home page search bar: *"What would you like to create?"* or click category tiles (e.g. "Presentation", "Instagram Post", "Whiteboard") — these open directly in the existing tab/window without triggering popup blockers.
         2. Click the "Pop-up blocked" icon in the browser address bar, select "Always allow pop-ups and redirects from canva.com", click "Done", and retry.
         3. Prefer the native Canva desktop application (`canva.exe`) which does not have browser popup blocker restrictions.
  3. **Honoring User Intent (Templates vs Custom Graphics):**
     - **When the user requests to use Canva templates:**
       - Search for the template in Canva's search bar or click "Templates" on the left navigation bar.
       - Select a template and use Canva's native tools. Do NOT fight the user's explicit request to use Canva templates.
     - **When generating marketing posters, graphics, or presentations in Canva:**
       - **STRICT PROHIBITION ON WHOLE-POSTER WORKFLOW SUBSTITUTION / PIL CHEATING:**
         - **NEVER** generate a finished marketing poster with baked-in text, typography, cards, and branding in Python via PIL and paste it into Canva via the Windows Clipboard.
         - Doing so violates Rule 1 and Rule 1.1, fails benchmark authenticity, and produces defective deliverables (pasted images do not auto-fill the canvas, leaving 200px+ stark white margins).
         - **All headlines, subtext, cards, shapes, colors, and layout hierarchy MUST be authored genuinely using Canva's native tools.**
         - Raw external source assets (such as an isolated product icon, 3D model render, or company logo PNG) may be copied or uploaded, but the poster composition, text, and layout MUST be created on canvas.
       - **Zero-Coordinate Single-Key Accelerators:**
         - Press `T` to instantly create and focus a text box in 1 turn (no need to navigate the left rail).
         - Press `R` to insert rectangle cards/containers.
         - Press `C` to insert circles/badges.
         - Press `L` to insert accent lines.
         - Press `Alt + /` or `Ctrl + /` to open Magic Search for elements ('3D glowing orb', 'gradient') or commands ('Set image as background', 'Align to page').
         - Select canvas -> click top toolbar color swatch to set background gradient/color.
     - **When the user requests manual drawing/sketching in Canva (Native Stroke Fast-Path):**
       - Create the custom canvas via "Custom size" on the home screen.
       - **MANDATORY DESIGN TAB ACTIVATION (NEVER use `Ctrl + Tab`):**
         - In Canva desktop (Electron), creating a design opens a new tab in the title bar (`Untitled design - ...`), but does NOT transfer active foreground focus.
         - `Ctrl + Tab` DOES NOT WORK for switching tabs in Canva desktop.
         - You MUST explicitly activate the design tab by clicking its header text directly: `extra_click(x=175, y=25)` (between `x=130` and `x=240`, safely away from the close 'x' at `x=281`).
       - **ELECTRON MULTI-WEBVIEW ACCESSIBILITY INVARIANT (DO NOT LOOP ON TABS):**
         - In Electron apps, background webviews retain their nodes in the Win32 UIA tree. The presence of Home screen elements (`Search anything`, `Templates Browse`) in `extra_inspect_ui` does NOT mean the design tab is not active!
         - To verify the Design Editor is active: check `active_window_title` in `extra_screenshot` or verify that the top editor menu displays `File` and `Resize`. NEVER cycle through tabs repeatedly because Home elements appear in UIA tree dumps!
       - **PRE-DRAWING MODE GATE:**
         - Confirm that the top menu displays `File`, `Resize`, `Undo`, and the left rail is active.
         - If the screen displays "All Brand Templates" or the Brand tab is selected, you are still on the Home screen! Click `x=175, y=25` again. NEVER dispatch drawing strokes while the Home or Brand screen is active!
       - Immediately send `extra_hotkey(keys=["ctrl", "0"])` to ensure the canvas is centered and zoomed to Fit (prevents multi-page zoom distortion).
       - **ENGAGING THE DRAW TOOL (Zero-Ghost Strokes):**
         - If "Draw" is visible on the left rail, click it.
         - If "Draw" is NOT visible on the left rail, click "Tools" or "Apps" (`x=36, y=505` or `x=36, y=650`), then click "Draw" from the flyout tray.
         - Click the Pen or Marker tool, then click ONCE in the center of the canvas (`extra_click(x=cx, y=cy)`) to dismiss the tool flyout and focus the WebGL drawing layer.
         - **CRITICAL:** NEVER dispatch stroke actions until you have verified the Pen tool is active! Dispatching mouse strokes without an active drawing tool will move the OS cursor with ZERO rendered ink on the canvas.
       - **CRITICAL: STRICT MARGIN GUARD (Avoid "Add Page" Disasters):** The "Add page" button sits directly beneath the bottom canvas border. NEVER send stroke coordinates or clicks within 60px of the canvas bottom edge.
        - Dispatch strokes in batches via `extra_batch_actions` (`{"action": "stroke", ...}`).
   4. **Fullscreen / Maximized Window Policy for Canvas Apps:** Never squeeze drawing canvases into half-screen splits. Maximize the window: `extra_snap_layout(layout="maximize", window="<AppName>")` or `extra_hotkey(keys=["win", "up"])` so the canvas has full screen real estate.

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

### 3. Purpose-Driven Window Sizing & Snapping Policy
- **NEVER** drag window title bars with mouse coordinates.
- In Windows 11, apps have tabs (Notepad tabs retain prior names). Never search for exact document file names in titles.
- **Window Sizing Policy by Application & Task Class:**
  - **Creative, Canvas, 3D & Media Apps (Paint, Photoshop, Blender, Canva, CAD):**
    - **MANDATORY FULLSCREEN / MAXIMIZED:** Creative and canvas tasks require maximum screen real estate. Squeezing a canvas to half-screen shrinks drawing areas, creates ugly scrollbars, and distorts coordinate frames.
    - **Action:** Maximize the window: `extra_snap_layout(layout="maximize", window="Paint")` or `extra_hotkey(keys=["win", "up"])`.
    - **NEVER** resize or dock canvas apps to half-screen unless the user explicitly commands a dual-split view.
  - **Dual-Window Comparison & Synthesis (Research + Briefing):**
    - Use side-by-side docking **ONLY** when a task specifically requires simultaneous reference (e.g. Edge on right, Notepad on left for financial briefings).
    - `extra_snap_layout(layout="side_by_side", left_window="Notepad", right_window="Edge")`
    - Win32 `SetWindowPos` directly docks both windows with sub-millisecond precision, avoiding the Windows 11 Snap Assist menu.
  - **Anti-Occlusion & Foreground Rules:**
    - If running inside a terminal or IDE, do NOT dock applications to half-screen merely to keep the terminal visible.
    - Focus the application directly via `extra_focus_window(window_title="<AppName>")` or bring to front. The application should occupy its natural, unconstrained geometry.
- **Fallback Hotkeys:**
  - Maximize: `extra_focus_window(window_title="<App>")` -> `extra_hotkey(keys=["win", "up"])`.
  - Half-Screen Docking: `extra_hotkey(keys=["win", "left"])` -> `extra_hotkey(keys=["esc"])` (dismisses Snap Assist).

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
- **ZERO Destructive Browser Process Termination (`Stop-Process -Force` Prohibition):**
  - **STRICT PROHIBITION:** NEVER execute `Stop-Process -Name chrome -Force` or `taskkill /f /im msedge.exe` while automated tasks are in progress. Killing browsers wipes active user tabs, closes authenticated sessions, and triggers crash restore dialogs.
  - If a browser is already running, focus it with `extra_focus_window(window_title="Chrome")` or open a new URL with `extra_launch(app_name="chrome", args=["<url>"])`.
  - When launching Chrome with a specific user profile, pass `extra_launch(app_name="chrome", profile="Profile 3", args=["<url>"])` or `args=['--profile-directory=Profile 3', '<url>']`. The launcher automatically handles Win32 command line escaping without argument splitting.
- **ZERO Shadow Daemon / Ad-Hoc Server Creation:**
  - **STRICT PROHIBITION:** NEVER build ad-hoc background FastAPI, Flask, or Uvicorn servers or secondary polling daemons (`localhost:8000`) to automate applications.
  - Doing so creates split-brain state, causes background UIA focus failures, and adds polling latency.
  - Use Extra's native tools (`extra_browser`, `extra_batch_actions`) or synthesize permanent API fast-paths via `extra_browser(action="synthesize_api")`.
- **THE 10-SECOND WEB FORM SUBMIT & VERIFICATION PROTOCOL:**
  - In modern web single-page apps (such as Meta Business Suite, Canva, LinkedIn), clicking a submission button (`Schedule`, `Publish`, `Save`) often leaves the button in an indefinite loading spinner state even after the server successfully processed the request.
  - **NEVER** treat an open modal or ongoing spinner as a failure and immediately click "Schedule" again (this creates duplicate posts/entries!).
  - **MANDATORY PROTOCOL:**
    1. Click the button.
    2. Wait 10 seconds (`extra_batch_actions(actions=[{"action": "sleep", "duration_ms": 10000}])`).
    3. If the modal has not dismissed, send `extra_hotkey(keys=["esc"])` or click Cancel/Discard to dismiss the modal.
    4. Navigate directly to the verification page (e.g. Content Calendar / Planner / Dashboard).
    5. Verify if the item is scheduled. ONLY if confirmed absent may a retry be attempted.
- **ZERO MCP Server Reverse-Engineering / Internal Driver Debugging:**
  - **STRICT PROHIBITION:** NEVER run Python reflection, inspection, or source-dumping scripts (`inspect.getsource(...)`, checking `extra.mcp.*` packages) during desktop tasks.
  - Extra MCP tools are low-level driver primitives. If drawing, clicks, or hotkeys do not produce expected effects, the root cause is application state (window focus, inactive drawing tool, modal blocking input, or viewport coordinates), NEVER the MCP driver code. Diagnose UI focus and application mode cleanly.
- **STRICT ANTI-BLIND COMPLETION MANDATE (Sequential Verification):**
  - **NEVER call `extra_task_complete` in the same tool turn as `extra_screenshot`.**
  - Calling `extra_screenshot` and `extra_task_complete` simultaneously forces the model to claim completion blindly without ever receiving or inspecting the verification visual state.
  - **Mandatory 2-Step Verification Sequence:**
    1. Turn N: Execute your final UI action and call `extra_screenshot()` (or inspect via `extra_inspect_ui`). Conclude your tool calls for that turn.
    2. Turn N+1: Receive the screenshot / inspection output, visually verify that the expected UI elements and content actually exist. Only then call `extra_task_complete(summary="...", success=true)` and present your response to the user.
    3. If the verification reveals missing elements (e.g. bookmarks dialog didn't take, text didn't paste), take corrective action—DO NOT claim completion!
- **THE MID-TASK HARDWARE VS VISUAL RENDERING GATE:**
  - OS-level execution success (e.g. `extra_batch_actions` or `extra_stroke` returning `success=True`) ONLY confirms hardware events were queued and sent to Windows. It does NOT guarantee that the application accepted or visually rendered the input.
  - You MUST verify that the application was in the correct state/mode before dispatching strokes, and visually verify the result on Turn N+1 before declaring completion.
- **STRICT ANTI-POISONING SKILL EVOLUTION RULE:**
  - NEVER invoke `extra_evolve_skill` on tasks that failed, stalled, required intermediate recovery steps, or were not visually verified.
  - Evolution is strictly reserved for clean, verified golden paths or documenting verified anti-stall guardrails via `friction_points`. Calling evolution on an unverified run poisons the skill library for future tasks.

### 4.5 The High-Speed Tiered Verification Protocol (Zero-LLM Latency Tax)
- **THE 5-MINUTE VERIFICATION TRAP:** NEVER verify every micro mouse click or keystroke with an LLM screenshot roundtrip. Doing so burns 5.0s–8.5s per action (3.5–5.5 minutes of pure waiting across 40 steps) and saturates the context window with 64,000+ vision tokens.
- **TIER 1 (In-Memory Perceptual Settle < 15ms):**
  - Default to `extra_batch_actions(actions=[...], auto_settle=True)`.
  - The engine uses row-difference hashing (`dhash`) directly in RAM to detect perceptual stability between clicks, hotkeys, and window switches, eliminating race conditions against fade-in animations with zero LLM tokens.
- **TIER 2 (Closed-Loop Compound Telemetry < 50ms):**
  - Focus actions automatically verify `verified_focus` against active HWND in < 1ms.
  - Drawing tasks automatically verify ink deposition along the actual Bezier trajectory. Set `strict_ink=True` if you require hard failure on ghost strokes.
  - Browser workflows can invoke `extra_browser(action="settle")` for sub-30ms DOM readiness and network quiescence.
- **TIER 3 (Milestone Verifier & Auto-Rollback ~1.8s):**
  - Structure long-horizon workflows using `extra_blueprint_start` with clear acceptance criteria:
    ```json
    {
      "id": "M1_EXPORT",
      "name": "Export High-Res Video",
      "expected_artifacts": ["%USERPROFILE%\\.extra\\workspace\\final.mp4"],
      "acceptance_criteria": {
        "min_file_size_bytes": 1000000,
        "expected_elements": ["Export Complete"],
        "unwanted_elements": ["Crash", "Error"]
      }
    }
    ```
  - When completing a milestone, call `extra_blueprint_milestone(task_id="...", milestone_id="...", action="complete", auto_rollback=True)`.
  - The engine runs `MilestoneVerifier` + `SOUL-Critic` to ground required elements, confirm physical files, and fold noisy intermediate history into compact semantic tokens.

### 5. Windows Defender & Controlled Folder Access (CFA) Compliance
- **STRICT DIRECTORY BOUNDARY:** NEVER create files or directories directly in Windows protected user folders:
  - DO NOT write to `%USERPROFILE%\Documents`, `%USERPROFILE%\Pictures`, `%USERPROFILE%\Desktop`, `%USERPROFILE%\Videos`.
  - Windows Defender Controlled Folder Access (Ransomware Protection) strictly blocks `python.exe` and `cmd.exe` from modifying these folders (Event 1123) and triggers alarming security toast popups for the user.
- **MANDATORY SAFE WORKSPACE:** Always perform file creation, data extraction, reports, and diagram exports in:
  - `%USERPROFILE%\.extra\workspace\` (or the active project repository).
  - This folder is 100% exempt from CFA restrictions, guaranteeing zero Defender warnings, zero permission errors, and flawless visual presentation in Notepad, Paint, and Explorer.