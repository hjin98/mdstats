---
kind: implementation-workplan
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1-R38
parent_workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.12.0
status: planned
supersedes_current_handoff: Revision 37 / IR19 and its plan-closure refinement
baseline_executable_commit: 7aa938d71361d2cb2ce6e370165a9a12566669f3
baseline_executable_tree: 5fd91f30672fb7d9a2be89d6e0fdc261619509aa
scope: bounded storage implementation-topology simplification preserving accepted owner, safety, durability, recovery, and truthful-outcome semantics while deleting redundant execution, classification, recursive-mutation, compatibility, and finalization machinery
---

# Storage/I-O simplicity consolidation — Revision 38

## Objective and protected concerns

The storage reset has reached a design-convergence boundary. The product requirements are legitimate, but repeated repairs have accumulated parallel cleanup execution paths, semantic classification/preflight machinery, several recursive deletion implementations, mutation-truth adapters, compatibility fallbacks, session/finalizer policies, and structural tests whose purpose is to keep those mechanisms synchronized. The implementation is now spending substantial complexity proving that its own abstractions agree with each other.

The core product problem is much smaller:

> **Safely transform campaign-owned filesystem representation without letting storage become a second scientific/currentness authority, and report exactly what persistent transitions this execution actually caused.**

The storage subsystem does not need a general destructive framework to solve that problem. It needs one semantic decision from the real owner, one revalidated execution shell, one cleanup filesystem-transition owner, and specialized representation engines only where the operation is materially different.

The durable outcome of this work is therefore not another patch layer. It is deletion and consolidation until the consequential path is recoverable from this simple model:

```text
real P1-P7 / CampaignStore / cache owner
  -> owner says what is disposable or transformable and why
  -> immutable owner-bound plan
  -> StorageExecutor: serialize + resnapshot + revalidate + admit + audit
  -> exactly one explicit operation engine
       cleanup -> one cleanup engine -> one cleanup mutation kernel
       archive/dedup/restore/maintenance -> their genuinely distinct engine
  -> exact transition truth -> terminal outcome/audit
```

Protected concerns remain unchanged:

- storage never infers scientific identity, selected membership, currentness, publication/qualification state, restartability, or deletion eligibility when a semantic owner exists;
- external user/source/reference inputs are never destructively consumed by campaign storage;
- owner/currentness ambiguity, stale plans, unsupported filesystem capability, symlink/special-node substitution, mount ambiguity, or identity contradiction fail toward retention/refusal;
- P7 released scratch remains authorized only by freshly authenticated P7 state/proof/root/target authority on a live capability;
- cleanup cannot transfer authority to a replacement object or a different mounted tree;
- persistent transition truth is recorded at the transition, not reconstructed from a later pathname or from byte totals;
- partial mutation, zero-byte mutation, already-absent state, no-change refusal, and audit-publication failure remain distinguishable and truthful;
- archive/restore/dedup/maintenance retain their accepted owner, durability, recovery, and integrity semantics;
- Python `>=3.10` and the accepted descriptor-pinned POSIX threat boundary remain unchanged;
- no new persistent descriptor/inode/release/retry registry or other storage control plane is introduced.

## Diagnosis: the actual failure is duplicated authority and duplicated mechanism

The recurring defects are not independent filesystem curiosities. They arise because one product invariant has been represented by too many cooperating mechanisms.

The current shape contains, or has recently contained, all of the following:

- a default `StorageExecutor` destructive cleanup path in addition to the production cleanup engine;
- a separate cleanup semantic classifier, plan-family preflight, supported-domain set, and dispatcher that exist largely to keep those two execution paths from drifting;
- generic recursive removal, common/certified-subtree removal, and P7 released-subtree recursion, each carrying overlapping no-follow, mount, identity, descriptor-lifetime, durability, and mutation-accounting responsibilities;
- transition callbacks and compatibility/fallback logic added because state-changing syscalls are hidden inside helpers that can fail after the transition but before the caller learns it happened;
- session caches, invalidation paths, and layered finalizers whose close-error ranking must be kept consistent with mutation truth;
- tests and structural scans that patch or inspect implementation seams which later stop being the real production seam.

This is the wrong decomposition. The solution is to remove the duplicated responsibilities rather than continue adding guards that prove the duplicates agree.

