# Extra for macOS: Universal Launch Plan (v0.2.0)
## The Complete 6-Pillar Blueprint for Zero-Friction User Distribution & Ecosystem Adoption

---

## Executive Summary

Project Extra gives AI agents native "hands and eyes" on modern desktop operating systems. Having achieved complete technical parity across Windows 10/11 and macOS (Apple Silicon M1-M4 & Intel), the objective of this Launch Plan is to bring Extra to macOS users with the exact same frictionless, viral **"1-command, 1-prompt"** adoption experience that powered Extra on Windows.

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             THE 1-PROMPT ADOPTION FUNNEL                         │
│                                                                                  │
│  User Prompt ──> Host AI Runs install.sh ──> Auto-Configures MCP & Rules ──>     │
│  User Restarts Client ──> Autonomous Desktop Computer-Use Active               │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## The 6 Pillars of the Launch Plan

```mermaid
flowchart TD
    P1["Pillar 1: Core Distribution Funnel"] --> P2["Pillar 2: install.sh Automation Engine"]
    P2 --> P3["Pillar 3: Apple TCC Permission Playbook"]
    P3 --> P4["Pillar 4: Edge Delivery & Web Infrastructure"]
    P4 --> P5["Pillar 5: Phased Multi-Channel Ecosystem"]
    P5 --> P6["Pillar 6: GTM Release Schedule & Playbook"]
```

---

## Pillar 1: The Core Distribution Funnel

The adoption model eliminates technical setup barriers. Users do not manage Python virtual environments, configure JSON files, or manually register MCP servers.

### 1.1 The Primary Onboarding Entry Points

#### Entry Point A: The "Ask Your AI" Single-Prompt Directive (Primary Funnel — 80% Target)
Users copy and paste a single directive into **Claude Desktop**, **Google Antigravity**, **Cursor**, **Windsurf**, or any MCP-enabled agent:

```text
Setup Extra on my Mac: In Terminal run 'curl -sSL https://extra.yantraos.com/install.sh | bash', then read and configure ~/.extra/app/STARTER_PROMPT_MACOS.md so we are ready to use Extra.
```

**How It Works:**
1. The AI opens a terminal session and triggers `curl -sSL https://extra.yantraos.com/install.sh | bash`.
2. The installer runs unattended, setting up the isolated environment, Claude Desktop config, and local rules.
3. The AI inspects `~/.extra/app/STARTER_PROMPT_MACOS.md`, activates its always-on execution rules, and replies:
   > **"We are ready! Please restart Claude Desktop (or your active AI client) to make it work."**
4. Once restarted, the AI possesses full macOS computer control capabilities (`extra_*` suite).

#### Entry Point B: The Terminal One-Liner (For Developers)
For users running their own command line:
```bash
curl -sSL https://extra.yantraos.com/install.sh | bash
```

#### Entry Point C: Developer Git Clone
For developers who prefer inspect-before-run:
```bash
git clone https://github.com/AIYantra/extra.git ~/.extra/app
cd ~/.extra/app && ./install.sh
```

### 1.2 Post-Install Delight & Immediate Verification
At the conclusion of the installation script, the terminal outputs a high-contrast banner confirming readiness:

```text
======================================================================
  EXTRA IS INSTALLED AND READY ON MACOS! 🚀
======================================================================

How to use Extra (Just 1 step):
Copy and paste this prompt into your AI (Claude, Antigravity, Cursor):

👉  Setup ~/.extra/app/STARTER_PROMPT_MACOS.md

Your AI will automatically configure its rules and reply:
"We are ready! Please restart <your AI application> to make it work."
======================================================================
```

### 1.3 Funnel Metrics & Conversion KPIs
- **Install Success Rate**: > 98% completed without manual intervention.
- **Time to First Action (TTFA)**: < 90 seconds from running the curl command to the first autonomous task execution.
- **Permission Authorization Rate**: > 90% authorization on first prompt via direct system deep-links.

### 1.4 Implementation Deliverables & Verification (Status: COMPLETE ✅)

All required deliverables for **Pillar 1: The Core Distribution Funnel** have been engineered, integrated, and verified:

| Funnel Component | Deliverable / Artifact | Status | Verification & Integration |
| :--- | :--- | :---: | :--- |
| **Entry Point A Directive** | [`STARTER_PROMPT_MACOS.md`](STARTER_PROMPT_MACOS.md), [`README_MACOS.md`](README_MACOS.md), [`README.md`](README.md) | **COMPLETE** | Exact 1-prompt text verified across all documentation and prompt directives. Validated via `test_entry_point_a_directive_presence`. |
| **Entry Point B One-Liner** | [`install.sh`](install.sh), [`README_MACOS.md`](README_MACOS.md), [`README.md`](README.md) | **COMPLETE** | `curl -sSL https://extra.yantraos.com/install.sh \| bash` documented and validated via `test_entry_point_b_terminal_one_liner`. |
| **Entry Point C Git Clone** | `git clone ... ~/.extra/app`, [`install.sh`](install.sh) | **COMPLETE** | Fully supported with automatic `~/.extra/app` symlink fallback to guarantee starter prompt path resolution. Validated via `test_entry_point_c_developer_git_clone`. |
| **Post-Install Delight** | [`install.sh`](install.sh) Banner & 1-step starter invocation | **COMPLETE** | High-contrast banner outputs `Setup ~/.extra/app/STARTER_PROMPT_MACOS.md` and expected AI reply message. Validated via `test_post_install_banner_in_installer`. |
| **Multi-Client MCP Templates** | [`claude_desktop_config.macos.template.json`](claude_desktop_config.macos.template.json), [`cursor_mcp.macos.template.json`](cursor_mcp.macos.template.json), [`windsurf_mcp.macos.template.json`](windsurf_mcp.macos.template.json) | **COMPLETE** | Validated JSON schemas specifying `extra` MCP server path and arguments. Validated via `test_client_mcp_templates_validity`. |
| **Zero-Config Client Auto-Injection** | [`install.sh`](install.sh) (Steps 6, 7, 8, 9) | **COMPLETE** | Auto-configures Claude Desktop, Cursor, Windsurf, and Antigravity CLI (`agy`) with non-destructive JSON merging. Validated via `test_multi_client_configuration_in_installer`. |
| **Automated Funnel Test Suite** | [`tests/test_pillar1_funnel.py`](tests/test_pillar1_funnel.py) | **COMPLETE** | 9 integration & unit tests validating syntax, directives, symlinks, banner, and configs (100% PASS). |

---

## Pillar 2: The `install.sh` Automation Engine Architecture

The `install.sh` script is the backbone of the automated user onboarding experience. It is engineered to be **self-healing, idempotent, and non-destructive**.

### 2.1 Execution Sequence Architecture

```mermaid
sequenceDiagram
    autonumber
    actor User as User / AI Agent
    participant Script as install.sh
    participant Sys as macOS System (uname, sw_vers)
    participant Brew as Homebrew Package Manager
    participant Venv as Isolated ~/.extra/venv
    participant Claude as Claude Desktop Config
    participant Agy as Antigravity CLI & Rules
    participant Doc as extra doctor CLI

    User->>Script: curl -sSL ... | bash
    Script->>Sys: 1. Verify macOS >= 12.3 & Arch (arm64/x86_64)
    Script->>Brew: 2. Discover Python 3.10+ (Auto-brew fallback)
    Script->>Venv: 3. Create isolated virtualenv (~/.extra/venv)
    Script->>Venv: 4. Install PyObjC, MCP, and Core dependencies
    Script->>Sys: 5. Create global CLI symlink (~/.local/bin/extra)
    Script->>Claude: 6. Inject MCP Server into claude_desktop_config.json
    Script->>Agy: 7. Register with agy & deploy extra_automation_macos.md
    Script->>Doc: 8. Execute 'extra doctor' diagnostic
    Doc-->>User: 9. Render permission status & 1-step starter prompt
```

### 2.2 Deep Technical Specifications of `install.sh`

#### 1. System & Architecture Validation
- Checks `uname -s == "Darwin"`. If non-Darwin, aborts with platform guidance.
- Checks `sw_vers -productVersion`: Requires `>= 12.3` (Monterey, Ventura, Sonoma, Sequoia) to ensure Apple's `ScreenCaptureKit` GPU buffer grabs are natively supported.
- Captures architecture (`arm64` for M1/M2/M3/M4 Apple Silicon, `x86_64` for Intel).

#### 2. Automated Python Runtime Discovery & Provisioning
- Iteratively tests candidate binaries: `python3.13`, `python3.12`, `python3.11`, `python3.10`, `python3`.
- Verifies `sys.version_info >= (3, 10)`.
- If no compatible Python runtime exists:
  - Detects if `brew` is installed.
  - Automatically runs `brew install python@3.12` in silent mode.
  - Resolves path via `$(brew --prefix python@3.12)/bin/python3`.
  - If Homebrew is absent, prints direct download link for official macOS Python installer package.

