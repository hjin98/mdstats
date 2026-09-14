# Gate A Revision 5 — proposed D2 method-paper amendment

Date: 2026-09-14
Workplan: `MLFF_FPS_COVERAGE_METHOD_RECONCILIATION_AND_ORDERING_CONFORMANCE_WORKPLAN.md`
Candidate family: `GATE_A_D1_D2_FPS_COVERAGE_METHOD_CANDIDATE.md`, Revision 5
Target owner: `docs/methods/mlff_numerical_algorithmic_method.md`
Lifecycle: **PROPOSED — not accepted current D2 authority**

## 1. Purpose and application rule

This file is the exact Gate-A D2 amendment overlay for the current MLFF Numerical Algorithmic Method Paper. It closes the promotion-packaging gap identified after Revision 5 and makes the target-order numerical method reconstructible without reverse-engineering the combined Gate-A candidate or future D3/D4 code.

Within the Revision-5 proposal family, this file is the detailed D2 owner for the target-order numerical surface. `GATE_A_D1_D2_FPS_COVERAGE_METHOD_CANDIDATE.md` remains the cross-domain D1/D2 summary and handoff. A semantic mismatch between the two is a Gate-A blocker; this overlay may not silently override D1.

Until separate-context independent D1/D2 review passes and the human owner ratifies the exact Revision-5 bundle, `docs/methods/mlff_numerical_algorithmic_method.md` remains the accepted current D2 authority. Repository presence of this overlay does not promote it.

At promotion, apply only the replacements/additions below. Every D2 section not named here is preserved byte-for-byte except mechanically necessary heading/cross-reference adjustments. Preserve the 2026-09-13 reconstruction provenance and append the later Gate-A reconciliation provenance rather than rewriting history.

## 2. Amend the Section 1 core-invariant list

Replace the target-order-specific bullets in the current core-invariant list with the following invariants; preserve unrelated source, training, replay, CV, and final-production bullets:

- pre-order target membership is constructed from one explicit material-neutral structural-support method; an empty priority vector or lexical UID order is not a valid baseline target-order method;
- exact `U_size -> P_train + M3` splitting preserves protected components, exact reserve cardinality, at least one retained training frame per eligible neutral condition, and globally minimum exact condition depletion before retained-set structural redundancy;
- `d_U` and `d_P` are distinct fitted target-order metrics with fixed source-coordinate schema and exact fit-domain identity;
- one medoid-anchored, condition-local exact farthest-point sampling (FPS) construction plus exact proportional condition scheduling owns `pi_train`; every target candidate is the exact prefix `T_N=pi_train[:N]`;
- exact full `M3` target-force EVAL2 is the sole automatic model-selection population at every configured fidelity boundary;
- `pi_eval`, `M1`, and `M2` are diagnostic probability-sampling evidence only and have no ranking, elimination, qualification, tie-break, recommendation, horizon-selection, or freeze authority;
- target-order identity binds the exact metric/provider/split/order/reduction semantics needed to prevent stale or semantically different prepared generations from masquerading as current;
- target-size fitted training state remains common across sizes/seeds and candidate projection never refits or renormalizes it.

## 3. Replace Section 4.1 — pre-order evidence

Use:

### 4.1 Pre-order target-order evidence

The baseline target-order method consumes one fixed candidate-independent evidence family:

- canonical neutral condition/provenance evidence;
- universal frame-level cell geometry;
- universal strain coordinates where scientifically defined; and
- material-neutral, element-resolved frame summaries of the accepted local-structure numerical contract.

Mass density, material/profile pair-rule coordinates, declared/profile atom groups or site classes, material-specific event descriptors, foundation-model predictions/descriptors, and label-derived residual/difficulty are not baseline membership coordinates.

Two fitted target-order metrics are authorized:

- `d_U`, fitted on exact `U_size`, is used only for pre-split retained-set structural redundancy;
- `d_P`, refitted after the split on exact `P_train`, is used for condition medoids, condition-local FPS, and training-prefix coverage diagnostics.

`M3` labels and candidate outcomes fit neither metric. Pre-order target-order evidence is preparation-owned scientific state and is published once with the immutable prepared generation; downstream commands consume that state rather than reconstructing it from live inputs.

