---
kind: numerical-evidence-analysis
protocol_version: 6.4.0
workplan: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN.md
stage: A
status: accepted-evidence
date: 2026-09-24
artifact_sha256: b3f08aeab0118d03364e1c33c3a9665c4a93c78a11d01c540a333bc50782f3be
artifact_content_sha256: f2bca742e8215bffb7299eef6f13e6d1378de3298e2c40760a4e70e66e7bea5d
artifact_schema: mdstats.stage-a-cueq-order-process-diagnostic.v1
foundation_family: mace_mpa_0
foundation_head: default
foundation_model_sha256: 75428afe3a1d7d8062e19bcaabd5c433623cabf308242ec9fb493e38604fb638
---

# TRAIN2 CuEq Stage-A MPA-0 fresh-process diagnostic analysis

## 1. Evidence integrity

The uploaded artifact is the predeclared cross-family MPA-0 realization of the same 20-process 2x2 construction/evaluation-order design used for MH-1.

All 20 child-process content digests and the aggregate canonical content digest recompute exactly. The evidence binds:

- MACE-MPA-0-medium / head `default`;
- locked model SHA-256 `75428afe3a1d7d8062e19bcaabd5c433623cabf308242ec9fb493e38604fb638`;
- the same three-structure corpus SHA used in the frozen diagnostic;
- CUDA / FP32;
- 20 fresh processes, 5 per factorial cell;
- 1 discarded warm-up and 3 retained pairs/process;
- no early stopping;
- ordinary nondeterministic settings;
- a clean mdstats repository at the recorded executable-source head.

The fresh process remains the independent experimental unit.

## 2. Force hierarchy

For process-mean force vectors:

| quantity | RMS |
| --- | ---: |
| e3nn fresh-process radius | 9.0134e-7 |
| CuEq fresh-process radius | 9.1972e-7 |
| backend centroid separation | 3.8643e-7 |
| backend separation / pooled process radius | 0.424 |
| all paired-output RMS discrepancy | 2.2614e-6 |

The stable backend centroid is therefore smaller than ordinary process-to-process variability.

Exact hierarchical variance decomposition of the paired force discrepancy gives:

- stable backend centroid: 2.92%;
- process-level differential state: 35.28%;
- within-process differential state: 61.80%.

The scalar per-process paired-force RMSE mean is `2.2216e-6` with process SD `2.1712e-7`.

By retained pair index the means are `2.1501e-6`, `2.1763e-6`, and `2.3383e-6`; this does not establish a monotone post-warm-up stabilization regime.

## 3. Cross-family stochastic structure

Against the identically designed MH-1 evidence:

| force quantity | MH-1 | MPA-0 | ratio |
| --- | ---: | ---: | ---: |
| e3nn process radius | 1.5945e-7 | 9.0134e-7 | 5.65 |
| CuEq process radius | 1.6520e-7 | 9.1972e-7 | 5.57 |
| centroid separation | 9.5935e-8 | 3.8643e-7 | 4.03 |
| paired RMS discrepancy | 4.0393e-7 | 2.2614e-6 | 5.60 |
| normalized centroid separation | 0.591 | 0.424 | — |

The absolute scale is family dependent by roughly a factor of 5-6. The normalized relation is not.

The paired RMS / pooled fresh-process radius is approximately:

- MH-1: `2.49` using the exact hierarchical paired RMS;
- MPA-0: `2.48`.

This is close to `sqrt(6)` for three retained observations/process and is consistent with paired instantaneous differences being dominated by realization-level stochastic arithmetic rather than a deterministic backend displacement.

The factorial decomposition is similarly stable across families:

| source | MH-1 | MPA-0 |
| --- | ---: | ---: |
| construction order | 5.41% | 6.88% |
| evaluation order | 4.96% | 5.53% |
| construction x evaluation | 5.23% | 8.25% |
| replicate/time block | 20.63% | 16.86% |
| residual process state | 63.77% | 62.48% |

This is strong evidence for a shared stochastic **form** while simultaneously falsifying one generic absolute microscopic tolerance.

## 4. Energy: the fixed `1e-6` stable floor is not generic

MPA-0 energy discrepancies occur on discrete FP32-scale levels.

Within the 20-process realization:

- e3nn-self maximum never exceeds `7.6294e-7`;
- CuEq-self reaches `1.5259e-6`;
- cross reaches `1.5259e-6`;
- 5/60 CuEq-self pair maxima exceed `1e-6`;
- 25/180 cross pair maxima exceed `1e-6`;
- 8/60 same-index paired maxima exceed `1e-6`.

Thus a cross-backend `1e-6` energy maximum cannot be called a generic stable-channel equivalence bound when ordinary CuEq self-repeatability crosses the same line.

The process-level energy backend-centroid RMS is `3.6780e-7`. It is small absolutely but larger than each backend process radius, which shows why noise-relative significance and scientific/material significance must be distinct coordinates.

## 5. Stress

Stress remains well behaved:

- all observed self/cross pair maxima remain below `1e-6`;
- backend centroid RMS is `2.1605e-8`;
- centroid variance contributes only about 1.8% of paired stress discrepancy variance.

No stress-specific numerical change is justified by this evidence.

## 6. Descriptor semantics

For flattened descriptors:

- e3nn process radius: `1.7043e-8`;
- CuEq process radius: `1.7052e-8`;
- backend centroid separation: `4.1138e-8`;
- normalized separation: `2.413`.

The systematic latent-coordinate representation shift is therefore stronger, relative to process variability, than for MH-1.

Nevertheless the complete three-structure inter-descriptor distance ordering is exactly the same for e3nn and CuEq in 20/20 same-process comparisons. The minimum ranking margins are orders of magnitude larger than the backend perturbations.

The numerical implication is not “ignore descriptors.” It is that raw latent coordinate equality is not the protected quantity. The D2 relation must protect the descriptor geometry / selection consequence actually consumed downstream.

## 7. Force extremes and the `1e-5` diagnostic

Across within-process comparisons, force components above `1e-5` occur in:

- e3nn-self: 2 / 2700;
- CuEq-self: 2 / 2700;
- all cross: 5 / 8100;
- same-index paired cross: 3 / 2700.

Therefore `abs(delta F) > 1e-5` is not a valid standalone backend-failure predicate in this MPA-0 regime.

The tail metrics remain extremely redundant:

- paired `corr(Fp99,Fp99.9) = 0.99979`;
- paired `corr(Fp99.9,Fmax) = 0.99979`;
- paired p99.9 is therefore again almost an interpolated maximum at 45 force components.

A catastrophic guard should be self-repeatability-aware and semantically distinct from the ordinary stochastic-equivalence estimator.

## 8. Stage-A conclusion

The MPA-0 evidence does not justify a model-family-specific exception. It instead strengthens a generic diagnosis:

1. absolute stochastic scale is model dependent;
2. stable backend bias is smaller than stochastic force spread in both families;
3. construction/order/process effects have similar fractional structure across families;
4. fixed `1e-6` stable-channel maxima are not generic even for energy;
5. descriptor coordinate maxima are not decision-level semantics;
6. multiple force-tail order statistics are redundant and finite-sample fragile;
7. threshold-only repair of Rev86 would preserve the wrong estimator structure.

Gate A is therefore complete. Stage B may define one bounded family-generic stochastic relation and then require fresh independent Stage-C evidence to test it.
