<div align="center">

<a href="https://extra.yantraos.com">
  <img src="https://raw.githubusercontent.com/AIYantra/extra/main/assets/logo.png" alt="Extra — Get extra from your AI on Mac" width="420" />
</a>

# Extra for macOS

### The Open-Source Astra 6 for your Mac
**Your AI can see, click, type, navigate, and get real work done on macOS.**

<!-- mcp-name: io.github.AIYantra/extra -->

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: macOS Monterey | Ventura | Sonoma | Sequoia](https://img.shields.io/badge/Platform-macOS%2012.3%2B-000000.svg?logo=apple&logoColor=white)](https://apple.com/macos)
[![Architecture: Apple Silicon M1-M4 & Intel](https://img.shields.io/badge/Arch-arm64%20%7C%20x86__64-orange.svg)](https://apple.com)
[![Protocol: Model Context Protocol (MCP)](https://img.shields.io/badge/Protocol-MCP%20Native-orange.svg)](https://modelcontextprotocol.io)
[![Ecosystem: yantraOS](https://img.shields.io/badge/Ecosystem-yantraOS-8A2BE2.svg)](https://yantraos.com)
[![Status: Open Source](https://img.shields.io/badge/Open%20Source-%E2%99%A5-emerald.svg)](https://github.com/AIYantra/extra)

[Website](https://extra.yantraos.com) • [Quickstart](#-quickstart-1-minute) • [Architecture](ARCHITECTURE_MACOS.md) • [Implementation Plan](macOS.md) • [License](LICENSE)

<br/>
<br/>

</div>

---

## ✨ Why Extra on Mac?

Today's AI assistants (Claude, Antigravity, Cursor, AGY) can write code and generate text, but they cannot directly touch your Mac desktop. When you need them to click a button, open an app, organize files, or extract information from a Mac window, they are limited to chat.

**Extra gives your AI native hands and eyes on macOS.**

Powered by Apple's native **ScreenCaptureKit**, **CoreGraphics Event Taps**, and the **Accessibility API (`AXUIElement`)**, Extra connects your AI agent directly to your macOS desktop with sub-10ms perception, pixel-perfect Retina clicking, and zero-latency typing.

* 🚀 **Sub-5ms Screen Capture**: Hardware-accelerated GPU frame buffer grabs via ScreenCaptureKit.
* 🎯 **Semantic Tree Inspection**: Inspects native macOS buttons, text fields, and tabs directly via `AXUIElement`.
* ⚡ **Instant Unicode Typing**: Zero-lag text and emoji injection using CoreGraphics event taps.
* 🛡️ **Zero Solo-Dev Binary Blobs**: Built 100% on official Apple frameworks and Anthropic's Model Context Protocol.
* 🔒 **100% Local & Sovereign**: No cloud screencasting, no telemetry, zero phone-home calls.

---

## 💡 What You Can Ask Your AI To Do on Mac

* 📊 **Calculations & Data**: *"Launch Calculator, compute our valuation multiples, and paste the results into TextEdit."*
* 🗂️ **Finder & File Organization**: *"Open Finder, organize my Downloads folder by moving DMG installers to Trash and grouping PDFs by date."*
* 🌐 **Web Research**: *"Open Safari or Chrome, search for the latest arXiv papers on multimodal agents, and summarize them."*
* ⚙️ **Mac System Settings**: *"Open System Settings, check my display scaling and battery health, and report back."*
* 🎵 **Media Control**: *"Open Spotify or Music, play low-fi focus tracks, and adjust the volume."*

---

## ⚡ Quickstart (1 Minute)

You can set up Extra on your Mac in three easy ways:

### Option A: Ask Your AI To Set It Up (Primary Funnel — Easiest / 80% Target)

Simply copy and paste this single directive into **Claude Desktop**, **Google Antigravity**, **Cursor**, **Windsurf**, or any MCP-enabled agent:

```text
Setup Extra on my Mac: In Terminal run 'curl -sSL https://extra.yantraos.com/install.sh | bash', then read and configure ~/.extra/app/STARTER_PROMPT_MACOS.md so we are ready to use Extra.
```

**How It Works:**
1. Your AI opens a terminal session and triggers `curl -sSL https://extra.yantraos.com/install.sh | bash`.
2. The installer runs unattended, setting up the isolated environment, configuring MCP for Claude Desktop, Cursor, Windsurf, and Antigravity, and deploying always-on rules.
3. Your AI inspects `~/.extra/app/STARTER_PROMPT_MACOS.md`, activates its execution rules, and replies:
   > **"We are ready! Please restart <your AI application> to make it work."**
4. Once restarted, your AI possesses native macOS computer control (`extra_*` suite).

---

### Option B: Run Terminal One-Liner Yourself (For Developers)

Open standard macOS **Terminal** or **iTerm2** and run:

```bash
curl -sSL https://extra.yantraos.com/install.sh | bash
```

The automated installer will:
1. Verify macOS 12.3+ (Monterey, Ventura, Sonoma, Sequoia) on Apple Silicon (`arm64`) or Intel (`x86_64`).
2. Discover or install Python 3.10+ in an isolated environment (`~/.extra/venv`).
3. Install official dependencies (`mcp`, `playwright`, `pyobjc-framework-*`).
4. Automatically configure **Claude Desktop**, **Cursor**, **Windsurf**, and **Antigravity CLI** (`agy`).
5. Run the diagnostic doctor and display the 1-step starter prompt.

---

### Option C: Developer Git Clone

For developers who prefer to inspect before running:

```bash
git clone https://github.com/AIYantra/extra.git ~/.extra/app
cd ~/.extra/app && ./install.sh
```

---

## 🔒 macOS Permissions Guide (Crucial)

To allow Extra to see your screen and synthesize mouse/keyboard input, macOS requires granting two permissions in **System Settings → Privacy & Security**:

```
┌────────────────────────────────────────────────────────────────────────┐
│                      REQUIRED MACOS PERMISSIONS                        │
├──────────────────────────┬─────────────────────────────────────────────┤
│ 1. Accessibility         │ Allows Extra to inspect UI elements via     │
│                          │ AXUIElement and synthesize mouse/keyboard.  │
├──────────────────────────┼─────────────────────────────────────────────┤
│ 2. Screen Recording      │ Allows ScreenCaptureKit and CoreGraphics to │
│                          │ capture desktop frames for vision models.   │
└──────────────────────────┴─────────────────────────────────────────────┘
```

### Fast 1-Click Deep Links:
Rather than navigating menus, run these commands in Terminal to open the exact settings panes instantly:

```bash
# Open Accessibility settings pane:
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"

# Open Screen Recording settings pane:
open "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture"
```
*(Or simply run: `extra permissions open`)*

### Verification:
Run `extra doctor` to confirm both checks pass `[OK]`. If permissions are missing, `extra doctor` will present this guidance card:

```text
┌────────────────────────────────────────────────────────────────────────┐
│               ACTION REQUIRED: MACOS SECURITY PERMISSIONS              │
├────────────────────────────────────────────────────────────────────────┤
│ Extra requires two standard permissions to automate your Mac:          │
│                                                                        │
│ 1. Accessibility:                                                      │
│    Run: open "x-apple.systempreferences:com.apple.preference.security? │
│               Privacy_Accessibility"                                   │
│    -> Toggle ON: Terminal / iTerm2 / Claude Desktop                    │
│                                                                        │
│ 2. Screen Recording:                                                   │
│    Run: open "x-apple.systempreferences:com.apple.preference.security? │
│               Privacy_ScreenCapture"                                   │
│    -> Toggle ON: Terminal / iTerm2 / Claude Desktop                    │
│                                                                        │
│ Once enabled, run 'extra doctor' to verify all checks pass [OK].       │
└────────────────────────────────────────────────────────────────────────┘
```

### Recovery & Troubleshooting:
If macOS permissions become corrupted or unresponsive:
```bash
# Reset Terminal permissions
tccutil reset Accessibility com.apple.Terminal
tccutil reset ScreenCapture com.apple.Terminal

# Or via Extra CLI
extra permissions reset --client Terminal
```

---

## 🤖 Configuring Host AI Agents

### 1. Claude Desktop (macOS)

Add Extra to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "extra": {
      "command": "/Users/YOUR_USERNAME/.extra/venv/bin/python",
      "args": ["-m", "extra.mcp.server"]
    }
  }
}
```
*(Replace `YOUR_USERNAME` with your macOS username).*

### 2. Cursor (macOS)

Add Extra to `~/Library/Application Support/Cursor/User/globalStorage/cursor.mcp/mcp.json` or `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "extra": {
      "command": "/Users/YOUR_USERNAME/.extra/venv/bin/python",
      "args": ["-m", "extra.mcp.server"]
    }
  }
}
```

### 3. Windsurf (macOS)

Add Extra to `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "extra": {
      "command": "/Users/YOUR_USERNAME/.extra/venv/bin/python",
      "args": ["-m", "extra.mcp.server"]
    }
  }
}
```

### 4. Google Antigravity CLI (`agy`) or IDE

Register Extra directly via CLI:
```bash
agy mcp add extra "$HOME/.extra/venv/bin/python" -m extra.mcp.server
```

Or in your Antigravity MCP configuration (`~/.gemini/config/mcp_config.json`):
```json
{
  "mcpServers": {
    "extra": {
      "command": "/Users/YOUR_USERNAME/.extra/venv/bin/python",
      "args": ["-m", "extra.mcp.server"],
      "disabled": false
    }
  }
}
```

---

## 🛠️ Extra CLI on macOS

Project Extra provides a fast diagnostic and automation CLI:

```bash
# Test screen capture (saves screenshot to current directory)
extra capture --output desktop.png

# Test deterministic app launch
extra launch calc

# Inspect active window UI elements
extra inspect

# Test instant typing
extra type "Hello from Extra on Mac!" --enter

# Run full permission and environment doctor
extra doctor
```

---

## 🏛️ Architecture & Documentation

* [**Architecture Specification (`ARCHITECTURE_MACOS.md`)**](ARCHITECTURE_MACOS.md) — Deep-dive into ScreenCaptureKit, CoreGraphics Event Taps, and `AXUIElement` architecture.
* [**Implementation Plan (`macOS.md`)**](macOS.md) — Phase-by-phase porting milestones and technical specification.
* [**Starter System Prompt (`STARTER_PROMPT_MACOS.md`)**](STARTER_PROMPT_MACOS.md) — Operational guidelines and prompts for AI assistants.

---

## 📄 License

Project Extra is licensed under the **MIT License**. Free for personal, commercial, and enterprise use.
