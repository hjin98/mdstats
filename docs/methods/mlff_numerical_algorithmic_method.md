---
title: "mdstats MLFF Numerical Algorithmic Method"
artifact_level: "D2 numerical algorithm design"
status: "proposed Gate-A D2 candidate; accepted 2026-09-13 baseline remains current until independent review and human ratification"
reconstructed_against_commit: "9fd82b0ed40990d56716a393aa3f7db0a2ff44d0"
accepted_baseline_date: "2026-09-13"
gate_a_workplan: "MLFF-FPS-COVERAGE-METHOD-RECONCILIATION-1"
gate_a_revision: 5
candidate_materialized_date: "2026-09-14"
---

# mdstats MLFF Numerical Algorithmic Method

## 1. Purpose and authority status

This paper states the D2 numerical method that concretizes `mlff_scientific_method.md`. D1 defines scientific meaning; D2 owns estimator, ordering, split, normalization, solver, precision, stochastic, reduction, and numerical-equivalence semantics. D3/D4 own module placement, persistence, process control, dependency adaptation, caches, and runtime scheduling unless a lower mechanism is itself required to preserve D2 semantics.

**Authority status.** The 2026-09-13 reconstruction remains the accepted current D2 authority until the Gate-A target-order reconciliation passes independent review and human ratification. This branch materializes the complete proposed Gate-A D2 candidate directly in the canonical owner file so review can inspect one assembled method rather than amendment overlays.

Core D2 invariants are:

- canonical geometry/label/condition evidence preserves declared physical conventions;
- correlated trajectories are blocked with the shared deterministic autocorrelation primitive and protected relations are closed before incompatible allocations;
- pre-order target membership is constructed from one explicit material-neutral structural-support method; empty priority vectors and lexical UID order are not a valid baseline target-order method;
- exact `U_size -> P_train + M3` splitting preserves protected components, exact reserve cardinality, at least one retained training frame per eligible neutral condition, and globally minimum exact condition depletion before retained-set structural redundancy;
- `d_U` and `d_P` are distinct fitted target-order metrics with fixed source-coordinate schema and exact fit-domain identity;
- one medoid-anchored, condition-local exact farthest-point sampling (FPS) construction plus exact proportional condition scheduling owns `pi_train`; every candidate is exact `T_N=pi_train[:N]`;
- exact full `M3` target-force EVAL2 is the sole automatic model-selection population at every configured fidelity boundary;
- `pi_eval`, `M1`, and `M2` are diagnostic probability-sampling evidence only and have no ranking, elimination, qualification, tie-break, recommendation, horizon-selection, or freeze authority;
- target-size fitted training state is common across sizes/seeds and candidate projection never refits or renormalizes it;
- optimizer progress is normalized by realized target-update count, with the final partial target batch retained;
- each `(N, optimizer_seed)` is one continuous authenticated trajectory through configured fidelity boundaries;
- the reducer consumes complete ordered seed matrices and never averages only successful seeds;
- practical equivalence prefers smaller `N`, while a materially superior configured ceiling remains recommendable with explicit nonconvergence evidence;
- post-selection CV and final production are fresh lineages, not continuations of screening trajectories; and
- post-selection replay/checkpoint constraints remain method semantics distinct from the target-size screen.

## 2. Canonical source numerical conventions

### 2.1 Occurrence and numerical identity

Source occurrence, geometry, label payload, and labeled-configuration identities are constructed separately. Quantized fingerprints use explicit tolerances owned by current source/frame specifications. Geometry fingerprints include ordered species, periodic flags, cell, and wrapped fractional coordinates but exclude target labels so duplicate geometry remains detectable across occurrences and label payloads.

A numerically different quantization/tolerance policy changes identity behavior and requires explicit compatibility treatment; implementation may not silently substitute floating-point object equality or pathname identity.

### 2.2 Row-vector cells and deformation gradient

For ASE row-vector cells,

$$
\mathbf r_{\mathrm{row}}=\mathbf s_{\mathrm{row}}\mathbf H.
$$

With reference cell `H_0` and current cell `H_t`, strain reconstruction uses

$$
\mathbf F=\left(\mathbf H_0^{-1}\mathbf H_t\right)^T.
$$

Proper polar decomposition `F=RU` is computed by singular-value decomposition. Reflections, singular cells, or nonpositive stretch singular values are rejected. Derived strain measures include linearized, Green-Lagrange, and logarithmic strain plus volume ratio, rotation, principal logarithmic strain, hydrostatic/deviatoric measures, and engineering shear. Transpose convention, reference cell, and shear-factor semantics are numerical invariants.

### 2.3 Stress normalization

Source stress is normalized to canonical symmetric Cartesian Cauchy stress and internal units. Conversions preserve sign, Voigt ordering, and tensor-versus-engineering shear semantics. Virial-like quantities remain distinct unless an accepted owner defines conversion.

### 2.4 Eligibility numerical checks

Eligibility validates finite/nonsingular geometry, atom-count consistency, required label completeness, finite force/energy fields, stress symmetry/finite values when present, and active electronic-convergence/source-quality gates. Unusual but finite values remain data; no implicit typical-value filter is permitted.

## 3. Correlated-sampling primitives and neutral statistical units

