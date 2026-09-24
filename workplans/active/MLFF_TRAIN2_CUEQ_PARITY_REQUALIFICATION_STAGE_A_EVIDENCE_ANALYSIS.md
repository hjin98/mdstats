---
kind: numerical-evidence-analysis
protocol_version: 6.4.0
workplan: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN.md
stage: A
status: evidence-accepted-diagnostics-open
date: 2026-09-24
snapshot_sha256: ef0e4d8c2d0b867294a97b86769a1e1fd709c1af9e35d1a1c7730bb936a6dd83
snapshot_schema: mdstats.stage-a-cueq-parity-evidence-snapshot.v1
---

# MLFF TRAIN2 CuEq parity requalification — Stage A evidence analysis

## 1. Evidence identity and authenticity

The imported target-host snapshot records one failed doctor realization on the stakeholder's RTX 3090 system. Canonical mdstats digest recomputation succeeds for every checked content-addressed record and parity/acceleration policy.

Material identities:

- selected-head qualification digest: `66867d6b08fc8af279c2f5e449168afa148d2f43aaa6fd745ae4524025c62244`;
- selected-head checkpoint SHA-256: `61c83c377dae92bf37c5412a263687237fbc4b9790828868ec0887cc992be928`;
- repeatability diagnostic digest: `66be5bdcc4e660067d6c7801a1fb3083ff634f21a48e919a6fb1199c2d9dedfa`;
- noise-normalized parity record digest: `7dc24d6f0201d34258cfbbfe15c507fb648a2c00b07aff57a6ed202f456c810f`;
- failed TRAIN2 realization digest: `9767ce3f3816deb1e19bfed330877401735380c3051db7324529f1e33ab7430b`;
- active noise-normalized parity-policy digest: `1faf33e781142ff0656cc6a49235294858dfe5dc7639c08e7a5e0f1fc73ed0d5`.

The realization is MACE 0.3.16 / Torch 2.13.0+cu126 / CUDA 12.6 / CuEq 0.10.0 / FP32 / `cueq_pure`. The MACE source-byte mismatch is not silently ignored: the stored runtime-freeze record carries the semantic compatibility pass.

## 2. Experimental geometry

The diagnostic contains:

- 1 discarded warm-up/backend;
- 10 retained evaluations/backend;
- 45 e3nn self pairs;
- 45 CuEq self pairs;
- 100 cross pairs;
- 3 structures / 15 atoms total;
- 45 force components per pair;
- ordinary nondeterministic production settings.

The 45/45/100 pair metrics are functions of only 20 retained backend outputs and are not 190 independent realizations.

## 3. Descriptor channel falsifies the fixed absolute-floor interpretation

For descriptor maximum absolute difference:

| set | p99 | max | fraction above `1e-6` |
|---|---:|---:|---:|
| e3nn self | 1.7395e-6 | 1.9073e-6 | 20/45 = 44.4% |
| CuEq self | 1.7700e-6 | 1.8120e-6 | 22/45 = 48.9% |
| cross | 2.1467e-6 | 2.2411e-6 | 70/100 = 70.0% |

The cross maximum is only 1.175 times the larger same-backend maximum. The cross p99 is 1.213 times the larger same-backend p99.

Therefore the current `stable_channel_abs_ceiling=1e-6` is not a valid discriminator between backend disagreement and ordinary repeatability for this latent descriptor representation: it rejects nearly half of same-backend pairwise maxima.

This does **not** by itself prove that descriptor parity should be removed. It proves that a raw unnormalized `1e-6` maximum is inadequately justified for this representation. D2 must either normalize descriptor error to an accepted repeatability/scale model or connect a descriptor perturbation bound directly to the protected downstream selection/neighbor decision.

## 4. Energy and stress do not show the same pathology

Energy:

- larger same-backend maximum: 8.5831e-7;
- cross maximum: 7.6294e-7;
- cross/self-max ratio: 0.889.

Stress:

- larger same-backend maximum: 7.8909e-8;
- cross maximum: 7.2130e-8;
- cross/self-max ratio: 0.914.

The observed cross discrepancy is no larger than ordinary same-backend maxima for these channels. Their current pass is therefore not implicated by the descriptor counterexample.

## 5. Force-tail ratio classification is finite-sample sensitive

Current authorizing values:

- `Frmse` p99 cross/self ratio = 1.153 — pass;
- `Fp99` p99 cross/self ratio = 1.266 — fail against 1.25;
- `Fp99.9` p99 cross/self ratio = 1.270 — fail against 1.25;
- `Fmax` = 2.6226e-6 under active limit 2.8610e-6 — pass;
- no force component exceeds `1e-5`.

Delete-one **paired-run sensitivity** (retain 9 of the 10 e3nn/CuEq run indices and recompute the exact current reducer):

| metric | min ratio | median | max | subsets above 1.25 |
|---|---:|---:|---:|---:|
| Frmse | 1.124 | 1.148 | 1.188 | 0/10 |
| Fp99 | 1.157 | 1.304 | 1.352 | 8/10 |
| Fp99.9 | 1.078 | 1.288 | 1.346 | 7/10 |

