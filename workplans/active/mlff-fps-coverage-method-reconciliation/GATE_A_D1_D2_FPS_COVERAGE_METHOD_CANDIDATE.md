---
kind: d1-d2-authority-candidate
workplan_id: MLFF-FPS-COVERAGE-METHOD-RECONCILIATION-1
protocol_version: 6.3.0
status: proposed-awaiting-fresh-independent-review-and-human-ratification
proposal_date: 2026-09-13
revision: 2
revision_basis_review: GATE_A_INDEPENDENT_D1_D2_REVIEW.md
branch: design/mlff-fps-coverage-method-reconciliation
project_state_basis: e8d04144f55c72d799ffcd3fe40c75e47078a66d
accepted_pem: hjin98/mdstats@4eabe2ae9783c7ff92f3a1093c37502a01380812:PROJECT-ENGINEERING-MEMORY.md
highest_affected_domain: D1
---

# Gate A D1/D2 candidate — FPS/coverage target-order method, Revision 2

## 0. Authority status

This is a **repaired Gate A proposal**, not current permanent authority. It responds to the independent NO-PASS review of candidate `cc55be388fa8ab6dd0641eeefc3b914bfcaefe0f`. The normative owners remain `docs/methods/mlff_scientific_method.md` and `docs/methods/mlff_numerical_algorithmic_method.md` until this revision passes a fresh independent D1/D2 Challenge review and receives explicit human ratification.

No behavior-changing D3/D4 implementation is accepted before Gate A closes. The repair preserves the accepted V7 shape: one `P_train/M3` split, one `pi_train`, one `pi_eval`, exact nested prefixes, one prepared generation, no per-N selector/repair, no pre-target CV/label-domain fanout, and no revived FEAS/MVIDX/MVSEL/REPAIR/MVQUAL topology.

## 1. Historical applicability and capability transfer

The applicable Project Engineering Memory (PEM) dispositions remain SP-001, FF-005, SP-002, SP-003, and SP-004 as applicable; FF-001 through FF-004 remain non-owning for this repair. The accepted PEM basis is unchanged from Revision 1.

The capability-transfer decision is unchanged except where this revision narrows claims:

- deterministic master order + exact prefixes: preserve;
- representative support: promote through per-condition representative anchors;
- exact frame-level farthest-point sampling (FPS): promote after the representative anchor;
- material-neutral frame-level local-structure coverage: promote;
- exhaustive atomic-environment/profile-specific coverage: **not claimed by this baseline**; profile-specific evidence remains diagnostic/future-authority material;
- foundation residual/difficulty ordering: retired from the baseline method;
- independent coverage rescoring: preserve as verification;
- historical fixed quotas, `N95`, uncovered-radius thresholds, public multi-view selector topology: retired unless separately re-accepted.

## 2. D1 scientific contract

### 2.1 Scientific question

The target-size experiment asks how one fixed MLFF training method behaves as the number of training configurations `N` increases under one frozen, candidate-independent data-construction policy. The intended experimental variable is configuration cardinality; membership therefore changes only by extending one precomputed order.

Coverage describes support of the selected configuration population. It does not prove force-field accuracy, deployment adequacy, long-horizon stability, or physical transferability. EVAL2, post-selection cross-validation, replay, and downstream validation remain separate evidence.

### 2.2 Three measures that must not be conflated

This revision distinguishes three different measures.

**Selection/support measure `mu_sel`.** On exact `P_train`, every eligible configuration has equal mass `1/|P_train|`. `mu_sel` governs the configuration-membership experiment: a target size of 512 means 512 configurations, not 512 weighted loss units or 512 effective independent samples.

**Training-loss influence measure `mu_loss`.** The frozen downstream training method may apply common per-configuration weights, property masks, and global objective coefficients. Those weights are fitted once over exact `P_train` and projected unchanged to every `T_N`; they do not define membership and are not renormalized per candidate. Their policy identity is nevertheless part of the target-size experimental method because changing it changes what the fixed training method means.

