---
kind: implementation-review-reopen
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1-R35
parent_workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
status: reopened
reviewed_date: 2026-09-03
reviewed_authority_revision: 34
reviewed_executable_commit: 557d32b84c5934096c95ba3ea1d33ed1714d165b
reviewed_executable_tree: 349a8cb9ac7cee653733f397f196d1426f6a7726
reviewed_plan_commit: 55dcb26f1dd770b98e13b92ba088f93d2da3c371
review_verdict: NO-PASS-PLAN-AMENDED
scope: snapshot-complete bounded implementation and acceptance closure for opened-descriptor mount ownership, transition-aware single-file mutation truth, typed common-subtree mutation authority, all-path cleanup/session-close failure transport, explicit cross-engine mutation accounting, canonical recursive-removal ownership, real-owner acceptance, and exact-candidate evidence
precedence: Revision 30 remains the accepted closed final-apply design; conforming implementation through Revision 34 is preserved; this Revision-35 handoff supersedes Revision 34 as the complete current bounded implementation/review contract
---

# Storage/I-O reset implementation review reopen 14 — Revision 35

## Disposition and purpose

**Revision-34 handoff review: NO-PASS as a final implementation handoff; amended and resealed here.**

The executable remains the merge candidate reviewed by Revision 34:

```text
commit  557d32b84c5934096c95ba3ea1d33ed1714d165b
tree    349a8cb9ac7cee653733f397f196d1426f6a7726
```

The generated-document successor `acdb3f8b2a43e5c65b4a3ca2844816cf9073b8d4` changes only the storage-specification PDF and does not alter executable/test source. Revision 35 therefore continues to bind behavioral findings to executable tree `349a8cb...`.

Revision 34 identified real remaining defects, but a second implementation-handoff review found that it still left material owner discovery and several failure/mutation boundaries implicit. In particular, it did not explicitly cover the destructive **top-level action root** in mutation-time mount checks; it did not close the single-file `durable_unlink()` post-hoc mutation inference race; it omitted individually-authorized common-subtree final-kind/current-entry authority; it bounded descriptor-close handling too narrowly and missed `ReleasedAttemptSession.invalidate()/close()` plus the cleanup engine's session-finalizer; and it said to reconcile mutation-producing engines without naming the archive, restore, dedup, and maintenance transition points that determine exception-time truth.

This Revision 35 is the single snapshot-complete current bounded implementation contract. Implementation does not need Revision 31-34 review files to recover any still-binding correction.

Revision 30 remains the accepted closed architecture. No P1-P7 scientific/currentness semantics, owner-driven storage architecture, CampaignStore ownership, P5 proof architecture, archive/dedup/restore/control-plane architecture, Python `>=3.10` floor, or accepted descriptor-pinned POSIX threat boundary is reopened.

## Preserved conforming state

Preserve these already-conforming repairs unless a local change is required to satisfy a Revision-35 blocker:

- P7 recursive removal uses the action-scoped `MutationLedger`; mutation truth, exact credited bytes, and action-wide inode deduplication are no longer separate P7 authorities.
- Zero-byte file deletion, empty-directory removal, and a zero-credit hard-link transition can remain `mutated=true` with exact reclaimed bytes `0`.
- Generic/common recursive child deletion is descriptor-relative/no-follow rather than `Path(entry.path)` recursive descent.
- `storage.trust` owns the shared no-follow directory acquisition and dir-fd capability predicate used by P7 and storage recursion.
- `StorageExecutor.run` can already distinguish a genuinely empty pre-mutation interruption from an execution with recorded mutation; preserve that direction while removing the remaining `completed` proxy described below.
- The R30 interruption/retry failpoint now points at current typed removal owners rather than the obsolete boolean remover.
- P7 complete target-identity acceptance covers released regular-file and released-directory targets, including every one-key-incomplete identity.
- The real two-released-attempt fixture proves independently authenticated attempt/session keys can coexist in one cleanup execution; the no-change-refusal variant demonstrates attempt-scoped invalidation while an independent attempt proceeds.
- Post-mutation byte acceptance now uses an independent deterministic removed-prefix oracle and exact action/audit equality.
- Resealed/damaged final-authority real-executor acceptance remains present.
- The storage specification states that mutation truth is independent of byte credit and that consequential recursive deletion is descriptor-relative/no-follow.
- Dedup already sets execution-level `result.mutated = True` immediately after a successful alias replacement; preserve that transition timing while adding the missing current-action evidence below.

