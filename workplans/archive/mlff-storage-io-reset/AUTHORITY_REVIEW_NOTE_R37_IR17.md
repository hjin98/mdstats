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

# Storage/I-O reset R37 implementation review note — refined IR17

The Revision-37 implementation at executable commit `9db97f72a6ba033aa4b092edb0ece39db56f5b23`, tree `a09dabfe5eb7279adb9398a98f9349c9713962a8`, is **NO-PASS**.

Revision 30 and Revision 37 remain the accepted closed design/workplan authority. The refined complete current bounded implementation correction is `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_17.md`; no Revision 38 is created because the corrections below are necessary consequences of already-frozen target-identity, descriptor-capability, transition/durability, and close-ranking semantics.

Blocking families after plan-closure review are:

1. **Capability acquisition / final target identity.** Generic/fully-certified and individually-authorized common cleanup still perform authority-relevant acquisition through pathname checks plus fresh opens without proving the actual opened capabilities are the plan/owner-bound objects. The default single-file cleanup path likewise can unlink a same-name replacement after plan revalidation because the live no-follow file is not compared with `PlannedAction.filesystem_identity` immediately before unlink.
2. **Capability continuity through durability.** Top-level directory removal currently can close the authenticated parent after fd-relative `rmdir` and later reopen `path.parent` by pathname for the authoritative fsync. The directory-entry durability step must use the same parent capability that performed the mutation. File unlink must likewise remain fd-relative once a bound parent capability exists.
3. **Exactly-once close/finalization.** Recursive mount-refusal close can bypass structured `MutationLedger` transport; `open_directory_nofollow()` contains a double-close shape when cleanup close itself fails; and failed P7 session acquisition can allow a raw `finally` close failure to replace an already-decided owner/authentication refusal. The consequential close family must be closed systematically under one primary/secondary ranking policy.
4. **Acceptance closure.** Material generic/common/default-file/P7 cleanup claims still require real inventory/planning/authorization/production-engine/`StorageExecutor.run`/settlement/audit counterfactuals, stage-local affected regression for each executable stage, and fresh exact-candidate affected regression/integration/static/document evidence after the last executable edit.

Preserve conforming R37 transition-exact unlink/publication behavior, archive and restore-journal phases, final fd-relative `rmdir` identity comparison, typed common-member authority, P7 session semantics already conforming, and all other accepted Revision-30 through Revision-37 behavior.

External DFT, long GPU production, and environment-specific HPC/shared-storage qualification remain deferred and nonblocking.