**Evaluation estimand `mu_eval`.** EVAL2 is the component-weighted force-error estimand on exact `M3`, because every admitted Cartesian force component contributes once to the numerator and denominator.

The target-size claim therefore does **not** assert that `mu_sel = mu_loss = mu_eval`. It asserts that membership is varied under fixed `mu_sel` while `mu_loss`, the optimizer method, and the evaluation design are frozen across candidates. This separation is intentional: using training weights to choose membership would feed a later fitted training objective backward into the pre-order experiment.

### 2.3 Training support and condition anchors

`pi_train` must provide frame-level structural coverage while preserving declared neutral-condition support. Every nonempty neutral condition that remains in `P_train` contributes one representative anchor before ordinary proportional progression.

This is a **method feasibility invariant**, not an optional `hard_support_obligation`: the configured smallest target size must be at least the number of nonempty `P_train` conditions. Optional hard obligations remain separate qualification authority and may impose additional prefix requirements.

After the anchor phase, condition counts track the empirical frame mass of `P_train` as closely as integer cardinality permits. Thus the order does not permanently equal-weight conditions and does not import historical fixed quota fractions.

### 2.4 Scientific scope of structural coverage

The baseline claims coverage of:

1. the accepted raw frame-level physical geometry variables; and
2. material-neutral **frame-level summaries** of local structure from the universal structural provider.

It does not claim exhaustive coverage of every atomic environment, profile-specific site class, or material-specific event. Those signals may remain diagnostics or become future D1/D2 authority, but are not allowed to silently alter current membership.

This scope is deliberately narrower than some historical DATA7/MVSEL machinery. The omitted capabilities are not treated as secretly preserved by aggregate frame descriptors.

### 2.5 `U_size -> P_train/M3`: training-priority residual allocation

The split objective is now explicit.

1. All P1 split-excluding/protected relations are closed transitively first; components are indivisible.
2. `|M3|` remains exact and `|P_train| >= N_max` remains mandatory.
3. Subject to exact feasibility, reserve allocation preferentially removes **redundant neutral-condition support** rather than scarce support. For a protected component `g`, define its neutral-condition depletion cost

```text
J(g) = sum_c n(g,c) / N_c
```

where `N_c` is the number of `U_size` frames in condition `c` and `n(g,c)` is the number of members of `g` in that condition.
4. Among exact-cardinality feasible component subsets, the split minimizes total `sum_g J(g)`. This penalizes taking a large fraction of a scarce condition more than taking the same number of frames from abundant support.
5. Exact ties use the scientific component identity defined in D2.

This is the accepted meaning of “M3 preferentially consumes redundant residual support” for this baseline. **Geometry/FPS is not part of the split objective.** Geometry coverage begins only after the split, avoiding a circular `fit P_train metric -> choose P_train` dependency.

M3 is development/model-selection evidence drawn from redundant residual support; it is not claimed to be a complete scientific-validation population for every scarce condition. Scarce support may deliberately remain training-side because training support has priority.

### 2.6 Evaluation ladder and its estimand

Exact M3 defines the final EVAL2 population and therefore the exact final force-component estimand:

```text
R_M3(f) = sqrt( sum_x SSE_x(f) / sum_x C_x )
C_x = 3 * n_atoms(x)
```

`M1` and `M2` are **finite-population frame-cluster samples** used for successive screening of that same ratio-of-totals estimand. They are not separate challenge distributions and do not use geometry FPS, target-label difficulty, foundation residuals, candidate predictions, reducer state, or selected-N evidence.

The evaluation order is one frozen pseudo-random permutation of M3 frames. Consequently every prefix of size `m` is interpreted, over the randomization ensemble, as a simple random sample without replacement (SRSWOR) of M3 frame clusters. The existing EVAL2 calculation on a prefix,

