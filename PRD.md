# Product Requirements Document (PRD) — Project "Extra"

**Product Name:** Extra (`extra.yantraos.com`)  
**Repository:** `AIYantra/extra`  
**Parent Ecosystem:** yantraOS (`AIYantra` / Euryale Ferox Private Limited)  
**Target Platform:** Windows 11 & Windows 10 (64-bit)  
**Launch Target:** 24-Hour Soft Launch  
**Version:** 0.1.0-alpha  

---

## 1. Executive Summary & Vision

**Extra** is an open-source, ultra-low-latency ("flashless") desktop automation bridge that brings the sovereign Computer Use capabilities of **yantraOS** to **Windows 11 and Windows 10**.

While Google’s Project Astra, Anthropic Computer Use, and existing Python automation scripts suffer from sluggish frame rates (150–300ms capture), high vision-token burn, DPI coordinate drift, and frequent infinite-loop stalls, **Extra** introduces a **Hybrid Dual-Plane Engine**:
1. **Visual Plane:** DirectX Desktop Duplication (DXGI) & MSS screen capture (sub-3ms frame grabs).
2. **Semantic Plane:** Windows UI Automation (UIA v3) COM inspection, providing 100% deterministic, pixel-perfect element clicking.
3. **Model Context Protocol (MCP) Native:** Instantly connects to Antigravity, Claude Desktop, Cursor, AGY, and any LLM with zero configuration.

**Strategic Role:** Extra serves as the primary soft-launch ambassador and onboarding funnel for **yantraOS**, proving the speed and autonomy of the AIYantra stack directly on the world's most ubiquitous desktop OS.

---

## 2. Problem Statement & Opportunities

| Existing Problem in Astra / Anthropic / PyAutoGUI | Root Cause | Extra's Solution |
| :--- | :--- | :--- |
| **High Latency (3–6s per step)** | Legacy GDI screen capture (`BitBlt`) taking 150–300ms + massive full-res vision token processing. | **DXGI / MSS Capture (< 3ms)** + ROI cropping and Windows UIA semantic element targeting. |
| **DPI & Multi-Monitor Misclicks** | Windows DPI Virtualization on 125%/150%/200% displays causes 20–50% coordinate offset. | **Strict `PerMonitorV2` DPI normalization** mapping physical hardware pixels directly. |
| **Fragile Blind Clicks** | Vision models guessing tiny 16×16 button bounding boxes on complex application interfaces. | **Direct UIA v3 Element Invocation** queryable by `Name`, `AutomationId`, or `ControlType`. |
| **Typing Lag & Character Drops** | Simulating key-down/key-up with 50ms sleeps chokes on long strings, emojis, and Unicode. | **Win32 `SendInput` with `KEYEVENTF_UNICODE`** (500 chars in 2ms, zero dropped keys). |
| **Infinite Loop Stalls** | Agent clicks an unresponsive or disabled control and repeats endlessly, wasting money. | **Closed-loop perceptual hash (`phash`) diffing** with a 2-strike automated stall-breaker. |
| **Security & Antivirus False Positives** | Unverified C++/Rust wheels triggering Windows Defender `Trojan:Win32/Wacatac` heuristics. | **Enterprise-audited stack:** Microsoft-owned (`playwright`), Anthropic-owned (`mcp`), and native Win32 DLLs. |

---

## 3. Goals & Non-Goals

### 3.1 Primary Goals (Launch within 24 Hours)
* **G1 — 1-Minute Onboarding:** A user runs a single PowerShell command (`irm https://extra.yantraos.com/install.ps1 | iex`) on Windows 11/10 to provision dependencies and start the bridge.
* **G2 — Universal AI Compatibility:** Provide an official Model Context Protocol (MCP) server that works immediately with Claude Desktop, Antigravity, Cursor, and custom agent scripts.
* **G3 — "Flashless" Performance:** Achieve sub-10ms local screen capture and input injection latency.
* **G4 — Enterprise Trust:** 100% clean pedigree—zero obscure binary blobs; only Microsoft, Anthropic, and foundational Python Software Foundation packages.
* **G5 — Closed-Loop Safety:** Automatic fail-safe abort corners, user interruption shortcuts (`Ctrl+Alt+Esc`), and automated visual stall breakers.

### 3.2 Non-Goals (Post-Launch / v1.0)
* *NG1:* Replacing yantraOS on bare metal (Extra is a Windows bridge; yantraOS is the sovereign OS).
* *NG2:* Custom local LLM weights distribution (Extra connects to user-supplied API keys or local Ollama instances).
* *NG3:* Kernel-mode device driver installation (stays entirely in user space via Win32 and Microsoft system DLLs).

---

## 4. User Personas & Workflows