These preserved gains do not waive the bounded work below.

## Frozen ownership map for this repair

This repair must converge authorities rather than create parallel ones:

- **P7 release/root/proof/target semantics:** `qualification/store.py` and `ReleasedAttemptSession` remain the P7 semantic owner.
- **Mutation-time filesystem trust and mount policy:** `storage/trust.py` owns no-follow directory acquisition, nested-mount/same-device-bind-mount detection, and fail-closed ambiguity. Destructive owners consume that policy; they do not duplicate it.
- **Cleanup action mutation truth and exact reclaimed bytes:** `storage/outcome.py::MutationLedger` remains the action-scoped cleanup owner.
- **Single-file durable unlink sequencing:** `storage/durability.py` owns unlink + parent-durability mechanics, but a consequential caller must be able to know exactly when the unlink transition succeeded. Do not infer that fact later from pathname existence.
- **Execution-level mutation truth, settlement, and durable audit:** `StorageExecutor` owns the execution result. Every engine that can leave a persistent mutation before raising must set/record that truth at its own irreversible transition before a later failure can escape.
- **Engine-specific action/phase truth:** archive/restore/dedup/maintenance remain their semantic owners. Do not force cleanup's four removal outcomes onto non-removal operations merely to centralize bookkeeping.
- **Public compatibility:** the exported `remove_durably` surface remains governed; consequential cleanup must use one canonical safe typed implementation, and the public wrapper may not retain an independent recursive algorithm.

## R35-1 — mutation-time mount authority must bind the actual opened object, including the top-level destructive root

### Findings

Revision 34 correctly identified that generic/common child recursion does not consume the canonical mount decision and that P7 checks the name before opening the child. Its end state, however, spoke primarily in terms of a “directory child” and did not close the same transfer at the **top-level action root**.

Current generic/common recursion opens the action root by pathname with `open_directory_nofollow(str(root))` and immediately enumerates it. A storage-owned root or certified common container can become a mount point after planning/revalidation but before that open. `O_NOFOLLOW` rejects symlinks, not ordinary mount points, so the opened object can be externally mounted bytes while all lexical/path checks still look campaign-contained.

Likewise, current `crosses_mount_boundary_at(parent_fd, name, display)` observes the named child and the mount table before the authority-bearing child descriptor is acquired. A mount can appear between that observation and the subsequent no-follow open.

### Required end state

Use one canonical trust-owned mutation-time decision that evaluates the **actual opened directory descriptor** that destructive descent will enumerate.

For every destructive directory acquisition in P7, generic cleanup, and fully certified common-subtree cleanup — top-level action root and descendants:

1. retain/authenticate the parent descriptor appropriate to the existing ownership boundary;
2. acquire the target directory no-follow relative to that authenticated parent where the platform contract permits it;
3. compare the opened descriptor's filesystem identity with the authenticated parent as required by the existing trust contract;
4. consult the canonical mount resolver for the display locator so a same-device bind mount is not accepted merely because `st_dev` matches;
5. resolver unavailability, unreadable identity, mount ambiguity, or a detected nested mount closes the opened child and retains it without enumeration/removal;
6. only an accepted opened descriptor may be used for recursive enumeration and fd-relative unlink/rmdir.

Prefer a minimal helper in `storage.trust` that accepts the authenticated parent descriptor, already-opened child descriptor, and display locator (or performs the open and returns an accepted descriptor). Do not recreate mount-table policy in `executor.py` or `qualification/store.py`.

