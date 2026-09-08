---
kind: implementation-review-reopen
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1-R32
parent_workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
status: reopened
reviewed_date: 2026-09-03
reviewed_authority_revision: 31
reviewed_executable_commit: 2e01d6fa5119ba67088f7c312c44962eba902c8e
reviewed_executable_tree: fe927d28612d411303676fc04d5a9cd7164720b1
reviewed_branch_head: 159c986bdf6273c0e7a44f833df30d4f3d10f852
review_verdict: NO-PASS
scope: bounded implementation and acceptance repair for mutation-truth independence from reclaimed-byte count, preservation of symlink-attack-resistant recursive deletion, truthful interrupted-execution status, still-missing real-StorageExecutor failure/scoping acceptance, exact deterministic per-action byte evidence, repair of decayed structural/failpoint guards, and exact-candidate final regression evidence
precedence: Revision 30 remains the accepted closed final-apply design; Revision 31 corrections that conform remain preserved; this review reopens only the bounded implementation and acceptance surfaces stated here
---

# Storage/I-O reset implementation review reopen 11 — Revision 32

## Verdict and preserved implementation

**NO-PASS / bounded implementation and acceptance reopen.**

Reviewed executable:

```text
commit  2e01d6fa5119ba67088f7c312c44962eba902c8e
tree    fe927d28612d411303676fc04d5a9cd7164720b1
```

Branch head `159c986bdf6273c0e7a44f833df30d4f3d10f852` differs from that executable only by the regenerated storage-specification PDF. Revision 31's implementation materially repairs several previously reproduced defects and those repairs must be preserved:

- per-action serialized removal evidence now carries an explicit credited/reclaimed byte value and the aggregate is accumulated from those action-local values;
- the default cleanup executor and CLI cleanup engine share an action-boundary `PartialMutationError` recorder;
- generic/common recursive removal now has an action-local mutation ledger for exact byte propagation across ordinary partial failures;
- P7 recursion retains a regular file when its required measurement fails rather than deleting it unaccounted;
- the exported P7 released-member mutation boundary now requires a complete plan-bound target identity before target observation or mutation;
- additional R31 real-owner tests were added for resealed authority, damaged final authority, mixed success/refusal, and durable-audit action evidence.

Revision 30's accepted architecture remains frozen: P7 semantic ownership, exact release/root/target binding, one retained descriptor capability, proof-as-upper-bound monotonic shrink, same-attempt invalidation, once-per-session read-only proof lookup, the four mutation outcomes, Python `>=3.10`, and the descriptor-pinned POSIX threat boundary are not reopened.

Seven blocking groups remain. R32-1 through R32-5 were raised by the Revision-32 review; R32-6 and R32-7 were surfaced by the Revision-32 gap re-derivation against the same executable tree and are equally binding.

## R32-1 — P7 mutation truth is still inferred from reclaimed-byte count

### Finding and evidence

`qualification/store.py::_remove_certified_directory()` keeps `freed = 0` and defines its ordinary stop path as:

```text
if freed:
    partial_change_refused(...)
else:
    refused_no_change(...)
```

That makes `freed > 0` stand in for “a destructive transition already happened.” These are different facts under the frozen storage metric. A successful removal can mutate the namespace while crediting zero bytes, including:

- unlinking a zero-byte regular file;
- removing an empty certified directory;
- unlinking another hard link for an inode already credited earlier in the same action.

If a later sibling contradicts the proof, cannot be measured/removed, or another later operation fails while the credited total is still zero, the current owner can return `refused_no_change` with `mutated=false` even though an entry is already gone. The same problem propagates upward when a nested removal mutated but contributed zero credited bytes.

This violates the still-frozen R30-F/R30-G distinction between mutation state and byte accounting and the R31-2 requirement that **any earlier mutation**, not merely a positive byte total or vanished top-level pathname, survives a later refusal/failure.

**Additionally verified on the same tree — the defect is not only a reporting defect.** `remove_released_attempt_member()` gates the post-mutation directory fsync on the recursion's own answer:

```text
outcome = _remove_certified_directory(...)
if outcome.mutated:
    _fsync_after_mutation(attempt_fd, removed_bytes=..., what=member_name)
```

