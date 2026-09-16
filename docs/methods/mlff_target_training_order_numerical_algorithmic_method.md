---
title: "mdstats MLFF Target-Training Order Numerical Algorithmic Method"
artifact_level: "D2 numerical algorithm design"
status: "accepted-current scoped D2 authority"
protocol_version: "6.3.0"
accepted_date: "2026-09-15"
reviewed_candidate_commit: "815823494c88969944eee8f58a6cf107d97bcc09"
recovery_snapshot: "3937881ef00222e80845aa81f5471d89a4a7736c"
workplan_id: "MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1"
---

# mdstats MLFF Target-Training Order Numerical Algorithmic Method

## 1. Scope and authority

This paper is the sole current D2 owner for the numerical realization of the MLFF `TargetTrainingOrder` / `pi_train` method defined by `mlff_target_training_order_scientific_method.md`.

It was reconstructed from the mature pre-P6 multi-view selector lineage, independently reviewed under Protocol 6.3, and stakeholder-ratified on 2026-09-15 against reviewed candidate `815823494c88969944eee8f58a6cf107d97bcc09`.

For this scoped surface, this paper supersedes conflicting target-order construction/qualification text in `mlff_numerical_algorithmic_method.md`. The general numerical method remains current for every unaffected P1/P2/P3, `pi_eval`, training, reducer, CV, replay, production, and threshold-separation contract.

The current method chain is

```text
exact P_train
 -> authenticated selector-input lineage
 -> sole fitted TargetCoverageReference
 -> FEAS1
 -> exact NEIGHBOR1 / MVIDX1 with canonical obligations
 -> exact MVSEL2 master order with certified-lazy Phase B
 -> configured-shell REPAIR2
 -> exact post-repair reconstruction
 -> independent configured-prefix MVQUAL
 -> one current TargetTrainingOrder / qualification projection
```

Historical label-domain/fold fan-out and the historical fixed `128..16384` target-size universe are not current numerical authority.

## 2. Selector evidence domain

The selector operates on one deterministic canonical ordering

```text
P_train = (u_0, ..., u_{n-1}).
```

Every selector-specific transform/reference family is fitted or projected on exact `P_train`. Partition-independent raw descriptors may exist earlier, but statistics, quantiles, robust scales, local radii, residual vectors, family weights, event/profile support incidence, and equivalent fitted selector state are rebound to exact `P_train` before order construction.

`TargetCoverageReference` is the sole selector-specific fitted numerical owner. Historical DATA7 contributes authenticated lineage/input semantics only.

Excluded are `M3/M1/M2`, post-selection monitor/CV, calibration/locked/challenge evidence, target-size candidate outcomes, reducer evidence, and downstream qualification. Foundation residual families exist only when the current target-size protocol uses a frozen authenticated foundation checkpoint. Profile families exist only when an accepted active profile provider supplies selection evidence.

## 3. Multi-view target-coverage reference

### 3.1 Family witness weights

For required family `m`, let `W_m` be the ordered participating witnesses, `g(w)` the P1 correlation-unit identity, `G_m={g(w):w in W_m}`, and `n_{m,g}` the witness count in unit `g`. Define

$$
\omega_m(w)=\frac{1}{|G_m|\,n_{m,g(w)}}.
$$

Normalize the binary64 vector once by its binary64 sum and store canonical normalized values. Every represented correlation unit therefore receives equal family mass and witnesses inside the unit divide that mass equally. A family with no represented unit is invalid.

### 3.2 Weighted quantiles and robust scale

For values `v_i` with nonnegative normalized weights `omega_i`, weighted quantile `Q(q)` is the first value in stable ascending `v_i` order whose cumulative weight is at least `q`.

For feature column `j`,

```text
s_j = Q_j(0.75)-Q_j(0.25)          if > 1e-12
      Q_j(0.99)-Q_j(0.01)          else if > 1e-12
      max(std_population(x_j),1.0)  otherwise
s_j = max(s_j,1e-12).
```

All statistics use binary64 and equal-value ordering is stable.

### 3.3 Family distance

For a `d`-column family,

$$
d_m(a,b)=\sqrt{\frac{1}{d}\sum_{j=1}^{d}\left(\frac{x_{a,j}-x_{b,j}}{s_j}\right)^2}.
$$

