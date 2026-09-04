---
kind: implementation-workplan-authority-entrypoint
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 37
status: reopened
current_authority_pointer: AUTHORITY_REVISION_37.md
current_workplan: STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_19.md
current_review_note: AUTHORITY_REVIEW_NOTE_R37_IR19.md
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
- `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_19.md` — complete current bounded implementation/review correction after candidate `7aa938d...`;
- `AUTHORITY_REVIEW_NOTE_R37_IR19.md` — current candidate verdict and review summary.

IR18 and earlier implementation-review artifacts are historical provenance only. The current storage specification plus Revision 30/37 preserve the closed behavior, and every still-open implementation/acceptance consequence is consolidated into IR19.

No Revision 38 is created. The open work is implementation/acceptance nonconformance under already accepted invocation-local action authority, semantic-owner routing, descriptor-capability, durability, transition-truth, close-ranking, and exact-candidate evidence semantics.

## Reviewed candidate

The executable candidate is `7aa938d71361d2cb2ce6e370165a9a12566669f3`, tree `5fd91f30672fb7d9a2be89d6e0fdc261619509aa`.

The branch successor `d035492a71652d562be7c23d0e1e77e8d5bb03c5`, tree `0b5a898308406f49cef3bc561584c12b1fc4b562`, changes only `docs/specs/training_data/mlff_storage_management_spec.pdf`; behavioral findings remain bound to the executable tree above.

## Preserved conforming implementation

Preserve candidate `7aa938d...` unless a narrowly necessary adjustment is required by IR19:

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
- ranked close/finalization behavior, one-way P7 session invalidation, shared `MutationLedger`, exact action bytes, zero-credit mutation truth, and the other conforming Revision-30 through Revision-37 behavior represented in the current specification and maintained tests.

## Current bounded reopen — IR19

The complete still-open contract is `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_19.md`. In summary:

1. the cleanup/default execution domain must be explicitly bound to the **cleanup policy action family**; a non-cleanup plan cannot spend `ACTION_REMOVE` / `ACTION_EVICT_CACHE` authority through `engine=None`, and even an empty non-cleanup plan must not settle `complete` through the default cleanup engine;
2. the generic destructive branch must be **explicitly positive** (`CLASS_GENERIC_LEAF` or equivalent exhaustive dispatch), with any residual/unexpected semantic class failing closed instead of mutating;
3. the structural negative proof must detect a classifier-present function that also contains an undominated generic-remover call; mere function-level co-occurrence of classifier/guard tokens is insufficient evidence of dominance;
4. preserve the successful IR18 common/P7/mixed-order/maintenance/cache/action-owner/owner-eligibility/unknown-authorizer/generic-liveness/production-routing behavior;
5. after the final executable/test edit, fresh exact-candidate focused, affected-regression, complete core/integration, owner-regression, collection/static/structural/document evidence is mandatory with commands and pass/fail/skip counts.

Serena/Semgrep/Hypothesis remain optional evidence helpers under Protocol 5.10. Use them where available and materially useful; their absence does not relax the product or acceptance claim.

External DFT, long GPU production, and environment-specific HPC/shared-storage qualification remain deferred and nonblocking.

## Disposition

**Design/workplan:** Revision 30 + Revision 37 + current storage specification + IR19 are **CLOSED / implementation-ready**.

**Reviewed executable `7aa938d71361d2cb2ce6e370165a9a12566669f3`, tree `5fd91f30672fb7d9a2be89d6e0fdc261619509aa`: NO-PASS / reopened under IR19.**
