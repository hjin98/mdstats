---
kind: implementation-workplan
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1-R38
parent_workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.12.0
status: planned
reviewed_date: 2026-09-04
reviewed_current_executable_commit: 38b37f6761d30c66ec29e27abf8f2ee3a311f804
reviewed_current_executable_tree: c5918d5db992c42b144b7770d100c160f9d417f7
reviewed_branch_head_at_design: 3c7160b82b8b32e21d79872e2bbaaab0f62890de
supersedes_current_handoff: Revision 37 / IR19 and its plan-closure refinement
scope: concrete reduction of the current storage cleanup/execution topology while preserving owner authority, plan revalidation, filesystem trust, P7 release semantics, transition truth, archive/restore integrity, and truthful audit outcomes
---

# Storage/I-O simplicity consolidation — Revision 38

## Objective and disposition

The storage reset has crossed the convergence boundary where another local repair would be the wrong engineering method. The original storage problem remains valid, but the implementation has accumulated mechanisms whose primary purpose is now to keep other mechanisms synchronized. The next implementation pass therefore **reduces the architecture first** and fixes remaining defects by altering the surviving canonical owners rather than adding another wrapper, classifier, fallback, compatibility path, state machine, or recursive remover.

The governing simplicity rule is:

> **One semantic authority, one explicit operation path, one persistent-transition owner.**

For a proposed repair, implementation must first ask whether the defect disappears by deleting, merging, narrowing, or altering an existing mechanism. New machinery is justified only when repository evidence shows that no existing owner can satisfy a required product invariant cleanly. Any new helper/type/module must replace more consequential complexity than it adds; a new abstraction that merely mediates between existing abstractions is nonconforming.

This is a **design consolidation**, not a weakening of the storage safety model. The accepted owner/currentness, P7 release, filesystem trust, durability/recovery, and truthful-outcome requirements remain binding.

## 1. Original problem versus the implementation we actually built

The parent workplan's original problem was straightforward:

1. retire stale STOR-era pathname/lifecycle policy;
2. ask the real P1-P7/CampaignStore/cache owners what exists, what is current/restartable, and what is disposable or transformable;
3. form an immutable owner-bound plan;
4. revalidate owners, policy, protection closure, and filesystem identity immediately before consequence under storage/owner synchronization;
5. perform safe cleanup/cache eviction or the genuinely different archive/dedup/restore operation;
6. report what actually changed and preserve restart-equivalent product state.

The parent workplan explicitly required the **minimum justified number of policies/state machines** and forbade storage from reimplementing P3/P5/P7 currentness semantics. The architecture it asked for was essentially:

```text
real owners
 -> owner-driven inventory
 -> policy
 -> immutable owner-bound plan
 -> synchronized fresh revalidation
 -> consequential operation
 -> truthful bounded audit
```

The current implementation satisfies much of the semantic side of that design, but the cleanup execution side became over-engineered.

| Original requirement | Current realization | Revision-38 decision |
| --- | --- | --- |
| Real owners are semantic authority | `owners.py` + `inventory.py` expose current owner views, dependencies, typed nodes, P7 exact authorizer, state/root/path identities | **Preserve.** This is the correct authority layer. Do not create another cleanup authority model. |
| Immutable plan + fresh apply-time revalidation | `plan.py` binds policy identity, owner-state digest, protection closure, coverage, typed certified nodes, root/path identities, exact authorizer and target filesystem identity | **Preserve and slightly strengthen.** Move the remaining cleanup action/view eligibility checks here instead of re-deriving them later. |
| One common execution envelope | `StorageExecutor.run` correctly owns lease/barriers, resnapshot, revalidation, admission, settlement and audit, but also owns a default destructive cleanup engine | **Delete the default destructive engine.** `StorageExecutor` becomes shell-only and every consequence supplies an explicit engine. |
| Cleanup dispatch must fail closed | A separate `cleanup_domain.py` now contains family gate, classification objects, semantic classes, supported-domain sets and dispatcher preflight because default and production cleanup drifted | **Delete the parallel state machine.** The problem it solves disappears with one cleanup engine and stronger existing plan revalidation. |
| Safe recursive deletion | Generic planned removal, certified-subtree removal, and P7 released-directory removal each implement overlapping recursion, mount checks, descriptor lifetime, final `rmdir`, durability and mutation accounting | **Collapse to one cleanup mutation kernel.** Keep one recursion and delete the other algorithms. |
| P7 released scratch requires owner-specific authority | `ReleasedAttemptSession`, authenticated state/proof/root identity, proof-as-upper-bound and same-attempt invalidation are real requirements, but P7 also owns its own filesystem deletion implementation | **Keep P7 authority acquisition; delete P7 deletion mechanics.** P7 supplies a live capability and proof to the shared cleanup kernel. |
| Partial/open containers must not become blanket ownership | `authorized_members()` plus `remove_certified_subtree(... members, refusals ...)` supports selective recursive cleanup at mutation time | **Delete selective recursive cleanup.** Current reclaimable owners already expose safe children as independent views or expose a `CLOSED` tree. `CONTAINER` remains non-recursive for cleanup. |
| Mutation truth must survive post-transition failure | Cleanup uses transition callbacks/fallback history while archive/restore use the centralized atomic-publication callback to expose `os.replace` before later fsync/readback failures | **Differentiate necessary from accidental machinery.** Cleanup owns unlink/rmdir directly and needs no callback. Retain the single durable-publication callback where it closes several genuine archive/restore post-`replace` windows with one mechanism. |
| Compatibility only where product requires it | `remove_durably`, classifier symbols and mutation helpers are exported; maintained repository uses are overwhelmingly implementation/tests | **Census then remove.** Tests do not justify preserving a destructive public compatibility surface. |

