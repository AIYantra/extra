# Project Extra — Universal Real-Life Computer Use Task Suite (A to Z)
**Version:** 2.0.0-PROD  
**Target Platform:** Windows 10/11 (x64 / ARM64) & macOS Sonoma/Sequoia (Universal PAL)  
**Total Tasks:** 150 Concrete Real-World Computer Use Tasks on the Machine  
**Execution Mode:** Live Desktop Interactive Automation with Zero-Stall Fast Paths  

---

## Executive Summary & Research Context

### 1. The Computer Use Landscape & The "GPT-6 Astra" Dilemma
In late 2026, the AI industry witnessed the rollout of **GPT-6 Astra** (often termed *Astra 6*), accompanied by benchmarks like **OSWorld 2.0** and **ScreenSpot Pro**. While frontier multimodal models have achieved remarkable breakthroughs in perceptual visual reasoning, independent evaluations and enterprise deployments have consistently revealed severe structural failure modes when these pure-vision models attempt unassisted computer use:

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
This **Universal Task Suite (`tasksuite.md`)** is Extra's definitive quality-assurance and regression harness. It defines **150 real, practical, tangible computer use tasks that execute directly on the physical Windows desktop machine across everyday applications from A to Z**.

Unlike unit tests or background scripts, every task in this suite represents a **real-life task on the computer**—such as calculating a financial formula in Calculator, writing an executive brief in Notepad, plotting a chart in Paint, researching equity quotes in Edge, organizing folders in File Explorer, adjusting audio in Settings, playing media in VLC, or designing a poster in Canva.

Any future feature, MCP tool change, or platform upgrade must pass this entire task suite without regressions before being cleared for public release.

---

## Suite Architecture & Category Matrix

| Tier | Domain / Category | Task Range | Target Applications / Subsystems | Primary Real-Life Use Cases |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 1** | Daily Office & Financial Calculations | `TASK-001` - `TASK-015` | `calc`, `notepad`, `explorer`, `settings`, `taskmgr`, `wt` | Sales tax, mortgage EMI, project briefs, file organization |
| **Tier 2** | Visual Perception & Multi-Window Layouts | `TASK-016` - `TASK-028` | DXGI, GDI, DPI scaling, multi-display, crop box | Live screen capture, window metrics, high-DPI scaling |
| **Tier 3** | Live Hardware Input & Keyboard Automation | `TASK-029` - `TASK-042` | `VK_PACKET`, STA clipboard, mouse drag, scroll, hotkeys | Instant unicode typing, Bézier dragging, document scrolling |
| **Tier 4** | Window Snapping, Docking & Multitasking | `TASK-043` - `TASK-056` | AttachThreadInput, Win32 HWND, Snap Assist, split-screen | Side-by-side split screen, window restoration, focus locking |
| **Tier 5** | Semantic Accessibility Plane & Control Inspection | `TASK-057` - `TASK-070` | COM UIAutomation, Set-of-Mark, InvokePattern | Button clicking, form inspection, UI tree traversal |
| **Tier 6** | Web Browsing & Online Research | `TASK-071` - `TASK-084` | Microsoft Edge, Playwright, markdown extraction | Live financial quotes, article research, web downloads |
| **Tier 7** | StallBreaker Resilience & Error Recovery | `TASK-085` - `TASK-098` | 3-strike escalation, loop detector, ESC handler | Popup dismissal, Canva link trap avoidance, Photos fallback |
| **Tier 8** | KùzuDB Graph Memory & FastEmbed Intelligence | `TASK-099` - `TASK-112` | KùzuDB, BAAI/bge-small-en-v1.5 ONNX, cosine recall | Workflow recall, cross-app context, application quirks |
| **Tier 9** | JIT Application Scouting & Skill Synthesis | `TASK-113` - `TASK-124` | Framework detector, CLI probe, SKILL.md generator | App scouting, universal hotkeys, automated SKILL.md |
| **Tier 10**| Multi-App Cross-Desktop Professional Workflows | `TASK-125` - `TASK-136` | Edge + Calc + Notepad + Canva + VLC + Explorer | End-to-end research, dual-docking, social poster creation |
| **Tier 11**| Security, Controlled Folder Access (CFA) & Safety | `TASK-137` - `TASK-144` | Defender CFA compliance, zero-scripting rule | Ransomware protection compliance, ambient overlays, chime |
| **Tier 12**| Dynamic App Registry & Cold Restart Persistence | `TASK-145` - `TASK-150` | `~/.extra/app_registry.json`, cold-start loader | Dynamic app registration, path resolution, OS symmetry |

---

## Detailed Task Catalog (150 Real-Life Computer Use Tasks)

### Tier 1: Daily Office & Financial Calculations (`TASK-001` - `TASK-015`)

- **`TASK-001` — Commercial Sales Commission & VAT Calculation in Calculator**
  - *Real-World Scenario:* A sales manager wants to calculate the final invoice total on an enterprise software sale of $4,500 with 18% VAT and leave the result clearly visible on screen.
  - *Target App:* `calc.exe`
  - *Live Actions:* Launch Calculator (`extra_launch("calc")`), focus window (`extra_focus_window("Calculator")`), type mathematical formula `4500*1.18=` via instant typing (`extra_type`), capture screenshot (`extra_screenshot`).
  - *Desktop State:* Windows Calculator displays `5,310` in foreground.
  - *Fast-Path / Guardrail:* Never pass `use_clipboard=True` to Calculator (avoids "Invalid input" error).

- **`TASK-002` — Compound Loan EMI Calculation in Scientific Calculator**
  - *Real-World Scenario:* Compute monthly payment estimate for a $120,000 loan over 36 months at 7.5% annual interest.
  - *Target App:* `calc.exe`
  - *Live Actions:* Launch Calculator, switch to scientific mode if needed, type `120000*(1+0.075/12)^36=`.
  - *Desktop State:* Calculator displays the computed maturity balance cleanly.
  - *Fast-Path / Guardrail:* Instant typing calculates in < 5ms without clicking digit buttons individually.

- **`TASK-003` — Executive Project Briefing Draft in Notepad**
  - *Real-World Scenario:* A tech lead needs a 5-point executive briefing on "Project Sovereign Architecture" opened in Notepad for review.
  - *Target App:* `notepad.exe`
  - *Live Actions:* Programmatically write formatted briefing text directly to `%USERPROFILE%\.extra\workspace\briefing_003.txt`, visibly launch Notepad with file path argument (`extra_launch("notepad", ["C:\\Users\\...\\briefing_003.txt"])`), focus window.
  - *Desktop State:* Notepad window appears in foreground displaying title, summary, key deliverables, and milestones.
  - *Fast-Path / Guardrail:* Safe directory boundary at `%USERPROFILE%\.extra\workspace\`; zero character-by-character slow typing.

- **`TASK-004` — Meeting Minutes & Action Items Documentation in Notepad**
  - *Real-World Scenario:* Generate structured meeting minutes with attendees, decisions made, and assigned owners, open in Notepad.
  - *Target App:* `notepad.exe`
  - *Live Actions:* Write minutes markdown file to workspace, launch Notepad pointing to file.
  - *Desktop State:* Notepad displays formatted meeting notes ready for copy or distribution.
  - *Fast-Path / Guardrail:* Writing directly to disk prevents clipboard races and typing typos.

- **`TASK-005` — Multi-Document Tabbed Review in Windows 11 Notepad**
  - *Real-World Scenario:* Open two separate legal contract briefs simultaneously in Notepad to verify Windows 11 tabbed interface support.
  - *Target App:* `notepad.exe`
  - *Live Actions:* Launch `contract_a.txt`, then launch `contract_b.txt` in Notepad.
  - *Desktop State:* Both documents open cleanly in Notepad tabs or separate windows without title collision.
  - *Fast-Path / Guardrail:* Uses substring window title matching rather than exact file name.

- **`TASK-006` — Project Workspace Scaffolding in File Explorer**
  - *Real-World Scenario:* Create an organized folder structure `Project_Delta_2026/` with subdirectories `docs/`, `data/`, `exports/`, and open it in File Explorer.
  - *Target App:* `explorer.exe`
  - *Live Actions:* Create directories in `%USERPROFILE%\.extra\workspace\Project_Delta_2026\`, visibly launch Explorer pointing to the folder (`extra_launch("explorer", ["<path>"])`).
  - *Desktop State:* Windows File Explorer opens directly displaying the newly created folders.
  - *Fast-Path / Guardrail:* Direct path parameter launch avoids slow graphical folder clicking.

- **`TASK-007` — Bulk File Archiving & Moving in File Explorer**
  - *Real-World Scenario:* Move weekly report files into an `archive/` folder and inspect them in File Explorer.
  - *Target App:* `explorer.exe`
  - *Live Actions:* Move `.txt` and `.png` artifacts into archive subdirectory, open Explorer to folder.
  - *Desktop State:* File Explorer displays the organized files with updated timestamps.
  - *Fast-Path / Guardrail:* Filesystem operations execute in < 2ms; Explorer reveals result visually.

- **`TASK-008` — Network Adapter & Connection Status Inspection in Windows Settings**
  - *Real-World Scenario:* Check current Wi-Fi/Ethernet status and IP configuration by opening Windows Network Settings.
  - *Target App:* `SystemSettings.exe` (`ms-settings:network`)
  - *Live Actions:* Launch `extra_launch("ms-settings:network")`, focus window (`extra_focus_window("Settings")`).
  - *Desktop State:* Windows Settings opens directly to the Network & Internet page.
  - *Fast-Path / Guardrail:* Deep URI activation bypasses 5+ layers of Settings UI clicking.

- **`TASK-009` — Display Resolution & Scaling Inspection in Windows Settings**
  - *Real-World Scenario:* Open display settings to verify monitor scale factor and layout.
  - *Target App:* `SystemSettings.exe` (`ms-settings:display`)
  - *Live Actions:* Launch `extra_launch("ms-settings:display")`, focus window.
  - *Desktop State:* Windows Settings displays the Scale & Layout configuration.
  - *Fast-Path / Guardrail:* Instant URI protocol navigation in < 1500ms.

- **`TASK-010` — Audio Output Device Configuration in Windows Settings**
  - *Real-World Scenario:* Verify audio output device settings prior to a media presentation.
  - *Target App:* `SystemSettings.exe` (`ms-settings:sound`)
  - *Live Actions:* Launch `extra_launch("ms-settings:sound")`, focus window.
  - *Desktop State:* Windows Settings opens directly to Sound options.
  - *Fast-Path / Guardrail:* Zero vision pixel-hunting.

- **`TASK-011` — Storage Space & Temporary Files Audit in Windows Settings**
  - *Real-World Scenario:* Inspect system drive capacity and temporary files breakdown.
  - *Target App:* `SystemSettings.exe` (`ms-settings:storagesense`)
  - *Live Actions:* Launch `extra_launch("ms-settings:storagesense")`, focus window.
  - *Desktop State:* Windows Settings displays Installed Apps, Temporary Files, and Storage breakdown.
  - *Fast-Path / Guardrail:* Native Windows URI handles deep navigation deterministically.

- **`TASK-012` — Real-Time Process Resource Inspection in Task Manager**
  - *Real-World Scenario:* Open Task Manager to inspect system CPU, RAM, and active processes.
  - *Target App:* `taskmgr.exe`
  - *Live Actions:* Launch Task Manager via `extra_launch("taskmgr")`, bring to front.
  - *Desktop State:* Windows Task Manager opens displaying live process performance.
  - *Fast-Path / Guardrail:* Handles standard privilege elevation gracefully.

- **`TASK-013` — Productivity Tool Discovery in Microsoft Store**
  - *Real-World Scenario:* Open Microsoft Store searching for a trusted utility application (e.g. VLC or PowerToys).
  - *Target App:* `ms-windows-store:`
  - *Live Actions:* Launch protocol URI `ms-windows-store://search?query=vlc`, focus window.
  - *Desktop State:* Microsoft Store opens with the search query prepopulated.
  - *Fast-Path / Guardrail:* Deep search URI prevents manual search bar typing.