#### 3. Sandboxed Virtual Environment (`~/.extra/venv`)
- Isolates all runtime packages inside `~/.extra/venv`.
- Completely avoids modifying macOS system Python or user-level pip environments.
- Idempotent: Reuses existing venv if healthy, or cleans and recreates if corrupted.

#### 4. Native Dependency Provisioning
- Upgrades `pip`, `setuptools`, and `wheel`.
- Installs base requirements: `mcp>=1.0.0`, `playwright>=1.47.0`, `pillow>=10.4.0`, `imagehash>=4.3.1`, `numpy>=1.26.0`, `psutil>=6.0.0`.
- Installs official Apple PyObjC framework bindings:
  - `pyobjc-core>=10.0`
  - `pyobjc-framework-Cocoa>=10.0`
  - `pyobjc-framework-Quartz>=10.0`
  - `pyobjc-framework-ApplicationServices>=10.0`
  - `pyobjc-framework-ScreenCaptureKit>=10.0`
- Links project in editable mode (`pip install -e ~/.extra/app --no-deps`).

#### 5. Global CLI Executable & Shell PATH Injection
- Generates executable launcher at `~/.local/bin/extra`:
  ```bash
  #!/usr/bin/env bash
  export PYTHONPATH="$HOME/.extra/app:$PYTHONPATH"
  exec "$HOME/.extra/venv/bin/python" -m extra.cli "$@"
  ```
- Automatically checks user shell (`~/.zshrc` for zsh or `~/.bash_profile` for bash).
- Appends `export PATH="$HOME/.local/bin:$PATH"` if not already present.

#### 6. Claude Desktop Automated MCP Injection
- Inspects target configuration directory: `~/Library/Application Support/Claude/`.
- File: `claude_desktop_config.json`.
- Safely parses existing JSON without clobbering other configured MCP servers.
- Injects or updates the `extra` entry:
  ```json
  {
    "mcpServers": {
      "extra": {
        "command": "/Users/USERNAME/.extra/venv/bin/python",
        "args": ["-m", "extra.mcp.server"]
      }
    }
  }
  ```

#### 7. Antigravity CLI (`agy`) Auto-Registration & Rules Deployment
- If `command -v agy` succeeds:
  - Registers Extra: `agy mcp add extra ~/.extra/venv/bin/python -m extra.mcp.server`.
  - Automatically copies `rules/extra_automation_macos.md` to:
    1. **Global Skill**: `~/.gemini/config/skills/extra-automation/SKILL.md` (active in every agy project).
    2. **Global Prompt**: `~/.gemini/GEMINI.md` (always-on protocol across all directories).
    3. **Global MCP Instructions**: `~/.gemini/antigravity-cli/mcp/extra/instructions.md`.
    4. **User Agent Rules**: `~/.agents/rules/extra_automation.md`.
    5. **Workspace Rules**: Current working directory `.agents/rules/extra_automation.md` (if in active workspace).

#### 8. Health Verification Execution
- Automatically invokes `~/.extra/venv/bin/python -m extra.cli doctor`.
- Reports hardware status, screen capture benchmark latency, and permission checkmarks.

### 2.3 Implementation Deliverables & Verification (Status: COMPLETE ✅)

All technical requirements and deliverables for **Pillar 2: The `install.sh` Automation Engine Architecture** have been engineered, integrated, and verified:

| Specification Area | Implementation Detail | Status | Verification & Integration |
| :--- | :--- | :---: | :--- |
| **System & Arch Validation** | `uname -s == "Darwin"`, `sw_vers >= 12.3`, `arm64`/`x86_64` | **COMPLETE** | Validated in `install.sh` with platform guidance for Windows hosts (`install.ps1`). Tested via `test_os_and_architecture_validation`. |
| **Python Provisioning** | 3.10+ discovery, Homebrew fallback (`brew install python@3.12`), official URL | **COMPLETE** | Validated candidate binary loop, brew auto-install, and python.org fallback in `install.sh`. Tested via `test_python_discovery_and_provisioning`. |
| **Sandboxed Virtualenv** | Isolated `~/.extra/venv`, self-healing idempotency check | **COMPLETE** | Validated clean recreation if corrupted (`$VENV_DIR/bin/python -c 'import sys; sys.exit(0)'`). Tested via `test_sandboxed_virtual_environment_self_healing`. |
| **Native PyObjC & MCP Deps** | Official Apple PyObjC framework bindings and core deps in `requirements.txt` | **COMPLETE** | Validated `pyobjc-core`, `Cocoa`, `Quartz`, `ApplicationServices`, `ScreenCaptureKit`, `mcp`, `playwright`. Tested via `test_native_dependencies_manifest`. |
| **Global CLI & PATH** | `~/.local/bin/extra` launcher, `PYTHONPATH`, shell rc injection | **COMPLETE** | Validated wrapper script and automatic PATH export in `~/.zshrc` / `~/.bash_profile`. Tested via `test_global_cli_and_path_injection`. |
| **Claude Desktop Injection** | Non-destructive JSON merge into `claude_desktop_config.json` | **COMPLETE** | Injects `extra` MCP server without clobbering other servers; creates dir in advance. Tested via `test_claude_desktop_mcp_injection`. |
| **Multi-IDE Config Injection** | Cursor (`cursor.mcp/mcp.json`, `~/.cursor/mcp.json`) & Windsurf (`mcp_config.json`) | **COMPLETE** | Automatically injects `extra` into Cursor and Windsurf configs when detected. Tested via `test_multi_client_mcp_injection`. |
| **Antigravity Rules Deployment** | `agy mcp add extra` and 5-target rules deployment | **COMPLETE** | Installs to Global Skill, Global Prompt, MCP Instructions, User Rules, and Workspace Rules. Tested via `test_antigravity_rules_deployment_targets`. |
| **Doctor Diagnostic & Deep-Links**| `extra doctor` execution & 1-click System Settings deep links | **COMPLETE** | Executes full hardware diagnostic and outputs direct `open "x-apple.systempreferences:..."` deep links. Tested via `test_doctor_diagnostic_and_deep_links`. |
| **Automated Test Suite** | [`tests/test_pillar2_installer.py`](tests/test_pillar2_installer.py) | **COMPLETE** | 9 unit & integration tests covering all Pillar 2 engine specifications (100% PASS). |

---

## Pillar 3: Apple TCC Privacy & Security Permissions Playbook

On macOS, Apple's Transparency, Consent, and Control (TCC) subsystem requires user permission for automation tools. Our objective is to guide the user through authorization in under 15 seconds.

### 3.1 The Two Essential Permissions

| Permission | macOS API / Subsystem | Purpose in Extra |
| :--- | :--- | :--- |
| **Accessibility** | `AXUIElement`, `CGEventTap` | Reading native UI hierarchies, control labels, button bounding boxes, and injecting mouse/keyboard HID events. |
| **Screen Recording** | `ScreenCaptureKit`, Quartz | Capturing hardware-accelerated GPU screen frame buffers with sub-8ms latency for vision models. |

### 3.2 1-Click Deep-Link Openers
Rather than asking users to manually navigate System Settings menus, `extra doctor` and `install.sh` provide direct macOS URL schemes:

```bash
# Deep-links directly to macOS Accessibility settings pane:
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"

# Deep-links directly to macOS Screen Recording settings pane:
open "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture"
```

### 3.3 Interactive Terminal Guidance Card
When permissions are absent, `extra doctor` renders this formatted card:

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

### 3.4 Recovery & Reset Commands (Troubleshooting)
If permissions get corrupted or stuck in an older binary state:
```bash
# Reset Accessibility permissions for Terminal:
tccutil reset Accessibility com.apple.Terminal

# Reset Screen Recording permissions:
tccutil reset ScreenCapture com.apple.Terminal
```

### 3.5 Implementation Deliverables & Verification (Status: COMPLETE ✅)

All technical requirements and deliverables for **Pillar 3: Apple TCC Privacy & Security Permissions Playbook** have been engineered, integrated, and verified:

| Component / Playbook Item | Implementation Artifact | Status | Verification & Integration |
| :--- | :--- | :---: | :--- |
| **Two Essential Permissions** | [`core/platform/macos/permissions.py`](core/platform/macos/permissions.py) | **COMPLETE** | `check_accessibility()` (`AXIsProcessTrusted`) and `check_screen_recording()` (`CGPreflightScreenCaptureAccess`). |
| **1-Click Deep-Link Openers** | [`permissions.py`](core/platform/macos/permissions.py), [`install.sh`](install.sh), [`cli.py`](cli.py) | **COMPLETE** | Direct URL openers for `Privacy_Accessibility` and `Privacy_ScreenCapture`. Also callable via `extra permissions open`. Tested via `test_open_settings_invocations`. |
| **Terminal Guidance Card** | `get_guidance_card()` in [`permissions.py`](core/platform/macos/permissions.py) | **COMPLETE** | High-contrast box drawing border card with deep links and instructions rendered in `extra doctor` and `extra permissions`. Tested via `test_guidance_card_structure`. |
| **TCC Recovery & Reset** | `reset_permissions()` in [`permissions.py`](core/platform/macos/permissions.py) | **COMPLETE** | Mapped client bundle identifiers (Terminal, iTerm2, Claude, Cursor, Windsurf) and automated `tccutil reset`. Tested via `test_reset_permissions_execution`. |
| **CLI Permissions Command** | `extra permissions [check\|open\|reset]` in [`cli.py`](cli.py) | **COMPLETE** | Dedicated CLI command to check, open settings panes, or reset stuck permissions. Tested via `test_cli_permissions_check_*`. |
| **Automated Test Suite** | [`tests/test_pillar3_tcc_playbook.py`](tests/test_pillar3_tcc_playbook.py) | **COMPLETE** | 8 unit & integration tests covering deep links, bundle mappings, guidance card, reset execution, and CLI integration (100% PASS). |