The central diagnosis is therefore:

> The difficult requirements are owner authority, no-follow/mount-safe destructive access, P7 release proof, apply-time revalidation, and truthful partial mutation. The excessive complexity comes from implementing those requirements several times and then inventing classification, compatibility, and test machinery to keep the copies aligned.

## 2. Frozen target architecture

The target product path is:

```text
owner adapters
  -> StorageInventorySnapshot
  -> StoragePolicy
  -> StoragePlan
  -> StorageExecutor.run(explicit_engine)
       storage-operation lease
       owner barriers
       fresh resnapshot
       revalidate_plan
       admission revalidation
       explicit engine
       settlement + audit
  -> operation engine
       cleanup -> one cleanup engine -> one cleanup mutation kernel
       archive -> archive engine
       restore -> restore engine
       dedup -> dedup engine
       maintenance -> existing owner maintenance path
```

### 2.1 `StorageExecutor` is a transaction/revalidation/audit shell

`StorageExecutor.run` owns only common execution concerns:

- invocation-local apply authorization;
- storage-operation serialization;
- owner activity/publication barriers;
- fresh owner resnapshot;
- `revalidate_plan`;
- admission revalidation when applicable;
- exception-to-terminal-status settlement from explicit mutation truth;
- bounded audit publication/retention.

It does **not** own cleanup classification or filesystem deletion.

The `engine` argument becomes mandatory for consequential execution. Remove the `engine=None` destructive behavior rather than trying to make it safer. Current production command paths already pass explicit cleanup/archive/reclaim/restore/dedup engines, so the default path is compatibility/test surface rather than required product architecture.

Operation-specific physical ownership checks stay with the explicit operation engine where they already differ materially. Do not invent a universal authorization registry inside `StorageExecutor` merely to make every engine look symmetric.

### 2.2 `revalidate_plan` is the canonical action-to-owner binding gate

The current plan already binds the information `cleanup_domain.py` later re-derives: owner state identity, `safe_reclaimable`, cache flags/class, coverage, typed nodes, retained members, exact authorizer, root/path identities, protection closure, policy identity and target filesystem identity.

Alter the existing `revalidate_plan` cleanup path so it closes the remaining malformed-plan cases directly:

- for `ACTION_REMOVE` and `ACTION_EVICT_CACHE`, the action's `artifact_id` must resolve to a fresh `OwnerArtifactView`;
- that view's canonical `path` must equal the action target exactly;
- `ACTION_REMOVE` requires the fresh view to remain `safe_reclaimable`;
- `ACTION_EVICT_CACHE` requires the cache tier plus `REUSABLE_CACHE_INDEX`, exact reconstructibility and owner evictability;
- the existing owner-binding digest, owner-state identity, protection closure and target filesystem identity checks remain authoritative;
- if any of those facts changed, the plan is stale/refused before the engine mutates anything.

Do this in `plan.py`; do **not** create another cleanup validator/classifier to call from it.

### 2.3 One cleanup engine; no semantic-class framework

The cleanup engine has one small direct dispatch over already-revalidated product facts. Equivalent exact syntax is delegated, but the logic is frozen:

```text
require plan.policy.action == cleanup before action iteration

for action in plan order:
    maintenance action
        -> existing CampaignStore maintenance owner

    remove / evict action
        -> get the already-revalidated owner view
        -> apply the ordinary physical ownership boundary

        P7 exact authorizer
            -> acquire/reuse live P7 attempt capability
            -> shared cleanup mutation kernel

        unknown non-empty exact authorizer
            -> fail closed; no generic fallback

        planned leaf (regular file or symlink entry)
            -> shared cleanup mutation kernel

        planned directory + SubtreeCoverage.CLOSED
            -> shared cleanup mutation kernel

        anything else, including SubtreeCoverage.CONTAINER
            -> refuse/fail closed; no recursive cleanup
```

