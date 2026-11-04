# ExtraApp — System Architecture & Technical Specification
**Framework:** Tauri v2 (Rust Backend + Native OS WebViews + React 19 Frontend)  
**IPC Protocol:** Local Loopback REST/WebSocket (`127.0.0.1:8000`) & Tauri Core IPC  
**Platforms:** Windows 10/11 (WebView2), macOS 12.3+ (WebKit), Linux (WebKitGTK)  

---

## 1. High-Level Architecture Overview

ExtraApp is architected as a lightweight, zero-daemon desktop companion that interfaces directly with Extra's active local MCP engine:

```
┌────────────────────────────────────────────────────────────────────────┐
│                          EXTRAAPP ARCHITECTURE                         │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │              FRONTEND LAYER (React 19 + Tailwind CSS)            │  │
│  │  • Isomorphic 5-Panel Cockpit    • Live Screen HUD Stream        │  │
│  │  • Real-Time Impact Counters     • Client Toggle Hub             │  │
│  └──────────────────────────────────┬───────────────────────────────┘  │
│                                     │ Tauri IPC (JSON-RPC)             │
│  ┌──────────────────────────────────▼───────────────────────────────┐  │
│  │                   TAURI V2 RUST BACKEND LAYER                    │  │
│  │  • Native System Tray Manager    • Global Panic Hook (Ctrl+Alt+Esc)│  │
│  │  • Local Loopback Client (reqwest)• WebSocket Client (tokio-tungstenite)│
│  │  • Multi-Client Config Serializer• Local Storage Manager (sqlite3)│ │
│  └──────────────────────────────────┬───────────────────────────────┘  │
│                                     │ Local Loopback (127.0.0.1:8000)  │
│  ┌──────────────────────────────────▼───────────────────────────────┐  │
│  │                 EXTRA CORE MCP ENGINE (Python/C++)                │  │
│  │  • Plane A: DXGI GPU Capture     • Plane B: Semantic UIA COM      │  │
│  │  • Win32 / macOS Input Actuator  • SQLite FTS5 Memory Engine     │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. The 3 Technical Layers

### 2.1 The Frontend Layer (React 19 + Tailwind CSS v4)
- **Engine:** Vite + React 19 SPA running inside the native OS webview (Microsoft WebView2 on Windows, WebKit on macOS).
- **Styling:** Tailwind CSS v4 using the verified design tokens from `extra.yantraos.com` and the Isomorphic dashboard design language.
- **State Store:** Lightweight `zustand` store synchronized over WebSocket telemetry.
- **Components:** Radix UI primitives and Lucide Icons for high-density, accessible controls.

### 2.2 The Native Rust Backend Layer (Tauri v2)
- **Process Model:** Single lightweight native binary (< 5 MB) compiled with Rust 2021.
- **System Tray:** Managed via `tauri::tray::TrayIconBuilder`. Listens for click events to toggle window visibility at cursor position.
- **Global Hardware Panic Hook:** Low-level keyboard hook monitoring `Ctrl + Alt + Esc`. When triggered, it dispatches an immediate abort packet to Extra's local server and drops all pending synthetic Win32 mouse/keyboard inputs.
- **Client Configuration Manager:** Directly parses and idempotently merges JSON configurations across:
  - Cursor: `~/.cursor/mcp.json`
  - Claude Desktop: `%APPDATA%\Claude\claude_desktop_config.json`
  - Windsurf: `~/.codeium/windsurf/mcp_config.json`
  - Claude Code: `~/.claude.json`

### 2.3 The Local Loopback Telemetry & Extra Engine Bridge
- **Transport:** HTTP GET/POST and WebSocket connections over `127.0.0.1:8000`.
- **Endpoints:**
  - `GET /health`: Sub-1ms heartbeat confirming engine status.
  - `GET /stats`: Running counters for tokens, cost, and latency saved.
  - `POST /mode`: Speed mode toggle (`turbo`, `balanced`, `smart`).
  - `POST /abort`: Immediate execution cancellation (Panic stop).
  - `WS /ws/telemetry`: Real-time streaming of active window title, focused element, perception thumbnails, and audit events.

---

## 3. Concurrency & Threading Model

```
┌───────────────────────────────────────────────────────────────┐
│                       THREAD CONCURRENCY                      │
├───────────────────────────────┬───────────────────────────────┤
│ THREAD 1: OS Main Thread      │ Win32 Event Loop / UI Window  │
│ THREAD 2: Tokio Async Runtime │ WebSocket telemetry streaming │
│ THREAD 3: Global Hotkey Hook  │ Low-level keyboard monitor    │
│ THREAD 4: File Watcher        │ Client config change listener │
└───────────────────────────────┴───────────────────────────────┘
```

- **Zero-Block Principle:** The OS UI thread never waits on network I/O or filesystem reads. All communication with Extra MCP is dispatched asynchronously via Tokio tasks.
- **Graceful Degradation:** If Extra is not currently running, the Station remains completely functional in "Waiting for Pilot" state, offering a 1-click "Launch Engine" button.

---

## 4. Hardware Panic Switch Sequence

When the user clicks **Panic Stop** or presses `Ctrl + Alt + Esc`:

```
User (Ctrl+Alt+Esc)
      │
      ▼
Rust Global Hook (rdev / WH_KEYBOARD_LL)
      │
      ├─► 1. Flush local OS input queues (Release Win32 virtual keys)
      ├─► 2. Send HTTP POST http://127.0.0.1:8000/abort
      ├─► 3. Extra Engine halts DXGI loop & cancels SendInput pipeline (< 3ms)
      └─► 4. Station UI updates to 🔴 PAUSED status & flashes red warning border
```

---

## 5. Security & Boundary Architecture

1. **Loopback Isolation:** The REST and WebSocket endpoints bind strictly to loopback (`127.0.0.1` / `::1`). External network interfaces are never opened.
2. **DNS Rebinding Defense:** All HTTP headers are verified for `Host: 127.0.0.1` or `Host: localhost`.
3. **Controlled Folder Access (CFA):** The Station stores its preferences and state exclusively in `%USERPROFILE%\.extra\station\` or `~/.extra/station/`, completely bypassing Windows Defender Protected Folders (`Documents`, `Pictures`).
4. **Air-Gap Capable:** The Station functions 100% offline with zero external network connectivity required.
