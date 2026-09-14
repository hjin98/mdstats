---
kind: d1-d2-authority-candidate
workplan_id: MLFF-FPS-COVERAGE-METHOD-RECONCILIATION-1
protocol_version: 6.3.0
status: proposed-awaiting-independent-review-and-human-ratification
proposal_date: 2026-09-13
branch: design/mlff-fps-coverage-method-reconciliation
project_state_basis: e8d04144f55c72d799ffcd3fe40c75e47078a66d
accepted_pem: hjin98/mdstats@4eabe2ae9783c7ff92f3a1093c37502a01380812:PROJECT-ENGINEERING-MEMORY.md
highest_affected_domain: D1
---

# Gate A D1/D2 candidate — FPS/coverage target-order method

## 0. Authority status

This file is a **Gate A proposal**, not current permanent authority. The current normative owners remain `docs/methods/mlff_scientific_method.md` and `docs/methods/mlff_numerical_algorithmic_method.md` until this candidate passes independent D1/D2 falsification and receives explicit human ratification. No behavior-changing D3/D4 implementation may claim conformance to this proposal before that gate closes.

The candidate resolves the decision menu in `MLFF_FPS_COVERAGE_METHOD_RECONCILIATION_AND_ORDERING_CONFORMANCE_WORKPLAN.md` into one implementable method. It deliberately does not revive FEAS/MVIDX/MVSEL/REPAIR/MVQUAL, historical selector quotas, per-N repair, target-size label-domain fanout, foundation-model difficulty ordering, or a second selector topology.

## 1. Refreshed Historical Applicability Set

The branch began from semantic candidate `1093a8b...`; accepted `main` has since advanced to `e8d04144f55c72d799ffcd3fe40c75e47078a66d` through the D1/D2 reconstruction merge. The accepted Project Engineering Memory (PEM) remains the record at `4eabe2ae9783c7ff92f3a1093c37502a01380812`.

| PEM item | Disposition | Application here |
| --- | --- | --- |
| SP-001 | APPLICABLE | One current order owner; reuse mature pure FPS kernels without reviving retired selector topology. |
| FF-005 | APPLICABLE | Pre-order evidence is preparation-owned and published once in the immutable prepared generation. |
| SP-002 | APPLICABLE | Order/evidence/metric identity is fail-closed across restart and stale ancestry. |
| SP-003 | APPLICABLE | Structural descriptors and fitted metric are built once at preparation, not rebuilt downstream. |
| SP-004 | APPLICABLE | Final acceptance must exercise real `prepare -> P2 order -> prepared-generation consumer`. |
| FF-001 | NOT_APPLICABLE | TRAIN2/EVAL2 model construction is unchanged by the order method. |
| FF-002 | NOT_APPLICABLE | Checkpoint continuation is not an ordering owner. |
| FF-003 | NOT_APPLICABLE | Storage routing is not redesigned. |
| FF-004 | NOT_APPLICABLE | The proposed method has no mandatory GPU dependency; final GPU qualification remains deferred. |

## 2. Capability-transfer map