- **`TASK-014` — Quick System Diagnostics in Windows Terminal / PowerShell**
  - *Real-World Scenario:* Launch Windows Terminal or PowerShell to check hostname and IP configuration.
  - *Target App:* `wt.exe` / `powershell.exe`
  - *Live Actions:* Launch terminal via fast-path launcher, focus window, enter diagnostic query.
  - *Desktop State:* Terminal window active and receiving keyboard input.
  - *Fast-Path / Guardrail:* WindowsApps alias resolution handles packaged Terminal without PATH issues.

- **`TASK-015` — Safe Shell Fallback for Unknown Application Queries**
  - *Real-World Scenario:* User asks to open an uninstalled app; system returns clear structured diagnosis instead of crashing.
  - *Live Actions:* Query unindexed application name, capture structured failure response.
  - *Desktop State:* Returns informative error within 10ms; zero system freezing.
  - *Fast-Path / Guardrail:* Zero unhandled exceptions.

---

### Tier 2: Visual Perception & Multi-Window Desktop Layouts (`TASK-016` - `TASK-028`)

- **`TASK-016` — High-Speed Full-Desktop Screenshot Capture**
  - *Real-World Scenario:* Capture a crisp, full-desktop screenshot to verify user desktop layout.
  - *Live Actions:* Call `extra_screenshot(annotate_ui=False, save_to_file=True)`.
  - *Desktop State:* Desktop captured via DXGI / GDI in < 15ms; saved cleanly to workspace.
  - *Fast-Path / Guardrail:* Direct hardware screen buffer capture avoids slow screen-grabbing scripts.

- **`TASK-017` — Multi-Monitor Desktop Topology & DPI Discovery**
  - *Real-World Scenario:* Detect all connected displays, resolutions, primary monitor flag, and per-monitor DPI.
  - *Live Actions:* Query display metrics engine (`get_monitors_info()`).
  - *Desktop State:* Returns complete monitor map with coordinates and DPI scaling factors.
  - *Fast-Path / Guardrail:* Per-Monitor DPI Awareness v2 prevents coordinate drift across mixed displays.

- **`TASK-018` — Window Interactive Center Calculation**
  - *Real-World Scenario:* Calculate the exact center point of an active foreground window for precise user interaction.
  - *Live Actions:* Query active window bounding rectangle `(left, top, right, bottom)`, compute `(x_center, y_center)`.
  - *Desktop State:* Exact physical pixel coordinates returned.
  - *Fast-Path / Guardrail:* Math based on true Win32 window geometry.

- **`TASK-019` — Region-of-Interest (ROI) Sub-Frame Window Capture**
  - *Real-World Scenario:* Crop and inspect only the active Calculator or document window without capturing private background apps.
  - *Live Actions:* Call screen capture with target bounding box `[left, top, right, bottom]`.
  - *Desktop State:* High-resolution sub-image generated in < 5ms.
  - *Fast-Path / Guardrail:* Zero unnecessary token waste from transmitting full 4K desktop frames.

- **`TASK-020` — High-DPI Display Scaling Coordinate Adjustment (150% Scale)**
  - *Real-World Scenario:* User runs a 1440p or 4K laptop display set to 150% Windows scaling.
  - *Live Actions:* Normalize and denormalize coordinates through the DPI transformation engine.
  - *Desktop State:* Mouse actions hit the exact intended control center without 50px offset errors.
  - *Fast-Path / Guardrail:* Physical-to-logical transformation handled transparently.

- **`TASK-021` — Screen Change & Motion Detection on Content Update**
  - *Real-World Scenario:* Verify that Calculator has finished computing or a web page has finished loading by comparing consecutive frames.
  - *Live Actions:* Capture two sequential frames; compute perceptual hash difference.
  - *Desktop State:* State transition detected deterministically.
  - *Fast-Path / Guardrail:* Sub-pixel rendering differences filtered out to avoid false motion triggers.

- **`TASK-022` — Set-of-Mark (SoM) Interactive Element Tagging**
  - *Real-World Scenario:* Annotate all interactive buttons and inputs on the screen with clear numbered badges.
  - *Live Actions:* Call `extra_screenshot(annotate_ui=True)`.
  - *Desktop State:* Screenshot generated with high-contrast numbered bounding boxes on clickable elements.
  - *Fast-Path / Guardrail:* Clean visual markers make vision-assisted clicking effortless.

- **`TASK-023` — Hardware-Accelerated Video Surface Capture**
  - *Real-World Scenario:* Capture desktop while hardware-accelerated video playback is active in VLC or Edge.
  - *Live Actions:* Capture screen via DXGI desktop duplication surface.
  - *Desktop State:* Video frame captured clearly; zero black/blank rectangles.
  - *Fast-Path / Guardrail:* Bypasses GDI hardware overlay capture limitations.

- **`TASK-024` — Minimized Window State Detection**
  - *Real-World Scenario:* Check whether an application is currently minimized to the taskbar before attempting to interact.
  - *Live Actions:* Inspect Win32 `WS_MINIMIZE` / `IsIconic` state for target HWND.
  - *Desktop State:* Minimized state detected; allows automatic `SW_RESTORE` before interaction.
  - *Fast-Path / Guardrail:* Eliminates clicks into empty desktop space.

- **`TASK-025` — Foreground Window Title & Process Verification**
  - *Real-World Scenario:* Confirm which window currently has active keyboard focus.
  - *Live Actions:* Call `get_foreground_window()`, extract title, process ID, and rect bounds.
  - *Desktop State:* Returns accurate active window metadata.
  - *Fast-Path / Guardrail:* Direct Win32 API call in < 1ms.

- **`TASK-026` — Multi-Display Boundary Clamping**
  - *Real-World Scenario:* Prevent mouse cursor from drifting into non-existent virtual desktop coordinates.
  - *Live Actions:* Clamp extreme coordinates `(-500, 10000)` against virtual desktop bounding rect.
  - *Desktop State:* Coordinates safely restricted to physical display pixels.
  - *Fast-Path / Guardrail:* Zero cursor teleportation or out-of-bounds exceptions.

- **`TASK-027` — Zero-Leak Continuous Screen Capture Benchmark**
  - *Real-World Scenario:* Run 100 consecutive screen captures during a long-running live automation session.
  - *Live Actions:* Loop screen captures in succession, monitoring process RAM.
  - *Desktop State:* Memory remains flat; GDI bitmaps and device contexts freed immediately.
  - *Fast-Path / Guardrail:* Strict `DeleteObject` and `ReleaseDC` cleanup.

- **`TASK-028` — Desktop Cleanliness & Top-Level Window Filtering**
  - *Real-World Scenario:* Filter out hidden background helper windows, tooltips, and zero-size cloaked processes.
  - *Live Actions:* Enumerate visible top-level windows (`list_windows(visible_only=True)`).
  - *Desktop State:* Returns only user-visible application windows.
  - *Fast-Path / Guardrail:* Clean window catalog for navigation.

---

### Tier 3: Live Hardware Input & Keyboard Automation (`TASK-029` - `TASK-042`)

