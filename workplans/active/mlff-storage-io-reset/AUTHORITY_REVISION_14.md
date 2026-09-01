---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 14
status: reopened
amended_date: 2026-09-01
current_authority_pointer: true
reviewed_authority_head: 33bcc888a3582b6f0cb5bfc4ba90f2a1f5e82cb5
reviewed_authority_tree: dadee83d237741c65e5c2d3437f3b24c565c7809
final_repair_design_amendment_commit: db01e0344c3b49e572d559e6986d140a17c26e18
final_repair_design_amendment_tree: 2a5027aab9baba41f90acf5b718da7734db8b0e8
reviewed_executable_commit: 53edc1c75c5b7c9df8f414914534ce915c34f303
reviewed_executable_tree: 8d24e6326b67c38e69a1fe1383be7b975788cac5
review_verdict: NO-PASS
repair_design_disposition: final-closure-reviewed implementation-ready while executable workplan remains reopened
authoritative_rework_amendments:
  - STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_1.md
  - STORAGE_IO_MANAGEMENT_RESET_REPAIR_PLAN_CLOSURE_AMENDMENT.md
  - STORAGE_IO_MANAGEMENT_RESET_FINAL_REPAIR_DESIGN_CLOSURE_AMENDMENT.md
precedence: this authority supersedes earlier mlff-storage-io-reset authority pointers; the current supplied contract is STORAGE_IO_MANAGEMENT_RESET_WORKPLAN_REVISION_2.md + STORAGE_IO_MANAGEMENT_RESET_FINAL_CLOSURE_AMENDMENT.md + AUTHORITY_REVISION_11.md + STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_1.md + STORAGE_IO_MANAGEMENT_RESET_REPAIR_PLAN_CLOSURE_AMENDMENT.md + STORAGE_IO_MANAGEMENT_RESET_FINAL_REPAIR_DESIGN_CLOSURE_AMENDMENT.md + this authority pointer; later repair amendments control where they explicitly narrow or correct earlier repair text; the frozen parent target-size V7 workplan remains the scientific and architectural verdict
---

# Storage/I-O reset package authority — revision 14 final repair-design closure

## Current verdict

The executable storage implementation remains **NO-PASS / reopened** because no new executable candidate has been presented after the implementation review.

Revision 14 records the final Software Design closure challenge of the repair contract. Two remaining design gaps were found and corrected before Implementation resumes:

1. directory-level owner views must not become blanket recursive authority for unexpected descendants; and
2. restore must not implicitly mutate metadata of pre-existing directory/container paths.

The repair design is now **final-closure reviewed and implementation-ready**. This is not a PASS for the executable implementation.

Reviewed executable source remains:

```text
commit 53edc1c75c5b7c9df8f414914534ce915c34f303
tree   8d24e6326b67c38e69a1fe1383be7b975788cac5
```

The revision-13 authority head challenged by this pass was:

```text
commit 33bcc888a3582b6f0cb5bfc4ba90f2a1f5e82cb5
tree   dadee83d237741c65e5c2d3437f3b24c565c7809
```

No P1-P7 or storage executable source changed between those identities.

## Final current implementation contract

Implementation must read these supplied artifacts together:

1. `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN_REVISION_2.md`;
2. `STORAGE_IO_MANAGEMENT_RESET_FINAL_CLOSURE_AMENDMENT.md`;
3. `AUTHORITY_REVISION_11.md` for archive locator and crash-durable publication corrections;
4. `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_1.md` for the R12 implementation-review blockers;
5. `STORAGE_IO_MANAGEMENT_RESET_REPAIR_PLAN_CLOSURE_AMENDMENT.md` for R13 repair-plan corrections and dedup simplification;
6. `STORAGE_IO_MANAGEMENT_RESET_FINAL_REPAIR_DESIGN_CLOSURE_AMENDMENT.md` for the final subtree-ownership and restore-container corrections;
7. this authority pointer.

Earlier authority revisions are provenance only. The supplied set is snapshot-complete for still-binding task-specific semantics.

## Revision-14 corrections

### Recursive ownership coverage

A directory owner view is not blanket authority over all descendants merely because they are lexically beneath the owner root. Every consequential recursive action must use either:

- real-owner **closed-subtree certification**, or
- per-descendant positive owner authorization.

Unexpected descendants discovered initially or between plan/apply reduce authority and remain untouched. This applies across recursive cleanup, archive collection/reclamation, dedup enumeration, restore planning and legacy storage cleanup.

### Restore container metadata

A restore-created directory may receive owner-certified archived metadata. A pre-existing directory/container may not be silently `chmod`/`chown`/ACL/xattr-mutated or replaced just because an archive contains the same directory entry. The restore plan must bind/revalidate relevant existing directory metadata and parent identity; incompatible required metadata fails closed, while compatible shared containers are reused without mutation.

### Durable schema preservation

The existing explicit schema/integrity checks for archive manifest/catalog/nonterminal-journal authority remain mandatory and fail closed. Revision-14 repair must not weaken them. Unsupported/corrupt durable authority is retained and rejected before consequential mutation rather than reinterpreted.

## Rework sequence

The implementation sequence remains the existing repair sequence:

```text
R12-S0  recensus/authority/liveness/trust closure
R12-S1  canonical plan/policy/synchronization repair
R12-S2  liveness + direct dedup + archive/control-plane lifecycle repair
R12-S3  reporting + CampaignStore I/O + public-contract reconciliation
R12-S4  assembled real-owner integration + final affected regression
```

Revision-14 obligations fold into those stages exactly as mapped in the final repair-design closure amendment. Do not create another parallel lifecycle and do not restart accepted P1-P7 work.

## Final closure gate for a future executable candidate

A future PASS requires, on one final assembled executable candidate:

- every R12, R13 and R14 source/conformance repair;
- real-owner tests for closed-subtree/per-descendant recursive authority and unexpected descendants;
- restore tests proving pre-existing directory/container metadata is not implicitly changed;
- all previously required authorization/currentness/liveness/archive/dedup/reporting/maintenance/security/recovery tests;
- stage-local affected regression after each material executable stage;
- final affected-surface re-derivation and fresh final affected regression/integration;
- repository-required CPU-safe broader/full checks where impact cannot be bounded confidently;
- truthful command/result evidence that the required tests actually executed;
- independent Software Design acceptance review.

A source test file or benchmark record without execution remains insufficient evidence.

Full external-DFT scientific qualification, long GPU production qualification and environment-specific HPC/storage qualification remain deferred under the frozen parent/P7 authority.

## Authority boundary

No target-size science, P2 statistics, P3/P4 currentness, P5 CV/final-production science, P7 qualification/locked/release science, or frozen parent V7 verdict is reopened.

**Disposition:** storage workplan **reopened / final repair design closed / implementation-ready under revision 14**. Resume at R12-S0 and implement through R12-S4, then return with a new executable candidate for independent closure review.
