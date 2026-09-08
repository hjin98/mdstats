---
kind: implementation-package-amendment
package_id: CODE-MLFF-TARGET-SIZE-V7-P3-REVIEW4
amends_package_id: CODE-MLFF-TARGET-SIZE-V7-P3
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
sequence: 3
status: active
package_revision: 6
amended_date: 2026-08-28
blocked_implementation_commit: 262cd3b114e6cbc39f67361257a97cb39030c18a
---

# P3 Review-4 final closure amendment — mandatory owner execution, byte-authenticated exact-M evidence, and full graph replay

## 0. Authority, routing, and closure intent

This is the **final cumulative P3 revision-6 closure authority** for the implementation gaps still present at `262cd3b114e6cbc39f67361257a97cb39030c18a` (`P3A2`). It is additive to:

1. `P3_CANDIDATE_EXECUTION_PAIRED_SCREEN.md`;
2. `P3_REVIEW2_AUTHENTICATED_EVAL_RESTART_FIX.md`;
3. `P3_REVIEW3_EXECUTION_OWNER_IMMUTABILITY_CLOSURE_FIX.md`; and
4. this amendment.

Review-2 and Review-3 remain authoritative. This amendment does **not** redesign P1/P2 or P3-A/B/C and does not change the scientific target-size policy. It closes the remaining implementation ambiguities revealed by final independent review. The defects are implementation nonconformance in P3-D/E/F, not evidence for a new architecture.

P4 remains blocked until the cumulative revision-6 P3 exit gate passes. Do not add another parallel P3 authority to satisfy this amendment; consolidate/refactor the current P3 implementation so there is one accepted owner for each scientific or persistence decision.

## 1. Frozen final invariants

The next implementation must preserve all prior P3 invariants and additionally satisfy these exact closure rules:

- accepted direct-boundary inference is impossible without the full current P1/P2/P3 authority bundle and an immutable historical boundary snapshot;
- every parent validator executes **inside** the inference owner before any allowed fake-forward seam;
- P3 contains no second numerical MACE inference engine; it reuses the established static/provider inference machinery;
- the model parameters actually supplied to inference are authenticated as the declared exact live/EMA boundary state;
- exact-M identity is authenticated from the durable ExtXYZ bytes in exact frame order, not merely from advertised metadata or a same-sized view;
- every successful metric and every scientific failure is derived from its authenticated immediate parent evidence;
- all completion-parent evidence is mandatory, immutable, persistently resolvable and replayable after a fresh process restart;
- publication is create-or-verify and conflict-safe under retry and concurrency;
- reconciliation reconstructs scientific outcomes from the parent graph and never trusts serialized completion/batch outcomes as reducer input;
- fresh-process assembled acceptance covers success, TRAIN2 numerical failure and EVAL2 numerical failure.

Absolute paths may be execution locators but are never scientific identity. Full long GPU/production qualification remains deferred.

---

# 2. P3-D final owner closure

## D-R4.1. Replace optional validation with one mandatory inference authority

Refactor `run_target_size_direct_boundary_inference()` (or its version-agnostic successor) so the accepted path cannot omit scientific authorities. Prefer one immutable `TargetSizeInferenceAuthority` / restart-authority object if that minimizes argument count. The owner must have, directly or through that authority:

- current `TargetSizeExperimentDefinition` / aggregate identity;
- current execution context and common preparation;
- exact screen schedule;
- exact candidate optimizer policy for the trajectory seed;
- canonical P1 frame/numerical authority;
- exact export/evaluation policy;
- materialization locator/root;
- immutable snapshot locator/root;
- exact evaluation-artifact locator/root;
- shared static MACE inference/provider configuration required to reconstruct and load the model.

Before any prediction forward call, the owner must unconditionally execute:

1. full trajectory re-derivation validation;
2. full materialization validation and configuration re-derivation;
3. immutable snapshot validation against TRAIN2 continuation artifacts;
4. exact EVAL2 role validation for the current boundary;
5. exact evaluation-artifact byte/order/policy validation;
6. exact live/EMA state loading and authentication.

Forbidden accepted-path fallbacks:

- metadata-only validation because an authority argument was omitted;
- accepting mutable/latest `TargetSizeBoundaryState` in place of an immutable snapshot;
- `evaluation_data_digest=None` for an accepted direct-EVAL2 role;
- invoking the fake prediction callback before model/state provenance has been loaded and authenticated.

