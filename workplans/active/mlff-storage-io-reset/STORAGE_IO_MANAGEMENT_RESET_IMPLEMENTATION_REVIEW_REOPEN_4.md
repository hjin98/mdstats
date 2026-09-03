---
kind: implementation-review-reopen
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1-R20
parent_workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
status: reopened
reviewed_date: 2026-09-02
reviewed_authority_revision: 19
reviewed_executable_commit: 869ae1b6e9211faa1873d47e7850050cd85b5ff7
reviewed_executable_tree: a5e6c8868bdec9e88a877e6ca84aa6ef6d609286
reviewed_branch_head: bf05fe5e35a44c4b5898075da3bb2b54ba220238
review_verdict: NO-PASS
scope: independent implementation review of the Revision-19 repair; preserve conforming R12-R19 work and repair only the remaining observational-purity, P7 attempt-census authentication/completeness, released-attempt terminal revalidation, and candidate-bound acceptance-evidence gaps
precedence: this review does not reopen the Revision-19 design; it identifies implementation nonconformance and acceptance gaps against the complete Revision-19 supplied contract. Where this file gives more precise implementation/acceptance instructions for those defects, follow it together with Revision 19.
---

# Storage/I-O reset implementation review reopen 4 — Revision 20

## 0. Verdict

**NO-PASS / reopened.**

The Revision-19 implementation is substantially conforming and should not be redesigned. The executable reviewed is:

```text
commit 869ae1b6e9211faa1873d47e7850050cd85b5ff7
tree   a5e6c8868bdec9e88a877e6ca84aa6ef6d609286
```

The current branch head `bf05fe5e35a44c4b5898075da3bb2b54ba220238` is a one-commit generated-document successor; compare shows only generated PDFs/PDF manifest output after the executable commit. Functional review therefore remains bound to executable `869ae1b6...`.

Most R19 repairs are present and must be preserved: typed P5/P7 node authority through `OwnerArtifactView` and `StorageInventorySnapshot.authorized_members`; no-follow owner-record reads on the supported POSIX path; symlink-aware recursive deletion refusal; P7 v3 released-attempt proof publication ordering; touched-attempt synchronization in the storage owner barrier; bounded-vs-exact P7 owner views; shared thread/cross-instance/cross-process CampaignStore writer gate; constructor participation in the writer census; and explicit CampaignStore writer-lock ownership.

Three source-level closure defects remain, plus final executed acceptance evidence. Two are genuine safety/authority defects; one is a storage-owner terminality/conformance defect. They are narrow repairs inside the existing R19-E/F sequence.

No target-size science, P2 statistical rule, P3/P4 currentness, P5 CV/final-production science, P7 qualification/locked/release science, or frozen target-size V7 verdict is reopened. Full external-DFT, long GPU production, and environment-specific HPC/storage qualification remain deferred.

---

## 1. IR20-1 — `replace_records_atomically()` can still mutate during observation

### Finding

R19-C requires every public/owner CampaignStore mutator to call `_require_writable()` **before** filesystem, external-payload, lock-file, SQLite, or receipt side effects. The implementation placed an extra

```python
self._require_writable("replace campaign records")
```

inside `put_records()`, but `replace_records_atomically()` itself still starts serializing/externalizing its replacement records before it reaches `writer_exclusion()`.

That ordering is consequential. `_encode_record_for_storage()` can write external payloads before SQLite is touched: `frame_catalog`, `data4`, and `data6` are forced through an external representation, and ordinary records above `EXTERNAL_RECORD_THRESHOLD_BYTES` are externalized as well. A `CampaignStore(create=False)` can therefore change `.mdstats/records/` and only then fail when `writer_exclusion()` finally calls `_require_writable()`.

The candidate test does not prove the required boundary. It uses a 2 MiB mapping under key `"huge"`, while `EXTERNAL_RECORD_THRESHOLD_BYTES` is 4 MiB and the key is not one of the forced-external keys. The test therefore stays on the pure in-memory serialization path and can pass even though the owner method is still side-effecting for a real externalized replacement.

### Required repair

1. Put `self._require_writable("replace campaign records")` at the **first executable line** of `replace_records_atomically()` before record encoding, externalization, delete normalization, writer-lock acquisition, or SQLite access.
2. Remove the accidental duplicate/misnamed guard from `put_records()`; retain only its own correctly named `write campaign records` guard.
3. Re-derive the CampaignStore public mutator surface once more. Any method capable of materializing an external payload, sharded payload, receipt, lock path, schema row, event/stage/meta/record row, or deletion must fail observationally before the first such side effect.
4. Do not move externalization inside the SQLite transaction merely to fix this bug. The accepted design deliberately keeps large filesystem materialization outside the narrow DB transaction; the missing requirement is an *early capability guard*, not a broader lock.