Because `outcome.mutated` is derived from the outcome kind, and the outcome kind is chosen by `if freed:`, a recursion that unlinked a zero-byte file (or rmdir-ed an empty subdirectory) and then stopped returns `refused_no_change` — so the directory-entry removals that really happened are **also never fsynced**. The byte-count conflation therefore silently drops a durability step the design requires after every destructive transition, not merely a truthful label. The repair must restore both.

### Required repair

- Track “has this action destructively changed the namespace?” independently from reclaimed-byte count throughout P7 recursive removal. Reuse the existing `MutationLedger` semantics or an equivalent explicit action-local mutation flag/ledger rather than adding another persistent state machine.
- Mark mutation only after a destructive unlink/rmdir actually succeeds. A zero-byte removal and an empty-directory rmdir must set mutation truth even though credited bytes remain zero.
- Propagate both mutation truth and credited bytes from nested removals to their parent. A nested partial/clean removal with `mutated=true, removed_bytes=0` must not collapse to no-change at the parent.
- Once the first destructive transition has occurred, every later exception before clean completion must cross the current action boundary with `partial_change_refused`, `mutated=true`, the exact credited byte total (which may legitimately be zero), and the underlying cause. A failure before the first destructive transition continues to fabricate neither mutation nor bytes.
- Audit/action evidence must preserve the distinction `mutated=true, reclaimed_bytes=0`; do not reinterpret zero byte credit as no mutation.

### Acceptance

Exercise the **real cleanup `StorageExecutor`, real P7 owner/session, settlement, and durable audit** with bounded low-level fault/topology injection only:

1. remove a certified zero-byte file, then encounter a later mutation-time contradiction; the action is partial, `mutated=true`, per-action and aggregate reclaimed bytes are exactly `0`, and the zero-byte file is gone while the contradicting entry is retained;
2. remove a certified empty nested directory, then encounter a later contradiction/failure; the same partial/true/zero semantics hold;
3. after a zero-credit destructive transition, inject a later exception and prove the partial action is recorded before propagation and the durable audit reports the mutation truth;
4. matching pre-first-mutation counterfactuals remain no-change/zero and leave the target intact;
5. a zero-credit destructive transition that then stops still performs the post-mutation durability step for the entries that actually went — prove the fsync is attempted (and its failure transported as `partial_change_refused`), not skipped because credited bytes are zero.

A test that asserts only positive byte cases does not establish this requirement.

The current specification states only that "every recorded action carries its own reclaimed-byte figure". After this repair it must also state that mutation truth is recorded independently of that figure and that `mutated=true, reclaimed_bytes=0` is a legitimate, meaningful record — with the generated PDF successor regenerated.

## R32-2 — the R31 generic recursive rewrite regressed the accepted symlink-race boundary

### Finding and evidence

Before R31, generic directory removal delegated recursion to `shutil.rmtree()` only when `shutil.rmtree.avoids_symlink_attacks` was true. The R31 implementation retained that capability check but replaced the recursive operation with `_remove_tree_tracked()`, whose descent is pathname based:

```text
os.scandir(root)
entry.is_dir(follow_symlinks=False)
child = Path(entry.path)
_remove_tree_tracked(child, ledger)
os.unlink(entry.path)
os.rmdir(root)
```

`shutil.rmtree.avoids_symlink_attacks` describes `shutil.rmtree`'s implementation; it does not make this separate custom pathname walker race-safe. After a child is classified as a directory and before the recursive pathname is reopened, that directory entry can be replaced by a symlink. The custom recursion can then follow the replacement and operate outside the certified/authorized tree. The same helper is used by the fully certified common-subtree path.

This is a new implementation regression against the parent workplan's frozen external/symlink non-destructibility and “external/symlink protections unchanged” requirements. It is not a reason to reopen the owner-driven storage design.

**Two existing guards have decayed with it and must be repaired, not merely supplemented.**

- `tests/test_mlff_storage_reset_core.py::test_no_consequential_recursive_path_equates_containment_with_ownership` asserts `executor.count("shutil.rmtree(") == 1` under the comment "the only rmtree *call* in the consequential path is the certified-subtree helper, and it is guarded by the platform's own symlink-safety promise". That is no longer true on this tree: `remove_certified_subtree()` reaches `_remove_tree_tracked()` via `_remove_tree_or_file_tracked()` and calls no `rmtree`; the single surviving `shutil.rmtree(` call is in the legacy boolean `remove_durably()`. The guard still passes while asserting a false narrative about the mechanism it exists to protect.
- `tests/test_mlff_storage_reset_core.py::test_recursive_deletion_is_symlink_attack_resistant` asserts the platform flag as though the flag were the protection. After R32-2 the flag protects only whatever actually delegates to `shutil.rmtree`; the test must say which owner it is speaking for.

