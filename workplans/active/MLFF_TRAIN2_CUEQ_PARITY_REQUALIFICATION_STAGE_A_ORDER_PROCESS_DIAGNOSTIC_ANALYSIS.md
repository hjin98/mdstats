---
kind: numerical-evidence-analysis
protocol_version: 6.4.0
workplan: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN.md
stage: A
status: accepted-evidence
date: 2026-09-24
artifact_sha256: 8f9df123b2ca5b055a7f1a82b3c819263021da52b005904af2f3f5df21acc056
artifact_content_sha256: 880261c2eabd33beeadcefe54eefea01e6acdc3d94e574c657dd3bee78cf570a
artifact_schema: mdstats.stage-a-cueq-order-process-diagnostic.v1
---

# TRAIN2 CuEq Stage-A fresh-process/order diagnostic analysis

## 1. Purpose

This diagnostic was frozen before execution to answer one question:

> Is the apparent backend-centered discrepancy stable across fresh processes and backend construction/evaluation order, or is a material part of the observed cross distribution process/order covariance?

It is evidence for D2 method design. It is not itself an acceptance rule.

## 2. Evidence integrity and design

The artifact canonical content digest recomputes exactly, and all 20 child-process content digests recompute exactly.

The design is balanced:

- construction order: e3nn-first / CuEq-first;
- evaluation order: e3nn-first / CuEq-first;
- 5 fresh processes per 2x2 cell;
- 20 fresh processes total;
- 1 discarded warm-up pair/process;
- 3 retained paired evaluations/process;
- no early stopping;
- ordinary nondeterministic settings;
- one exact checkpoint, config, corpus, GPU and repository identity.

The independent experimental unit for process/order conclusions is the **fresh process**. The 60 retained pairs are nested observations and are not treated as 60 independent processes.

## 3. Force: systematic backend component exists but is not dominant

Averaging the three retained outputs inside each process and comparing the 20 process means gives:

| quantity | RMS scale |
|---|---:|
| e3nn process radius about e3nn centroid | 1.5945e-7 |
| CuEq process radius about CuEq centroid | 1.6520e-7 |
| backend centroid separation | 9.5935e-8 |
| all cross-process e3nn/CuEq RMS distance | 2.4883e-7 |

The backend centroid separation is only `0.591` times the pooled backend process radius.

This revises the earlier single-process all-pairs inference. The first snapshot implied a force-centroid separation near `2.05e-7`; after fresh-process counterbalancing, the stable grand centroid separation is about half that value.

Therefore:

- there is evidence of a nonzero backend-centered force component;
- it is not large relative to fresh-process variability;
- it cannot be treated as a clean deterministic backend bias without representing process/order uncertainty.

## 4. Force: order/process covariance is material

For the signed 45-component process-mean force-difference vector, balanced factorial decomposition of centered process variation gives approximately:

| source | fraction of centered variation |
|---|---:|
| calculator construction order | 5.41% |
| evaluation order | 4.96% |
| construction x evaluation interaction | 5.23% |
| replicate block / temporal state | 20.63% |
| remaining process variation | 63.77% |

The four cell-mean backend-difference vectors are not collinear. Pairwise cosines are approximately:

`0.287, 0.338, 0.367, 0.337, 0.332, 0.442`.

Thus the direction of the signed backend discrepancy changes materially with the execution condition. The current one-process all-pairs diagnostic cannot identify a unique backend-offset direction independently of process/order state.

This does not prove that construction or evaluation order is the sole cause; most process variation remains residual. It proves that order/process covariance is large enough that the current all-pairs reducer is not an adequate stochastic model.

## 5. Scalar paired force discrepancy

Per-process mean paired force RMSE:

| construction | evaluation | mean RMSE |
|---|---|---:|
| e3nn-first | e3nn-first | 4.1331e-7 |
| e3nn-first | CuEq-first | 3.9159e-7 |
| CuEq-first | e3nn-first | 3.8706e-7 |
| CuEq-first | CuEq-first | 4.0871e-7 |

