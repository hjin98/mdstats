---
kind: implementation-repair
package_id: CODE-MLFF-TARGET-SIZE-V7-P3-P3A9
parent_package_id: CODE-MLFF-TARGET-SIZE-V7-P3
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
status: accepted
accepted_closure_commit: 0bed3080ac4e3ba45f04fdf2fab891cfdc92fe58
repair_revision: 7
instruction_revision: 2
created_date: 2026-08-29
amended_date: 2026-08-29
entry_p3a8_commit: 472276ee521eb2b19177299c1c9ad660dbd6ad46
reviewed_candidate_commit: 4315b0ab4c13bbb45b963f3d816b5bb08aac75c0
superseded_closure_metadata_commit: 7eb3d9c1891a32a7dee7eeb31d39987730adb466
reconciliation_reason: Independent review of the first P3A9 candidate found the stale-current-head recovery algorithm itself conformant, but found one blocking functional-closure gap: the accepted concurrency invariant was not exercised through a real commit-versus-reconcile race under the canonical screen lock. The P3A9-local tests also overclaimed inherited P3A7/P3A8 restart-owner and P3F TRAIN2/EVAL2-failure evidence with weaker substitutes. This instruction revision reopens only P3A9 acceptance/closure, preserves the implemented reconciliation design as the baseline, and requires proxy-proof concurrency plus authoritative inherited regression before P3 may close and P4 may activate. It does not reopen P1-P3 scientific semantics, reducer policy, TRAIN2/EVAL2 semantics, checkpoint semantics, provider ownership, seed policy, or target-size decision logic.
---

# P3A9 — stale-head successor reconciliation repair

## 0. Review disposition and immediate sequencing correction

The implementation at `4315b0ab4c13bbb45b963f3d816b5bb08aac75c0` is the **reviewed P3A9 baseline**. Independent review did not identify a blocking product-code defect in its successor-chain replay algorithm. Do not roll back, replace, or redesign that implementation merely because closure evidence was incomplete.

The prior metadata commit `7eb3d9c1891a32a7dee7eeb31d39987730adb466` marked P3 accepted and P4 active before the acceptance contract was actually closed. That closure disposition is superseded by this instruction revision. Until a new accepted P3A9 closure commit is produced and recorded:

- P3A9 is active;
- cumulative P3 revision 7 is not yet formally closed;
- P4 must be treated as **blocked**, regardless of stale `status: active` metadata elsewhere;
- no P4 executable runtime-cutover implementation may begin.

This is an **acceptance/closure repair first**. Production code should remain byte-identical to the reviewed P3A9 baseline unless the newly required real-owner race or affected regression exposes an actual defect.

---

## 1. Purpose and authority

The frozen parent workplan remains the sole scientific and architectural verdict. This instruction closes one demonstrated crash-recovery defect in the existing P3 persistence owner and the missing evidence needed to prove that repair safe under concurrent restart/publication before P4 may begin.

P3A9 is **not** a new scientific revision. It preserves the complete cumulative P3 revision-7 contract through P3A8 and changes only recovery of an already-valid immutable execution-head chain plus acceptance evidence for the owning persistence/reconciliation path.

Accepted authority remains:

```text
P2 reducer/statistical owner
  -> P3 immutable boundary batches
  -> P3 immutable execution heads
  -> P3 typed resolver/reconciler
  -> rebuildable current_head.json pointer
```

`current_head.json` remains a recovery/localization pointer only. Immutable P3 evidence and deterministic reducer replay remain the scientific execution authority.

P4 is blocked until this repair has semantic/conformance closure, functional closure, and a committed accepted P3 closure point.

---

## 2. Demonstrated defect and reviewed baseline

Boundary publication is effectively:

```text
publish immutable boundary batch
 -> derive reducer post-state
 -> publish immutable heads/<head-digest>.json
 -> atomically replace current_head.json
```

A crash after the immutable successor head is durable but before the pointer replacement can leave:

```text
current_head.json -> H_g
heads/ contains H_g and valid child H_g+1
```

The pre-P3A9 reconciler validated the pointer ancestry and rejected immutable heads outside that ancestry as orphans. Therefore a valid crash-left successor could be rejected instead of deterministically recovered.

The candidate at `4315b0ab4c13bbb45b963f3d816b5bb08aac75c0` repairs that behavior in the existing coordinator by replaying authenticated ancestry plus a unique linear successor chain under the existing screen-commit lock and advancing the pointer only after deterministic scientific replay. That design remains the required baseline unless the new acceptance below proves a concrete implementation defect.