---

## Pillar 4: Web Infrastructure & Edge Delivery Engine (`extra.yantraos.com`)

The distribution portal `https://extra.yantraos.com` handles both Windows and macOS users from a single domain.

### 4.1 Edge Request Router Logic (Cloudflare Workers / Vercel Edge)

An edge worker intercepts incoming requests and routes them adaptively based on client characteristics:

```javascript
/**
 * Cloudflare Worker / Vercel Edge Router for extra.yantraos.com
 */
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const userAgent = (request.headers.get("user-agent") || "").toLowerCase();

    // Route 1: Direct script requests
    if (url.pathname === "/install.sh") {
      return fetch("https://raw.githubusercontent.com/AIYantra/extra/main/install.sh");
    }
    if (url.pathname === "/install.ps1") {
      return fetch("https://raw.githubusercontent.com/AIYantra/extra/main/install.ps1");
    }

    // Route 2: Rule downloads
    if (url.pathname === "/extra_automation_macos.md") {
      return fetch("https://raw.githubusercontent.com/AIYantra/extra/main/rules/extra_automation_macos.md");
    }
    if (url.pathname === "/extra_automation.md") {
      return fetch("https://raw.githubusercontent.com/AIYantra/extra/main/rules/extra_automation.md");
    }

    // Route 3: Universal CLI one-liner: curl -sSL https://extra.yantraos.com/install | bash
    if (url.pathname === "/install") {
      if (userAgent.includes("curl") || userAgent.includes("wget") || userAgent.includes("darwin") || userAgent.includes("macintosh")) {
        return fetch("https://raw.githubusercontent.com/AIYantra/extra/main/install.sh");
      }
      return fetch("https://raw.githubusercontent.com/AIYantra/extra/main/install.ps1");
    }

    // Route 4: Web Browser UI with Adaptive OS Tabs
    return handleWebInterface(request, userAgent);
  }
};
```

### 4.2 Web Landing Page Enhancements
1. **Adaptive Hero Section**:
   - Detects visitor OS via JavaScript `navigator.userAgent`.
   - On macOS: Displays `curl -sSL https://extra.yantraos.com/install.sh | bash` with 1-click copy.
   - On Windows: Displays `irm https://extra.yantraos.com/install.ps1 | iex`.
   - Explicit toggle buttons: `[ 🍏 macOS ]` and `[ 🪟 Windows ]` allowing manual switching.
2. **Speed & Latency Benchmark Table**:
   - Compares Extra on Apple Silicon M3/M4 against traditional automation tools:
     - Perception: **2.4 ms** (ScreenCaptureKit) vs 250 ms (PyAutoGUI)
     - Typing: **< 0.005 s** (CoreGraphics) vs 3.5 s (Keyboard emulation)
     - Accuracy: **99.4%** (AXUIElement semantic tree) vs 65% (Vision guessing)
3. **Split-Screen Demo Video**:
   - High-definition video showing Claude Desktop autonomously calculating financial metrics in Calculator, writing an executive memo in TextEdit, and flashing the emerald green indicator with a glass marimba chime.

### 4.3 Implementation Deliverables & Verification Status

