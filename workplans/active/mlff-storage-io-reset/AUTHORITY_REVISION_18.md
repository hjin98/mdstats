---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 18
status: reopened
amended_date: 2026-09-01
current_authority_pointer: true
reviewed_authority_head: a5f5d1c3d721df2e0ca3a6bd06745c129c8b7e72
reviewed_authority_tree: c9e098e54299e252e93a30aee956bc89081f6c6c
reviewed_executable_commit: 2e6a2768341f75a87430d1313b7d64a1e85dfd04
reviewed_executable_tree: 681ed2b915bb29f05505eef87fcc83cf8e1c4b99
review_verdict: NO-PASS
precedence: this authority supersedes earlier mlff-storage-io-reset authority pointers; the current supplied contract is STORAGE_IO_MANAGEMENT_RESET_WORKPLAN_REVISION_2.md + STORAGE_IO_MANAGEMENT_RESET_FINAL_CLOSURE_AMENDMENT.md + AUTHORITY_REVISION_11.md + STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_1.md + STORAGE_IO_MANAGEMENT_RESET_REPAIR_PLAN_CLOSURE_AMENDMENT.md + STORAGE_IO_MANAGEMENT_RESET_FINAL_REPAIR_DESIGN_CLOSURE_AMENDMENT.md + STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_2.md + STORAGE_IO_MANAGEMENT_RESET_FINAL_REPAIR_PLAN_CLOSURE_REVISION_16.md + STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_3.md + STORAGE_IO_MANAGEMENT_RESET_FINAL_REPAIR_PLAN_CLOSURE_REVISION_18.md + this authority pointer; later amendments control where they explicitly narrow or correct earlier text; the frozen parent target-size V7 workplan remains the scientific and architectural verdict
---

# Storage/I-O reset package authority — revision 18 final repair-plan closure

## Disposition

The executable package remains **NO-PASS / reopened**. Revision 17's implementation findings remain valid, but the repair plan itself required the additional closure corrections in `STORAGE_IO_MANAGEMENT_RESET_FINAL_REPAIR_PLAN_CLOSURE_REVISION_18.md` before another implementation pass.

Revision 18 does not add another lifecycle or reopen the global owner-driven storage architecture. It closes five handoff surfaces:

1. P5 terminal authority is split conceptually into bounded compact completion authority plus exact immutable member/topology authority, so normal reporting remains O(1) in descendant count while destructive certification remains complete;
2. recursive closed-subtree authority explicitly covers directory nodes, including unexpected empty directories;
3. VACUUM's final predicate exclusion is cross-process and operation-scoped;
4. audit append and retention are one serialized diagnostic-owner lifecycle with realistic fsync-failure semantics;
5. dedup staging abandonment is derived from the existing storage-operation/recovery ownership contract, never PID/age heuristics.

The Revision-18 amendment also clarifies final executable evidence reuse across generated-document-only successor commits.

## Current supplied implementation contract

Implementation must read these artifacts together:

1. `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN_REVISION_2.md`;
2. `STORAGE_IO_MANAGEMENT_RESET_FINAL_CLOSURE_AMENDMENT.md`;
3. `AUTHORITY_REVISION_11.md`;
4. `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_1.md`;
5. `STORAGE_IO_MANAGEMENT_RESET_REPAIR_PLAN_CLOSURE_AMENDMENT.md`;
6. `STORAGE_IO_MANAGEMENT_RESET_FINAL_REPAIR_DESIGN_CLOSURE_AMENDMENT.md`;
7. `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_2.md`;
8. `STORAGE_IO_MANAGEMENT_RESET_FINAL_REPAIR_PLAN_CLOSURE_REVISION_16.md`;
9. `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_3.md`;
10. `STORAGE_IO_MANAGEMENT_RESET_FINAL_REPAIR_PLAN_CLOSURE_REVISION_18.md`;
11. this authority pointer.

`AUTHORITY.md` is the canonical navigation entrypoint and must agree with this revision. Earlier authority revisions other than the explicitly included Revision 11 are provenance only.

## Implementation boundary

Preserve the substantial conforming R12-R17 implementation. Resume only the earliest affected R12-S0/S1 obligations identified by Revision 18, then continue through the existing R12-S4 acceptance stage.

No target-size science, P2 statistical rule, P3/P4 currentness, P5 CV/final-production science, P7 qualification/locked/release science, or frozen parent V7 verdict is reopened.

Full external-DFT, long GPU production, and environment-specific HPC/storage qualification remain deferred.

**Disposition:** repair plan **final-closure reviewed and implementation-ready under Revision 18**; executable remains **NO-PASS / reopened** until repaired and accepted.