## Frozen new storage architecture invariant

### 1. One semantic authority, one execution path, one transition owner

For every consequential storage action:

1. exactly one semantic owner decides whether the artifact may be transformed or removed;
2. exactly one operation engine owns the action after `StorageExecutor` revalidation;
3. exactly one low-level owner records each persistent filesystem transition.

No later layer may independently re-derive or widen a decision already owned above it. Defense-in-depth checks may reduce authority, but they must not form a second semantic state machine.

A future change that would require a second parallel authority, a second cleanup execution path, or a second recursive mutation algorithm is a **Design reopen condition**, not an implementation convenience.

### 2. `StorageExecutor` is an authorization/transaction shell, not a cleanup engine

`StorageExecutor.run` owns only the common consequential envelope:

```text
invocation-local apply authorization
 -> storage-operation lease
 -> touched-owner barriers
 -> fresh owner snapshot
 -> plan/currentness/filesystem/policy revalidation
 -> admission revalidation when applicable
 -> invoke the explicit operation engine
 -> settle truthful result
 -> publish bounded audit
```

It does **not** perform cleanup mutation itself.

Required consequence: remove the destructive `engine=None` fallback/default cleanup implementation. Every consequential production operation supplies its explicit engine. An apply invocation with no engine is a construction error before mutation. Non-apply planning/reporting does not need an engine.

This eliminates the default-versus-production cleanup split and the cross-action-family laundering problem that IR19 was trying to guard with additional classifier/preflight machinery.

### 3. Cleanup has one engine and two mutation forms

The only cleanup engine receives a fresh revalidated owner snapshot and normalizes each owner-approved cleanup action into one of two destructive forms:

```text
EXACT_LEAF
  one file/symlink directory entry, removed relative to an authenticated parent

CERTIFIED_CLOSED_TREE
  one directory tree for which the owner has supplied complete typed destructive authority
```

Campaign-state maintenance is not a third cleanup mutation form; it remains its own owner action. P7 is not a third filesystem algorithm; it is a specialized authority-acquisition path that supplies a live authenticated capability to the same mutation kernel.

A directory with only selective/partial member authority is resolved **before mutation** into explicit authorized work units. The filesystem kernel never negotiates a mixed `members + refusals` policy while recursively deleting. A directory without complete owner-certified closed-tree authority is never sent to a generic recursive remover.

### 4. One cleanup filesystem mutation kernel

Exactly one production implementation owns consequential cleanup unlink/rmdir recursion. It owns, in one place:

- no-follow descriptor-relative acquisition and descent;
- opened-descriptor mount/ownership trust;
- expected kind/device/inode/identity checks at the destructive boundary;
- final immediate name-versus-opened-descriptor comparison before fd-relative `rmdir`;
- unlink/rmdir transition timing;
- descriptor lifetime and deterministic close;
- parent/directory durability steps;
- one action-local `MutationLedger`, hard-link de-duplication, zero-credit mutation truth, and exact substantiated byte accounting;
- conversion of post-transition failure into the existing typed partial-mutation outcome.

The kernel receives already-authorized immutable capability/data. It does not decide P7 state, owner eligibility, policy tier, currentness, or archive semantics.

P7, common owner subtrees, and generic cleanup must all call this kernel. No recursive `os.unlink`/`os.rmdir` algorithm remains in `qualification/store.py`, `storage/executor.py`, or a second cleanup helper after consolidation.

### 5. P7 owns authority acquisition, not deletion mechanics

P7 continues to own the hard semantic facts that only P7 can know:

- attempt state and released-proof authentication;
- generation/attempt/release identity;
- root identity and plan-bound target identity;
- typed released topology;
- monotonic-shrink proof semantics;
- same-attempt contradiction invalidation/isolation.

A live P7 capability exposes only what the shared cleanup kernel needs: authenticated ancestry/root descriptor(s), immutable typed destructive authority, and bound identity. The capability is ephemeral and one-way close.

The current independent P7 recursive deletion implementation is not part of the target architecture and must be deleted after the shared kernel consumes its authority.

Session lifetime must have one obvious owner. Prefer one attempt-scoped context/lifetime per attempt batch over a cache plus multiple nested invalidation/finalization policies. A close failure is ranked once at that lifetime owner: it cannot erase a primary mutation failure, and a close-only failure cannot disappear.

