---
title: "MLFF-DATA6: Selection-Grade Structural and Foundation-Model Feature Specification"
author: "mdstats project"
date: "2026-07-30"
version: "0.20.53a0"
geometry: margin=0.8in
fontsize: 10pt
header-includes:
  - |
    ```{=latex}
    \usepackage{microtype}
    \usepackage{booktabs}
    \usepackage{longtable}
    \usepackage{array}
    \usepackage{enumitem}
    \setlist{nosep}
    ```
---

# 1. Purpose and stage boundary

MLFF-DATA6 converts immutable DATA3 frame facts, DATA4 raw and optional
profile-extension states, and DATA5 statistical roles into **raw selection
evidence**. It introduces no
fitted scaler, PCA basis, covariance metric, farthest-point selection, atomic
reference fit, loss weight, MACE training file, or checkpoint decision. Those
remain DATA7-DATA9 responsibilities.

The stage implements four contracts:

1. universal structural and optional profile-extension descriptors;
2. optional checkpoint-bound MACE invariant atomic descriptors;
3. DFT-label-derived difficulty residuals on authorized training domains only;
4. blinded prediction catalogs for non-training evidence domains.

The controlling information boundary is

```text
geometry-only feature
    may be computed on every role for which geometry access is authorized

label-derived residual
    may be computed only on an authorized gradient-training domain

non-training prediction
    may be stored without DFT residuals

locked test
    remains sealed and unmaterialized before protocol freeze
```


# 1A. Current generic structural profile amendment

The historical sections below document the original DATA6 LTA and model-feature
contracts. Beginning with `0.20.48a0`, DATA6 also carries the material-neutral
`UniversalStructuralFeatureCatalog`. Beginning with `0.20.49a0`, DATA6 may
carry one `PhaseGeometrySelectionPlan` derived from explicit DATA9A7a material
contracts. Beginning with `0.20.53a0`, DATA6 schema v5 may bind one completed,
restartable checkpoint-bound model sweep.

The phase/geometry plan controls only MLFF selection exposure:

- enabled universal local-structure feature families;
- enabled generic geometry-event families;
- ordered atom-group coverage priorities for bulk, surface, interface,
  confined, and cluster geometries;
- advisory physical-observable call profiles;
- immutable plan/policy/material-contract lineage.

The numerical local-structure calculation remains owned by
`mdstats.analysis.local_structure`. DATA6 does not own RDF, coordination-
distribution, angle-distribution, topology, dynamics, transport, phonon,
elastic, or thermodynamic algorithms.

DATA6-v1 through DATA6-v4 bundles remain readable. Historical evidence does
not receive a fabricated phase/geometry plan or production model-sweep identity
during deserialization.

# 2. Definitions

## 2.1 Raw descriptor

A raw descriptor is a deterministic numerical representation calculated without
learning any dataset-dependent transformation. A MACE descriptor is an atomic
feature after one or more message-passing blocks. MACE exposes these descriptors
through `MACECalculator.get_descriptors()`; invariant-only output has one row per
atom and a model-dependent feature dimension [1].

## 2.2 Difficulty feature

A difficulty feature compares a frozen foundation-model prediction with a DFT
label. For frame $i$,

$$
e_{E,i}=\frac{|E_i^{\mathrm{model}}-E_i^{\mathrm{DFT}}|}{N_i},
$$

$$
e_{F,i}=\sqrt{\frac{1}{3N_i}\sum_{a=1}^{N_i}
\|\mathbf F_{ia}^{\mathrm{model}}-\mathbf F_{ia}^{\mathrm{DFT}}\|_2^2},
$$

and, when stress exists,

$$
e_{\sigma,i}=\sqrt{\frac{1}{9}\|\boldsymbol\sigma_i^{\mathrm{model}}-
\boldsymbol\sigma_i^{\mathrm{DFT}}\|_F^2}.
$$

Species-resolved force errors are generated for every species present in the
authorized frame. Profile-declared focus groups may later receive explicit
objective or checkpoint emphasis, but DATA6 does not assume Li, Na, K, cations,
or any material-specific species list. Difficulty features are selection
evidence and must never be computed from outer-monitor, calibration,
held-out-fold, or locked-test labels.

## 2.3 Blinded prediction

