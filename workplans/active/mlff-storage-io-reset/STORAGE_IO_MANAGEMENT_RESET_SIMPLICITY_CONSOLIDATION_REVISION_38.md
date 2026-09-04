---
kind: implementation-workplan
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1-R38
parent_workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.14.0
status: planned
reviewed_date: 2026-09-04
reviewed_current_executable_commit: 38b37f6761d30c66ec29e27abf8f2ee3a311f804
reviewed_current_executable_tree: c5918d5db992c42b144b7770d100c160f9d417f7
supersedes_current_handoff: Revision 37 / IR19 and its plan-closure refinement
scope: bounded architectural reduction of the current storage cleanup/execution realization while preserving owner authority, apply-time safety, P7 release semantics, truthful persistence outcomes, recovery, and supported storage behavior
---

# Storage/I-O simplicity consolidation — Revision 38

## Objective / problem invariants / non-goals

### Original product problem

The storage subsystem must safely manage campaign-owned persistent representation after the P1-P7 architectural reset. Storage must be able to report, clean up, evict reconstructible caches, deduplicate, archive, restore, and maintain storage-owned/campaign-owned operational state without becoming a second scientific/currentness authority and without losing restart-equivalent product state.

The durable product flow remains:

```text
real semantic owners
  -> owner-driven storage inventory
  -> resolved storage policy
  -> immutable owner-bound plan
  -> synchronized fresh reauthentication/revalidation
  -> consequential storage operation
  -> truthful bounded result/audit
```

### Tier-1A product invariants

The following are intrinsic product/problem requirements and remain binding independently of the current implementation:

- P1-P7/CampaignStore/cache owners, not storage pathname heuristics, own scientific identity, currentness, restartability, publication/qualification state, and transform/reclaim eligibility.
- External user/source/reference inputs are never destructively consumed by campaign storage.
- Current, restartable, in-flight, ambiguous, unreadable, or owner-unresolved state fails toward retention/refusal rather than guessed cleanup.
- An inspected/authorized consequential plan does not silently retarget itself after owner/currentness/policy/filesystem state changes; current authority is re-established before mutation under the required storage/owner synchronization.
- Storage authority does not transfer to a replacement filesystem object, symlink target, or different mount merely because a pathname is unchanged.
- Recursive destruction requires real owner authority over the whole traversed destructive unit; lexical containment is not ownership.
- P7 released scratch is reclaimable only under authentic released-state/proof/generation/root/target authority, with proof semantics remaining a monotonic-shrink upper bound rather than a license to absorb newly appearing content.
- Persistent transition truth belongs to this execution and is recorded from the actual state-changing transition, not reconstructed later from pathname disappearance, byte totals, or another actor's state.
- Already-absent, no-change refusal, successful mutation, and partial mutation after a later failure remain distinguishable; exact substantiated reclaimed-byte accounting, zero-byte namespace mutation, and hard-link de-duplication remain truthful.
- Archive/restore/dedup/maintenance preserve their existing owner, integrity, recovery, durability, and transition-truth contracts.
- Storage admission, scratch/inode/I/O limits, bounded report/audit behavior, Python >=3.10, and the accepted POSIX threat/portability boundary remain unchanged.
- No new persistent descriptor/inode/release/retry registry or second storage scientific/currentness authority is introduced.

### Non-goals

- No change to target-size science, post-selection science, publication membership, qualification algorithms, calibration, or locked-test semantics.
- No resurrection of retired STOR1-STOR5 lifecycle authority.
- No intentionally lossy history-pruning feature.
- No speculative distributed/object/cloud storage architecture.
- No package-wide API cleanup unrelated to the affected storage topology.
- No production-scale DFT/GPU/HPC qualification requirement for this refactor.
- No line-count target. Simplicity is total justified product/system complexity, not textual minimization.

## Current implementation diagnosis — evidence, not authority

The current executable contains legitimate safety semantics but realizes them through too many cooperating Tier-2 mechanisms. In particular, the current tree contains or recently required:

- a production cleanup path and a destructive default `StorageExecutor` path;
- a separate cleanup family gate, semantic classifier, class set, supported-domain preflight, and dispatcher completeness machinery created to keep those paths aligned;
- multiple consequential recursive deletion implementations across generic/common/P7 cleanup;
- runtime selective `members + refusals` recursive cleanup machinery;
- mutation-truth callbacks/fallback history where a helper hides the state-changing syscall from the component that must report it;
- P7 filesystem deletion mechanics layered on top of genuinely P7-specific release/proof/session authority;
- tests and exported helpers whose main purpose is preserving or reconciling those implementation seams.

Those are Tier-2 facts. Their existence, tests, documentation, previous review closure, or internal consumers do not make them product invariants.

The root problem is therefore not that the current abstractions need more guards. It is that one product invariant is represented by multiple authorities and multiple destructive implementations, after which extra machinery is required to prove those copies agree.

Protocol 5.14 active simplification is triggered. Before any additive durable repair, implementation must first remove, narrow, alter, consolidate, or replace the Tier-2 cause of the intermediate problem. Net-new machinery is justified only when a Tier-1/Frozen capability remains genuinely missing, or when one canonical mechanism demonstrably replaces broader existing machinery and reduces total system complexity.

## Frozen high-level architecture and engineering envelope

Only the following solution decisions are deliberately Frozen for this implementation cycle.

### F1. Owner-driven semantic authority remains singular

The existing owner-driven architecture remains the semantic source of truth. Storage consumes owner facts; it does not create a second cleanup/currentness model.

A consequential remove/evict action must still be authorized by the fresh current owner representation of the exact artifact it will affect. Which internal function performs that check is delegated.

### F2. Plan then synchronized fresh authority check before consequence

Consequential operations continue to use an immutable owner/policy/filesystem-bound plan plus fresh under-synchronization reauthentication/revalidation immediately before mutation. The current `StoragePlan`/`StorageExecutor` realization is the expected base, but exact helper/function ownership is Tier 2.

There must be one common consequential execution envelope for serialization, owner synchronization, fresh authority checking, applicable admission revalidation, settlement, and audit. That envelope must not contain a hidden alternate cleanup algorithm.

### F3. Cleanup has one canonical semantic operation path

There is one canonical production cleanup operation path after common revalidation. No parallel default cleanup path and no parallel semantic classifier/domain state machine survive merely to keep multiple cleanup paths synchronized.

This freezes singular ownership, not an exact callable count or module name. An implementation with one engine function, one command-owned operation object, or an equivalent simpler realization is acceptable if it preserves the same singular authority and introduces no parallel route.

### F4. Cleanup has one canonical destructive filesystem implementation family

Ordinary cleanup and P7 cleanup share one canonical consequential unlink/rmdir implementation family and one mutation-truth model. There is no second generic remover, second certified-subtree remover, or P7-owned recursive deletion algorithm with overlapping filesystem responsibilities.

The canonical destructive owner must preserve the accepted safety envelope: no-follow/anchored destructive access, mount/ownership protection, plan/owner target identity at the destructive boundary, safe directory descent/removal, exact transition truth, durability, descriptor/resource cleanup, and partial-mutation transport. Exact helper decomposition and syscall-wrapper layout are delegated.

### F5. Recursive cleanup authority is whole-unit owner authority

An owner-known open container is not recursive cleanup authority. Cleanup may recurse only through a destructive unit for which the real owner grants whole-tree authority under the accepted closed/exclusive semantics.

If only selected children are reclaimable, those children must be represented as independently owner-authorized destructive units before cleanup acts. The current owner-view model already supports this for the affected product. Runtime recursive negotiation of `members + refusals` is not part of the target architecture.

The exact enum/type names (`SubtreeCoverage`, `CertifiedNode`, etc.) remain delegated.

### F6. P7 owns release semantics, not a second deletion algorithm

P7 remains the sole authority for released-attempt state/proof/generation/root/release/target semantics, live authority acquisition, monotonic-shrink proof behavior, spent capability protection, same-attempt invalidation, and independent-attempt isolation.