There is no valid baseline state in which required target-order evidence is represented by an empty priority vector and lexical UID order.

Preserve current Section 4.2 (`TargetSizeCommonPreparation`) unchanged except for cross-references that must now point to the new target-order sections below.

## 4. Replace Sections 5–7 in full

Replace current Sections 5, 6, and 7 with the following.

## 5. Canonical target-order evidence and fitted metrics

### 5.1 Exact target-size population and protected components

`U_size` is the exact set of currently eligible, canonically labeled DEVELOPMENT frames admitted to the neutral target-size study. It must contain enough frames for both configured `N_max` and exact reserve cardinality `m3`.

Project the accepted P1 protected-relation authority onto `U_size` and compute transitive connected components. These components are indivisible allocation units for `P_train/M3`.

Every eligible neutral condition represented in `U_size` is training-critical for the baseline target-size experiment: a valid split must retain at least one `P_train` frame from every such condition.

### 5.2 Scientific occurrence key and exact encoding

Target-order tie and identity semantics use the scientific occurrence key

```text
schema = "mdstats.target-order-scientific-occurrence-key.v3"
condition_id
source_identity_signature
source_frame_index
geometry_fingerprint
```

Canonical encoding is:

- every UTF-8 string `v`: `uint64_big_endian(len(utf8(v))) || utf8(v)`;
- `source_frame_index`: unsigned 64-bit big-endian with `0 <= source_frame_index <= 2^64-1`;
- concatenate fields in the stated order after the schema field and SHA-256 the resulting bytes.

Out-of-range frame index is an identity failure, not an alternate encoding. Call the resulting digest `kappa`.

A protected-component key is SHA-256 over the same length-prefixed encoding of canonical P1 protected-relation identity followed by member `kappa` values sorted lexicographically. Lexical `frame_uid` spelling is not a numerical score or target-order tie-break.

### 5.3 Material-neutral feature substrate

The universal raw target-order coordinates are exactly:

```text
cell_volume_angstrom3
cell_length_a_angstrom
cell_length_b_angstrom
cell_length_c_angstrom
cell_angle_alpha_degrees
cell_angle_beta_degrees
cell_angle_gamma_degrees
hydrostatic_strain
deviatoric_strain_norm
engineering_shear_xy
engineering_shear_yz
engineering_shear_zx
```

Cell volume/length/angle are the `cell_geometry` family. Hydrostatic/deviatoric/shear values are the `strain` family. `mass_density_g_cm3` is excluded. Energy, forces, pressure/stress, instantaneous-temperature labels, force statistics, and material/profile `RawFeaturePolicy.pair_rules` are forbidden membership coordinates.

The local-structure source is bound to the accepted numerical contract rather than to feature-name coincidence:

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

`maximum_dense_pair_work` is a resource guard, not a feature-value parameter. A semantic change to the bound local-structure contract changes target-order metric identity and reopens D2.

Target-order aggregation uses a dedicated neutral view:

```text
include_declared_atom_groups = false
include_element_groups = true
materialize_atomic_environments = false
aggregate_statistics = (mean,std,min,max,q10,q50,q90)
profile/material membership provider = forbidden
profile phase-geometry plan = forbidden
```

The element set is the sorted union of atomic numbers in exact `U_size`; it fixes the element-coordinate schema for both `d_U` and `d_P`. Frame-level element count/fraction coordinates are excluded.

The local semantic families are:

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
  angular_legendre_l1
  angular_legendre_l2
  angular_legendre_l3
  angular_legendre_l4
orientational_order:
  bond_orientational_q4
  bond_orientational_q6
