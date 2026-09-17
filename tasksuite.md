# Project Extra — Universal Computer Use Regression Task Suite (A to Z)
**Version:** 2.0.0-PROD  
**Target Platform:** Windows 10/11 (x64 / ARM64) & macOS Sonoma/Sequoia (Universal PAL)  
**Total Tasks:** 150 Discrete Industrial-Grade Regression Tasks  
**Harness Specification:** Deterministic Zero-Stall Fast-Path Validation  

---

## Executive Summary & Research Context

### 1. The Computer Use Landscape & The "GPT-6 Astra" Dilemma
In September 2026, the AI industry witnessed the rollout of **GPT-6 Astra** (often termed *Astra 6*), accompanied by benchmarks like **OSWorld 2.0** and **ScreenSpot Pro**. While frontier multimodal models have achieved remarkable breakthroughs in perceptual visual reasoning, independent evaluations and enterprise deployments have consistently revealed severe structural failure modes when these pure-vision models attempt unassisted computer use:

```
+-----------------------------------------------------------------------------------------+
|                  THE 7 DEADLY SINS OF FRONTIER COMPUTER USE AGENTS                     |
+-------------------+---------------------------------------+-----------------------------+
| Failure Mode      | Astra 6 / Pure-Vision Agent Symptom   | Project Extra Antidote      |
+-------------------+---------------------------------------+-----------------------------+
| 1. High Latency   | Captures 4K/1080p frames every click; | 0.8ms DXGI screen capture;  |
|    & Token Cost   | 3–8s per action; $10–$50/M tokens.    | Win32 SendInput / direct COM|
+-------------------+---------------------------------------+-----------------------------+
| 2. Coordinate     | High DPI (125%, 150%, 200%) causes    | Per-Monitor DPI Awareness v2|
|    Drift          | clicks to hit 50–200px off-target.    | + AttachThreadInput scaling |
+-------------------+---------------------------------------+-----------------------------+
| 3. Focus & Modal  | Clicks background apps or gets trapped| AttachThreadInput focus     |
|    Lockout        | by Windows 11 Snap Assist / popups.   | bypass + ESC auto-dismiss   |
+-------------------+---------------------------------------+-----------------------------+
| 4. Canvas         | Electron/WebGL canvas (Canva, Figma,  | Zero-Stall Fast-Paths: PIL  |
|    Blindness      | Blender) lacks UIA accessibility nodes| synthesis + STA paste / CLI |
+-------------------+---------------------------------------+-----------------------------+
| 5. Mid-Task       | Forgets initial constraints across    | Embedded KùzuDB Graph Memory|
|    Amnesia        | multiple applications and steps.      | + FastEmbed vector recall   |
+-------------------+---------------------------------------+-----------------------------+
| 6. Infinite Error | Retries failing clicks or invalid link| StallBreaker closed loop    |
|    Loops          | inputs 10+ times without recovery.    | (3-strike escalation abort) |
+-------------------+---------------------------------------+-----------------------------+
| 7. Security / CFA | Writes to Protected folders triggering| Strict safe boundary at     |
|    Violations     | Windows Defender Ransomware blockades.| `%USERPROFILE%\.extra\`     |
+-------------------+---------------------------------------+-----------------------------+
```

### 2. Purpose of This Task Suite
This **Universal Task Suite (`tasksuite.md`)** is Extra's definitive quality-assurance and regression harness. It defines **150 discrete, comprehensive tasks spanning every desktop feature from A to Z**. 

Any future feature, MCP tool change, or platform upgrade must pass this entire task suite without regressions before being cleared for public release.

---

## Suite Architecture & Category Matrix

| Tier | Domain / Category | Task Range | Target Applications / Subsystems | Primary Failure Modes Tested |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 1** | System Utilities & Shell Fast-Paths | `TASK-001` - `TASK-015` | `calc`, `notepad`, `explorer`, `settings`, `cmd`, `terminal` | Slow startup, parameter quoting, path discovery |
| **Tier 2** | Screen Perception & Multi-Monitor | `TASK-016` - `TASK-028` | DXGI, GDI, DPI scaling, multi-display, crop box | Coordinate drift, black frames, DPI scaling errors |
| **Tier 3** | Hardware Input Injection | `TASK-029` - `TASK-042` | `VK_PACKET`, STA clipboard, mouse drag, scroll, hotkeys | Dropped keystrokes, clipboard lock, jittery drags |
| **Tier 4** | Window Focus, Snapping & Docking | `TASK-043` - `TASK-056` | AttachThreadInput, Win32 HWND, Snap Assist, split-screen | LockSetForegroundWindow bypass, snap menu trapping |
| **Tier 5** | Semantic Accessibility Plane (UIA) | `TASK-057` - `TASK-070` | COM UIAutomation, Set-of-Mark, InvokePattern | Tree traversal timeouts, inaccessible elements |
| **Tier 6** | Headless Web & Browser Fast-Path | `TASK-071` - `TASK-084` | Microsoft Edge, Playwright, markdown extraction | Headless crashes, selector mismatches, session loss |
| **Tier 7** | StallBreaker Resilience & Guardrails | `TASK-085` - `TASK-098` | 3-strike escalation, loop detector, ESC handler | Infinite retry loops, stuck modal dialogues |
| **Tier 8** | KùzuDB Graph Memory & FastEmbed | `TASK-099` - `TASK-112` | KùzuDB, BAAI/bge-small-en-v1.5 ONNX, cosine recall | Embedding mismatch, DB lockouts, schema drift |
| **Tier 9** | JIT Scout & Skill Synthesis | `TASK-113` - `TASK-124` | Framework detector, CLI probe, SKILL.md generator | Viewport blindness, missing CLI parsing |
| **Tier 10**| Multi-App Cross-Desktop Workflows | `TASK-125` - `TASK-136` | Edge + Calc + Notepad + Canva + VLC + Blender | Cross-app context loss, clipboard collisions |
| **Tier 11**| Security, CFA & Anti-Stall Guardrails | `TASK-137` - `TASK-144` | Defender CFA compliance, zero-scripting rule | Ransomware popups, runaway test scripts |
| **Tier 12**| Dynamic App Registry & Persistence | `TASK-145` - `TASK-150` | `~/.extra/app_registry.json`, cold-start loader | Lost custom app mappings, restart memory loss |

