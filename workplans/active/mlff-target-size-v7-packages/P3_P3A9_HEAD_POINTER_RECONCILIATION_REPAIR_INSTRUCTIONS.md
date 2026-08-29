---
kind: implementation-repair
package_id: CODE-MLFF-TARGET-SIZE-V7-P3-P3A9
parent_package_id: CODE-MLFF-TARGET-SIZE-V7-P3
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
status: active
repair_revision: 7
instruction_revision: 3
created_date: 2026-08-29
amended_date: 2026-08-29
entry_p3a8_commit: 472276ee521eb2b19177299c1c9ad660dbd6ad46
reviewed_product_baseline_commit: 4315b0ab4c13bbb45b963f3d816b5bb08aac75c0
reviewed_acceptance_candidate_commit: 0bed3080ac4e3ba45f04fdf2fab891cfdc92fe58
superseded_closure_metadata_commit: bf24a9e5ae17724d1ecd90a9e11643534e7f79f5
reconciliation_reason: Independent review of the instruction-revision-2 candidate found the P3A9 production reconciliation implementation still conformant and found the new process races useful, but the races were not discriminating evidence for the frozen shared-lock invariant because the tested operations can converge correctly even without serialization. The review also found that the claimed third-process post-race reconciliation was still executed in the parent pytest process. This instruction revision reopens only P3A9 acceptance/closure, preserves the product implementation and prior process races, and adds deterministic canonical-lock-identity acceptance plus actual fresh-child reconciliation. It does not reopen P1-P3 scientific semantics, reducer policy, TRAIN2/EVAL2 semantics, checkpoint semantics, provider ownership, seed policy, or target-size decision logic.
---

# P3A9 — stale-head successor reconciliation repair

## 0. Review disposition and sequencing override

The production P3A9 implementation at `4315b0ab4c13bbb45b963f3d816b5bb08aac75c0` remains the reviewed product baseline. The acceptance candidate `0bed3080ac4e3ba45f04fdf2fab891cfdc92fe58` correctly added real OS-process races and removed the previously overclaiming local req11/req12/req13 substitutes. Independent review still found one blocking acceptance-harness gap: those races do not prove that the two public mutation owners actually contend on the same canonical lock.

The subsequent metadata commit `bf24a9e5ae17724d1ecd90a9e11643534e7f79f5` therefore closed P3 and activated P4 prematurely. This instruction revision supersedes that closure disposition.

Until a new P3A9 acceptance candidate satisfies this instruction and a new closure commit is recorded:

- P3A9 is **active**;
- cumulative P3 revision 7 is not formally closed;
- P4 is **blocked**, even if older P4/README metadata still says `active` or points at `0bed3080...`;
- no P4 executable runtime-cutover implementation may begin.

This is expected to be a **test/acceptance-only repair**. Do not modify `coordinator.py` merely to satisfy the harness. Production code may change only if the new lock-identity acceptance or affected regression demonstrates a real product defect.

---

## 1. Frozen authority and protected behavior

The frozen parent workplan remains the sole scientific/architectural verdict. P3A9 remains a persistence/restart repair, not a new scientific revision.

The authoritative chain remains:

```text
P2 reducer/statistical owner
  -> P3 immutable complete boundary batches
  -> P3 immutable execution heads
  -> P3 typed resolver/reconciler
  -> rebuildable current_head.json pointer
```

The following remain frozen:

- all P1/P2 scientific/statistical semantics;
- all cumulative P3 revision-7 execution, owner, evidence, checkpoint, EMA/LIVE, TRAIN2/EVAL2 failure, and restart semantics;
- immutable batches/heads as durable scientific execution evidence;
- deterministic P2 reducer replay as the sole post-state/recovery authority;
- `current_head.json` as a rebuildable localization pointer, not scientific authority;
- unique-linear-successor recovery from a stale pointer;
- fork/orphan corruption remains fail-closed;
- `commit_target_size_boundary_batch(...)` remains the public complete-boundary/head commit owner;
- `reconcile_target_size_screen_root(...)` remains the public screen reconciliation owner;
- both public mutation owners serialize head/pointer mutation through the single canonical `root/.screen_commit.lock` domain;
- no second replay owner, mutable scientific head authority, compatibility fallback, PID authority, or P4-side recovery path;
- version-agnostic product naming;
- long GPU/real-production qualification remains deferred.

