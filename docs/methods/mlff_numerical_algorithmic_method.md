---
title: "mdstats MLFF Numerical Algorithmic Method"
artifact_level: "D2 numerical algorithm design"
status: "proposed Gate-A D2 candidate; accepted 2026-09-13 baseline remains current until independent review and human ratification"
reconstructed_against_commit: "9fd82b0ed40990d56716a393aa3f7db0a2ff44d0"
accepted_baseline_commit: "e8d04144f55c72d799ffcd3fe40c75e47078a66d"
accepted_baseline_date: "2026-09-13"
gate_a_workplan: "MLFF-FPS-COVERAGE-METHOD-RECONCILIATION-1"
gate_a_revision: 5
candidate_materialized_date: "2026-09-14"
---

# mdstats MLFF Numerical Algorithmic Method

## 1. Purpose and authority status

This paper reconstructs the D2 numerical method that realizes the scientific formulation in `mlff_scientific_method.md`. It separates numerically meaningful invariants from replaceable software realization so that optimization or refactoring cannot silently change the experiment.

D1 determines what scientific comparison is meaningful. D2 owns estimators, deterministic constructions, fitted numerical models, normalization, reduction, conditioning, stochastic semantics, and numerical-equivalence requirements. D3/D4 own module placement, persistence, process control, dependency adaptation, caches, and runtime scheduling.

**Authority status.** The reconstruction accepted on 2026-09-13 remains the current D2 numerical/algorithmic authority. This branch materializes the later Gate-A Revision-5 target-order reconciliation directly in the canonical owner path as a **proposed** candidate for independent review. Repository presence does not accept the amendment. The Gate-A candidate becomes current only after the required independent D1/D2 falsification and explicit human ratification. Exact schema names, file layouts, configuration defaults, runtime dependency locks, and serialization forms remain D3/D4 authority except where their value changes the numerical method itself.

The core current D2 invariants are:

- canonical geometry/label/condition evidence preserves the declared physical conventions;
- correlated trajectories are blocked with the shared deterministic autocorrelation primitive and protected relations are closed before incompatible allocations;
- pre-order target membership is constructed from one explicit material-neutral structural-support method; an empty priority vector or lexical UID order is not a valid baseline target-order method;
- exact `U_size -> P_train + M3` splitting preserves protected components, exact reserve cardinality, at least one retained training frame per eligible neutral condition, and globally minimum exact condition depletion before retained-set structural redundancy;
- `d_U` and `d_P` are distinct fitted target-order metrics with fixed source-coordinate schema and exact fit-domain identity;
- one median-nearest-representative-anchored, condition-local exact farthest-point sampling (FPS) construction plus exact proportional condition scheduling owns `pi_train`; every target candidate is the exact prefix `T_N=pi_train[:N]`;
- exact full `M3` target-force EVAL2 is the sole automatic model-selection population at every configured fidelity boundary;
- `pi_eval`, `M1`, and `M2` are diagnostic probability-sampling evidence only and have no ranking, elimination, qualification, tie-break, recommendation, horizon-selection, or freeze authority;
- target-size fitted training state is common across sizes/seeds and candidate projection never refits or renormalizes it;
- optimizer progress is normalized by realized target update count, with the final partial target batch retained;
- each `(N, optimizer_seed)` is one continuous authenticated trajectory through the three configured fidelity boundaries;
- EVAL2 uses exact target-force RMSE over exact `M3` membership;
- the reducer consumes one complete ordered seed matrix and does not average only successful seeds;
- practical equivalence prefers smaller `N`, while a materially superior configured ceiling remains recommendable with explicit nonconvergence evidence;
- post-selection CV and final production are fresh lineages, not continuations of screening trajectories; and
- post-selection replay/checkpoint constraints are method semantics distinct from the target-size screen.

## 2. Canonical source numerical conventions

### 2.1 Occurrence and numerical identity

Source occurrence, geometry, label payload, and labeled-configuration identities are constructed separately. Quantized fingerprints use explicit tolerances owned by the current source/frame specifications. Geometry fingerprints include ordered species, periodic flags, cell, and wrapped fractional coordinates but exclude target labels, so duplicate geometry remains detectable across different source occurrences or label payloads.

A numerically different quantization/tolerance policy changes identity behavior and therefore requires explicit compatibility treatment; an implementation may not silently use floating-point object equality or path identity instead.

### 2.2 Row-vector cells and deformation gradient

For ASE row-vector cells,

$$
\mathbf r_{\text{row}}=\mathbf s_{\text{row}}\mathbf H.
$$

With reference cell `H_0` and current cell `H_t`, the current MLFF strain reconstruction uses

$$
\mathbf F=\left(\mathbf H_0^{-1}\mathbf H_t\right)^T.
$$

A proper polar decomposition

$$
\mathbf F=\mathbf R\mathbf U
$$

is computed by singular-value decomposition. Reflections, singular cells, or nonpositive stretch singular values are rejected. Derived strain measures include

$$
\boldsymbol\varepsilon_{\text{lin}}=\frac12(\mathbf F+\mathbf F^T)-\mathbf I,
$$

$$
\mathbf E=\frac12(\mathbf F^T\mathbf F-\mathbf I),
$$

and logarithmic strain

$$
\mathbf L=\log\mathbf U.
$$

The numerical record also derives `det(F)`, rotation angle, principal logarithmic strains, hydrostatic/deviatoric measures, and engineering shear from the declared tensor convention. A different transpose convention, implicit reference cell, or shear-factor convention is not numerically equivalent.

### 2.3 Stress normalization

Source stress is normalized to the canonical symmetric Cartesian Cauchy-stress representation and internal unit convention. Conversions must preserve sign, Voigt ordering, and tensor-vs-engineering shear semantics. Virial-like quantities remain a distinct channel unless explicitly converted by an accepted owner.

Stress round-trip checks are numerical falsification oracles: a sign reversal, shear-factor error, or Voigt permutation is a D1/D2 correctness failure, not a formatting issue.

### 2.4 Eligibility numerical checks

