---
kind: proposed-D2-authority-overlay
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
gate: R1
protocol_version: 6.3.0
lifecycle: PROPOSED_NOT_ACCEPTED
owner_after_ratification: docs/methods/mlff_numerical_algorithmic_method.md
basis_commit: e72090e21cec5311ce87745b03603f8783cd15a7
---

# R1 proposed D2 amendment — exact multi-view `pi_train` / MVSEL2 numerical method

## 1. Authority and scope

This file is the exact proposed D2 overlay corresponding to `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_D1_METHOD_AMENDMENT.md`. It is not accepted-current D2 authority until independent D1/D2 review passes and the stakeholder ratifies the pair.

The change replaces only the current weak target-training-order construction/qualification method. The accepted `U_size -> P_train + M3` split algorithm, independent `pi_eval/M1/M2/M3`, P3 training/evaluation/reducer algorithm, post-selection CV, replay and final-production numerical methods remain unchanged except for consuming different authenticated `T_N` memberships.

## 2. Replace current Section 4.1 pre-order evidence semantics

Use:

### 4.1 Selector evidence is fitted on exact `P_train`

The restored target-order method operates on exactly one ordered candidate domain

```text
P_train = (u_0, ..., u_{n-1})
```

with a deterministic canonical frame order used only to index scientific arrays. Candidate training outcomes do not exist when the selector evidence is built.

Every selector transform/reference family is fitted or projected on exact `P_train`. Partition-independent raw descriptors may be computed earlier, but any statistics, quantiles, scales, local radii, residual vectors, family weights, event/profile support incidence or other fitted selector state are rebound to `P_train` before order construction.

The following are excluded from selector fitting: `M3/M1/M2`, post-selection monitor/held-out/CV, calibration/locked/challenge evidence, target-size candidate outcomes, reducer evidence and downstream qualification.

Foundation residual families are present only when the current target-size protocol uses a frozen authenticated foundation checkpoint. Profile families are present only when an accepted active profile provider exposes selection-stage evidence.

## 3. Add a target-coverage numerical-method section before training-order construction

### 5A. Multi-view target-coverage reference

#### 5A.1 Family witness weights

For required family `m`, let its ordered participating witnesses be `W_m`. Let `g(w)` be the P1 correlation-unit identity of witness `w`, let

```text
G_m = {g(w) : w in W_m},
n_{m,g} = |{w in W_m : g(w)=g}|.
```

The family reference weight is

$$
\omega_m(w)=\frac{1}{|G_m|\,n_{m,g(w)}}.
$$

The implementation normalizes the resulting FP64 vector once by its FP64 sum and stores the canonical normalized values. Thus every represented correlation unit has equal family mass and frames within one unit divide that mass equally.

If no unit is represented, the family is invalid.

#### 5A.2 Weighted quantiles and robust scale

For values `v_i` with nonnegative normalized weights `omega_i`, weighted quantile `Q(q)` is the first value in stable ascending `v_i` order whose cumulative weight is at least `q`.

For feature column `j`, define

```text
s_j = Q_j(0.75)-Q_j(0.25)                         if > 1e-12
      Q_j(0.99)-Q_j(0.01)                         else if > 1e-12
      max(std_population(x_j), 1.0)                otherwise
s_j = max(s_j, 1e-12).
```

All statistics are binary64. Stable sorting is required where equal values occur.

#### 5A.3 Family distance

For a `d`-column family with scales `s_j`, define

$$
d_m(a,b)=\sqrt{\frac{1}{d}\sum_{j=1}^{d}
\left(\frac{x_{a,j}-x_{b,j}}{s_j}\right)^2}.
$$

Missing/inapplicable rows do not enter that family. A family requires at least two reference elements. Constant optional scalar families are omitted rather than creating zero-information dimensions.

#### 5A.4 Local reference radius

Let `beta=1/128`. For witness `w`, remove self mass, renormalize the remaining family weights by `1-omega_m(w)`, sort other witnesses by `d_m(w,.)`, and choose the smallest neighbor distance at which cumulative renormalized mass is at least `beta` using the recovered binary64 comparison `cumulative >= beta - 1e-15`.

The resulting value is `r_m(w)`.

A degenerate family for which the requested leave-one-out mass cannot be reached fails preparation.

#### 5A.5 Exact neighborhood predicate

The final recovered executable method freezes neighborhood membership as

$$
A_m(w,c)=1
\quad\Longleftrightarrow\quad
 d_m(w,c)\le r_m(w)+10^{-12}\max(1,r_m(w)).
$$

This `1e-12` metric tolerance is D2 authority. Worker count, k-d-tree block size, sparse representation and native/vector backend are execution-only when they reproduce exactly the same adjacency.

