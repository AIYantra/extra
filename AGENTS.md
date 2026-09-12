# AI Agent Guidelines & Operating Rules — Project Extra ⚡

Welcome to **Extra** (`extra.yantraos.com`), the open-source "flashless" computer-use engine for Windows 11/10.

When an autonomous AI agent (Antigravity, Claude, Cursor, AGY, Codex) develops or refactors code within this repository, the following non-negotiable architectural rules apply.

---

## 🏛️ Non-Negotiable Development Rules

### Rule 1: Zero Solo Binary Blobs (Enterprise Audit Clean)
* **Never** add or link third-party compiled C++ / Rust `.pyd` or `.dll` binaries from solo maintainers or unverified wheels.
* **Always** call Microsoft's built-in Windows system DLLs via Python `ctypes` (`user32.dll`, `gdi32.dll`, `dxgi.dll`, `UIAutomationCore.dll`) or use Tier-1 PSF/Microsoft libraries (`playwright`, `pywin32`, `mcp`, `pillow`).
* Any change introducing unverified binaries will trigger Windows Defender alerts and fail review.

### Rule 2: Strict `PerMonitorV2` Hardware DPI Awareness
* **Never** use raw un-scaled coordinates or naive pixel math.
* Ensure all screen coordinates are normalized or properly denormalized through [`extra.core.geometry`](core/geometry.py).
* All processes must initialize with `DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2` (-4).

### Rule 3: Dual-Plane Targeting (Semantic UIA First)
* **Never** write automation tasks that rely solely on screenshot OCR or vision bounding-box guesses when a standard Windows control exists.
* Query the control using [`UIAutomationPlane.inspect_window`](core/uia_plane.py) first, and activate it via COM `InvokePattern` or physical bounding box center.
* Only fall back to full visual Set-of-Mark capture on non-UIA canvases (games, custom graphics).

### Rule 4: Sub-Millisecond Input Injection
* **Never** use character-by-character slow typing loops (e.g. `pyautogui.typewrite` with delays).
* Use Win32 `KEYEVENTF_UNICODE` (`VK_PACKET`) in [`extra.core.input_engine.instant_type`](core/input_engine.py). It types hundreds of characters in under 5ms with zero dropped keys and full multilingual/emoji support.
* Use atomic clipboard paste for multi-line code blocks or long essays.

### Rule 5: Closed-Loop Stall Prevention
* Every mutating action must check screen delta before and after execution via [`StallBreaker`](core/stall_breaker.py).
* If an action produces no screen or window state change, increment strikes. Halt on 2 consecutive zero-delta actions with `STALL_DETECTED`.
* Honor the corner fail-safe at `(0, 0)`.

---

## 🧪 Verification Standard

Before declaring any task or PR `DONE`:
1. Run `python -m extra.cli test` (all 6 core subsystems must pass).
2. Run `python -m extra.cli doctor` (latency benchmarks must pass).
3. If modifying UI automation or capture, run `python manual_test.py` or inspect a live window.
4. Verify that dependencies in [`requirements.txt`](requirements.txt) and [`pyproject.toml`](pyproject.toml) remain synchronized.