For a top-level generic/common action root, do not treat its pathname open as exempt: authenticate/pin the parent/root relationship at the same final boundary before descendant deletion. Preserve existing `root_identity` / `authority_identity` checks for certified common subtrees; opened-descriptor mount acceptance is additional mutation-time ownership evidence, not a replacement for those identity bindings.

Once an accepted descriptor is held, a later pathname substitution does not transfer authority to the replacement. The implementation may conservatively retain on a later ambiguous display-path observation; it may never widen authority to a different mounted object.

### Mandatory acceptance

Through real planning/authorization and the real cleanup `StorageExecutor`, injecting only the trust/mount observation seam:

- generic top-level root becomes a same-device mount after planning but before destructive acquisition: root/sentinel survive;
- generic nested child becomes such a mount before descent: child/sentinel survive;
- fully certified common-subtree top-level container and a nested child each get equivalent mutation-time mount counterfactuals;
- P7 released directory introduces the mount specifically between initial entry observation and the authority-bearing child acquisition: mounted sentinel survives;
- resolver unavailable/ambiguous cases retain rather than traverse for each shared destructive mechanism;
- include no-earlier-mutation cases (`mutated=false`, zero bytes) and known-prefix cases (`partial_change_refused`, `mutated=true`, exact prefix bytes);
- preserve the symlink-swap counterfactual and exercise generic plus fully certified common-subtree paths through the real cleanup executor rather than helper-only invocation.

## R35-2 — single-file mutation truth must be transition-aware; individually-authorized common members need final typed/current authority

### R35-2A: post-hoc `durable_unlink()` inference is not authoritative

Current `remove_durably_outcome()` calls `durable_unlink(path)` and, when it raises, decides whether unlink happened from a later `path.exists() or path.is_symlink()` observation. That is not a valid mutation boundary.

Two counterexamples are sufficient:

- unlink succeeds, parent fsync fails, and another object is installed at the pathname before the post-hoc existence check: the execution did mutate, but the replacement can make the code report a raw/no-change failure;
- unlink never succeeds because the name disappears concurrently, but the later name is still absent: absence can be misattributed to this execution and bytes can be falsely credited.

### Required end state

Consequential single-file removal must know the unlink transition directly:

- observe/measure the authorized object before unlink as already required;
- perform unlink through a transition-aware primitive or local sequence that marks the action ledger **immediately after the unlink syscall succeeds and before parent durability work**;
- if parent fsync then fails, propagate structured partial mutation with exact bytes;
- if unlink itself fails, do not fabricate mutation/bytes regardless of later pathname state;
- do not use a post-failure pathname existence check as proof that this execution performed the deletion.

`storage/durability.py` may expose a callback/typed result or the consequential typed owner may perform unlink + fsync explicitly using the shared durability primitive. Preserve ordinary non-consequential callers where their contract is still justified, but consequential cleanup must have transition truth.

Apply the same rule to hot archive reclamation and any other consequential raw `durable_unlink` owner reached by the affected surface.

### R35-2B: individually-authorized common members cannot spend path-only stale kind authority

In `remove_certified_subtree(... refusals=...)`, current member handling uses path predicates and then `lstat()`/`durable_unlink(member)`. `Path.is_file()` follows symlinks. An authorized regular-file member replaced by a symlink to a regular external target can therefore pass the initial file predicate; `lstat()` sees the new link, but the code does not compare that current kind with the kind the owner authorized before unlinking the link entry.

That removes a namespace object the owner did not authorize. The external target is not followed, but deleting an unauthorized replacement link still violates the frozen final-apply authority contract.

### Required end state

- individually-authorized common members carry or recover the owner's **typed** authorization through the final mutation boundary; a bare path is insufficient if the current entry kind can change;
- final observation is no-follow and compared with the authorized kind/identity evidence available from the owner contract;
- regular-file authorization cannot be spent on a replacement symlink, directory, or special node; such a replacement is retained;
- a symlink entry may be unlinked only when that exact link entry/kind is explicitly owner-authorized under the existing product contract;
- final mutation is descriptor-relative to an authenticated parent wherever the accepted POSIX trust boundary requires it; do not reintroduce a check-by-path then mutate-by-fresh-path gap;
- prior successful members remain represented by the same action ledger if a later member is refused or fails.

