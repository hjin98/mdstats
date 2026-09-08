---
kind: implementation-package-amendment
package_id: CODE-MLFF-TARGET-SIZE-V7-P3-REVIEW3
amends_package_id: CODE-MLFF-TARGET-SIZE-V7-P3
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
sequence: 3
status: active
package_revision: 5
amended_date: 2026-08-28
blocked_implementation_commit: d7e1aead580d3cecad6eec16219bda00317b1dfc
---

# P3 Review-3 closure amendment — exact execution owners, immutable evidence, and replayable failures

## 0. Authority and scope

This amendment is **mandatory P3 revision-5 authority**. P3 revision 5 consists of:

1. `P3_CANDIDATE_EXECUTION_PAIRED_SCREEN.md`;
2. `P3_REVIEW2_AUTHENTICATED_EVAL_RESTART_FIX.md`; and
3. this Review-3 closure amendment.

The implementation at `d7e1aead580d3cecad6eec16219bda00317b1dfc` is **not accepted**. Review-2 remains authoritative. This amendment does not reopen P1/P2 or P3-A/B/C scientific design; it makes the still-open P3-D/E/F implementation consequences exact enough to prevent another proxy or internally-consistent-but-unauthenticated pass.

P4 remains blocked until the cumulative revision-5 P3 exit gate passes.

### Frozen scope

Preserve without redesign unless a listed reopen condition fires:

- exact P2 candidate sizes, optimizer seeds, fidelity boundaries and evaluation memberships;
- P3-A common preparation and exact `T_N` projection semantics;
- P3-B exact target/harness materialization semantics;
- P3-C one continuous TRAIN2 trajectory with exact completed-epoch boundaries and authenticated continuation;
- Review-2 exact-M direct-boundary EVAL2 semantics;
- Review-2 immutable historical boundary evidence, per-cell execution proof, completion-bound batches, and deterministic reducer replay;
- no P3 public CLI/CampaignStore cutover before P4;
- no full long GPU/production qualification during this repair.

The remaining work is implementation nonconformance and necessary persistence/owner closure, not a broad architecture redesign.

---

# R3-D — make direct inference and EVAL2 evidence real, policy-faithful, and non-forgeable

## D-R3.1. The direct-boundary inference owner must execute every provenance check itself

`run_target_size_direct_boundary_inference()` or its version-agnostic successor is the required semantic owner. A caller must not obtain admissible prediction evidence by presenting mutually consistent metadata while bypassing the validators that authenticate the bytes actually consumed.

Before any expensive forward computation, the owner must execute the real validation path for:

1. candidate trajectory against the current P2 definition, P3 context/common preparation, screen schedule, and candidate optimizer policy;
2. candidate materialization against the exact trajectory, current canonical P1 frame authority, current common preparation/context, and candidate optimizer policy;
3. immutable TRAIN2 boundary snapshot against the exact trajectory, schedule, snapshot bytes, continuation companion and checkpoint identity;
4. direct EVAL2 role against the trajectory, exact boundary snapshot, current P2 boundary/M-rung and exact evaluation-data authority;
5. exact evaluation artifact against the current P2 membership and canonical P1 numerical/frame authority;
6. exact evaluated model representation (`live` or `ema`) and its digest against the immutable boundary snapshot.

These checks must happen inside the owner before invoking any allowed test double. Tests may replace only the expensive model-forward primitive below this point.

A plain mutable/latest `TargetSizeBoundaryState` is not sufficient for the accepted durable scientific path once a historical boundary snapshot exists. The accepted D/E/F path should require the immutable snapshot object or an equivalent immutable authenticated boundary reference.

## D-R3.2. Reuse the existing static MACE/EVAL2 inference machinery; do not maintain a second inference engine

The current bespoke path that directly `torch.load()`s a checkpoint, constructs `MACECalculator(device="cpu", default_dtype="float64")`, and loops serially over ASE structures must be removed from the accepted owner path.