---

## Detailed Task Catalog (150 Industrial Regression Tasks)

### Tier 1: System Utilities & Shell Fast-Paths (`TASK-001` - `TASK-015`)

- **`TASK-001` — Deterministic Calculator Launch & Instant Evaluation**
  - *Target:* `calc.exe`
  - *Steps:* Launch via `extra_launch("calc")`, verify window presence, inject formula `1425.50*1.18=`, capture screenshot.
  - *Assertion:* Window handle acquired in < 250ms; formula computes without clipboard paste.
- **`TASK-002` — Calculator Scientific Mode Switch & Trigonometric Evaluation**
  - *Target:* `calc.exe`
  - *Steps:* Switch Calculator mode via shortcut or typing, evaluate `sin(30)=` or compound expression.
  - *Assertion:* Computation result displayed cleanly; zero vision pixel-hunting.
- **`TASK-003` — Notepad Zero-Stall Document Briefing Creation**
  - *Target:* `notepad.exe`
  - *Steps:* Generate markdown document directly to `%USERPROFILE%\.extra\workspace\briefing_003.txt`, launch Notepad with path argument.
  - *Assertion:* Notepad opens with content populated immediately without slow character-by-character typing.
- **`TASK-004` — Notepad Multi-File Session Isolation**
  - *Target:* `notepad.exe`
  - *Steps:* Launch two distinct files sequentially in Notepad; verify both window handles or tabs.
  - *Assertion:* Window title matching handles Windows 11 tabbed Notepad without naming conflicts.
- **`TASK-005` — File Explorer Direct Directory Navigation**
  - *Target:* `explorer.exe`
  - *Steps:* Launch Explorer pointing directly to `%USERPROFILE%\.extra\workspace\`.
  - *Assertion:* Explorer window opens directly to target directory; no search bar navigation needed.
- **`TASK-006` — Windows Settings Deep-URI Activation (Network)**
  - *Target:* `ms-settings:network`
  - *Steps:* Open protocol URI via `open_uri("ms-settings:network")`.
  - *Assertion:* SystemSettings.exe window opens to Network & Internet in < 1500ms.
- **`TASK-007` — Windows Settings Deep-URI Activation (Display & Scaling)**
  - *Target:* `ms-settings:display`
  - *Steps:* Open protocol URI `ms-settings:display`; focus window.
  - *Assertion:* Settings displays Scale & Layout page; zero mouse searching.
- **`TASK-008` — Windows Terminal / PowerShell Rapid Spawn**
  - *Target:* `wt.exe` / `powershell.exe`
  - *Steps:* Launch terminal via fast-path launcher; verify process and window activation.
  - *Assertion:* Terminal activates and receives keyboard focus.
- **`TASK-009` — Task Manager Fast-Path Inspection**
  - *Target:* `taskmgr.exe`
  - *Steps:* Launch `extra_launch("taskmgr")`; focus window.
  - *Assertion:* Taskmgr window opens; handles elevated privilege gracefully.
- **`TASK-010` — Command Prompt Silent Command Execution**
  - *Target:* `cmd.exe`
  - *Steps:* Launch cmd with `/c dir` argument; verify non-blocking execution.
  - *Assertion:* Subprocess completes without leaving dangling or zombie processes.
- **`TASK-011` — Microsoft Store URI Activation**
  - *Target:* `ms-windows-store:`
  - *Steps:* Open Store URI to search for utility: `ms-windows-store://search?query=vlc`.
  - *Assertion:* Store opens with query prepopulated.
