# ExtraApp — Product Requirements Document (PRD)
**Version:** 1.0.0  
**Status:** Approved  
**Author:** yantraOS Core Team  
**Target Platform:** Windows 10/11, macOS 12.3+, Linux (KDE Wayland / X11)  
**Binary Footprint:** < 8 MB installer, < 35 MB RAM  

---

## 1. Executive Summary & Vision

### 1.1 The Problem
Today, **Extra** operates as an ultra-fast, headless Model Context Protocol (MCP) server. While developers and autonomous agents appreciate its silent, flashless execution, end-users face **"The Black-Box Anxiety"**:
1. **Perception Void:** Users cannot tell at a glance if Extra is actively running, idle, or stalled.
2. **Loss of Control (Fear of the Rogue Agent):** When an LLM begins clicking and typing, users feel helpless if the agent clicks the wrong button. There is no universal "Emergency Panic Brake".
3. **Invisible Value:** Extra saves users tens of thousands of vision tokens and dollars by replacing screenshot loops with native UI Automation trees, but users never *see* those savings.
4. **Configuration Friction:** Non-CLI users struggle to know which AI apps (Cursor, Claude, Windsurf) have Extra enabled.

### 1.2 The Solution: ExtraApp
**ExtraApp** is a sovereign, lightweight desktop companion application built with **Tauri v2**. It lives silently in the system tray and pops open on demand to provide:
- A real-time **Pilot Radar** displaying what the AI sees and controls right now.
- A physical **Emergency Kill Switch** (`Ctrl + Alt + Esc` global hotkey) to freeze all automation instantly.
- A **Brave-Style Impact Shield** showing live counters for tokens, dollars, and minutes saved.
- A **1-Click AI Client Configurator** to toggle Extra across Cursor, Claude Desktop, and Windsurf without touching JSON files.
- A **First Missions Launcher** allowing instant execution and testing of verified workflows.

---

## 2. Target Personas

| Persona | Environment | Primary Need | Station Value |
| :--- | :--- | :--- | :--- |
| **The Cursor / IDE Builder** | Windows / macOS · Cursor IDE | Wants fast computer-use while coding; hates bloated background apps. | Tiny footprint (<30 MB RAM), 1-click MCP toggling, zero lag. |
| **The Claude Desktop Operator** | Windows / Mac · Claude Desktop | Uses Claude for administrative desktop tasks (files, spreadsheets). Needs high confidence and safety. | Visual proof of life, instant Panic Stop button, live action log. |
| **The Autonomous AI Engineer** | Linux / Windows · Headless Agents | Debugs multi-turn desktop loops, evaluates token consumption. | DXGI live vision stream, token savings telemetry, audit logs. |

---

## 3. Product Principles

1. **Lightweight Above All Else:** Never exceed 8 MB download size or 35 MB RAM. No bundled Chromium runtimes.
2. **Sovereign Safety First:** Human physical control always overrides AI input. The Kill Switch is an absolute circuit breaker.
3. **Zero Configuration Drift:** The Station reads and writes directly to the authoritative client configurations (`~/.cursor/mcp.json`, `claude_desktop_config.json`, etc.).
4. **Isomorphic Modern Aesthetic:** High-density, dark/light contrast, sleek status pills, and zero visual clutter.

---

## 4. Functional Specifications & The 5 Core Panels

