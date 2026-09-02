---
kind: implementation-workplan-authority-entrypoint
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 20
status: reopened
current_authority_pointer: AUTHORITY_REVISION_20.md
review_verdict: NO-PASS
---

# Storage/I-O reset package authority

This is the canonical navigation entrypoint for the active storage/I/O reset package.

The **Revision-19 design remains final-closure reviewed and accepted**, while the executable package is **reopened / NO-PASS under Revision 20** after review of executable `869ae1b6e9211faa1873d47e7850050cd85b5ff7` / tree `a5e6c8868bdec9e88a877e6ca84aa6ef6d609286`.

The current branch-head successor `bf05fe5e35a44c4b5898075da3bb2b54ba220238` changes generated PDF outputs only and does not alter the executable review target.

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
11. `STORAGE_IO_MANAGEMENT_RESET_FINAL_REPAIR_PLAN_CLOSURE_REVISION_19.md`;
12. `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_4.md`;
13. `AUTHORITY_REVISION_20.md`.

Earlier authority revisions other than the explicitly included Revision 11 are provenance only. The frozen parent target-size V7 workplan remains the scientific/architectural verdict; storage repair must not reopen target-size, CV, publication, qualification, calibration, locked-test, or release science for convenience.

Revision 20 is an implementation-review reopen, not a new design revision. The bounded remaining work is:

- move the observational writability guard to the true start of `replace_records_atomically()` and make its test cross a real externalization boundary;
- make the P7 attempt census directory-complete, root/identity-bound, and strict about the persisted current-state digest so missing/copied/unauthenticated state becomes the required global consequential-planning failure;
- validate/reuse the retained v3 proof on repeated terminal release and close the remaining proof/state cross-field checks;
- add the missing real-owner counterfactuals and supply exact executable commit/tree regression/integration evidence required by Revision 19.

Preserve all conforming R12-R19 source work. Resume at the affected R19-E2/E3 repair gates, run their stage-local regressions, then complete R19-E5/R19-F final acceptance.

Full external-DFT, long GPU production, and environment-specific HPC/storage qualification remain deferred.