The repaired owner must reuse/extract the repository's established static MACE inference/provider machinery, including the already-qualified architecture reconstruction, batching, ordering, OOM/backoff, resource/admission and acceleration seams where applicable. The direct target-size owner may specialize **checkpoint selection** to exactly one bound snapshot, but it must not duplicate the numerical inference engine.

Required behavior:

- reconstruct the trained MACE architecture/configuration from the validated candidate materialization/current training configuration rather than assuming the raw TRAIN2 checkpoint is directly a deployable model object;
- load/apply the exact authenticated boundary state into that architecture;
- honor the trajectory/context frozen device, dtype, critical-precision, acceleration and batching policy where scientifically or execution-material;
- preserve exact input order and return exactly one prediction per ordered `M_i` frame;
- retain existing safe batching/resource behavior instead of forcing serial CPU inference;
- do not enter historical shortlist/rescue/checkpoint-selection logic.

CPU-only bounded tests are allowed by constructing a legitimate CPU execution policy. They may not justify hard-coding CPU or FP64 into the production owner. No full GPU qualification is required here.

## D-R3.3. Snapshot, materialization and evaluation-data locators must be distinct from scientific identity

The inference API must not overload one `root_directory` as the root for unrelated artifact families.

The owner must receive or resolve, explicitly and unambiguously:

- materialization/configuration location;
- immutable boundary-snapshot location;
- exact evaluation-artifact location;
- any content-addressed prediction/evidence store location.

A version-agnostic resolver/authority object is preferred if it lowers complexity. Relative locators are execution metadata, not scientific identity. Absolute filesystem paths must not enter scientific content digests merely to locate files.

The accepted path must work when materialization, snapshot and evaluation artifacts live under different roots, as they do in the assembled P3 workflow.

## D-R3.4. Live/EMA state must be the state actually evaluated

The owner must prove the model parameters presented to inference equal the declared evaluated state:

- `live` -> exact `rung_runtime_summary.live_parameter_digest`;
- `ema` -> exact `rung_runtime_summary.ema_state_digest`.

For EMA:

- the authenticated continuation/snapshot must contain the required EMA state;
- the EMA shadow state must be applied completely and with exact parameter cardinality/order/shape compatibility;
- missing, truncated, foreign or incompatible EMA state is an execution/provenance error and must fail closed;
- silently leaving raw/live parameters in place while declaring EMA is forbidden.

Where the shared MACE inference provider has a canonical state-loading/hot-swap compatibility owner, reuse it rather than reimplementing parameter application.

## D-R3.5. Prediction evidence authenticates the payload actually reduced

`TargetSizePredictionEvidence` or its successor must be self-authenticating:

- construction and deserialization recompute the canonical prediction-payload digest from the stored prediction values and bound role, and reject a supplied digest that differs;
- stored arrays must be immutable copies or otherwise protected from in-place mutation after digest construction;
- reduction must recompute/validate payload identity before consuming the predictions;
- evidence must continue to bind exact trajectory, immutable boundary snapshot, completed epoch, live/EMA representation, evaluated-state digest, evaluation artifact, ordered M membership, count/order and any scientifically material backend/precision realization.

A caller-provided digest plus mutable prediction arrays is not admissible evidence.

## D-R3.6. Remove the arbitrary-view scientific bypass

The authoritative target-size reduction must not accept an unauthenticated arbitrary `EvaluationDatasetView` merely because its count equals `M_i`.

Choose one of these acceptable realizations:

- build the view internally from the already validated exact evaluation artifact; or
- accept only a provenance-bearing view wrapper whose exact artifact/view digest is revalidated against `TargetSizeEvaluationArtifact.evaluation_view_digest` and whose ordered membership is authenticated.

A generic same-sized view with no source/membership identity is forbidden at the accepted owner boundary.

## D-R3.7. Metric and P2 outcome must be derived, not independently supplied

For a successful cell, the owner chain must enforce:

```text
prediction_evidence.prediction_payload_digest
    == Eval2TargetMetricRecord.prediction_digest
Eval2TargetMetricRecord.target_role_digest
    == exact role digest
TargetSizeBoundaryMetric
    == deterministic translation of that exact metric record + role
```