Tests may fake only the expensive numerical forward primitive after steps 1-6 have succeeded.

## D-R4.2. Delete the bespoke inference engine from P3

Remove the production path that directly `torch.load()`s the TRAIN2 checkpoint, directly constructs `MACECalculator`, and serially loops over ASE structures. Reuse/extract the existing static MACE inference/provider machinery that already owns architecture reconstruction, provider compatibility, ordering, batching, device/dtype policy, OOM/backoff/resource behavior and model execution.

The P3 specialization is only: **evaluate this one exact immutable boundary state on this one exact ordered M_i artifact**. It must not reintroduce checkpoint selection, rescue, shortlist or another provider/state-loading implementation.

Acceptance includes structural/source evidence that the P3 package no longer contains its own direct `MACECalculator` numerical execution loop.

## D-R4.3. Authenticate the parameters actually evaluated

For `live`, load the exact live boundary parameters and prove their canonical parameter-state digest equals `snapshot.live_parameter_digest` / runtime-summary live digest.

For `ema`, the state-loading owner must:

- require authenticated EMA evidence;
- require exact parameter/shadow cardinality;
- require exact parameter ordering/key identity where the shared provider exposes keys;
- require shape/dtype compatibility;
- apply every required shadow parameter exactly once;
- recompute the canonical evaluated parameter-state digest after application and require equality with the snapshot/runtime-summary EMA digest.

Using `zip()` without an explicit cardinality check is forbidden. Copying the expected digest from metadata without proving the loaded model equals it is forbidden.

## D-R4.4. Exact-M bytes and view are one authenticated chain

Strengthen `TargetSizeEvaluationArtifact` validation so it proves the **bytes consumed by inference/reduction** represent the exact P2 M_i in exact order.

The validator must, from the actual ExtXYZ file and sidecar:

- parse the ExtXYZ frames and require the observed ordered `frame_uid` tuple to equal `definition.evaluation_membership(M_i)` exactly;
- require observed frame count and atom ordering to match;
- require sidecar dataset id, role, canonical authority digest, membership digest and export-policy digest to equal the expected current authority;
- require every sidecar frame record to match the corresponding current P1 canonical geometry/label identity, not merely the set of UID keys;
- re-derive energy/forces/stress keys and policy identity from the accepted evaluation/export policy;
- recompute the deterministic view/input digest from the authenticated bytes/policy/order.

A coherently rebuilt same-sized artifact with reordered frames, another export policy, or foreign canonical frame records must fail even if its internal hashes are self-consistent.

The authoritative reduction path must then either build its `EvaluationDatasetView` internally from the already validated artifact or accept only a provenance-bearing wrapper whose artifact/view digest and ordered membership are exact. A generic `EvaluationDatasetView` with no provenance identity is never admissible, regardless of matching count.

## D-R4.5. Close prediction -> metric -> P2 outcome/failure linkage

For success, `build_target_size_cell_completion_record()` must require and prove:

```text
prediction_evidence.role_digest == eval2_role.content_digest
prediction_evidence.evaluation_data_digest == evaluation_data.content_digest
prediction_evidence.prediction_payload_digest == eval2_metric_record.prediction_digest
eval2_metric_record.target_role_digest == eval2_role.content_digest
P2 metric == deterministic translation(eval2_role, eval2_metric_record)
```

No successful cell may accept an independently supplied scalar as authority.

For EVAL2 numerical failure:

- the durable EVAL2 error/failure record must bind the exact role and the exact authenticated prediction attempt/payload digest that triggered the numerical failure;
- the completion owner derives `TargetSizeNumericalFailure` internally from that record;
- an arbitrary `Eval2NumericalEvaluationError` with a placeholder/foreign prediction digest is not admissible;
- `eval2_failure` completion requires prediction-attempt/evidence identity whenever the failure occurred after prediction materialization.

Ordinary provenance/state/input/programmer/resource errors remain execution errors.

---

# 3. P3-E final re-derivation, immutability, and graph closure

## E-R4.1. Finish trajectory/materialization re-derivation

`validate_target_size_candidate_trajectory()` must re-derive the complete candidate identity, including:

- exact candidate optimizer policy validation against the context seed-neutral template plus the authorized seed;
- exact replay/foundation-none identity required by P3;
- recomputed `candidate_training_protocol_digest` from current definition/context/common/schedule/realization and equality with the durable value;
- exact live/EMA convention and realization.

`validate_target_size_materialization()` must always receive enough accepted authority to recompute the exact MACE configuration. Do not make strong configuration validation conditional on optional `projection/common/optimizer_policy` arguments on the accepted path. It must include the exact ExtXYZ/export policy used to create target/harness artifacts rather than silently substituting a default policy.

## E-R4.2. Every scientific writer is create-or-verify before commit

Fix all remaining destructive or race-prone publishers. At minimum this includes:

- target/harness ExtXYZ sidecars;
- candidate MACE configuration;
- exact-M ExtXYZ + sidecar;
- immutable boundary snapshot files + `snapshot.json`;
- trajectory/materialization/snapshot/role/evaluation/prediction/metric/failure records;
- completion records, batches, heads and current-head pointer publication.

Rules:

1. generate/validate attempt-local bytes first;
2. if the logical/content-addressed destination is absent, publish with an exclusive/CAS/lock discipline appropriate to concurrent writers;
3. if present, deserialize/hash and require exact identity; identical retry is idempotent;
4. if different, fail without modifying the existing object.

Do not overwrite sidecar/config bytes and only afterward discover a manifest conflict.

For snapshot metadata specifically, compare by deserializing `TargetSizeBoundarySnapshot.from_dict()` and comparing `content_digest`, or otherwise hash the same canonical payload domain. Do **not** compare `digest(snapshot.to_dict())` (which includes the outer `content_digest` field) with `snapshot.content_digest` (which does not).

Process-crash durability is sufficient for P3 unless the product separately claims power-loss durability; do not add unnecessary filesystem ceremony.

## E-R4.3. Completion variants derive failures at the owner boundary

### TRAIN2 failure

The completion owner must accept the real durable `Train2NumericalFailureRecord` plus the attempted rung/continuation ancestry and derive the P2 `TargetSizeNumericalFailure` itself. A caller-supplied translated P2 failure may be used only as a redundant equality assertion, never as the authority required to make a raw record admissible.

The real TRAIN2 failure validator must verify all record fields against the attempted rung and, where the taxonomy states a raw checkpoint exists, verify the named checkpoint bytes against the recorded SHA. Placeholder SHA fixtures are forbidden at the accepted owner boundary.

### EVAL2 failure

The completion owner derives the P2 failure from the exact EVAL2 role + authenticated prediction attempt + real EVAL2 numerical-error record. The error record's prediction digest must equal the bound prediction attempt/evidence digest.

## E-R4.4. Make the whole completion graph physically resolvable

Extend the resolver/storage layout so every digest referenced by every completion variant has a durable record or deterministic relative locator. The current resolver must not stop at trajectory/materialization/evaluation/role/prediction/metric/failure. Add, as applicable:

- immutable boundary snapshot record locator;
- attempted rung-plan record locator;
- predecessor continuation/request or predecessor snapshot ancestry locator;
- TRAIN2 failure artifact and any referenced raw-checkpoint locator;
- EVAL2 error record locator;
- any export-policy/configuration record required for re-derivation.

The exact layout is delegated, but **no committed digest may point to an object that restart cannot resolve**.

Completion publication must be one real owner that receives the complete variant-specific parent objects/locators and persists/verifies all required parents before publishing the completion pointer. Parent persistence cannot be optional keyword arguments that normal callers simply omit.

For artifacts whose bulk bytes live outside the screen root, persist a stable relative locator/root mapping in the execution resolver. Do not rely on retained Python `Path` objects or an unbound filename such as `target_size_eval_mX.extxyz` whose root is lost after process exit.

## E-R4.5. Make per-cell publication genuinely conflict-safe

The logical cell key is exactly `(screen/window, boundary, N, optimizer_seed)`. Publication semantics:

- no existing logical-cell pointer -> exactly one writer wins publication;
- existing pointer to identical completion -> idempotent success;
- existing pointer to different completion -> hard scientific conflict;
- two concurrent different writers may not resolve by last `os.replace()`.

Use exclusive create, advisory/process lock with verified ownership, compare-and-swap, or another correct local-filesystem mechanism. Keep content-addressed completion objects immutable, but separately protect the unique logical-cell pointer.

