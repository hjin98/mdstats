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

The branch ancestry is reconciled to accepted project state `e8d04144...` by merge commit `9a016f60...`; the accepted D1/D2 method-paper blobs were byte-identical across that merge.

Revision 4 preserves the V7 topology: one target-size population, one protected `P_train/M3` split, one `pi_train`, one `pi_eval`, exact nested prefixes, one immutable prepared generation, no per-N selector/repair, no label-domain target-size fanout, and no restored FEAS/MVIDX/MVSEL/REPAIR/MVQUAL product topology.

The applicable Project Engineering Memory (PEM) remains evidence only: SP-001, FF-005, SP-002, SP-003, and SP-004 are applicable; FF-001 through FF-004 remain non-owning for this cycle.

## 1. D1 scientific contract

### 1.1 Scientific question

The target-size experiment asks how one frozen machine-learned force-field (MLFF) training method behaves as training configuration cardinality `N` increases under one frozen candidate-independent data-construction policy. Candidate membership changes only by extending one precomputed training order.

Coverage is support evidence. It does not establish model accuracy, transferability, dynamical stability, or deployment adequacy. Those remain separate EVAL2, post-selection cross-validation, replay, final-production, and physical-validation questions.

### 1.2 Distinct measures

**Selection/support measure `mu_sel`.** Every exact `P_train` configuration has equal mass `1/|P_train|`. Target size counts configurations, not loss weight and not effective independent samples.

**Training-loss influence measure `mu_loss`.** Accepted common per-configuration weights, property masks, and global objective coefficients may be fitted once on exact `P_train` and projected unchanged to every `T_N`. Their policy identity is frozen but they do not choose membership.

**Evaluation estimand `mu_eval`.** Exact M3 owns the component-weighted force-error estimand used by EVAL2:

```text
R_M3(f) = sqrt( sum_x SSE_x(f) / sum_x C_x )
C_x = 3*n_atoms(x)
```

No equality among these measures is claimed.

### 1.3 Hard split support

Every neutral condition admitted to `U_size` is training-critical. A valid split must satisfy simultaneously:

```text
|M3| = m3
|P_train| >= N_max
count(P_train,c) >= 1 for every eligible neutral condition c
all P1 split-excluding/protected components remain indivisible
```

If no exact component allocation satisfies these constraints, preparation reports split infeasibility. It does not erase a condition, split a protected component, reduce M3, or relax exactness.

### 1.4 Redundant residual support is a retained-set concept

Training support has priority. Among exact hard-feasible splits, M3 should consume support that is redundant relative to what actually remains for training.

1. Neutral-condition depletion is minimized globally.
2. Within globally condition-optimal completions, structural redundancy is assessed against the **current retained set** and recomputed after every component removal.

Two components may not permanently certify one another as redundant and then both disappear without the second being rescored after the first removal.

This is a deterministic retained-set greedy criterion inside the set of globally condition-optimal exact completions. It is not claimed to globally minimize final P_train covering radius. Structurally distinctive support may still be lost when exact cardinality/protected constraints force that result; the loss is reported explicitly.

### 1.5 Structural-coverage scope

The baseline claims frame-level support across:

- universal cell/strain geometry; and
- material-neutral element-resolved summaries of universal local-structure features.

It does not claim exhaustive atomic-environment, material-profile group, site-class, or material-specific event coverage. Profile-declared groups, profile extensions, and material-specific raw pair rules are excluded from baseline membership authority.

### 1.6 Training order

Every nonempty P_train neutral condition contributes one representative medoid before ordinary progression. Therefore configured `N_min` must be at least the number of P_train conditions.

After anchors, selected counts track empirical P_train frame mass as closely as exact integer prefixes permit. Inside each condition, exact farthest-point sampling (FPS) progressively expands accepted frame-level structural support.

### 1.7 Evaluation ladder