`build_target_size_cell_completion_record()` must not accept an independently constructed successful P2 metric alongside otherwise valid parent digests. It must derive the P2 outcome internally or recompute it and require exact equality.

The same principle applies to EVAL2 numerical failure: classification must be derived from the authenticated prediction attempt/error record and exact role, not accepted as a free-standing P2 failure object.

### D-R3 acceptance

Before R3-E dependent work:

- direct inference invokes the real trajectory/materialization/snapshot/evaluation validators before the fake-forward seam;
- tampered materialization config/ExtXYZ, snapshot checkpoint/summary/companion, or evaluation ExtXYZ/sidecar is rejected **by the direct owner** before forward execution;
- a same-sized foreign or reordered evaluation population cannot enter reduction;
- mutable/tampered prediction payload after evidence construction is rejected or structurally impossible;
- forged prediction payload digest is rejected on construction/deserialization/use;
- live-for-EMA substitution, missing EMA, truncated EMA and wrong evaluated-state digest fail closed;
- an execution policy configured for float32/CPU remains float32/CPU; an accelerator-configured policy is not silently rewritten to CPU/FP64;
- structural/source evidence confirms the P3 owner no longer contains a bespoke hard-coded serial `MACECalculator(device="cpu", default_dtype="float64")` inference engine;
- bounded owner-level tests may fake only the model-forward primitive below all provenance/state-loading checks;
- affected static-inference, EVAL2, MACE provider/state-loading, critical-precision and target-size D regressions pass.

---

# R3-E — make every persisted object re-derivable, immutable, conflict-safe, and replayable

## E-R3.1. Validators are re-derivation authorities, not internal-consistency checkers

Restart validators must reconstruct expected identity from current accepted authorities and compare the durable record to that expectation.

### Candidate trajectory validator

In addition to existing `T_N` and realization checks, validate at minimum:

- exact experiment/context/common/schedule bindings;
- exact optimizer seed and membership in P2 seed policy;
- `seed_neutral_training_policy_digest == context.seed_neutral_optimizer_policy_digest`;
- candidate optimizer policy equals the seed-neutral template except for the authorized seed/authorized realization fields;
- `evaluation_model_state == ("ema" if optimizer_policy.ema else "live")`;
- exact replay/foundation-none identity required by P3;
- recomputed candidate training-protocol digest equals the stored digest;
- exact candidate membership/digest/order and N-derived realization.

A coherently forged trajectory record must not pass because only membership and update geometry happen to match.

### Candidate materialization validator

Extend its authority inputs as required. Re-derive and validate at minimum:

- target-train artifact ordered UIDs exactly equal `trajectory.candidate_membership`;
- target-train membership digest exactly equals `trajectory.candidate_membership_digest`;
- target-train common-preparation digest equals current common preparation;
- harness-validation ordered UIDs/digest exactly equal current common harness membership and remain non-controlling;
- both exported artifacts bind the current canonical P1 frame authority and exact export policy;
- MACE configuration is recomputed from trajectory + projection + common preparation + optimizer policy + export policy and is byte/content equivalent to the durable configuration except for explicitly execution-only fields, if any;
- seed, dtype, device, batch/worker policy, EMA convention, acceleration/critical precision, E0 mapping, target/harness paths and any training-objective/material configuration fields cannot drift silently.

Do not validate only file hashes plus seed/path.

### Exact evaluation-artifact validator

Re-derive and validate at minimum:

- exact P2 `M_i`, ordered frame UIDs and membership digest;
- current canonical P1 dataset/frame authority;
- exact energy/forces/stress keys and export policy;
- ExtXYZ bytes SHA;
- sidecar bytes SHA and content digest;
- sidecar dataset id, role, canonical authority digest, membership digest and exact record UID set/order semantics;
- each sidecar frame record corresponds to the advertised exact M membership and canonical P1 record;
- recomputed deterministic `evaluation_view_digest` equals the stored value;
- a view built from the artifact has the expected count/order/numerical channel structure.