### 3.1 Exact autocorrelation estimator

The neutral substrate reuses the shared `mdstats.sampling` autocorrelation method: unbiased FFT autocovariance, normalized `rho(k)`, and Geyer initial-positive-sequence truncation. Adjacent lag pairs are accumulated while

$$
\rho(2m-1)+\rho(2m)>0.
$$

An unpaired final positive lag may be retained. Integrated time is bounded by current policy with canonical floor `1/2` stored frame. Constant/insufficient sequences are explicit states rather than fabricated long correlation times.

The effective count is

$$
N_{\mathrm{eff}}=\min\left(N,\frac{N}{2\tau_{\mathrm{int}}}\right).
$$

No autocorrelation is computed across source gaps, continuation resets, or excluded intervals.

### 3.2 Complete-frame block length

For every configured observable and contiguous run, estimate `tau`; let `tau_max` be the maximum. The correlation-derived block target is

$$
L_{\mathrm{corr}}=\max\left(1,\lceil m\tau_{\max}\rceil\right),
$$

and resolved target

$$
L=\max(L_{\min},L_{\mathrm{corr}})
$$

unless an accepted override applies. A short override is an adequacy limitation. Balanced all-frame splitting retains every eligible frame; no remainder/tail is dropped.

### 3.3 Protected event merge and relation closure

Full-resolution event windows are constructed before ordinary thinning. Current split-exclusion relations include correlation-unit membership, exact geometry duplicates, protected-event membership, condition-scoped replica lineage, and condition-scoped structural-realization lineage. P1 projects these relations to the requested frame universe and computes transitive connected components; P2 consumes them without reconstructing relation authority from lower evidence.

### 3.4 Neutrality of the target-size substrate

The neutral condition key contains reduced formula, temperature condition, strain class, regime, and optional user labels. It does not contain retired `label_domain_id` fanout and constructs no pre-target-size CV plan.

## 4. Pre-order target-order evidence versus common training preparation

### 4.1 Pre-order target-order evidence

The baseline target-order method consumes one fixed candidate-independent evidence family:

- canonical neutral condition/provenance evidence;
- universal frame-level cell geometry;
- universal strain coordinates where scientifically defined; and
- material-neutral, element-resolved frame summaries of the accepted local-structure numerical contract.

Mass density, material/profile pair-rule coordinates, declared/profile atom groups or site classes, material-specific event descriptors, foundation-model predictions/descriptors, and label-derived residual/difficulty are not baseline membership coordinates.

Two fitted metrics are authorized:

- `d_U`, fitted on exact `U_size`, used only for pre-split retained-set structural redundancy;
- `d_P`, refitted after split on exact `P_train`, used for condition medoids, condition-local FPS, and training-prefix coverage diagnostics.

`M3` labels and candidate outcomes fit neither metric. Pre-order target-order evidence is preparation-owned scientific state and is published once with the immutable prepared generation. Downstream commands consume it rather than reconstruct it from live inputs.

There is no valid baseline state in which required target-order evidence is represented by an empty priority vector plus lexical UID order.

### 4.2 Post-order common candidate-training preparation

`TargetSizeCommonPreparation` is built after exact `P_train/M3` split and canonical target order exist, over exact `P_train`, and is shared by every candidate `N` and optimizer seed. It includes the common target atomic-reference fit, mean-one normalized configuration weights, property availability masks, foundation/head identity and target objective, common MACE normalization, and candidate architecture/method inputs that must remain common except for explicitly `N`-dependent execution quantities.

Candidate projection selects frozen common values for `T_N`; it does not renormalize weights, refit `E0`, or recompute common model normalization on each prefix.

## 5. Canonical target-order evidence and fitted metrics

### 5.1 Exact target-size population and protected components

`U_size` is the exact set of currently eligible, canonically labeled DEVELOPMENT frames admitted to the neutral target-size study. It must be large enough for configured `N_max` and exact reserve cardinality `m3`.

Project accepted P1 protected-relation authority onto `U_size` and compute transitive connected components. These are indivisible allocation units. Every eligible neutral condition represented in `U_size` is training-critical and must retain at least one `P_train` frame.

### 5.2 Scientific occurrence key and exact encoding

Target-order identity/tie semantics use:

```text
schema = "mdstats.target-order-scientific-occurrence-key.v3"
condition_id
source_identity_signature
source_frame_index
geometry_fingerprint
```

Canonical encoding:

- UTF-8 string `v`: `uint64_big_endian(len(utf8(v))) || utf8(v)`;
- `source_frame_index`: unsigned 64-bit big-endian with `0 <= source_frame_index <= 2^64-1`;
- concatenate fields in stated order after schema and SHA-256 the bytes.

The digest is `kappa`. Out-of-range frame index is identity failure.

Protected-component key is SHA-256 over the same length-prefixed encoding of canonical P1 protected-relation identity followed by member `kappa` values sorted lexicographically. Lexical `frame_uid` spelling is not a numerical score or tie-break.

### 5.3 Material-neutral feature substrate

Universal raw target-order coordinates are exactly:

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

Cell volume/length/angle form `cell_geometry`; hydrostatic/deviatoric/shear form `strain`. `mass_density_g_cm3`, energy, forces, pressure/stress, instantaneous-temperature labels, force statistics, and material/profile `RawFeaturePolicy.pair_rules` are excluded.

