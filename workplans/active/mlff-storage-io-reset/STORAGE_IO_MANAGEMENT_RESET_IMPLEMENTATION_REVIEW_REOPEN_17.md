---
kind: implementation-review-reopen
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1-R37-IR17
parent_workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
status: reopened
reviewed_date: 2026-09-03
reviewed_authority_revision: 37
reviewed_plan_commit: ecf9feecefaac2612d36db8f656d7fec2d7a81b6
reviewed_executable_commit: 9db97f72a6ba033aa4b092edb0ece39db56f5b23
reviewed_executable_tree: a09dabfe5eb7279adb9398a98f9349c9713962a8
reviewed_branch_head: bd4b78e59f0b500ac130597943adab5e07fcad4b
reviewed_branch_tree: 683fcc2324780a6f9b3dba4aab98f949090529e4
review_verdict: NO-PASS
scope: bounded R37 implementation correction for transition-exact destructive authority from acquisition through parent durability, close-ranking completeness, real-owner acceptance, and exact-candidate evidence
precedence: Revision 30 and Revision 37 remain the accepted design/workplan authority; this file is snapshot-complete for still-open implementation/review work after candidate 9db97f72 and does not create new product semantics
---

# Storage/I-O reset implementation review reopen 17 — refined R37 closure

## Disposition

**Reviewed executable: NO-PASS.**

The executable candidate is:

```text
commit  9db97f72a6ba033aa4b092edb0ece39db56f5b23
 tree    a09dabfe5eb7279adb9398a98f9349c9713962a8
```

The branch successor is:

```text
commit  bd4b78e59f0b500ac130597943adab5e07fcad4b
 tree    683fcc2324780a6f9b3dba4aab98f949090529e4
```

and changes only the generated storage-specification PDF. Behavioral findings therefore bind to executable tree `a09dabfe...`.

The candidate closes substantial Revision-37 work: unlink/publication transition callbacks occur at the actual syscall transition; archive blob/manifest/catalog phases and restore-journal phases are transition-exact; final directory removal compares the entry name against the still-open authenticated descriptor; typed common-member authority is present; P7 session invalidation is one-way; and the core/integration suites contain materially stronger counterfactuals.

The remaining work is bounded implementation/acceptance nonconformance under Revision 30 and Revision 37. No Revision 38 or product redesign is justified. This refinement closes the remaining plan-level handoff gaps found after IR17 was first written: the root-of-trust must itself be justified rather than shifting an absolute open upward; ordinary single-file cleanup must retain the plan-bound target identity through its unlink boundary; the directory-entry durability step must use the same authenticated parent capability rather than a later pathname re-resolution; and P7 session-acquisition close ranking is an explicit closure obligation rather than only a census prompt.

## Review method and evidence boundary

The review reconciled the exact candidate against:

- `STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md`;
- `AUTHORITY_REVISION_37.md`;
- `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_16.md`;
- `docs/specs/training_data/mlff_storage_management_spec.md`;
- changed storage/P7 owners and the core/integration acceptance source.

Serena/Semgrep remain optional Protocol-5.10 evidence helpers. Use them when available for the bounded reference/close-family census, but tool absence does not waive any product claim and may be replaced by direct AST/reference/source inspection. Real-owner acceptance remains mandatory regardless of tooling.

GitHub records only the successful documentation-PDF workflow for executable commit `9db97f72...`; no behavioral CI/status or other exact-candidate execution evidence closes the required affected regression/integration pass. An implementation commit message or test source is not execution evidence.

# Protected concern and capability lifetime

A consequential storage action may mutate only the filesystem object and owner ancestry that the immutable plan and current semantic owner authorize. The protected lifetime is:

```text
plan/owner identity
  -> authenticated root of trust
  -> componentwise no-follow descriptor descent
  -> opened target/container identity comparison
  -> enumeration/member observation
  -> destructive syscall
  -> same-parent directory-entry durability
  -> descriptor close/finalization
```

