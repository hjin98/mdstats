---
title: "MLFF-DATA8: MACE Artifacts, Replay, and Protocol Identity"
author: "mdstats project"
date: "2026-09-14"
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

The stage owns five boundaries for consumers that still use the DATA8 fixed-file
representation:

1. MACE-readable target extended XYZ plus compact sidecar provenance;
2. explicit atomic-reference mappings and target training weights;
3. replay train/monitor preparation with disjointness evidence;
4. complete, immutable `TrainingProtocolIdentity` records; and
5. independent final-development and cross-validation job directories in which
   held-out evaluation and locked interpolation test data never appear in a
   training configuration.

DATA8 is an artifact-preparation gate. DATA9 owns process execution, candidate
checkpoint evaluation, replay-retention enforcement, out-of-fold aggregation,
final committee construction, and protocol freeze for the consumers that still
use this representation.

**Restored current P5 is not authorized by this broad DATA8 protocol graph.**
Current post-selection cross-validation and fresh final production are governed
by `mlff_post_selection_p5_spec.md` and descend from
`PostSelectionMethodIdentity -> role policy -> role plan -> fitted preparation ->
PostSelectionMaterialization -> run evidence`. `TrainingProtocolIdentity` and
`Data8PreparationBundle` remain current only for separately current non-P5
consumers that still use them and as historical provenance; successful
deserialization does not make them current P5 authority.

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
- multi-head fine-tuning can replace the requested learning rate and EMA
  settings unless `force_mh_ft_lr` is true;
- target-head, distributed-sampler, and combined training loaders can discard
  the final partial batch through `drop_last`;
- `dry_run` and `save_all_checkpoints` are available; and
- external replay supports `pt_train_file` and `pt_valid_file`.

The broad DATA8 fixed-file adapter uses target-last ordering where that
consumer's checkpoint contract requires native target-last scheduling, disables
implicit duplication by writing `real_pt_data_ratio_threshold: 0.0`, requests
all candidate checkpoints, and records a loader dry-run prediction. Restored
P5 does not inherit DATA8's historical fold-local checkpoint-monitor topology;
its exact common-monitor topology and mode-specific execution are owned by
`mlff_post_selection_p5_spec.md`.

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
- the multi-head loss, LR/EMA override, and target-loader truncation branches
  that the qualified runtime must control;
- dry-run support;
- save-all-checkpoint support; and
- fixed-file adapter acceptance.

The adapter fails closed if any required behavior is absent.

### `MaceCheckpointControlPolicy`

For broad DATA8 consumers using this legacy/general fixed-file policy, the
initial mode is `NATIVE_TARGET_LAST_WITH_EXTERNAL_CONSTRAINT_AUDIT`. It requires:

- target validation head last;
- all candidate checkpoints saved;
- native early stopping effectively neutralized by large patience;
- external replay-retention audit when replay is enabled; and
- no locked-test evidence in checkpoint selection.

Restored P5 checkpoint/adaptive-stop target evidence is instead the external
campaign-common `M_mon` defined by the current P5 specification.

### `MaceLoaderDryRun`

Predicts the realized loader contract before training:

- head and validation-head order;
- native checkpoint head;
- requested and effective target/replay counts;
- implicit target duplication factor;
- target/replay ratio; and
- fixed-file backend identity.

For target count \(N_{ft}\), replay count \(N_{pt}\), and threshold \(r\),
the v0.3.16 compatibility emulation repeats target data until the realized
ratio satisfies the source behavior. DATA8 defaults to \(r=0\), so balancing is
owned explicitly by mdstats rather than hidden inside MACE.

### Qualified execution semantics

The current execution identity is pinned to `mace-torch==0.3.16` and the
source-qualified mdstats MACE wrapper. Loss realization is **method-specific**.

For separately accepted weighted paths represented through DATA8, including P3
target-size screening and the accepted P5-scratch method where applicable, the
parser-facing configuration explicitly carries the weighted loss and all
objective coefficients. Replay-enabled weighted configurations also carry:

```text
loss = "stress"
force_mh_ft_lr = true
real_pt_data_ratio_threshold = 0.0
```

Every ordinary one-head parser-facing configuration explicitly carries
`multiheads_finetuning = false`; replay configurations carry
`multiheads_finetuning = true` where that current consumer uses the DATA8
multi-head path. This prevents MACE 0.3.16 parser defaults from silently
changing an accepted mode.

The historical wrapper mutation that replaced MACE's multi-head
`UniversalLoss` with `WeightedEnergyForcesStressLoss` belongs only to the
weighted DATA8 method family. It **must not** be applied to restored foundation
P5. Current `naive_fine_tuning` and `multihead_replay` foundation P5 resolve
native `UniversalLoss` with the fixed D2 parameters through the P5 method owner
and existing MACE seam. There is no global cross-mode MACE loss-family authority.

For target-size execution, the same authenticated target-size authority
activates complete target-head and combined-loader coverage: `drop_last` is
false, the realized batch count is `ceil(N / B)`, every exported target
`frame_uid` is present exactly once, and target-size distributed sampler paths
are rejected unless separately qualified. No frame is duplicated to fill a
partial batch. The resolved evidence is attached to the existing TRAIN2
runtime summary; missing, stale, or mismatched evidence cannot authorize a
restart or downstream current artifact.

Restored foundation P5 has different accepted exposure semantics (`drop_last=true`
and single-process, with replay/`pt_head` first then target for multihead replay)
and is governed by `mlff_post_selection_p5_spec.md` rather than this P3
complete-batch clause.

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

For restored foundation P5, `config_weight` may remain a neutral transport field
but is not an active loss/identity layer; binary property masks remain active.

### Executable loss family and weighting layers

For separately accepted **weighted** methods represented through DATA8, the
generated MACE configuration emits the resolved objective explicitly:

```text
loss = "stress"
energy_weight
forces_weight
stress_weight
```

`loss = "stress"` selects pinned MACE's `WeightedEnergyForcesStressLoss`. Its
native reductions consume `config_weight` (`ref.weight`) and the per-frame
property weights linearly and apply the global coefficients exactly once,
outside those reductions. A weighted path may not rely on MACE's
`forces_weight = 100` default.

The old blanket statement that `UniversalLoss` is forbidden on every current
path is retired. Foundation P5 intentionally uses native `UniversalLoss` under
accepted D1/D2. That is valid precisely because foundation P5 no longer claims
the weighted-path `config_weight` contract. Do not emulate foundation
UniversalLoss with a patched loss, square-root weighting trick, residual
pre-scaling, sample duplication, or a second mdstats loss engine.

For methods that consume them, the three weighting layers remain distinct:

| Layer | Owner | Exported as |
| --- | --- | --- |
| global loss coefficients | `[objective]` / `TrainingObjectivePolicy` | `energy_weight`, `forces_weight`, `stress_weight` config keys |
| per-configuration weight | `[weighting]` / `ConfigurationWeightPolicy` | `config_weight` |
| local property weights | canonical label presence | `config_energy_weight`, `config_forces_weight`, `config_stress_weight` |

Local property weights are availability masks - `1.0` when the canonical label
is present, `0.0` when it is absent - and SHALL NOT carry per-frame copies of
the global coefficient ratio.

The `[objective]` and `[weighting]` policy readers validate raw configuration
and current-schema values before canonicalization. Global coefficients are
finite nonnegative reals with at least one positive value; the configuration
equalization flag is an actual boolean; configuration multipliers and bounds
are finite positive reals satisfying the normalized-mean constraint; and
focus collections contain only declared string or positive-integer elements.
Malformed current-schema values SHALL fail rather than become valid policy
identity through `int`, `float`, or `bool` coercion. Historical representations
remain admissible only through an explicit supported compatibility reader.