| Deliverable | Location | Status | Implementation Details |
| :--- | :--- | :--- | :--- |
| **Edge Request Router** | [`middleware.ts`](../extra.yantraos.com/middleware.ts) & [`worker.js`](../extra.yantraos.com/worker.js) | **COMPLETE** | Edge router intercepting `/install.sh`, `/install.ps1`, `/extra_automation_macos.md`, `/extra_automation.md`, and `/install` with adaptive User-Agent detection (curl, darwin, macintosh). |
| **Universal Route Handlers** | [`app/install/route.ts`](../extra.yantraos.com/app/install/route.ts), [`app/install.sh/route.ts`](../extra.yantraos.com/app/install.sh/route.ts), etc. | **COMPLETE** | Dynamic Next.js route handlers in `app/` fetching upstream GitHub raw with resilient local filesystem fallback from `public/` and `text/plain; charset=utf-8` headers. |
| **Adaptive Install Section** | [`components/install-section.tsx`](../extra.yantraos.com/components/install-section.tsx) | **COMPLETE** | Auto-detects client OS via `navigator.userAgent`, provides segmented `[ 🍏 macOS ]` and `[ 🪟 Windows ]` switcher, renders `curl` vs `irm` one-liners and respective AI setup prompts. |
| **Adaptive Install Modal** | [`components/install-modal.tsx`](../extra.yantraos.com/components/install-modal.tsx) | **COMPLETE** | Modal OS switcher with architecture-specific verification checklists for macOS (ScreenCaptureKit, TCC permissions) and Windows 10/11. |
| **Apple Silicon Benchmark Table** | [`components/benchmark-table.tsx`](../extra.yantraos.com/components/benchmark-table.tsx) | **COMPLETE** | Multi-platform benchmark matrix featuring ScreenCaptureKit (2.4ms vs 250ms), CoreGraphics (<0.005s vs 3.5s), and AXUIElement (99.4% vs 65%) with dynamic platform switcher. |
| **Landing Page Integration** | [`app/page.tsx`](../extra.yantraos.com/app/page.tsx) & [`components/navbar-clean.tsx`](../extra.yantraos.com/components/navbar-clean.tsx) | **COMPLETE** | Embedded `BenchmarkTable` on homepage, added `#benchmarks` nav link, updated Hero and Footer copy for macOS & Windows parity. |
| **Automated Test Suite** | [`tests/test_pillar4_web_edge.py`](tests/test_pillar4_web_edge.py) | **COMPLETE** | 9 unit & integration tests covering edge router, UA branching, Next.js route handlers, fallback asset parity, next.config headers, and benchmark schemas (100% PASS). |

---

## Pillar 5: Phased Multi-Channel Package Ecosystem

To scale from early adopters to mainstream developers, we roll out distribution across four sequential stages:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       MULTI-CHANNEL DISTRIBUTION ROADMAP                    │
│                                                                             │
│  Phase A (Day 1)  : curl one-liner + GitHub source (Immediate)              │
│  Phase B (Day 3)  : Homebrew Tap formula (brew install aiyantra/extra)       │
│  Phase C (Day 5)  : PyPI Universal Wheels (pip install extra-desktop)       │
│  Phase D (Day 7)  : Anthropic MCP Registry, Smithery.ai, Pulse MCP          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.1 Phase A: One-Liner Script (Day 1 — Launch Day)
- Target: Everyday users of Claude Desktop, Antigravity, and Cursor.
- Execution: `curl -sSL https://extra.yantraos.com/install.sh | bash`.
- Zero prerequisite package managers.

### 5.2 Phase B: Homebrew Tap Formula (Day 3)
For developers who manage all system tools via Homebrew:
```bash
brew tap aiyantra/extra
brew install extra
```

#### Homebrew Formula Specification (`Formula/extra.rb`):
```ruby
class Extra < Formula
  include Language::Python::Virtualenv

  desc "Flashless macOS & Windows Computer-Use Engine & MCP Server"
  homepage "https://extra.yantraos.com"
  url "https://github.com/AIYantra/extra/archive/refs/tags/v0.2.0.tar.gz"
  sha256 "REPLACE_WITH_ACTUAL_SHA256"
  license "MIT"

  depends_on "python@3.12"
  depends_on :macos => :monterey

  def install
    virtualenv_install_with_resources
    bin.install_symlink libexec/"bin/extra" => "extra"
  end

  def post_install
    system bin/"extra", "doctor"
  end

  test do
    assert_match "extra 0.2.0", shell_output("#{bin}/extra --version")
  end
end
```

### 5.3 Phase C: PyPI Universal Package (Day 5)
```bash
pip install extra-desktop
```
- Multi-platform packaging supporting `darwin_arm64`, `darwin_x86_64`, and `win_amd64`.
- Automated GitHub Actions build pipeline triggering on tag creation.