- **`TASK-012` — Store MSIX Execution Alias Resolution**
  - *Target:* `%LOCALAPPDATA%\Microsoft\WindowsApps\`
  - *Steps:* Resolve Store execution alias (e.g. `winget.exe`, `python.exe`, or `wt.exe`).
  - *Assertion:* Path resolved accurately from WindowsApps directory without PATH corruption.
- **`TASK-013` — Program Files Deep Binary Discovery**
  - *Target:* `ProgramFiles` / `ProgramFiles(x86)`
  - *Steps:* Resolve unindexed binary installed in standard vendor directory (e.g. `7-Zip\7zFM.exe`).
  - *Assertion:* Exact executable path discovered and resolved in < 5ms.
- **`TASK-014` — App Launcher Parameter Quoting & Whitespace Safety**
  - *Target:* `notepad.exe`
  - *Steps:* Pass arguments containing spaces and quotes (e.g. `["C:\\My Folder\\test file.txt"]`).
  - *Assertion:* Path cleanly parsed by ShellExecuteW without argument splitting.
- **`TASK-015` — Invalid Application Fallback & Clean Error Response**
  - *Target:* `non_existent_app_xyz.exe`
  - *Steps:* Attempt launch of unknown application.
  - *Assertion:* Returns structured error JSON in < 10ms; zero system panic or unhandled exceptions.

---

### Tier 2: Screen Perception & Multi-Monitor (`TASK-016` - `TASK-028`)

- **`TASK-016` — Primary Monitor Zero-Latency Screen Capture**
  - *Steps:* Call `extra_screenshot(monitor_index=0)`.
  - *Assertion:* Frame captured in < 15ms via DXGI / GDI; returns valid PIL Image and base64.
- **`TASK-017` — Multi-Monitor Hardware Metrics Discovery**
  - *Steps:* Query all connected displays via `get_monitors_info()`.
  - *Assertion:* Discovers virtual desktop bounds, per-monitor DPI, coordinates, and primary flag.
- **`TASK-018` — Coordinate Normalization ([0, 1000] Space)**
  - *Steps:* Convert physical pixels across 1080p, 1440p, and 4K displays to normalized [0, 1000].
  - *Assertion:* Bijective mapping: `denormalize(normalize(x, y)) == (x, y)`.
- **`TASK-019` — High-DPI Scaling Coordinate Adjustment (150% Scale)**
  - *Steps:* Simulate 150% display scaling (144 DPI); normalize coordinates.
  - *Assertion:* Coordinates scale with physical hardware pixels, eliminating cursor drift.
- **`TASK-020` — High-DPI Scaling Coordinate Adjustment (200% Scale / 4K)**
  - *Steps:* Simulate 3840x2160 display at 200% scaling.
  - *Assertion:* Center point and bounding boxes remain strictly within hardware limits.
- **`TASK-021` — Region-of-Interest (ROI) Sub-Frame Capture**
  - *Steps:* Capture cropped bounding box `[100, 100, 500, 500]`.
  - *Assertion:* Output image dimensions exactly 400x400; capture time < 5ms.
- **`TASK-022` — Screen Difference & Frame Motion Detection**
  - *Steps:* Capture two consecutive frames; verify perceptual difference hash.
  - *Assertion:* Detects dynamic UI state changes while ignoring sub-pixel rendering noise.
- **`TASK-023` — Set-of-Mark (SoM) Visual Annotation Engine**
  - *Steps:* Capture screen with `annotate_ui=True`.
  - *Assertion:* Interactive elements numbered with colored badges; annotations clear and legible.
- **`TASK-024` — Secondary Monitor Coordinate Offset Translation**
  - *Steps:* Test coordinate conversion for display positioned at negative or positive offset (e.g. `x=1920`).
  - *Assertion:* Mouse coordinates clamp cleanly without jumping back to primary display.
- **`TASK-025` — Out-of-Bounds Coordinate Clamping**
  - *Steps:* Pass coordinates `(-50, 5000)`.
  - *Assertion:* Clamped safely to `(0, monitor.bottom)`.
- **`TASK-026` — Screen Capture Format Compression (JPEG vs PNG)**
  - *Steps:* Benchmark base64 payload size and latency between JPEG quality 85 and PNG.
  - *Assertion:* JPEG payload achieves 85%+ compression with < 5ms overhead.
- **`TASK-027` — Fullscreen Video & Hardware Overlay Capture**
  - *Steps:* Capture screen while hardware-accelerated video/DirectX is active.
  - *Assertion:* DXGI captures surface directly without returning blank black rectangles.
- **`TASK-028` — Capture Engine Resource Cleanup & Memory Leak Guard**
  - *Steps:* Run 100 consecutive screen captures in tight loop.
  - *Assertion:* Process memory remains flat; device contexts and bitmaps released immediately.

---

### Tier 3: Hardware Input Injection (`TASK-029` - `TASK-042`)

- **`TASK-029` — Instant Win32 Unicode Text Injection (`VK_PACKET`)**
  - *Steps:* Type text containing spaces, punctuation, numbers, and symbols: `Hello, World! @#$%^&*()`.
  - *Assertion:* Injected instantly in < 5ms without character drops or modifier state corruption.
- **`TASK-030` — Multilingual & Emoji Unicode Typing**
  - *Steps:* Inject international text: `Extra 日本語 🚀 Système d'exploitation`.
  - *Assertion:* Non-ASCII Unicode characters render perfectly without encoding artifacts.
- **`TASK-031` — Enter Key Submission Flag Verification**
  - *Steps:* Call `instant_type("Search Query", press_enter=True)`.
  - *Assertion:* Text is entered and followed immediately by `VK_RETURN` keyevent.
- **`TASK-032` — Atomic STA Virtual Clipboard Swap & Paste**
  - *Steps:* Use atomic clipboard paste on a 5,000-word document string.
  - *Assertion:* Swaps clipboard, pastes via `Ctrl+V`, and restores prior clipboard in < 30ms.
- **`TASK-033` — Clipboard Concurrency & Race Condition Guard**
  - *Steps:* Execute rapid clipboard writes in succession while another process queries clipboard.
  - *Assertion:* Employs exponential backoff retry on `CLIPBRD_E_CANT_OPEN`; zero crashes.
- **`TASK-034` — Hardware Mouse Move & Cursor Position Inquiry**
  - *Steps:* Move cursor to `(500, 500)`; verify via `get_cursor_position()`.
  - *Assertion:* Coordinates match physical cursor position within 1 pixel.
- **`TASK-035` — Left, Right & Middle Mouse Click Execution**
  - *Steps:* Dispatch left, right, and middle clicks with configurable intervals.
  - *Assertion:* Mouse down/up events dispatched symmetrically.
- **`TASK-036` — Double-Click Timing Precision**
  - *Steps:* Dispatch `mouse_double_click()` at target coordinates.
  - *Assertion:* Event interval respects Windows `GetDoubleClickTime()` threshold (~100ms).
- **`TASK-037` — Smooth Human-Like Bézier Mouse Drag**
  - *Steps:* Execute `mouse_drag(start_x=100, start_y=100, end_x=600, end_y=400, steps=20)`.
  - *Assertion:* Trajectory follows smooth curve with easing; no teleportation.
- **`TASK-038` — Linear High-Speed Mouse Drag**
  - *Steps:* Execute rapid straight-line drag for slider/scrubber controls.
  - *Assertion:* Mouse button held continuously throughout intermediate steps; released at target.
- **`TASK-039` — Vertical Mouse Wheel Scroll Precision**
  - *Steps:* Dispatch `mouse_scroll(delta=-500)`.
  - *Assertion:* Exactly 5 WHEEL_DELTA clicks dispatched vertically; smooth UI scroll.
- **`TASK-040` — Horizontal Mouse Wheel Scroll**
  - *Steps:* Dispatch `mouse_scroll(delta=360, horizontal=True)`.
  - *Assertion:* Dispatches `MOUSEEVENTF_HWHEEL` horizontally.
- **`TASK-041` — Multi-Key Synchronized Hotkeys (`Ctrl+Shift+Esc`)**
  - *Steps:* Send 3-key chord: `send_hotkey(["ctrl", "shift", "esc"])`.
  - *Assertion:* Modifiers depressed in order, action key pressed, released in reverse order.
- **`TASK-042` — System Modal Dismissal Hotkey (`Esc` & `Alt+F4`)**
  - *Steps:* Send `send_hotkey(["esc"])` to dismiss popup modal.
  - *Assertion:* Keycode dispatched cleanly; frees focus immediately.

