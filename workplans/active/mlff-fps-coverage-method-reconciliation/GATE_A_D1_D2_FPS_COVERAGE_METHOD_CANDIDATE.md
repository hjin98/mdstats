---
kind: d1-d2-authority-candidate
workplan_id: MLFF-FPS-COVERAGE-METHOD-RECONCILIATION-1
protocol_version: 6.3.0
status: proposed-awaiting-fresh-independent-review-and-human-ratification
proposal_date: 2026-09-13
revision: 3
revision_basis_review: GATE_A_REVISION_2_INDEPENDENT_REVIEW.md
branch: design/mlff-fps-coverage-method-reconciliation
project_state_basis: e8d04144f55c72d799ffcd3fe40c75e47078a66d
accepted_pem: hjin98/mdstats@4eabe2ae9783c7ff92f3a1093c37502a01380812:PROJECT-ENGINEERING-MEMORY.md
highest_affected_domain: D1
---

# Gate A D1/D2 candidate — FPS/coverage target-order method, Revision 3

## 0. Authority status

This is a repaired Gate A proposal, not current permanent authority. It supersedes Revision 2 of this candidate only. The permanent owners remain `docs/methods/mlff_scientific_method.md` and `docs/methods/mlff_numerical_algorithmic_method.md` until this revision passes a fresh independent D1/D2 Challenge review and explicit human ratification.

Revision 3 preserves the accepted V7 topology: one target-size population, one protected `P_train/M3` split, one `pi_train`, one `pi_eval`, exact nested prefixes, one prepared generation, no per-N selector or repair, no pre-target CV/label-domain fanout, and no restored FEAS/MVIDX/MVSEL/REPAIR/MVQUAL authority chain.

## 1. D1 scientific contract

### 1.1 Scientific question

The target-size experiment asks how one frozen MLFF training method behaves as the number of training configurations `N` increases under one candidate-independent data-construction policy. The intended experimental variable is configuration cardinality. For one prepared experiment, candidate membership therefore changes only by extending one frozen order.

Coverage is support evidence. It is not model adequacy, long-horizon stability, deployment validity, or physical transferability. EVAL2, post-selection cross-validation, replay, and downstream validation remain separate evidence.

### 1.2 Distinct measures

Three measures remain deliberately distinct.

**Selection/support measure `mu_sel`.** Every exact `P_train` configuration has equal membership mass `1/|P_train|`. Target size counts configurations, not loss weight and not effective independent samples.

**Training-loss influence measure `mu_loss`.** The frozen downstream training method may apply common per-configuration weights, property masks, and global objective coefficients. Those are fitted once over exact `P_train`, projected unchanged to every `T_N`, and bound into target-size experiment identity. They do not feed backward into membership construction.

**Evaluation estimand `mu_eval`.** EVAL2 is the exact M3 component-weighted force-error estimand because each admitted Cartesian force component contributes once:

```text
R_M3(f) = sqrt( sum_x SSE_x(f) / sum_x C_x )
C_x = 3 * n_atoms(x)
```

No equality among `mu_sel`, `mu_loss`, and `mu_eval` is claimed.

### 1.3 Training-critical neutral-condition support is hard split feasibility

Every neutral condition represented in `U_size` is training-critical for this baseline unless an upstream accepted policy has already excluded it from target-size eligibility. The `P_train/M3` split must therefore retain at least one frame from every eligible neutral condition in `P_train`.

Because protected-relation components are indivisible, exact reserve cardinality is feasible only if there exists a complete-component M3 subset satisfying all of:

```text
|M3| = configured m3
|P_train| >= N_max
for every eligible condition c: count(P_train,c) >= 1
all P1 split-excluding/protected relations remain unsplit
```

If no such split exists, preparation reports target-size split infeasibility. It does not erase a scarce condition, split a protected component, reduce M3 silently, or reinterpret later training anchors as a repair.

The later one-representative-per-condition training anchor is therefore a second, order-level consequence of already preserved support, not a substitute for split preservation.

### 1.4 Redundant residual support has two ordered meanings

Among hard-feasible exact splits, M3 should consume support that is redundant for training. Revision 3 makes this lexicographic and label-blind.