The local-structure source is bound to the accepted numerical contract:

```text
analysis_owner = mdstats.analysis.local_structure
LOCAL_STRUCTURE_POLICY_SCHEMA = mdstats.local-structure-feature-policy.v1
LOCAL_STRUCTURE_RESULT_SCHEMA = mdstats.local-structure-feature-result.v1
LOCAL_STRUCTURE_POLICY_VERSION = mdstats.analysis.local-structure.2026-07.v1
accepted specification = hjin98/mdstats@e8d04144f55c72d799ffcd3fe40c75e47078a66d:
  docs/specs/analysis/local_structure_features_spec.md
accepted specification blob = cc5be8d4f31d9168e09f2baa07711d5c37cf9b62
```

Frozen feature-value policy:

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

`maximum_dense_pair_work` is a resource guard, not a feature-value parameter. Semantic change to the bound local-structure contract changes target-order metric identity and reopens D2.

Target-order aggregation uses a neutral view:

```text
include_declared_atom_groups = false
include_element_groups = true
materialize_atomic_environments = false
aggregate_statistics = (mean,std,min,max,q10,q50,q90)
profile/material membership provider = forbidden
profile phase-geometry plan = forbidden
```

The element set is the sorted union of atomic numbers in exact `U_size` and fixes coordinate schema for both metrics. Frame-level element count/fraction coordinates are excluded.

Local semantic families are:

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
4. otherwise aggregate scalar binary64 values:
   - `mean`: left-to-right binary64 sum in increasing atom-index order, divide once by binary64 count;
   - `std`: two-pass population standard deviation (`ddof=0`) using canonical mean, then left-to-right sum of `(v-mean)^2`, divide once by count, then binary64 square root;
   - `min/max`: exact scalar extrema;
   - `q10/q50/q90`: Hyndman-Fan type-7 quantiles after ascending numerical sort.

Optimized execution may replace this reference form only when membership-relevant discrete results are equivalent.

### 5.5 Missing, constant, and active-coordinate semantics

Fit transform separately on each domain `D` (`U_size` for `d_U`, `P_train` for `d_P`). Let `O_j` be rows observing source coordinate `j`.

If `|O_j|=0`: numerical state `ALL_MISSING_INACTIVE`; no median/scale; numerical coordinate inactive; all-one missingness indicator inactive; neither counts in family dimension `d_f`.

Otherwise compute type-7 median and interquartile range (IQR) over observed values:

```text
m = Q_0.5
s_iqr = Q_0.75 - Q_0.25
s_dev = max |x_i-m|
```

Then:

```text
if s_iqr != 0.0 exactly in binary64:
    active; scale = s_iqr
elif s_dev != 0.0 exactly in binary64:
    active; scale = s_dev
else:
    CONSTANT_INACTIVE
```

There is no generic `sqrt(u)` or minimum-resolution threshold. An accepted upstream coordinate-specific resolution/error bound may be adopted only through a D2 metric revision.

For active numerical coordinates, missing rows are median-imputed and transform to zero. Binary missingness (`0` observed, `1` missing) is active iff both states occur, i.e. `0 < |O_j| < |D|`; it is not centered/scaled.

Inactive numerical/indicator coordinates do not count in `d_f`; an all-inactive semantic family contributes zero distance and does not dilute other families. Persist fit-domain identity, observation count, state, active flag, median/scale when defined, and missing-indicator state.

### 5.6 Equal-family normalization and scalar distance

Each active semantic family `f` is divided by `sqrt(d_f)` where `d_f` counts only active numerical coordinates and varying missingness indicators. Equal active-family mass is the explicit no-prior baseline and is subject to real-feature sensitivity/ablation evidence before acceptance.

Final metric is scalar binary64 Euclidean distance over canonical `(family_id, semantic_coordinate_name, coordinate_kind)` order. There is no PCA, whitening, learned weighting, random projection, foundation descriptor, or profile-specific membership block.

Squared distances use scalar multiply followed by left-to-right binary64 addition in canonical coordinate order. Fused contraction is not reference semantics. Exact binary64 score equality is the only numerical-score tie; ties use `kappa` or component key. Optimized paths must reproduce the same discrete decision or fall back to canonical scalar comparison.

### 5.7 Two fit domains

`d_U` is fit on exact `U_size` and used only by pre-split retained-set redundancy. `d_P` is refit on exact `P_train` and used for condition medoids, condition-local FPS, and training-prefix coverage diagnostics. Source coordinate schema is fixed by `U_size`; active states, medians, scales, and family dimensions are fit separately. `M3` labels/candidate outcomes fit neither metric.

## 6. Exact development split and canonical training order

### 6.1 Hard feasibility and globally minimum condition depletion

For protected component `g`, define size `w_g`, condition count `n(g,c)`, reserve indicator `z_g`, and `U_size` condition count `N_c`.

Hard feasibility:

```text
z_g in {0,1}
sum_g w_g*z_g = m3
for every c: sum_g n(g,c)*z_g <= N_c-1
|U_size|-m3 >= N_max
```

For feasible reserve `S`, define exact rational condition-depletion cost:

```text
A_g = sum_c n(g,c)/N_c
J_condition(S) = sum_{g in S} A_g
J* = min J_condition(S)
```

All terms/comparisons are exact rationals. No hard-feasible exact reserve means split infeasibility.

### 6.2 Exact reference solver for `J*` and completion admissibility

The D2 reference algorithm is an exact memoized dynamic program (DP) over canonical protected components. Its purpose is to make `J*` and completion admissibility reconstructible; D3/D4 may use another exact algorithm only when it is proven to return the same exact objective/predicate and downstream split decisions.

For any subproblem, sort available components by ascending `component_key`, yielding `g_0...g_{m-1}`. Let `r` be remaining reserve cardinality and `b_c` remaining removable capacity for condition `c`; store capacity vector in canonical condition-ID order.

Define `OPT(i,r,b)` as minimum additional exact rational depletion cost from suffix `i...m-1` selecting exactly `r` frames without exceeding condition capacities. `+infinity` means infeasible.

```text
OPT(i,0,b) = 0
OPT(m,r>0,b) = +infinity

exclude = OPT(i+1,r,b)
include = +infinity
if w_i <= r and n(g_i,c) <= b_c for every c:
    include = A_i + OPT(i+1,r-w_i,b-n_i)
OPT(i,r,b) = min_exact_rational(exclude,include)
```

Only exact pruning that cannot remove an optimum is permitted: negative cardinality, insufficient remaining component cardinality, explicit condition-capacity violation, and reuse of memoized identical state. No floating objective tolerance, heuristic infeasibility declaration, or approximate mixed-integer gap is reference semantics.

Global optimum is

```text
J* = OPT(0,m3,{c:N_c-1})
```

when finite.

At retained-set removal step `t`, let reserve-so-far be `S_t`. For candidate `g` not in `S_t`, form residual cardinality/capacities after tentatively adding `g`; solve the same exact recurrence over components outside `S_t union {g}`.

`g` is **completion-admissible** iff:

1. residual state is hard-feasible;
2. residual exact optimum is finite; and
3. `J_condition(S_t) + A_g + OPT_residual == J*` by exact rational equality.

This proves accepting `g` preserves at least one globally condition-optimal exact completion. It does not choose that completion directly.

Implementations may cache/share exact subproblems, use exact branch-and-bound or exact integer reformulations, or another exact solver, but may not change the predicate. A solver relying on floating feasibility/objective tolerances is not equivalent unless an independent exact verification step certifies final results.

Worst-case state growth is combinatorial in protected-component/condition-capacity structure; no simple `O(C*m3)` claim applies. Representative CPU/RAM feasibility is an acceptance condition. Resource exhaustion in representative supported regimes reopens D2; it is not permission for approximation.

### 6.3 Dynamic retained-set structural redundancy

Initialize reserve `S_0=empty` and retained population `R_0=U_size`. For every completion-admissible candidate component `g` at step `t`:

```text
q_x(g|R_t) = min_{y in R_t\g} d_U(x,y)^2
H_max(g|R_t) = max_{x in g} q_x
H_mean(g|R_t) = canonical_sum(q_x in ascending kappa order)/float64(len(g))
```

Choose lexicographically smallest `(H_max,H_mean,component_key)`, add that complete component to reserve, remove it from retained set, and recompute retained-set scores. Repeat until exactly `m3` reserve frames are selected.

Structural redundancy is a deterministic secondary criterion within the globally minimum condition-depletion feasible set; it is not a global covering-radius optimum claim.

### 6.4 Condition medoids and exact condition-local FPS

Fit `d_P` on final exact `P_train`. For every nonempty condition:

1. compute coordinate-wise type-7 median vector in fitted `d_P` coordinates;
2. choose frame minimizing canonical squared distance to that vector; exact ties use `kappa`;
3. initialize exact FPS with that medoid;
4. repeatedly select remaining frame maximizing canonical nearest-selected squared distance; exact ties use `kappa`.

FPS is required through `K=max(configured candidate_sizes)` for candidate membership. Optional persisted tail beyond `K` cannot alter any configured candidate.

### 6.5 Exact global condition scheduler and `pi_train`

Let `N_c` be final condition count, `N=|P_train|`, and `s_c(k)` emitted count after `k` global ranks.

Anchor phase emits one medoid per condition ordered by decreasing `N_c`, then canonical condition ID. Therefore configured `N_min` must be at least the represented condition count.

After anchors, choose nonexhausted condition maximizing exact integer deficit

```text
D_c(k+1) = (k+1)*N_c - s_c(k)*N
```

with canonical condition-ID tie-break, then emit that condition's next FPS frame. This defines one exact `pi_train`.

Every target candidate is exactly

```text
T_N = pi_train[:N]
```

with no per-`N` rerun, swap, repair, or rescue selector.

If a persisted tail after `K` is needed, continue the same condition scheduler and order within-condition remainder by `kappa`; no configured candidate may intersect the non-FPS tail.

### 6.6 Exact `M3` model-selection population at every automatic boundary

At every configured automatic fidelity boundary and active `(N,seed)`, evaluate exact same `M3` membership and compute

```text
RMSE_F = sqrt(sum_{x in M3} SSE_x / sum_{x in M3} 3*n_atoms(x))
```

