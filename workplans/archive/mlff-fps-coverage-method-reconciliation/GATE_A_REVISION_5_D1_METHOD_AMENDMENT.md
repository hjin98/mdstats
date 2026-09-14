# Gate A Revision 5 — proposed D1 method-paper amendment

Date: 2026-09-13
Workplan: `MLFF_FPS_COVERAGE_METHOD_RECONCILIATION_AND_ORDERING_CONFORMANCE_WORKPLAN.md`
Candidate: `GATE_A_D1_D2_FPS_COVERAGE_METHOD_CANDIDATE.md`, Revision 5
Target owner: `docs/methods/mlff_scientific_method.md`
Lifecycle: **PROPOSED — not accepted current D1 authority**

## 1. Purpose and application rule

This file is the exact Gate-A D1 amendment overlay for the current MLFF Scientific Method Paper. It exists so a separate-context reviewer can reconstruct the would-be permanent D1 without reverse-engineering the combined Gate-A candidate or implementation.

Until Gate A passes and the human owner ratifies Revision 5, `docs/methods/mlff_scientific_method.md` remains the accepted current D1 authority. No sentence in this overlay is current merely because it is committed on the design branch.

At promotion, apply only the replacements below. Every D1 section and sentence not named here is preserved byte-for-byte except mechanically necessary heading/cross-reference adjustments. If a later accepted review requires a semantic change, revise the owning Gate-A candidate first rather than patching this overlay independently.

## 2. Authority metadata after acceptance

On accepted promotion, retain the existing paper identity and reconstruction provenance, and append the Gate-A reconciliation provenance rather than erasing the 2026-09-13 reconstruction history. The authority paragraph must state that the target-order reconciliation was independently reviewed and human-ratified under workplan `MLFF-FPS-COVERAGE-METHOD-RECONCILIATION-1`; it must not claim that the original reconstruction review already covered this later correction.

## 3. Replace Section 2.3 final paragraph

Replace the paragraph beginning `The current method therefore uses...` with:

> The target-size experiment therefore uses one deterministic training order, exact nested training prefixes, one fixed exact model-selection reserve `M3`, common candidate-independent training preparation, paired optimizer seeds, and an explicit short-horizon comparison policy. Every automatic fidelity boundary evaluates the same exact `M3` target-force estimand. Smaller nested `M1/M2` populations may exist only as diagnostic probability samples and have no ranking, elimination, qualification, tie-break, recommendation, or freeze authority. The automatic screen is a diagnostic that recommends a size. The operator remains responsible for the provisional downstream design, and post-selection cross-validation evaluates that frozen design rather than feeding backward into it.

## 4. Amend Section 4.4 evidence-role statement

Replace the sentence

> The target-size `M1/M2/M3` populations are **development/model-selection evidence**, not post-selection held-out CV and not locked final tests.

with:

> The exact `M3` reserve is target-size development/model-selection evidence, not post-selection held-out cross-validation (CV) and not a locked final test. `M1/M2` are nested diagnostic probability samples of `M3`; they may characterize evaluation-sampling behavior but cannot make target-size decisions.

## 5. Replace Section 5.1 — pre-order selection evidence

Use:

### 5.1 Pre-order selection evidence

The baseline target-order method uses only candidate-independent evidence whose scientific meaning is fixed before target-size candidate training:

- canonical neutral condition/provenance evidence;
- universal frame-level cell geometry;
- universal strain coordinates where they are scientifically defined; and
- material-neutral, element-resolved frame summaries of the accepted universal local-structure feature contract.

These inputs define one target-order metric and one order owner. Mass density, material/profile-specific pair-rule coordinates, profile-declared atom groups or site classes, material-specific event descriptors, foundation-model predictions/descriptors, and label-derived residual/difficulty are not baseline membership coordinates.

Fitted target-order transforms obey their authorized domain: pre-split redundancy evidence is fitted only on exact `U_size`; post-split training-order evidence is refitted only on exact `P_train`. `M3` labels and candidate outcomes fit neither metric. Candidate-independent evidence does not create a second selector or per-candidate order.

## 6. Replace Section 6 in full

Replace current Sections 6.1–6.8 with the following present-state D1 contract.

## 6. Target-size scientific experiment

### 6.1 Population, measures, and exact development split

The target-size population `U_size` contains currently eligible, canonically labeled frames from the neutral **development** role. Physical-only frames without the required canonical training labels do not enter the target-size training experiment.

Three measures are intentionally distinct:

- **selection/support measure `mu_sel`** — every exact `P_train` configuration has equal membership mass; target size counts configurations rather than loss weight or effective independent samples;
- **training-loss influence measure `mu_loss`** — accepted common per-configuration weights, property masks, and global objective coefficients may be fitted once over exact `P_train` and projected unchanged to every `T_N`, but do not choose membership; and
- **evaluation estimand `mu_eval`** — exact `M3` owns the target-force component-weighted EVAL2 estimand.

No equality among these measures is assumed.