```
┌────────────────────────────────────────────────────────────────────────┐
│  🟢 EXTRA STATION                    [Turbo Mode ▼]  [🛑 PANIC STOP]  │
├────────────────────────────────────────────────────────────────────────┤
│  [1. LIVE PILOT RADAR]                 [2. BRAVE-STYLE IMPACT SHIELD] │
│  Active Client: Cursor (PID 1824)       Tokens Saved:    1,420,500     │
│  Target App:    Excel (Book1.xlsx)      Estimated Cost:  $18.42 USD    │
│  Perception:    DXGI VRAM (11.2ms)      Time Reclaimed:  42 minutes    │
│  Live Feed:     [ Mini Screen HUD ]                                    │
├────────────────────────────────────────────────────────────────────────┤
│  [3. 1-CLICK CLIENT CONFIGURATOR]      [4. FIRST MISSIONS LAUNCHER]    │
│  [✔] Cursor IDE          [Active]       🪄 The Desktop Magic Trick     │
│  [✔] Claude Desktop      [Active]       🧮 The Fast Calculator         │
│  [✔] Windsurf IDE        [Active]       📁 The Safe File Organizer     │
│  [ ] Claude Code CLI     [Connect]      [ 1-Click Test Execution ]     │
├────────────────────────────────────────────────────────────────────────┤
│  [5. SOVEREIGN LIVE AUDIT TRAIL]                                       │
│  • 12:45:10 — Window Snapped Left (50%) · Settled (14ms)               │
│  • 12:45:11 — Launch notepad.exe · Focused (22ms)                      │
│  • 12:45:12 — Win32 Key Injection "Haiku draft" (0.4ms)               │
└────────────────────────────────────────────────────────────────────────┘
```

### 4.1 Top Bar & Safety Rail
- **Status Indicator:** Glowing pill badge (`🟢 Active Pilot: Cursor` | `⚪ Idle` | `🔴 Paused / Locked`).
- **Speed Mode Selector:** Instant toggle between `⚡ Turbo` (<15ms batch), `⚖️ Balanced`, and `🧠 Smart` (deliberate verification).
- **Emergency Panic Button:** Prominent red button. Clicking or pressing `Ctrl + Alt + Esc` triggers an immediate Win32 hardware queue purge, cancels active batch commands, and disengages the MCP actuator.

### 4.2 Panel 1: Live Pilot Radar & Perception Feed
- Hardware-accelerated mini screen thumbnail showing what Extra's DXGI capture engine sees in real time.
- Set-of-Mark (SoM) bounding box overlays showing active interactive elements.
- Active window metadata: executable name, window title, PID, and focus duration.

### 4.3 Panel 2: Brave-Style Impact Shield
- **Vision Tokens Saved:** Running tally of tokens saved by utilizing the Semantic UI Automation plane (Plane B) instead of sending full-resolution 4K images to multimodal LLMs.
- **Estimated Dollar Savings:** Computed based on standard multimodal vision pricing ($3.00 / 1M tokens).
- **Time Reclaimed:** Cumulative seconds/minutes saved through sub-15ms fast paths vs. human-speed execution.

### 4.4 Panel 3: 1-Click Client Configurator
- Auto-detects Cursor, Claude Desktop, Windsurf, Claude Code, and agy.
- Provides visual toggle switches: enables or disables Extra in any client with one click, automatically handling file locking and JSON serialization.

### 4.5 Panel 4: First Missions Launcher
- Embedded cards for verified starter missions:
  - 🪄 *The Desktop Magic Trick* (Window Snap + Notepad Haiku)
  - 🧮 *The Fast Calculator* (Math Calculation)
  - 📁 *The Safe File Organizer* (Desktop Cleanup)
- Allows 1-click prompt copying or direct local test dispatch.

### 4.6 Panel 5: Sovereign Live Audit Trail
- Real-time scrolling audit log displaying every native OS call dispatched by Extra.
- Includes timestamp, API plane used (DXGI, UIA, Win32 SendInput), duration, and outcome status.

---

## 5. Non-Functional Requirements & Performance SLAs

| Requirement | Target SLA | Verification Method |
| :--- | :--- | :--- |
| **Download Size** | < 8 MB | MSI / NSIS installer binary size check |
| **Memory Footprint** | < 35 MB RAM | Windows Task Manager / `psutil` RSS measurement |
| **Cold Startup Time** | < 300 ms | Timestamp from launch to first UI frame |
| **Panic Response** | < 5 ms | Latency from `Ctrl+Alt+Esc` to input queue abort |
| **Telemetry & Privacy** | 100% Local | Zero unconsented outbound network calls; verified via Wireshark / Fiddler |