The reviewed production source currently opens the same exact lock path in both public owners:

```text
root_path / ".screen_commit.lock"
```

and acquires `fcntl.LOCK_EX`. The acceptance repair below must prove that property without replacing either public owner.

---

## 2. Exact remaining acceptance defect

Instruction revision 2 required process-level races. Candidate `0bed3080...` added:

```text
Race A: commit_target_size_boundary_batch(...) vs reconcile_target_size_screen_root(...)
Race B: reconcile_target_size_screen_root(...) vs reconcile_target_size_screen_root(...)
```

on the same stale-pointer durable graph.

Those are valid concurrency regression tests and must remain, but they are not sufficient proof of canonical lock ownership. In the tested stale-pointer state, both operations target the same already-valid successor and use idempotent immutable publication/atomic pointer replacement. Therefore the following broken implementation could still pass those races:

```text
commit owner uses no lock (or a different lock)
reconcile owner uses no lock (or a different lock)
both happen to converge on the same H1
```

P3A9 closure therefore requires a **discriminating lock-identity test**: evidence must fail if either public owner stops contending on the exact canonical `.screen_commit.lock`, even when the underlying mutation would otherwise converge harmlessly.

The candidate also called the final post-race reconciliation directly in the parent pytest process while describing it as a third process. That must be replaced with an actual newly spawned child process.

---

## 3. Required implementation scope

### 3.1 Default path — tests only

Expected changed executable surface:

`tests/test_mlff_target_size_p3a9_head_pointer_reconciliation.py`

Do not change production P3 source if the new acceptance passes against the reviewed baseline.

Retain the existing focused crash/replay tests and the two process races from `0bed3080...`, subject to the robustness corrections in this instruction.

### 3.2 Public semantic owners under acceptance

The tests must invoke the real public functions:

```python
commit_target_size_boundary_batch(...)
reconcile_target_size_screen_root(...)
```

The tests may **not** use either private locked helper as the operation under acceptance:

```python
_commit_target_size_boundary_batch_locked(...)
_reconcile_target_size_screen_root_locked(...)
```

The tests may not monkeypatch `fcntl.flock`, monkeypatch either public owner, mock atomic pointer publication, or replace P3 typed persistence/reducer replay with a test-local implementation.

Bounded deterministic scientific fixtures below the P3 owner boundary remain allowed exactly as in the existing P3 suite.

---

## 4. Mandatory canonical-lock-identity acceptance

Add the following acceptance to the P3A9 test file. The naming below is recommended and may be used verbatim.

### 4.1 Test-fixture lock holder

Add a small **test-only external lock-holder process** whose sole purpose is to act as an adversarial process already owning the production lock file.

Recommended helper behavior:

```python
def _worker_hold_screen_commit_lock(root_path, acquired_event, release_event, queue):
    lock_path = Path(root_path) / ".screen_commit.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "w") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        acquired_event.set()
        if not release_event.wait(timeout=10):
            queue.put(("holder", None, "release timeout"))
            return
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    queue.put(("holder", "released", None))
```

The exact helper shape is delegated, but these semantics are mandatory:

1. it opens **exactly** `<screen-root>/.screen_commit.lock`;
2. it signals `acquired_event` only after the exclusive `flock` has succeeded;
3. it keeps the file descriptor open and the lock held until `release_event` is set;
4. it has bounded timeout/failure reporting and cannot leak a child or lock;
5. it is a test adversary only, not a replacement implementation of commit/reconcile.

Using raw `fcntl.flock` in this holder is explicitly allowed because the holder is external contention, not the semantic owner under acceptance.

Use `multiprocessing.get_context("fork")` consistently with the existing P3A9/POSIX fixture unless repository platform policy requires an equivalent supported context.

### 4.2 Commit-owner lock-identity test

Add:

```text
test_p3a9_lock_identity_commit_owner_blocks_on_canonical_lock
```

Construct a bounded real P3 root with:

- committed predecessor head `H0` current;
- next valid complete batch `B1` built from `H0.post_state`;
- `B1` **not yet committed by the public commit owner**;
- no successor head/pointer mutation yet.

Then execute this exact state-transition probe:

1. start the external lock-holder process;
2. wait for `acquired_event` with a bounded timeout and require success;
3. start a separate worker process that:
   - signals `call_started_event` immediately before entering `commit_target_size_boundary_batch(...)`;
   - calls the **real public commit owner** with `B1`;
   - records returned head digest or exception;
   - sets `completed_event` in `finally`;
