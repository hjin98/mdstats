---
kind: implementation-review-reopen
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1-R36
parent_workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
status: reopened
reviewed_date: 2026-09-03
reviewed_authority_revision: 35
reviewed_plan_commit: bdc62d2512b9fb27c5177c98a5d416017370c95a
reviewed_executable_commit: 84a2df7779884fa3c0590588366bd139dd6241de
reviewed_executable_tree: 9e57b388a5826ea900edb674decc605605b51fe2
reviewed_branch_head: db0d603edf2e129c9f7a90e79c47ee5fcc11e25a
reviewed_branch_tree: 531731982b980c453fcb02a77d7ec56e741c39e2
review_verdict: NO-PASS
scope: snapshot-complete bounded implementation and acceptance closure for exact mutation transitions, continuous descriptor/mount authority through final destructive syscalls, typed common-member authority, all-path descriptor/session close semantics, real-owner counterfactual acceptance, and exact-candidate evidence
precedence: Revision 30 remains the accepted closed final-apply design; conforming implementation through Revision 35 is preserved; this Revision-36 handoff supersedes Revision 35 as the complete current bounded implementation/review contract
---

# Storage/I-O reset implementation review reopen 15 — Revision 36

## Disposition

**Revision-35 implementation review: NO-PASS.**

The implementation candidate is:

```text
commit  84a2df7779884fa3c0590588366bd139dd6241de  (store-A11)
tree    9e57b388a5826ea900edb674decc605605b51fe2
```

The branch successor:

```text
commit  db0d603edf2e129c9f7a90e79c47ee5fcc11e25a
tree    531731982b980c453fcb02a77d7ec56e741c39e2
```

changes only `docs/specs/training_data/mlff_storage_management_spec.pdf`. Behavioral findings therefore bind to executable tree `9e57b388...`; the PDF-only successor does not alter them.

Revision 35 produced material conforming work, but independent source/acceptance review found remaining defects at exactly the authority and transition boundaries Revision 35 was meant to close. These are blocking because they can make the durable audit claim that nothing changed after a persistent mutation, delete a replacement directory through a stale name after descriptor authentication, traverse an individually-authorized common path without mutation-time mount authority, or silently lose/replace descriptor/session failure truth. The new R35 tests also leave these paths green because several test helpers or hand-constructed results rather than the required real semantic owners.

Revision 30 remains the accepted closed architecture. Do **not** reopen P1-P7 science/currentness, CampaignStore ownership, P5/P7 proof architecture, archive/dedup/restore/control-plane product design, the four cleanup outcomes, Python `>=3.10`, or the accepted descriptor-pinned POSIX threat boundary. Repair only the bounded surfaces below.

## Evidence and tooling disposition

This review reconciled the candidate against:

- `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md`;
- `STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md`;
- `AUTHORITY_REVISION_35.md` and its complete bounded workplan;
- `docs/specs/training_data/mlff_storage_management_spec.md`;
- the changed storage/qualification owners and the core/integration acceptance suites.

Serena/Semgrep were considered as optional Protocol-5.10 evidence tools, but no local repository/tool runtime exposing those executables was available in the review environment. Equivalent direct source/reference/AST-style structural inspection was therefore used, as Revision 35 explicitly permits. Tool absence is not a product blocker and does not weaken the findings below.

GitHub records only the `docs` check on executable commit `84a2df...`; there is no recorded behavioral check establishing the R35 exact-candidate affected regression/integration pass. That missing evidence is blocking independently under R36-5, but the source defects below mean a behavioral run alone could not close the review anyway.

## Preserved conforming Revision-35 implementation

Preserve these gains unless a local adjustment is necessary to implement a blocker below:

- `StorageExecutor.run` now settles exceptional execution status from explicit `result.mutated`, not `result.completed`.
- `verify_opened_directory_trust(parent_fd, child_fd, display)` centralizes the opened-descriptor device/mount-table decision and fails closed when mount discovery is unavailable.
- generic/P7 recursive child acquisition is no-follow and descriptor-relative, with opened-descriptor trust verification in the main recursive path.
- `AuthorizedPath` / certified-node kind information carries typed member authority out of inventory for common-subtree cleanup.
- restore marks execution mutation immediately after a successful destination-directory creation or member `os.replace`, before later chmod/fsync work.
- dedup marks mutation and current-action evidence immediately after alias `os.replace`, before its durability failpoint.
- maintenance marks positive event-prune and successful `VACUUM` mutation explicitly; zero-prune remains nonmutating.
- the public `remove_durably(path) -> bool` compatibility surface is now a thin adaptation over the typed remover and no longer owns a second `shutil.rmtree` algorithm.
- `walk_contained()` documentation now describes read-only/planning traversal rather than claiming to be the universal destructive walker.
- the storage specification states explicit mutation-based exceptional terminality and opened-descriptor mount trust.
- complete P7 target identity, shared cleanup `MutationLedger`, zero-credit mutation truth, exact per-action byte accounting, two-attempt authority isolation, resealed/damaged-authority coverage, and the other conforming Revision-30 through Revision-35 behavior remain binding.

These preserved changes do not waive the defects below.

# R36-1 — mutation truth must be established at the actual persistent transition, with no inference escape hatch

## R36-1A — `durable_unlink` callback semantics are not yet exact

Current `storage/durability.py::durable_unlink()` documents `on_unlinked` as a callback invoked immediately after the unlink syscall succeeds. The implementation nevertheless invokes it after a `FileNotFoundError` when `missing_ok=True`, and the pathname variant invokes it after `Path.unlink(missing_ok=True)` even when there was nothing to unlink.

A transition callback that can fire without the transition is not an authority for mutation truth.

### Required end state

- `on_unlinked` executes **if and only if this invocation's unlink syscall actually succeeded**.
- Missing target with `missing_ok=True` returns without callback and without mutation/byte attribution.
- Missing target with `missing_ok=False` raises without callback.
- The primitive may return an explicit `did_unlink: bool` or retain the callback interface, but only one source of transition truth may exist.
- Consequential callers must not catch `TypeError` and fall back to an older `durable_unlink(path)` signature followed by manually invoking the mutation callback. That compatibility escape hatch destroys the very transition guarantee R35 introduced. Update tests to inject below the real current primitive (`os.unlink`, fsync, or an explicit failpoint), not by replacing it with a signature-incompatible semantic substitute.

Apply this to generic single-file cleanup, common-member cleanup, archive hot reclamation, and any other consequential current caller.

## R36-1B — forbidden post-hoc disappearance inference remains in cleanup

Current `remove_durably_outcome()` and `_remove_tree_or_file_tracked()` still contain the equivalent of:

```python
not unlinked and not path.exists() and not path.is_symlink()
```

inside failure handling and may then credit the previously observed object's bytes.

That is the exact R35-2A counterexample: the target can disappear because another actor removed/replaced the name after this execution's unlink failed. A later absence cannot prove this execution caused it.

### Required end state

- Remove every post-failure pathname-existence inference used as proof of this execution's deletion.
- Mutation/bytes come only from the transition-aware unlink callback/result recorded immediately after successful unlink.
- If unlink itself fails before that transition, propagate/refuse with `mutated=false` for the current action regardless of the later pathname state.
- If unlink succeeds and parent durability fails, carry a structured partial outcome with exact substantiated bytes even if a replacement now occupies the pathname.

## R36-1C — archive publication still has an unrecorded persistent window

Current archive creation performs:

```text
_publish_archive_blob(...)
 -> BOUNDARY_AFTER_BLOB failpoint
 -> seal manifest
 -> result.mutated = True
```

`_publish_archive_blob()` delegates to `durable_publish_bytes()`, which performs `os.replace(staging, target)` before parent fsync/authentication. Therefore two blocking windows exist:

1. `_publish_archive_blob()` returns successfully and `BOUNDARY_AFTER_BLOB` raises before `result.mutated` is set;
2. `durable_publish_bytes()` successfully replaces the blob and then raises during parent fsync or published-byte authentication, so `_publish_archive_blob()` never returns and the archive engine never learns that persistent state changed.

Both violate the R35/R30 rule that execution mutation is established at the first persistent transition before any later failure can escape.

### Required end state