P7 delegates filesystem deletion mechanics to the canonical cleanup destructive owner. Exact session/capability representation, caching, context-manager shape, and source placement are Tier 2.

### F7. Persistent transition truth is local to the transition owner

The component that owns a state-changing transition must make the execution's mutation truth available before later fallible durability/verification work can erase that fact.

Post-hoc pathname disappearance, reclaimed-byte inference, signature fallback, or manually fabricated transition notification are forbidden because they cannot establish which execution caused the transition.

The exact mechanism is delegated. A direct ledger update, a narrow exact callback at an atomic `replace`, or an equivalent typed mechanism may be used when it is the lowest-complexity solution. No callback/function identity is Frozen.

### F8. Necessary specialization remains where the product semantics are materially different

Archive creation/reclamation, restore, deduplication, and CampaignStore maintenance may remain specialized because their data transformations, recovery obligations, and persistence semantics differ materially from cleanup.

Do not force them through a universal cleanup/action framework merely for symmetry. Conversely, current helper/module boundaries inside those features are Tier 2 and may be reduced if affected by the consolidation.

## Delegated solution space

Everything below the Frozen decisions above remains replaceable. In particular, implementation may alter, merge, move, rename, consolidate, or delete:

- the exact `StorageExecutor.run` signature and whether an explicit engine argument is how F2/F3 are realized;
- whether cleanup action-to-owner eligibility is checked in `revalidate_plan`, the canonical cleanup path immediately after it, or another single existing owning boundary;
- `cleanup_domain.py` versus `cleanup.py` versus folding the remaining code into an existing module;
- `CLASS_*`, `CleanupClassification`, supported-domain sets, family-gate helpers, and dispatcher/preflight objects;
- exact leaf/tree helper boundaries and private function names;
- current generic/common/P7 recursive-removal functions;
- `remove_durably`, `remove_durably_outcome`, `remove_planned_outcome`, `remove_certified_subtree`, and other internal convenience surfaces after maintained-consumer reconciliation;
- exact P7 session-cache representation, invalidation representation, finalization shape, and descriptor ownership helpers;
- the current atomic-publication callback versus an equivalent simpler exact transition mechanism;
- `durable_unlink` retention or inlining for archive hot reclamation;
- `authorized_members()` implementation details and the P7 planning-only authorization branch where no maintained non-cleanup consumer requires it;
- placement of result-recording helpers;
- test organization and structural-analysis technique.

No detail in this section becomes Frozen because the implementation or tests currently depend on it.

## Implementation obligations

### O1. Remove duplicated cleanup authority rather than hardening it

**Concern / rationale:** the default cleanup path and the production cleanup path created a solution-level problem: keeping their routing domains synchronized. The classifier/domain layer is a repair for that duplicated realization, not a product requirement.

**Required end state:** one production cleanup semantic path exists after the common execution envelope. No second destructive default route and no separate classifier/domain synchronization state machine are needed to make duplicate paths agree.

**Delegated solution space:** exact executor/engine APIs and location of the small operation-family/owner/path checks.

**Suggested realization:** remove destructive `engine=None` behavior; keep the common executor as shell; strengthen the existing plan/current-owner check; make production cleanup the only cleanup path. This is suggested because current production commands already use explicit operation engines and it deletes machinery rather than adding it.

**Acceptance evidence:** runtime production cleanup and wrong-operation controls plus structural/reference evidence that no alternate consequential cleanup route or classifier/domain state machine remains. Do not preserve classifier-specific tests merely to satisfy this obligation.

### O2. Consolidate cleanup mutation into one destructive owner

**Concern / rationale:** multiple recursive removers independently own no-follow descent, mount checks, identity, durability, close behavior, partial mutation, and byte accounting. Repeated defects arose from those copies drifting.

**Required end state:** one canonical cleanup destructive implementation family owns consequential leaf/tree unlink/rmdir behavior for ordinary and P7 cleanup.

**Delegated solution space:** which existing remover supplies the best code base, module/function boundaries, iterative versus recursive traversal, local helper layout, and exact result helper names.