### 6. Transition truth is synchronous and local

A component that performs a state-changing syscall owns mutation truth for that transition.

For cleanup, the shared kernel updates its ledger immediately after successful unlink/rmdir.

For archive, restore, dedup, and maintenance, structure helpers so the engine regains control immediately after the state-changing syscall (`os.replace`, mkdir, prune/VACUUM transition, or equivalent) **before** any later fsync/readback/authentication/failpoint can raise. Record mutation/phase at that point, then perform post-transition durability/verification.

Do not use a widening callback/fallback protocol to recover transition truth after the fact. Do not infer this execution's mutation from later pathname disappearance. Do not catch a signature `TypeError` and manually fabricate the transition callback. If a helper currently hides both transition and later fallible work, split it at the transition boundary or return/raise a typed result that unambiguously carries the transition without compatibility branching.

### 7. Preserve specialized representation engines only where specialization is real

Archive creation/reclamation, restore, deduplication, and CampaignStore maintenance remain separate engines because their algorithms, persistence/recovery behavior, and representation semantics are materially different.

They share the `StorageExecutor` envelope, but they do not share a generic "storage action" state machine beyond what is necessary for plan/result/audit. Do not force them through cleanup classification, and do not create a universal handler framework merely for symmetry.

### 8. Internal APIs are not compatibility obligations by default

The storage package currently exports internal mutation helpers. Implementation must census real maintained consumers and shrink the export surface.

Tests, historical workplans, and internal convenience imports do not by themselves justify preserving a compatibility wrapper. Retain an old helper only when there is concrete evidence of a supported consumer contract that cannot be migrated safely. If retained, it must be a trivial facade over the one canonical mechanism and must not preserve a second algorithm or semantic branch.

## Required deletion and consolidation

The following current machinery is **not frozen** and is expected to disappear or collapse. A consolidation that merely routes through new wrappers while leaving these mechanisms live is nonconforming.

1. **Default destructive cleanup in `StorageExecutor`.** Delete `_execute_actions` or its destructive equivalent and all production reliance on `engine=None` for apply.
2. **Parallel cleanup-domain state machine.** Delete the current multi-class classifier/preflight/supported-domain machinery (`cleanup_domain.py`, `CLEANUP_SEMANTIC_CLASSES`, `require_cleanup_family`, `require_supported_domain`, parallel domain sets, and equivalent scaffolding) unless a residual tiny type definition is demonstrably the lowest-complexity place for a value used by the single cleanup engine. No standalone second authority/dispatcher may survive.
3. **Generic recursive directory removal.** Delete generic recursive cleanup. Generic cleanup is leaf-only.
4. **Duplicate recursive removers.** Replace and delete the separate generic tree walker, `remove_certified_subtree` recursive algorithm, and P7 certified-directory recursive algorithm. There is one consequential cleanup recursion in the final product.
5. **Mixed partial-authority recursive API.** Delete the runtime remover mode that accepts a container plus `members/refusals` and decides selective authority while walking. Resolve selective authority before mutation.
6. **Legacy convenience removers.** Delete `remove_durably`, `remove_durably_outcome`, and similar compatibility surfaces unless the consumer census proves a supported external/public contract; if one survives, it is a trivial facade with no separate recursion, fallback, or truth model.
7. **Transition-recovery patches.** Delete post-hoc pathname disappearance inference, signature-incompatible `TypeError` fallback, manually replayed transition callbacks, and any duplicate mutation inference based on reclaimed-byte totals.
8. **Layered cleanup finalizers.** Remove session-cache/finalizer/invalidation branches made unnecessary by a single attempt-scoped lifetime owner and shared kernel. No blanket close suppression remains.
9. **Implementation-shaped tests.** Delete or rewrite tests whose only purpose is to preserve removed classifiers, wrappers, dual dispatch paths, or dead patch seams. Behavioral safety claims move to the real owner -> cleanup engine -> executor -> kernel path.
10. **Excess internal exports.** Remove internal mutation/trust helpers from `storage.__init__` unless they are deliberately supported API.

Historical workplan/review files may remain as history; they are not production machinery and are not current normative authority after this revision.