### Required acceptance

Use a real read-only `CampaignStore` and a payload guaranteed to cross the externalization boundary. Prefer either:

- `replace_records_atomically({"frame_catalog": {...}})` because `frame_catalog` is force-externalized independently of test size; or
- a normal mapping strictly larger than `EXTERNAL_RECORD_THRESHOLD_BYTES`.

Before/after filesystem signatures must prove no new or modified:

- `.mdstats/records` payload;
- CampaignStore writer-lock;
- SQLite journal/WAL/SHM;
- hash-receipt state;
- state DB bytes;
- other managed file.

The call must fail with the explicit observation-only owner error. Keep the existing raw read-only SQLite test as defense in depth; it does not substitute for this pre-SQL filesystem-side-effect test.

---

## 2. IR20-2 — the P7 attempt census is not yet complete or identity-authenticated enough to protect external references

### Finding

R19-B correctly identifies P7 attempt state as cross-owner liveness authority: an active attempt can pin exact P5 checkpoints outside the P7 tree. Unknown state must therefore block **all consequential storage planning**, not merely retain the local attempt directory.

The candidate introduces `iter_attempt_state_census()`, but its census is driven by

```text
g*/attempts/*/attempt-state.json
```

files rather than by the actual attempt directories, and it deserializes a found state without proving that the state belongs to the directory from which it was read.

This leaves three related holes.

### 2.1 Missing state is invisible to the global blocker

An existing `attempts/<identity>/` directory with no `attempt-state.json` is absent from `iter_attempt_state_census()` entirely. Later `qualification_views()` notices the directory and conservatively treats its scratch as unreleased, but that local retention does **not** recover the external `referenced_paths` that an active attempt could have been pinning. The global integrity blocker is never raised, so unrelated P5 cleanup/archive/dedup planning can proceed without knowing those references.

### 2.2 A valid state copied under the wrong attempt directory is accepted

`iter_attempt_state_census()` authenticates the state payload through `QualificationAttemptState.from_dict()` but never checks

```text
state.attempt_identity == attempt_directory.name
```

A digest-valid terminal/aborted state copied over an active attempt's state file can therefore be accepted as the state of the wrong attempt. Its real external reference set disappears from the census without an integrity failure.

`read_attempt_state(paths, binding, attempt_identity)` performs this identity check for the qualification owner itself, but the storage-facing census and `read_attempt_state_at()` do not. The storage census must not be weaker than the owner API whose liveness it represents.

### 2.3 Current-schema state digest is optional in the strict storage reader

`QualificationAttemptState.from_dict()` accepts `content_digest=None` for compatibility. That permissiveness is not sufficient for the R19 storage authority boundary. A current v1 state with its digest removed can be altered and then accepted by the census, because the deserializer simply reconstructs a new in-memory content digest. For a liveness record that can release external P5 protection, missing authentication must be an unknown state, not a reconstructed truth.

### Required repair

Create/reuse one **strict storage-facing attempt-state reader/census** and make inventory plus the qualification retention fence consume it.

1. Enumerate the actual `g*/attempts/*` entries, not merely state files.
2. Classify the attempt-root entry no-follow. A symlink/special/unreadable attempt root is an integrity failure, not an attempt to follow the target.
3. For every plain attempt directory, require an `attempt-state.json` regular file. Missing, symlinked, unreadable, malformed, unsupported-schema, or otherwise unusable state is returned as an explicit census failure naming the attempt root/path.
4. For storage consequential authority, require the persisted current-schema `content_digest` to be present and exactly equal to the recomputed `QualificationAttemptState.content_digest`. Do not rely on the permissive `from_dict(... content_digest=None)` compatibility behavior as destructive liveness authority.
5. Require `state.attempt_identity == attempt_root.name` before accepting its `state` or `referenced_paths`.
6. Preserve the current strict `binding_digest` / `publication_digest` field validation performed by the dataclass and add any direct cross-field checks needed by the released-attempt proof reader. A storage-facing state/proof pair that is internally contradictory is unresolved, not partially trusted.
7. `qualification_views()` propagates every strict-census failure into `owner_integrity`, and `StorageInventorySnapshot.require_planable()` remains the global mutation gate.
8. `build_qualification_retention_fence()` consumes the same strict census result. Do not create a second permissive state scan.
9. Once the exact state is repaired/authenticated, planning becomes available again and uses its real `referenced_paths` normally.