| Historical capability | Evidence/source identity | Candidate disposition | Current replacement/mechanism | Acceptance/oracle route |
| --- | --- | --- | --- | --- |
| One deterministic master order and exact prefixes | P2 population/split identities | CURRENT + PRESERVE | one `pi_train`, one `pi_eval`, exact prefix projection | permutation/prefix tests |
| Mandatory condition/support anchors | neutral condition keys | PROPOSED_FOR_PROMOTION | one representative training anchor per nonempty `P_train` neutral condition | condition-anchor and smallest-N feasibility tests |
| Representative centroid support | fitted geometry metric | PROPOSED_FOR_PROMOTION | condition medoid is the first local training representative | direct medoid oracle |
| Exact configuration FPS/maximin diversity | fitted geometry metric | PROPOSED_FOR_PROMOTION | exact FP64 within-condition FPS after each medoid | direct bounded FPS oracle |
| Empirical production/condition mass | neutral condition membership | PROPOSED_FOR_PROMOTION | global training queue follows empirical condition counts after mandatory anchors | proportional-deficit oracle |
| Material-neutral local structural/environment diversity | universal structural provider | PROPOSED_FOR_PROMOTION | geometry-only universal frame descriptor block, rebound to current pre-order authority | provider-lineage + metric-coordinate tests |
| Profile-specific environment features | profile providers | EVIDENCE_ONLY in baseline | diagnostics/future method revision; not required to construct current order | lineage review |
| Protected/rare-event prioritization | neutral event/protected-relation evidence | HARD ONLY WHEN EXPLICIT; otherwise diagnostic | existing explicit hard-support obligations plus soft reporting | hard/soft separation tests |
| Foundation residual/difficulty enrichment | foundation prediction/residual products | RETIRED FROM BASELINE METHOD | none; future method change only after separate D1/D2 acceptance | forbidden-flow tests |
| Candidate nearest-distance quantiles | fitted metric + selected prefix | PROPOSED_FOR_PROMOTION | `Q50/Q90/Q95/Q99` over `P_train` | direct rescoring oracle |
| Maximum covering radius / historical `D_max` | fitted metric + selected prefix | PROPOSED_FOR_PROMOTION | `R_max=max_x d_x(S)` | direct rescoring oracle |
| Historical `D_sum` | fitted metric + `mu_train` | REINTERPRETED | report `D_mean = |P_train|^-1 sum_x d_x(S)`; no unnormalized size-dependent sum | direct rescoring oracle |
| Historical `N95` and uncovered mass | historical radius threshold | RETIRED UNTIL A CURRENT RADIUS THRESHOLD IS ACCEPTED | none in baseline | absence/no hidden threshold test |
| Selected-selected nearest-neighbor diagnostics | fitted metric | PROPOSED_FOR_PROMOTION | selected NN `Q50/Q90/Q95` | direct scorer |
| Condition/environment/event support counts | current neutral evidence | PROPOSED_FOR_PROMOTION as diagnostics | monotone support counts; only configured hard obligations gate | direct counts |
| Bounded/incremental exact FPS kernels | `selection.py` mature kernels | REUSE CAPABILITY | one neutral pure numerical owner after Gate B/C | optimized-vs-simple equivalence |
| Independent coverage rescoring | historical MVQUAL pattern | PRESERVE AS VERIFICATION PATTERN | simple scorer independent of optimized selector state | falsification tests |
| FEAS/MVIDX/MVSEL/REPAIR/MVQUAL public topology | retired products | RETIRED | none | repository search/current ownership review |
| Historical fixed selector quotas/fractions/score thresholds | archived policies | RETIRED | no quota schedule in this candidate | configuration/schema negative |

## 3. D1 scientific contract

### 3.1 Scientific question

The target-size experiment asks how the fixed MLFF training method behaves as the number of training configurations increases under **one frozen, candidate-independent training-data construction**. The independent variable is cardinality `N`; changes in membership must therefore follow one declared coverage-progressive order rather than lexical frame identity or candidate outcomes.

Coverage is evidence about the support of the selected data population. It is not evidence of MLFF adequacy, long-horizon stability, or deployment validity. EVAL2, replay, post-selection CV, and downstream physical validation remain separate authorities.

### 3.2 Training reference measure `mu_train`

`mu_train` is the empirical configuration measure on exact `P_train`: every admissible frame has equal mass `1/|P_train|`. The training construction adds one explicit support constraint: every nonempty neutral condition in `P_train` must contribute one representative medoid before the ordinary proportional coverage progression. This avoids the known pure-FPS failure mode where sparse geometric extremes can displace all representation of a scientifically declared condition.

The target-size policy is method-infeasible if its smallest configured candidate size is smaller than the number of nonempty `P_train` neutral conditions. This is a policy/configuration error, not an emergent per-candidate repair rule.

After those condition anchors, the number of selected frames from each condition follows the empirical condition frame count as closely as integer prefix cardinality permits. Thus the method does not permanently equal-weight conditions and does not import historical quota fractions.

### 3.3 Evaluation reference measure `mu_eval` and EVAL2 estimand

`mu_eval` is the exact M3 empirical target distribution represented by the existing EVAL2 force-component RMSE:

```text
R_M3(f) = sqrt(
  sum_{x in M3} sum_{a=1}^{n_x} sum_{k=1}^{3} e_f(x,a,k)^2
  /
  sum_{x in M3} 3 n_x
)
```

`M1` and `M2` are increasing-resolution approximations to that same M3 estimand, not increasingly difficult challenge distributions. `pi_eval` therefore does **not** use FPS, target-label difficulty, foundation residuals, candidate predictions, reducer state, or selected-N evidence.