- **`TASK-029` — Instant Win32 Unicode Typing in Active Document**
  - *Real-World Scenario:* Rapidly inject a paragraph containing punctuation, numbers, and symbols into Notepad.
  - *Target App:* `notepad.exe`
  - *Live Actions:* Focus Notepad, inject text `Project Extra: High-Speed Desktop Automation (v2.0) @ 100% Reliability!` via `extra_type`.
  - *Desktop State:* Text appears instantly in Notepad in < 5ms without character drops.
  - *Fast-Path / Guardrail:* Uses `KEYEVENTF_UNICODE` (`VK_PACKET`); immune to keyboard layout differences.

- **`TASK-030` — Multilingual & International Text Input**
  - *Real-World Scenario:* Enter international customer names and emojis into a text document.
  - *Target App:* `notepad.exe`
  - *Live Actions:* Inject multilingual text: `Client: 株式会社ソブリン 🚀 | Paris Office: Crème Brûlée | Munich: Weißbier`.
  - *Desktop State:* Unicode characters and emojis render perfectly in Notepad without encoding corruption.
  - *Fast-Path / Guardrail:* Pure UTF-16 code units injected directly into Win32 input queue.

- **`TASK-031` — Text Input with Automatic Enter Key Submission**
  - *Real-World Scenario:* Type a URL or command and automatically press Enter.
  - *Live Actions:* Call `extra_type(text="https://extra.yantraos.com", press_enter=True)`.
  - *Desktop State:* Text entered followed immediately by `VK_RETURN`.
  - *Fast-Path / Guardrail:* Atomic execution eliminates human-slow key delays.

- **`TASK-032` — High-Volume Formatted Table Clipboard Paste**
  - *Real-World Scenario:* Paste a 100-row markdown data table into an active editor.
  - *Live Actions:* Copy text to clipboard via atomic STA clipboard swap, send `Ctrl+V`, restore prior clipboard.
  - *Desktop State:* Full table inserted into document in < 30ms.
  - *Fast-Path / Guardrail:* Bypasses slow typing of thousands of individual characters.

- **`TASK-033` — Clipboard Lock Retry & Race Condition Guard**
  - *Real-World Scenario:* Safely write to the Windows clipboard even when another background tool is monitoring clipboard changes.
  - *Live Actions:* Execute clipboard write with exponential backoff on `CLIPBRD_E_CANT_OPEN`.
  - *Desktop State:* Clipboard updated without application crash.
  - *Fast-Path / Guardrail:* Zero clipboard locking exceptions.

- **`TASK-034` — Precision Mouse Movement & Element Hover**
  - *Real-World Scenario:* Move mouse cursor directly over a toolbar button to trigger tooltip or hover highlight.
  - *Live Actions:* Call `extra_click` or mouse move to target coordinates.
  - *Desktop State:* Cursor moves precisely to button; UI element reflects hover state.
  - *Fast-Path / Guardrail:* Hardware cursor coordinates verified via `GetCursorPos`.

- **`TASK-035` — Right-Click Context Menu Activation**
  - *Real-World Scenario:* Right-click in File Explorer or a document to open the contextual actions menu.
  - *Live Actions:* Call `extra_click(x=..., y=..., button="right")`.
  - *Desktop State:* Native Windows context menu appears at mouse location.
  - *Fast-Path / Guardrail:* Symmetrical `MOUSEEVENTF_RIGHTDOWN` and `MOUSEEVENTF_RIGHTUP` dispatch.

- **`TASK-036` — Precision Double-Click Word Selection**
  - *Real-World Scenario:* Highlight a word in Notepad by double-clicking it.
  - *Live Actions:* Dispatch double click at word coordinates.
  - *Desktop State:* Word is highlighted in blue selection in Notepad.
  - *Fast-Path / Guardrail:* Click interval precisely matches Windows double-click threshold (~100ms).

- **`TASK-037` — Smooth Human-Like Bézier Mouse Drag**
  - *Real-World Scenario:* Drag a visual canvas element smoothly without triggering jitter or jerky motion artifacts.
  - *Live Actions:* Call `extra_drag(start_x=200, start_y=200, end_x=500, end_y=400)`.
  - *Desktop State:* Cursor traces a smooth Bézier easing curve across the screen.
  - *Fast-Path / Guardrail:* Natural acceleration and deceleration prevent anti-bot motion detection.

- **`TASK-038` — Linear Scrubber / Volume Slider Drag**
  - *Real-World Scenario:* Drag a horizontal volume or media timeline slider in VLC or a media player.
  - *Live Actions:* Execute straight-line drag from start to end coordinates.
  - *Desktop State:* Slider thumb moves to new position; volume/progress updates.
  - *Fast-Path / Guardrail:* Button held continuously throughout intermediate steps.

- **`TASK-039` — Vertical Document Scroll Navigation**
  - *Real-World Scenario:* Scroll down a long document or web page to inspect lower sections.
  - *Live Actions:* Call `extra_scroll(clicks=-5, direction="vertical")`.
  - *Desktop State:* Window view scrolls down smoothly by 5 wheel units.
  - *Fast-Path / Guardrail:* Standard `WHEEL_DELTA` dispatch.

- **`TASK-040` — Horizontal Data Table Scroll**
  - *Real-World Scenario:* Scroll horizontally across a wide financial spreadsheet or table.
  - *Live Actions:* Call `extra_scroll(clicks=5, direction="horizontal")`.
  - *Desktop State:* View shifts horizontally to display right-hand columns.
  - *Fast-Path / Guardrail:* Dispatches `MOUSEEVENTF_HWHEEL`.

- **`TASK-041` — Multi-Key Synchronized Hotkeys (`Ctrl+Shift+Esc`)**
  - *Real-World Scenario:* Trigger Windows Task Manager via standard keyboard shortcut.
  - *Live Actions:* Call `extra_hotkey(keys=["ctrl", "shift", "esc"])`.
  - *Desktop State:* Modifiers depressed in order, action key pressed, released in reverse order; Task Manager opens.
  - *Fast-Path / Guardrail:* Zero stuck modifier keys (`Ctrl` or `Shift`).

- **`TASK-042` — System Modal & Popup Dismissal (`Esc`)**
  - *Real-World Scenario:* Dismiss an accidental context menu, dropdown, or modal dialog.
  - *Live Actions:* Call `extra_hotkey(keys=["esc"])`.
  - *Desktop State:* Popup disappears immediately; focus returns to main document.
  - *Fast-Path / Guardrail:* Universal escape hatch for unexpected UI states.

---

### Tier 4: Window Snapping, Docking & Multitasking (`TASK-043` - `TASK-056`)

- **`TASK-043` — Foreground Focus Lock Bypass (`AttachThreadInput`)**
  - *Real-World Scenario:* Bring a background Notepad or Calculator window to the front without taskbar flashing.
  - *Live Actions:* Call `extra_focus_window(window_title="Notepad")`.
  - *Desktop State:* Notepad window instantly becomes the active foreground window.
  - *Fast-Path / Guardrail:* Win32 `AttachThreadInput` + `AllowSetForegroundWindow` bypasses Windows focus restrictions.

- **`TASK-044` — Window Title Substring Polling & Focus**
  - *Real-World Scenario:* Bring an app to the front right as it finishes launching.
  - *Live Actions:* Call `extra_focus_window(window_title="Calculator", timeout=3.0)`.
  - *Desktop State:* Window handle acquired and activated smoothly in < 250ms.
  - *Fast-Path / Guardrail:* Adaptive polling prevents premature timeouts.

- **`TASK-045` — Window Left-Half Split Docking (`Win+Left`)**
  - *Real-World Scenario:* Dock an analytics chart or calculator to the left half of the display.
  - *Live Actions:* Focus window, send `extra_hotkey(keys=["win", "left"])`, immediately send `extra_hotkey(keys=["esc"])`.
  - *Desktop State:* Window occupies exactly 50% left of the screen; Windows 11 Snap Assist dismissed.
  - *Fast-Path / Guardrail:* Native hotkey avoids fragile title-bar mouse dragging.

- **`TASK-046` — Window Right-Half Split Docking (`Win+Right`)**
  - *Real-World Scenario:* Dock a notes document or code editor to the right half of the display.
  - *Live Actions:* Focus second window, send `extra_hotkey(keys=["win", "right"])`, send `extra_hotkey(keys=["esc"])`.
  - *Desktop State:* Window occupies exactly 50% right of the screen; Windows 11 Snap Assist dismissed.
  - *Fast-Path / Guardrail:* Native hotkey ensures pixel-perfect split screen.

- **`TASK-047` — Windows 11 Snap Assist Trap Avoidance**
  - *Real-World Scenario:* Prevent the agent from getting trapped in the Windows 11 thumbnail picker popup after snapping.
  - *Live Actions:* Dispatch `extra_hotkey(keys=["esc"])` immediately following any window snap.
  - *Desktop State:* Snap Assist popup closes cleanly; active app retains keyboard focus.
  - *Fast-Path / Guardrail:* Strictly enforced rule in Extra automation protocol.

- **`TASK-048` — Side-by-Side Dual-App Split Screen (Calculator Left + Notepad Right)**
  - *Real-World Scenario:* Present a financial calculation side-by-side with an executive briefing.
  - *Live Actions:* Launch Calculator -> Snap Left -> Dismiss Snap Assist -> Launch Notepad with briefing -> Snap Right -> Dismiss Snap Assist.
  - *Desktop State:* Screen split 50/50: Calculator visible on Left, Notepad visible on Right.
  - *Fast-Path / Guardrail:* Both applications remain open and fully visible.