Eligibility validates finite/nonsingular geometry, atom-count consistency, required label completeness, finite force/energy fields, stress symmetry/finite values when present, and the active electronic-convergence/source-quality gates. Unusual but finite values remain data; the eligibility algorithm must not implement an implicit “typical value” filter.

## 3. Correlated-sampling primitives and neutral statistical units

### 3.1 Exact autocorrelation estimator

The current MLFF neutral substrate reuses the shared `mdstats.sampling` autocorrelation algorithm. For a finite one-dimensional scalar sequence it computes unbiased FFT autocovariance, normalizes to `rho(k)`, and uses Geyer's initial-positive-sequence truncation. Adjacent lag pairs are accumulated while

$$
\rho(2m-1)+\rho(2m)>0.
$$

An unpaired final positive lag may be retained. The integrated time is bounded to the current policy range, with the canonical floor `1/2` stored frame. Constant or insufficient sequences are represented explicitly rather than generating a fabricated long correlation time.

The effective count is

$$
N_{\text{eff}}=\min\left(N,\frac{N}{2\tau_{\text{int}}}\right).
$$

No autocorrelation is computed across a source gap, continuation reset, or excluded interval.

### 3.2 Complete-frame block length

For every configured observable and contiguous run, estimate `tau`. Let

$$
\tau_{\max}=\max_{j,r}\tau_{j,r}.
$$

The correlation-derived block target is

$$
L_{\text{corr}}=\max\left(1,\left\lceil m\tau_{\max}\right\rceil\right),
$$

and the resolved target is

$$
L=\max(L_{\min},L_{\text{corr}}),
$$

unless an explicit accepted override is in force. A short override is recorded as an adequacy limitation rather than silently treated as decorrelated support.

For a contiguous run longer than `L`, the balanced all-frame split retains every eligible frame. No remainder or tail is dropped.

### 3.3 Protected event merge and relation closure

Full-resolution event windows are constructed before ordinary thinning. When an event crosses candidate block boundaries, the affected blocks are merged before role allocation so the protected event remains indivisible.

Current split-exclusion evidence contains five relation families:

1. correlation-unit membership;
2. exact geometry-duplicate membership;
3. protected-event membership;
4. condition-scoped replica lineage across distinct runs; and
5. condition-scoped structural-realization lineage across distinct runs.

The canonical P1 relation owner projects these relations to a requested frame universe and computes their transitive connected components. P2 consumes those components; it does not reconstruct protected relations from raw provenance or model evidence.

### 3.4 Neutrality of the target-size substrate

The current neutral condition key contains reduced formula, temperature condition, strain class, regime, and optional user labels. It does not contain the retired `label_domain_id` partition axis, and the neutral statistical base constructs no pre-target-size cross-validation plan.

This does not remove upstream label compatibility. It removes compatibility-domain and preselection-CV fan-out from the target-size algorithm.

## 4. Pre-order selection evidence versus common training preparation

### 4.1 Pre-order target-order evidence

The baseline target-order method consumes one fixed candidate-independent evidence family:

- canonical neutral condition/provenance evidence;
- universal frame-level cell geometry;
- universal strain coordinates where scientifically defined; and
- material-neutral, element-resolved frame summaries of the accepted local-structure numerical contract.

Mass density, material/profile pair-rule coordinates, declared/profile atom groups or site classes, material-specific event descriptors, foundation-model predictions/descriptors, and label-derived residual/difficulty are not baseline membership coordinates.

Two fitted target-order metrics are authorized:

- `d_U`, fitted on exact `U_size`, is used only for pre-split retained-set structural redundancy;
- `d_P`, refitted after the split on exact `P_train`, is used for condition median-nearest representatives, condition-local FPS, and training-prefix coverage diagnostics.

`M3` labels and candidate outcomes fit neither metric. Pre-order target-order evidence is preparation-owned scientific state and is published once with the immutable prepared generation; downstream commands consume that state rather than reconstructing it from live inputs.

There is no valid baseline state in which required target-order evidence is represented by an empty priority vector and lexical UID order.

### 4.2 Post-order common candidate-training preparation

`TargetSizeCommonPreparation` is a separate later object. It is built after the exact `P_train/M3` split and canonical P2 orders exist, over exact `P_train`, and is shared by every candidate `N` and optimizer seed.

Its current fitted numerical state includes, as applicable:

- the common target atomic-reference fit;
- mean-one normalized configuration weights over exact `P_train`;
- per-frame property availability masks;
- the current foundation/head identity and target training objective;
- one common MACE neighbor/model-construction normalization fitted over `P_train`; and
- the canonical realized candidate architecture/method inputs that must be identical across sizes except for explicitly N-dependent execution quantities.

Candidate projection selects frozen common values for `T_N`. It does **not** renormalize configuration weights, refit `E0`, or recompute common model normalization on each prefix.

This separation is a numerical anti-confounding requirement and removes the circular statement that a P3 common preparation could be an input to the P2 order that precedes it.

## 5. Canonical target-order evidence and fitted metrics

### 5.1 Exact target-size population and protected components

`U_size` is the set of exact DEVELOPMENT frames from the accepted neutral substrate that are currently eligible and have canonical training labels. It must contain enough frames for both configured `N_max` and exact reserve cardinality `m3`.

Project the accepted P1 protected-relation authority onto `U_size` and compute transitive connected components. These components are indivisible allocation units for `P_train/M3`.

Every eligible neutral condition represented in `U_size` is training-critical for the baseline target-size experiment: a valid split must retain at least one `P_train` frame from every such condition.

### 5.2 Scientific occurrence key, component tie key, and exact encoding

Target-order tie and identity semantics use a **scientific occurrence key** that distinguishes declared source occurrences even when their source content and geometry are identical:

```text
schema = "mdstats.target-order-scientific-occurrence-key.v4"
condition_id
source_occurrence_signature
source_frame_index
geometry_fingerprint
```

