# Security Policy — Project Extra ⚡

**Extra** (`extra.yantraos.com`) is an enterprise-grade desktop computer-use bridge and Model Context Protocol (MCP) server designed with a strict zero-compromise security posture.

Because Extra interacts directly with the Windows kernel, Win32 input queues, and desktop display buffers, security and sandboxing are treated as first-class architectural pillars.

---

## 🛡️ Supported Versions

We actively provide security patches and updates for the following releases:

| Version | Supported | Notes |
| :--- | :--- | :--- |
| **0.1.x (Current: 0.1.1)** | :white_check_mark: | Latest release line |
| < 0.1.0 | :x: | Experimental / development prototypes |

---

## 🔒 Security Invariants & Threat Model

### 1. 100% Enterprise-Clean Dependency Pedigree
* **Zero Solo Binary Blobs:** Extra strictly forbids shipping pre-compiled C++ or Rust wheels from unverified individual maintainers.
* **Built-in System DLLs:** All hardware-level Win32 calls interface directly with Microsoft's digitally signed operating system libraries (`user32.dll`, `dxgi.dll`, `UIAutomationCore.dll`) via Python's standard `ctypes`.
* **Zero Defender False-Positives:** Extra passes Microsoft Defender, SmartScreen, and corporate EDR inspections out-of-the-box with zero `Trojan:Win32/Wacatac` alerts.

### 2. Autonomous Loop Supervision & Safety Abort
* **2-Strike Perceptual Stall Breaker:** To prevent infinite clicking loops or runaway API token burn, Extra hashes screen deltas before and after actions. Two consecutive zero-change actions trigger an immediate halt.
* **Corner Abort Fail-Safe:** Moving the physical mouse cursor to `(0, 0)` (the top-left pixel) triggers an immediate `EmergencyAbortError`, halting all automated execution instantly.
* **Emergency Hotkey:** Pressing `Ctrl+Alt+Shift+Q` halts the active MCP tool supervisor immediately.

### 3. Local-Only Stdio Transport
* Extra runs strictly on the local machine over `stdio` JSON-RPC streams.
* Extra does **NOT** expose open HTTP listening ports or transmit telemetry, screen captures, or keystrokes to any third-party cloud infrastructure. All data remains exclusively on your Windows host.

---

## 🚨 Reporting a Vulnerability

If you identify a security vulnerability, privilege escalation vector, or bypass in Extra's safety supervisor:

1. **Do NOT open a public GitHub issue.**
2. Send an encrypted or confidential report to:
   * **Email:** `security@yantraos.com`
   * **Subject:** `[SECURITY VULNERABILITY] Extra - <Brief Vulnerability Description>`
3. Include the following details in your report:
   * Detailed steps to reproduce the vulnerability.
   * Windows OS version, build number, and hardware configuration.
   * Proof of Concept (PoC) script or demonstration.
   * Impact assessment (e.g. unauthorized input injection, crash, denial-of-service).

### Our Response SLA
* **Initial Acknowledgement:** Within **24 hours**.
* **Triage & Reproduction:** Within **48 hours**.
* **Remediation & Patch Release:** Within **7 days** (or coordinated disclosure timeline).