**Suggested realization:** reuse the strongest current plan-bound descriptor-relative implementation and merge only the P7 typed-proof constraint into it; migrate all callers and delete superseded recursion in the same coherent stage. Do not create a fourth remover for staged migration.

**Acceptance evidence:** structural uniqueness/absence evidence plus real-owner ordinary/P7 behavioral tests covering successful removal, replacement/symlink/mount contradiction, partial prefix, zero-byte mutation, hard links, durability failure, and final directory identity safety.

### O3. Remove selective open-container recursive cleanup

**Concern / rationale:** runtime `members + refusals` recursion exists to compensate for an over-broad destructive unit. The current owner topology already exposes reclaimable P7 top-level members independently, certifies reclaimable CampaignStore orphan trees before marking them reclaimable, and treats storage-owned staging as whole-tree exclusive scratch.

**Required end state:** recursive cleanup never derives destructive authority from an open/container root. A selectively reclaimable child is a first-class owner-authorized action target before mutation.

**Delegated solution space:** exact owner-view representation and whether any now-dead read-only member helper remains for archive/dedup.

**Acceptance evidence:** real owner inventory/plan tests proving open containers are retained/non-recursive while independently released children and whole-tree-certified artifacts remain reclaimable; structural absence of runtime selective-recursive cleanup authority.

### O4. Preserve P7 authority while deleting P7 filesystem duplication

**Concern / rationale:** P7 specialization is necessary for owner semantics but not for generic filesystem deletion mechanics.

**Required end state:** authentic P7 release/proof/root/target authority remains required and live through mutation, but P7 does not own a separate recursive unlink/rmdir algorithm.

**Delegated solution space:** exact session/capability representation and lifetime implementation.

**Suggested realization:** retain the existing authenticated released-attempt acquisition/session semantics, pass its authenticated ancestry/typed authority into the canonical cleanup destructive owner, and remove P7-only deletion helpers that become redundant.

**Acceptance evidence:** real P7 owner -> plan -> current production cleanup path -> canonical destructive owner for file and tree cases; release reseal mismatch, root/target replacement, proof monotonic shrink, live addition/kind contradiction, spent capability, same-attempt invalidation, independent-attempt isolation, partial mutation, and close/finalization ranking.

### O5. Make transition truth exact without building a transition framework

**Concern / rationale:** cleanup had to recover mutation truth because the component reporting the action did not always own the state-changing syscall. Archive/restore legitimately have atomic publication followed by fallible postchecks.

**Required end state:** each consequential transition is attributed exactly to this execution before later failure can hide it. No post-hoc or fabricated inference remains.

**Delegated solution space:** direct ledger updates, narrow exact callbacks, typed transition results/errors, or equivalent simpler mechanisms.

**Suggested realization:** cleanup directly owns unlink/rmdir and updates its ledger immediately. Retain the current `on_published` atomic-publication callback only if it remains the smallest shared solution for archive/restore replace-before-fsync/readback failures after consolidation. This callback is not Frozen and may be replaced by an equivalent simpler mechanism.

**Acceptance evidence:** failpoint/liveness tests through the real transition owner for cleanup, archive blob/manifest/catalog, restore journal/member/container, hot reclaim, dedup replace, maintenance, and audit degradation where affected.

### O6. Delete obsolete compatibility/export/test machinery unless a real contract requires it

**Concern / rationale:** internal helpers and tests can accidentally turn previous implementation seams into pseudo-APIs.

**Required end state:** the final runtime/export/test surface reflects the surviving product architecture. Obsolete destructive helpers, classifier symbols, dual-route tests, and compatibility adapters are removed unless a concrete maintained supported contract requires them.

**Delegated solution space:** exact migration of maintained internal callers and final public export list.

**Acceptance evidence:** maintained-consumer census; package/export references; affected tests. Repository tests or historical workplans alone do not establish a compatibility obligation. If a supported external/public contract is discovered, preserve the contract through the simplest canonical implementation rather than preserving its old algorithm.

### O7. Reconcile specification language with stable contract authority

**Concern / rationale:** current storage-spec section 5c describes cleanup semantic classes and a default executor domain. Those are current implementation details and conflict with the reduction target.