If `StorageInventorySnapshot.authorized_members()` currently loses typed evidence needed here, minimally extend the owner handoff rather than reconstructing authority from current filesystem shape in the executor.

### Mandatory acceptance

- single file: unlink succeeds then durability fails, while a replacement is installed before any possible later pathname observation; action remains partial with the original removed object's exact bytes and the replacement survives;
- single file: unlink does not occur and the name is concurrently absent; no mutation/bytes are attributed to this execution;
- individually-authorized common regular file swapped to symlink-to-external-file immediately before final mutation: replacement link and external sentinel survive;
- regular file swapped to directory/special node: replacement survives;
- matching ordinary authorized member removal still succeeds and exact byte deduplication remains action-wide;
- all claims above are exercised through the real cleanup executor/settlement/audit, with only low-level filesystem transition injection.

## R35-3 — every cleanup/session close path must preserve primary mutation truth and cause

### Findings

Revision 34 covered raw descriptor closes inside P7 and generic recursive walkers, but the same failure class exists one owner level higher.

`ReleasedAttemptSession.close()` marks the capability closed, invalidates its descriptor field, then calls `os.close(handle)`, which can raise. `_apply_released_member()` calls `session.invalidate()` while handling a `PartialMutationError`; `invalidate()` closes the session. A close failure there can replace the post-mutation primary cause before the intended exception is re-raised.

Separately, `_cleanup_engine()` closes every cached P7 session in an outer `finally`. A session-close failure can replace an already-active action failure, or can be the only escaping exception after earlier successful mutation.

### Required end state

Close/cleanup failure handling must cover all of these owners:

- P7 recursive child/root descriptors;
- generic/common recursive child/root descriptors;
- `ReleasedAttemptSession.invalidate()` and `ReleasedAttemptSession.close()`;
- `_cleanup_engine()`'s cached-session finalization.

Required semantics:

1. capability state becomes permanently unspendable before/independent of the kernel close result; an fd number must never be reused as a live session capability after a close attempt;
2. when a product-significant primary exception is already active, a secondary close failure must not replace it or erase the structured mutation outcome; preserve/chaining/diagnostic details may include the close failure;
3. when close failure is the only failure after a prior mutation, the execution remains truthful about that mutation and publishes partial audit evidence before propagation;
4. when close failure occurs before any mutation, do not fabricate mutation or reclaimed bytes;
5. ordinary successful close remains behaviorally unchanged.

Do not silently swallow a close failure if doing so would make the operation look fully successful. Do not, however, let cleanup mechanics overwrite the more important primary cause/outcome.

### Mandatory acceptance

At minimum, through real owners:

- P7 `DirEntry.is_symlink`, `is_dir`, and `is_file` observation failure after a zero-credit mutation -> partial/true/0; matching pre-mutation cases fabricate nothing;
- generic/common entry observation failure after a known prefix -> exact structured partial;
- recursive child close failure after mutation -> current action evidence survives;
- primary recursive post-mutation failure plus close failure -> primary cause and action outcome survive;
- `ReleasedAttemptSession.invalidate()` close failure while handling a real low-level `PartialMutationError` -> partial action already recorded, session unspendable, original cause remains the propagated primary failure;
- `_cleanup_engine()` final session close failure after earlier successful mutation -> execution/audit remain mutated/partial before propagation;
- matching session close failure with no mutation -> refused/no fabricated mutation.

## R35-4 — preserve the two distinct P7 partial semantics and prove each through the real owner

The current product has two materially different ways a P7 action can become partial. Acceptance must not collapse them.

### Typed mutation-time contradiction after a destructive prefix

A normal owner contradiction can return `partial_change_refused` without raising. `_apply_released_member()` records it, invalidates the attempt session, and the engine loop continues. Therefore:

- the partial action is recorded with exact bytes;
- later actions sharing that attempt are withheld without destructive calls;
- an independently authenticated P7 attempt remains eligible and proceeds through its own session;
- final execution settles partial and durable audit contains both the first attempt's partial/withheld evidence and the independent attempt's result.

