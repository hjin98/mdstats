# CUEQ-REPEAT1-PARITY1: Permanent TRAIN2 FP32 Noise-Normalized Parity

## Status

- Release: `mdstats 0.20.219a0`
- Architecture revision: 86
- Dependency-graph schema: 68
- Authorizing: **yes** for TRAIN2 FP32 CuEq backend equivalence
- Deterministic-control subprocess: optional diagnostic only

## Stable channels

Energy, stress, and descriptor differences retain the tight FP32 stable-channel authority. The repeatability reduction requires the maximum observed cross-pair absolute error in each of those channels to remain at or below `1e-6`. The generic/source `MaceAccelerationParityPolicy` remains `rtol=1e-5`, `atol=1e-6`; force authorization is no longer derived from one-shot force `allclose`.

## Force measurement algorithm

1. Construct the exact selected TRAIN2 e3nn and pure-CuEq calculators.
2. Discard one complete warm-up evaluation from each backend.
3. Retain ten post-warm-up outputs from each backend.
4. Compute 45 unordered e3nn-self pairs, 45 unordered CuEq-self pairs, and 100 e3nn/CuEq cross pairs.
5. Persist the full DIAG3 scalar evidence using repeatability-diagnostic schema v2.
6. Reduce that evidence into the noise-normalized parity-record schema v1.

Full schema identifiers:

- `mdstats.training-acceleration-repeatability-diagnostic.v2`
- `mdstats.training-acceleration-noise-normalized-parity-record.v1`

## Distribution gate

For each force statistic `m` in `Frmse`, `Fp99`, and `Fp99.9`:

`self_envelope(m) = max(P99(e3nn-self m), P99(CuEq-self m))`

`cross_stat(m) = P99(cross m)`

`ratio(m) = cross_stat(m) / self_envelope(m)`

Every ratio must be finite and `<= 1.25`. If the self envelope is exactly zero, only an exactly zero cross statistic can pass.

## Catastrophic Fmax guard

`Fmax_self = max(max(e3nn-self Fmax), max(CuEq-self Fmax))`

`Fmax_limit = min(1.5 * Fmax_self, 1e-4 eV/A)`

The maximum cross-pair `Fmax` must not exceed `Fmax_limit`. This is a catastrophic-tail guard, not the primary equivalence statistic.

## Selection and finiteness

All 45 e3nn-self, 45 CuEq-self, and 100 cross selection fingerprints must be identical. Any non-finite evaluation or metric fails qualification. No adaptive widening, retry-until-pass behavior, or silent fallback is allowed.

## MPA-0 evidence used to freeze the policy

Ordinary DIAG3 evidence reported p99 force-distribution ratios of approximately `1.08` for `Frmse`, `1.02` for `Fp99`, and `0.90` for `Fp99.9`. Cross `Fmax` was `2.261e-5`, below the same-backend `2.337e-5` envelope, and cross selection identity was `100/100`. Under deterministic control, e3nn post-warm-up self comparisons became exactly zero while CuEq retained a force-noise envelope, supporting the interpretation of CuEq FP32 reduction variability rather than systematic backend disagreement.

## Scope

This criterion is only a TRAIN2 FP32 backend-equivalence authority. It does not alter scientific convergence tolerances, DATA8 acceptance, replay qualification, deployment parity, or FP64 parity.