Candidate comparison, practical equivalence, funnel elimination, configured-ceiling diagnosis, recommendation, and no-recommendation consume only this full-`M3` metric. The old changing `M1/M2/M3` decision ladder is retired.

### 6.7 Diagnostic `pi_eval`, `M1`, and `M2`

Diagnostic evaluation sampling uses one persisted Fisher-Yates permutation over distinct exact `M3` occurrences. Start from occurrences sorted by `kappa`. For `i=|M3|-1...1`:

1. `b=ceil(log2(i+1))`;
2. draw `b` independent unbiased random bits independently of scientific/candidate data;
3. interpret as integer `r`;
4. reject/redraw while `r>i`;
5. swap positions `i` and `r`.

Nested diagnostic prefixes `M1/M2` are simple random samples without replacement (SRSWOR) under this design. They may report finite-population sampling error, atom/component-mass discrepancy, condition/correlation discrepancy, and related diagnostics. They have no target-size decision authority.

Changing only diagnostic `pi_eval` invalidates its diagnostic descendants but not reducer identity when exact `M3`, model state, and per-frame predictions are unchanged.

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

`R_max(N)` must be nonincreasing over exact nested prefixes.

Split diagnostics report `J*`, per-step completion-admissible component set, chosen `(H_max,H_mean,component_key)`, condition retained/reserve counts, and final removed-to-retained maximum distance. Diagnostic `M1/M2` reports may include component-mass/condition discrepancy and SRSWOR uncertainty, labeled non-decision evidence.

## 7. Prefix qualification

For configured candidate size `N`:

```text
Q(N) = prefix_exists
       AND labels_usable(T_N)
       AND every explicitly accepted hard-support obligation holds
```

Hard-support selectors may consume only frozen pre-candidate evidence explicitly accepted for that obligation. Baseline condition retention is enforced at split construction; post-order hard obligations do not authorize reorder/repair.

FPS distances, retained-set redundancy scores, coverage metrics, event/environment summaries, correlation diagnostics, and diagnostic `M1/M2` evidence remain soft unless later D1/D2 explicitly promotes a hard obligation. Qualification never reorders, swaps, repairs, or expands `T_N`; candidate outcomes, CV/replay state, and runtime accidents cannot enter it.

## 8. Common atomic-reference and weight fitting

### 8.1 Count matrix and total-energy target

For exact fit membership `D`, construct element-count matrix `C` and total-energy target `y`. From-scratch fitting uses configured regularized least squares conceptually

$$
\widehat e=\arg\min_e\left[\|Ce-y\|_2^2+\lambda\|e-e_{\mathrm{prior}}\|_2^2\right],
$$

with prior term active only under its policy.

For foundation fine-tuning, with foundation predicted total energy `y_fnd` and elemental references `e_fnd`, fit residual correction

$$
r=y-y_{\mathrm{fnd}},
$$

$$
\widehat{\delta e}=\arg\min_{\delta e}\left[\|C\delta e-r\|_2^2+\lambda\|\delta e-\delta e_{\mathrm{prior}}\|_2^2\right],
$$

and `e_target=e_fnd+delta_e`. Element order is semantic atomic-number order.

### 8.2 Conditioning evidence

Record rank/singular values, null-space dimension where applicable, residual RMSE/MAE/max error, and rank-deficiency/transfer warnings. Rank deficiency is structural identifiability evidence, not a tolerance issue.

### 8.3 Configuration weights and masks

Common per-configuration weights are fit once over exact common membership and normalized to mean one. Candidate projection never recomputes the mean on `T_N`. Local property weights are availability masks derived from canonical label presence and are not copies of global objective ratios.

## 9. Objective and dependency-facing loss semantics

The numerical loss preserves global energy/force/stress coefficients, positive per-configuration weights, and local property availability masks. The accepted current MACE method realizes these with native weighted energy+forces+stress loss. A different loss family is not equivalent merely because coefficients can be manipulated to look similar.

Pinned MACE source/version guards are D3/D4 conformance mechanisms. D2 requires executed dependency behavior to realize authenticated objective, optimizer values, sample exposure, and batch geometry.

## 10. Target-size optimizer-progress normalization

With target batch size `B`, candidate `N` exposes

$$
U_N=\left\lceil\frac{N}{B}\right\rceil
$$

target optimizer updates per nominal epoch when final partial batch is retained. For reference size `N_ref`, learning rate `LR_ref`, EMA decay `beta_ref`:

$$
U_{\mathrm{ref}}=\left\lceil\frac{N_{\mathrm{ref}}}{B}\right\rceil,\qquad s_N=\frac{U_{\mathrm{ref}}}{U_N}.
$$

Use

$$
LR_N=LR_{\mathrm{ref}}s_N,
$$

and when EMA is enabled

$$
\beta_N=\beta_{\mathrm{ref}}^{s_N}.
$$

Thus `LR_N U_N = LR_ref U_ref` and `(beta_N)^{U_N}=beta_ref^{U_ref}`. Normalized values are computed once from full candidate geometry and remain fixed across later fidelity boundaries. This is first-order progress normalization, not optimizer-path equivalence.

Target batches retain the final partial batch (`drop_last=false`), expose every target UID once per epoch under accepted loader semantics, do not duplicate-pad targets, and do not truncate through distributed sampling unless exact equivalent exposure/update geometry is proven.