The baseline keeps the existing unweighted EVAL2 reduction. Nested evaluation prefixes are formed by deterministic stratified pseudorandom-like sampling that tracks M3 neutral-condition frame proportions; M3 itself remains exact. No new EVAL2 weight field is introduced by this candidate.

### 3.4 Split meaning

The accepted `U_size -> P_train/M3` split remains a protected-relation exact allocation and is **not made coverage-metric aware** in this repair. Training support keeps priority and the split is completed before the P_train-only fitted geometry metric exists. This prevents a circular `fit metric -> choose split -> refit metric` authority loop and confines the present repair to the target-order defect.

The only split change proposed here is numerical tie identity: lexical `frame_uid` spelling must not choose among scientifically distinct feasible allocations. Split/component ties use canonical scientific occurrence keys defined in Section 5.7.

### 3.5 Hard versus soft evidence

Only explicit accepted `hard_support_obligations` may qualify or reject an exact training prefix. FPS distance, coverage quantiles, event counts, environment counts, representative scores, or difficulty diagnostics are soft unless a future D1/D2 revision explicitly promotes a named quantity into a hard obligation.

The one-medoid-per-condition rule is part of the training-order construction itself, not an after-the-fact prefix repair and not a hidden qualification threshold.

### 3.6 Excluded scientific dependencies

The baseline method does not require foundation-model inference, target-label residuals, or difficulty scores. This is intentional: a geometry/condition method satisfies the target-size coverage claim without turning `prepare` into a GPU/model-provider prerequisite or allowing label-derived challenge ordering to steer `pi_eval`.

Profile-specific selection features remain admissible evidence for diagnostics or a future method revision, but they do not alter baseline membership until their producer lineage and weighting are separately accepted.

## 4. D2 numerical contract

### 4.1 Current pre-order evidence

The training metric has exactly two geometry-only blocks:

1. **raw physical geometry block**, sourced from current `NeutralFeatureEvidence.raw_features`, excluding every label-derived quantity; and
2. **universal structural frame block**, using the material-neutral local-structure provider already implemented by `mdstats.analysis.local_structure` / `UniversalStructuralFeatureCatalog`, but rebound by D3/D4 to current pre-order P1/P2 ancestry rather than importing DATA6/DATA7 role authority.

The raw block includes, in canonical name order:

```text
cell_volume_angstrom3
mass_density_g_cm3
cell_length_a_angstrom
cell_length_b_angstrom
cell_length_c_angstrom
cell_angle_alpha_degrees
cell_angle_beta_degrees
cell_angle_gamma_degrees
hydrostatic_strain
deviatoric_strain_norm
engineering_shear_xy
engineering_shear_xz
engineering_shear_yz
pair:<rule_id>:minimum_pair_distance_angstrom
pair:<rule_id>:mean_nearest_neighbor_distance_angstrom
pair:<rule_id>:maximum_nearest_neighbor_distance_angstrom
pair:<rule_id>:coordination_mean
pair:<rule_id>:coordination_maximum
```

Pair coordinates are included for every active `RawFeaturePolicy.pair_rules` entry in lexical `rule_id` order. Energy, force, force quantile/statistic, pressure, stress, and temperature-label values are excluded from the metric. Temperature/composition/regime/strain-class support enters through the neutral condition key rather than as a continuously scaled score.

The universal structural block is the canonical `UniversalFrameStructuralDescriptor.feature_names`/vector after provider authentication. Atomic-environment rows are not FPS candidates and no millions-of-environment FPS is performed.

### 4.2 Fit domain and metric transformation

The split is established first. Metric fitting uses **P_train geometry only**; M3 contributes no fitted coordinates. Both blocks canonicalize coordinates by semantic feature name before any matrix construction.

For each numerical coordinate over P_train:

1. missing values are replaced by the coordinate median of observed values;
2. one binary missingness indicator is appended for that coordinate when any P_train value is missing;
3. center is the observed-value median;
4. primary scale is `Q75 - Q25`;
5. if that scale is numerically degenerate, fallback scale is the maximum absolute observed deviation from the median;
6. if both are degenerate, transformed numerical values are exactly zero and scale identity is recorded as constant-coordinate;
7. nonconstant scale is accepted only when greater than `1e-12 * max(1, max_abs_observed_value)`; otherwise the next fallback is used.