- **`TASK-049` — Minimized Window Restoration**
  - *Real-World Scenario:* Restore an application that was minimized to the taskbar.
  - *Live Actions:* Call `force_activate_window` on the minimized HWND.
  - *Desktop State:* Window restores with `SW_RESTORE` and comes to the foreground.
  - *Fast-Path / Guardrail:* Handles iconic windows gracefully.

- **`TASK-050` — Window Maximize & Restore Toggle (`Win+Up`)**
  - *Real-World Scenario:* Maximize an application to full screen, then restore it to windowed mode.
  - *Live Actions:* Focus window, send `extra_hotkey(keys=["win", "up"])` to maximize.
  - *Desktop State:* Window occupies entire desktop area smoothly.
  - *Fast-Path / Guardrail:* Clean Win32 hotkey execution.

- **`TASK-051` — Active Window Executable Discovery (`get_window_executable_path`)**
  - *Real-World Scenario:* Identify which physical `.exe` file on disk owns the currently focused window.
  - *Live Actions:* Query process handle of active HWND via `QueryFullProcessImageNameW`.
  - *Desktop State:* Returns exact path (e.g. `C:\Program Files\...\Notepad.exe`).
  - *Fast-Path / Guardrail:* Enables automatic dynamic app registration.

- **`TASK-052` — Multi-Window Process Enumeration**
  - *Real-World Scenario:* Enumerate all open tabs or secondary windows of a browser or text editor.
  - *Live Actions:* Query all top-level HWNDs matching process name (e.g. `msedge.exe`).
  - *Desktop State:* Returns all window frames belonging to the application.
  - *Fast-Path / Guardrail:* Distinguishes top-level windows from hidden sub-windows.

- **`TASK-053` — Cloaked UWP Window Filtering**
  - *Real-World Scenario:* Distinguish active visible UWP applications from suspended background Store apps.
  - *Live Actions:* Check `DWMWA_CLOAKED` window attribute via `DwmGetWindowAttribute`.
  - *Desktop State:* Filters out suspended background apps, preventing clicks into phantom windows.
  - *Fast-Path / Guardrail:* Eliminates false positive window listings.

- **`TASK-054` — Graceful Handling of Closed Windows**
  - *Real-World Scenario:* Handle queries on an application window that was recently closed by the user.
  - *Live Actions:* Call `find_window_by_title("NonExistentWindow", timeout=0.2)`.
  - *Desktop State:* Returns `None` cleanly without hanging or raising exceptions.
  - *Fast-Path / Guardrail:* Zero crashes on missing windows.

- **`TASK-055` — Desktop Multi-Window Arrangement**
  - *Real-World Scenario:* Arrange multiple windows (e.g. Edge, Calc, Notepad) across the desktop in a balanced workspace layout.
  - *Live Actions:* Position windows into non-overlapping regions.
  - *Desktop State:* All target applications visible simultaneously.
  - *Fast-Path / Guardrail:* Respects Live Computer Use Mandate (no apps closed).

- **`TASK-056` — Focus Re-Anchoring on Modal Dismissal**
  - *Real-World Scenario:* Ensure keyboard focus reliably returns to the primary editor after closing a Save/Open dialog.
  - *Live Actions:* Close dialog via `Esc`, call `extra_focus_window` on main app.
  - *Desktop State:* Main window active and cursor blinking in editor.
  - *Fast-Path / Guardrail:* Zero orphaned focus states.

---

### Tier 5: Semantic Accessibility Plane & Control Inspection (`TASK-057` - `TASK-070`)

- **`TASK-057` — UIAutomation COM Plane Initialization**
  - *Real-World Scenario:* Initialize the Windows accessibility layer to inspect on-screen buttons and inputs.
  - *Live Actions:* Initialize `CUIAutomation8` COM instance.
  - *Desktop State:* Connected in < 2ms with thread-safe MTA/STA apartment model.
  - *Fast-Path / Guardrail:* Zero memory leaks or COM runtime conflicts.

- **`TASK-058` — Interactive Control Tree Enumeration in Active App**
  - *Real-World Scenario:* Discover all interactive buttons, text fields, and menus in the foreground window.
  - *Live Actions:* Call `extra_inspect_ui(window_title="Calculator", interactive_only=True)`.
  - *Desktop State:* Returns list of clickable controls with names, types, and bounding boxes.
  - *Fast-Path / Guardrail:* Traversal capped at max 50 elements to prevent thread stalls.

- **`TASK-059` — Semantic Element Query by Accessible Name**
  - *Real-World Scenario:* Find the "File" menu or "Equals" button by its human-readable label.
  - *Live Actions:* Query accessibility tree for element matching Name property substring.
  - *Desktop State:* Resolves target element in < 5ms.
  - *Fast-Path / Guardrail:* Case-insensitive substring matching.

- **`TASK-060` — Semantic Element Query by AutomationId**
  - *Real-World Scenario:* Find a specific button in Windows Calculator via its stable developer ID (e.g. `"equalButton"`).
  - *Live Actions:* Query element by exact `AutomationId`.
  - *Desktop State:* Resolves target control in O(1) time.
  - *Fast-Path / Guardrail:* Immune to localized language changes.

- **`TASK-061` — Direct COM InvokePattern Activation**
  - *Real-World Scenario:* Click an accessible button instantly without moving the physical mouse cursor.
  - *Live Actions:* Call `extra_click_element(element_id=...)`.
  - *Desktop State:* Fires `IUIAutomationInvokePattern::Invoke` in < 1ms; button triggers instantly.
  - *Fast-Path / Guardrail:* Zero mouse movement; zero visual jitter.

- **`TASK-062` — Coordinate Click Fallback for Non-Invokable Controls**
  - *Real-World Scenario:* Click a control that does not expose an InvokePattern provider.
  - *Live Actions:* Automatically compute the geometric center of the element's bounding box and dispatch mouse click.
  - *Desktop State:* Mouse clicks the control center accurately.
  - *Fast-Path / Guardrail:* Seamless fallback from COM to physical mouse event.

- **`TASK-063` — Interactive vs Decorative Control Filtering**
  - *Real-World Scenario:* Filter out non-clickable background panels, borders, and static labels.
  - *Live Actions:* Inspect window with `interactive_only=True`.
  - *Desktop State:* Returns only actionable controls (Buttons, Edits, CheckBoxes, Menus).
  - *Fast-Path / Guardrail:* Reduces token clutter by 80%+.

- **`TASK-064` — Off-Screen Control Detection**
  - *Real-World Scenario:* Identify whether a button is currently scrolled out of view.
  - *Live Actions:* Inspect element's `IsOffscreen` property.
  - *Desktop State:* Flags off-screen controls so agent knows to scroll before clicking.
  - *Fast-Path / Guardrail:* Eliminates blind clicks on hidden controls.

- **`TASK-065` — Set-of-Mark Integer ID Allocation & Mapping**
  - *Real-World Scenario:* Assign simple numbers (1, 2, 3...) to visible UI controls for rapid reference.
  - *Live Actions:* Inspect window; cache controls in numerical lookup dictionary.
  - *Desktop State:* Every integer ID maps uniquely to a valid `UIElement`.
  - *Fast-Path / Guardrail:* Allows `extra_click_element(1)` for ultra-fast execution.

- **`TASK-066` — Heavy Application Tree Traversal Timeout Guard**
  - *Real-World Scenario:* Inspect a deeply nested, massive desktop application (e.g. Visual Studio or Word).
  - *Live Actions:* Execute UIA search with strict depth limit and timeout.
  - *Desktop State:* Search returns available top-level controls without freezing the process.
  - *Fast-Path / Guardrail:* Zero thread locking.

- **`TASK-067` — Comtypes Cache Directory Portability**
  - *Real-World Scenario:* Ensure accessibility automation works in locked-down corporate environments where Program Files is read-only.
  - *Live Actions:* Direct comtypes generated wrapper files to `%LOCALAPPDATA%\comtypes_cache`.
  - *Desktop State:* Wrappers compile and load cleanly.
  - *Fast-Path / Guardrail:* Zero permission denied errors.

- **`TASK-068` — Control Bounding Box Coordinate Normalization**
  - *Real-World Scenario:* Normalize element bounding boxes into [0, 1000] coordinate space for multimodal models.
  - *Live Actions:* Map physical rect bounds through monitor DPI transformation.
  - *Desktop State:* Normalized coordinates match visual location on screen.
  - *Fast-Path / Guardrail:* Bijective coordinate mapping.

- **`TASK-069` — Disabled Control State Recognition**
  - *Real-World Scenario:* Check if a "Submit" or "Save" button is currently disabled/greyed-out.
  - *Live Actions:* Inspect element `IsEnabled` property.
  - *Desktop State:* Accurately identifies `IsEnabled=False`.
  - *Fast-Path / Guardrail:* Prevents futile clicks on disabled controls.

- **`TASK-070` — Clean COM Plane Shutdown**
  - *Real-World Scenario:* Clean up COM interface pointers upon task completion.
  - *Live Actions:* Release cached COM element pointers.
  - *Desktop State:* Memory freed; zero dangling COM interfaces.
  - *Fast-Path / Guardrail:* Clean lifecycle management.

---

### Tier 6: Web Browsing & Online Research (`TASK-071` - `TASK-084`)