There is no `CleanupClassification`, no `CLASS_*`, no supported-domain registry, and no default-versus-production domain alignment test. A short local wrong-action guard is sufficient because there is only one cleanup engine.

Unknown action kinds must be rejected before the first destructive transition of the plan. Implement this as a small direct preflight in the cleanup engine or an equivalent simpler source shape; do not create a handler registry solely to prove dispatch completeness.

### 2.4 `CONTAINER` is not a cleanup mutation mode

The current owner topology removes the need for runtime selective recursion:

- P7 released attempt scratch is already emitted as one reclaimable owner view per top-level released member; directory members are `CLOSED` and carry exact P7 authority;
- a CampaignStore orphan directory is `safe_reclaimable` only when the owner has certified it closed;
- abandoned storage-owned restore staging is `CLOSED + owner_exclusive`;
- P3/P4/P5/P7 generation/root/container views that are merely `CONTAINER` are retained/reporting/dependency surfaces and are not blanket cleanup authority.

Therefore cleanup never calls `authorized_members(view)` to obtain `members + refusals` and never selectively mutates inside an open container.

If a future owner wants some children of a `CONTAINER` to be reclaimable, the default solution is to expose those children as independent owner views using the existing owner model, not to reintroduce a selective recursive cleanup framework. Reopen Design only if a real owner cannot express the required product behavior that way.

`StorageInventorySnapshot.authorized_members()` may remain for archive/dedup read-only member collection where a complete member set is genuinely part of those operations. Its P7 exact-authorizer branch and `qualification.store.authorize_released_attempt_member()` should be deleted if the final maintained-consumer census confirms, as the current product model indicates, that no archive/dedup operation can select P7 released scratch. In all cases, they leave the cleanup mutation path.

## 3. One cleanup filesystem mutation kernel

Revision 38 authorizes exactly one consequential cleanup implementation for unlink/rmdir recursion.

### 3.1 Reuse the strongest existing code; do not build a fourth remover

Use the current plan-bound descriptor logic in `storage/executor.py` as the primary mechanical base:

- anchored componentwise no-follow descent;
- plan-bound target identity;
- opened-descriptor mount trust;
- descriptor-relative child operations;
- final name-versus-opened-descriptor identity comparison before `rmdir`;
- action-local `MutationLedger`;
- structured `PartialMutationError` transport.

Merge into that one implementation the P7-specific **typed proof constraint**, not the P7 recursive algorithm itself.

Do not write a fresh recursive walker beside the existing three and migrate callers gradually. The consolidation stage must move callers and delete superseded recursion in the same stage so there is no shadow fallback.

### 3.2 Kernel inputs are existing authority, not a new policy object

Do not create another cleanup action/capability class. The kernel needs only existing data:

- an authenticated parent descriptor plus entry name, or an anchored ordinary path from which that parent is acquired;
- `PlannedAction.filesystem_identity` for the target entry;
- optional owner-certified typed descendant map for a `CLOSED` tree;
- `owner_exclusive=True` for the one accepted closed-tree case where exclusivity itself is the owner's ownership statement;
- the existing `MutationLedger`/`MutationOutcome` semantics.

Suggested low-complexity shape, not frozen names:

```text
ordinary cleanup:
    no-follow open parent from plan.workspace
    -> remove leaf or closed tree from parent fd

P7 cleanup:
    borrow session.attempt_fd
    -> remove the same leaf or closed tree from parent fd
```

The P7 attempt descriptor is borrowed, never closed by the kernel. Every descriptor the kernel opens itself is owned and closed exactly once by the kernel.

### 3.3 Leaf behavior

For one file/symlink entry:

1. no-follow observe the entry relative to the authenticated parent;
2. compare the required plan identity immediately before mutation;
3. if absent, return `already_absent` with zero mutation/bytes;
4. if kind/identity contradicts the plan, return `refused_no_change`;
5. measure accountable bytes before unlink;
6. call `os.unlink(name, dir_fd=parent_fd)`;
7. immediately after successful unlink, update the ledger/mutation truth;
8. fsync the same authenticated parent;
9. a post-unlink fsync/close failure carries the already-recorded partial mutation.

Cleanup must not call `durable_unlink(... on_unlinked=...)`; the cleanup kernel itself owns both the syscall and the ledger and therefore needs no callback to rediscover its own transition.

### 3.4 Closed-tree behavior

The single recursion must preserve these accepted rules:

- acquire every child directory no-follow relative to its authenticated parent;
- apply the canonical opened-descriptor mount/ownership test before descent;
- never follow a symlink or cross an unresolved/nested mount;
- for owner-certified topology, every live descendant must be present in the certified map with the same kind;
- missing certified descendants are allowed monotonic shrink and grant no new authority/bytes;
- an unexpected descendant, kind change, symlink, special node or mount contradiction stops/refuses using the running ledger;
- for `owner_exclusive` closed storage staging, plain files/directories are owner-owned by construction; symlink/special/mount ambiguity still reduces authority;
- measure before unlink and credit only after successful unlink;
- hard-link identity is de-duplicated action-wide under the existing metric;
- removing an empty/zero-byte namespace entry still marks mutation even when credited bytes are zero;
- fsync the directory whose entries changed;
- keep the authenticated child descriptor live through the final directory-removal boundary;
- immediately before `os.rmdir(name, dir_fd=parent_fd)`, compare the no-follow entry identity with the still-open descriptor;
- only the accepted irreducible POSIX race after that final comparison remains outside the guarantee;
- descriptor close failure never erases a primary mutation failure and is never silently converted to success when it is the only failure.

There is exactly one recursive implementation of these rules in the final tree.

## 4. P7 reduction: keep authority, delete filesystem duplication

P7 is the strongest evidence that specialization and duplication are different things.

### 4.1 Preserve the genuinely P7-specific pieces

Keep in `qualification/store.py`:

- authenticated attempt-state and released-proof reading;
- generation/attempt/release-authority binding;
- proof-as-monotonic-shrink upper-bound semantics;
- strict no-follow attempt-root acquisition;
- plan-bound root/release verification;
- ephemeral `ReleasedAttemptSession` capability;
- read-only authenticated proof lookup on the session;
- one-way close / spent-capability protection;
- same-attempt contradiction invalidation and independent-attempt isolation.

These are owner semantics and cannot be inferred by storage.

### 4.2 Delete the P7-specific deletion implementation

Delete after migration:

- `remove_released_attempt_member` as a filesystem-mutation owner;
- `_unlink_certified_file`;
- `_fsync_after_mutation` if it becomes mutation-only dead code;
- `_remove_certified_directory`;
- `_empty_and_remove_certified_directory`;
- `_close_owner_descriptor` where it exists only for the deleted recursive remover;
- duplicated target-identity/mutation helpers that the shared kernel now owns.

The cleanup engine verifies/acquires the P7 session and supplies the session's authenticated proof/topology plus `attempt_fd` to the same kernel used by ordinary cleanup.

### 4.3 Do not invent a P7 session manager

The current per-attempt session dictionary is sufficient state for two real requirements: proof lookup reuse and same-attempt invalidation. Simplify it rather than replacing it with another class/framework.

Target lifetime:

- one cached live session or cached acquisition refusal per attempt for the execution;
- later same-attempt actions do no filesystem work after invalidation;
- one final session-close site in the cleanup engine;
- one primary-versus-secondary close ranking rule;
- no nested finalizer framework and no blanket close suppression.

If a kernel outcome is `refused_no_change`/`partial_change_refused` because P7 authority was contradicted, invalidate that attempt before later same-attempt work. If a `PartialMutationError` escapes, record the current action first, invalidate the attempt, preserve the original mutation cause, then let `StorageExecutor` settle/audit the execution.

## 5. Transition truth: delete accidental plumbing, retain the one justified shared mechanism

The first R38 draft treated callbacks too broadly. Current source review shows an important distinction.

### 5.1 Cleanup transition truth becomes direct

Because the single cleanup kernel performs `os.unlink`/`os.rmdir` itself, it records the `MutationLedger` immediately after each successful syscall. Remove from cleanup:

- `durable_unlink` callback use;
- post-hoc pathname disappearance inference;
- any `TypeError` signature fallback or manually replayed mutation callback;
- any decision that equates `reclaimed_bytes > 0` with `mutated=True`.

### 5.2 Keep the atomic-publication callback where it is the simplest sufficient mechanism

`durable_publish_bytes/json` performs `os.replace` and then performs fallible parent-fsync/readback/authentication. If a later step raises, a normal return value cannot tell the caller that the replace already happened. The current `on_published` callback solves this same real problem for archive blob, manifest, catalog and restore-journal publication with one centralized mechanism.

Therefore **do not replace it merely for stylistic purity**. Retain one exact callback contract if it remains the smallest implementation after cleanup reduction:

- fires if and only if this invocation's atomic replace succeeded;
- fires immediately after replace, before any later failure;
- all archive/restore phase truth uses that one contract;
- no compatibility fallback fabricates it;
- acceptance-critical tests prove the callback/failpoint is live through the real engine.

Likewise, after cleanup stops using `durable_unlink`, retain `durable_unlink(on_unlinked=...)` only if archive hot reclamation remains its real maintained consumer and centralizing unlink+parent durability is smaller than inlining equivalent logic there. Do not create a new universal transition event framework.

Dedup and maintenance already record their own state-changing transitions directly; preserve that rather than routing them through cleanup machinery.

## 6. Concrete file-by-file repair instructions

### `mdstats/training_data/storage/plan.py`

