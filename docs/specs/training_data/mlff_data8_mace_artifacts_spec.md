---
title: "MLFF-DATA8: MACE Artifacts, Replay, and Protocol Identity"
author: "mdstats project"
date: "2026-07-28"
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

# MLFF-DATA8: MACE artifacts, replay, and protocol identity

## Status and scope

MLFF-DATA8 converts DATA5-DATA7 evidence into executable, fixed-file MACE job
artifacts. It does not run training, choose a checkpoint, activate a locked test,
or perform active learning. The first adapter is intentionally narrow and is
locked to `mace-torch==0.3.16` with the `NATIVE_MACE_FIXED` exposure backend.

The stage owns five boundaries:

1. MACE-readable target extended XYZ plus compact sidecar provenance;
2. explicit atomic-reference mappings and target training weights;
3. replay train/monitor preparation with disjointness evidence;
4. complete, immutable `TrainingProtocolIdentity` records;
5. independent final-development and cross-validation job directories in which
   held-out evaluation and locked interpolation test data never appear in a
   training configuration.

DATA8 is an artifact-preparation gate. DATA9 owns process execution, candidate
checkpoint evaluation, replay-retention enforcement, out-of-fold aggregation,
final committee construction, and protocol freeze.

## Why the adapter is version locked

MACE is an evolving training application rather than a static file format. The
adapter therefore verifies the exact source behavior on which its artifacts
depend. For MACE v0.3.16, the required behaviors are:

- the replay head `pt_head` is sorted before target heads;
- validation heads are evaluated in loader order;
- native scheduler, patience, and best-checkpoint logic use only the last
  validation head;
- target data can be duplicated internally when the target/replay ratio falls
  below `real_pt_data_ratio_threshold`;
- `dry_run` and `save_all_checkpoints` are available;
- external replay supports `pt_train_file` and `pt_valid_file`.

The first adapter uses target-last ordering so native scheduling observes the
target monitor, disables implicit duplication by writing
`real_pt_data_ratio_threshold: 0.0`, requests all candidate checkpoints, and
records a loader dry-run prediction. DATA9 later applies the declared target,
cation-resolved, stress, and replay-retention constraints externally.

A source probe is evidence, not a claim that any future MACE version is
compatible. Every supported version requires its own tested compatibility
record.

## Public contracts

### `MaceCompatibilityPolicy`

Locks package name, package version, release tag, commit, official source URLs,
and policy version. The initial policy accepts only `mace-torch==0.3.16`.

### `MaceSourceProbe`

Records content digests and verified source semantics:

- replay-head ordering;
- target-last validation ordering;
- last-head checkpoint behavior;
- implicit target duplication;
- dry-run support;
- save-all-checkpoint support;
- fixed-file adapter acceptance.

The adapter fails closed if any required behavior is absent.

### `MaceCheckpointControlPolicy`

The initial mode is
`NATIVE_TARGET_LAST_WITH_EXTERNAL_CONSTRAINT_AUDIT`. It requires:

- target validation head last;
- all candidate checkpoints saved;
- native early stopping effectively neutralized by large patience;
- external replay-retention audit when replay is enabled;
- no locked-test evidence in checkpoint selection.

### `MaceLoaderDryRun`

Predicts the realized loader contract before training:

- head and validation-head order;
- native checkpoint head;
- requested and effective target/replay counts;
- implicit target duplication factor;
- target/replay ratio;
- fixed-file backend identity.

For target count \(N_{ft}\), replay count \(N_{pt}\), and threshold \(r\),
the v0.3.16 compatibility emulation repeats target data until the realized
ratio satisfies the source behavior. DATA8 defaults to \(r=0\), so balancing is
owned explicitly by mdstats rather than hidden inside MACE.

### `MaceExtxyzArtifact`

Stores one verified target data file and its sidecar manifest. Every exported
configuration contains the minimum MACE-readable keys:

```text
REF_energy
REF_forces
REF_stress
config_weight
config_energy_weight
config_forces_weight
config_stress_weight
frame_uid
```

The exporter performs an ASE write/read round trip and verifies frame order,
labels, weights, and stress representation. Per-atom floating columns are
written with at least 17 significant decimal digits. The ASE 3.29 default
`%16.8f` format is not used because it can round Cartesian positions and force
labels by several nanounits and violate the lossless DATA8 contract.

### Stress contract

`REF_stress` is an ASE six-component stress vector in eV/Angstrom^3 with order

```text
xx yy zz yz xz xy
```

and ASE's stress sign convention. Stress and virial are never conflated. A
missing stress label is represented through zero stress loss weight, not by a
fabricated physical value.

### Atomic-reference mapping