Construct this using the real P7 recursive remover and a low-level contradiction (for example a current unrecorded/wrong-kind/mount boundary appearing after a known removed prefix). Do **not** replace `remove_released_attempt_member()` with a test function that simply returns the desired outcome.

### Exceptional post-mutation failure

A `PartialMutationError` represents a later operational failure after mutation. `_apply_released_member()` records the action, invalidates the session, and re-raises the original cause. The execution stops; later actions of either attempt do not execute.

Prove with a low-level fsync/observation/close failure below the real P7 owner that:

- the action is recorded before propagation with exact bytes/mutation truth;
- the attempt capability is invalidated and remains unspendable;
- cached sessions are closed under the R35-3 rules;
- durable audit is published with partial status before the original primary cause propagates;
- no later action of either attempt executed.

A test that monkeypatches the semantic owner to directly raise a fabricated `PartialMutationError` is useful unit coverage only; it does not close this real-owner claim.

## R35-5 — exception-time execution status needs one explicit cross-engine mutation fact, not completed-action proxies

### Findings

Revision 34 correctly identified that `StorageExecutor.run` currently treats `result.completed` as mutation evidence. That makes an `already_absent` completed action followed by a later pre-mutation exception look partial even though this execution changed nothing.

Removing that proxy is necessary but insufficient. The shared executor runs more than cleanup, and several engines can persist mutation before their normal “completed action” append. Revision 34 said to reconcile mutation-producing engines but did not enumerate the current transition points. That leaves correctness discovery to Implementation.

### Canonical execution rule

- `StorageExecutionResult.mutated` is the authoritative execution-wide fact for “did this execution leave a persistent mutation before the failure?”
- the outer exception path decides `partial` versus `refused` from explicit mutation truth, not from `completed`, `created_bytes`, `restored_bytes`, reason strings, or exception type;
- `completed` remains terminal-action evidence, not a proxy for mutation;
- an `already_absent` completed action does not set mutation;
- every engine must set/record mutation at the first persistent transition that can survive a later failure, before any later failpoint/fsync/observation can escape;
- transient staging that is fully cleaned/recovered before propagation need not be reported as a surviving product mutation. The distinction is whether the failed execution leaves changed persistent state that the audit/retry must account for.

### Current mutation-producing owners that must be reconciled

#### Cleanup/default/common/P7

Use the cleanup action recorder/ledger from R35-1 through R35-4. A successful/partial removal sets execution mutation; already-absent/no-change refusal does not.

#### Archive creation

Archive publication can persist blob/manifest/catalog/representation state before the engine reaches its normal completed/result publication. If a later failure leaves that representation behind, set execution mutation at the publication transition and retain enough engine-specific evidence (archive identity/publication phase) for the durable audit/recovery path to explain what exists.

Do not label harmless temporary staging as a surviving mutation if the engine removes it before propagation.

#### Archive hot reclamation

A hot file unlink is destructive and currently uses raw durable unlink sequencing. Route it through transition-aware removal truth from R35-2 so an unlink followed by durability failure is recorded as mutation with the exact affected action/path before propagation.

#### Restore

`mkdir`/container publication and `os.replace(temporary, destination)` are persistent installation transitions. Mark/record mutation immediately after a transition succeeds and before chmod/fsync/failpoints can raise. A post-replace failure must identify the installed destination/action; a pre-replace failure must not fabricate restored bytes/mutation.

#### Deduplication

Keep the existing immediate `result.mutated = True` after successful alias `os.replace`. Add current-action evidence before a later failpoint/fsync can raise so the audit says which alias changed and the exact reclaimed-byte amount it can substantiate. Do not convert the operation into a cleanup removal outcome merely for bookkeeping.

#### Campaign-state maintenance

- after `prune_events` returns a positive prune count, set execution mutation before a later action can fail;
- a zero-prune result is not mutation;
- after a successful `VACUUM`, set execution mutation before any later action/finalization failure can make the outer exception path decide status.