---

### Tier 4: Window Focus, Snapping & Docking (`TASK-043` - `TASK-056`)

- **`TASK-043` — LockSetForegroundWindow Restriction Bypass**
  - *Target:* Background application window
  - *Steps:* Call `force_activate_window(hwnd)` using `AttachThreadInput` + `AllowSetForegroundWindow`.
  - *Assertion:* Window forced to foreground without flashing taskbar icon or failing.
- **`TASK-044` — Window Title Substring Search & Polling Retry**
  - *Target:* Asynchronously launching app
  - *Steps:* Find window with partial title: `find_window_by_title("Notepad", timeout=3.0)`.
  - *Assertion:* Polls smoothly until window handle is available; returns `WindowInfo`.
- **`TASK-045` — Window Process ID (PID) Association**
  - *Target:* Launched child process
  - *Steps:* Launch app; inspect `win.process_id` and `win.process_name`.
  - *Assertion:* PID accurately maps to spawned process.
- **`TASK-046` — Active Foreground Window State Inquiry**
  - *Steps:* Call `get_foreground_window()`.
  - *Assertion:* Returns non-null `WindowInfo` with rect bounds, title, and process.
- **`TASK-047` — Top-Level Visible Window Enumeration**
  - *Steps:* Call `list_windows(visible_only=True)`.
  - *Assertion:* Returns list of active user windows, filtering zero-size background cloaked handles.
- **`TASK-048` — Window Bounds & Geometric Center Calculation**
  - *Steps:* Calculate center of window with rect `(100, 100, 1100, 900)`.
  - *Assertion:* Center equals `(600, 500)`; dimensions equal 1000x800.
- **`TASK-049` — Window Left-Half Split Docking (`Win+Left`)**
  - *Target:* Target app 1 (e.g. Paint / Edge)
  - *Steps:* Focus app, dispatch `send_hotkey(["win", "left"])`, dispatch `send_hotkey(["esc"])`.
  - *Assertion:* Window snaps to left half of display; Windows 11 Snap Assist menu dismissed.
- **`TASK-050` — Window Right-Half Split Docking (`Win+Right`)**
  - *Target:* Target app 2 (e.g. Notepad)
  - *Steps:* Focus app, dispatch `send_hotkey(["win", "right"])`, dispatch `send_hotkey(["esc"])`.
  - *Assertion:* Window snaps to right half of display; side-by-side arrangement complete.
- **`TASK-051` — Windows 11 Snap Assist Trap Avoidance**
  - *Steps:* Trigger window snap; immediately follow with `esc`.
  - *Assertion:* Focus does not get stuck in thumbnail selector menu.
- **`TASK-052` — Minimized Window Restoration**
  - *Target:* Minimized window
  - *Steps:* Call `force_activate_window` on iconic/minimized window.
  - *Assertion:* Restores window with `SW_RESTORE` before bringing to front.
- **`TASK-053` — Window Executable Path Discovery (`get_window_executable_path`)**
  - *Target:* Active window handle
  - *Steps:* Query full `.exe` file path via process handle query.
  - *Assertion:* Returns absolute executable path on disk (e.g. `C:\...\Notepad.exe`).
- **`TASK-054` — Multi-Window Process Enumeration (`find_windows_by_process`)**
  - *Target:* Multi-instance app (e.g. `chrome.exe` / `msedge.exe`)
  - *Steps:* Query all windows belonging to process name.
  - *Assertion:* Discovers all top-level frames belonging to process.
- **`TASK-055` — Cloaked & UWP Suspended Window Filtering**
  - *Target:* Windows UWP background apps
  - *Steps:* Inspect windows with `DWMWA_CLOAKED` attribute.
  - *Assertion:* Distinguishes active visible UWP frames from suspended background frames.
- **`TASK-056` — Zero-Window Graceful Failure Handling**
  - *Target:* Non-existent window title
  - *Steps:* Call `find_window_by_title("NonExistentWindow12345", timeout=0.2)`.
  - *Assertion:* Returns `None` cleanly without hanging or raising exceptions.

---

### Tier 5: Semantic Accessibility Plane (UIA) (`TASK-057` - `TASK-070`)

- **`TASK-057` — UIAutomation COM Plane Initialization**
  - *Steps:* Initialize `CUIAutomation8` instance with thread safety.
  - *Assertion:* Connected in < 2ms; memory stable.
- **`TASK-058` — Window Interactive Element Hierarchy Inspection**
  - *Target:* Active document or utility window
  - *Steps:* Inspect window interactive elements with `max_elements=50`.
  - *Assertion:* Returns controls (Buttons, Edits, CheckBoxes, Menus) with bounding boxes.
- **`TASK-059` — Semantic Element Filtering (Interactive vs Passive)**
  - *Steps:* Inspect window with `interactive_only=True`.
  - *Assertion:* Filters out decorative panels, static text labels, and scroll containers.
- **`TASK-060` — Element Search by Name Substring**
  - *Steps:* Call `find_element(query="File")`.
  - *Assertion:* Resolves element with matching Name property.
- **`TASK-061` — Element Search by AutomationId**
  - *Steps:* Query element using exact `AutomationId` (e.g. `"num5Button"` in Calculator).
  - *Assertion:* Resolves target element in O(1) time.
- **`TASK-062` — Direct COM InvokePattern Activation**
  - *Target:* Accessible button element
  - *Steps:* Call `invoke_element(element_id)`.
  - *Assertion:* Fires `IUIAutomationInvokePattern::Invoke` in < 1ms without mouse movement.
- **`TASK-063` — Physical Mouse Click Fallback for Non-Invokable Controls**
  - *Target:* Element lacking InvokePattern
  - *Steps:* Call `invoke_element` on element lacking invoke provider.
  - *Assertion:* Computes geometric center of bounding box and dispatches physical click.
- **`TASK-064` — Offscreen Element Filtering**
  - *Steps:* Inspect scrollable view with elements below view boundary.
  - *Assertion:* Elements with `is_offscreen=True` flagged appropriately.
