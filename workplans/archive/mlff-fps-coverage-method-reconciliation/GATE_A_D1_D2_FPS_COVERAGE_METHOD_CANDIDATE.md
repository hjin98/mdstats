---
kind: d1-d2-authority-candidate
workplan_id: MLFF-FPS-COVERAGE-METHOD-RECONCILIATION-1
protocol_version: 6.3.0
status: proposed-awaiting-separate-context-independent-review-and-human-ratification
proposal_date: 2026-09-13
revision: 5
revision_basis_review: GATE_A_REVISION_4_REVIEW.md
branch: design/mlff-fps-coverage-method-reconciliation
project_state_basis: e8d04144f55c72d799ffcd3fe40c75e47078a66d
branch_basis_merge: 9a016f6087066c036c78b13c933bf3ddf30c5cc5
accepted_pem: hjin98/mdstats@4eabe2ae9783c7ff92f3a1093c37502a01380812:PROJECT-ENGINEERING-MEMORY.md
highest_affected_domain: D1
---

# Gate A D1/D2 candidate — FPS/coverage target-order method, Revision 5

## 0. Authority state

This is a proposed D1/D2 contract. It supersedes Revision 4 of this Gate A candidate only. Permanent authority remains `docs/methods/mlff_scientific_method.md` and `docs/methods/mlff_numerical_algorithmic_method.md` until a genuinely separate-context independent D1/D2 review passes and the human owner ratifies this revision.

Revision 5 preserves the successful Revision-4 training-side topology: one exact `P_train/M3` split, hard neutral-condition retention, protected components, globally minimum condition depletion, dynamically recomputed retained-set structural redundancy, one `pi_train`, exact nested `T_N` prefixes, and one immutable prepared generation. It does not revive FEAS/MVIDX/MVSEL/REPAIR/MVQUAL products, label-domain target-size fanout, pre-target CV, generated rescue sizes, or per-N selectors.

Revision 5 deliberately simplifies one challenged surface: **automatic reducer decisions use exact full M3 at every training-fidelity boundary.** M1/M2 remain diagnostic SRSWOR prefixes only and have no ranking, elimination, qualification, tie-break, recommendation, or freeze authority.

## 1. D1 scientific contract

### 1.1 Scientific question and independent variable

The target-size experiment asks how one frozen machine-learned force-field (MLFF) training method behaves as training configuration cardinality `N` increases under one frozen candidate-independent construction policy. Candidate membership changes only by extending one canonical training order.

Coverage is support evidence. It does not prove model accuracy, transferability, dynamical stability, long-horizon adequacy, or deployment validity.

### 1.2 Distinct measures

**Selection/support measure `mu_sel`.** Every exact `P_train` configuration has equal membership mass. Target size is configuration count, not optimization weight and not effective independent-sample count.

**Training-loss influence measure `mu_loss`.** Accepted common per-configuration weights, masks, and global property coefficients may be fitted once over exact `P_train` and projected unchanged to every `T_N`. They do not choose membership.

**Evaluation estimand `mu_eval`.** Exact M3 owns the target-force component-weighted EVAL2 estimand:

```text
R_M3(f) = sqrt( sum_x SSE_x(f) / sum_x C_x )
C_x = 3*n_atoms(x)
```

No equality among these measures is claimed.

### 1.3 Exact split feasibility and training support

Every neutral condition admitted to `U_size` is training-critical for the baseline target-size experiment. A valid split must satisfy simultaneously:

```text
|M3| = m3
|P_train| >= N_max
count(P_train,c) >= 1 for every eligible neutral condition c
all P1 split-excluding/protected components remain indivisible
```

If no exact complete-component allocation satisfies these constraints, preparation reports split infeasibility. It does not erase a condition, split a protected component, change M3, or relax exactness.

### 1.4 Redundant residual support is relative to the retained training set

Training support has priority. Among hard-feasible exact splits:

1. minimize neutral-condition depletion globally; then
2. within globally condition-optimal completions, remove structurally redundant components greedily, recomputing redundancy against the current retained set after every removal.

Two components may not permanently certify one another as redundant and then both disappear without rescoring the second against the newly retained population. This is not claimed to be a global final-covering-radius optimum; it is a deterministic retained-set redundancy criterion constrained by the globally optimal condition-depletion objective.

### 1.5 Structural-support scope

The baseline membership metric claims frame-level support across:

- universal cell geometry;
- universal strain coordinates where defined; and
- material-neutral element-resolved summaries of the accepted local-structure kernel.

It does not use mass density, material/profile pair-rule coordinates, declared material groups, phase-specific geometry plans, site classes, material-specific event descriptors, foundation predictions, or label-derived difficulty as baseline membership coordinates.

### 1.6 Training order

Every nonempty `P_train` neutral condition contributes one representative medoid before ordinary progression; therefore configured `N_min` must be at least the number of represented P_train conditions.

After anchors, selected counts track empirical P_train frame mass as closely as exact integer prefixes permit. Within each condition, exact farthest-point sampling (FPS) progressively expands the accepted frame-level structural support. Every candidate is exactly `T_N = pi_train[:N]`; there is no per-N rerun, swap, repair, or selector.

### 1.7 Exact-M3 decision population at every automatic screen boundary

Revision 5 retires the historical changing M1/M2/M3 **decision** ladder.

At every configured automatic training-fidelity boundary, every active `(N, seed)` candidate is evaluated on the same exact M3 frame population using the exact component-weighted target-force RMSE. The reducer's practical-equivalence comparison, funnel elimination, configured-ceiling diagnostic, recommendation, and no-recommendation state consume only these full-M3 metrics.

Consequences:

- the evaluation population does not change across automatic fidelity boundaries;
- a candidate cannot be eliminated because of evaluation-subset sampling noise;
- the practical-equivalence tolerance `epsilon` is compared to metrics with the same M3 estimand at every boundary;
- the remaining controlled stochastic replicate dimension is the optimizer-seed population and training stochasticity, not an evaluation-population random draw.

Training fidelity may still increase through the accepted continuous trajectory; only the evaluation population is frozen to full M3 at every boundary.

### 1.8 M1/M2 are diagnostic probability samples only

One persisted Fisher-Yates permutation `pi_eval` over distinct M3 frame occurrences may still define nested diagnostic prefixes `M1` and `M2`. Under the randomization design those prefixes are SRSWOR samples of M3 frame occurrences and may be used to study:

- finite-population sampling error;
- atom/component-mass discrepancy;
- condition/correlation discrepancy; and
- whether a smaller evaluation population could be adequate in a future separately ratified method.

M1/M2 may **not** rank, eliminate, qualify, tie-break, recommend, select horizons, alter practical equivalence, or freeze target-size membership. They may be computed from per-frame predictions already obtained while evaluating full M3; no additional model inference is scientifically required.

Changing only the diagnostic `pi_eval` realization invalidates M1/M2 diagnostic artifacts but does not invalidate reducer decisions if exact M3 membership, model state, and per-frame predictions remain identical.

### 1.9 Correlation, hard/soft evidence, and forbidden dependencies

Target size intentionally counts configurations rather than effective independent samples. Correlation/protected relations govern split exclusion and remain diagnostics after splitting.

The split-level condition-retention invariant is baseline feasibility. After order construction, only explicitly accepted `hard_support_obligations` may qualify exact training prefixes. FPS distances, retained-set redundancy, coverage metrics, event/environment summaries, correlation diagnostics, and M1/M2 sampling diagnostics remain soft.

Foundation predictions, target-label residual/difficulty, candidate outcomes, CV/replay/reducer state, and downstream physical evidence may not influence the split or `pi_train`. M3 labels are used only by EVAL2 after M3 membership has frozen.

