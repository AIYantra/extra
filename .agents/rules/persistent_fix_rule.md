# Persistent Fix Rule — Project Extra

Every bug fix, performance optimization, or enhancement must be permanently implemented in the Extra source tree and verified across both automated and real-world environments.

## Definition of DONE
- [ ] Root cause identified and documented.
- [ ] Minimal, robust fix applied to `extra/`.
- [ ] Verified via `extra test` and `extra doctor`.
- [ ] Confirmed on physical Windows 10/11 hardware without regressions.
- [ ] Permanent change committed to the repository (no temporary monkey-patches).
- [ ] Zero unverified binary dependencies added.