An object that advertises exact M metadata while pointing to self-consistent bytes for another same-sized population must fail.

## E-R3.2. Scientific artifact publication is create-or-verify, never destructive overwrite

For candidate target/harness ExtXYZ, MACE config, exact-M evaluation artifacts, immutable boundary snapshots, prediction evidence, metric/failure evidence, completion records, batches and heads:

- publish to content-addressed or otherwise collision-safe immutable locations;
- if the intended identity already exists and bytes/content match exactly, reuse it;
- if an identity/location already exists with different bytes/content, fail closed **without modifying the existing object**;
- perform conflict detection before replacing any previously committed scientific bytes;
- a retry may not overwrite accepted evidence and then raise a conflict afterward.

For boundary snapshots specifically:

- do not use only `(trajectory, boundary)` as an overwriteable directory identity;
- a second different snapshot for the same trajectory/boundary is a scientific conflict and must not replace the first;
- existing committed cell references must keep their snapshot bytes for their full lifetime;
- garbage collection must respect committed references.

For candidate materialization:

- `output_directory` or any absolute path must be moved out of the scientific content digest or replaced by a relative execution locator that is not scientific identity;
- pre-amendment P3-local records may be rejected/rebuilt rather than migrated because P3 has not cut over.

Atomic publication must include the directory-durability steps required by the repository's claimed crash model. If the product claims survival of process crash only, ordinary atomic rename may suffice; if the tests/contract claim filesystem/power-loss durability, fsync containing directories after durable rename/pointer publication as appropriate.

## E-R3.3. Completion records use explicit success/TRAIN2-failure/EVAL2-failure variants

A single schema that requires successful downstream objects for every outcome is forbidden.

Implement one discriminated/version-agnostic completion authority with these semantic variants (exact class layout delegated):

### Successful evaluation

Must bind/revalidate:

```text
window
trajectory + exact realization
validated materialization
immutable completed-boundary snapshot
exact EVAL2 role
exact M evaluation artifact
prediction evidence
Eval2TargetMetricRecord
P2 metric derived from the record
```

### Authenticated TRAIN2 numerical failure

A TRAIN2 failure may occur before the scheduled boundary is completed. It must therefore bind:

```text
window
trajectory + attempted scheduled boundary/rung plan
validated materialization
predecessor continuation ancestry, if any
real durable Train2NumericalFailureRecord / failure artifact
P2 TargetSizeNumericalFailure derived from that record
```

It must **not** require or fabricate:

- a completed-boundary snapshot for the failed boundary;
- an EVAL2 role;
- an evaluation artifact/prediction/metric.

The durable failure owner must authenticate the actual failure record. Where a raw checkpoint SHA/name is part of the failure record, verify the referenced durable bytes when the failure taxonomy says such a checkpoint exists. Tests must not close this path by manually constructing a record with placeholder SHA values and calling only the translation helper.

### Authenticated EVAL2 numerical failure

Must bind:

```text
window
trajectory/materialization
immutable completed-boundary snapshot
exact EVAL2 role + exact M artifact
prediction attempt/evidence
real EVAL2 numerical-error record
P2 TargetSizeNumericalFailure derived from that error
```

Ordinary provenance/input/checkpoint errors remain execution errors and cannot be converted into scientific failure evidence.

## E-R3.4. Persist the referenced execution graph, not only its digests

Every digest in a committed completion record must be resolvable after a fresh process restart.

Persist immutable/content-addressed records or locators for, as applicable:

- trajectory;
- materialization;
- boundary snapshot;
- exact evaluation artifact authority;
- EVAL2 role;
- prediction evidence/payload;
- EVAL2 metric or error record;
- TRAIN2 numerical failure record/evidence;
- completion record;
- batch;
- head.

A completion record may store relative locators plus digests, but restart must be able to resolve those locators and then verify the resolved object's content digest equals the bound digest. Digest-only references to objects that were never persisted are insufficient.

