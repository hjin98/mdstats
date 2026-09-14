---
kind: d1-d2-authority-candidate
workplan_id: MLFF-FPS-COVERAGE-METHOD-RECONCILIATION-1
protocol_version: 6.3.0
status: proposed-awaiting-fresh-independent-review-and-human-ratification
proposal_date: 2026-09-13
revision: 4
revision_basis_review: GATE_A_REVISION_3_INDEPENDENT_REVIEW.md
branch: design/mlff-fps-coverage-method-reconciliation
project_state_basis: e8d04144f55c72d799ffcd3fe40c75e47078a66d
branch_basis_merge: 9a016f6087066c036c78b13c933bf3ddf30c5cc5
accepted_pem: hjin98/mdstats@4eabe2ae9783c7ff92f3a1093c37502a01380812:PROJECT-ENGINEERING-MEMORY.md
highest_affected_domain: D1
---

# Gate A D1/D2 candidate — FPS/coverage target-order method, Revision 4

## 0. Authority state

This is a proposed D1/D2 contract, not current permanent authority. It supersedes Revision 3 of this Gate A candidate only. Permanent D1/D2 remain `docs/methods/mlff_scientific_method.md` and `docs/methods/mlff_numerical_algorithmic_method.md` until this proposal passes fresh independent falsification and explicit human ratification.

The branch ancestry has been reconciled to accepted project state `e8d04144...` by merge commit `9a016f60...`; the accepted D1/D2 method-paper blobs were byte-identical across that ancestry reconciliation.

Revision 4 preserves the V7 topology: one target-size population, one protected `P_train/M3` split, one `pi_train`, one `pi_eval`, exact nested prefixes, one immutable prepared generation, no per-N selector/repair, no label-domain target-size fanout, and no restored FEAS/MVIDX/MVSEL/REPAIR/MVQUAL product topology.

## 1. Historical applicability and preserved capabilities

The accepted Project Engineering Memory (PEM) remains evidence only. The materially applicable dispositions are unchanged:

- SP-001: one real owner; reduce duplicated selector machinery;
- FF-005: downstream consumers must not rebuild preparation-owned scientific state;
- SP-002: fail closed on stale/mismatched authority;
- SP-003: persist expensive evidence once and reuse it;
- SP-004: final implementation evidence must exercise the real owner/path.

Historical DATA7 and MVSEL/MVQUAL evidence supports the capability hypotheses of representative anchors, frame-level farthest-point sampling (FPS), structural coverage diagnostics, and independent rescoring. Historical fixed quota fractions, radius thresholds, target-label difficulty ordering, and retired public selector topology are not promoted by history alone.

## 2. D1 scientific contract

### 2.1 Scientific question

The target-size experiment asks how one frozen machine-learned force-field (MLFF) training method behaves as the number of training configurations `N` increases under one frozen candidate-independent data-construction policy. Candidate membership changes only by extending one precomputed training order.

Coverage is support evidence. It does not establish model accuracy, force-field transferability, dynamical stability, or deployment adequacy. Those remain separate EVAL2, post-selection cross-validation, replay, final-production, and physical-validation questions.

### 2.2 Three distinct measures

**Selection/support measure `mu_sel`.** Every exact `P_train` configuration has equal mass `1/|P_train|`. Target size is configuration cardinality, not optimization weight and not effective independent sample count.

**Training-loss influence measure `mu_loss`.** The frozen downstream training method may apply accepted common per-configuration weights, property masks, and global objective coefficients. They are fitted once on exact `P_train`, projected unchanged to every `T_N`, and bound into experiment identity. They do not choose membership.

**Evaluation estimand `mu_eval`.** Exact M3 owns the component-weighted force-error estimand used by EVAL2:

```text
R_M3(f) = sqrt( sum_x SSE_x(f) / sum_x C_x )
C_x = 3 * n_atoms(x)
```

No equality among these three measures is claimed.

### 2.3 Training-critical condition support is hard split feasibility