```

### 5.4 Canonical element aggregation

For one frame, element `Z`, local feature `F`, and requested statistic:

1. visit center atoms of atomic number `Z` in increasing canonical atom index;
2. omit rows whose provider missing mask is true for `F`;
3. if no valid row remains, the frame aggregate coordinate is missing;
4. otherwise aggregate scalar binary64 values as follows:
   - `mean`: left-to-right binary64 sum in increasing atom-index order, divide once by binary64 count;
   - `std`: two-pass population standard deviation (`ddof=0`) using the canonical mean, then left-to-right sum of `(v-mean)^2`, divide once by count, then binary64 square root;
   - `min/max`: exact scalar extrema;
   - `q10/q50/q90`: Hyndman–Fan type-7 quantiles after ascending numerical sort.

Optimized execution may replace this reference form only when membership-relevant results reproduce the accepted discrete decisions/equivalence contract.

### 5.5 Missing, constant, and active-coordinate semantics

Fit the transform separately on each metric fit domain `D` (`U_size` for `d_U`, `P_train` for `d_P`). For source coordinate `j`, let `O_j` be rows with an observed value.

If `|O_j|=0`:

- numerical state is `ALL_MISSING_INACTIVE`;
- no median or scale is defined;
- the numerical coordinate is inactive;
- the all-one missingness indicator is constant/inactive;
- neither coordinate contributes to family dimension `d_f`.

If at least one value is observed, compute type-7 median and interquartile range (IQR) over observed values only:

```text
m = Q_0.5
s_iqr = Q_0.75 - Q_0.25
s_dev = max |x_i-m| over observed values
```

Then:

```text
if s_iqr != 0.0 exactly in binary64:
    numerical coordinate active; scale = s_iqr
elif s_dev != 0.0 exactly in binary64:
    numerical coordinate active; scale = s_dev
else:
    numerical state = CONSTANT_INACTIVE
```

There is no generic `sqrt(u)` or other minimum-resolution threshold. If an upstream accepted numerical owner later provides a coordinate-specific resolution/error bound and target ordering wishes to suppress variations below it, that adoption changes D2 metric identity.

For an active numerical coordinate, missing rows are imputed with the observed median before transform and therefore map to zero. A binary missingness coordinate (`0` observed, `1` missing) is active iff both values occur in the fit domain, i.e. `0 < |O_j| < |D|`; it is neither centered nor scaled.

Constant numerical coordinates, all-missing coordinates, constant missingness indicators, and any other inactive coordinate do not count in `d_f`. An all-inactive semantic family contributes zero distance and does not dilute other active families.

Persist for every source coordinate: fit-domain identity, observation count, state, active/inactive flag, median when defined, scale when defined, and missing-indicator state.

### 5.6 Equal-family normalization and scalar distance

Every active semantic family `f` is divided by `sqrt(d_f)`, where `d_f` counts only active numerical coordinates and varying missingness indicators. Equal active-family mass is the explicit no-prior baseline and remains subject to Gate-A real-feature sensitivity/ablation evidence before promotion.

The final metric is scalar binary64 Euclidean distance over canonical `(family_id, semantic_coordinate_name, coordinate_kind)` order. There is no PCA, whitening, learned weighting, random projection, foundation descriptor, or profile-specific membership block.

Squared distances use scalar multiply followed by left-to-right binary64 addition in canonical coordinate order. Fused contraction is not reference semantics. Exact binary64 score equality is the only numerical-score tie; ties use `kappa` or protected-component key as specified. An optimized path must reproduce the same discrete decision or fall back to canonical scalar comparison.

### 5.7 Two fit domains

- `d_U`: fit on exact `U_size` and used only by pre-split retained-set redundancy;
- `d_P`: refit after the split on exact `P_train` and used for condition medoids, condition-local FPS, and training-prefix coverage diagnostics.

The source coordinate schema is fixed by `U_size`; active-coordinate states, medians, and scales are fitted independently in the two domains. `M3` labels and candidate outcomes fit neither metric.

## 6. Exact development split and canonical training order

### 6.1 Hard feasibility and globally minimum condition depletion

For protected component `g`, define size `w_g`, condition count `n(g,c)`, and reserve indicator `z_g`. Let `N_c` be the `U_size` count for condition `c`.

Hard feasibility is:

```text
z_g in {0,1}
sum_g w_g*z_g = m3
for every c: sum_g n(g,c)*z_g <= N_c-1
|U_size|-m3 >= N_max
```

For a feasible reserve set `S`, define the exact rational condition-depletion cost

```text
A_g = sum_c n(g,c)/N_c
J_condition(S) = sum_{g in S} A_g
J* = min J_condition(S)
```

All `A_g`, partial sums, and comparisons used to decide `J*` are exact rationals. No hard-feasible exact reserve means split infeasibility.

### 6.2 Exact reference solver for `J*` and completion admissibility

The D2 reference algorithm is an exact memoized dynamic program over canonical protected components. Its purpose is to make `J*` and the completion-admissibility predicate reconstructible; D3/D4 may use another exact algorithm only if it is proven to return the same exact objective/predicate and therefore the same downstream split decisions.

For any subproblem, sort the available components by ascending `component_key`. Let the ordered list be `g_0 ... g_{m-1}`. Let `r` be the remaining reserve cardinality and let `b_c` be the remaining removable capacity for condition `c` (`0 <= b_c <= N_c-1`). Store the capacity vector in canonical condition-ID order.

Define `OPT(i,r,b)` as the minimum additional exact rational depletion cost obtainable from suffix `i...m-1` while selecting exactly `r` frames and not exceeding any condition capacity. Use `+infinity` for infeasible states.

Reference recurrence:

```text
OPT(i, 0, b) = 0
OPT(m, r>0, b) = +infinity