## 11. Continuous fidelity trajectories and restart

For active `(N,s)`, training is one continuous trajectory through configured boundaries. Exact predecessor state includes model, optimizer, EMA where enabled, learning-rate state, and required Python/NumPy/Torch random-number-generator lineage. Later fidelity restores authenticated predecessor rather than restarting from foundation. Recovery cannot change candidate membership, normalization, common preparation, seed, or boundary identity.

## 12. EVAL2 target-force estimator

At every automatic target-size fidelity boundary, exact checkpoint is evaluated on exact `M3`. If `K` Cartesian components are admitted,

$$
\mathrm{RMSE}_{F,\mathrm{eV}/\AA}=\sqrt{\frac1K\sum_{k=1}^{K}(\widehat F_k-F_k)^2},
$$

and stored metric is

$$
\mathrm{RMSE}_{F,\mathrm{meV}/\AA}=1000\,\mathrm{RMSE}_{F,\mathrm{eV}/\AA}.
$$

Equivalently `K=sum_x 3*n_atoms(x)` over exact `M3`. Device batching may partition inference only when exact membership/model/prediction semantics and accepted aggregate-reduction equivalence are preserved. Non-finite prediction or metric is typed numerical failure, not an invented infinite score. `M1/M2` are diagnostic samples, not alternative decision populations.

## 13. Pure target-size reducer

### 13.1 Ordered boundary matrix

At boundary `j`, with active candidates `A_j` and ordered seeds `S`, expected outcomes are size-major then seed-minor over `A_j x S`. Every outcome binds exact experiment definition, execution context, boundary epoch, and exact `M3` identity. Missing, duplicate, reordered, foreign, or lineage-incompatible evidence yields insufficient comparison rather than silent rearrangement.

### 13.2 Complete-seed score

A size receives finite score only when all configured seeds have valid finite target metrics:

$$
\bar E_N=\frac1{|S|}\sum_{s\in S}E_{N,s}.
$$

Any authenticated numerical failure removes that candidate from successful comparison; means are never taken over successful subsets only.

### 13.3 Practical-equivalence order

Given successful scores and tolerance `epsilon`, repeatedly find `E_min`, define

$$
\mathcal E=\{N:E_N\le E_{\min}+\epsilon\},
$$

choose smallest `N` in `E`, remove it, and repeat. Any floating comparison guard beyond `epsilon` is numerical implementation detail, not the scientific tolerance.

### 13.4 Funnel

The structural funnel is

$$
q\rightarrow\min(q,4)\rightarrow2\rightarrow1.
$$

At first boundary successful candidates must be at least `min(|A_1|,4)`; second and terminal comparisons require two. Otherwise reducer terminates with insufficient comparison.

The three configured positions carry increasing training-fidelity boundaries only. Every position evaluates the same exact `M3` membership. Diagnostic `M1/M2` sizes are not funnel policy values and cannot alter survivor decisions.

### 13.5 Configured-ceiling rule

If configured `N_max` is a successful terminal finalist and

$$
E_{N_{\max}}+\epsilon<E_N
$$

for every other successful finalist, `N_max` is materially superior, recommended, and carries explicit nonconvergence-at-configured-ceiling diagnostic. Otherwise first practical-equivalence-ranked finalist is recommended. No extrapolated learning curve or rescue size is invented.

## 14. Post-selection fold construction and fitting

After operator collection is frozen, each admitted `T_N` is validated separately. For each required fold: partition exact frozen `T_N` preserving protected relations/purge constraints; derive checkpoint monitor from training-eligible evidence disjoint from held-out evaluation; fit all fold-local transforms/atomic references/training inputs from fold training domain only; initialize fresh model/optimizer lineage; train selected CV horizon; choose admissible representative using authorized monitor/integrity/replay-retention evidence only; then evaluate once on held-out fold. Every required fold/seed must be represented.

## 15. Checkpoint selection as constrained optimization

Checkpoint owner filters through mandatory constraints before ranking. If admissible set is empty, there is no admissible checkpoint; do not fall back to best target error among inadmissible checkpoints. Held-out fold data are unavailable to checkpoint decision.

## 16. Replay and post-selection exposure

Target-size execution has zero replay training samples. Post-selection replay supports true-reference/DFT replay as canonical default when available and foundation pseudo-label replay only under explicit opt-in bound to frozen foundation/head. Pseudo-label path still requires separate true-reference replay-monitor lineage under current policy.

Replay membership, label mode, monitor membership, head identity, exposure policy, and realized counts belong to post-selection method identity. Target examples may not be silently duplicated to satisfy target/replay ratio heuristics; effective target membership/count must equal authenticated target exposure.

## 17. Fresh final production and publication selection

Final production starts a new lineage on complete exact `T_N`; screen/CV checkpoints are never warm-start parents. For each final seed, freeze representative using accepted checkpoint/admissibility owner and exact target evaluation evidence. Final publication membership is selected before downstream qualification. Qualification/physical/locked evidence never enters cross-seed publication ranking.

## 18. Current dependency realization boundary