## 2. D2 numerical contract

### 2.1 Scientific occurrence key and exact encoding

Define occurrence identity:

```text
schema = "mdstats.target-order-scientific-occurrence-key.v3"
condition_id
source_identity_signature
source_frame_index
geometry_fingerprint
```

Canonical encoding is:

- every UTF-8 string `v`: `uint64_big_endian(len(utf8(v))) || utf8(v)`;
- `source_frame_index`: exactly unsigned 64-bit big-endian, requiring `0 <= source_frame_index <= 2^64-1`;
- concatenate fields in the stated order after the schema field and SHA-256 the resulting bytes.

An out-of-range source frame index is a preparation identity failure, not an alternate encoding.

A protected-component key is SHA-256 over the same length-prefixed encoding of canonical P1 protected-relation identity followed by the component member `kappa` values sorted lexicographically. Lexical `frame_uid` spelling is not a score.

### 2.2 Material-neutral target-order feature substrate

#### Universal raw geometry

The raw target-order coordinates are exactly:

```text
cell_volume_angstrom3
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

`cell_geometry` owns volume/length/angle coordinates; `strain` owns hydrostatic/deviatoric/shear coordinates. `mass_density_g_cm3` is deliberately excluded because it is composition/mass-derived rather than solely cell/strain geometry and composition already participates through neutral-condition structure.

Energy, forces, pressure/stress, instantaneous temperature labels, force statistics, and `RawFeaturePolicy.pair_rules` are forbidden membership coordinates.

#### Bound local-structure numerical contract

The target-order method binds the analysis numerical contract, not merely matching feature names:

```text
analysis_owner = mdstats.analysis.local_structure
LOCAL_STRUCTURE_POLICY_SCHEMA = mdstats.local-structure-feature-policy.v1
LOCAL_STRUCTURE_RESULT_SCHEMA = mdstats.local-structure-feature-result.v1
LOCAL_STRUCTURE_POLICY_VERSION = mdstats.analysis.local-structure.2026-07.v1
accepted specification = hjin98/mdstats@e8d04144f55c72d799ffcd3fe40c75e47078a66d:
  docs/specs/analysis/local_structure_features_spec.md
accepted specification blob = cc5be8d4f31d9168e09f2baa07711d5c37cf9b62
```

The frozen feature-value policy is:

```text
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

`maximum_dense_pair_work` is a resource guard and is not a feature-value parameter. A semantic change to the bound analysis numerical contract, even with unchanged feature names, changes target-order metric identity and reopens D2.

Target-order aggregation is a dedicated neutral view:

```text
include_declared_atom_groups = false
include_element_groups = true
materialize_atomic_environments = false
aggregate_statistics = (mean,std,min,max,q10,q50,q90)
profile/material membership provider = forbidden
profile phase-geometry plan = forbidden
```

The element set is the sorted union of atomic numbers in exact U_size and fixes the coordinate schema for both `d_U` and `d_P`. Frame-level element atom-count/fraction coordinates are excluded.

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
  radial_density_r{center:.3f}_angstrom for every frozen radial center
angular_environment:
  angular_legendre_l1, angular_legendre_l2,
  angular_legendre_l3, angular_legendre_l4
orientational_order:
  bond_orientational_q4, bond_orientational_q6