Missing/inapplicable rows do not enter that family. A family requires at least two reference elements. Constant optional scalar families are omitted rather than creating zero-information dimensions.

### 3.4 Local reference radius

Let `beta=1/128`. For witness `w`, remove self mass, renormalize the remaining weights by `1-omega_m(w)`, sort the other witnesses by `d_m(w,.)`, and choose the smallest distance at which

```text
cumulative >= beta - 1e-15.
```

This is `r_m(w)`. A family that cannot reach the requested leave-one-out mass fails preparation.

### 3.5 Exact neighborhood predicate

$$
A_m(w,c)=1
\Longleftrightarrow
d_m(w,c)\le r_m(w)+10^{-12}\max(1,r_m(w)).
$$

The `1e-12` metric tolerance is numerical authority. Worker count, k-d-tree block size, sparse storage, mmap layout, and native/vector backend are execution-only provided they reproduce the same adjacency. Every witness must retain at least one exact candidate support edge.

### 3.6 Covered reference mass

For selected set `S`,

$$
n_m(w;S)=\sum_{c\in S} A_m(w,c),
$$

$$
C_m(S)=\sum_{w\in W_m}\omega_m(w)\mathbf 1[n_m(w;S)>0].
$$

The baseline required-family threshold is exactly `0.95`; a family passes when

```text
C_m(S) + 1e-12 >= 0.95.
```

There is no active named-family threshold override in this accepted baseline.

### 3.7 Extent channels

For extent-bearing channel `j`,

```text
L_j = Q_j(0.01)
U_j = Q_j(0.99).
```

Selected representatives pass when

```text
min_selected x_j <= L_j + 1e-12
and
max_selected x_j >= U_j - 1e-12.
```

Each side is also one required hard obligation with minimum 1.

## 4. Required family catalog

### 4.1 Universal structural families

Required accepted structural feature names are partitioned into:

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

`pair_distance`, `coordination`, and `local_density` are extent-bearing; the others use hard mass coverage without separate extent predicates.

### 4.2 Profile selection families

For each active accepted profile-selection provider, every valid nonconstant scalar selection feature is one required one-dimensional, extent-bearing family over provider-valid frames. Every provider environment-class label represented over `P_train` contributes one required profile-environment obligation. No profile provider is loaded merely because the selector exists.

### 4.3 Raw pair-geometry families

For each applicable accepted pair rule, build required extent-bearing:

1. `bond_length_distribution` from minimum pair distance, mean nearest-neighbor distance, and maximum nearest-neighbor distance;
2. `coordination_distribution` from coordination mean and coordination maximum.

### 4.4 Target-development response families

From exact `P_train` target-development evidence, build required extent-bearing:

1. `force_distribution` containing force-component RMS, mean force norm, maximum force norm, and canonical available force-norm quantile channels;
2. one scalar family for each defined nonconstant accepted channel among energy/atom, instantaneous temperature, hydrostatic strain, deviatoric strain norm, pressure, and stress deviatoric norm.

These are membership-design inputs, not held-out evaluation statistics.

### 4.5 Foundation residual families

Only when the target-size protocol itself uses a frozen authenticated foundation model, construct on exact `P_train`:

- one required extent-bearing global family containing absolute energy error/atom, force-component RMSE, mean force-vector error, and maximum force-vector error;
- one required extent-bearing family per represented atomic species containing component RMSE, mean vector error, and maximum vector error.

Foundation checkpoint/head/provider identity is part of selector-evidence identity. Historical final-development/label-domain residual catalogs are not current authority.

## 5. FEAS1

FEAS1 executes before selection as a fail-closed feasibility/fragility gate over exact `P_train` and the same neighborhood/canonical-obligation authority. It verifies domain/self-support consistency, obligation support capacity, and conservative lower-bound evidence for hard family/obligation cardinality.

Historical support-degree bins `(2,4,8,16,32)`, own-correlation-unit exclusion, and fragile-zero-mass tolerance `1e-12` remain diagnostics. Historical `maximum_candidate_size=16384` is retired; the configured feasibility horizon is current `N_max=max(candidate_sizes)`. A proven lower bound above current `N_max` establishes configured-ladder infeasibility; it does not create rescue sizes or relax the method.