- **`TASK-065` — Set-of-Mark Integer ID Allocation & Mapping**
  - *Steps:* Query elements; verify mapping dictionary.
  - *Assertion:* Every integer ID maps uniquely to a valid `UIElement` cache entry.
- **`TASK-066` — UIAutomation Tree Timeout Guard**
  - *Target:* Heavy or complex desktop app (e.g. Visual Studio / Word)
  - *Steps:* Inspect deeply nested hierarchy.
  - *Assertion:* Search terminates cleanly at max depth / element count without blocking thread.
- **`TASK-067` — Comtypes Cache Directory Portability**
  - *Steps:* Initialize UIA in environments with read-only program files.
  - *Assertion:* Directs comtypes generated modules to user writable `%APPDATA%` path.
- **`TASK-068` — Element Bounding Box Normalization**
  - *Steps:* Inspect elements; normalize bounding box coordinates.
  - *Assertion:* Bounding box maps to normalized screen space.
- **`TASK-069` — Disabled Element State Detection**
  - *Steps:* Inspect form containing disabled / greyed out controls.
  - *Assertion:* `is_enabled=False` detected accurately.
- **`TASK-070` — Accessibility Plane Disconnection & COM Release**
  - *Steps:* Release COM references during shutdown.
  - *Assertion:* COM runtime uninitialized without memory leaks.

---

### Tier 6: Headless Web & Browser Fast-Path (`TASK-071` - `TASK-084`)

- **`TASK-071` — Microsoft Edge Fast Navigation**
  - *Steps:* Execute `extra_browser(action="navigate", url="https://extra.yantraos.com/")`.
  - *Assertion:* Page loaded; returns status code 200 and duration < 1000ms.
- **`TASK-072` — Clean Semantic Markdown Extraction**
  - *Steps:* Execute `extra_browser(action="content")`.
  - *Assertion:* Returns clean markdown text without HTML script/style noise.
- **`TASK-073` — CSS Selector Direct Click**
  - *Steps:* Execute `extra_browser(action="click", selector="button.cta-primary")`.
  - *Assertion:* Target element clicked cleanly in headless DOM.
- **`TASK-074` — Form Input Text Typing via Selector**
  - *Steps:* Execute `extra_browser(action="fill", selector="input[name='q']", value="Extra OS")`.
  - *Assertion:* Input populated directly in DOM without SendInput latency.
- **`TASK-075` — In-Page JavaScript Evaluation**
  - *Steps:* Execute `extra_browser(action="eval", value="document.title")`.
  - *Assertion:* Returns evaluated JavaScript result string.
- **`TASK-076` — Web Page Screenshot Capture**
  - *Steps:* Execute `extra_browser(action="screenshot")`.
  - *Assertion:* Returns clean base64 image data of web viewport.
- **`TASK-077` — Financial Quotes Direct Extraction (Edge Live URL)**
  - *Target:* Google Finance live market quote
  - *Steps:* Navigate to quote URL; extract financial numbers directly.
  - *Assertion:* Market quote extracted in < 800ms; zero reverse-engineering required.
- **`TASK-078` — Cookie Banner / Consent Dismissal**
  - *Steps:* Navigate to site presenting cookie dialog; dismiss via selector or `esc`.
  - *Assertion:* Main page content accessible.
- **`TASK-079` — Browser Multi-Tab Management**
  - *Steps:* Open second tab; switch between tabs; close tab.
  - *Assertion:* Tab contexts maintained without session collision.
- **`TASK-080` — Network Timeout & Offline Resilience**
  - *Steps:* Navigate to non-resolving domain `https://invalid.domain.xyz123`.
  - *Assertion:* Returns structured failure message within timeout threshold.
- **`TASK-081` — Browser Instance Teardown & Process Cleanup**
  - *Steps:* Call `extra_browser(action="close")`.
  - *Assertion:* Headless browser processes terminated cleanly.
- **`TASK-082` — User-Agent & Desktop Viewport Emulation**
  - *Steps:* Inspect viewport width and user-agent string.
  - *Assertion:* Standard 1920x1080 desktop profile rendered; avoids mobile redirects.
- **`TASK-083` — Web Page Scroll Navigation via Browser API**
  - *Steps:* Evaluate `window.scrollTo(0, 1000)`.
  - *Assertion:* Viewport scroll updated without hardware mouse scrolling.
