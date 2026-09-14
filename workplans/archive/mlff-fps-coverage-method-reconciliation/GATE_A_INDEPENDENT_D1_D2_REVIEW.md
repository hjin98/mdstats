# Gate A independent D1/D2 review — FPS/coverage target-order candidate

Date: 2026-09-13
Reviewed candidate: `GATE_A_D1_D2_FPS_COVERAGE_METHOD_CANDIDATE.md` at commit `cc55be388fa8ab6dd0641eeefc3b914bfcaefe0f`
Workplan: `MLFF-FPS-COVERAGE-METHOD-RECONCILIATION-1`
Protocol: SSDP 6.3
Disposition: **NO PASS FOR PROMOTION**

## 1. Challenge disposition

The candidate is directionally sound in four important respects: it removes lexical UID ordering as scientific priority, preserves one exact nested training order, keeps coverage diagnostics soft, and avoids reviving the retired FEAS/MVIDX/MVSEL/REPAIR/MVQUAL topology. However, promotion is blocked because the proposed D1/D2 contract is not yet internally closed. Several descendants can satisfy the present text while implementing scientifically or numerically different experiments.

This is not a rejection of the coverage-progressive target-order concept. It is a request to repair the owning D1/D2 semantics before they become current authority.

## 2. Blocking findings

### B1 — `mu_eval` and the proposed `pi_eval` allocation optimize different measures

D1 correctly states that the current EVAL2 estimand is force-component RMSE:

```text
R_M3 = sqrt(sum_x SSE_x / sum_x (3 n_x))
```

where a frame with `n_x` atoms contributes `3 n_x` Cartesian force components. D2 then allocates the nested evaluation prefixes by **frame-count** condition mass `N_c / |M3|` and explicitly retains the unweighted EVAL2 reduction.

Those are equivalent only when relevant frame atom counts are equal. In heterogeneous-composition/size data, early prefixes can track frame proportions while badly misrepresenting the force-component estimand.

Counterexample: one condition contains one 100-atom frame and another contains ten 1-atom frames. Full-M3 EVAL2 component mass is about 91% in the first condition, but the proposed frame-count scheduler initially assigns almost all early ranks to the ten-frame condition. The claimed “same estimand at increasing resolution” is therefore false under an admissible current dataset.

**Required repair:** D1 must define `mu_eval` in the same measure actually estimated by EVAL2. D2 must then either (a) construct nested evaluation prefixes against force-component mass, with a frame-level deterministic allocation rule that approximates that measure, or (b) introduce explicitly accepted evaluation weights/estimator semantics. Frame-count proportionality cannot be described as preserving the current component-weighted EVAL2 estimand.

### B2 — `pi_eval` has no accepted approximation/error semantics beyond condition proportions

Even after correcting component mass, deterministic SHA-based within-condition order has no stated approximation guarantee, discrepancy bound, sampling-uncertainty interpretation, or structural/correlation balancing requirement. A legal hash realization can delay an important within-condition structural subpopulation until late while all condition proportions remain perfect.

D1 says `M1/M2` are increasing-resolution approximations to the same M3 model-selection estimand. D2 therefore needs an explicit adequacy statement for those approximations. A deterministic pseudo-random-looking permutation is not by itself an error model.

**Required repair:** choose and state one of these scientific meanings explicitly:

- a probability-sampling interpretation with a defined finite-population sampling design, deterministic seed construction, and numerical uncertainty/adequacy route; or
- a deterministic balanced-design interpretation with explicit balance variables and discrepancy or calibration oracles.

Protected/correlation units must also be adjudicated: either balance them because estimator variance/correlation materially matters, or state why they are intentionally diagnostic-only.

### B3 — the `P_train/M3` split still lacks a scientific allocation objective

Historical accepted target-size design states that training support has priority and that M3 should preferentially consume redundant residual support while retaining useful representative/condition coverage subject to exact feasibility and protected disjointness. The current implementation is deterministic exact subset-sum with ordering-dependent first-predecessor selection; the candidate changes the tie identity but explicitly leaves the scientific allocation objective unchanged.

Replacing lexical UID with `kappa` removes one arbitrary spelling dependence but does not make two scientifically different exact-feasible splits scientifically equivalent. `kappa` is still a deterministic tie-breaker, not a rule for identifying redundant residual support.

**Required repair:** D1 must either explicitly retire/narrow the historical “redundant residual support / preserve representative coverage” requirement with rationale, or retain it and define a pre-split objective that can be evaluated without circular P_train-only fitting. If retained, D2 needs an exact-feasibility-preserving deterministic allocation objective and a counterexample where two feasible M3 subsets have different accepted support quality.

### B4 — `mu_train` is not reconciled with the actual fixed training objective

The candidate defines `mu_train` as equal mass per P_train frame and schedules condition counts toward empirical frame frequency. The accepted common training method can apply fitted per-configuration weights, including condition equalization/bounds/multipliers, and candidate projection preserves those P_train-fitted weights.

Thus “representing the training population” and “representing the optimization influence measure” are not necessarily the same object. The candidate does not state which one the coverage-progressive membership is meant to approximate, or why empirical-frame membership is the correct design when the frozen training loss may deliberately reweight conditions.

