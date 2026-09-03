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
scope: bounded implementation and acceptance repair for mutation-truth independence from reclaimed-byte count, preservation of symlink-attack-resistant recursive deletion, still-missing real-StorageExecutor failure/scoping acceptance, exact deterministic per-action byte evidence, and exact-candidate final regression evidence
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

Five blocking groups remain.

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
4. matching pre-first-mutation counterfactuals remain no-change/zero and leave the target intact.

A test that asserts only positive byte cases does not establish this requirement.

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

### Required repair

Preserve R31 exact mutation/byte tracking **without weakening the pre-existing recursive trust boundary**:

- Generic and common certified recursive deletion must descend through a race-resistant mechanism compatible with Python `>=3.10`: descriptor-relative/no-follow directory acquisition and fd-relative child operations, or an engineering-equivalent use of the platform's actually symlink-attack-resistant recursive primitive while retaining exact per-transition accounting.
- A check of `shutil.rmtree.avoids_symlink_attacks` may justify use of that implementation; it may not be cited as protection for an unrelated pathname walker.
- Re-observe/retain the relevant directory identity at the destructive boundary so a directory-to-symlink substitution cannot transfer authority to the symlink target. Symlinks themselves may only be unlinked when the current owner authorizes the link entry; recursive descent must never follow them.
- Preserve nested-mount/external-owner fail-closed behavior and the existing storage ownership boundary. Do not broaden deletion authority to obtain easier accounting.
- Preserve `MutationLedger` semantics: measure before unlink where required, credit after successful mutation, hard-link dedup action-wide, and structured partial transport after any later failure.

### Acceptance

- Deterministically inject a swap after a child directory has been observed/classified but before recursive descent: replace it with a symlink to an external test-owned directory containing a sentinel file. Through the real generic cleanup executor, the external directory/sentinel must survive and the action must refuse/fail closed without traversing the symlink target.
- Exercise the same counterfactual through the fully certified common-subtree path if it shares the recursive primitive.
- Add a focused structural/static regression proving the accepted recursion uses the intended fd-relative/no-follow or genuinely safe-rmtree owner path and cannot regress to `is_dir(no-follow) -> recurse by Path(entry.path)` while claiming the `shutil.rmtree` capability flag as protection.
- Preserve ordinary recursive partial-byte and post-mutation durability tests after the safe traversal repair.

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

### Required repair and acceptance

- Build a bounded fixture/execution containing at least two independently authenticated released P7 attempt/session keys in one real cleanup plan/execution. Inject a mutation-boundary refusal or partial mutation in one attempt; prove its later same-attempt actions are withheld without destructive calls while the independent P7 attempt remains eligible and proceeds through its own real session. If the actual supported product model makes two independent P7 attempts in one execution impossible, do not substitute an unrelated storage action; reopen only that acceptance/design premise with repository evidence.
- Include a partial-mutation variant so the durable audit proves same-attempt invalidation after `partial_change_refused`, not only a no-change refusal.
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
6. repository static checks, including the recursive traversal structural guard, plus Python compile/diff checks and affected Markdown/PDF validation;
7. final affected-surface re-derivation from the assembled candidate followed by a fresh complete affected regression/integration pass on that exact executable tree.

A generated-document-only successor may reuse executable evidence only after an exact compare proves no executable or test change. Whole-repository behavioral pytest remains conditional on unbounded final impact or independent repository policy. External DFT, long GPU production, and environment-specific HPC/shared-storage qualification remain deferred and nonblocking; do not present them as executed.

## Affected surface and implementation sequence

The initially affected executable surface is bounded to:

- `mdstats/training_data/qualification/store.py` for P7 mutation-truth state independent of bytes;
- `mdstats/training_data/storage/executor.py` for safe generic/common recursive traversal and action-boundary truth;
- `mdstats/training_data/storage/outcome.py` only if the existing ledger needs a small reusable extension;
- `mdstats/training_data/storage/commands.py` only if real-executor/session routing needs a local acceptance-preserving correction;
- `mdstats/training_data/storage/trust.py` only if the canonical mount/safe-descent primitive is the correct owner of a reusable fd-relative traversal helper;
- storage core/integration tests and the affected P1/P3/P4/P5/P6/P7 regressions;
- current storage specification/PDF only if implementation truth changes wording.

Treat R32-1 and R32-2 as one coherent mutation-truth/trust-boundary implementation stage, because the recursion must simultaneously know which destructive transitions succeeded and ensure those transitions cannot escape the authorized tree. Close that stage semantically and run focused plus stage-local affected regression before dependent acceptance work. Then close R32-3/R32-4 real-owner tests, re-derive final affected surface, and execute R32-5 final acceptance on the assembled candidate.

Do not add a new persistent ledger, recursive-control-plane service, platform-specific kernel extension, or duplicate P7 authority. Prefer consolidation around the existing `MutationLedger`, retained-descriptor/no-follow patterns, and current trust helpers where they cleanly own the requirement.

## Routing and redesign triggers

- **R32-1:** implementation nonconformance with frozen R30-F/G and R31 mutation-truth requirements.
- **R32-2:** new independent implementation regression against the parent workplan's frozen external/symlink protection and the accepted recursive threat boundary.
- **R32-3/R32-4/R32-5:** implementation/acceptance nonconformance; no architecture redesign is implied.

Reopen Design only if supported Python `>=3.10`/POSIX interfaces cannot realize a symlink-race-resistant recursive removal while preserving exact per-transition accounting under the frozen threat boundary, or if repository evidence proves the accepted independent-P7-attempt acceptance premise cannot exist in the supported product model. Reopen only that affected decision; preserve unrelated Revision-30/31 implementation and evidence.

## Handoff closure

The current supplied set after Revision 32 is:

- `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md` — broader frozen owner-driven storage architecture and non-goals;
- `STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md` — complete accepted final-apply design;
- `docs/specs/training_data/mlff_storage_management_spec.md` — current storage product contract;
- this Revision-32 implementation-review reopen — all still-binding Revision-31 acceptance corrections plus the newly surfaced implementation regressions;
- `AUTHORITY_REVISION_32.md` / `AUTHORITY.md` — current disposition/navigation.

No still-binding Revision-32 requirement depends exclusively on Git history, prior conversation, a superseded review file, or local Serena/Semgrep state.

**Design/workplan disposition:** Revision 30 remains **CLOSED / implementation-ready**; Revision 32 is bounded implementation and acceptance rework only.

**Executable disposition:** reviewed executable `2e01d6fa5119ba67088f7c312c44962eba902c8e` is **NO-PASS / reopened under Revision 32**.
