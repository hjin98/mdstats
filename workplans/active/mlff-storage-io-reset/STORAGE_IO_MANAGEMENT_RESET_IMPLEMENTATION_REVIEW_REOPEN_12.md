---
kind: implementation-review-reopen
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1-R33
parent_workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
status: reopened
reviewed_date: 2026-09-03
reviewed_authority_revision: 32
reviewed_executable_commit: 2e01d6fa5119ba67088f7c312c44962eba902c8e
reviewed_executable_tree: fe927d28612d411303676fc04d5a9cd7164720b1
reviewed_plan_commit: 1b9b3845777c34480c1cd032c49cf9281a30049a
review_verdict: NO-PASS-PLAN-AMENDED
scope: snapshot-complete bounded implementation and acceptance repair for truthful mutation state, descriptor-safe recursive deletion, canonical mount ownership, all-path post-mutation failure transport, real-owner acceptance, compatibility/consolidation, and exact-candidate final evidence
precedence: Revision 30 remains the accepted closed final-apply design; conforming Revision-31 implementation is preserved; this Revision-33 handoff supersedes Revision 32 as the complete current bounded implementation/review contract
---

# Storage/I-O reset implementation review reopen 12 — Revision 33

## Disposition and purpose

**Revision-32 plan review: NO-PASS as a final implementation handoff; amended and resealed here.**

The reviewed executable remains:

```text
commit  2e01d6fa5119ba67088f7c312c44962eba902c8e
tree    fe927d28612d411303676fc04d5a9cd7164720b1
```

Revision 32 correctly identified the two remaining implementation defects and most missing acceptance. A second source/ownership review found that its repair wording still left material choices and acceptance consequences for Implementation to rediscover: it did not make the existing action ledger the canonical mutation-truth owner, did not fully bind destructive mount checks to the existing trust owner, left an effectively unsupported `shutil` alternative open, did not enumerate several post-mutation observation/descriptor failures, lost a known exact regression-file set during snapshot compression, and did not close the coexistence of the public boolean remover with the typed removal path.

This Revision 33 is therefore the **single snapshot-complete current bounded implementation contract**. Implementation does not need Revision 31 or Revision 32 to recover any still-binding review correction.

Revision 30 remains the accepted closed architecture. No P1-P7 science/currentness semantics, owner-driven storage architecture, R26 historical retirement, CampaignStore ownership, P5 typed proof, archive/dedup/restore/control-plane design, Python `>=3.10` floor, or accepted POSIX threat boundary is reopened.

## Preserved conforming implementation

Preserve these already-conforming pieces unless a local change is necessary to satisfy the corrections below:

- exact released-state/proof authority bound into the immutable plan and reauthenticated on the live P7 descriptor;
- retained attempt descriptor continuity through state/proof/topology certification and fd-relative P7 mutation;
- mandatory complete plan-bound target identity before every released-member target observation/mutation;
- permanently unspendable closed/invalidated session objects;
- proof-as-upper-bound monotonic shrink and interrupted retry;
- same-attempt invalidation after a mutation-boundary contradiction;
- once-per-session read-only typed proof lookup;
- four typed mutation outcomes;
- `MutationOutcome` action-local reclaimed-byte serialization and aggregate summation from those recorded values;
- executor-owned `record_or_reraise` coverage of CLI and default cleanup removal paths;
- retention of an unmeasurable P7 regular file before unlink;
- `MutationLedger`'s current in-memory ownership of `mutated`, exact `removed_bytes`, and action-wide `(device,inode)` deduplication;
- existing audit-publication degradation semantics.

## Frozen ownership map for this repair

This repair must reduce, not multiply, authorities:

- **P7 release/root/proof/target authority:** `qualification/store.py` and its live `ReleasedAttemptSession` remain the semantic owner. Storage does not reproduce P7 certification.
- **Mutation truth/accounting:** one action-scoped in-memory mutation ledger owns whether a destructive transition occurred, exact credited bytes, and action-wide inode deduplication. `storage/outcome.py::MutationLedger` is the existing canonical realization and should be reused/generalized minimally rather than reimplemented as parallel `freed`, `seen`, and mutation flags.
- **Mount/ownership crossing semantics:** `storage/trust.py` remains the canonical policy owner for nested-mount detection and fail-closed ambiguity. A destructive fd walker may live where dependency direction is clean, but it must consume the canonical trust decision rather than duplicate mount policy.
- **Action recording/settlement/audit:** `StorageExecutor` remains the real execution owner; helper/direct-result tests cannot establish those claims.
- **Public compatibility:** `storage.remove_durably` is currently exported. Do not silently delete or semantically repurpose that public surface without a governed compatibility decision. Consequential production paths, however, must have one canonical typed removal mechanism and may not bypass structured outcomes through the boolean helper.

