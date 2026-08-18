# Part V - Multi-view target-data architecture

## Motivation

A target-data subset must cover several physically meaningful feature views simultaneously. Optimizing only an average distance or one descriptor can hide a severe deficit in another required view. The multi-view design therefore treats each required family as an explicit coverage constraint, diagnoses full-pool feasibility before subset optimization, and preserves exact nested prefixes so target-size learning comparisons are not confounded by resampling.

The architecture follows four rules:

1. feasibility precedes subset optimization;
2. hard coverage cannot be traded for aggregate utility;
3. redundancy is defined through **unique covered witness mass**, not merely local density;
4. the selector and the independent coverage verifier remain separate authorities.

## Exact neighborhood graph

For feature family $m$, let $x_w^{(m)}$ be witness coordinates, $x_c^{(m)}$ candidate coordinates, $D_m$ the frozen scaling transform, and $r_w^{(m)}$ the authoritative witness radius. Define the exact binary adjacency

$$
A_{wc}^{(m)} =
\mathbf 1\!\left[
\left\|D_m\left(x_w^{(m)}-x_c^{(m)}\right)\right\|_2
\le r_w^{(m)}
\right].
$$

The production search is exact (`eps=0`) and uses `scipy.spatial.cKDTree` radius queries; SciPy exposes explicit worker control for these searches [26, 33]. Approximate-neighbor methods are outside the current scientific authority.

For a selected subset $S$, witness multiplicity and weighted family coverage are

$$
n_w^{(m)}(S)=\sum_{c\in S} A_{wc}^{(m)},
$$

$$
C_m(S)=
\frac{\sum_w \omega_w^{(m)}\,\mathbf 1[n_w^{(m)}(S)>0]}
     {\sum_w \omega_w^{(m)}}.
$$

With frozen hard threshold $\tau=0.95$, the robust deficit is

$$
D_{\max}(S)=\max_m \max\!\left(0,\tau-C_m(S)\right).
$$

A weighted average is not a substitute for this worst-view condition.

## FEAS1 - feasibility, fragility, and capacity evidence

FEAS1 evaluates the complete eligible development pool before subset optimization. It verifies expected self-cover, measures cross-support fragility, records candidate-degree histograms, and derives conservative lower bounds on the cardinality required to satisfy hard support/obligation constraints.

For witness $w$, full-pool support degree is

$$
d_w^{(m)}=\sum_{c\in \mathcal C}A_{wc}^{(m)}.
$$

Low-degree witness mass identifies fragile regions where deletion or correlation-unit exclusion can destroy support. FEAS1 may diagnose `cross_support_fragile` without changing the frozen hard threshold. A proven lower bound above the fixed 16,384 ceiling is a capacity diagnosis, not permission to relax coverage.

## MVIDX1 - one shared sparse graph, not a second neighborhood search

MVIDX1 SHALL reuse the exact neighborhood output produced by FEAS1 whenever the semantic identity matches. FEAS1 and MVIDX1 are therefore consumers of one internal **ExactNeighborhoodEngine**, not separate geometric implementations.

The canonical execution substrate for each family is witness-oriented CSR-equivalent storage:

- `witness_offsets`: 64-bit offsets when required by edge count;
- `candidate_indices`: `uint32` when candidate cardinality permits;
- FP64 scientific weights stored separately;
- content identity bound to domain/candidate ordering, family/scaling identity, witness coordinates, radii, distance semantics, and cache-format version.

Worker count, query block size, queue depth, and other execution-only knobs SHALL NOT enter the scientific neighborhood identity. Changing parallelism must not invalidate an exact cache.

CSR/CSC compressed sparse representations store one contiguous index array plus pointer offsets; SciPy documents the canonical row/column forms and conversions [34]. MVIDX1 adopts the authenticated FEAS1 witness-to-candidate CSR and constructs the candidate-to-witness inverse graph without repeating cKDTree geometry.

### Stable parallel CSR-to-CSC transpose

The inverse graph is constructed by a deterministic two-pass algorithm:

1. parallel block-local candidate-degree histograms;
2. canonical prefix reduction to global candidate offsets;
3. precomputed deterministic destination ranges per block;
4. parallel fill into disjoint ranges without atomics;
5. verification that forward and inverse edge counts and identities agree exactly.

This exposes parallelism while preserving canonical within-candidate witness order.

## MVSEL1 - deterministic progressive selection

Selection constructs one global order whose prefixes are the planned target sizes. Phase A services mandatory reservations and unsatisfied hard views/strata. Phase B fills remaining capacity with a density-aware representative objective after hard obligations are met.

At each rank, admissible candidates are compared lexicographically by frozen priorities including worst-view deficit reduction, newly covered weighted mass, provenance/correlation balance, representative gain, normalized diversity, and stable frame identity. Rank generation is sequential because selection state changes after every accepted candidate; exact performance work therefore targets sparse incremental state updates rather than speculative rank selection.

The selector maintains per-witness multiplicity and per-candidate marginal state. When a witness changes state, inverse adjacency updates only candidates touching that witness. Full candidate-by-witness rescoring after every rank is forbidden.

## REPAIR1 - exact shell repair from multiplicity

For selected candidate $c$, exact unique covered mass is obtained from witnesses with multiplicity one:

$$
U(c\mid S)=
\sum_m\sum_{w:A_{wc}^{(m)}=1}
\omega_w^{(m)}\,\mathbf 1[n_w^{(m)}(S)=1].
$$

This avoids literal leave-one-out recomputation of complete coverage. Removal candidates must have negligible unique contribution and no unique hard/provenance role. Replacement candidates are drawn from the deficit frontier and every accepted swap must strictly improve the frozen lexicographic objective while remaining inside the active shell; lower-rung prefixes never change.

Within one repair iteration, proposal evaluations share an immutable pre-swap state and may execute concurrently. The accepted proposal is chosen afterward by the original deterministic comparison order.

## MVQUAL1 and independent authority

MVQUAL1 compares legacy and multi-view subsets at identical cardinality using independent coverage recomputation. It records $D_{\max}$, aggregate deficit, uncovered mass/count, redundancy metrics, provenance/correlation diversity, and

$$
N_{95}=\min\{N:\text{all hard predicates pass at size }N\}.
$$

Selector-internal coverage is not accepted as independent qualification evidence. Locked-test data cannot tune radii, weights, repair budgets, or tie rules.

## Fixed size/fidelity funnel

The planned nested rungs are

$$
128,256,512,1024,2048,4096,8192,16384.
$$

Only hard-coverage-qualified rungs can survive the learning funnel. Candidate counts reduce as

$$
8\xrightarrow{3\ \mathrm{epochs}}4
\xrightarrow{10\ \mathrm{epochs}}2
\xrightarrow{30\ \mathrm{epochs}}1.
$$

The arrows denote surviving candidate count, not dataset-size halving. Fewer than four hard-qualified rungs fails closed before the 10-epoch stage.
