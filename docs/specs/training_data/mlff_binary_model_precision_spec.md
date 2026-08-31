# MLFF ADAPT-PREC1 binary model precision specification

Status: implemented in mdstats 0.20.122a0.

## Purpose

ADAPT-PREC1 defines one precision variable for the learned MACE model and removes staged
FP32-to-FP64 refinement from new production campaign identity. It supersedes the
production precision semantics of PREC1-PREC3 without rewriting historical campaign
evidence.

## Canonical model modes

New campaign initialization supports exactly:

- `single`: learned-model parameters/buffers, training/autograd, optimizer/EMA state, and
  every MACE inference path use float32;
- `double`: the same learned-model lifecycle uses float64.

Plain `init` resolves to `single`. `refine` and user-facing `mixed` are not production
model modes. No hardware heuristic may change the selected model dtype.

The selected dtype must agree across `[model].dtype`, `[training].dtype`,
`[evaluation].dtype`, and `[export].dtype`. Current campaign commands fail
closed on a mismatch.

## Inference and export invariant

A checkpoint is evaluated and exported in its learned-model dtype. An FP32
checkpoint must not be cast to FP64 merely to satisfy a separate evaluation or
deployment dtype. Checkpoint/template reconstruction therefore forbids
model-dtype promotion in current campaign evaluation.

## FP64 scientific-arithmetic invariant

Model dtype does not control mdstats-owned numerical analysis. Operations that are cheap
relative to model inference and benefit from wider arithmetic remain float64 under both
model modes, including:

- elemental/reference-energy fitting, rank/SVD diagnostics, PCA/QR/SVD, feature scaling,
  and deterministic selection-distance reductions;
- cell/strain/geometric linear algebra;
- SSE/RMSE/MAE, regression, confidence/statistical aggregation, and checkpoint scoring;
- observable analysis and NVE drift fitting; and
- mdstats-owned persistent MD positions, cell, velocities/momenta, and integration
  bookkeeping where applicable.

The qualified critical energy/virial reduction policy is also FP64 where that adapter is
applicable. This does not make an FP32 network an FP64 model; operations inseparable from
the MACE differentiation graph remain in the selected learned-model dtype.

## New-campaign protocol identity

New campaign TOML contains no `[training.precision]` staged schedule. New optimizer and
DATA8 protocol identities therefore carry no resolved precision schedule and cannot
reach the historical PREC2 optimizer/EMA promotion runtime. Binary model dtype is bound
through the ordinary model/training/evaluation/export identities.

## Historical compatibility

Historical staged `refine` schedules remain deserializable for reporting, storage,
audit, and archive operations. They are read-only historical evidence. Current
`prepare`, `select-target-size`, `cross-validate`, and `train-production` fail closed when such a profile
is supplied and require the user to choose a new `single` or `double` scientific
identity. Historical schedules are never silently flattened or reinterpreted.

## Acceptance tests

The gate is qualified only when tests prove:

1. CLI initialization exposes only `single|double` and defaults to `single`;
2. generated configs contain no staged precision schedule;
3. model dtype is identical across training, evaluation, and export;
4. evaluation forbids checkpoint/template dtype promotion;
5. FP64 critical/scientific arithmetic remains active for both learned-model dtypes;
6. new DATA8/optimizer policies are schedule-free; and
7. historical `refine` evidence remains readable while production execution rejects it.