## R33-1 — mutation truth must be independent of byte credit, using one action ledger

### Problem

P7 `_remove_certified_directory()` currently owns a parallel `freed` integer and `seen` set and decides whether a stop is partial from `freed > 0`. That is not equivalent to mutation truth. A namespace transition can credit zero bytes:

- unlinking a zero-byte regular file;
- removing an empty directory;
- unlinking an additional hard link whose inode has already been credited in the same action.

The repository already has an action-scoped `MutationLedger` whose `credit()` marks mutation even for zero-size/deduplicated credit and whose `note_mutation()` records zero-byte destructive transitions. Keeping a second P7 accounting state is unnecessary ownership duplication and was the source of the current bug.

### Required end state

- P7 recursive removal uses **one action-scoped mutation ledger shared across the complete top-level action and all nested recursion**, or an engineering-equivalent minimal generalization of `MutationLedger` that remains the sole owner of the same three facts: mutation occurrence, exact credited bytes, and inode deduplication.
- Do not retain an independently authoritative `freed`/`seen`/`mutated` trio in P7. Local display/count variables that do not determine outcome/accounting are fine.
- Mark mutation only after `unlink`/`rmdir` actually succeeds. A zero-byte file unlink and empty-directory rmdir must make `mutated=true` while credited bytes remain exactly zero.
- Nested recursion updates the same action ledger. Do not manually reconstruct parent mutation truth from `nested.removed_bytes`; zero-byte nested mutations must propagate automatically.
- `partial_change_refused` is selected from the ledger's mutation fact, never from a positive byte total.
- A clean `removed` action may legitimately carry `reclaimed_bytes=0` while `mutated=true`.

### Failure semantics

The same ledger must distinguish the two sides of every failure:

```text
before first destructive transition
    -> no fabricated mutation / no fabricated bytes

after first destructive transition
    -> partial_change_refused / mutated=true
       + exact credited bytes (possibly 0)
       + original cause preserved
```

This applies to recursive P7, generic cleanup, and common certified-subtree cleanup wherever the same action semantics apply.

### Acceptance

Through the **real cleanup executor, real P7 owner/session, settlement and durable audit**:

1. remove a certified zero-byte file, then encounter a later contradiction: partial, `mutated=true`, exact per-action and aggregate bytes `0`;
2. remove a certified empty nested directory, then encounter a later contradiction: same partial/true/zero semantics;
3. remove a second hard-link name after the inode was already credited, then encounter a later contradiction: mutation truth survives even if that transition adds zero bytes;
4. inject a post-zero-credit destructive failure: action is recorded partial before propagation, with zero exact credit;
5. matching failures before the first destructive transition remain no-change/zero and leave the would-be target intact.

## R33-2 — one descriptor-safe tracked recursive mutation mechanism, with canonical mount checks

### Problem

Revision 31 replaced `shutil.rmtree()` with `_remove_tree_tracked()` to gain per-transition accounting, but `_remove_tree_tracked()` descends by pathname after a no-follow classification. `shutil.rmtree.avoids_symlink_attacks` describes `shutil.rmtree`; it does not protect this separate walker. The walker also performs no canonical mount-boundary check during destructive descent.

The current product specification already establishes the public-Python solution for P7: no-follow fd-relative recursion using `os.open(..., dir_fd=...)`, `os.scandir(fd)`, `os.unlink(..., dir_fd=...)`, and `os.rmdir(..., dir_fd=...)`. Python `>=3.10` does not provide a public `shutil.rmtree(..., dir_fd=...)` API that simultaneously exposes exact per-transition accounting.

### Required end state

For generic cleanup and fully certified common-subtree cleanup:

- replace the pathname `_remove_tree_tracked()` descent with a **public-API descriptor-relative/no-follow tracked destructive walker** (or reuse/consolidate with an existing equivalent) that retains the authenticated parent descriptor while classifying, entering, unlinking, and removing each child;
- do not rely on private `shutil` internals such as `_rmtree_safe_fd` as a supported product dependency;
- do not treat `shutil.rmtree.avoids_symlink_attacks` as protection for any custom walker. If a public supported alternative is discovered that genuinely supplies the same race resistance, exact transition accounting, Python-floor compatibility, mount semantics, and partial-failure transport, using it requires concrete source/runtime evidence; otherwise the fd-relative tracked walker is the required consequence;
- use the action ledger from R33-1 for every successful destructive transition;
- measure regular-file identity/size before unlink, credit only after successful unlink, and preserve action-wide hard-link deduplication;
- retain symlinks/special nodes or unlink only the link entry when the actual owner has explicitly authorized that link; never descend through a symlink target.

### Canonical mount ownership

`storage/trust.py` remains the owner of “is this descent crossing into externally owned/mounted bytes?” semantics.

For every directory descent that may recurse destructively:

1. open/reacquire the child no-follow relative to its authenticated parent;
2. compare descriptor filesystem identity to the parent as required by the existing trust contract;
3. apply the canonical mount-point/availability decision for the child display locator, including same-device bind-mount detection through the existing resolver;
4. if crossing or ambiguity is reported, close the child descriptor and retain it without traversing/removing its descendants.

Exact helper placement/order may be locally reconciled when it preserves the same property, but mount policy must not be copied into `executor.py` as a second independent definition.

A mount that appears after planning but before destructive descent must still be a refusal boundary. Opening the actual child descriptor before trusting its descendants must never grant authority merely because the earlier plan did not see that mount.

### Acceptance

Using the real executor/authorization and low-level deterministic injection only:

- **directory-to-symlink substitution:** after a child is initially observed but before destructive descent, replace it with a symlink to an external test-owned directory containing a sentinel. The external directory/sentinel survive; no descendant of the symlink target is touched. Exercise generic and fully certified common-subtree paths when they share the mechanism.
- **mutation-time nested mount:** after planning/certification but before destructive descent, make the canonical deterministic `MountIdentityResolver` report the child as a nested mount. The child and sentinel survive and the action refuses/partials according to any earlier mutation. Include a same-device mount representation so `st_dev` equality alone cannot pass it.
- **ambiguous mount discovery:** inability to establish mount ownership during destructive descent retains rather than traverses.
- preserve ordinary recursive success, exact partial bytes, hard-link deduplication, durability-failure, and already-absent behavior.

Add a focused structural/static guard showing that the canonical destructive recursive path cannot regress to `entry.is_dir(follow_symlinks=False) -> recurse by Path(entry.path)` / `os.unlink(entry.path)` while claiming `shutil.rmtree.avoids_symlink_attacks` as its protection.

## R33-3 — close every post-mutation exception path, not only unlink/rmdir/fsync

### Problem

R32 stated the general rule but did not enumerate several concrete operations in the current P7 loop. After an earlier mutation, failures can still arise while observing the next entry or while cleaning up a descriptor. Current examples include `DirEntry.is_symlink`, `is_dir`, `is_file`, recursive open/enumeration, stat/measurement, trust/mount observation, unlink/rmdir/fsync, and `os.close` in a `finally` block.

There is also a converse bug: P7's current `stop_failure()` always constructs a partial outcome. An `fsync(handle)` failure on an initially empty directory occurs **before** that directory's `rmdir`; when no child was removed, it must not fabricate mutation merely because the failure happened on a durability-looking operation.

### Required end state

- Every exception after the first successful destructive transition must reach the current action boundary with the action ledger's partial outcome and exact bytes before propagation.
- Every exception before the first destructive transition must carry no fabricated mutation/bytes. If the existing API propagates that exception, it may propagate; it simply cannot be recorded as a mutation.
- Observation failures (`is_symlink`, `is_dir`, `is_file`, open/scandir/stat, mount/trust observation) are subject to the same ledger rule as unlink/rmdir/fsync failures.
- Descriptor cleanup is part of the failure path. A close failure after mutation must not bypass action recording. If a primary exception is already active, cleanup failure must not erase the primary structured mutation truth; preserve/chaining/reporting mechanics are delegated, but the original product-significant cause and mutation outcome must remain observable.
- Do not turn normal owner contradictions into exceptions merely to centralize code; typed refusal/partial outcomes remain valid where the current owner deliberately stops.

