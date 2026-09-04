---
kind: implementation-review-authority-note
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 37
status: reopened
current_workplan: STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_18.md
accepted_design: STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md
reviewed_executable_commit: 6391043b3641e007017d1781678c96a2b6b0d259
reviewed_executable_tree: 4055b67f2f86954b4355023cc84c9b0134a76e85
reviewed_branch_head: e76ca9cf40bc5b52b48827cb3503d4611b19de34
reviewed_branch_tree: 5ab42b2996d58804e70871ee9dc436e34a968dea
review_verdict: NO-PASS
reviewed_date: 2026-09-03
---

# Storage/I-O reset R37 implementation review note — IR18

Executable `6391043b3641e007017d1781678c96a2b6b0d259`, tree `4055b67f2f86954b4355023cc84c9b0134a76e85`, is **NO-PASS**. The later branch head `e76ca9cf40bc5b52b48827cb3503d4611b19de34` changes only the generated storage-specification PDF.

The candidate substantially closes refined IR17 and its capability-acquisition, final-target-identity, same-parent durability, opened common-owner identity, mount/close, and P7 failed-session-acquisition defects. Preserve that implementation.

Two blockers remain:

1. **Default-executor semantic-owner bypass.** `StorageExecutor.run(..., engine=None)` is an exported consequential path, but `_execute_actions()` root-authorizes each remove/evict action and then calls the generic `remove_planned_outcome()` without consulting `snapshot.view()`, `exact_authorizer`, subtree coverage, typed member/refusal authority, owner root/path identities, or P7 live-session semantics. `build_cleanup_plan()` can legitimately contain those owner-specific actions. Omitting the specialized engine can therefore widen a valid plan from owner-authorized members to generic recursive deletion. IR18 requires a fail-closed default-engine domain/canonical dispatch and real common/P7/mixed-plan counterfactuals before any mutation.
2. **Exact-candidate evidence is absent.** GitHub records only the successful `docs` check for the executable commit and no combined commit statuses. No repository-accessible execution record binds the required IR17/R37 focused, complete core/integration, owner regression, collection/static, and structural closure to the final executable tree. Source/test existence is not execution evidence.

The complete current bounded repair/acceptance contract is `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_18.md`.

No Revision 38 is created. The default-executor defect violates the already-frozen rule that storage consumes semantic-owner authority rather than replacing it with path/root authority; the evidence defect is ordinary implementation closure. Revision 30 and Revision 37 remain the accepted design/workplan authority.

External DFT, long GPU production, and environment-specific HPC/shared-storage qualification remain deferred and nonblocking.