**Consolidation evidence for the repair.** The repository already owns a correct primitive: `qualification/store.py::_open_directory_nofollow()` (`O_DIRECTORY|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC`, `dir_fd`-relative, `NamespaceAmbiguity` on a substituted entry), used by the P7 recursion and by `authorize_released_attempt_member`'s descent, and `storage/trust.py::crosses_mount_boundary_at(parent_fd, name, display)` is already the descriptor-relative mount guard. Do not write a second no-follow descent.

### Required repair

Preserve R31 exact mutation/byte tracking **without weakening the pre-existing recursive trust boundary**:

- Generic and common certified recursive deletion must descend through a race-resistant mechanism compatible with Python `>=3.10`: descriptor-relative/no-follow directory acquisition and fd-relative child operations, or an engineering-equivalent use of the platform's actually symlink-attack-resistant recursive primitive while retaining exact per-transition accounting.
- A check of `shutil.rmtree.avoids_symlink_attacks` may justify use of that implementation; it may not be cited as protection for an unrelated pathname walker.
- Re-observe/retain the relevant directory identity at the destructive boundary so a directory-to-symlink substitution cannot transfer authority to the symlink target. Symlinks themselves may only be unlinked when the current owner authorizes the link entry; recursive descent must never follow them.
- Preserve nested-mount/external-owner fail-closed behavior and the existing storage ownership boundary. Do not broaden deletion authority to obtain easier accounting.
- Preserve `MutationLedger` semantics: measure before unlink where required, credit after successful mutation, hard-link dedup action-wide, and structured partial transport after any later failure. `MutationLedger.note_mutation()` already exists for a zero-credit destructive transition; `_remove_tree_tracked` already calls it after `rmdir` — that behaviour must survive the traversal repair.
- **Own the primitive once.** Promote the no-follow descriptor-relative directory open into `storage/trust.py` (which `qualification/store.py` already imports, so the dependency direction is preserved) and have both the P7 recursion and the storage executor's generic/common recursion use that one helper. `storage/executor.py` must not import `qualification/store.py`; a duplicated second implementation of the same descent is not acceptable, because two copies is exactly how the current divergence arose.
- **Resolve the second recursive-removal mechanism.** The exported legacy `remove_durably()` still performs a `shutil.rmtree` recursion with different safety and accounting properties from the accepted owner path, and no consequential code calls it any more (only `storage/__init__.py` re-export and tests). Either retire it with its exports and dependent tests, or retain it deliberately as a documented non-consequential helper with its own guard stating that it is not the cleanup owner. Do not leave two recursive deletion mechanisms in the exported surface with an unstated difference in trust boundary.

### Acceptance

- Deterministically inject a swap after a child directory has been observed/classified but before recursive descent: replace it with a symlink to an external test-owned directory containing a sentinel file. Through the real generic cleanup executor, the external directory/sentinel must survive and the action must refuse/fail closed without traversing the symlink target.
- Exercise the same counterfactual through the fully certified common-subtree path if it shares the recursive primitive.
- Add a focused structural/static regression proving the accepted recursion uses the intended fd-relative/no-follow or genuinely safe-rmtree owner path and cannot regress to `is_dir(no-follow) -> recurse by Path(entry.path)` while claiming the `shutil.rmtree` capability flag as protection. Prefer an AST/Semgrep-style check over a `count("shutil.rmtree(") == 1` string count, whose failure mode is exactly the decay described above.
- Repair the two decayed guards named above so each states the owner it actually speaks for, and re-point them at the post-repair recursion.
- Preserve ordinary recursive partial-byte and post-mutation durability tests after the safe traversal repair.

The current specification documents the descriptor-relative no-follow recursion only for the P7 released-attempt boundary and is silent on the generic/certified-subtree recursion, which a reader would therefore assume is `shutil.rmtree`. Once the traversal is repaired the specification must state the recursion guarantee for that path too, with the PDF successor regenerated.