4. wait for `call_started_event` and require success;
5. while the external holder still owns `.screen_commit.lock`, require a bounded negative completion wait:

```python
assert not completed_event.wait(timeout=1.0)
```

   An equivalent bounded value in the 0.5–2 s range is acceptable if needed for CI stability. Use `Event.wait(timeout=...)`; do **not** use `sleep()` as the ordering oracle.
6. while the canonical lock is still held, verify durable mutation has **not** occurred:
   - `current_head.json` still resolves to `H0`;
   - no `heads/<H1>.json` successor produced by this commit exists;
   - if commit normally persists `B1` only after acquiring the lock, require the batch artifact to remain absent as well;
7. set `release_event`;
8. join both processes with bounded timeouts and assert clean exit;
9. retrieve the worker result and require successful commit to exactly one authenticated successor `H1`;
10. require `current_head.json -> H1` and no competing child/fork;
11. run a **newly spawned fresh reconciliation child process** and require it returns the same `H1.content_digest`.

The acceptance claim is specifically:

```text
an independently held canonical .screen_commit.lock prevents the real public commit owner from completing or publishing head/pointer mutation until that exact lock is released.
```

If the public commit owner removes its lock or switches to another lock path, this test plus the structural guard in 4.4 must fail.

### 4.3 Reconcile-owner lock-identity test

Add:

```text
test_p3a9_lock_identity_reconcile_owner_blocks_on_canonical_lock
```

Construct the standard stale-pointer crash state:

```text
current_head.json -> H0
batches/ contains valid B1
heads/ contains authenticated valid H1 child of H0
```

Then:

1. start the same external holder and require it has acquired `<root>/.screen_commit.lock`;
2. start a separate worker process that signals `call_started_event` immediately before invoking the **real public** `reconcile_target_size_screen_root(...)`;
3. while the holder still owns the lock, require `completed_event.wait(timeout=1.0)` to return false;
4. while still held, require `current_head.json` remains exactly `H0`;
5. release the external holder;
6. require the reconciliation worker completes cleanly and returns exactly `H1.content_digest`;
7. require `current_head.json -> H1` with no alternate head/fork;
8. spawn a new child process for a second reconciliation and require it independently returns `H1` unchanged.

The acceptance claim is specifically:

```text
an independently held canonical .screen_commit.lock prevents the real public reconciler from advancing the pointer until that exact lock is released.
```

### 4.4 Mandatory targeted structural lock guard

Behavioral blocking is necessary but the negative-wait interval alone must not be the only discriminator, because an unrelated slow operation could otherwise look blocked.

Add one targeted structural test, recommended name:

```text
test_p3a9_public_owners_bind_same_canonical_screen_commit_lock
```

It must inspect the actual production public-owner definitions and establish for **both** `commit_target_size_boundary_batch` and `reconcile_target_size_screen_root`:

- the function binds the lock path from the screen root and the literal canonical name `.screen_commit.lock`;
- it acquires an exclusive `fcntl.flock(..., fcntl.LOCK_EX)` before entering the corresponding locked mutation path;
- both functions use the same canonical lock-file identity, not two different files.

A narrow `inspect.getsource(...)` assertion or equally narrow AST/source inspection is acceptable. Do not introduce a global source-scanning framework. Do not count a comment, test helper, or private unused function as evidence; the assertions must target the two actual public owner definitions.

This structural test is deliberately paired with the behavioral holder tests:

```text
structural guard -> proves both public definitions name/acquire the same canonical lock
external holder  -> proves that lock actually blocks each real public owner at runtime
existing races   -> prove concurrent valid operations converge/no-deadlock under real process scheduling
```

Together these are the required proxy-proof acceptance for the shared-lock invariant.

---

## 5. Required corrections to the existing process races

Keep the existing process-level Race A and Race B from `0bed3080...`; they remain valuable state-transition concurrency tests.

### 5.1 Replace parent-process “fresh” reconciliation

Where the current tests do approximately:

```python
fresh_rec = reconcile_target_size_screen_root(root, authority)
```

in the pytest parent after the race, replace that acceptance step with a newly spawned process invoking the real public reconciler.

Recommended helper reuse:

```text
_worker_reconcile(...)
```