Every neutral condition admitted to `U_size` is training-critical for this baseline. A valid `P_train/M3` split must preserve at least one frame from every such condition in `P_train`, preserve complete P1 split-excluding/protected components, satisfy exact `|M3|=m3`, and leave `|P_train| >= N_max`.

If no exact component allocation satisfies all of those simultaneously, preparation reports target-size split infeasibility. It does not erase a condition, split a protected component, reduce M3 silently, or relax exactness.

### 2.4 “Redundant residual support” is a retained-set concept

Training support has priority. Among exact hard-feasible splits, M3 should preferentially consume support that is redundant relative to what actually remains available for training.

Condition redundancy remains the first objective: reserve selection should minimize fractional depletion of scarce neutral-condition support.

Structural redundancy is second and is **dynamic with respect to the current retained set**. A component is structurally redundant only to the extent that its frames have close analogues among frames that are still retained at the moment that component is considered for removal. Two components are not allowed to certify one another as permanently redundant and then both disappear without re-evaluation.

This is deliberately a deterministic retained-set greedy criterion inside the set of globally condition-optimal exact completions. It is not claimed to be a global optimum of final training-set covering radius. If exact cardinality/protected constraints force removal of structurally distinctive support, that loss is reported rather than disguised.

### 2.5 Structural-coverage scope

The baseline claims frame-level support across:

1. universal cell/strain geometry; and
2. material-neutral element-resolved summaries of universal local-structure features.

It does **not** claim exhaustive atomic-environment, material-profile group, site-class, or material-specific event coverage. Profile-declared groups and profile-extension features are excluded from baseline membership authority.

### 2.6 Training-order meaning

Every nonempty P_train neutral condition contributes one representative medoid before ordinary progression. Therefore configured `N_min` must be at least the number of nonempty P_train conditions.

After the anchor phase, the number of selected frames per condition tracks empirical P_train frame mass as closely as exact integer prefixes permit. Within each condition, exact FPS progressively expands the accepted frame-level structural support.

### 2.7 Evaluation ladder is one realized probability design

After M3 membership freezes and before candidate training, exactly one uniform random permutation of the **distinct M3 frame occurrences** is drawn independently of scientific values, geometry, labels, candidate state, model outcomes, and reducer state. The realized permutation is persisted as immutable experiment authority and reused on restart.

Therefore every prefix `M_i` is, under the randomization design, a simple random sample without replacement (SRSWOR) of M3 frame occurrences. Geometry duplicates remain distinct occurrences and are randomized independently.

For prefix size `m`,

```text
r_m(f) = sum_{x in M_m} SSE_x(f) / sum_{x in M_m} C_x
R_m(f) = sqrt(r_m(f))
```

is the finite-population ratio estimator for exact M3 component-weighted mean squared force error. It is not claimed exactly unbiased at finite m. The same realized membership is shared by all candidates at a rung, and ladder sampling uncertainty is diagnostic only. At full M3, ladder sampling error is zero.

### 2.8 Correlation and effective independence

Target size intentionally counts configurations rather than effective independent samples. Correlation/protected relations govern split exclusion and remain diagnostics after splitting. Increasing N with correlated frames may therefore carry less information gain than increasing N with independent frames; this is an explicit interpretation limitation, not a hidden redefinition of N.

### 2.9 Hard versus soft evidence

The split-level condition-retention invariant is baseline method feasibility. After order construction, only explicit accepted `hard_support_obligations` may qualify/reject prefixes. FPS distances, retained-set redundancy scores, coverage radii/quantiles, event counts, environment summaries, correlation diagnostics, and evaluation sampling-uncertainty measures remain soft evidence.

### 2.10 Forbidden membership dependencies

Foundation-model predictions, target-label residual/difficulty, candidate outcomes, cross-validation state, replay state, reducer state, and downstream physical evidence may not influence the split, `pi_train`, or `pi_eval`. Preparation remains CPU-capable and requires no model/GPU provider.

## 3. D2 numerical contract

### 3.1 Scientific occurrence and component identity

Lexical `frame_uid` spelling is not a score. Define `kappa(x)` from:

```text
schema = "mdstats.target-order-scientific-occurrence-key.v2"
condition_id
source_identity_signature
source_frame_index
geometry_fingerprint
```

with the canonical byte encoding below. Source repackaging that changes authenticated source identity creates a new prepared-generation identity. Outside exact numerical ties, occurrence identity does not steer geometry scores.

A protected-component key is the digest of its sorted member `kappa` values plus canonical P1 protected-relation identity.

### 3.2 Canonical hash encoding

For every ordered UTF-8 string field `v`, encode

```text
uint64_big_endian(len(utf8(v))) || utf8(v)
```

and concatenate fields in the stated order before SHA-256. Fixed-width integer fields use the explicitly named unsigned big-endian width. JSON mapping order, delimiters, locale, and Python object identity are excluded.

### 3.3 Baseline target-order feature substrate is explicitly material-neutral

Revision 4 no longer imports arbitrary active raw pair rules or material-profile aggregation into membership.

#### 3.3.1 Universal raw geometry

The raw geometry coordinates are exactly:

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
```

Target labels, force/stress/pressure statistics, instantaneous-temperature labels, and `RawFeaturePolicy.pair_rules` are excluded from the target-order metric. Pair-rule geometry is omitted because the accepted current raw policy may be material/profile-specific; local pair/environment geometry is supplied by the neutral structural view below.

Raw coordinates form two semantic families: `cell_geometry` for volume/density/length/angle coordinates and `strain` for hydrostatic/deviatoric/shear coordinates.

#### 3.3.2 Neutral local-structure policy

The numerical local-structure owner is `mdstats.analysis.local_structure`. The target-order method freezes this `LocalStructureFeaturePolicy`:

```text
policy_version = "mdstats.analysis.local-structure.2026-07.v1"
normalized_switch_start = 1.15
normalized_switch_end = 1.75
radial_centers_angstrom = (1.0,1.5,2.0,2.5,3.0,3.5,4.0,5.0)
radial_width_angstrom = 0.35
density_radius_angstrom = 4.0
angular_legendre_orders = (1,2,3,4)
orientational_orders = (4,6)
minimum_weight = 1e-8
coincident_tolerance_angstrom = 1e-8
fallback_covalent_radius_angstrom = 1.0
```

`maximum_dense_pair_work` is an execution/resource guard rather than a metric coordinate; it may vary only if feature values remain identical and resource policy admits the change.

Frame aggregation for target ordering is a dedicated neutral view:

```text
include_declared_atom_groups = false
include_element_groups = true
materialize_atomic_environments = false
aggregate_statistics = (mean,std,min,max,q10,q50,q90)
profile/material atom-group membership = forbidden
profile phase-geometry plan = forbidden
```

The element set is the sorted union of atomic numbers in exact `U_size`; this same coordinate schema is used by both fitted metrics `d_U` and `d_P`. For each element Z, enabled local feature F, and aggregate statistic s, one coordinate is named semantically as `(element_Z, F, s)`. Frame-level `atom_count` and `atom_fraction` aggregation coordinates are excluded from the structural metric because composition support is already a neutral-condition axis.

The enabled local feature families are exactly:

```text
pair_distance:
  nearest_neighbor_distance_angstrom
  weighted_neighbor_distance_mean_angstrom
  weighted_neighbor_distance_std_angstrom
coordination:
  smooth_coordination
connectivity:
  hard_neighbor_count
  weighted_degree_l2
chemical_environment:
  neighbor_species_entropy
local_density:
  local_number_density_angstrom^-3
radial_environment:
  radial_density_r*.angstrom coordinates generated by the frozen radial centers
angular_environment:
  angular_legendre_l1 ... angular_legendre_l4
orientational_order:
  bond_orientational_q4, bond_orientational_q6