The generic qualification deserializer may retain a clearly documented legacy compatibility mode if another accepted runtime path genuinely needs it; storage destructive authority must use the strict current-state path. Do not silently migrate an unauthenticated state by inferring its references from filenames.

### Required acceptance

Use the real P7 owner, P5 publication, storage inventory, planner, and executor.

1. **Missing state:** create/retain a real attempt directory, remove `attempt-state.json`, and prove report names the unresolved attempt while cleanup/archive/dedup planning is globally unavailable and exact published P5 checkpoints remain untouched.
2. **Wrong-root state:** create two real attempts, keep one active with a referenced P5 checkpoint, copy a digest-valid terminal/aborted state from the other under the active attempt directory, and prove the root/identity mismatch becomes an integrity failure rather than releasing the checkpoint.
3. **Missing digest:** remove `content_digest` from an otherwise parseable current state and modify liveness/reference fields; the state must be unresolved, not accepted with a reconstructed digest.
4. **State symlink and attempt-root symlink:** neither may contribute state or external reference authority through the target; both block consequential planning.
5. Repair each condition and prove the blocker disappears only when the exact authenticated state returns.
6. Retain the existing corrupt-JSON case, but do not treat it as proxy proof for the missing/wrong-root/missing-digest counterfactuals above.

---

## 3. IR20-3 — terminal released-attempt proof validation is still bypassed on repeated terminal release

### Finding

R19-B freezes terminal release as monotonic **and** requires a repeated terminal release to validate/reuse the existing bound v3 proof, failing closed if the proof is missing, corrupt, or conflicting.

The candidate currently returns immediately when the existing state is terminal:

```python
if existing.state == ATTEMPT_TERMINAL:
    return existing
```

That bypasses `read_attempt_member_proof()` / `certified_attempt_nodes()` entirely. A terminal state whose retained topology proof was lost or corrupted is therefore reported by the owner API as an ordinary successful repeated release. Storage itself later refuses reclamation, so this is conservative for deletion, but it violates the accepted owner terminality/recovery contract and can leave terminal scratch permanently unreclaimable without surfacing the broken retained proof at the owner boundary.

There is a smaller related validation asymmetry: `certified_attempt_nodes()` checks proof `state_digest`, `attempt_identity`, and `released_state`, but the v3 proof also redundantly carries `binding_digest` and `publication_digest`. Those fields should agree with the exact state they claim to bind rather than being self-digest-valid but semantically contradictory metadata.

### Required repair

1. On repeated `ATTEMPT_TERMINAL`, validate the retained v3 proof against the exact terminal state under the same per-attempt lock.
2. If the proof is valid and state-bound, return the existing terminal state without rescanning/recomputing the depleted scratch tree.
3. If proof is missing, v2-only, malformed, self-digest-invalid, state-digest-mismatched, wrong-root, wrong-attempt, or otherwise conflicting, raise the existing P7 lineage/serialization error and retain everything. Do **not** reconstruct a new proof by scanning a possibly cleaned/tampered terminal tree.
4. Validate proof `binding_digest == state.binding_digest` and `publication_digest == state.publication_digest` in the strict bound-proof reader in addition to the already checked state digest/attempt/state fields.
5. Preserve supported aborted -> active -> released behavior: an aborted proof may be superseded only through that lifecycle under the attempt-state lock.

### Required acceptance

- valid repeated terminal release is idempotent and does not rescan/rewrite proof or scratch;
- delete the terminal proof, then repeat terminal release -> explicit fail-closed owner error;
- corrupt proof self digest -> fail;
- make proof binding/publication fields contradict the exact state while recomputing the proof's own self digest -> fail on cross-field binding, not pass merely because the record is self-consistent;
- terminal scratch remains retained in every failed case.

---

## 4. IR20-4 — candidate-bound acceptance evidence is not complete, and several new tests are not proxy-proof

### Repository evidence available

For executable commit `869ae1b6e9211faa1873d47e7850050cd85b5ff7`, GitHub exposes one completed check run: `docs`, successful. No storage-core, storage-integration, affected-owner regression, or final affected-surface functional check is attached to the exact executable commit.

The refreshed `benchmarks/benchmark_mlff_storage_io_reset_results.json` proves that the storage benchmark was executed, including owner-report/archive measurements. It is useful performance evidence, but it is not the R19-F functional/regression/integration acceptance set.

No candidate-bound command/result log was added to the active storage workplan package in the implementation commit.