`TrainingObjectivePolicy` owns the global component coefficients only; it SHALL
NOT carry a loss-family field. Loss family belongs to the applicable method
identity. Foundation P5 therefore resolves its fixed UniversalLoss objective
through `PostSelectionMethodIdentity`, while weighted P3/scratch consumers keep
their existing objective/weighting owners.

### Stress contract

`REF_stress` is an ASE six-component stress vector in eV/Angstrom^3 with order

```text
xx yy zz yz xz xy
```

and ASE's stress sign convention. Stress and virial are never conflated. A
missing stress label is represented through zero stress loss weight, not by a
fabricated physical value.

The six-component transport representation does not redefine the restored
foundation-P5 UniversalLoss reduction, which is governed by D2 and consumes all
nine stored Cartesian stress entries after the dependency's representation
conversion.

### Atomic-reference mapping

DATA7 `AtomicReferenceFitRecord` values are serialized into the target head as
an explicit mapping from atomic number to energy. Conceptual record names are
never placed in the MACE `E0s` field. The target head also carries an explicit
head-local `atomic_numbers` literal containing only elements present in target
configurations. The top-level `atomic_numbers` remains the union of target and
replay elements for model construction. This distinction is required by MACE
0.3.16: without the head-local table, the target head inherits replay-only
elements and incorrectly demands target E0 values for them. The fit-record
digest remains in the applicable job manifest and identity.

Restored foundation-P5 atomic-reference fit/selected-head residual/transfer
semantics are owned by `mlff_post_selection_p5_spec.md`; DATA8 transport does
not create a second E0 solver or fit authority.

### `ReplayPreparationPlan`

Supported modes are:

- `NONE`;
- `PRESELECTED` local replay;
- `EXTERNAL_TRUE_LABEL` local replay;
- `EXTERNAL_PSEUDOLABEL` local replay; and
- `MP_SHORTCUT` preparation-only planning.

Fixed-file execution requires local replay train and monitor artifacts.
`MP_SHORTCUT` is rejected at job-bundle construction until its selected replay
file has been materialized and inspected.

Replay train and monitor configurations must be geometry-disjoint. The monitor
is never used for gradients and later provides retention evidence. Each file
records its SHA-256 digest, frame count, element set, geometry identities, and
property keys.

Current P5 replay-label default/legacy-ambiguity semantics are owned by the P5
specification and cannot be overridden by a broad DATA8 default.

### `ReplayRetentionPolicy`

Declares the retention metric, maximum tolerated degradation, disjoint-monitor
requirement, and failure behavior. DATA8 serializes this policy for consumers
that use this representation; the execution owner evaluates it against saved
checkpoints.

### `FoundationCheckpointIdentity`

Binds protocol artifacts to the exact foundation checkpoint path, file digest,
model label, and optional model metadata. A changed checkpoint creates a new
applicable training identity.

### `TrainingProtocolIdentity`

For separately current non-P5 DATA8 consumers, `TrainingProtocolIdentity` binds
all choices represented by that broad protocol record that can change
optimization or interpretation:

- target label domain;
- generic training mode;
- foundation checkpoint;
- replay-plan digest;
- DATA7 objective, weight, E0-fit, and checkpoint-policy digests;
- MACE compatibility lock and source probe;
- optimizer and precision settings;
- checkpoint-control policy;
- exposure backend;
- loader dry-run realization;
- selected training level; and
- random seed.

A naive protocol and a replay protocol represented through this family are
different identities even if their target XYZ files are identical.

`TrainingProtocolIdentity` is **not current restored-P5 method authority**. Old
DATA8 protocol records cannot authorize P5 cross-validation, final production,
restart, or publication merely because their bytes deserialize.

### `SealedEvaluationArtifact`

Records locked interpolation-test membership and lineage without writing a test
XYZ file. The artifact is explicitly unmaterialized. A downstream owner may
activate it only after the applicable freeze boundary exists.

### `MaceJobArtifact`

For consumers that still use the DATA8 fixed-file job family,
`MaceJobArtifact` represents one final-development job or one independent
cross-validation fold. It binds:

- target training and checkpoint-monitor artifacts;
- optional replay train and monitor artifacts;
- explicit fold evaluation artifact excluded from the training configuration;
- YAML configuration;
- run script;
- protocol identity;
- loader dry-run record; and
- file checksums/manifests.

This fold-local target-monitor shape is **not** current restored-P5 topology.
Current P5 folds bind external common `M_mon` in their role plans.

### `Data8PreparationBundle`

Collects all final and fold jobs for exactly one target label domain, plus local
replay artifacts and sealed outer evaluation metadata, for consumers that still
use this fixed-file representation. Multiple incompatible target label domains
require separate DATA8 bundles.

Current restored P5 SHALL NOT be forced back through `Data8PreparationBundle`
merely to preserve historical structure.

## Extended-XYZ and sidecar split

Extended XYZ carries only training labels, weights/masks, and a stable
`frame_uid`. Complete provenance remains in a canonical JSON sidecar keyed by
frame UID:

- source occurrence and source-content identities;
- source frame index;
- composition and condition;
- geometry and label-payload identities;
- eligibility and selection lineage;
- applicable weight and E0-fit records; and
- file and policy digests.

This prevents long provenance payloads from becoming fragile XYZ header text.

## Job layout

For the broad DATA8 fixed-file representation, a bundle has the conceptual
layout:

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

The presence of `target_monitor.xyz` in this DATA8 layout does not define current
restored-P5 monitor ownership; P5 uses its external common-monitor plan lineage.

## MACE configuration contract

For DATA8 consumers, the target head contains explicit property keys and E0
values. A replay job also declares `pt_train_file` and `pt_valid_file`. The
applicable generated configuration includes the fields required by that method,
including foundation/model, mode/head definitions, property keys, optimizer,
seed, device/precision, checkpoint retention, replay-threshold controls, and no
test path.

Historical/current non-P5 DATA8 weighted configurations may include target/replay
training-head scales and DATA7 objective weights where their accepted method
consumes them. **Restored current P5 does not:** its target/replay training-head
scalar weights are retired, and its foundation objective is fixed by current
D2/P5 specification.

The first DATA8 adapter supports fixed-file training only.
`CUSTOM_EPOCH_RESAMPLE` and `MULTI_JOB_RESAMPLE` remain separate backends and
cannot be represented merely by writing one static YAML file.

## Cross-validation jobs

The following nested-monitor DATA8 job description is retained only for
separately current consumers/historical interpretation of this bundle family:

1. fitted features/E0/weights are fit only on the authorized gradient-training domain;
2. the DATA8 job's checkpoint-monitor artifact is exported as its validation file;
3. the held-out evaluation fold is exported separately and excluded from training configuration;
4. replay artifacts and optimizer/checkpoint rules match that protocol; and
5. execution evaluates held-out evidence only after checkpoint choice.

It does **not** define restored P5 CV. Current P5 fold membership is selected-only
train + held-out outer evaluation + purge, with exact external common `M_mon`
used for checkpoint/adaptive-stop control.

## Failure rules

DATA8 fails closed for its consumers when:

- the MACE source probe does not match the active version lock;
- more than one target label domain enters one bundle;
- a required DATA7 fold is missing or has incompatible lineage;
- the foundation checkpoint cannot be hashed;
- an E0 mapping is incomplete for required target elements;
- a target label or required training weight/mask is unavailable;
- replay train and monitor overlap where forbidden;
- local replay is incomplete;
- `MP_SHORTCUT` is passed to fixed-file execution;
- a locked-test or fold-evaluation path enters a training configuration;
- an extended-XYZ round trip changes labels, stress, weights/masks, or frame order; or
- serialized digests or file checksums fail.

For restored P5, additional current failure rules in
`mlff_post_selection_p5_spec.md` govern UniversalLoss, exact common monitor,
selected-head residual transfer, exposure, currentness, and publication.

## Non-goals