```text
R_m(f) = sqrt( sum_{x in M_m} SSE_x(f) / sum_{x in M_m} C_x )
```

is a finite-population ratio estimator of the exact M3 component-weighted mean-squared force error. It is not exactly unbiased at finite `m`, but is design-consistent, its sampling uncertainty decreases as the prefix grows, and the approximation error vanishes exactly at M3.

The same frozen evaluation membership is used for every candidate at a rung, preserving paired candidate comparison. Sampling uncertainty is diagnostic evidence; it does not silently replace the current reducer rule.

### 2.7 Correlation and effective independence

Target size `N` intentionally counts configurations, not estimated independent samples. Correlation/protected relations govern split exclusion and are reported diagnostically after the split; they do not redefine target cardinality or create another ordering domain. This is a limitation of the target-size interpretation: adding strongly correlated frames can increase `N` with less information gain than adding independent frames. Coverage and correlation diagnostics must make that visible rather than pretending `N` is effective sample size.

### 2.8 Hard versus soft evidence

Only explicit accepted `hard_support_obligations` qualify/reject prefixes. FPS distances, coverage radii/quantiles, event counts, correlation diagnostics, environment summaries, and sampling-uncertainty diagnostics are soft. The mandatory representative anchor phase is part of the order method itself, not an after-the-fact qualification repair.

### 2.9 Excluded dependencies

No foundation-model inference, target-label residual, or difficulty score is required for membership. This keeps `prepare` CPU-capable and prevents target labels or candidate outcomes from steering `pi_train` or `pi_eval`.

## 3. D2 numerical contract

### 3.1 Scientific occurrence and component keys

Lexical `frame_uid` spelling is not a score. Define an occurrence key `kappa(x)` from canonical scientific/provenance fields:

```text
condition_id
source_identity_signature
source_frame_index
geometry_fingerprint
```

using the exact hash encoding below. `source_identity_signature` and source-frame index are intentionally included because the current method distinguishes authenticated occurrences, not only geometries. Repackaging that changes source identity therefore creates a new prepared-generation identity. For `pi_train`, this can affect only accepted numerical tie sets. Evaluation random priority is geometry-based first, so source repackaging may alter order only among equal geometry-priority ties.

A component key is the digest of the sorted member `kappa` values plus the canonical P1 protected-relation identity.

### 3.2 Exact hash byte encoding

All D2 order hashes use SHA-256 over a length-prefixed byte sequence, not implementation-defined JSON.

For schema tag and each ordered UTF-8 string field `v`, encode:

```text
uint64_big_endian(len(utf8(v))) || utf8(v)
```

and concatenate fields in the order specified by the owning formula. Integer seed fields are encoded as unsigned 64-bit big-endian integers. There is no delimiter ambiguity and no mapping-iteration dependence.

### 3.3 Exact split algorithm

Let protected components be `g_1...g_C`, with integer size `w_j` and exact rational depletion cost

```text
J_j = sum_c n(g_j,c) / N_c.
```

Solve the exact-cardinality reserve problem by dynamic programming over reachable totals `0..M3`. For each total store the predecessor subset with minimum exact rational total cost. Rational comparisons use exact integer numerator/denominator arithmetic; they are not floating-point scores. If costs tie exactly, choose the lexicographically smaller sorted component-key tuple.

This preserves `O(C*M3)` reachability states. Cost arithmetic may use reduced rational integers; no condition-count vector is part of the state. If M3 is unreachable, split construction fails. The method is exact for the stated additive depletion objective; it does not claim to globally optimize geometry coverage.

### 3.4 Training feature families

The frame metric uses only current geometry-derived evidence and has named semantic **families**, not two arbitrary blocks.

Raw families:

- `cell_geometry`: volume, density, cell lengths, cell angles;
- `strain`: hydrostatic strain, deviatoric strain norm, engineering shear components;
- `pair_geometry`: all active pair-rule minimum/mean-nearest/maximum-nearest/coordination summary coordinates, canonicalized by `(rule_id, coordinate_name)`.