## Preserved behavioral semantics

Simplification is not permission to weaken the hard requirements that caused the storage reset. The assembled implementation must preserve at least:

- owner-driven inventory/currentness and fail-closed ambiguity;
- invocation-local `--apply` authority and dry-run observational behavior;
- storage-operation serialization and owner activity/publication barriers;
- immutable plan binding and fresh apply-time revalidation;
- external/protected-input containment and symlink/mount boundaries;
- P7 exact release/root/target identities, live descriptor capability, proof-as-monotonic-shrink upper bound, read-only proof lookup, same-attempt invalidation and independent-attempt isolation;
- exact leaf identity and certified-tree typed authority;
- no-follow descriptor-relative mutation and final identity check before fd-relative directory removal;
- the four cleanup dispositions: `removed`, `already_absent`, `refused_no_change`, `partial_change_refused`;
- mutation truth independent of credited bytes, exact action-local reclaimed bytes, hard-link de-duplication, and zero-byte namespace mutation;
- post-mutation failure truth and primary-versus-secondary close failure ranking;
- archive blob/manifest/catalog transition truth, hot-reclaim truth, restore journal/container/member transition truth, dedup replace truth, and maintenance prune/VACUUM truth;
- truthful execution settlement and bounded durable audit, including unaudited degradation when audit publication itself fails;
- accepted archive/restore integrity and recovery behavior;
- bounded normal reporting and explicit deep physical audit;
- existing resource admission/policy semantics that are independent of the removed cleanup machinery.

## Implementation obligations

### A. Remove the dual execution authority

**Concern / rationale:** `StorageExecutor` currently has enough cleanup behavior to require its own semantic domain restrictions, while production cleanup has a second dispatcher. IR19 exists because those two paths drifted.

**Required end state:** `StorageExecutor` cannot perform a destructive action without an explicit engine. All production cleanup uses one cleanup engine; archive/dedup/restore/maintenance use their own explicit engines.

**Required consequences:**

- delete the default destructive cleanup path and the action-family/domain machinery needed only to make it safe;
- census every production `StorageExecutor.run` caller and convert intentional consequential callers to explicit engines;
- an apply call without an engine fails before mutation;
- an empty cleanup plan through the explicit cleanup engine remains a valid no-op;
- do not add a new registry/framework merely to replace `engine=None`.

**Acceptance evidence:** source/reference census; focused construction-error/no-op tests; affected regression for every production executor caller; structural absence of destructive cleanup references from `StorageExecutor`.

### B. Consolidate all cleanup deletion into the one kernel

**Concern / rationale:** generic/common/P7 recursive implementations independently encode the same dangerous filesystem rules and have repeatedly diverged.

**Required end state:** one canonical cleanup mutation module/function family is the only consequential recursive unlink/rmdir owner.

**Required consequences:**

- generic cleanup only emits exact leaf work;
- owner-certified complete directory actions emit certified closed-tree work;
- selective member authority is normalized before mutation;
- P7 acquires/revalidates its live authority then delegates deletion to the kernel;
- the kernel uses one ledger and one descriptor/close discipline across all owners;
- delete the superseded recursive algorithms and compatibility wrappers in the same stage; there is no shadow fallback.

**Acceptance boundary:** real planner/inventory owner, production cleanup engine, `StorageExecutor`, real P7 authority acquisition, and shared mutation kernel must execute. Filesystem race/failure injection may occur below the owner/kernel boundary.

**Acceptance evidence:** real-owner generic leaf, common certified tree, and P7 file/tree cases; symlink/special-node, mount, root/target replacement, final-pre-rmdir substitution, monotonic shrink, partial-prefix, zero-byte, hard-link, durability-failure, descriptor-close, and two-attempt isolation counterfactuals; structural proof that only one consequential cleanup recursion remains.

### C. Make transition truth local and remove recovery patches

**Concern / rationale:** callbacks, fallback signatures, post-hoc absence checks, and manual mutation marks exist because transition and post-transition failure are not cleanly separated.

**Required end state:** every engine records mutation immediately after its own persistent transition, before any later fallible step.

**Required consequences:**