- Preserve `StoragePlan`, `PlannedAction`, owner-binding digest and existing target revalidation.
- Add the small cleanup remove/evict action-to-owner/path/current-eligibility checks described in §2.2 inside existing plan revalidation.
- Remove `EXECUTOR_ACTIONS` or comments implying `StorageExecutor` itself performs cleanup if no maintained consumer remains.
- Do not add a policy-family registry or new action-class hierarchy.

### `mdstats/training_data/storage/executor.py`

Reduce this module to common execution concerns.

Delete/move out of it:

- `DEFAULT_CLEANUP_DOMAIN`;
- cleanup-domain imports;
- `engine=None` destructive branch;
- `_execute_actions`;
- cleanup-only engine-domain exception handling made obsolete by the deleted classifier;
- `remove_durably` / `remove_durably_outcome` after consumer migration;
- `remove_planned_outcome` as a public/general remover;
- `remove_certified_subtree`;
- generic/parallel recursive deletion functions;
- selective-member `_DescriptorScope` modes needed only by `members/refusals` cleanup;
- cleanup-specific `record_or_reraise` / `record_removal` placement (move with the one cleanup engine if still useful);
- `authorize_path` if final references confirm it exists only for cleanup; perform the ordinary physical boundary check directly in the cleanup engine instead of constructing a second executor object inside that engine.

Keep:

- `StorageExecutionResult`;
- operation identity;
- common run/lease/barrier/resnapshot/revalidation/admission flow;
- settlement/audit/retention behavior;
- `synchronization_for` if it remains the canonical owner-barrier derivation.

Make the engine callable mandatory and invoke it directly after successful common revalidation.

### `mdstats/training_data/storage/cleanup_domain.py`

The current classifier/domain module is superseded.

Preferred realization: replace/rename this module into the **single cleanup implementation** rather than adding another cleanup module. Module count must not increase merely because architecture is being simplified.

Delete:

- `CLASS_EXACT_AUTHORIZER`, `CLASS_OWNER_SUBTREE`, `CLASS_GENERIC_LEAF`, `CLASS_MAINTENANCE`, `CLASS_INVALID`;
- `CLEANUP_SEMANTIC_CLASSES`;
- `CleanupClassification`;
- `StorageEngineDomainError` if no non-classifier consumer remains;
- `require_cleanup_family` as a separate abstraction;
- `classify_cleanup_action` / `classify_cleanup_plan`;
- `require_supported_domain` and supported-domain sets.

Replace with only the one cleanup engine plus its private canonical mutation helpers. If retaining the filename avoids pointless import churn, keeping the filename is acceptable; do not preserve classifier semantics for compatibility.

### `mdstats/training_data/storage/commands.py`

- Keep CLI/policy/context/plan orchestration.
- `storage_cleanup` continues to pass an explicit cleanup engine to `StorageExecutor.run`.
- Remove `PRODUCTION_CLEANUP_DOMAIN`, `_view_node_kind`, local class dispatch and the duplicated `context.executor(policy)` instance used only for `authorize_path`.
- Remove `_apply_released_member` from commands once P7 dispatch is owned by the one cleanup engine.
- Keep `build_cleanup_plan` simple and strict: every eligible decision must resolve back to its owner view; do not silently emit empty owner-state identity when the view is absent.
- Do not add a command-layer router to replace the deleted classifier.

### `mdstats/training_data/storage/inventory.py`

- Preserve cross-owner protection closure and read-only owner inventory.
- Cleanup stops using `authorized_members()` as a mutation authorization API.
- Preserve the generic read-only member enumeration only where archive/dedup genuinely consume it.
- Remove the P7 `authorize_released_attempt_member` branch if the final maintained runtime census confirms no archive/dedup feature selects P7 released scratch.
- Do not introduce a cleanup-specific inventory/capability type.

### `mdstats/training_data/storage/owners.py`

Preserve the existing semantic vocabulary; it is already sufficient:

- `safe_reclaimable` / cache/archive/dedup eligibility;
- `SubtreeCoverage.CLOSED`, `CONTAINER`, `NOT_APPLICABLE`;
- typed `certified_nodes`;
- `owner_exclusive`;
- `exact_authorizer` for P7;
- state/root/path identity.

Do not add a new cleanup enum. If selective cleanup is ever needed, first express the reclaimable child as another owner view.

### `mdstats/training_data/qualification/store.py`

- Preserve P7 authentication/session/proof code from §4.1.
- Delete the duplicate P7 filesystem remover family from §4.2 after migration.
- Remove `authorize_released_attempt_member` if the final non-cleanup consumer census shows it is dead.
- Do not duplicate shared cleanup target-identity, mount, close or mutation-ledger helpers here after consolidation.

### `mdstats/training_data/storage/outcome.py`