Universal structural families are the provider's enabled material-neutral feature families (for example pair-distance, radial-environment, coordination, connectivity, chemical-environment, local-density, angular-environment, orientational-order), identified by the provider's semantic family name. A provider change that changes the enabled family set is metric identity.

Energy, forces, stress/pressure, instantaneous temperature labels, foundation predictions, residuals, and target-derived difficulty are excluded. Neutral condition identity handles composition/temperature/regime/strain-class support as a discrete support axis rather than a fitted continuous score.

### 3.5 Canonical coordinate transform

Metric fitting occurs on exact `P_train` after the split. M3 contributes no fitted metric coordinates.

For every numerical coordinate, first sort P_train rows by `kappa`. Missing values are imputed with the observed-value median and a binary missingness indicator is appended if any value is missing.

Quantiles use Hyndman-Fan **type 7** interpolation. For sorted observed values `x[0..n-1]` and probability `p`, let `h=(n-1)p`, `i=floor(h)`, `r=h-i`; then

```text
Q_p = (1-r)*x[i] + r*x[min(i+1,n-1)].
```

Center is `Q_0.5`. Primary scale is `Q_0.75-Q_0.25`. If the scale is numerically degenerate under Section 3.7, fallback scale is the maximum absolute deviation from the median. If that is also degenerate, the transformed numerical coordinate is identically zero and the coordinate is recorded as constant.

Every transformed semantic family `f` is divided by `sqrt(d_f)`, where `d_f` includes its active missingness indicators. Thus each accepted family has equal total Euclidean weight before data-dependent variation, and adding more coordinates to one family does not automatically multiply that family's nominal influence.

**Rationale:** D1 asserts coverage across named frame-level physical/local-structure families but provides no accepted evidence that one family deserves a larger prior weight. Equal family mass is therefore the symmetry-preserving baseline. It is an explicit ratifiable method choice, not an accidental consequence of coordinate count. Sensitivity/ablation evidence remains mandatory before promotion; material instability to plausible family regrouping reopens D2.

The final metric is FP64 Euclidean distance over the concatenated family-normalized coordinates. No PCA, whitening, learned weights, random projection, profile-specific feature block, or foundation descriptor is present.

### 3.6 Deterministic distance and representative computation

All feature coordinates are traversed in canonical `(family_name, coordinate_name)` order. Squared Euclidean distance is accumulated left-to-right in binary64 in that fixed order; fused contraction is not part of the semantic reference. Optimized implementations may reorder/vectorize only if they reproduce the reference ordering decisions under the accepted equivalence envelope.

The representative anchor for one condition is the **coordinate-median medoid**, avoiding an order-sensitive floating-point centroid:

1. compute the type-7 median independently for every transformed coordinate;
2. compute each frame's squared distance to that median vector;
3. select the smallest distance, with numerical ties resolved by `kappa`.

Exact FPS then starts from this medoid and repeatedly selects the remaining frame with maximum nearest-selected squared distance. Nearest-distance state is updated incrementally; no persistent dense pairwise matrix is required.

### 3.7 Finite-precision equivalence

Let binary64 unit roundoff be `u = 2^-53`. For a squared-distance sum over `d` transformed coordinates define

```text
gamma_d = d*u / (1-d*u)
```

for `d*u < 1`. Two nonnegative squared-distance scores `a,b` belong to the same numerical tie set when

```text
|a-b| <= 8*gamma_d*max(1,|a|,|b|).
```

The factor 8 is the accepted guard for accumulation and preceding coordinate-transform roundoff in the scalar reference; it must be falsified against higher-precision/direct fixtures before promotion.

Scale degeneracy is a separate one-coordinate question. A positive scale `s` is treated as numerically zero when

