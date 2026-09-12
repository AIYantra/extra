# Contributing to Extra ⚡

Thank you for your interest in contributing to **Extra** (`extra.yantraos.com`), the open-source "flashless" computer-use engine and Model Context Protocol (MCP) bridge for Windows 11 and Windows 10, developed by **AIYantra** (parent project: [yantraOS](https://yantraos.com)).

We welcome contributions from kernel-level Win32 hackers, AI researchers, frontend engineers, and automation enthusiasts.

---

## 🏛️ Architectural Invariants & Guiding Principles

Before writing code, please review the core architectural invariants. Pull requests violating these invariants will not be merged:

### 1. Zero Solo Binary Blobs (Enterprise Audit Clean)
* **Rule:** Do **NOT** introduce third-party compiled C++ / Rust `.pyd` or `.dll` binaries from unverified solo maintainers.
* **Rationale:** Enterprise security teams and Windows Defender flag obscure binary wheels as `Trojan:Win32/Wacatac`.
* **Standard:** All low-level OS operations must directly call Microsoft's built-in Windows system DLLs via Python `ctypes` (`user32.dll`, `gdi32.dll`, `dxgi.dll`, `UIAutomationCore.dll`) or use Tier-1 audited libraries (`playwright` [Microsoft], `pywin32` [PSF], `mcp` [Anthropic], `pillow` [PSF]).

### 2. Strict `PerMonitorV2` DPI Geometry
* **Rule:** Never execute mouse clicks using raw un-normalized coordinates or standard `pyautogui`.
* **Standard:** The process must declare `DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2` (-4). All coordinate transformations between physical pixels, normalized `[0, 1000]` coordinates, and multi-display monitor offsets must flow through [`extra.core.geometry`](extra/core/geometry.py).

### 3. Dual-Plane Perception (Visual + Semantic UIA)
* **Rule:** Never rely purely on vision-model screenshot parsing when Windows UI Automation can provide the exact bounding box and COM `InvokePattern` in < 1ms.
* **Standard:** Standard controls (buttons, menus, inputs) belong to **Plane B (Semantic UIA)**. Custom graphics, games, and non-accessible canvases fall back to **Plane A (Visual DXGI/MSS)**.

### 4. Closed-Loop Stall Prevention
* **Rule:** Every mutating desktop action (clicks, drags, keystrokes) must verify screen and window delta. If two consecutive actions produce zero change, the action supervisor must halt and raise a stall warning to prevent infinite runaway token burn.

---

## 🛠️ Local Development Setup

### Prerequisites
* **Operating System:** 64-bit Windows 11 (22H2+) or Windows 10 (Build 1703+).
* **Python:** Python 3.10, 3.11, 3.12, or 3.13 (64-bit).
* **PowerShell:** PowerShell 5.1 or PowerShell 7+ (Core).
* **Git:** Installed and available in PATH.

### 1. Clone & Create Environment
Open PowerShell in your working directory:

```powershell
git clone https://github.com/AIYantra/extra.git
cd extra

# Create an isolated virtual environment
python -m venv .venv

# Activate the virtual environment
.\.venv\Scripts\Activate.ps1

# Upgrade pip and install production dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Install extra in editable development mode
python -m pip install -e .
```

### 2. Run Diagnostics & Test Suite
Verify your hardware capture, DPI scaling, and UIA COM plane:

```powershell
# 1. Run system health diagnostics
extra doctor

# 2. Run the 6-module integration test suite
extra test

# 3. Test Set-of-Mark visual annotation
extra snap --som --output preview.png
ii preview.png

# 4. Run the interactive manual testing playground
python manual_test.py
```

---

## 📐 Project Structure

```text
extra/
├── core/                   # The Core Flashless Engine
│   ├── capture.py          # Screen capture (DXGI & MSS buffers, sub-25ms)
│   ├── geometry.py         # PerMonitorV2 DPI scaling & display normalization
│   ├── input_engine.py     # Win32 SendInput Unicode & atomic clipboard injection
│   ├── focus.py            # AttachThreadInput window activation enforcer
│   ├── uia_plane.py        # Windows UI Automation v3 COM client & Set-of-Mark
│   └── stall_breaker.py    # Perceptual hash diffing & 2-strike supervisor
├── fastpath/               # High-speed deterministic execution
│   ├── shell.py            # Win32 ShellExecuteEx application launcher
│   └── browser.py          # Playwright / Microsoft Edge CDP DOM bridge
├── mcp/                    # Model Context Protocol
│   └── server.py           # Anthropic MCP JSON-RPC server (11 native tools)
├── cli.py                  # CLI runner (extra doctor, test, run, inspect, snap)
├── install.ps1             # 1-line PowerShell zero-friction installer
├── manual_test.py          # Interactive manual testing suite
├── test_core_engine.py     # End-to-end automated integration tests
├── pyproject.toml          # PEP 518 / 621 package manifest
├── requirements.txt        # Enterprise-audited dependency manifest
├── STARTER_PROMPT.md       # Master AI system prompt & few-shot playbooks
├── PRD.md                  # Product Requirements Document
├── ARCHITECTURE.md         # Full System Architecture Specification
└── MEMORY.md               # Project Context & Architecture Decision Records (ADRs)
```

---

## 🧪 Testing Guidelines

Before opening a pull request, ensure:
1. All automated integration tests pass without exceptions:
   ```powershell
   extra test
   ```
2. Hardware diagnostics report `[OK]` for all subsystems:
   ```powershell
   extra doctor
   ```
3. Type annotations are complete and valid:
   ```powershell
   python -m pip install mypy
   mypy core fastpath mcp cli.py
   ```
4. Code passes formatting and lint standards:
   ```powershell
   python -m pip install ruff
   ruff check .
   ruff format --check .
   ```

---

## 📝 Commit & Pull Request Guidelines

### Conventional Commits
We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:
* `feat:` A new user-facing feature or tool (e.g. `feat: add multi-monitor coordinate translation in extra_drag`)
* `fix:` A bug fix (e.g. `fix: resolve window handle restoration on minimized apps`)
* `perf:` A code change that improves performance (e.g. `perf: reduce MSS buffer copy duration`)
* `docs:` Documentation-only changes
* `refactor:` Code refactoring without changing external behavior
* `test:` Adding or updating test suites

### Pull Request Checklist
- [ ] PR branch branched from `main`.
- [ ] Description clearly explains the *problem* and the *chosen solution*.
- [ ] Added or updated automated tests in `test_core_engine.py` if adding core functionality.
- [ ] Verified on physical Windows 10 or Windows 11 hardware with `extra doctor` and `extra test`.
- [ ] No solo-dev binary blobs introduced.
- [ ] All new functions and methods have full Python type annotations.

---

## 🔒 Security & Bug Reports

If you discover a security vulnerability or exploit in Extra's input or execution planes, please **do not open a public GitHub issue**. Instead, follow the instructions in [SECURITY.md](SECURITY.md) or email **security@yantraos.com**.
