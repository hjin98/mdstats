---
title: "Stage 11E8a Pilot Common Provenance Utilities Specification"
version: "0.20.16a0"
date: "2026-07-26"
---

# Scope

`mdstats.analysis.density._pilot_common` is the private implementation owner for
mechanically identical helpers shared by the Stage 11E8a S0-S4 pilot modules.
It does not own any public scientific schema.

# Owned helpers

The module owns:

- canonical JSON serialization;
- SHA-256 signing of canonical values and exact files;
- dtype/shape-aware array digests;
- finite immutable metadata normalization and JSON thawing;
- positive, nonnegative, fractional, and positive-integer validation;
- read-only array normalization;
- unique NumPy payload-byte accounting; and
- canonical evidence-record replacement by `evidence_id`.

# Compatibility requirements

- Public exception types remain the `PilotAudit*Error` classes exported by
  `pilot_audit`.
- Existing serialized payloads and signatures must remain byte-for-byte stable.
- The helper module remains private and is not re-exported from public package
  namespaces.
- Scientific stage modules retain ownership of their own schemas and gates.
- The refactor must not alter the real-source E8a dossier or any accepted test
  fixture signature.

# Acceptance

- Pilot S0-S4 tests pass without signature changes.
- Common helper tests cover deterministic serialization, immutable metadata,
  duplicate-array accounting, and evidence replacement.
- No S1-S4 module retains a private duplicate of the extracted helper functions.
