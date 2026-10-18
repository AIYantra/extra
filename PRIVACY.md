# Project Extra Privacy Policy & Telemetry Specification
**Effective Date:** October 2026 • **Status:** Active Standard

Project Extra is an autonomous, flashless computer-use engine built for developers, AI agents, and power users. Because Extra interacts with desktop environments, monitors, and OS input subsystems, we operate under a strict **Privacy-by-Design** architecture.

---

## 1. The Core Privacy Guarantees

1. **Local Air-Gapped by Default:**
   * Outbound telemetry is **DISABLED BY DEFAULT**.
   * In non-interactive environments (agent subtasks, background daemons, headless CI/CD), Extra operates in 100% air-gapped local mode. Zero network requests are made.
2. **The Zero-PII Guarantee:**
   * ❌ **WE NEVER COLLECT SCREENSHOTS.** Visual frame buffers and captures remain strictly on your physical machine.
   * ❌ **WE NEVER COLLECT PROMPTS OR TEXT INPUTS.** Prompts, typed strings, and LLM reasoning are completely excluded.
   * ❌ **WE NEVER COLLECT PASSWORDS OR CREDENTIALS.** Auth tokens, API keys, and bearer headers are automatically redacted client-side before any event serialization.
   * ❌ **WE NEVER COLLECT PERSONAL FILE PATHS.** Absolute paths (e.g. `C:\Users\John\Documents\taxes.pdf`) are scrubbed to generic placeholders (`<USERPROFILE>\...\*.pdf`).
3. **Universal Standards Compliance:**
   * Setting `DO_NOT_TRACK=1` or `EXTRA_TELEMETRY=0` in your environment strictly overrides all settings and permanently disables any network transmission.

---

## 2. What Data Is Collected (When Explicitly Opted-In)

When you choose to enable community telemetry (`extra telemetry on`), Extra transmits minimal, aggregated performance metrics to help the community discover broken application interfaces, reduce latency, and tune adaptive visual settle thresholds:

```json
{
  "client_hash": "4b048fc826fd6548...",
  "extra_version": "0.3.1",
  "platform": {
    "os": "win32",
    "release": "10.0.26100",
    "arch": "AMD64"
  },
  "execution_metrics": {
    "app_name": "calc",
    "archetype": "math_calculation",
    "tool_name": "extra_subtask_run",
    "compilation_latency_ms": 0.007,
    "execution_duration_ms": 450.2,
    "settle_latency_ms": 14.5,
    "actions_count": 8,
    "success": true,
    "error_class": null,
    "speedup_multiplier": 21.1
  }
}
```

### Data Fields Explained:
* **`client_hash`:** A one-way salt-hashed machine identifier (`sha256(machine_guid + salt)`). It cannot be reversed into an IP address, MAC address, hostname, or username.
* **`platform`:** OS family and architecture for cross-platform compatibility auditing.
* **`execution_metrics`:** High-level execution speeds, intent categories, error categories, and speedup ratios.

---

## 3. How to Manage Your Settings

You have full, transparent 1-command control over telemetry:

```bash
# Check current telemetry and privacy status
extra telemetry status

# Opt-in to help improve Extra for everyone
extra telemetry on

# Instant complete opt-out (100% air-gapped local mode)
extra telemetry off
```

### Environment Variable Overrides:
```bash
# Universally disable all telemetry across all tools
export DO_NOT_TRACK=1

# Or specifically for Extra
export EXTRA_TELEMETRY=0
```

---

## 4. Local Impact Ledger & Data Storage

All calculations regarding **Time Saved, Tokens Saved, and Dollar Cost Saved** (the "Brave Shields" system) are stored **100% locally on your machine**:
* **Ledger File:** `~/.extra/metrics/impact_ledger.json`
* **Local Dashboard:** `~/.extra/workspace/impact_dashboard.html`

View your local savings anytime in the terminal:
```bash
extra stats
```
Or open the visual dashboard in your browser:
```bash
extra dashboard
```

---

## 5. Regulatory Compliance

* **European Union (GDPR & ePrivacy Directive):** Extra enforces prior consent (opt-in) by default, strips all identifying pseudonymous data, and honors user rights.
* **California (CCPA / CPRA):** Extra does not sell or share personal information.
* **India (Digital Personal Data Protection Act 2023):** Built under digital sovereignty and verifiable user consent guidelines.
