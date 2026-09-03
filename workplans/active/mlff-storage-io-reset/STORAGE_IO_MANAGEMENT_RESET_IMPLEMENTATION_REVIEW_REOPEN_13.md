---
kind: implementation-review-reopen
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1-R34
parent_workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
status: reopened
reviewed_date: 2026-09-03
reviewed_authority_revision: 33
reviewed_executable_commit: 557d32b84c5934096c95ba3ea1d33ed1714d165b
reviewed_executable_tree: 349a8cb9ac7cee653733f397f196d1426f6a7726
reviewed_branch_head: acdb3f8b2a43e5c65b4a3ca2844816cf9073b8d4
reviewed_branch_tree: 3f09a96b292ca682539f2751b2e774dc715e3a44
review_verdict: NO-PASS
scope: bounded implementation and acceptance closure for mutation-time mount ownership, all-path structured mutation failure transport, canonical recursive-removal ownership, mutation-derived execution status, real-owner acceptance, authority hygiene, and exact-candidate evidence
precedence: Revision 30 remains the accepted closed final-apply design; this Revision-34 handoff supersedes Revision 33 as the complete current bounded implementation/review contract while preserving conforming Revision-31 through Revision-33 work
---

# Storage/I-O reset implementation review reopen 13 — Revision 34

## Verdict and reviewed candidate

**NO-PASS.**

The executable reviewed here is the merge candidate:

```text
commit  557d32b84c5934096c95ba3ea1d33ed1714d165b
tree    349a8cb9ac7cee653733f397f196d1426f6a7726
```

The current branch head is the generated-document-only successor:

```text
commit  acdb3f8b2a43e5c65b4a3ca2844816cf9073b8d4
tree    3f09a96b292ca682539f2751b2e774dc715e3a44
```

That successor changes only `docs/specs/training_data/mlff_storage_management_spec.pdf`; it does not change executable or test source. Functional findings therefore bind to executable tree `349a8cb...`.

Revision 30 remains the accepted closed architecture. No P1-P7 scientific/currentness semantics, owner-driven storage architecture, CampaignStore ownership, P5 proof architecture, archive/dedup/restore/control-plane design, Python `>=3.10` floor, or accepted POSIX threat boundary is reopened.

The implementation materially improves the Revision-33 baseline and several previously blocking requirements are now conforming. It is nevertheless not safe or evidentially complete enough to close. The remaining blockers are precise implementation/acceptance defects described below.

## Preserved conforming implementation and tests

Preserve these repairs unless a local change is necessary to satisfy a Revision-34 blocker:

- P7 recursive deletion now uses the action-scoped `MutationLedger`, so mutation truth is independent of positive reclaimed-byte credit and action-wide inode deduplication remains one authority.
- Zero-byte file deletion and empty-directory removal can remain `mutated=true` with exact reclaimed bytes `0`.
- Generic/common recursive deletion no longer descends into `Path(entry.path)` after classification; child traversal and mutation use descriptor-relative/no-follow primitives.
- `storage.trust` now owns the shared no-follow directory acquisition and dir-fd capability predicate used by P7 and storage recursion.
- `StorageExecutor.run` no longer mechanically labels every escaping exception partial; a genuinely empty pre-mutation interruption can be audited as refused.
- The R30 interruption/retry failpoint was repointed toward current typed removal owners rather than the dead legacy boolean call site.
- P7 complete target identity acceptance now explicitly exercises both released regular-file and released-directory targets, including each one-key-incomplete identity.
- A bounded fixture now supplies two independently authenticated released P7 attempts in one real cleanup plan/execution; the refusal variant demonstrates same-attempt invalidation while an independent attempt proceeds through its own session.
- The post-mutation byte test now derives an independent deterministic oracle from the exact removed prefix and checks exact action/audit aggregate values.
- Resealed/damaged final-authority real-executor acceptance remains present.
- The storage specification now states that mutation truth is independent of byte credit and that consequential recursive deletion is descriptor-relative/no-follow.

These conforming improvements do not waive the remaining requirements below.