`U_size` is split exactly once into `P_train` and `M3`. Every inherited split-excluding/protected relation component is indivisible. A valid split must satisfy simultaneously:

```text
|M3| = m3
|P_train| >= N_max
count(P_train,c) >= 1 for every eligible neutral condition c
all protected components remain indivisible
```

Failure to satisfy these constraints exactly is a scientific split-infeasibility result; it is not permission to erase a condition, split a protected component, change `M3`, or relax exactness.

### 6.2 Training support and redundant residual reserve

Training support has priority. Among exact hard-feasible splits, neutral-condition depletion is minimized globally. Within globally condition-optimal exact completions, reserve construction preferentially removes structure that is redundant relative to the **currently retained** training population, and that redundancy is recomputed after every component removal.

Two components may therefore not permanently certify one another as redundant and then both disappear without rescoring the second after the first is removed. This retained-set criterion is not claimed to globally minimize final `P_train` covering radius; exact cardinality and protected-relation constraints may still force the loss of distinctive support, which remains visible in diagnostics.

### 6.3 Structural-support scope

The baseline target-order metric claims frame-level support across:

- universal cell geometry;
- universal strain coordinates where defined; and
- material-neutral element-resolved summaries of the accepted local-structure kernel.

It does not claim exhaustive coverage of every atomic environment, material-profile group, site class, or material-specific event. Mass density, material/profile pair-rule coordinates, declared material groups, phase-specific geometry plans, site classes, material-specific event descriptors, foundation predictions, and label-derived difficulty are excluded from baseline membership authority.

### 6.4 One canonical training order

One deterministic order

$$
\pi_{\mathrm{train}}=(x_1,x_2,\ldots,x_{|P_{\mathrm{train}}|})
$$

is constructed before candidate training. Every nonempty `P_train` neutral condition contributes one representative anchor before ordinary progression, so configured `N_min` must be at least the number of represented `P_train` conditions.

After anchors, selected condition counts track empirical `P_train` frame mass as closely as exact integer prefixes permit. Within each condition, exact farthest-point sampling (FPS) progressively expands the accepted frame-level structural support.

Candidate membership is exactly

$$
T_N=\pi_{\mathrm{train}}[:N].
$$

For `N_a<N_b`, the smaller candidate is a prefix of the larger candidate. There is no per-`N` rerun, swap, repair, or selector.

Only explicit accepted hard-support obligations may qualify/reject an exact prefix after order construction. FPS distances, retained-set redundancy scores, coverage diagnostics, event/environment summaries, correlation diagnostics, and diagnostic evaluation-sampling uncertainty remain soft evidence.

### 6.5 Exact `M3` decision population at every automatic fidelity boundary

The historical changing `M1/M2/M3` **decision** ladder is retired by this method.

At every configured automatic training-fidelity boundary, every active `(N, optimizer_seed)` candidate is evaluated on the same exact `M3` frame population. The reducer's practical-equivalence comparison, funnel elimination, configured-ceiling diagnostic, recommendation, and no-recommendation state consume only the exact `M3` target-force response.

Therefore the evaluation population does not change across automatic boundaries, and a candidate cannot be eliminated because of evaluation-subset sampling noise. The remaining controlled stochastic replicate dimension is the optimizer-seed population and training stochasticity rather than a random evaluation-population draw.

Training fidelity may still increase through the accepted continuous training trajectory; only the model-selection population remains fixed.

### 6.6 Diagnostic `M1/M2` probability samples

One persisted Fisher–Yates random permutation `pi_eval` over distinct `M3` frame occurrences may define nested diagnostic prefixes `M1` and `M2`. Under that randomization design the prefixes are simple random samples without replacement (SRSWOR) from the finite `M3` occurrence population.

They may diagnose finite-population sampling error, atom/component-mass discrepancy, condition/correlation discrepancy, and whether a smaller evaluation population might be adequate under some future separately accepted method.

`M1/M2` may not rank, eliminate, qualify, tie-break, recommend, select horizons, alter practical equivalence, or freeze target-size membership. Changing only the diagnostic permutation invalidates its diagnostic descendants but does not change target-size reducer evidence when exact `M3`, model state, and per-frame predictions are unchanged.

### 6.7 Primary target-size response

For a trained candidate `f`, let `SSE_x(f)` be the sum of squared target-force component errors for frame `x` and let

$$
C_x=3n_{\mathrm{atoms}}(x).
$$

The exact model-selection response is

$$
R_{M3}(f)=\sqrt{\frac{\sum_{x\in M3}SSE_x(f)}{\sum_{x\in M3}C_x}}.
$$

This is the exact target-force root-mean-square error (RMSE) over admitted Cartesian force components of `M3`; the current screen stores it in meV/Å. Energy and stress may remain part of training/checkpoint semantics but do not silently replace this ranking response.

### 6.8 Controlled stochastic replicate dimension and successive fidelity

