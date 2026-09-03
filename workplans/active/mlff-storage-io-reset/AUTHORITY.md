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
- `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_17.md` — complete current bounded implementation/review correction after the Revision-37 candidate;
- `AUTHORITY_REVIEW_NOTE_R37_IR17.md` — current candidate verdict summary.

`STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_16.md` remains the Revision-37 implementation handoff that produced candidate `9db97f72...`; IR17 supersedes it only for work still open after review. Revision 31-36 review/authority files remain historical provenance.

No Revision 38 is created: the current blockers are implementation and acceptance nonconformance under requirements already explicit in Revision 37, not new product semantics.

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

## Current bounded reopen — IR17

The complete still-open contract is `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_17.md`. In summary:

1. generic/fully-certified recursive cleanup must authenticate the actual opened root against the plan-bound target identity before traversal and may not treat a fresh absolute/multi-component parent open as an authenticated capability;
2. individually-authorized common cleanup must move authority-root/container identity proof onto the actual opened descriptors, eliminating the precheck-then-reopen window;
3. recursive mount-refusal close must route through the canonical primary/secondary close ranking so an earlier `MutationLedger` prefix cannot be lost;
4. `open_directory_nofollow()` must never attempt to close the same acquired descriptor twice when cleanup close itself fails;
5. perform a bounded close-family census over consequential generic/common/P7 acquisition and finalization paths;
6. replace helper/manual-result proxy acceptance for material generic/common R37 claims with real inventory/planning/`StorageExecutor.run`/audit counterfactuals;
7. after the last executable/test edit, run and record the complete exact-candidate affected regression/integration/static/document evidence required by IR17/R37.

Serena/Semgrep/Hypothesis remain optional evidence helpers under Protocol 5.10. Use them where available and materially useful; their absence is nonblocking and does not waive the engineering claims.

External DFT, long GPU production, and environment-specific HPC/shared-storage qualification remain deferred and nonblocking.

## Disposition

**Design/workplan:** Revision 30 + Revision 37 remain **CLOSED / implementation-ready**.

**Reviewed executable `9db97f72a6ba033aa4b092edb0ece39db56f5b23`, tree `a09dabfe5eb7279adb9398a98f9349c9713962a8`: NO-PASS / reopened for bounded R37 correction under IR17.**