## 6. Canonical hard obligations

Automatic obligations are, where applicable:

1. each represented current P2 condition, minimum 1;
2. each recognized represented structural-event type, minimum 1;
3. each represented active profile environment class, minimum 1;
4. each extent lower side, minimum 1;
5. each extent upper side, minimum 1;
6. each represented current P1 correlation interval/unit, minimum 1.

Current explicit `ResolvedTargetSizePolicy.hard_support_obligations` are projected through current P2 condition-attribute authority with their declared positive minima.

For retained source obligation `o`, define

```text
L(o) = (
  obligation_kind,
  applicability_scope,
  family_identity_or_none,
  target_selector_or_identity,
  relation_or_side,
  applicability_domain
)
A(o) = exact candidate-incidence set on current P_train
k(o) = positive required minimum
```

`k(o)` and source-local IDs are not locus identity. Canonicalization is exactly:

1. validate supplied source-ID uniqueness inside its source namespace;
2. project automatic and explicit obligations into exact current `P_train` semantics;
3. remove retired-topology-only obligations;
4. normalize `(L,A,k)` and source provenance;
5. fail closed if one supplied source ID is reused for different semantics;
6. group only by equal accepted `L` semantics, never by incidence equality alone;
7. require exact incidence equality inside a locus group;
8. define

   $$
   k_{\mathrm{canonical}}(L)=\max_{o\in L} k(o);
   $$

9. retain aliases/minima as provenance only, not additional hard-gain votes;
10. assign one deterministic canonical ID binding locus, effective minimum, incidence, applicability, and governing policy identity;
11. build MVIDX incidence and all selector/repair/qualification counts from the canonical set only.

Automatic and explicit namespaces must prevent accidental identifier collision. Equality of incidence alone never proves semantic equivalence; for example a `user_label.*` selector does not alias an event/profile locus unless accepted provider semantics establish that equivalence.

Different scientific loci remain distinct even with identical incidence.

For selected state `S`,

$$
q_o(S)=|S\cap A_o|,
$$

and obligation `o` is satisfied iff `q_o(S)\ge k_o`.

## 7. MVIDX scientific sparse authority

MVIDX contains exact sparse scientific incidence needed downstream:

- witness-to-candidate and candidate-to-witness incidence for every required family;
- canonical obligation-to-candidate and candidate-to-obligation incidence;
- current P1 candidate correlation-unit codes.

Persistence dtype/layout may change only as an exact representation. Scientific adjacency, incidence, canonical ordering, and identity cannot change.

## 8. Exact MVSEL2 semantics

All scientific decision arithmetic is binary64 unless explicitly integer. Every candidate index, family, witness, obligation, correlation unit, and final UID tie order is canonical and identity-bound.

State includes selected/available membership and ordered prefix, each family witness multiplicity and covered mass, canonical obligation counts, correlation-unit selected counts, and reconstructible representative state. Lazy heaps, marginal caches, native batches, and worker decisions are not scientific state.

### 8.1 Candidate primitives

For available candidate `c`, define

$$
H(c)=\left|\{o:q_o(S)<k_o\text{ and }c\in A_o\}\right|,
$$

$$
G_m(c)=\sum_{w:A_m(w,c)=1,\,n_m(w)=0}\omega_m(w),
$$

$$
G(c)=\sum_m G_m(c),
$$

$$
R(c)=\sum_m\sum_{w:A_m(w,c)=1}\frac{\omega_m(w)}{n_m(w)+1}.
$$

For the sparse-diversity term, define

$$
W_m(c)=\{w\in W_m:A_m(w,c)=1\},
$$

$$
M(c)=\{m:|W_m(c)|>0\}.
$$

If `M(c)` is empty, define `D(c)=0`. Otherwise,

$$
D(c)=
\frac{1}{|M(c)|}
\sum_{m\in M(c)}
\left[
\frac{1}{|W_m(c)|}
\sum_{w\in W_m(c)}
\frac{1}{n_m(w)+1}
\right].
$$

This is exactly the nested arithmetic mean over nonempty family rows and their supporting witnesses; the explicit finite-sum form avoids renderer-specific named-operator macros.