### Acceptance

At minimum cover:

1. a `DirEntry` kind/observation failure after one zero-credit destructive transition -> partial/true/0;
2. the same observation failure before any mutation -> no fabricated mutation;
3. `fsync` failure on an initially empty directory before its `rmdir` -> no fabricated mutation;
4. `fsync` failure after a child was removed -> exact partial mutation;
5. descriptor-close failure after mutation -> current action still recorded before propagation;
6. primary post-mutation failure plus cleanup/close failure -> the structured mutation evidence and primary cause are not replaced by the cleanup failure.

Use bounded deterministic test doubles below the real owner only.

## R33-4 — real `StorageExecutor.run` failure acceptance remains mandatory

Focused helper tests may remain, but they are not final evidence for executor settlement/audit claims. Add real-owner integration tests for all of the following:

1. default `engine=None`: unlink succeeds, durability fails;
2. generic recursive directory: one child is removed, a later child/removal/observation fails while the container survives;
3. fully certified common subtree: destructive work succeeds and a later durability/cleanup step fails;
4. individually authorized common subtree: an earlier member succeeds and a later member fails before its own mutation;
5. corresponding pre-first-mutation failures.

For each, production planning/authorization as applicable, `StorageExecutor.run`, action recording, settlement/finalization and durable audit remain real. Instrument only the low-level filesystem transition needed to create the counterfactual. Assert action collection, outcome, `mutated`, exact bytes, execution status, durable audit and exception propagation.

A helper that directly constructs `StorageExecutionResult` and calls `record_or_reraise()` is useful focused coverage but cannot close these owner claims.

## R33-5 — real independent-P7-attempt scoping, exact deterministic bytes, and both target kinds

### Independent P7 attempt scoping

The current owner inventory explicitly supports multiple authenticated attempt authorities grouped under a generation and emits independently keyed released-scratch views/actions for their top-level members. The acceptance premise is therefore not hypothetical and is no longer an open design escape hatch.

Construct a bounded real-owner fixture with **at least two independently authenticated released P7 attempts present in one inventory/cleanup plan/execution**. Then:

- inject a mutation-boundary `refused_no_change` in attempt A; later A actions are withheld without destructive calls while attempt B proceeds through its own real session;
- separately inject `partial_change_refused` in A after a known destructive prefix; later A actions are withheld, B proceeds, and the durable audit records A's exact mutation/bytes plus B's independent result;
- prove session cache keys/invalidation are attempt-scoped rather than generation/global-scoped.

Do not substitute storage-owned residue or another non-P7 action for the independent attempt claim. If implementation unexpectedly cannot construct the two-attempt plan despite the owner model, treat that as evidence of a newly discovered implementation/owner-graph issue and route it explicitly rather than weakening the test.

### Exact deterministic action bytes

The post-mutation acceptance must assert a known exact value, not a range. Build/select a deterministic fixture with a known removed prefix and assert equality at:

- the action-local `reclaimed_bytes` field;
- execution aggregate;
- durable audit action and aggregate.

`> 0`, `<= planned`, or aggregate-equals-sum without a known oracle is insufficient.

### Mandatory complete target identity — file and directory

For **both** a top-level released regular file and a released directory:

- missing identity and each one-key-incomplete identity over every current `TARGET_IDENTITY_DIMENSIONS` key refuse before descriptor-relative stat/open/unlink/rmdir;
- target remains intact;
- complete identity retains ordinary staleness/replacement behavior;
- closed/spent capability still rejects before any filesystem observation regardless of identity validity.

## R33-6 — consolidate generic removal authority without breaking public compatibility

The package currently exports `remove_durably` while consequential cleanup uses the newer typed `remove_durably_outcome`. Repeated recursion repairs must not leave two independent generic destructive implementations whose safety properties can drift.

### Required reconciliation