## R32-3 — R31-2 real-StorageExecutor failure acceptance is still proxy evidence

### Finding and evidence

The new core-test helper `_drive_removal()` constructs a `StorageExecutionResult` and directly calls `record_or_reraise()`. It does **not** call `StorageExecutor.run()`, does not execute executor authorization/revalidation, does not invoke `_settle()`, and does not publish the durable audit. Its generic partial test explicitly allows the result status to remain `planned`.

The R31-2 acceptance contract explicitly required the real `StorageExecutor`, settlement, and durable audit for all five generic/default/common-subtree failure counterfactuals. Moving the tests from a lower helper to the action recorder is useful focused coverage, but it still can remain green while executor routing, settlement, or audit behavior is broken.

### Required repair and acceptance

Keep the focused helper tests if useful, but add real-owner integration cases for every still-binding R31-2 case:

1. `engine=None`: unlink succeeds and durability fails;
2. generic recursive directory: one child is removed and a later child/removal fails while the container survives;
3. fully certified common subtree: removal succeeds and the later durability step fails;
4. individually authorized common subtree: an earlier member succeeds and a later member fails before its own mutation;
5. corresponding failures before the first destructive transition.

For each case, authorization/planning as applicable, `StorageExecutor.run`, action recording, settlement, finalization, and durable audit remain production code. Instrument only the low-level filesystem transition necessary to create the counterfactual. Assert exact action collection, outcome, `mutated`, reclaimed bytes, terminal/partial status, audit content, and exception propagation where the contract raises.

## R32-4 — R31-5 attempt-scoping and exact-value acceptance remain incomplete

### Finding and evidence

Two R31-5 requirements remain materially unclosed:

- `test_an_invalidated_attempt_still_lets_an_independent_action_proceed` substitutes storage-owned residue as the independent action. Its own docstring points to `test_an_invalidated_attempt_does_not_withhold_an_independent_attempt` for the two-P7-attempt claim, but that test directly invokes `_apply_released_member()` with two separately built results/snapshots rather than driving one real cleanup execution. R31-5 explicitly required a combined real-executor case proving same-attempt invalidation does not withhold an **independent P7 attempt**.
- `test_the_post_mutation_partial_records_the_exact_byte_amount` asserts only `reclaimed_bytes > 0` and `<= planned size`. That is a bounded range, not the exact deterministic per-action value R31-5 expressly required after the previous review found the same weakness.

The newly added incomplete-target-identity integration case is also not parameterized by target kind; the still-binding R31-4 acceptance requires the missing and one-key-incomplete identity counterfactuals for both file and directory targets. Existing focused identity tests may be reused, but final acceptance must make the two target kinds explicit at the owner boundary.

**Both open premises behind this group have now been settled against the executable tree; do not re-derive them and do not reopen design on either.**

1. *Two independent released P7 attempts in one execution are supported by the product model.* `storage/owners.py` enumerates `attempts_by_generation.get(generation, ())` and emits one `p7:attempt_scratch:{generation}:{attempt.name}` view per released attempt, and `storage/commands.py::_cleanup_engine` keys its live sessions by `str(view.path.parent)` — one session per attempt root, opened lazily, all closed in the engine's `finally`. The limitation is in the fixture (`_released_attempt_campaign` builds one binding, as that test's own docstring concedes), not in the design. The required acceptance is therefore realizable with a two-released-attempt fixture, the design premise is **not** reopened, and storage-owned residue may not be substituted for the second attempt.

2. *The partial-mutation variant as originally written is not realizable and its acceptance is corrected here.* `_apply_released_member` records the partial action, invalidates the session, and then **re-raises** (`raise (exc.cause or exc) from exc`). The engine loop therefore never reaches a later action of any attempt, so "later same-attempt actions are withheld after `partial_change_refused`" cannot be observed and must not be asserted. This is the accepted design (an execution that mutated and then failed stops and re-plans from live state), not a defect.

### Required repair and acceptance