A stronger minimum extends how long a canonical locus remains unsatisfied. It does not multiply that locus's hard-gain vote and hard gain is not proportional to deficit magnitude.

### 8.2 Phase A

Phase A remains active while a canonical hard obligation is unsatisfied or a required family is below threshold within selector tolerance. Let `epsilon=1e-14`. Filter contenders lexicographically:

1. if any required obligation is unsatisfied, maximal integer `H(c)`;
2. choose the first family in canonical order minimizing `C_m/0.95` among families tied within `epsilon` at the minimum;
3. maximal bottleneck-family `G_m(c)` within `epsilon`;
4. maximal total `G(c)` within `epsilon`;
5. minimum current selected count of the candidate's own correlation unit;
6. maximal `R(c)` within `epsilon`;
7. maximal `D(c)` within `epsilon`;
8. minimum stable current frame UID.

The winner updates multiplicities, coverage masses, canonical obligation counts, and its correlation-unit count exactly once.

### 8.3 Phase B

After every canonical obligation and required-family threshold is satisfied, filter by:

1. maximum representative gain within `1e-14`;
2. minimum selected count of the candidate's correlation unit;
3. maximum sparse diversity within `1e-14`;
4. minimum stable UID.

Continue until all `P_train` candidates are eventually ordered, subject to configured-shell REPAIR2.

### 8.4 Full-forward oracle and certified-lazy exactness

The scalar/full-forward algorithm is the numerical oracle. Lazy Phase B is permitted only as exact-equivalent acceleration.

At Phase-A to Phase-B transition, and after authoritative reconstruction invalidating representative marginals, score every available candidate exactly. This establishes generation `g` and exact `R_g(c)`. Initialize

```text
B_g(c) = nextafter(R_g(c), +infinity).
```

After selections, stale earlier scores may serve only as conservative upper bounds while representative gain is monotone non-increasing. A stale candidate must be rescored exactly before its value is treated as current. If a refreshed representative gain exceeds its earlier exact value by more than the `5e-13` monotonicity guard, fail the invariant; do not widen ranking tolerance.

Maintain exact incumbent `R_best`. Refresh every stale candidate whose bound can reach the inclusive contender region. Certification terminates only when

```text
B_max < R_best - 1e-14.
```

At termination, every candidate that can satisfy

```text
R(c) >= R_best - 1e-14
```

has an exact current score. Correlation balance, diversity, and UID are applied only to this certified exact contender set.

If conservative bounds cannot be proved, generations disagree, or a numerical invariant fails, discard/rebuild the lazy frontier or fall back to full-forward exact scoring. Every selected rank must equal the full-forward oracle under identical canonical state. Execution completion order has no scientific tie authority.

## 9. Configured-shell REPAIR2

Let current configured sizes be strictly increasing `N_1<...<N_K`, `N_0=0`. Historical fixed-eight sizes are retired. At shell `i`, REPAIR2 may remove only ranks `[N_{i-1},N_i)`; lower ranks are immutable.

### 9.1 Removal eligibility

For selected candidate `c`, unique covered mass is total family reference mass of witnesses currently covered only by `c`. Candidate is removable only when

```text
unique_mass(c) <= 1e-14
```

and removal does not increase the deficit of any canonical hard obligation.

Order removable candidates by representative loss ascending, removed candidate correlation-unit selected count descending, then removed UID ascending. Keep at most 64.

### 9.2 Replacement frontier

For a contemplated removal, evaluate replacement against immutable pre-swap state using:

1. maximal hard gain when obligations remain pending;
2. first canonical bottleneck family;
3. maximal bottleneck-family new coverage;
4. maximal total new coverage;
5. minimum hypothetical correlation-unit count after removal;
6. maximal representative gain after removal;
7. maximal sparse diversity after removal;
8. minimum replacement UID.

### 9.3 Exact global objective

Define hard deficit

$$
D_{\mathrm{hard}}(S)=\sum_{o\in O_{\mathrm{canonical}}}\max(0,k_o-q_o(S)).
$$

and

```text
J(S) = (
  D_hard(S),
  min_m C_m(S),
  sum_m C_m(S),
  U_rep(S),
  -sum_g b_g(S)^2
)
```

where