Delete-two sensitivity (retain 8 of 10; 45 possible retained-index subsets):

| metric | min ratio | median | max | subsets above 1.25 |
|---|---:|---:|---:|---:|
| Frmse | 1.054 | 1.144 | 1.262 | 1/45 |
| Fp99 | 1.091 | 1.337 | 1.421 | 29/45 |
| Fp99.9 | 1.034 | 1.304 | 1.618 | 30/45 |

These are **sensitivity analyses**, not confidence intervals or probabilities. They show that the hard 1.25 verdict for the two tail ratios is not classification-stable at the frozen ten-repeat cardinality.

## 6. `Fp99.9` is nearly a duplicate of `Fmax` at this corpus size

Each pair contains only 45 force components. NumPy's default linear percentile for q=99.9 uses index

`(45 - 1) * 0.999 = 43.956`,

so the result is approximately 95.6% of the largest component plus 4.4% of the second largest component. It is not an independently resolved 0.1% population tail.

Across the 100 cross pairs, Pearson correlations are:

- `corr(Fmax, Fp99.9) = 0.999812`;
- `corr(Fmax, Fp99) = 0.966513`;
- `corr(Fp99.9, Fp99) = 0.971311`.

The current rule therefore applies multiple strongly correlated extreme-force gates to a very small component corpus. D2 should retain only metrics with distinct protected meaning and adequate finite-sample resolution.

## 7. Fixed evaluation order materially affects the cross statistic

The production diagnostic evaluates e3nn then CuEq on every retained run. When only same-index cross pairs `(e3nn_i, CuEq_i)` are examined, their p99 relative to the same self envelopes is:

- `Frmse`: 1.157;
- `Fp99`: 1.183;
- `Fp99.9`: 1.004;
- descriptor Dmax: 1.080.

All are below 1.25, whereas the all-pairs `Fp99` and `Fp99.9` ratios fail.

The same-index result is **not** adopted as the replacement authority: adjacent e3nn->CuEq evaluations can share temporal/process state and are not order-counterbalanced. The result instead proves that pairing/order/process covariance is material enough that a fresh-process reversed-order diagnostic is required before D2 chooses an estimator.

## 8. Force RMSE geometry separates systematic offset from stochastic spread

Because force RMSE is Euclidean distance divided by `sqrt(45)`, the complete 45/45/100 self/cross RMSE arrays define the exact pairwise distance geometry of the 20 retained force-output vectors.

Distance decomposition gives:

- e3nn within-backend RMS radius about its centroid: 2.6375e-7;
- CuEq within-backend RMS radius: 2.5626e-7;
- cross-pair RMS distance: 4.2081e-7;
- inferred RMS distance between backend centroids: 2.0456e-7;
- centroid separation / pooled within-backend RMS radius: 0.787;
- centroid separation / cross-pair RMS distance: 0.486.

Thus CuEq is **not noisier than e3nn** in force RMSE for this realization; its within-backend radius is slightly smaller. The cross cloud nevertheless contains a small systematic backend-centered offset.

This is the key conceptual defect in the current reducer: a cross/self tail ratio mixes systematic backend bias, ordinary stochastic spread, finite-sample extreme behavior and pair dependence into one threshold. D2 should represent systematic offset and stochastic repeatability as distinct quantities, with an independent absolute/materiality guard.

No inferential p-value is claimed from these 20 dependent sequential evaluations.

## 9. Decision-level evidence remains benign on the smoke corpus

- cross FPS selection identity: 100/100;
- e3nn self selection identity: 45/45;
- CuEq self selection identity: 45/45;
- force components above `1e-5`: 0 in all cross and self pairs.

This substantially weakens the claim that the observed microscopic discrepancy already changed the governed selection decision on the doctor corpus. It does not establish robustness outside that three-structure smoke corpus.

## 10. Stage-A numerical conclusion

The imported evidence confirms the Serious Challenge and narrows it:

1. **descriptor failure:** current absolute latent-space maximum is not normalized to its own same-backend repeatability;
2. **force-tail failure:** current p99-of-pairwise-tail ratios are finite-sample unstable and heavily redundant with Fmax;
3. **backend effect:** a small systematic force-output centroid separation appears to exist, so simply declaring the failure “noise” would also be wrong;
4. **method requirement:** the replacement must separate systematic backend offset, stochastic repeatability, absolute catastrophic error and discrete decision preservation.

The evidence does **not** authorize raising `1.25`, raising `1e-6`, deleting all force-tail checks, or accepting this CuEq realization.

## 11. Frozen next evidence question

Before Stage B is allowed to choose its numerical relation, run one bounded target-host diagnostic whose sole purpose is to answer:

> Is the measured backend-centered offset stable across fresh processes and evaluation order, and what part of the observed cross distribution is ordinary within-backend stochastic spread versus order/process covariance?

The diagnostic must be predeclared, must retain per-evaluation outputs or sufficient signed summaries, and must not stop early when a desired outcome appears.

A fresh MPA-0 realization remains mandatory before claiming a generic MPA-0/MH-1 D2 relation.