```

For generated radial names the canonical owner is the frozen `LocalStructureFeaturePolicy.feature_names`; the semantic family rule is the `radial_density_r` prefix. No display-string parsing is permitted for any other family. The complete generated coordinate list and family IDs are persisted as metric identity.

A frame lacking center atoms for one element has those element-resolved aggregate coordinates marked missing; it does not receive profile-dependent substitutes.

### 3.4 Canonical robust transform with an explicit conditioning floor

Rows are canonicalized by `kappa`; coordinates by `(family_id, semantic_coordinate_name)`.

Quantiles use Hyndman-Fan type 7. For sorted observed binary64 values `x[0..n-1]` and p:

```text
h=(n-1)p
i=floor(h)
r=h-i
Q_p=(1-r)*x[i] + r*x[min(i+1,n-1)]
```

with scalar binary64 operations in the written order.

Let

```text
u = 2^-53
tau = sqrt(u)
M = max_i |x_i|
rho = tau * M
m = Q_0.5
s_iqr = Q_0.75 - Q_0.25
s_dev = max_i |x_i - m|
```

If `M == 0`, the numerical coordinate is constant. Otherwise:

```text
if s_iqr >= rho:      scale = s_iqr
elif s_dev >= rho:    scale = s_dev
else:                 coordinate is numerically unresolved and transforms to zero
```

Missing observed values are imputed with the observed median before transformation; if a source coordinate is ever missing, append a separate binary missingness coordinate even when the numerical coordinate is unresolved.

The `sqrt(u)` relative floor is a D2 conditioning rule, not a score-tie tolerance. It prevents relative binary64 perturbations of order u from being amplified above order `sqrt(u)` solely by division through a near-zero empirical scale. Because `rho` scales with `M`, the criterion is invariant to positive linear unit rescaling. Rare genuine excursions remain representable: when IQR is collapsed but maximum deviation exceeds `rho`, `s_dev` becomes the fallback scale rather than deleting the coordinate.

If a future provider declares a stronger coordinate-specific numerical resolution bound than `rho`, the stronger bound controls and changes metric identity.

### 3.5 Family normalization and distance

Every transformed semantic family f is divided by `sqrt(d_f)`, where `d_f` counts its active numerical and missingness coordinates. Each accepted family therefore receives equal nominal Euclidean mass before observed variation. This remains the explicit no-prior-weight baseline and must pass sensitivity/ablation falsification before promotion.

The metric is scalar binary64 Euclidean distance over the concatenated family-normalized coordinates. There is no PCA, whitening, learned weighting, randomized projection, foundation descriptor, or profile-specific block.

### 3.6 Canonical scalar numerical reference

All discrete membership decisions are owned by one scalar binary64 reference. Squared distances use canonical coordinate order and scalar multiply then left-to-right add; fused contraction is not reference semantics.

A score tie exists only when canonical reference scores compare exactly equal as binary64 values. Ties use `kappa` or component key as the declared secondary identity.

Optimized/vectorized/parallel paths are admissible only when they reproduce the same discrete selections. When they cannot establish the same winner, they must recompute the governing comparison with the canonical scalar reference. There is no fuzzy winner/tie tolerance.

### 3.7 Two fitted metrics with no circularity

The metric definition is identical but fit domains differ:

- `d_U`: fit on exact U_size geometry/neutral structural evidence. It is used only by the pre-split retained-set redundancy method.
- `d_P`: refit after the split on exact P_train. It governs condition medoids, local FPS, and training-prefix coverage diagnostics.

The coordinate schema is fixed from U_size, but fitted medians/scales/missingness statistics for `d_P` use P_train only. No M3 label or candidate outcome fits either metric.

### 3.8 Exact hard feasibility and globally optimal condition depletion

Let protected components be g=1..G, with binary final reserve indicator `z_g`, component size `w_g`, condition counts `n(g,c)`, and U_size condition counts `N_c`.

Hard final constraints are:

```text
z_g in {0,1}
sum_g w_g z_g = m3
for every eligible c: sum_g n(g,c) z_g <= N_c - 1
|U_size| - m3 >= N_max
```

Among these exact-feasible final subsets define

```text
J_condition(S) = sum_{g in S} sum_c n(g,c)/N_c
J* = minimum hard-feasible J_condition.
```

Rational comparison of `J_condition` is exact. If no hard-feasible exact subset exists, preparation fails as split infeasible.

### 3.9 Dynamic retained-set structural redundancy within J*-optimal completions

Initialize removed reserve components `S_0=empty` and retained frames `R_0=U_size`. At step t, a not-yet-removed component g is **completion-admissible** iff there exists at least one final reserve `S_final` such that:

```text
S_t union {g} is a subset of S_final
S_final satisfies every hard constraint
J_condition(S_final) = J*
```

For each completion-admissible g, calculate against the **current retained set after candidate removal**:

```text
q_x(g | R_t) = min_{y in R_t \ g} d_U(x,y)^2
H_max(g | R_t) = max_{x in g} q_x
H_mean(g | R_t) = mean_{x in g} q_x
```

Choose the lexicographically smallest tuple

```text
(H_max, H_mean, component_key)
```

under the canonical scalar reference, remove that complete component, update the retained set, and repeat until exact removed frame count equals m3.

The completion oracle is exact: it may use memoized sparse dynamic programming, branch-and-bound, mixed-integer search, or another solver, but it may not reject a genuinely feasible J*-optimal completion because a heuristic traversal missed it. Resource exhaustion is an explicit preparation failure.

Because structural scores are recomputed after each removal, two mutually redundant components cannot both continue to use each other as retained analogues. Removing one changes the score of the other before any subsequent decision.

This method is not claimed to minimize final global covering radius over all possible P_train sets. Its accepted meaning is narrower: preserve globally minimal condition depletion, then greedily consume currently redundant structural support while continuously preserving exact completion feasibility.

### 3.10 P_train condition representatives and exact FPS

For each nonempty P_train condition:

1. compute the coordinate-wise type-7 median vector in fitted d_P coordinates;
2. choose the frame minimizing canonical squared distance to that vector;
3. exact score ties use `kappa`;
4. initialize exact FPS with that medoid;
5. repeatedly emit the remaining frame maximizing canonical nearest-selected squared distance; exact ties use `kappa`.

Nearest-distance state may be updated incrementally; no persistent dense pairwise matrix is required.

### 3.11 Global `pi_train`

Let `N_c` be P_train frame count in condition c, `N=sum_c N_c`, and `s_c(k)` emitted count after k ranks.

Anchor phase: emit one condition medoid from every condition, ordered by decreasing N_c then canonical condition ID.

Proportional phase: among nonexhausted conditions maximize the exact integer deficit

```text
D_c(k+1) = (k+1)*N_c - s_c(k)*N.
```

Exact ties use canonical condition ID. Emit that condition's next FPS frame.

FPS governs through `K=max(configured candidate_sizes)`. Any persisted completion tail after K uses the same condition scheduler with within-condition remainder ordered by `kappa`; no configured candidate may intersect the tail. Changing K changes order-method identity.

Every target candidate is exactly `T_N = pi_train[:N]`.

### 3.12 Exact `pi_eval` randomization

Canonical distinct M3 occurrences are first sorted by `kappa`. Fisher-Yates then produces one exact uniform permutation. For i=|M3|-1 down to 1:

1. `b=ceil(log2(i+1))`;
2. draw b independent unbiased random bits from the experiment randomization source;
3. interpret as nonnegative integer r;
4. reject and redraw while r>i;
5. swap positions i and r.

The randomization source must supply independent unbiased bits independently of scientific/candidate data. The realized permutation, method version, source-class identity, creation-event identity, and audit digest are persisted. Restart authenticates and reuses the stored permutation and never redraws. A new randomization event creates a new experiment identity.

### 3.13 Evaluation sampling uncertainty

For prefix m and model f define Y_x=SSE_x(f), C_x=3*n_atoms(x), and r_m=sum Y/sum C. A diagnostic first-order SRSWOR ratio-estimator standard error may be reported via

```text
z_x = Y_x - r_m*C_x
SE(r_m) ~= sqrt((1-m/M)*s_z^2 / (m*mean(C)^2))
```

with M=|M3| and ordinary sample variance `s_z^2`. Delta-method `SE(R_m)` may be reported for positive r_m. This uncertainty is diagnostic only; it never changes membership or reducer semantics.

### 3.14 Diagnostics

For every configured training prefix independently rescore full P_train under d_P:

```text
R_max(N) = max_x min_{y in T_N} d_P(x,y)
D_mean(N) = mean_x min_{y in T_N} d_P(x,y)
Q50/Q90/Q95/Q99 nearest-selected distance
selected-selected NN Q50/Q90/Q95
represented condition count
neutral structural-family support summaries
protected-event count/fraction
correlation/effective-sample diagnostics
hard-obligation status separately
```

R_max must be nonincreasing over nested prefixes.

Split diagnostics include exact J*, each removal step's admissible set, chosen `(H_max,H_mean)`, condition retained/reserve counts, and the maximum final removed-to-retained distance. Evaluation diagnostics include condition/component-mass discrepancy, correlation summaries, and ratio-estimator uncertainty.

### 3.15 Resource envelope

- target-order evidence is CPU-capable and foundation/GPU-independent;
- fitted feature matrices are O(Nd) persistent storage;
- no persistent dense N-by-N pairwise matrix is allowed;
- retained-set redundancy uses chunked nearest-neighbor scoring and may memoize bounded component/frame nearest-distance state, but final decisions must equal the reference algorithm;
- exact J* and completion-admissibility search may use cached exact solvers; heuristic semantic relaxation is forbidden;
- FPS stores O(N) nearest-distance state and is required only through K=max configured candidate N;
- Fisher-Yates is O(|M3|) time and O(|M3|) permutation state.

If exact split/completion semantics cannot be realized within representative supported CPU/RAM bounds, D2 reopens; D4 may not silently approximate them.

## 4. Stage-by-evidence authorization matrix

Legend: A=authorized, I=identity/support only, D=diagnostic only, H=explicit hard obligation only, F=forbidden.

| Evidence | U_size eligibility | split | pi_train | pi_eval | soft diagnostics | hard prefix qualification |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| canonical condition/provenance | I | A | A | I occurrence identity | A | H |
| universal raw cell/strain geometry | I | A through d_U | A through d_P | F | A | H only if separately accepted |
| neutral element-resolved local structure | F | A through d_U | A through d_P | F | A | H only if separately accepted |
| raw profile-specific pair rules | F | F | F | F | D | F |
| declared/profile atom-group features | F | F | F | F | D | H only if separately accepted in future |
| profile/site/event extensions | F | F | F | F | D | H only if separately accepted |
| foundation descriptors/predictions | F | F | F | F | D after membership freeze | F |
| target-label residual/difficulty | F | F | F | F | D after membership freeze | F |
| protected/correlation/duplicate relations | I | A hard component authority | D | D | A | H where explicitly named |
| candidate/CV/replay/production outcomes | F | F | F | F | post hoc only | F |
| evaluation randomization/permutation | F | F | F | A after M3 freezes | A | F |

No P_train-fitted evidence flows backward into split selection. No target label or candidate result enters either order.

## 5. Identity/currentness and stale descendants

Prepared target-order identity binds at least:

- P1 split-exclusion authority and exact U_size;
- neutral-condition preservation rule;
- frozen neutral feature substrate and complete coordinate/family list;
- fitted d_U parameters and conditioning policy;
- exact J* split policy and retained-set structural-removal trace;
- exact P_train;
- fitted d_P parameters;
- canonical scalar arithmetic/version and type-7 quantile convention;
- K=max configured candidate N and pi_train digest;
- evaluation randomization method/event/source-class and realized pi_eval digest;
- `mu_sel`, `mu_loss`, `mu_eval`, and hard-support policy identities.

Old empty-evidence/UID-order generations and Revision-1/2/3 candidate artifacts remain historical. They cannot deserialize/default themselves into Revision-4 currentness.

Target-order-dependent aggregate/order/T_N/M_i/screen/reducer/provisional/frozen/CV/production descendants become stale when membership ancestry changes. Unrelated authenticated source/P1 evidence remains reusable when independently current. Common-training evidence is reusable only when bound to the same exact P_train and training-method identity.

## 6. Revision-3 blocker closure map

| Revision-3 finding | Revision-4 repair |
| --- | --- |
| structural redundancy was precomputed against U_size\g and allowed mutual disappearance | replaced by stepwise retained-set scores recomputed after every removal, with exact completion admissibility constrained to global minimum condition depletion J* |
| structural substrate remained profile-sensitive/ambiguous | removed raw pair-rule membership features; froze element-only, no-declared-group local-structure aggregation and exact local-feature/family mapping |
| near-zero IQR could amplify numerical jitter | added unit-rescaling-invariant `sqrt(u)*max_abs` conditioning floor, with max-deviation fallback preserving rare genuine excursions |
| required realizations absent | added Revision-4 bounded reference evidence for the new split counterexample, scale conditioning, SRSWOR enumeration, variable-atom evaluation, and condition feasibility; real-owner/provider/resource evidence remains explicitly pending rather than claimed |
| active workplan described Revision-1 method | restore the original lossless workplan and carry Revision-4 state in a separate current status record; obsolete compressed Revision-1 summary is no longer the controlling plan |

## 7. Required pre-promotion falsification

A fresh independent review must realize or independently verify at least:

1. mutual-redundancy counterexample: two components that are each other's only close analogue cannot both disappear without the second being rescored against the new retained set;
2. exact hard-condition infeasibility and a feasible mixed protected-component case against an independent exhaustive reference;
3. exact J* and completion-admissibility reference comparison on bounded cases;
4. neutral provider-policy audit proving no declared/profile group or raw profile pair rule enters d_U/d_P;
5. complete coordinate/family identity and feature-column permutation invariance;
6. near-degenerate scale fixtures, unit-rescaling invariance, rare-outlier fallback, and scalar-reference/optimized equivalence;
7. real-family sensitivity/ablation for equal family mass;
8. small-n Fisher-Yates exact-uniform reference plus duplicate-occurrence non-clustering and restart/no-redraw evidence;
9. variable-atom-count EVAL2 ratio-estimator reference and finite-prefix uncertainty behavior;
10. UID renaming and source/input enumeration metamorphic checks;
11. old-generation rejection and bounded stale-descendant impact;
12. current low-level local-structure producer-lineage authentication;
13. representative CPU/RAM evidence for neutral descriptor construction, retained-set split search, and K-bounded FPS with no dense persistent quadratic state.

The Revision-4 bounded author-side record closes only its stated mathematical fixtures. It is not independent Gate A acceptance evidence and does not substitute for unavailable real-owner/resource checks.

## 8. Human ratification bundle

If a fresh independent review passes, the human owner must accept or reject this bundle as one method:

- configuration-count target-size experiment under equal-frame `mu_sel`, separate frozen `mu_loss`, and component-weighted M3 `mu_eval`;
- exact protected split preserving every eligible neutral condition;
- global minimum neutral-condition depletion followed by dynamically recomputed retained-set structural redundancy under exact completion admissibility;
- universal raw cell/strain geometry plus element-only neutral local-structure summaries; no profile pair rules or declared material groups;
- explicit frozen local-structure policy and semantic feature-family map;
- robust type-7 scaling with a `sqrt(u)` relative conditioning floor and rare-excursion fallback;
- equal semantic-family metric mass as the no-prior baseline;
- scalar binary64 reference with exact ties and no fuzzy winner tolerance;
- one medoid-seeded condition-local exact FPS training order with exact proportional condition interleaving;
- one realized exact Fisher-Yates SRSWOR evaluation permutation over distinct M3 occurrences;
- existing component-weighted EVAL2 ratio estimator with finite-prefix sampling uncertainty diagnostic only;
- no foundation/difficulty membership ordering, no historical quota/radius thresholds, and no GPU prerequisite.

Until fresh independent review and explicit human ratification complete, permanent D1/D2 amendments and behavior-changing D3/D4 remain blocked.