DATA7 `AtomicReferenceFitRecord` values are serialized into the target head as
an explicit mapping from atomic number to energy. Conceptual record names are
never placed in the MACE `E0s` field. The target head also carries an explicit
head-local `atomic_numbers` literal containing only elements present in target
configurations. The top-level `atomic_numbers` remains the union of target and
replay elements for model construction. This distinction is required by MACE
0.3.16: without the head-local table, the target head inherits replay-only
elements and incorrectly demands target E0 values for them. The fit-record
digest remains in the job manifest and `TrainingProtocolIdentity`.

### `ReplayPreparationPlan`

Supported modes are:

- `NONE`;
- `PRESELECTED` local replay;
- `EXTERNAL_TRUE_LABEL` local replay;
- `EXTERNAL_PSEUDOLABEL` local replay;
- `MP_SHORTCUT` preparation-only planning.

Fixed-file execution requires local replay train and monitor artifacts.
`MP_SHORTCUT` is rejected at job-bundle construction until its selected replay
file has been materialized and inspected.

Replay train and monitor configurations must be geometry-disjoint. The monitor
is never used for gradients and later provides retention evidence. Each file
records its SHA-256 digest, frame count, element set, geometry identities, and
property keys.

### `ReplayRetentionPolicy`

Declares the retention metric, maximum tolerated degradation, disjoint-monitor
requirement, and failure behavior. DATA8 serializes this policy; DATA9 evaluates
it against saved checkpoints.

### `FoundationCheckpointIdentity`

Binds protocol artifacts to the exact foundation checkpoint path, file digest,
model label, and optional model metadata. A changed checkpoint creates a new
training protocol.

### `TrainingProtocolIdentity`

Binds all choices that can change optimization or interpretation:

- target label domain;
- naive or multi-head replay mode;
- foundation checkpoint;
- replay-plan digest;
- DATA7 objective, weight, E0-fit, and checkpoint-policy digests;
- MACE compatibility lock and source probe;
- optimizer and precision settings;
- checkpoint-control policy;
- exposure backend;
- loader dry-run realization;
- selected training level;
- random seed.

A naive protocol and a replay protocol are different identities even if their
target XYZ files are identical.

### `SealedEvaluationArtifact`

Records locked interpolation-test membership and lineage without writing a test
XYZ file. The artifact is explicitly unmaterialized. DATA9 may activate it only
after a `ProtocolFreezeRecord` exists.

### `MaceJobArtifact`

Represents one final-development job or one independent cross-validation fold.
It binds:

- target training and checkpoint-monitor artifacts;
- optional replay train and monitor artifacts;
- explicit fold evaluation artifact excluded from the training configuration;
- YAML configuration;
- run script;
- protocol identity;
- loader dry-run record;
- file checksums and manifests.

### `Data8PreparationBundle`

Collects all final and fold jobs for exactly one target label domain, plus local
replay artifacts and sealed outer evaluation metadata. Multiple incompatible
target label domains require separate DATA8 bundles.

## Extended-XYZ and sidecar split

Extended XYZ carries only training labels, weights, and a stable `frame_uid`.
Complete provenance remains in a canonical JSON sidecar keyed by frame UID:

- source occurrence and source-content identities;
- source frame index;
- composition and condition;
- geometry and label-payload identities;
- eligibility and selection lineage;
- weight and E0-fit records;
- file and policy digests.

This prevents long provenance payloads from becoming fragile XYZ header text.

## Job layout

A bundle has the conceptual layout:

```text
data8_bundle/
  shared/
    replay/replay_train.xyz
    replay/replay_monitor.xyz
  jobs/
    final/
      target_train.xyz
      target_monitor.xyz
      mace_config.yaml
      run_mace.sh
      job_manifest.json
    fold_00/
      target_train.xyz
      target_monitor.xyz
      fold_evaluation.xyz
      mace_config.yaml
      run_mace.sh
      job_manifest.json
    ...
  data8_bundle.json
```

`fold_evaluation.xyz` is an evaluation artifact only. Its path must not appear
in `mace_config.yaml`. No locked interpolation-test XYZ exists in this tree.

## MACE configuration contract

The target head contains explicit property keys and E0 values. A replay job
also declares `pt_train_file` and `pt_valid_file`. The generated configuration
shall include:

- `foundation_model`;
- `multiheads_finetuning`;
- target head and optional `pt_head` definitions;
- explicit energy, force, and stress keys;
- target/replay head weights;
- DATA7 global property weights;
- optimizer, seed, device, and floating-point precision;
- `save_all_checkpoints: true`;
- target-last native checkpoint-control settings;
- `real_pt_data_ratio_threshold: 0.0` by default;
- no test path.

The first adapter supports fixed-file training only. `CUSTOM_EPOCH_RESAMPLE`
and `MULTI_JOB_RESAMPLE` remain later backends and cannot be represented merely
by writing one static YAML file.

## Cross-validation jobs

Each DATA5 fold produces an independent job:

1. DATA7 features, E0 values, weights, and selection are fit only on the fold's
   gradient-training domain.