- Use semantic/reference analysis to identify every production and test caller of `remove_durably`, `remove_durably_outcome`, `_remove_tree_tracked`, `_remove_tree_or_file_tracked`, and any replacement recursive helper.
- Consequential `StorageExecutor`/cleanup paths must route through one canonical typed outcome + action-ledger implementation.
- If `remove_durably` remains a supported public compatibility surface, preserve its documented bool contract with a thin wrapper/adaptation over the canonical safe mechanism where feasible; partial failures must still propagate truthfully rather than being converted to false/no-op.
- Do not delete the public export merely because no in-repository caller remains. Removal requires an independently authorized compatibility/deprecation decision.
- Retire obsolete private recursive helpers after all callers move, or give each retained helper a distinct justified responsibility. No dead unsafe fallback remains reachable.

### Structural acceptance

Prove source/reference absence of consequential bypasses to a pathname/boolean recursive remover and prove the public export, if retained, delegates to the canonical safe mechanism rather than owning a second traversal algorithm.

## R33-7 — documentation/authority alignment for traversal ownership

`storage.trust.walk_contained()` currently describes itself as “the single traversal primitive every recursive storage action uses,” while the accepted P7 mutation design already has an owner-specific descriptor recursion and Revision 33 requires a descriptor-safe destructive recursion for generic/common cleanup.

Update affected durable documentation/comments so they distinguish:

- canonical **mount-boundary policy** (`storage.trust`);
- read-only/planning traversal helpers;
- descriptor-relative destructive traversal owners.

Do not rewrite architecture chronology. The product contract should describe current ownership, not preserve a statement that becomes false after the repair.

The storage specification already requires descriptor-relative P7 recursion and truthful action accounting. Adjust it only where the generic/common recursion or mutation-ledger ownership needs consumer-facing clarification; regenerate its committed PDF derivative if the source changes.

## R33-8 — exact-candidate acceptance must be snapshot-complete

Revision 32 compressed a previously known affected-regression list into generic owner labels. That loses actionable task-specific acceptance under the snapshot-loss counterfactual. The following known checks are mandatory unless final impact analysis **broadens** them; it may not silently replace them with a narrower subset:

### Focused/current repair

Run the focused R22-R33 storage/P7 namespace, state, proof, release/root/target identity, capability, mutation outcome, zero-credit mutation, recursive race/mount, concurrency and failure counterfactuals added/affected by this work.

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

Final affected-surface re-derivation may add files/nodes when the assembled implementation shows additional impact. It may remove a named check only if repository evidence proves the test is retired/renamed or wholly unrelated after a legitimate design-preserving change, and that reconciliation must be stated rather than silently omitted.

### Repository/static/document checks

- `pytest --collect-only -q` over the maintained suite;
- compile/import checks for changed Python modules;
- `git diff --check` and repository-required static checks;
- focused structural guard for unsafe pathname recursive deletion and consequential bypasses;
- affected Markdown/PDF source/derivative validation.

### Final fresh acceptance

After the last executable/test edit:

1. record exact executable commit and tree;
2. re-derive the affected surface from the assembled candidate;
3. run a fresh complete affected regression/integration pass on that exact tree;
4. record actual command/node selection and pass/fail/skip summaries;
5. compare any later plan/docs-only or generated-PDF-only successor to prove it has no executable/test change before reusing functional evidence.

A required command that did not execute is not a pass. Whole-repository behavioral pytest remains conditional on unbounded final impact or independent repository policy. External DFT, long GPU production, and environment-specific HPC/shared-storage qualification remain deferred and nonblocking.

## Tool-assisted review/implementation guidance

Serena and Semgrep are high-information instruments for this bounded repair but are not new product dependencies or normative authorities.

When available:

- **Serena:** inspect definitions/references/callers for `remove_durably`, `remove_durably_outcome`, `remove_certified_subtree`, `_remove_tree_tracked`, `_remove_tree_or_file_tracked`, replacement fd-descent helpers, `MutationLedger`, `walk_contained`, `crosses_mount_boundary_at`, and P7 `remove_released_attempt_member`; use the caller graph to prove all consequential paths converge on the intended owners.
- **Semgrep:** run focused local structural rules for pathname recursive-destructive patterns and bypasses. Any acceptance-critical custom rule must be checked against one known-positive unsafe example and one known-negative fd-relative safe example before a zero-finding claim is used.
- Cross-check tool results with direct source/AST inspection because Python dynamic calls/monkeypatching and test-only imports can escape a single static model.