## E-R3.5. Give reconciliation the authorities required to perform real replay

`reconcile_target_size_screen_root()` may be extended with one narrow version-agnostic restart-authority/resolver object rather than accumulating unrelated positional arguments.

It must have authenticated access to the minimum authorities needed to execute the real validators, including:

- current P2 experiment/initial reducer state;
- current P3 context/common preparation;
- exact screen schedule;
- candidate optimizer-policy template / means to re-derive per-seed policy;
- current canonical P1 frame/numerical authority;
- export/evaluation policy needed to reproduce artifact identity;
- durable resolver/root mapping for materialization, snapshots, exact-M artifacts, predictions, metrics/failures and other committed records.

The resolver is execution infrastructure, not a new scientific authority. Scientific identity remains in the accepted P1/P2/P3 records and content digests.

## E-R3.6. Reconciler performs complete graph replay and strict content-address checks

For every reopen:

1. validate screen/window against current aggregate/context/common and initial reducer state;
2. reject unsupported pre-revision-5 P3-local durable schema rather than fabricating provenance;
3. enumerate immutable heads/batches sufficiently to detect forks, conflicting siblings, skipped parents and orphan committed heads/batches according to the accepted visibility rules;
4. treat `current_head` as a pointer to an immutable head, or if it embeds a copy, require exact equality with the immutable `heads/<digest>.json` object;
5. whenever an object is loaded from a path keyed by digest, require `loaded.content_digest == digest encoded by the reference/path`;
6. replay head ancestry from genesis/initial reducer state in order;
7. for each batch, derive the active boundary/M/key matrix from the replayed pre-state;
8. load every ordered completion record by its bound digest and revalidate the correct success/TRAIN2-failure/EVAL2-failure variant through the real owners;
9. reconstruct every P2 outcome from validated parent evidence rather than trusting the serialized completion/batch scalar;
10. rebuild/revalidate the complete batch identity from the reconstructed completion records/outcomes;
11. call the real `advance_target_size_reducer(...)` on those reconstructed outcomes;
12. require recomputed post-state exactly equals the committed head declaration;
13. require final replayed head/state exactly equals the atomic current pointer;
14. only then expose reopened state or schedule more work.

Serialized `batch.outcomes`, completion `outcome`, and head pre/post state remain caches/evidence only. They are never authoritative over reconstruction.

## E-R3.7. Concurrent publication is atomic and conflict-detecting

Per-cell publication must not use a check-then-replace race that permits last-writer-wins for conflicting evidence.

For each `(window, boundary, N, seed)` progress slot:

- identical duplicate publication is idempotent;
- a distinct completion digest for the same slot is a hard conflict;
- concurrent writers must resolve atomically using exclusive create, compare-and-swap/lock, immutable slot file plus conflict scan, or an equivalent mechanism;
- conflicting immutable completion records that exist even if only one progress pointer won must be detected during restart/collection rather than ignored as harmless orphans;
- workers may publish independent cell artifacts/completions but never reducer transitions.

Likewise, current-head publication must remain single-history and fail closed on conflicting same-pre-state batches/heads.

### E-R3 acceptance

Add focused/adversarial evidence for at least:

- trajectory validator rejects wrong seed-neutral policy digest, wrong evaluation live/EMA convention, forged training-protocol digest and stale realization;
- materialization validator rejects same-sized wrong target membership, wrong harness membership, altered E0/config dtype/device/batch/EMA/acceleration policy, and changed artifact bytes;
- evaluation validator rejects a self-consistent same-sized wrong/reordered population, wrong sidecar role/dataset/membership/policy, stale view digest and modified bytes;
- republishing conflicting materialization/evaluation/snapshot evidence leaves the original committed bytes unchanged;
- same trajectory/boundary with different snapshot bytes fails without overwrite;
- absolute materialization paths do not affect scientific identity;
- real TRAIN2 numerical failure can become a committed cell without snapshot/EVAL2 fabrication and survives fresh restart/replay;
- real EVAL2 numerical failure binds exact boundary/M/prediction attempt and survives replay;
- successful cell outcome is derived from the exact metric; changing only the stored scalar is rejected;
- every content-addressed load rejects filename/reference-digest mismatch;
- tampering/deleting trajectory, materialization, snapshot, evaluation artifact, prediction evidence, metric/failure record or completion causes real reconciliation failure even if downstream P2 scalar remains syntactically valid;
- orphan/skipped/forked/conflicting heads and batches fail closed;
- conflicting concurrent completion publication is detected; identical duplicate publication remains idempotent;
- old revision-3/revision-4 P3-local roots without the revision-5 graph fail closed with rebuild guidance;
- affected TRAIN2 persistence/failure, materialization/export, EVAL2, static inference, P2 reducer and P3 concurrency/restart regressions pass.

---

# R3-F — assembled acceptance must be fresh-process equivalent

## F-R3.1. Required success-path integration

The final bounded success integration must use the real owners through:

```text
P1 canonical authority
 -> P2 definition + initial bound reducer
 -> P3 common/context/schedule
 -> candidate trajectory
 -> immutable candidate materialization
 -> TRAIN2 n1
 -> immutable n1 snapshot
 -> exact M1 artifact
 -> real direct-boundary inference owner
      -> allowed fake only below validation/state-loading at the expensive forward seam
 -> authenticated prediction evidence
 -> EVAL2 metric
 -> success completion
 -> complete batch
 -> real P2 transition
 -> immutable head/current pointer
 -> continued TRAIN2 n2/n3 for survivors
 -> terminal P2 state
```

Then simulate a fresh process rather than keeping `_CandidateLane`/boundary/materialization objects as hidden authority:

- discard in-memory candidate lanes and previously instantiated completion objects;
- reconstruct/reload required P3 state through durable records + accepted P1/P2/context/common/schedule authorities;
- run the real reconciler over the entire history;
- prove the same terminal P2 state and selected membership;
- where a survivor must continue after a restart boundary, prove TRAIN2 resumes from the authenticated predecessor snapshot/continuation rather than from retained Python objects or foundation initialization.

## F-R3.2. Required TRAIN2-failure integration

Add a bounded assembled path where one matrix cell experiences a real authenticated TRAIN2 numerical failure before completing its scheduled boundary. The real coordinator must:

- persist the failure evidence variant;
- construct the derived P2 numerical failure without fabricated snapshot/EVAL2 parents;
- complete the boundary matrix according to P2 policy;
- transition through the real reducer;
- reopen in a fresh-process-equivalent reconciler and reconstruct the same failure/outcome from durable evidence.

## F-R3.3. Required EVAL2-failure integration

Add a bounded assembled path where direct inference completes but EVAL2 emits an authenticated non-finite numerical failure. The real owner must bind exact boundary + exact M + prediction attempt, derive the P2 failure, persist it, replay it after restart, and reject an otherwise identical failure carrying a foreign prediction/boundary/M identity.

## F-R3.4. Crash/recovery matrix remains cumulative

Review-2 crash positions remain mandatory. Revision 5 additionally requires that the crash/recovery tests use the new durable graph/resolver and cover destructive-publication and conflict windows, including:

- after artifact temp/write but before immutable publication;
- concurrent conflicting progress publication;
- immutable completion published but progress slot not yet visible;
- head immutable object published but current pointer missing;
- current pointer present but immutable head missing/mismatched;
- fresh restart after later-rung continuation has advanced mutable TRAIN2 runtime files, proving historical n1/n2 snapshots remain independently valid.

Each valid crash point converges to exactly one reducer history. Corrupt/conflicting scientific evidence fails closed rather than being repaired by coordinated rehash or last-writer-wins behavior.

## F-R3.5. Test-double boundary

Allowed:

- reduced epochs/data sizes preserving semantics;
- synthetic canonical P1 fixtures;
- CPU execution policy for bounded CI;
- fake expensive model forward **inside/below** the real static/direct inference owner after architecture/state/input validation;
- deterministic persistence/concurrency fault injection.