Every witness must retain at least one exact candidate support edge under this relation.

#### 5A.6 Covered reference mass

For selected candidate set `S`, define multiplicity

$$
n_m(w;S)=\sum_{c\in S} A_m(w,c)
$$

and family covered mass

$$
C_m(S)=\sum_{w\in W_m}\omega_m(w)\,\mathbf 1[n_m(w;S)>0].
$$

The baseline required-family threshold is exactly

```text
coverage_threshold = 0.95.
```

A family passes mass coverage iff

```text
C_m(S) + 1e-12 >= 0.95.
```

No family/profile-specific threshold override is part of this reconstructed baseline. Adding one is a future D1/D2 change.

#### 5A.7 Extent channels

For an extent-bearing feature channel `j`, define weighted reference limits

```text
L_j = Q_j(0.01)
U_j = Q_j(0.99).
```

The selected representatives pass that channel iff

```text
min_selected x_j <= L_j + 1e-12
and
max_selected x_j >= U_j - 1e-12.
```

Each side is also represented as one required hard obligation with minimum count 1 so MVSEL2/REPAIR2 can prioritize satisfying it incrementally.

### 5B. Required family catalog

The current restored baseline contains the following required families whenever their stated applicability conditions hold.

#### 5B.1 Universal structural families

From the accepted universal structural feature contract, group/species-resolved DATA6 frame descriptors are partitioned by semantic family:

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

The exact feature columns are those whose accepted structural feature names map to the corresponding semantic family. `pair_distance`, `coordination`, and `local_density` are extent-bearing; the other structural families use hard mass coverage without a separate extent predicate.

#### 5B.2 Profile selection families

For every active accepted profile-selection provider, each valid nonconstant scalar selection feature forms one required one-dimensional family over frames for which the provider declares that feature valid. It is extent-bearing.

Every environment-class label declared by that provider over `P_train` contributes one required profile-environment stratum obligation.

No profile provider is loaded merely because the selector exists.

#### 5B.3 Raw pair-geometry families

For each applicable accepted pair rule, build:

1. `bond_length_distribution` with
   `minimum_pair_distance_angstrom`,
   `mean_nearest_neighbor_distance_angstrom`,
   `maximum_nearest_neighbor_distance_angstrom`;
2. `coordination_distribution` with
   `coordination_mean`, `coordination_maximum`.

Both are required and extent-bearing.

#### 5B.4 Target-development response families

From exact `P_train` target-development raw evidence, build:

1. required `force_distribution` containing
   `force_component_rms_ev_per_angstrom`,
   `force_norm_mean_ev_per_angstrom`,
   `force_norm_max_ev_per_angstrom`,
   and every canonical available force-norm quantile channel;
2. one required scalar family for each defined, nonconstant channel among
   `energy_per_atom_ev`,
   `instantaneous_temperature_kelvin`,
   `hydrostatic_strain`,
   `deviatoric_strain_norm`,
   `pressure_ev_per_angstrom3`,
   `stress_deviatoric_norm_ev_per_angstrom3`.

All target-development response families are extent-bearing.

These are membership-design inputs from `P_train`, not held-out evaluation statistics.

#### 5B.5 Foundation residual families

When and only when the current target-size protocol uses a frozen authenticated foundation model, construct on exact `P_train`:

- required global family with
  `absolute_energy_error_per_atom_ev`,
  `force_component_rmse_ev_per_angstrom`,
  `force_vector_error_mean_ev_per_angstrom`,
  `force_vector_error_max_ev_per_angstrom`;
- for every represented atomic species, a required family with
  `component_rmse_ev_per_angstrom`,
  `vector_error_mean_ev_per_angstrom`,
  `vector_error_max_ev_per_angstrom`.

All are extent-bearing. Their source foundation checkpoint/head/provider identity is part of selector-evidence identity.

The old final-development/label-domain residual catalog is not current authority; current reconstruction/projection must cover exact `P_train` only.

### 5C. Canonical hard obligations

One indexed hard-obligation set is built over exact `P_train`.

Automatic obligations are:

1. each current P2 condition represented in `P_train`, minimum 1;
2. each recognized structural-event type represented in `P_train`, minimum 1;
3. each active profile environment class, minimum 1;
4. each extent-family lower channel side, minimum 1;
5. each extent-family upper channel side, minimum 1;
6. each P1 correlation interval/unit represented in `P_train`, minimum 1.

Current explicit `ResolvedTargetSizePolicy.hard_support_obligations` are projected through the current P2 condition-attribute authority and appended with their declared positive minimum counts.