1. **Condition redundancy first.** Prefer reserve allocations that deplete a smaller fraction of scarce neutral-condition support.
2. **Structural redundancy second.** Within equal condition-depletion quality, prefer reserve components whose geometries/local-structure summaries have close analogues remaining elsewhere in `U_size`.

Structural uniqueness is not a new hard support class. Exact cardinality and hard condition preservation may force some structural loss. The method therefore treats structural redundancy as a secondary scientific objective and reports residual structural loss explicitly.

### 1.5 Structural coverage scope

The baseline claims frame-level coverage of:

- accepted raw physical geometry variables; and
- material-neutral frame-level summaries from the universal structural provider.

It does not claim exhaustive atomic-environment, profile-specific site, or material-specific event coverage. Those remain diagnostics or future authority unless separately accepted.

### 1.6 Training order meaning

Every nonempty neutral condition in `P_train` contributes one representative frame before ordinary proportional progression. This is a method-feasibility invariant: configured `N_min` must be at least the number of nonempty `P_train` conditions.

After anchors, condition counts track empirical P_train frame mass as closely as exact integer prefix cardinality permits. Inside a condition, successive frames expand the accepted frame-level structural coverage by exact FPS under the accepted metric.

### 1.7 Evaluation ladder is a realized probability design

`M3` is fixed first. Then, exactly once for the prepared target-size experiment and before any candidate training, an evaluation randomization operation draws one **uniform random permutation of the distinct M3 frame occurrences**, independently of frame values, labels, geometry, condition, model state, candidate state, or reducer outcomes.

The realized permutation is persisted as immutable experiment authority. After realization it is frozen and shared by every candidate and every screening boundary. Restarts reuse the same persisted permutation; they do not redraw. A genuinely new preparation that intentionally creates a new evaluation randomization is a different target-size experiment identity.

Therefore every prefix of size `m` is, under the randomization design, a simple random sample without replacement (SRSWOR) of M3 frame occurrences. Exact/canonical geometry duplicates remain distinct frame occurrences and participate independently in the randomization; they are not clustered by geometry hash.

For a model `f`, the prefix statistic

```text
r_m(f) = sum_{x in M_m} SSE_x(f) / sum_{x in M_m} C_x
R_m(f) = sqrt(r_m(f))
```

is the finite-population ratio estimator for the exact M3 ratio of totals. It is not claimed exactly unbiased at finite `m`. Its design uncertainty decreases with increasing `m` and is exactly zero at M3.

The same realized M_i membership is used for all candidates, preserving paired comparison. Sampling uncertainty remains diagnostic and does not silently alter the current reducer.

### 1.8 Correlation and cardinality

Target size intentionally counts configurations rather than effective independent samples. Correlation/protected relations govern split exclusion and remain diagnostics after the split. This is an explicit interpretation limitation: increasing N with highly correlated frames may yield less information gain than increasing N with independent frames.

### 1.9 Hard versus soft evidence

Only explicit `hard_support_obligations` qualify/reject exact candidate prefixes after order construction. The split-level one-condition-preservation rule is not an optional prefix obligation; it is part of baseline experiment feasibility. FPS distance, structural uniqueness, coverage radii, event counts, correlation diagnostics, environment summaries, and evaluation sampling-uncertainty measures remain soft.

### 1.10 Excluded dependencies

No foundation-model inference, target-label residual, candidate outcome, CV state, replay state, or downstream reducer result may influence the split, `pi_train`, or `pi_eval`. Preparation remains CPU-capable and does not require a GPU/model-provider prerequisite.

## 2. D2 numerical contract

### 2.1 Scientific occurrence key

Lexical `frame_uid` spelling is not a scientific priority. Define `kappa(x)` from the authenticated occurrence fields:

```text
schema = "mdstats.target-order-scientific-occurrence-key.v2"
condition_id
source_identity_signature
source_frame_index
geometry_fingerprint
```

using the exact byte encoding in Section 2.2. `kappa` distinguishes authenticated occurrences. Source repackaging that changes source identity creates a new prepared-generation identity. Outside exact numerical ties, `kappa` does not steer the training metric/FPS score.

For a protected component, the component key is the digest of the sorted member `kappa` values plus the canonical P1 protected-relation identity.

### 2.2 Canonical hash byte encoding