The accepted adapter is qualified against `mace-torch==0.3.16`. Behaviors in that dependency that would violate D2 if uncontrolled include forced `UniversalLoss` under multihead fine-tuning, LR/EMA mutation, ratio-driven target duplication, and target-batch truncation. Current source guards/patch mechanics are D3/D4 evidence, not timeless D2 requirements. Future dependency versions may replace them after proving the same loss, optimizer, exposure, and batch semantics or reopening D2.

## 19. Numerical failure, conditioning, precision, and uncertainty

### 19.1 Failure is typed evidence

Non-finite model/optimizer state and non-finite evaluation evidence carry typed failure identities. Missing/contradictory boundary evidence yields insufficient comparison. Neither is silently converted into arbitrary finite/infinite ranking values.

### 19.2 Atomic-reference conditioning

Rank/null-space evidence characterizes identifiability, not merely solver accuracy. Null directions persist at infinite arithmetic precision unless additional independent compositional information or accepted prior changes the mathematical problem.

### 19.3 Optimizer stochasticity

Optimizer seeds are explicit stochastic replicates. Pairing controls one comparative variation source but does not eliminate minibatch, finite-horizon, or model-training uncertainty. Reproducibility preserves accepted seed/method lineage and numerical compatibility contract, not unsupported bitwise identity across hardware/library regimes.

### 19.4 Precision and backend

Learned-model dtype, critical-precision policy, acceleration/backend behavior, and other trajectory-changing settings belong to method/execution identity. Worker count, queue order, cache path, device-batch width, and file-backed representation are execution-only only when accepted numerical results are preserved.

## 20. Complexity and scaling

Ignoring neural-network training cost:

- autocorrelation is FFT-dominated per observable/run plus linear block construction;
- relation closure is near-linear in frame/relation edges with union-find-style closure;
- local-structure/raw descriptor preparation is bounded by the accepted analysis provider and must not materialize persistent dense `N x N` frame-distance state;
- fitted target-order feature storage is `O(Nd)` for active coordinate dimension `d`;
- exact reference `J*`/completion solver is sparse memoized DP over component index, remaining reserve cardinality, and condition residual capacities; worst case is combinatorial and no simple `O(C*m3)` bound is claimed;
- retained-set structural scoring may stream/chunk candidate-to-retained distances while preserving canonical scalar decisions; persistent dense pairwise state is forbidden;
- condition-local FPS maintains `O(N)` nearest-selected state and is required only through `K=max(candidate_sizes)`;
- proportional condition scheduling uses exact integer deficits with negligible state;
- exact `M3` EVAL2 is linear in evaluated force components at each boundary and may chunk inference;
- diagnostic Fisher-Yates is `O(|M3|)` time/state;
- reducer is `O(boundaries*candidates*seeds)` with small state relative to training.

Representative supported CPU/RAM feasibility of exact split/completion is a Gate-A acceptance condition. Resource exhaustion on representative supported input reopens D2; D4 may not obtain a pass by approximating `J*`, weakening condition retention, changing reserve cardinality, or skipping completion-admissibility checks.

## 21. Verification and falsification oracles

D2 should be challenged through independent invariants rather than successful end-to-end execution alone. Applicable oracles include:

- cell/strain/stress round trips under declared conventions;
- autocorrelation parity and complete-frame block coverage;
- re-derivation of P1 protected relations and stale-descendant rejection;
- neutral target-size condition key free of compatibility-domain/CV fanout;
- protected-component projection and hard split feasibility;
- exhaustive subset enumeration on bounded fixtures to verify `J*` and completion admissibility, including infeasible and multiple-optimum cases;
- mutual-redundancy counterexample proving retained-set rescoring prevents stale reciprocal redundancy;
- scientific occurrence-key byte encoding and frame-index bounds;
- provider-contract/coordinate-family lineage against immutable accepted local-structure specification;
- all-missing, constant, partial-missing, rare-outlier, and finite-small-variation transform cases;
- representative real-feature equal-family sensitivity/ablation and precision-sensitivity evidence before promotion;
- input-enumeration, non-semantic UID relabeling, and feature-column permutation metamorphics where invariance preconditions hold;
- each condition medoid and condition-local FPS order against independently simple scalar reference fixtures;
- proportional condition scheduling against exact integer-deficit references;
- `pi_train` complete parent permutation and every configured `T_N` exact prefix;
- independent full-`P_train` coverage rescoring with nonincreasing `R_max` over nested prefixes;
- exact full-`M3` reducer input at every automatic boundary and invariance of recommendation to diagnostic `pi_eval` when exact `M3` predictions are fixed;
- Fisher-Yates diagnostic sampling separately from model-selection decisions;
- candidate projection without refit/renormalization of common weights, `E0`, or model normalization;
- realized target batches equal `ceil(N/B)` without target duplication;
- fixed normalized LR/EMA identity across surviving fidelity boundaries;
- reducer-history replay through pure transition semantics with same result;
- incomplete/reordered matrices fail rather than being silently rearranged/subset-averaged;
- held-out CV labels cannot reach fold fitting/checkpoint selection;
- no-admissible-checkpoint outcome cannot fall back to inadmissible checkpoint;
- replay-only changes invalidate post-selection descendants but not frozen target-size evidence;
- final-product member selection completes before downstream qualification; and
- representative CPU/RAM feasibility of descriptor preparation, exact `J*`/completion solving, retained-set scoring, and K-bounded FPS.

