## 🚀 Pull Request Description

### Summary of Changes
Provide a brief summary of what this PR introduces or fixes.

### Related Issues
Fixes # (issue number)

---

## 🏛️ Architectural Invariants Checklist

Please confirm your changes strictly adhere to Extra's core architectural standards:

- [ ] **Zero Solo Binary Blobs:** No unverified third-party C++/Rust `.pyd`/`.dll` packages added.
- [ ] **PerMonitorV2 DPI Compliance:** All coordinate math uses [`extra.core.geometry`](extra/core/geometry.py).
- [ ] **Dual-Plane Perception:** Leveraged Semantic UI Automation (Plane B) wherever possible instead of blind coordinate guessing.
- [ ] **Zero-Lag Input:** Fast typing and input injection verified without artificial delays.
- [ ] **Closed-Loop Stall Protection:** Checked delta / outcome where actions mutate screen state.

---

## 🧪 Verification & Hardware Testing

- [ ] Run `extra doctor` and confirmed all hardware checks pass.
- [ ] Run `extra test` and verified all 6 core integration test modules pass.
- [ ] Tested on physical Windows 10 or Windows 11 hardware.
- [ ] Added or updated test coverage in `test_core_engine.py` (if applicable).

---

## 📸 Demonstration / Output
If adding a visual or CLI feature, paste logs or screenshots demonstrating the change in action.
