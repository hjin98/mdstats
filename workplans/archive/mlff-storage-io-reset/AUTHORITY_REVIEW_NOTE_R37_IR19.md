---
kind: implementation-review-authority-note
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 37
status: reopened
current_workplan: STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_19.md
accepted_design: STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md
reviewed_executable_commit: 7aa938d71361d2cb2ce6e370165a9a12566669f3
reviewed_executable_tree: 5fd91f30672fb7d9a2be89d6e0fdc261619509aa
reviewed_branch_head: d035492a71652d562be7c23d0e1e77e8d5bb03c5
reviewed_branch_tree: 0b5a898308406f49cef3bc561584c12b1fc4b562
review_verdict: NO-PASS
reviewed_date: 2026-09-03
---

# Storage/I-O reset R37 implementation review note — IR19

Executable `7aa938d71361d2cb2ce6e370165a9a12566669f3`, tree `5fd91f30672fb7d9a2be89d6e0fdc261619509aa`, is **NO-PASS**. The later branch head `d035492a71652d562be7c23d0e1e77e8d5bb03c5` changes only the generated storage specification PDF, so behavioral findings remain bound to the executable tree.

Candidate `7aa938d...` materially closes the main corrected-IR18 defect: cleanup now has one canonical positive semantic classifier; default execution is restricted to generic leaves; classification occurs from the fresh post-revalidation snapshot under the storage/owner barriers; action paths are rebound to current owner views and current remove/evict eligibility; unknown exact authorizers fail closed; whole-plan wrong-domain preflight occurs before mutation; and production cleanup consumes the same semantic classes for P7, owner-subtree, maintenance, and generic routing. Preserve that work and the previously conforming Revision-30/37 descriptor, durability, transition-truth, close-ranking, accounting, and P7 session behavior.

Three blocking closure points remain:

1. **Cleanup engine selection is not bound to the invocation action family.** The shared cleanup classifier accepts `ACTION_REMOVE` / `ACTION_EVICT_CACHE` from owner semantics but does not require `policy.action == cleanup`. `revalidate_plan()` proves only that executor policy and plan policy agree with each other. A malformed archive/dedup plan can therefore contain an otherwise legitimate cleanup leaf and reach `StorageExecutor.run(..., engine=None)` as generic cleanup; an empty non-cleanup plan can pass the empty default-domain preflight and settle as `complete`. The default cleanup engine must reject non-cleanup policy/action families before any transition, including empty plans.
2. **The generic destructive dispatch still exists as residual negative fallthrough, and the structural proof is too weak.** Production cleanup handles maintenance/exact/subtree classes and then treats the residual branch as `CLASS_GENERIC_LEAF`. The current AST check proves only that a function contains some classifier/guard somewhere; it would miss an additional undominated generic-remover call in the same function. Generic mutation must be reached through an explicit positive generic-leaf branch (or equivalent exhaustive dispatch), with residual classes failing closed, and the negative structural rule must be live against a classifier-present-but-undominated known-bad construct.
3. **Exact-candidate functional closure is still absent.** GitHub exposes only the successful `docs` check for executable `7aa938d...` and no behavioral commit statuses. Source/test presence is not evidence that the required focused, affected-regression, complete core/integration, owner-regression, collection/static, and structural checks executed on the exact tree. The final repaired tree must carry or supply those command outputs and pass/fail/skip counts before closure.

The complete current bounded repair/acceptance contract is `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_19.md`.

No Revision 38 is created. These are implementation/acceptance consequences of the already-frozen invocation-local action authority and canonical semantic-owner design, not a new storage architecture. Revision 30 and Revision 37 remain accepted.

External DFT, long GPU production, and environment-specific HPC/shared-storage qualification remain deferred and nonblocking.
