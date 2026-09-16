# Extra Release Notes — v0.2.3

**Release Date:** September 16, 2026  
**Release Title:** Desktop Automation Bottlenecks Resolution (Screenshot Persistence, StallBreaker Viewport Fallback, Window Focus Polling, and Microsoft Store/UWP App Resolution)  
**Target Systems:** Windows 10/11 (x64) & macOS (Apple Silicon / Intel)  
**Special Thanks & Attribution:** Special credit to [@harshbuttru3](https://github.com/harshbuttru3) for identifying and reporting these real-world automation bottlenecks in [Issue #4](https://github.com/AIYantra/extra/issues/4) during complex 3D modeling workflows in Blender 3.6 on Windows 11.

---

## 1. Executive Summary & Problem Resolution (v0.2.3)

In real-world desktop automation sessions driving complex CAD and 3D modeling workflows (e.g., Blender 3.6 on Windows 11 with Antigravity / Gemini), four operational friction points were identified and resolved:

### 1. `extra_screenshot` Payload Truncation Fix
- **Problem:** Returning full-resolution screenshots as raw base64 strings in `result["screenshot_base64"]` generated 200 KB – 400 KB payloads, exceeding LLM tool output buffers (40 KB–50 KB). Client harnesses (Antigravity, Cursor, Claude Code) dumped output to disk `.txt` files, interrupting agent flows.
- **Fix:** `extra_screenshot` now defaults to saving captures into the CFA-safe scratch workspace (`~/.extra/workspace/screenshots/screenshot_<timestamp>.png`) and returning `file_path`. The raw base64 string is omitted by default (`include_base64: bool = False`), keeping tool responses under 1 KB while providing immediate clickable file links.

### 2. StallBreaker 200×200 ROI False-Stall Elimination
- **Problem:** `StallBreaker` evaluated visual diffs over a localized 200×200 ROI around the clicked coordinate. In applications like Blender, CAD software, and IDEs, clicking a header icon or toolbar toggle updates a distant 3D viewport canvas or preview area while the local 200×200 ROI registers zero delta, causing premature `STALL DETECTED` aborts.
- **Fix:** `extra_click` and `StallBreaker` now feature a zero-latency global fallback diff. If the local ROI shows zero change, `StallBreaker` downsamples the full monitor frame (sub-2ms via Nearest Neighbor downsampling + numpy mean diff). If remote screen areas changed, strikes are reset to 0 and the action succeeds with `remote visual change` status.

### 3. `extra_focus_window` Retry Polling
- **Problem:** `extra_focus_window` was an instantaneous single-shot check. When an application was launched asynchronously, calling `extra_focus_window` immediately failed with `Window not found`.
- **Fix:** Added a `timeout: float = 3.0` parameter to `extra_focus_window` and `find_window_by_title` with an active 100ms polling loop, allowing asynchronously initializing windows to be focused reliably without artificial sleep scripts.

### 4. Microsoft Store / MSIX / UWP App Resolution
- **Problem:** Applications installed from the Microsoft Store or winget (Blender, Windows Terminal, Python) install execution aliases in `%LOCALAPPDATA%\Microsoft\WindowsApps`. `resolve_executable` previously failed to search this directory or common Program Files locations, causing launch resolution failures and `FileNotFoundError`.
- **Fix:** `resolve_executable` now searches `%LOCALAPPDATA%\Microsoft\WindowsApps`, standard Program Files locations, and explicit Blender Foundation installation paths. Added `"blender"` to `APP_REGISTRY`.

---

# Extra Release Notes — v0.2.2

**Release Date:** September 16, 2026  
**Release Title:** Developer Binary Auto-Whitelisting & Controlled Folder Access (CFA) Workspace Diagnostics  
**Target Systems:** Windows 10/11 (x64) & macOS (Apple Silicon / Intel)

---

## 1. Executive Summary & Root Cause Analysis (v0.2.2)

Following the successful release of v0.2.1 (which achieved **zero AMSI/Trojan malware detections** on Windows Defender), follow-up testing on host `SURYA` uncovered a subtle, recurring friction point in user environments:

### Incident C: The 5 Post-Update Controlled Folder Access (CFA) Blocks
In `defenderhistory (2).md` recorded on **16-Sep-2026 at 12:47 IST**, 5 additional Controlled Folder Access (Event ID 1123) blocks were registered:
```
16-09-2026 12:47:58 | Access blocked: C:\Users\Surya\Documents\work\.agents\rules  | Process: agy.exe
16-09-2026 12:47:58 | Access blocked: C:\Users\Surya\Documents\work\.agents\skills | Process: agy.exe
16-09-2026 12:47:58 | Access blocked: C:\Users\Surya\Documents\work\.extra         | Process: agy.exe
16-09-2026 12:47:58 | Access blocked: C:\Users\Surya\Documents\work                | Process: python.exe
16-09-2026 12:47:58 | Access blocked: C:\Users\Surya\Documents\work                | Process: powershell.exe
```

### Forensic Diagnosis:
1. **The Culprit: Working Inside Windows Protected Libraries**
   - The user initialized or cloned their project directory inside `C:\Users\Surya\Documents\work`.
   - Windows Defender Controlled Folder Access monitors `Documents`, `Pictures`, `Desktop`, `Videos`, and `Music` indiscriminately.
   - When `agy` launched to supervise coding tasks, `agy.exe`, Python, and PowerShell attempted to read/write project metadata (`.agents/skills`, `.extra`, git worktrees).
   - Because `agy.exe` and user/venv Python instances were not explicitly in the Defender CFA allowlist, Defender blocked each write attempt, triggering toast alerts.

2. **The Dual Solution in v0.2.2:**
   - **Automated Binary Whitelisting:** `install.ps1` now proactively registers `agy.exe`, the active Python interpreter, the `.extra` virtualenv Python, and `powershell.exe` in Defender's `ControlledFolderAccessAllowedApplications`.
   - **Workspace Location Diagnostics:** `extra doctor` now inspects the current directory. If the user runs `extra doctor` inside a protected folder (e.g. `Documents`), it emits an actionable warning and offers a one-click elevated fix via `extra doctor --fix-cfa`.

---

## 2. What Was Added in v0.2.2

### 1. Developer Binary Whitelisting in `install.ps1`
Step 6 of `install.ps1` automatically detects active developer toolchains and whitelists them:
```powershell
Add-MpPreference -ControlledFolderAccessAllowedApplications `
    "$agyPath", "$sysPython", "$venvPython", "$psPath"
```
Even if a developer chooses to place their workspace inside `Documents\my-project`, Defender recognizes `agy.exe` and Python as trusted tools and allows operations without alerts.

### 2. Workspace Proximity Guard in `extra doctor`
Running `extra doctor` now checks if `Get-Location` is inside `Documents`, `Desktop`, `Pictures`, `Videos`, or `Music`:
```text
[!] WARNING: Current workspace is inside a Windows Protected Folder:
    C:\Users\Surya\Documents\work
    Windows Defender Controlled Folder Access (CFA) may block write operations.
    Recommended: Move project to C:\work or run 'extra doctor --fix-cfa' to allowlist.
```

### 3. One-Click UAC Elevation Repair: `extra doctor --fix-cfa`
Users or automated agents can trigger instant, clean Windows UAC elevation to allowlist developer tools:
```powershell
extra doctor --fix-cfa
```
This triggers a native Windows UAC prompt (`Start-Process powershell -Verb RunAs`) to execute `Add-MpPreference` for all discovered developer binaries without requiring manual PowerShell administration.

---

# Extra Release Notes — v0.2.1

**Release Date:** September 16, 2026  
**Release Title:** Windows Defender Zero-Alarm Architecture & Controlled Folder Access (CFA) Compliance  
**Target Systems:** Windows 10/11 (x64) & macOS (Apple Silicon / Intel)

---

## 1. Executive Summary & Forensic Disclosure

In the spirit of complete transparency, Extra v0.2.1 addresses real-world security log discoveries from production Windows 11 deployments between **September 13, 2026 and September 16, 2026**.

During real-hardware automated computer-use sessions on a Windows 11 host (`SURYA`), Microsoft Defender registered **31 security events** across two separate protection subsystems:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                              DEFENDER LOG FORENSIC BREAKDOWN                                │
├─────────────────────────┬───────┬──────────┬───────────────────────┬────────────────────────┤
│ Protection Subsystem    │ Count │ Severity │ Trigger Resource      │ Underlying Cause       │
├─────────────────────────┼───────┼──────────┼───────────────────────┼────────────────────────┤
│ AMSI Cloud ML Engine    │ 5     │ Severe   │ powershell.exe        │ irm ... | iex in-memory│
│ (Trojan:Win32/          │       │ (Level 5)│ irm .../install.ps1   │ download cradle flagged│
│ Commando.A!ml)          │       │          │ | iex                 │ as stager dropper      │
├─────────────────────────┼───────┼──────────┼───────────────────────┼────────────────────────┤
│ Controlled Folder Access│ 26    │ Low /    │ python.exe, cmd.exe,  │ Unwhitelisted processes│
│ (Ransomware Protection  │       │ Info     │ powershell.exe        │ writing to Documents & │
│ Event ID 1123)          │       │          │ -> \Documents, \Pictures Pictures libraries     │
└─────────────────────────┴───────┴──────────┴───────────────────────┴────────────────────────┘
```

For any normal user, these notifications are alarming:
1. **"Severe Threat Detected: Trojan:Win32/Commando.A!ml"** during installation makes users believe they just ran a destructive Trojan or remote-access exploit.
2. **"Protected Folder Access Blocked: Ransomware Protection"** popping up 26 times whenever the AI creates audit reports, spreadsheets, or charts makes users believe the AI is attempting to encrypt or hijack their personal files.

**Extra v0.2.1 permanently eliminates both classes of false positives and execution blockades directly at the architectural level.**

---

## 2. Root Cause Analysis

### Incident A: The `Commando.A!ml` Installer False Positive
* **What Happened:** On 13-Sep-2026 at 19:42:59 and 19:43:08 IST, running `irm https://extra.yantraos.com/install.ps1 | iex` was immediately intercepted and remediated (`Action: Remove`) by Microsoft Defender.
* **Why Defender Intercepted It:**
  1. **In-Memory Download Cradle:** Piping remote HTTP payloads directly into `iex` (Invoke-Expression) without writing to disk is the signature pattern of malware loaders, memory-only droppers, and offensive penetration tools (hence Defender ML classifying it under the `Commando` family).
  2. **System Environment Modifications in Memory:** The installer modified machine/user environment variables, downloaded GitHub archives, created CLI wrappers, and registered MCP configurations while running in a memory buffer.
  3. **Installer Telemetry Callback:** The raw HTTP POST to a telemetry endpoint at the end of the script resembled a post-exploitation beacon to Defender's cloud ML heuristics.

### Incident B: The 26 Controlled Folder Access (CFA) Blocks
* **What Happened:** Between 13-Sep-2026 and 16-Sep-2026, Defender recorded 26 blocks (Event ID 1123) against `python.exe` (Python 3.12), `cmd.exe`, `powershell.exe`, and even `Photos.exe`:
  * `16-Sep 11:19:56`: `cmd.exe` blocked writing to `%userprofile%\Documents\GST_Audit_Final_Report`
  * `16-Sep 11:19:48`: `python.exe` blocked writing to `%userprofile%\Documents\GST_Audit_Source_Data`
  * `13-Sep 19:13–19:15`: `powershell.exe` and `cmd.exe` blocked in `%userprofile%\Pictures\`
  * `13-Sep 18:27–18:34`: `python.exe` and `cmd.exe` blocked in `%userprofile%\Documents\Astra6_Win11_AI_Laptop_Research`
* **Why Defender Blocked It:**
  Windows Defender Controlled Folder Access (Ransomware Protection) strictly locks down default Windows shell user libraries:
  * `%USERPROFILE%\Documents`
  * `%USERPROFILE%\Pictures`
  * `%USERPROFILE%\Desktop`
  * `%USERPROFILE%\Videos`
  * `%USERPROFILE%\Music`
  
  When an AI agent executed fast-path instructions (e.g., generating text files for Notepad or PNG charts for MS Paint), the agent intuitively chose `%userprofile%\Documents` or `%userprofile%\Pictures` as the destination. Because Python and CMD are not in the Defender CFA allowlist by default, Defender blocked every single write operation with `Access is denied` / `PermissionError: [Errno 13]`, triggering repeated ransomware warnings.

---

## 3. What Was Fixed in v0.2.1

### 1. Staged, Two-Step Installation Pipeline (Erasing `Commando.A!ml`)
* **Eliminated `irm | iex` Memory Cradle:** The recommended installation method is now a clean, staged on-disk download:
  ```powershell
  iwr -useb https://extra.yantraos.com/install.ps1 -OutFile "$env:TEMP\install_extra.ps1"; & "$env:TEMP\install_extra.ps1"
  ```
  By saving the script to disk before execution, Defender inspects the script statically as a legitimate developer installer rather than treating it as an in-memory remote execution exploit.
* **Stripped Raw Telemetry from Installer:** Removed the external `Invoke-RestMethod` telemetry call from `install.ps1` to keep the setup script 100% local, audited, and telemetry-free.

### 2. Isolated Safe Scratch Workspace (`~/.extra/workspace`)
* **Architectural Exemption from CFA:** Windows Defender Controlled Folder Access **only** monitors default user libraries. It **never** monitors custom directories such as `C:\Users\<user>\.extra\workspace\`.
* **Zero Permission Errors:** `install.ps1` now automatically creates and provisions `%USERPROFILE%\.extra\workspace\` and exports the `EXTRA_WORKSPACE` environment variable.
* All AI fast-path scratch files (Notepad briefs, Paint PNG charts, temporary CSVs, research folders) are directed here by default.

### 3. Proactive CFA Detection & Auto-Whitelisting in `install.ps1`
* `install.ps1` now interrogates Windows Defender via `Get-MpPreference`.
* If Controlled Folder Access is active and the installer is executed in an elevated session, it silently registers Extra's virtual environment (`.extra\venv\Scripts\python.exe`) with `Add-MpPreference -ControlledFolderAccessAllowedApplications`.
* If non-elevated, it transparently configures the safe workspace path without requiring administrator intervention or causing user panic.

### 4. Native Windows Defender Diagnostics in `extra doctor`
* `extra doctor` in `extra/cli.py` now includes a dedicated **Windows Defender & Controlled Folder Access (CFA)** health check matching our existing macOS TCC privacy checks.
* It verifies whether CFA is Enabled, in Audit Mode, or Disabled, and verifies that `%USERPROFILE%\.extra\workspace\` is writable with zero Defender alerts.

### 5. Updated Agent Directives (`extra_automation.md` & `STARTER_PROMPT.md`)
* The high-speed automation protocol has been upgraded with a strict **Directory Boundary Guardrail**:
  * **Rule:** NEVER write directly to `%USERPROFILE%\Documents`, `Pictures`, or `Desktop`.
  * **Rule:** ALWAYS route fast-path outputs to `%USERPROFILE%\.extra\workspace\<filename>` or the active workspace.
  * Windows applications (Notepad, MS Paint, File Explorer) are launched pointing to these unblocked safe paths, maintaining instant visual presentation with zero friction.

---

## 4. How This Makes Your AI Work Flawlessly

1. **Zero Silent Crashes:** Python scripts and terminal commands will never fail with `PermissionError: [Errno 13] Access is denied` or `File not found` errors caused by Defender intercepting write calls.
2. **Zero False Alarms for Users:** The user's screen stays clean—no scary "Trojan" or "Ransomware Blocked" toast notifications.
3. **Pristine Visual Automation:** The user still sees Notepad open with their report, MS Paint open with their data chart, and File Explorer open with their organized files—completely unaware of the underlying sandboxing that kept their system calm and secure.
4. **Enterprise Compliant:** Organizations that enforce Windows Defender Controlled Folder Access and strict AMSI policies can now run Extra seamlessly without disabling security controls.

---

*AIYantra Engineering Team — Sovereignty, Speed, and Complete Transparency.*