Authority may narrow at any point; it may never be transferred to a same-name replacement. A pathname observation before opening is only an early refusal optimization. Once a descriptor capability exists, later mutation or durability may not fall back to a fresh pathname resolution merely because that is convenient.

The root of the descriptor chain must itself be justified. An implementation may use an already-retained owner/campaign descriptor whose identity/stability is guaranteed by the existing frozen owner+synchronization contract, or open an anchor and compare it against an already-bound owner/plan identity. Merely replacing `open(path.parent)` with `open(path.parent.parent)` is not continuous authentication. If no existing synchronization-stable or identity-bound anchor can support the required descent without a new persistent authority, stop and route to the redesign trigger below rather than inventing a registry.

Plan target identity and owner identities are independent constraints. When an owner supplies `root_identity` / `path_identity` (or engineering-equivalent live owner identities), those constraints remain mandatory in addition to `PlannedAction.filesystem_identity`; one may not silently substitute for the other.

# IR17-1 — destructive authority must be continuous from acquisition through durability

## IR17-1A — generic and fully-certified recursive root acquisition

Current generic recursion performs an early pathname observation and then opens a fresh multi-component parent path before opening the target. Opened-descriptor mount trust proves facts about the object that was opened; it does not prove that object is the one the plan authorized.

### Required end state

- Every consequential recursive cleanup call receives the exact plan-bound target identity from `PlannedAction.filesystem_identity` or an engineering-equivalent binding already owned by the plan. The default executor and production cleanup engine may not call an unbound removal mode when an action identity exists.
- Acquire the target from a justified authenticated anchor by componentwise no-follow descriptor descent, or through an engineering-equivalent retained capability. No fresh absolute/multi-component intermediate open is treated as authority merely because its final component used `O_NOFOLLOW`.
- Before enumeration or mutation, compare the actual opened target descriptor against the plan-bound target identity using all current bounded identity dimensions observable on the opened object and not weaker than ordinary plan revalidation (`kind`, `device`, `inode`, `size_bytes`, `mtime_ns` at the current schema). `action.size_bytes` remains separate aggregate accounting and is not substituted for the identity field.
- For a fully-certified common subtree, also compare the opened owner authority/container descriptors against the owner's bound identities. The plan target identity remains independently required.
- Disappearance or mismatch before the first transition is a no-change refusal. It never transfers authority to the replacement.
- Retain the authenticated parent/target descriptors through the existing immediate pre-`rmdir` identity comparison, the fd-relative `rmdir`, and the parent-directory durability step required by IR17-1D.
- The thin public compatibility remover may keep a non-plan-bound convenience mode only if consequential `StorageExecutor`/production cleanup execution cannot reach that mode. Do not weaken the consequential path for compatibility.

### Mandatory acceptance

Through real inventory/planning, production cleanup owner, `StorageExecutor.run`, settlement, and durable audit:

1. generic recursive action: let ordinary plan revalidation succeed, then replace the top-level directory with a same-name/same-device plain directory immediately before authority-bearing acquisition; replacement sentinel survives and action is refused/nonmutating;
2. replace an ancestor used by the acquisition path in the same timing window; no replacement descendant is enumerated or mutated;
3. run the fully-certified common equivalents;
4. prove the injected seam fired and refusal came from comparison of the actual opened capability with bound identity, not only from a pre-open pathname check;
5. preserve the post-open/pre-`rmdir` replacement counterfactual so both ends of the capability lifetime remain covered.

## IR17-1B — individually-authorized common cleanup

A pathname `lstat` of the authority root/container may remain an early refusal optimization, but `_remove_authorized_members` or its successor may not later reopen those names and treat the new descriptors as inheriting the prior authorization.

### Required end state

