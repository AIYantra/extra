---
trigger: always_on
description: Universal Engine Invariant & Architectural Generalization Rule - All Extra fixes, primitives, and implementations must be 100% universal across all applications, strictly prohibiting app-specific code branches.
---

# Universal Engine Invariant & Architectural Generalization Rule

Extra is designed to be an **autonomous, universal computer-use engine** capable of piloting any desktop or web application on macOS and Windows—including software it has never encountered before.

To maintain architectural integrity and prevent Extra from degenerating into a fragile collection of application-specific hacks:

---

## 1. CORE INVARIANT — ZERO APP-SPECIFIC CODE IN THE CORE ENGINE

- **STRICT PROHIBITION:** **NEVER write application-specific code branches** (`if app == "canva":`, `if "photoshop" in title:`, `if proc == "blender":`) inside the core Extra engine, MCP server tools, or evolution subsystems:
  - `extra/core/` (motion, soul, evolution, memory, scout, platform drivers)
  - `extra/mcp/` (server tool definitions and dispatchers)
  - `extra/fastpath/` (system-level filesystem, browser, and shell primitives)
- **WHERE APP KNOWLEDGE LIVES:**
  - **Declarative Skills:** Application-specific workflows, hotkeys, and coordinate conventions belong **exclusively** in declarative skill markdown files (`skills/extra-<app>/SKILL.md`).
  - **Episodic Memory:** Known application quirks and verified workarounds belong in the local **KùzuDB memory graph** (`memory/graph.kuzu`), ingested dynamically via `record_action_quirk()`.
- **THE ENGINE INVARIANT:** If an engine feature or fix only works for one specific application, **it is architecturally invalid.**

---

## 2. THE 4-STEP UNIVERSAL ROOT CAUSE GENERALIZATION PROTOCOL

Whenever an issue, failure, or bug is discovered while automating a specific application:

### Step 1: Deep Root Cause Analysis
Determine the exact technical failure mechanism (e.g. why did an input fail, why did focus not transfer, why did the model hallucinate?).

### Step 2: Abstract to UI Framework & OS Failure Class
Do **NOT** treat the issue as a "Canva bug" or "Premiere bug". Categorize it into its universal architectural class:
- **Custom Chrome / Tab Focus Isolation:** Custom Electron/Chromium, WPF, or Qt window title bars not forwarding standard OS tab-switching hotkeys.
- **Actuator vs. Perception Divergence:** Low-level OS event injection succeeding (`SendInput`, `CGEvent`) while an opaque HTML5/WebGL/DirectX canvas fails to render or accept input.
- **State Transition / Mode Gate Violations:** Dispatching actions intended for Mode B (e.g., Editor/Canvas) while the application is still in Mode A (e.g., Home/Dashboard/Modal).
- **Epistemic Drift & Blind Completion:** Declaring task completion or self-evolving based on actuation acknowledgments rather than ground-truth pixel verification.
- **Stale Accessibility Tree Caching:** Background processes keeping orphaned accessibility nodes alive in the OS tree.

### Step 3: Implement the Universal Architectural Fix
Design and implement a solution at the **engine or protocol level** that permanently eliminates that entire failure class for **ALL applications**:
- E.g. **Universal Pre-Action State Gates:** Require mode verification before inner-mode dispatch.
- E.g. **Universal Hardware vs. Visual Telemetry:** MCP tools explicitly report actuation vs. visual rendering boundaries.
- E.g. **Universal Golden-Path Evolution Gating:** Any noisy or stalled trajectory across *any* app is barred from creating fast paths.
- E.g. **Universal Visual Grounding (Project SOUL):** Resolving targets from raw pixels when accessibility trees are opaque.

### Step 4: Declarative Playbook Update
If the application has a unique user-facing quirk, document it declaratively in that application's `SKILL.md` under `## 5. Anti-Stall Guardrails & Caveats` and commit it to episodic memory.

---

## 3. ENGINE VS. SKILL BOUNDARY

| Concern | Core Engine (`extra/`) | Skill Playbook (`skills/extra-<app>/`) |
| :--- | :--- | :--- |
| **Logic Type** | Universal primitives, drivers, perception, heuristics | Declarative workflows, application tips, templates |
| **App Names** | **Forbidden** (completely agnostic) | Expected in title and frontmatter |
| **Hotkeys** | General dispatch (`extra_hotkey`) | Specific application key combinations |
| **Coordinates** | Dynamic resolution, visual grounding, normalization | General layout regions (e.g. sidebar rail) |
| **Failure Handling** | Universal stall detection, golden-path gating | App-specific workarounds and pitfalls |

---

## 4. DEFINITION OF A UNIVERSAL FIX

Before finalizing any fix or plan, verify:
* [ ] Does this fix contain zero hardcoded application names in `extra/core/`, `extra/mcp/`, or `extra/fastpath/`?
* [ ] Does this fix protect an entire class of applications (Electron, WebGL, Win32, Cocoa, Qt), not just the one being tested?
* [ ] If the user runs an unknown custom desktop app tomorrow, will this fix benefit that app too?
* [ ] Is application-specific guidance strictly confined to `SKILL.md` or episodic memory?

If the answer to any of the above is NO, refactor the implementation until it is truly universal.