A blinded prediction contains model outputs or output summaries but no DFT
residual, ranking, or label-derived selection field. Its record is bound to the
DATA5 role and blinding boundary. A locked test produces a sealed metadata record
only; prediction materialization is deferred until a protocol-freeze record
exists.

# 3. Module ownership

```text
mdstats.analysis.local_structure
    universal material-neutral local-geometry calculations

mdstats.training_data.structural_selection
    MLFF atom-group aggregation and universal selection evidence

mdstats.training_data.lta_selection
    optional LTA extension implementation only

mdstats.training_data.model_features
    checkpoint identities, optional MACE calculator adapter,
    raw descriptor sidecars, and prediction summaries

mdstats.training_data.difficulty
    authorized training domains, difficulty residuals,
    blinded prediction domains and catalogs

mdstats.training_data.production_model_sweep
    exact checkpoint-bound frame planning, sidecars, checkpoints, and resume

mdstats.training_data.data6_bundle
    lineage-checked DATA6 orchestration
```

PyTorch and MACE are optional dependencies. Importing `mdstats` must not import
MACE. The public calculator adapter imports MACE lazily only when a model-path
constructor is requested.

# 4. Optional selection-grade LTA extension descriptors

## 4.1 Input requirements

The LTA builder requires:

- a DATA3 `TrainingFrameCatalog`;
- source-index-aligned `FrameData` for each run;
- a DATA4 `LtaPartitionFeatureCatalog`;
- DATA4 raw physical features.

DATA4 ring IDs and atom indices are treated as authoritative for this stage.
Automatic natural-tiling discovery is not repeated in DATA6. A future profile
may provide topology-derived ring IDs through the same record contract.

## 4.2 Per-cation environment vector

For every Li, Na, and K atom, the raw named vector contains:

- oxygen coordination;
- nearest, mean, standard-deviation, median, and maximum M-O distance;
- ring-center distance;
- signed and absolute ring-plane distance;
- radial off-center distance;
- one-hot ring-size indicators for 4R, 6R, 8R, and unresolved;
- one-hot site-class indicators;
- coordination-change, site-change, and ring-crossing flags.

Missing physical values are represented by a policy-declared finite fill value in the
numeric named record and by an aligned missing mask. DATA7 decides how the mask
and fill value enter a fitted metric; DATA6 does not impute from the dataset.

## 4.3 Per-frame LTA vector

The configuration-level vector contains:

- framework-integrity and event flags;
- counts by species, ring size, and site class;
- per-species mean, standard deviation, minimum, and maximum of the cation
  environment scalars;
- DATA4 framework pair-distance and coordination summaries;
- counts of unresolved cation environments.

Feature names are serialized beside values. Reordering a feature changes the
policy digest and record digest.

# 5. Checkpoint-bound MACE descriptors

## 5.1 Checkpoint identity

Every descriptor and prediction record is bound to a
`ModelCheckpointIdentity` containing:

```text
model family
checkpoint locator
checkpoint SHA-256
calculator class
MACE version
adapter version
supported atomic numbers, when declared
device and default dtype
```

A descriptor produced by another checkpoint is a different feature block even
when its shape is identical.

## 5.2 Calculator adapter

The `MaceCalculatorProvider` supports two constructors:

```text
from_model_path(...)
    lazy-imports MACE and constructs MACECalculator

from_calculator(...)
    wraps an already constructed calculator and explicit checkpoint identity
```

The adapter calls `get_descriptors(atoms, invariants_only=..., num_layers=...)`
and validates a finite two-dimensional array with one row per atom. Current MACE
documentation states that only the base `MACE` and `ScaleShiftMACE` model classes
support this descriptor path [1]. Unsupported calculators fail explicitly.

Predictions use ASE energy, force, and full $3\times3$ stress conventions.
Missing stress is recorded rather than fabricated.

## 5.3 Array sidecars

High-dimensional descriptors are not embedded in JSON. Each frame is stored in
one deterministic NumPy `.npy` file. In production, prediction outputs are
stored independently as `predictions/<frame_uid>.npz`. The descriptor manifest
records:

```text
frame UID
relative path
shape
dtype
file SHA-256
array-content digest
```

The cache reader verifies the file hash, dtype, shape, finite values, and
array-content digest before returning an array. Full provenance stays in JSON;
raw arrays stay in sidecars.