- Build a bounded fixture/execution containing at least two independently authenticated released P7 attempt/session keys in one real cleanup plan/execution. Inject a mutation-boundary refusal or partial mutation in one attempt; prove its later same-attempt actions are withheld without destructive calls while the independent P7 attempt remains eligible and proceeds through its own real session. If the actual supported product model makes two independent P7 attempts in one execution impossible, do not substitute an unrelated storage action; reopen only that acceptance/design premise with repository evidence.
- Include a partial-mutation variant, asserting what the design actually guarantees rather than withholding: the partial action is recorded **before** the exception propagates, the session is invalidated and then closed by the engine's `finally`, the durable audit is published with `status=partial`, `mutated=true` and the exact per-action bytes, the original cause propagates to the caller, and no later action of either attempt executed. Withholding-after-invalidation continues to be proven by the `refused_no_change` variant, where the engine loop does continue.
- Prove in the two-attempt refusal variant that the second attempt's session is opened and its members are removed through their **own** real session while the first attempt's remaining members carry the shared-authority withholding refusal, and that both sessions are closed.
- Make the post-mutation exact-byte test deterministic: construct or select a known removed prefix and assert equality to its known action-local byte value in the recorded action and aggregate. `> 0`, `<= planned`, or “aggregate equals sum” alone is insufficient.
- Explicitly cover missing and every one-key-incomplete target identity for both a top-level released file and a released directory, with no stat/open/unlink/rmdir before refusal and the target intact.

## R32-5 — exact-candidate final functional evidence is still absent

### Finding and evidence

Revision 31 required fresh final evidence after the last executable/test edit, bound to the exact executable commit/tree, including focused R22-R31/R32 checks, complete storage core/integration suites, affected current-owner regressions, maintained-suite collection, static checks, affected documentation validation, and a final affected-surface re-derivation followed by fresh assembled regression/integration.

The reviewed implementation commit contains executable/test changes, so Revision-30 evidence was invalidated for those affected claims. In the supplied repository/connected CI evidence for executable `2e01d6f...`, the only workflow run is the documentation-PDF build; no candidate-bound behavioral regression record or CI status establishes the required final functional acceptance set.

This is an unavailable/unexecuted acceptance boundary, not permission to infer PASS from source inspection or from the implementation commit message.

### Required final evidence

After the last executable/test repair, bind the evidence to the exact executable commit and tree and record the actual commands/node selections plus pass/fail/skip summaries for:

1. focused R22-R32 P7 namespace/state/proof/root/release-authority/target-identity/capability/mutation/outcome/concurrency/failure and recursive-race counterfactuals;
2. complete `tests/test_mlff_storage_reset_core.py`;
3. complete `tests/test_mlff_storage_reset_integration.py`;
4. affected current-owner P1/P3/P4/P5/P7 plus P6 destructive/current-lifecycle regressions implicated by the common cleanup/result/durability/trust path;
5. clean maintained-suite `pytest --collect-only -q`;
6. repository static checks, including the repaired recursive-traversal structural guard and the new monkeypatch-liveness guard, plus Python compile/diff checks and affected Markdown/PDF validation;
7. the R32-7 monkeypatch-liveness sweep result across both storage-reset suites, reported even when it finds nothing further;
8. affected regression for any P4C/P4F/STOR1 test that depends on `remove_durably`, whichever disposition R32-2 chooses for it;
9. final affected-surface re-derivation from the assembled candidate followed by a fresh complete affected regression/integration pass on that exact executable tree.

A generated-document-only successor may reuse executable evidence only after an exact compare proves no executable or test change. Whole-repository behavioral pytest remains conditional on unbounded final impact or independent repository policy. External DFT, long GPU production, and environment-specific HPC/shared-storage qualification remain deferred and nonblocking; do not present them as executed.

## R32-6 — an interrupted execution is reported as `partial` even when nothing was mutated

### Finding and evidence

`storage/executor.py::StorageExecutor.run()` handles any escape from the engine with a single unconditional verdict:

```text
except BaseException as exc:
    result.status = STATUS_PARTIAL
    result.detail = (
        "execution was interrupted after a strict subset of "
        f"actions: {exc}"
    )
    self._finalize(result, trigger=trigger)
    raise
```