**Required repair:** D1 must distinguish the **selection/support measure** from the **training-loss influence measure** and state whether alignment is required. If equal-frame `mu_train` remains correct, explain why the existing configuration-weight policy does not invalidate the target-size interpretation. D2 must bind the appropriate weight-policy identity if it materially constrains that interpretation.

### B5 — the fitted metric contains material unratified weighting choices

The proposed metric fixes: raw-geometry block + universal-structural block, equal block weights, coordinate-wise robust scaling, missing indicators, and `1/sqrt(d_b)` block normalization. These choices directly alter medoids, FPS order, every `T_N`, and all coverage diagnostics.

The author-side two-dimensional fixture does not falsify these real metric choices. In particular, equal block weighting and dimension normalization are not scientifically justified, and correlated/redundant coordinates inside the structural block can still dominate particular physical degrees of freedom after `1/sqrt(d_b)` normalization. Likewise, excluding profile/environment evidence can lose the historical capability to preserve rare local environments even when frame-aggregate structural descriptors look similar.

**Required repair:** D1 must state whether the target claim is only frame-level geometric coverage or includes rare/local environment coverage. D2 must justify the chosen block/coordinate weighting against that D1 claim and add sensitivity/counterexample evidence using the actual proposed feature families. Do not promote equal weighting merely because it is simple.

### B6 — numerical identity is not reconstructible enough for D2 authority

Several order-changing operations remain under-specified:

1. median/Q25/Q75 do not specify the quantile/interpolation convention;
2. centroid accumulation does not specify a deterministic reduction order or equivalent reproducibility rule, despite input-enumeration invariance being required;
3. the proportional-deficit scheduler is written in floating point even though an exact integer comparison is available;
4. `sha256(canonical(...))` does not name the exact canonical byte/semantic encoding owner;
5. the same `1e-12 * max(1, |s*|)` tolerance is used as a generic tie/degeneracy rule without a conditioning/roundoff derivation for medoid, distance, and scale calculations.

Different legitimate implementations can therefore produce different membership while claiming D2 conformance.

**Required repair:** freeze the quantile convention, deterministic reduction/equivalence semantics, exact deficit comparison (prefer integer cross-products), canonical digest serialization owner, and separately justified numerical tolerances. Tolerances must come from accepted finite-precision/error semantics, not convenience.

## 3. Important nonblocking-but-required closure gaps

### G1 — unconditional condition anchors need explicit authority classification

The candidate says only explicit `hard_support_obligations` gate prefixes, yet it also makes the study method-infeasible when `N_min` is below the number of P_train conditions. That is a legitimate method-level invariant, but it must be named as such so it is not confused with optional hard qualification.

### G2 — correlation/protected-relation ordering role is decided but not justified

The authorization matrix marks correlation/protected relations as diagnostic for `pi_train/pi_eval` after the split. This is a substantive choice because repeated highly correlated frames can dominate raw cardinality without adding comparable independent information. The revised D1 should explain why target-size `N` intentionally counts configurations rather than effective independent units, and D2 should report correlation-balance diagnostics if they remain non-governing.

### G3 — `kappa` invariance scope is narrower than the stated scientific invariance goal

`kappa` removes dependence on frame-UID spelling but includes source identity signature and source frame index. The revised method should state whether scientifically equivalent source repackaging/relocation is expected to preserve ordering. If yes, `kappa` needs a more semantic occurrence identity; if no, the limitation belongs in D1/D2 validity/currentness semantics.

### G4 — old-generation invalidation needs an exact dependency impact map before acceptance

The candidate correctly says old empty-evidence generations become historical. Before promotion, identify which persisted target-order-dependent artifacts become stale (`aggregate`, orders, T_N/M_i, screen/reducer/provisional/frozen/CV/production descendants as applicable) and which unrelated source/P1/common-training evidence remains valid. Do not invalidate more than dependency requires, but do not leave target-order descendants current.

## 4. Evidence review

The author-side bounded fixture is useful but insufficient for Gate A promotion. It demonstrates that the proposed **interleaving concept** can outperform UID, representative-only, difficulty-only, and pure global FPS on one equal-frame synthetic geometry. It does not exercise variable atom counts, actual raw/universal feature blocks, protected/correlation components, split alternatives, quantile conventions, floating-point tie sensitivity, evaluation estimand error, or real producer lineage.

The independent re-review must include at least:

1. variable-atom-count EVAL2 counterexample/reference;
2. within-condition heterogeneous-error evaluation fixture;
3. two exact-feasible M3 split alternatives with materially different support quality if that D1 requirement is retained;
4. real feature-block sensitivity/ablation and a rare-local-environment counterexample;
5. quantile/reduction/tolerance differential tests;
6. UID renaming plus source/input enumeration metamorphic checks;
7. direct simple-reference FPS/medoid/coverage scorer;
8. stale old-generation rejection and bounded dependent-impact checks;
9. CPU/resource evidence with the real structural provider and expected `K=max(N)` scale.

## 5. Promotion decision

**NO PASS. Do not promote this candidate into the permanent D1/D2 method papers yet.**

The revised Gate A package should preserve the current strengths—single exact order owner, exact nested prefixes, soft/hard separation, no foundation/GPU prerequisite, no retired selector topology—but repair B1–B6 at the owning layer. After that, perform a fresh independent D1/D2 Challenge pass. Human ratification should occur only on that revised, reviewed contract, not on `cc55be388fa8ab6dd0641eeefc3b914bfcaefe0f`.