### Mandatory acceptance matrix

Using real engine owners and bounded failpoints immediately **after** the named transition:

- `already_absent` cleanup action followed by a later pre-mutation failure -> execution/audit refused, `mutated=false`;
- cleanup removal then later failure -> partial, `mutated=true`;
- archive publication survives then injected later failure -> partial/mutated with representation/phase evidence; pre-publication failure -> no fabricated mutation;
- archive hot unlink then durability failure -> partial/mutated with exact action evidence;
- restore `os.replace` succeeds then fsync/chmod failure -> partial/mutated with destination evidence; pre-replace failure -> no fabricated mutation;
- dedup alias replacement then failpoint/fsync failure -> partial/mutated and current alias/action evidence present;
- positive event prune then later failure -> partial/mutated; zero-prune then later pre-mutation failure does not become partial because of the maintenance action;
- successful vacuum then later failure -> partial/mutated.

For every exceptional case, durable audit is attempted before propagation under the existing audit-degradation contract. Do not count successful-but-nonmutating terminal actions as mutation merely to make the tests pass.

## R35-6 — converge recursive removal and traversal documentation onto truthful owners

Revision 34's direction remains binding and is made explicit here:

- consequential cleanup routes through the canonical typed/ledger implementation only;
- the public exported `remove_durably(path) -> bool` compatibility surface, if retained, becomes a thin adaptation over the canonical safe mechanism where its bool contract can be preserved without hiding partial failure; it may not own a second `shutil.rmtree` recursive algorithm;
- partial mutation from the canonical implementation propagates rather than being converted to `False`;
- if a compatibility edge cannot be preserved without changing supported external behavior, evidence triggers a bounded compatibility-design reopen rather than silently deleting/repurposing the export;
- retire unreachable unsafe private recursion after callers move;
- `storage.trust.walk_contained()` documentation must describe a read-only/planning traversal helper and canonical mount-policy ownership, not claim to be “the single traversal primitive every recursive storage action uses” when destructive owners use descriptor-relative walkers;
- update the storage specification where needed to state the cross-engine execution mutation rule and actual destructive traversal ownership; regenerate the committed PDF derivative whenever Markdown changes.

Structural acceptance must prove consequential callers do not bypass the canonical typed path and the public wrapper no longer owns independent recursive traversal.

## R35-7 — real-owner acceptance matrix; semantic-owner replacement cannot establish owner claims

The following claims must be established through the actual production owner boundary. Instrument only the lowest filesystem/trust/failpoint seam needed to create the counterfactual.

### Cleanup executor / default / generic / common

1. default `engine=None`: a genuinely authorized non-directory action unlinks successfully and parent durability fails; prove real `StorageExecutor.run`, record, finalize/audit, exact bytes and propagated cause. The test is invalid if no unlink occurred.
2. generic recursive directory: known prefix removed, later observation/unlink/rmdir/fsync/close fails; exact partial evidence.
3. fully certified common subtree: same post-prefix failure and durability/close variants through `remove_certified_subtree` reached by real `_cleanup_engine`.
4. individually-authorized common subtree: earlier member succeeds, later member fails before its own mutation; earlier exact bytes persist, later member retained.
5. matching pre-first-mutation failures for each path do not fabricate mutation.

### Trust/race boundaries

6. top-level and nested same-device mount substitution from R35-1.
7. directory-to-symlink swap for generic and fully certified common subtree through the real executor.
8. individually-authorized file-to-symlink replacement from R35-2B.

### P7

9. zero-credit file/empty-directory/hard-link mutation followed by contradiction or failure through the real P7 session/executor/audit.
10. typed partial contradiction in attempt A -> later A withheld, independent attempt B proceeds.
11. exceptional post-mutation failure in attempt A -> action recorded, execution stops, no later A/B, primary cause survives session cleanup.
12. complete target identity for file+directory and spent capability remain pre-syscall guards.

### Other engines

13. archive-create publication, hot reclamation, restore, dedup and maintenance transition cases from R35-5.