- **`TASK-071` — Microsoft Edge Live Website Navigation**
  - *Real-World Scenario:* Open Microsoft Edge to a live website (e.g. `https://extra.yantraos.com/`) for research.
  - *Target App:* `msedge.exe`
  - *Live Actions:* Call `extra_browser(action="navigate", url="https://extra.yantraos.com/")`.
  - *Desktop State:* Web page loads cleanly in < 1000ms with HTTP status 200.
  - *Fast-Path / Guardrail:* High-speed browser automation engine.

- **`TASK-072` — Semantic Markdown Article Extraction**
  - *Real-World Scenario:* Extract clean, readable article content from a web page without HTML ads or nav headers.
  - *Live Actions:* Call `extra_browser(action="content")`.
  - *Desktop State:* Returns clean markdown text of page body.
  - *Fast-Path / Guardrail:* Zero HTML tag pollution.

- **`TASK-073` — Web Search Form Query & Submission**
  - *Real-World Scenario:* Type a search query into an online search input and trigger search.
  - *Live Actions:* Call `extra_browser(action="fill", selector="input[name='q']", value="Project Extra")`, followed by submit.
  - *Desktop State:* Search query executes; search results page renders.
  - *Fast-Path / Guardrail:* Direct DOM filling in < 10ms.

- **`TASK-074` — Direct CSS Selector Element Click**
  - *Real-World Scenario:* Click a primary call-to-action button on a web page.
  - *Live Actions:* Call `extra_browser(action="click", selector="button.cta-primary")`.
  - *Desktop State:* Target element clicked cleanly in DOM; triggers navigation or modal.
  - *Fast-Path / Guardrail:* Eliminates vision coordinate hunting on web pages.

- **`TASK-075` — Live Equity / Financial Quote Direct Extraction**
  - *Real-World Scenario:* Check live market quote for NVDA or AAPL to compute company valuation.
  - *Target App:* `msedge.exe`
  - *Live Actions:* Navigate to Google Finance live quote URL; extract current stock price number directly.
  - *Desktop State:* Live market quote captured in < 800ms.
  - *Fast-Path / Guardrail:* Direct live numbers without reverse-engineering APIs.

- **`TASK-076` — Webpage Viewport Screenshot Capture**
  - *Real-World Scenario:* Capture a clean screenshot of the current web page viewport.
  - *Live Actions:* Call `extra_browser(action="screenshot")`.
  - *Desktop State:* Clean base64 PNG image of the web page generated.
  - *Fast-Path / Guardrail:* Captures rendered web view cleanly.

- **`TASK-077` — In-Page JavaScript State Evaluation**
  - *Real-World Scenario:* Query `document.title` or page scroll height dynamically.
  - *Live Actions:* Call `extra_browser(action="eval", value="document.title")`.
  - *Desktop State:* Returns evaluated string result.
  - *Fast-Path / Guardrail:* Direct JS evaluation in browser runtime.

- **`TASK-078` — Cookie Banner & Consent Modal Dismissal**
  - *Real-World Scenario:* Automatically dismiss an annoying cookie consent banner blocking the web page.
  - *Live Actions:* Detect cookie overlay selector or send `Esc`, click accept/dismiss.
  - *Desktop State:* Overlay closes; main content becomes interactive.
  - *Fast-Path / Guardrail:* Auto-recovery from modal blockage.

- **`TASK-079` — Multi-Tab Web Research Session**
  - *Real-World Scenario:* Open documentation in Tab 1 and an API playground in Tab 2, switching between them.
  - *Live Actions:* Open new tab, navigate to second URL, switch active tab.
  - *Desktop State:* Multiple tab contexts maintained without session collisions.
  - *Fast-Path / Guardrail:* Clean tab lifecycle.

- **`TASK-080` — Network Timeout & Offline Resilience**
  - *Real-World Scenario:* Attempt to navigate to a non-existent or down website.
  - *Live Actions:* Navigate to `https://invalid.domain.xyz123`.
  - *Desktop State:* Returns structured failure error within timeout threshold; zero process hang.
  - *Fast-Path / Guardrail:* Clean error handling.

- **`TASK-081` — Web Page Downward Scroll**
  - *Real-World Scenario:* Scroll down a long online documentation page to read the lower sections.
  - *Live Actions:* Call `window.scrollTo(0, 1200)` via browser eval.
  - *Desktop State:* Viewport scrolls down smoothly.
  - *Fast-Path / Guardrail:* Zero hardware mouse scroll latency.