`source_occurrence_signature` is the accepted upstream occurrence identity that binds the declared run occurrence, including its run/source-locator context and source-content identity. `source_identity_signature` alone is insufficient because two declared occurrences may intentionally share identical source content.

Canonical encoding is:

- every UTF-8 string `v`: `uint64_big_endian(len(utf8(v))) || utf8(v)`;
- `source_frame_index`: unsigned 64-bit big-endian with `0 <= source_frame_index <= 2^64-1`;
- concatenate fields in the stated order after the schema field and SHA-256 the resulting bytes.

Out-of-range frame index is an identity failure, not an alternate encoding. Call the resulting digest `kappa`. The accepted occurrence authority must not contain two exact `U_size` frames with the same `(source_occurrence_signature, source_frame_index)` pair; therefore every exact `U_size` frame must have a unique `kappa`. A duplicate `kappa` is a fail-closed target-order identity error rather than a tie to be resolved by traversal order or lexical `frame_uid` spelling.

Numerical component ordering uses a separate **component tie key**, not the serialized P1 relation/component digest:

```text
schema = "mdstats.target-order-component-tie-key.v1"
member_count
member_kappa_1 ... member_kappa_member_count
```

Sort member `kappa` values lexicographically. Encode the schema and each `kappa` with the same length-prefixed UTF-8 rule above; encode `member_count` as unsigned 64-bit big-endian between the schema and member list; SHA-256 the concatenation. This definition applies equally to singleton and multi-frame components. Because exact `U_size` `kappa` values are unique and projected components are disjoint, `component_key` is unique within the split population.

The accepted P1 split-exclusion authority identity, projected component membership, and ancestry/currentness evidence remain separately bound to the split-method identity so stale or semantically changed P1 relations are rejected. They do **not** participate in numerical component tie ordering. This separation preserves P1 ownership/currentness while preventing non-semantic `frame_uid` serialization or relation-path spelling from changing a target-order tie.

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

The local-structure source is bound to the analysis-owned numerical contract rather than to feature-name coincidence:

```text
analysis_owner = mdstats.analysis.local_structure
LOCAL_STRUCTURE_POLICY_SCHEMA = mdstats.local-structure-feature-policy.v1
LOCAL_STRUCTURE_RESULT_SCHEMA = mdstats.local-structure-feature-result.v1
LOCAL_STRUCTURE_POLICY_VERSION = mdstats.analysis.local-structure.2026-07.v1
numerical specification path = docs/specs/analysis/local_structure_features_spec.md
Gate-A reconciled specification blob = ee7ecb7deb0412bdec5ca24b81d539e2d8ee6569
2026-09-13 baseline specification blob = cc5be8d4f31d9168e09f2baa07711d5c37cf9b62
```

The reconciled specification makes the already implemented switch, weighted-distance, species-entropy, radial, density, Legendre, bond-orientational, missing-mask, feature-order, and binary64/backend semantics explicit without changing the underlying feature-value method. A semantic change to that analysis-owned contract changes target-order metric identity and reopens D2.

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

`maximum_dense_pair_work` is a resource guard, not a feature-value parameter.

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
   - `q10/q50/q90`: Hyndman-Fan type-7 quantiles after ascending numerical sort.

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

### 5.6 Equal-family normalization and canonical scalar distance order

Every active semantic family `f` is divided by `sqrt(d_f)`, where `d_f` counts only active numerical coordinates and varying missingness indicators. Equal active-family mass is the explicit no-prior baseline and remains subject to Gate-A real-feature sensitivity/ablation evidence before promotion.

The final metric is scalar binary64 Euclidean distance. Its source-coordinate order is a D2 numerical invariant because squared-distance accumulation is left-to-right binary64 and exact score equality controls ties.

Each transformed coordinate has the canonical semantic order key

```text
(family_rank, scope_rank, atomic_number, feature_rank, statistic_rank, coordinate_kind_rank)
```

compared lexicographically as integers. The ranks are:

```text
family_rank:
  0 cell_geometry
  1 strain
  2 pair_distance
  3 coordination
  4 connectivity
  5 chemical_environment
  6 local_density
  7 radial_environment
  8 angular_environment
  9 orientational_order

scope_rank:
  0 global frame coordinate
  1 element-resolved aggregate

statistic_rank for element aggregates:
  0 mean
  1 std
  2 min
  3 max
  4 q10
  5 q50
  6 q90

coordinate_kind_rank:
  0 transformed numerical coordinate
  1 missingness indicator
```

For global frame coordinates, set `atomic_number=0` and `statistic_rank=0`. Their `feature_rank` follows the exact order in Section 5.3: cell volume, lengths `a/b/c`, angles `alpha/beta/gamma`; then hydrostatic strain, deviatoric-strain norm, and engineering shear `xy/yz/zx` within the separate `strain` family.

For element-resolved local coordinates, `atomic_number` is the integer atomic number in ascending order. `feature_rank` is family-local in the Section-5.3 feature order: nearest/weighted-mean/weighted-std for `pair_distance`; smooth coordination; hard-neighbor-count then weighted-degree for `connectivity`; species entropy; local density; radial centers in increasing configured center order; angular Legendre orders in increasing order; and orientational orders in increasing order. `statistic_rank` then orders the seven aggregate statistics above. If both the numerical coordinate and a varying missingness indicator are active, the numerical coordinate precedes its indicator by `coordinate_kind_rank`.

Inactive coordinates are omitted before distance evaluation and do not create gaps with semantic effect. Serialization strings, mapping iteration order, provider column order, and lexical `frame_uid` order do not define this semantic order.

For two transformed frames, squared distance uses scalar multiply followed by left-to-right binary64 addition in the canonical order above. Fused contraction is not reference semantics. Exact binary64 score equality is the only numerical-score tie; ties use `kappa` or `component_key` as specified. There is no PCA, whitening, learned weighting, random projection, foundation descriptor, or profile-specific membership block. An optimized path must reproduce the same discrete decision or fall back to canonical scalar comparison.

### 5.7 Two fit domains

