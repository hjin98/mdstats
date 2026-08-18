# Part V - Multi-view target-data architecture

## Motivation and authority

A target-data subset must cover several physically meaningful feature views simultaneously. Optimizing only an average distance or one descriptor can hide a severe deficit in another required view. The multi-view architecture treats each required family as an explicit coverage constraint, diagnoses full-pool feasibility before subset optimization, and preserves deterministic nested target sets so size/fidelity comparisons are not confounded by resampling.

The architecture follows four rules:

1. feasibility precedes subset optimization;
2. hard coverage cannot be traded for aggregate utility;
3. redundancy is defined through unique covered witness mass and hard/provenance obligations rather than local density alone;
4. selector state and independent qualification remain separate authorities.

## Exact neighborhood graph

For feature family $m$, let $x_w^{(m)}$ be witness coordinates, $x_c^{(m)}$ candidate coordinates, $D_m$ the frozen scaling transform, and $r_w^{(m)}$ the authoritative witness radius. Exact adjacency is

$$
A_{wc}^{(m)} =
\mathbf 1\!\left[
\left\|D_m\left(x_w^{(m)}-x_c^{(m)}\right)\right\|_2
\le r_w^{(m)}
\right].
$$

Production authority uses exact radius semantics; approximate-neighbor substitutions are not scientifically equivalent unless a future accepted specification explicitly changes that contract.

For selected subset $S$,

$$
n_w^{(m)}(S)=\sum_{c\in S} A_{wc}^{(m)},
$$

and weighted family coverage is

$$
C_m(S)=
\frac{\sum_w \omega_w^{(m)}\,\mathbf 1[n_w^{(m)}(S)>0]}
     {\sum_w \omega_w^{(m)}}.
$$

For hard threshold $\tau$ defined by the current coverage policy, robust deficit is

$$
D_{\max}(S)=\max_m \max\!\left(0,\tau-C_m(S)\right).
$$

A weighted average cannot substitute for a failed required view.

## FEAS1 - full-pool feasibility and fragility

FEAS1 evaluates the complete eligible candidate/reference authority before subset optimization. It verifies expected self/cross support, measures low-support fragility, records candidate-degree/support evidence, and derives conservative lower bounds needed to satisfy hard support/obligation constraints.

For witness $w$,

$$
d_w^{(m)}=\sum_{c\in \mathcal C}A_{wc}^{(m)}.
$$

Low-degree witness mass identifies regions where correlation-unit exclusion or subset restriction can destroy support. A capacity diagnosis is evidence that a requested ceiling/rung cannot satisfy the frozen predicates; it is not permission to relax those predicates silently.

## MVIDX1 - one shared exact sparse relation

MVIDX1 reuses the exact neighborhood relation already produced/qualified for the same semantic inputs. FEAS1 and MVIDX are therefore consumers of one exact neighborhood authority rather than independent geometric implementations.

Canonical sparse execution uses witness-oriented CSR-equivalent storage with fixed typed offsets/indices and FP64 scientific weights stored separately. Identity binds candidate/reference ordering, family/scaling/radius/distance semantics, cardinalities, and cache/schema version; execution-only worker/block/queue/storage choices are excluded.

MVIDX adopts authenticated forward witness-to-candidate CSR and constructs candidate-to-witness inverse state without repeating geometry. Forward/inverse edge cardinality and identities are cross-checked exactly.

Large inversions may use the current deterministic out-of-core implementation described in Part VI, but in-memory and file-backed realizations remain byte-equivalent for authoritative sparse arrays.

## MVSEL1 - deterministic progressive selection

MVSEL constructs one global selection order whose permitted target sets are prefixes/rungs defined by the current target-data policy. Mandatory reservations and unsatisfied hard views/strata are serviced before discretionary representative filling.

At each rank, admissible candidates are compared by the frozen lexicographic priorities, including hard/worst-view deficit reduction, newly covered weighted mass, correlation/provenance balance, representative gain, normalized diversity, and stable candidate identity as applicable.

Rank authority is sequential because selection state changes after every accepted candidate. Parallel/vector execution may accelerate exact sparse state preparation/mutation only when the authoritative candidate choice and FP state remain equivalent.

The selector maintains witness multiplicity, hard-obligation state, and candidate marginal state incrementally through inverse adjacency. Full candidate-by-witness rescoring after each rank is not the current execution architecture.

## REPAIR1 - exact shell repair

For selected candidate $c$, unique covered mass follows from multiplicity-one witnesses:

$$
U(c\mid S)=
\sum_m\sum_{w:A_{wc}^{(m)}=1}
\omega_w^{(m)}\,\mathbf 1[n_w^{(m)}(S)=1].
$$

Removal candidates must have sufficiently small/allowed unique contribution and no unique mandatory obligation. Replacement candidates come from the declared deficit/frontier policy. Every accepted swap obeys the frozen objective/tie hierarchy and preserves lower protected prefixes/rungs.

Proposal scoring within one immutable pre-swap state may execute concurrently, but accepted-winner comparison and authoritative state mutation remain deterministic. Exact selector-to-repair state reuse is governed by Part VI: a pure-selector checkpoint is valid only before repair divergence.

## MVQUAL1 - independent same-N qualification

MVQUAL independently recomputes coverage/obligation evidence for candidate subsets at identical cardinality. It records the current hard-view deficits, uncovered mass/count, redundancy/unique-support evidence, provenance/correlation diversity, and other policy-defined diagnostics.

Selector-internal counters are not accepted as independent qualification evidence. Qualification may share authenticated primitive sparse inputs but recomputes the relevant predicates through its own verification path. Locked-test data cannot tune radii, weights, repair budgets, tie rules, or qualification thresholds.

## Target-size and fidelity funnel

The allowed nested sizes and screening/fidelity stages are current specification/policy, not architecture chronology. Architecture requires:

- a deterministic ordered/rung family whose smaller accepted sets are protected prefixes of larger ones where the current policy declares nesting;
- a hard coverage/obligation feasibility screen before expensive training;
- deterministic reduction of surviving candidate sizes under the declared zero-shot/short/full training policy;
- the smaller-size tie preference whenever the current indistinguishability criterion is satisfied;
- fail-closed behavior when too few sizes satisfy the minimum coverage/feasibility requirement;
- full-fidelity comparison only among survivors authorized by the earlier current-policy stages.

The exact size list, epoch budgets, indistinguishability threshold, survivor counts, and coverage threshold belong to the current target-data specifications/policies and are not duplicated here as a developer roadmap.

## Scientific non-negotiables

Execution optimization does not authorize approximate neighborhood search, relaxed hard coverage, changing correlation/leakage boundaries, altering sequential selection/repair decision authority, or using locked evidence to tune target-data policy. Any scientific change to those semantics requires an explicit specification/architecture revision rather than an execution optimization.