Each resulting block is divided by `sqrt(d_b)`, where `d_b` is its transformed output dimension including missingness indicators. The two present blocks have equal block weight. The final metric is FP64 Euclidean distance over the concatenated normalized blocks. There is no PCA, whitening, randomized projection, learned feature weighting, or foundation descriptor in this baseline.

The fitted metric record binds the exact input feature names, missing masks, centers, scales/fallback kind, block dimensions, block normalization, provider/policy digests, P_train membership digest, FP64 identity, and tolerance policy.

### 4.3 Numerical equality/tie policy

All metric fitting, centroid/medoid scoring, distance accumulation, and FPS nearest-distance state use IEEE-754 binary64 (`float64`). For a governing nonnegative score `s*`, values are in the same numerical tie set when

```text
abs(s - s*) <= 1e-12 * max(1, abs(s*))
```

The `1e-12` relative/absolute floor is a numerical equivalence tolerance, not a scientific coverage threshold. It is part of method identity and requires Gate A ratification with the rest of this contract.

### 4.4 Exact local training queues

For every nonempty neutral condition `c` in P_train:

1. collect its transformed metric vectors;
2. compute their FP64 centroid;
3. choose the **medoid anchor** minimizing Euclidean distance to the centroid; numerical ties use the scientific key from Section 5.7;
4. initialize exact FPS with that medoid;
5. each subsequent local rank chooses the remaining frame maximizing its current nearest-selected distance under the accepted metric; numerical ties use the same scientific key;
6. update nearest-selected distances incrementally without a persistent pairwise distance matrix.

The local queue is therefore representative at rank 1 and maximin/coverage-progressive thereafter. This is not pure global FPS and contains no category quota schedule.

### 4.5 Global `pi_train` interleaving

Let `N_c` be the number of P_train frames in condition `c`, `N=sum_c N_c`, `s_c(k)` the number from `c` already emitted after `k` global ranks.

**Anchor phase.** Emit one medoid from every condition. Conditions are ordered by decreasing `N_c/N`; exact count ties use canonical condition identity. The smallest configured target size must contain this complete anchor phase.

**Proportional phase.** For the next global position `k+1`, among nonexhausted condition queues choose the condition maximizing

```text
Delta_c(k+1) = (k+1) * N_c / N - s_c(k)
```

with exact numerical ties resolved by canonical condition identity, then emit that condition's next local FPS frame.

This largest-proportional-deficit scheduler makes integer condition counts track `mu_train` after the required support anchors while local FPS expands structural coverage inside each condition.

The scientifically governed FPS region extends through `K=max(configured candidate_sizes)` ranks. To preserve the current full-permutation record without forcing an unnecessary full O(N^2) FPS traversal, remaining unused P_train frames are appended by continuing the same proportional condition scheduler with each local remainder ordered by the scientific key. No configured `T_N` may intersect this completion tail. Raising `K` is an order-policy identity change and requires a fresh prepared generation.

`T_N` remains exactly `pi_train[:N]`; no per-N rerun, repair, swap, or selector exists.

### 4.6 Exact `pi_eval`

`pi_eval` is independent of the fitted training metric and all candidate outcomes.

For each M3 frame define the scientific occurrence key in Section 5.7 and an evaluation hash

```text
h(x) = sha256(canonical({
  schema: "mdstats.target-size-eval-order-key.v1",
  policy_seed: 0,
  scientific_occurrence_key: kappa(x)
}))
```

Within each neutral condition, order frames by `(h(x), kappa(x))`. Globally, starting with zero selected counts, choose at each rank the nonexhausted condition maximizing the same frame-count proportional deficit

```text
Delta_c(k+1) = (k+1) * N_c / |M3| - s_c(k)
```

and emit the next hashed frame from that condition. There is **no mandatory one-per-condition evaluation anchor**: doing so would deliberately distort the early-rung empirical M3 measure. The scheduler naturally includes rare conditions when their empirical mass warrants it.

`M_i` remains the exact configured prefix of this one order; `M3` is the full reserve. Existing EVAL2 force-component RMSE is unchanged.

### 4.7 UID-independent scientific keys

`frame_uid` remains a persisted identity, but lexical UID spelling is not a scientific score. Define

```text
kappa(x) = sha256(canonical({
  schema: "mdstats.target-order-scientific-occurrence-key.v1",
  condition_id: neutral_condition_id(x),
  source_identity_signature: source_identity_signature(x),
  source_frame_index: source_frame_index(x),
  geometry_fingerprint: geometry_fingerprint(x)
}))
```

