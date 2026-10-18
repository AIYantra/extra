<div align="center">

<a href="https://extra.yantraos.com">
  <img src="https://raw.githubusercontent.com/AIYantra/extra/main/assets/logo.png" alt="Extra — Get extra from your AI on Linux" width="420" />
</a>

# Extra for Linux

### The Sovereign, Open-Source Computer-Use Engine for Linux
**Your AI can see, click, type, navigate, and get real work done across Wayland & X11.**

<!-- mcp-name: io.github.AIYantra/extra -->

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: Arch | Ubuntu | Debian | Fedora](https://img.shields.io/badge/Platform-Linux%20Kernel%206.x%2B-FCC624.svg?logo=linux&logoColor=black)](https://kernel.org)
[![Compositors: Wayland & X11](https://img.shields.io/badge/Compositor-Wayland%20%7C%20X11-555555.svg)](https://wayland.freedesktop.org)
[![Protocol: Model Context Protocol (MCP)](https://img.shields.io/badge/Protocol-MCP%20Native-orange.svg)](https://modelcontextprotocol.io)
[![Ecosystem: yantraOS](https://img.shields.io/badge/Ecosystem-yantraOS-8A2BE2.svg)](https://yantraos.com)
[![Status: Open Source](https://img.shields.io/badge/Open%20Source-%E2%99%A5-emerald.svg)](https://github.com/AIYantra/extra)

[Website](https://extra.yantraos.com) • [Quickstart](#-quickstart-1-minute) • [Architecture](ARCHITECTURE_LINUX.md) • [Starter Prompt](STARTER_PROMPT_LINUX.md) • [License](LICENSE)

<br/>
<br/>

</div>

---

## ✨ Why Extra on Linux?

Linux desktop automation has historically suffered from fragmented display servers (Wayland vs. X11), brittle shell scripts, and lack of semantic accessibility integration.

**Extra delivers unified, high-performance computer use across all major Linux distributions.**

* 🚀 **Sub-10ms Perception**: Multi-tier capture with KDE Wayland `spectacle`, wlroots `grim`, and X11 MIT-SHM `mss`.
* ⚡ **Kernel `/dev/uinput` Injection**: Hybrid absolute/relative virtual input device with terminal-aware atomic clipboard pasting (`Ctrl+Shift+V` for terminals vs `Ctrl+V` for GUI).
* 🎯 **Pure-Python AT-SPI2 Engine**: Sub-15ms semantic accessibility tree traversal and `< 1ms` direct `DoAction(0)` widget actuation over D-Bus without C-library dependencies.
* 🪟 **Sub-15ms Snapping & Focus**: Injected KWin Scripting and WindowsRunner D-Bus query for programmatic split/side-by-side layouts without keyboard shortcuts.
* 🎵 **Procedural Audio & Ambient HUD**: In-memory glass marimba synthesizer streaming to PipeWire (`pw-play`), PulseAudio (`paplay`), and ALSA (`aplay`), coupled with sub-2ms D-Bus desktop notifications.
* 🔒 **100% Local & Sovereign**: Zero cloud dependencies, zero telemetry.

---

## 💡 What You Can Ask Your AI To Do on Linux

* 📊 **Calculations & Data**: *"Open calculator, calculate revenue growth, and paste into a briefing document."*
* 🗂️ **Desktop & File Management**: *"Open Dolphin, organize my Downloads folder by date, and create an archive of project logs."*
* 🌐 **Web Research & Browsing**: *"Open Chromium or Firefox, look up the release notes for Linux kernel 6.12, and summarize them."*
* 💻 **Terminal Workflows**: *"Open Konsole, check git status on my workspace, and report active branches."*
* 🪟 **Window Organization**: *"Snap Dolphin to the left half and Kate to the right half."*

---

## ⚡ Quickstart (1 Minute)

### Option A: Ask Your AI To Set It Up (Recommended)

Copy and paste this directive into **Claude Desktop**, **Antigravity**, **Cursor**, **Windsurf**, or any MCP agent:

```text
Setup Extra on my Linux machine: In Terminal run 'curl -sSL https://extra.yantraos.com/install.sh | bash', then read and configure ~/.extra/app/STARTER_PROMPT_LINUX.md so we are ready to use Extra.
```

Your AI will run the installer, configure MCP and local rules, and report:
> **"We are ready! Please restart <your AI application> to make it work."**

---

### Option B: One-Line Terminal Setup

Run the universal installer in your terminal:

```bash
curl -sSL https://extra.yantraos.com/install.sh | bash
```

Verify your setup anytime by running:

```bash
extra doctor
```

---

## 🐧 Distribution Compatibility

| Distribution | Package Manager | Input Backend | Capture Pipeline | Accessibility |
| :--- | :--- | :--- | :--- | :--- |
| **yantraOS / Arch Linux** | `pacman` | `/dev/uinput` | KWin / spectacle | AT-SPI2 D-Bus |
| **Ubuntu / Debian** | `apt` | `/dev/uinput` | Mutter / X11 / mss | AT-SPI2 D-Bus |
| **Fedora** | `dnf` | `/dev/uinput` | Portal / PipeWire | AT-SPI2 D-Bus |
| **openSUSE** | `zypper` | `/dev/uinput` | Wayland / X11 | AT-SPI2 D-Bus |

---

## 🛠️ CLI Utilities

```bash
extra doctor         # Run complete system health & hardware diagnostics
extra inspect        # Inspect active window semantic UI element tree
extra snap --som     # Capture desktop screenshot with numbered Set-of-Mark badges
extra test           # Run end-to-end integration test suite
```

---

## 📄 License

MIT © 2026 AIYantra & Project Extra Contributors.