- `d_U`: fit on exact `U_size` and used only by pre-split retained-set redundancy;
- `d_P`: refit after the split on exact `P_train` and used for condition median-nearest representatives, condition-local FPS, and training-prefix coverage diagnostics.

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

Worst-case state growth is combinatorial in the protected-component/condition-capacity structure; this method therefore makes no `O(C*m3)` claim for the repaired split. Representative CPU/RAM feasibility of the exact method is a Gate-A acceptance condition. Resource exhaustion is explicit preparation infeasibility of the proposed method in the tested supported regime and reopens D2; it is not permission for D4 approximation.

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

### 6.4 Condition median-nearest representatives and exact condition-local FPS

Fit `d_P` on final exact `P_train`.

For every nonempty `P_train` condition:

1. compute the coordinate-wise type-7 median vector in fitted `d_P` coordinates;
2. choose the observed frame minimizing canonical squared distance to that vector; exact ties use `kappa`; this frame is the **median-nearest representative** (called the condition medoid in earlier Gate-A drafts, but it is not defined by minimum total pairwise distance);
3. initialize that condition's exact FPS order with the median-nearest representative;
4. repeatedly select the remaining frame maximizing canonical nearest-selected squared distance; exact ties use `kappa`.

FPS is required only through `K=max(configured candidate_sizes)` for candidate membership. An optional persisted tail beyond `K` is not allowed to alter any configured candidate.

### 6.5 Exact global condition scheduler and `pi_train`

Let `N_c` be the final `P_train` count for condition `c`, let `N=|P_train|`, and let `s_c(k)` be the number emitted from condition `c` after `k` global ranks.

Anchor phase emits one median-nearest representative per condition ordered by decreasing `N_c`, then canonical condition ID. Therefore configured `N_min` must be at least the number of represented `P_train` conditions.

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

The current structural policy retains three configured evaluation cardinalities

```text
0 < m1 < m2 < m3
```

and requires all three to be positive powers of two. Their decision roles change under Gate A: `m3 = |M3|` is the exact automatic model-selection population, while `m1` and `m2` are diagnostic prefix cardinalities only.

Diagnostic evaluation sampling uses one persisted Fisher-Yates permutation over distinct exact `M3` occurrences. Start from occurrences sorted by unique `kappa`. For `i=|M3|-1 ... 1`:

1. `b=ceil(log2(i+1))`;
2. draw `b` independent unbiased random bits independently of scientific/candidate data;
3. interpret them as integer `r`;
4. reject/redraw while `r>i`;
5. swap positions `i` and `r`.

Define

```text
M1 = pi_eval[:m1]
M2 = pi_eval[:m2]
M3 = exact frozen reserve membership
```

`M1` and `M2` are simple random samples without replacement (SRSWOR) under that randomization design. They may report finite-population sampling error, atom/component-mass discrepancy, condition/correlation discrepancy, and related diagnostics. They have no target-size decision authority.

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

### 6.9 Current structural policy domain

The current target-size policy requires:

- at least three strictly increasing positive power-of-two candidate sizes;
- exactly three strictly increasing positive power-of-two evaluation cardinalities `(m1,m2,m3)`, interpreted according to Section 6.7;
- exactly three strictly increasing positive fidelity epochs; and
- one ordered unique nonnegative optimizer-seed population.

Exact default values remain specification/configuration authority. These structural restrictions are part of the current algorithm, not a general scientific theorem. Changing them creates a different target-size policy identity.

## 7. Prefix qualification

For configured candidate size `N`, derive qualification from the exact prefix:

$$
Q(N)=
\text{prefix exists}
\land\text{labels usable}(T_N)
\land\bigwedge_j c_j(T_N)\ge q_j.
$$

Hard-support selectors may refer only to frozen pre-candidate condition evidence explicitly accepted for that obligation. Baseline condition retention is already enforced at split construction; post-order hard obligations do not create permission to reorder or repair the prefix.

FPS distances, retained-set redundancy scores, coverage metrics, event/environment summaries, correlation diagnostics, and diagnostic `M1/M2` sampling evidence remain soft unless a later D1/D2 amendment explicitly promotes a particular hard obligation.

Qualification does not reorder, swap, repair, or expand `T_N`. Because prefixes are nested and hard-support counts are membership counts, support counts are monotone nondecreasing in `N`. A contradictory qualification lineage indicates corrupt policy/evidence rather than a reason to mutate the order. Candidate outcomes, CV/replay state, and runtime accidents cannot enter qualification.

The current funnel requires at least three qualified candidates before automatic numerical screening.

## 8. Common atomic-reference and weight fitting

### 8.1 Count matrix and total-energy target

For exact fit membership `D`, construct a count matrix `C` whose row `i` contains the number of atoms of each element in frame `i`. Let `y` be the selected total-energy vector.

For from-scratch fitting, the configured regularized least-squares problem is conceptually

$$
\widehat e=\arg\min_e
\left[\|Ce-y\|_2^2+\lambda\|e-e_{\text{prior}}\|_2^2\right],
$$

with the prior term active only under the corresponding policy.

For foundation-model fine-tuning, the current production method fits the residual against the bound foundation prediction. With foundation predicted total energy `y_fnd` and foundation elemental references `e_fnd`,

$$
r=y-y_{\text{fnd}},
$$

$$
\widehat{\delta e}=\arg\min_{\delta e}
\left[\|C\delta e-r\|_2^2+
\lambda\|\delta e-\delta e_{\text{prior}}\|_2^2\right],
$$

and

$$
e_{\text{target}}=e_{\text{fnd}}+\widehat{\delta e}.
$$

The result binds element order by semantic atomic-number key, not serialized mapping iteration order.

### 8.2 Conditioning evidence

The solver records rank/singular-value information, null-space dimension where applicable, residual RMSE/MAE/maximum error, and rank-deficiency/transfer warnings. Rank deficiency is structural identifiability evidence; tightening a floating-point tolerance cannot recover a composition direction absent from `C`.

### 8.3 Configuration weights and masks

Common per-configuration weights are fitted once over the exact common membership and normalized to mean one. The current policy may equalize represented condition strata and then apply its configured bounds/multipliers.

