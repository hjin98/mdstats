---
kind: implementation-workplan-authority-entrypoint
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 16
status: reopened
current_authority_pointer: AUTHORITY_REVISION_16.md
review_verdict: NO-PASS
repair_design_disposition: final-closure-reviewed implementation-ready
---

# Storage/I-O reset package authority

This is the canonical navigation entrypoint for the active storage/I-O reset package.

The package is **reopened / executable NO-PASS** under `AUTHORITY_REVISION_16.md`. The repair design is final-closure reviewed and implementation-ready; implementation continues through the existing R12-S0 -> R12-S4 sequence and returns for independent acceptance after the required executed regression/integration evidence exists.

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
9. `AUTHORITY_REVISION_16.md`.

Earlier authority revisions other than the explicitly included Revision 11 are provenance only. Historical pre-intake entry conditions in older authority files no longer govern the current package.

The frozen parent target-size V7 workplan remains the scientific/architectural verdict. Storage repair must not reopen target-size, CV, publication, qualification, calibration, locked-test, or release science for convenience.

Current reviewed executable remains `e7cd824070a6bd7fb3fb83751d2dde185acf0c16` / tree `51bab072d871c9bcef8271b01def1f82c2cad3c5`; it remains NO-PASS until the R15/R16 repair is implemented and acceptance evidence is executed on the final candidate.
