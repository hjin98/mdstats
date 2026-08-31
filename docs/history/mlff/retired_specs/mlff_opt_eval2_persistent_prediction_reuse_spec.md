# MLFF OPT-EVAL2 - persistent prediction artifacts and foundation reuse

Status: implemented in mdstats 0.20.98a0.

## 1. Purpose

OPT-EVAL2 removes repeated MACE forward passes when the expensive model/geometry
calculation is unchanged but reference labels, metric weights, reporting policy, or
restart state changes. It separates **model prediction** from **metric reduction**.
The scientific checkpoint-selection rules are unchanged.

This stage follows OPT-EVAL1. OPT-EVAL1 makes a checkpoint cheap to materialize;
OPT-EVAL2 makes materialization and inference unnecessary when authenticated
predictions already exist.

## 2. Prediction artifact contract

A persistent evaluation prediction artifact contains only model outputs:

- one total energy per configuration;
- one `(n_atoms, 3)` force array per configuration;
- optional `(3, 3)` stress tensors;
- frame offsets needed to reconstruct variable-size configurations.

The artifact does **not** contain DFT/reference labels and does not bind metric
thresholds or combined-loss weights.

The runtime-inference cache key binds:

- model SHA-256;
- model head;
- ordered geometry identity digest;
- configuration count;
- MACE evaluation dtype;
- device identity;
- acceleration-policy digest;
- versioned numerical-execution contract.

The cache layout is content-addressed beneath
`<campaign-internal>/evaluation-predictions/`. Metadata and NumPy payloads are
published atomically. Every load verifies metadata identity and the prediction-file
SHA-256 before arrays are accepted.

Cache corruption is a miss, never a silent partial read. If the source checkpoint is
still available, the prediction is recomputed and the corrupt entry is replaced. If
both source checkpoint and valid prediction are unavailable, evaluation fails closed.

## 3. Metric contract

Metric reduction consumes an immutable labelled monitor plus a prediction sequence.
It computes the existing energy, force, focused-species, condition, stress, and
combined-loss records. Therefore:

`prediction identity != metric identity`.

A new label artifact or a changed metric-weight policy can recompute metrics from the
same prediction artifact without invoking MACE. Acceptance/selection thresholds that
do not alter the underlying metric definition continue to operate above this layer.

`CheckpointEvaluationRecord` schema v3 stores optional prediction-artifact digests for
candidate/foundation target/replay predictions. v1 and v2 evaluation records remain
readable and migrate with these fields unset.

## 4. Candidate prediction reuse

For each shortlisted checkpoint, target and (when applicable) replay candidate
predictions are looked up before checkpoint reconstruction. When all required
candidate prediction artifacts are authenticated:

- the raw checkpoint may already have been pruned;
- OPT-EVAL1 checkpoint materialization is skipped;
- the MACE calculator is not constructed;
- metrics are rebuilt directly from cached predictions and current labels.

An existing checkpoint file whose bytes no longer match the frozen checkpoint
inventory is always an error. Cached predictions may replace **missing** immutable
checkpoint bytes, but may not hide a changed checkpoint file.

## 5. Foundation prediction reuse

Foundation predictions are shared across all checkpoints evaluating the same monitor.
Miss resolution is single-flight under the existing foundation-evaluation lock so
parallel checkpoint workers cannot redundantly import or infer the same foundation
prediction set.

### 5.1 DATA6 target-monitor reuse

The existing DATA6 foundation prediction manifest is an eligible source when all of
the following are authenticated:

- foundation checkpoint SHA-256;
- default/single-head semantics;
- device;
- dtype;
- acceleration-policy digest;
- requested ordered target frame UIDs;
- DATA6 prediction sidecar/file digests.

Matching DATA6 predictions are imported once into the uniform evaluation-prediction
cache. A mismatch falls back to normal foundation inference.

### 5.2 Frozen replay pseudolabel reuse

For `FOUNDATION_PSEUDOLABEL` training replay, the frozen replay labels are themselves
the historical foundation outputs used to define replay regularization. They may be
used as the foundation prediction values for an independent TRUE_DFT replay monitor
when:

- the exact foundation checkpoint digest matches;
- default-head semantics are used;
- training and evaluation replay configuration counts match;
- geometry identities and order match exactly;
- the pseudolabel replay bytes match their frozen artifact SHA-256.

This reuse authenticates the **frozen prediction values actually used to build the
replay corpus**. It does not claim that re-running a different accelerator/runtime
implementation today would reproduce every floating-point bit. The source replay
artifact digest is retained as prediction-source provenance. If these conditions do
not hold, mdstats runs the foundation model normally.

## 6. Restart and cleanup behavior

A restart checks prediction artifacts independently of metric records. Thus:

- stale metric record + valid prediction artifact -> metric-only rebuild;
- corrected true replay labels + same geometry -> metric-only rebuild;
- changed combined-loss weights + same model/geometry -> metric-only rebuild;
- missing raw checkpoint + complete candidate predictions -> metric-only rebuild;
- corrupt/missing prediction + valid checkpoint -> inference and cache repair;
- corrupt/missing prediction + missing checkpoint -> fail closed.

The existing true-label replay provenance split remains unchanged: the enclosing
evaluation record identifies the TRUE_DFT evaluation replay artifact, while the
nested checkpoint metric remains bound to the DATA8 training replay lineage used for
admissibility.

## 7. Concurrency

Candidate predictions remain parallel across admitted workers. Shared foundation
miss resolution is serialized only around cache recheck plus one DATA6/pseudolabel
import or foundation inference. Followers become cache hits immediately after atomic
publication. This avoids duplicate foundation GPU work while preserving candidate
parallelism.

## 8. Evidence and diagnostics

Metric evaluation notes record prediction cache hit/miss state and source kind for
target/replay candidate/foundation predictions. This makes restart and foundation
reuse auditable without changing selection policy.

Focused qualification covers:

- metric-policy changes with no repeated inference;
- true-label replay corrections with no repeated candidate inference;
- successful reuse after raw checkpoint deletion;
- corrupted prediction rejection/recomputation;
- DATA6 foundation import without foundation inference;
- frozen pseudolabel foundation reuse against TRUE_DFT labels;
- single-flight foundation import under concurrent checkpoint evaluation;
- v2 evaluation-record migration;
- existing true-label lineage, checkpoint reconstruction, CuEq concurrency, campaign
  control, and evaluation-cost-policy regressions.

## 9. Non-goals

OPT-EVAL2 does not change monitor graph construction or make metric reduction fully
vectorized. Those are OPT-EVAL3 concerns. It does not change the heterogeneous
campaign scheduler into a staged producer/consumer pipeline; that remains OPT-EVAL4.
It does not change checkpoint selection thresholds, replay admissibility rules,
training data, or model weights.