Candidate projection never recomputes the mean on `T_N`, because doing so would make the loss scale candidate-dependent.

Local energy/force/stress property weights are availability masks derived from canonical label presence. They are not copies of the global objective ratio.

## 9. Objective and dependency-facing loss semantics

The numerical loss preserves three layers:

- global energy/force/stress coefficients;
- positive per-configuration weights; and
- local property availability masks.

The accepted current MACE method realizes these with the native weighted energy+forces+stress loss. The global coefficients are applied once. Configuration weights and local masks are consumed at their intended local layers.

A different mathematical loss family is not numerically equivalent merely because coefficients can be manipulated to resemble one another. In particular, a robust loss that inserts weights inside a nonlinear residual transformation cannot be made equivalent by naively rescaling the global coefficients.

The exact pinned MACE dependency and source-shape guards are **D3/D4 conformance mechanisms**. D2's invariant is that the executed dependency must realize the authenticated weighted objective, optimizer values, sample exposure, and batch geometry. A future dependency version may replace the current adapter only after proving these same numerical semantics or explicitly reopening D2.

## 10. Target-size optimizer-progress normalization

### 10.1 Confound being controlled

With target batch size `B`, candidate `N` exposes

$$
U_N=\left\lceil\frac{N}{B}\right\rceil
$$

target optimizer updates per nominal epoch when the final partial batch is retained. A fixed per-update learning rate and EMA decay would therefore couple larger `N` to larger optimizer progress.

### 10.2 Current normalization

For reference size `N_ref`, reference learning rate `LR_ref`, and reference EMA decay `beta_ref`, define

$$
U_{\text{ref}}=\left\lceil\frac{N_{\text{ref}}}{B}\right\rceil,
\qquad
s_N=\frac{U_{\text{ref}}}{U_N}.
$$

The target-size screen uses

$$
\text{LR}_N=\text{LR}_{\text{ref}}s_N,
$$

and, when EMA is enabled,

$$
\beta_N=\beta_{\text{ref}}^{s_N}.
$$

This preserves the first-order per-epoch products

$$
\text{LR}_N U_N=\text{LR}_{\text{ref}}U_{\text{ref}},
$$

and

$$
(\beta_N)^{U_N}=\beta_{\text{ref}}^{U_{\text{ref}}}.
$$

The normalized values are computed once from the full candidate geometry and remain unchanged through later fidelity rungs. Survivor count does not rescale them.

### 10.3 Not exact optimizer-path equivalence

This is a first-order progress normalization, **not** a theorem that candidate trajectories have identical optimization dynamics. Residual differences include minibatch stochasticity, order-dependent gradients, Adam/AMSGrad moment history, finite discretization of the learning-rate schedule, and candidate-dependent loss landscape/data composition.

The intended estimand is therefore the current normalized screening method, not an imaginary optimizer-invariant learning curve.

### 10.4 Complete target batches

The ceiling update geometry is valid only when the final partial target batch is retained. Target-size execution therefore requires:

- `drop_last = false` for the target path;
- every exported target UID exposed once per epoch under the accepted loader semantics;
- no duplicate padding merely to complete the last batch; and
- no distributed sampler that truncates the target population unless it proves exact equivalent coverage/update geometry.

A runtime that produces `floor(N/B)` updates is a different numerical experiment.

## 11. Continuous fidelity trajectories and restart

For active `(N,s)` with optimizer seed `s`, training is one continuous trajectory through configured boundaries

$$
n_1<n_2<n_3.
$$

The exact predecessor state includes model, optimizer, EMA where enabled, learning-rate state, and the Python/NumPy/Torch RNG lineage required by the accepted runtime. A later rung restores its authenticated predecessor rather than restarting from the foundation model.

Accepted progress is immutable evidence. Unaccepted first-rung materialization/checkpoint state is attempt-local scratch and may be reclaimed only under the D3 execution-ownership rules that prevent concurrent writers from deleting live work.

Recovery cannot change candidate membership, normalization, common preparation, seed, or boundary identity.

## 12. EVAL2 target-force estimator

At every automatic target-size fidelity boundary, the exact checkpoint is evaluated on exact `M3`. If `K` Cartesian force components are admitted,

$$
\text{RMSE}_{F,\text{eV}/\text{Å}}=
\sqrt{\frac{1}{K}\sum_{k=1}^{K}
(\widehat F_k-F_k)^2},
$$

and the target-size stored metric is

$$
\text{RMSE}_{F,\text{meV}/\text{Å}}=
1000\,\text{RMSE}_{F,\text{eV}/\text{Å}}.
$$

Equivalently, with per-frame squared-error sum `SSE_x`, `K=sum_x 3*n_atoms(x)` over exact `M3`.

Device batching may partition inference to bound memory. Batch width is execution-only only if exact membership/model state/prediction semantics are preserved and the aggregate metric agrees under the accepted floating-point equivalence contract.

A non-finite model prediction or non-finite target metric is a typed numerical failure, not an invented infinite score.

`M1/M2` are diagnostic samples and are not alternative Section-12 decision populations.

## 13. Pure target-size reducer

### 13.1 Ordered boundary matrix

At boundary `j`, with active candidates `A_j` and configured ordered seeds `S`, the expected outcome sequence is size-major then seed-minor over

$$
A_j\times S.
$$

Every outcome binds the exact experiment definition, execution context, boundary epoch, and exact `M3` membership identity. Missing, duplicate, reordered, foreign, or lineage-incompatible evidence produces an insufficient-comparison terminal result rather than being silently rearranged.

### 13.2 Complete-seed score

A size receives a finite score only when **all** configured seeds have finite valid target metrics:

$$
\bar E_N=\frac{1}{|S|}\sum_{s\in S}E_{N,s}.
$$

If any seed has an authenticated numerical failure, that candidate is removed from successful comparison. The mean is never computed over only the successful subset.

Current typed failures include non-finite training model state, non-finite optimizer state, non-finite evaluation prediction, and non-finite target metric.