No target label value or label digest participates. If two records somehow have identical `kappa` despite being distinct current frames, preparation fails as ambiguous rather than using arbitrary UID spelling.

For protected split components, define a component key as the digest of the sorted member `kappa` values plus the component's accepted protected-relation identity. Current exact split feasibility/allocation semantics are preserved, but all formerly arbitrary component/DP tie choices use this component key instead of minimum UID.

### 4.8 Coverage diagnostics

For every configured training prefix `S_N=T_N`, independently rescore against full P_train in the accepted metric:

```text
d_x(S_N) = min_{y in S_N} d(z_x, z_y)
R_max(N) = max_x d_x(S_N)
D_mean(N) = (1 / |P_train|) * sum_x d_x(S_N)
Q50/Q90/Q95/Q99 of {d_x(S_N)} under equal-frame mu_train
selected-NN Q50/Q90/Q95 over min_{y in S_N, y != x} d(z_x,z_y)
represented neutral-condition count
represented universal-structure support summaries where provider definitions are monotone
protected-event represented count/fraction
explicit hard-obligation status (reported separately from soft diagnostics)
```

`R_max` must be nonincreasing over nested prefixes. Historical `D_max` maps to `R_max`; historical size-dependent `D_sum` is replaced by normalized `D_mean`. `N95` and uncovered-mass measures are absent because this candidate defines no scientifically accepted coverage-radius threshold.

For evaluation prefixes, report condition-count discrepancy from the full M3 frame proportions and the exact EVAL2 component count. These are diagnostics only.

### 4.9 Resource envelope

- Descriptor production: current material-neutral local-structure provider, CPU-capable; no foundation model and no GPU prerequisite.
- Metric fit/storage: `O(N d)` memory and work up to provider cost; no dense `N x N` pairwise matrix.
- Training FPS: incremental nearest-distance state, `O(N)` distance state plus `O(N d)` feature matrix; only the first `K=max candidate N` ranks use FPS. Worst-case distance work is `O(K N d)` and may be reduced by condition partitioning, but numerical results must equal the simple reference.
- Evaluation order: `O(|M3| log |M3|)` hash/sort plus linear proportional interleaving.
- Coverage rescoring: bounded/incremental or chunked exact calculation with no persistent dense quadratic state.

Execution batching, thread/process count, cache layout, and vectorization are D3/D4 choices only if exact results and tie sets are preserved.

## 5. Stage-by-evidence authorization matrix

Legend: `A` allowed and method-relevant; `I` identity/support only; `D` diagnostic only; `H` only through explicit existing hard obligation; `F` forbidden for the baseline method.

| Evidence class | U_size eligibility | P_train/M3 split scoring | pi_train | pi_eval | soft diagnostics | hard qualification |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| canonical condition/provenance facts | I | A (accepted split constraints/ties) | A | A | A | H |
| geometry-only/raw structural features | I | F | A, fit on P_train | I only for `kappa`; no geometry priority | A | H only if explicitly configured |
| universal structural frame features | F | F | A, fit on P_train after current-generation provider authentication | F | A | H only if separately accepted/configured |
| profile/environment features | F | F | F in baseline | F | D | H only through existing explicit obligation |
| fitted geometry metric/scaler/PCA/whitening | F | F | A; scaler fit P_train; no PCA/whitening | F | A | F |
| frozen foundation descriptors/predictions | F | F | F | F | D only outside membership identity | F |
| target-label foundation residual/difficulty | F | F | F | F | D only after membership freeze | F |
| protected-event evidence | I | A only through accepted protected relations | D; does not reorder baseline | F | A | H |
| correlation/duplicate/protected relations | I | A | D | D | A | H where existing obligation names it |
| candidate outcomes/reducer/CV/replay/physical validation | F | F | F | F | post hoc only | F |

Circularity consequence: no evidence fitted only after the split can flow backward into split selection. M3 labels never fit the training order. Candidate outcomes never affect either order.

## 6. Resolved Gate A decision table

