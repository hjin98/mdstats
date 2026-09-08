---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 20
status: reopened
amended_date: 2026-09-02
current_authority_pointer: true
reviewed_authority_revision: 19
reviewed_executable_commit: 869ae1b6e9211faa1873d47e7850050cd85b5ff7
reviewed_executable_tree: a5e6c8868bdec9e88a877e6ca84aa6ef6d609286
reviewed_branch_head: bf05fe5e35a44c4b5898075da3bb2b54ba220238
review_verdict: NO-PASS
precedence: this authority supersedes earlier mlff-storage-io-reset authority pointers; the current supplied contract is the Revision-19 supplied contract plus STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_4.md and this authority pointer; Revision 19 remains the accepted design and this revision routes only bounded implementation nonconformance and acceptance gaps
---

# Storage/I-O reset package authority — revision 20 implementation review

## Disposition

The Revision-19 implementation at executable commit `869ae1b6e9211faa1873d47e7850050cd85b5ff7` / tree `a5e6c8868bdec9e88a877e6ca84aa6ef6d609286` is **NO-PASS / reopened**.

The current branch-head successor `bf05fe5e35a44c4b5898075da3bb2b54ba220238` changes generated document outputs only and therefore does not alter the functional review target.

Revision 19 remains the accepted storage design. This review found bounded implementation nonconformance:

1. `replace_records_atomically()` still externalizes before an observational writability guard, and its candidate test never crosses the 4 MiB/forced-external boundary;
2. the P7 storage-facing attempt census is state-file-driven rather than attempt-directory-complete, does not bind state `attempt_identity` to the directory name, and accepts current attempt-state payloads with omitted `content_digest`, so missing/copied/unauthenticated state can erase unknown external retention references without the required global planning failure;
3. repeated terminal attempt release returns before validating/reusing the retained v3 topology proof, and the strict proof/state binding should validate its duplicated binding/publication fields;
4. exact candidate-bound functional/regression/integration evidence required by Revision 19 is not present; the exact executable commit exposes only a successful docs check, and several candidate tests are not yet proxy-proof for the required counterfactuals.

The complete repair and acceptance instructions are in `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_4.md`.

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
11. `STORAGE_IO_MANAGEMENT_RESET_FINAL_REPAIR_PLAN_CLOSURE_REVISION_19.md`;
12. `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_4.md`;
13. this authority pointer.

`AUTHORITY.md` is the canonical navigation entrypoint and must agree with this revision. Earlier authority revisions other than the explicitly included Revision 11 are provenance only.

## Rework boundary

Preserve all conforming R12-R19 implementation. Reopen only the earliest affected R19-E2/E3 obligations and then complete R19-E5/R19-F acceptance.

No target-size science, P2 statistical rule, P3/P4 currentness, P5 CV/final-production science, P7 qualification/calibration/locked-test/release science, archive/restore architecture, or frozen target-size V7 verdict is reopened.

Full external-DFT, long GPU production, and environment-specific HPC/storage qualification remain deferred.

**Disposition:** implementation **NO-PASS / reopened under Revision 20**; Revision-19 design remains implementation-ready and accepted.