After M3 freezes and before candidate training, exactly one uniform random permutation of **distinct M3 frame occurrences** is drawn independently of scientific values, geometry, labels, candidate/model outcomes, and reducer state. The realized permutation is persisted and reused on restart.

Every prefix is therefore, under the randomization design, a simple random sample without replacement (SRSWOR) of M3 frame occurrences. Geometry duplicates remain distinct occurrences.

For prefix `M_m`,

```text
r_m(f) = sum_{x in M_m} SSE_x(f) / sum_{x in M_m} C_x
R_m(f) = sqrt(r_m(f))
```

is the finite-population ratio estimator for the exact M3 ratio of totals. It is not claimed exactly unbiased at finite m. The same realized prefix is shared by all candidates at a rung; sampling uncertainty is diagnostic only; at full M3 the ladder sampling error is zero.

### 1.8 Correlation, hard/soft evidence, forbidden dependencies

Target size intentionally counts configurations rather than effective independent samples. Correlation/protected relations govern split exclusion and remain diagnostics after splitting.

The split-level condition-retention invariant is baseline feasibility. After order construction, only explicit accepted `hard_support_obligations` may qualify/reject prefixes. FPS distances, retained-set redundancy scores, coverage metrics, event/environment summaries, correlation diagnostics, and evaluation uncertainty remain soft.

Foundation predictions, target-label residual/difficulty, candidate outcomes, CV/replay/reducer state, and downstream physical evidence may not influence the split, `pi_train`, or `pi_eval`. Preparation remains CPU-capable and model/GPU independent.

## 2. D2 numerical contract

### 2.1 Occurrence and component identity

Lexical `frame_uid` spelling is not a score. Define `kappa(x)` from:

```text
schema = "mdstats.target-order-scientific-occurrence-key.v2"
condition_id
source_identity_signature
source_frame_index
geometry_fingerprint
```

For every ordered UTF-8 string `v`, encode `uint64_big_endian(len(utf8(v))) || utf8(v)` and hash the concatenated fields with SHA-256. Fixed-width integer fields use their stated unsigned big-endian representation.

A protected-component key is the digest of sorted member `kappa` values plus canonical P1 protected-relation identity. Source repackaging that changes authenticated source identity creates new prepared-generation identity. Outside exact score ties, occurrence identity does not steer geometry scores.

### 2.2 Explicit material-neutral feature substrate

Revision 4 does not import active material-profile pair rules or declared atom groups into membership.

#### 2.2.1 Universal raw geometry

Coordinates are exactly:

```text
cell_volume_angstrom3
mass_density_g_cm3
cell_length_a_angstrom        <- cell_lengths_angstrom[0]
cell_length_b_angstrom        <- cell_lengths_angstrom[1]
cell_length_c_angstrom        <- cell_lengths_angstrom[2]
cell_angle_alpha_degrees      <- cell_angles_degrees[0]
cell_angle_beta_degrees       <- cell_angles_degrees[1]
cell_angle_gamma_degrees      <- cell_angles_degrees[2]
hydrostatic_strain
deviatoric_strain_norm
engineering_shear_xy          <- engineering_shear[0]
engineering_shear_yz          <- engineering_shear[1]
engineering_shear_zx          <- engineering_shear[2]
```

`cell_geometry` owns volume/density/length/angle coordinates. `strain` owns hydrostatic/deviatoric/shear coordinates.

Energy, forces, pressure/stress, instantaneous-temperature labels, force statistics, and `RawFeaturePolicy.pair_rules` are excluded. Pair-rule geometry is omitted because accepted raw pair policies may be material-specific; neutral local geometry is supplied below.

#### 2.2.2 Frozen low-level local-structure policy

The numerical owner is `mdstats.analysis.local_structure`. The target-order method freezes:

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

`maximum_dense_pair_work` is a resource guard rather than a feature-value parameter; changing it is admissible only when numerical feature values are unchanged and the resource contract remains satisfied.