or a smaller no-barrier child helper that reconstructs/receives the same real `TargetSizeRestartAuthority` and reports the returned digest.

The post-race child must be created **after** the racing workers have completed. A direct call in the parent is not a fresh-process check.

### 5.2 Do not use `multiprocessing.Queue.empty()` as synchronization

The current race harness drains results using `Queue.empty()`. That method is not a reliable cross-process synchronization primitive.

For a test expecting exactly `N` child results, retrieve exactly `N` messages with bounded blocking calls, for example:

```python
messages = [queue.get(timeout=5) for _ in range(N)]
```

Then validate labels/digests/errors. Do not use `while not queue.empty()` or `get_nowait()` as the acceptance mechanism.

For every spawned child also assert:

- bounded `join(...)` completes;
- `process.is_alive()` is false;
- `process.exitcode == 0` unless the test intentionally expects process failure;
- failure paths terminate/join any still-live child in `finally`;
- queues/events are not used as authority for scientific state.

### 5.3 No forced winner requirement

Do not add sleeps or hooks to force whether commit or reconcile wins Race A. Both acquisition orders remain valid:

```text
commit first     -> create-or-verify/adopt H1 -> reconcile validates H1
reconcile first  -> replay/adopt H1            -> commit exact-retries H1
```

The lock-identity holder tests prove canonical serialization; Race A only needs to prove order-independent convergence under natural scheduling.

---

## 6. Existing focused and inherited acceptance remains mandatory

The revised harness must continue to pass all focused P3A9 crash/replay requirements already present:

1. complete batch durable, head absent -> unique recovery;
2. immutable successor durable, stale pointer -> replay and advance;
3. multiple valid linear successors -> replay to unique tip;
4. missing pointer with valid chain -> rebuild after full replay;
5. corrupted successor -> reject/no pointer advance;
6. fork -> reject;
7. authenticated unrelated orphan -> reject;
8. tampered parent/batch/pre/post relation -> reject through owner/reducer validation;
9. exact duplicate retry -> idempotent;
10. repaired crash path -> same reducer/scientific state as uninterrupted control;
11. Race A commit-versus-reconcile -> one authenticated history/no deadlock;
12. Race B reconcile-versus-reconcile -> one authenticated history/no deadlock;
13. commit-owner canonical-lock holder acceptance;
14. reconcile-owner canonical-lock holder acceptance;
15. targeted public-owner same-lock structural acceptance;
16. actual fresh-child post-race reconciliation.

The following inherited authoritative tests must execute on the final candidate and remain the evidence for their respective contracts:

```text
tests/test_mlff_target_size_execution_p3f.py::test_p3f_subprocess_fresh_continuation_and_replay

tests/test_mlff_target_size_execution_p3f.py::test_p3f_fresh_process_train2_and_eval2_failure_replay

tests/test_mlff_target_size_p3a4_final_review.py::test_p3a4_durable_trajectory_tampered_evaluation_state_rejected
```

Do not recreate weaker local substitutes for these tests. Do not weaken, skip, xfail, or rename away their assertions to obtain closure.

---

## 7. Regression commands and evidence boundary

### 7.1 Expected test-only repair

If production P3 source remains byte-identical to `4315b0ab4c13bbb45b963f3d816b5bb08aac75c0`, run on the final acceptance candidate at minimum:

```bash
pytest -q tests/test_mlff_target_size_p3a9_head_pointer_reconciliation.py
pytest -q tests/test_mlff_target_size_execution_p3e.py tests/test_mlff_target_size_execution_p3f.py
pytest -q tests/test_mlff_target_size_p3a4_final_review.py::test_p3a4_durable_trajectory_tampered_evaluation_state_rejected
```

Every listed test/module must actually execute. A skipped, unavailable, timed-out, or not-collected required check is not a pass.

Record enough command output in the implementation handoff to attribute the passing evidence to the exact candidate commit. No new evidence database/report schema is required.

### 7.2 If a production defect is exposed

If any new lock-identity or race test fails because the production owner is genuinely wrong, repair only the smallest existing owning layer necessary to restore the frozen one-lock architecture.

Allowed local consequences, only if proven necessary:

- correct the existing `.screen_commit.lock` path/scope in a public owner;
- correct exclusive lock acquisition/release;
- correct exact-retry behavior after another owner wins the lock;
- correct exception-safe release/pointer publication ordering.