### 13.3 Practical-equivalence order

Given successful scores and tolerance `epsilon`, repeatedly find the current best score `E_min`, define the equivalent set

$$
\mathcal E=\{N:E_N\le E_{\min}+\epsilon\},
$$

choose the smallest `N` in `E`, remove it, and repeat. The current implementation uses only a tiny fixed floating-point comparison guard beyond the scientific `epsilon`; machine epsilon is not the practical-equivalence policy.

### 13.4 Funnel

The structural funnel is

$$
q\rightarrow\min(q,4)\rightarrow2\rightarrow1,
$$

where `q` is the number of qualified candidates entering the first boundary.

At the first boundary the number of successful candidates must be at least `min(|A_1|,4)`; the second and terminal comparisons require two successful candidates. Otherwise the reducer terminates with insufficient comparison.

The three configured positions carry the three strictly increasing training-fidelity boundaries only. Every position evaluates the same exact `M3` membership. Diagnostic `m1/m2` cardinalities are not funnel policy values and cannot alter survivor decisions.

### 13.5 Configured-ceiling rule

Let `N_max` be the configured maximum candidate and suppose it is a successful terminal finalist. If

$$
E_{N_{\max}}+\epsilon<E_N
$$

for every other successful terminal finalist, `N_max` is materially superior, is recommended, and carries the explicit nonconvergence-at-configured-ceiling diagnostic.

Otherwise the first practical-equivalence-ranked finalist is recommended. This naturally selects the smaller finalist when its score is within `epsilon` of the best.

The reducer does not extrapolate a learning curve, solve for an asymptotic root, or invent an unconfigured rescue size.

## 14. Post-selection fold construction and fitting

After the operator's collection is frozen, each admitted `T_N` is validated separately. Current post-selection fold construction is downstream of target-size selection and is **not** the retired DATA5 preselection CV authority.

For each required fold:

1. partition only the exact frozen `T_N` while preserving inherited protected relations and purge requirements;
2. derive a checkpoint-monitor role from training-eligible evidence, disjoint from held-out evaluation;
3. fit all fold-local transforms/atomic references/other fitted training inputs from the fold training domain only;
4. initialize a fresh model/optimizer lineage under the frozen post-selection method;
5. train for the selected CV horizon;
6. choose an admissible representative using only authorized monitor/integrity/replay-retention evidence; and
7. after representative freeze, evaluate once on the held-out fold.

Every configured fold and seed required by the policy must be represented. A missing fold, failed required seed, no-admissible-checkpoint outcome, or method-identity mismatch is not ignored to obtain a favorable acceptance statistic.

## 15. Checkpoint selection as constrained optimization

The post-selection checkpoint owner filters candidates through mandatory constraints before ranking. The current constraint family can include target/focus/condition/property integrity and replay-retention requirements.

If the admissible set is empty, the run has no admissible checkpoint. The algorithm must not fall back to “best target error among inadmissible checkpoints.”

Only after admissibility is established does the policy apply its deterministic target-side ranking/tie semantics. Held-out fold data are unavailable to this decision.

## 16. Replay and post-selection exposure

### 16.1 Separation from target-size screening

Target-size execution has zero replay training samples. Its numerical identity is target-only. Post-selection replay therefore cannot alter P2/P3 target-size evidence or target membership.

### 16.2 Replay label modes

The current post-selection architecture supports:

- true-reference/DFT replay as the canonical default when canonical replay labels are available; and
- foundation pseudo-label replay only under explicit opt-in policy bound to the frozen foundation model/head.

Pseudo-label replay is not an automatic substitution for missing DFT labels. A pseudo-label training path still requires a separate true-reference replay-monitor lineage under current policy.

Replay source membership, label mode, monitor membership, head identity, exposure policy, and realized counts belong to post-selection method identity.

### 16.3 No hidden target duplication

Current replay-enabled execution explicitly disables the dependency behavior that would duplicate target examples to satisfy a target/replay ratio heuristic. Effective target membership/count must equal the authenticated target exposure. Any intentional future resampling would need its own accepted D2/D3 policy.

## 17. Fresh final production and publication selection

Final production starts a new lineage on complete exact `T_N`; screen and CV checkpoints are never warm-start parents.

For each required final seed, the final-production run freezes its representative using the accepted checkpoint/admissibility owner and exact target evaluation evidence. The final publication decision is then made **before** downstream qualification.

The current architecture supports two publication modes:

- publish every required final seed whose frozen representative is admissible; or
- among already-frozen admissible representatives, publish one deterministic best representative using the accepted target-only final-production ordering/tie material.

These modes are upstream product-membership algorithms. Qualification/physical/locked evidence never enters the cross-seed publication ranking.

## 18. Current dependency realization boundary

The accepted current adapter is qualified against `mace-torch==0.3.16`. That exact upstream version contains behaviors that would violate the D2 invariants if allowed to control the method: forced `UniversalLoss` under multihead fine-tuning, LR/EMA mutation, ratio-driven target duplication, and target-batch truncation.

mdstats currently source-qualifies and narrowly guards/repairs those behaviors in its existing qualified execution seam. Those source markers, package version, and patch mechanics are **not timeless D2 requirements**. They are current D3/D4 evidence that the dependency realizes the D2 method. A future dependency can replace them only after demonstrating the same resolved loss, optimizer, exposure, and batch semantics or after an explicit D2 revision.

## 19. Numerical failure, conditioning, precision, and uncertainty

### 19.1 Failure is typed evidence

A failed numerical comparison is different from a poor but finite model. Non-finite model/optimizer state and non-finite evaluation evidence carry typed failure identities. Missing or contradictory boundary evidence produces insufficient comparison. Neither is silently converted into an arbitrary finite/infinite ranking value.

### 19.2 Atomic-reference conditioning

Rank and null-space evidence characterize an identifiability problem, not merely solver accuracy. A null direction in element-count space persists at infinite arithmetic precision unless additional independent compositional information or an accepted prior changes the mathematical problem.

### 19.3 Optimizer stochasticity