- cleanup ledger marks successful unlink/rmdir at the syscall seam;
- archive publication reports blob/manifest/catalog replace phases at the replace seam;
- restore journal, container, and member publication report their transitions at their seams;
- dedup alias replacement and maintenance prune/VACUUM preserve their explicit transition marks;
- post-transition durability/readback failures propagate with already-recorded mutation truth;
- pre-transition failures remain nonmutating;
- delete callbacks/fallbacks/inference that are no longer necessary.

**Acceptance evidence:** symmetric pre/post-transition failpoints through real engines and executor/audit; liveness assertion that each failpoint actually fires.

### D. Collapse P7 lifetime/finalization machinery

**Concern / rationale:** the current session cache/invalidation/finalizer layering creates independent close/error-ranking failure surfaces.

**Required end state:** one attempt-scoped lifetime owner acquires, spends, invalidates when necessary, and closes the live P7 capability exactly once.

**Required consequences:**

- closed capability is permanently unspendable before any filesystem syscall;
- same-attempt contradiction stops later same-attempt work; independent attempt semantics are preserved;
- a primary mutation failure remains primary if close also fails;
- a close-only failure is observable and settled from current mutation truth;
- no descriptor leak on success, refusal, partial, exception, or normal early stop;
- remove superseded session-cache/finalizer branches.

**Acceptance evidence:** real P7 owner/executor cases for normal close, contradiction, post-mutation failure + close failure, close-only failure, repeated bounded runs/fd-leak check, and independent attempt isolation.

### E. Delete obsolete API/test/document machinery and close the architecture

**Concern / rationale:** keeping dead wrappers/tests/exports after consolidation preserves accidental contracts and encourages the next agent to patch obsolete paths.

**Required end state:** the repository communicates one current storage architecture and exposes only maintained interfaces.

**Required consequences:**

- run a maintained-consumer reference census before retaining compatibility helpers;
- remove obsolete internal exports and implementation-shaped tests;
- rewrite behavioral tests around the new canonical real path rather than preserving deleted helpers;
- update `docs/specs/training_data/mlff_storage_management_spec.md` and `storage/__init__.py` to state the new one-authority/one-path/one-transition-owner invariant and remove wording that freezes superseded classifiers/removers/finalizers;
- keep historical revision documents as history only; `AUTHORITY.md`, this plan, the current specification, and the parent owner-driven workplan form the current handoff.

**Acceptance evidence:** reference/structural absence checks, affected documentation validation, and final diff inspection showing actual deletion rather than wrapper relocation.

## Implementation authority

### Frozen

- The core problem and architecture invariant in this plan: **one semantic authority, one explicit operation path, one persistent-transition owner**.
- `StorageExecutor` is a common authorization/transaction/audit shell and never a second cleanup engine.
- Exactly one production cleanup engine.
- Exactly one consequential cleanup recursion/mutation kernel.
- Cleanup destructive forms are exact leaf or owner-certified closed tree; partial/selective authority is resolved before filesystem mutation.
- P7 remains semantic authority for release/proof/currentness and delegates filesystem deletion mechanics to the shared kernel.
- Transition truth is recorded at the state-changing syscall, never reconstructed from later pathname state or byte totals.
- Specialized archive/dedup/restore/maintenance engines remain only because their operations are materially distinct.
- All preserved behavioral semantics listed above.
- No new persistent authority/control plane, no speculative compatibility framework, no temporary parallel destructive path.
- A consolidation that only adds a facade while leaving superseded live mechanisms reachable is not completion.
- Subsequent ordinary defects are repaired in the canonical owner/kernel under this same architecture. New concrete failure sites, tests, or implementation mistakes do **not** create a new numbered storage authority revision. A future normative revision is justified only if evidence invalidates a frozen decision here.

### Delegated

- Exact module/function/class names of the shared cleanup mutation kernel.
- Whether normalized cleanup work uses an enum, dataclass, small protocol, or direct exhaustive branch, provided it does not recreate the current parallel classifier/domain framework.
- Exact batching/grouping mechanism for P7 attempt-scoped lifetime.
- Exact low-level typed result used to carry a post-transition failure when a syscall helper cannot practically be split, provided there is no callback/fallback ambiguity.
- Local organization of `MutationOutcome`, `MutationLedger`, trust helpers, and descriptor utilities when consolidation preserves one owner and reduces total machinery.
- Removal/retention of a compatibility facade only after the required consumer census establishes a real supported contract.