The remaining blocker is not a new recovery algorithm requirement. It is the absence of proxy-proof evidence for the already-frozen concurrency invariant:

```text
reconciliation racing legitimate P3 head publication/retry
must serialize through the canonical screen commit lock
and must converge on one authenticated history without fork or deadlock.
```

---

## 3. Required product behavior

### 3.1 Owning implementation

The owning P3 implementation remains:

`mdstats/training_data/target_size_execution/coordinator.py`

`reconcile_target_size_screen_root(...)` and `commit_target_size_boundary_batch(...)` remain the public semantic owners under acceptance. Their internal locked helpers may be reused, but tests must not substitute for either public owner.

Do **not** create a P4-specific replay routine, a second execution-head state machine, a second lock domain, or a compatibility wrapper that bypasses the existing P3 resolver.

Reuse the canonical P3 screen/head serialization and the same `.screen_commit.lock` ownership used by boundary-head publication.

### 3.2 Required reconciliation semantics

When reconciliation may mutate `current_head.json`:

1. Acquire the same canonical screen-commit serialization used by boundary-head publication. Do not introduce an independently ordered second head-commit lock.
2. If `current_head.json` exists, load it through typed P3 deserialization and require the corresponding immutable `heads/<digest>.json` record to exist with exactly the same authenticated content.
3. Load immutable heads through the existing typed resolver/deserializer; raw JSON fields or filenames are not authority.
4. Build ancestry only from authenticated immutable `parent_head_digest` relations.
5. Reconstruct/replay the reducer state of the current pointer ancestry using the accepted P3/P2 scientific replay path.
6. From the current authenticated tip, inspect immutable descendants and accept only a **unique linear successor chain**.
7. For each successor, require all of the following before advancing:
   - exactly one authenticated child from the current accepted head;
   - exact parent-head identity;
   - referenced boundary batch resolves through P3;
   - batch pre-state equals the exact replayed current reducer state;
   - all normal P3 batch/completion/evidence validation executes;
   - the frozen P2 reducer re-derives the successor post-state;
   - the re-derived post-state agrees exactly with the immutable head record.
8. Continue recursively only while each accepted head has exactly one validated child.
9. More than one authenticated child from any accepted head is a fork/conflicting history and must fail closed.
10. Any immutable head outside the accepted ancestry or unique validated successor chain remains an orphan/fork and must fail closed. Filesystem ordering, modification time, filename ordering, or "newest" heuristics may not choose a winner.
11. Only after the complete successor chain has passed typed loading and deterministic scientific replay may the reconciler atomically advance `current_head.json` to the validated tip.
12. If `current_head.json` is absent, retain the existing unique-tip repair behavior only after full typed ancestry validation and deterministic scientific replay.
13. Preserve the existing complete-batch-without-head recovery path. An unreferenced complete boundary batch may be committed only when it is the unique exact successor of the current reducer state under the existing commit owner.
14. Never accept a serialized `post_state` merely because its digest/schema parses. Re-derive the state through the accepted reducer owner.
15. Preserve create-or-verify immutable publication, historical owner proof, generation/attempt semantics, TRAIN2/EVAL2 evidence semantics, and checkpoint provenance unchanged.

### 3.3 Idempotency, locking, and concurrency

The repaired path must remain safe under restart, duplicate invocation, and concurrent process execution:

- an exact retry after pointer repair returns the same authenticated tip;
- reconciliation racing another legitimate P3 head commit/retry cannot manufacture a second history;
- two concurrent reconcilers of the same crash-left root converge on the same authenticated tip;
- canonical P3 locking prevents pointer/head mutators from choosing different descendants;
- a fork that already exists remains an error rather than being "healed" by choosing one branch;
- process identity/PID is not authority;
- no deadlock, lock leak, or partially advanced pointer may result from ordinary exception paths.

Do not broaden lock scope over expensive model inference or unrelated I/O merely to make the test easy. The lock protects the logical head/pointer commit/reconciliation critical section only. Do not add sleeps, retries, process IDs, or test hooks to product code as a synchronization mechanism.

---

## 4. Mandatory acceptance

Acceptance must exercise the **real P3 resolver/reconciler and real public commit owner**. A helper-only reconstruction, test-local replay engine, direct call to `_reconcile_target_size_screen_root_locked(...)`, direct call to `_commit_target_size_boundary_batch_locked(...)`, monkeypatched lock, or mocked atomic publication cannot establish closure.