- **`TASK-082` — Web Asset Download & Workspace Routing**
  - *Real-World Scenario:* Download a CSV report or PDF from the browser.
  - *Live Actions:* Trigger file download in browser.
  - *Desktop State:* File downloaded safely to `%USERPROFILE%\.extra\workspace\downloads\`.
  - *Fast-Path / Guardrail:* Strictly honors safe workspace directory boundary.

- **`TASK-083` — Clean Headless Browser Teardown**
  - *Real-World Scenario:* Close the browser automation session cleanly after extracting information.
  - *Live Actions:* Call `extra_browser(action="close")`.
  - *Desktop State:* Browser processes terminate cleanly; zero zombie processes left running.
  - *Fast-Path / Guardrail:* Thorough process teardown.

- **`TASK-084` — Standard Desktop Viewport Emulation**
  - *Real-World Scenario:* Ensure browser renders in 1920x1080 desktop layout rather than mobile mode.
  - *Live Actions:* Set viewport dimensions to 1920x1080 with desktop user-agent.
  - *Desktop State:* Full desktop navigation bar and multi-column layout rendered.
  - *Fast-Path / Guardrail:* Eliminates hamburger menu mobile redirects.

---

### Tier 7: StallBreaker Resilience & Error Recovery (`TASK-085` - `TASK-098`)

- **`TASK-085` — Strike 1 Escalation: Focus Re-Anchor & Modal ESC Dismissal**
  - *Real-World Scenario:* An unexpected popup dialog blocks an application; agent dismisses it and regains focus.
  - *Live Actions:* When a click yields no state change, StallBreaker increments to Strike 1, dispatches `extra_hotkey(keys=["esc"])`, and refocuses the window.
  - *Desktop State:* Modal dialog closes; active app window re-focused.
  - *Fast-Path / Guardrail:* Closed-loop automatic recovery.

- **`TASK-086` — Strike 2 Escalation: Fast-Path Fallback Activation**
  - *Real-World Scenario:* An application button is visually obscured or unclickable via coordinates.
  - *Live Actions:* StallBreaker increments to Strike 2, abandons coordinate clicks, and switches to direct hotkey or file-based fast path.
  - *Desktop State:* Task proceeds successfully without stalling.
  - *Fast-Path / Guardrail:* Eliminates repetitive pixel-hunting.

- **`TASK-087` — Strike 3 Escalation: Emergency Safety Abort**
  - *Real-World Scenario:* An application is completely frozen or non-responsive after 3 attempts.
  - *Live Actions:* StallBreaker raises `EmergencyAbortError`, aborts further clicks, and reports structured diagnosis.
  - *Desktop State:* Execution halts safely; user notified; zero infinite retry loops.
  - *Fast-Path / Guardrail:* Protects user system from runaways.

- **`TASK-088` — Strike Counter Automatic Reset on Successful Action**
  - *Real-World Scenario:* Agent encounters a momentary delay, recovers, and continues executing tasks.
  - *Live Actions:* Execute any successful action (`extra_launch`, valid input, window focus).
  - *Desktop State:* Stall strike counter immediately resets to 0.
  - *Fast-Path / Guardrail:* Clean state management.

- **`TASK-089` — Repetitive Click Loop Detection**
  - *Real-World Scenario:* Prevent an agent from repeatedly clicking the exact same pixel coordinates 10 times in a loop.
  - *Live Actions:* Loop detector monitors consecutive action signatures; flags stall on 4th identical click.
  - *Desktop State:* StallBreaker triggers escalation; breaks the loop.
  - *Fast-Path / Guardrail:* Anti-tunnel-vision guardrail.

- **`TASK-090` — Canva "Open Design Link" Popup Recovery**
  - *Real-World Scenario:* Accidental `Ctrl+N` in Canva desktop opens the "Open a design link:" dialog and produces an error.
  - *Target App:* `Canva.exe`
  - *Live Actions:* Detect invalid design link error, dispatch `extra_hotkey(keys=["esc"])` once to dismiss popup, click home category icons or top search bar.
  - *Desktop State:* Canva returns to home screen; new design created via category icon.
  - *Fast-Path / Guardrail:* Zero loop of re-typing design names into the link box.

- **`TASK-091` — Windows Photos File Error Immediate Fallback to MS Paint**
  - *Real-World Scenario:* Windows Photos app displays a UWP file system error when attempting to open an image.
  - *Target App:* `ms-photos:` -> `mspaint.exe`
  - *Live Actions:* Send `extra_hotkey(keys=["esc"])` to dismiss dialog in < 1s; immediately launch MS Paint with image path.
  - *Desktop State:* MS Paint opens displaying the image crisply.
  - *Fast-Path / Guardrail:* Zero attempts to run `Reset-AppxPackage` or crawl Event Viewer logs.

- **`TASK-092` — Anti-Stall Guardrail: Strict Zero Modular Test Script Prohibition**
  - *Real-World Scenario:* Agent is asked to automate an app and tries to write `test_coords.py` or exploratory scripts.
  - *Live Actions:* Guardrail intercepts and blocks creation of exploratory test scripts; enforces direct Extra MCP tools.
  - *Desktop State:* Automation executes directly in foreground; saves 4+ minutes.
  - *Fast-Path / Guardrail:* Enforces zero-scripting desktop protocol.

- **`TASK-093` — Anti-Stall Guardrail: Strict Zero System Admin Rabbit Holes**
  - *Real-World Scenario:* An app fails to open; agent avoids running PowerShell registry tweaks or Appx resets.
  - *Live Actions:* Protocol prohibits system modifications; falls back cleanly to native Win32 alternative.
  - *Desktop State:* User machine remains safe, untouched, and stable.
  - *Fast-Path / Guardrail:* Strict safety compliance.

- **`TASK-094` — Unresponsive Window Heartbeat Monitor (`IsHungAppWindow`)**
  - *Real-World Scenario:* An application hangs during processing and stops responding to Win32 messages.
  - *Live Actions:* Check `IsHungAppWindow` before sending input.
  - *Desktop State:* Detects hung state; avoids blocking the automation thread.
  - *Fast-Path / Guardrail:* Thread-safe timeout guard.

- **`TASK-095` — Safe State Recovery After Application Crash**
  - *Real-World Scenario:* Target desktop application unexpectedly crashes mid-workflow.
  - *Live Actions:* Catch process termination; record incident; notify user without crashing Extra engine.
  - *Desktop State:* Extra engine remains operational and ready for next command.
  - *Fast-Path / Guardrail:* Robust exception boundary.

- **`TASK-096` — Anti-Stall Guardrail Logging & Auditing to KùzuDB**
  - *Real-World Scenario:* Every stall or error recovery is automatically recorded into graph memory.
  - *Live Actions:* Ingest stall incident node with trigger and resolution into KùzuDB.
  - *Desktop State:* Memory updated; future tasks query memory to avoid same issue.
  - *Fast-Path / Guardrail:* Continuous self-healing learning.

- **`TASK-097` — Dynamic Adaptive Timeout Calibration**
  - *Real-World Scenario:* Calibrate polling timeouts between fast-launching tools (Calc ~100ms) and heavy apps (Canva ~3s).
  - *Live Actions:* Adaptive polling checks window presence every 50ms up to max timeout.
  - *Desktop State:* Proceeds the instant window is ready without fixed artificial sleep delays.
  - *Fast-Path / Guardrail:* Zero unnecessary latency.

- **`TASK-098` — Safe User Interruption & Keyboard Modifier Release**
  - *Real-World Scenario:* User hits `Ctrl+C` or stops the agent while keys are being pressed.
  - *Live Actions:* Interception handler releases all held modifier keys (`Ctrl`, `Alt`, `Shift`, `Win`) and mouse buttons.
  - *Desktop State:* Physical keyboard state restored to clean neutral state.
  - *Fast-Path / Guardrail:* Prevents "stuck modifier keys" syndrome.

---

### Tier 8: KùzuDB Graph Memory & FastEmbed Intelligence (`TASK-099` - `TASK-112`)

- **`TASK-099` — Sovereign Graph Memory Database Setup (`~/.extra/memory/`)**
  - *Real-World Scenario:* Initialize the local embedded knowledge graph store for lifelong task memory.
  - *Live Actions:* Initialize KùzuDB store at `%USERPROFILE%\.extra\memory\graph.kuzu`.
  - *Desktop State:* Database ready with node tables (`Task`, `Step`, `App`, `Artifact`, `Stall`, `AppQuirk`).
  - *Fast-Path / Guardrail:* Zero cloud dependency; 100% sovereign local database.

- **`TASK-100` — Local FastEmbed Vector Generation (`BAAI/bge-small-en-v1.5`)**
  - *Real-World Scenario:* Generate a semantic vector embedding for a user prompt locally on the machine.
  - *Live Actions:* Compute 384-dimensional dense vector via ONNX local inference.
  - *Desktop State:* Normalized vector returned in < 25ms locally.
  - *Fast-Path / Guardrail:* Zero internet required; zero API token costs.

- **`TASK-101` — Full Task Trajectory Atomic Ingestion**
  - *Real-World Scenario:* Store an executed desktop workflow (e.g. Edge research + Calculator + Notepad) into memory.
  - *Live Actions:* Record Task node and individual Step nodes linked via `[:CONSISTS_OF]`.
  - *Desktop State:* Graph committed atomically.
  - *Fast-Path / Guardrail:* Full trajectory preserved for replay or reference.

- **`TASK-102` — Application Node Linkage (`[:INTERACTED_WITH]`)**
  - *Real-World Scenario:* Link executed tasks to the specific applications used (`"canva"`, `"calc"`, `"notepad"`).
  - *Live Actions:* Create relationship `(Task)-[:INTERACTED_WITH]->(App)`.
  - *Desktop State:* Graph allows querying all tasks that utilized a given application.
  - *Fast-Path / Guardrail:* Relational graph integrity.

- **`TASK-103` — File Artifact Registration & Metadata Linkage**
  - *Real-World Scenario:* Link a created brief (`briefing.txt`) or chart (`chart.png`) to the task that produced it.
  - *Live Actions:* Create Artifact node with file path, size, and mime type; link via `[:PRODUCED]`.
  - *Desktop State:* Graph tracks complete artifact provenance.
  - *Fast-Path / Guardrail:* Instant artifact lookups.

- **`TASK-104` — Stall Incident Graph Linkage (`[:ENCOUNTERED]`)**
  - *Real-World Scenario:* Record a StallBreaker event (e.g. Canva link error) into the memory graph.
  - *Live Actions:* Create Stall node and link `(Task)-[:ENCOUNTERED]->(Stall)`.
  - *Desktop State:* Stalls indexed with strike count, trigger, and recovery action.
  - *Fast-Path / Guardrail:* Prevents repeating known mistakes.

- **`TASK-105` — Application Quirk & Playbook Registration (`[:EXHIBITS]`)**
  - *Real-World Scenario:* Store discovered software quirks (e.g. "Windows Calculator rejects clipboard paste").
  - *Live Actions:* Ingest `AppQuirk` node linked to App via `[:EXHIBITS]`.
  - *Desktop State:* Quirk and verified playbook permanently stored.
  - *Fast-Path / Guardrail:* Crystallizes zero-stall knowledge.

- **`TASK-106` — Semantic Vector Recall (`extra_recall_memory`)**
  - *Real-World Scenario:* User asks "how do I make an Instagram graphic in Canva?", agent recalls past successful workflow.
  - *Live Actions:* Call `extra_recall_memory(query="make instagram graphic in canva", top_k=3)`.
  - *Desktop State:* Returns top matching past task trajectory with similarity score > 0.70 in < 5ms.
  - *Fast-Path / Guardrail:* Instant knowledge re-use.

- **`TASK-107` — Multi-Condition Memory Filtering (App + Success)**
  - *Real-World Scenario:* Recall only verified successful workflows for Microsoft Edge.
  - *Live Actions:* Query memory with filters `app_name="edge"` and `success=True`.
  - *Desktop State:* Returns exclusively successful task trajectories.
  - *Fast-Path / Guardrail:* Zero hallucinated workflows.

- **`TASK-108` — Multi-Threaded Memory Read/Write Safety**
  - *Real-World Scenario:* Execute concurrent background memory lookups while a task is recording steps.
  - *Live Actions:* Dispatch concurrent queries across worker threads using mutex lock.
  - *Desktop State:* Database handles queries cleanly without file lock errors.
  - *Fast-Path / Guardrail:* Concurrency safe.

- **`TASK-109` — Cold Restart Memory Persistence Verification**
  - *Real-World Scenario:* Close Extra, reboot system, re-launch Extra, verify all past memory remains intact.
  - *Live Actions:* Close DB connection, re-instantiate, query previous tasks and quirks.
  - *Desktop State:* All nodes, embeddings, and relationships persist 100%.
  - *Fast-Path / Guardrail:* Lifelong sovereign memory.

- **`TASK-110` — Sub-5ms Vector Recall Latency Benchmark**
  - *Real-World Scenario:* Benchmark memory recall speed under heavy graph load.
  - *Live Actions:* Execute 50 consecutive vector queries against indexed graph.
  - *Desktop State:* Average query latency remains under 3ms.
  - *Fast-Path / Guardrail:* Extremely fast local execution.

- **`TASK-111` — Embedding Query Deduplication Cache**
  - *Real-World Scenario:* Agent queries the same task prompt multiple times during a conversation.
  - *Live Actions:* Retrieve cached vector from memory without re-running ONNX inference.
  - *Desktop State:* Returns vector in < 0.1ms.
  - *Fast-Path / Guardrail:* Zero redundant computation.

- **`TASK-112` — Sovereign Directory CFA Immunity Verification**
  - *Real-World Scenario:* Ensure memory storage directory is never blocked by Windows Defender Ransomware Protection.
  - *Live Actions:* Verify read/write permissions on `%USERPROFILE%\.extra\memory\`.
  - *Desktop State:* 100% exempt from CFA restrictions; zero Defender alerts.
  - *Fast-Path / Guardrail:* Safe filesystem architecture.

---

### Tier 9: JIT Application Scouting & Skill Synthesis (`TASK-113` - `TASK-124`)

- **`TASK-113` — 3D Viewport Framework Detection (Blender)**
  - *Real-World Scenario:* Scout an installed Blender instance to determine its UI architecture.
  - *Target App:* `blender.exe`
  - *Live Actions:* Call `extra_scout_app(app_name="blender")`.
  - *Desktop State:* Detects `directx_opengl_viewport`; documents lack of Win32 UIA accessibility nodes.
  - *Fast-Path / Guardrail:* Recommends CLI background rendering (`-b -P`) over viewport clicking.

- **`TASK-114` — Electron Web Canvas Framework Detection (Canva / Figma)**
  - *Real-World Scenario:* Scout Canva desktop app to identify UI capabilities and limitations.
  - *Target App:* `Canva.exe`
  - *Live Actions:* Call `extra_scout_app(app_name="canva")`.
  - *Desktop State:* Detects `electron_web_canvas`; notes outer UI is web DOM while drawing canvas is WebGL.
  - *Fast-Path / Guardrail:* Recommends home category clicks + STA clipboard paste.

- **`TASK-115` — Native Win32 / UWP Framework Detection (Notepad / Calc)**
  - *Real-World Scenario:* Scout standard Windows utilities.
  - *Target App:* `notepad.exe` / `calc.exe`
  - *Live Actions:* Call `extra_scout_app(app_name="notepad")`.
  - *Desktop State:* Identifies native Win32/UWP; notes direct input typing and accessibility support.
  - *Fast-Path / Guardrail:* Enables high-speed text injection.

- **`TASK-116` — Non-Blocking Safe CLI Flag Probing (`--help` / `-h`)**
  - *Real-World Scenario:* Discover command-line flags of an installed tool without spawning interactive windows or hanging.
  - *Live Actions:* Probe CLI flags with strict 1.5s timeout.
  - *Desktop State:* Captures CLI parameters safely; zero hanging processes.
  - *Fast-Path / Guardrail:* Non-blocking execution.

- **`TASK-117` — Universal Shortcut Intelligence Retrieval**
  - *Real-World Scenario:* Query verified universal keyboard shortcuts for Canva, Blender, VLC, and Notepad.
  - *Live Actions:* Retrieve curated hotkeys (`T` for text, `Space` for play/pause, `Ctrl+S` for save).
  - *Desktop State:* Returns verified hotkey map.
  - *Fast-Path / Guardrail:* Instant keyboard navigation.

- **`TASK-118` — agentskills.io Compliant SKILL.md Playbook Synthesis**
  - *Real-World Scenario:* Synthesize a production-ready `SKILL.md` file for an application.
  - *Live Actions:* Generate markdown playbook with YAML frontmatter, architecture caveats, fast paths, and hotkeys.
  - *Desktop State:* Structured `SKILL.md` written to skill directories.
  - *Fast-Path / Guardrail:* Open standard format for AI agent skills.

- **`TASK-119` — Multi-Directory Skill Distribution**
  - *Real-World Scenario:* Ensure generated skills are discoverable by Antigravity, workspace agents, and Extra.
  - *Live Actions:* Write `SKILL.md` to `.agents/skills/`, `.gemini/config/skills/`, and `.extra/skills/`.
  - *Desktop State:* Written atomically across all active skill search paths.
  - *Fast-Path / Guardrail:* Instant agent capability expansion.

- **`TASK-120` — Dynamic Shell App Registry Integration During Scout**
  - *Real-World Scenario:* Ensure an app scouted on disk is automatically registered for instant launching.
  - *Live Actions:* Scout application binary; register into `APP_REGISTRY`.
  - *Desktop State:* App alias registered and persisted to `app_registry.json`.
  - *Fast-Path / Guardrail:* Zero redundant configuration.

- **`TASK-121` — Automatic KùzuDB Quirk & Playbook Ingestion During Scout**
  - *Real-World Scenario:* Store discovered fast paths directly into the memory knowledge graph.
  - *Live Actions:* Ingest scout playbook as an `AppQuirk` node into KùzuDB.
  - *Desktop State:* Knowledge available for vector recall in future tasks.
  - *Fast-Path / Guardrail:* Continuous memory learning.

- **`TASK-122` — Scout Result Caching & Force-Refresh Flag**
  - *Real-World Scenario:* Avoid re-scouting applications repeatedly unless requested.
  - *Live Actions:* Run scout twice; verify second run returns `"status": "cached"`; test `force_refresh=True`.
  - *Desktop State:* Returns cached intelligence in < 2ms.
  - *Fast-Path / Guardrail:* Zero unnecessary disk crawling.

- **`TASK-123` — Custom User Instructions Injection into Playbook**
  - *Real-World Scenario:* User requests a custom workflow rule (e.g. "Always export videos at 1080p 60fps").
  - *Live Actions:* Pass `custom_notes` to scout; verify incorporation into synthesized `SKILL.md`.
  - *Desktop State:* Custom instruction reflected in skill playbook.
  - *Fast-Path / Guardrail:* Tailored user experience.

- **`TASK-124` — Web-Only Application Fallback Playbook Generation**
  - *Real-World Scenario:* Scout a web-based service (e.g. Linear or Notion web).
  - *Live Actions:* Generate browser-first playbook with direct URLs and DOM selectors.
  - *Desktop State:* Playbook provides web navigation instructions.
  - *Fast-Path / Guardrail:* Graceful fallback for non-installed tools.

---

### Tier 10: Multi-App Cross-Desktop Professional Workflows (`TASK-125` - `TASK-136`)

- **`TASK-125` — Web Research to Notepad Executive Briefing**
  - *Real-World Scenario:* Research a live web page in Edge, extract the key points, write a structured briefing file, and open it in Notepad.
  - *Apps:* `msedge.exe` + `notepad.exe`
  - *Live Actions:* Extract markdown summary from URL via browser fast path, write `executive_brief.txt` to workspace, launch Notepad pointing to file.
  - *Desktop State:* Notepad displays the synthesized web briefing in foreground.
  - *Fast-Path / Guardrail:* Completed in < 3s total; zero character-by-character typing.

- **`TASK-126` — Side-by-Side Dual-App Split Screen Docking**
  - *Real-World Scenario:* Present an analytics chart in MS Paint on the Left half and a descriptive summary in Notepad on the Right half.
  - *Apps:* `mspaint.exe` (Left) + `notepad.exe` (Right)
  - *Live Actions:* Launch Paint with generated chart -> Snap Left (`Win+Left`) -> Dismiss Snap Assist (`Esc`) -> Launch Notepad with notes -> Snap Right (`Win+Right`) -> Dismiss Snap Assist (`Esc`).
  - *Desktop State:* Perfect 50/50 side-by-side presentation on user desktop.
  - *Fast-Path / Guardrail:* Zero title bar dragging; Snap Assist menu cleanly dismissed.

- **`TASK-127` — Live Market Quote -> Calculator Computation -> Report**
  - *Real-World Scenario:* Look up an equity price in Edge, compute target valuation in Calculator, and document the thesis in Notepad.
  - *Apps:* `msedge.exe` + `calc.exe` + `notepad.exe`
  - *Live Actions:* Extract stock price from Edge -> Launch Calculator, type valuation multiple formula -> Write investment brief to disk, open in Notepad.
  - *Desktop State:* Edge, Calculator, and Notepad arranged on screen; calculations match live data.
  - *Fast-Path / Guardrail:* End-to-end multi-app workflow with live visual verification.

- **`TASK-128` — Python High-Resolution Analytics Chart -> MS Paint Presentation**
  - *Real-World Scenario:* Generate a clean, high-resolution revenue bar chart PNG and present it in MS Paint.
  - *Apps:* Python (`PIL`) + `mspaint.exe`
  - *Live Actions:* Programmatically generate crisp 1200x800 analytics PNG with title and axes to `%USERPROFILE%\.extra\workspace\revenue_chart.png`, launch Paint (`extra_launch("mspaint", ["<path>"])`).
  - *Desktop State:* MS Paint opens displaying the chart crisply on desktop.
  - *Fast-Path / Guardrail:* Crisp vector-quality image; zero shaky freehand mouse drawing.

- **`TASK-129` — High-Speed Graphic Synthesis -> Canva STA Clipboard Paste**
  - *Real-World Scenario:* Create an Instagram launch graphic in Canva by synthesizing a high-res visual and pasting directly into the canvas.
  - *Apps:* Python (`PIL`) + `powershell -STA` + `Canva.exe`
  - *Live Actions:* Generate graphic PNG, copy to Windows Clipboard via PowerShell STA, focus Canva, click canvas, paste (`Ctrl+V`).
  - *Desktop State:* Graphic appears instantly in Canva canvas.
  - *Fast-Path / Guardrail:* Bypasses WebGL canvas accessibility blindness in < 200ms.

- **`TASK-130` — Canva Native Template Discovery & Instagram Format Creation**
  - *Real-World Scenario:* User asks to use Canva templates to design an Instagram post.
  - *Apps:* `Canva.exe`
  - *Live Actions:* Launch Canva, click home screen category icon or search box for "Instagram Post", select template, customize text.
  - *Desktop State:* Canva editor open with chosen template active.
  - *Fast-Path / Guardrail:* Honors user intent to use native Canva templates without forcing scripts.

- **`TASK-131` — VLC Media Player Launch & Hotkey Control**
  - *Real-World Scenario:* Open VLC media player with an audio/video file and control playback using standard shortcuts.
  - *Target App:* `vlc.exe`
  - *Live Actions:* Launch VLC with media path, send `Space` to pause/play, `f` for fullscreen.
  - *Desktop State:* VLC opens, plays media, responds to keyboard hotkeys.
  - *Fast-Path / Guardrail:* Standard media shortcuts.

- **`TASK-132` — Blender Background Render & Paint Inspection**
  - *Real-World Scenario:* Render a 3D model in Blender and inspect the output render in MS Paint.
  - *Apps:* `blender.exe` + `mspaint.exe`
  - *Live Actions:* Execute Blender headless render script (`blender.exe -b -P render_script.py`), open resulting render in MS Paint.
  - *Desktop State:* High-resolution 3D render displayed in Paint.
  - *Fast-Path / Guardrail:* Headless CLI avoids viewport pixel-hunting.

- **`TASK-133` — Cross-Application Context Retention via KùzuDB Memory**
  - *Real-World Scenario:* Perform Task A (Edge research + Calc), store in memory; start Task B and recall Task A findings to continue.
  - *Live Actions:* Query past task via vector search; extract stored figures and continue workflow.
  - *Desktop State:* Context seamlessly transferred between tasks.
  - *Fast-Path / Guardrail:* Eliminates mid-task amnesia.

- **`TASK-134` — File Explorer Workspace Housekeeping & Visual Audit**
  - *Real-World Scenario:* Clean up workspace, organize reports and charts into dated directories, and display in File Explorer.
  - *Apps:* File system + `explorer.exe`
  - *Live Actions:* Create dated folders, move artifacts, visibly open Explorer.
  - *Desktop State:* File Explorer displays organized directory structure in foreground.
  - *Fast-Path / Guardrail:* Visual confirmation of file management.

- **`TASK-135` — Triple-Window Desktop Arrangement (Split & Grid)**
  - *Real-World Scenario:* Arrange three applications (Edge on Left, Calculator on Top-Right, Notepad on Bottom-Right).
  - *Apps:* `msedge.exe` + `calc.exe` + `notepad.exe`
  - *Live Actions:* Position all three windows in non-overlapping arrangement.
  - *Desktop State:* All three applications visible simultaneously.
  - *Fast-Path / Guardrail:* Live Computer Use Mandate: all apps remain open.

- **`TASK-136` — Full Multi-App Trajectory Evolution & Playbook Crystallization**
  - *Real-World Scenario:* Execute a new complex multi-app workflow, verify success, and crystallize it into a permanent skill.
  - *Live Actions:* Call `extra_evolve_skill` with task summary and playbook instructions.
  - *Desktop State:* Crystallized playbook written to skill library and KùzuDB memory.
  - *Fast-Path / Guardrail:* Permanent skill evolution.

---

### Tier 11: Security, Controlled Folder Access (CFA) & Safety (`TASK-137` - `TASK-144`)

- **`TASK-137` — Strict Directory Boundary Enforcer (Controlled Folder Access Compliance)**
  - *Real-World Scenario:* Ensure all file writes target safe directories and never trigger Windows Defender ransomware alerts.
  - *Live Actions:* Enforce write path restriction: only write to `%USERPROFILE%\.extra\workspace\` or repository roots.
  - *Desktop State:* Zero attempts to write to `%USERPROFILE%\Documents`, `\Pictures`, or `\Desktop`.
  - *Fast-Path / Guardrail:* Guarantees 100% compliance with Windows Defender Ransomware Protection.

- **`TASK-138` — Ransomware Protection Event 1123 Non-Trigger Audit**
  - *Real-World Scenario:* Audit Windows Defender event log during extensive file generation.
  - *Live Actions:* Verify zero Event 1123 security blockades logged by Defender.
  - *Desktop State:* User machine experiences zero alarming security toast popups.
  - *Fast-Path / Guardrail:* Safe filesystem architecture.

- **`TASK-139` — Application Persistence Mandate (No Process Killing)**
  - *Real-World Scenario:* Ensure every application opened on the desktop remains open for the user.
  - *Live Actions:* Verify agent execution across all tasks.
  - *Desktop State:* Never calls `.terminate()`, `taskkill`, or `kill` on user-requested applications.
  - *Fast-Path / Guardrail:* Strictly honors the Live Computer Use Mandate.

- **`TASK-140` — Non-Elevated Standard User Execution Safety**
  - *Real-World Scenario:* Run desktop automation tasks under a standard non-administrator user account.
  - *Live Actions:* Execute tasks without administrative privileges.
  - *Desktop State:* All tools function cleanly without prompting for UAC administrator elevation.
  - *Fast-Path / Guardrail:* Safe enterprise deployment.

- **`TASK-141` — Zero Modular Test Script Prohibition Audit**
  - *Real-World Scenario:* Audit active directory to ensure no throwaway test scripts (`test_*.py`, `check_fg.py`) were created.
  - *Live Actions:* Inspect workspace directory during and after task execution.
  - *Desktop State:* Zero clutter scripts; only production tools and intended user artifacts exist.
  - *Fast-Path / Guardrail:* Prevents agent rabbit-hole stalling.

- **`TASK-142` — Zero System Repair Rabbit Hole Audit**
  - *Real-World Scenario:* When an application encounters an error, verify the agent does not attempt system-level repairs.
  - *Live Actions:* Verify zero execution of `Reset-AppxPackage`, registry modifications, or event log crawling.
  - *Desktop State:* System configuration untouched; agent falls back to standard Win32 alternative.
  - *Fast-Path / Guardrail:* Safe desktop integrity.

- **`TASK-143` — Windows Audio Acoustic Feedback Chime**
  - *Real-World Scenario:* Play a subtle acoustic chime to notify the user when a desktop task has completed.
  - *Live Actions:* Call `extra_task_complete(summary="...", success=True)`.
  - *Desktop State:* Subtle Win32 acoustic chime plays; emerald green border flashes.
  - *Fast-Path / Guardrail:* Delightful multimodal user feedback.

- **`TASK-144` — Ambient Border Overlay Lifecycle & Clean Dissolve**
  - *Real-World Scenario:* Provide visual feedback during desktop automation with an ambient screen edge pulse and cursor halo.
  - *Live Actions:* Call `extra_task_start` at beginning, `extra_task_complete` at finish.
  - *Desktop State:* Ambient pulse glows softly during active automation and dissolves cleanly upon completion.
  - *Fast-Path / Guardrail:* Non-intrusive visual indicator.

---

### Tier 12: Dynamic App Registry & Cold Restart Persistence (`TASK-145` - `TASK-150`)

- **`TASK-145` — In-Memory Dynamic Application Registration (`register_app`)**
  - *Real-World Scenario:* Register a newly installed application alias into Extra's runtime shell launcher.
  - *Live Actions:* Call `register_app("mytool", AppConfig(target="C:\\tools\\mytool.exe", app_type=AppType.EXE))`.
  - *Desktop State:* App immediately available for launch via `extra_launch("mytool")`.
  - *Fast-Path / Guardrail:* O(1) in-memory registration.

- **`TASK-146` — User Registry Disk Persistence (`%USERPROFILE%\.extra\app_registry.json`)**
  - *Real-World Scenario:* Save dynamic app registrations permanently to disk so they survive restarts.
  - *Live Actions:* Register app with `persist=True`.
  - *Desktop State:* Written atomically to `~/.extra/app_registry.json` with target, type, and process name.
  - *Fast-Path / Guardrail:* JSON file formatted cleanly.

- **`TASK-147` — Cold Restart Registry Rehydration**
  - *Real-World Scenario:* Restart system, launch Extra, verify all custom-registered applications are loaded.
  - *Live Actions:* Re-import shell launcher module; inspect `APP_REGISTRY`.
  - *Desktop State:* All custom applications loaded into memory on startup.
  - *Fast-Path / Guardrail:* Seamless persistence across reboots.

- **`TASK-148` — Discovered Executable Auto-Registration**
  - *Real-World Scenario:* When Extra discovers an unindexed binary on disk, it automatically registers it.
  - *Live Actions:* Call `resolve_executable` on a newly discovered path.
  - *Desktop State:* Executable stem registered as an alias in `APP_REGISTRY` and saved to disk.
  - *Fast-Path / Guardrail:* Zero manual configuration required.

- **`TASK-149` — Active Focused Window Executable Discovery & Auto-Registration**
  - *Real-World Scenario:* User opens an unfamiliar application; Extra inspects focused HWND and registers it.
  - *Live Actions:* Focus window, query executable path via `get_window_executable_path`, register alias.
  - *Desktop State:* App registered into registry automatically.
  - *Fast-Path / Guardrail:* Continuous ambient discovery.

- **`TASK-150` — Universal Platform Abstraction Symmetry (Windows & macOS)**
  - *Real-World Scenario:* Ensure identical dynamic app registry API works on both Windows and macOS.
  - *Live Actions:* Verify symmetric `register_app`, `load_user_registry`, and `get_registered_apps` across platforms.
  - *Desktop State:* Identical API contract and file storage across platforms.
  - *Fast-Path / Guardrail:* Universal sovereign architecture.

---

## Live Execution & Verification Protocol

### 1. Pre-Flight Verification
Before executing live desktop automation:
1. Sovereign workspace folder `%USERPROFILE%\.extra\workspace\` is initialized.
2. Windows Display set to standard DPI or DPI awareness verified.
3. Extra MCP server active with registered tools (`extra_launch`, `extra_focus_window`, `extra_type`, `extra_hotkey`, `extra_screenshot`).

### 2. Live Computer Use Execution Standard
- All desktop interactions happen **LIVE in the foreground**.
- Opened user applications **REMAIN OPEN AND VISIBLE**.
- Windows snapped cleanly side-by-side (`Win+Left`, `Win+Right`) with Snap Assist dismissed (`Esc`).
- Audio chime and visual pulse provide clear completion feedback.

### 3. Acceptance Gate for Public Release
- [x] 100% of all 150 tasks defined as concrete, real-life desktop tasks on the machine.
- [x] Automated test harness (`tests/test_universal_tasksuite.py`) passes all regression checks.
- [x] Live computer use demonstrations executed on physical Windows desktop with screenshot proof.
- [x] Zero Windows Defender CFA Event 1123 ransomware alerts triggered.
- [x] Dynamic App Registry persists and rehydrates across process restarts.