- Acquire the authority root through justified authenticated ancestry and compare the **opened** authority-root descriptor with `authority_identity` before opening the common container.
- Open the container relative to that authenticated descriptor and compare the **opened** container with `root_identity` before any member descent.
- Also enforce the plan-bound action target identity on the opened action target/container; owner identity and plan identity remain independent constraints.
- Apply canonical opened-descriptor mount trust to the actual authority/container descriptors and every nested intermediate directory.
- Preserve explicit owner-certified member kind. A bare path never defaults to regular-file deletion permission.
- Keep one action-wide `MutationLedger` across earlier successful members and a later identity/mount/type contradiction.

### Mandatory acceptance

Through real cleanup planning/execution/audit, inject a same-kind/same-device plain-directory replacement specifically between the early precheck and the authority-bearing open for both the authority root and the container. The replacement and sentinels survive. If an earlier genuine member in the same action was removed first, that prefix remains exactly attributed and the later contradiction produces the correct partial outcome.

## IR17-1C — ordinary single-file cleanup must spend the plan-bound target identity

The default single-file path currently revalidates the plan, later calls `path.lstat()`, and then performs a pathname unlink without comparing that live object to the action identity. A same-name file replaced after plan revalidation can therefore inherit the old action's permission.

### Required end state

- For every consequential action whose planned target is a non-directory file/symlink entry, acquire its parent through the same justified descriptor-root rule and observe the target no-follow relative to that authenticated parent immediately before unlink.
- Compare the live target against the current plan-bound filesystem identity dimensions. A same-kind replacement, changed inode, or an in-place change that makes a currently bound dimension differ refuses before unlink. Absence is `already_absent` and credits zero.
- Execute the unlink fd-relative to that authenticated parent. The accepted POSIX threat boundary remains unchanged: only the irreducible race after the final comparison and before the unlink syscall is outside the guarantee.
- `durable_unlink(..., dir_fd=...)` or an engineering-equivalent single canonical path should carry the transition callback and fsync the same parent descriptor. A consequential default cleanup must not fall back to absolute `Path.unlink()` once the authenticated parent capability exists.
- Do not invent a new persistent per-file authority or identity schema; use the plan identity already carried by `PlannedAction`.

### Mandatory acceptance

Through the real default cleanup executor/audit path:

1. replace a planned regular file with a same-name/same-kind different inode after ordinary plan revalidation but immediately before final observation; replacement survives and action is refused/nonmutating;
2. modify the same inode so a currently plan-bound identity dimension such as size/mtime changes in the same window; action refuses before unlink;
3. preserve the existing unlink-success/parent-durability-failure transition-truth counterfactual and exact byte accounting.

## IR17-1D — directory-entry durability must use the same authenticated parent

A correct fd-relative unlink/rmdir can still be followed by a misleading durability step if code closes the parent capability and later reopens `path.parent` by pathname. That can fsync a replacement directory rather than the directory in which this execution actually removed the entry.

### Required end state

- After a consequential file unlink or top-level directory `rmdir`, persist the directory-entry change using the **same authenticated parent descriptor** through which the mutation occurred, before releasing that descriptor.
- For file unlink, the existing `durable_unlink(..., dir_fd=parent_fd)` behavior is an acceptable realization because it fsyncs that descriptor after the transition.
- For top-level directory removal, fsync the retained authenticated parent fd after successful fd-relative `rmdir`; do not close it and then call a path-based `fsync_parent_directory(path)` as the authoritative durability step.
- A parent-fsync failure after successful unlink/rmdir is a structured partial mutation carrying exact action-local mutation/bytes; it never becomes a no-change refusal.
- Nested directory removals may rely on the already-authenticated containing directory's later fsync when that is the canonical parent durability point, but the top-level action entry removal must have an equivalent same-capability durability proof.

### Mandatory acceptance

- After successful generic file unlink and generic/fully-certified top-level directory `rmdir`, replace or rename the pathname spelling of the parent before the injected durability seam. Prove the durability operation targets the retained original parent descriptor, not the replacement pathname.
- Inject failure of that retained-parent fsync and prove the real executor/audit reports exact partial mutation; the replacement parent/sentinel is untouched.

