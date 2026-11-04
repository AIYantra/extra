# Extra Desktop Station — Release Package v1.0.0

## 📦 Binary Deliverables

- **Standalone Windows Executable:** [`dist-desktop/ExtraApp.exe`](file:///D:/yantra_workspace/extra/app/dist-desktop/ExtraApp.exe)
  - **File Size:** 219,895,729 bytes (~209.7 MB)
  - **SHA256 Checksum:** `7fce71540e06e3bc18d70264c84e2e379ad74e7eff111e90dadda13bfeaa99e5`
  - **Updated At:** 2026-11-01 18:41:50 (Integrated Real Brand Logos & Clean Inverted White Icons on Dark Badges)
- **Native Launcher Scripts:**
  - [`Extra.bat`](file:///D:/yantra_workspace/extra/app/Extra.bat): One-click Windows Command Prompt / Explorer launcher
  - [`Launch-Extra.ps1`](file:///D:/yantra_workspace/extra/app/Launch-Extra.ps1): Sovereign PowerShell launcher
- **Embedded Web Cockpit:** `dist/` (React 19 + TypeScript + Tailwind CSS v4 + Nexsas UI Library)
- **Local MCP Loopback Server:** `run_app.py` (Fast loopback SSE on `http://127.0.0.1:8000`)
- **Desktop Application Viewport:** Chromeless native application window powered by Edge/Chrome standalone application mode (`--app=http://127.0.0.1:5173`) with custom icon and isolated profile in `%USERPROFILE%\.extra\station_profile`.

---

## 🎨 Design System & Theme Alignment

- **Design Library:** Reused from `C:\Users\AdLoa\Downloads\nexsas-270\` (`automation-saas`, `ai-application`).
- **Default Theme:** **Light Theme** matching `https://extra.yantraos.com`.
- **Palette Tokens:**
  - Electric Azure Blue (`#1677ff`)
  - Elevated Card Background (`#ffffff`)
  - Subtle Canvas Background (`#f0f2f6`)
  - Active Dark Pill (`#1a1a1c`)
  - Stroke / Border (`#dfe4eb`)
  - Typography: `Inter Tight`, system-ui

---

## ⚡ Infrastructure: AWS + Cloudflare

- **Edge Layer:** Cloudflare Workers (`extra.yantraos.com`) with `TELEMETRY_KV` and Cloudflare Tunnel.
- **AI Core:** AWS `us-west-2` (Oregon) Production Cluster hosting Amazon Bedrock (`ANTHROPIC_MODEL=us.anthropic.claude-sonnet-4-6`).
- **Local Sovereignty:** 100% offline sovereign mode enabled by default when skipping login. All 20 native MCP tools, skills, and KùzuDB memory run on local hardware with zero network requirements.

---

## 🚀 How to Run

### Method 1: One-Click Executable
Double-click `Extra.bat` or run:
```cmd
dist-desktop\ExtraApp.exe
```

### Method 2: Python Development Server
```powershell
python run_app.py
```
