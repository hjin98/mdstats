---
kind: implementation-workplan-authority-entrypoint
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 37
status: reopened
current_authority_pointer: AUTHORITY_REVISION_37.md
current_workplan: STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_17.md
current_review_note: AUTHORITY_REVIEW_NOTE_R37_IR17.md
accepted_design: STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md
reviewed_executable_commit: 9db97f72a6ba033aa4b092edb0ece39db56f5b23
reviewed_executable_tree: a09dabfe5eb7279adb9398a98f9349c9713962a8
reviewed_branch_head: bd4b78e59f0b500ac130597943adab5e07fcad4b
reviewed_branch_tree: 683fcc2324780a6f9b3dba4aab98f949090529e4
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
- `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_17.md` — complete refined current bounded implementation/review correction after the Revision-37 candidate;
- `AUTHORITY_REVIEW_NOTE_R37_IR17.md` — current candidate verdict and plan-closure summary.

`STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_16.md` remains the Revision-37 implementation handoff that produced candidate `9db97f72...`; refined IR17 supersedes it only for work still open after implementation and plan review. Revision 31-36 review/authority files remain historical provenance.

No Revision 38 is created. The current blockers and the plan-closure refinements are necessary implementation consequences of already accepted Revision-30/37 target-identity, descriptor-capability, transition-truth, durability, close-ranking, and real-owner acceptance semantics; they do not introduce a new product model.

## Reviewed candidate

The executable candidate is `9db97f72a6ba033aa4b092edb0ece39db56f5b23`, tree `a09dabfe5eb7279adb9398a98f9349c9713962a8`.

The branch successor `bd4b78e59f0b500ac130597943adab5e07fcad4b`, tree `683fcc2324780a6f9b3dba4aab98f949090529e4`, changes only the generated storage-specification PDF, so behavioral findings remain bound to the executable tree above.

## Preserved conforming implementation

Preserve the candidate's conforming Revision-37 work unless a narrowly necessary local adjustment is required by IR17:

- exact unlink transition callbacks with no post-hoc disappearance inference or mutation-fabricating signature fallback;
- atomic-publication callbacks at `os.replace`, monotonic archive blob/manifest/catalog phases, and restore nonterminal/terminal journal mutation phases;
- hot-reclaim transition truth, restore destination transition truth, and existing dedup/maintenance mutation timing;
- final no-follow name-vs-opened-descriptor comparison before fd-relative directory `rmdir`;
- descriptor-relative/no-follow child recursion and canonical opened-descriptor mount policy;
- explicit typed common-member authority;
- one-way `ReleasedAttemptSession` invalidation and conforming P7 action/finalizer ranking;
- shared `MutationLedger`, exact per-action byte accounting, zero-credit mutation truth, complete P7 target identity, two-attempt isolation, and the frozen four cleanup outcomes.

## Current bounded reopen — refined IR17

The complete still-open contract is `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_17.md`. In summary:

1. authenticate the descriptor chain from a justified synchronization-stable or identity-bound root of trust; do not merely move a fresh absolute/multi-component open one ancestor upward;
2. propagate `PlannedAction.filesystem_identity` into every consequential generic/fully-certified target capability and keep owner root/path identities as independent constraints;
3. ordinary default single-file cleanup must compare the live no-follow target with the plan-bound identity immediately before fd-relative unlink, rather than allowing a same-name replacement to inherit the old plan;
4. after unlink or top-level `rmdir`, persist the directory-entry transition through the same authenticated parent fd before release; do not reopen `path.parent` by pathname as the authoritative durability step;
5. individually-authorized common cleanup must authenticate the opened authority root/container, preserve typed intermediate/member authority, and retain exact action-local mutation truth;
6. recursive mount-refusal close, `open_directory_nofollow`, P7 failed-session acquisition, capability invalidation, and cleanup finalization must obey one exactly-once primary/secondary close-ranking doctrine;
7. perform the bounded consequential close-family census and close all siblings in the same family rather than returning one site per review cycle;
8. material generic/common/default-file/P7 cleanup claims require real inventory/planning/authorization/production engine/`StorageExecutor.run`/settlement/audit acceptance with live low-level seams;
9. each executable stage requires focused checks plus stage-local affected regression, followed by fresh exact-candidate affected regression/integration/static/document closure after the last executable edit.

Serena/Semgrep/Hypothesis remain optional evidence helpers under Protocol 5.10. Use them where available and materially useful; their absence is nonblocking and does not waive the engineering claims.

External DFT, long GPU production, and environment-specific HPC/shared-storage qualification remain deferred and nonblocking.

## Disposition

**Design/workplan:** Revision 30 + Revision 37 + refined IR17 are **CLOSED / implementation-ready**.

**Reviewed executable `9db97f72a6ba033aa4b092edb0ece39db56f5b23`, tree `a09dabfe5eb7279adb9398a98f9349c9713962a8`: NO-PASS / reopened for bounded R37 correction under IR17.**