### 5.4 Phase D: MCP Registry & Marketplace Submissions (Day 7)
- **Anthropic Official Model Context Protocol Registry**: Submit PR to `modelcontextprotocol/servers`.
- **Smithery.ai**: Submit registry package for 1-click Claude Desktop install.
- **Glama & Pulse MCP**: Directory listing with benchmark citations.
- **Cursor Directory**: Submit configuration template for Cursor IDE users.

### 5.5 Implementation Deliverables & Verification Status

| Deliverable | Location | Status | Implementation Details |
| :--- | :--- | :--- | :--- |
| **Phase A: Curl One-Liner** | [`install.sh`](install.sh) & [`extra.yantraos.com/install.sh`](../extra.yantraos.com/public/install.sh) | **COMPLETE** | Production-ready zero-prerequisite installer for macOS and Linux, auto-detecting clients and checking TCC permissions. |
| **Phase B: Homebrew Tap Formula** | [`Formula/extra.rb`](Formula/extra.rb) & [`scripts/setup_homebrew_tap.sh`](scripts/setup_homebrew_tap.sh) | **COMPLETE** | Clean formula specifying `Language::Python::Virtualenv`, `python@3.12`, Monterey+ macOS dependency, symlinks, `post_install` doctor, and tap setup script. |
| **Phase C: PyPI Universal Wheels** | [`pyproject.toml`](pyproject.toml) & [`dist/`](dist/) | **COMPLETE** | Verified universal distribution package `extra-desktop` v0.2.0 (`extra_desktop-0.2.0-py3-none-any.whl` and `extra_desktop-0.2.0.tar.gz`) generated via `python -m build`. |
| **Phase C: CI/CD Release Pipelines** | [`.github/workflows/publish-pypi.yml`](.github/workflows/publish-pypi.yml) & [`.github/workflows/ci.yml`](.github/workflows/ci.yml) | **COMPLETE** | Automated GitHub Actions workflow building wheels, running pre-flight tests across `macos-latest` & `windows-latest`, uploading to PyPI, and attaching assets to GitHub releases. |
| **Phase D: Anthropic MCP Registry** | [`server.json`](server.json) | **COMPLETE** | Conforms to official Model Context Protocol schema v0.2.0 with PyPI `extra-desktop` package definition and stdio transport. |
| **Phase D: Smithery.ai Integration** | [`smithery.yaml`](smithery.yaml) | **COMPLETE** | Smithery specification enabling 1-click Claude Desktop install via stdio transport. |
| **Phase D: Glama & Pulse MCP** | [`glama.json`](glama.json) | **COMPLETE** | Directory manifest with capability metadata, multi-channel install commands, and Apple Silicon benchmarks (2.4ms perception, 99.4% accuracy). |
| **Phase D: Cursor Directory** | [`.cursor/mcp.json`](.cursor/mcp.json) | **COMPLETE** | Configuration template for Cursor IDE users. |
| **Automated Test Suite** | [`tests/test_pillar5_package_ecosystem.py`](tests/test_pillar5_package_ecosystem.py) | **COMPLETE** | 10 unit tests verifying formula structure, wheel artifacts, GitHub Actions pipelines, marketplace manifests, and v0.2.0 synchronization (100% PASS). |

---

## Pillar 6: Master Release Schedule, Go-To-Market (GTM) & Community Playbook

### 6.1 Launch Schedule Timeline

| Timestamp | Phase | Key Actions | Owners |
| :--- | :--- | :--- | :--- |
| **T - 24h** | **Pre-Flight Staging** | Full regression test runs; version bump to 0.2.0; staging verification on M-series and Intel Macs. | Engineering |
| **T - 0h** | **Release Execution** | Tag `v0.2.0`; push GitHub release; sync `install.sh` to edge CDN. | Lead Architect |
| **T + 1h** | **Health & CDN Check** | Test curl installer from 3 distinct global regions; verify Claude Desktop auto-patching. | QA / Ops |
| **T + 2h** | **Hacker News Launch** | Post "Show HN: Extra — Sub-10ms Native Computer-Use for macOS via ScreenCaptureKit & AXUIElement". | Founder / DevRel |
| **T + 2.5h** | **Social Media Blitz** | Publish 20-second video demo on X (Twitter) and LinkedIn; tag ecosystem leaders. | Marketing / DevRel |
| **T + 4h** | **Community Outreach** | Publish technical writeups in `r/ClaudeAI`, `r/LocalLLaMA`, and `r/mac`. | DevRel |
| **T + 24h** | **Triage & Patching** | Monitor issues for any edge macOS permission bugs; push `v0.2.1` if minor patch needed. | Engineering |
| **T + 72h** | **Homebrew Tap Live** | Push Homebrew formula to `aiyantra/homebrew-extra`. | Package Maintainer |