Bounded deterministic scientific fixtures remain allowed below the accepted P3 owner boundary. Expensive numerical training/inference may be reduced/faked exactly as in the existing P3 acceptance fixtures, but the resolver, reconciler, public commit owner, typed persistence, P2 reducer replay, `.screen_commit.lock`, immutable publication, and pointer publication must remain real.

### 4.1 Focused crash/replay acceptance

The focused P3A9 suite must continue to prove at minimum:

1. complete boundary batch durable, immutable head absent -> existing unique-batch recovery succeeds;
2. immutable successor head durable, `current_head.json` still on predecessor -> unique successor is scientifically replayed and pointer advances;
3. stale pointer followed by multiple valid **linear** successors -> complete chain replays and pointer advances to the unique tip;
4. `current_head.json` missing with one valid chain -> pointer is rebuilt only after full replay;
5. stale pointer with one corrupted successor -> reject and do not advance pointer;
6. stale pointer with two children from the same parent -> reject as fork;
7. unrelated authenticated orphan head -> reject;
8. tampered parent/batch/pre-state/post-state relation -> reject through the owning validator/reducer path;
9. exact duplicate reconciliation/retry -> idempotent identical result;
10. repaired crash state replays to the same reducer state, active matrix/terminal state, and scientific outcome identity as the uninterrupted control path.

### 4.2 New blocking real-owner concurrency acceptance

Add explicit process-level race coverage. Sequential invocation is not sufficient.

#### Race A — legitimate commit/retry versus reconciliation on the same stale-pointer successor

Construct the ordinary real bounded P3 screen through one committed predecessor head `H0`. Then construct the next valid complete batch `B1` and immutable successor head `H1` using the same typed/P2 identities as the existing stale-pointer crash fixture, publish `B1` and `H1`, and deliberately leave `current_head.json` pointing at `H0`.

From that exact shared durable root, synchronize **two independent OS processes** immediately before they enter the public owners:

```text
worker A -> commit_target_size_boundary_batch(root, definition, H0.post_state, B1)
worker B -> reconcile_target_size_screen_root(root, restart_authority)
```

The test must use the production `.screen_commit.lock` opened by those public functions. Do not hold the lock in the parent, monkeypatch `fcntl.flock`, invoke the private locked helpers, or serialize the workers in the harness. A process barrier/event immediately before the public calls is allowed. Do not use `sleep()` ordering as the correctness oracle.

Required observations after both workers complete:

- both workers terminate within a bounded timeout; timeout/deadlock is failure;
- neither worker reports a serialization/corruption/fork error;
- both resolve/return the exact same authenticated `H1.content_digest`;
- `current_head.json` resolves to exactly `H1`;
- the immutable head graph contains one predecessor/successor history, not two competing children;
- the complete batch is not duplicated into a second logical boundary result;
- a fresh third-process `reconcile_target_size_screen_root(...)` returns the same `H1` and performs no scientific change.

This race is intentionally valid in either lock acquisition order:

```text
commit first     -> normal/create-or-verify H1 -> reconcile validates H1
reconcile first  -> replay/adopt H1            -> commit becomes exact idempotent retry
```

Both orderings must be semantically legal and converge on the same history; the test need not force which process wins.

#### Race B — concurrent reconcilers on the same stale-pointer root

Using a real root with `H0` current and one already-durable valid successor `H1`, synchronize two independent OS processes and invoke:

```text
worker A -> reconcile_target_size_screen_root(root, restart_authority)
worker B -> reconcile_target_size_screen_root(root, restart_authority)
```

Require:

- bounded completion with no deadlock;
- both workers return the same `H1.content_digest`;
- `current_head.json` ends at `H1`;
- no second head, fork, duplicate pointer authority, or alternate reducer state appears;
- fresh-process reconciliation remains idempotent afterward.

If the current test environment cannot construct `TargetSizeRestartAuthority` directly in child processes, reuse the existing P3F fresh-process reconstruction pattern. It is permissible to reconstruct the authority from the same durable scientific inputs in each child; it is not permissible to replace the real resolver/reconciler/commit owner with a test-local equivalent.

Process cleanup is part of the test: failed/timed-out children must be terminated/joined so the suite does not leak workers or retain the test lock.

### 4.3 Authoritative inherited regression — no weak substitutes

The following existing tests are authoritative inherited evidence and must execute on the final P3A9 candidate:

1. `tests/test_mlff_target_size_execution_p3f.py::test_p3f_subprocess_fresh_continuation_and_replay`
   - proves real fresh-process continuation and terminal replay through the assembled P3 owner path.
2. `tests/test_mlff_target_size_execution_p3f.py::test_p3f_fresh_process_train2_and_eval2_failure_replay`
   - proves fresh-process replay of real TRAIN2 and real EVAL2 failure evidence.
3. `tests/test_mlff_target_size_p3a4_final_review.py::test_p3a4_durable_trajectory_tampered_evaluation_state_rejected`
   - is the authoritative cumulative P3A7/P3A8 restart-owner acceptance: a self-consistently re-keyed durable LIVE-under-EMA graph must reach `resolve_target_size_candidate_for_resume(...)` and fail specifically at canonical trajectory-policy validation before continuation authorization.

The current P3A9-local functions named approximately:

- `test_p3a9_req11_success_train2_failure_eval2_failure_replay`;
- `test_p3a9_req12_p3a7_restart_owner_rejection_preserved`;
- `test_p3a9_req13_p3a8_owner_level_reconciliation_acceptance_preserved`;

must **not** be counted as substitutes for the authoritative tests above in their present form. Their current names overstate what they prove:

- a success + TRAIN2-failure fixture with the remaining cells successful does not prove EVAL2-failure replay;
- a generic `TrainingDataInputError` from an absent/non-resumable candidate does not prove the P3A7/P3A8 canonical LIVE-under-EMA rejection;
- a sequential reconciliation/continuation smoke test is useful but is not the authoritative P3A8 owner-level durable-tamper closure.

Implementation must either:

- remove those redundant weak sentinel tests; or
- rename/rewrite them so the test name and assertions claim only the narrow behavior actually exercised.

Do not weaken, delete, skip, xfail, or replace the authoritative inherited tests to obtain closure.

### 4.4 Affected regression gate

If this amendment changes **tests/workplan only** and product code remains byte-identical to `4315b0ab4c13bbb45b963f3d816b5bb08aac75c0`, execute at minimum on the final candidate:

```bash
pytest -q tests/test_mlff_target_size_p3a9_head_pointer_reconciliation.py
pytest -q tests/test_mlff_target_size_execution_p3e.py tests/test_mlff_target_size_execution_p3f.py
pytest -q tests/test_mlff_target_size_p3a4_final_review.py::test_p3a4_durable_trajectory_tampered_evaluation_state_rejected
```

Equivalent repository-supported invocation is acceptable, but every listed test/module must actually execute and pass; an unavailable or skipped required check is not a pass.

If the new concurrency acceptance exposes a product defect and **any production P3 source changes**, rerun the complete affected cumulative P3 execution/restart surface rather than only the new race tests. At minimum include all existing `tests/test_mlff_target_size_execution_p3*.py` and cumulative `tests/test_mlff_target_size_p3a*.py` acceptance files that exercise the changed coordinator/restart/persistence path, plus any additional affected module discovered from the actual diff.

Long GPU/real-production qualification is not part of this repair and remains deferred to final release.

---

## 5. Implementation instructions and decision routing

### 5.1 Default implementation path — expected

Because independent review found the `4315b0ab...` reconciliation algorithm sound, the expected repair is:

```text
add real commit-vs-reconcile process race
+ add concurrent-reconciler process race
+ remove/rename weak overclaiming P3A9 sentinel tests
+ run authoritative inherited P3A7/P3A8 and P3F evidence
+ run affected P3 regression
+ no production source change
```

Do not add another lock helper, retry loop, compatibility path, replay engine, or product synchronization primitive merely to satisfy the test.

### 5.2 If a race fails

A failing real-owner race is evidence of a product defect, not permission to weaken the fixture. Diagnose the earliest violated invariant in the existing commit/reconcile ownership path.

Allowed repair scope is the smallest owning-layer correction inside the existing P3 coordinator/persistence machinery that preserves all frozen semantics. Examples of legitimate local consequences, only if proven necessary, include:

- correcting use/scope of the existing `.screen_commit.lock`;
- correcting exact-retry handling when reconciliation wins the race;
- correcting pointer verification/publication order inside the existing owner;
- correcting exception-safe release of the existing lock.

Do **not** introduce:

- a second lock file or lock-order domain;
- PID/process ownership as authority;
- a winner-by-mtime/newest heuristic;
- a second mutable head/result manifest;
- a P4 replay path;
- a fallback that bypasses scientific replay;
- test-only hooks in product code.

Any production source change invalidates prior affected regression evidence for that path and requires the broader gate in section 4.4.

### 5.3 Structural/conformance closure

Before claiming P3A9 closed, inspect the final candidate and establish:

1. `reconcile_target_size_screen_root(...)` remains the sole public P3 screen reconciler;
2. `commit_target_size_boundary_batch(...)` remains the sole public complete-boundary head commit owner;
3. both serialize head/pointer mutation through the same canonical `.screen_commit.lock` domain;
4. no second replay/reducer authority, lock domain, mutable scientific head authority, or P4 compatibility path was added;
5. P2 reducer replay remains the sole scientific post-state derivation;
6. stale-pointer successor recovery still validates complete typed ancestry/evidence before pointer advancement;
7. fork/orphan corruption remains fail-closed;
8. the new concurrency acceptance invokes the real public owners in independent processes and cannot remain green if those owners stop sharing the lock;
9. the authoritative P3A7/P3A8 restart-owner test still fails specifically at canonical evaluation-state policy validation, not at a generic stale/missing-parent error;
10. real TRAIN2 and EVAL2 fresh-process failure replay remains passing.

---

## 6. Formal P3 closure and P4 handoff

After the amended P3A9 implementation/evidence passes:

1. perform semantic/conformance review against cumulative P3 revision 7 through this P3A9 instruction revision;
2. complete focused concurrency acceptance and the affected P3 regression required above;
3. commit the accepted P3A9 repair/evidence candidate;
4. record that **new** candidate commit as the accepted cumulative P3 closure commit;
5. update this file from `status: active` to `status: accepted` and record `accepted_closure_commit: <new-commit>`;
6. update package README/sequencing metadata to identify the same accepted P3 closure commit;
7. update P4 `entry_p3_closure_commit` and entry gate to that exact commit, then and only then change P4 to `status: active`;
8. only after the metadata handoff commit may P4-A executable work begin.

Do not reuse `4315b0ab4c13bbb45b963f3d816b5bb08aac75c0` as the final accepted closure commit unless the final candidate is literally that commit, which is impossible once the required concurrency acceptance is added. The historical product implementation remains useful baseline evidence, but the accepted closure identity must include the new required tests/evidence-bearing source state.

Do not start P4 executable runtime-cutover work while P3A9 is active, while any required acceptance check is unexecuted/failing, or while P4 still points at the superseded closure commit.

---

## 7. Frozen / delegated / reopen boundary

### Frozen

- all P1/P2 scientific/statistical semantics;
- all cumulative P3 revision-7 execution, evidence, owner, reducer, checkpoint, EMA/LIVE, failure, and restart semantics;
- the reviewed P3A9 unique-linear-successor recovery design unless a real-owner race proves a defect;
- immutable execution heads/batches as scientific evidence;
- deterministic reducer replay as recovery authority;
- `current_head.json` as rebuildable non-scientific pointer/index only;
- fork/orphan corruption remains fail-closed;
- one canonical `.screen_commit.lock` domain for head/pointer mutation;
- no second replay owner;
- version-agnostic product naming;
- full long GPU qualification deferred.

### Delegated

- exact multiprocessing/subprocess harness mechanics used to start the two race workers;
- whether the child reconstructs `TargetSizeRestartAuthority` using the existing P3F pattern or safely inherits/passes the real typed authority under the platform's process model;
- exact helper names inside the test fixture used to construct the already-accepted stale-pointer crash state;
- whether the three weak P3A9-local sentinel tests are removed or renamed/re-scoped;
- exact broader pytest command expansion, provided the required affected files/tests actually execute.

### Reopen only on evidence

Reopen P3 design only if implementation proves one of the following:

- the current immutable-head representation lacks enough authenticated ancestry/state information to distinguish a unique valid successor chain from a fork without changing frozen P3 scientific semantics; or
- the single canonical screen-commit lock cannot provide correct commit/reconcile serialization under the actual supported process model without a material ownership redesign.

If either occurs, stop before P4 and reopen only the affected P3 persistence/concurrency representation. A mere failing test caused by a local lock-scope, exact-retry, pointer-publication, or fixture defect is implementation repair, not architecture reopening.

Legacy compatibility, desire to avoid the process-level race tests, test runtime, or convenience of handling the crash in P4 are not reopen conditions.