```text
s <= 32*u*max(1,max_abs_observed_value).
```

These tolerances are numerical equivalence bounds, not scientific coverage thresholds. If independent higher-precision evidence shows they merge scientifically distinct values or fail to cover legitimate reference roundoff, D2 reopens; implementations do not tune them to make tests pass.

### 3.8 Global `pi_train`

Let `N_c` be P_train frame count in condition `c`, `N=sum_c N_c`, and `s_c(k)` the count already emitted after `k` ranks.

**Anchor phase:** emit one condition medoid from every nonempty condition, ordered by decreasing `N_c`, then canonical condition ID. `N_min` must contain the full anchor phase.

**Proportional phase:** choose the nonexhausted condition maximizing the exact integer deficit numerator

```text
D_c(k+1) = (k+1)*N_c - s_c(k)*N.
```

There is no floating-point proportional comparison. Exact ties use canonical condition ID. Emit that condition's next local FPS frame.

FPS governs through `K=max(configured candidate_sizes)`. Remaining frames exist only to complete the persisted permutation and are interleaved by the same exact condition-deficit scheduler with within-condition remainder ordered by `kappa`. No configured `T_N` may enter this tail. Changing K changes method identity.

Every candidate is exactly `T_N=pi_train[:N]`; there is no per-N rerun, swap, repair, or selector.

### 3.9 Exact `pi_eval`: frozen simple-random frame permutation

The evaluation order is a deterministic realization of SRSWOR over M3 frame clusters.

For each frame define a random-priority digest from:

```text
schema = "mdstats.target-size-eval-random-priority.v2"
policy_seed = fixed unsigned 64-bit evaluation seed
condition_id
geometry_fingerprint
```

encoded by Section 3.2. Order by `(priority_digest, kappa)`. Geometry-identical priority ties use occurrence lineage only as the final tie break. Candidate outcomes, labels, fitted training metric, protected-event scores, and reducer state are forbidden.

The seed is part of method identity and is common to every candidate. It is not varied per N, seed, fold, or candidate. `M_i=pi_eval[:m_i]`; M3 is the full reserve.

This order intentionally does **not** force per-condition quotas, because unequal deterministic stratum inclusion probabilities would require a changed EVAL2 weighting estimator. Instead, condition/component-mass discrepancies are diagnostics of the realized finite sample.

### 3.10 Evaluation sampling uncertainty

For candidate model `f` and an evaluation prefix of `m` frames, define per-frame

```text
Y_x = SSE_x(f)
C_x = 3*n_atoms(x)
r_m = sum Y_x / sum C_x
```

and `R_m=sqrt(r_m)`. Under the SRSWOR design, `r_m` is the usual finite-population ratio estimator for the M3 ratio of totals. It is not claimed exactly unbiased. A diagnostic linearization standard error may be reported using

```text
z_x = Y_x - r_m*C_x
SE(r_m) ~= sqrt((1-m/M3_size) * s_z^2 / (m * mean(C)^2))
```

with the usual sample variance `s_z^2`; delta-method propagation may report `SE(R_m)` when `r_m>0`. These uncertainty diagnostics never alter membership or silently change the reducer. Their role is to expose when early-rung estimates are too noisy to interpret strongly. At M3, sampling error from the ladder is exactly zero.

### 3.11 Coverage and correlation diagnostics

For every configured training prefix `S_N` independently rescore full P_train in the accepted metric:

```text
d_x(S_N) = min_y d(x,y)
R_max(N) = max_x d_x(S_N)
D_mean(N) = mean_x d_x(S_N)
Q50/Q90/Q95/Q99 of d_x(S_N) under equal-frame mu_sel
selected-NN Q50/Q90/Q95
represented neutral-condition count
material-neutral frame-structural family support summaries
protected-event represented count/fraction
correlation-unit count and effective-sample diagnostics from accepted P1 evidence
explicit hard-obligation status, separately
```