**Required end state:** durable specification describes stable owner authority, plan/apply revalidation, recursive authority, filesystem safety, and truthful outcomes without freezing classifier/default-engine machinery.

Until the specification is reconciled, Revision 38 supersedes section 5c's implementation-topology clauses (`CLASS_*`, classifier/domain sets, dual cleanup engines, default `engine=None` semantics) while preserving the behavioral safety claims they were intended to protect.

**Acceptance evidence:** source/spec alignment review plus regenerated/validated derived storage-spec PDF before final implementation closure.

## Expected current simplification surface — non-normative symbol map

The following current symbols/files are high-probability deletion/consolidation targets. This list guides implementation intake; it is not a Frozen proof script. Equivalent simpler realization may change the exact symbol set while preserving O1-O7.

- `storage/cleanup_domain.py`: `CLASS_*`, `CleanupClassification`, family/domain/preflight helpers and supported-domain sets.
- `storage/executor.py`: default destructive cleanup branch, cleanup-domain imports, `_execute_actions`, duplicate generic/certified recursive removal, obsolete destructive convenience APIs, and cleanup-specific authorization/result machinery that moves or disappears with singular ownership.
- `storage/commands.py`: production class/domain dispatch, duplicated cleanup authorization objects, P7-specific filesystem routing after canonicalization.
- `qualification/store.py`: P7-specific unlink/rmdir recursion and mutation-only helpers after authority is delegated to the canonical destructive owner.
- `storage/inventory.py`: cleanup use of selective `authorized_members`; P7 planning-only exact-authorizer branch if no maintained archive/dedup consumer requires it.
- `storage/__init__.py`: exports for removed classifier/destructive internals.
- tests: default-engine/classifier/domain-equality tests and seam-patching tests that no longer represent a product claim.

If implementation discovers additional callers/consumers, that expands the affected surface; it does not automatically create a new product requirement or freeze the current helper.

## Implementation authority

### Frozen

- Tier-1A product invariants listed above.
- F1 owner-driven semantic authority.
- F2 immutable plan plus synchronized fresh authority check before consequence and one common non-destructive execution envelope.
- F3 one canonical production cleanup semantic path with no hidden alternate destructive route.
- F4 one canonical cleanup destructive filesystem implementation family shared by ordinary and P7 cleanup.
- F5 whole-unit owner authority for recursive cleanup; open/container ownership alone is not recursive destructive authority.
- F6 P7 owns release/proof/root/currentness semantics and delegates generic filesystem deletion mechanics.
- F7 exact transition truth at the transition owner; no later pathname/byte/fallback inference.
- F8 specialization only where materially required by distinct archive/restore/dedup/maintenance semantics.
- Existing supported storage behavior, durability/recovery/security/compatibility envelope, and prohibition on a new persistent storage scientific/currentness authority.

### Delegated

- Exact filenames, classes, functions, enum names, helper counts, callable signatures, engine-argument mechanics, result-helper placement, session-cache representation, callback identity, private traversal structure, and test organization.
- Whether current `revalidate_plan` is the exact location of all cleanup current-owner checks, provided there remains one fresh authoritative gate before mutation.
- Whether `cleanup_domain.py` is deleted, renamed, or repurposed.
- Which existing recursive implementation is used as the consolidation base.
- Whether `durable_unlink` or `on_published` survive as the minimum justified realization.
- Exact compatibility facades retained for any real supported consumer discovered during implementation.
- Structural-analysis tool choice and rule shape.

### Reopen only on evidence

Reopen only the affected Frozen surface if evidence establishes one of the following:

1. the owner-driven plan/fresh-revalidation architecture cannot express a required current storage operation without a materially different authority model;
2. a real current owner must safely reclaim selected descendants that cannot be represented as independent owner-authorized destructive units and refusing them violates a required product capability;
3. P7 cannot delegate filesystem deletion to one canonical destructive owner without weakening its release/proof/root/target guarantees;
4. a supported filesystem/platform within the product contract requires materially different destructive semantics that make one canonical cleanup implementation family unsafe or unmaintainable;
5. the common consequential execution envelope itself must own materially different cleanup semantics to satisfy a real product contract;
6. a concrete supported external compatibility contract requires an otherwise removed behavior and cannot be preserved through the canonical path without changing Frozen architecture.

