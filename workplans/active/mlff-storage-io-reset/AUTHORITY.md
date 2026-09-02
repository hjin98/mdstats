---
kind: implementation-workplan-authority-entrypoint
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 18
status: reopened
current_authority_pointer: AUTHORITY_REVISION_18.md
review_verdict: NO-PASS
---

# Storage/I-O reset package authority

This is the canonical navigation entrypoint for the active storage/I/O reset package.

The **repair plan is final-closure reviewed and implementation-ready under Revision 18**, while the executable package remains **reopened / NO-PASS** until the bounded R17/R18 repairs and candidate-bound acceptance evidence are complete.

## Current supplied contract

Read these artifacts together:

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
11. `AUTHORITY_REVISION_18.md`.

Earlier authority revisions other than the explicitly included Revision 11 are provenance only. The frozen parent target-size V7 workplan remains the scientific/architectural verdict; storage repair must not reopen target-size, CV, publication, qualification, calibration, locked-test, or release science for convenience.

Revision 18 closes the remaining repair-plan gaps around bounded P5 completion authority versus exact topology certification, empty-directory recursive ownership, cross-process VACUUM serialization, serialized audit append/retention and realistic fsync-failure semantics, dedup staging liveness authority, and final evidence identity.

Reviewed executable remains `2e6a2768341f75a87430d1313b7d64a1e85dfd04` / tree `681ed2b915bb29f05505eef87fcc83cf8e1c4b99`. Preserve conforming R12-R17 work and implement only the earliest affected R12-S0/S1 obligations before continuing through the existing R12-S4 acceptance sequence.

Full external-DFT, long GPU production, and environment-specific HPC/storage qualification remain deferred.