# IR17-2 — close/finalization handling must have one exactly-once ranking policy

## IR17-2A — recursive mount refusal may not close before constructing the primary

When an opened child is refused by mount/authority trust, construct the intended structured refusal/failure first, then close through `_close_descriptor()` or the one canonical equivalent with that primary already active. A raw close exception may not bypass the `MutationLedger`.

Required behavior:

- mount/authority failure remains primary;
- close failure is logged/retained as secondary evidence when a primary exists;
- an earlier action-local mutated prefix crosses `record_or_reraise()` with exact bytes;
- no direct close-before-outcome branch remains in generic/common/P7 destructive paths after a descriptor has entered an action ledger.

Mandatory real-owner acceptance: an earlier certified sibling is removed, a later child is refused as a mount, and the refused child's close is injected to fail. Audit records the exact partial prefix, the mount refusal remains primary, close failure is secondary, and the mounted/external sentinel survives. Run a no-prefix control proving no fabricated mutation/bytes.

## IR17-2B — `open_directory_nofollow()` owns each acquired fd exactly once

### Required end state

- The helper has explicit ownership state and attempts at most one kernel close for every fd it acquires unless ownership is deliberately transferred to its caller.
- Failed `fstat` or wrong-kind observation is the primary namespace/authentication failure. Cleanup is attempted once. A cleanup-close failure is secondary and cannot trigger another close or replace the primary classification.
- Once a valid directory fd is returned, ownership is transferred and the helper performs no close.
- Because this primitive is shared by generic/common/P7 owners, affected destructive acceptance is rerun after the repair.

Mandatory primitive acceptance: instrument `os.close`; for wrong-kind and `fstat`-failure acquisition, prove cleanup is attempted exactly once even when close raises, the primary namespace/authentication failure remains visible, and no recycled fd can be closed by a second attempt.

## IR17-2C — P7 session acquisition and capability finalization use the same ranking doctrine

Known session-acquisition paths can return an owner/authentication refusal from inside a scope whose `finally` performs a raw close. A close failure there can replace the intended refusal. This must be closed explicitly, not left only to a search instruction.

### Required end state

- Before ownership transfers to a live `ReleasedAttemptSession`, every acquired attempt/ancestor descriptor is closed exactly once on every failed-acquisition path.
- If acquisition already has a primary namespace, root-identity, release-authority, state/proof, topology, or authentication refusal/failure, cleanup-close failure is secondary and may not replace that primary classification.
- Do not return a semantic refusal through a control-flow shape whose raw `finally: os.close(...)` can cancel/replace the return. Materialize the outcome, rank close, then return/raise.
- Once a session is successfully constructed, ownership transfers exactly once; the acquisition helper must not also close that fd.
- Existing one-way `ReleasedAttemptSession.close()` remains: mark closed and clear the stored fd before kernel close. Caller-owned primary-vs-secondary ranking remains binding.
- `_cleanup_engine` final session cleanup preserves the same policy and cannot fabricate success or erase an earlier mutation.

### Mandatory acceptance

- Inject an attempt-fd close failure during at least one early namespace/root-identity acquisition refusal and one post-authentication/release-authority refusal. The semantic owner/refusal remains primary, nothing mutates, and the descriptor has exactly one close attempt.
- Preserve `ReleasedAttemptSession.invalidate()` close-only evidence, real P7 post-mutation failure plus session-close failure, and cleanup-finalizer pre-/post-mutation close-only cases required by R37.

## IR17-2D — bounded close-family census

Perform a bounded structural/reference census of:

- `mdstats/training_data/storage/executor.py`
- `mdstats/training_data/storage/trust.py`
- `mdstats/training_data/qualification/store.py`
- `mdstats/training_data/storage/commands.py`

for raw `os.close` and equivalent descriptor-finalization sites in consequential acquisition, destructive traversal, session acquisition, capability invalidation, and cleanup finalization.

