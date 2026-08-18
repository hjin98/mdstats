---
title: "MLFF-DATA9A4: Selectable Precision and Production DATA6-DATA8 Realization"
version: "0.20.41a0"
status: "precision implemented; production DATA6-DATA8 realization incomplete"
date: "2026-07-29"
---

# MLFF-DATA9A4: selectable precision and production DATA6-DATA8 realization

## 1. Purpose and boundary

DATA9A4 completes the production realization between the qualified 27-source
bulk-LTA corpus and executable MACE jobs. It also makes the numerical precision
of every fine-tuning job an explicit, user-selectable protocol choice.

The starting MACE-MPA-0 checkpoint may be stored in `float64`. The fine-tuned
model may be realized in either:

- `float64`, for maximum numerical consistency with the foundation checkpoint;
- `float32`, for lower memory use and higher throughput on hardware such as an
  RTX 3090.

Precision selection changes the optimization trajectory and model artifact.
It is therefore part of the immutable training-protocol identity, not a runtime
convenience flag.

DATA9A4 does not compare production checkpoints or activate locked-test labels.
Those operations remain owned by DATA9B.

## 2. User-facing precision contract

The user selects precision through
`MaceOptimizerPolicy(default_dtype="float32")` or
`MaceOptimizerPolicy(default_dtype="float64")`.

No other value is accepted. DATA8 writes the selected value to the generated
MACE configuration as `default_dtype`. Final-development and fold-local jobs may
be generated in either precision, but a single DATA8 preparation bundle must use
one optimizer policy and therefore one precision.

The `TrainingProtocolIdentity` already binds the optimizer-policy digest. Thus,
identical data and hyperparameters trained in `float32` and `float64` are
distinct protocols.

## 3. Foundation-to-target conversion

For `mace-torch==0.3.16`, fine-tuning from a file checkpoint proceeds by:

1. loading the foundation model in its stored dtype;
2. constructing a new fine-tuning model under the requested default dtype;
3. copying compatible foundation weights;
4. converting the resulting model to the requested dtype before optimization.

mdstats does not rewrite the original foundation checkpoint. The source model
may remain `float64` while the resulting trainable model is `float32`.

The conversion is accepted only if all floating parameters and floating buffers
in the trained artifact use the requested dtype. Integer and Boolean buffers are
permitted and are reported separately.

## 4. Precision evidence

`MaceModelPrecisionRecord` records, for one model artifact:

- exact file path and SHA-256 digest;
- model class;
- floating parameter dtypes and counts;
- floating buffer dtypes and counts;
- non-floating parameter and buffer counts;
- inferred uniform floating dtype;
- expected dtype, when supplied;
- pass/fail status and explicit failure reasons.

A record fails when:

- the artifact is absent or cannot be loaded;
- no floating state exists;
- more than one floating dtype is present;
- the uniform dtype differs from the expected dtype;
- the artifact digest changes after inspection.

`MacePrecisionTransitionRecord` binds:

- foundation checkpoint identity and observed precision;
- DATA8 job and optimizer-policy digests;
- requested target precision;
- trained full-model precision;
- extracted target-head precision;
- whether a real dtype conversion occurred.

A `float64 -> float32` transition is valid and expected. A trained model whose
floating state remains `float64` after requesting `float32` fails closed.

## 5. Execution-smoke integration

The real MACE execution smoke must inspect the final compiled model and the
extracted target-head model. The smoke passes only when both artifacts match the
job's requested precision.

Evaluation is performed using the extracted model without overriding it back to
a different dtype. Energies, forces, and stresses must remain finite.

The smoke record includes the precision-transition record digest. Precision
verification cannot be replaced by parsing log text such as "Using float32".
The serialized model state is the source of truth.

## 6. Production DATA6-DATA8 realization

The production realization remains bound to:

- DATA3 frame-catalog digest;
- DATA4 feature-bundle and compact-projection digests;
- DATA5 partition-bundle digest;
- candidate-plan digest;
- exact MPA-0 checkpoint digest;
- exact candidate frame UIDs;
- exact ring/site policy and catalog identity;
- final and fold-local DATA6/DATA7 digests;
- four DATA8 job identities;
- selected precision.

Expensive checkpoint inference and LTA site realization may be restricted to the
DATA5-owned candidate union, but no outer-monitor, uncertainty-calibration,
locked-test, purged, or otherwise excluded frame may enter a fitting or selection
domain.

## 7. Acceptance tests

DATA9A4 precision support is accepted only when focused tests demonstrate:

1. both `float32` and `float64` policies serialize and produce distinct protocol
   identities;
2. invalid dtype names fail closed;
3. generated MACE YAML contains the exact requested `default_dtype`;
4. the supplied `float64` MPA-0 checkpoint is detected as `float64`;
5. a real one-epoch `float32` fine-tuning job completes from that checkpoint;
6. the trained full model is uniformly `float32`;
7. the extracted target-head model is uniformly `float32`;
8. finite energy, force, and stress evaluation succeeds with the `float32`
   artifact;
9. a real `float64` smoke remains supported and produces a uniformly `float64`
   artifact;
10. precision records round-trip with digest validation and reject tampering.

Production DATA9A closes only after the remaining DATA6-DATA8 lineage and
execution artifacts also pass. Precision support alone does not authorize
DATA9B.