Required Gate-A evidence that is unavailable, stale, non-independent where independence is required, or demonstrates infeasibility blocks acceptance. Production optimized-versus-reference equivalence, prepared-generation persistence/currentness, old-generation rejection, and real `prepare -> publish -> consume` integration remain downstream D3/D4 Gates B-E evidence.

## 22. Reproducibility contract

A numerical reproduction requires, as applicable, exact:

- source/frame numerical conventions and eligibility policies;
- correlated-sampling/block policy and protected-relation authority;
- exact `U_size` and scientific occurrence-key/component-key semantics;
- bound local-structure numerical-contract identity and neutral aggregation policy;
- source-coordinate schema plus fitted `d_U`/`d_P` states, medians, scales, and family dimensions;
- hard split policy, exact `J*`, retained-set removal trace, and final `P_train/M3` memberships;
- canonical scalar distance/reduction/tie semantics;
- `K`, condition medoids, condition-local FPS state sufficient to reconstruct configured prefixes, proportional scheduler, and exact `pi_train` identity;
- every configured `T_N` prefix and hard-support policy;
- exact `M3` decision membership and full-`M3`-at-every-boundary policy;
- diagnostic randomization method/realization plus `pi_eval/M1/M2` identities separately from reducer evidence;
- common target-size training preparation including fitted `E0`, weights/masks, and common model normalization;
- target objective/loss family;
- `mu_sel`, frozen common `mu_loss`, component-weighted `mu_eval`, candidate ladder, optimizer-seed population, fidelity schedule, optimizer-normalization policy, target batch geometry, and practical-equivalence policy;
- exact boundary metrics/failures and reducer history;
- frozen selected memberships/horizons;
- post-selection replay/monitor/checkpoint/fold method identity; and
- final-production/publication identity for production claims.

Changing only diagnostic `pi_eval` does not change target-size reducer identity. Changing `M3`, `pi_train`, metric/provider semantics, split semantics, full-`M3` evaluation policy, or training method does.

Runtime caches/scratch need not be preserved when exactly reconstructible and not scientific evidence.

## 23. D2 -> D3 handoff

D3 must preserve at minimum:

1. one preparation-owned target-order provider publishing exact metric/split/order state once;
2. no empty-evidence/UID-order fallback when accepted target-order method is required;
3. exact protected split membership and enough identity to reject stale descendants;
4. exact reference-result semantics for `J*`, completion admissibility, retained-set scoring, medoids, FPS, and proportional scheduling even if implementation algorithms differ;
5. one immutable `pi_train` and exact `T_N` prefixes;
6. exact full `M3` evaluation at every automatic fidelity boundary;
7. diagnostic `pi_eval/M1/M2` state separated from reducer/model-selection identity;
8. fail-closed currentness/restart semantics for persisted target-order evidence; and
9. bounded CPU/RAM execution without persistent dense frame-pair matrices or silent numerical approximation.

No module layout, cache format, process topology, solver library, or accelerator mechanism is promoted unless its identity is necessary to preserve these numerical semantics.

## 24. Provenance and references

The accepted baseline was reconstructed against repository commit `9fd82b0ed40990d56716a393aa3f7db0a2ff44d0` and accepted 2026-09-13. This target-order reconciliation is a later proposed Gate-A amendment and requires its own independent D1/D2 review and human ratification.

1. I. Batatia, D. P. Kovacs, G. N. C. Simm, C. Ortner, and G. Csanyi, “MACE: Higher Order Equivariant Message Passing Neural Networks for Fast and Accurate Force Fields,” *Advances in Neural Information Processing Systems* **35**, 11423–11436 (2022), arXiv:2206.07697.
2. H. Flyvbjerg and H. G. Petersen, “Error Estimates on Averages of Correlated Data,” *Journal of Chemical Physics* **91**, 461–466 (1989). DOI: 10.1063/1.457480.
3. C. J. Geyer, “Practical Markov Chain Monte Carlo,” *Statistical Science* **7**, 473–483 (1992). DOI: 10.1214/ss/1177011137.
4. J. Racine, “Consistent Cross-Validatory Model-Selection for Dependent Data: hv-Block Cross-Validation,” *Journal of Econometrics* **99**, 39–61 (2000). DOI: 10.1016/S0304-4076(00)00030-0.
5. D. R. Roberts, V. Bahn, S. Ciuti, et al., “Cross-Validation Strategies for Data with Temporal, Spatial, Hierarchical, or Phylogenetic Structure,” *Ecography* **40**, 913–929 (2017). DOI: 10.1111/ecog.02881.
6. J. D. Morrow, J. L. A. Gardner, and V. L. Deringer, “How to Validate Machine-Learned Interatomic Potentials,” *Journal of Chemical Physics* **158**, 121501 (2023). DOI: 10.1063/5.0139611.
7. ACEsuit, MACE training and multihead fine-tuning documentation, version-qualified by current adapter where execution semantics depend on it.
8. ACEsuit, `mace-torch` 0.3.16 source (`mace.cli.run_train` and `mace.tools.train`), used by current dependency-conformance qualification; dependency version is D3/D4 realization, not timeless D2 axiom.