Observational readers need not be refactored for stylistic uniformity. Every consequential close that can run after an action-local mutation, while a structured product/refusal failure is active, or while spending a mutation capability must implement the R37 primary/secondary policy and exactly-once ownership. Discovered siblings are implementation consequences under this same family; do not return one site per review cycle.

Serena/Semgrep may accelerate this census when available. A direct AST/reference/source census is acceptable. Record the scan scope and disposition of consequential sites; tool absence does not relax the claim.

# IR17-3 — semantic-owner acceptance must replace proxy acceptance for material cleanup claims

Helper tests such as `_drive_removal()` may remain as unit evidence, but hand-constructed `StorageExecutionResult` plus direct `record_or_reraise()` cannot establish planner/authorization/synchronization/settlement/audit claims.

### Required owner-boundary acceptance

For each material case below, production inventory/planning/authorization, production cleanup engine/default executor as applicable, `StorageExecutor.run`, settlement/finalization, and durable audit remain in the path. Inject only the lowest filesystem/trust/close timing seam needed and assert that seam fired.

Cover:

- generic recursive root and ancestor replacement before authority-bearing acquisition;
- fully-certified common root/ancestor equivalent;
- individually-authorized authority-root/container replacement between precheck and opened-descriptor authentication;
- ordinary default single-file same-kind replacement and bound-identity change immediately before unlink;
- same-parent fd durability for file unlink and top-level directory `rmdir`;
- mount-refusal close failure after a mutated prefix plus no-prefix control;
- generic/common close-only post-mutation and pre-mutation cases;
- final post-open/pre-`rmdir` substitution;
- resolver unavailable and same-device mount cases;
- typed-member absence/replacement cases already required by R37;
- P7 session-acquisition primary+close-failure cases from IR17-2C.

Preserve the candidate's real-owner archive publication/restore-journal and P7 integration tests. Do not regress them while repairing cleanup.

# IR17-4 — exact-candidate behavioral evidence and family closure

After the **last executable or test edit**:

1. record the final executable commit and tree;
2. re-derive the affected surface from the assembled diff and references, including callers of changed descriptor/trust/removal/durability helpers;
3. run focused IR17 plus all maintained R22-R37 storage/P7 publication, namespace, mount, final-rmdir, final-unlink identity, mutation-truth, close/finalizer, concurrency, retry, and liveness nodes;
4. run complete:

```text
tests/test_mlff_storage_reset_core.py
tests/test_mlff_storage_reset_integration.py
```

5. run at minimum the existing owner regressions:

```text
tests/test_mlff_target_size_p4f_storage_docs_structure.py
tests/test_mlff_target_size_p6_destructive_closure.py
tests/test_mlff_p7_r11_repair_acceptance.py
tests/test_mlff_p7_r12_repair_acceptance.py
tests/test_mlff_p7_r13_authority_acceptance.py
tests/test_mlff_campaign_cli.py
```

6. include every maintained module/node discovered from the final candidate that exercises changed durability, archive/catalog/journal publication, archive/reclaim/restore, dedup/maintenance, generic/common cleanup, default single-file cleanup, or P7 released-attempt removal/session;
7. run maintained-suite `pytest --collect-only -q`;
8. run compile/import checks for every changed Python module, repository-required static checks, `git diff --check`, and conflict-marker scan;
9. structurally establish at minimum:
   - no consequential absolute/multi-component anchor is accepted merely because its final component was opened no-follow;
   - the chosen root of trust is either retained under an existing synchronization/owner guarantee or identity-checked against existing bound authority;
   - actual opened generic/common action targets are compared with the plan-bound identity before traversal/mutation, and owner identities remain independently enforced where supplied;
   - no consequential default or production cleanup caller reaches the unbound compatibility-removal mode when a `PlannedAction.filesystem_identity` exists;
   - the default consequential single-file path cannot call an unbound pathname unlink mode after a plan-bound parent capability exists;
   - top-level directory-entry durability does not close the authenticated parent and reopen its pathname before the authoritative fsync;
   - no direct close-before-structured-outcome remains in destructive paths;
   - no descriptor acquired by `open_directory_nofollow` or P7 session acquisition can be closed twice;
   - no post-failure pathname disappearance inference or signature-incompatible unlink fallback has returned;
   - publication/journal transition callbacks remain at atomic replace;
   - every final consequential `rmdir` remains fd-relative and immediately identity-checked;
