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

# Storage/I-O reset R37 implementation review note — corrected IR18 plan closure

Executable `6391043b3641e007017d1781678c96a2b6b0d259`, tree `4055b67f2f86954b4355023cc84c9b0134a76e85`, remains **NO-PASS**. The later branch head `e76ca9cf40bc5b52b48827cb3503d4611b19de34` changes only the generated storage-specification PDF.

The candidate substantially closes refined IR17 and its capability-acquisition, final-target-identity, same-parent durability, opened common-owner identity, mount/close, and P7 failed-session-acquisition defects. Preserve that implementation.

A second plan-level closure review found that the first IR18 handoff still left the semantic-domain repair too permissive. It named specific unsafe classes but delegated an open-ended eligibility predicate; it also focused the bypass on `engine=None` even though production cleanup maintained a separate negative-fallthrough semantic definition. That could recreate the same owner-authority drift later.

Corrected IR18 therefore freezes the following bounded closure:

1. **One canonical cleanup semantic classifier/dispatch.** Default and production cleanup consume the same positive classification. Unknown/unmatched shapes never become generic by falling through previous branches.
2. **Fresh synchronized classification.** Classification is derived from the fresh post-`revalidate_plan()` snapshot while the storage lease and owner activity/publication barriers are held.
3. **Exact action-owner binding.** Cleanup actions must bind to the matching current `OwnerArtifactView.path` and current action-kind eligibility. A valid `artifact_id`, physical path authorization, and `PlannedAction.filesystem_identity` cannot camouflage a different target or an owner-ineligible remove/evict action.
4. **Positive default domain.** `engine=None` may destructively execute only a positively classified generic leaf. P7/exact-authorizer, common/owner-scoped directories, maintenance, cache directories, unknown/special nodes, and malformed/ambiguous actions fail closed.
5. **Whole-plan preflight.** Wrong-engine/domain incompatibility is discovered before the first mutation regardless of action order; a generic prefix may not be spent before a later unsupported action is noticed.
6. **Acceptance closes sibling classes.** Real common/P7 bypass tests, both mixed-plan orders, maintenance, cache-directory, mismatched action/view binding, owner-ineligible action, unknown exact authorizer, generic-leaf liveness, production routing, and structural absence of residual generic fallthrough are required. Guards must prove they fired rather than passing accidentally through stale-plan rejection.
7. **Snapshot-complete handoff.** Earlier IR17 is provenance only. Current specification + Revision 30/37 + corrected IR18 contain all still-binding product and open implementation/acceptance semantics.

The other blocker remains unchanged: exact-candidate behavioral acceptance must execute after the last executable/test edit and be bound to the final executable tree. Source/test existence is not execution evidence.

No Revision 38 is created. These refinements strengthen implementation closure under already-frozen owner-driven storage semantics and do not change product architecture.

External DFT, long GPU production, and environment-specific HPC/shared-storage qualification remain deferred and nonblocking.