Preserve `MutationOutcome`, `MutationLedger`, `PartialMutationError` and the four dispositions. They represent real product states and replace ambiguous booleans/prose. Consolidation should reduce their callers, not weaken them.

### `mdstats/training_data/storage/trust.py`

Keep one canonical implementation for no-follow directory acquisition, opened-descriptor mount trust and final directory identity verification. The cleanup kernel and P7 authority acquisition reuse it. Do not copy these rules into another module.

### `mdstats/training_data/storage/durability.py`

- Keep the crash-durable publication owner.
- Preserve the exact `on_published` transition callback if it remains the lowest-complexity solution for the archive/restore replace-before-fsync failure window.
- Cleanup no longer uses `durable_unlink` to learn mutation truth.
- Remove compatibility/fallback behavior rather than supporting multiple callback signatures.

### `mdstats/training_data/storage/archive.py`, `dedup.py`, `maintenance.py`

Do not redesign these merely because cleanup is being simplified. Preserve their genuinely distinct algorithms and recovery semantics.

Only touch them where needed to:

- remove dead cleanup/shared imports;
- preserve exact transition truth;
- migrate an internal helper whose old cleanup compatibility API is deleted.

### `mdstats/training_data/storage/__init__.py`

Remove public exports for implementation machinery that ceases to exist, including classifier/domain symbols and destructive convenience helpers. Do not keep a compatibility export merely because repository tests imported it.

Limit API cleanup to the affected storage internals; do not turn R38 into an unrelated package-wide API redesign.

### Tests

Delete or rewrite tests whose only product is the superseded machinery, including tests centered on:

- default cleanup engine domains;
- `CLASS_*` / exported cleanup classifier behavior;
- supported-domain/handler equality;
- `remove_durably` compatibility behavior as an API;
- monkeypatching generic/certified/P7 removers separately simply to prove which duplicate path was reached.

Preserve the behavioral claim behind a test when it is real. Examples:

- the old symlink-removal test should exercise the real cleanup path or the one canonical kernel, not force retention of `remove_durably`;
- a P4/cross-store test that used `remove_durably` merely as fixture manipulation should use ordinary test filesystem operations rather than a product compatibility API;
- wrong-family safety needs one real explicit-cleanup-engine guard test, not a matrix proving both a deleted default engine and a deleted classifier agree.

## 7. Required acceptance: prove reduction and behavior together

### 7.1 Structural reduction acceptance

Final source must establish all of the following:

- `StorageExecutor.run` has no destructive default/fallback engine;
- no production consequential apply call uses `engine=None`;
- one production cleanup engine exists;
- `cleanup_domain` semantic classes/classifier/domain sets are absent;
- one and only one consequential cleanup recursive unlink/rmdir implementation exists;
- no P7 recursive deletion implementation remains;
- no generic recursive directory-removal compatibility path remains;
- no cleanup mutation accepts `members + refusals` and decides selective ownership while walking;
- cleanup never recursively deletes a `SubtreeCoverage.CONTAINER`;
- no consequential fallback from unknown/owner-specific authority to generic deletion exists;
- no post-hoc pathname disappearance inference or mutation-from-byte-total inference exists;
- no signature-incompatible `TypeError` fallback fabricates transition truth;
- P7 and ordinary cleanup reuse the same filesystem mutation kernel;
- mutation/trust helpers removed from the architecture are also removed from `storage.__init__`;
- no new storage module/state machine/registry was added solely to replace deleted routing machinery.

Use references plus Semgrep/AST/Serena when available. Any custom structural rule used for acceptance must be proven live against one known-bad and one known-good construct and state its scan scope.

Net line count is not itself a correctness metric, but the named mechanism deletion is mandatory. If the combined production cleanup topology (`executor.py`, cleanup implementation, `commands.py`, P7 removal surface, affected exports) grows materially instead of shrinking, implementation must stop and explain which required invariant forced the growth before review; wrapper relocation is not closure.

### 7.2 Real-owner behavioral acceptance

All safety claims that cross an owner boundary must traverse the real owner -> plan -> `StorageExecutor` -> explicit cleanup engine -> shared kernel path.

Required representative cases:

**Ordinary leaf**

- successful file removal and exact bytes;
- already absent -> completed terminal state, zero mutation/bytes;
- symlink entry removal never touches its target;
- kind/device/inode/size/mtime replacement contradiction survives;
- zero-byte file removal still sets mutation truth;
- unlink succeeds then parent fsync fails -> exact partial outcome/audit.

**Certified/owner-exclusive closed tree**

- complete normal removal;
- unexpected descendant, kind substitution, symlink, special node or mount boundary refuses/stops;
- missing recorded node is tolerated only where monotonic shrink is part of that owner's contract;
- earlier prefix removed then later contradiction/failure -> exact partial bytes/mutation;
- hard-link accounting follows the existing metric;
- directory replacement after opened-descriptor acceptance but before final `rmdir` survives;
- nested/root descriptor close failure preserves primary mutation truth and a close-only failure remains visible.