- The durable publication owner exposes transition truth at the atomic publish (`os.replace`) boundary, e.g. an `on_published` callback/typed result invoked immediately after the replace and before parent fsync/readback, or an engineering-equivalent local sequence.
- Archive creation sets `result.mutated = True` and records at least archive identity + `publication_phase="blob_published"` at that transition, **before** `BOUNDARY_AFTER_BLOB` or any later durability/authentication failure can escape.
- A failure before atomic publication does not fabricate mutation.
- `created_bytes` is credited only when its amount is substantiated; mutation truth must not depend on whether byte-size authentication completed.
- Manifest/catalog publication phase evidence must not knowingly lag a successfully completed atomic publication merely because the helper later failed during durability/readback. If the existing publication helper can raise after replacing those records, carry the latest known publication phase through the same transition-aware mechanism or equivalent evidence.
- Hot reclamation continues to use exact unlink transition truth from R36-1A/B.

### Mandatory R36-1 acceptance

Through real engines and `StorageExecutor.run`/audit unless the assertion is specifically about the low-level primitive:

1. `durable_unlink(..., missing_ok=True, on_unlinked=...)` on an absent target does not fire the callback.
2. A file exists and is observed; this execution's unlink fails, another actor removes the name before failure handling, and no mutation/bytes are attributed to this execution.
3. Unlink succeeds, a replacement appears, parent durability fails: current action is exact partial mutation and replacement survives.
4. Archive blob atomic publication succeeds, then `BOUNDARY_AFTER_BLOB` raises: execution/audit are partial+mutated with blob publication evidence.
5. Archive blob `os.replace` succeeds, then publication parent-fsync/readback fails **inside** the durability helper: execution/audit are still partial+mutated; the symmetric pre-replace failure is refused/nonmutating.
6. Archive hot unlink followed by durability failure carries exact action evidence; missing/failed unlink does not fabricate it.

# R36-2 — descriptor/mount authority must remain continuous through the final destructive syscall

Revision 35 correctly introduced opened-descriptor trust, but the implementation drops that authority before some final `rmdir` operations and bypasses it in the individually-authorized common path.

## R36-2A — generic/common closed-subtree `rmdir` still spends a fresh pathname

Current `_remove_tree_tracked()`:

- opens the parent and root descriptors;
- verifies the opened root;
- closes the parent descriptor;
- empties/closes the root descriptor;
- finally calls `os.rmdir(root)` by pathname.

Nested recursion similarly closes `child_handle` before `os.rmdir(entry.name, dir_fd=handle)`. P7 `_remove_certified_directory()` closes its child/root handle before `os.rmdir(name, dir_fd=parent_fd)`.

An opened descriptor authenticates the object it references, not a later directory entry lookup. If the name is substituted after the opened directory was authenticated, a later fresh-name `rmdir` can delete a replacement empty directory that never carried the authority of the opened descriptor. Revision 30 explicitly allows only the irreducible race **after an immediate final identity check**, not a design that discards identity and later spends the pathname.

### Required end state

For every directory removal in generic cleanup, fully certified common cleanup, and P7 recursion:

1. retain the authenticated parent descriptor and opened child/root descriptor through the final directory-removal boundary;
2. immediately before `rmdir`, no-follow stat the child name relative to the authenticated parent and compare `(kind, device, inode)` with the still-open authenticated child descriptor (or its descriptor-derived identity retained without closing it);
3. kind/identity mismatch, disappearance, mount ambiguity, or replacement stops/refuses according to the running action ledger; it never transfers authority to the replacement;
4. execute `os.rmdir(name, dir_fd=authenticated_parent_fd)` only after that final comparison;
5. only the irreducible race after this immediate comparison and before the kernel `rmdir` is outside the accepted POSIX guarantee;
6. close descriptors under R36-3 after/around the final transition without replacing primary mutation truth.

Do not use absolute `os.rmdir(root)` for a consequential recursive root once descriptor authority exists.

## R36-2B — individually-authorized common-subtree descent still re-enters pathname/mount authority

Current `remove_certified_subtree(... refusals=...)` first `lstat`s the authority root/container, then reopens the container with `open_directory_nofollow(str(path))` by absolute pathname. It does not verify that newly opened container against the authenticated parent/mount decision. When an individually-authorized member is nested, each intermediate directory is opened no-follow, but those opened directory descriptors are not passed through `verify_opened_directory_trust()`.

This leaves two gaps:

- check-by-path -> fresh absolute open can enter a replacement container;
- a nested same-device bind mount can be opened as an ordinary directory and then supply an externally-owned same-relative-name file to the final unlink.

### Required end state

