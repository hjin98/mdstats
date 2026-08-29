---
kind: implementation-repair
package_id: CODE-MLFF-TARGET-SIZE-V7-P3-P3A9
parent_package_id: CODE-MLFF-TARGET-SIZE-V7-P3
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
status: accepted
accepted_closure_commit: 4315b0ab4c13bbb45b963f3d816b5bb08aac75c0
repair_revision: 7
created_date: 2026-08-29
entry_p3a8_commit: 472276ee521eb2b19177299c1c9ad660dbd6ad46
reconciliation_reason: Final P4 design review demonstrated one remaining P3 persistence/reconciliation defect: after an immutable successor execution head is durably published but before current_head.json advances, a crash leaves a valid unique successor that the current reconciler rejects as an orphan. This repair is a narrow cumulative revision-7 implementation-closure binding. It does not reopen P1-P3 scientific semantics, reducer policy, TRAIN2/EVAL2 semantics, checkpoint semantics, provider ownership, seed policy, or target-size decision logic.
---

# P3A9 — stale-head successor reconciliation repair

## 1. Purpose and authority

The frozen parent workplan remains the sole scientific and architectural verdict. This instruction closes one demonstrated crash-recovery defect in the existing P3 persistence owner before P4 may begin.

P3A9 is **not** a new scientific revision. It preserves the complete cumulative P3 revision-7 contract through P3A8 and changes only recovery of an already-valid immutable execution-head chain.

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

## 2. Demonstrated defect

Current boundary publication is effectively:

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

The current reconciler validates the pointer ancestry and then rejects immutable heads outside that ancestry as orphans. Therefore a valid crash-left successor can be rejected instead of deterministically recovered.

The defect is fail-closed rather than scientifically permissive, but it violates the accepted P3 restart contract because an already-authenticated unique successor cannot be recovered after an ordinary publication crash.

---

## 3. Required repair

### 3.1 Owning implementation

Repair the existing P3 reconciliation owner in:

`mdstats/training_data/target_size_execution/coordinator.py`

Prefer modifying `reconcile_target_size_screen_root(...)` or the smallest existing helper naturally beneath it. Do **not** create a P4-specific replay routine, a second execution-head state machine, or a compatibility wrapper that bypasses the existing P3 resolver.

Reuse the canonical P3 screen/head serialization and lock ownership already used by `commit_target_size_boundary_batch(...)`.

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

### 3.3 Idempotency and concurrency

The repaired path must remain safe under restart and duplicate invocation:

- an exact retry after pointer repair returns the same authenticated tip;
- reconciliation racing another legitimate P3 head commit cannot manufacture a second history;
- canonical P3 locking prevents two pointer/head mutators from choosing different descendants;
- a fork that already exists remains an error rather than being "healed" by choosing one branch;
- process identity/PID is not authority.

Do not broaden lock scope over expensive model inference or unrelated I/O. The lock protects the logical head/pointer commit/reconciliation critical section only.

---

## 4. Mandatory acceptance

Acceptance must exercise the **real P3 resolver/reconciler**, not a helper-only reconstruction or test-local replay.

Prove at minimum:

1. complete boundary batch durable, immutable head absent -> existing unique-batch recovery succeeds;
2. immutable successor head durable, `current_head.json` still on predecessor -> unique successor is scientifically replayed and pointer advances;
3. stale pointer followed by multiple valid **linear** successors -> complete chain replays and pointer advances to the unique tip;
4. `current_head.json` missing with one valid chain -> pointer is rebuilt only after full replay;
5. stale pointer with one corrupted successor -> reject and do not advance pointer;
6. stale pointer with two children from the same parent -> reject as fork;
7. unrelated authenticated orphan head -> reject;
8. tampered parent/batch/pre-state/post-state relation -> reject through the owning validator/reducer path;
9. exact duplicate reconciliation/retry -> idempotent identical result;
10. fresh-process restart after repaired crash state yields the same reducer state, active matrix/terminal state, and scientific outcome identity as uninterrupted execution;
11. existing success, TRAIN2-failure, and EVAL2-failure fresh-process replay remains passing;
12. P3A7 canonical restart-owner rejection remains passing;
13. P3A8 owner-level reconciliation acceptance remains passing.

Use bounded deterministic fixtures. Expensive numerical training/inference may be faked only below the already-accepted P3 semantic-owner boundary; the P3 resolver, reconciler, typed persistence, reducer replay, and pointer publication themselves may not be replaced.

After the focused bug reproducer passes, run the complete affected P3 persistence/restart regression surface before closure.

Long GPU/real-production qualification is not part of this repair.

---

## 5. Formal P3 closure and P4 handoff

After implementation passes all acceptance above:

1. perform semantic/conformance review against cumulative P3 revision 7 through P3A9;
2. run the affected P3 regression surface required by this repair;
3. commit the accepted repair;
4. update package sequencing metadata/README to record the accepted P3 closure commit;
5. only then activate P4 with that commit as its `entry_p3_commit`.

Do not start P4 executable runtime-cutover work while P3 remains formally active or while this repair is unaccepted.

---

## 6. Frozen / delegated / reopen boundary

### Frozen

- all P1/P2 scientific/statistical semantics;
- all cumulative P3 revision-7 execution, evidence, owner, reducer, checkpoint, EMA/LIVE, failure, and restart semantics;
- immutable execution heads/batches as scientific evidence;
- deterministic reducer replay as recovery authority;
- `current_head.json` as rebuildable non-scientific pointer/index only;
- fork/orphan corruption remains fail-closed;
- no second replay owner;
- version-agnostic product naming;
- full long GPU qualification deferred.

### Delegated

- exact helper extraction inside the existing coordinator/resolver;
- exact focused test filename;
- internal data structures used to index authenticated head parent/child relations;
- whether pointer advancement uses the existing helper directly or a smaller equivalent existing atomic-write owner.

### Reopen only on evidence

Reopen only if implementation proves that the current P3 immutable-head representation lacks enough authenticated ancestry/state information to distinguish a unique valid successor chain from a fork **without changing frozen P3 scientific semantics**. If that occurs, stop before P4 and reopen only the P3 persistence representation needed to recover the frozen behavior.

Legacy compatibility, desire to avoid the regression tests, or convenience of handling the crash in P4 are not reopen conditions.