Forbidden for P3 acceptance:

- callback that replaces checkpoint/model reconstruction or boundary-state application;
- callback executed before snapshot/materialization/evaluation validation;
- arbitrary same-sized evaluation view;
- manually constructed prediction evidence or trusted digest;
- manually constructed TRAIN2 failure with placeholder checkpoint identity as the only failure-path evidence;
- manually supplied final P2 scalar/failure where the completion owner should derive it;
- retained in-memory candidate lanes as the authority for the post-crash/reopen phase;
- custom test-only reconciliation/state reconstruction replacing the real owner;
- direct reducer invocation bypassing coordinator/reconciler for the assembled acceptance claim.

---

# 1. Revision-5 implementation sequence

Implement in this order unless a smaller equivalent ordering preserves the dependency boundaries:

1. **R3-D1 — owner and validator closure**
   - strengthen trajectory/materialization/evaluation validators;
   - separate locators from identity;
   - make immutable snapshot validation mandatory inside direct inference.
   - focused tests + affected P3 A-D/materialization/export/TRAIN2 regressions.

2. **R3-D2 — shared inference + prediction/metric closure**
   - replace bespoke CPU/FP64 loop with shared static MACE inference/state-loading seam;
   - enforce live/EMA and backend/precision policy;
   - make prediction payload immutable/self-authenticating;
   - remove arbitrary-view bypass;
   - derive metric/P2 outcome.
   - focused tests + affected static-inference/EVAL2/P3-D regression.

3. **R3-E1 — immutable publication and completion variants**
   - create-or-verify artifact stores;
   - content-address snapshot/evidence lifetime;
   - success/TRAIN2-failure/EVAL2-failure completion variants;
   - persist resolvable parent evidence.
   - focused tests + affected TRAIN2 failure/export/materialization/persistence regression.

4. **R3-E2 — full restart graph and concurrency closure**
   - introduce the minimum restart authority/resolver;
   - rehydrate/rederive every cell;
   - reconstruct batches/outcomes;
   - strict digest/path validation;
   - fork/orphan/conflict detection;
   - atomic conflicting-cell publication.
   - adversarial restart/concurrency tests + affected P2/P3-E regression.

5. **R3-F — fresh-process assembled closure**
   - success, TRAIN2-failure and EVAL2-failure end-to-end paths;
   - full crash matrix;
   - fresh-process terminal replay and survivor continuation;
   - fresh final affected-surface regression and repository-required checks.

Every executable stage requires semantic/conformance closure and stage-local affected regression before dependent work proceeds.

---

# 2. Revision-5 implementation authority

## Frozen additions

Implementation must preserve all Review-2 frozen additions and additionally:

- direct inference itself authenticates every consumed parent before the forward seam;
- one shared/static MACE inference engine remains the numerical execution authority; P3 does not grow a second hard-coded CPU/FP64 engine;
- materialization, snapshot and evaluation roots are resolved independently of scientific identity;
- evaluated live/EMA digest corresponds to the parameters actually presented to inference;
- prediction payload digest is recomputed from immutable values actually reduced;
- successful P2 metrics and scientific failures are derived from authenticated parent evidence;
- validators re-derive expected identities from current accepted authorities rather than trusting self-consistent durable metadata;
- scientific publication is create-or-verify and never destroys previously accepted evidence on conflict;
- TRAIN2-failure cells do not fabricate completed-boundary/EVAL2 parents;
- all committed parent evidence is durably resolvable after process restart;
- reconciler has enough accepted authority to execute real validation/replay;
- every digest-addressed lookup verifies the loaded object matches the requested digest;
- concurrent conflicting cell publication is detected, never last-writer-wins;
- assembled acceptance is fresh-process equivalent and includes success, TRAIN2-failure and EVAL2-failure paths.

## Delegated mechanics

Implementation may choose:

- exact restart-authority/resolver class shape;
- exact content-addressed directory layout;
- whether current-head is a digest-only pointer or an embedded copy plus exact immutable-head verification;
- exact locking/CAS/exclusive-create mechanism for per-cell progress publication;
- exact immutable prediction payload storage format;
- exact shared static-inference adapter extracted for single-boundary use;
- exact discriminated-union/class layout for completion variants;
- hardlink/reflink/copy strategy for immutable snapshot bytes, provided conflicts never overwrite committed evidence.

## Forbidden additions

Implementation may not:

- preserve the bespoke direct `torch.load` + serial CPU/FP64 MACE inference path as a parallel production authority;
- call the fake inference callback before real provenance/state/input validation;
- treat absolute artifact paths as scientific identity;
- accept materialization because its bytes hash while its exact T_N/harness/config semantics differ;
- accept evaluation bytes because hashes match while their exact M membership/policy differs;
- trust a stored prediction digest without recomputing it from the stored values;
- allow mutable prediction arrays to change after authentication without invalidation;
- require fabricated boundary/EVAL2 objects for a pre-boundary TRAIN2 failure;
- overwrite committed artifacts/snapshots before discovering a conflict;
- persist only digests for parent evidence that restart cannot resolve;
- replay serialized batch/completion outcomes instead of deriving them from parent evidence;
- ignore orphan conflicting completion/head/batch evidence that changes uniqueness of the committed history;
- resolve concurrent conflicting completion publication by whichever writer replaces the progress file last;
- use retained Python objects as the authority for the fresh-restart acceptance path;
- add compatibility migration for unaccepted pre-revision-5 P3-local durable roots merely to preserve old fixtures.

## Reopen only on evidence

Reopen only the smallest affected P3 surface if evidence shows one of these is impossible without changing frozen product semantics:

- the existing static MACE inference/state-loading machinery cannot evaluate the exact immutable TRAIN2 live/EMA boundary representation without entering retired checkpoint-selection authority;
- the real TRAIN2 numerical-failure owner cannot persist enough evidence to authenticate a scientific failure without changing the P2 failure taxonomy;
- current accepted P1/P2 authorities do not expose enough information to re-derive exact T_N/M_i artifact identity without adding a new scientific authority;
- atomic/create-or-verify persistence cannot satisfy the repository's declared crash model on supported filesystems without a broader persistence-policy decision.

Do not reopen merely because the current revision-4 schema or tests are inconvenient; those P3-local schemas are unaccepted and may be replaced.

---

# 3. Revision-5 exit gate

P3 is accepted only when the assembled implementation proves, through real owners and fresh-process replay, that every reducer input is losslessly derived from one of these authenticated chains:

```text
SUCCESS:
trajectory
 -> exact materialization
 -> exact immutable completed-boundary TRAIN2 state
 -> exact ordered P2 M_i artifact
 -> shared direct-boundary inference owner
 -> immutable/self-authenticating prediction evidence
 -> EVAL2 metric
 -> derived P2 metric

TRAIN2 SCIENTIFIC FAILURE:
trajectory + attempted rung
 -> exact materialization + predecessor continuation
 -> real durable TRAIN2 numerical-failure evidence
 -> derived P2 numerical failure

EVAL2 SCIENTIFIC FAILURE:
trajectory/materialization
 -> exact immutable completed boundary
 -> exact ordered P2 M_i artifact
 -> authenticated prediction attempt
 -> real EVAL2 numerical-error evidence
 -> derived P2 numerical failure
```

Every completed cell must then be durably resolvable, bound into exactly one complete ordered batch, replayed through the real P2 reducer from the initial accepted state, and reproduced after a fresh-process-equivalent reopen.

Tampered or same-sized foreign memberships, stale/foreign model state, live/EMA substitution, mutable/forged predictions, destructive retry, missing parent evidence, wrong digest-addressed file, forged scalar, conflicting concurrent cell, fork/orphan head/batch, and stale pre-revision-5 root must all fail closed.

Only after this cumulative revision-5 gate passes may P3 be marked accepted and P4 begin.
