---
kind: implementation-workplan-authority-entrypoint
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 37
status: reopened
current_authority_pointer: AUTHORITY_REVISION_37.md
current_workplan: STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_19_PLAN_CLOSURE.md
current_review_note: AUTHORITY_REVIEW_NOTE_R37_IR19_PLAN_CLOSURE.md
accepted_design: STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md
reviewed_executable_commit: 7aa938d71361d2cb2ce6e370165a9a12566669f3
reviewed_executable_tree: 5fd91f30672fb7d9a2be89d6e0fdc261619509aa
reviewed_branch_head: d035492a71652d562be7c23d0e1e77e8d5bb03c5
reviewed_branch_tree: 0b5a898308406f49cef3bc561584c12b1fc4b562
review_verdict: NO-PASS
---

# Storage/I-O reset package authority

This is the sole canonical navigation/status entrypoint for `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1`.

## Current normative handoff

Implementation uses this supplied current authority set:

- `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md` — broader frozen owner-driven storage architecture and non-goals;
- `STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md` — accepted closed final-apply design and protected trust/outcome semantics;
- `docs/specs/training_data/mlff_storage_management_spec.md` — current storage product contract;
- `AUTHORITY_REVISION_37.md` — accepted Revision-37 bounded design/workplan authority;
- `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_19.md` — IR19 diagnosis and base bounded implementation correction;
- `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_19_PLAN_CLOSURE.md` — current plan-closure refinement; where wording differs, this file governs;
- `AUTHORITY_REVIEW_NOTE_R37_IR19_PLAN_CLOSURE.md` — current plan-closure summary and candidate verdict.

IR18 and earlier implementation-review artifacts are historical provenance only. No still-open requirement depends on loading them. The current storage specification, Revision 30/37, IR19, and the IR19 plan-closure refinement are snapshot-complete for the remaining task-specific semantics.

No IR20 and no Revision 38 are created. The open work remains implementation/acceptance nonconformance under already accepted invocation-local action authority, semantic-owner routing, descriptor-capability, durability, transition-truth, close-ranking, and exact-candidate evidence semantics.

## Reviewed candidate

The executable candidate is `7aa938d71361d2cb2ce6e370165a9a12566669f3`, tree `5fd91f30672fb7d9a2be89d6e0fdc261619509aa`.

The branch successor `d035492a71652d562be7c23d0e1e77e8d5bb03c5`, tree `0b5a898308406f49cef3bc561584c12b1fc4b562`, changes only `docs/specs/training_data/mlff_storage_management_spec.pdf`; behavioral findings remain bound to the executable tree above.

## Preserved conforming implementation

Preserve candidate `7aa938d...` unless a narrowly necessary adjustment is required by refined IR19:

- one canonical positive cleanup semantic classifier shared by default and production cleanup;
- fresh post-revalidation classification while storage lease and owner barriers remain held;
- exact action-to-current-owner path binding and current remove/evict eligibility checks;
- unknown exact-authorizer fail-closed behavior;
- generic-leaf-only default destructive domain and whole-plan domain preflight;
- production P7 exact-authorizer, owner-subtree, maintenance, and generic routing through the shared classification;
- anchored componentwise descriptor acquisition, plan-bound opened-target identity, default single-file fd-relative unlink, and same-parent durability;
- common opened authority/container identities, typed members, and action-wide mutation truth;
- final no-follow name-vs-opened-descriptor comparison before fd-relative `rmdir` and same-parent fsync;
- exact unlink/publication transition callbacks and archive/restore-journal transition phases;
- ranked close/finalization behavior, one-way P7 session invalidation, shared `MutationLedger`, exact action bytes, zero-credit mutation truth, and all other conforming Revision-30 through Revision-37 behavior represented in the current specification and maintained tests.

## Current bounded reopen — refined IR19

The complete still-open implementation contract is IR19 plus its plan-closure refinement. The remaining obligations are:

1. **Plan-level cleanup action-family totality.** The canonical cleanup semantic owner must reject any policy action other than cleanup before per-action classification, including empty plans and maintenance actions. Both default and production cleanup consume this same gate. The exported single-action classifier may not positively classify cleanup work under a non-cleanup policy. A genuine empty cleanup remains a valid no-op.
2. **One coherent supported-domain/dispatch set.** Generic mutation is reached only through an explicit `CLASS_GENERIC_LEAF` handler. Residual classes fail closed. Each engine's preflight-supported classes and actual handlers are mechanically shared or explicitly checked for completeness so future class additions cannot become routing drift.
3. **Bounded structural/caller closure.** Re-census production `StorageExecutor.run` callers, classifier consumers, and direct/aliased consequential `remove_planned_outcome` calls. Every consequential generic-remover call must be explicitly generic-class dominated. Any AST/Semgrep rule must catch the classifier-present-plus-undominated-call false-negative shape and state its scan scope.
4. **Real acceptance controls.** Cover default and production wrong-family execution, empty wrong-family versus empty-cleanup liveness, standalone classifier wrong-family behavior, generic cleanup liveness, specialized-engine regressions, residual nonmutation, and the already-conforming IR18 real-owner routing cases.
5. **Exact-candidate closure.** After the final executable/test edit, run fresh focused, stage-local affected regression, complete storage core/integration, owner regressions, collection/static/structural/document checks, and all final-census-discovered affected callers on the exact executable tree; record command/node selection and pass/fail/skip counts.

Serena/Semgrep/Hypothesis remain optional evidence helpers under Protocol 5.10. Their absence does not relax the product or acceptance claim.

External DFT, long GPU production, and environment-specific HPC/shared-storage qualification remain deferred and nonblocking.

## Disposition

**Design/workplan:** Revision 30 + Revision 37 + current storage specification + IR19 + its plan-closure refinement are **CLOSED / implementation-ready**.

**Reviewed executable `7aa938d71361d2cb2ce6e370165a9a12566669f3`, tree `5fd91f30672fb7d9a2be89d6e0fdc261619509aa`: NO-PASS / reopened under refined IR19.**