| Decision | Candidate resolution |
| --- | --- |
| `mu_train` | equal mass per P_train frame, with one representative medoid anchor per nonempty neutral condition before proportional progression |
| `mu_eval` | exact M3 empirical force-component EVAL2 estimand; early prefixes approximate same population |
| split objective | preserve accepted exact protected-relation P_train/M3 allocation; no coverage score in split |
| split tie | UID-independent component scientific key |
| training evidence | current neutral raw geometry + current-generation rebound universal structural frame descriptors; labels/foundation/difficulty excluded |
| fit domain | P_train geometry only, after split |
| metric | two equal blocks, robust median/IQR with explicit fallback/missing indicators, block dimension normalization, FP64 Euclidean, no PCA |
| metric tolerance | `1e-12 * max(1, |score|)` tie/degeneracy tolerance |
| `pi_train` | condition medoid anchors -> within-condition exact FPS -> empirical-condition proportional global scheduler through max configured N -> deterministic nonexperimental tail completion |
| `pi_eval` | condition-proportional deterministic hash order over M3; no FPS/difficulty/challenge enrichment |
| EVAL2 weighting | unchanged existing force-component RMSE; no new weights |
| hard/soft boundary | only explicit hard-support obligations gate; coverage/event/difficulty diagnostics remain soft |
| coverage diagnostics | `R_max`, `D_mean`, Q50/Q90/Q95/Q99, selected-NN quantiles, support counts, event fraction |
| resource envelope | CPU-capable; O(Nd) persistent feature state; no dense persistent O(N^2); FPS bounded to max configured N |
| restart identity | order method/version, represented measures, evidence/provider identities, split digest, fitted metric digest, K=max N, tolerance/tie policy, kappa schema, pi_train/pi_eval digests, eval hash policy/seed, hard-obligation policy |
| old empty-evidence generations | historical only; fail current admission and require fresh `prepare`; no default migration |
| retired constants/mechanisms | historical quotas, MVSEL/MVQUAL public topology, N95/uncovered radius thresholds, foundation difficulty ordering, UID fallback |

## 7. D3/D4 contract implied after ratification

If ratified, Gate B/C/D must realize the following without changing the D1/D2 meaning:

```text
P1 canonical frame / neutral statistical / raw feature authority
  + current-generation universal structural descriptor provider
  -> one preparation-owned TargetOrderEvidence/metric authority
  -> existing single P2 split/order owner
       -> exact split
       -> fitted P_train metric
       -> pi_train + pi_eval + diagnostics
  -> immutable prepared target-size generation
  -> downstream consumers (read only; zero metric/FPS rebuild)
```

The current DATA6/DATA7 role authority may not be imported wholesale. Reuse the low-level material-neutral structural provider and mature pure FPS kernels; rebind them to current P1/P2 ancestry. Production order APIs must require the resolved method/evidence explicitly. `None` or empty priority vectors may remain only for deserializing historical method records, never as the current production default.

A schema/method-version boundary must make pre-repair empty-evidence generations stale. No current descendant may be relabeled as having used the new method.

## 8. Required falsification before ratification

The following remain Gate A acceptance requirements:

1. bounded clustered/common + rare-support fixture comparing UID order, pure FPS, representative-only, difficulty-only, and this combined method;
2. UID-renaming invariance outside genuine numerical tie sets;
3. source/enumeration-order invariance;
4. metric-coordinate-name permutation invariance;
5. direct medoid/FPS equivalence to a simple reference;
6. monotone `R_max` and exact-prefix/permutation checks;
7. evaluation-prefix proportionality and direct comparison to full-M3 EVAL2 estimand on a fixture with heterogeneous error patterns;
8. old-generation negative;
9. producer-lineage proof that the universal structural descriptor bytes are rebound to current ancestry and carry no retired label-domain/CV authority;
10. resource benchmark sufficient to rule out accidental dense pairwise storage.

A bounded same-session falsification record may prepare this review, but it is not the independent Protocol review required by Gate A.

## 9. Human ratification statement

Gate A closes only when a human owner explicitly ratifies or rejects this resolved bundle, including these material choices as one method contract:

- empirical-frame `mu_train` plus one training medoid anchor per neutral condition;
- geometry-only raw + universal structural metric, with no foundation/difficulty ordering;
- robust two-block FP64 metric and `1e-12` numerical tolerance;
- condition-local medoid-seeded FPS with proportional global interleaving;
- proportional deterministic-hash `pi_eval` preserving the ordinary M3 EVAL2 estimand;
- no coverage-aware split objective beyond UID-independent tie repair;
- no historical quota schedule or radius threshold;
- CPU-capable preparation with FPS bounded to the largest configured target size.

Until that explicit decision and an independent review exist, permanent D1/D2 documents and behavior-changing D3/D4 code remain unchanged.