Restart must additionally scan content-addressed completions/progress evidence sufficiently to detect a conflicting orphan completion for the same logical cell rather than trusting only the winning pointer.

---

# 4. P3-E restart algorithm is fixed, not delegated

`reconcile_target_size_screen_root()` must be refactored to accept one authenticated restart authority/resolver containing the current schedule, optimizer-policy template/per-seed derivation, canonical P1 authority, export/evaluation policy, context/common preparation and durable root mappings.

For a fresh reopen it must execute this algorithm:

1. authenticate `screen.json` against current aggregate/context/common;
2. enumerate immutable heads and current-head pointer; require the pointer to resolve exactly to its immutable head object;
3. verify every requested digest-addressed filename equals the loaded object's actual `content_digest`;
4. determine one unique committed head ancestry from the initial reducer state; reject loops, missing parents, sibling/fork/orphan heads or skipped/conflicting ancestry;
5. enumerate complete batches and reject more than one batch claiming the same reducer pre-state, including orphan candidates;
6. for each committed batch in ancestry, derive the expected active boundary and ordered matrix from the **replayed** P2 state;
7. resolve every completion by digest and exact logical cell; reject duplicate/conflicting/orphan completion evidence for an active cell;
8. for each completion, rehydrate and execute the real variant-specific validators:
   - trajectory;
   - materialization;
   - successful snapshot or attempted-rung/failure ancestry;
   - role + exact-M artifact where applicable;
   - prediction evidence/attempt where applicable;
   - metric or numerical-error/failure record;
9. reconstruct the P2 `BoundaryOutcome` from those authenticated parents; never use the serialized completion outcome or `batch.outcomes` as authority;
10. require reconstructed outcome digest == completion outcome digest only as an integrity cross-check;
11. rebuild the ordered complete boundary batch from reconstructed completions/outcomes and require its digest/content to equal the stored batch;
12. invoke the real `advance_target_size_reducer()` exactly once for that replay step;
13. require the recomputed post-state to equal the immutable head post-state;
14. continue until the unique current head; require final replayed state equality;
15. only after full validation expose the reopened head/state or continue new work.

If the current-head pointer is missing after a fully durable unique head/batch publication, repair is allowed only after the same graph/uniqueness checks prove a single valid successor. Do not infer authority merely from the presence of a batch file.

Serialized `outcome` fields remain caches/integrity evidence; they do not enter reducer replay without re-derivation.

---

# 5. P3-F final proxy-proof acceptance

Replace or substantially revise the existing P3-F assembled test. P3-F must no longer retain `_CandidateLane`, boundary-state, materialization, or continuation Python objects as restart authority across the reopen boundary.

Use an actual subprocess/fresh interpreter when practical; otherwise use a harness that destroys all runtime execution objects and constructs a new restart-authority/resolver solely from durable roots plus freshly rebuilt accepted P1/P2/P3 authorities. A test that calls reconcile in the same process and then continues from retained lane objects does not close this gate.

Required assembled bounded tests:

### F-R4.1 success path

```text
P1 -> P2 -> P3 common/context
 -> exact trajectory/materialization
 -> TRAIN2 to n1 -> immutable snapshot
 -> exact M1 artifact
 -> real direct inference owner (fake only final expensive forward)
 -> authenticated prediction -> EVAL2 metric -> derived P2 metric
 -> completion -> full parent persistence -> batch -> head
 -> continue through surviving n2/n3 trajectories
 -> terminal reducer state
 -> destroy process/runtime objects
 -> fresh full graph replay
 -> identical terminal reducer state
```

The test must exercise distinct materialization/snapshot/evaluation roots.

### F-R4.2 TRAIN2 numerical-failure path

Generate/persist a real authenticated TRAIN2 numerical-failure record through the TRAIN2 failure owner; do not fabricate placeholder SHA evidence. Publish a `train2_failure` completion with no fake boundary/EVAL2 parents, place it in a complete active matrix, reduce, destroy runtime objects, reopen, revalidate the raw failure ancestry and reproduce the same reducer transition.

### F-R4.3 EVAL2 numerical-failure path