Target-order frame aggregation is a dedicated neutral view:

```text
include_declared_atom_groups = false
include_element_groups = true
materialize_atomic_environments = false
aggregate_statistics = (mean,std,min,max,q10,q50,q90)
profile/material membership provider = forbidden
profile phase-geometry plan = forbidden
```

The element set is the sorted union of atomic numbers in exact U_size and defines the coordinate schema for both d_U and d_P. For each element Z, local feature F, and statistic s, one semantic coordinate `(element_Z,F,s)` exists. Frame-level group `atom_count` and `atom_fraction` coordinates are excluded because composition support is already a neutral-condition axis.

For one frame and one element group, aggregation uses only atoms of that center element. Per-feature missing local values are omitted. If no valid value remains, the frame coordinate is missing. Otherwise:

```text
mean = arithmetic mean
std  = population standard deviation (ddof=0)
min/max = extrema
q10/q50/q90 = Hyndman-Fan type-7 quantiles
```

These aggregation outputs are binary64 evidence values; their semantic coordinate names and missing masks are persisted.

The exact local feature-family map is:

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
  radial_density_r{center:.3f}_angstrom for each frozen radial center
angular_environment:
  angular_legendre_l1
  angular_legendre_l2
  angular_legendre_l3
  angular_legendre_l4
orientational_order:
  bond_orientational_q4
  bond_orientational_q6