2. The nested checkpoint monitor is exported as the MACE validation file.
3. The held-out evaluation fold is exported separately and excluded from the
   MACE configuration.
4. Replay artifacts and optimizer/checkpoint rules match the final protocol.
5. DATA9 trains a fresh model and evaluates the held-out fold only after the
   checkpoint decision.

A cross-validation family that omits replay cannot validate a final replay
protocol.

## Failure rules

DATA8 fails closed when:

- the MACE source probe does not match the active version lock;
- more than one target label domain enters one bundle;
- a DATA7 fold is missing or has incompatible DATA5 lineage;
- the foundation checkpoint cannot be hashed;
- an E0 mapping is incomplete for the target elements;
- a target label or training weight is unavailable;
- replay train and monitor overlap;
- local replay is incomplete;
- `MP_SHORTCUT` is passed to fixed-file execution;
- a locked-test or fold-evaluation path enters a training configuration;
- an extended-XYZ round trip changes labels, stress, weights, or frame order;
- serialized digests or file checksums fail.

## Non-goals

DATA8 does not execute MACE, inspect actual checkpoint files, enforce replay
retention numerically, aggregate out-of-fold results, choose a final model,
construct a committee, freeze a protocol, activate locked tests, calibrate
uncertainty, or acquire active-learning labels.

## References

1. MACE documentation, "Multihead fine-tuning," official project documentation,
   accessed 2026-07-28.
2. MACE documentation, "Training," official project documentation, accessed
   2026-07-28.
3. ACEsuit/MACE v0.3.16 source, `mace/cli/run_train.py`, official tagged source.
4. ACEsuit/MACE v0.3.16 source, `mace/tools/train.py`, official tagged source.
5. ACEsuit/MACE v0.3.16 source, `mace/tools/multihead_tools.py`, official tagged
   source.
6. ASE documentation, extended XYZ and stress conventions, version 3.29.0.

## DATA9A hardening amendments

The production adapter applies the following stricter contracts:

- foundation fine-tuning requires a checkpoint-bound `foundation_residual`
  atomic-reference fit; direct total-energy E0 fitting is a from-scratch-only
  fallback;
- the foundation checkpoint and local replay files are staged under `shared/`,
  YAML paths are relative, and run scripts change to their own directory;
- extended-XYZ verification compares species/order, PBC, cell, positions,
  energy, forces, stress, config type, and all weights numerically;
- replay inspection rejects nonfinite/misshaped labels and internal exact
  duplicates, records stress coverage, and binds pseudo-labels to a checkpoint;
- top-level `atomic_numbers` is the union of target and replay elements;
- `heads.target_head.atomic_numbers` is the target-only element set, preventing
  replay-only species from becoming target-head E0 requirements;
- one explicit DATA7 ladder size is bound into every protocol identity.

These amendments are implemented in 0.20.37a0 as part of DATA9A hardening.

## DATA9A2 executable-serialization amendments

The v0.3.16 runtime contract is stricter than a native YAML interpretation.
`atomic_numbers`, `heads`, every nested head `atomic_numbers` value, and every
nested head `E0s` mapping are emitted as scalar strings containing deterministic
Python literals. The loss name is the
lowercase parser choice `universal`. DATA8 does not emit unsupported
`weight_pt` or `weight_ft` options.

For preselected fixed-file replay, target and replay training exposure is
realized by multiplying each training structure's extended-XYZ
`config_weight` by the corresponding target or replay head scale. Validation,
monitor, fold-evaluation, and locked-test structures remain unscaled. The target
sidecar records base, scale, and realized weights. These amendments are
implemented in 0.20.39a0 and are qualified by the real-MACE DATA9A2 records.


## Selectable fine-tuning precision

`MaceOptimizerPolicy.default_dtype` SHALL be either `float32` or `float64` and
SHALL be serialized into every generated MACE configuration. Because the
optimizer policy is part of `TrainingProtocolIdentity`, changing precision
creates a different protocol even when every dataset artifact is unchanged.

The MPA-0 foundation checkpoint may remain uniformly float64. The DATA8 bundle
SHALL reference it unchanged; runtime conversion to float32 is requested through
MACE's `default_dtype` option. DATA8 SHALL NOT claim the output precision from
configuration text alone. DATA9A runtime realization must inspect the saved
model and target-head model and prove that all floating parameters and buffers
are uniformly the requested dtype.

## DATA9A9b production orchestration

DATA9A9b calls the native DATA8 builder only after all planned final and
fold-local DATA7 bundles verify. The production plan binds the foundation
checkpoint, MACE compatibility probe, optimizer/checkpoint/export policies,
selection size, and exact replay train/monitor plan before artifact generation.
A `ProductionData8ArtifactRecord` binds the native DATA8 bundle digest and every
relative file path and SHA-256 in the emitted tree. A partial or modified tree is
not accepted as production materialization evidence.