Forbidden:

- second lock file/domain;
- PID/process authority;
- mtime/newest winner selection;
- second mutable head/result authority;
- retry loops that hide deterministic corruption;
- P4-side replay/recovery;
- test hooks or sleeps in production code;
- weakening typed replay/fork/orphan validation.

Any production P3 source change invalidates the narrow test-only regression boundary. Re-derive the affected surface and run the complete cumulative P3 execution/restart surface, at minimum all affected `tests/test_mlff_target_size_execution_p3*.py` and `tests/test_mlff_target_size_p3a*.py` files plus any additionally affected caller/consumer discovered from the actual diff.

Long GPU/real-production qualification remains out of scope.

---

## 8. Structural/conformance closure

Before claiming P3A9 closed, independently inspect the final candidate and establish:

1. the two required public semantic owners remain the production entrypoints under acceptance;
2. both public owners acquire the exact same `root/.screen_commit.lock` with exclusive `flock`;
3. the external-holder tests invoke the real public owners and would fail if either stopped contending on that lock;
4. the tests do not monkeypatch `flock`, the lock path, public owners, atomic pointer publication, typed resolver, or P2 reducer replay;
5. immutable batch/head publication and deterministic reducer replay remain unchanged unless a demonstrated product defect required a local repair;
6. no second replay owner, lock domain, mutable head authority, or P4 compatibility path was added;
7. fork/orphan corruption remains fail-closed;
8. the existing natural process races still converge without deadlock;
9. fresh post-race reconciliation is now truly performed by a newly spawned process;
10. inherited P3F and P3A7/P3A8 owner-level regression passes on the same final candidate;
11. process cleanup is bounded and the test suite leaves no live child or held lock after success/failure.

A green test suite does not substitute for this source/conformance inspection.

---

## 9. Formal P3 closure and P4 handoff

After the amended acceptance passes:

1. commit the test/acceptance candidate and record its exact SHA;
2. run the mandatory focused + inherited affected regression on that exact candidate;
3. perform semantic/conformance closure against cumulative P3 revision 7 through this instruction revision 3;
4. only if both semantic and functional closure pass, update this file to `status: accepted` and record `accepted_closure_commit: <new-candidate-sha>`;
5. update package README/sequencing metadata to the same accepted P3 closure SHA;
6. update P4 `entry_p3_closure_commit` and entry gate to that same new SHA;
7. only then set P4 to `status: active` and begin P4-A executable work.

Do **not** reuse `0bed3080ac4e3ba45f04fdf2fab891cfdc92fe58` as final closure identity because the required lock-identity/fresh-child acceptance is not present in that candidate. Do not reuse `bf24a9e5...` as closure authority; it is superseded metadata.

The expected next closure candidate should differ from `0bed3080...` only in the P3A9 acceptance harness unless the new tests expose a real production defect.

---

## 10. Frozen / delegated / reopen boundary

### Frozen

- parent scientific/statistical target-size architecture;
- cumulative P3 revision-7 product semantics;
- reviewed P3A9 unique-linear-successor recovery design;
- one canonical `root/.screen_commit.lock` domain;
- public commit/reconcile ownership;
- immutable evidence + deterministic reducer replay;
- fail-closed fork/orphan handling;
- no second replay/mutable authority;
- version-agnostic product naming;
- deferred long GPU qualification.

### Delegated

- exact helper names for the holder/call-start/completion events;
- exact bounded timeout values within the ranges above if CI stability requires adjustment;
- whether the targeted structural guard uses `inspect.getsource` or a narrow AST equivalent;
- whether fresh-child authority is inherited under `fork` or reconstructed using the existing P3F pattern;
- exact test function ordering within the P3A9 file.

### Reopen only on evidence

Reopen P3 design only if the final real-owner acceptance proves one of these material premises false:

- the current single canonical filesystem lock cannot serialize commit/reconcile correctly on the supported process/filesystem model; or
- the immutable-head representation cannot support deterministic unique-successor recovery without changing frozen scientific semantics.

A flaky/incorrect test helper, missing process cleanup, Queue synchronization issue, lock-path typo, local public-owner lock-scope bug, or exact-retry bug is implementation repair, not architecture reopening.

Legacy compatibility, test runtime, desire to avoid process-level acceptance, or convenience of moving recovery into P4 are not reopen conditions.
