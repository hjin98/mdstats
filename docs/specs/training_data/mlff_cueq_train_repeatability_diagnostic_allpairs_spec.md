# CUEQ-REPEAT1-DIAG3: Warm-up + All-Pairs TRAIN2 FP32 Repeatability Diagnostic

## Status

- Release: `mdstats 0.20.218a0`
- Architecture revision: 85
- Dependency-graph schema: 67
- Authorizing: **no**
- Active TRAIN2 FP32 parity policy: unchanged at `rtol=1e-5`, `atol=1e-5`

## Motivation

Revision-84 MPA-0/default evidence showed that same-backend FP32 force variability is comparable to the e3nn/pure-CuEq discrepancy. The deterministic-control probe also produced a constant non-zero e3nn run-1-versus-later-run self difference, demonstrating that the temporary baseline method can fold a first-call/warm-up shift into every self statistic. DIAG3 therefore removes both first-call contamination and arbitrary baseline dependence before any permanent parity-policy redesign.

## Frozen measurement algorithm

For each execution mode (ordinary production-path and isolated deterministic control):

1. Construct the exact e3nn and pure-CuEq TRAIN2 calculators/checkpoint/head already used by doctor.
2. Evaluate the complete probe once with e3nn and once with pure CuEq; discard both outputs.
3. Collect ten post-warm-up e3nn outputs and ten post-warm-up pure-CuEq outputs. The normal implementation keeps the existing interleaved e3nn/CuEq collection order.
4. Compute 45 e3nn-self comparisons over all unordered pairs.
5. Compute 45 CuEq-self comparisons over all unordered pairs.
6. Compute 100 cross-backend comparisons over the Cartesian product of the ten e3nn and ten CuEq samples.
7. Persist the complete pairwise scalar metric arrays. Do not retain duplicate force/descriptor arrays after the record is assembled.

## Pair metrics

Every comparison records:

- energy maximum absolute error and RMSE;
- force maximum absolute error and RMSE;
- force absolute-error p99 and p99.9;
- count of force components with absolute difference greater than `1e-5`;
- stress maximum absolute error and RMSE;
- descriptor maximum absolute error and RMSE.

Self comparisons additionally record self-selection identity. Cross comparisons record e3nn/CuEq selection identity.

## Terminal reporting

For DIAG3 all-pairs records, doctor prints:

- mode, warm-up count, post-warm-up repeat count;
- exact pair counts (`45`, `45`, `100` for the default ten samples);
- `min`, `median`, `p90`, `p99`, and `max` for `Fmax`, `Frmse`, `Fp99`, `Fp99.9`;
- equivalent summaries for `Emax`, `Smax`, and `Dmax`;
- force-component exceedance-count distributions;
- same-backend and cross-backend selection-identity counts.

The 100 individual cross pairs are not printed because they add terminal noise without adding information; the full arrays remain in the persisted record.

## Schema compatibility

New records use `mdstats.training-acceleration-repeatability-diagnostic.v2` with `comparison_mode="all_pairs"` and `warmup_count=1`. Historical v1 records remain deserializable and retain `comparison_mode="baseline"`, `warmup_count=0`, `N-1` self comparisons, and `N` paired cross comparisons.

The outer deterministic-control wrapper remains schema v1; when completed under revision 85, its nested repeatability record is v2.

## Deterministic control

The isolated subprocess remains unchanged in purpose and setup:

- `CUBLAS_WORKSPACE_CONFIG=:4096:8` before CUDA initialization;
- `torch.use_deterministic_algorithms(True)`;
- deterministic debug mode `error`;
- cuDNN benchmarking disabled;
- cuDNN deterministic mode enabled.

It now runs the same discarded-warm-up + all-pairs algorithm. Unsupported deterministic operations fail visibly with no fallback.

## Non-authorizing rule

DIAG3 is measurement-only. Its statistics must not widen TRAIN2 parity tolerances or authorize CuEq. A permanent noise-normalized criterion is a separate subsequent policy decision based on the workstation DIAG3 evidence.