All D2 identity hashes use SHA-256 over an ordered length-prefixed byte sequence. For each UTF-8 field `v`, append:

```text
uint64_big_endian(len(utf8(v))) || utf8(v)
```

Integer fields are encoded in the explicitly stated fixed-width unsigned big-endian representation. No JSON mapping order, delimiter convention, locale, or Python object identity participates.

### 2.3 Canonical structural feature families

Every coordinate entering a target-order metric belongs to exactly one semantic family.

Raw families are exactly:

```text
cell_geometry
strain
pair_geometry
```

with raw-coordinate ownership:

```text
cell_geometry:
  cell_volume_angstrom3
  mass_density_g_cm3
  cell_length_a_angstrom
  cell_length_b_angstrom
  cell_length_c_angstrom
  cell_angle_alpha_degrees
  cell_angle_beta_degrees
  cell_angle_gamma_degrees

strain:
  hydrostatic_strain
  deviatoric_strain_norm
  engineering_shear_xy
  engineering_shear_xz
  engineering_shear_yz

pair_geometry:
  for every active RawFeaturePolicy pair rule, in lexical rule_id order:
    minimum_pair_distance_angstrom
    mean_nearest_neighbor_distance_angstrom
    maximum_nearest_neighbor_distance_angstrom
    coordination_mean
    coordination_maximum
```

Universal structural coordinates are not assigned by parsing display-name strings. The universal provider must publish one ordered `coordinate_family_ids` sequence aligned one-to-one with `feature_names`. Every family ID must be one of exactly:

```text
pair_distance
radial_environment
coordination
connectivity
chemical_environment
local_density
angular_environment
orientational_order
```

The complete `(feature_name, family_id)` table is part of provider identity and target-order metric identity. Missing, duplicate, unknown, reordered-without-identity-change, or ambiguously mapped coordinates are fatal evidence errors. If the current provider representation lacks this explicit table, D3/D4 must expose it from the existing provider semantics rather than infer a second taxonomy downstream.

### 2.4 One canonical scalar transform and distance reference

All discrete membership decisions are defined by one canonical scalar binary64 reference. There is **no fuzzy score-tie tolerance in normative membership semantics**.

For the chosen fit population, rows are ordered by `kappa`; coordinates are ordered by `(family_id, feature_name)`.

For each numerical coordinate:

1. observed values are sorted by IEEE-754 binary64 numerical order;
2. quantiles use Hyndman-Fan type 7:

```text
h=(n-1)p
i=floor(h)
r=h-i
Q_p=(1-r)*x[i] + r*x[min(i+1,n-1)]
```

with scalar binary64 operations evaluated in the written order;
3. center is `Q_0.5`;
4. scale is `Q_0.75-Q_0.25`;
5. if and only if the resulting binary64 scale compares exactly equal to `0.0`, fallback scale is the maximum scalar-binary64 `abs(x-Q_0.5)` over observed values in canonical row order;
6. if fallback also equals `0.0`, the coordinate is constant and its transformed numerical value is exactly zero;
7. otherwise transformed value is scalar-binary64 `(x-center)/scale`;
8. missing values are replaced by the observed median before transformation, and one binary missingness coordinate is appended if any row is missing that source coordinate.

Each semantic family is then divided by scalar-binary64 `sqrt(d_f)`, where `d_f` is the transformed family dimension including active missingness coordinates. The final squared Euclidean distance is accumulated left-to-right in canonical coordinate order using scalar binary64 multiply then add; fused contraction is not the reference semantics.

A score tie exists only when the canonical reference scores compare exactly equal as binary64 values. Exact score ties use `kappa` or component key as the declared secondary key.

Optimized/vectorized/parallel implementations are permitted only when they reproduce the same discrete reference decisions. If an optimized path cannot establish the same winner/order, it must fall back to canonical scalar reference recomputation for the governing comparison. D2 therefore does not rely on an unvalidated numerical tolerance to decide membership.

### 2.5 Two fit domains, one metric definition

The same family/transform/distance definition is used in two separately identified fitted metrics.

**Pre-split metric `d_U`.** Fit on exact `U_size` geometry/structural evidence only. It is used only to evaluate structural redundancy among protected components before `P_train/M3` is chosen. No target label, model prediction, or candidate outcome enters it.