`R_max` must be nonincreasing over nested prefixes. Historical `D_max` maps to `R_max`; historical unnormalized `D_sum`, `N95`, and uncovered-radius mass are not current authority.

Evaluation diagnostics include atom/component-mass discrepancy, condition-count discrepancy, correlation-unit coverage, and the candidate-specific ratio-estimator uncertainty diagnostic above.

### 3.12 Resource envelope

- current structural-provider construction must remain CPU-capable; no foundation/GPU prerequisite;
- fitted feature storage is `O(Nd)`; no persistent `N x N` matrix;
- local FPS uses `O(N)` nearest-distance state and is required only through K=max configured candidate size;
- worst-case scalar reference work is `O(KNd)` across the governed prefixes, with condition partitioning/vectorization allowed only under reference-equivalent semantics;
- split DP remains `O(C*M3)` states plus exact rational cost arithmetic;
- evaluation random priorities are `O(|M3| log |M3|)` sort work;
- coverage rescoring must be chunked/incremental without persistent dense quadratic state.

## 4. Stage-by-evidence authorization matrix

Legend: `A` method-relevant; `I` identity/support only; `D` diagnostic only; `H` explicit hard obligation only; `F` forbidden.

| Evidence class | U_size eligibility | P_train/M3 split | pi_train | pi_eval | soft diagnostics | hard qualification |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| canonical condition/provenance facts | I | A: condition depletion + component identity | A | I: hash/key only | A | H |
| raw geometry features | I | F | A, fit P_train | F | A | H only if separately explicit |
| universal frame structural features | F | F | A, fit P_train | F | A | H only if separately explicit |
| profile/environment extensions | F | F | F baseline | F | D | H only if separately accepted |
| fitted geometry metric/scaler | F | F | A | F | A | F |
| foundation descriptors/predictions | F | F | F | F | D after membership freeze | F |
| target-label residual/difficulty | F | F | F | F | D after membership freeze | F |
| protected-event evidence | I | A only through inherited split protection | D | F | A | H |
| correlation/duplicate/protected relations | I | A | D | D | A | H where explicitly named |
| candidate outcomes/reducer/CV/replay/physical validation | F | F | F | F | post hoc only | F |

No P_train-fitted evidence flows backward into the split. No M3 target label or candidate outcome influences either order.

## 5. Identity/currentness and stale descendants

Current target-order identity must bind at least:

- split-exclusion authority digest;
- split depletion-objective version and exact component membership;
- `P_train/M3` identities;
- `mu_sel` and evaluation-design identities;
- training weight-policy identity as part of the fixed experiment, without feeding it into membership;
- feature-provider/family names and provider policies;
- fitted transform parameters, type-7 quantile convention, family normalization;
- FP64 reference/tolerance semantics;
- K=max configured candidate N;
- `pi_train` and `pi_eval` digests;
- evaluation randomization policy/seed;
- hard-support-obligation policy.

Pre-repair empty-evidence/UID-order prepared generations are historical evidence only. A current method-version/schema boundary must require fresh `prepare` rather than default-field migration.

Target-order-dependent descendants become stale: aggregate/order identities, `T_N/M_i`, screen/reducer evidence, provisional/frozen target selections, and any downstream CV/production evidence whose exact selected membership descends from those orders. Unrelated authenticated source/P1 authority, normalized frame payloads, and other evidence not semantically dependent on the old order remain valid where their own identities still match. Common-training evidence is reusable only if it is independently bound to the same exact P_train and training-method identity; it is not reinterpreted across a changed P_train.

## 6. Revision-1 review closure map