10. validate the affected storage specification and regenerate/validate its PDF derivative if permanent Markdown changes;
11. record command/node selection and pass/fail/skip counts for the exact final executable tree. A later docs/workplan/PDF-only successor may reuse behavior evidence only after proving its executable tree is unchanged.

Full external DFT, long GPU production, and environment-specific HPC/shared-storage qualification remain deferred and nonblocking. Whole-repository behavioral pytest remains conditional on an affected surface that cannot be bounded or an independent repository requirement.

# Expected affected surface

Initially expect implementation/test impact in:

- `mdstats/training_data/storage/executor.py` — plan-bound removal entry, recursive capability lifetime, parent durability, close ranking;
- `mdstats/training_data/storage/trust.py` — exactly-once no-follow acquisition cleanup and any shared descriptor-identity helper;
- `mdstats/training_data/storage/commands.py` — production cleanup engine identity/capability handoff and final session ranking;
- `mdstats/training_data/qualification/store.py` — P7 failed-session-acquisition/finalization ranking;
- `mdstats/training_data/storage/durability.py` only if a narrow shared API adjustment is needed; preserve existing transition-exact callbacks and fd-relative unlink semantics;
- `mdstats/training_data/storage/plan.py` only if a narrow internal handoff is needed; no new persistent identity schema is expected because `PlannedAction.filesystem_identity` already owns the target binding;
- `tests/test_mlff_storage_reset_core.py`, `tests/test_mlff_storage_reset_integration.py`, and the owner regressions named above.

`storage/archive.py`, `storage/control_plane.py`, dedup/maintenance owners, and permanent storage documentation are regression surfaces because shared durability/executor behavior is involved, but they should not be edited unless final affected-surface evidence or a necessary local consequence requires it.

The final affected surface is re-derived from the assembled candidate and may expand through actual references/behavior; this initial list is not a ceiling.

# Implementation authority

## Frozen

- Revision-30/37 owner architecture, P7 science/currentness semantics, CampaignStore ownership, archive/dedup/restore product architecture, four cleanup outcomes, Python `>=3.10`, and the accepted POSIX threat boundary.
- `PlannedAction.filesystem_identity` remains the plan's existing bounded target identity; do not add a persistent inode/descriptor registry.
- Owner root/path/release identities remain independent constraints and may only narrow authority.
- Mutation truth, byte credit, durability truth, and diagnostic audit publication remain distinct claims.
- Once a descriptor capability is authenticated, mutation/durability may not widen back to a pathname-only authority path.

## Delegated

- Exact internal helper/class/context-manager signatures for carrying parent/target descriptors and identities.
- Whether generic and fully-certified common paths share one new acquisition helper or reuse/refactor an existing one, provided there is no weaker consequential bypass.
- Exact deterministic low-level test seams and whether the close-family census uses Serena, Semgrep, AST inspection, or an equivalent local method.
- Logging representation for secondary close evidence, provided primary product/mutation truth remains authoritative.

Prefer one canonical plan-bound descriptor-acquisition/finalization mechanism for generic/common cleanup rather than duplicating subtly different identity and close logic. If specialization remains, acceptance/structural evidence must cover each materially distinct consequential path.

## Reopen design only on evidence

Reopen only the affected design surface if implementation proves one of the following:

- no existing synchronization-stable or already-bound campaign/owner anchor can support continuous generic/common descriptor ancestry without introducing a new persistent authority or changing frozen ownership;
- the current plan/owner identity contracts cannot be compared to the actual opened target without changing a frozen public/persistent schema rather than a local internal handoff;
- the supported Python/platform floor cannot persist an fd-relative directory-entry mutation using the retained parent capability and no equivalent existing primitive satisfies the contract;
- a supported external consumer makes the consequential unbound compatibility path impossible to isolate without a material compatibility/design change;
- the required real semantic-owner acceptance cannot be exercised without replacing/bypassing the owner whose behavior is the claim, exposing an architectural testability/ownership problem.

Fixture inconvenience, optional-tool absence, or an ordinary implementation refactor is not a redesign trigger.

# Stage/gate sequence

Each material executable stage closes both semantics and function before dependent work proceeds: focused checks **plus stage-local affected regression** on the current stage candidate. A later edit to a shared primitive reruns earlier claims it can plausibly invalidate. Final assembled acceptance remains fresh after all executable edits.

## Stage A — close the descriptor-ownership/finalization family

Repair IR17-2A/2B/2C and complete the bounded IR17-2D census in one family closure so later acquisition work builds on final exactly-once primary/secondary semantics. Close every consequential sibling found by the census before leaving the stage. Run focused mount-refusal+close, wrong-kind/fstat-close, P7 failed-acquisition close-ranking, capability-finalizer tests, and stage-local affected regression across shared trust/P7/executor/commands finalization consumers.

## Stage B — authenticate plan-bound capabilities through mutation and durability

Repair IR17-1A/B/C/D using the stable Stage-A primitives. Add pre-acquisition replacement, default single-file identity, same-parent durability, mount/substitution, and final-rmdir counterfactuals. Before Stage C, run focused tests and the stage-local affected regression spanning default cleanup, generic/common cleanup, shared trust, and any P7 consumer affected by shared helper changes.

## Stage C — close semantic-owner acceptance

Add/convert IR17-3 tests so material cleanup claims traverse real inventory/planning/authorization, production engine, `StorageExecutor.run`, settlement/finalization, and audit. If these tests expose an executable defect, return that defect to Stage A or B as appropriate and rerun the invalidated stage-local regression; do not patch only the harness.

## Final assembled closure

Run IR17-4 on the exact final executable tree. Only after source/conformance closure, family-level structural closure, stage-local affected regression, final complete affected regression/integration, and exact-candidate evidence are all complete may implementation be passed and the storage-I/O workplan archived.

# Preserved conforming R37 implementation

Preserve unless a narrowly necessary local adjustment is required by the blockers above:

- transition-exact `durable_unlink` callback semantics and removal of mutation-fabricating fallbacks/post-hoc disappearance inference;
- transition-exact `durable_publish_bytes/json` callback at atomic replace;
- monotonic archive blob/manifest/catalog publication phases;
- restore nonterminal/terminal journal mutation phases and destination transition truth;
- hot-reclaim exact unlink transition truth;
- final no-follow name-vs-opened-descriptor comparison before fd-relative directory `rmdir`;
- descriptor-relative no-follow child recursion and canonical opened-descriptor mount policy;
- explicit typed common-member authority;
- one-way `ReleasedAttemptSession` invalidation and conforming P7 action/finalizer ranking;
- shared `MutationLedger`, exact action byte accounting, zero-credit mutation truth, complete P7 target identity, two-attempt isolation, and all other conforming Revision-30 through Revision-37 behavior;
- reconciled storage-specification direction.

# Final disposition

No Revision-37 redesign trigger is currently met. The newly explicit single-file target-identity and same-parent durability requirements are necessary consequences of already-frozen plan binding, transition truth, descriptor-capability, and durability semantics; they do not create a new product model.

**Design/workplan:** Revision 30 + Revision 37 + this refined IR17 handoff are **CLOSED / implementation-ready**.

**Implementation:** executable `9db97f72a6ba033aa4b092edb0ece39db56f5b23` / tree `a09dabfe5eb7279adb9398a98f9349c9713962a8` remains **NO-PASS / reopened for bounded R37 correction under IR17**.