### Persona A: The AI Developer / Power User (Alex)
* **Goal:** Wants Claude Code or Antigravity to automate testing of their desktop app, reorganize local files, or research flights on their Windows 11 laptop.
* **Workflow:**
  1. Runs `extra run` in terminal.
  2. Copies the MCP server config into their agent configuration.
  3. Prompts the agent: *"Fill out the quarterly report in Excel using the data in `invoices/`."*
  4. Watches the agent execute smoothly with zero coordinate misclicks.

### Persona B: The Enterprise Analyst (Priya)
* **Goal:** Needs repetitive data entry across legacy Win32 ERP software and a modern browser without risking malware from unverified packages.
* **Workflow:**
  1. Audits Extra’s dependency manifest (verifies Microsoft and Anthropic provenance).
  2. Deploys Extra to Windows 10 workstation.
  3. Uses hybrid UIA element targeting to extract table rows and submit forms deterministically.

---

## 5. Functional Requirements (FR)

* **FR-1: Ultra-Fast Screen Capture**
  * Support Windows DXGI Desktop Duplication API and fallback to MSS (`gdi32.dll` via `ctypes`).
  * Capture full screen or specified monitor within ≤ 5ms.
  * Provide region-of-interest (ROI) cropping and JPEG/PNG compression with base64 encoding.

* **FR-2: Zero-Latency Hardware & Unicode Input**
  * Support instant text typing using `KEYEVENTF_UNICODE` / `VK_PACKET`.
  * Support atomic virtual clipboard swaps for large code or text payloads (> 100 characters).
  * Support multi-key combinations (`Win+R`, `Alt+Tab`, `Ctrl+Shift+Esc`, etc.).
  * Smooth Bézier mouse movement option (to avoid jarring jumps) and immediate hardware clicks.

* **FR-3: Windows UI Automation (UIA) Semantic Plane**
  * Query interactive UI trees of active windows via Microsoft `UIAutomationCore.dll`.
  * Extract control properties: `Name`, `AutomationId`, `ControlType`, `BoundingRectangle`, and `IsEnabled`.
  * Enable direct invocation of buttons and menu items via `InvokePattern` without requiring pixel clicks.

* **FR-4: Fast-Path Launchers**
  * Instant deterministic app launch via `ShellExecuteEx` / `Win+R` aliases (e.g. Chrome, Edge, Notepad, Calculator, Explorer).
  * Direct web DOM extraction via Playwright/Edge CDP when browser automation is requested.

* **FR-5: Closed-Loop Stall Breaker & Safety Guardrails**
  * Compare perceptual hash (`phash`) of target bounding box before and after action.
  * If two consecutive interactive actions yield no visual or window state change, halt and report `STALL_DETECTED` with diagnostic context.
  * Moving mouse to screen corner (0, 0) immediately halts all agent automation.
  * Global emergency kill-switch hotkey (`Ctrl+Alt+Shift+Q`).

* **FR-6: Model Context Protocol (MCP) Standard Interface**
  * Expose standard tools: `extra_screenshot`, `extra_click`, `extra_type`, `extra_key`, `extra_inspect_ui`, `extra_launch`.
  * Output ready-to-use JSON snippets for `claude_desktop_config.json` and Antigravity workspace config.

---

## 6. Non-Functional Requirements (NFR)

* **NFR-1: Performance & Latency**
  * Total frame-to-action execution overhead (excluding LLM inference time) < 20ms.
* **NFR-2: Compatibility**
  * Fully compatible with Windows 10 (Build 19041+) and Windows 11 (22H2, 23H2, 24H2).
  * Automatic scaling adaptation across mixed DPI setups (100% to 250%).
* **NFR-3: Security & Clean Pedigree**
  * Zero third-party unsigned binary DLLs or pre-compiled solo-maintainer wheels.
  * All low-level OS calls utilize Windows built-in DLLs (`user32.dll`, `shcore.dll`, `dxgi.dll`, `UIAutomationCore.dll`).
* **NFR-4: Zero Footprint Uninstallation**
  * Clean teardown removing virtual environments, cache, and MCP registrations cleanly.

---

## 7. Launch Deliverables & Success Metrics (24-Hour Horizon)

1. **GitHub Repository:** `github.com/AIYantra/extra` with complete source code, tests, and documentation.
2. **Landing Page:** `extra.yantraos.com` showcasing the 1-line PowerShell installer and interactive comparison with Astra 6.
3. **Demo Asset:** A 45-second video/GIF showing Extra executing an end-to-end multi-app workflow on Windows 11.
4. **Starter Prompt:** `STARTER_PROMPT.md` allowing any user to copy-paste into Claude/ChatGPT and instantly turn it into an autonomous Windows operator.
