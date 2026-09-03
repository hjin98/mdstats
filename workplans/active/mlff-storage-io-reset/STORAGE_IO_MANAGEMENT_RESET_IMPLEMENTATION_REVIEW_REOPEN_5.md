---
kind: implementation-review-reopen
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1-R22
parent_workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
status: reopened
reviewed_date: 2026-09-02
reviewed_authority_revision: 21
reviewed_executable_commit: 9da6525be75c328ffbbf6968cebe773e2dc8921e
reviewed_executable_tree: 7ff82374cbc966795e710f21ba3737d892af57f2
reviewed_branch_head: 071387cb21c1a046f4ffa7b641bcdd3ad2da1699
review_verdict: NO-PASS
scope: independent implementation review of the Revision-21 closure; preserve all conforming Revision-20/21 repairs and reopen only the remaining P7 no-follow namespace race/root classification plus acceptance-counterfactual and exact-candidate evidence gaps
precedence: Revision 21 remains the accepted design. This review adds precise implementation and acceptance requirements where executable 9da6525... does not yet realize the frozen Revision-21 invariants. It does not reopen parent storage architecture or P1-P7 science.
---

# Storage/I-O reset implementation review reopen 5 — Revision 22

## 0. Verdict and reviewed candidate

**NO-PASS / reopened.**

The implementation reviewed is:

```text
executable commit  9da6525be75c328ffbbf6968cebe773e2dc8921e
executable tree    7ff82374cbc966795e710f21ba3737d892af57f2
branch head        071387cb21c1a046f4ffa7b641bcdd3ad2da1699
```

`071387cb...` is a generated-document-only successor to the executable implementation, so functional review remains bound to executable `9da6525...`.

Revision 21 remains the accepted design. The implementation closes most of Revision 20/21 correctly and those repairs must be preserved:

- `replace_records_atomically()` now checks observational writability before externalization and the accidental duplicate guard in `put_records()` is gone;
- the current P7 state reader requires a persisted exact digest and checks directory/state/canonical binding-derived attempt identity;
- storage owner views consume the authenticated state result rather than reparsing `QualificationAttemptState` independently;
- the P7 retention fence now has an explicit workspace-wide ambiguity mode;
- repeated terminal release validates/reuses the retained v3 proof and checks proof/state binding/publication fields;
- touched-attempt storage synchronization remains in place and `OwnerSynchronization.to_dict()` now exposes `attempt_roots`;
- the common owner-record reader fails closed where `O_NOFOLLOW` is unavailable rather than silently opening followably;
- existing typed P5/P7 proof, CampaignStore writer-gate, archive/dedup/restore/audit, and frozen P1-P7 scientific behavior remain accepted.

Three blocking groups remain: one source-level authority/race defect and two acceptance/evidence gaps.

---

## 1. IR22-1 — P7 namespace traversal is still path-racy and the family root can disappear from authority

### 1.1 Family-root wrong-kind/unreadable state is silently treated as “no attempts”

Revision 21 requires the qualification family root itself to participate in the no-follow authority hierarchy. A present symlink, special/wrong-kind object, or unreadable required owner namespace is unresolved authority because unknown attempt state may hide P5 references outside the P7 tree.

The candidate currently does the equivalent of:

```python
root = internal.resolve() / QUALIFICATION_ROOT_NAME
if observed_node_kind(root) != NODE_DIRECTORY:
    return ()
```

This collapses a legitimate absent P7 family and a present substituted/unreadable P7 family into the same answer: “there are no attempts.” In particular, a symlinked `.mdstats/qualification` root yields no `AttemptStateAuthority`, no owner-integrity failure, and no workspace-wide ambiguity. Unknown external references can therefore disappear from both the primary owner-graph gate and the defense-in-depth retention fence.

This is a genuine destructive-authority defect, not a reporting preference.

### 1.2 The hierarchy is classified first, then traversed by path

The candidate describes the census as no-follow at every authority-bearing component, but it still performs a path classification followed later by path-based directory traversal:

```text
observed_node_kind(root)      -> os.scandir(root)
observed_node_kind(generation)-> os.scandir(generation / "attempts")
observed_node_kind(attempt)   -> read attempt state through attempt/path
```

Those are separate namespace lookups. A directory can be replaced with a symlink after the check and before `os.scandir()`/the descendant open. `O_NOFOLLOW` on `attempt-state.json` only protects the final file name; it does not stop the kernel from following a symlink substituted into an ancestor component.

The accepted Revision-21 outcome is stronger: owner-namespace enumeration must **never traverse a substituted symlink/special ancestor as a directory**, including under concurrent substitution. Static “the symlink was already there before the scan” tests do not close this time-of-check/time-of-use seam.