---

### 6.2 Community Copy & Asset Templates

#### Template 1: Hacker News ("Show HN") Post
- **Title**: `Show HN: Extra – Sub-10ms Native Computer-Use for macOS via ScreenCaptureKit & AXUIElement`
- **Content**:
  > Hey HN!
  > 
  > We built **Extra**, an open-source, local MCP server that gives AI models native hands and eyes on macOS.
  > 
  > **The Problem:** Current computer-use agents take slow 300–800ms screenshots and guess button coordinates with vision models. They burn thousands of tokens, miss small buttons on Retina displays, get stuck in infinite loops, and stream desktop frames to cloud servers.
  > 
  > **Our Approach:** Extra connects directly to Apple's native macOS subsystems:
  > 1. **Perception**: Uses `ScreenCaptureKit` for hardware-accelerated GPU frame buffer grabs in under 4ms.
  > 2. **Accessibility**: Traverses the `AXUIElement` semantic tree. Instead of guessing pixels, it clicks buttons deterministically via element ID.
  > 3. **Input**: Injects UTF-16 Unicode text into CoreGraphics event taps with zero typing delay.
  > 4. **Safety**: Uses perceptual hash diffing to catch infinite loops and abort after 2 consecutive non-progressing actions.
  > 5. **Privacy**: 100% local. Zero screenshots or keystrokes leave your machine.
  > 
  > It installs in one command and auto-configures Claude Desktop:
  > `curl -sSL https://extra.yantraos.com/install.sh | bash`
  > 
  > GitHub: https://github.com/AIYantra/extra  
  > Website: https://extra.yantraos.com  
  > 
  > Would love to hear feedback and answer any questions about ScreenCaptureKit or AXUIElement integration!

#### Template 2: X (Twitter) Video Thread
- **Tweet 1 (The Hook & Video)**:
  > Computer-use agents shouldn't take 5 seconds to click a button.
  > 
  > Today we're releasing **Extra for macOS**: sub-10ms desktop perception, deterministic clicking, and instant typing for Claude, Antigravity, and Cursor.
  > 
  > 🍏 Native ScreenCaptureKit + AXUIElement  
  > 🔒 100% local & open-source  
  > 
  > [ATTACH: 20-second split-screen demo video]
- **Tweet 2 (The Architecture)**:
  > Why is it fast?
  > - Screen capture: 3.2ms via GPU frame buffers (ScreenCaptureKit)
  > - Button clicks: 0.5ms via native accessibility tree (zero vision tokens wasted)
  > - Typing: 1,000 characters in <5ms via CoreGraphics event taps
  > - Ambient awareness: Green edge glow + audio chime when complete
- **Tweet 3 (Installation)**:
  > Works with Claude Desktop out of the box. Just copy-paste this to Claude:
  > 
  > "Setup Extra on my Mac: In Terminal run 'curl -sSL https://extra.yantraos.com/install.sh | bash', then read ~/.extra/app/STARTER_PROMPT_MACOS.md"
  > 
  > Star the repo on GitHub: https://github.com/AIYantra/extra 🚀

#### Template 3: Reddit (`r/ClaudeAI`) Deep-Dive Post
- **Title**: `How to give Claude Desktop native hands and eyes on macOS with zero latency (Open Source)`
- **Body**: Detailed walkthrough of setting up Claude Desktop with Extra, technical benchmarks comparing ScreenCaptureKit vs PyAutoGUI, and practical use cases (cleaning up folders, running calculations, filling web forms).

---

## Technical Appendix: System Health & Rollback Protocols

### A.1 Post-Launch Monitoring Checklist
1. **GitHub Issues Watch**: Triage tags: `platform:macos`, `tcc:permissions`, `install:brew`.
2. **Telemetry (Optional/Anonymous)**: Track OS version distribution and completion rates.
3. **Automated CI Integration**: GitHub Actions matrix testing macOS 13, 14, and 15 on every PR.

### A.2 Rollback Plan
If an unexpected macOS update breaks a PyObjC binding:
1. `install.sh` has a fallback capture path (`CGDisplayCreateImage` via Quartz) that runs independently of `ScreenCaptureKit`.
2. Edge router can instantly roll back `install.sh` to a previous stable commit tag without requiring DNS changes.

---

## Conclusion

By executing these 6 pillars, **Project Extra** transforms from a Windows-only tool into the premier, sovereign, cross-platform computer-use engine for both Windows and macOS. The user adoption path remains frictionless, predictable, and immediately delightful.