## R34-1 — destructive descent still does not enforce the canonical mutation-time mount boundary

### Blocking finding

Revision 33 required every destructive directory descent to consume `storage.trust`'s canonical nested-mount policy at the mutation boundary, including same-device bind mounts and unavailable/ambiguous mount discovery.

The current generic/common walker does not do so. `storage/executor.py::_remove_tree_contents()` opens a directory child no-follow and descends into it, but never calls `crosses_mount_boundary_at()` or an engineering-equivalent canonical trust helper. A nested mount that appears after planning can therefore be traversed and deleted even though the path remains lexically inside the authorized tree.

The P7 recursion calls `crosses_mount_boundary_at(parent_fd, name, display)` before recursively opening the child. That is still weaker than the Revision-33 destructive-boundary contract: a mount can appear between the path-based mount observation and the subsequent no-follow child open. `O_NOFOLLOW` protects against symlink substitution; it does not reject an ordinary mounted directory. If the mount appears in that interval, the recursion can acquire the mounted object after the acceptance check.

This is a genuine ownership/security blocker. The frozen contract says nested-mounted/external bytes are retained, not recursively deleted.

### Required end state

Use one canonical trust-owned decision for the **actual opened child descriptor** used for destructive descent.

For every directory child in P7, generic cleanup, and fully certified common-subtree cleanup:

1. acquire the child no-follow relative to the authenticated parent descriptor;
2. compare the opened child descriptor's filesystem identity with the parent descriptor as required by the existing trust contract;
3. consult the canonical mount resolver for the child display locator so same-device bind mounts are detected and resolver unavailability/ambiguity fails toward retention;
4. only after that decision succeeds may the destructive walker enumerate descendants through the opened descriptor;
5. a crossing or ambiguous result closes the child without traversing or removing its descendants and returns/stops with `MutationLedger` truth for any earlier transition.

Prefer a minimal `storage.trust` helper that accepts the already-opened child descriptor, parent descriptor, and display locator. Do not duplicate mount policy in `executor.py` or `qualification/store.py`, and do not regress to check-by-path followed by a separate authority-bearing open.

A mount that appears after the child descriptor is already acquired need not transfer authority to that mount: mutation must continue only against the authenticated descriptor already held. A mount observed on the display locator after acquisition may conservatively force retention; it may not widen authority.

### Mandatory acceptance

Through real planning/authorization and the real `StorageExecutor.run`/cleanup owner, instrumenting only the canonical mount resolver or low-level mount-observation seam:

- generic recursive cleanup: a same-device nested mount appears after planning but before destructive descent; mounted child and sentinel survive;
- fully certified common subtree: the same mutation-time mount counterfactual; mounted child and sentinel survive;
- P7 released directory: the mount is introduced specifically between initial entry observation and child acquisition/check; external/mounted sentinel survives;
- unavailable/ambiguous mount discovery retains rather than traverses in each shared destructive mechanism that can encounter it;
- include both a no-earlier-mutation case (`refused_no_change`, `mutated=false`, zero bytes) and an earlier-known-prefix case (`partial_change_refused`, `mutated=true`, exact prefix bytes);
- preserve the existing directory-to-symlink race case, but exercise at least generic and fully certified common-subtree paths through the real cleanup executor rather than only calling the removal helper directly.

## R34-2 — post-mutation observation and descriptor-close failures can still bypass structured mutation truth

### Blocking finding

Revision 33 explicitly required every exception after the first destructive transition to reach the action boundary with the action ledger's structured partial outcome, and required descriptor cleanup not to erase a primary structured failure.

Current P7 `_remove_certified_directory()` still calls these operations without ledger-aware exception handling:

- `entry.is_symlink()`;
- `entry.is_dir(follow_symlinks=False)`;
- `entry.is_file(follow_symlinks=False)`;
- `os.close(handle)` in `finally`.

Current generic/common recursion likewise closes root and child descriptors in unguarded `finally: os.close(...)` blocks. A close failure after an earlier mutation can therefore escape as a raw `OSError`; worse, a close failure raised while a `PartialMutationError` is already active can replace the primary exception in Python's `finally` semantics, so `record_or_reraise()` never receives the mutation outcome it is supposed to record.

