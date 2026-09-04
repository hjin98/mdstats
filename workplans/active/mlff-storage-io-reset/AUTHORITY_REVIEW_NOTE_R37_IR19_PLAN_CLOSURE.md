---
kind: implementation-review-plan-closure-note
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 37
status: reopened
current_workplan: STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_19_PLAN_CLOSURE.md
accepted_design: STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md
reviewed_executable_commit: 7aa938d71361d2cb2ce6e370165a9a12566669f3
reviewed_executable_tree: 5fd91f30672fb7d9a2be89d6e0fdc261619509aa
review_verdict: NO-PASS
reviewed_date: 2026-09-03
---

# Storage/I-O reset R37 IR19 plan-closure note

A second design-handoff review found no need to change Revision 30, Revision 37, or the product architecture. IR19 remains the correct bounded implementation family, but its first wording left several implementation escape hatches.

The plan is now closed around these additional consequences:

1. the cleanup action-family guard is **plan-level and total**: it runs before per-action classification, covers empty plans and maintenance as well as removal/eviction, and is consumed by both default and production cleanup;
2. the exported single-action classifier cannot positively classify cleanup semantics under a non-cleanup policy, while a genuine empty cleanup plan remains a valid no-op;
3. the set an engine preflights as supported and the classes it actually dispatches must be one coherent closed set or be explicitly checked for completeness; generic destruction is an explicit `CLASS_GENERIC_LEAF` handler and every residual class fails closed;
4. final structural evidence includes a bounded census of production `StorageExecutor.run` callers and consequential generic-remover calls, including aliases/references, and any AST/Semgrep rule must catch a classifier-present function that also contains an undominated generic call;
5. final functional evidence remains bound to the exact post-test executable tree and must include the real default and production wrong-family counterfactuals, empty wrong-family and empty-cleanup controls, preserved IR18 real-owner routing, affected regression, core/integration, owner regressions, static/collection checks, and command/pass/fail/skip counts.

The current normative implementation handoff is the original `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_19.md` together with `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_19_PLAN_CLOSURE.md`; the latter governs where the wording differs.

No IR20 and no Revision 38 are created. The executable `7aa938d71361d2cb2ce6e370165a9a12566669f3`, tree `5fd91f30672fb7d9a2be89d6e0fdc261619509aa`, remains **NO-PASS** until these refined IR19 obligations and exact-candidate evidence are implemented. External DFT, long GPU production, and environment-specific HPC/shared-storage qualification remain deferred and nonblocking.

**Plan disposition:** CLOSED / implementation-ready.