Optimizer seeds are explicit stochastic replicates. Pairing controls one source of comparative variation but does not remove minibatch, finite-horizon, or model-training uncertainty. Reproducibility means preserving the accepted seed/method lineage and numerical compatibility contract, not claiming bitwise identity across unsupported hardware/library regimes.

### 19.4 Precision and backend

Learned-model dtype, critical-precision policy, acceleration/backend behavior, and other numerically trajectory-changing settings belong to method/execution identity. Worker count, queue order, cache path, device-batch width for exact evaluation, and file-backed representation are execution-only only when they preserve the accepted numerical result.

## 20. Complexity and scaling

Ignoring neural-network training cost, principal control-plane operations have these governing resource properties:

- autocorrelation estimation: FFT-dominated per observable/run plus linear block construction;
- relation closure: near-linear in frame/relation edges with union-find-style closure;
- local-structure/raw descriptor preparation is bounded by the accepted analysis provider and must not materialize a persistent dense `N x N` frame-distance matrix;
- fitted target-order feature storage is `O(Nd)` for `N` frames and active coordinate dimension `d`;
- the exact reference `J*`/completion solver is sparse memoized dynamic programming over component index, remaining reserve cardinality, and per-condition residual capacities; its worst case is combinatorial in the protected-component/condition-capacity structure, and no simple `O(C*m3)` bound is claimed for the repaired method;
- retained-set structural scoring may stream/chunk candidate-to-retained distances while preserving canonical scalar decisions; persistent dense pairwise state is forbidden;
- condition-local FPS maintains `O(N)` nearest-selected state and is required only through `K=max(candidate_sizes)`;
- the exact proportional condition scheduler uses integer deficits and negligible state relative to descriptors/FPS;
- exact `M3` EVAL2 is linear in evaluated force components at each fidelity boundary and may chunk device inference to bound memory;
- diagnostic Fisher-Yates is `O(|M3|)` time/state; and
- the reducer remains `O(boundaries * candidates * seeds)` with tiny state relative to training.

Training dominates total computational cost. Representative supported CPU/RAM feasibility of the exact split/completion method is a Gate-A acceptance condition. Wall time is engineering evidence rather than an arbitrary scientific threshold. Resource exhaustion on representative supported input reopens D2; D4 may not obtain a pass by approximating `J*`, weakening condition retention, changing reserve cardinality, or skipping completion-admissibility checks.

Performance changes are admissible only when they preserve the authoritative memberships, fits, trajectories, reductions, and decisions above.

## 21. Verification and falsification oracles

The D2 method should be falsified through independent invariants rather than only by successful end-to-end execution:

- verify cell/strain/stress round trips under the declared conventions;
- verify autocorrelation parity against the shared sampling oracle and complete-frame block coverage without dropped tails;
- re-derive P1 protected relations and reject stale split descendants;
- prove the neutral target-size condition key has no compatibility-domain/CV fan-out;
- independently verify protected-component projection and hard split feasibility;
- compare `J*` and completion-admissibility against exhaustive subset enumeration on bounded fixtures, including infeasible and multiple-optimum cases;
- include a mutual-redundancy counterexample proving retained-set rescoring prevents stale reciprocal redundancy from removing both components;
- verify scientific occurrence-key byte encoding and `source_frame_index` bounds;
- construct two declared source occurrences with identical source-content identity, frame index, condition, and geometry but different `source_occurrence_signature`; require distinct `kappa` values and traversal-order-invariant downstream ties;
- verify exact `U_size` `kappa` uniqueness and fail closed on a duplicate;
- verify `component_key` from sorted member `kappa` only, including singleton and multi-frame components, while changing only P1/UID serialization leaves the tie key unchanged when semantic member occurrences are unchanged;
- verify provider-contract/coordinate-family lineage against the exact reconciled local-structure specification blob and direct scalar formulas for switch, weighted distance, species entropy, radial, density, Legendre, orientational, and missing-mask behavior;
- verify all-missing, constant, partial-missing, rare-outlier, and finite-small-variation transform cases;
- verify the canonical semantic coordinate-order key, including family/element/feature/statistic/kind order, and prove serialized feature-column permutation cannot change canonical scalar accumulation or downstream discrete decisions;
- perform representative real-feature equal-family sensitivity/ablation and precision-sensitivity challenge evidence before promotion;
- verify input-enumeration and non-semantic UID relabeling metamorphics where their invariance preconditions hold;
- prove each condition median-nearest representative and condition-local FPS order against an independently simple scalar reference on bounded fixtures;
- verify proportional condition scheduling using exact integer-deficit reference cases;
- prove `pi_train` is a complete parent permutation and every configured `T_N` is its exact prefix;
- independently rescore full `P_train` coverage and require nonincreasing `R_max` over nested prefixes;
- verify exact full-`M3` reducer input at every automatic boundary and prove changing only diagnostic `pi_eval` cannot alter recommendation when exact `M3` predictions are fixed;
- verify Fisher-Yates diagnostic sampling separately from model-selection decisions;
- prove hard-support qualification is re-derived from the exact prefix and pre-candidate obligation policy;
- prove candidate projection does not refit/renormalize common weights, `E0`, or model normalization;
- verify realized target batches equal `ceil(N/B)` with no target duplication;
- verify normalized LR/EMA identity is fixed across the surviving rungs of one candidate;
- replay reducer history through the pure transition owner and require the same result;
- prove incomplete/reordered matrices fail rather than being reordered or subset-averaged;
- prove held-out CV labels cannot reach fold fitting or checkpoint selection;
- verify a no-admissible-checkpoint outcome does not fall back to an inadmissible checkpoint;
- verify replay-only changes invalidate post-selection descendants but do not mutate the frozen target-size evidence;
- verify final-product member selection is complete before downstream qualification;
- measure representative CPU/RAM feasibility of descriptor preparation, exact `J*`/completion solving, retained-set scoring, and K-bounded FPS; and
- prove execution resource/chunk/cache changes preserve outputs under the accepted exact/bounded numerical-equivalence contract.