### Reopen only on evidence

Reopen only the affected design surface if implementation proves one of these assumptions false:

1. a maintained supported external/public consumer genuinely requires destructive `StorageExecutor.run(engine=None)` semantics and cannot be migrated without unacceptable compatibility break;
2. a real owner cannot express its cleanup authority as exact leaf or certified closed tree without loss of a required product behavior;
3. P7 cannot delegate deletion to the shared kernel without weakening its live proof/root/target capability semantics;
4. a materially distinct filesystem/hardware/platform requirement makes one shared cleanup mutation kernel less safe or less supportable than justified specialization;
5. an accepted archive/dedup/restore/recovery contract requires a transition API that cannot expose exact mutation truth without a different frozen architecture.

Tests written around old helpers, historical workplans, implementation inconvenience, or optional-tool absence are not redesign evidence.

## Affected surface and task-specific acceptance

Initial implementation surface is intentionally bounded to storage consequential topology and its real semantic owners:

- `mdstats/training_data/storage/executor.py`;
- `mdstats/training_data/storage/commands.py`;
- `mdstats/training_data/storage/cleanup_domain.py` (expected deletion/collapse);
- `mdstats/training_data/storage/outcome.py`;
- `mdstats/training_data/storage/trust.py`;
- `mdstats/training_data/storage/durability.py`;
- `mdstats/training_data/storage/archive.py`;
- `mdstats/training_data/storage/dedup.py`;
- `mdstats/training_data/storage/maintenance.py`;
- `mdstats/training_data/storage/inventory.py`, `plan.py`, `owners.py` only where normalization/authority handoff requires a smaller interface;
- `mdstats/training_data/qualification/store.py` for P7 authority/lifetime and deletion delegation;
- `mdstats/training_data/storage/__init__.py` export cleanup;
- storage core/integration tests plus maintained P7/CLI/owner regressions discovered from final references;
- current storage specification and generated derivative.

This is a closure horizon, not a scope ceiling. Broaden only through a concrete ownership/dependency/caller chain.

### Structural/absence acceptance

Final source must establish all of the following:

- no destructive default/fallback cleanup in `StorageExecutor`;
- no production consequential `engine=None` apply caller;
- one production cleanup engine;
- one consequential cleanup recursive unlink/rmdir implementation;
- no P7-owned recursive deletion implementation;
- no generic recursive directory removal;
- no live parallel cleanup classifier/preflight/domain/dispatcher state machine;
- no mixed selective-member recursive remover that decides authority while traversing;
- no consequential compatibility route to a superseded remover;
- no post-hoc pathname disappearance inference, signature-compatibility mutation fabrication, or mutation-from-byte-total inference;
- no blanket close-failure suppression;
- no internal mutation helper exported without a supported-contract justification;
- named superseded symbols/algorithms are deleted, not merely bypassed;
- the consolidation diff over the consequential cleanup/mutation topology is materially net-deleting. Exact line count is not a product metric, but a net-growing wrapper refactor that leaves the old mechanisms in place fails this plan.

Use direct references plus Semgrep/AST/Serena when available. Any custom structural rule used as acceptance evidence must be live against a known bad and known good shape and state its scan scope.

### Functional acceptance

Preserve and run real-owner behavioral coverage for:

- generic exact-leaf cleanup: success, absence, replacement, symlink, durability failure, zero-byte/hard-link truth;
- owner-certified closed-tree cleanup: nested no-follow descent, mount ambiguity/substitution, final identity check, partial-prefix failure, close failure;
- P7: release reseal/root/target mismatch, monotonic shrink, live additions/kind changes, spent capability, same-attempt invalidation, independent-attempt isolation, file/tree removal through the shared kernel;
- external/protected input refusal;
- stale plan/currentness/lease/admission refusal;
- archive blob/manifest/catalog publication and hot reclaim transition truth;
- restore journal/container/member transition truth and recovery semantics;
- dedup and maintenance transition truth;
- execution settlement and durable audit for complete/refused/partial/unaudited outcomes.

Acceptance must traverse the real semantic owner and production engine. A helper-only test cannot establish an owner/dispatcher/executor claim.