$$
U_{\mathrm{rep}}(S)=\sum_m\sum_w\omega_m(w)H_{n_m(w;S)},
\qquad H_k=\sum_{j=1}^{k}\frac1j,\quad H_0=0.
$$

Comparison minimizes `D_hard`, then maximizes components 2-4 with `1e-14` floating tolerance, then maximizes the exact integer balance component. A swap is admissible only if it strictly improves `J` and every family satisfies

```text
C_m(after) + 1e-14 >= C_m(before).
```

Objective-equivalent admissible proposals use ascending `(representative_loss, removed_rank, removed_UID, replacement_UID)`.

### 9.4 Limits and rank inheritance

Per configured shell: at most 2 passes, 32 accepted swaps, and removal shortlist 64. The accepted replacement inherits the removed rank. If the replacement already appears at a future rank, move the removed candidate to that future rank. The master permutation is preserved and earlier configured prefixes remain immutable.

### 9.5 Post-repair reconstruction and complete order

After any accepted swap, every prefix-dependent lazy/frontier/marginal/cache/checkpoint/journal state derived from the pre-swap prefix is stale for continuation. Reconstruct exact forward state from authenticated primitive family/obligation/correlation evidence and the exact repaired prefix. If continuation begins in Phase B, perform an exact all-candidate rebase. A zero-swap shell may retain otherwise authentic state whose exact prefix identity still matches.

After the final configured shell, continue the same exact optimized MVSEL2 method until every frame in `P_train` is ordered. There is no extra repair shell and no UID-only, condition-round-robin, scalar-only, or alternate-selector suffix.

## 10. Independent MVQUAL

For each configured `N`, `T_N` is the exact repaired nested prefix. MVQUAL independently evaluates it from immutable `TargetCoverageReference` and canonical obligation definitions. MVIDX may be an exact secondary sparse cross-check; selector/repair counters are never its sole oracle.

Direct family scoring recomputes covered mass under the exact family metric/local radii and extent predicates. Canonical obligation scoring recomputes `q_o(T_N)` against effective `k_o`.

MVIDX family mass must agree with direct TargetCoverage mass using

```text
rtol = 0
atol = 5e-12.
```

Disagreement is an invariant error.

A configured candidate qualifies iff the exact prefix exists, labels are training-usable, all required family masses pass, required extents pass, and every canonical hard obligation passes. The current P2 qualification record is the sole public/current projection.

Under fixed nested prefixes/evidence, qualification must have the form `FAIL* -> PASS*`. `PASS -> FAIL` fails closed. The current target-size funnel's minimum number of qualified configured candidates remains unchanged. MVQUAL cannot create rescue sizes, relax 0.95, relax extents, or reduce obligation minima. Manual selection of an unqualified configured size fails before training/CV.

Among qualified candidates, MVQUAL does not rank or tie-break size; current P3 target-force reducer semantics remain authoritative.

## 11. Precision and canonical ordering

- scientific family values, weights, scales, radii, gains, utilities, and masses are binary64;
- exact integer sparse types may be chosen to fit cardinality but cannot alter ordering;
- family order is canonical by family ID after construction;
- obligation order is canonical by canonical obligation ID;
- correlation-unit IDs/codes are current canonical P1 identities;
- final tie-breaking uses stable current frame UID;
- selector/repair floating contender filters use `1e-14` except explicitly stated neighborhood/extent/MVQUAL tolerances;
- summations whose association belongs to the reference algorithm remain in canonical family/witness order; parallel execution may distribute only independent work while reproducing required reference results.

## 12. Restart and reconstruction

MVSTATE2 or an equivalent continuation object is valid only if it authenticates the exact `P_train` split, selector-evidence/reference identities, exact MVIDX family/canonical-obligation/correlation identities, MVSEL2 policy/version and selected prefix, configured ladder where shell position matters, and repair policy plus exact repaired-prefix/repair-plan identity after divergence.

Durable scientific continuation state contains only quantities needed to reconstruct exact forward state: selected prefix/order, witness multiplicities/coverage mass, canonical obligation counts, correlation counts, and representative state or exact equivalents. Lazy heaps, cached marginals, native scratch, and preflight decisions are reconstructible execution state.

Fresh and resumed execution must yield identical complete order, repair trace, and configured qualification evidence.

## 13. Performance-preserving execution contract