- Open/authenticate the common container relative to an authenticated parent descriptor, compare it to the plan/owner root identity, and apply `verify_opened_directory_trust()` to the actual opened container before any member mutation.
- Every intermediate directory descriptor used to reach an individually-authorized nested member is no-follow **and** evaluated by the canonical opened-descriptor mount decision before descent.
- Final member observation remains no-follow and typed; mutation remains relative to the authenticated parent descriptor.
- Do not default missing typed authority to `"file"`. A bare path without owner-certified kind evidence is insufficient and must be retained/refused. `AuthorizedPath` or explicit `member_authorities` may carry the type; absence of both grants nothing.
- Preserve action-wide ledger/inode accounting across earlier successful members and later refusal/failure.

## R36-2C — actual-open mount tests must exercise owners, not only the helper

The new `test_r35_canonical_opened_descriptor_mount_trust` proves the helper's local return values, but it does not prove that generic/common/P7 destructive owners consume that helper at all required boundaries. Real-owner acceptance remains mandatory.

### Mandatory R36-2 acceptance

Using real planning/authorization, `_cleanup_engine`, `StorageExecutor.run`, settlement, and audit with only trust/filesystem timing injected:

1. generic top-level root same-device mount substitution between planning and destructive acquisition -> sentinel survives, no false mutation;
2. generic nested child equivalent, including a known-prefix partial case;
3. fully certified common top-level/nested equivalent;
4. individually-authorized common nested parent becomes a same-device mount after planning -> authorized-looking external member survives;
5. P7 released directory mount introduced between initial entry observation and authority-bearing child open -> sentinel survives;
6. resolver unavailable/ambiguous retains at every shared destructive mechanism;
7. generic, fully certified common, and P7 directory name replacement **after the directory descriptor is accepted but before final rmdir** -> replacement survives and outcome/audit reflect only mutations actually performed before the contradiction;
8. directory-to-symlink swap remains safe through generic and fully certified common real executor paths;
9. individually-authorized regular-file replacement by symlink/directory/special node remains retained, and a member with no typed owner authority is not implicitly treated as a regular file.

# R36-3 — all descriptor/session close paths must be terminality-safe and leak-free

## R36-3A — P7 recursion leaks descriptors on normal stop returns

Current `_remove_certified_directory()` opens `handle`, enters a `try`, and returns `stop(...)` from numerous observation/contradiction branches inside that `try`. Its descriptor close is in the `else:` of the surrounding `try/except/else`.

In Python, a `return` from the `try` does not execute that `else`. Therefore symlink/kind/refusal/stat/unlink/nested-stop/enumeration-return paths can leave the opened directory descriptor live. This is both a resource leak and stale authority lifetime beyond the action that produced the terminal outcome.

### Required end state

- Every acquired P7/generic/common descriptor is closed exactly once on every success, refusal/stop, partial, and exception path unless ownership is deliberately transferred to a still-live session.
- Structure recursion so outcome computation cannot bypass finalization. Prefer a single explicit outcome variable plus `try/finally`/close helper, or an engineering-equivalent pattern whose control flow is statically obvious.
- Closing after a prior mutation uses the running ledger so close-only failure cannot erase mutation truth.

## R36-3B — `ReleasedAttemptSession.invalidate()` cannot decide primary-vs-secondary failure with its current `sys.exc_info()` check

Current `invalidate()` catches its own `close()` exception and then tests `sys.exc_info()[0] is not None`. Inside that `except`, the condition is necessarily true for the caught close exception itself, so a close-only failure is silently swallowed even when no product exception was previously active.

That violates Revision 35's required distinction between:

- secondary close failure while a more important primary post-mutation exception is propagating; and
- close failure as the only failure, which must not make the operation look cleanly successful.

### Required end state

- `ReleasedAttemptSession.close()` remains one-way: mark closed and invalidate/clear the stored fd before attempting kernel close.
- `invalidate()` marks the capability unspendable and does **not** silently suppress a close-only failure.
- Primary-vs-secondary exception policy belongs at the caller that actually knows whether a primary product exception is active. In `_apply_released_member`, record the structured partial first, invalidate, preserve the original mutation cause as primary, and attach/log the close failure only as secondary evidence. Do not replace the primary cause.
- On typed no-exception contradiction, a close failure after recording the action must surface under the execution's current mutation truth rather than disappearing.
- `_cleanup_engine` final session cleanup keeps its rule: if a primary exception is active, do not replace it; if close failure is the only failure, surface it. If earlier actions mutated, the executor must audit partial before propagation; if none mutated, audit refused without fabricated bytes.

