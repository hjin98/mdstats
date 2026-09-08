---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 36
status: reopened
current_workplan: STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_15.md
accepted_design: STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md
reviewed_executable_commit: 84a2df7779884fa3c0590588366bd139dd6241de
reviewed_executable_tree: 9e57b388a5826ea900edb674decc605605b51fe2
reviewed_branch_head: db0d603edf2e129c9f7a90e79c47ee5fcc11e25a
reviewed_branch_tree: 531731982b980c453fcb02a77d7ec56e741c39e2
review_verdict: NO-PASS
reviewed_date: 2026-09-03
---

# Storage/I-O reset authority — Revision 36

## Verdict

The Revision-35 implementation at executable commit `84a2df7779884fa3c0590588366bd139dd6241de`, tree `9e57b388a5826ea900edb674decc605605b51fe2`, is **NO-PASS**.

The current branch successor `db0d603edf2e129c9f7a90e79c47ee5fcc11e25a` changes only the generated storage-specification PDF, so behavioral findings remain bound to the executable tree above.

Revision 30 remains the accepted closed final-apply design. This review does not reopen P1-P7 scientific/currentness semantics, owner architecture, archive/dedup/restore product design, CampaignStore authority, the four cleanup outcomes, Python `>=3.10`, or the accepted POSIX threat boundary.

## Current bounded implementation authority

The complete current repair and acceptance contract is:

`STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_15.md`

It supersedes Revision-35's implementation-review handoff for all still-open implementation work while preserving conforming Revision-35 changes.

## Blocking findings

### 1. Mutation transitions remain inexact

- `durable_unlink()` can invoke `on_unlinked` when `missing_ok=True` and no unlink occurred.
- generic single-file helpers still infer mutation from later pathname absence after an unlink failure.
- consequential callers retain a `TypeError` fallback that can call the mutation callback without proof that the current unlink occurred.
- archive creation records `result.mutated` only after `BOUNDARY_AFTER_BLOB`; failures after atomic blob replacement but before return/failpoint can therefore persist archive bytes while the executor audits a pre-mutation refusal.

Revision 36 requires mutation truth at the actual unlink/atomic-publication transition and forbids post-hoc namespace inference.

### 2. Destructive descriptor authority is dropped before some final syscalls

Generic, common, and P7 recursive paths authenticate opened directories but close/drop that identity before later `rmdir` name lookups. Individually-authorized common cleanup also reopens the container by absolute pathname and does not apply opened-descriptor mount trust to each intermediate directory.

Revision 36 requires the authenticated parent/child descriptors and a final no-follow name-vs-opened-descriptor identity comparison through each fd-relative `rmdir`, plus opened-descriptor mount verification for common-member descent. Missing typed common-member authority may not default to regular-file permission.

### 3. Descriptor/session close semantics remain unsafe

- P7 recursion returns from inside a `try` whose close is in `else`, so normal contradiction/stop branches can leak the opened directory fd.
- `ReleasedAttemptSession.invalidate()` catches its own close failure and tests `sys.exc_info()` inside that handler, which necessarily sees the caught close exception and therefore suppresses close-only failure.
- common nested descriptor closes and mount-refusal closes can be swallowed or replace structured mutation truth.

Revision 36 requires one-way capability invalidation, leak-free all-path descriptor closure, preservation of a primary mutation failure over secondary close failure, and observable close-only failures without fabricated mutation.

### 4. Revision-35 acceptance does not prove the material owner claims

Several new R35 tests call helpers directly or construct `StorageExecutionResult` by hand. The archive mutation test does not execute archive creation/reclamation; the mount test only calls the trust helper; the no-unlink test begins with an absent path rather than the required observed-then-concurrently-disappeared counterfactual; the session test does not cross the real P7 cleanup/executor boundary; the integration suite was not changed by `store-A11`.

The patch-liveness guard still checks only `hasattr(module, name)`, although Revision 35 explicitly required proof that the production path actually reads/calls the injected seam.

Revision 36 requires real planner/owner/`StorageExecutor`/audit acceptance with only low-level filesystem/trust/failpoint injection.

### 5. Exact-candidate behavioral evidence is absent

GitHub records only the successful `docs` check on executable commit `84a2df...`; no behavioral check establishes the mandatory affected regression/integration suite. Final closure requires fresh exact-tree functional evidence after the last executable edit.

## Preserved conforming work

Preserve the explicit executor `mutated` exceptional-status rule, shared `MutationLedger`, opened-descriptor trust helper, no-follow recursive child acquisition, `AuthorizedPath` typed handoff, restore/dedup/maintenance immediate transition marks, thin public `remove_durably` wrapper, truthful planning-vs-destructive traversal documentation, complete P7 target identity, exact byte accounting, two-attempt isolation, and all other conforming Revision-30 through Revision-35 behavior.

## Tooling

Serena/Semgrep are optional evidence helpers under this protocol/workplan. They were not available in the review runtime; direct source/reference/AST-style inspection was used instead. Their absence is nonblocking and may not be used to waive any structural or behavioral acceptance requirement.

## Disposition

**Design/workplan:** **CLOSED / implementation-ready under Revision 30 plus the bounded Revision-36 correction.**

**Implementation:** **NO-PASS / reopened under Revision 36.**

External DFT, long GPU production, and environment-specific HPC/shared-storage qualification remain deferred and nonblocking.