Obligation IDs are namespaced, canonical and unique. Reusing one ID for contradictory incidence/minimum semantics is an input error. Distinct semantic obligations remain distinct even if their candidate sets overlap.

For selected state `S`, obligation count is the number of selected candidates in its exact incidence set. Required obligation `o` is satisfied iff `count_o(S) >= k_o`.

## 4. Replace current Section 6.1 with exact MVSEL2 semantics

### 6.1 One exact MVSEL2 master order

Let every candidate index, family, witness, obligation, correlation unit and final UID tie order be canonical and identity-bound. All scientific decision arithmetic below is binary64 unless the quantity is explicitly integer.

State contains:

- selected/available candidate membership and ordered prefix;
- each family witness multiplicity `n_m(w)` and covered mass `C_m`;
- each hard-obligation count;
- each correlation-unit selected count;
- reconstructible representative utility.

Persistent heap/lazy marginal caches are not scientific state.

#### 6.1.1 Candidate primitives

For available candidate `c`, define:

**hard gain**

$$
H(c)=\#\{o: o\text{ required and unsatisfied and }c\in A_o\};
$$

**family new-coverage gain**

$$
G_m(c)=\sum_{w:A_m(w,c)=1,\ n_m(w)=0}\omega_m(w);
$$

**total new-coverage gain**

$$
G(c)=\sum_m G_m(c);
$$

**representative gain**

$$
R(c)=\sum_m\sum_{w:A_m(w,c)=1}
\frac{\omega_m(w)}{n_m(w)+1};
$$

**sparse diversity**

$$
D(c)=\operatorname{mean}_{m:A_m(c)\ne\varnothing}
\left[\operatorname{mean}_{w:A_m(w,c)=1}\frac{1}{n_m(w)+1}\right],
$$

with `D(c)=0` if all family rows are empty.

#### 6.1.2 Phase A — hard coverage/support progression

Phase A remains active while any required obligation is unsatisfied or any required family has coverage below the hard threshold within selector tolerance.

Let `epsilon = 1e-14`. Filter the available candidates lexicographically:

1. if any required obligation is unsatisfied, retain candidates with maximal integer `H(c)`;
2. choose the first family in canonical family order minimizing `C_m/0.95` among families tied within `epsilon` at the minimum;
3. retain candidates with `G_m(c) >= best_Gm - epsilon` for that bottleneck family;
4. retain candidates with `G(c) >= best_G - epsilon`;
5. retain candidates whose own correlation unit currently has the minimum selected count among contenders;
6. retain candidates with `R(c) >= best_R - epsilon`;
7. retain candidates with `D(c) >= best_D - epsilon`;
8. choose minimum stable frame UID.

The selected candidate updates all multiplicities, coverage masses, obligation counts and its correlation-unit count exactly once.

#### 6.1.3 Phase B — representative progression

When every hard obligation is satisfied and every required family reaches the threshold, filter available candidates by:

1. maximum representative gain within `epsilon`;
2. minimum selected count of the candidate's correlation unit;
3. maximum sparse diversity within `epsilon`;
4. minimum stable UID.

Continue until the required ordering boundary. For the current product that boundary is eventual `|P_train|`, subject to configured-shell REPAIR2 described below.

#### 6.1.4 Full-forward oracle and optimized equivalence

The scalar/full-forward algorithm above is the exact numerical oracle. Lazy frontiers, locality kernels, native/OpenMP row scoring, batching and parallel candidate-row execution are permitted only when they reproduce the same rank history under the same canonical inputs and tolerance semantics.

No execution completion order participates in scientific tie-breaking.

## 5. Replace current Section 6.2 training-membership construction

### 6.2 Configured prefixes, REPAIR2, and full-order continuation

The current configured target-size ladder is the strictly increasing `ResolvedTargetSizePolicy.candidate_sizes`; historical fixed-eight membership is not authority.

Run MVSEL2 to supply the necessary ordered candidates for configured shells. Then process configured sizes `N_1 < ... < N_K` in order with `N_0=0`.

For shell `i`, REPAIR2 may remove only ranks

```text
[N_{i-1}, N_i).
```

Ranks below `N_{i-1}` are immutable.

### 6.2.1 REPAIR2 removal eligibility and shortlist

For selected candidate `c`, define unique covered mass as total family reference mass for witnesses with current multiplicity exactly one that are covered by `c`. Candidate is removable only if:

```text
unique_mass(c) <= 1e-14
```

and removing it would not increase the deficit of any required hard obligation.

For each active repair state, order removable candidates by:

1. representative loss ascending;
2. selected count of removed candidate's correlation unit descending;
3. removed UID ascending.