Keep focused helper/unit tests where useful, but they do not substitute for these owner-boundary claims.

The monkeypatch-liveness guard must continue to prove that patched production names exist **and** the relevant production path actually reads/calls them; mere module attribute existence is not sufficient if a dead alias can remain defined. For acceptance-critical failpoints, assert the failpoint fired.

## R35-8 — exact-candidate final acceptance remains mandatory and is broadened by the actual affected surface

After the last executable/test edit, bind all evidence to the exact executable commit/tree.

### Focused/current repair

Run all focused R22-R35 storage/P7 namespace, state/proof/release/root/target identity, capability, mutation-outcome, zero-credit, recursive race/mount, single-file transition, close/session cleanup, cross-engine mutation-status, interruption/retry, concurrency and failure counterfactuals added or affected by this work.

### Complete storage suites

```text
tests/test_mlff_storage_reset_core.py
tests/test_mlff_storage_reset_integration.py
```

### Known affected current-owner regressions

At minimum retain the previously named set:

```text
tests/test_mlff_target_size_p4f_storage_docs_structure.py
tests/test_mlff_target_size_p6_destructive_closure.py
tests/test_mlff_p7_r11_repair_acceptance.py
tests/test_mlff_p7_r12_repair_acceptance.py
tests/test_mlff_p7_r13_authority_acceptance.py
tests/test_mlff_campaign_cli.py
```

Because Revision 35 explicitly affects archive/restore/dedup/maintenance behavior, reference/affected-surface analysis must additionally include every maintained test module that exercises `archive_create_engine`, `archive_reclaim_engine`, `archive_restore_engine`, `dedup_engine`, `campaign_state_maintenance_engine`, or their CLI commands. Do not silently omit such a module merely because it was not in the earlier storage-only list. Record the resolved added node/file set in final evidence.

### Repository/static/document checks

- maintained-suite `pytest --collect-only -q`;
- compile/import checks for every changed Python module;
- `git diff --check` and repository-required static checks;
- structural guard for pathname recursive-destructive regressions and consequential remover bypasses;
- strengthened monkeypatch/failpoint liveness guard;
- source/reference scan proving all mutation-producing `StorageExecutor` engines establish explicit mutation truth at persistent transition points and no exceptional path relies on `completed` as mutation evidence;
- affected Markdown/PDF source/derivative validation.

Serena/Semgrep may be used when locally available for caller/variant analysis; they remain optional methodology under this Protocol-5.10 workplan. If unavailable, equivalent AST/text/reference inspection establishes the structural claim. Tool absence is not a blocker.

### Fresh final acceptance

1. record exact executable commit and tree after the final executable/test edit;
2. re-derive the affected surface from that assembled candidate, including new archive/dedup/maintenance dependencies;
3. run focused repair nodes;
4. run complete core and integration suites;
5. run the known affected current-owner regressions plus every newly implicated maintained node/file;
6. run collect-only/static/compile/diff/document checks;
7. run a fresh complete affected regression/integration pass on the exact final tree after all fixes are assembled;
8. record command/node selection and pass/fail/skip summaries;
9. if a later successor changes only workplan/docs/generated PDF, compare it exactly against the executable-evidence tree before reusing functional evidence.

A required command that did not execute is not a pass. Whole-repository behavioral pytest remains conditional on unbounded final impact or independent repository policy. External DFT, long GPU production, and environment-specific HPC/shared-storage qualification remain deferred and nonblocking.

## Implementation sequence

### Stage A — trust + transition-aware cleanup primitives

Implement R35-1, R35-2 and the recursive/session portions of R35-3 as one coherent safety stage:

- canonical opened-descriptor mount decision including top-level roots;
- transition-aware single-file unlink/durability;
- typed current-entry authority for individually authorized common members;
- ledger-aware observation and descriptor/session close handling;
- canonical remover/public-wrapper convergence needed by these changes.

Run focused mount/symlink/single-file/close tests and stage-local storage regression before continuing.

### Stage B — explicit execution mutation truth across every engine