**Training-order metric `d_P`.** After the split, refit the same metric definition on exact `P_train`. It governs condition representatives, FPS, and training-prefix coverage diagnostics.

The two fitted metric identities are distinct and both are bound into the prepared experiment lineage. M3 labels never fit either metric.

### 2.6 Hard-feasible exact split and lexicographic objective

Let protected components be `g=1..G`; `z_g=1` means component g is assigned to M3. Let `w_g` be component size, `n(g,c)` its count in condition c, and `N_c` the U_size count of condition c.

Hard constraints are:

```text
z_g in {0,1}
sum_g w_g z_g = m3
for every eligible condition c:
  sum_g n(g,c) z_g <= N_c - 1
```

The exact-size condition already implies `|P_train|=|U_size|-m3`; ordinary policy admission separately requires that value be at least `N_max`.

Among hard-feasible subsets, optimize lexicographically.

**Objective 1 — neutral-condition depletion**

```text
J_condition = sum_g z_g * sum_c n(g,c)/N_c
```

All rational comparisons are exact integer/rational comparisons.

**Objective 2 — structural uniqueness removed from training**

For each component g and member frame x, define

```text
u_x = min_{y in U_size, y not in g} d_U(x,y)
```

and component uniqueness

```text
U_g = max_{x in g} u_x.
```

If no frame exists outside g, the component cannot participate in any proper split and the split is infeasible unless m3 is zero. `U_g` is computed by the canonical scalar reference.

Then

```text
J_structure = sum_g z_g * U_g
```

with component terms accumulated in ascending component-key order by canonical scalar binary64 arithmetic. Lower is better: components with close analogues outside themselves are preferred for M3 over structurally isolated components.

**Objective 3 — deterministic tie**

If both objectives compare exactly equal under their own canonical semantics, choose the lexicographically smaller sorted component-key tuple.

The numerical solver may be sparse dynamic programming, branch-and-bound, or another exact method, but it must return the same lexicographic optimum. A heuristic/greedy approximation is nonconforming. Solver resource exhaustion is an explicit preparation failure, not permission to change the objective.

### 2.7 Condition representative and local FPS

For each nonempty P_train condition:

1. compute the coordinate-wise type-7 median vector in fitted `d_P` coordinates;
2. choose the frame minimizing canonical squared distance to that median vector;
3. exact score ties use `kappa`;
4. initialize exact FPS with that medoid;
5. repeatedly choose the remaining frame maximizing its canonical nearest-selected squared distance; exact score ties use `kappa`.

Nearest-distance state may be updated incrementally. No persistent dense pairwise matrix is required.

### 2.8 Global training interleaving

Let `N_c` be P_train frame count in condition c, `N=sum_c N_c`, and `s_c(k)` emitted count after k ranks.

**Anchor phase:** emit one condition medoid from every condition, ordered by decreasing `N_c`, then canonical condition ID.

**Proportional phase:** among nonexhausted conditions choose the one maximizing the exact integer deficit numerator

```text
D_c(k+1) = (k+1)*N_c - s_c(k)*N.
```

Exact ties use canonical condition ID. Emit the next frame from that condition's local FPS queue.

FPS governs through `K=max(configured candidate_sizes)`. The remaining persisted-permutation tail uses the same exact condition scheduler with within-condition remainder ordered by `kappa`. No configured `T_N` may intersect the tail. Changing K changes target-order method identity.

Every candidate is exactly `T_N=pi_train[:N]`.

### 2.9 Exact evaluation randomization algorithm

The evaluation randomization consumes the canonical list of distinct M3 frame occurrences sorted by `kappa` and produces one exact uniform random permutation with Fisher-Yates.

For `i = |M3|-1, |M3|-2, ..., 1`:

1. let `b = ceil(log2(i+1))`;
2. draw exactly `b` independent unbiased random bits from the experiment randomization source;
3. interpret them as nonnegative integer `r`;
4. if `r > i`, discard those bits and repeat step 2;
5. otherwise swap positions `i` and `r`.

This rejection rule makes each accepted `r` exactly uniform on `{0,...,i}`, hence the realized permutation is exactly uniform over all M3 occurrence permutations under the assumption that the supplied random bits are independent and unbiased.