This is exactly the all-path failure-transport gap Revision 33 kept open.

### Required end state

- Every `DirEntry` kind/observation operation whose failure can occur after a prior destructive transition routes through the action ledger.
- Every descriptor close in a destructive recursion uses one bounded cleanup pattern that preserves the primary exception and the ledger's mutation truth.
- With no primary exception:
  - close failure before any mutation propagates/refuses without fabricated mutation;
  - close failure after mutation raises a structured partial with exact ledger bytes.
- With a primary exception already active:
  - a cleanup/close failure must not replace the primary product-significant cause or erase its structured mutation outcome;
  - preserve causal chaining or bounded secondary diagnostic detail, but the action boundary must still observe the primary mutation truth.
- Do not convert normal owner contradictions into exceptions merely for code uniformity; typed stop outcomes remain valid.

Apply the same semantics to P7, generic cleanup, and common certified-subtree recursion wherever descriptors are owned by the destructive walker.

### Mandatory acceptance

Use low-level deterministic injection below the real owner and assert real action recording, settlement/finalization, durable audit, and propagation:

1. `DirEntry` observation failure before any mutation -> no fabricated mutation/bytes;
2. the same observation failure after a zero-credit mutation -> partial/true/0;
3. fsync failure on an initially empty directory before its own `rmdir` -> no fabricated mutation;
4. fsync failure after a known removed child -> structured partial with exact bytes;
5. descriptor-close failure after a zero-credit or positive-credit mutation -> current action is recorded before propagation;
6. primary post-mutation failure plus descriptor-close failure -> primary cause and structured mutation evidence survive; cleanup failure cannot replace them.

Do not satisfy these cases by monkeypatching `_remove_tree_contents()` or `remove_released_attempt_member()` to manufacture `ledger.failure()`/`PartialMutationError` directly. The semantic owner being tested must remain real.

## R34-3 — the public boolean remover still owns a second recursive deletion implementation, and traversal ownership documentation still drifts

### Blocking finding

Revision 33 required consequential cleanup to have one canonical typed recursive deletion implementation and, if the exported `remove_durably` compatibility surface remained, required that surface to delegate/adapt to the canonical safe mechanism rather than own a second traversal algorithm.

Current `remove_durably()` still performs its own `shutil.rmtree()` recursion. Its docstring now labels it non-consequential, which is useful documentation but does not satisfy the sealed R33-6 consolidation requirement. Two exported recursive deletion implementations still exist with different trust/accounting behavior.

`storage.trust.walk_contained()` also still claims it is "the single traversal primitive every recursive storage action uses", which is false after the accepted distinction between planning/read-only traversal and descriptor-relative destructive walkers.

### Required end state

- Consequential cleanup remains exclusively on typed outcome + `MutationLedger` removal owners.
- Preserve the exported `remove_durably` API unless a separately governed compatibility decision authorizes removal.
- Implement `remove_durably` as a thin compatibility adaptation over the canonical safe typed removal mechanism rather than owning `shutil.rmtree` recursion.
- Preserve the currently documented/covered boolean compatibility semantics for ordinary removed/already-absent/non-removable cases; do not silently change caller-visible behavior merely to simplify the wrapper.
- Never swallow or coerce a `PartialMutationError`/post-mutation failure into `False`; partial mutation must still propagate truthfully.
- Retire any now-dead private recursive helper or give every retained helper one distinct, necessary responsibility.
- Update `walk_contained()` and affected durable documentation/comments to state the real ownership split: `storage.trust` owns mount policy, planning/read-only walkers own enumeration for planning, and destructive owners use descriptor-relative mutation traversal.

### Structural acceptance

Use AST/Semgrep-equivalent structure checks, not only string counts:

- no consequential cleanup call graph reaches a boolean/pathname recursive remover;
- the public `remove_durably` wrapper contains no independent recursive traversal and delegates to the canonical typed safe mechanism;
- no current destructive recursive helper cites `shutil.rmtree.avoids_symlink_attacks` as protection for unrelated code;
- `walk_contained` no longer claims to be the destructive recursion owner.