### 1.3 Storage-facing attempt reporting still independently traverses the namespace by followable `Path` APIs

`qualification_views()` correctly uses `iter_attempt_state_authorities()` for state classification, but then independently enumerates P7 generation/attempt directories through the generic generation-root scan plus `Path.is_dir()` / `Path.iterdir()` to construct attempt views.

That second traversal does not independently confer `safe_reclaimable=True` when state is unresolved, so it is conservative for the currently tested static cases. It nevertheless violates the Revision-21 consolidation goal that storage-facing attempt enumeration/reporting not reach state-bearing namespace descendants through a followable parallel path. It can also traverse the target of a substituted generation/`attempts` symlink even while the strict state authority is reporting the namespace unresolved.

### Required repair

Implement one descriptor/identity-bound no-follow P7 namespace traversal on the supported POSIX target and make all storage-facing attempt enumeration derive from it.

1. **Distinguish absence from ambiguity at the family root.** A genuinely absent qualification family is ordinary “no P7 state.” If the path exists but is a symlink, regular file, special object, unreadable directory, or otherwise cannot be authenticated as the expected plain directory, return an explicit unresolved authority. Do not map generic `OSError` to absence at this boundary.
2. **Open authority-bearing directories atomically no-follow.** On the accepted POSIX/Linux target, preferred realization is `os.open(..., O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC)` (or equivalent) followed by `fstat()`. Child directories must be opened relative to an already authenticated parent descriptor (`dir_fd`/openat-style) or by an equivalent identity-bearing mechanism. A pre-check followed by a new path lookup is not sufficient.
3. **Enumerate from the authenticated directory identity.** `os.scandir(fd)`/descriptor-relative enumeration or an equivalent mechanism may be used. The enumeration must not re-resolve an already authenticated parent path merely to list its children.
4. **Validate generation namespace names.** Entries reserved as generation namespaces must satisfy the repository’s canonical `g<generation>` naming rule before they can contribute P7 attempt authority. A malformed reserved `g*` entry is an integrity problem, not another place to search for state.
5. **Authenticate the literal `attempts` child no-follow** relative to the generation descriptor. Absence is allowed. Present wrong-kind/symlink/special/unreadable is explicit unresolved authority.
6. **Authenticate each attempt directory no-follow** relative to the `attempts` descriptor. A substituted attempt root never supplies state through its target.
7. **Read `attempt-state.json` relative to the authenticated attempt identity.** Use a descriptor-relative no-follow regular-file open (or equivalent) and `fstat`; then retain all existing persisted-digest and three-way canonical identity checks. Do not fall back to a path that can follow a replaced ancestor.
8. **Proof certification must not lose the root binding.** `validate_bound_attempt_proof()` / `certified_attempt_nodes()` must either consume the same descriptor-bound attempt snapshot or freshly re-authenticate the complete ancestor hierarchy before reading the proof/observing descendants. An authenticated state object followed by a weaker path traversal is not a sufficient root binding.
9. **Use the same namespace result for attempt views/reporting.** `qualification_views()` must not independently rediscover attempt directories through followable `Path.is_dir()/iterdir()` after the strict census. Derive attempt roots and unresolved namespace facts from the strict traversal result. Durable non-attempt P7 reporting may remain separately bounded, but it must not traverse a symlink target to discover attempt state/scratch.
10. **Preserve bounded reporting.** The fix classifies namespace components and compact state only; it must not hash/walk released attempt descendants during ordinary `storage report`.
11. **Preserve synchronization semantics.** Consequential planning/revalidation still takes the established storage/P5/P7/attempt lock order. The repaired strict snapshot is rebuilt while the relevant owner seams are held before mutation. No expensive qualification work is moved under these locks.
12. If the supported target cannot provide an identity-bearing no-follow directory traversal that satisfies these invariants, stop and trigger Revision-21 redesign condition 2 rather than weakening the requirement.

### Required focused acceptance

Add proxy-proof tests through the real P7 owner/storage boundary:

1. **Family root substitution:** replace the qualification family root itself with (a) a symlink to a tree containing otherwise valid state and (b) one safely modeled wrong-kind/special object. The target state must not be consumed; owner integrity must fail; `require_planable()` must fail; the retention fence must enter workspace-wide ambiguity; a real P5 checkpoint must be denied by `CampaignOwnershipBoundary`.
2. **Family root unreadability:** where portable, make the family root unreadable; otherwise inject an `EACCES`/equivalent failure only at the filesystem-open seam below the real owner. It must become unresolved, never “no attempts.”
3. **Ancestor swap race:** deterministically substitute a symlink **after any preliminary observation but immediately before the authority-bearing directory open/traversal** for at least the generation root and the literal `attempts` container. Instrumentation may wrap the real filesystem primitive/real no-follow open to signal and pause; it must not replace the P7 semantic owner or storage planner. The valid target tree must never become authority.
4. Include the attempt-root form if the repaired implementation has a distinct root-open seam not already covered by the generation/`attempts` cases.
5. Repair the exact namespace and prove both global planability and the workspace-wide fence return to normal.
6. Keep the bounded-report counterfactual and prove the descriptor-bound traversal does not make report cost scale with attempt descendants.

---

## 2. IR22-2 — several required counterfactuals still do not prove the intended owner boundary

### 2.1 “Wrong-root self-digest-valid” test is not self-digest-valid

Revision 20/21 requires a copied/wrong-root state whose **own persisted digest remains valid**, so the test can only pass by enforcing root/identity binding rather than failing earlier on generic digest validation.

The candidate mutates `attempt_identity` in the copied payload but does not recompute `content_digest` for that `wrong_root_state` branch before writing it. The fixture is therefore digest-invalid and can pass even if root/identity checking regresses.

Required repair:

- construct a state with the wrong attempt identity/root relation;
- recompute and persist its exact `QualificationAttemptState.content_digest` after all mutations;
- assert the failure reason is the root/identity/canonical relation rather than self-digest mismatch;
- retain the real owner-graph/fence/P5 protection assertions.

### 2.2 P7 released-attempt special-node proof case is still absent

The released-attempt foreign-node matrix covers regular files, empty directories, nested symlink, and file/directory substitution, but no FIFO/socket/device/other safely modeled special node. The only new FIFO case is the **state authority file**, which is a different invariant.

Revision 19/20 explicitly requires special-node refusal in the **released-attempt topology proof/closed-subtree** path.

Required repair:

- create an unexpected FIFO under a released attempt (or replace one recorded released-attempt node with a FIFO) after the v3 proof exists;
- run exact P7 certification plus real storage planning/execution path;
- prove the FIFO is classified as special/other, grants no closed-subtree authority, is not traversed/read as a regular file, and no released scratch action consumes it;
- retain the separate state-FIFO test.

### 2.3 The two-ordering reopen/cleanup race does not prove which ordering actually happened

The candidate parameterizes `owner_first=True/False`, starts the selected contender first while an externally held production attempt lock blocks both contenders, then releases the seam. It asserts only that nothing passed the held seam and that the final state is active. It does **not** assert that the intended first contender actually acquired the production attempt lock before the second after release. Kernel/thread scheduling is not a contractual FIFO queue.

Thus both parameter values can pass while exercising the same actual lock acquisition order.

Required repair:

Make both actual orderings deterministic while retaining the real lock and real owner/executor:

- instrumentation may **wrap and delegate to the production attempt lock**, signalling only after the real lock is acquired and optionally pausing there; do not replace it with a fake mutex or local boolean;
- in the owner-first case, prove the real P7 reopen acquired the seam, start real storage cleanup while it is paused, and prove cleanup cannot acquire/complete until owner release;
- in the storage-first case, prove the real storage barrier acquired the same attempt seam, start the real reopen while storage is paused, and prove reopen cannot acquire/complete until storage releases;
- assert the observed acquisition/completion ordering in each case, not merely the final state;
- preserve the postcondition that active scratch is never reclaimed and the legal aborted -> active lifecycle remains intact.

### 2.4 Ancestor static symlink tests remain useful but are not race proof

Keep the current generation-root and `attempts`-container static symlink tests. They establish fail-closed behavior when substitution predates the scan. They do not substitute for IR22-1’s concurrent TOCTOU counterfactual.

---

## 3. IR22-3 — exact executable candidate regression/integration evidence is still not supplied

Revision 21 E5/F requires commands, result summaries, exact executable commit and executable tree after final affected-surface re-derivation.

For executable `9da6525be75c328ffbbf6968cebe773e2dc8921e`, GitHub exposes one successful check run named `docs`. There is no storage-core, storage-integration, P7 qualification, affected-owner, final affected-surface, or broader functional check attached to the exact executable commit. The implementation diff contains refreshed benchmark output, but no candidate-bound functional command/result evidence artifact. Benchmarks and successful docs generation do not establish regression/integration acceptance.

This is independently blocking even if source conformance were otherwise complete.

### Required final evidence after IR22-1/2 source/test repair

Because the repair changes the P7 authority path, earlier functional evidence for that path is invalidated. On the exact final executable candidate:

1. run the complete IR22 focused counterfactual set;
2. run all Revision-20/21 focused CampaignStore/P7 proof/state/fence/concurrency cases, including the corrected proxy-proof cases above;
3. run all still-binding R19-A through R19-D focused tests and affected R17/R18 storage tests;
4. run full `tests/test_mlff_storage_reset_core.py`;
5. run full `tests/test_mlff_storage_reset_integration.py`;
6. run affected P1/P3/P4/P5/P7 currentness, publication, restart, retention, qualification-owner tests plus P6 destructive closure where the shared owner/inventory/executor path is affected;
7. re-derive the final affected surface from the completed repair diff;
8. run a **fresh final affected regression/integration set** after that re-derivation;
9. run CPU-safe broader/full repository tests if the affected surface cannot be confidently bounded;
10. run static checks and affected docs/spec/build validation.

Record the actual commands, pass/fail/skip counts or equivalent result summaries, and the exact executable commit/tree. `not run` is not `pass`. CI is acceptable, and concise committed/review-visible command output is acceptable; do not create a parallel evidence bureaucracy merely to satisfy the format.

A generated-doc-only successor may reuse this evidence only after compare proves it changed no executable/configuration/persistence/test-harness contract.

Full external-DFT, long GPU production, and environment-specific HPC/storage qualification remain deferred and are not blockers.

---

## 4. Preservation boundary

Do **not** redesign or reimplement conforming work merely because this review reopened the candidate.

Preserve:

- Revision-19 typed P5/P7 node authority and common `authorized_members()` semantics;
- P5 completion/topology architecture and bounded normal reporting;
- P7 v3 proof schema/publication ordering and current proof/state cross-field validation;
- P7 canonical binding-derived attempt identity and mandatory persisted state digest;
- workspace-wide P7 ambiguity fence semantics;
- existing storage/P7 attempt synchronization and global lock order;
- CampaignStore shared RLock/flock writer gate, constructor participation, writer-lock ownership, and now-correct early replacement guard;
- archive, dedup, reclaim, restore, audit, admission and storage-control-plane architecture;
- parent P1-P7 scientific/currentness/publication/qualification rules.

The source repair belongs in the existing P7 owner/storage-authentication layer. Do not introduce a second storage state machine or path-authentication authority.

---

## 5. Non-blocking cleanup notes

These do not independently drive the NO-PASS verdict:

1. `QualificationInputBinding.attempt_identity` and the storage-side `_expected_attempt_identity()` currently implement the same canonical formula separately. Revision 21 said to reuse/extract the production helper where practical. The formulas currently agree, so this is maintainability debt rather than a present correctness blocker. If the identity code is touched, consolidate the formula under the qualification owner instead of leaving two conventions to drift.
2. The new observational externalization test has a redundant trailing assertion containing `or True`. The preceding whole-workspace `_tree_signature(...) == before` assertion is the real strong proof and remains effective, so this does not invalidate the test. Remove the dead assertion if the test is touched.
3. The `O_NOFOLLOW`-unavailable owner-record behavior now fails closed and documents the supported target, closing the prior non-blocking portability note.
4. `OwnerSynchronization.to_dict()` now includes `attempt_roots`, closing the prior diagnostic note.

---

## 6. Rework routing and exit criteria

This is **implementation nonconformance + acceptance closure**, not design reopening.

Resume at the earliest affected gate:

- P7 namespace/authentication repair: **R21-E2**;
- CampaignStore R21-E3 source is conforming and should not be reopened unless the new diff actually touches it;
- corrected counterfactuals and exact functional evidence: **R21-E5/F**.

The next implementation review may return PASS only if all of the following are true:

1. a present but non-directory/unreadable qualification family root is explicit unresolved authority, never “no attempts”;
2. every authority-bearing P7 directory descent is identity-bearing/no-follow at the traversal syscall boundary, so an ancestor swapped to a symlink cannot be traversed after an earlier check;
3. storage-facing attempt enumeration/reporting derives from the same strict namespace result rather than a parallel followable attempt traversal;
4. persisted state digest and the three-way canonical identity invariant remain enforced;
5. repeated terminal proof validation and workspace-wide ambiguity fencing remain intact;
6. corrected wrong-root digest-valid, released-attempt special-node, deterministic two-ordering owner/storage race, family-root, and concurrent ancestor-swap tests pass through real owners;
7. all required candidate-bound final regression/integration evidence is supplied for the exact final executable commit/tree.

**Disposition:** executable `9da6525...` / tree `7ff82374...` is **NO-PASS / reopened under Revision 22**. Revision-21 design remains accepted and no parent scientific/storage architecture redesign is authorized.
