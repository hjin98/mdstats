---
kind: implementation-workplan-authority-entrypoint
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 37
status: reopened
current_authority_pointer: AUTHORITY_REVISION_37.md
current_workplan: STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_18.md
current_review_note: AUTHORITY_REVIEW_NOTE_R37_IR18.md
accepted_design: STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md
reviewed_executable_commit: 6391043b3641e007017d1781678c96a2b6b0d259
reviewed_executable_tree: 4055b67f2f86954b4355023cc84c9b0134a76e85
reviewed_branch_head: e76ca9cf40bc5b52b48827cb3503d4611b19de34
reviewed_branch_tree: 5ab42b2996d58804e70871ee9dc436e34a968dea
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
- `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_18.md` — complete current bounded implementation/review correction after candidate `6391043b...`;
- `AUTHORITY_REVIEW_NOTE_R37_IR18.md` — current candidate verdict and plan-closure summary.

Earlier IR17 and Revision-31 through Revision-37 implementation-review artifacts are historical provenance only. They may identify useful maintained regression nodes, but no still-open requirement depends on loading them: current product semantics live in the current storage specification / accepted Revision-30/37 authority, and every still-open implementation/acceptance consequence is consolidated into IR18.

No Revision 38 is created. The open work is implementation/acceptance nonconformance under already accepted owner-authority, descriptor-capability, typed-subtree, P7 live-session, durability, close-ranking, and exact-candidate evidence semantics.

## Reviewed candidate

The executable candidate is `6391043b3641e007017d1781678c96a2b6b0d259`, tree `4055b67f2f86954b4355023cc84c9b0134a76e85`.

The branch successor `e76ca9cf40bc5b52b48827cb3503d4611b19de34`, tree `5ab42b2996d58804e70871ee9dc436e34a968dea`, changes only `docs/specs/training_data/mlff_storage_management_spec.pdf`; behavioral findings remain bound to the executable tree above.

## Preserved conforming implementation

Preserve candidate `6391043b...` unless a narrowly necessary adjustment is required by IR18:

- anchored componentwise descriptor acquisition and plan-bound opened-target identity;
- default single-file final identity, fd-relative unlink, and same-parent durability;
- common opened authority/container identities, typed members, and action-wide mutation truth;
- final no-follow name-vs-opened-descriptor comparison before fd-relative `rmdir` and same-parent fsync;
- exact unlink/publication transition callbacks and archive/restore-journal transition phases;
- ranked recursive mount-refusal close, exactly-once no-follow acquisition cleanup, failed P7 session-acquisition ranking, and one-way session invalidation;
- shared `MutationLedger`, exact action bytes, zero-credit mutation truth, complete P7 target identity, two-attempt isolation, and all other conforming Revision-30 through Revision-37 behavior represented in the current specification and maintained tests.

## Current bounded reopen — corrected IR18

The complete still-open contract is `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_18.md`. Its plan-closure refinements are material:

1. cleanup semantic routing must have **one canonical classifier/dispatch owner** consumed by both production cleanup and `StorageExecutor.run(..., engine=None)`; duplicated negative fallthrough is not acceptable closure;
2. classification uses the **fresh post-revalidation snapshot while the storage lease and owner barriers remain held**;
3. every cleanup action is positively bound to the matching current owner view and action-kind eligibility; an `artifact_id` cannot camouflage a different path or ineligible action;
4. the default engine has a positive **generic-leaf-only** destructive domain; P7/exact-authorizer, owner-scoped directory/container, maintenance/specialized, cache-directory, unknown/special, and ambiguous/malformed shapes fail closed;
5. wrong-engine/domain incompatibility is preflighted across the **entire plan before any mutation**, independent of action order;
6. production cleanup consumes the same classification and retains its existing P7/common/maintenance/generic implementations rather than maintaining a second semantic definition;
7. acceptance explicitly covers common/P7 bypass, both mixed-plan orders, maintenance, cache-directory, mismatched action/view binding, owner-ineligible actions, unknown exact authorizer, generic-leaf liveness, production routing, and structural absence of residual generic fallthrough;
8. after the final executable/test edit, fresh exact-candidate focused, affected-regression, complete core/integration, owner-regression, collection/static/structural/document evidence is mandatory with commands and pass/fail/skip counts.

Serena/Semgrep/Hypothesis remain optional evidence helpers under Protocol 5.10. Use them where available and materially useful; their absence does not relax the product or acceptance claim.

External DFT, long GPU production, and environment-specific HPC/shared-storage qualification remain deferred and nonblocking.

## Disposition

**Design/workplan:** Revision 30 + Revision 37 + current storage specification + corrected IR18 are **CLOSED / implementation-ready**.

**Reviewed executable `6391043b3641e007017d1781678c96a2b6b0d259`, tree `4055b67f2f86954b4355023cc84c9b0134a76e85`: NO-PASS / reopened under IR18.**