Grand mean: `4.0017e-7`.

The scalar discrepancy shows almost no standalone evaluation-order main effect. The dominant designed effect is interaction: when the backend constructed first is also evaluated first, discrepancy is roughly 5% larger than in crossed-order cells. Process residual variation remains dominant.

The corresponding grand process means remain well below the historical `1e-5` force-component catastrophic guard.

## 6. Retained-pair / warm-up sensitivity

Mean paired force RMSE by retained pair index is:

- pair 0: `3.9480e-7`;
- pair 1: `3.9855e-7`;
- pair 2: `4.0715e-7`.

The pair-to-pair mean changes are small relative to process scatter, and no monotonic stabilization pattern is established. Similar non-monotonic behavior occurs for descriptor/stress maxima.

The evidence therefore does not support increasing warm-up count merely to obtain a preferred classification.

## 7. Descriptor channel: systematic representation shift, stable coarse geometry

For the complete flattened descriptor vector:

- e3nn process radius: `3.9441e-8`;
- CuEq process radius: `3.8508e-8`;
- backend centroid separation: `4.4812e-8`;
- separation / pooled process radius: `1.150`.

Per structure, separation / pooled process radius is approximately:

- structure 0: `1.370`;
- structure 1: `1.242`;
- structure 2: `0.741`.

So the descriptor difference is not adequately described as stochastic repeatability alone.

However, the inter-structure descriptor geometry is extremely stable. Across all 20 process-mean realizations on both backends:

- structures 0 and 2 are always the closest pair;
- structures 1 and 2 are always the farthest pair;
- the complete three-pair distance ranking agrees between backends in 20/20 same-process comparisons.

Therefore the evidence supports a semantic split:

- raw latent-coordinate absolute maximum is not a portable physical error metric;
- descriptor geometry/selection consequence is the relevant governed object;
- a replacement D2 relation must protect that consequence explicitly rather than retain the current arbitrary `1e-6` latent maximum.

## 8. Energy and stress

Energy and stress remain microscopic. One factorial cell produces bitwise-identical paired energies across the retained sample, while other cells show single-precision-scale differences. This is additional evidence that low-level reduction/initialization state affects exact arithmetic, but no material energy/stress failure is established.

Stress paired maxima remain of order `1e-8`.

## 9. Numerical conclusion

The fresh-process diagnostic closes the Stage-A process/order question:

1. the earlier apparent force backend offset is partly real but was overstated by a single-process all-pairs interpretation;
2. fresh-process stochastic variation is larger than the stable force centroid separation;
3. construction/evaluation condition changes the signed discrepancy materially, including its direction;
4. the current all-pairs cross/self tail-ratio reducer therefore conflates backend effect, process state, order state and finite-sample extremes;
5. descriptor outputs contain a systematic representation shift, but the coarse descriptor geometry relevant to selection is stable on this smoke corpus;
6. no evidence supports a threshold-only repair.

## 10. D2 consequence

Stage B should not attempt to repair Rev86 by choosing a new ratio ceiling.

The replacement method must separate:

- a **systematic backend discrepancy** estimator;
- a **fresh-process stochastic/repeatability** scale;
- an **absolute catastrophic/materiality guard**;
- **discrete decision/geometry preservation** where descriptors are proxies for selection;
- the applicability domain over model family, checkpoint/model state, runtime and precision.

The routine doctor need not reproduce the full 20-process qualification experiment. The 20-process design is qualification evidence for defining/validating the method. D3 should prefer a cheaper runtime smoke once D2 establishes what that smoke must prove.

## 11. Remaining cross-family evidence

The current executable TRAIN2 parity policy is generic across the supported model families, but raw current target-host evidence now exists only for MH-1.

The original MPA-0 workstation evidence survives only as secondary summaries/test constants. Therefore Gate A remains open until a fresh MPA-0 realization is obtained under this same frozen process/order design or until stakeholder-authorized D2 scope is explicitly narrowed before candidate formulation.

No family-specific magic threshold should be created merely to avoid this obligation.