```

### 2.3 Canonical element aggregation

For one frame, element Z, local feature F, and statistic s:

1. visit center atoms of atomic number Z in increasing canonical atom index;
2. omit rows whose provider missing mask is true for F;
3. if no valid row remains, the frame aggregate coordinate is missing;
4. otherwise aggregate scalar binary64 values as follows:
   - `mean`: left-to-right binary64 sum in increasing atom-index order, divide once by binary64 count;
   - `std`: two-pass population standard deviation (`ddof=0`): canonical mean, then left-to-right sum of `(v-mean)^2`, divide once by count, then binary64 square root;
   - `min/max`: exact scalar extrema;
   - `q10/q50/q90`: Hyndman-Fan type-7 quantiles after ascending numerical sort.

This target-order aggregation contract is normative even if a future implementation uses a vectorized backend; optimized execution must reproduce the membership-relevant reference result.

### 2.4 Exact missing, constant, and active-coordinate semantics

The fitted transform is defined separately for `d_U` and `d_P` over their own fit populations D.

For source coordinate j let `O_j` be rows with an observed value.

**No observations.** If `|O_j|=0`:

- numerical state is `ALL_MISSING_INACTIVE`;
- no median or scale is defined;
- the numerical coordinate is inactive;
- the all-one missingness indicator is constant and inactive;
- neither coordinate counts in family dimension `d_f`.

**At least one observation.** Compute type-7 median and interquartile range (IQR) over observed values only:

```text
m = Q_0.5
s_iqr = Q_0.75 - Q_0.25
s_dev = max |x_i-m| over observed values
```

Then:

```text
if s_iqr != 0.0 exactly in binary64:
    numerical coordinate active; scale=s_iqr
elif s_dev != 0.0 exactly in binary64:
    numerical coordinate active; scale=s_dev
else:
    numerical state = CONSTANT_INACTIVE