Nothing here consults `result.mutated`, `result.completed`, or `result.refused`, all of which the action recorder maintains precisely so the truth is available. `record_or_reraise()` intercepts only `PartialMutationError`; every failure that happens **before** an action's first destructive transition — a `ledger.failure()` that returns the bare `OSError` because the ledger never mutated, an enumeration failure at the root, a revalidation-independent engine error — propagates unrecorded. The durable audit then carries `status=partial`, `mutated=false`, no completed actions, and a detail sentence asserting "after a strict subset of actions", i.e. a mutation claim for an execution that changed nothing.

This is the same class of defect as R32-1 one level up: an execution-level status inferred from *how control left* rather than from *what was recorded*. It also directly contradicts `_settle()`, which already refuses to call a nothing-happened execution partial ("Reporting that as `partial` would imply a mutation this operation never made"). The two paths disagree, and the failure path — the one an operator reads after an incident — is the untruthful one. R32-3 case 5 and R32-1's pre-first-mutation counterfactuals both assert terminal status, so this must be repaired before that acceptance can be honest.

### Required repair

- Derive the interrupted execution's status from recorded evidence, exactly as `_settle()` does: an interruption with a recorded mutation (`result.mutated`, or any completed/partial action) remains `partial`; an interruption with nothing recorded is a refused/failed execution, not a partial one.
- The detail must state what actually happened — that the execution was interrupted and whether any action had mutated — and must not assert a "strict subset of actions" that does not exist.
- Preserve unconditionally: the audit is still finalized **before** the exception is re-raised; nothing is rolled back; the exception still propagates unchanged; a genuinely partial interruption still reports `partial` and still blocks a `complete` claim.
- Do not swallow the exception, do not add a second status vocabulary, and do not make the failure path re-run `_settle()` in a way that could relabel a partial interruption as complete.

### Acceptance

Through the **real `StorageExecutor.run`, real engine, settlement and durable audit**:

1. inject a failure before any action's first destructive transition; the published audit is not `partial`, `mutated=false`, no completed action is recorded, the exception propagates, and every target is intact;
2. inject a failure after a recorded mutation; the audit remains `partial`, `mutated=true`, carries the exact per-action bytes, and the exception propagates;
3. both cases publish the audit before propagation, and neither can report `complete`.

## R32-7 — a decayed failpoint leaves the generic-removal half of the interruption counterfactual vacuous

### Finding and evidence

`tests/test_mlff_storage_reset_integration.py` (the R30 interrupted-execution/retry case) installs its failpoint as:

```text
executor_mod.remove_durably = failing_remove
storage_commands.remove_durably = failing_remove
qstore.remove_released_attempt_member = failing_released
```

under a comment stating the failpoint "has to sit on whichever removal owner the actions actually reach: generic storage removal, and the P7 released-attempt boundary". Neither generic patch is live on this tree. `storage/commands.py` imports `remove_durably_outcome`, never `remove_durably`, so the second assignment creates an attribute the production module never reads; and `_execute_actions`/`_cleanup_engine` both call `remove_durably_outcome(action.path)`, so patching `executor_mod.remove_durably` intercepts nothing. Only `failing_released` is live. The test still passes because the P7 path alone supplies the two removals — so the generic-removal half of the interruption/retry claim silently evaporated during R31 while the assertion text still claims it.

This is evidence decay of exactly the kind the acceptance doctrine forbids: the test could stay green while the mechanism it names is entirely untested. It is also the pattern that hid R32-2 (a guard whose subject moved out from under it).

### Required repair and acceptance

- Re-point the failpoint at the owner the engine actually calls (`remove_durably_outcome`, and `remove_certified_subtree` where the certified-container branch is the one reached), and prove the generic branch is genuinely exercised — e.g. assert the failpoint was invoked, rather than inferring it from the surviving-target count.
- Sweep `tests/test_mlff_storage_reset_core.py` and `tests/test_mlff_storage_reset_integration.py` for every other monkeypatched production name and confirm each is an attribute the production path actually reads on this tree; repair or retire the ones that are not. Report the sweep result in the R32-5 evidence record even if it finds nothing further.
- Add a cheap static/structural guard that a name patched on a production module in these two suites is imported/read by that module, so this class of decay fails loudly instead of passing quietly.
- Preserve the case's real claim: an interruption after a strict subset leaves the remaining targets intact, no audit record says `complete`, and the retry plan re-derived from live state removes exactly the survivors.

## Affected surface and implementation sequence

The initially affected executable surface is bounded to:

- `mdstats/training_data/qualification/store.py` for P7 mutation-truth state independent of bytes;
- `mdstats/training_data/storage/executor.py` for safe generic/common recursive traversal, action-boundary truth, and the R32-6 interrupted-execution status derivation;
- `mdstats/training_data/storage/outcome.py` only if the existing ledger needs a small reusable extension;
- `mdstats/training_data/storage/commands.py` only if real-executor/session routing needs a local acceptance-preserving correction;
- `mdstats/training_data/storage/trust.py` as the expected owner of the promoted no-follow descriptor-relative directory-open helper, alongside the existing `crosses_mount_boundary_at`;
- `mdstats/training_data/qualification/store.py` additionally to consume that promoted helper in place of its local `_open_directory_nofollow`, without changing its behaviour;
- `mdstats/training_data/storage/__init__.py` only if R32-2 retires the legacy `remove_durably` export;
- storage core/integration tests and the affected P1/P3/P4/P5/P6/P7 regressions;
- current storage specification/PDF only if implementation truth changes wording.

Treat R32-1, R32-2 and R32-6 as one coherent truth-and-trust-boundary implementation stage: the recursion must simultaneously know which destructive transitions succeeded and ensure those transitions cannot escape the authorized tree, and the execution-level status must be derived from what that recursion recorded rather than from how control left. Close that stage semantically and run focused plus stage-local affected regression before dependent acceptance work.

Then close the acceptance stage — R32-3 and R32-4 real-owner tests plus the R32-7 failpoint repair and monkeypatch-liveness sweep — since R32-3's and R32-1's pre-first-mutation cases assert terminal status and would otherwise be written against the untruthful R32-6 behaviour. Finally re-derive the affected surface and execute R32-5 acceptance on the assembled candidate.

Specification/PDF alignment (R32-1 mutation-truth wording, R32-2 generic-recursion guarantee) belongs to the same candidate as the implementation it describes, not to a later documentation-only successor.

Do not add a new persistent ledger, recursive-control-plane service, platform-specific kernel extension, or duplicate P7 authority. Prefer consolidation around the existing `MutationLedger`, retained-descriptor/no-follow patterns, and current trust helpers where they cleanly own the requirement.

## Routing and redesign triggers

- **R32-1:** implementation nonconformance with frozen R30-F/G and R31 mutation-truth requirements.
- **R32-2:** new independent implementation regression against the parent workplan's frozen external/symlink protection and the accepted recursive threat boundary.
- **R32-3/R32-4/R32-5:** implementation/acceptance nonconformance; no architecture redesign is implied.
- **R32-6:** implementation nonconformance with the frozen truthful-reporting requirement and with `_settle()`'s own accepted rule; a new independent issue relative to the Revision-32 review, not a design reopen.
- **R32-7:** acceptance nonconformance (evidence decay), plus the standing obligation that a guard names the owner it actually protects.

Reopen Design only if supported Python `>=3.10`/POSIX interfaces cannot realize a symlink-race-resistant recursive removal while preserving exact per-transition accounting under the frozen threat boundary. The independent-P7-attempt premise is **settled** by the repository evidence recorded under R32-4 and is no longer a redesign trigger. Reopen only an affected decision; preserve unrelated Revision-30/31 implementation and evidence.

## Handoff closure

The current supplied set after Revision 32 is:

- `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md` — broader frozen owner-driven storage architecture and non-goals;
- `STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md` — complete accepted final-apply design;
- `docs/specs/training_data/mlff_storage_management_spec.md` — current storage product contract;
- this Revision-32 implementation-review reopen — all still-binding Revision-31 acceptance corrections, the Revision-32 review findings R32-1..R32-5, and the gap-re-derivation findings R32-6..R32-7, including the settled premises recorded under R32-4;
- `AUTHORITY_REVISION_32.md` / `AUTHORITY.md` — current disposition/navigation.

No still-binding Revision-32 requirement depends exclusively on Git history, prior conversation, a superseded review file, or local Serena/Semgrep state.

**Design/workplan disposition:** Revision 30 remains **CLOSED / implementation-ready**; Revision 32 is bounded implementation and acceptance rework only.

**Executable disposition:** reviewed executable `2e01d6fa5119ba67088f7c312c44962eba902c8e` is **NO-PASS / reopened under Revision 32**.