Required Gate-A evidence that is unavailable, stale, non-independent where independence is required, or demonstrates infeasibility blocks acceptance. Production optimized-versus-reference equivalence, prepared-generation persistence/currentness, old-generation rejection, and real `prepare -> publish -> consume` integration remain downstream D3/D4 Gates B-E evidence because they require the future D3/D4 concretization.

A failure of these oracles is evidence of D2 or lower-layer nonconformance. If the only repair requires changing the mathematical estimator, ordering/tie rule, normalization, or scientific decision semantics, D2 must be reopened and descendant evidence applicability re-evaluated.

## 22. Reproducibility contract

A numerical reproduction requires, as applicable, the exact:

- source/frame numerical conventions and eligibility policies;
- correlated-sampling/block policy and protected-relation authority;
- exact `U_size`, scientific occurrence-key v4 semantics, `kappa` uniqueness, component tie-key semantics, and separately bound P1 split-exclusion ancestry/currentness identity;
- bound local-structure numerical-contract identity, exact reconciled specification blob, and neutral aggregation policy;
- source-coordinate schema plus canonical semantic coordinate-order key, fitted `d_U`/`d_P` states, medians, scales, and family dimensions;
- hard split policy, exact `J*`, retained-set removal trace, and final `P_train/M3` memberships;
- canonical scalar distance/reduction/tie semantics;
- `K`, condition median-nearest representatives, condition-local FPS state sufficient to reconstruct configured prefixes, proportional scheduler, and exact `pi_train` identity;
- every configured `T_N` prefix and hard-support policy;
- exact `M3` decision membership and full-`M3`-at-every-boundary policy;
- diagnostic randomization method/realization plus `m1/m2`, `pi_eval/M1/M2` identities separately from reducer evidence;
- common target-size training preparation, including fitted `E0`, weights/masks, and common model normalization;
- target objective and executable mathematical loss family;
- `mu_sel`, frozen common `mu_loss`, component-weighted `mu_eval`, candidate ladder, seed population, three fidelity boundaries, structural cardinality policy, and practical-equivalence policy;
- target-size optimizer-normalization reference policy and target batch geometry;
- exact boundary metrics/failures and reducer history;
- frozen selected memberships and role horizons;
- post-selection replay/monitor/checkpoint/fold method identity; and
- final-production/publication membership identity for production claims.

Changing only diagnostic `pi_eval` does not change target-size reducer identity. Changing `M3`, `pi_train`, metric/provider semantics, split semantics, full-`M3` evaluation policy, or training method does.

Runtime caches and scratch need not be preserved when they are exactly reconstructible and are not scientific evidence.

## 23. D2 -> D3 handoff

D3 must preserve at minimum:

1. one preparation-owned target-order provider publishing exact metric/split/order state once;
2. no empty-evidence/UID-order fallback when the accepted target-order method is required;
3. unique scientific occurrence keys and semantic component tie keys separated from P1 ancestry/currentness identity;
4. exact protected split membership and enough identity to reject stale descendants;
5. exact reference-result semantics for `J*`, completion admissibility, retained-set scoring, median-nearest representatives, FPS, and proportional scheduling even if implementation algorithms differ;
6. one immutable `pi_train` and exact `T_N` prefixes;
7. exact full `M3` evaluation at every automatic fidelity boundary;
8. diagnostic `pi_eval/M1/M2` state separated from reducer/model-selection identity;
9. fail-closed currentness and restart semantics for persisted target-order evidence; and
10. bounded CPU/RAM execution without a persistent dense frame-pair matrix or silent numerical approximation.

No module layout, cache format, process topology, solver library, or accelerator mechanism is promoted by this D2 method unless its identity is required to preserve the numerical semantics above.

## 24. Provenance and references

The accepted baseline was reconstructed against repository commit `9fd82b0ed40990d56716a393aa3f7db0a2ff44d0` and accepted on 2026-09-13. The target-order reconciliation represented here is a later proposed Gate-A amendment and requires its own independent D1/D2 review and human ratification.

1. I. Batatia, D. P. Kovacs, G. N. C. Simm, C. Ortner, and G. Csanyi, “MACE: Higher Order Equivariant Message Passing Neural Networks for Fast and Accurate Force Fields,” *Advances in Neural Information Processing Systems* **35**, 11423–11436 (2022), arXiv:2206.07697.
2. H. Flyvbjerg and H. G. Petersen, “Error Estimates on Averages of Correlated Data,” *Journal of Chemical Physics* **91**, 461–466 (1989). DOI: 10.1063/1.457480.
3. C. J. Geyer, “Practical Markov Chain Monte Carlo,” *Statistical Science* **7**, 473–483 (1992). DOI: 10.1214/ss/1177011137.
4. J. Racine, “Consistent Cross-Validatory Model-Selection for Dependent Data: hv-Block Cross-Validation,” *Journal of Econometrics* **99**, 39–61 (2000). DOI: 10.1016/S0304-4076(00)00030-0.
5. D. R. Roberts, V. Bahn, S. Ciuti, et al., “Cross-Validation Strategies for Data with Temporal, Spatial, Hierarchical, or Phylogenetic Structure,” *Ecography* **40**, 913–929 (2017). DOI: 10.1111/ecog.02881.
6. J. D. Morrow, J. L. A. Gardner, and V. L. Deringer, “How to Validate Machine-Learned Interatomic Potentials,” *Journal of Chemical Physics* **158**, 121501 (2023). DOI: 10.1063/5.0139611.
7. ACEsuit, MACE training and multihead fine-tuning documentation, version-qualified by the current mdstats adapter where execution semantics depend on it.
8. ACEsuit, `mace-torch` 0.3.16 source (`mace.cli.run_train` and `mace.tools.train`), used by current dependency-conformance qualification; the dependency version is a current D3/D4 realization, not a timeless numerical axiom.

Exact current configuration constants, schemas, source-probe markers, persistence records, and module paths remain with the current specifications/architecture and are not duplicated here as independently tunable D2 values.