Run through an authenticated completed snapshot and exact-M prediction attempt that produces a real EVAL2 numerical-error record. Require prediction digest equality, derive the P2 failure, commit it in a complete matrix, destroy runtime objects and reproduce the same transition after fresh replay.

### F-R4.4 adversarial persistence/identity matrix

At minimum prove fail-closed behavior for:

- same-sized wrong or reordered ExtXYZ M population while advertised metadata remains plausible;
- changed P1 sidecar geometry/label identity;
- stale/foreign materialization config or export policy;
- corrupted snapshot checkpoint/summary/companion and identical snapshot retry;
- live-for-EMA substitution, truncated EMA shadow list, wrong loaded-state digest;
- forged/mutated prediction payload;
- metric record from different prediction evidence under same role;
- EVAL2 failure record with foreign/placeholder prediction digest;
- TRAIN2 failure record with foreign/placeholder checkpoint SHA where a checkpoint is required;
- missing parent resolver record/locator;
- content-address filename containing a different internally valid object;
- current-head copy differing from immutable head;
- orphan/sibling/fork head or batch;
- conflicting orphan completion for one logical cell;
- two truly concurrent different completions racing for one logical-cell pointer;
- retry of identical completion/snapshot/artifact remaining idempotent;
- unaccepted pre-revision-6 P3-local root failing closed rather than being silently migrated.

The generic same-sized `EvaluationDatasetView` bypass requires an explicit negative test using the real generic view type, which has no provenance digest.

---

# 6. Required implementation order and regression gates

Do not spread the repair across new parallel authorities. Implement in this order unless concrete repository evidence requires a smaller local reordering:

1. **D owner consolidation** — mandatory authority object, immutable snapshot only, shared static inference/state loading, exact loaded-state authentication, exact-M byte/order validation, no generic-view bypass, prediction/metric linkage.
   - focused tests;
   - affected trajectory/materialization/TRAIN2/static-inference/provider/EVAL2/P3-D regression.
2. **E immutable publication + failure derivation** — full re-derivation validators, create-or-verify writers, snapshot retry fix, real TRAIN2/EVAL2 failure derivation, conflict-safe logical-cell publication.
   - focused failure/concurrency/storage tests;
   - affected P3-B/C/D/E + TRAIN2/EVAL2 regression.
3. **E full resolver/reconciliation** — all parent locators, mandatory graph publication, fixed replay algorithm, digest-path/head/fork/orphan checks.
   - focused tamper/crash/restart tests;
   - affected P2 reducer + P3-E regression.
4. **F assembled closure** — fresh-process success + TRAIN2 failure + EVAL2 failure and adversarial matrix.
   - fresh final affected-surface regression across all changed TRAIN2, EVAL2, provider/static-inference, export, P2 reducer and P3 tests;
   - repository-required checks.

No production-scale GPU qualification is required for this P3 repair. Bounded CPU/accelerator-policy reference checks are sufficient where needed to prove policy preservation.

---

# 7. Revision-6 exit gate

P3 passes only if an independent reviewer can take a newly produced screen root, discard every live P3 execution object, rebuild only the accepted external authorities, and deterministically prove that each reducer input came from exactly one authenticated chain:

```text
SUCCESS:
P2/context/common
 -> re-derived trajectory
 -> re-derived exact materialization
 -> authenticated immutable TRAIN2 boundary state
 -> byte/order-authenticated exact M_i
 -> shared state-loaded direct inference owner
 -> immutable prediction evidence
 -> EVAL2 metric bound to that prediction
 -> derived P2 metric

TRAIN2 FAILURE:
P2/context/common
 -> re-derived trajectory/materialization + attempted rung/predecessor
 -> durable authenticated TRAIN2 failure evidence
 -> derived P2 numerical failure

EVAL2 FAILURE:
P2/context/common
 -> re-derived trajectory/materialization
 -> authenticated immutable boundary + exact M_i
 -> authenticated prediction attempt
 -> EVAL2 numerical-error record bound to that attempt
 -> derived P2 numerical failure
```

Those reconstructed outcomes must rebuild the exact committed batches and reproduce the complete reducer head chain from the initial P2 state. No optional missing authority, serialized scalar, same-sized generic view, retained Python object, last-writer-wins pointer, or internally self-consistent but externally unverified artifact may substitute for this chain.

Only after this gate and fresh affected-surface regression pass may P3 be marked accepted and P4 start.