## R36-3C — common/generic mount-rejection and nested-close branches also need the same discipline

Current individually-authorized common descent suppresses exceptions from `opened_dirs` close unconditionally. Generic/P7 mount-refusal paths perform direct `os.close(...)` before constructing the intended ledger outcome, so a close failure can replace that outcome when an earlier prefix already mutated.

### Required end state

- Do not blanket-`pass` a nested descriptor close failure when no higher-priority exception is active.
- When a primary structured failure/outcome already exists, preserve it and retain the close failure only as secondary evidence.
- When close is the sole failure after mutation, raise/transport a structured partial for the current action.
- When close is the sole failure before mutation, surface a no-mutation failure without byte credit.
- Apply this uniformly to parent/root/child descriptors, mount-refusal close, individually-authorized intermediate descriptors, P7 session descriptors, and `_cleanup_engine` cached-session finalization.

### Mandatory R36-3 acceptance

Through real owners where the claim crosses an owner boundary:

1. P7 enumeration/`DirEntry.is_symlink`/`is_dir`/`is_file` stop paths close the opened handle; pre-mutation outcome remains no-change and post-prefix outcome remains exact partial.
2. A P7 normal contradiction return does not leak a descriptor; repeated bounded runs do not accumulate live fds.
3. Recursive descriptor close failure after mutation -> current action/audit remain partial with exact prior bytes.
4. Primary post-mutation recursive failure plus close failure -> primary cause/outcome survives.
5. Mount-refusal close failure after an earlier prefix -> prefix partial evidence survives.
6. `ReleasedAttemptSession.invalidate()` close-only failure is observable and capability is permanently unspendable.
7. Real low-level P7 post-mutation failure + session close failure -> partial action recorded, original low-level cause remains primary, session unspendable.
8. `_cleanup_engine` final session close failure after earlier successful mutation -> execution/audit partial before propagation; corresponding no-mutation case -> refused/nonmutating.
9. Individually-authorized common intermediate-descriptor close failure is not silently converted to success.

# R36-4 — acceptance must establish the real owner claims; current R35 additions do not

Revision 35 required semantic-owner acceptance with only low-level filesystem/trust/failpoint injection. The implementation added useful unit tests but did not close that requirement:

- `test_r35_canonical_opened_descriptor_mount_trust` invokes the trust helper directly;
- `test_r35_single_file_unlink_not_occurring_no_mutation` starts with a target that never existed and therefore does not exercise the concurrent-disappearance counterexample after observation;
- `test_r35_common_member_swapped_to_symlink_or_dir_retained` calls `remove_certified_subtree` directly instead of real cleanup planning/executor/audit;
- `test_r35_session_close_failure_preserves_primary_exception` constructs a session directly and does not exercise the P7 action/cleanup engine/audit boundaries;
- `test_r35_archive_create_and_reclaim_mutation_truth` manually creates `StorageExecutionResult(mutated=True/False)` and calls `_settle`; it never runs archive creation, hot reclamation, a publication failpoint, or `StorageExecutor.run`;
- `test_r35_dedup_and_maintenance_mutation_truth` exercises only a mocked event-prune return; it does not prove dedup, archive, restore, vacuum, or executor/audit exceptional transition behavior;
- the integration suite was not changed by `store-A11`, so no new real-owner R35 matrix was added there.

The monkeypatch-liveness guard also still proves only that a patched module attribute exists (`hasattr`). Revision 35 explicitly rejected that as sufficient because a dead alias can remain defined while production no longer reads it.

### Required acceptance end state

Keep helper tests, but add/repair owner-boundary tests so each material claim executes the production semantic owner whose behavior is claimed:

## Cleanup/default/generic/common

- real default `engine=None` single-file unlink succeeds then parent durability fails -> current action partial, exact bytes, execution/audit partial, original cause visible;
- observed target + this execution's unlink fails + concurrent disappearance -> no false mutation;
- generic recursive known prefix + later observation/unlink/rmdir/fsync/close failure -> exact partial through executor/audit;
- fully certified common equivalent;
- individually-authorized common earlier member succeeds, later member is replaced/refused/fails pre-mutation -> earlier bytes persist, replacement survives;
- top-level/nested mount and post-open/pre-rmdir substitution cases from R36-2.

## P7