**P7**

- release authority reseal mismatch;
- attempt-root replacement;
- top-level target identity replacement for both file and directory;
- proof monotonic shrink / interrupted retry;
- live addition and kind change refusal;
- spent/closed session cannot reach a filesystem syscall;
- mutation-time contradiction invalidates later same-attempt actions;
- an independent attempt remains independent;
- P7 file and directory removals demonstrably execute the same kernel as ordinary cleanup;
- post-mutation kernel failure plus session-close failure retains the original primary cause and exact partial action evidence.

**Cross-operation preservation**

- archive blob/manifest/catalog post-`replace` failures retain exact publication phase/mutation truth;
- restore staging/terminal journal and destination transitions remain truthful;
- archive hot reclaim unlink-before-durability failure remains exact;
- dedup alias replacement and maintenance prune/VACUUM transition truth remain intact;
- audit publication failure still degrades audit status without pretending to roll back a mutation.

### 7.3 Exact-candidate final evidence

After the final executable/test edit:

1. record exact executable commit and tree;
2. re-derive the affected surface from the final diff and references;
3. run focused reduction/kernel/P7/transition tests;
4. run complete `tests/test_mlff_storage_reset_core.py` and `tests/test_mlff_storage_reset_integration.py`;
5. run maintained P7 and owner regressions, including the existing P4F storage/docs, P6 destructive-closure, P7 R11/R12/R13 and campaign CLI suites where they remain maintained;
6. include every final-census-discovered maintained caller of `StorageExecutor`, cleanup, archive reclaim, restore, dedup, maintenance, P7 session/proof, or affected durability primitives;
7. run `pytest --collect-only -q`;
8. run changed-module compile/import checks, `git diff --check`, repository-required static checks and conflict-marker scan;
9. rerun the structural/absence checks in §7.1 on the exact final tree;
10. validate affected Markdown and regenerate/validate the committed storage-spec PDF derivative;
11. rerun the complete affected-surface regression/integration set after all executable/test changes are assembled.

External DFT, long GPU production and environment-specific HPC/shared-filesystem qualification remain deferred and nonblocking: R38 changes storage control/mutation topology, not scientific algorithms or production-scale performance policy.

## 8. Implementation sequence

### Stage A — make the plan/executor architecture truthful

1. Change `StorageExecutor.run` to require an explicit engine.
2. Remove default cleanup execution and its domain/error handling.
3. Strengthen existing `revalidate_plan` with exact cleanup action/view/path/eligibility checks.
4. Convert/remove tests that exist only for the deleted default engine/classifier boundary.
5. Run stage-local executor/plan/command affected regression.

**Stage-A exit condition:** there is one production cleanup engine and no default destructive execution path; malformed cleanup action authority is closed by existing plan revalidation rather than a classifier layer.

### Stage B — collapse cleanup routing and recursion in one edit set

1. Replace/delete `cleanup_domain.py` classifier contents and establish the one cleanup implementation without increasing storage module count.
2. Remove class/domain routing from `commands.py` and move the one cleanup engine to its canonical home.
3. Consolidate generic/closed-tree descriptor recursion into one kernel using current plan-bound mechanics.
4. Route ordinary leaf/CLOSED cleanup through it.
5. Route P7 live-session actions through the same kernel.
6. Delete generic compatibility recursion, certified-subtree recursion and P7 recursive removal in the same stage.
7. Remove cleanup use of `authorized_members(... members, refusals ...)` and refuse `CONTAINER` recursion.
8. Run real-owner ordinary/P7/tree race/failure regression before continuing.

**Stage-B exit condition:** source inspection can point to one recursive cleanup implementation and one cleanup engine; there is no fallback path waiting for a later cleanup stage.

### Stage C — reduce lifetime/transition/API debris

1. Simplify P7 session handling to one per-attempt cache/refusal plus one close-ranking site; do not add a manager class.
2. Remove cleanup transition callbacks/fallbacks; direct kernel syscalls own ledger truth.
3. Preserve the one justified durable-publication callback for archive/restore unless an actually smaller equivalent is demonstrated.
4. Remove dead `remove_durably`/classifier/destructive helper exports and migrate tests/fixtures.
5. Remove P7 planning/member-authorizer traversal if the final real-consumer census proves it dead outside superseded cleanup/tests.
6. Run stage-local P7 lifetime, archive/restore transition and package import regression.

### Stage D — reconcile current specification and delete implementation-shaped tests

Update `docs/specs/training_data/mlff_storage_management_spec.md` so current normative prose describes:

- one explicit cleanup engine;
- one cleanup mutation kernel;
- plan revalidation as the action-to-owner binding gate;
- `CONTAINER` as non-recursive cleanup authority;
- P7 as authority provider to the shared kernel;
- one justified atomic-publication transition callback rather than a universal transition framework.