DATA8 does not execute MACE, inspect actual checkpoint files, enforce replay
retention numerically, aggregate out-of-fold results, choose a final model,
construct a committee, freeze a protocol, activate locked tests, calibrate
uncertainty, or acquire active-learning labels. It also does not define current
restored-P5 method identity, common-monitor topology, residual-transfer rule, or
final-publication ordering.

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

The production adapter applies the following stricter contracts where the DATA8
representation is still consumed:

- foundation fine-tuning records a checkpoint-bound `foundation_residual`
  atomic-reference fit; direct total-energy E0 fitting is a from-scratch-only
  fallback in the historical/general topology;
- the foundation checkpoint and local replay files are staged under `shared/`,
  YAML paths are relative, and run scripts change to their own directory;
- extended-XYZ verification compares species/order, PBC, cell, positions,
  energy, forces, stress, config type, and all weights numerically;
- replay inspection rejects nonfinite/misshaped labels and internal exact
  duplicates, records stress coverage, and binds pseudo-labels to a checkpoint;
- top-level `atomic_numbers` is the union of target and replay elements;
- `heads.target_head.atomic_numbers` is the target-only element set, preventing
  replay-only species from becoming target-head E0 requirements; and
- one explicit DATA7 ladder size is bound into every applicable protocol identity.

These amendments are implemented in 0.20.37a0 as part of DATA9A hardening.
Current restored-P5 residual/transfer authority is the P5 specification, not
this historical hardening clause.

## DATA9A2 executable-serialization amendments

The v0.3.16 runtime contract is stricter than a native YAML interpretation.
`atomic_numbers`, `heads`, every nested head `atomic_numbers` value, and every
nested head `E0s` mapping are emitted as scalar strings containing deterministic
Python literals. DATA8 does not emit unsupported `weight_pt` or `weight_ft`
options.

The loss name recorded in this amendment was the lowercase parser choice
`universal`. The subsequent DATA8 weighted topology standardized its current
weighted consumers on `stress`; restored foundation P5 now intentionally uses
native `UniversalLoss` again under the independently accepted P5 method. The
historical transition note is retained so old evidence remains interpretable.

For preselected fixed-file replay, historical DATA9A2 target/replay training
exposure was realized by multiplying each training structure's extended-XYZ
`config_weight` by a corresponding target/replay head scale. Validation,
monitor, fold-evaluation, and locked-test structures remained unscaled. The
target sidecar recorded base, scale, and realized weights. These amendments are
implemented in 0.20.39a0 and remain historical evidence for that topology.
They are **not** current restored-P5 training-head weighting semantics.

## Selectable fine-tuning precision

`MaceOptimizerPolicy.default_dtype` SHALL be either `float32` or `float64` and
SHALL be serialized into every generated MACE configuration that uses this
policy. Because the optimizer policy is part of `TrainingProtocolIdentity` for
its consumers, changing precision creates a different broad protocol even when
dataset artifacts are unchanged. For restored P5, precision identity is bound
through the current P5 method/runtime lineage instead.

The MPA-0 foundation checkpoint may remain uniformly float64. A DATA8 bundle
references it unchanged; runtime conversion to float32 is requested through
MACE's `default_dtype` option. DATA8 SHALL NOT claim output precision from
configuration text alone. Runtime realization must inspect the saved model and
target-head model and prove that all floating parameters and buffers are
uniformly the requested dtype where that qualification is required.

## DATA9A9b production orchestration

For the DATA9A9b topology, the orchestrator calls the native DATA8 builder only
after all planned final and fold-local DATA7 bundles verify. Its production plan
binds the foundation checkpoint, MACE compatibility probe,
optimizer/checkpoint/export policies, selection size, and exact replay
train/monitor plan before artifact generation. A `ProductionData8ArtifactRecord`
binds the native DATA8 bundle digest and every relative file path and SHA-256 in
the emitted tree. A partial or modified tree is not accepted as production
materialization evidence.

This historical/general production topology does not override the current P5
plan/materialization graph.