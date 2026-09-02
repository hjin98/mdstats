---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 19
status: reopened
amended_date: 2026-09-01
current_authority_pointer: true
reviewed_candidate_head: 00fc36001f37fa81039f17d62436fb7deda89e80
reviewed_candidate_tree: 739114a59884ca8c231a4239da6ca4820aec3272
reviewed_executable_commit: 408cf5495e6e361b6273770d212dfb3bd2e23d95
reviewed_executable_tree: 13bea3b6fc63366d853454313c8ee7c3d2f36a0f
review_verdict: NO-PASS
precedence: this authority supersedes earlier mlff-storage-io-reset authority pointers; the current supplied contract is STORAGE_IO_MANAGEMENT_RESET_WORKPLAN_REVISION_2.md + STORAGE_IO_MANAGEMENT_RESET_FINAL_CLOSURE_AMENDMENT.md + AUTHORITY_REVISION_11.md + STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_1.md + STORAGE_IO_MANAGEMENT_RESET_REPAIR_PLAN_CLOSURE_AMENDMENT.md + STORAGE_IO_MANAGEMENT_RESET_FINAL_REPAIR_DESIGN_CLOSURE_AMENDMENT.md + STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_2.md + STORAGE_IO_MANAGEMENT_RESET_FINAL_REPAIR_PLAN_CLOSURE_REVISION_16.md + STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_3.md + STORAGE_IO_MANAGEMENT_RESET_FINAL_REPAIR_PLAN_CLOSURE_REVISION_18.md + STORAGE_IO_MANAGEMENT_RESET_FINAL_REPAIR_PLAN_CLOSURE_REVISION_19.md + this authority pointer; later amendments control where they explicitly narrow or correct earlier text; the frozen parent target-size V7 workplan remains the scientific and architectural verdict
---

# Storage/I-O reset package authority — revision 19 final repair-plan closure

## Disposition

The executable package remains **NO-PASS / reopened** at executable commit
`408cf5495e6e361b6273770d212dfb3bd2e23d95` / tree
`13bea3b6fc63366d853454313c8ee7c3d2f36a0f`. Candidate head
`00fc36001f37fa81039f17d62436fb7deda89e80` is a generated-document-only
successor and does not alter that executable identity.

Revision 19 is the final independent challenge of the Revision-18 implementation
handoff. The conforming R12-R18 storage architecture remains accepted. Revision
19 narrows the remaining work to these implementation surfaces:

1. typed/no-follow recursive ownership from P5/P7 owner proof through the common
   inventory/executor, including same-path file/directory substitution,
   symlink/special-node refusal, and strict authority-file reads;
2. an authenticated, state-bound typed P7 released-attempt proof so no foreign
   top-level file/empty directory or damaged manifest can become reclaimable;
3. shared storage/P7 attempt-state synchronization, including the legal
   aborted-to-active reopen path;
4. fail-closed handling of unreadable P7 attempt state as a cross-owner planning
   integrity failure rather than silently dropping unknown referenced paths;
5. a bounded P7 normal-report path separate from exact consequential
   certification;
6. thread-correct, cross-instance, cross-process, constructor-complete
   CampaignStore writer exclusion plus early observational write refusal;
7. explicit CampaignStore ownership of the persistent writer-lock file; and
8. exact candidate-bound executed regression/integration evidence.

The complete implementation instructions and counterfactual acceptance cases are
frozen in
`STORAGE_IO_MANAGEMENT_RESET_FINAL_REPAIR_PLAN_CLOSURE_REVISION_19.md`.

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
12. this authority pointer.

`AUTHORITY.md` is the canonical navigation entrypoint and must agree with this
revision. Earlier authority revisions other than the explicitly included
Revision 11 are provenance only.

## Implementation boundary

Preserve all conforming R12-R18 behavior. Resume at the earliest affected
R12-S0/S1 owner-contract obligation, execute the R19-A through R19-F repair gates
inside the existing lifecycle, and continue through R12-S4 final affected-
surface acceptance.

No target-size science, P2 statistical rule, P3/P4 currentness, P5 CV/final-
production science, P7 qualification/calibration/locked-test/release science, or
frozen parent V7 verdict is reopened.

Full external-DFT, long GPU production, and environment-specific HPC/storage
qualification remain deferred.

**Design disposition:** Revision-19 repair plan **PASS / implementation-ready**.
**Executable disposition:** **NO-PASS / reopened** until R19 is implemented and
accepted on the exact executable candidate.