- **`TASK-084` — File Download Capture & Workspace Routing**
  - *Steps:* Trigger file download in browser.
  - *Assertion:* File saved to `%USERPROFILE%\.extra\workspace\downloads\`.

---

### Tier 7: StallBreaker Resilience & Guardrails (`TASK-085` - `TASK-098`)

- **`TASK-085` — Strike 1 Escalation (Focus Re-anchor & ESC Dismissal)**
  - *Steps:* Trigger repeated non-responsive action on modal dialog.
  - *Assertion:* Strike count increments to 1; fires `esc` and re-focuses active window.
- **`TASK-086` — Strike 2 Escalation (Fast-Path Fallback Activation)**
  - *Steps:* Trigger second non-responsive action.
  - *Assertion:* Strike count increments to 2; switches from GUI click to fast-path / hotkey.
- **`TASK-087` — Strike 3 Escalation (Emergency Safety Abort)**
  - *Steps:* Trigger third repeated non-responsive action.
  - *Assertion:* Raises `EmergencyAbortError`; halts execution to prevent infinite loop.
- **`TASK-088` — StallBreaker Strike Counter Reset on Successful Action**
  - *Steps:* Trigger 1 strike; execute successful action (`extra_launch` or valid click).
  - *Assertion:* Strike counter resets to 0 immediately.
- **`TASK-089` — Loop Detection on Identical Consecutive Actions**
  - *Steps:* Dispatch 4 identical mouse clicks at the exact same pixel coordinates.
  - *Assertion:* Loop detector flags repetitive stall; initiates escalation.
- **`TASK-090` — Canva Link Popup Tunnel Vision Guard**
  - *Target:* Canva Desktop App
  - *Steps:* Simulate accidental `Ctrl+N` opening "Open a design link:" dialog.
  - *Assertion:* Detects invalid link error; sends `esc` once; navigates back to main home icons.
- **`TASK-091` — Windows Photos UWP File System Error Fallback**
  - *Target:* `ms-photos:`
  - *Steps:* Simulate Photos file system launch failure.
  - *Assertion:* Dismisses error dialog via `esc` in < 1s; immediately falls back to `mspaint.exe`.
- **`TASK-092` — Zero Modular Test Script Prohibition Enforcer**
  - *Steps:* Detect agent attempting to write `test_*.py` exploratory scripts during computer use.
  - *Assertion:* Blocked by protocol; enforces direct MCP tool usage.
- **`TASK-093` — Zero System Admin Rabbit Hole Enforcer**
  - *Steps:* Detect attempt to execute `Reset-AppxPackage`, registry edits, or Event Viewer crawling.
  - *Assertion:* Strictly prohibited by guardrails; falls back to standard Win32 alternative.
- **`TASK-094` — Unresponsive Window Heartbeat Monitor**
  - *Steps:* Target window hanging or frozen in Win32 message loop.
  - *Assertion:* `IsHungAppWindow` detected; avoids infinite freeze.
- **`TASK-095` — Safe State Recovery After Unexpected Crash**
  - *Steps:* Terminate target application unexpectedly during multi-step workflow.
  - *Assertion:* Extra catches process termination and reports structured error without hanging.
- **`TASK-096` — Anti-Stall Guardrail Logging & Auditing**
  - *Steps:* Inspect logged stall events.
  - *Assertion:* Ingested cleanly into KùzuDB memory table for continuous evolution.
- **`TASK-097` — Dynamic Timeout Calibration**
  - *Steps:* Benchmark timeout adaptability across slow vs fast launching applications.
  - *Assertion:* Adaptive polling respects upper bound without unnecessary sleep delays.
- **`TASK-098` — User Interruption / Ctrl+C Safety Handling**
  - *Steps:* Send interruption signal during active input injection.
  - *Assertion:* Releases held modifiers and mouse buttons cleanly.

---

### Tier 8: KùzuDB Graph Memory & FastEmbed (`TASK-099` - `TASK-112`)

- **`TASK-099` — Sovereign Memory Database Initialization (`~/.extra/memory/`)**
  - *Steps:* Initialize embedded KùzuDB graph store at default sovereign path.
  - *Assertion:* Creates `graph.kuzu` with node tables: `Task`, `Step`, `App`, `Artifact`, `Stall`, `AppQuirk`.
- **`TASK-100` — FastEmbed ONNX Local Embedding Engine (`BAAI/bge-small-en-v1.5`)**
  - *Steps:* Generate 384-dimensional dense vector for task query string.
  - *Assertion:* Generates normalized float vector in < 25ms locally without internet connectivity.
- **`TASK-101` — Full Task Trajectory Atomic Ingestion**
  - *Steps:* Record multi-step workflow with tools, parameters, durations, and commit to DB.
  - *Assertion:* Task node and Step nodes created and linked via `[:CONSISTS_OF]`.
- **`TASK-102` — Application Node Linkage (`[:INTERACTED_WITH]`)**
  - *Steps:* Associate `App` node (`"canva"`, `"calc"`) with committed `Task`.
  - *Assertion:* Graph query verifies `(Task)-[:INTERACTED_WITH]->(App)` relationship.
- **`TASK-103` — Artifact Node Linkage (`[:PRODUCED]`)**
  - *Steps:* Register created file artifact (`briefing.txt` or `chart.png`).
  - *Assertion:* Artifact node created with size, mime type, and linked to Task.
- **`TASK-104` — Stall Event Linkage (`[:ENCOUNTERED]`)**
  - *Steps:* Record StallBreaker strike into task recorder.
  - *Assertion:* Graph links `(Task)-[:ENCOUNTERED]->(Stall)` with strike count and trigger.
- **`TASK-105` — App Quirk & Playbook Ingestion (`[:EXHIBITS]`)**
  - *Steps:* Record application quirk (issue, workaround, playbook).
  - *Assertion:* Linked to target App; queryable by future task planners.
- **`TASK-106` — Vector Cosine Similarity Search (`extra_recall_memory`)**
  - *Steps:* Query memory with semantic prompt: `"how to make instagram graphic in canva"`.
  - *Assertion:* Returns most relevant prior task trajectory in < 5ms with similarity score > 0.70.
- **`TASK-107` — Multi-Condition Memory Filtering (App + Success)**
  - *Steps:* Query memory filtered by `app_name="canva"` and `success=True`.
  - *Assertion:* Scopes results exclusively to verified successful workflows.
- **`TASK-108` — Memory Database Thread Safety & Connection Pooling**
  - *Steps:* Dispatch concurrent read/write queries across 4 worker threads.
  - *Assertion:* Thread lock coordinates transactions cleanly; zero lock contention errors.
- **`TASK-109` — Memory Database Re-Open & Persistence Across Process Restarts**
  - *Steps:* Write record, close DB connection, re-instantiate DB connection, query record.
  - *Assertion:* All nodes, embeddings, and relationships persist intact.
- **`TASK-110` — Memory Query Benchmarking (< 10ms SLA)**
  - *Steps:* Benchmark 50 consecutive memory recalls against 1,000 embedded nodes.
  - *Assertion:* Average query latency remains under 5ms.
- **`TASK-111` — Embedding Cache & Deduplication**
  - *Steps:* Query embedding for identical string twice.
  - *Assertion:* Returns cached vector immediately without redundant ONNX inference.
- **`TASK-112` — Sovereign Directory CFA Immunity Verification**
  - *Steps:* Verify read/write permissions on `~/.extra/memory/` under Controlled Folder Access.
  - *Assertion:* 100% exempt from CFA ransomware blocks; zero Defender warnings.

---

### Tier 9: JIT Scout & Skill Synthesis (`TASK-113` - `TASK-124`)

- **`TASK-113` — Viewport Application Framework Detection (Blender / Maya / Unreal)**
  - *Target:* `blender.exe`
  - *Steps:* Detect framework of Blender installation.
  - *Assertion:* Identifies `directx_opengl_viewport`; notes lack of Win32 UIA accessibility nodes.
- **`TASK-114` — Web/Electron Canvas Framework Detection (Canva / Figma)**
  - *Target:* `Canva.exe`
  - *Steps:* Detect framework of Canva desktop app.
  - *Assertion:* Identifies `electron_web_canvas`; warns against UIA inner canvas clicking.
- **`TASK-115` — Native Win32 / UWP Application Detection (Notepad / Calc)**
  - *Target:* `notepad.exe` / `calc.exe`
  - *Steps:* Detect framework of standard Windows tools.
  - *Assertion:* Accurately identifies native Win32 / UWP; notes direct input typing.
- **`TASK-116` — Non-Blocking CLI Flag Probing (`--help` / `-h` / `/?`)**
  - *Target:* Installed CLI tools (e.g. `blender.exe -b -h`, `vlc.exe -H`)
  - *Steps:* Probe CLI parameters with strict 1.5s timeout.
  - *Assertion:* Captures CLI help text safely without hanging or spawning visible GUI.
- **`TASK-117` — Universal Shortcuts & Hotkey Intelligence Retrieval**
  - *Steps:* Query curated intelligence for Canva, Blender, VLC, Notepad.
  - *Assertion:* Returns verified hotkeys (e.g. `T` for text, `R` for rectangle, `Space` for play/pause).
- **`TASK-118` — agentskills.io Compliant SKILL.md Markdown Synthesis**
  - *Target:* Scouted application
  - *Steps:* Synthesize complete `SKILL.md` markdown with YAML frontmatter.
  - *Assertion:* Contains name, description, architecture caveats, fast-paths, hotkeys, and guardrails.
- **`TASK-119` — Multi-Directory Skill Distribution**
  - *Steps:* Verify scout writes `SKILL.md` to workspace `.agents/skills/`, user `.gemini/config/skills/`, and `.extra/skills/`.
  - *Assertion:* Written atomically to all active agent skill search directories.
- **`TASK-120` — Automatic Shell Registry Integration During Scout**
  - *Steps:* Scout unindexed application on disk.
  - *Assertion:* App automatically registered into `APP_REGISTRY` and saved to `app_registry.json`.
- **`TASK-121` — Automatic KùzuDB Quirk & Playbook Ingestion During Scout**
  - *Steps:* Complete scout run.
  - *Assertion:* Discovered fast-path ingested as `AppQuirk` node into KùzuDB memory.
- **`TASK-122` — Scout Cache Validation & Force-Refresh Flag**
  - *Steps:* Run scout twice; verify second run returns `"status": "cached"`; test `force_refresh=True`.
  - *Assertion:* Respects cache unless force refresh is explicitly requested.
- **`TASK-123` — Custom Notes Injection into Synthesized Playbook**
  - *Steps:* Pass `custom_notes="Always export as MP4 with 1080p"` to scout.
  - *Assertion:* Custom rule incorporated into synthesized SKILL.md under Fast-Paths.
- **`TASK-124` — Scout Fallback for Non-Installed / Web Tools**
  - *Steps:* Scout web-only application (e.g. `linear`, `notion`).
  - *Assertion:* Generates web-in-browser playbook gracefully.

---

### Tier 10: Multi-App Cross-Desktop Workflows (`TASK-125` - `TASK-136`)

- **`TASK-125` — Edge Research to Notepad Briefing Orchestration**
  - *Apps:* `edge` + `notepad`
  - *Steps:* Extract summary from web page via Edge fast-path, write markdown brief to disk, open in Notepad.
  - *Assertion:* Both applications complete workflow in < 3s total.
- **`TASK-126` — Side-by-Side Dual-App Split Screen Docking**
  - *Apps:* `mspaint` (Left) + `notepad` (Right)
  - *Steps:* Launch Paint with generated chart, snap Left (`Win+Left`); launch Notepad with report, snap Right (`Win+Right`).
  - *Assertion:* Windows split 50/50 cleanly across display with zero title bar dragging.
- **`TASK-127` — Edge Live Financial Quote -> Calculator Computation -> Report**
  - *Apps:* `edge` + `calc` + `notepad`
  - *Steps:* Extract live stock price in Edge, compute target valuation in Calculator via instant typing, write report in Notepad.
  - *Assertion:* Calculations match live quote numbers; screenshot captures final state.
- **`TASK-128` — Python PIL Chart Generation -> MS Paint Visual Presentation**
  - *Apps:* Python (PIL) + `mspaint`
  - *Steps:* Generate clean high-res 1200x800 analytics PNG chart to `%USERPROFILE%\.extra\workspace\chart.png`, launch Paint.
  - *Assertion:* Paint displays crisp vector-quality chart; zero shaky freehand drawing.
- **`TASK-129` — High-Speed Graphic Generation -> Canva STA Clipboard Paste**
  - *Apps:* Python (PIL) + `powershell -STA` + `Canva`
  - *Steps:* Generate launch graphic PNG, copy to Windows Clipboard via PowerShell STA, focus Canva, paste (`Ctrl+V`).
  - *Assertion:* Graphic appears instantly in Canva canvas; avoids WebGL canvas clicking.
- **`TASK-130` — Canva Native Template Discovery & Instagram Format Creation**
  - *Target:* `Canva`
  - *Steps:* Launch Canva, click home screen category icon / search box for "Instagram Post", select template.
  - *Assertion:* Honours user intent to use native Canva templates without forcing scripts.
- **`TASK-131` — VLC Media Player Fast-Path Launch & Hotkey Control**
  - *Target:* `vlc.exe`
  - *Steps:* Launch VLC with test media URI/path, send hotkeys (`Space` to pause/play, `f` for fullscreen).
  - *Assertion:* Media plays deterministically; hotkeys control player instantly.
- **`TASK-132` — Blender Foundation Discovery & Background Python Scripting**
  - *Target:* `blender.exe`
  - *Steps:* Resolve Blender from Program Files / Store, execute headless background render script (`-b -P`).
  - *Assertion:* Renders 3D object to disk; zero GUI viewport pixel-hunting.
- **`TASK-133` — Cross-Application Context Retention via KùzuDB Memory**
  - *Steps:* Start Task A (Edge + Calc); commit to memory. Start Task B; recall Task A context via vector search.
  - *Assertion:* Task B retrieves exact URLs, formulas, and artifacts produced in Task A.
- **`TASK-134` — File Explorer File Management & Visual Verification**
  - *Apps:* File system + `explorer`
  - *Steps:* Create organized directory structure in workspace, copy report artifacts, open in Explorer.
  - *Assertion:* Explorer displays generated files in foreground.
- **`TASK-135` — Triple-Window Desktop Arrangement (Grid / Stack)**
  - *Apps:* `edge` + `calc` + `notepad`
  - *Steps:* Launch and arrange three windows in foreground across display.
  - *Assertion:* All windows remain visible; no window minimized or hidden.
- **`TASK-136` — Full Multi-App Trajectory Evolution & Crystallization**
  - *Steps:* Execute multi-app workflow, analyze trajectory, call `extra_evolve_skill` to crystallize playbook.
  - *Assertion:* Updated playbook committed to skill library and memory graph.

---

### Tier 11: Security, Controlled Folder Access (CFA) & Safety (`TASK-137` - `TASK-144`)

- **`TASK-137` — Controlled Folder Access (CFA) Strict Directory Boundary**
  - *Steps:* Verify all file creation targets `%USERPROFILE%\.extra\workspace\` or repository roots.
  - *Assertion:* Zero attempts to write to `%USERPROFILE%\Documents`, `\Pictures`, or `\Desktop`.
- **`TASK-138` — Ransomware Protection Event 1123 Non-Trigger Guarantee**
  - *Steps:* Execute full file export suite while Windows Defender Ransomware Protection is enabled.
  - *Assertion:* Zero Event 1123 security alerts logged; zero user security toast popups.
- **`TASK-139` — Window Destruction Prohibition Enforcer**
  - *Steps:* Verify agent execution across all tasks.
  - *Assertion:* Never calls `.terminate()`, `taskkill`, or `kill` on user-requested applications.
- **`TASK-140` — Non-Elevated Standard User Execution Safety**
  - *Steps:* Run Extra under non-administrator user context.
  - *Assertion:* Functions cleanly without requiring UAC privilege escalation.
- **`TASK-141` — Zero Modular Test Script Prohibition Audit**
  - *Steps:* Audit active directory during and after task execution.
  - *Assertion:* Zero `test_coords.py`, `check_fg.py`, or exploratory scrapers created.
- **`TASK-142` — Zero System Repair Rabbit Hole Audit**
  - *Steps:* Inject simulated application failure.
  - *Assertion:* Agent refuses to execute `Reset-AppxPackage` or registry fixes; falls back cleanly.
- **`TASK-143` — Windows Audio Indicator & Chime Acoustic Feedback**
  - *Steps:* Execute task start and completion signals.
  - *Assertion:* Plays subtle Win32 acoustic chime (`MessageBeep` / wave sound) on completion.
- **`TASK-144` — Ambient Border Overlay Lifecycle & Clean Dissolve**
  - *Steps:* Fire task start, pulse, and complete.
  - *Assertion:* Ambient overlay indicator appears during task and dissolves completely on finish.

---

### Tier 12: Dynamic App Registry & Persistence (`TASK-145` - `TASK-150`)

- **`TASK-145` — Dynamic In-Memory App Registration (`register_app`)**
  - *Steps:* Register new application alias with executable target.
  - *Assertion:* Added to `APP_REGISTRY` in-memory; accessible in O(1) time.
- **`TASK-146` — User Registry Disk Persistence (`%USERPROFILE%\.extra\app_registry.json`)**
  - *Steps:* Register app with `persist=True`.
  - *Assertion:* Atomic JSON file write to disk; valid JSON structure with target, type, and proc.
- **`TASK-147` — Cold-Start Registry Loading on System Restart**
  - *Steps:* Populate user registry file, re-import shell launcher module.
  - *Assertion:* All custom applications loaded into `APP_REGISTRY` on module initialization.
- **`TASK-148` — Automatic Registration of Resolved Executables**
  - *Steps:* Call `resolve_executable` on newly discovered binary path on disk.
  - *Assertion:* Executable stem alias auto-registered in `APP_REGISTRY` and saved to disk.
- **`TASK-149` — Active Window Executable Discovery & Auto-Registration**
  - *Target:* User-opened desktop window
  - *Steps:* Focus window with `extra_focus_window`; query executable path.
  - *Assertion:* Discovers executable path and auto-registers application alias.
- **`TASK-150` — macOS Platform Abstraction Symmetry**
  - *Steps:* Test `register_app`, `load_user_registry`, and `get_registered_apps` on macOS PAL.
  - *Assertion:* Symmetric API functions identically with macOS bundles and JSON persistence.

---

## Verification & Execution Protocol

### 1. Pre-Flight Verification Checks
Before executing the regression harness, verify:
1. Python 3.10+ with `pywin32`, `comtypes`, `pillow`, `kuzu`, `fastembed`, and `playwright`.
2. Windows Display Settings set to standard DPI or ensure DPI awareness is enabled.
3. Sovereign workspace folder `%USERPROFILE%\.extra\workspace\` exists and is writeable.

### 2. Automated Test Execution
Run the automated regression test harness matching these 150 tasks:
```powershell
# Run the complete Universal Task Suite
python -m unittest tests/test_universal_tasksuite.py -v

# Run the complete Extra regression suite (all 1,750+ tests)
python -m unittest discover tests -v
```

### 3. Acceptance Gate for Public Release
A release candidate is approved for public deployment if and only if:
- [x] 100% of all 150 tasks pass without assertion errors.
- [x] Zero regressions detected in the existing unit test suites.
- [x] All opened user applications remain visible and docked side-by-side.
- [x] Zero Windows Defender CFA Event 1123 alerts triggered.
- [x] Dynamic app registry successfully persists and survives cold restarts.