- preserve the real two-attempt fixture;
- typed mutation-time partial contradiction in attempt A -> action recorded, later A withheld, independent B proceeds;
- exceptional low-level post-mutation failure in A -> action recorded, A invalidated, execution stops, no later A/B action, primary cause survives session/finalizer cleanup;
- observation and close/finalizer cases from R36-3;
- complete target identity/spent capability remain pre-syscall guards.

## Archive/restore/dedup/maintenance

Using real engine owners with named failpoints or lowest transition seam:

- archive atomic blob publication then later failpoint/failure -> partial+mutated with phase evidence; pre-publication counterpart nonmutating;
- hot reclaim unlink then durability failure -> exact action evidence;
- restore container creation and member replace followed by chmod/fsync/failpoint failure -> partial+mutated with current destination evidence; pre-transition counterparts nonmutating;
- dedup alias replace followed by its directory-durability failpoint -> partial+mutated and current alias evidence;
- positive prune followed by later failure -> partial+mutated; zero prune followed by later pre-mutation failure -> not partial because of prune;
- successful vacuum followed by later failure -> partial+mutated.

## Patch/failpoint liveness

For every acceptance-critical patch/failpoint:

- assert the injected seam actually fired (counter/event/failpoint assertion);
- prove the production owner path reads/calls the patched target, not merely that `module.attr` exists;
- prefer patching the lowest callable the owner actually invokes or instrument a spy around it;
- add a structural guard only when the property is structural; do not use `hasattr` as execution liveness evidence.

# R36-5 — exact-candidate affected regression/integration evidence remains mandatory

The candidate has only a successful GitHub `docs` check recorded. Revision 30/R35 require fresh functional regression/integration evidence bound to the exact assembled executable candidate; a required command that never ran is not a pass.

After the **last executable/test edit**:

1. record exact executable commit and tree;
2. re-derive the affected surface from that candidate;
3. run all focused R22-R36 storage/P7 namespace, release/root/target identity, opened-descriptor mount, transition-aware unlink/publication, typed common-member, mutation outcome, zero-credit, close/session-finalizer, interruption/retry, concurrency, and cross-engine mutation-truth nodes;
4. run complete:

```text
tests/test_mlff_storage_reset_core.py
tests/test_mlff_storage_reset_integration.py
```

5. run at minimum the previously named owner regressions:

```text
tests/test_mlff_target_size_p4f_storage_docs_structure.py
tests/test_mlff_target_size_p6_destructive_closure.py
tests/test_mlff_p7_r11_repair_acceptance.py
tests/test_mlff_p7_r12_repair_acceptance.py
tests/test_mlff_p7_r13_authority_acceptance.py
tests/test_mlff_campaign_cli.py
```

6. include every maintained test module/node discovered from the final candidate that exercises `archive_create_engine`, archive reclaim, restore, `dedup_engine`, campaign-state maintenance, `durable_unlink`, common/generic cleanup, or the P7 released-attempt remover/session;
7. run maintained-suite `pytest --collect-only -q`;
8. run compile/import checks for every changed Python module, `git diff --check`, repository-required static checks, conflict-marker scan, and structural checks for:
   - no consequential pathname-recursive bypass;
   - no post-failure pathname disappearance inference;
   - no signature-incompatible `TypeError` fallback that fabricates unlink transition truth;
   - every destructive directory acquisition uses actual-open trust before descent;
   - every directory `rmdir` retains parent authority and performs the final identity check;
   - all `StorageExecutor` mutation-producing engines establish explicit mutation truth at the persistent transition;
   - acceptance-critical patches/failpoints are live;
9. validate affected Markdown and regenerate/validate committed PDF derivatives;
10. perform a fresh complete affected regression/integration pass on the exact final executable tree after all fixes are assembled, recording command/node selection and pass/fail/skip counts;
11. if a later successor is docs/workplan/PDF-only, prove the exact executable tree is unchanged before reusing the behavioral evidence.

Whole-repository behavioral pytest remains conditional on an unbounded final affected surface or independent repository policy. External DFT, long GPU production, and environment-specific HPC/shared-storage qualification remain deferred and nonblocking.

# Implementation sequence

## Stage A — exact transition and publication truth

Implement R36-1 as one coherent transition-ownership repair:

- correct `durable_unlink` callback/result semantics;
- remove post-hoc absence inference and `TypeError` compatibility escapes from consequential callers;
- expose archive atomic-publication transition before fsync/readback/failpoint;
- preserve exact action/phase evidence without using outcome prose as semantics.