Implement R35-5 with the minimum local changes in cleanup, archive/reclaim/restore, dedup and maintenance owners. The shared executor consumes the explicit mutation fact; engine owners establish it at their persistent transitions and preserve engine-specific action/phase evidence.

Run stage-local affected regression for each touched engine plus the shared executor.

### Stage C — real-owner acceptance closure

Implement only the test/fixture/failpoint work required by R35-4 and R35-7. Do not replace semantic owners with functions that return/raise the desired result when the claim is about that owner's real behavior.

### Final assembled closure

Perform R35-8 exact-candidate reconciliation, affected-surface expansion, fresh affected regression/integration, static checks and document validation.

## Initially affected surface

Expected executable surface is now explicit:

- `mdstats/training_data/storage/trust.py` — opened-descriptor mount decision and truthful traversal ownership;
- `mdstats/training_data/storage/durability.py` — transition-aware unlink/durability seam where needed;
- `mdstats/training_data/storage/outcome.py` — only minimal ledger/action-evidence generalization if justified;
- `mdstats/training_data/storage/executor.py` — canonical cleanup recursion, single-file/common-member truth, public remover consolidation, exception-time settlement;
- `mdstats/training_data/qualification/store.py` — P7 opened-child mount use, observation failure transport, session close/invalidation semantics;
- `mdstats/training_data/storage/commands.py` — cleanup session finalization and real P7 partial routing;
- `mdstats/training_data/storage/archive.py` — archive publication/hot-reclaim/restore transition truth;
- `mdstats/training_data/storage/dedup.py` — post-replace current-action evidence while preserving existing immediate execution mutation flag;
- `mdstats/training_data/storage/maintenance.py` — explicit prune/vacuum execution mutation truth;
- `mdstats/training_data/storage/__init__.py` — only if public remover export/documentation needs reconciliation;
- storage core/integration tests plus every affected current-owner regression discovered under R35-8;
- `docs/specs/training_data/mlff_storage_management_spec.md` and its PDF derivative if contract wording changes.

Final affected-surface analysis may broaden this list. It may not silently narrow a named owner or mandatory test.

## Redesign triggers

This remains implementation rework under Revision 30 unless concrete evidence proves one of these:

- supported public Python `>=3.10`/POSIX primitives cannot realize the opened-descriptor mount decision plus fd-relative/no-follow destructive descent required by the accepted trust boundary;
- the cleanup action ledger cannot represent required mutation truth without changing the frozen four removal outcomes;
- the shared execution result cannot truthfully represent non-removal engine mutation without an incompatible public schema change;
- preserving the exported `remove_durably` compatibility contract while removing its independent recursive implementation is impossible for a supported external consumer;
- current owner/synchronization contracts make the required final typed common-member or P7 authority boundary impossible rather than locally repairable.

If triggered, reopen only the invalidated decision with evidence. Do not use a difficult test fixture or local implementation inconvenience as a redesign trigger.

## Snapshot-complete handoff

The current supplied task authority after Revision 35 is:

1. `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md` — broader frozen owner-driven storage architecture/non-goals;
2. `STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md` — complete accepted final-apply design;
3. `docs/specs/training_data/mlff_storage_management_spec.md` — current product contract;
4. **this file** — complete current bounded implementation/review obligations, including every still-binding Revision-31 through Revision-34 correction;
5. `AUTHORITY_REVISION_35.md` / `AUTHORITY.md` — current disposition/navigation.

Revision 31-34 review/authority files remain historical provenance only. No current requirement depends exclusively on them, Git history, prior conversation, or local Serena/Semgrep state.

**Design/workplan disposition:** Revision 30 remains **CLOSED / implementation-ready**; the current bounded implementation handoff is **Revision 35 / reopened for implementation**.

**Reviewed executable disposition:** `557d32b84c5934096c95ba3ea1d33ed1714d165b` / tree `349a8cb9ac7cee653733f397f196d1426f6a7726` remains **NO-PASS** pending Revision-35 implementation and exact-candidate acceptance.