## 5.4 Restartable production sweep

`Data6ModelSweepPlan` derives the exact descriptor and prediction frame sets
from DATA5 roles and the active DATA6 policy. Locked-test, purged, excluded, and
otherwise unauthorized frames are recorded as sealed or excluded and may not
appear in the requested union.

`Data6ModelSweepCheckpoint` stores verified per-frame descriptor and prediction
records with `incomplete`, `complete`, or `failed` status. Sidecars and checkpoint
JSON are promoted atomically. Resume verifies file hashes, shapes, dtypes,
finite values, content digests, and required-artifact completeness before reuse.
A complete sweep provides a lazy persistent prediction cache so DATA6 residual
and blinded-summary construction does not rerun the foundation model.

## 5.5 Native MACE descriptor autograd boundary

Native DATA6 graph batching separates descriptor extraction from prediction.
Descriptor extraction is a forward-only operation and runs inside
`torch.no_grad()`. Because MACE 0.3.16 defaults `compute_force=True`, the adapter
must explicitly pass `False` for force, virial, stress, displacement, Hessian,
edge-force, and atomic-stress outputs. A descriptor call must never enter
`torch.autograd.grad`; doing so inside the no-gradient scope is a runtime error
and wastes memory even when it succeeds outside that scope.

Prediction batching has a different contract. Energy, force, and optional stress
are model outputs used by DATA6, so prediction executes inside
`torch.enable_grad()` and retains MACE's derivative path. The adapter may not
solve descriptor failures by globally disabling autograd or by suppressing the
exception, because either action would invalidate force and stress predictions.

# 6. Authorized training domains

A `TrainingDifficultyDomain` is derived only from DATA5 assignments.

## 6.1 Final-development domain

Contains frames in the outer `development` role for one label domain. It is the
only domain from which a final-training difficulty catalog may be built.

## 6.2 Cross-validation training domain

For fold $k$, contains only frames in `training_unit_ids`. Checkpoint-monitor,
evaluation, and purge units are excluded. A fold-specific difficulty catalog is
therefore valid input to fold-local DATA7 selection.

The builder verifies exact frame membership against the DATA5 unit catalog. A
caller cannot create an arbitrary domain and label it as training evidence.

# 7. Blinded prediction domains

DATA6 creates domain metadata for:

- outer checkpoint monitor;
- uncertainty calibration;
- cross-validation checkpoint monitor;
- cross-validation held-out evaluation;
- locked interpolation test.

The first four may be materialized as prediction-only catalogs. The locked test
is emitted with status `sealed_not_materialized` and zero prediction records.
Purged and excluded roles produce no model feature catalog.

A blinded prediction record may contain predicted energy, force norms,
species-resolved predicted-force norms, and predicted stress. It must not contain
DFT energies, DFT forces, DFT stress, residuals, error ranks, or acceptance
judgments.

# 8. DATA6 bundle

`Data6FeatureBundle` binds:

```text
dataset ID
DATA2 source-catalog digest
DATA3 frame-catalog digest
DATA4 feature-bundle digest
DATA5 partition-bundle digest
universal structural and optional profile-extension catalogs
MACE raw-descriptor manifest, optional
atomic-model prediction manifest, optional
production model-sweep plan and checkpoint digest, optional
training-difficulty catalogs
blinded-prediction catalogs
checkpoint identity, when model features exist
```

The bundle fails when:

- any frame or unit lineage differs;
- a difficulty frame lies outside its authorized training domain;
- a blinded catalog contains residual fields;
- a locked-test catalog contains materialized predictions;
- a descriptor file does not verify;
- descriptors and predictions refer to different checkpoint identities;
- a production sweep does not realize the exact plan frame sets;
- a sweep plan, checkpoint, DATA5 bundle, DATA6 policy, or checkpoint identity
  disagrees.

# 9. Determinism and numerical policy

- Frame iteration follows sorted `frame_uid` order.
- Atomic rows retain source atom order.
- Feature names use a policy-defined stable order.
- Descriptor arrays use an explicit dtype.
- Sidecar filenames are `descriptors/<frame_uid>.npy`.
- JSON uses canonical sorted serialization and SHA-256 content digests.
- No random operation occurs in DATA6.