## R34-4 — exception-time execution status can still claim a partial mutation after only no-op completions

### Blocking finding

The new outer exception handler in `StorageExecutor.run()` decides:

```text
if result.mutated or result.completed:
    status = partial
```

But `record_removal()` places `already_absent` into `completed` while correctly leaving `result.mutated == false` and reclaimed bytes at zero. Therefore this real sequence is still misreported:

1. an earlier action is terminally satisfied because its target is already absent;
2. no action has actually mutated anything;
3. a later action raises before its own mutation;
4. `result.completed` is non-empty, so the execution is audited as `partial` even though `mutated=false` and nothing changed.

That contradicts the Revision-33/spec rule that interruption status follows actual mutation truth, not control-flow shape or the mere presence of terminal actions.

### Required end state

- Exception-time `partial` status is justified only by explicit mutation truth, not by a completed/no-op collection.
- Ensure every consequential engine that can mutate before a later failure sets the shared result-level mutation fact at the actual irreversible transition. Do not fix the cleanup case by simply deleting `or result.completed` unless affected archive/dedup/restore/maintenance engines are reconciled so genuine prior mutations remain visible.
- `already_absent` and other terminal no-op completions may remain in `completed_actions`; they cannot by themselves imply mutation.
- A pre-mutation failure after one or more no-op terminal actions must audit a non-partial failure/refusal with `mutated=false` and exact zero mutation bytes, then propagate the original exception.

### Mandatory acceptance and impact reconciliation

- Real executor case: first removal action is already absent, later action fails before mutation; durable audit is not `partial`, `mutated=false`, zero reclaimed bytes, no-op completed action retained, original cause propagates.
- Real executor case: a genuinely mutated earlier action followed by failure remains `partial`.
- Re-derive every engine that writes `completed`, `created_bytes`, `restored_bytes`, or performs an irreversible namespace/content transition; prove its result-level mutation fact is set early enough for exception-time settlement. Add affected archive/dedup/restore/maintenance regressions where this review broadens the impact.

## R34-5 — required real-owner acceptance remains incomplete or vacuous in several places

### Blocking finding

Green-looking focused tests do not close an owner claim when they bypass the owner or permit the target branch never to execute.

Current gaps include:

1. `test_the_default_engine_records_a_post_mutation_failure` explicitly accepts the branch where no unlink happened. R33-4 required the concrete case "engine=None: unlink succeeds, durability fails"; a test that passes when `unlinked == []` is not evidence for that claim.
2. The generic recursive real-executor test monkeypatches `_remove_tree_contents()` itself to raise `ledger.failure(...)`. That bypasses the exact observation/removal/close failure transport under review and can remain green while those production paths are defective.
3. No supplied test closes the Revision-33 real-owner fully certified common-subtree post-mutation failure case or the individually authorized common-subtree "earlier member succeeds, later member fails before its own mutation" case with production planning/authorization, real `StorageExecutor.run`, settlement/finalization, durable audit, and only low-level filesystem instrumentation.
4. The directory-to-symlink race test directly invokes `remove_durably_outcome()`; it does not prove the required real generic cleanup executor and fully certified common-subtree integration boundaries.
5. No implementation test supplies the required mutation-time nested-mount/same-device bind-mount counterfactuals; this matches the production omission in R34-1.
6. The partial two-attempt test manufactures `PartialMutationError(removed_bytes=7)` by replacing `remove_released_attempt_member()` itself. That can supplement executor propagation coverage, but it cannot establish the real P7 owner's post-mutation partial behavior or exact filesystem prefix. Preserve the separate real low-level fsync/unlink exact-byte test and add a real-owner two-attempt partial/termination case if the acceptance claim depends on P7 owner behavior.
7. The monkeypatch-liveness static guard checks only `hasattr(module, patched_name)`. An obsolete production attribute can remain defined but never be read by the path under test, so the guard does not establish the R33 requirement that the production module/path actually consumes the patched name.

