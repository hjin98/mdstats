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

Implementation uses:

- `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md` — broader frozen owner-driven storage architecture and non-goals;
- `STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md` — accepted closed final-apply design and protected trust/outcome semantics;
- `docs/specs/training_data/mlff_storage_management_spec.md` — current storage product contract;
- `AUTHORITY_REVISION_37.md` — accepted Revision-37 bounded design/workplan authority;
- `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_18.md` — complete current bounded implementation/review correction after candidate `6391043b...`;
- `AUTHORITY_REVIEW_NOTE_R37_IR18.md` — current candidate verdict and review summary.

Refined IR17 remains the implementation handoff that produced candidate `6391043b...`; IR18 supersedes it only for work still open after this review. Earlier Revision-31 through Revision-37 review artifacts remain historical provenance.

No Revision 38 is created. The open work is implementation/acceptance nonconformance under already accepted owner-authority, descriptor-capability, typed-subtree, P7 live-session, durability, and exact-candidate evidence semantics.

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
- shared `MutationLedger`, exact action bytes, zero-credit mutation truth, complete P7 target identity, two-attempt isolation, and all other conforming Revision-30 through Revision-37 behavior.

## Current bounded reopen — IR18

The complete still-open contract is `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_18.md`. In summary:

1. `StorageExecutor.run(..., engine=None)` must have a fail-closed semantic domain. A valid plan requiring P7 `exact_authorizer` or common typed/subtree/owner-identity semantics may never fall through to generic recursive deletion because the caller omitted the specialized engine.
2. Default-engine suitability must be resolved before the first mutation. A mixed plan containing an unsupported owner-specific action must not partially execute a convenient generic subset first.
3. Preserve the useful plan-bound default generic leaf path, and preserve the production cleanup engine's P7/common/generic routing rather than duplicating a second full semantic dispatcher unnecessarily.
4. Add real common-container, P7 exact-authorizer, mixed-plan, and generic-leaf `StorageExecutor.run(engine=None)` acceptance plus structural absence evidence for the bypass.
5. After the final executable/test edit, supply fresh exact-candidate focused, affected-regression, complete core/integration, owner-regression, collection/static/structural/document evidence with commands and pass/fail/skip counts.

Serena/Semgrep/Hypothesis remain optional evidence helpers under Protocol 5.10. Use them where available and materially useful; their absence does not relax the product or acceptance claim.

External DFT, long GPU production, and environment-specific HPC/shared-storage qualification remain deferred and nonblocking.

## Disposition

**Design/workplan:** Revision 30 + Revision 37 + refined IR17 + IR18 are **CLOSED / implementation-ready**.

**Reviewed executable `6391043b3641e007017d1781678c96a2b6b0d259`, tree `4055b67f2f86954b4355023cc84c9b0134a76e85`: NO-PASS / reopened under IR18.**