```

No display-name inference is allowed outside the explicitly defined generated radial-name rule. The complete generated `(semantic_coordinate_name,family_id)` table is persisted as metric identity.

### 2.3 Canonical transform and conditioning

Rows are ordered by `kappa`; coordinates by `(family_id,semantic_coordinate_name)`.

For observed values, Hyndman-Fan type-7 quantiles use scalar binary64 operations in the written order:

```text
h=(n-1)p
i=floor(h)
r=h-i
Q_p=(1-r)*x[i] + r*x[min(i+1,n-1)]
```

Define

```text
u = 2^-53
tau = sqrt(u)
M = max_i |x_i|
rho = tau*M
m = Q_0.5
s_iqr = Q_0.75-Q_0.25
s_dev = max_i |x_i-m|
```

If `M==0`, the numerical coordinate is constant. Otherwise:

```text
if s_iqr >= rho:   scale=s_iqr
elif s_dev >= rho: scale=s_dev
else:              numerical coordinate is unresolved and transforms to zero
```

Missing values are imputed with the observed median before numerical transformation. If any source value is missing, append a separate binary missingness coordinate even when the numerical coordinate is unresolved.

The `sqrt(u)` floor is a conditioning rule, not a score-tie tolerance. It prevents order-u relative binary64 perturbations from being amplified above order `sqrt(u)` solely by division through a near-zero empirical scale. Because `rho` scales with M, this branch rule is invariant under positive linear unit rescaling. If a provider declares a stronger coordinate-specific numerical resolution bound, the stronger bound controls and changes metric identity.

Rare genuine excursions are retained: a collapsed IQR uses `s_dev` when that deviation exceeds the resolution floor.

### 2.4 Family normalization, distance, and scalar reference

Every semantic family f is divided by `sqrt(d_f)`, where d_f counts active numerical and missingness coordinates. Equal family mass is the explicit no-prior baseline and requires sensitivity/ablation evidence before promotion.

The final metric is binary64 Euclidean distance. There is no PCA, whitening, learned weighting, random projection, foundation descriptor, or profile-specific feature block.

All membership decisions are owned by one canonical scalar binary64 reference. Squared distance uses canonical coordinate order and scalar multiply followed by left-to-right add; fused contraction is not reference semantics.

A score tie exists only when canonical reference scores compare exactly equal as binary64 values. Ties use `kappa` or component key. Optimized/vectorized/parallel implementations must reproduce the same discrete selection or fall back to canonical reference recomputation. There is no fuzzy winner/tie tolerance.

### 2.5 Two fit domains

The metric definition and coordinate schema are shared, but fitted transforms differ:

- `d_U`: fit on exact U_size geometry/neutral structural evidence; used only by pre-split retained-set redundancy.
- `d_P`: refit after the split on exact P_train; used for condition medoids, local FPS, and training-prefix coverage diagnostics.

The coordinate schema is fixed from U_size. d_P medians/scales/missingness statistics use P_train only. M3 labels and candidate outcomes fit neither metric.

### 2.6 Exact hard feasibility and minimum condition depletion

Let protected components be `g=1..G`, with final reserve indicator `z_g`, component size `w_g`, condition count `n(g,c)`, and U_size condition count `N_c`.

Hard constraints:

```text
z_g in {0,1}
sum_g w_g*z_g = m3
for every eligible c: sum_g n(g,c)*z_g <= N_c-1
|U_size|-m3 >= N_max
```

Among hard-feasible final subsets:

```text
J_condition(S) = sum_{g in S} sum_c n(g,c)/N_c
J* = min J_condition(S)
```

J_condition comparison is exact rational arithmetic. No hard-feasible subset means split infeasibility.

### 2.7 Dynamic retained-set structural redundancy

Initialize removed components `S_0=empty` and retained frames `R_0=U_size`.

At step t, an unremoved component g is **completion-admissible** iff there exists at least one final reserve S_final such that:

```text
S_t union {g} subset S_final
S_final satisfies every hard constraint
J_condition(S_final) = J*
```

For every completion-admissible g, score the candidate removal against the current retained set after removing g:

```text
q_x(g|R_t) = min_{y in R_t\g} d_U(x,y)^2
H_max(g|R_t) = max_{x in g} q_x
H_mean(g|R_t) = mean_{x in g} q_x
```

Choose lexicographically smallest `(H_max,H_mean,component_key)`, remove the whole component, update R_t, and repeat until exactly m3 frames are removed.

The completion oracle is exact. Memoized sparse dynamic programming, branch-and-bound, mixed-integer search, or another exact solver is allowed; a heuristic may not declare infeasibility or change J*. Resource exhaustion is explicit preparation failure.

Because H is recomputed after every removal, two mutually redundant components cannot both continue to use one another as retained analogues. This method preserves globally minimum condition depletion and then greedily consumes currently redundant structural support; it does not claim a global optimum of final P_train covering radius.

### 2.8 P_train representatives, FPS, and global `pi_train`

For every nonempty P_train condition:

1. compute coordinate-wise type-7 median vector in fitted d_P coordinates;
2. choose the frame minimizing canonical squared distance to the median; exact ties use `kappa`;
3. initialize exact FPS with that medoid;
4. repeatedly choose the remaining frame maximizing canonical nearest-selected squared distance; exact ties use `kappa`.

Let N_c be P_train condition count, N the total, and s_c(k) emitted count after k ranks.

Anchor phase emits one medoid per condition ordered by decreasing N_c then canonical condition ID.

Proportional phase chooses the nonexhausted condition maximizing the exact integer deficit

```text
D_c(k+1) = (k+1)*N_c - s_c(k)*N
```

with canonical condition ID tie-break, then emits that condition's next FPS frame.

FPS governs through `K=max(configured candidate_sizes)`. Any persisted tail after K uses the same condition scheduler with within-condition remainder ordered by `kappa`; no configured candidate intersects the tail. Every target candidate is exactly `T_N=pi_train[:N]`.

### 2.9 Exact `pi_eval`

Canonical distinct M3 occurrences are sorted by `kappa`, then Fisher-Yates produces one exact uniform permutation. For i=|M3|-1 down to 1:

1. `b=ceil(log2(i+1))`;
2. draw b independent unbiased random bits independently of scientific/candidate data;
3. interpret as integer r;
4. reject/redraw while r>i;
5. swap positions i and r.

The realized permutation, method version, source-class identity, creation-event identity, and audit digest are persisted. Restart validates/reuses it and never redraws. A new randomization event creates a new experiment identity.

### 2.10 Evaluation uncertainty

For prefix m, `Y_x=SSE_x(f)`, `C_x=3*n_atoms(x)`, `r_m=sum Y/sum C`. Diagnostic first-order SRSWOR ratio-estimator uncertainty may use

```text
z_x = Y_x-r_m*C_x
SE(r_m) ~= sqrt((1-m/M)*s_z^2/(m*mean(C)^2))
```

with M=|M3|. Delta-method SE(R_m) may be reported for positive r_m. It does not alter membership or reducer semantics.

### 2.11 Diagnostics and resources

For each configured training prefix independently rescore full P_train under d_P:

```text
R_max(N)
D_mean(N)
Q50/Q90/Q95/Q99 nearest-selected distance
selected-selected NN Q50/Q90/Q95
represented condition count
neutral structural-family support summaries
protected-event count/fraction
correlation/effective-sample diagnostics
hard-obligation status separately
```

R_max must be nonincreasing over nested prefixes.

Split diagnostics include J*, per-step completion-admissible candidates, chosen `(H_max,H_mean)`, condition retained/reserve counts, and final removed-to-retained maximum distance. Evaluation diagnostics include component-mass/condition discrepancy, correlation summaries, and ratio-estimator uncertainty.

Resource contract:

- CPU-capable; no foundation/GPU prerequisite;
- O(Nd) persistent fitted-feature storage;
- no persistent dense N-by-N pairwise matrix;
- chunked retained-set nearest-neighbor scoring with reference-equivalent decisions;
- exact J*/completion feasibility with cached exact solver allowed but no semantic approximation;
- O(N) FPS nearest-distance state through K only;
- O(|M3|) Fisher-Yates time/state.

If exact split/completion semantics are not feasible within representative supported CPU/RAM bounds, D2 reopens rather than allowing D4 approximation.

## 3. Stage-by-evidence authorization matrix

Legend: A=authorized, I=identity/support only, D=diagnostic only, H=explicit hard obligation only, F=forbidden.

| Evidence | U_size eligibility | split | pi_train | pi_eval | soft diagnostics | hard prefix qualification |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| canonical condition/provenance | I | A | A | I occurrence identity | A | H |
| universal raw cell/strain geometry | I | A through d_U | A through d_P | F | A | H only if separately accepted |
| neutral element-resolved local structure | F | A through d_U | A through d_P | F | A | H only if separately accepted |
| raw profile-specific pair rules | F | F | F | F | D | F |
| declared/profile atom-group features | F | F | F | F | D | H only if separately accepted later |
| profile/site/event extensions | F | F | F | F | D | H only if separately accepted |
| foundation descriptors/predictions | F | F | F | F | D after membership freeze | F |
| target-label residual/difficulty | F | F | F | F | D after membership freeze | F |
| protected/correlation/duplicate relations | I | A hard component authority | D | D | A | H where explicitly named |
| candidate/CV/replay/production outcomes | F | F | F | F | post hoc only | F |
| evaluation randomization/permutation | F | F | F | A after M3 freezes | A | F |

No P_train-fitted evidence flows backward into split selection. No target label or candidate result enters either order.

## 4. Identity/currentness and stale descendants

Prepared target-order identity binds at least:

- P1 split-exclusion authority and exact U_size;
- neutral-condition preservation rule;
- frozen neutral feature substrate and complete coordinate/family table;
- fitted d_U parameters and conditioning policy;
- J* policy and retained-set removal trace;
- exact P_train and fitted d_P parameters;
- canonical scalar arithmetic/version and type-7 conventions;
- K and pi_train digest;
- evaluation randomization method/event/source class and realized pi_eval digest;
- mu_sel/mu_loss/mu_eval and hard-support policy identities.

Old empty-evidence/UID-order generations and Revision-1/2/3 proposal artifacts remain historical and cannot default into Revision-4 currentness.

When membership ancestry changes, target-order-dependent aggregate/order/T_N/M_i/screen/reducer/provisional/frozen/CV/production descendants are stale. Unrelated authenticated source/P1 evidence remains reusable if independently current. Common-training evidence is reusable only when bound to the same exact P_train and training-method identity.

## 5. Revision-3 closure map

| Revision-3 finding | Revision-4 repair |
| --- | --- |
| static structural redundancy allowed mutually redundant components to disappear together | dynamic retained-set H scores are recomputed after every removal and only exact J*-optimal completions are admissible |
| structural substrate was profile-sensitive/ambiguous | raw pair rules removed; element-only no-declared-group local aggregation frozen with exact local policy, aggregation statistics, and family map |
| near-zero IQR could amplify numerical jitter | `sqrt(u)*max_abs` conditioning floor plus max-deviation rare-excursion fallback |
| required realizations absent | new bounded mathematical/static evidence added; unavailable real-owner/resource evidence remains explicit |
| active workplan described obsolete Revision-1 method | original 669-line reviewed workplan restored losslessly; Revision-4 status is carried separately |

## 6. Required pre-promotion falsification

Fresh independent review must realize or independently verify at least:

1. mutual-redundancy retained-set counterexample;
2. hard-condition infeasibility and feasible protected-component exhaustive reference;
3. exact J* and completion-admissibility comparison on bounded cases;
4. neutral provider audit proving no profile group or raw pair rule enters d_U/d_P;
5. complete coordinate/family identity and feature-column permutation invariance;
6. near-degenerate scale, positive unit-rescaling invariance, rare-outlier fallback, and optimized/reference equivalence;
7. real-family equal-mass sensitivity/ablation;
8. small-n Fisher-Yates exact uniformity, duplicate occurrence non-clustering, and restart/no-redraw;
9. variable-atom-count EVAL2 ratio-estimator reference and finite-prefix uncertainty;
10. UID renaming and source/input enumeration metamorphic checks;
11. old-generation rejection and bounded stale-descendant impact;
12. current low-level local-structure producer-lineage authentication;
13. representative CPU/RAM evidence for neutral descriptors, retained-set split search, and K-bounded FPS with no persistent dense quadratic state.

`GATE_A_REVISION_4_BOUNDED_FALSIFICATION_RECORD.md` closes only its stated author-side mathematical/static fixtures. It is not independent acceptance evidence.

## 7. Human ratification bundle

If fresh independent review passes, human ratification accepts or rejects this bundle as one method:

- equal-frame configuration-count `mu_sel`, separate frozen `mu_loss`, and component-weighted M3 `mu_eval`;
- exact protected split hard-preserving every eligible neutral condition;
- global minimum condition depletion followed by dynamically recomputed retained-set structural redundancy under exact completion admissibility;
- universal cell/strain geometry plus element-only neutral local-structure summaries; no profile pair rules or declared material groups;
- frozen local-structure/aggregation policy and exact semantic family map;
- type-7 robust scaling with `sqrt(u)` conditioning floor and rare-excursion fallback;
- equal semantic-family metric mass as the no-prior baseline;
- canonical scalar binary64 winner semantics with exact ties and no fuzzy winner tolerance;
- one medoid-seeded condition-local exact FPS training order with exact proportional interleaving;
- one realized exact Fisher-Yates SRSWOR evaluation permutation over distinct M3 occurrences;
- existing component-weighted EVAL2 ratio estimator with finite-prefix sampling uncertainty diagnostic only;
- no foundation/difficulty membership ordering, no historical quota/radius thresholds, and no GPU prerequisite.

Until fresh independent review and explicit human ratification complete, permanent D1/D2 mutation and behavior-changing D3/D4 remain blocked.