Do not upload private source/findings to managed/cloud Semgrep services. Do not commit `.serena`, `.hypothesis`, Semgrep cache, or one-off findings. If these tools are unavailable, equivalent local AST/text/reference analysis may establish the structural claim; the engineering invariant is mandatory, not a particular tool invocation.

The active workplan remains bound to Protocol `5.10.0`; using capabilities introduced as optional methodology in a newer installed skill does not silently upgrade the governing protocol.

## Implementation sequence and dual closure

### Stage A — canonical mutation ledger + descriptor-safe recursion/trust

Implement R33-1, R33-2, R33-3, R33-6 and any R33-7 documentation consequence needed to keep source ownership truthful. Treat this as one coherent behavior stage: mutation truth and safe descent are inseparable in the recursive owners.

Before dependent acceptance work:

- complete semantic/conformance review of the ownership map above;
- execute focused zero-credit, symlink-swap, mutation-time-mount, pre/post-mutation failure and recursive byte tests;
- run stage-local affected storage regression broad enough to cover P7, generic cleanup and common certified-subtree consumers.

### Stage B — real-owner acceptance closure

Implement/repair only the bounded test/fixture/routing consequences needed for R33-4 and R33-5. Do not patch semantic owners to return desired acceptance results. Low-level filesystem failure/race/mount instrumentation remains allowed below the real owner.

Run focused + stage-local affected regression for the added real-owner paths.

### Final assembled closure

Perform R33-8 exact-candidate reconciliation, affected-surface re-derivation, fresh affected regression/integration, static checks and documentation validation.

## Initially affected surface

Expected executable surface:

- `mdstats/training_data/qualification/store.py` — P7 action ledger integration and all-path failure truth;
- `mdstats/training_data/storage/outcome.py` — only minimal ledger API generalization if needed;
- `mdstats/training_data/storage/executor.py` — canonical fd-relative tracked generic/common recursion, action-boundary routing, compatibility wrapper consolidation;
- `mdstats/training_data/storage/trust.py` — canonical descriptor-aware mount decision helper and/or truthful traversal documentation where needed; do not duplicate policy elsewhere;
- `mdstats/training_data/storage/__init__.py` — only if public compatibility/export documentation must be reconciled;
- `mdstats/training_data/storage/commands.py` — only if real cleanup routing/session scoping requires a local correction;
- storage core/integration tests and the explicitly named affected regression files;
- storage specification Markdown/PDF if current contract wording changes.

Final impact analysis controls the actual affected surface and may broaden this list.

## Redesign triggers

This remains implementation rework under Revision 30 unless evidence proves one of these:

- supported public Python `>=3.10`/POSIX primitives cannot realize descriptor-relative/no-follow recursive deletion with canonical mount refusal and exact per-transition accounting;
- the existing `MutationLedger` model cannot represent a required action truth without changing the frozen four-outcome semantics;
- a supported external consumer of the public remover/result schema creates an unavoidable compatibility conflict with the required truthful typed path;
- current owner/synchronization contracts make the required safe destructive boundary impossible rather than merely requiring local implementation repair.

Reopen only the invalidated decision and preserve unrelated accepted architecture/evidence. The current owner model already represents multiple P7 attempts; inability of a test fixture to exercise them is not by itself a design trigger.

## Snapshot-complete handoff

The current supplied task authority after Revision 33 is:

1. `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md` — broader frozen owner-driven storage architecture/non-goals;
2. `STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md` — complete accepted final-apply design;
3. `docs/specs/training_data/mlff_storage_management_spec.md` — current product contract;
4. **this file** — complete current bounded implementation/review obligations, including every still-binding Revision-31/32 correction;
5. `AUTHORITY_REVISION_33.md` / `AUTHORITY.md` — current disposition/navigation.

Revision 31 and Revision 32 remain provenance only. No still-binding requirement depends exclusively on them, Git history, prior conversation, or local tool state.

**Design/workplan disposition:** Revision 30 remains **CLOSED / implementation-ready**; the current bounded implementation handoff is **Revision 33 / reopened for implementation**.

**Reviewed executable disposition:** `2e01d6fa5119ba67088f7c312c44962eba902c8e` remains **NO-PASS** pending Revision-33 implementation and exact-candidate acceptance.