Implementation inconvenience, old tests, historical workplans, current helper dependencies, code-size aesthetics, or a new failure site under already-binding semantics are not redesign evidence.

## Affected surface and task-specific acceptance

### Provisional affected surface

At minimum re-derive and inspect:

- `mdstats/training_data/storage/{plan,executor,commands,inventory,owners,outcome,trust,durability,__init__}.py`;
- current cleanup implementation/classifier module;
- `mdstats/training_data/qualification/store.py`;
- archive hot-reclamation and any shared durability consumer affected by destructive-helper cleanup;
- dedup/maintenance only where shared transition/result APIs change;
- campaign CLI/storage entry points and every maintained `StorageExecutor`/cleanup caller;
- storage core/integration tests plus maintained P7/owner/campaign regressions discovered from final references;
- current storage specification and generated PDF derivative.

This surface is provisional. Final Implementation must re-derive it from the assembled candidate. Affected-surface expansion does not expand product requirements or freeze newly discovered Tier-2 machinery.

### Structural reduction claims

Final source must establish, by source/reference/structural evidence appropriate to the final realization:

- no alternate consequential cleanup path bypasses the canonical cleanup semantic owner;
- no independent classifier/domain state machine exists merely to reconcile parallel cleanup paths;
- only one canonical consequential cleanup recursive unlink/rmdir implementation family remains;
- P7 has no separate recursive filesystem deletion algorithm;
- open/container ownership is not converted into runtime selective recursive cleanup authority;
- unknown/owner-specific authority cannot fall through to generic deletion;
- mutation truth is not inferred from later pathname disappearance, reclaimed bytes, or signature fallback;
- obsolete destructive compatibility routes do not preserve a second algorithm;
- no new abstraction/state/registry was added unless it satisfies the Protocol-5.14 justified-abstraction rule by protecting an identified Tier-1/Frozen capability or replacing broader existing complexity.

A net-growing refactor is not automatically wrong, but it triggers an explicit conformance challenge: identify the Tier-1/Frozen capability the added machinery protects and show what broader complexity it replaces. Growth whose purpose is only to mediate surviving old machinery is nonconforming.

### Real-boundary behavioral acceptance

Acceptance binds to product/Frozen claims, not to current Tier-2 function names. In the current realization the path is approximately owner -> plan -> common executor envelope -> cleanup operation -> destructive owner; if implementation legitimately relocates delegated owners, remap acceptance to the new real production path and invalidate/rerun owner-specific evidence.

For owner-authority and cleanup-safety claims, tests must execute the real current semantic owner and the real production cleanup operation. Doubles/failpoints may sit below the semantic owner/destructive transition boundary to simulate filesystem failure, durability failure, or expensive dependencies. Do not monkeypatch the owner/cleanup dispatcher itself to manufacture the accepted decision.

Representative required cases:

- ordinary leaf: success, already absent, symlink entry safety, plan/target replacement contradiction, zero-byte mutation, post-unlink durability failure;
- whole-tree owner authority: normal removal, unexpected descendant, kind/symlink/special/mount contradiction, monotonic missing recorded node where owner contract permits it, partial prefix, hard links, final directory replacement, descriptor close/finalization failure;
- P7: release/proof/root/target mismatch, monotonic shrink, live addition/kind contradiction, spent authority, same-attempt invalidation, independent-attempt isolation, file/tree cleanup through the canonical destructive owner, post-mutation plus finalization failure ranking;
- cross-operation preservation: archive/restore/dedup/maintenance transition truth and audit degradation on affected shared code.

Exact current helper identity is not an acceptance invariant unless a real supported contract makes it so.

### Final functional acceptance

After all material executable/test edits:

