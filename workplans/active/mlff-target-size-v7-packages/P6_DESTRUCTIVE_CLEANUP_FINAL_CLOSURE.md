---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P6
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
sequence: 6
status: active
package_revision: 4
amended_date: 2026-08-30
entry_p5_accepted_baseline_commit: 1670275487d29bbcde4c59efafdef9d1f8b0ced7
entry_p5_accepted_baseline_tree: 17e2c5609974712bda1efd3375f09f42da830f68
compatibility_policy: destructive-generation-reset-current-generation-cutover-no-derived-migration
---

# P6 revision 4 — destructive cleanup and assembled final closure

The frozen parent remains the scientific/architectural verdict. P6 remains bound to Protocol 5.8.0 and the exact accepted P5A6 baseline above.

## Authoritative revision-4 artifact set

Revision 4 is intentionally represented as a snapshot-complete two-document composition so the already-reviewed revision-3 contract remains verbatim while the final persistence-compatibility correction is explicit and lossless:

1. `P6_REVISION_3_BASE.md` — exact revision-3 P6 body as committed at `a709c7f8d3082dd5e41222d62ce7047e159adf60`.
2. `P6_REVISION_4_P5A6_COMPATIBILITY_AMENDMENT.md` — revision-4 amendment.

Both files are mandatory implementation authority. The amendment has precedence only where it explicitly changes or tightens revision-3 wording; all other revision-3 obligations remain binding.

Do **not** implement this pointer file in isolation and do not treat the amendment as replacing the revision-3 cleanup/acceptance contract.

Revision 4 does not reopen P1-P5 science. Its only material changes are:

- mandatory real **P5A6-created current workspace -> final-P6 reopen/authentication** acceptance, distinct from P6->P6 restart and obsolete V5/V6 rejection;
- strict blocking treatment for documentation/PDF checks that are actually required by the frozen parent or governing repository policy.

After implementation, independent Software Design review evaluates the composed revision-4 authority against the frozen parent.