Retain at most 64 removals.

### 6.2.2 REPAIR2 replacement frontier

For each contemplated removal, evaluate replacements against the immutable pre-swap state. The replacement frontier preserves the Phase-A priority:

1. maximal hard gain if hard obligations remain pending;
2. first canonical bottleneck family;
3. maximal bottleneck-family new coverage;
4. maximal total new coverage;
5. minimum hypothetical correlation-unit count after removal;
6. maximal representative gain after removal;
7. maximal sparse diversity after removal;
8. minimum replacement UID.

### 6.2.3 REPAIR2 global objective

For selected state `S`, define

```text
J(S) = (
  hard_deficit(S),
  min_m C_m(S),
  sum_m C_m(S),
  U_rep(S),
  -sum_g b_g(S)^2
)
```

where hard deficit is total missing required-obligation count and

$$
U_{rep}(S)=\sum_m\sum_w \omega_m(w) H_{n_m(w;S)}
$$

with `H_k=sum_{j=1}^k 1/j` and `H_0=0`.

Comparison minimizes the first component, then maximizes components 2-4 using `1e-14` floating tolerance, then maximizes the exact integer balance component.

A proposal is admissible only if it strictly improves `J` and every family obeys

```text
C_m(after) + 1e-14 >= C_m(before).
```

When two admissible proposals are objective-equivalent, choose by:

```text
(representative_loss,
 removed_rank,
 removed_UID,
 replacement_UID)
```

ascending.

### 6.2.4 REPAIR2 limits and rank inheritance

Per shell:

```text
max_passes = 2
max_accepted_swaps = 32
removal_shortlist_limit = 64.
```

The accepted replacement inherits the removed rank. If that replacement already occurs at a future rank, move the removed candidate to that future rank. This preserves one permutation rather than duplicating/dropping candidates.

A repaired shell cannot invalidate an earlier configured prefix.

### 6.2.5 Post-repair continuation to complete `P_train`

After the final configured shell is repaired, discard/reconstruct any selector state whose selected prefix no longer authenticates the repaired order. Rebuild exact MVSEL2 state from the final repaired prefix and primitive family/obligation/correlation evidence, then continue the same Phase-A/Phase-B logic until every frame in `P_train` is ordered.

No additional REPAIR2 shell is created beyond the configured ladder. No UID-only, condition-round-robin or other fallback may complete the suffix.

The result is the sole current complete `TargetTrainingOrder`.

## 6. Replace current candidate qualification section

### 7.1 Independent MVQUAL membership qualification

For each configured `N`, let `T_N` be the exact repaired nested prefix.

MVQUAL independently evaluates `T_N` from the immutable TargetCoverageReference plus canonical obligation definitions. It may use MVIDX only as an exact secondary sparse cross-check; selector/repair internal counters are not its oracle.

Direct family scoring recomputes:

- covered reference mass under the exact family metric/local radii;
- lower/upper extent predicates;
- required stratum support.

Canonical obligation scoring recomputes every required automatic/current explicit obligation count.

MVIDX-covered family mass must agree with direct TargetCoverage mass with

```text
rtol = 0
atol = 5e-12.
```

Disagreement is an invariant error.

A configured candidate is qualified iff:

```text
prefix_exists
AND labels_training_usable
AND every required family mass passes
AND every required extent passes
AND every required canonical hard obligation passes.
```

The current P2 qualification record is the sole public/current projection of this evidence; no second public MVQUAL decision owner is introduced.

### 7.2 Qualification monotonicity and target-size funnel

Under fixed nested prefixes and fixed primitive evidence, mass coverage, extents and minimum-count obligations are positive predicates. Therefore configured hard qualification must have form

```text
FAIL* -> PASS*
```

across increasing materializable configured sizes. PASS->FAIL is a numerical/lineage invariant failure and fails closed.

At least three qualified configured candidates remain required by the current target-size funnel. MVQUAL does not create rescue sizes, relax 0.95, relax extents or reduce obligation minima.

Manual target-size selection of an unqualified configured size fails before training/CV.

Among qualified candidates, MVQUAL metrics/telemetry do not rank or tie-break size. Current P3 target-force reducer semantics remain unchanged.

## 7. FEAS1 current rebinding

Add to the D2 preparation section:

FEAS1 executes before selection as a fail-closed feasibility/fragility gate over exact `P_train` and the same neighborhood/obligation authority.

It must establish:

- candidate/reference domain and exact self-support consistency;
- hard-obligation support capacity;
- conservative lower-bound evidence for hard family/obligation cardinality.

Historical support-degree and own-correlation-unit-exclusion fragility measures are diagnostics, not selection scores.

