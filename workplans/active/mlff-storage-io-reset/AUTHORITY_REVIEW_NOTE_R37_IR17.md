---
kind: implementation-review-authority-note
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 37
status: reopened
current_workplan: STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_17.md
accepted_design: STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md
reviewed_executable_commit: 9db97f72a6ba033aa4b092edb0ece39db56f5b23
reviewed_executable_tree: a09dabfe5eb7279adb9398a98f9349c9713962a8
reviewed_branch_head: bd4b78e59f0b500ac130597943adab5e07fcad4b
reviewed_branch_tree: 683fcc2324780a6f9b3dba4aab98f949090529e4
review_verdict: NO-PASS
reviewed_date: 2026-09-03
---

# Storage/I-O reset R37 implementation review note — IR17

The Revision-37 implementation at executable commit `9db97f72a6ba033aa4b092edb0ece39db56f5b23`, tree `a09dabfe5eb7279adb9398a98f9349c9713962a8`, is **NO-PASS**.

Revision 30 and Revision 37 remain the accepted closed design/workplan authority. No new product semantic or redesign is introduced by this review. The complete current bounded implementation correction is `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_17.md`.

Blocking families are:

1. generic/fully-certified and individually-authorized common cleanup still perform authority-relevant root/parent acquisition through a pathname check followed by a fresh absolute/multi-component open without proving the actual opened descriptor is the plan/owner-bound object;
2. recursive mount-refusal close can bypass structured `MutationLedger` transport, and the shared no-follow open helper contains a double-close control-flow shape when its first cleanup close itself fails;
3. several generic/common R37 counterfactuals still use a hand-constructed `StorageExecutionResult` helper rather than the required real planner/`StorageExecutor`/audit boundary, and no exact-candidate behavioral execution receipt/status is recorded for the candidate.

Preserve conforming R37 transition-exact unlink/publication behavior, archive and restore-journal phases, final fd-relative `rmdir` identity comparison, typed common-member authority, P7 session semantics, and all other conforming Revision-30 through Revision-37 behavior.

External DFT, long GPU production, and environment-specific HPC/shared-storage qualification remain deferred and nonblocking.