### Candidate-test gaps that must be corrected before evidence is accepted

1. Replace the 2 MiB observational `replace_records_atomically()` test with a forced-external or >4 MiB case as specified in IR20-1.
2. Add the P7 missing-state, wrong-root copied-state, missing-current-digest, and attempt-root-symlink cases from IR20-2.
3. Add the repeated-terminal proof validation cases from IR20-3.
4. R19-B asked for a deterministic **aborted-attempt reopen versus real storage cleanup race exercising both lock orderings**. The candidate contains a sequential reopen test but no equivalent concurrent two-ordering storage race. Add it using the production attempt-state lock and real storage executor; do not substitute a local boolean for the owner seam.
5. Add a P7 special-node case (FIFO or another safely modeled special node) in addition to the current symlink cases, because R19-B required special-node refusal independently for the P7 released-attempt proof.
6. Keep the current P5 typed substitution/no-follow cases, CampaignStore same-thread/cross-thread/cross-instance/cross-process cases, P7 bounded-report scaling, and existing real-owner integration tests.

### Required final executed sequence

After the source repair, execute and record against the **exact final executable commit/tree**:

1. focused IR20-1 through IR20-3 counterfactuals plus all R19-A through R19-D focused tests;
2. every still-binding R17/R18 focused storage test;
3. full `tests/test_mlff_storage_reset_core.py`;
4. full `tests/test_mlff_storage_reset_integration.py`;
5. affected P1/P3/P4/P5/P7 currentness, publication, restart, retention, qualification-owner tests, plus P6 destructive closure where the common owner-proof/executor path is affected;
6. re-derive the final affected surface from the completed repair diff;
7. run a **fresh** final affected regression/integration set after that re-derivation;
8. CPU-safe broader/full tests if the final impact cannot be confidently bounded;
9. static checks plus affected docs/spec/build validation.

Record command, exit/result summary, and exact executable commit/tree. Distinguish `not run`, `run/pass`, and deferred full production qualification. A later PDF/generated-document-only successor can reuse functional evidence only after compare proves that no executable/config/persistence/test-harness contract changed.

Full external-DFT, long GPU production, and environment-specific HPC/storage qualification remain deferred and are not blockers for this acceptance.

---

## 5. Non-blocking closure notes to fold into the repair if touched

These do not independently drive the NO-PASS verdict, but they should not be left as silent drift if the affected code is already being edited.

1. `OwnerSynchronization.to_dict()` currently omits `attempt_roots`. Runtime synchronization uses the field correctly, but diagnostics should serialize the complete synchronization contract so evidence/debugging does not hide the P7 seam.
2. The strict owner-record reader uses `getattr(os, "O_NOFOLLOW", 0)` without the Revision-19 fallback identity check when `O_NOFOLLOW` is absent. On the current Linux/POSIX target `O_NOFOLLOW` is available. If the package claims support for a POSIX target where it is not, implement the specified pre/open/post descriptor identity fallback or explicitly narrow/document the supported platform contract; do not silently downgrade to a followable open.
3. The current exact P5/P7 subtree scanners swallow `os.scandir()` errors locally, while the common `authorized_members()` walker later converts enumeration failures into refusals. Destructive paths are therefore conservative today. Preserve that common refusal behavior; if owner-local certification is refactored, do not turn I/O/permission ambiguity into an absent-node claim.

---

## 6. Rework boundary and acceptance routing

This is **implementation repair**, not a new design phase.

Resume from the earliest affected R19-E gate:

- CampaignStore observational guard: R19-E3;
- P7 strict census/proof terminal validation: R19-E2;
- acceptance tests/evidence: corresponding stage-local regressions, then R19-E5/R19-F.

Do not redo the conforming typed P5 authority, P7 v3 proof representation, CampaignStore RLock/flock architecture, archive/dedup design, storage audit model, restore design, or parent P1-P7 science.

### Exit criteria for the next review

A next implementation review can return PASS only if:

- `replace_records_atomically()` fails before every observational externalization side effect;
- every actual P7 attempt directory contributes either one strict authenticated state or an explicit global planning failure, with root identity and persisted current digest verified;
- repeated terminal release validates/reuses the existing bound v3 proof rather than bypassing it;
- focused counterfactuals above pass through real owners;
- exact candidate-bound final regression/integration evidence required by R19-F/IR20-4 is supplied.

**Disposition:** executable `869ae1b6...` is **NO-PASS / reopened**. Revision-19 architecture remains accepted; apply this bounded repair and re-run the final acceptance sequence.