The historical fixed `maximum_candidate_size=16384` is replaced by current configured `N_max=max(candidate_sizes)`. A proven lower bound above `N_max` establishes that no configured candidate can satisfy the hard method; it does not authorize a larger generated rescue size or threshold relaxation.

## 8. Canonical ordering and precision rules

The reconstructed method freezes these numerical rules:

- all scientific family values/weights/scales/radii/gains/utilities/coverage masses use binary64;
- candidate/witness sparse indices may use exact integer types sufficient for cardinality, but integer representation cannot alter ordering;
- family order is canonical by family ID after family construction;
- hard obligation order is canonical by obligation ID;
- correlation-unit IDs and candidate codes are canonical/current P1 identities;
- final frame tie-breaking uses stable current frame UID;
- all selector/repair floating contender filters use `1e-14` except neighborhood/extent and MVQUAL cross-check tolerances explicitly specified above;
- summations whose association is part of the reference algorithm remain in canonical family/witness order; parallel execution may only distribute independent work and must reproduce the reference result required by qualification.

## 9. Restart and reconstruction semantics

MVSTATE2 or equivalent continuation state is valid only when it authenticates:

- exact `P_train`/split;
- target-order evidence/reference family identities;
- exact MVIDX family/obligation/correlation identities;
- MVSEL2 policy/version and exact selected prefix;
- configured ladder where shell position matters;
- repair policy and exact repaired-prefix/repair-plan identity after divergence.

Durable scientific continuation state contains only quantities needed to reconstruct the exact forward state: selected prefix/order, witness multiplicities/coverage mass, obligation counts, correlation counts and representative state or an exactly reconstructible equivalent.

Lazy heaps, cached candidate marginals, native batch scratch and worker/preflight decisions are execution-only.

After any accepted REPAIR2 swap, every pre-swap prefix-dependent selector cache/checkpoint/journal is stale. Reconstruct from the repaired prefix before suffix selection. Zero-swap shells do not invalidate an otherwise authentic selector state.

Fresh and resumed execution must yield identical complete order, repair trace and configured qualification evidence.

## 10. Current-architecture exclusions

Do not restore as D2 authority:

- per-label-domain or per-CV-fold target-order domains;
- historical fixed-eight target-size universe;
- historical old target-size reducer/outcome authority;
- DATA7 independent quota/FPS membership selection;
- MVSEL1 eager inverse candidate-marginal method;
- approximate/ANN/stochastic coverage or selection;
- foundation residuals for a scratch protocol;
- selector-irrelevant DATA7 training objective/checkpoint fields as membership authority;
- any per-`N` independent selector/graph;
- post-selection evidence feedback into membership.

## 11. D2 falsification requirements

Independent review and later implementation qualification must attempt at least:

1. direct dense/reference vs NEIGHBOR1 exact adjacency at metric boundaries;
2. direct TargetCoverage vs MVIDX covered-mass equality;
3. full-forward vs optimized/lazy MVSEL2 rank equality at every rank on adversarial bounded fixtures;
4. stable first-canonical bottleneck-family behavior under `1e-14` ties;
5. hard-obligation gain priority over discretionary utility;
6. condition/event/profile/extent/correlation obligation satisfaction;
7. exact current P2 condition authority with no historical label-domain substitution;
8. target-label and foundation-residual leakage tests against `M3`/CV/outcome perturbations;
9. scratch mode proving absence of foundation-provider acquisition;
10. REPAIR2 scalar/optimized proposal equality and exact swap trace;
11. lower-prefix immutability through repair;
12. post-repair state reconstruction equality to primitive replay;
13. full-order continuation beyond current `N_max` by the same MVSEL2 method;
14. direct MVQUAL vs progressive/bounded optimized qualification equality;
15. qualification monotonicity;
16. worker/backend/chunk/cache/restart invariance of scientific outputs.

A failure is not repaired by widening tolerances or lowering coverage thresholds unless D1/D2 is explicitly reopened.

## 12. D2 -> D3 handoff after acceptance

Once and only once this D1/D2 pair is independently accepted and human-ratified, D3/D4 must realize:

```text
exact P_train
 -> current-compatible selector evidence
 -> TargetCoverageReference
 -> FEAS1
 -> exact NEIGHBOR1/MVIDX
 -> MVSEL2 complete order with configured-shell REPAIR2
 -> independent configured-prefix MVQUAL
 -> one current P2 TargetTrainingOrder / qualification projection
 -> unchanged P3 target-size execution/reducer
```

D3 owns persistence/currentness/resource/concurrency/build topology. Those choices may optimize but may not alter the numerical method above.