Run the focused real default/archive/reclaim transition tests before continuing.

## Stage B — continuous destructive descriptor authority

Implement R36-2:

- keep parent/child descriptor identity through every final `rmdir`;
- perform final no-follow name-vs-opened-descriptor identity comparison immediately before fd-relative rmdir;
- close the individually-authorized common container and nested-mount gaps;
- require explicit typed member authority.

Run real generic/common/P7 mount, substitution, and typed-member counterfactuals.

## Stage C — close/finalization semantics

Implement R36-3 across recursion, common intermediate descriptors, P7 session invalidation, and cleanup finalization. Run primary-vs-secondary, close-only, pre-mutation, post-mutation, and leak/lifetime tests.

## Stage D — acceptance closure

Replace/augment helper/manual-result tests under R36-4 with real-owner tests and strengthen patch/failpoint liveness.

## Final assembled closure

Execute R36-5 on the exact candidate and record evidence. Only after all blocking obligations pass may the implementation workplan close.

# Initially affected surface

Expected executable surface is bounded but may broaden after final reference analysis:

- `mdstats/training_data/storage/durability.py` — exact unlink/publication transition callbacks/results;
- `mdstats/training_data/storage/executor.py` — no post-hoc inference, continuous generic/common descriptor authority, final rmdir checks, typed common-member behavior, close transport;
- `mdstats/training_data/storage/trust.py` — only minimal helper/identity support if needed; preserve canonical opened-descriptor mount policy;
- `mdstats/training_data/qualification/store.py` — P7 final-rmdir continuity, all-return descriptor closure, session close/invalidation semantics;
- `mdstats/training_data/storage/commands.py` — P7 primary-vs-secondary invalidation and cleanup session finalization if local adjustment is required;
- `mdstats/training_data/storage/archive.py` — atomic blob/publication mutation phase and hot-reclaim transition truth;
- `mdstats/training_data/storage/inventory.py` — only if typed common-member handoff needs a minimal interface adjustment; preserve owner authority;
- `mdstats/training_data/storage/dedup.py`, `storage/maintenance.py` — preserve current conforming transition timing; touch only if real-owner acceptance exposes a local evidence/failure gap;
- storage core/integration tests and every newly implicated maintained owner regression;
- `docs/specs/training_data/mlff_storage_management_spec.md` and PDF derivative only where final semantics/document wording changes.

Do not silently narrow a named owner or mandatory acceptance path.

# Redesign triggers

This remains bounded implementation rework under Revision 30 unless evidence proves one of the following:

- supported Python `>=3.10`/POSIX primitives cannot maintain parent/child descriptor identity plus final fd-relative rmdir under the accepted threat boundary;
- the durability primitive cannot expose whether atomic publish/unlink crossed its persistent transition without an incompatible public contract;
- typed common-member authority cannot be carried from the existing owner inventory without changing the frozen owner model;
- the four cleanup outcomes or shared execution result cannot represent the required truth without incompatible schema change;
- a supported external consumer makes removal of the consequential `durable_unlink` compatibility fallback or public bool remover adaptation impossible.

If triggered, reopen only that decision with concrete evidence. Test inconvenience, lack of Serena/Semgrep, or a difficult race fixture is not a redesign trigger.

# Snapshot-complete handoff

The current normative set after Revision 36 is:

1. `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md` — broader frozen owner-driven storage architecture/non-goals;
2. `STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md` — accepted final-apply design and protected trust/outcome semantics;
3. `docs/specs/training_data/mlff_storage_management_spec.md` — current product contract;
4. **this file** — complete current bounded implementation/review obligations still open after the Revision-35 implementation;
5. `AUTHORITY_REVISION_36.md` / `AUTHORITY.md` — current disposition/navigation.

Revision 31-35 implementation-review/authority files remain historical provenance. No still-open implementation requirement depends exclusively on them, prior conversation, Git archaeology, or optional Serena/Semgrep state.

**Design/workplan disposition:** Revision 30 remains **CLOSED / implementation-ready**.

**Reviewed executable disposition:** `84a2df7779884fa3c0590588366bd139dd6241de` / tree `9e57b388a5826ea900edb674decc605605b51fe2` is **NO-PASS / reopened under Revision 36**.