The randomization source is an execution dependency whose required scientific property is independent unbiased bits obtained independently of scientific/candidate data. The realized permutation, randomization-method version, source-class identity, creation event identity, and an audit digest are persisted. Raw entropy need not be retained once the permutation is authenticated; the permutation itself is the immutable realized design authority.

Restart validates and reuses the stored permutation. It does not regenerate from a deterministic hash or redraw. A new randomization event changes experiment identity.

### 2.10 Evaluation ratio estimator and uncertainty

For a realized SRSWOR prefix of m frames:

```text
Y_x = SSE_x(f)
C_x = 3*n_atoms(x)
r_m = sum Y_x / sum C_x
R_m = sqrt(r_m)
```

A diagnostic first-order design standard error for `r_m` may use

```text
z_x = Y_x - r_m*C_x
SE(r_m) ~= sqrt((1-m/M)*s_z^2 / (m*mean(C)^2))
```

where `M=|M3|`, `s_z^2` is the ordinary sample variance over sampled frames, and `mean(C)` is the sampled mean component count. Delta-method `SE(R_m)` may be reported for positive `r_m`. This approximation is diagnostic only; it does not gate candidates or change the reducer. At M3 the evaluation-ladder sampling error is exactly zero.

### 2.11 Coverage and split diagnostics

Training-prefix diagnostics include:

```text
R_max(N)
D_mean(N)
Q50/Q90/Q95/Q99 nearest-selected distance
selected-NN Q50/Q90/Q95
represented neutral-condition count
material-neutral family support summaries
protected-event represented count/fraction
correlation-unit/effective-sample diagnostics
explicit hard-obligation status separately
```

`R_max` must be nonincreasing over nested prefixes.

Split diagnostics report per-condition retained/reserve counts, `J_condition`, component `U_g`, total `J_structure`, and the most structurally unique support placed in M3. These are audit evidence for the accepted split objective, not additional gates after allocation.

Evaluation diagnostics report atom/component-mass discrepancy of each realized prefix, condition/correlation summaries, and the diagnostic ratio-estimator uncertainty above.

### 2.12 Resource envelope

- universal structural evidence remains CPU-capable; no foundation/GPU prerequisite;
- fitted feature matrices are `O(Nd)` storage;
- no persistent dense `N x N` distance matrix is allowed;
- pre-split component uniqueness may use chunked nearest-neighbor evaluation under `d_U` with `O(Nd)` persistent state and bounded temporary chunks;
- exact constrained split solving may use sparse DP/branch-and-bound; approximation is forbidden, and solver exhaustion is explicit infeasibility/resource failure rather than silent semantic relaxation;
- training FPS stores `O(N)` nearest-distance state and runs only through K=max configured candidate size;
- evaluation Fisher-Yates is `O(|M3|)` time and `O(|M3|)` permutation state.

## 3. Stage-by-evidence authorization

| Evidence class | U_size eligibility | split | pi_train | pi_eval | diagnostics | hard qualification |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| canonical condition/provenance | I | A | A | I occurrence identity only | A | H |
| raw geometry | I | A through pre-split d_U | A through d_P | F | A | H only if separately explicit |
| universal frame structural features | F | A through pre-split d_U | A through d_P | F | A | H only if separately explicit |
| profile/environment extension | F | F baseline | F baseline | F | D | H only if separately accepted |
| fitted d_U | F | A | F | F | A | F |
| fitted d_P | F | F | A | F | A | F |
| foundation prediction/residual/difficulty | F | F | F | F | D after membership freeze | F |
| protected/correlation/duplicate relations | I | A hard component authority | D | D | A | H where explicitly named |
| candidate/CV/replay/production outcomes | F | F | F | F | post hoc only | F |
| evaluation random bits/permutation | F | F | F | A, after M3 only | A | F |

No target label, candidate outcome, or P_train-fitted training evidence flows backward into split selection. Evaluation randomization occurs only after M3 membership is fixed.

## 4. Identity/currentness

Prepared target-order identity binds at least:

- P1 split-exclusion authority;
- exact U_size and M3 policy identities;
- hard neutral-condition preservation rule;
- pre-split metric definition/provider/family mapping and fitted d_U identity;
- split objective version, exact selected components, `J_condition`, and `J_structure` identities;
- exact P_train identity;
- training-order metric definition/provider/family mapping and fitted d_P identity;
- scalar reference arithmetic/version and type-7 quantile convention;
- K=max candidate N;
- pi_train digest;
- evaluation randomization method version, realized pi_eval digest, randomization-event identity, and source-class/audit identity;
- mu_sel/mu_loss/mu_eval method identities;
- hard-support-obligation policy.

Pre-repair empty-evidence/UID-order generations and Revision-1/Revision-2 experimental candidates are historical only. No default migration may relabel them as Revision-3 evidence.

Target-order-dependent descendants become stale: aggregate/order identities, T_N/M_i, screening/reducer evidence, provisional/frozen target selections, and downstream CV/production evidence whose exact membership descends from those orders. Unrelated authenticated source/P1 evidence remains valid where its own identity matches. Common training evidence is reusable only if independently bound to the same exact P_train and training-method identity.

## 5. Revision-2 blocker closure map

| Revision-2 blocker | Revision-3 repair |
| --- | --- |
| R2-B1 false SRSWOR from deterministic/geometry hash | replaced by one realized exact Fisher-Yates permutation over unique M3 occurrences using independent unbiased random bits; persisted permutation is frozen experiment authority |
| R2-B2 condition extinction possible at split | every eligible U_size neutral condition is now a hard split-feasibility constraint with at least one P_train frame retained |
| R2-B3 structurally unique support could lose component-key tie | added pre-split U_size-fitted structural metric d_U and lexicographic component uniqueness cost after condition depletion |
| R2-B4 family mapping ambiguous | universal provider must publish complete one-to-one feature-name/family-id table from an exact allowed family set, bound into provider/metric identity |
| R2-B4 unvalidated fuzzy tie tolerance | removed tolerance from membership semantics; one scalar binary64 reference defines exact winners and optimized paths must reproduce discrete decisions/fallback to reference |

## 6. Required falsification before promotion

Fresh independent review must realize, not merely restate, at least:

1. uniform-permutation reference check on small M3 by enumerating Fisher-Yates transition probabilities or exhaustive/mock unbiased-bit paths;
2. geometry-duplicate evaluation fixture proving duplicate occurrences are not clustered by design;
3. variable-atom-count EVAL2 ratio-estimator fixture and finite-prefix uncertainty check;
4. split condition-extinction counterexample proving infeasibility instead of silent condition loss;
5. same-condition 99-near-duplicate + one-unique-mode split fixture proving the structural uniqueness objective retains the unique mode when an equal-condition-cost redundant alternative exists;
6. mixed protected-component split fixture and exact constrained-solver/reference comparison;
7. complete provider coordinate-to-family mapping validation and family-regrouping sensitivity/ablation;
8. scalar-reference type-7/scale/distance/medoid/FPS tests plus optimized-vs-reference discrete-order equivalence;
9. UID-renaming, input enumeration, feature-column-order metamorphic checks;
10. stale-generation and bounded dependency-impact negatives;
11. current universal-structural provider-lineage authentication;
12. representative CPU/resource benchmark for pre-split uniqueness + K-bounded FPS with no dense persistent quadratic state.

## 7. Human ratification bundle

If fresh independent review passes, human ratification must accept or reject this method as one bundle:

- configuration-count target-size experiment under equal-frame selection/support measure;
- separate fixed training-loss influence policy;
- exact protected split that hard-preserves every eligible neutral condition in P_train;
- lexicographic reserve objective: condition depletion first, structural redundancy second;
- pre-split U_size metric for redundancy and separately refitted P_train metric for training order;
- one medoid-seeded condition-local exact FPS order with proportional condition interleaving;
- frame-level raw + material-neutral structural-family coverage only;
- complete provider-owned coordinate-to-family mapping and equal family mass baseline;
- canonical scalar binary64 reference with no fuzzy membership tolerance;
- one exact realized SRSWOR Fisher-Yates evaluation permutation over distinct frame occurrences, frozen after experiment initialization;
- existing component-weighted EVAL2 ratio estimator with sampling uncertainty diagnostic only;
- no foundation/difficulty ordering, no historical quota schedule/radius threshold, and no GPU prerequisite.

Until a fresh independent review passes and the human owner ratifies Revision 3, permanent D1/D2 and behavior-changing D3/D4 remain unchanged.