```

There is no generic `sqrt(u)` or other minimum-resolution threshold. The target-order layer treats the bound provider's finite binary64 outputs as its input evidence and does not silently relabel a nonzero observed variation as physical/numerical noise.

For an active numerical coordinate, missing rows are imputed with the observed median before transformation and therefore transform to zero. A binary missingness coordinate with raw value `0` for observed and `1` for missing is active **iff both values occur in the fit domain**, i.e. `0 < |O_j| < |D|`. It is not centered or scaled.

Constant numerical coordinates, all-missing coordinates, constant all-zero/all-one missing indicators, and any other inactive coordinate do not count in `d_f` and therefore cannot dilute informative dimensions.

If a semantic family has `d_f=0`, that family is inactive and contributes zero distance; it does not dilute other active families. Persist for every source coordinate: fit-domain identity, observation count, state, active/inactive flag, median when defined, scale when defined, and missing-indicator state.

If the upstream numerical owner later establishes a coordinate-specific error/resolution bound and target ordering wishes to suppress variations below it, adopting that rule changes D2 metric identity and requires explicit acceptance; it is not inferred from binary64 epsilon.

### 2.5 Family normalization and scalar metric

Every active semantic family f is divided by `sqrt(d_f)` where `d_f` counts only its active numerical coordinates and varying missingness indicators. Equal active-family mass is the explicit no-prior baseline and remains subject to real-feature sensitivity/ablation evidence before promotion.

The final metric is scalar binary64 Euclidean distance over canonical `(family_id, semantic_coordinate_name, coordinate_kind)` order. There is no PCA, whitening, learned weighting, random projection, foundation descriptor, or profile-specific block.

Squared distances use scalar multiply then left-to-right add in canonical coordinate order. Fused contraction is not reference semantics. Exact binary64 score equality is the only score tie; ties use the declared `kappa` or component key. Optimized paths must reproduce the same discrete decisions or fall back to the canonical scalar comparison.

### 2.6 Two fit domains

- `d_U`: fit on exact U_size geometry/neutral structural evidence; used only by pre-split retained-set redundancy.
- `d_P`: refit after the split on exact P_train; used for condition medoids, condition-local FPS, and training-prefix coverage diagnostics.

The source coordinate schema is fixed by U_size, but active-coordinate states, medians, and scales are independently fitted on the relevant domain. M3 labels and candidate outcomes fit neither metric.

### 2.7 Hard-feasible split and globally minimum condition depletion

For protected components g with reserve indicator `z_g`, size `w_g`, condition count `n(g,c)`, and U_size condition count `N_c`:

```text
z_g in {0,1}
sum_g w_g*z_g = m3
for every c: sum_g n(g,c)*z_g <= N_c-1
|U_size|-m3 >= N_max
```

For hard-feasible final reserve S:

```text
J_condition(S) = sum_{g in S} sum_c n(g,c)/N_c
J* = min J_condition(S)
```

`J_condition` is compared by exact rational arithmetic. No hard-feasible exact subset means split infeasibility.

### 2.8 Dynamic retained-set structural redundancy under exact completion admissibility

Initialize `S_0=empty` and `R_0=U_size`. At step t, an unremoved component g is completion-admissible iff there exists a final reserve `S_final` containing `S_t union {g}` that satisfies every hard constraint and `J_condition(S_final)=J*`.

For each completion-admissible g:

```text
q_x(g|R_t) = min_{y in R_t\g} d_U(x,y)^2
H_max(g|R_t) = max_{x in g} q_x
```

For `H_mean`, sort component members by ascending `kappa`, compute each canonical `q_x`, accumulate the q values left-to-right in that order using binary64 addition, and divide once by binary64 `len(g)`:

```text
H_mean(g|R_t) = canonical_sum(q_x in ascending kappa order) / float64(len(g))
```

Choose the lexicographically smallest `(H_max, H_mean, component_key)`, remove the complete component, recompute retained-set scores, and repeat until exactly m3 frames are removed. The completion oracle is exact; resource exhaustion is explicit preparation failure rather than semantic approximation.

### 2.9 P_train representatives, FPS, and global `pi_train`

For every nonempty P_train condition:

1. compute the coordinate-wise type-7 median vector in fitted `d_P` coordinates;
2. choose the frame minimizing canonical squared distance to that vector; exact ties use `kappa`;
3. initialize exact FPS with that medoid;
4. repeatedly select the remaining frame maximizing canonical nearest-selected squared distance; exact ties use `kappa`.

Let `N_c` be P_train condition count, `N` total frames, and `s_c(k)` emitted count after k ranks.

Anchor phase emits one medoid per condition ordered by decreasing `N_c`, then canonical condition ID.

Proportional phase chooses the nonexhausted condition maximizing exact integer deficit

```text
D_c(k+1) = (k+1)*N_c - s_c(k)*N
```

with canonical condition-ID tie-break, then emits that condition's next FPS frame.

FPS is required through `K=max(configured candidate_sizes)`. Any persisted tail after K uses the same condition scheduler with within-condition remainder ordered by `kappa`; no configured candidate intersects the tail.

### 2.10 Exact M3 EVAL2 at every automatic boundary

At every automatic fidelity boundary j and active `(N,seed)` candidate, evaluate exact M3 and compute:

```text
RMSE_F = sqrt(sum_{x in M3} SSE_x / sum_{x in M3} 3*n_atoms(x))
```

The same M3 membership identity is required at every boundary. Candidate comparison and the practical-equivalence reducer consume only this full-M3 value.

This changes the prior M1/M2/M3 decision-ladder method. It does not change the target-force component estimator itself.

### 2.11 Diagnostic `pi_eval`, M1/M2, and sampling uncertainty

For diagnostic sampling only, sort distinct M3 occurrences by `kappa` and perform exact Fisher-Yates. For i=|M3|-1 down to 1:

1. `b=ceil(log2(i+1))`;
2. draw b independent unbiased random bits independently of scientific/candidate data;
3. interpret as integer r;
4. reject/redraw while `r>i`;
5. swap positions i and r.

The realized permutation is diagnostic experiment evidence. Prefix ratio estimates may report the first-order SRSWOR ratio-estimator standard error, but neither prefix estimates nor their uncertainty can alter reducer state.

### 2.12 Diagnostics

For every configured training prefix independently rescore full P_train under `d_P`:

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

`R_max` must be nonincreasing over nested prefixes.

Split diagnostics include J*, per-step completion-admissible candidates, chosen `(H_max,H_mean)`, condition retained/reserve counts, and final removed-to-retained maximum distance.

Diagnostic M1/M2 reports may include component-mass/condition discrepancy and sampling uncertainty, explicitly labeled non-decision evidence.

### 2.13 Resource envelope

- CPU-capable; no foundation/GPU prerequisite;
- O(Nd) persistent fitted-feature storage;
- no persistent dense N-by-N pairwise matrix;
- chunked retained-set nearest-neighbor scoring with reference-equivalent decisions;
- exact J*/completion feasibility with cached exact solver permitted but no semantic approximation;
- O(N) FPS nearest-distance state through K only;
- full-M3 evaluation at each fidelity boundary may batch inference for memory but must preserve exact membership and estimator semantics;
- diagnostic Fisher-Yates is O(|M3|) time/state.

If exact split/completion semantics are not demonstrably feasible within representative supported CPU/RAM bounds, D2 reopens rather than allowing D4 approximation.

## 3. Evidence authorization

| Evidence | U_size eligibility | split | pi_train | automatic EVAL2 decision | diagnostic M1/M2 | soft diagnostics | hard prefix qualification |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| canonical condition/provenance | I | A | A | I membership identity | I | A | H |
| universal raw cell/strain geometry | I | A via d_U | A via d_P | F | F | A | H only if separately accepted |
| neutral element-resolved local structure | F | A via d_U | A via d_P | F | F | A | H only if separately accepted |
| profile/raw material-specific pair rules | F | F | F | F | F | D | F |
| declared/profile atom groups/site/event extensions | F | F | F | F | F | D | H only if separately accepted later |
| foundation descriptors/predictions | F | F | F | F | F | D after membership freeze | F |
| target-label residual/difficulty | F | F | F | A only as exact EVAL2 target labels | A only for diagnostic error estimates after membership freeze | D | F |
| protected/correlation/duplicate relations | I | A hard component authority | D | D | D | A | H where explicitly named |
| candidate/CV/replay/production outcomes | F | F | F | candidate prediction required for EVAL2 only | same frozen per-frame predictions only | post hoc | F |
| evaluation randomization | F | F | F | F | A | A | F |

No P_train-fitted evidence flows backward into the split. Diagnostic randomization cannot alter automatic decision state.

## 4. Identity/currentness

Prepared target-order method identity binds at least:

- P1 split-exclusion authority and exact U_size;
- hard neutral-condition retention;
- bound local-structure numerical-contract identity and exact neutral aggregation policy;
- source coordinate schema and exact active/missing transform semantics;
- fitted `d_U` parameters;
- J* policy and retained-set removal trace;
- exact P_train and fitted `d_P` parameters;
- canonical scalar arithmetic/reduction semantics;
- K and `pi_train` digest;
- exact M3 membership and full-M3-at-every-boundary evaluation policy;
- diagnostic evaluation-randomization method/event and `pi_eval` digest separately;
- `mu_sel`, `mu_loss`, `mu_eval`, and hard-support policy identities.

Changing only diagnostic `pi_eval` does not change target-size reducer identity. Changing M3 membership, full-M3 evaluation policy, `pi_train`, metric semantics, split, or training method does.

Old empty-evidence/UID-order generations and Revision-1/2/3/4 proposal artifacts remain historical. Final storage/currentness rejection of old generations is a downstream D3/D4 gate obligation, not a prerequisite for accepting this D1/D2 proposal.

## 5. Revision-4 blocker closure map

| Revision-4 finding | Revision-5 repair |
| --- | --- |
| R4-B1 all-missing/constant semantics undefined | exact `ALL_MISSING_INACTIVE`, `CONSTANT_INACTIVE`, varying missing-indicator, and active-family-dimension semantics |
| R4-B2 arbitrary `sqrt(u)` floor | removed; exact nonzero IQR/max-deviation fallback only; future provider error floors require separate D2 acceptance |
| R4-B3 SRSWOR noise could eliminate candidates | reducer now evaluates exact full M3 at every fidelity boundary; M1/M2 random prefixes are diagnostic only |
| R4-B4 integer/reduction/provider identity incomplete | kappa v3 with uint64 frame index; canonical H_mean; canonical element aggregation; immutable local-structure spec/policy binding |
| R4-B5 capability transfer and gate staging incomplete | separate Revision-5 capability-transfer map added; Gate-A evidence separated from Gates B-E implementation evidence |
| D1/D2 mass-density scope mismatch | mass density removed from target-order membership metric |

## 6. Gate A evidence required before promotion

A separate-context independent Gate A review must independently realize or verify enough evidence to falsify the D1/D2 method itself. Before human ratification, Gate A requires:

1. bounded exhaustive/reference split cases, including condition infeasibility, J*, completion admissibility, and mutual-redundancy rescoring;
2. exact missing/all-missing/constant/partial-missing transform fixtures and active-family dimension checks;
3. finite nonzero small-variation and rare-outlier transform fixtures showing no generic resolution floor;
4. provider numerical-contract and coordinate/family lineage audit against the bound accepted analysis spec;
5. real-feature equal-family sensitivity/ablation and precision sensitivity sufficient to challenge whether the no-prior family weighting is stable;
6. method-level UID/source/input/feature-column metamorphic checks where realizable without depending on future storage architecture;
7. exact-M3 decision-population oracle showing reducer inputs are invariant to diagnostic `pi_eval` realization;
8. representative algorithmic CPU/RAM feasibility for neutral descriptor preparation, exact J*/completion search, retained-set scoring, and K-bounded FPS; and
9. the completed capability-transfer map.

Required unavailable Gate-A evidence is a blocker; author-side evidence is not independent acceptance.

## 7. Downstream evidence deferred to Gates B-E, not waived

The following remain mandatory after D1/D2 acceptance but do not circularly block Gate A:

- production neutral-provider construction/publish API;
- production optimized implementation versus scalar-reference discrete equivalence;
- actual real-owner UID/input/feature-column metamorphic execution;
- persistence/restart/no-redraw behavior for diagnostic `pi_eval`;
- old-generation storage/currentness fail-closed admission;
- real `prepare -> publish -> consume` integration;
- target-order-dependent stale-descendant invalidation;
- affected regression and production resource qualification.

These are D3/D4 conformance evidence for the accepted method.

## 8. Human ratification bundle

If the separate-context independent review passes, the human owner must accept or reject Revision 5 as one bundle:

- equal-frame configuration-count `mu_sel`, separate frozen `mu_loss`, and exact component-weighted M3 `mu_eval`;
- exact protected split hard-preserving every eligible neutral condition;
- global minimum condition depletion followed by dynamically recomputed retained-set structural redundancy under exact completion admissibility;
- universal cell/strain geometry plus element-only neutral local-structure summaries, excluding mass density, material-specific pair rules, and declared profile groups;
- the explicitly bound low-level local-structure numerical contract and canonical target-order aggregation semantics;
- exact type-7 robust scaling with no generic minimum-resolution threshold, explicit all-missing/constant semantics, and varying missingness indicators only;
- equal active semantic-family metric mass as the no-prior baseline;
- canonical scalar binary64 winner/reduction semantics with exact ties and no fuzzy winner tolerance;
- one medoid-seeded condition-local exact FPS training order with exact proportional interleaving;
- **exact full M3 target-force RMSE at every automatic training-fidelity boundary**;
- M1/M2 retained only as diagnostic SRSWOR prefixes with no decision authority;
- no foundation/difficulty membership ordering, no historical quota/radius thresholds, and no GPU prerequisite.

Until separate-context independent review and explicit human ratification complete, permanent D1/D2 mutation and behavior-changing D3/D4 remain blocked.