Delete prose that freezes the obsolete default engine, cleanup semantic classes, parallel supported-domain sets, or three recursive deletion paths. Preserve behavioral trust/P7/outcome/durability guarantees.

Regenerate the PDF derivative and run documentation checks.

### Final assembled closure

Perform final accepted-contract reconciliation, structural reduction proof, affected-surface derivation, complete affected regression/integration and exact-candidate audit. Close/archive the storage reset only if the resulting code both preserves the hard semantics and materially reduces the number of consequential mechanisms.

## 9. Implementation authority

### Frozen

- The original product goal: owner-driven safe storage transformation with truthful persistent outcomes.
- One semantic authority, one explicit operation path, one persistent-transition owner.
- `StorageExecutor` is common transaction/revalidation/audit shell only; no default cleanup engine.
- `revalidate_plan` is the canonical cleanup action-to-owner/path/current-eligibility gate.
- One production cleanup engine; no parallel cleanup classifier/domain state machine.
- Cleanup recursively mutates only owner-authorized `CLOSED` trees; `CONTAINER` is never blanket/selective recursive cleanup authority.
- One consequential cleanup unlink/rmdir recursion shared by ordinary and P7 cleanup.
- P7 owns release/proof/root/currentness/session semantics and does not own a second filesystem deletion algorithm.
- Existing four cleanup outcomes and exact mutation/byte semantics.
- No-follow descriptor-relative mutation, mount trust and final directory identity rules.
- Persistent transition truth is established at the transition, never inferred from later pathname state or byte totals.
- The existing atomic-publication callback may remain because evidence shows it closes several real replace-before-postcheck failure windows with one mechanism; do not replace it with more machinery without a demonstrated simplification.
- Archive/dedup/restore/maintenance remain specialized only where their algorithms/recovery semantics are materially distinct.
- No new persistent authority/control plane, handler registry, cleanup state machine, compatibility framework or temporary parallel remover.
- Tests/historical workplans are not compatibility authority for obsolete internal destructive APIs.
- Future ordinary defects governed by these invariants are implementation fixes in the surviving owner/kernel, not grounds for another numbered architecture revision.

### Delegated

- Exact final filename of the single cleanup implementation (`cleanup_domain.py` repurposed versus one-for-one rename to `cleanup.py`). Do not increase module count merely for cleanliness.
- Exact private function names and whether leaf/tree entry points are two small functions over one private recursion or one function with a simple branch.
- Exact source placement of cleanup result-recording helpers.
- Whether `durable_unlink` is retained solely for archive hot reclamation or inlined there, based on smaller total implementation while preserving exact transition truth.
- Removal of `authorize_released_attempt_member` after the required final real-consumer census.
- Local exception wording and test organization.

### Reopen only on evidence

Reopen only the affected design surface if implementation establishes one of these facts:

1. a maintained supported external/public consumer truly requires destructive `StorageExecutor.run(engine=None)` and cannot be migrated safely;
2. a current owner must safely reclaim a strict subset of a `CONTAINER`, cannot expose those children as independent owner views, and refusing the operation would violate a required product behavior;
3. P7 cannot spend its authenticated live capability through the shared kernel without weakening release/root/target/proof semantics;
4. a materially distinct filesystem/platform requirement makes one shared cleanup recursion less safe/supportable than justified specialization;
5. atomic publication transition truth cannot be preserved by the existing callback without a demonstrably simpler replacement.

Old tests, historical review language, implementation inconvenience, code-size aesthetics, or absence of optional Serena/Semgrep/Hypothesis tooling are not redesign evidence.

## 10. Handoff closure

This Revision-38 file is the complete current architectural-reduction contract. Revision 30-37 and IR review/reopen documents remain historical evidence only and are not required to implement this target.

The supplied current handoff is:

- `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md` — original owner-driven product architecture and non-goals;
- this Revision-38 plan — concrete current reduction architecture and repair obligations;
- `docs/specs/training_data/mlff_storage_management_spec.md` — behavioral storage contract, with obsolete implementation-topology wording to be reconciled by Stage D;
- current source/tests — evidence of the implementation to reduce.

Snapshot-loss counterfactual: with Git history, prior chats, and R30-R37/IR files removed, this set still recovers the original problem, protected semantics, mechanisms that must survive, mechanisms that must be deleted, exact reduction topology, acceptance boundaries and genuine redesign triggers.

**Design/workplan disposition: CLOSED / implementation-ready under Revision 38.**

**Implementation disposition: PENDING. The reviewed current executable is `38b37f6761d30c66ec29e27abf8f2ee3a311f804`, tree `c5918d5db992c42b144b7770d100c160f9d417f7`; it is the pre-consolidation implementation to reduce, not the accepted target architecture.**