After the final executable/test edit:

1. record exact executable commit/tree;
2. re-derive the final affected surface from references/diff;
3. run focused canonical-kernel and transition tests;
4. run complete `tests/test_mlff_storage_reset_core.py` and `tests/test_mlff_storage_reset_integration.py`;
5. run maintained P7, CLI, destructive-closure, archive/dedup/restore/maintenance callers discovered by the final census, including the previously maintained P4F storage/docs, P6 destructive closure, P7 R11/R12/R13, and campaign CLI suites where still present;
6. run `pytest --collect-only -q`, changed-module compile/import checks, `git diff --check`, repository-required static checks, conflict-marker scan, and the structural/absence checks above;
7. validate affected Markdown and regenerate/validate committed PDF derivatives;
8. run a fresh complete affected-surface regression/integration pass on the exact assembled candidate after all behavior-changing edits.

External DFT, long GPU production, and environment-specific HPC/shared-storage qualification remain deferred and nonblocking because this consolidation changes storage control/mutation topology rather than scientific algorithms or target-HPC performance claims.

## Implementation sequence and redesign risks

### Stage A — remove the second execution path

Make `StorageExecutor` shell-only, make every consequential caller explicit, and collapse/delete the cleanup-domain machinery that existed to reconcile default and production cleanup. Migrate focused tests to the single production path. Close stage-local conformance and affected regression before changing recursive mutation.

### Stage B — introduce the one kernel and delete duplicate removers

Move the already-proven no-follow/mount/identity/ledger semantics into the one canonical cleanup mutation kernel. Route generic leaf, common owner tree, and P7 authority through it. Normalize selective authority before mutation. In the same stage, delete the superseded generic/common/P7 recursive implementations and dead wrappers so no fallback survives. Close real-owner race/failure regression before proceeding.

### Stage C — simplify transition and lifetime truth

Split representation transitions from later durability/verification where needed, remove transition callbacks/fallbacks/inference, and collapse P7 lifetime/finalizer behavior to one attempt-scoped owner. Close pre/post-transition, partial, close-ranking, and leak tests.

### Stage D — delete accidental API/test surface and reconcile current documentation

Shrink exports, remove implementation-shaped tests and dead compatibility symbols, update the current storage specification/architecture prose, and perform final source/structural complexity review. This stage may delete substantially more than it adds; do not preserve dead machinery for historical convenience.

### Final assembled closure

Perform exact-candidate conformance reconciliation, final affected-surface derivation, fresh functional regression/integration, structural absence proof, and documentation validation. Close/archive the storage reset only when the resulting implementation is simpler **and** retains the protected behavior.

## Conditional convergence guidance

The recurring semantic family is:

```text
consequential storage mutation
+ owner/currentness authority
+ cleanup filesystem transition
+ truthful partial/durability outcome
+ duplicated execution/recursive/finalization mechanism
```

This revision is the bounded Design reconsideration required by that recurrence. Implementation owns complete consolidation of this family in one pass; review should not resume one-sibling-at-a-time patching.

After this consolidation, a newly found defect governed by the frozen invariant is an implementation nonconformance: fix the single owner/kernel and its affected tests. Do not add another compatibility branch, wrapper, fallback, classifier, or numbered authority revision to accommodate it.

If the same material family recurs **because the one-owner/one-path/one-kernel architecture itself is insufficient**, stop and reopen only the invalidated frozen decision. That is the only normal route to a future storage architecture revision.

## Handoff closure

This plan deliberately replaces the current Revision-37/IR19 patch-shaped handoff with one architecture/consolidation contract. The still-binding product semantics needed for implementation are contained here together with the parent owner-driven workplan and current storage specification; historical IR files are evidence/provenance, not required normative input.

Snapshot-loss counterfactual: if Git history, prior conversations, and IR18/IR19/revision chains disappear, an implementer supplied with:

- `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md`;
- this Revision-38 plan;
- `docs/specs/training_data/mlff_storage_management_spec.md`;
- the current source/tests;

can recover the protected behavior, the new architecture invariant, the mechanisms to delete, the allowed redesign boundary, and the acceptance obligations without reconstructing the forty-revision history.

**Design disposition: CLOSED / implementation-ready for simplicity consolidation.**
