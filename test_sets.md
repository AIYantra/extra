# Extra 10-Phase Comprehensive Desktop Computer Use Test & Audit Plan

This test suite rigorously verifies all capabilities of **Extra** on Windows 11 desktop: core Win32 input, UWP apps, Electron apps, UIAutomation, visual/audio indicators, memory graph recall, JIT app scouting, skill evolution, StallBreaker resilience, and live application workflows.

---

## Architecture of the Test Sets

| Test # | Subsystem Focus | Applications Involved | Verification Criteria |
| :--- | :--- | :--- | :--- |
| **Test 1** | **Indicators & Feedback** | System Desktop, Audio Engine | `extra_task_start`, ambient edge pulse, cursor halo, status indicator, `extra_task_complete`, audio chime. |
| **Test 2** | **Win32 Input & Snapping** | Notepad, File Explorer | File generation in `.extra/workspace`, `extra_launch`, text verification, `extra_hotkey` window docking (`Win+Left`, `Win+Right`). |
| **Test 3** | **UWP Input & Typing** | Windows Calculator (`calc`) | Foreground activation, direct Win32 `VK_PACKET` formula evaluation (`245.12 * 8 =`), screenshot result capture. |
| **Test 4** | **UIAutomation & Set-of-Mark** | Windows Settings (`ms-settings:`) | `extra_inspect_ui` node extraction, Set-of-Mark bounding box calculations, `extra_click_element` by ID. |
| **Test 5** | **Browser Automation & Web** | Microsoft Edge, `extra_browser` | Web navigation, DOM content extraction, quote/site verification (`extra.yantraos.com`), visual capture. |
| **Test 6** | **Memory Subsystem** | KùzuDB + FastEmbed ONNX | Semantic query recall (`extra_recall_memory`), vector similarity search (< 3ms), relationship graph traversal. |
| **Test 7** | **JIT Scouting & Synthesis** | VLC Media Player (`vlc`) | `extra_scout_app` framework detection, shortcut extraction, multi-directory agentskills.io `SKILL.md` synthesis. |
| **Test 8** | **StallBreaker Resilience** | Desktop Canvas / Controls | Target switching, multi-tool strike resets (click, type, hotkey, scroll), zero false stalls. |
| **Test 9** | **Store & App Exploration** | Microsoft Store (`ms-windows-store:`) | Store launch, window activation, search interaction, safe UI navigation. |
| **Test 10** | **End-to-End Creative Design** | Canva Desktop (Electron) | Native Template Fast-Path, search "Poster", template opening, element creation hotkeys, `extra_evolve_skill`. |

---

## Execution Protocol: Test → Audit → Fix → Advance

For each test set:
1. **Execute** the live workflow using Extra MCP tools directly.
2. **Audit** results (visual screenshot, exit codes, latency, logs).
3. **Fix** any regression, rule conflict, or bug discovered immediately in the source code.
4. **Advance** to the next test set once fully verified.