The numerical method does not require one software realization, but optimized execution must preserve exact scientific outputs.

The mature accepted execution lineage includes:

- file-backed/out-of-core NEIGHBOR1 construction with bounded anonymous finalization scratch and storage admission;
- exact sparse MVIDX forward/inverse incidence with file-backed large inverse arrays and bounded chunk scratch;
- packed/shared persistence restoring O(1)-in-family-count mapped-file descriptors rather than one mapping per family;
- certified-lazy MVSEL2 using reconstructible witness-term caches;
- a qualified native/OpenMP Phase-B candidate-row scoring primitive that leaves certification, family accumulation, contender logic, ties, and mutation in canonical scientific control;
- real-MVIDX worker preflight probing serial, powers-of-two, and the exact authorized endpoint, requiring bitwise FP64 equality and choosing the smallest parallel width within 5% of measured best when best parallel speedup is at least 1.05x, else one worker.

Worker count, queue order, block size, mmap layout, cache residence, timing, and preflight choice are execution-only and must not enter scientific identity.

If current-envelope performance is poor, first verify that the accepted optimized sparse/lazy/native execution closure is active. Performance design may be reopened only on measured evidence; it may not be hidden by truncating the order or changing scientific ranking.

## 14. Excluded historical authority

Do not restore as current numerical authority:

- per-label-domain/per-CV-fold target-order domains;
- historical fixed-eight target sizes or fixed 16384 authority ceiling;
- historical target-size reducer/outcome authority;
- DATA7 independent quota/FPS membership selection;
- MVSEL1 eager inverse candidate-marginal method;
- approximate/ANN/stochastic coverage or selection;
- foundation residuals for a scratch protocol;
- selector-irrelevant objective/checkpoint fields as membership authority;
- independent per-`N` selectors/graphs;
- post-selection evidence feedback into membership.

## 15. Required falsification/oracle evidence

Implementation qualification must attempt at least:

1. direct dense/reference vs NEIGHBOR1 adjacency at metric boundaries;
2. direct TargetCoverage vs MVIDX covered-mass equality;
3. full-forward vs optimized/lazy MVSEL2 rank equality at every rank on bounded adversarial fixtures;
4. stable first-canonical bottleneck behavior under `1e-14` ties;
5. hard-obligation gain priority over discretionary utility;
6. exact alias invariance;
7. weaker same-locus requirements subsumed by stronger via `max(k)`;
8. automatic min-1 plus explicit same-locus min-`k>1` equivalent to one min-`k` obligation;
9. source-ID rename invariance and semantic-collision failure;
10. same purported locus with changed incidence fails closed;
11. different loci with identical incidence remain distinct;
12. a minimum-2 locus remains unsatisfied after one member and contributes exactly one hard-gain vote;
13. condition/event/profile/extent/correlation satisfaction;
14. current P2 condition authority with no historical label-domain substitution;
15. leakage perturbation tests against `M3`/CV/outcome evidence;
16. scratch mode proves no foundation-provider acquisition;
17. REPAIR2 scalar/optimized proposal and swap-trace equality;
18. lower-prefix immutability through repair;
19. post-repair reconstruction equality to primitive replay;
20. complete-order continuation beyond current `N_max` by the same MVSEL2 method;
21. direct MVQUAL vs optimized qualification equality;
22. qualification monotonicity;
23. worker/backend/chunk/cache/restart invariance of scientific outputs.

Tolerance widening or threshold reduction is not an implementation fix; it requires explicit D1/D2 reopening.

## 16. D2 -> D3 handoff

D3 shall realize one current chain:

```text
exact P_train
 -> authenticated current-compatible selector evidence
 -> sole TargetCoverageReference
 -> FEAS1
 -> exact NEIGHBOR1/MVIDX with canonical obligations
 -> exact optimized MVSEL2 complete order
 -> configured-shell REPAIR2
 -> exact post-repair reconstruction
 -> independent configured-prefix MVQUAL
 -> one current P2 TargetTrainingOrder / qualification projection
 -> unchanged P3 target-size execution/reducer
```

D3 owns persistence/currentness, resource admission, concurrency, build topology, and integration into current `prepare`/CampaignStore ownership. Those choices may optimize but may not alter this D2 method.