exclude = OPT(i+1, r, b)
include = +infinity
if w_i <= r and n(g_i,c) <= b_c for every c:
    include = A_i + OPT(i+1, r-w_i, b-n_i)
OPT(i,r,b) = min_exact_rational(exclude, include)
```

The reference may apply only exact pruning that cannot remove an optimum, including:

- `r < 0` -> infeasible;
- total remaining component cardinality `< r` -> infeasible;
- a condition-capacity violation -> infeasible;
- already memoized identical state -> reuse exact result.

No floating objective tolerance, heuristic infeasibility declaration, or approximate mixed-integer gap is reference semantics.

Global optimum is

```text
J* = OPT(0, m3, {c: N_c-1})
```

when finite.

At retained-set removal step `t`, let already chosen reserve components be `S_t`. For a candidate component `g` not in `S_t`, define residual cardinality and capacities after tentatively adding `g`. Rebuild the available-component list as all components not in `S_t union {g}`, in canonical `component_key` order, and evaluate the same exact `OPT` recurrence on that subproblem.

`g` is **completion-admissible** iff:

1. the residual state is hard-feasible;
2. the residual exact optimum is finite; and
3. `J_condition(S_t) + A_g + OPT_residual == J*` by exact rational equality.

This definition proves that accepting `g` preserves at least one globally condition-optimal exact completion. It does not select that completion directly.

Implementations may cache/share equivalent exact subproblems, use exact branch-and-bound, exact integer reformulations, or another exact solver, but may not change the completion predicate. A solver whose correctness depends on floating feasibility/objective tolerances is not equivalent unless an independent exact verification step certifies the final predicate/result.

Worst-case state growth is combinatorial in the protected-component/condition-capacity structure; this amendment therefore makes no `O(C*m3)` claim for the repaired split. Representative CPU/RAM feasibility of the exact method is a Gate-A acceptance condition. Resource exhaustion is explicit preparation infeasibility of the proposed method in the tested supported regime and reopens D2; it is not permission for D4 approximation.

### 6.3 Dynamic retained-set structural redundancy

Initialize `S_0=empty` (reserve chosen so far) and `R_0=U_size` (retained training population before removals).

For every completion-admissible candidate component `g` at step `t`:

```text
q_x(g|R_t) = min_{y in R_t\g} d_U(x,y)^2
H_max(g|R_t) = max_{x in g} q_x
```

For `H_mean`, sort component members by ascending `kappa`, accumulate canonical `q_x` left-to-right in binary64, then divide once by binary64 `len(g)`:

```text
H_mean(g|R_t) = canonical_sum(q_x in ascending kappa order) / float64(len(g))
```

Choose the lexicographically smallest `(H_max, H_mean, component_key)`, add that complete component to the reserve, remove it from the retained set, and recompute all retained-set scores. Repeat until exactly `m3` frames are in reserve.

Because every chosen component is completion-admissible against `J*`, the procedure never knowingly leaves the globally minimum condition-depletion feasible set. Structural redundancy is a deterministic secondary criterion, not a claim of globally minimum final covering radius.

### 6.4 Condition medoids and exact condition-local FPS

Fit `d_P` on final exact `P_train`.

For every nonempty `P_train` condition:

1. compute the coordinate-wise type-7 median vector in fitted `d_P` coordinates;
2. choose the frame minimizing canonical squared distance to that vector; exact ties use `kappa`;
3. initialize that condition's exact FPS order with the medoid;
4. repeatedly select the remaining frame maximizing canonical nearest-selected squared distance; exact ties use `kappa`.

FPS is required only through `K=max(configured candidate_sizes)` for candidate membership. An optional persisted tail beyond `K` is not allowed to alter any configured candidate.

### 6.5 Exact global condition scheduler and `pi_train`

Let `N_c` be the final `P_train` count for condition `c`, let `N=|P_train|`, and let `s_c(k)` be the number emitted from condition `c` after `k` global ranks.

Anchor phase emits one medoid per condition ordered by decreasing `N_c`, then canonical condition ID. Therefore configured `N_min` must be at least the number of represented `P_train` conditions.

After anchors, choose the nonexhausted condition maximizing the exact integer deficit

```text
D_c(k+1) = (k+1)*N_c - s_c(k)*N
```

with canonical condition-ID tie-break, then emit that condition's next FPS frame. This produces one exact `pi_train`.

Every target candidate is exactly

```text
T_N = pi_train[:N]
```

with no per-`N` rerun, swap, repair, or rescue selector.

If a persisted tail after `K` is required for ordinary bookkeeping, continue the same condition scheduler and order within-condition remainder by `kappa`; no configured candidate may intersect that non-FPS tail.

### 6.6 Exact `M3` model-selection population at every automatic boundary

At every configured automatic fidelity boundary `j` and active `(N, optimizer_seed)` candidate, evaluate the exact same `M3` membership and compute

```text
RMSE_F = sqrt(sum_{x in M3} SSE_x / sum_{x in M3} 3*n_atoms(x))
```

Candidate comparison, practical equivalence, funnel elimination, configured-ceiling diagnosis, recommendation, and no-recommendation state consume only this full-`M3` metric. The old changing `M1/M2/M3` decision ladder is retired.

### 6.7 Diagnostic `pi_eval`, `M1`, and `M2`

Diagnostic evaluation sampling may use one persisted Fisher–Yates permutation over distinct exact `M3` occurrences. Start from occurrences sorted by `kappa`. For `i=|M3|-1 ... 1`:

1. `b=ceil(log2(i+1))`;
2. draw `b` independent unbiased random bits independently of scientific/candidate data;
3. interpret them as integer `r`;
4. reject/redraw while `r>i`;
5. swap positions `i` and `r`.

Nested diagnostic prefixes `M1` and `M2` are simple random samples without replacement (SRSWOR) under that randomization design. They may report finite-population sampling error, atom/component-mass discrepancy, condition/correlation discrepancy, and related diagnostics. They have no target-size decision authority.

Changing only diagnostic `pi_eval` invalidates its diagnostic descendants but does not change reducer identity when exact `M3`, model state, and per-frame predictions are unchanged.

### 6.8 Coverage and split diagnostics

For every configured `T_N`, independently rescore full `P_train` under `d_P` and report at least:

```text
R_max(N)
D_mean(N)
Q50/Q90/Q95/Q99 nearest-selected distance
selected-selected nearest-neighbor Q50/Q90/Q95
represented-condition count
neutral structural-family support summaries
protected-event count/fraction
correlation/effective-sample diagnostics
hard-obligation status separately
```

`R_max(N)` must be nonincreasing for exact nested prefixes.

Split diagnostics report at least `J*`, per-step completion-admissible component set, chosen `(H_max,H_mean,component_key)`, per-condition retained/reserve counts, and final removed-to-retained maximum distance.

Diagnostic `M1/M2` reports may include component-mass/condition discrepancy and SRSWOR uncertainty, explicitly labeled non-decision evidence.

## 7. Prefix qualification

For configured candidate size `N`, derive qualification from the exact prefix:

```text
Q(N) = prefix exists
       AND labels_usable(T_N)
       AND every explicitly accepted hard-support obligation holds