1. reconcile the assembled implementation against Tier-1A + Frozen F1-F8;
2. re-derive final affected surface and maintained consumers;
3. run focused cleanup/P7/transition checks;
4. run stage-local affected regression after each coherent executable stage;
5. run complete storage core/integration suites and every final-census maintained affected owner/CLI/consumer regression;
6. run repository-required collection/import/static/conflict/diff checks;
7. establish structural reduction claims on the exact assembled candidate;
8. reconcile Markdown specification and regenerate/validate its PDF derivative;
9. rerun final complete affected-surface regression/integration after all material executable edits;
10. record exact final commit/tree and any genuinely unavailable blocking check.

External DFT, long GPU production, and environment-specific HPC/shared-filesystem qualification remain deferred/nonblocking because this work changes storage control/mutation topology rather than scientific algorithms or production-scale performance policy.

## Implementation sequence and simplification triggers

### Stage A — remove duplicate cleanup authority

Coherently remove the alternate/default destructive cleanup route and the classifier/domain reconciliation machinery it necessitated. Preserve the common consequential envelope and one fresh authoritative remove/evict gate. Update affected tests in the same stage.

**Stage exit:** one canonical cleanup semantic path remains; wrong-operation/malformed authority fails before mutation without a second semantic state machine.

### Stage B — collapse destructive filesystem ownership

Move ordinary and P7 cleanup onto one canonical destructive implementation family, eliminate runtime selective open-container recursion, and delete superseded generic/common/P7 recursion in the same coherent stage. Preserve P7 owner semantics and exact mutation truth.

**Stage exit:** one canonical destructive owner serves ordinary/P7 cleanup; no shadow fallback remains.

### Stage C — remove compatibility/finalization/transition residue

Reconcile maintained consumers; delete obsolete destructive exports/wrappers; simplify P7 lifetime/finalization and cleanup transition plumbing; retain or replace archive/restore transition signaling only according to the minimum justified realization.

**Stage exit:** no remaining helper/state exists primarily to preserve a removed cleanup architecture.

### Stage D — specification and assembled closure

Reconcile the storage specification to stable behavior/authority rather than implementation classes; perform final accepted-contract reconciliation, affected-surface derivation, structural reduction proof, final regression/integration, and exact-candidate evidence.

### Active simplification trigger during implementation

If implementation encounters another defect whose proposed fix adds a wrapper, fallback, classifier, state bit, compatibility path, retry, session layer, or second representation, stop before making it durable and ask:

1. Which Tier-1A or Frozen F1-F8 requirement does the proposed machinery protect?
2. Is the problem created only by surviving Tier-2 machinery?
3. Can deleting/narrowing/altering/consolidating that machinery make the problem disappear?
4. If a new abstraction is still needed, what broader mechanisms does it replace so total system complexity decreases?

If no Tier-1/Frozen justification exists, additive preservation is not an acceptable repair.

## Handoff closure

Current supplied authority is:

- `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md` — original product problem, owner-driven architecture, engineering envelope, and non-goals;
- this Revision-38 plan — current Protocol-5.14 Frozen architecture, delegated solution space, reduction obligations, acceptance boundaries, and redesign triggers;
- `docs/specs/training_data/mlff_storage_management_spec.md` — stable behavioral contract, except that section 5c's classifier/default-engine implementation topology is immediately superseded by Revision 38 and must be reconciled before final closure;
- current source/tests — evidence of the Tier-2 realization to reduce, not authority for preserving it.

Snapshot-loss counterfactual: with Git history, prior chats, R30-R37/IR artifacts, and implementation-created invariants removed, the supplied set still recovers the original product problem, Tier-1 requirements, Frozen high-level architecture, delegated solution freedom, expected reduction, task-specific acceptance, and genuine Design-reopen triggers.

**Design/workplan disposition: CLOSED / implementation-ready under Protocol 5.14.0 Revision 38.**

**Implementation disposition: PENDING. The reviewed current executable is `38b37f6761d30c66ec29e27abf8f2ee3a311f804`, tree `c5918d5db992c42b144b7770d100c160f9d417f7`; it is evidence of the pre-consolidation Tier-2 realization, not the target architecture.**