| Review blocker | Revision-2 repair |
| --- | --- |
| B1 frame-count `pi_eval` vs force-component EVAL2 | removed condition-count evaluation scheduler; defined SRSWOR frame-cluster ratio estimator for exact component-weighted M3 estimand |
| B2 no evaluation approximation/error semantics | added finite-population sampling interpretation, frozen randomization, ratio-estimator uncertainty, and exact zero sampling error at M3 |
| B3 split lacked scientific allocation objective | added exact neutral-condition depletion-cost objective over protected components; geometry split scoring explicitly retired for baseline |
| B4 `mu_train` conflicted with training weights | separated `mu_sel`, `mu_loss`, and `mu_eval`; bound weight-policy identity without feeding weights backward into membership |
| B5 unratified arbitrary two-block metric | narrowed D1 claim; replaced raw-vs-structural block weighting with named equal-family baseline and mandatory sensitivity/ablation falsification |
| B6 numerical identity under-specified | froze type-7 quantiles, fixed coordinate order, median-medoid, exact integer deficit comparison, exact hash byte encoding, and dimension-aware FP64 tolerances |
| G1 anchor authority unclear | explicitly classified as method feasibility invariant, separate from optional hard qualification |
| G2 correlation role unjustified | explicitly defined N as configuration cardinality and correlation as split/diagnostic evidence, not effective-sample target |
| G3 kappa repackaging scope unclear | explicitly declared occurrence-lineage sensitivity; evaluation priority uses geometry before occurrence tie |
| G4 stale impact map absent | added bounded stale-descendant/preserved-evidence map |

## 7. Required falsification before promotion

Fresh independent review must attempt to falsify this revision with at least:

1. variable-atom-count M3 fixture proving the SRSWOR prefix estimator targets the exact component-weighted M3 ratio and exposing finite-prefix uncertainty;
2. heterogeneous within-condition force-error fixture demonstrating that no condition-quota claim is being smuggled into the estimator;
3. exact split fixture with two same-size feasible M3 subsets and different depletion costs; verify the lower-cost subset and protected-component closure;
4. split fixture showing additive depletion cost protects scarce support relative to UID/component-order baseline without claiming impossible geometry optimality;
5. real-family metric sensitivity/ablation including a rare local-structure case; material order instability under plausible regrouping is a D2 challenge;
6. type-7 quantile, scale-degeneracy, distance-tie, and higher-precision differential checks for the proposed FP64 envelopes;
7. direct simple-reference median-medoid/FPS/coverage scoring and optimized-kernel equivalence;
8. UID-renaming invariance outside genuine numerical ties, plus source-enumeration and feature-column permutation invariance;
9. source-repackaging test demonstrating only the explicitly allowed occurrence-tie/currentness consequences;
10. old-generation rejection plus dependency-bounded stale/preserved descendant checks;
11. current universal-structural producer-lineage authentication with no retired DATA6/DATA7 role authority imported;
12. CPU/resource benchmark ruling out dense quadratic state at representative K/N/d.

The prior author-side fixture remains supporting evidence for the interleaving concept, but is stale for the revised metric/evaluation/split semantics and cannot by itself close this revision.

## 8. Human ratification bundle

If fresh independent review passes, human ratification must accept or reject this bundle as one D1/D2 method:

- configuration-count target-size experiment under equal-frame selection/support measure;
- separate fixed training-loss influence policy;
- training-priority exact M3 split minimizing neutral-condition depletion over protected components;
- one medoid-seeded, condition-local exact FPS training order with exact proportional condition interleaving;
- frame-level raw + material-neutral structural-family coverage only, not exhaustive atomic-environment coverage;
- equal semantic-family metric weighting after robust type-7 scaling as the no-preference baseline;
- one frozen SRSWOR evaluation permutation and current unweighted EVAL2 ratio estimator, with finite-prefix sampling uncertainty treated diagnostically;
- exact numerical serialization/reduction/tolerance semantics above;
- no foundation/difficulty ordering, no historical quota schedule/radius threshold, and no GPU prerequisite.

Until both fresh independent review and explicit human ratification complete, permanent D1/D2 method papers and behavior-changing D3/D4 remain unchanged.