The optimizer-seed set is explicit and common to all candidate sizes. A candidate score is formed only from a complete comparable seed population. A numerical failure is not silently discarded to improve the candidate mean.

A surviving `(N, seed)` trajectory continues through later fidelity boundaries with the same model/optimizer/random-number-generator lineage rather than restarting as an unrelated rung-local experiment. Every boundary evaluates exact `M3`.

The automatic stage therefore measures one configured short-horizon screening protocol. It is not a universal learning curve and cannot establish long-horizon or deployment behavior by itself.

### 6.9 Practical equivalence, configured ceiling, and operator decision

A configured practical-equivalence tolerance `epsilon` defines improvements too small to justify preferring a larger target dataset in the screen. Within the equivalence band, smaller `N` is preferred.

At the terminal comparison, if the largest configured candidate is materially superior to every other successful finalist by more than `epsilon`, it remains the best tested permitted size and is recommended while recording that a plateau was not demonstrated inside the configured ladder. The configured ceiling is a budget boundary, not an asymptotic-convergence claim.

If too few complete comparable candidates remain, the automatic result is no recommendation. The operator owns the provisional downstream design and may accept, ignore, or override a recommendation within the qualified configured candidate set, including selecting multiple sizes for a comparative downstream experiment. `cross-validate` admission remains the freeze boundary for selected memberships and role-specific horizons.

### 6.10 Leakage and correlation limits

Target size intentionally counts configurations rather than effective independent samples. Correlation/protected relations govern split exclusion and remain diagnostics after splitting.

Foundation predictions, target-label residual/difficulty, candidate outcomes, CV/replay/reducer state, and downstream physical evidence may not influence the split or `pi_train`. `M3` target labels become available to EVAL2 only after `M3` membership has frozen.

## 7. Amend Section 13.1 — target-size diagnostic validity

Replace Section 13.1 with:

### 13.1 What the target-size diagnostic supports

Within the exact configured candidate ladder, canonical target population, protected `P_train/M3` split, frozen target-order metric and `pi_train`, common training preparation, objective/weights, target-size optimizer-normalization policy, optimizer-seed population, fidelity schedule, exact full-`M3` evaluation policy, and practical-equivalence threshold, the diagnostic supports a **comparative short-horizon statement** about exact-`M3` target-force error for the tested target memberships.

It supports an operator decision among qualified configured memberships. It does not prove that an untested size would behave monotonically, that a selected size transfers to a different training method, or that diagnostic `M1/M2` sampling behavior is model-selection evidence.

## 8. Amend Section 13.4 uncertainty list

Preserve the current list, but interpret evaluation-population sampling as follows:

- exact `M3` membership/finiteness and target-force measurement remain model-selection uncertainty/evidence dependencies;
- `M1/M2` finite-population sampling uncertainty is diagnostic only and cannot be a causal source of reducer elimination under the accepted Revision-5 method.

All existing uncertainty sources not contradicted by this statement remain unchanged.

## 9. Amend Section 14 falsification/reopen conditions

Add the following target-order falsification conditions to the existing list:

- a supposedly valid split removes the last training member of an eligible neutral condition;
- a protected component is divided between `P_train` and `M3`;
- reserve redundancy is not recomputed after retained-set changes;
- target-order membership depends on mass density, material-specific/profile coordinates, foundation predictions, or label-derived difficulty without a later accepted D1 amendment;
- a configured `T_N` is not the exact prefix of the one canonical `pi_train`;
- an automatic fidelity boundary ranks/eliminates candidates on `M1` or `M2` rather than exact `M3`; or
- changing only diagnostic `pi_eval` changes the target-size recommendation while exact `M3` predictions are unchanged.

These are D1/D2 method violations; D3/D4 may not compensate for them by adding wrappers, rescue selectors, or hidden thresholds.

## 10. Amend Section 15 reproducibility list

Replace the target-order bullet with:

- the exact `U_size`, protected `P_train/M3` split and split-policy identity, fitted target-order metric identities, `pi_train`, exact `T_N` prefixes, exact `M3` model-selection membership, and separately identified diagnostic `pi_eval/M1/M2` sampling evidence;

Preserve every other reproducibility/provenance requirement.

## 11. D1 -> D2 handoff after acceptance

D2 must preserve at minimum:

1. equal-frame `mu_sel`, separate frozen `mu_loss`, and exact component-weighted `mu_eval`;
2. hard exact split feasibility with at least one retained training frame per eligible neutral condition and indivisible protected components;
3. global minimum condition depletion before retained-set structural redundancy;
4. universal cell/strain plus material-neutral element-resolved local-structure membership scope and the explicit forbidden membership evidence;
5. one anchored condition-local coverage-progressive `pi_train` with exact nested `T_N` prefixes;
6. exact full `M3` evaluation at every automatic fidelity boundary;
7. diagnostic-only probability semantics for `M1/M2`; and
8. hard/soft and leakage boundaries above.

No D3 or D4 implementation choice is promoted by this D1 amendment.