### Required closure

Implement the exact R33-4 owner-boundary cases, now extended by R34-1/R34-2/R34-4:

- default engine post-unlink durability failure, guaranteed to execute the unlink;
- generic recursive post-prefix low-level observation/removal/close failure through real cleanup;
- fully certified common-subtree post-prefix durability/cleanup failure through real cleanup;
- individually authorized common-subtree earlier success + later pre-mutation failure;
- matching pre-first-mutation cases;
- real generic/common/P7 mutation-time mount cases;
- real no-op-completed-then-pre-mutation-failure status case.

Instrument filesystem calls, the deterministic mount resolver, or another seam **below** the semantic owner. Do not replace the owner function whose behavior is the acceptance claim.

Strengthen the monkeypatch-liveness guard to prove the patched production name is actually referenced/read by the governing production module/path, or pair the structural check with an invocation assertion at each acceptance-critical failpoint.

Preserve the already-good two-attempt refusal test, exact target-identity coverage for both kinds, exact byte oracle, zero-credit mutation tests, and real resealed/damaged authority cases.

## R34-6 — canonical authority and exact-candidate acceptance are not closeable on the current branch

### Canonical authority blocker

The current `workplans/active/mlff-storage-io-reset/AUTHORITY.md` contains literal unresolved Git conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`) and simultaneously carries Revision-33 and superseded Revision-32 prose. Because that file is the sole canonical navigation/status entrypoint, it is not a valid snapshot-complete authority handoff.

Revision 34 repairs the canonical entrypoint. Do not reintroduce superseded current obligations through historical authority/review files during future merges.

### Exact-candidate evidence blocker

No complete Revision-33 exact-candidate behavioral acceptance record is supplied for executable tree `349a8cb...`. Connected GitHub checks on the merge candidate contain only the documentation workflow; that is not behavioral regression/integration evidence.

After the last Revision-34 executable/test edit, record and execute the following on the exact executable tree:

### Focused current repair

- all focused R22-R34 storage/P7 namespace, proof, release/root/target identity, capability, mutation-outcome, zero-credit mutation, symlink-race, mutation-time-mount, descriptor-close, status-settlement, concurrency, and failure counterfactuals affected by this work;
- all new R34 real-owner cases above.

### Complete storage suites

```text
tests/test_mlff_storage_reset_core.py
tests/test_mlff_storage_reset_integration.py
```

### Known affected current-owner regressions

```text
tests/test_mlff_target_size_p4f_storage_docs_structure.py
tests/test_mlff_target_size_p6_destructive_closure.py
tests/test_mlff_p7_r11_repair_acceptance.py
tests/test_mlff_p7_r12_repair_acceptance.py
tests/test_mlff_p7_r13_authority_acceptance.py
tests/test_mlff_campaign_cli.py
```

Broaden this set if R34-4 mutation-flag reconciliation touches archive, dedup, restore, CampaignStore maintenance, or another engine. Final impact analysis may add tests; it may not silently omit a known affected test.

### Static/document/repository checks

- maintained-suite `pytest --collect-only -q`;
- compile/import checks for every changed Python module;
- `git diff --check` and repository-required static checks;
- structural checks for descriptor-relative destructive descent, canonical mount-policy consumption, public-remover delegation, no consequential bypass, and live failpoints;
- conflict-marker scan over current authority/workplan and changed source/test/docs;
- affected Markdown/PDF source/derivative validation.

### Final fresh exact-tree pass

After the final executable or test edit:

1. record exact executable commit and tree;
2. re-derive the affected surface from the assembled candidate;
3. run a fresh complete affected regression/integration pass on that exact tree;
4. record actual command/node selections plus pass/fail/skip counts and any justified exclusions;
5. if a later plan/docs/PDF-only successor is produced, compare it exactly against the validated executable commit and state that no executable/test source changed before reusing functional evidence.

A command that did not execute is not a pass. Whole-repository behavioral pytest remains conditional on unbounded final impact or independent repository policy. External DFT, long GPU production, and environment-specific HPC/shared-storage qualification remain deferred and nonblocking.

## Affected surface

Initial expected implementation surface:

- `mdstats/training_data/storage/trust.py` — canonical opened-descriptor mount decision and truthful traversal-ownership documentation;
- `mdstats/training_data/storage/executor.py` — mount-aware generic/common descent, ledger-aware descriptor cleanup, public remover consolidation, mutation-derived exception settlement;
- `mdstats/training_data/qualification/store.py` — opened-child mount ordering and all-path DirEntry/descriptor-close failure transport;
- `mdstats/training_data/storage/outcome.py` — only if a minimal ledger/cleanup API is required; do not add a second mutation authority;
- `mdstats/training_data/storage/commands.py` — only if real-owner routing/session closure needs a local correction;
- archive/dedup/restore/maintenance engine files only if R34-4 result-level mutation-truth census finds a genuine affected path;
- storage core/integration tests and any newly affected owner regressions;
- storage spec Markdown/PDF only where current consumer-facing wording changes;
- current authority/review files.

Final affected-surface analysis controls the actual set.

## Implementation sequence

### Stage A — trust boundary and structured failure truth

Implement R34-1 and R34-2 together. A destructive walker is not closed if it is descriptor-safe against symlinks but can cross a mount, or if it mutates safely but loses mutation truth on cleanup failure.

Run focused generic/common/P7 symlink/mount/observation/fsync/close cases and stage-local storage regression before proceeding.

### Stage B — consolidate removal ownership and terminal status

Implement R34-3 and R34-4. Reconcile all mutation-producing engines before making exception settlement depend exclusively on the explicit mutation fact.

Run focused compatibility, structural, no-op-completion, genuine-prior-mutation, archive/dedup/restore/maintenance affected regressions as indicated by the actual impact.

### Stage C — real-owner acceptance closure

Implement/repair only the tests/fixtures/failpoints needed for R34-5. Keep semantic owners real; use low-level filesystem/mount instrumentation.

### Final assembled closure

Perform R34-6 exact-candidate reconciliation and fresh affected regression/integration/static/document checks on the final executable tree.

## Routing and redesign triggers

All current blockers are implementation, acceptance, or authority-entrypoint nonconformance under the frozen Revision-30 design. Keep Revision 30 closed unless evidence proves one of these narrower premises false:

- supported public Python `>=3.10`/POSIX primitives cannot preserve descriptor-relative/no-follow recursion, canonical nested-mount refusal, and exact per-transition accounting together;
- the existing four-outcome + `MutationLedger` model cannot preserve mutation truth through required cleanup/descriptor failures;
- preserving the public boolean remover contract while delegating to the canonical safe mechanism creates a demonstrated supported-consumer compatibility conflict;
- a consequential non-cleanup engine cannot expose mutation truth early enough for correct exception settlement without changing a frozen owner contract.

If one of those is proven, reopen only that invalidated decision. Do not broaden the redesign to unrelated storage architecture or P1-P7 scientific semantics.

## Snapshot-complete current handoff

Implementation after Revision 34 reads only:

1. `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md` — broader frozen owner-driven storage architecture/non-goals;
2. `STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md` — accepted closed final-apply design;
3. `docs/specs/training_data/mlff_storage_management_spec.md` — current product contract;
4. **this file** — complete current bounded implementation/review obligations, preserving conforming prior work and superseding Revision 33 corrections where stated more precisely;
5. `AUTHORITY_REVISION_34.md` / `AUTHORITY.md` — current disposition/navigation.

Revision 31-33 implementation-review and authority files are provenance only. No current requirement depends exclusively on superseded review files, Git history, prior conversation, or local Serena/Semgrep state.

**Design/workplan disposition:** Revision 30 remains **CLOSED / implementation-ready**; bounded implementation is **REOPENED under Revision 34**.

**Reviewed executable disposition:** tree `349a8cb9ac7cee653733f397f196d1426f6a7726` is **NO-PASS** pending Revision-34 implementation and exact-candidate acceptance.