# 10. Public runtime records

The implemented public DATA6 contracts are:

```text
UniversalStructuralFeatureCatalog
ProfileFeatureCatalog
ModelCheckpointIdentity
MaceDescriptorManifest
AtomicModelPredictionManifest
Data6ModelSweepPlan
Data6ModelSweepCheckpoint
TrainingDifficultyFeatureCatalog
BlindedEvaluationPredictionCatalog
Data6FeatureBundle
```

The real VASP-path acceptance tests use the supplied ASE 3.29.0 source
distribution. ASE is a runtime dependency of frame materialization, while MACE
and PyTorch remain optional lazy dependencies for checkpoint-backed features.

# 11. Tests and gate criteria

The stage gate requires:

1. exact round-trip serialization and tamper rejection;
2. Li/Na/K environment-vector fixtures with ring and coordination changes;
3. fixed feature-name and vector ordering;
4. fake-calculator descriptor extraction through the public MACE adapter;
5. descriptor sidecar hash, shape, and dtype verification;
6. final-development and fold-training domain membership checks;
7. rejection of residual computation on monitor, calibration, evaluation, or
   locked-test frames;
8. blinded catalogs containing no DFT residual fields;
9. locked tests remaining unmaterialized;
10. real ASE 3.29.0 VASP-to-DATA6 integration;
11. DATA0-DATA5 regression tests;
12. interruption, failure, resume, and corrupt-sidecar recovery;
13. DATA6 consumption of a completed sweep without repeated model calls;
14. a genuine MPA-0/Na-LTA descriptor and prediction smoke;
15. wheel/install/source-archive smoke tests.

# 12. Deferred work

DATA6 does not implement:

- robust scaling, PCA, whitening, or heterogeneous block metrics;
- farthest-point sampling or training-set size selection;
- fold-local or final atomic-reference energy fitting;
- training objectives and sample/property weights;
- complete production sweep execution;
- final/fold DATA7 production materialization;
- MACE replay binding, DATA8 job generation, or training execution;
- uncertainty calibration or active learning.

These remain DATA7-DATA10 responsibilities.

# References

[1] ACEsuit, "MACE descriptors," MACE documentation,
https://mace-docs.readthedocs.io/en/latest/guide/descriptors.html, accessed
2026-07-28.

[2] I. Batatia et al., "MACE: Higher Order Equivariant Message Passing Neural
Networks for Fast and Accurate Force Fields," NeurIPS 2022,
https://arxiv.org/abs/2206.07697.

[3] A. S. Rosen et al., "Machine learning the quantum-chemical properties of
metal-organic frameworks for accelerated materials discovery," Matter 4,
1578-1597 (2021). Descriptor diversity and model-error diagnostics are useful
selection evidence, but they do not replace independent physical validation.

# DATA9A7d amendment: optional selection-profile extensions

Beginning with `0.20.50a0`, canonical DATA6 schema v4 stores optional
material-specific selection evidence as `profile_selection_features`. The
scientific payload remains owned by the extension provider. Generic DATA6 and
DATA7 code may consume only the common frame-vector, atomic-environment, and
environment-class adapters.

The previous `lta_selection_features` field is not emitted by new bundles. It
remains a compatibility view and a v1-v3 deserialization input. The policy
default no longer activates LTA construction; an explicit LTA profile extension
or an explicitly requested historical compatibility path is required.

The generic fitted feature block is `profile_extensions`. `lta_frame` remains a
read alias. Per-species raw, learned, and difficulty columns are derived from
species present in the authorized fit domain and never from a fixed Li/Na/K
list or from sealed roles.


# DATA9A9a amendment: restartable checkpoint-bound model evidence

Beginning with `0.20.53a0`, canonical DATA6 schema v5 may bind a complete
`Data6ModelSweepPlan`, `MaceDescriptorManifest`,
`AtomicModelPredictionManifest`, and sweep-checkpoint digest. The exact
scientific plan is independent of how many bounded invocations are needed to
finish it. Verified completed frames are reused; corrupt, incomplete, foreign,
or policy-mismatched evidence fails or is explicitly recomputed according to
the execution policy.

The production sweep does not activate locked-test predictions. It also does not
complete DATA7, DATA8, replay binding, or DATA9B.