```

Hard-support selectors may consume only frozen pre-candidate evidence explicitly accepted for that obligation. Baseline condition retention is already enforced at split construction; post-order hard obligations do not create permission to reorder or repair the prefix.

FPS distances, retained-set redundancy scores, coverage metrics, event/environment summaries, correlation diagnostics, and diagnostic `M1/M2` sampling evidence remain soft unless a later D1/D2 amendment explicitly promotes a particular hard obligation.

Qualification does not reorder, swap, repair, or expand `T_N`. Candidate outcomes, CV/replay state, and runtime accidents cannot enter qualification.

## 5. Replace Section 12 — EVAL2 target-force estimator

Use:

## 12. EVAL2 target-force estimator

At every automatic target-size fidelity boundary, the exact checkpoint is evaluated on exact `M3`. If `K` Cartesian force components are admitted,

$$
\mathrm{RMSE}_{F,\mathrm{eV}/\AA}=
\sqrt{\frac{1}{K}\sum_{k=1}^{K}(\widehat F_k-F_k)^2},
$$

and the stored target-size metric is

$$
\mathrm{RMSE}_{F,\mathrm{meV}/\AA}=1000\,\mathrm{RMSE}_{F,\mathrm{eV}/\AA}.
$$

Equivalently, with per-frame squared-error sum `SSE_x`, `K=sum_x 3*n_atoms(x)` over exact `M3`.

Device batching may partition inference to bound memory only if exact membership/model state/prediction semantics and the accepted aggregate-reduction equivalence are preserved. A non-finite model prediction or target metric is a typed numerical failure, not an invented infinite score.

`M1/M2` are diagnostic samples and are not alternative Section-12 decision populations.

## 6. Amend Section 13.4 — funnel

Preserve the structural candidate-count funnel

```text
q -> min(q,4) -> 2 -> 1
```

and its existing complete-seed success requirements, but replace the statement that three evaluation sizes are attached to the three positions with:

> The three configured positions carry increasing training-fidelity boundaries only. Every position evaluates the same exact `M3` membership. Diagnostic `M1/M2` sizes are not funnel policy values and cannot alter survivor decisions.

Preserve Section 13.5 configured-ceiling semantics unchanged.

## 7. Replace Section 20 — complexity and scaling

Use:

## 20. Complexity and scaling

Ignoring neural-network training cost, principal target-order/control-plane operations have these governing resource properties:

- local-structure/raw descriptor preparation is bounded by the accepted analysis provider and must not materialize a persistent dense `N x N` frame-distance matrix;
- fitted target-order feature storage is `O(Nd)` for `N` frames and active coordinate dimension `d`;
- the exact reference `J*`/completion solver is sparse memoized dynamic programming over component index, remaining reserve cardinality, and per-condition residual capacities; its worst case is combinatorial in the protected-component/condition-capacity structure, and no simple `O(C*m3)` bound is claimed for the repaired method;
- retained-set structural scoring may stream/chunk candidate-to-retained distances while preserving canonical scalar decisions; persistent dense pairwise state is forbidden;
- condition-local FPS maintains `O(N)` nearest-selected state and is required only through `K=max(candidate_sizes)`;
- the exact proportional condition scheduler uses integer deficits and negligible state relative to descriptors/FPS;
- exact `M3` EVAL2 is linear in evaluated force components at each fidelity boundary and may chunk device inference to bound memory;
- diagnostic Fisher–Yates is `O(|M3|)` time/state; and
- the reducer remains `O(boundaries*candidates*seeds)` with small state relative to training.

Representative supported CPU/RAM feasibility of the exact split/completion method is a Gate-A acceptance condition. Wall time is reported as engineering evidence rather than silently converted into an arbitrary scientific threshold. Resource exhaustion on representative supported input reopens D2; D4 may not obtain a pass by approximating `J*`, weakening condition retention, changing reserve cardinality, or skipping completion-admissibility checks.

## 8. Replace the target-order bullets in Section 21 — verification and falsification oracles

Preserve unaffected source/training/replay/CV/final-production oracles. Replace target-order-specific bullets with:

- independently verify protected-component projection and hard split feasibility;
- compare `J*` and completion-admissibility against exhaustive subset enumeration on bounded fixtures, including infeasible and multiple-optimum cases;
- include a mutual-redundancy counterexample proving retained-set rescoring prevents stale reciprocal redundancy from removing both components;
- verify scientific occurrence-key byte encoding and `source_frame_index` bounds;
- verify provider-contract/coordinate-family lineage against the immutable accepted local-structure specification identity;
- verify all-missing, constant, partial-missing, rare-outlier, and finite-small-variation transform cases;
- perform representative real-feature equal-family sensitivity/ablation and precision-sensitivity challenge evidence before promotion;
- verify input-enumeration, non-semantic UID relabeling, and feature-column permutation metamorphics where their invariance preconditions hold;
- prove each condition medoid and condition-local FPS order against an independently simple scalar reference on bounded fixtures;
- verify proportional condition scheduling using exact integer-deficit reference cases;
- prove `pi_train` is a complete parent permutation and every configured `T_N` is its exact prefix;
- independently rescore full `P_train` coverage and require nonincreasing `R_max` over nested prefixes;
- verify exact full-`M3` reducer input at every automatic boundary and prove changing only diagnostic `pi_eval` cannot alter recommendation when exact `M3` predictions are fixed;
- verify Fisher–Yates diagnostic sampling separately from model-selection decisions;
- measure representative CPU/RAM feasibility of descriptor preparation, exact `J*`/completion solving, retained-set scoring, and K-bounded FPS; and
- fail Gate A if a required D1/D2 evidence realization is unavailable, stale, non-independent where independence is required, or demonstrates that the exact method is not feasible in the supported regime.

Production optimized-vs-reference equivalence, prepared-generation persistence/currentness, old-generation rejection, and real `prepare -> publish -> consume` integration remain downstream Gates B–E evidence because they require the future D3/D4 concretization.

## 9. Replace the target-order portion of Section 22 — reproducibility contract

A numerical reproduction of the target-order experiment requires, as applicable, the exact:

- accepted P1 protected-relation authority and exact `U_size`;
- scientific occurrence-key schema/encoding and protected-component-key semantics;
- bound local-structure numerical-contract identity and neutral aggregation policy;
- fixed source-coordinate schema plus fitted `d_U` and `d_P` coordinate states/medians/scales/family dimensions;
- hard split policy, exact `J*`, retained-set removal trace, and final exact `P_train/M3` memberships;
- canonical scalar distance/reduction/tie semantics;
- `K`, condition medoids, condition-local FPS state sufficient to reconstruct configured prefixes, proportional scheduler semantics, and exact `pi_train` identity;
- every configured `T_N` prefix and explicit hard-support policy;
- exact `M3` decision membership and full-`M3`-at-every-boundary policy;
- diagnostic randomization method/realization plus `pi_eval/M1/M2` identities separately from reducer evidence;
- `mu_sel`, frozen common `mu_loss`, component-weighted `mu_eval`, candidate ladder, optimizer-seed population, fidelity schedule, and practical-equivalence policy;
- exact boundary metrics/failures and reducer history; and
- the unchanged downstream common-training, post-selection, replay, CV, and final-production identities already required by this paper.

Changing only diagnostic `pi_eval` does not change target-size reducer identity. Changing `M3`, `pi_train`, metric/provider semantics, split semantics, full-`M3` evaluation policy, or training method does.

## 10. D2 -> D3 handoff after acceptance

D3 must preserve at minimum:

1. one preparation-owned target-order provider publishing exact metric/split/order state once;
2. no empty-evidence/UID-order fallback when the accepted target-order method is required;
3. exact protected split membership and enough identity to reject stale descendants;
4. exact reference-result semantics for `J*`, completion admissibility, retained-set scoring, medoids, FPS, and proportional scheduling even if implementation algorithms differ;
5. one immutable `pi_train` and exact `T_N` prefixes;
6. exact full `M3` evaluation at every automatic fidelity boundary;
7. diagnostic `pi_eval/M1/M2` state separated from reducer/model-selection identity;
8. fail-closed currentness and restart semantics for persisted target-order evidence; and
9. bounded CPU/RAM execution without a persistent dense frame-pair matrix or silent numerical approximation.

No module layout, cache format, process topology, solver library, or accelerator mechanism is promoted by this D2 amendment unless its identity is required to preserve the numerical semantics above.
